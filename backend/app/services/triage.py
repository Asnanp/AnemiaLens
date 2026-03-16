from __future__ import annotations

from app.config import SCREENING_DISCLAIMER
from app.schemas import PredictionResult, QualityAssessment, SignalBreakdown, SymptomInput, TriageResult


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

        # Symptom-driven escalation: severe symptoms alone can push to high concern
        if fused_score >= 0.58 or (
            prediction.anemia_risk >= 0.52 and symptom_score >= 0.32
        ) or symptom_score >= 0.68:
            band = "high_concern"
            label = "High concern"
            summary = "This screening suggests a higher level of concern. Arrange formal medical review soon, especially if symptoms are increasing."
        elif fused_score >= 0.28 or prediction.anemia_risk >= 0.42 or symptom_score >= 0.26:
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

        return SignalBreakdown(
            image_risk=prediction.anemia_risk,
            symptom_score=symptom_score,
            fused_score=min(
                1.0,
                prediction.anemia_risk * self.IMAGE_WEIGHT + symptom_score * self.SYMPTOM_WEIGHT,
            ),
            image_weight=self.IMAGE_WEIGHT,
            symptom_weight=self.SYMPTOM_WEIGHT,
            symptom_burden=symptoms.symptom_burden,
            confidence=prediction.confidence,
            uncertainty=prediction.uncertainty,
            reliability_flag=prediction.reliability_flag,
        )

    def _symptom_score(self, symptoms: SymptomInput) -> float:
        raw_score = 0.0
        for field_name, weight in self._WEIGHTS.items():
            value = getattr(symptoms, field_name)
            if value:
                raw_score += weight
        return min(1.0, raw_score)
