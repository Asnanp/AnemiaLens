from __future__ import annotations

import ast
import json
import logging
import re
from collections import OrderedDict
from typing import Literal

import requests as _requests

from app.config import settings
from app.schemas import (
    GuidanceResult,
    GuidanceRuntimeStatus,
    PredictionResult,
    SymptomInput,
    TriageResult,
)

_FIELD_LIMITS = {
    "explanation": 480,
    "urgency_guidance": 280,
    "food_advice": 300,
}
_UNSAFE_CLAIM_PATTERN = re.compile(
    r"\b(definitely\s+(?:confirms?|have|has|anemic|anaemic)|confirm(?:ed|s)?\s+(?:anemia|anaemia)|"
    r"you\s+(?:have|are)\s+(?:anemia|anaemia|anemic|anaemic)|"
    r"diagnoses?\s+(?:anemia|anaemia|iron deficiency)|"
    r"proves?\s+(?:anemia|anaemia)|proof\s+of\s+anemia)\b",
    flags=re.IGNORECASE,
)
_SAFE_DIAGNOSTIC_CONTEXT_PATTERNS = (
    re.compile(r"\bnot a diagnos(?:is|tic)\b", flags=re.IGNORECASE),
    re.compile(r"\bnon-diagnostic\b", flags=re.IGNORECASE),
    re.compile(r"\bdoes not diagnos(?:e|is)\b", flags=re.IGNORECASE),
)
log = logging.getLogger("anemialens.guidance")

_MISTRAL_API_URL = "https://api.mistral.ai/v1/chat/completions"


class GuidanceService:
    def __init__(self) -> None:
        self.mistral_enabled = settings.mistral_enabled
        self.mistral_model = settings.mistral_model.strip()
        self.guidance_timeout = settings.guidance_timeout
        self.guidance_max_tokens = settings.guidance_max_tokens
        self.api_key_configured = bool(settings.mistral_api_key.strip())
        self._fallback_reason: str | None = None
        self._last_provider_error: str | None = None
        self._response_cache: OrderedDict[str, GuidanceResult] = OrderedDict()
        self._response_cache_size = 64

        if not self.mistral_enabled:
            self._fallback_reason = "Mistral guidance is disabled in configuration."
        elif not self.api_key_configured:
            self._fallback_reason = "Mistral API key is missing."

    def generate(
        self,
        triage: TriageResult,
        symptoms: SymptomInput,
        prediction: PredictionResult | None,
        language: str | None = None,
        region: str | None = None,
    ) -> GuidanceResult:
        if not self._should_use_llm(triage, prediction):
            log.info("Skipping LLM: prediction=%s, band=%s", prediction is not None, triage.band)
            return self.generate_smart_fallback(
                triage.band,
                prediction.predicted_hemoglobin if prediction else None,
                prediction.confidence if prediction else None,
                symptoms,
                region,
            )

        payload = self._build_payload(triage, symptoms, prediction, language, region)
        cache_key = self._cache_key(payload)
        cached = self._response_cache.get(cache_key)
        if cached is not None:
            log.info("Returning cached guidance (source=%s)", cached.source)
            self._response_cache.move_to_end(cache_key)
            return GuidanceResult.model_validate(cached.model_dump())

        log.info(
            "Calling Mistral: enabled=%s, key_set=%s, model=%s",
            self.mistral_enabled, self.api_key_configured, self.mistral_model,
        )

        if self._mistral_ready():
            result = self._generate_mistral(
                payload,
                triage_band=triage.band,
                predicted_hemoglobin=prediction.predicted_hemoglobin if prediction else None,
                confidence=prediction.confidence if prediction else None,
                symptoms=symptoms,
                region=region,
            )
            if result is not None:
                log.info("Guidance source: %s", result.source)
                if result.source == "mistral":
                    self._last_provider_error = None
                    self._store_cached_result(cache_key, result)
                return result
        else:
            log.warning(
                "Mistral not ready: enabled=%s, key_configured=%s, fallback_reason=%s",
                self.mistral_enabled, self.api_key_configured, self._fallback_reason,
            )

        return self.generate_smart_fallback(
            triage.band,
            prediction.predicted_hemoglobin if prediction else None,
            prediction.confidence if prediction else None,
            symptoms,
            region,
        )

    def _build_payload(
        self,
        triage: TriageResult,
        symptoms: SymptomInput,
        prediction: PredictionResult | None,
        language: str | None,
        region: str | None,
    ) -> dict[str, object]:
        active_symptoms = [
            label
            for label, active in {
                "fatigue": symptoms.fatigue,
                "dizziness": symptoms.dizziness,
                "pale skin": symptoms.pale_skin,
                "shortness of breath": symptoms.shortness_of_breath,
                "heavy menstrual bleeding": bool(symptoms.heavy_menstrual_bleeding),
                "low iron intake": symptoms.poor_diet_low_iron,
            }.items()
            if active
        ]
        return {
            "triage_label": triage.label,
            "triage_band": triage.band,
            "triage_score": triage.score,
            "screening_text": prediction.screening_text if prediction else None,
            "screening_label": prediction.screening_label if prediction else None,
            "prediction_risk": prediction.anemia_risk if prediction else None,
            "prediction_risk_percent": round(prediction.anemia_risk * 100, 1) if prediction else None,
            "predicted_hemoglobin": prediction.predicted_hemoglobin if prediction else None,
            "confidence": prediction.confidence if prediction else None,
            "confidence_percent": round(prediction.confidence * 100, 1) if prediction else None,
            "uncertainty": prediction.uncertainty if prediction else None,
            "uncertainty_percent": round(prediction.uncertainty * 100, 1) if prediction else None,
            "reliability_flag": prediction.reliability_flag if prediction else None,
            "symptom_count": symptoms.active_count,
            "active_symptoms": active_symptoms,
            "symptoms": symptoms.model_dump(),
            "language": language,
            "region": region,
        }

    def _system_prompt(self) -> str:
        return (
            "You are the guidance engine for AnemiaLens, a smartphone-based anemia screening tool that analyzes conjunctival pallor (inner lower eyelid color) using computer vision. "
            "AnemiaLens estimates hemoglobin levels from eye images and fuses that with self-reported symptoms to produce a triage band: low_risk, moderate_risk, high_concern, or uncertain_retake_needed. "
            "This is a SCREENING tool only — not a diagnostic device. Results must be confirmed with clinical blood testing.\n\n"
            "Your job: write personalized, grounded guidance based on the screening data provided. "
            "Interpret what the hemoglobin estimate and risk score MEAN for this person — don't just repeat the numbers. "
            "For example: if Hb is 13.9 g/dL and risk is 15%, explain that 13.9 is within normal range (normal adult range ~12-17 g/dL) and 15% risk is low. "
            "If Hb is 8.5 g/dL, explain that is significantly below normal and warrants urgent attention. "
            "Reference active symptoms in your guidance — if fatigue + dizziness are present, mention them. "
            "Adapt food advice to the region if provided.\n\n"
            "RULES:\n"
            "- Never say 'you have anemia' or 'you are anemic' — say 'screening suggests' or 'this result indicates'\n"
            "- Never invent numbers, symptoms, or treatments not in the payload\n"
            "- Keep language simple and compassionate\n\n"
            "Return ONLY valid JSON with exactly these keys: explanation, urgency_guidance, food_advice, next_steps.\n"
            "explanation: 2 sentences — interpret what the Hb estimate and risk score mean in plain language (not just repeat them). Mention triage band context.\n"
            "urgency_guidance: 1 sentence — specific timeline based on triage band (low_risk=routine, moderate_risk=1-2 weeks, high_concern=24-48h).\n"
            "food_advice: 1 sentence — concrete iron-rich food examples for the region.\n"
            "next_steps: array of 3-4 short actionable strings tailored to this result.\n"
            "No markdown, no extra keys, no preamble."
        )

    def _user_prompt(self, payload: dict[str, object]) -> str:
        hb = payload.get("predicted_hemoglobin")
        risk_pct = payload.get("prediction_risk_percent")
        conf_pct = payload.get("confidence_percent")
        band = payload.get("triage_band", "unknown")
        label = payload.get("triage_label", "")
        active_symptoms = payload.get("active_symptoms") or []
        region = payload.get("region") or "not specified"
        screening_text = payload.get("screening_text") or ""

        hb_str = f"{hb} g/dL" if hb is not None else "not available"
        # Normal adult Hb range context
        if hb is not None:
            if hb >= 12.0:
                hb_context = "within normal range"
            elif hb >= 10.0:
                hb_context = "mildly below normal"
            elif hb >= 8.0:
                hb_context = "moderately below normal"
            else:
                hb_context = "severely below normal"
        else:
            hb_context = "unknown"

        symptom_str = ", ".join(active_symptoms) if active_symptoms else "none reported"

        return (
            f"AnemiaLens Screening Result:\n"
            f"- Hemoglobin estimate: {hb_str} ({hb_context})\n"
            f"- Anemia risk score: {risk_pct}%\n"
            f"- Model confidence: {conf_pct}%\n"
            f"- Triage band: {band} ({label})\n"
            f"- Active symptoms: {symptom_str}\n"
            f"- Region: {region}\n"
            f"- Model screening text: {screening_text}\n\n"
            "Write personalized guidance for this person based on the above. "
            "Interpret what these numbers mean for them — don't just repeat the values. "
            "This is screening guidance, not a diagnosis."
        )

    def _mistral_system_prompt(self) -> str:
        return (
            "You are Mistral, writing the guidance section for AnemiaLens, a smartphone anemia screening tool. "
            "The system analyzes the inner lower eyelid, combines that signal with symptom input, and returns a screening band: low_risk, moderate_risk, high_concern, or uncertain_retake_needed. "
            "This is screening only, never a diagnosis, and every answer must stay medically cautious.\n\n"
            "Write like a calm clinician or health educator speaking to one person right after their screening. "
            "Sound natural, specific, and grounded in the payload. "
            "Do not sound like a marketing blurb, a lab report template, or a generic wellness article. "
            "Use the hemoglobin estimate, risk score, symptom pattern, and reliability limits to explain what this case means.\n\n"
            "STYLE RULES:\n"
            "- Never say 'you have anemia', 'you are anemic', or any other diagnostic claim\n"
            "- Prefer phrases like 'this screening leans toward', 'this result suggests', or 'this pattern points to'\n"
            "- Mention uncertainty when confidence is limited or reliability is low\n"
            "- Avoid stock phrases like 'calls for closer attention', 'maintain a balanced diet', or 'monitor symptoms' unless you also say why or when\n"
            "- Never invent symptoms, treatments, lab values, or medical history not present in the payload\n"
            "- Keep the tone human, direct, and reassuring without sounding casual\n\n"
            "Return ONLY valid JSON with exactly these keys: explanation, urgency_guidance, food_advice, next_steps.\n"
            "explanation: 2 or 3 sentences. Sentence 1 says what the screening leans toward. Sentence 2 explains why using the actual signal, symptoms, or risk. Sentence 3 is optional and should only be used to explain uncertainty or reassurance.\n"
            "urgency_guidance: 1 or 2 sentences with a concrete follow-up window tied to the triage band.\n"
            "food_advice: 1 sentence with concrete iron-supportive foods, adapted to the region when possible.\n"
            "next_steps: array of 3 or 4 short actions that are specific, non-repetitive, and realistic.\n"
            "No markdown, no extra keys, no preamble."
        )

    def _mistral_user_prompt(self, payload: dict[str, object]) -> str:
        hb = payload.get("predicted_hemoglobin")
        risk_pct = payload.get("prediction_risk_percent")
        conf_pct = payload.get("confidence_percent")
        uncertainty_pct = payload.get("uncertainty_percent")
        reliability_flag = payload.get("reliability_flag") or "unknown"
        band = payload.get("triage_band", "unknown")
        label = payload.get("triage_label", "")
        active_symptoms = payload.get("active_symptoms") or []
        region = payload.get("region") or "not specified"
        screening_text = payload.get("screening_text") or ""
        screening_label = payload.get("screening_label") or "unknown"

        hb_str = f"{hb} g/dL" if hb is not None else "not available"
        if hb is not None:
            if hb >= 12.0:
                hb_context = "within normal range"
            elif hb >= 10.0:
                hb_context = "mildly below normal"
            elif hb >= 8.0:
                hb_context = "moderately below normal"
            else:
                hb_context = "severely below normal"
        else:
            hb_context = "unknown"

        symptom_str = ", ".join(active_symptoms) if active_symptoms else "none reported"

        return (
            f"AnemiaLens Screening Result:\n"
            f"- Hemoglobin estimate: {hb_str} ({hb_context})\n"
            f"- Anemia risk score: {risk_pct}%\n"
            f"- Screening label: {screening_label}\n"
            f"- Model confidence: {conf_pct}%\n"
            f"- Uncertainty: {uncertainty_pct}%\n"
            f"- Reliability flag: {reliability_flag}\n"
            f"- Triage band: {band} ({label})\n"
            f"- Active symptoms: {symptom_str}\n"
            f"- Region: {region}\n"
            f"- Model screening text: {screening_text}\n\n"
            "Write personalized guidance for this person based on the above. "
            "Interpret what these findings mean instead of repeating them. "
            "If reliability is limited, say that clearly in plain language. "
            "Make it sound like a real clinician explaining a screening result, not a report template."
        )

    def _generate_mistral(
        self,
        payload: dict[str, object],
        *,
        triage_band: str,
        predicted_hemoglobin: float | None,
        confidence: float | None,
        symptoms: SymptomInput,
        region: str | None,
    ) -> GuidanceResult | None:
        try:
            text = self._call_mistral_api(payload)
            return self._parse_guidance_response(
                text,
                source="mistral",
                model_used=self.mistral_model,
                provider_used="mistral",
            )
        except Exception as exc:
            self._last_provider_error = self._summarize_error(exc)
            log.warning("Mistral guidance request failed: %s", exc)
            return self.generate_smart_fallback(
                triage_band,
                predicted_hemoglobin,
                confidence,
                symptoms,
                region,
            )

    def _call_mistral_api(self, payload: dict[str, object]) -> str:
        headers = {
            "Authorization": f"Bearer {settings.mistral_api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.mistral_model,
            "messages": [
                {"role": "system", "content": self._mistral_system_prompt()},
                {"role": "user", "content": self._mistral_user_prompt(payload)},
            ],
            "max_tokens": self.guidance_max_tokens,
            "temperature": 0.55,
            "response_format": {"type": "json_object"},
        }
        log.info("POST %s model=%s max_tokens=%s", _MISTRAL_API_URL, self.mistral_model, self.guidance_max_tokens)
        resp = _requests.post(_MISTRAL_API_URL, headers=headers, json=body, timeout=self.guidance_timeout)
        log.info("Mistral HTTP %s", resp.status_code)
        if not resp.ok:
            log.error("Mistral error body: %s", resp.text[:400])
        resp.raise_for_status()
        data = resp.json()
        try:
            text = data["choices"][0]["message"]["content"].strip()
        except (KeyError, IndexError) as exc:
            raise ValueError(f"Unexpected Mistral response shape: {exc}") from exc
        if not text:
            raise ValueError("Mistral response was empty.")
        log.info("Mistral response length: %d chars", len(text))
        return text

    def _mistral_ready(self) -> bool:
        return self.mistral_enabled and self.api_key_configured

    def _should_use_llm(self, triage: TriageResult, prediction: PredictionResult | None) -> bool:
        return not (prediction is None or triage.band == "uncertain_retake_needed")

    def _cache_key(self, payload: dict[str, object]) -> str:
        return json.dumps(payload, sort_keys=True, ensure_ascii=False)

    def _store_cached_result(self, cache_key: str, result: GuidanceResult) -> None:
        self._response_cache[cache_key] = result
        self._response_cache.move_to_end(cache_key)
        while len(self._response_cache) > self._response_cache_size:
            self._response_cache.popitem(last=False)

    def _summarize_error(self, exc: Exception) -> str:
        message = " ".join(str(exc).split())
        if "401" in message or "unauthorized" in message.lower():
            return "Mistral API key was rejected."
        if "429" in message or "rate limit" in message.lower():
            return "Mistral rate limit reached."
        return message[:220]

    def generate_smart_fallback(
        self,
        triage_band: str,
        predicted_hemoglobin: float | None,
        confidence: float | None,
        symptoms: SymptomInput,
        region: str | None = None,
    ) -> GuidanceResult:
        band = (triage_band or "").lower()
        hb = predicted_hemoglobin

        if band == "uncertain_retake_needed" or hb is None:
            explanation = (
                "Image signal was not strong enough for a confident prediction. "
                "This is not a clear result."
            )
            urgency = "Retake the scan in better lighting. If symptoms persist, see a doctor regardless of this result."
            next_steps = [
                "Retake eye image in bright natural light",
                "Pull lower eyelid gently and hold camera steady",
                "If you feel dizzy or very tired, visit a clinic anyway",
            ]
        elif band == "high_concern" or hb < 8.0:
            explanation = (
                "Severely low hemoglobin may mean the blood cannot carry enough oxygen well. "
                "Fatigue, dizziness, and breathlessness are expected at this level."
            )
            urgency = "Seek medical attention within 24 to 48 hours. Do not delay."
            next_steps = [
                "Visit nearest clinic or hospital today",
                "Request a full blood count (CBC) test",
                "Ask a doctor about iron or B12 treatment options",
                "Avoid strenuous physical activity until reviewed",
            ]
        elif band == "moderate_risk" or (hb is not None and 8.0 <= hb <= 10.9):
            explanation = (
                "Mild to moderate anemia-like signal detected. "
                "Hemoglobin appears below the healthy threshold, which may cause tiredness and reduced concentration."
            )
            urgency = "See a doctor within 1 to 2 weeks. Dietary changes can help."
            next_steps = [
                "Book a clinic visit this week",
                "Start an iron-rich diet immediately",
                "Take an iron supplement if recommended by a pharmacist or clinician",
                "Rescreen in 4 weeks after dietary changes",
            ]
        else:
            explanation = (
                "Conjunctival pallor signal is within the normal range for this screening. "
                "The hemoglobin estimate suggests adequate red blood cell levels."
            )
            urgency = "No immediate action is needed from this screening alone. Maintain a balanced diet."
            next_steps = [
                "Continue an iron-rich diet as prevention",
                "Rescreen in 3 months or if symptoms develop",
                "Stay hydrated and maintain regular sleep",
            ]

        if confidence is not None and confidence < 0.55:
            urgency = f"{urgency} Confidence is low, so formal testing matters more."

        food_advice = self._food_advice_for_region(region)
        next_steps = self._augment_next_steps(next_steps, symptoms)

        return GuidanceResult(
            source="fallback",
            model_used=None,
            provider_used=None,
            explanation=self._sanitize_text(explanation, limit=_FIELD_LIMITS["explanation"]),
            urgency_guidance=self._sanitize_text(urgency, limit=_FIELD_LIMITS["urgency_guidance"]),
            food_advice=self._sanitize_text(food_advice, limit=_FIELD_LIMITS["food_advice"]),
            next_steps=[self._sanitize_text(step, limit=120) for step in next_steps],
        )

    def _augment_next_steps(self, base_steps: list[str], symptoms: SymptomInput) -> list[str]:
        steps = list(base_steps)
        if symptoms.fatigue and symptoms.shortness_of_breath:
            steps.append("Avoid strenuous activity until reviewed by a doctor.")
        if symptoms.heavy_menstrual_bleeding:
            steps.append("Discuss menstrual blood loss with your doctor as a likely contributing factor.")
        deduped: list[str] = []
        seen: set[str] = set()
        for step in steps:
            if step not in seen:
                deduped.append(step)
                seen.add(step)
        return deduped

    def _food_advice_for_region(self, region: str | None) -> str:
        region_value = (region or "").strip().lower()
        if "india" in region_value:
            base = "Choose local iron-rich foods such as spinach (palak), lentils (dal), jaggery, moringa leaves, amla, and bajra roti."
        elif any(token in region_value for token in ("ghana", "nigeria", "kenya", "africa")):
            base = "Choose iron-rich foods such as ugwu leaves, beans, liver, garden eggs, and citrus fruits with meals."
        elif any(token in region_value for token in ("indonesia", "philippines", "vietnam", "thailand", "malaysia")):
            base = "Choose iron-rich foods such as kangkong, tempeh, tofu, moringa, fortified rice, and guava."
        else:
            base = "Choose iron-rich foods such as dark leafy greens, lentils, lean red meat, fortified cereals, and pumpkin seeds."
        return f"{base} Pair with vitamin C-rich foods, and avoid tea or coffee within 1 hour of iron-rich meals."

    def _parse_guidance_response(
        self,
        raw_text: str,
        source: Literal["mistral"],
        model_used: str,
        provider_used: str,
    ) -> GuidanceResult:
        text = raw_text.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text).strip()

        try:
            parsed = json.loads(text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", text, flags=re.DOTALL)
            if not match:
                raise
            try:
                parsed = json.loads(match.group(0))
            except json.JSONDecodeError:
                parsed = ast.literal_eval(match.group(0))

        if not isinstance(parsed, dict):
            raise ValueError("Guidance response must be a JSON object")

        next_steps = parsed.get("next_steps") or []
        if isinstance(next_steps, str):
            next_steps = [next_steps]

        explanation = self._sanitize_text(str(parsed.get("explanation", "")), limit=_FIELD_LIMITS["explanation"])
        urgency_guidance = self._sanitize_text(str(parsed.get("urgency_guidance", "")), limit=_FIELD_LIMITS["urgency_guidance"])
        food_advice = self._sanitize_text(str(parsed.get("food_advice", "")), limit=_FIELD_LIMITS["food_advice"])
        cleaned_steps = [
            self._sanitize_text(str(s), limit=120) for s in next_steps if str(s).strip()
        ][:4]

        if not cleaned_steps:
            raise ValueError("Guidance next_steps cannot be empty")

        combined = " ".join([explanation, urgency_guidance, food_advice, *cleaned_steps])
        if self._contains_unsafe_claim(combined):
            log.warning("Mistral output blocked by safety filter: %s", combined[:200])
            raise ValueError("Guidance output made an unsafe medical claim")

        return GuidanceResult(
            source=source,
            model_used=model_used,
            provider_used=provider_used,
            explanation=explanation,
            urgency_guidance=urgency_guidance,
            food_advice=food_advice,
            next_steps=cleaned_steps,
        )

    def _sanitize_text(self, text: str, *, limit: int) -> str:
        normalized = " ".join(text.split())
        if len(normalized) <= limit:
            return normalized
        return normalized[: limit - 3].rstrip(" ,.;:") + "..."

    def _contains_unsafe_claim(self, text: str) -> bool:
        scrubbed = text
        for pattern in _SAFE_DIAGNOSTIC_CONTEXT_PATTERNS:
            scrubbed = pattern.sub(" ", scrubbed)
        return bool(_UNSAFE_CLAIM_PATTERN.search(scrubbed))

    def runtime_status(self) -> GuidanceRuntimeStatus:
        provider_healthy = self._mistral_ready() and self._last_provider_error is None
        active_strategy: Literal["mistral", "fallback"] = "mistral" if provider_healthy else "fallback"
        return GuidanceRuntimeStatus(
            active_strategy=active_strategy,
            mistral_enabled=self.mistral_enabled,
            client_ready=self._mistral_ready(),
            api_key_configured=self.api_key_configured,
            mistral_model=self.mistral_model if self.mistral_enabled else None,
            provider="mistral" if self.mistral_enabled else None,
            fallback_reason=self._fallback_reason or (self._last_provider_error if not provider_healthy else None),
            last_provider_error=self._last_provider_error,
        )
