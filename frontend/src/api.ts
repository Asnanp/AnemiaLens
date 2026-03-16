import type {
  AnalyzeResponse,
  QualityAssessment,
  RuntimeStatusResponse,
  SymptomInput
} from './types';

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL ?? ''
).replace(/\/$/, '');

function endpoint(path: string): string {
  return API_BASE ? `${API_BASE}${path}` : path;
}

export async function checkBackendHealth(): Promise<boolean> {
  try {
    const response = await fetch(endpoint('/health'), {
      method: 'GET'
    });
    return response.ok;
  } catch {
    return false;
  }
}

export async function getRuntimeStatus(): Promise<RuntimeStatusResponse> {
  const response = await fetch(endpoint('/api/runtime-status'), {
    method: 'GET'
  });

  if (!response.ok) {
    throw new Error('Runtime status request failed.');
  }

  return (await response.json()) as RuntimeStatusResponse;
}

export async function checkImageQuality(file: File): Promise<QualityAssessment> {
  const formData = new FormData();
  formData.append('image', file);

  const response = await fetch(endpoint('/api/quality-check'), {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    let message = 'Image quality check failed.';
    try {
      const body = await response.json();
      if (body?.error) message = body.error;
    } catch { /* use default */ }
    throw new Error(message);
  }

  const data = (await response.json()) as { quality: QualityAssessment };
  return data.quality;
}

export async function analyzeScreening(
  file: File,
  symptoms: SymptomInput,
  language?: string,
  region?: string
): Promise<AnalyzeResponse> {
  const formData = new FormData();
  formData.append('image', file);
  formData.append('symptoms', JSON.stringify(symptoms));
  if (language) {
    formData.append('language', language);
  }
  if (region) {
    formData.append('region', region);
  }

  const response = await fetch(endpoint('/api/analyze'), {
    method: 'POST',
    body: formData
  });

  if (!response.ok) {
    let message = 'Screening request failed.';
    try {
      const body = await response.json();
      if (body?.error) message = body.error;
    } catch { /* use default */ }
    throw new Error(message);
  }

  return (await response.json()) as AnalyzeResponse;
}
