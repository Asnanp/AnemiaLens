from __future__ import annotations

from app.config import SCREENING_DISCLAIMER
from app.schemas import (
    CaseInsightPack,
    ClinicalBrief,
    DecisionAudit,
    GuidanceResult,
    HandoffSummary,
    PredictionResult,
    QualityAssessment,
    SignalBreakdown,
    SymptomInput,
    TriageResult,
)


class ClinicalBriefService:
    def build(
        self,
        quality: QualityAssessment,
        prediction: PredictionResult | None,
        triage: TriageResult,
        decision_audit: DecisionAudit,
        guidance: GuidanceResult,
        symptoms: SymptomInput,
        insight_pack: CaseInsightPack,
        handoff_summary: HandoffSummary,
        signal_breakdown: SignalBreakdown,
    ) -> ClinicalBrief:
        supporting_evidence = self._supporting_evidence(
            quality,
            prediction,
            decision_audit,
            symptoms,
            insight_pack,
        )
        limiting_factors = self._limiting_factors(
            quality,
            prediction,
            decision_audit,
            insight_pack,
        )
        safety_checks = self._safety_checks(
            prediction,
            decision_audit,
            guidance,
            symptoms,
        )
        recommended_actions = guidance.next_steps[:4]

        return ClinicalBrief(
            headline=handoff_summary.headline,
            verdict=self._verdict(triage, prediction, symptoms, insight_pack),
            action_window=insight_pack.priority_window,
            action_label=insight_pack.priority_label,
            signal_breakdown=signal_breakdown,
            supporting_evidence=supporting_evidence,
            limiting_factors=limiting_factors,
            safety_checks=safety_checks,
            recommended_actions=recommended_actions,
            share_text=self._share_text(
                handoff_summary,
                triage,
                signal_breakdown,
                supporting_evidence,
                limiting_factors,
                recommended_actions,
            ),
        )

    def _verdict(
        self,
        triage: TriageResult,
        prediction: PredictionResult | None,
        symptoms: SymptomInput,
        insight_pack: CaseInsightPack,
    ) -> str:
        if prediction is None:
            symptom_context = (
                "No symptoms were added."
                if symptoms.active_count == 0
                else f"{symptoms.active_count} reported symptom{'s were' if symptoms.active_count != 1 else ' was'} preserved for follow-up context."
            )
            return (
                "The image quality gate blocked model inference, so the safest outcome is a retake-first screening result. "
                f"{symptom_context} {insight_pack.confidence_story}"
            )
        return f"{triage.summary} {insight_pack.confidence_story}"

    def _supporting_evidence(
        self,
        quality: QualityAssessment,
        prediction: PredictionResult | None,
        decision_audit: DecisionAudit,
        symptoms: SymptomInput,
        insight_pack: CaseInsightPack,
    ) -> list[str]:
        evidence: list[str] = []

        if prediction is None:
            self._append_unique(
                evidence,
                "The image quality gate blocked model inference before a screening result was produced.",
            )
        else:
            self._append_unique(
                evidence,
                f"Model anemia-like risk signal: {round(prediction.anemia_risk * 100)}% with {prediction.reliability_flag} reliability.",
            )
            if prediction.predicted_hemoglobin is not None:
                self._append_unique(
                    evidence,
                    f"Estimated hemoglobin signal: {prediction.predicted_hemoglobin:.1f} g/dL.",
                )
            else:
                self._append_unique(
                    evidence,
                    "Estimated hemoglobin was withheld because uncertainty was too high for a stable number.",
                )
            self._append_unique(
                evidence,
                "Direct conjunctiva ROI processing was used."
                if decision_audit.processing_path == "roi_crop"
                else "Fallback full-frame rescue processing was used after the ROI crop looked weak.",
            )

        if symptoms.active_count == 0:
            self._append_unique(evidence, "No active symptoms were added in the questionnaire.")
        else:
            self._append_unique(
                evidence,
                f"Active symptoms fused into triage: {self._symptom_list(symptoms)}.",
            )

        for driver in insight_pack.risk_drivers:
            if driver.impact != "limit":
                self._append_unique(evidence, driver.detail)

        if quality.warning_issues:
            warning_titles = ", ".join(issue.title.lower() for issue in quality.warning_issues[:2])
            self._append_unique(
                evidence,
                f"Non-blocking quality warnings were tracked during analysis: {warning_titles}.",
            )

        return evidence[:4]

    def _limiting_factors(
        self,
        quality: QualityAssessment,
        prediction: PredictionResult | None,
        decision_audit: DecisionAudit,
        insight_pack: CaseInsightPack,
    ) -> list[str]:
        limits: list[str] = []

        if prediction is None and quality.issues:
            self._append_unique(
                limits,
                f"Primary blocker: {quality.issues[0].title}. {quality.issues[0].message}",
            )
        if decision_audit.processing_path == "full_frame_rescue":
            self._append_unique(
                limits,
                "The backend used the fallback full-frame rescue path, which is less ideal than a clean direct ROI crop.",
            )
        if prediction is not None and (prediction.reliability_flag == "low" or prediction.uncertainty >= 0.5):
            self._append_unique(
                limits,
                "Model uncertainty is elevated, so follow-up timing matters more than the exact risk number.",
            )
        if decision_audit.calibration_band.startswith("borderline"):
            self._append_unique(
                limits,
                "The score sits close to the operating threshold, so a cleaner retake could shift the screening call.",
            )
        if prediction is not None and prediction.predicted_hemoglobin is None:
            self._append_unique(
                limits,
                "The hemoglobin estimate was hidden because the backend did not consider the number stable enough to show.",
            )
        for driver in insight_pack.risk_drivers:
            if driver.impact == "limit":
                self._append_unique(limits, driver.detail)
        if quality.warning_issues:
            warning_titles = ", ".join(issue.title.lower() for issue in quality.warning_issues[:2])
            self._append_unique(
                limits,
                f"Image warnings remained even though the scan passed: {warning_titles}.",
            )

        if not limits:
            limits.append(
                "No major blocker was triggered, but the result still remains screening-only and should be confirmed clinically if symptoms persist."
            )

        return limits[:4]

    def _safety_checks(
        self,
        prediction: PredictionResult | None,
        decision_audit: DecisionAudit,
        guidance: GuidanceResult,
        symptoms: SymptomInput,
    ) -> list[str]:
        checks = [
            "Image quality gating ran before any screening interpretation.",
            "Questionnaire symptoms were fused into triage instead of relying on image alone.",
            "Non-diagnostic disclaimer remained attached to the result and handoff text.",
        ]

        if prediction is not None:
            checks.insert(1, "Uncertainty, confidence, and reliability were attached to the model output.")
        if decision_audit.processing_path == "full_frame_rescue":
            checks.append("The fallback rescue path was labeled transparently in the audit trail.")
        if decision_audit.review_flags:
            checks.append("Structured review flags were generated for follow-up and UI display.")
        if guidance.source == "mistral":
            checks.append(
                "Mistral guidance was constrained to the screening result, uncertainty, symptoms, and locale context."
            )
        else:
            checks.append("Rule-based fallback guidance stayed grounded to the current result and symptoms.")
        if symptoms.active_count == 0:
            checks.append("The system preserved an explicit no-symptoms state rather than assuming missing data.")

        return checks[:5]

    def _share_text(
        self,
        handoff_summary: HandoffSummary,
        triage: TriageResult,
        signal_breakdown: SignalBreakdown,
        supporting_evidence: list[str],
        limiting_factors: list[str],
        recommended_actions: list[str],
    ) -> str:
        image_signal = (
            "not available"
            if signal_breakdown.image_risk is None
            else f"{round(signal_breakdown.image_risk * 100)}%"
        )
        lines = [
            "AnemiaLens clinical brief",
            f"Headline: {handoff_summary.headline}",
            f"Urgency: {handoff_summary.urgency_label}",
            f"Triage band: {triage.label}",
            (
                "Signal breakdown: "
                f"image={image_signal}, "
                f"symptoms={round(signal_breakdown.symptom_score * 100)}%, "
                f"fused={round(signal_breakdown.fused_score * 100)}%"
            ),
            "Supporting evidence:",
            *[f"- {item}" for item in supporting_evidence],
            "Limiting factors:",
            *[f"- {item}" for item in limiting_factors],
            "Recommended actions:",
            *[f"{index}. {item}" for index, item in enumerate(recommended_actions, start=1)],
            f"Disclaimer: {SCREENING_DISCLAIMER}",
        ]
        return "\n".join(lines)

    def _symptom_list(self, symptoms: SymptomInput) -> str:
        labels: list[str] = []
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
        return ", ".join(labels)

    def _append_unique(self, bucket: list[str], item: str) -> None:
        if item not in bucket:
            bucket.append(item)
