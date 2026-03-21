import type {
  AnalyzeResponse,
  QualityAssessment,
  RuntimeStatusResponse,
  SymptomInput
} from './types';

// In production (Vercel), we use relative paths so Vercel's rewrites proxy requests to Render.
const IS_PROD = window.location.hostname !== 'localhost' && !window.location.hostname.includes('127.0.0.1');

const API_BASE = IS_PROD
  ? ''
  : (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

export function endpoint(path: string): string {
  return `${API_BASE}${path}`;
}

// Token accessor — set by AuthProvider so api.ts can attach auth headers
let _getToken: (() => string | null) | null = null;
export function setTokenAccessor(fn: () => string | null) { _getToken = fn; }

function authHeaders(): Record<string, string> {
  const token = _getToken?.();
  return token ? { Authorization: `Bearer ${token}` } : {};
}

// ── WAKE STATE — subscribers notified when backend comes online ───────────────
type WakeStatus = 'waking' | 'ready' | 'failed';
let _wakeStatus: WakeStatus = 'waking';
const _wakeListeners = new Set<(s: WakeStatus) => void>();

export function onWakeStatus(cb: (s: WakeStatus) => void): () => void {
  _wakeListeners.add(cb);
  cb(_wakeStatus);
  return () => { _wakeListeners.delete(cb); };
}

function _setWake(s: WakeStatus) {
  _wakeStatus = s;
  _wakeListeners.forEach(cb => cb(s));
}

// ── SILENT WAKE — retry with backoff until backend responds ──────────────────
// Render free tier cold start ~50-90s. Poll aggressively, give up after 150s.
(function silentWake() {
  const url = endpoint('/health');
  const INTERVALS = [500, 1000, 2000, 5000, 8000, 10000, 10000, 10000, 10000, 10000, 10000, 10000, 10000, 10000, 10000];
  const MAX_MS = 150_000;
  let elapsed = 0;
  let idx = 0;

  const schedule = () => {
    const delay = INTERVALS[Math.min(idx++, INTERVALS.length - 1)];
    elapsed += delay;
    if (elapsed >= MAX_MS) { _setWake('failed'); return; }
    setTimeout(ping, delay);
  };

  const ping = () => {
    fetch(url, { method: 'GET', signal: AbortSignal.timeout(8000) })
      .then(r => { if (r.ok) _setWake('ready'); else schedule(); })
      .catch(() => schedule());
  };

  ping();
})();

// ── IMAGE COMPRESSION ─────────────────────────────────────────────────────────
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
      const qualities = [0.82, 0.72, 0.62, 0.52, 0.42];
      let i = 0;
      const tryNext = () => {
        const q = qualities[i++];
        canvas.toBlob((blob) => {
          if (!blob) { resolve(file); return; }
          if (blob.size <= maxBytes || i >= qualities.length) {
            resolve(new File([blob], file.name, { type: 'image/jpeg' }));
          } else { tryNext(); }
        }, 'image/jpeg', q);
      };
      tryNext();
    };
    img.onerror = () => { URL.revokeObjectURL(url); resolve(file); };
    img.src = url;
  });
}

// ── API CALLS ─────────────────────────────────────────────────────────────────
export async function checkBackendHealth(): Promise<boolean> {
  try {
    const r = await fetch(endpoint('/health'), { method: 'GET', signal: AbortSignal.timeout(10000) });
    return r.ok;
  } catch { return false; }
}

export async function getRuntimeStatus(): Promise<RuntimeStatusResponse> {
  const r = await fetch(endpoint('/api/runtime-status'), { method: 'GET', signal: AbortSignal.timeout(10000) });
  if (!r.ok) throw new Error('Runtime status request failed.');
  return (await r.json()) as RuntimeStatusResponse;
}

export async function checkImageQuality(file: File): Promise<QualityAssessment> {
  const compressed = await compressImage(file);
  const form = new FormData();
  form.append('image', compressed);
  const r = await fetch(endpoint('/api/quality-check'), {
    method: 'POST',
    body: form,
    signal: AbortSignal.timeout(30000),
  });
  if (!r.ok) {
    let msg = 'Image quality check failed.';
    try { const b = await r.json(); if (b?.error) msg = b.error; } catch { /* use default */ }
    throw new Error(msg);
  }
  const data = (await r.json()) as { quality: QualityAssessment };
  return data.quality;
}

export async function analyzeScreening(
  file: File,
  symptoms: SymptomInput,
  language?: string,
  region?: string,
  symptomSeverity?: Record<string, number>
): Promise<AnalyzeResponse> {
  const compressed = await compressImage(file);
  const form = new FormData();
  form.append('image', compressed);
  // Merge severity into symptoms payload so backend can weight them
  const symptomsPayload = symptomSeverity
    ? { ...symptoms, symptom_severity: symptomSeverity }
    : symptoms;
  form.append('symptoms', JSON.stringify(symptomsPayload));
  if (language) form.append('language', language);
  if (region) form.append('region', region);
  const r = await fetch(endpoint('/api/analyze'), {
    method: 'POST',
    body: form,
    headers: authHeaders(),
    signal: AbortSignal.timeout(90000), // 90s — Mistral can be slow
  });
  if (!r.ok) {
    let msg = 'Screening request failed.';
    try { const b = await r.json(); if (b?.error) msg = b.error; else if (b?.detail) msg = b.detail; } catch { /* use default */ }
    throw new Error(msg);
  }
  return (await r.json()) as AnalyzeResponse;
}

export async function upgradeToProDemo(): Promise<void> {
  const r = await fetch(endpoint('/api/billing/create-checkout-session'), {
    method: 'POST',
    headers: { ...authHeaders() },
    signal: AbortSignal.timeout(15000),
  });
  if (!r.ok) throw new Error('Upgrade request failed');
  const data = await r.json();
  if (data.checkout_url) window.location.href = data.checkout_url;
}

export async function exportScreeningsCSV(): Promise<void> {
  const token = _getToken?.();
  if (!token) throw new Error('Not authenticated');
  const r = await fetch(endpoint('/api/screenings/export/csv'), {
    headers: { Authorization: `Bearer ${token}` },
    signal: AbortSignal.timeout(30000),
  });
  if (!r.ok) {
    let msg = 'Export failed';
    try { const b = await r.json(); msg = b.detail || msg; } catch { /* */ }
    throw new Error(msg);
  }
  const blob = await r.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url; a.download = 'anemialens_history.csv';
  document.body.appendChild(a); a.click();
  document.body.removeChild(a); URL.revokeObjectURL(url);
}

export async function sendEmailReport(email: string, shareText: string, triageLabel: string, hb: number | null, risk: number): Promise<void> {
  const r = await fetch(endpoint('/api/email-report'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...authHeaders() },
    body: JSON.stringify({ email, share_text: shareText, triage_label: triageLabel, predicted_hemoglobin: hb, anemia_risk: risk }),
    signal: AbortSignal.timeout(20000),
  });
  if (!r.ok) {
    let msg = 'Failed to send report';
    try { const b = await r.json(); msg = b.detail || msg; } catch { /* */ }
    throw new Error(msg);
  }
}
