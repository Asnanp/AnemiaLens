import { useEffect, useState } from 'react';
import type { AnalyzeResponse } from '../../types';

// ── useCountUp Hook ──────────────────────────────────────────────────────────

export function useCountUp(target: number, duration = 1600, delay = 200) {
  const [val, setVal] = useState(0);
  useEffect(() => {
    let start: number | null = null;
    const t = setTimeout(() => {
      const step = (ts: number) => {
        if (!start) start = ts;
        const p = Math.min((ts - start) / duration, 1);
        const ease = 1 - Math.pow(1 - p, 3);
        setVal(parseFloat((ease * target).toFixed(1)));
        if (p < 1) requestAnimationFrame(step);
        else setVal(target);
      };
      requestAnimationFrame(step);
    }, delay);
    return () => clearTimeout(t);
  }, [target, duration, delay]);
  return val;
}

// ── Reliability Status ───────────────────────────────────────────────────────

export type ReliabilityStatus = {
  label: 'High' | 'Moderate' | 'Low';
  color: string;
  detail: string;
};

function isSevereLightingCase(analysis: AnalyzeResponse): boolean {
  const breakdown = analysis.prediction?.confidence_breakdown;
  return (
    analysis.quality.lighting_condition === 'glare_heavy'
    || analysis.quality.lighting_condition === 'shadow_heavy'
    || analysis.quality.lighting_condition === 'overexposed'
    || (breakdown?.glare_risk ?? analysis.quality.glare_risk ?? 0) > 0.65
    || (breakdown?.shadow_risk ?? analysis.quality.shadow_risk ?? 0) > 0.65
  );
}

export function getReliabilityStatus(analysis: AnalyzeResponse): ReliabilityStatus {
  const prediction = analysis.prediction;
  const confidencePct = Math.round((prediction?.confidence ?? 0) * 100);
  const hasWarnings = analysis.quality.issues.some((issue) => issue.severity === 'warning');
  const blockedByQuality = !prediction || !analysis.quality.passed || analysis.decision_audit.processing_path === 'quality_blocked';
  const severeLighting = isSevereLightingCase(analysis);
  const captureQuality = prediction?.confidence_breakdown?.capture_quality ?? 0;
  const thresholdStability = prediction?.confidence_breakdown?.threshold_stability ?? 0;
  const modelStability = prediction?.confidence_breakdown?.model_stability ?? 0;

  if (blockedByQuality) {
    return {
      label: 'Low',
      color: '#EF4444',
      detail: 'Image quality affected prediction reliability, so the system stayed retake-first instead of giving false reassurance.',
    };
  }

  if (
    severeLighting
    || confidencePct < 45
    || analysis.decision_audit.processing_path === 'full_frame_rescue'
  ) {
    return {
      label: 'Low',
      color: '#F97316',
      detail: 'Image quality affected prediction reliability, so a cleaner retake would improve trust in this result.',
    };
  }

  if (
    prediction.reliability_flag === 'low'
    && analysis.quality.passed
    && confidencePct >= 65
    && captureQuality >= 0.7
    && thresholdStability >= 0.72
    && !severeLighting
  ) {
    return {
      label: 'Moderate',
      color: '#F59E0B',
      detail: modelStability < 0.45
        ? 'The result is leaning one way, but repeat model passes varied more than ideal. A cleaner retake would make it more defensible.'
        : 'The capture is usable and the result is leaning one way, but it still benefits from a cleaner retake for stronger trust.',
    };
  }

  if (
    prediction.reliability_flag === 'low'
    || confidencePct < 50
    || hasWarnings
  ) {
    return {
      label: 'Low',
      color: '#F97316',
      detail: 'Image quality or model spread reduced trust in this result, so a cleaner retake would improve confidence.',
    };
  }

  if (prediction.reliability_flag === 'high' && confidencePct >= 80) {
    return {
      label: 'High',
      color: '#10B981',
      detail: 'Clean image quality and a stable signal support this prediction.',
    };
  }

  return {
    label: 'Moderate',
    color: '#F59E0B',
    detail: 'The prediction is usable, but stronger lighting or a cleaner capture would make it more defensible.',
  };
}
