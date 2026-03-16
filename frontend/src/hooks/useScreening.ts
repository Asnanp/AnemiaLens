import { useState, useEffect } from 'react';
import { analyzeScreening, checkBackendHealth, checkImageQuality, getRuntimeStatus } from '../api';
import type { AnalyzeResponse, QualityAssessment, RecentScreening, RuntimeStatusResponse, SymptomInput } from '../types';

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
      setError(err instanceof Error ? err.message : 'Screening failed.');
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
  };

  return {
    step, setStep,
    file, previewUrl,
    symptoms, toggleSymptom, setSymptoms,
    quality, analysis, runtime,
    recent, loading, error, backendUp,
    pickFile, runQuality, runAnalysis, loadSample, reset,
    symptomLabels, defaultSymptoms
  };
}
