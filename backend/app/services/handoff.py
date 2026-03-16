from __future__ import annotations

from datetime import datetime

from app.config import SCREENING_DISCLAIMER
from app.schemas import GuidanceResult, HandoffSummary, PredictionResult, QualityAssessment, SymptomInput, TriageResult


class HandoffSummaryService:
    def build(
        self,
        quality: QualityAssessment,
        prediction: PredictionResult | None,
        triage: TriageResult,
        guidance: GuidanceResult,
        symptoms: SymptomInput,
        language: str | None = None,
        region: str | None = None,
    ) -> HandoffSummary:
        symptom_list = self._active_symptoms(symptoms)
        generated_at = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M")

        if prediction is None:
            headline = "Retake needed before screening interpretation"
            urgency_label = "Retake image"
            key_points = [
                "Image quality was not strong enough for a reliable screening interpretation.",
                self._quality_line(quality),
                f"Reported symptoms: {symptom_list}.",
            ]
        else:
            headline = f"{triage.label} screening summary"
            urgency_label = self._urgency_label(triage.band)
            key_points = [
                f"Screening band: {triage.label}.",
                prediction.screening_text,
                self._hemoglobin_line(prediction),
                self._confidence_line(prediction),
                f"Reported symptoms: {symptom_list}.",
            ]
            if region:
                key_points.append(f"Region context used for guidance: {region}.")
            if language:
                key_points.append(f"Preferred language requested: {language}.")

        next_steps = guidance.next_steps[:4]
        share_lines = [
            "AnemiaLens screening handoff",
            f"Generated: {generated_at}",
            f"Headline: {headline}",
            f"Urgency: {urgency_label}",
            *[f"- {point}" for point in key_points],
            "Recommended next steps:",
            *[f"{index}. {step}" for index, step in enumerate(next_steps, start=1)],
            f"Guidance note: {guidance.urgency_guidance}",
            f"Disclaimer: {SCREENING_DISCLAIMER}",
        ]

        return HandoffSummary(
            headline=headline,
            urgency_label=urgency_label,
            generated_at=generated_at,
            key_points=key_points,
            next_steps=next_steps,
            share_text="\n".join(share_lines),
        )

    def _active_symptoms(self, symptoms: SymptomInput) -> str:
        labels = []
        if symptoms.fatigue:
            labels.append("fatigue")
        if symptoms.dizziness:
            labels.append("dizziness")
        if symptoms.pale_skin:
            labels.append("pale skin")
        if symptoms.shortness_of_breath:
            labels.append("shortness of breath")
        if symptoms.heavy_menstrual_bleeding:
            labels.append("heavy menstrual bleeding")
        if symptoms.poor_diet_low_iron:
            labels.append("low iron intake")
        return ", ".join(labels) if labels else "none reported"

    def _quality_line(self, quality: QualityAssessment) -> str:
        if not quality.issues:
            return "No blocking quality issue was returned."
        primary_issue = quality.issues[0]
        return f"Main image issue: {primary_issue.title}. {primary_issue.message}"

    def _hemoglobin_line(self, prediction: PredictionResult) -> str:
        if prediction.predicted_hemoglobin is None:
            return "Estimated hemoglobin was withheld because model uncertainty was elevated."
        return f"Estimated hemoglobin: {prediction.predicted_hemoglobin:.1f} g/dL."

    def _confidence_line(self, prediction: PredictionResult) -> str:
        return (
            f"Model confidence: {round(prediction.confidence * 100)}% "
            f"with {prediction.reliability_flag} reliability."
        )

    def _urgency_label(self, band: str) -> str:
        if band == "high_concern":
            return "Medical review soon"
        if band == "moderate_risk":
            return "Clinic follow-up"
        if band == "low_risk":
            return "Routine monitoring"
        return "Retake image"
