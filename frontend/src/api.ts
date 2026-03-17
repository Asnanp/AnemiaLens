import type {
  AnalyzeResponse,
  QualityAssessment,
  RuntimeStatusResponse,
  SymptomInput
} from './types';

// Silent wake ping — fires immediately on import, warms Render cold start
// before the user even clicks anything
(function silentWake() {
  const base = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
  const url = base ? `${base}/health` : '/health';
  fetch(url, { method: 'GET' }).catch(() => {/* silent — just warming */});
})();


  import.meta.env.VITE_API_BASE_URL ?? ''
).replace(/\/$/, '');

// Compress image to max 300KB before sending to backend.
// Resizes to max 800px then iterates quality down until under the size cap.
async function compressImage(file: File, maxDim = 800, maxBytes = 300_000): Promise<File> {
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

      // Try quality steps from 0.82 down to 0.40 until under maxBytes
      const qualities = [0.82, 0.72, 0.62, 0.52, 0.42];
      let idx = 0;

      const tryNext = () => {
        const q = qualities[idx++];
        canvas.toBlob((blob) => {
          if (!blob) { resolve(file); return; }
          if (blob.size <= maxBytes || idx >= qualities.length) {
            resolve(new File([blob], file.name, { type: 'image/jpeg' }));
          } else {
            tryNext();
          }
        }, 'image/jpeg', q);
      };

      tryNext();
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
