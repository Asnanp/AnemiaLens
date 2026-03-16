from __future__ import annotations

from app.schemas import (
    CaseInsightPack,
    DecisionAudit,
    GuidanceResult,
    InsightDriver,
    PredictionResult,
    QualityAssessment,
    SymptomInput,
    TimelineStep,
    TriageResult,
)


_ISSUE_FIXES = {
    "blur_detected": "Hold the camera steady and tap to focus before capturing again.",
    "poor_lighting": "Move into bright, even natural light and avoid deep shadows.",
    "overexposed": "Avoid flash glare and lower the exposure so the inner eyelid keeps texture.",
    "low_contrast": "Use softer front light so the inner eyelid is visible without harsh shine.",
    "framing_off": "Move closer so one eye and the lower inner eyelid fill most of the frame.",
    "bad_framing": "Center the eye more tightly so the conjunctiva crop can be used directly.",
    "eye_not_visible": "Pull the lower eyelid down gently so the inner tissue is clearly visible.",
    "resolution_too_low": "Use the rear camera or step closer so the eye occupies more pixels.",
    "roi_cropped": "Keep the eyelid fully inside the frame so the ROI crop is complete.",
}

_DRIVER_STRENGTH = {"high": 3, "medium": 2, "watch": 1}
_DRIVER_IMPACT = {"up": 3, "limit": 2, "down": 1}


class CaseInsightService:
    def build(
        self,
        quality: QualityAssessment,
        prediction: PredictionResult | None,
        triage: TriageResult,
        decision_audit: DecisionAudit,
        guidance: GuidanceResult,
        symptoms: SymptomInput,
    ) -> CaseInsightPack:
        return CaseInsightPack(
            priority_window=self._priority_window(triage.band),
            priority_label=self._priority_label(triage.band),
            why_this_result=self._why_this_result(triage, prediction, decision_audit, symptoms),
            confidence_story=self._confidence_story(quality, prediction, decision_audit),
            risk_drivers=self._risk_drivers(quality, prediction, triage, decision_audit, symptoms),
            capture_improvements=self._capture_improvements(quality, decision_audit),
            follow_up_timeline=self._follow_up_timeline(triage, guidance, symptoms),
            judge_summary=self._judge_summary(triage, prediction, decision_audit, symptoms),
        )

    def _priority_window(self, band: str) -> str:
        if band == "high_concern":
            return "within_24_48_hours"
        if band == "moderate_risk":
            return "within_1_2_weeks"
        if band == "low_risk":
            return "routine_monitoring"
        return "retake_now"

    def _priority_label(self, band: str) -> str:
        if band == "high_concern":
            return "Act within 24-48 hours"
        if band == "moderate_risk":
            return "Plan follow-up within 1-2 weeks"
        if band == "low_risk":
            return "Routine monitoring"
        return "Retake before relying on this result"

    def _why_this_result(
        self,
        triage: TriageResult,
        prediction: PredictionResult | None,
        decision_audit: DecisionAudit,
        symptoms: SymptomInput,
    ) -> str:
        if prediction is None:
            return (
                "The image quality gate blocked model inference, so the safest output is a retake-first result "
                "rather than a weak screening claim."
            )

        symptom_count = symptoms.active_count
        symptom_text = (
            "no active symptoms were added"
            if symptom_count == 0
            else f"{symptom_count} symptom{'s' if symptom_count != 1 else ''} were fused into the triage score"
        )
        path_text = (
            "The result came from a direct conjunctiva ROI crop."
            if decision_audit.processing_path == "roi_crop"
            else "The standard crop was weak, so the backend used the stricter full-frame rescue path."
        )
        return (
            f"{triage.label} was assigned after combining the eye-image signal with symptom fusion; {symptom_text}. "
            f"{path_text}"
        )

    def _confidence_story(
        self,
        quality: QualityAssessment,
        prediction: PredictionResult | None,
        decision_audit: DecisionAudit,
    ) -> str:
        if prediction is None:
            return (
                "Confidence is intentionally withheld because the image did not meet the minimum safety gate."
            )
        if decision_audit.processing_path == "full_frame_rescue":
            return (
                "This result used the fallback full-frame rescue path, which keeps the case usable but is less ideal "
                "than a clean direct conjunctiva crop."
            )
        if prediction.reliability_flag == "high" and (decision_audit.threshold_margin or 0) >= 0.18:
            return (
                "This was a high-reliability direct ROI result with a clear margin away from the operating threshold."
            )
        if prediction.reliability_flag == "low" or prediction.uncertainty >= 0.5:
            return (
                "Uncertainty is elevated, so the result should be treated as screening-only and not stronger than the symptoms."
            )
        if decision_audit.calibration_band.startswith("borderline"):
            return (
                "The score is close to the operating threshold, so follow-up timing matters more than the exact percentage."
            )
        if quality.warning_issues:
            return (
                "The result is usable, but image warnings mean a cleaner retake would improve confidence."
            )
        return (
            "Confidence is moderate because the model signal was usable, but screening results still need symptom-aware follow-up."
        )

    def _risk_drivers(
        self,
        quality: QualityAssessment,
        prediction: PredictionResult | None,
        triage: TriageResult,
        decision_audit: DecisionAudit,
        symptoms: SymptomInput,
    ) -> list[InsightDriver]:
        drivers: list[InsightDriver] = []

        if prediction is None:
            drivers.append(
                InsightDriver(
                    title="Image quality gate",
                    impact="limit",
                    strength="high",
                    detail="The uploaded image blocked model inference because it was not reliable enough for safe screening.",
                )
            )
        else:
            hb = prediction.predicted_hemoglobin
            if hb is not None and hb < 8.0:
                drivers.append(
                    InsightDriver(
                        title="Very low hemoglobin estimate",
                        impact="up",
                        strength="high",
                        detail=f"The estimated hemoglobin of {hb:.1f} g/dL is far below the usual healthy range.",
                    )
                )
            elif hb is not None and hb < 11.0:
                drivers.append(
                    InsightDriver(
                        title="Below-range hemoglobin estimate",
                        impact="up",
                        strength="medium",
                        detail=f"The estimated hemoglobin of {hb:.1f} g/dL supports an anemia-like screening signal.",
                    )
                )
            elif hb is not None and hb >= 13.0:
                drivers.append(
                    InsightDriver(
                        title="Near-normal hemoglobin estimate",
                        impact="down",
                        strength="medium",
                        detail=f"The estimated hemoglobin of {hb:.1f} g/dL lowers concern in the final screening story.",
                    )
                )

            if prediction.anemia_risk >= 0.72:
                drivers.append(
                    InsightDriver(
                        title="Strong image signal",
                        impact="up",
                        strength="high",
                        detail="The conjunctiva image pattern pushed the model toward a confident anemia-like signal.",
                    )
                )
            elif prediction.anemia_risk >= 0.45:
                drivers.append(
                    InsightDriver(
                        title="Borderline image signal",
                        impact="up",
                        strength="medium",
                        detail="The image model detected some pallor-like signal, but not at the strongest tier.",
                    )
                )
            elif prediction.anemia_risk <= 0.24:
                drivers.append(
                    InsightDriver(
                        title="Low image-model risk",
                        impact="down",
                        strength="medium",
                        detail="The eye-image model did not detect a strong pallor signal in this scan.",
                    )
                )

            if symptoms.shortness_of_breath:
                drivers.append(
                    InsightDriver(
                        title="Shortness of breath reported",
                        impact="up",
                        strength="high",
                        detail="Breathlessness increases the urgency of follow-up even when screening is not diagnostic.",
                    )
                )
            if symptoms.fatigue:
                drivers.append(
                    InsightDriver(
                        title="Fatigue reported",
                        impact="up",
                        strength="medium",
                        detail="Fatigue raises symptom burden and makes low-hemoglobin screening results more actionable.",
                    )
                )
            if symptoms.heavy_menstrual_bleeding:
                drivers.append(
                    InsightDriver(
                        title="Heavy bleeding history",
                        impact="up",
                        strength="medium",
                        detail="Heavy menstrual blood loss is a common reason to take low-hemoglobin screening results seriously.",
                    )
                )
            if symptoms.poor_diet_low_iron:
                drivers.append(
                    InsightDriver(
                        title="Low iron intake",
                        impact="up",
                        strength="watch",
                        detail="Low iron intake adds practical context for diet and follow-up planning.",
                    )
                )
            if symptoms.active_count == 0 and triage.band == "low_risk":
                drivers.append(
                    InsightDriver(
                        title="No symptom burden added",
                        impact="down",
                        strength="watch",
                        detail="No extra symptom burden was added on top of the image-model result.",
                    )
                )

            if decision_audit.processing_path == "full_frame_rescue":
                drivers.append(
                    InsightDriver(
                        title="Full-frame rescue path",
                        impact="limit",
                        strength="medium",
                        detail="The ROI crop was not ideal, so the backend used the stricter full-frame rescue path instead.",
                    )
                )
            if decision_audit.calibration_band.startswith("borderline"):
                drivers.append(
                    InsightDriver(
                        title="Near-threshold result",
                        impact="limit",
                        strength="medium",
                        detail="The model score is close to the operating threshold, so small changes in image quality could shift the call.",
                    )
                )
            if prediction.reliability_flag == "low" or prediction.uncertainty >= 0.5:
                drivers.append(
                    InsightDriver(
                        title="Elevated uncertainty",
                        impact="limit",
                        strength="high",
                        detail="Uncertainty is high enough that retake quality and symptom follow-up matter more than the raw score.",
                    )
                )

        if quality.warning_issues:
            warning_names = ", ".join(issue.title.lower() for issue in quality.warning_issues[:2])
            drivers.append(
                InsightDriver(
                    title="Quality warnings present",
                    impact="limit",
                    strength="watch",
                    detail=f"The scan still passed, but warnings remained: {warning_names}.",
                )
            )

        ranked = sorted(
            drivers,
            key=lambda driver: (_DRIVER_IMPACT[driver.impact], _DRIVER_STRENGTH[driver.strength]),
            reverse=True,
        )
        return ranked[:4] or [
            InsightDriver(
                title="Screening pipeline complete",
                impact="limit",
                strength="watch",
                detail="The multilayer screening pipeline ran successfully, but no stronger single driver dominated the result.",
            )
        ]

    def _capture_improvements(
        self,
        quality: QualityAssessment,
        decision_audit: DecisionAudit,
    ) -> list[str]:
        fixes: list[str] = []
        seen: set[str] = set()

        for issue in quality.issues:
            fix = _ISSUE_FIXES.get(issue.code)
            if fix and fix not in seen:
                seen.add(fix)
                fixes.append(fix)

        if decision_audit.processing_path == "full_frame_rescue":
            rescue_fix = "Keep the lower eyelid centered so the direct conjunctiva crop is used instead of rescue mode."
            if rescue_fix not in seen:
                fixes.append(rescue_fix)

        if not fixes:
            fixes.append("Current image quality was usable; keep the same lighting and framing on the next scan.")

        return fixes[:4]

    def _follow_up_timeline(
        self,
        triage: TriageResult,
        guidance: GuidanceResult,
        symptoms: SymptomInput,
    ) -> list[TimelineStep]:
        if triage.band == "high_concern":
            timeline = [
                TimelineStep(window="Today", action="Reduce strenuous activity and use the clinician handoff now."),
                TimelineStep(window="24-48 hours", action="Seek medical review and request a full blood count (CBC) test."),
                TimelineStep(window="After review", action="Follow clinician advice on iron, B12, or other treatment causes."),
            ]
        elif triage.band == "moderate_risk":
            timeline = [
                TimelineStep(window="This week", action="Book a clinic visit and start a stronger iron-rich meal plan."),
                TimelineStep(window="Next 1-2 weeks", action="Arrange blood testing if symptoms continue or get worse."),
                TimelineStep(window="Around 4 weeks", action="Repeat the screening after diet or treatment changes."),
            ]
        elif triage.band == "low_risk":
            timeline = [
                TimelineStep(window="Now", action="Maintain a balanced diet and hydration routine."),
                TimelineStep(window="If symptoms appear", action="Do not wait for the next routine scan; arrange clinical review."),
                TimelineStep(window="Around 3 months", action="Repeat the screening or sooner if symptoms develop."),
            ]
        else:
            timeline = [
                TimelineStep(window="Now", action="Retake the image with better light before acting on this result."),
                TimelineStep(window="Next attempt", action="Expose the lower inner eyelid clearly and keep the camera steady."),
                TimelineStep(window="If symptoms persist", action="See a clinician even if the app still cannot produce a clean scan."),
            ]

        if symptoms.fatigue and symptoms.shortness_of_breath:
            timeline.insert(
                1,
                TimelineStep(
                    window="Until reviewed",
                    action="Avoid strenuous activity while fatigue and breathlessness are active.",
                ),
            )
        if symptoms.heavy_menstrual_bleeding:
            timeline.append(
                TimelineStep(
                    window="At follow-up",
                    action="Discuss menstrual blood loss as a possible contributor to low hemoglobin.",
                )
            )
        if guidance.next_steps:
            timeline[0] = TimelineStep(window=timeline[0].window, action=guidance.next_steps[0])
        return timeline[:4]

    def _judge_summary(
        self,
        triage: TriageResult,
        prediction: PredictionResult | None,
        decision_audit: DecisionAudit,
        symptoms: SymptomInput,
    ) -> str:
        if prediction is None:
            return "The safety gate stopped the pipeline before the model could over-claim on a weak image."
        if decision_audit.processing_path == "full_frame_rescue":
            return (
                f"The backend rescued a framing-limited case, kept the output transparent, and still surfaced a {triage.label.lower()} screening result."
            )
        if symptoms.active_count > 0:
            return (
                f"This run combined direct ROI inference, symptom fusion, and threshold auditing to produce a {triage.label.lower()} result."
            )
        return (
            f"This run produced a {triage.label.lower()} result from the direct conjunctiva crop with an explicit confidence story."
        )
