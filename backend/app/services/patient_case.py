from __future__ import annotations

from app.schemas import (
    GuidanceResult,
    PatientProfile,
    PatientProfileInput,
    PredictionResult,
    QualityAssessment,
    StructuredCaseImageQuality,
    StructuredCaseRecord,
    StructuredCaseScreeningResult,
    SymptomInput,
    TriageResult,
    WorkflowStage,
)

_SYMPTOM_LABELS = {
    "fatigue": "Fatigue",
    "dizziness": "Dizziness",
    "pale_skin": "Pale skin",
    "shortness_of_breath": "Shortness of breath",
    "heavy_menstrual_bleeding": "Heavy menstrual bleeding",
    "poor_diet_low_iron": "Low iron intake",
}


class PatientCaseService:
    def build_profile(
        self,
        request_id: str,
        patient_input: PatientProfileInput,
        symptoms: SymptomInput,
    ) -> PatientProfile:
        patient_id = f"ANM-{request_id.upper()[-6:]}"
        reported_symptoms = self._active_symptoms(symptoms)
        descriptor = self._patient_descriptor(patient_input)
        symptom_line = (
            f"Reported symptoms: {self._join_human(reported_symptoms)}."
            if reported_symptoms
            else "No symptoms were reported in intake."
        )
        summary = f"{descriptor} {symptom_line}".strip()

        return PatientProfile(
            patient_id=patient_id,
            age=patient_input.age,
            sex=patient_input.sex,
            diet_type=patient_input.diet_type,
            reported_symptoms=reported_symptoms,
            summary=summary,
        )

    def build_workflow_stages(
        self,
        quality: QualityAssessment,
        prediction: PredictionResult | None,
        triage: TriageResult,
        guidance: GuidanceResult,
        symptoms: SymptomInput,
    ) -> list[WorkflowStage]:
        return [
            WorkflowStage(
                key="image_quality_agent",
                agent_label="Image Quality Agent",
                title="Capture validation",
                status=self._quality_status(quality),
                summary=self._quality_summary(quality),
            ),
            WorkflowStage(
                key="screening_agent",
                agent_label="Screening Agent",
                title="Conjunctiva screening",
                status=self._screening_status(quality, prediction),
                summary=self._screening_summary(quality, prediction),
            ),
            WorkflowStage(
                key="triage_agent",
                agent_label="Triage Agent",
                title="Symptom + image fusion",
                status="complete",
                summary=self._triage_summary(triage, symptoms),
            ),
            WorkflowStage(
                key="guidance_agent",
                agent_label="Guidance Agent",
                title="Next-step guidance",
                status="complete",
                summary=self._guidance_summary(guidance),
            ),
        ]

    def build_structured_case(
        self,
        request_id: str,
        patient_profile: PatientProfile,
        quality: QualityAssessment,
        prediction: PredictionResult | None,
        triage: TriageResult,
        guidance: GuidanceResult,
        symptoms: SymptomInput,
    ) -> StructuredCaseRecord:
        active_symptoms = self._active_symptoms(symptoms)
        primary_issue = quality.issues[0].title if quality.issues else None
        warnings = [issue.title for issue in quality.warning_issues]
        recommendation = guidance.next_steps[0] if guidance.next_steps else guidance.urgency_guidance

        return StructuredCaseRecord(
            case_id=f"CASE-{request_id.upper()[-6:]}",
            patient_id=patient_profile.patient_id,
            age=patient_profile.age,
            sex=patient_profile.sex,
            diet_type=patient_profile.diet_type,
            symptoms=active_symptoms,
            image_quality=StructuredCaseImageQuality(
                status=self._structured_quality_status(quality),
                lighting_condition=quality.lighting_condition,
                lighting_score=quality.lighting_score,
                blur_detected=any(issue.code == "blur_detected" for issue in quality.issues),
                eye_region_visible=not any(issue.code == "eye_not_visible" for issue in quality.issues),
                primary_issue=primary_issue,
                warnings=warnings,
            ),
            screening_result=StructuredCaseScreeningResult(
                risk_level=triage.band,
                confidence=prediction.confidence if prediction else None,
                reliability=prediction.reliability_flag if prediction else None,
                predicted_hemoglobin=prediction.predicted_hemoglobin if prediction else None,
                anemia_risk=prediction.anemia_risk if prediction else None,
            ),
            recommendation=recommendation,
            case_summary=self._case_summary(triage, active_symptoms, prediction),
        )

    def _active_symptoms(self, symptoms: SymptomInput) -> list[str]:
        return [
            label
            for field, label in _SYMPTOM_LABELS.items()
            if getattr(symptoms, field) is True
        ]

    def _patient_descriptor(self, patient_input: PatientProfileInput) -> str:
        parts: list[str] = []
        if patient_input.age is not None:
            parts.append(f"{patient_input.age}-year-old")
        if patient_input.sex != "not_specified":
            parts.append(patient_input.sex.replace("_", " "))
        descriptor = " ".join(parts).strip()

        diet = (
            f"{patient_input.diet_type.replace('_', ' ')} diet"
            if patient_input.diet_type != "not_specified"
            else None
        )

        if descriptor and diet:
            return f"{descriptor.capitalize()} on a {diet}."
        if descriptor:
            return f"{descriptor.capitalize()}."
        if diet:
            return f"Intake recorded with a {diet}."
        return "Basic intake context captured."

    def _join_human(self, items: list[str]) -> str:
        if not items:
            return "none"
        if len(items) == 1:
            return items[0]
        if len(items) == 2:
            return f"{items[0]} and {items[1]}"
        return f"{', '.join(items[:-1])}, and {items[-1]}"

    def _quality_status(self, quality: QualityAssessment) -> str:
        if not quality.passed:
            return "blocked"
        if quality.warning_issues:
            return "warning"
        return "passed"

    def _quality_summary(self, quality: QualityAssessment) -> str:
        if not quality.passed:
            issue = quality.issues[0] if quality.issues else None
            if issue is None:
                return "The capture failed the safety gate and needs a retake before screening can continue."
            return f"{issue.title} blocked the capture, so the workflow stayed retake-first."
        if quality.warning_issues:
            warnings = ", ".join(issue.title.lower() for issue in quality.warning_issues[:2])
            return (
                f"The image passed with {quality.lighting_condition.replace('_', ' ')} lighting, "
                f"but warnings remained: {warnings}."
            )
        return (
            f"The image passed the safety gate with {quality.lighting_condition.replace('_', ' ')} lighting "
            "and a usable conjunctiva view."
        )

    def _screening_status(self, quality: QualityAssessment, prediction: PredictionResult | None) -> str:
        if not quality.passed or prediction is None:
            return "blocked"
        if prediction.reliability_flag == "low":
            return "warning"
        return "passed"

    def _screening_summary(self, quality: QualityAssessment, prediction: PredictionResult | None) -> str:
        if not quality.passed or prediction is None:
            return "Screening inference was skipped because the image quality gate did not allow a safe prediction."
        hb_text = (
            "hemoglobin estimate withheld"
            if prediction.predicted_hemoglobin is None
            else f"estimated hemoglobin {prediction.predicted_hemoglobin:.1f} g/dL"
        )
        return (
            f"The screening model produced a {round(prediction.anemia_risk * 100)}% anemia-like signal, "
            f"{hb_text}, and {round(prediction.confidence * 100)}% confidence."
        )

    def _triage_summary(self, triage: TriageResult, symptoms: SymptomInput) -> str:
        symptom_count = symptoms.active_count
        symptom_text = (
            "no active symptoms"
            if symptom_count == 0
            else f"{symptom_count} symptom{'s' if symptom_count != 1 else ''}"
        )
        return (
            f"The triage layer combined the image signal with {symptom_text} and assigned {triage.label.lower()}."
        )

    def _guidance_summary(self, guidance: GuidanceResult) -> str:
        first_step = guidance.next_steps[0] if guidance.next_steps else guidance.urgency_guidance
        source_label = "Mistral guidance" if guidance.source == "mistral" else "Rule-based guidance"
        return f"{source_label} translated the case into a next step: {first_step}"

    def _structured_quality_status(self, quality: QualityAssessment) -> str:
        if not quality.passed:
            return "blocked"
        if quality.warning_issues:
            return "warning"
        return "acceptable"

    def _case_summary(
        self,
        triage: TriageResult,
        active_symptoms: list[str],
        prediction: PredictionResult | None,
    ) -> str:
        if prediction is None:
            return "Case requires repeat image capture because the quality gate blocked a safe screening interpretation."
        symptom_context = (
            "with no additional symptom burden"
            if not active_symptoms
            else f"with reported symptoms including {self._join_human(active_symptoms)}"
        )
        return (
            f"Patient shows {triage.label.lower()} based on the conjunctiva image signal {symptom_context}."
        )
