import { useState, useEffect } from 'react';
import { analyzeScreening, checkBackendHealth, checkImageQuality, getRuntimeStatus } from '../api';
import type { AnalyzeResponse, QualityAssessment, RecentScreening, RuntimeStatusResponse, SymptomInput, TriageResult } from '../types';

const defaultSymptoms: SymptomInput = {
  fatigue: false,
  dizziness: false,
  pale_skin: false,
  shortness_of_breath: false,
  heavy_menstrual_bleeding: null,
  poor_diet_low_iron: false
};

const RECENT_KEY = 'anemialens.recent-screenings';

const symptomLabels: Record<keyof SymptomInput, string> = {
  fatigue: 'Fatigue',
  dizziness: 'Dizziness',
  pale_skin: 'Pale skin',
  shortness_of_breath: 'Shortness of breath',
  heavy_menstrual_bleeding: 'Heavy menstrual bleeding',
  poor_diet_low_iron: 'Low iron intake'
};

function activeSymptoms(input: SymptomInput) {
  return Object.entries(input)
    .filter(([, value]) => value === true)
    .map(([key]) => symptomLabels[key as keyof SymptomInput]);
}

function loadRecent(): RecentScreening[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem(RECENT_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveRecent(items: RecentScreening[]) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem(RECENT_KEY, JSON.stringify(items));
  } catch {
    /* ignore */
  }
}

function buildRecent(analysis: AnalyzeResponse): RecentScreening | null {
  if (!analysis.prediction) return null;
  return {
    id: `${analysis.handoff_summary.generated_at}-${analysis.triage.band}`,
    saved_at: analysis.handoff_summary.generated_at,
    triage_label: analysis.triage.label,
    triage_band: analysis.triage.band,
    urgency_label: analysis.handoff_summary.urgency_label,
    predicted_hemoglobin: analysis.prediction.predicted_hemoglobin,
    anemia_risk: analysis.prediction.anemia_risk,
    confidence: analysis.prediction.confidence,
    symptoms: activeSymptoms(analysis.symptoms),
    share_text: analysis.handoff_summary.share_text
  };
}

export function useScreening() {
  const [step, setStep] = useState(0);
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [symptoms, setSymptoms] = useState<SymptomInput>(defaultSymptoms);
  const [quality, setQuality] = useState<QualityAssessment | null>(null);
  const [analysis, setAnalysis] = useState<AnalyzeResponse | null>(null);
  const [runtime, setRuntime] = useState<RuntimeStatusResponse | null>(null);
  const [recent, setRecent] = useState<RecentScreening[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backendUp, setBackendUp] = useState(false);
  const [isOfflineMode, setIsOfflineMode] = useState(false);

  useEffect(() => {
    setRecent(loadRecent());
    checkBackendHealth().then(setBackendUp);
    getRuntimeStatus().then(setRuntime).catch(() => null);
  }, []);

  useEffect(() => () => {
    if (previewUrl?.startsWith('blob:')) URL.revokeObjectURL(previewUrl);
  }, [previewUrl]);

  const setPreview = (value: string | null) => setPreviewUrl(prev => {
    if (prev?.startsWith('blob:')) URL.revokeObjectURL(prev);
    return value;
  });

  const pickFile = (nextFile: File) => {
    setFile(nextFile);
    setPreview(URL.createObjectURL(nextFile));
    setQuality(null);
    setAnalysis(null);
    setError(null);
    setStep(0);
  };

  const toggleSymptom = (key: keyof SymptomInput) => setSymptoms(prev => 
    key === 'heavy_menstrual_bleeding'
      ? { ...prev, heavy_menstrual_bleeding: prev.heavy_menstrual_bleeding === true ? null : true }
      : { ...prev, [key]: !prev[key] }
  );

  const runQuality = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const result = await checkImageQuality(file);
      setQuality(result);
      setStep(1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Image quality check failed.');
    } finally {
      setLoading(false);
    }
  };

  const runAnalysis = async () => {
    if (!file) return;
    setLoading(true);
    setError(null);
    try {
      const result = await analyzeScreening(file, symptoms);
      setAnalysis(result);
      const item = buildRecent(result);
      if (item) {
        const next = [item, ...recent].slice(0, 6);
        setRecent(next);
        saveRecent(next);
      }
      setStep(3);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Screening failed.';
      // Surface scan limit errors clearly
      if (msg.toLowerCase().includes('limit reached') || msg.toLowerCase().includes('upgrade')) {
        setError('Free plan limit reached (10 scans). Open your Dashboard to upgrade to Pro for unlimited screenings.');
      } else if (msg.toLowerCase().includes('timeout') || msg.toLowerCase().includes('aborted')) {
        setError('Analysis timed out. The AI guidance service may be slow — please try again.');
      } else {
        setError(msg);
      }
    } finally {
      setLoading(false);
    }
  };

  const loadSample = async (imageUrl: string, sampleSymptoms: SymptomInput, id: string) => {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(imageUrl);
      const blob = await response.blob();
      setFile(new File([blob], `${id}.jpg`, { type: 'image/jpeg' }));
      setPreview(imageUrl);
      setSymptoms(sampleSymptoms);
      setQuality(null);
      setAnalysis(null);
      setStep(0);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Sample image failed to load.');
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setStep(0);
    setFile(null);
    setPreview(null);
    setSymptoms(defaultSymptoms);
    setQuality(null);
    setAnalysis(null);
    setError(null);
    setIsOfflineMode(false);
  };

  // Offline symptom-only assessment — runs locally when backend is down
  const symptomOnlyAssess = () => {
    const activeKeys = Object.entries(symptoms)
      .filter(([, v]) => v === true)
      .map(([k]) => k);
    const count = activeKeys.length;
    const hasHeavyBleeding = symptoms.heavy_menstrual_bleeding === true;
    const hasSevere = symptoms.fatigue && symptoms.shortness_of_breath && symptoms.dizziness;

    let band: TriageResult['band'];
    let score: number;
    if (hasSevere || (count >= 4 && hasHeavyBleeding)) {
      band = 'high_concern'; score = 0.82;
    } else if (count >= 3 || (count >= 2 && hasHeavyBleeding)) {
      band = 'moderate_risk'; score = 0.55;
    } else if (count >= 1) {
      band = 'low_risk'; score = 0.25;
    } else {
      band = 'low_risk'; score = 0.1;
    }

    const labelMap: Record<string, string> = {
      high_concern: 'High Concern',
      moderate_risk: 'Moderate Risk',
      low_risk: 'Low Risk',
      uncertain_retake_needed: 'Uncertain',
    };

    const offlineResult: AnalyzeResponse = {
      blocked: false,
      quality: { passed: false, blur_score: 0, brightness_score: 0, contrast_score: 0, framing_score: 0, issues: [] },
      prediction: null,
      decision_audit: {
        processing_path: 'quality_blocked',
        calibration_band: 'uncertain',
        decision_threshold: null,
        threshold_margin: null,
        quality_warning_codes: ['offline_mode'],
        review_flags: ['Symptom-only assessment — no image analysis'],
        summary: 'Offline mode: symptom-only triage',
      },
      triage: {
        band,
        score,
        label: labelMap[band],
        summary: `Based on ${count} reported symptom${count !== 1 ? 's' : ''}, this offline assessment suggests ${labelMap[band].toLowerCase()}. Image analysis unavailable.`,
        disclaimer: 'This is a symptom-only offline estimate. It is not a diagnosis. Please connect to the internet and retake the screening with an eye image for accurate results.',
      },
      guidance: {
        source: 'fallback',
        model_used: null,
        provider_used: null,
        explanation: 'Backend unavailable. This result is based on symptoms only — no image was analyzed.',
        urgency_guidance: band === 'high_concern'
          ? 'Multiple severe symptoms reported. Seek medical attention within 24–48 hours.'
          : band === 'moderate_risk'
          ? 'Moderate symptoms present. See a doctor within 1–2 weeks.'
          : 'Mild or no symptoms. Maintain a balanced diet and monitor.',
        food_advice: 'Eat iron-rich foods: dark leafy greens, lentils, lean meat, fortified cereals.',
        next_steps: [
          'Reconnect to internet and retake with an eye image for accurate results',
          'Visit a clinic for a full blood count (CBC) test',
          'Maintain an iron-rich diet',
        ],
      },
      insight_pack: {
        priority_window: band === 'high_concern' ? 'within_24_48_hours' : band === 'moderate_risk' ? 'within_1_2_weeks' : 'routine_monitoring',
        priority_label: band === 'high_concern' ? 'Within 24–48 hours' : band === 'moderate_risk' ? 'Within 1–2 weeks' : 'Routine monitoring',
        why_this_result: 'Symptom-only offline assessment.',
        confidence_story: 'No image data available. Confidence is low.',
        risk_drivers: [],
        capture_improvements: ['Reconnect to internet', 'Retake with eye image'],
        follow_up_timeline: [],
        judge_summary: 'Offline symptom triage only.',
      },
      clinical_brief: {
        headline: `Offline: ${labelMap[band]}`,
        verdict: 'Symptom-only assessment',
        action_window: band === 'high_concern' ? 'within_24_48_hours' : 'within_1_2_weeks',
        action_label: 'Retake when online',
        signal_breakdown: {
          image_risk: null,
          symptom_score: score,
          fused_score: score,
          image_weight: 0,
          symptom_weight: 1,
          symptom_burden: count === 0 ? 'none' : count <= 2 ? 'mild' : count <= 4 ? 'moderate' : 'severe',
          confidence: null,
          uncertainty: null,
          reliability_flag: null,
        },
        supporting_evidence: activeKeys.map(k => symptomLabels[k as keyof SymptomInput]),
        limiting_factors: ['No image analysis', 'Offline mode'],
        safety_checks: ['offline_mode'],
        recommended_actions: ['Retake with image when online', 'See a doctor'],
        share_text: `AnemiaLens Offline Assessment\nSymptoms: ${activeKeys.map(k => symptomLabels[k as keyof SymptomInput]).join(', ') || 'None'}\nResult: ${labelMap[band]}\nNote: Symptom-only — no image analyzed.`,
      },
      handoff_summary: {
        headline: `Offline: ${labelMap[band]}`,
        urgency_label: band === 'high_concern' ? 'Urgent' : band === 'moderate_risk' ? 'Soon' : 'Routine',
        generated_at: new Date().toISOString(),
        key_points: [`${count} symptom(s) reported`, 'No image analysis available'],
        next_steps: ['Retake with image when online', 'See a doctor for CBC test'],
        share_text: `AnemiaLens Offline Assessment\nSymptoms: ${activeKeys.map(k => symptomLabels[k as keyof SymptomInput]).join(', ') || 'None'}\nResult: ${labelMap[band]}\nNote: Symptom-only — no image analyzed.`,
      },
      analysis_meta: {
        request_id: 'offline',
        generated_at: new Date().toISOString(),
        api_version: 'offline',
        processing_time_ms: 0,
        quality_gate_passed: false,
        processing_path: 'quality_blocked',
        guidance_source: 'fallback',
        used_raw_frame_rescue: false,
        safety_layers: ['offline_mode'],
      },
      symptoms,
      language: null,
      region: null,
    };

    setIsOfflineMode(true);
    setAnalysis(offlineResult);
    setStep(3);
  };

  return {
    step, setStep,
    file, previewUrl,
    symptoms, toggleSymptom, setSymptoms,
    quality, analysis, runtime,
    recent, loading, error, backendUp,
    isOfflineMode,
    pickFile, runQuality, runAnalysis, loadSample, reset, symptomOnlyAssess,
    symptomLabels, defaultSymptoms
  };
}
