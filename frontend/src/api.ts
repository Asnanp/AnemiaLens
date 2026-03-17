import type {
  AnalyzeResponse,
  QualityAssessment,
  RuntimeStatusResponse,
  SymptomInput
} from './types';

const API_BASE = (
  import.meta.env.VITE_API_BASE_URL ?? ''
).replace(/\/$/, '');

// Compress image to max 800px and ~80% JPEG quality before sending to backend.
// Shrinks 2-3MB demo/phone images down to ~80-150KB — prevents OOM on free-tier servers.
async function compressImage(file: File, maxDim = 800, quality = 0.82): Promise<File> {
  return new Promise((resolve) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      URL.revokeObjectURL(url);
      const { width, height } = img;
      const scale = Math.min(1, maxDim / Math.max(width, height));
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(width * scale);
      canvas.height = Math.round(height * scale);
      const ctx = canvas.getContext('2d')!;
      ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(
        (blob) => resolve(blob ? new File([blob], file.name, { type: 'image/jpeg' }) : file),
        'image/jpeg',
        quality
      );
    };
    img.onerror = () => { URL.revokeObjectURL(url); resolve(file); };
    img.src = url;
  });
}

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
  const compressed = await compressImage(file);
  const formData = new FormData();
  formData.append('image', compressed);

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
  const compressed = await compressImage(file);
  const formData = new FormData();
  formData.append('image', compressed);
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
