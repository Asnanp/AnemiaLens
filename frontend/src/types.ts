export type SymptomInput = {
  fatigue: boolean;
  dizziness: boolean;
  pale_skin: boolean;
  shortness_of_breath: boolean;
  heavy_menstrual_bleeding: boolean | null;
  poor_diet_low_iron: boolean;
};

export type PatientProfileInput = {
  age: number | null;
  sex: 'female' | 'male' | 'other' | 'not_specified';
  diet_type: 'omnivore' | 'vegetarian' | 'vegan' | 'mixed' | 'not_specified';
};

export type PatientProfile = PatientProfileInput & {
  patient_id: string;
  reported_symptoms: string[];
  summary: string;
};

export type QualityIssue = {
  code: string;
  severity: 'warning' | 'blocking';
  title: string;
  message: string;
};

export type QualityAssessment = {
  passed: boolean;
  blur_score: number;
  brightness_score: number;
  contrast_score: number;
  framing_score: number;
  lighting_score: number;
  lighting_condition: string;
  lighting_summary: string;
  glare_risk: number;
  shadow_risk: number;
  issues: QualityIssue[];
};

export type PredictionResult = {
  anemia_risk: number;
  predicted_hemoglobin: number | null;
  confidence: number;
  uncertainty: number;
  reliability_flag: 'low' | 'medium' | 'high';
  screening_label: 'anemia_likely' | 'anemia_unlikely' | 'uncertain';
  screening_text: string;
  model_source: string;
  confidence_breakdown?: {
    capture_quality: number;
    model_stability: number;
    threshold_stability: number;
    guardrail_applied: boolean;
    lighting_condition: string;
    glare_risk: number;
    shadow_risk: number;
    summary: string;
  } | null;
};

export type DecisionAudit = {
  processing_path: 'roi_crop' | 'full_frame_rescue' | 'quality_blocked';
  calibration_band:
    | 'quality_blocked'
    | 'strong_positive'
    | 'borderline_positive'
    | 'strong_negative'
    | 'borderline_negative'
    | 'uncertain';
  decision_threshold: number | null;
  threshold_margin: number | null;
  quality_warning_codes: string[];
  review_flags: string[];
  summary: string;
};

export type TriageResult = {
  band: 'low_risk' | 'moderate_risk' | 'high_concern' | 'uncertain_retake_needed';
  score: number;
  label: string;
  summary: string;
  disclaimer: string;
};

export type GuidanceResult = {
  source: 'mistral' | 'fallback';
  model_used?: string | null;
  provider_used?: string | null;
  explanation: string;
  urgency_guidance: string;
  food_advice: string;
  next_steps: string[];
};

export type HandoffSummary = {
  headline: string;
  urgency_label: string;
  generated_at: string;
  key_points: string[];
  next_steps: string[];
  share_text: string;
};

export type InsightDriver = {
  title: string;
  impact: 'up' | 'down' | 'limit';
  strength: 'high' | 'medium' | 'watch';
  detail: string;
};

export type TimelineStep = {
  window: string;
  action: string;
};

export type CaseInsightPack = {
  priority_window:
    | 'retake_now'
    | 'within_24_48_hours'
    | 'within_1_2_weeks'
    | 'routine_monitoring';
  priority_label: string;
  why_this_result: string;
  confidence_story: string;
  risk_drivers: InsightDriver[];
  capture_improvements: string[];
  follow_up_timeline: TimelineStep[];
  judge_summary: string;
};

export type SignalBreakdown = {
  image_risk: number | null;
  symptom_score: number;
  fused_score: number;
  image_weight: number;
  symptom_weight: number;
  symptom_burden: 'none' | 'mild' | 'moderate' | 'severe';
  confidence: number | null;
  uncertainty: number | null;
  reliability_flag: PredictionResult['reliability_flag'] | null;
};

export type ClinicalBrief = {
  headline: string;
  verdict: string;
  action_window:
    | 'retake_now'
    | 'within_24_48_hours'
    | 'within_1_2_weeks'
    | 'routine_monitoring';
  action_label: string;
  signal_breakdown: SignalBreakdown;
  supporting_evidence: string[];
  limiting_factors: string[];
  safety_checks: string[];
  recommended_actions: string[];
  share_text: string;
};

export type WorkflowStage = {
  key: 'image_quality_agent' | 'screening_agent' | 'triage_agent' | 'guidance_agent';
  agent_label: string;
  title: string;
  status: 'passed' | 'warning' | 'blocked' | 'complete';
  summary: string;
};

export type StructuredCaseRecord = {
  case_id: string;
  patient_id: string;
  age: number | null;
  sex: PatientProfile['sex'];
  diet_type: PatientProfile['diet_type'];
  symptoms: string[];
  image_quality: {
    status: 'acceptable' | 'warning' | 'blocked';
    lighting_condition: string;
    lighting_score: number;
    blur_detected: boolean;
    eye_region_visible: boolean;
    primary_issue: string | null;
    warnings: string[];
  };
  screening_result: {
    risk_level: TriageResult['band'];
    confidence: number | null;
    reliability: PredictionResult['reliability_flag'] | null;
    predicted_hemoglobin: number | null;
    anemia_risk: number | null;
  };
  recommendation: string;
  case_summary: string;
};

export type AnalysisMeta = {
  request_id: string;
  generated_at: string;
  api_version: string;
  processing_time_ms: number;
  quality_gate_passed: boolean;
  processing_path: DecisionAudit['processing_path'];
  guidance_source: GuidanceResult['source'];
  used_raw_frame_rescue: boolean;
  safety_layers: string[];
};

export type RecentScreening = {
  id: string;
  saved_at: string;
  triage_label: string;
  triage_band: TriageResult['band'];
  urgency_label: string;
  predicted_hemoglobin: number | null;
  anemia_risk: number;
  confidence: number;
  symptoms: string[];
  share_text: string;
};

export type GuidanceRuntimeStatus = {
  active_strategy: 'mistral' | 'fallback';
  mistral_enabled: boolean;
  client_ready: boolean;
  api_key_configured: boolean;
  mistral_model?: string | null;
  provider?: string | null;
  fallback_reason?: string | null;
  last_provider_error?: string | null;
};

export type ModelRuntimeStatus = {
  primary_model: string;
  deep_stack_loaded: boolean;
  legacy_loaded: boolean;
  artifact_ready?: boolean;
  artifact_path?: string | null;
  load_error?: string | null;
  record_count?: number | null;
  validation_accuracy?: number | null;
  validation_f1?: number | null;
  split_strategy?: string | null;
  deployed_scope?: string | null;
  deployed_validation_size?: number | null;
  deployed_accuracy?: number | null;
  deployed_precision?: number | null;
  deployed_recall?: number | null;
  deployed_f1?: number | null;
  deployed_blocked_total?: number | null;
  deployed_likely_count?: number | null;
  deployed_uncertain_count?: number | null;
};

export type RuntimeStatusResponse = {
  api_status: 'ok';
  guidance: GuidanceRuntimeStatus;
  model: ModelRuntimeStatus;
};

export type AnalyzeResponse = {
  blocked: boolean;
  quality: QualityAssessment;
  prediction: PredictionResult | null;
  decision_audit: DecisionAudit;
  triage: TriageResult;
  guidance: GuidanceResult;
  insight_pack: CaseInsightPack;
  clinical_brief: ClinicalBrief;
  handoff_summary: HandoffSummary;
  analysis_meta: AnalysisMeta;
  patient_profile: PatientProfile;
  workflow_stages: WorkflowStage[];
  structured_case: StructuredCaseRecord;
  symptoms: SymptomInput;
  language?: string | null;
  region?: string | null;
};
