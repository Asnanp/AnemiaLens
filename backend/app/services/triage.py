from __future__ import annotations

from pathlib import Path

from app.config import SCREENING_DISCLAIMER
from app.ml.learned_fusion import LearnedFusionModel
from app.schemas import PredictionResult, QualityAssessment, SignalBreakdown, SymptomInput, TriageResult

_FUSION_MODEL_PATH = Path(__file__).parent.parent / "artifacts" / "fusion_model.pkl"


class TriageService:
    IMAGE_WEIGHT = 0.55
    SYMPTOM_WEIGHT = 0.45
    # Weights calibrated to clinical literature: pallor + dyspnoea are strongest
    _WEIGHTS = {
        "fatigue": 0.16,
        "dizziness": 0.15,
        "pale_skin": 0.26,
        "shortness_of_breath": 0.26,
        "heavy_menstrual_bleeding": 0.20,
        "poor_diet_low_iron": 0.12,
    }

    def __init__(self) -> None:
        self._fusion_model: LearnedFusionModel = self._load_fusion_model()

    def _load_fusion_model(self) -> LearnedFusionModel:
        try:
            if _FUSION_MODEL_PATH.exists():
                return LearnedFusionModel.load(_FUSION_MODEL_PATH)
        except Exception:
            pass
        return LearnedFusionModel()  # untrained → uses static 55/45 weights

    @property
    def fusion_model_active(self) -> bool:
        return self._fusion_model.trained

    def assess(
        self,
        quality: QualityAssessment,
        prediction: PredictionResult | None,
        symptoms: SymptomInput,
        signal_breakdown: SignalBreakdown | None = None,
    ) -> TriageResult:
        breakdown = signal_breakdown or self.build_signal_breakdown(quality, prediction, symptoms)
        symptom_score = breakdown.symptom_score

        if not quality.passed or prediction is None:
            issue_codes = {issue.code for issue in quality.issues}
            summary = (
                "The image does not clearly show one eye and the inner eyelid. Retake the photo with the lower eyelid visible before screening."
                if "eye_not_visible" in issue_codes
                else "The image quality is not strong enough for a reliable screening result. Retake the photo before acting on it."
            )
            return TriageResult(
                band="uncertain_retake_needed",
                score=round(breakdown.fused_score, 3),
                label="Uncertain, retake needed",
                summary=summary,
                disclaimer=SCREENING_DISCLAIMER,
            )

        fused_score = breakdown.fused_score
        predicted_hb = prediction.predicted_hemoglobin
        strong_hb_flag = predicted_hb is not None and predicted_hb <= 10.5
        moderate_hb_flag = predicted_hb is not None and predicted_hb <= 12.8

        # Symptom-driven escalation: severe symptoms alone can push to high concern
        if fused_score >= 0.52 or strong_hb_flag or (
            prediction.anemia_risk >= 0.62 and symptom_score >= 0.28
        ) or symptom_score >= 0.55:
            band = "high_concern"
            label = "High concern"
            summary = "This screening suggests a higher level of concern. Arrange formal medical review soon, especially if symptoms are increasing."
        elif (
            fused_score >= 0.28
            or (prediction.anemia_risk >= 0.52 and prediction.screening_label == "anemia_likely")
            or moderate_hb_flag
            or symptom_score >= 0.22
        ):
            band = "moderate_risk"
            label = "Moderate risk"
            summary = "This screening shows some concern. A routine check with a clinician or lab test would be reasonable."
        else:
            band = "low_risk"
            label = "Low risk"
            summary = "This screening does not show an urgent signal, but symptoms that continue or worsen still deserve follow-up."

        if prediction.uncertainty >= 0.80:
            band = "uncertain_retake_needed"
            label = "Uncertain, retake needed"
            summary = "The model uncertainty is high, so the safest next step is to retake the image and repeat the screening."

        return TriageResult(
            band=band,
            score=round(fused_score, 3),
            label=label,
            summary=summary,
            disclaimer=SCREENING_DISCLAIMER,
        )

    def build_signal_breakdown(
        self,
        quality: QualityAssessment,
        prediction: PredictionResult | None,
        symptoms: SymptomInput,
    ) -> SignalBreakdown:
        symptom_score = min(1.0, self._symptom_score(symptoms))
        if not quality.passed or prediction is None:
            return SignalBreakdown(
                image_risk=None,
                symptom_score=symptom_score,
                fused_score=max(0.2, symptom_score),
                image_weight=self.IMAGE_WEIGHT,
                symptom_weight=self.SYMPTOM_WEIGHT,
                symptom_burden=symptoms.symptom_burden,
                confidence=None,
                uncertainty=None,
                reliability_flag=None,
            )

        # Use learned fusion if trained, else fall back to static weights
        symptom_count = sum(
            1 for field in self._WEIGHTS if getattr(symptoms, field, False)
        )
        has_severe = bool(
            getattr(symptoms, "pale_skin", False)
            or getattr(symptoms, "shortness_of_breath", False)
        )

        fused_score = self._fusion_model.predict(
            image_risk=prediction.anemia_risk,
            uncertainty=prediction.uncertainty,
            symptom_score=symptom_score,
            symptom_count=symptom_count,
            has_severe_symptoms=has_severe,
        )

        # Symptom escalation: if symptom burden is high, floor the fused score
        # This ensures all-symptoms case always reaches high concern
        if symptom_score >= 0.55:
            fused_score = max(fused_score, 0.55)
        elif symptom_score >= 0.35:
            fused_score = max(fused_score, 0.30)

        # Effective weights for display (approximate from fusion output)
        if self._fusion_model.trained:
            # Derive display weights from perturbation
            base = fused_score
            img_perturbed = self._fusion_model.predict(
                min(1.0, prediction.anemia_risk + 0.1),
                prediction.uncertainty, symptom_score, symptom_count, has_severe,
            )
            sym_perturbed = self._fusion_model.predict(
                prediction.anemia_risk, prediction.uncertainty,
                min(1.0, symptom_score + 0.1), symptom_count, has_severe,
            )
            img_sens = abs(img_perturbed - base)
            sym_sens = abs(sym_perturbed - base)
            total_sens = img_sens + sym_sens + 1e-9
            display_img_w = round(img_sens / total_sens, 2)
            display_sym_w = round(sym_sens / total_sens, 2)
        else:
            display_img_w = self.IMAGE_WEIGHT
            display_sym_w = self.SYMPTOM_WEIGHT

        return SignalBreakdown(
            image_risk=prediction.anemia_risk,
            symptom_score=symptom_score,
            fused_score=min(1.0, fused_score),
            image_weight=display_img_w,
            symptom_weight=display_sym_w,
            symptom_burden=symptoms.symptom_burden,
            confidence=prediction.confidence,
            uncertainty=prediction.uncertainty,
            reliability_flag=prediction.reliability_flag,
        )

    def _symptom_score(self, symptoms: SymptomInput) -> float:
        raw_score = 0.0
        severity_map = symptoms.symptom_severity or {}
        for field_name, weight in self._WEIGHTS.items():
            value = getattr(symptoms, field_name)
            if value:
                # Severity multiplier: none=1.0, mild=1.0, severe=1.5
                sev = severity_map.get(field_name, 1)
                multiplier = 1.5 if sev >= 2 else 1.0
                raw_score += weight * multiplier
        return min(1.0, raw_score)
