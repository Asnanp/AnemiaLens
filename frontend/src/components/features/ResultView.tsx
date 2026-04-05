import { useEffect, useState } from 'react';
import { Download, Info, Share2, AlertCircle, RefreshCw, Stethoscope, TrendingUp, TrendingDown, Minus, Clock, Camera, Mail, BarChart2, Zap, MessageSquare, Send } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { AnalyzeResponse, GuidanceChatMessage, InsightDriver, RuntimeStatusResponse } from '../../types';
import { getRuntimeStatus, sendEmailReport, sendGuidanceChat } from '../../api';
import { useAuth } from '../../hooks/useAuth';

const E = [0.22, 1, 0.36, 1] as const;

function useCountUp(target: number, duration = 1600, delay = 200) {
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

function RiskArc({ value, color }: { value: number; color: string }) {
  const r = 52, circ = 2 * Math.PI * r;
  return (
    <div style={{ position: 'relative', width: 124, height: 124, flexShrink: 0 }}>
      <svg width="124" height="124" style={{ transform: 'rotate(-90deg)' }}>
        <circle cx="62" cy="62" r={r} fill="none" stroke="rgba(255,255,255,0.04)" strokeWidth="6" />
        <motion.circle cx="62" cy="62" r={r} fill="none"
          stroke={color} strokeWidth="6" strokeLinecap="round"
          strokeDasharray={circ}
          initial={{ strokeDashoffset: circ }}
          animate={{ strokeDashoffset: circ - (value / 100) * circ }}
          transition={{ duration: 1.6, delay: 0.5, ease: E }}
          style={{ filter: `drop-shadow(0 0 10px ${color})` }}
        />
      </svg>
      <div style={{ position: 'absolute', inset: 0, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' }}>
        <span style={{ fontFamily: 'var(--mono)', fontWeight: 700, fontSize: '1.4rem', color, lineHeight: 1 }}>{value}%</span>
        <span style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', letterSpacing: '0.12em', textTransform: 'uppercase', marginTop: 4 }}>Risk Score</span>
      </div>
    </div>
  );
}

const SYMPTOM_LABELS: Record<keyof AnalyzeResponse['symptoms'], string> = {
  fatigue: 'fatigue',
  dizziness: 'dizziness',
  pale_skin: 'pale skin',
  shortness_of_breath: 'shortness of breath',
  heavy_menstrual_bleeding: 'heavy menstrual bleeding',
  poor_diet_low_iron: 'low iron intake',
};

function activeSymptomLabels(symptoms: AnalyzeResponse['symptoms']): string[] {
  return (Object.keys(SYMPTOM_LABELS) as Array<keyof AnalyzeResponse['symptoms']>)
    .filter((key) => symptoms[key] === true)
    .map((key) => SYMPTOM_LABELS[key]);
}

function joinHuman(items: string[]): string {
  if (items.length === 0) return '';
  if (items.length === 1) return items[0];
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(', ')}, and ${items[items.length - 1]}`;
}

type ReliabilityStatus = {
  label: 'High' | 'Moderate' | 'Low';
  color: string;
  detail: string;
};

type HemoglobinPresentation = {
  headline: string;
  detail: string;
  preview: string;
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

function classificationLabel(label: string): string {
  return (label ?? 'screening result').toLowerCase().replace(/\s+/g, '-');
}

function formatModelVersion(modelSource?: string | null): string {
  return (modelSource ?? 'archive-evidence-fusion-v4').replace(/_/g, '-').toLowerCase();
}

function humanizeToken(value?: string | null, fallback = 'N/A'): string {
  if (!value) return fallback;
  return value.replace(/_/g, ' ');
}

function getReliabilityStatus(analysis: AnalyzeResponse): ReliabilityStatus {
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

function buildMandatoryWhySummary(analysis: AnalyzeResponse): string {
  const activeSymptoms = activeSymptomLabels(analysis.symptoms);
  const classLabel = classificationLabel(analysis.triage.label);

  if (!analysis.prediction) {
    return 'The system could not trust the captured image enough to estimate conjunctival pallor. Because image quality affected prediction reliability, this result stays retake-first rather than giving false reassurance.';
  }

  const imageRisk = analysis.prediction.anemia_risk;
  if (imageRisk >= 0.55) {
    return activeSymptoms.length > 0
      ? `The model detected reduced redness in the conjunctival region, which is a key indicator of low hemoglobin. Combined with the reported symptom severity, this leads to a ${classLabel} classification.`
      : `The model detected reduced redness in the conjunctival region, which is a key indicator of low hemoglobin. With no additional symptom burden lowering the case, this leads to a ${classLabel} classification.`;
  }

  if (imageRisk >= 0.35) {
    return activeSymptoms.length > 0
      ? `The model detected mildly reduced redness in the conjunctival region, suggesting a borderline low-hemoglobin signal. Combined with the reported symptom severity, this leads to a ${classLabel} classification.`
      : `The model detected a borderline change in conjunctival redness, but not a strong pallor pattern. With no added symptom burden, this leads to a ${classLabel} classification.`;
  }

  return activeSymptoms.length > 0
    ? `The model did not detect strong pallor in the conjunctival region, which lowers concern for low hemoglobin. Symptom input was still considered, and the combined signal leads to a ${classLabel} classification.`
    : `The model did not detect strong pallor in the conjunctival region, which lowers concern for low hemoglobin. With no additional symptom burden, this leads to a ${classLabel} classification.`;
}

function buildWhyResultSteps(analysis: AnalyzeResponse): Array<{
  title: string;
  detail: string;
  impact: InsightDriver['impact'];
}> {
  const activeSymptoms = activeSymptomLabels(analysis.symptoms);
  const warningIssues = analysis.quality.issues.filter((issue) => issue.severity === 'warning');
  const fusedPct = Math.round((analysis.clinical_brief?.signal_breakdown?.fused_score ?? analysis.triage.score ?? 0) * 100);

  if (!analysis.prediction) {
    const blocker = analysis.quality.issues[0];
    return [
      {
        title: 'Image quality gate stopped inference',
        detail: 'The backend did not trust this scan enough to make a stronger screening claim.',
        impact: 'limit',
      },
      {
        title: 'Capture issue needs a retake',
        detail: blocker
          ? `${blocker.title}: ${blocker.message}`
          : 'A clearer image is needed before the model can weigh the eye-image signal.',
        impact: 'limit',
      },
      {
        title: activeSymptoms.length > 0 ? 'Symptoms still raised follow-up context' : 'No symptom burden was added',
        detail: activeSymptoms.length > 0
          ? `Reported symptoms such as ${joinHuman(activeSymptoms)} were still preserved for clinical follow-up context.`
          : 'No symptoms were reported, so the system did not add extra clinical burden on top of the blocked scan.',
        impact: activeSymptoms.length > 0 ? 'up' : 'down',
      },
      {
        title: 'Safest result stayed retake-first',
        detail: `Because the confidence gate failed, the app kept the final call at ${analysis.triage.label.toLowerCase()} instead of over-claiming.`,
        impact: 'limit',
      },
    ];
  }

  const imageRiskPct = Math.round(analysis.prediction.anemia_risk * 100);
  const imageStep =
    imageRiskPct >= 72
      ? {
          title: 'Strong pallor-like image signal',
          detail: `The conjunctiva scan produced a ${imageRiskPct}% anemia-like risk signal, which pushed the case upward.`,
          impact: 'up' as const,
        }
      : imageRiskPct >= 45
        ? {
            title: 'Borderline pallor-like image signal',
            detail: `The eye image showed a ${imageRiskPct}% risk signal, enough to keep the case above a low-risk story but not at the strongest tier.`,
            impact: 'up' as const,
          }
        : {
            title: 'Image signal reduced concern',
            detail: `The eye image stayed around ${imageRiskPct}% anemia-like risk, which lowered concern relative to a stronger pallor signal.`,
            impact: 'down' as const,
          };

  const confidenceLimited =
    analysis.decision_audit.processing_path === 'full_frame_rescue'
    || analysis.decision_audit.calibration_band.startsWith('borderline')
    || analysis.prediction.reliability_flag === 'low'
    || (analysis.prediction.uncertainty ?? 0) >= 0.5
    || warningIssues.length > 0;

  const confidenceStep = confidenceLimited
    ? {
        title: 'Confidence was tempered by scan conditions',
        detail:
          analysis.decision_audit.processing_path === 'full_frame_rescue'
            ? 'The backend had to use the fallback rescue path, so the result stayed usable but less ideal than a clean ROI crop.'
            : warningIssues.length > 0
              ? `The scan passed, but quality warnings such as ${joinHuman(warningIssues.slice(0, 2).map((issue) => issue.title.toLowerCase()))} reduced confidence in the final call.`
              : analysis.decision_audit.summary,
        impact: 'limit' as const,
      }
    : {
        title: 'Clean capture supported the call',
        detail: `The scan used a direct ROI path with ${Math.round((analysis.prediction.confidence ?? 0) * 100)}% confidence, which made the final story easier to trust.`,
        impact: 'down' as const,
      };

  const symptomStep = activeSymptoms.length > 0
    ? {
        title: 'Reported symptoms pushed triage upward',
        detail: `Symptoms such as ${joinHuman(activeSymptoms)} were fused into the triage score instead of relying on the image alone.`,
        impact: 'up' as const,
      }
    : {
        title: 'No symptoms slightly lowered the story',
        detail: 'No symptoms were reported, so the system did not add extra symptom burden on top of the eye-image model.',
        impact: 'down' as const,
      };

  const finalImpact: InsightDriver['impact'] =
    analysis.triage.band === 'high_concern' || analysis.triage.band === 'moderate_risk'
      ? 'up'
      : analysis.triage.band === 'low_risk'
        ? 'down'
        : 'limit';

  const finalStep = {
    title: `Combined signal landed at ${analysis.triage.label}`,
    detail: `After image signal, symptom fusion, and threshold auditing were combined, the final fused score settled at ${fusedPct}% and produced a ${analysis.triage.label.toLowerCase()} classification.`,
    impact: finalImpact,
  };

  return [imageStep, confidenceStep, symptomStep, finalStep];
}

function SignalBar({ label, value, color, delay = 0 }: { label: string; value: number; color: string; delay?: number }) {
  const pct = Math.round(Math.min(Math.max(value, 0), 1) * 100);
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>{label}</span>
        <span style={{ fontSize: '0.75rem', fontWeight: 700, fontFamily: 'var(--mono)', color }}>{pct}%</span>
      </div>
      <div style={{ height: 7, borderRadius: 99, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
        <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }}
          transition={{ duration: 1.2, delay, ease: E }}
          style={{ height: '100%', borderRadius: 99, background: `linear-gradient(90deg, var(--crimson), ${color})`, boxShadow: `0 0 8px ${color}60` }}
        />
      </div>
    </div>
  );
}

function getHemoglobinPresentation(analysis: AnalyzeResponse): HemoglobinPresentation {
  const value = analysis.prediction?.predicted_hemoglobin;
  if (value != null) {
    return {
      headline: `${value.toFixed(1)} g/dL`,
      detail: 'This estimate was shown because the scan quality and model trust checks were strong enough.',
      preview: `${value.toFixed(1)} g/dL`,
    };
  }

  const lighting = analysis.quality.lighting_condition;
  const reviewFlags = analysis.decision_audit?.review_flags ?? [];
  const reliability = analysis.prediction?.reliability_flag ?? 'low';

  if (lighting === 'overexposed') {
    return {
      headline: 'Estimate held back',
      detail: 'The image is brighter than ideal, so the app held back the hemoglobin number instead of showing a shaky value.',
      preview: 'Held back for this scan',
    };
  }

  if (lighting === 'glare_heavy') {
    return {
      headline: 'Estimate held back',
      detail: 'Glare washed out part of the inner eyelid, so the app kept the screening result but did not show a hemoglobin number.',
      preview: 'Held back for this scan',
    };
  }

  if (lighting === 'shadow_heavy' || lighting === 'dim') {
    return {
      headline: 'Estimate held back',
      detail: 'The inner eyelid was too shadowed for a stable hemoglobin estimate, so the app held that number back.',
      preview: 'Held back for this scan',
    };
  }

  if (reviewFlags.includes('raw_frame_rescue')) {
    return {
      headline: 'Estimate held back',
      detail: 'The app had to rescue this result from the full image because the eyelid crop was weak, so it kept the hemoglobin number hidden.',
      preview: 'Held back for this scan',
    };
  }

  if (reliability === 'low') {
    return {
      headline: 'Estimate held back',
      detail: 'The screening result still ran, but the scan was not repeatable enough for the app to show a hemoglobin number confidently.',
      preview: 'Held back for this scan',
    };
  }

  return {
    headline: 'Estimate held back',
    detail: 'The app kept the screening label, but held the hemoglobin number back because this scan did not pass the trust checks for that value.',
    preview: 'Held back for this scan',
  };
}

type SystemResultState = 'normal' | 'runtime_unavailable' | 'offline_symptom_only' | 'quality_blocked';

function getSystemResultState(analysis: AnalyzeResponse): SystemResultState {
  const qualityWarnings = analysis.decision_audit?.quality_warning_codes ?? [];
  const reviewFlags = analysis.decision_audit?.review_flags ?? [];

  if (analysis.prediction?.model_source === 'missing-model') {
    return 'runtime_unavailable';
  }

  if (!analysis.prediction && (qualityWarnings.includes('offline_mode') || reviewFlags.some((flag) => flag.toLowerCase().includes('offline')))) {
    return 'offline_symptom_only';
  }

  if (!analysis.prediction) {
    return 'quality_blocked';
  }

  return 'normal';
}

function FramedCapturePreview({
  src,
  alt,
  roiPreview,
}: {
  src?: string | null;
  alt: string;
  roiPreview?: AnalyzeResponse['roi_preview'] | null;
}) {
  const box = roiPreview?.roi_box;
  const frameWidth = roiPreview?.frame_width ?? 0;
  const frameHeight = roiPreview?.frame_height ?? 0;
  const hasBox = Boolean(
    box
    && frameWidth > 0
    && frameHeight > 0
    && box.width > 0
    && box.height > 0
  );

  const overlayStyle = hasBox
    ? {
        left: `${(box!.x / frameWidth) * 100}%`,
        top: `${(box!.y / frameHeight) * 100}%`,
        width: `${(box!.width / frameWidth) * 100}%`,
        height: `${(box!.height / frameHeight) * 100}%`,
      }
    : null;

  return (
    <div style={{ borderRadius: '0.85rem', overflow: 'hidden', border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)', minHeight: 112, position: 'relative' }}>
      {src ? (
        <>
          <img
            src={src}
            alt={alt}
            style={{ width: '100%', height: 140, objectFit: 'cover', display: 'block' }}
          />
          {overlayStyle && (
            <div
              style={{
                position: 'absolute',
                border: '2px solid rgba(34,211,238,0.95)',
                boxShadow: '0 0 0 1px rgba(0,0,0,0.35), 0 0 18px rgba(34,211,238,0.45)',
                borderRadius: '0.7rem',
                background: 'rgba(34,211,238,0.08)',
                pointerEvents: 'none',
                ...overlayStyle,
              }}
            />
          )}
        </>
      ) : (
        <div style={{ minHeight: 140, display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)', fontSize: '0.72rem' }}>
          Preview unavailable
        </div>
      )}
    </div>
  );
}

function RoiPreviewPanel({
  analysis,
  bandColor,
  capturedImageUrl,
}: {
  analysis: AnalyzeResponse;
  bandColor: string;
  capturedImageUrl?: string | null;
}) {
  const preview = analysis.roi_preview;
  if (!preview) return null;

  const sourceLabel = preview.extracted
    ? humanizeToken(preview.source, 'roi crop')
    : 'full frame fallback';
  const previewCards = [
    capturedImageUrl
      ? {
          label: 'Captured image',
          src: capturedImageUrl,
          detail: preview.roi_box
            ? 'The rectangle marks the lower inner-eyelid region accepted for screening.'
            : 'The original photo you uploaded for this screening run.',
          overlay: true,
        }
      : null,
    {
      label: preview.extracted ? 'Inner-eye focus' : 'Captured frame',
      src: preview.original_data_url,
      detail: preview.extracted
        ? 'The extracted lower inner-eyelid region used for image-led analysis.'
        : 'The app could not isolate the inner eyelid, so it fell back to the full frame.',
      overlay: false,
    },
    {
      label: 'Enhanced focus',
      src: preview.enhanced_data_url,
      detail: 'A cleaned preview with tone and contrast adjusted for easier review.',
      overlay: false,
    },
  ].filter((item): item is { label: string; src: string | null; detail: string; overlay: boolean } => Boolean(item));

  return (
    <div
      className="roi-preview-panel"
      style={{
        padding: '1rem 1.1rem',
        borderRadius: '0.95rem',
        background: 'rgba(34,211,238,0.04)',
        border: '1px solid rgba(34,211,238,0.14)',
        display: 'grid',
        gap: '0.85rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap' }}>
        <div>
          <div style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(34,211,238,0.78)', marginBottom: '0.25rem' }}>
            Capture + inner-eye preview
          </div>
          <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
            You can compare the original captured photo with the inner-eye region the model actually used.
          </div>
        </div>
        <div style={{ padding: '0.32rem 0.72rem', borderRadius: '999px', border: `1px solid ${bandColor}33`, background: `${bandColor}12`, color: bandColor, fontSize: '0.55rem', fontFamily: 'var(--mono)', letterSpacing: '0.12em', textTransform: 'uppercase', fontWeight: 700 }}>
          {sourceLabel}
        </div>
      </div>

      <div
        className="roi-preview-images"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '0.75rem',
        }}
      >
        {previewCards.map((item) => (
          <div key={item.label} style={{ display: 'grid', gap: '0.42rem' }}>
            <div style={{ fontSize: '0.54rem', fontFamily: 'var(--mono)', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-dim)' }}>
              {item.label}
            </div>
            <FramedCapturePreview
              src={item.src}
              alt={item.label}
              roiPreview={item.overlay ? analysis.roi_preview : null}
            />
            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', lineHeight: 1.55 }}>
              {item.detail}
            </div>
          </div>
        ))}
      </div>

      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.65 }}>
        {preview.enhancement_summary}
      </div>

      <div className="roi-preview-metrics" style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '0.6rem' }}>
        {[
          { label: 'ROI confidence', value: `${Math.round(preview.extraction_confidence * 100)}%`, accent: '#22D3EE' },
          { label: 'Sharpness', value: `${Math.round(preview.preview_sharpness * 100)}%`, accent: '#10B981' },
          { label: 'Tone balance', value: `${Math.round(preview.preview_tone_balance * 100)}%`, accent: '#FB7185' },
        ].map((metric) => (
          <div key={metric.label} style={{ padding: '0.72rem 0.8rem', borderRadius: '0.75rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ fontSize: '0.52rem', fontFamily: 'var(--mono)', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: '0.22rem' }}>
              {metric.label}
            </div>
            <div style={{ fontSize: '0.76rem', fontFamily: 'var(--mono)', fontWeight: 700, color: metric.accent }}>
              {metric.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function WhyThisResultPanel({
  analysis,
  bandColor,
  previewUrl,
}: {
  analysis: AnalyzeResponse;
  bandColor: string;
  previewUrl?: string | null;
}) {
  const reliability = getReliabilityStatus(analysis);
  const activeSymptoms = activeSymptomLabels(analysis.symptoms);
  const mandatorySummary = buildMandatoryWhySummary(analysis);
  const confidenceBreakdown = analysis.prediction?.confidence_breakdown;
  const systemState = getSystemResultState(analysis);
  const nextMoveSummary = analysis.quality.lighting_summary;

  const compactReason = systemState === 'runtime_unavailable'
    ? 'The screening runtime was not fully available, so the app held back normal risk storytelling and is showing a system-safe state instead.'
    : systemState === 'offline_symptom_only'
      ? 'This result is symptom-led because the live image model was not available for a full screening run.'
      : mandatorySummary;
  return (
    <motion.div className="glass" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.08, duration: 0.5, ease: E }}
      style={{
        padding: 'clamp(1.25rem,3vw,2rem)',
        borderLeft: `3px solid ${bandColor}`,
        background: 'linear-gradient(135deg, rgba(255,255,255,0.03), rgba(255,255,255,0.015))',
        display: 'flex',
        flexDirection: 'column',
        gap: '1.25rem',
      }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap' }}>
        <div>
          <div className="section-eyebrow">Why This Result</div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-dim)', lineHeight: 1.6, marginTop: '0.45rem', maxWidth: 760 }}>
            Grounded in the image signal, symptom context, and capture quality used for this run.
          </div>
        </div>
        <div style={{ padding: '0.35rem 0.85rem', borderRadius: '99px', fontSize: '0.55rem', fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: bandColor, background: `${bandColor}12`, border: `1px solid ${bandColor}30` }}>
          Transparent AI
        </div>
      </div>

      <div style={{ padding: '1rem 1.125rem', borderRadius: '0.875rem', background: 'rgba(255,255,255,0.025)', border: '1px solid rgba(255,255,255,0.06)', fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: 1.75 }}>
        {compactReason}
      </div>

      <RoiPreviewPanel analysis={analysis} bandColor={bandColor} capturedImageUrl={previewUrl} />

      <div className="result-explanation-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.85rem' }}>
        <div style={{ padding: '1rem 1.1rem', borderRadius: '0.875rem', background: 'rgba(0,194,255,0.05)', border: '1px solid rgba(0,194,255,0.14)' }}>
          <div style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(0,194,255,0.7)', marginBottom: '0.65rem' }}>
            Confidence + reliability
          </div>
          <div style={{ display: 'grid', gap: '0.55rem', marginBottom: '0.75rem' }}>
            {systemState === 'normal' ? (
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', fontSize: '0.76rem' }}>
                <span style={{ color: 'var(--text-dim)' }}>Prediction confidence</span>
                <span style={{ fontFamily: 'var(--mono)', color: 'var(--text)', fontWeight: 700 }}>{Math.round((analysis.prediction?.confidence ?? 0) * 100)}%</span>
              </div>
            ) : (
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', fontSize: '0.76rem' }}>
                <span style={{ color: 'var(--text-dim)' }}>Prediction confidence</span>
                <span style={{ fontFamily: 'var(--mono)', color: 'var(--text)', fontWeight: 700 }}>Unavailable</span>
              </div>
            )}
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', fontSize: '0.76rem' }}>
              <span style={{ color: 'var(--text-dim)' }}>Trust level</span>
              <span style={{ fontFamily: 'var(--mono)', color: reliability.color, fontWeight: 700 }}>{reliability.label}</span>
            </div>
            {systemState === 'normal' && confidenceBreakdown ? [
              { label: 'Capture quality', value: `${Math.round(confidenceBreakdown.capture_quality * 100)}%` },
              { label: 'Lighting', value: humanizeToken(confidenceBreakdown.lighting_condition, 'balanced') },
            ].map((row) => (
              <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', fontSize: '0.76rem' }}>
                <span style={{ color: 'var(--text-dim)' }}>{row.label}</span>
                <span style={{ fontFamily: 'var(--mono)', color: 'var(--text)', fontWeight: 700 }}>{row.value}</span>
              </div>
            )) : null}
          </div>
          <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.65 }}>
            {systemState === 'runtime_unavailable'
              ? 'The model runtime was unavailable for this result, so the app avoided showing misleading confidence numbers.'
              : confidenceBreakdown?.summary ?? reliability.detail}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
          <div style={{ padding: '1rem 1.1rem', borderRadius: '0.875rem', background: 'rgba(255,165,0,0.05)', border: '1px solid rgba(255,165,0,0.14)' }}>
            <div style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(255,165,0,0.8)', marginBottom: '0.65rem' }}>
              Best next move
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.65 }}>
              {activeSymptoms.length > 0
                ? `Symptoms reported: ${joinHuman(activeSymptoms)}. ${nextMoveSummary}`
                : nextMoveSummary} {analysis.insight_pack.capture_improvements[0] ?? 'A cleaner retake would mainly improve confidence, not replace medical follow-up.'}
            </div>
          </div>
          <div style={{ padding: '1rem 1.1rem', borderRadius: '0.875rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: '0.45rem' }}>
              Safety
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.65 }}>
              This is still a screening result, not a diagnosis. The safest next step is guided follow-up, not false certainty.
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function GuidanceChatPanel({ analysis }: { analysis: AnalyzeResponse }) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<GuidanceChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSend = async () => {
    const message = input.trim();
    if (!message || loading) return;

    const nextHistory: GuidanceChatMessage[] = [...messages, { role: 'user', content: message }];
    setMessages(nextHistory);
    setInput('');
    setLoading(true);
    setError(null);
    try {
      const reply = await sendGuidanceChat(analysis, message, messages);
      setMessages([...nextHistory, { role: 'assistant', content: reply.message }]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to reach the live guidance assistant.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'grid', gap: '0.75rem', marginTop: '0.35rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap' }}>
        <div style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(0,194,255,0.8)' }}>
          Ask the live guidance assistant
        </div>
        <div style={{ padding: '0.28rem 0.72rem', borderRadius: '999px', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', fontSize: '0.54rem', fontFamily: 'var(--mono)', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'rgba(0,194,255,0.85)' }}>
          Live follow-up
        </div>
      </div>

      <div style={{ fontSize: '0.76rem', color: 'var(--text-dim)', lineHeight: 1.6 }}>
        Ask a follow-up question about this screening. The reply is generated when you ask, using the current screening result as context.
      </div>

      {messages.length > 0 && (
        <div style={{ display: 'grid', gap: '0.55rem', maxHeight: 240, overflowY: 'auto', paddingRight: '0.2rem' }}>
          {messages.map((message, index) => (
            <div
              key={`${message.role}-${index}`}
              style={{
                padding: '0.8rem 0.95rem',
                borderRadius: '0.85rem',
                background: message.role === 'assistant' ? 'rgba(0,194,255,0.05)' : 'rgba(255,255,255,0.03)',
                border: message.role === 'assistant' ? '1px solid rgba(0,194,255,0.14)' : '1px solid rgba(255,255,255,0.06)',
              }}
            >
              <div style={{ fontSize: '0.52rem', fontFamily: 'var(--mono)', letterSpacing: '0.12em', textTransform: 'uppercase', color: message.role === 'assistant' ? 'rgba(0,194,255,0.82)' : 'var(--text-dim)', marginBottom: '0.38rem' }}>
                {message.role === 'assistant' ? 'Assistant reply' : 'You'}
              </div>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.65 }}>
                {message.content}
              </div>
            </div>
          ))}
        </div>
      )}

      <div style={{ display: 'flex', gap: '0.65rem', alignItems: 'stretch' }}>
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && !event.shiftKey) {
              event.preventDefault();
              void handleSend();
            }
          }}
          placeholder="Ask why the result looks this way, whether a retake matters, or what follow-up means."
          style={{
            flex: 1,
            minWidth: 0,
            padding: '0.9rem 1rem',
            borderRadius: '0.85rem',
            border: '1px solid rgba(255,255,255,0.08)',
            background: 'rgba(255,255,255,0.03)',
            color: 'var(--text)',
            fontSize: '0.78rem',
          }}
        />
        <button
          className="btn btn-glass"
          onClick={() => void handleSend()}
          disabled={loading || !input.trim()}
          style={{ padding: '0.85rem 1rem', borderRadius: '0.85rem', display: 'inline-flex', alignItems: 'center', gap: '0.45rem', opacity: loading || !input.trim() ? 0.55 : 1 }}
        >
          <Send size={13} />
          {loading ? 'Sending' : 'Ask'}
        </button>
      </div>

      {error && (
        <div style={{ fontSize: '0.72rem', color: '#F59E0B', lineHeight: 1.55 }}>
          {error}
        </div>
      )}
    </div>
  );
}

function ExplainabilityPanel({ analysis, bandColor }: { analysis: AnalyzeResponse; bandColor: string }) {
  const sb = analysis.clinical_brief?.signal_breakdown;
  if (!sb) return null;
  const imageContrib = sb.image_risk !== null ? (sb.image_risk ?? 0) * sb.image_weight : null;
  const symptomContrib = sb.symptom_score * sb.symptom_weight;
  const fused = sb.fused_score;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
      <div style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(0,194,255,0.7)' }}>
        Signal Contributions
      </div>
      {imageContrib !== null && <SignalBar label="Image Signal (conjunctival pallor)" value={imageContrib} color={bandColor} delay={0.2} />}
      <SignalBar label="Symptom Signal (self-reported)" value={symptomContrib} color="#F59E0B" delay={0.35} />
      <SignalBar label="Fused Score (combined)" value={fused} color={bandColor} delay={0.5} />
      <div style={{ display: 'flex', gap: '1.5rem', marginTop: '0.25rem', flexWrap: 'wrap' }}>
        {[
          { label: 'Image weight', val: `${Math.round(sb.image_weight * 100)}%` },
          { label: 'Symptom weight', val: `${Math.round(sb.symptom_weight * 100)}%` },
          { label: 'Symptom burden', val: sb.symptom_burden },
        ].map(r => (
          <div key={r.label} style={{ fontSize: '0.65rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)' }}>
            {r.label}: <span style={{ color: 'var(--text-muted)', textTransform: 'capitalize' }}>{r.val}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function ClinicalModePanel({ analysis }: { analysis: AnalyzeResponse }) {
  const audit = analysis.decision_audit;
  const meta = analysis.analysis_meta;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      <div style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(0,229,150,0.7)' }}>
        Clinical Audit Data
      </div>
      {[
        { label: 'Calibration Band', val: humanizeToken(audit.calibration_band) },
        { label: 'Threshold Margin', val: audit.threshold_margin !== null ? `${(audit.threshold_margin * 100).toFixed(1)}%` : 'N/A' },
        { label: 'Processing Path', val: humanizeToken(meta.processing_path) },
        { label: 'Safety Layers', val: meta.safety_layers?.join(', ') || 'None' },
      ].map(row => (
        <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', padding: '0.6rem 0.875rem', borderRadius: '0.5rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
          <span style={{ fontSize: '0.7rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)' }}>{row.label}</span>
          <span style={{ fontSize: '0.7rem', fontFamily: 'var(--mono)', color: 'var(--text-muted)', textAlign: 'right', textTransform: 'capitalize' }}>{row.val}</span>
        </div>
      ))}
      {audit.review_flags && audit.review_flags.length > 0 && (
        <div style={{ padding: '0.75rem', borderRadius: '0.5rem', background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.15)' }}>
          <div style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', color: 'rgba(245,158,11,0.8)', marginBottom: '0.35rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Review Flags</div>
          {audit.review_flags.map((f, i) => (
            <div key={i} style={{ fontSize: '0.7rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>• {f}</div>
          ))}
        </div>
      )}
    </div>
  );
}

const WHO_BANDS = [
  { label: 'Severe', max: 8, color: '#EF4444', bg: 'rgba(239,68,68,0.15)' },
  { label: 'Moderate', max: 11, color: '#F59E0B', bg: 'rgba(245,158,11,0.12)' },
  { label: 'Mild', max: 12, color: '#FBBF24', bg: 'rgba(251,191,36,0.1)' },
  { label: 'Normal', max: 18, color: '#10B981', bg: 'rgba(16,185,129,0.1)' },
];

function HbReferenceBand({ hb }: { hb: number }) {
  const MIN = 4, MAX = 18;
  const clamp = (v: number) => Math.max(MIN, Math.min(MAX, v));
  const pct = (v: number) => ((clamp(v) - MIN) / (MAX - MIN)) * 100;
  const markerPct = pct(hb);
  const activeBand = WHO_BANDS.find((b, i) => {
    const prev = WHO_BANDS[i - 1];
    return hb <= b.max && (!prev || hb > prev.max);
  }) ?? WHO_BANDS[WHO_BANDS.length - 1];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(255,215,0,0.6)' }}>WHO Hb Reference</span>
        <span style={{ fontSize: '0.7rem', fontFamily: 'var(--mono)', color: activeBand.color, fontWeight: 700 }}>{activeBand.label} {hb < 12 ? '⚠' : '✓'}</span>
      </div>
      <div style={{ position: 'relative', height: 32, borderRadius: 99, overflow: 'visible' }}>
        <div style={{ position: 'absolute', inset: 0, borderRadius: 99, background: 'linear-gradient(90deg, #EF4444 0%, #F59E0B 35%, #FBBF24 55%, #10B981 100%)', opacity: 0.25 }} />
        {WHO_BANDS.map((band, i) => {
          const prevMax = WHO_BANDS[i - 1]?.max ?? MIN;
          const left = pct(prevMax);
          const width = pct(band.max) - left;
          return (
            <div key={band.label} style={{ position: 'absolute', top: 0, bottom: 0, left: `${left}%`, width: `${width}%`, background: band.bg, borderRight: i < WHO_BANDS.length - 1 ? '1px solid rgba(255,255,255,0.08)' : 'none', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <span style={{ fontSize: '0.48rem', fontFamily: 'var(--mono)', color: band.color, fontWeight: 700, letterSpacing: '0.08em', textTransform: 'uppercase', whiteSpace: 'nowrap' }}>{band.label}</span>
            </div>
          );
        })}
        <motion.div initial={{ left: '0%' }} animate={{ left: `${markerPct}%` }} transition={{ duration: 1.4, delay: 0.4, ease: [0.22, 1, 0.36, 1] }}
          style={{ position: 'absolute', top: '50%', transform: 'translate(-50%, -50%)', width: 16, height: 16, borderRadius: '50%', background: activeBand.color, border: '2px solid rgba(255,255,255,0.9)', boxShadow: `0 0 12px ${activeBand.color}, 0 0 24px ${activeBand.color}60`, zIndex: 2 }}
        />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        {[4, 8, 11, 12, 18].map(v => (
          <span key={v} style={{ fontSize: '0.55rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)' }}>{v}</span>
        ))}
      </div>
      <div style={{ textAlign: 'center', fontSize: '0.52rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', marginTop: '-0.25rem' }}>g/dL — WHO Adult Reference Ranges</div>
    </div>
  );
}

const DRIVER_ICONS: Record<InsightDriver['impact'], React.ReactNode> = {
  up: <TrendingUp size={13} />,
  down: <TrendingDown size={13} />,
  limit: <Minus size={13} />,
};
const DRIVER_COLORS: Record<InsightDriver['strength'], string> = {
  high: '#EF4444',
  medium: '#F59E0B',
  watch: '#94A3B8',
};

function InsightPackPanel({ analysis }: { analysis: AnalyzeResponse }) {
  const ip = analysis.insight_pack;
  const [tab, setTab] = useState<'drivers' | 'timeline' | 'tips'>('drivers');
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: '100%' }}>
      <div style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(255,165,0,0.8)' }}>Case Insight Pack</div>
      <div style={{ padding: '0.75rem 1rem', borderRadius: '0.875rem', background: 'rgba(255,165,0,0.07)', border: '1px solid rgba(255,165,0,0.2)', display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
        <Clock size={14} style={{ color: '#FFA500', flexShrink: 0 }} />
        <div>
          <div style={{ fontSize: '0.55rem', fontFamily: 'var(--mono)', color: 'rgba(255,165,0,0.6)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Priority Window</div>
          <div style={{ fontSize: '0.85rem', fontWeight: 700, color: '#FFA500' }}>{ip.priority_label}</div>
        </div>
      </div>
      <div style={{ display: 'flex', borderRadius: '0.625rem', overflow: 'hidden', border: '1px solid rgba(255,255,255,0.07)', background: 'rgba(255,255,255,0.02)' }}>
        {(['drivers', 'timeline', 'tips'] as const).map(t => (
          <button key={t} onClick={() => setTab(t)} style={{ flex: 1, padding: '0.55rem', fontSize: '0.58rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.08em', fontWeight: 600, background: tab === t ? 'rgba(255,165,0,0.15)' : 'transparent', color: tab === t ? '#FFA500' : 'var(--text-dim)', border: 'none', cursor: 'pointer', transition: 'all 0.2s', borderRight: t !== 'tips' ? '1px solid rgba(255,255,255,0.06)' : 'none' }}>
            {t === 'drivers' ? 'Risk Drivers' : t === 'timeline' ? 'Timeline' : 'Capture Tips'}
          </button>
        ))}
      </div>
      <AnimatePresence mode="wait">
        <motion.div key={tab} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.2 }} style={{ flex: 1, overflowY: 'auto' }}>
          {tab === 'drivers' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {ip.risk_drivers.length === 0
                ? <p style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>No specific risk drivers identified.</p>
                : ip.risk_drivers.map((d, i) => (
                  <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.07 }}
                    style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start', padding: '0.75rem 1rem', borderRadius: '0.625rem', background: 'rgba(255,255,255,0.02)', border: `1px solid ${DRIVER_COLORS[d.strength]}22`, borderLeft: `3px solid ${DRIVER_COLORS[d.strength]}` }}>
                    <div style={{ color: DRIVER_COLORS[d.strength], flexShrink: 0, marginTop: 2 }}>{DRIVER_ICONS[d.impact]}</div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text)', marginBottom: '0.2rem' }}>{d.title}</div>
                      <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', lineHeight: 1.5 }}>{d.detail}</div>
                    </div>
                    <span style={{ fontSize: '0.52rem', fontFamily: 'var(--mono)', color: DRIVER_COLORS[d.strength], textTransform: 'uppercase', letterSpacing: '0.1em', flexShrink: 0 }}>{d.strength}</span>
                  </motion.div>
                ))}
            </div>
          )}
          {tab === 'timeline' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {ip.follow_up_timeline.length === 0
                ? <p style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>No timeline steps available.</p>
                : ip.follow_up_timeline.map((step, i) => (
                  <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.07 }}
                    style={{ display: 'flex', gap: '0.875rem', alignItems: 'flex-start', padding: '0.75rem 1rem', borderRadius: '0.625rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <div style={{ width: 32, height: 32, borderRadius: '0.5rem', background: 'rgba(255,165,0,0.1)', border: '1px solid rgba(255,165,0,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                      <Clock size={13} style={{ color: '#FFA500' }} />
                    </div>
                    <div>
                      <div style={{ fontSize: '0.65rem', fontFamily: 'var(--mono)', color: '#FFA500', marginBottom: '0.2rem', textTransform: 'uppercase', letterSpacing: '0.08em' }}>{step.window}</div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>{step.action}</div>
                    </div>
                  </motion.div>
                ))}
            </div>
          )}
          {tab === 'tips' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {ip.capture_improvements.length === 0
                ? <p style={{ fontSize: '0.78rem', color: 'var(--text-dim)', fontStyle: 'italic' }}>Image quality was good — no improvements needed.</p>
                : ip.capture_improvements.map((tip, i) => (
                  <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.07 }}
                    style={{ display: 'flex', gap: '0.75rem', alignItems: 'center', padding: '0.75rem 1rem', borderRadius: '0.625rem', background: 'rgba(0,194,255,0.04)', border: '1px solid rgba(0,194,255,0.12)' }}>
                    <Camera size={13} style={{ color: 'rgba(0,194,255,0.7)', flexShrink: 0 }} />
                    <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>{tip}</span>
                  </motion.div>
                ))}
            </div>
          )}
        </motion.div>
      </AnimatePresence>
      {ip.judge_summary && (
        <div style={{ padding: '0.875rem 1rem', borderRadius: '0.625rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', fontSize: '0.72rem', color: 'var(--text-dim)', lineHeight: 1.6, fontStyle: 'italic' }}>
          "{ip.judge_summary}"
        </div>
      )}
    </div>
  );
}

function formatPercentMetric(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined) return '—';
  return `${(value * 100).toFixed(digits)}%`;
}

type AudienceMode = 'user' | 'doctor';

function estimateRetakeConfidence(analysis: AnalyzeResponse): number {
  const current = Math.round((analysis.prediction?.confidence ?? 0) * 100);
  const warningCount = analysis.quality.issues.filter((issue) => issue.severity === 'warning').length;
  let lift = 8 + warningCount * 6;
  if ((analysis.prediction?.reliability_flag ?? 'low') === 'low') lift += 8;
  if (analysis.decision_audit.processing_path === 'full_frame_rescue') lift += 5;
  if (!analysis.quality.passed) lift += 10;
  return Math.min(94, current + lift);
}

function estimateSymptomLift(analysis: AnalyzeResponse): number {
  const breakdown = analysis.clinical_brief?.signal_breakdown;
  if (!breakdown) return 6;
  return Math.max(4, Math.round(Math.max(0, 1 - breakdown.symptom_score) * breakdown.symptom_weight * 100));
}

function AudienceModePanel({
  analysis,
  mode,
  onModeChange,
  bandColor,
}: {
  analysis: AnalyzeResponse;
  mode: AudienceMode;
  onModeChange: (mode: AudienceMode) => void;
  bandColor: string;
}) {
  const audit = analysis.decision_audit;
  const meta = analysis.analysis_meta;
  const items = mode === 'user'
    ? [
        {
          label: 'What this means',
          value: analysis.triage.summary,
        },
        {
          label: 'Action now',
          value: analysis.guidance.urgency_guidance,
        },
        {
          label: 'How it is phrased',
          value: 'Keeps medical language simple, calm, and safety-first for patients or families.',
        },
      ]
    : [
        {
          label: 'Threshold + margin',
          value: audit.threshold_margin !== null && audit.decision_threshold !== null
            ? `${(audit.threshold_margin * 100).toFixed(1)} pts around a ${(audit.decision_threshold * 100).toFixed(0)}% operating threshold`
            : 'Threshold data unavailable for this case.',
        },
        {
          label: 'Processing path',
          value: `${humanizeToken(meta.processing_path)} with ${(meta.safety_layers ?? []).length} active safety layers and ${(audit.review_flags ?? []).length} review flags.`,
        },
        {
          label: 'Clinical handoff',
          value: 'Doctor mode is optimized for CBC follow-up, provider sharing, and structured review rather than consumer-only language.',
        },
      ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap' }}>
        <div className="section-eyebrow">Audience Modes</div>
        <div style={{ display: 'inline-flex', padding: '0.2rem', borderRadius: '999px', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.08)' }}>
          {([
            { key: 'user', label: 'User View', icon: <Zap size={11} /> },
            { key: 'doctor', label: 'Doctor View', icon: <Stethoscope size={11} /> },
          ] as const).map((option) => (
            <button
              key={option.key}
              onClick={() => onModeChange(option.key)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.38rem',
                padding: '0.45rem 0.8rem',
                borderRadius: '999px',
                border: 'none',
                cursor: 'pointer',
                background: mode === option.key ? `${bandColor}18` : 'transparent',
                color: mode === option.key ? bandColor : 'var(--text-dim)',
                fontSize: '0.58rem',
                fontFamily: 'var(--mono)',
                fontWeight: 700,
                letterSpacing: '0.1em',
                textTransform: 'uppercase',
              }}
            >
              {option.icon}{option.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ padding: '0.95rem 1rem', borderRadius: '0.9rem', background: `${bandColor}10`, border: `1px solid ${bandColor}20`, fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.7 }}>
        {mode === 'user'
          ? 'User View keeps the narrative simple and action-oriented so the result feels understandable without losing the safety message.'
          : 'Doctor View foregrounds threshold logic, audit metadata, and handoff readiness so a clinician can review the case faster.'}
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.7rem' }}>
        {items.map((item) => (
          <div key={item.label} style={{ padding: '0.9rem 1rem', borderRadius: '0.85rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ fontSize: '0.55rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--text-dim)', marginBottom: '0.35rem' }}>
              {item.label}
            </div>
            <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', lineHeight: 1.65 }}>
              {item.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function ScenarioSimulatorPanel({
  analysis,
  onRetake,
  onShare,
}: {
  analysis: AnalyzeResponse;
  onRetake: () => void;
  onShare: () => void;
}) {
  const retakeConfidence = estimateRetakeConfidence(analysis);
  const symptomLift = estimateSymptomLift(analysis);
  const thresholdMargin = Math.abs(analysis.decision_audit.threshold_margin ?? 0);
  const currentConfidence = Math.round((analysis.prediction?.confidence ?? 0) * 100);
  const activeSymptoms = activeSymptomLabels(analysis.symptoms);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: '100%' }}>
      <div className="section-eyebrow">What-If Simulator</div>
      <div style={{ padding: '0.95rem 1rem', borderRadius: '0.9rem', background: 'rgba(0,194,255,0.06)', border: '1px solid rgba(0,194,255,0.15)', fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.7 }}>
        These are forward-looking estimates based on the current confidence, symptom weighting, and threshold margin of this exact case.
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <div style={{ padding: '1rem', borderRadius: '0.9rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', marginBottom: '0.35rem', alignItems: 'center' }}>
            <span style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'rgba(0,194,255,0.75)' }}>
              Better Retake
            </span>
            <span style={{ fontSize: '0.8rem', fontFamily: 'var(--mono)', color: 'rgba(0,194,255,0.95)' }}>
              {currentConfidence}% → ~{retakeConfidence}%
            </span>
          </div>
          <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', lineHeight: 1.65, marginBottom: '0.75rem' }}>
            Cleaner lighting and steadier framing would most likely improve confidence first. {thresholdMargin < 0.08 ? 'Because this case sits near threshold, a stronger retake could also stabilize the final band.' : 'The biggest gain here is a more defensible explanation and hemoglobin estimate.'}
          </div>
          <button className="btn btn-glass" onClick={onRetake} style={{ width: '100%', padding: '0.7rem', borderRadius: '0.8rem', fontSize: '0.66rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.45rem' }}>
            <RefreshCw size={13} /> Retake for Stronger Confidence
          </button>
        </div>

        <div style={{ padding: '1rem', borderRadius: '0.9rem', background: 'rgba(255,165,0,0.05)', border: '1px solid rgba(255,165,0,0.15)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', marginBottom: '0.35rem', alignItems: 'center' }}>
            <span style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'rgba(255,165,0,0.8)' }}>
              Symptom Change
            </span>
            <span style={{ fontSize: '0.8rem', fontFamily: 'var(--mono)', color: '#FFA500' }}>
              ~+{symptomLift} pts possible
            </span>
          </div>
          <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', lineHeight: 1.65 }}>
            {activeSymptoms.length > 0
              ? `Current symptom burden already includes ${joinHuman(activeSymptoms)}. If symptoms worsen or new ones appear, urgency would move upward faster even with the same image signal.`
              : 'No symptom burden was added to this case. If real symptoms such as fatigue, dizziness, or shortness of breath are present, the fused triage score would move upward because symptoms are explicitly weighted in the model pipeline.'}
          </div>
        </div>

        <div style={{ padding: '1rem', borderRadius: '0.9rem', background: 'rgba(0,229,150,0.05)', border: '1px solid rgba(0,229,150,0.15)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', marginBottom: '0.35rem', alignItems: 'center' }}>
            <span style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'rgba(0,229,150,0.8)' }}>
              Clinician Review
            </span>
            <span style={{ fontSize: '0.8rem', fontFamily: 'var(--mono)', color: 'rgba(0,229,150,0.85)' }}>
              packet ready
            </span>
          </div>
          <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', lineHeight: 1.65, marginBottom: '0.75rem' }}>
            The case already has share text, safety checks, and threshold-aware audit context prepared for a provider. That makes follow-up faster than a generic symptom app.
          </div>
          <button className="btn btn-glass" onClick={onShare} style={{ width: '100%', padding: '0.7rem', borderRadius: '0.8rem', fontSize: '0.66rem', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.45rem' }}>
            <Share2 size={13} /> Share Clinician Packet
          </button>
        </div>
      </div>

      <div style={{ padding: '0.9rem 1rem', borderRadius: '0.9rem', background: 'linear-gradient(135deg, rgba(200,0,30,0.08), rgba(0,194,255,0.06))', border: '1px solid rgba(255,255,255,0.08)', fontSize: '0.76rem', color: 'var(--text-muted)', lineHeight: 1.7 }}>
        <span style={{ color: 'var(--text)', fontWeight: 700 }}>Traditional screening</span> requires lab tests. <span style={{ color: 'var(--text)', fontWeight: 700 }}>AnemiaLens</span> provides instant first-pass screening using only a smartphone, then packages the result for clinical confirmation instead of pretending to replace lab testing.
      </div>
    </div>
  );
}

function MLProofPanel() {
  const [runtimeStatus, setRuntimeStatus] = useState<RuntimeStatusResponse | null>(null);
  const [proofLoadFailed, setProofLoadFailed] = useState(false);

  useEffect(() => {
    let active = true;
    getRuntimeStatus()
      .then((status) => {
        if (!active) return;
        setRuntimeStatus(status);
        setProofLoadFailed(false);
      })
      .catch(() => {
        if (!active) return;
        setProofLoadFailed(true);
      });
    return () => {
      active = false;
    };
  }, []);

  const model = runtimeStatus?.model;
  const hasDeployedMetrics = model?.deployed_accuracy !== null && model?.deployed_accuracy !== undefined;
  const headlineAccuracy = hasDeployedMetrics ? model?.deployed_accuracy : model?.validation_accuracy;
  const headlineSubtitle = hasDeployedMetrics
    ? `deployed ROI screening${model?.deployed_validation_size ? ` · n=${model.deployed_validation_size}` : ''}`
    : model?.split_strategy ?? 'cross-validation';

  const metrics = hasDeployedMetrics
    ? [
        { label: 'Accuracy', value: formatPercentMetric(model?.deployed_accuracy), sub: headlineSubtitle, highlight: true },
        { label: 'Precision', value: formatPercentMetric(model?.deployed_precision), sub: 'positive-call correctness' },
        { label: 'Recall', value: formatPercentMetric(model?.deployed_recall), sub: 'captured anemia cases' },
        { label: 'F1 Score', value: formatPercentMetric(model?.deployed_f1), sub: 'balanced operating score' },
      ]
    : [
        { label: 'Accuracy', value: formatPercentMetric(model?.validation_accuracy), sub: headlineSubtitle, highlight: true },
        { label: 'F1 Score', value: formatPercentMetric(model?.validation_f1), sub: 'broad validation baseline' },
        { label: 'Primary Model', value: model?.primary_model ?? 'archive-fusion-v4-pipeline', sub: 'runtime artifact' },
        { label: 'Dataset', value: model?.record_count ? `${model.record_count}` : '217', sub: 'training records / subjects' },
      ];

  const footer = hasDeployedMetrics
    ? `Deployed ROI screening is the headline metric because it matches the exact in-app path. Broad training CV remains ${formatPercentMetric(model?.validation_accuracy)} accuracy${model?.validation_f1 !== null && model?.validation_f1 !== undefined ? ` / ${formatPercentMetric(model.validation_f1)} F1` : ''}.`
    : 'Showing the broader cross-validation baseline because no deployed screening report is available.';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <BarChart2 size={14} style={{ color: 'rgba(0,194,255,0.8)' }} />
        <span style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(0,194,255,0.8)' }}>Model Performance · Validated</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: '0.625rem' }}>
        {metrics.map(m => (
          <div key={m.label} style={{ padding: '1rem', borderRadius: '0.75rem', background: m.highlight ? 'rgba(0,194,255,0.07)' : 'rgba(255,255,255,0.02)', border: m.highlight ? '1px solid rgba(0,194,255,0.25)' : '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ fontSize: '0.55rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.3rem' }}>{m.label}</div>
            <div style={{ fontSize: '1.3rem', fontWeight: 700, fontFamily: 'var(--mono)', color: m.highlight ? 'rgba(0,194,255,0.95)' : 'var(--text)', lineHeight: 1 }}>{m.value}</div>
            <div style={{ fontSize: '0.55rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>{m.sub}</div>
          </div>
        ))}
      </div>
      {headlineAccuracy !== null && headlineAccuracy !== undefined && (
        <div style={{ padding: '0.85rem 1rem', borderRadius: '0.75rem', background: 'rgba(0,194,255,0.05)', border: '1px solid rgba(0,194,255,0.16)' }}>
          <div style={{ fontSize: '0.55rem', fontFamily: 'var(--mono)', color: 'rgba(0,194,255,0.6)', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: '0.35rem' }}>
            Headline Proof
          </div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
            Current headline accuracy is <span style={{ color: 'rgba(0,194,255,0.95)', fontFamily: 'var(--mono)', fontWeight: 700 }}>{formatPercentMetric(headlineAccuracy)}</span> from {headlineSubtitle}.
          </div>
        </div>
      )}
      <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', lineHeight: 1.7, padding: '0.75rem 1rem', borderRadius: '0.625rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', marginTop: 'auto' }}>
        {footer}
        {proofLoadFailed && ' Runtime status fetch failed, so the panel may be showing fallback values.'}
      </div>
    </div>
  );
}

// ── Email Report Modal ────────────────────────────────────────────────────────
function EmailReportModal({ analysis, onClose }: { analysis: AnalyzeResponse; onClose: () => void }) {
  const { user } = useAuth();
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');
  const [errMsg, setErrMsg] = useState('');
  const riskPct = Math.round((analysis.prediction?.anemia_risk ?? analysis.triage.score ?? 0) * 100);
  const summaryPreview = analysis.handoff_summary.headline || analysis.triage.summary;
  const nextStepPreview = analysis.guidance.next_steps.slice(0, 2);
  const hemoglobinPresentation = getHemoglobinPresentation(analysis);
  const hbPreview = hemoglobinPresentation.preview;

  useEffect(() => {
    if (user?.email) {
      setEmail(prev => prev || user.email);
    }
  }, [user?.email]);

  const handleSend = async () => {
    const normalizedEmail = email.trim().toLowerCase();
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(normalizedEmail)) {
      setErrMsg('Enter a valid email address');
      return;
    }
    setErrMsg('');
    setStatus('sending');
    try {
      await sendEmailReport(
        normalizedEmail,
        analysis.handoff_summary.share_text,
        analysis.triage.label,
        analysis.prediction?.predicted_hemoglobin ?? null,
        analysis.prediction?.anemia_risk ?? analysis.triage.score ?? 0,
      );
      setStatus('sent');
    } catch (e: unknown) {
      console.error('[FIX] Email report send failed', e);
      setErrMsg(e instanceof Error ? e.message : 'Send failed');
      setStatus('error');
    }
  };

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      style={{ position: 'fixed', inset: 0, zIndex: 9999, background: 'rgba(0,0,0,0.8)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '1rem' }}
      onClick={onClose}>
      <motion.div initial={{ scale: 0.92, y: 20 }} animate={{ scale: 1, y: 0 }} exit={{ scale: 0.92, y: 20 }}
        onClick={e => e.stopPropagation()}
        style={{ width: '100%', maxWidth: 520, borderRadius: '1.5rem', background: 'rgba(10,10,20,0.98)', border: '1px solid rgba(255,255,255,0.12)', padding: '2rem', display: 'flex', flexDirection: 'column', gap: '1.25rem', boxShadow: '0 40px 120px rgba(0,0,0,0.8)' }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem' }}>
            <div style={{ width: 44, height: 44, borderRadius: '1rem', background: 'rgba(200,0,30,0.12)', border: '1px solid rgba(200,0,30,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <Mail size={18} style={{ color: 'var(--accent-bright)' }} />
            </div>
            <div>
              <div style={{ fontFamily: 'var(--serif)', fontSize: '1.25rem', color: 'var(--text)', fontWeight: 600 }}>Email Report</div>
              <div style={{ fontSize: '0.76rem', color: 'var(--text-dim)', marginTop: '0.2rem', lineHeight: 1.5 }}>
                Send a clean screening summary that is easy to review or share with a clinician.
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            aria-label="Close email dialog"
            style={{ width: 36, height: 36, borderRadius: '0.9rem', border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)', color: 'var(--text-dim)', cursor: 'pointer', fontSize: '1rem', flexShrink: 0 }}
          >
            ×
          </button>
        </div>

        {status === 'sent' ? (
          <div style={{ textAlign: 'center', padding: '1.5rem 0 0.5rem' }}>
            <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1rem' }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="2.5" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>
            </div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: '0.9rem', color: 'rgba(16,185,129,0.9)', marginBottom: '0.5rem' }}>Report sent successfully</div>
            <div style={{ fontSize: '0.84rem', color: 'var(--text-muted)', lineHeight: 1.7, maxWidth: 320, margin: '0 auto' }}>
              A structured result summary was sent to <strong style={{ color: 'var(--text)' }}>{email.trim().toLowerCase()}</strong>.
            </div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '0.55rem' }}>Check your inbox in a moment and review the next steps.</div>
            <button onClick={onClose} style={{ marginTop: '1.5rem', padding: '0.8rem 2rem', borderRadius: '0.875rem', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--text)', fontSize: '0.82rem', cursor: 'pointer' }}>Done</button>
          </div>
        ) : (
          <>
            <div style={{ display: 'grid', gap: '0.9rem', padding: '1rem', borderRadius: '1.15rem', background: 'linear-gradient(180deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02))', border: '1px solid rgba(255,255,255,0.08)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.8rem', flexWrap: 'wrap' }}>
                <div style={{ fontSize: '0.64rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>Email preview</div>
                <div style={{ padding: '0.35rem 0.8rem', borderRadius: '999px', border: '1px solid rgba(255,255,255,0.1)', background: 'rgba(255,255,255,0.03)', fontSize: '0.62rem', fontFamily: 'var(--mono)', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>
                  {analysis.triage.label}
                </div>
              </div>
              <div style={{ fontSize: '0.92rem', color: 'var(--text)', lineHeight: 1.65, fontWeight: 500 }}>
                {summaryPreview}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
                <div style={{ padding: '0.9rem 1rem', borderRadius: '0.9rem', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                  <div style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: '0.4rem' }}>Risk score</div>
                  <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text)' }}>{riskPct}%</div>
                </div>
                <div style={{ padding: '0.9rem 1rem', borderRadius: '0.9rem', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                  <div style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: '0.4rem' }}>Hemoglobin</div>
                  <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text)' }}>{hbPreview}</div>
                </div>
              </div>
              <div style={{ display: 'grid', gap: '0.55rem' }}>
                <div style={{ fontSize: '0.62rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>Included in the email</div>
                {nextStepPreview.map((step) => (
                  <div key={step} style={{ display: 'flex', gap: '0.65rem', alignItems: 'flex-start', fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                    <span style={{ color: 'var(--accent-bright)', marginTop: 1 }}>•</span>
                    <span>{step}</span>
                  </div>
                ))}
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.7rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Send to</label>
              <input type="email" placeholder="name@example.com" value={email}
                onChange={e => { setEmail(e.target.value); setErrMsg(''); if (status === 'error') setStatus('idle'); }}
                style={{ width: '100%', padding: '0.875rem 1.125rem', borderRadius: '0.875rem', fontSize: '0.9rem', background: 'rgba(255,255,255,0.04)', border: errMsg ? '1px solid rgba(239,68,68,0.5)' : '1px solid rgba(255,255,255,0.1)', color: 'var(--text)', outline: 'none', boxSizing: 'border-box', transition: 'border 0.2s' }}
              />
              {errMsg && <div style={{ fontSize: '0.72rem', color: '#EF4444' }}>{errMsg}</div>}
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', lineHeight: 1.65, padding: '0.95rem 1rem', borderRadius: '0.9rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
              The email includes the result, a short explanation, and next-step guidance. It is a screening aid, not a diagnosis, and should still be confirmed with a clinical blood test (CBC).
            </div>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <button onClick={onClose} style={{ flex: 1, padding: '0.8rem', borderRadius: '0.875rem', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'var(--text-dim)', fontSize: '0.8rem', cursor: 'pointer' }}>Cancel</button>
              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }} onClick={handleSend} disabled={status === 'sending'}
                style={{ flex: 2, padding: '0.8rem', borderRadius: '0.875rem', background: 'linear-gradient(135deg, #C8001E, #E8294A)', border: 'none', color: '#fff', fontSize: '0.8rem', fontWeight: 700, cursor: 'pointer', opacity: status === 'sending' ? 0.6 : 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}>
                <Mail size={14} />{status === 'sending' ? 'Sending…' : 'Send Report'}
              </motion.button>
            </div>
          </>
        )}
      </motion.div>
    </motion.div>
  );
}

function RiskActionBadge({
  band,
  runtimeUnavailable,
  retakeRecommended,
}: {
  band: string;
  runtimeUnavailable?: boolean;
  retakeRecommended?: boolean;
}) {
  const config = runtimeUnavailable
    ? {
        color: '#38BDF8',
        bg: 'rgba(56,189,248,0.08)',
        border: 'rgba(56,189,248,0.2)',
        action: 'The screening model is temporarily unavailable. Retry this scan in a moment instead of relying on this incomplete result.',
      }
    : retakeRecommended || band === 'uncertain_retake_needed'
    ? {
        color: '#F59E0B',
        bg: 'rgba(245,158,11,0.08)',
        border: 'rgba(245,158,11,0.25)',
        action: 'Retake the image in bright indirect light and keep the lower eyelid fully visible before making a follow-up decision.',
      }
    : band === 'high_concern'
    ? { color: '#EF4444', bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.25)', action: 'Consult a doctor immediately — seek a CBC blood test within 24–48 hours.' }
    : band === 'moderate_risk'
    ? { color: '#F59E0B', bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.25)', action: 'Consider scheduling a blood test soon. Monitor symptoms and maintain iron-rich diet.' }
    : { color: '#10B981', bg: 'rgba(16,185,129,0.08)', border: 'rgba(16,185,129,0.25)', action: 'Maintain a balanced diet. Rescreen in 3–6 months or if symptoms develop.' };
  return (
    <div style={{ display: 'flex', gap: '0.875rem', alignItems: 'flex-start', padding: '1rem 1.125rem', borderRadius: '0.875rem', background: config.bg, border: `1px solid ${config.border}` }}>
      <Zap size={15} style={{ color: config.color, flexShrink: 0, marginTop: 2 }} />
      <div>
        <div style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', color: config.color, textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: '0.35rem' }}>Recommended Action</div>
        <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>{config.action}</div>
      </div>
    </div>
  );
}

function ConfidenceGauge({ analysis, color }: { analysis: AnalyzeResponse; color: string }) {
  const pct = Math.round((analysis.prediction?.confidence ?? 0) * 100);
  const reliability = getReliabilityStatus(analysis);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>Confidence</span>
        <span style={{ fontSize: '0.9rem', fontWeight: 700, fontFamily: 'var(--mono)', color }}>{pct}%</span>
      </div>
      <div style={{ height: 7, borderRadius: 99, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
        <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 1.4, delay: 0.6, ease: [0.22, 1, 0.36, 1] }}
          style={{ height: '100%', borderRadius: 99, background: `linear-gradient(90deg, ${color}80, ${color})`, boxShadow: `0 0 8px ${color}60` }}
        />
      </div>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', fontSize: '0.62rem', fontFamily: 'var(--mono)' }}>
        <span style={{ color: 'var(--text-dim)' }}>Trust level</span>
        <span style={{ color: reliability.color, fontWeight: 700 }}>{reliability.label}</span>
      </div>
      <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', lineHeight: 1.65 }}>
        {reliability.detail}
      </div>
      <div style={{ fontSize: '0.58rem', color: 'var(--text-dim)', fontFamily: 'var(--mono)', letterSpacing: '0.04em' }}>
        Confidence shows direction. Trust level shows how clean and repeatable the capture was.
      </div>
    </div>
  );
}

interface ResultViewProps {
  analysis: AnalyzeResponse;
  previewUrl?: string | null;
  onReset: () => void;
  onDownload: () => void;
  onOpenAuth?: (mode?: 'login' | 'register') => void;
}

export function ResultView({ analysis, previewUrl, onReset, onDownload, onOpenAuth }: ResultViewProps) {
  const { isAuthenticated } = useAuth();
  const systemState = getSystemResultState(analysis);
  const runtimeUnavailable = systemState !== 'normal';
  const isHigh     = analysis.triage.band === 'high_concern';
  const isModerate = analysis.triage.band === 'moderate_risk';
  const bandColor  = isHigh ? '#EF4444' : isModerate ? '#F59E0B' : '#10B981';
  const bandBg     = isHigh ? 'rgba(239,68,68,0.07)' : isModerate ? 'rgba(245,158,11,0.07)' : 'rgba(16,185,129,0.07)';
  const bandBorder = isHigh ? 'rgba(239,68,68,0.3)'  : isModerate ? 'rgba(245,158,11,0.3)'  : 'rgba(16,185,129,0.3)';
  const bandGlow   = isHigh ? 'rgba(239,68,68,0.2)'  : isModerate ? 'rgba(245,158,11,0.15)' : 'rgba(16,185,129,0.15)';

  const hbValue = analysis.prediction?.predicted_hemoglobin ?? null;
  const hasHbEstimate = hbValue !== null;
  const hemoglobinPresentation = getHemoglobinPresentation(analysis);
  const hbRaw  = hbValue ?? 0;
  const risk   = Math.round((analysis.prediction?.anemia_risk ?? analysis.triage.score ?? 0) * 100);
  const hbAnim = useCountUp(hbRaw, 1600, 200);
  const reliability = getReliabilityStatus(analysis);
  const [flashDone,     setFlashDone]     = useState(false);
  const [revealed,      setRevealed]      = useState(false);
  const [shareToast,    setShareToast]    = useState<string | null>(null);
  const [showEmailModal,setShowEmailModal]= useState(false);
  const [showAdvanced,  setShowAdvanced]  = useState(false);
  const retakeRecommended =
    analysis.triage.band === 'uncertain_retake_needed'
    || (analysis.prediction?.confidence ?? 0) < 0.55
    || analysis.quality.issues.some((issue) => issue.severity === 'warning');
  useEffect(() => {
    const t1 = setTimeout(() => setFlashDone(true), 600);
    const t2 = setTimeout(() => setRevealed(true), 700);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  const handleShare = async () => {
    const text = analysis.handoff_summary.share_text;
    if (navigator.share) {
      try { await navigator.share({ text }); return; } catch { /* fall through */ }
    }
    try {
      await navigator.clipboard.writeText(text);
      setShareToast('Copied to clipboard');
    } catch {
      setShareToast('Share text ready — copy manually');
    }
    setTimeout(() => setShareToast(null), 3000);
  };

  if (runtimeUnavailable) {
    const copy = systemState === 'offline_symptom_only'
      ? {
          badge: 'Offline symptom-only result',
          title: 'This run did not analyze the image.',
          detail:
            'The app stayed in offline symptom-only mode for this run, so it should not present a normal image-based risk story or hemoglobin estimate. Reconnect and retake the screening with an eyelid image for a real model-backed result.',
          action: 'Reconnect and retake',
          accent: '#F59E0B',
        }
      : systemState === 'quality_blocked'
        ? {
            badge: 'Retake required',
            title: 'The image did not pass the capture gate.',
            detail:
              'The screening stopped before prediction because the capture was not strong enough to interpret safely. A cleaner image is needed before the normal result layout should appear.',
            action: 'Retake image',
            accent: '#F59E0B',
          }
        : {
            badge: 'Model temporarily unavailable',
            title: 'This scan could not be completed.',
            detail:
              'The app did not have a working screening model for this run, so it should not present a normal risk story, confidence score, or follow-up action. Retry the scan once the model reconnects.',
            action: 'Retry screening',
            accent: '#38BDF8',
          };

    return (
      <motion.div
        className="glass result-hero-card result-hero-surface"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, ease: E }}
        style={{
          padding: 'clamp(1.35rem,3vw,2.25rem)',
          border: `1px solid ${copy.accent}33`,
          borderLeft: `3px solid ${copy.accent}`,
          background: 'linear-gradient(180deg, rgba(18,18,28,0.9), rgba(18,18,28,0.82))',
        }}
      >
        <div style={{ display: 'grid', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <span style={{ padding: '0.4rem 1rem', borderRadius: '99px', fontSize: '0.6rem', fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', background: `${copy.accent}14`, border: `1px solid ${copy.accent}33`, color: copy.accent }}>
              {copy.badge}
            </span>
          </div>
          <div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: '0.68rem', color: copy.accent, letterSpacing: '0.18em', textTransform: 'uppercase', marginBottom: '0.65rem' }}>
              Screening runtime
            </div>
            <div style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(2rem,4.2vw,3.2rem)', fontWeight: 600, lineHeight: 1.05, letterSpacing: '-0.03em', color: 'var(--text)' }}>
              {copy.title}
            </div>
            <div style={{ maxWidth: 620, fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: 1.75, marginTop: '0.8rem' }}>
              {copy.detail}
            </div>
          </div>
          <RiskActionBadge band={analysis.triage.band} runtimeUnavailable={systemState === 'runtime_unavailable'} retakeRecommended={systemState !== 'runtime_unavailable'} />
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button className="btn btn-primary" onClick={onReset}>
              <RefreshCw size={14} />
              {copy.action}
            </button>
            <button className="btn btn-glass" onClick={onDownload}>
              <Download size={14} />
              Export current report
            </button>
          </div>
          <div style={{ padding: '1rem 1.1rem', borderRadius: '0.875rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', fontSize: '0.76rem', color: 'var(--text-dim)', lineHeight: 1.65 }}>
            This is a system state, not a medical result. Confirm any concern with a clinician or a blood test rather than relying on an unavailable model.
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <div style={{ position: 'relative' }}>

      {/* ── EMERGENCY ALERT ── */}
      <AnimatePresence>
        {isHigh && revealed && (
          <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            style={{ marginBottom: '1.5rem', padding: '1.125rem 1.5rem', borderRadius: '1rem', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.4)', display: 'flex', alignItems: 'center', gap: '1rem', boxShadow: '0 0 40px rgba(239,68,68,0.12)' }}>
            <motion.div animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 1.5, repeat: Infinity }}
              style={{ width: 10, height: 10, borderRadius: '50%', background: '#EF4444', flexShrink: 0, boxShadow: '0 0 12px #EF4444' }} />
            <div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', color: '#EF4444', marginBottom: '0.2rem' }}>Urgent — Seek Medical Attention</div>
              <p style={{ fontSize: '0.82rem', color: '#FCA5A5', lineHeight: 1.5 }}>This result indicates high concern. Please visit a clinic within 24–48 hours and request a full blood count (CBC) test.</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── SHARE TOAST ── */}
      <AnimatePresence>
        {shareToast && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
            style={{ position: 'fixed', bottom: '2rem', left: '50%', transform: 'translateX(-50%)', zIndex: 9999, padding: '0.75rem 1.5rem', borderRadius: '0.875rem', background: 'rgba(10,10,20,0.95)', border: '1px solid rgba(255,255,255,0.12)', fontFamily: 'var(--mono)', fontSize: '0.75rem', color: 'var(--text)', boxShadow: '0 8px 40px rgba(0,0,0,0.5)', whiteSpace: 'nowrap' }}>
            ✓ {shareToast}
          </motion.div>
        )}
      </AnimatePresence>

      {/* ── EMAIL MODAL ── */}
      <AnimatePresence>
        {showEmailModal && <EmailReportModal analysis={analysis} onClose={() => setShowEmailModal(false)} />}
      </AnimatePresence>

      {/* ── FLASH OVERLAY ── */}
      <AnimatePresence>
        {!flashDone && isHigh && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: [0, 0.5, 0] }} exit={{ opacity: 0 }}
              transition={{ duration: 0.6, times: [0, 0.3, 1] }}
              style={{ position: 'fixed', inset: 0, zIndex: 9000, background: bandColor, pointerEvents: 'none' }} />
            <motion.div initial={{ opacity: 0, scale: 0.7 }} animate={{ opacity: [0, 1, 1, 0], scale: [0.7, 1.05, 1, 0.9] }}
              transition={{ duration: 0.6, times: [0, 0.25, 0.6, 1] }}
              style={{ position: 'fixed', inset: 0, zIndex: 9001, display: 'flex', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none' }}>
              <div style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(3rem,10vw,7rem)', fontWeight: 700, color: '#fff', textShadow: `0 0 60px ${bandColor}, 0 0 120px ${bandColor}80`, letterSpacing: '-0.04em' }}>
                {analysis.triage.label}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ── MAIN CONTENT ── */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: revealed ? 1 : 0 }} transition={{ duration: 0.4 }}
        style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

        {/* ── ROW 1: HERO CARD ── */}
        <motion.div className="glass result-hero-card result-hero-surface" initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: E }}
          style={{
            padding: 'clamp(1.35rem,3vw,2.35rem)',
            border: `1px solid ${bandBorder}`,
            borderLeft: `3px solid ${bandColor}`,
            background: `linear-gradient(180deg, rgba(18,18,28,0.9), rgba(18,18,28,0.82)), ${bandBg}`,
            boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06), 0 22px 44px rgba(0,0,0,0.28)',
            position: 'relative',
            overflow: 'hidden',
          }}>
          <motion.div animate={{ scale: [1, 1.12, 1], opacity: [0.06, 0.1, 0.06] }} transition={{ duration: 7, repeat: Infinity }}
            style={{ position: 'absolute', top: -100, right: -100, width: 360, height: 360, borderRadius: '50%', background: bandColor, filter: 'blur(140px)', pointerEvents: 'none' }} />

          <div style={{ position: 'relative', zIndex: 1 }}>
            {/* Badges row */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1.5rem', flexWrap: 'wrap' }}>
              <span style={{ padding: '0.4rem 1.125rem', borderRadius: '99px', fontSize: '0.6rem', fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', background: bandBg, border: `1px solid ${bandBorder}`, color: bandColor }}>
                {analysis.triage.label}
              </span>
            </div>

            {/* Metrics row */}
            <div className="result-hero-metrics" style={{ display: 'flex', alignItems: 'center', gap: 'clamp(1.35rem,3vw,2.8rem)', flexWrap: 'wrap', marginBottom: '1.5rem' }}>
              <div>
                {hasHbEstimate ? (
                  <>
                    <div style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(3.2rem,7vw,5.75rem)', fontWeight: 300, lineHeight: 1, letterSpacing: '-0.04em', color: bandColor, textShadow: `0 0 50px ${bandColor}25` }}>
                      {hbAnim.toFixed(1)}
                    </div>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: '0.68rem', color: 'var(--text-dim)', letterSpacing: '0.2em', textTransform: 'uppercase', marginTop: '0.5rem' }}>g/dL Hemoglobin</div>
                  </>
                ) : (
                  <>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: '0.68rem', color: bandColor, letterSpacing: '0.18em', textTransform: 'uppercase', marginBottom: '0.65rem' }}>
                      Hemoglobin estimate
                    </div>
                    <div style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(2rem,4.2vw,3.2rem)', fontWeight: 600, lineHeight: 1.05, letterSpacing: '-0.03em', color: 'var(--text)' }}>
                      {hemoglobinPresentation.headline}
                    </div>
                    <div style={{ maxWidth: 320, fontSize: '0.8rem', color: 'var(--text-dim)', lineHeight: 1.6, marginTop: '0.65rem' }}>
                      {hemoglobinPresentation.detail}
                    </div>
                  </>
                )}
              </div>
              <div style={{ width: 1, height: 90, background: 'rgba(255,255,255,0.08)', flexShrink: 0 }} className="result-divider" />
              <RiskArc value={risk} color={bandColor} />
              <div style={{ width: 1, height: 90, background: 'rgba(255,255,255,0.08)', flexShrink: 0 }} className="result-divider" />
              <div className="result-metric-cluster" style={{ display: 'flex', gap: '1.5rem', flexWrap: 'wrap' }}>
                {[
                  { label: 'Triage Score', val: `${Math.round((analysis.triage.score ?? 0) * 100)}%` },
                  { label: 'Confidence', val: `${Math.round((analysis.prediction?.confidence ?? 0) * 100)}%` },
                  { label: 'Reliability', val: reliability.label },
                ].map(s => (
                  <div key={s.label}>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: '0.6rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: '0.3rem' }}>{s.label}</div>
                    <div style={{ fontFamily: 'var(--mono)', fontWeight: 700, fontSize: '1.15rem', color: 'var(--text)' }}>{s.val}</div>
                  </div>
                ))}
              </div>
            </div>

            <p style={{ fontSize: '0.9rem', color: 'var(--text-muted)', lineHeight: 1.72, maxWidth: 720, marginBottom: '1.35rem' }}>
              {analysis.triage.summary}
            </p>

            {/* WHO band + Confidence + Action — 3 col */}
            <div className="result-summary-grid result-summary-grid-clean" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '0.9rem', marginBottom: '1.35rem' }}>
              {hasHbEstimate && (
                <div style={{ padding: '1.25rem 1.5rem', borderRadius: '0.875rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.07)', gridColumn: 'span 1' }}>
                  <HbReferenceBand hb={hbRaw} />
                </div>
              )}
              <div style={{ padding: '1.25rem 1.5rem', borderRadius: '0.875rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.07)' }}>
                <ConfidenceGauge analysis={analysis} color={bandColor} />
              </div>
              <RiskActionBadge band={analysis.triage.band} retakeRecommended={retakeRecommended} />
            </div>

            {/* Disclaimer */}
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start', padding: '1rem 1.25rem', borderRadius: '0.875rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
              <Info size={14} style={{ color: 'var(--accent-bright)', flexShrink: 0, marginTop: 2 }} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.45rem' }}>
                <p style={{ fontSize: '0.76rem', color: 'var(--text-muted)', lineHeight: 1.65, fontWeight: 600 }}>
                  This system is designed as a screening aid and prioritizes safety by avoiding false reassurance.
                </p>
                <p style={{ fontSize: '0.72rem', color: 'var(--text-dim)', lineHeight: 1.6 }}>{analysis.triage.disclaimer}</p>
              </div>
            </div>
          </div>
        </motion.div>

        <WhyThisResultPanel analysis={analysis} bandColor={bandColor} previewUrl={previewUrl} />

        <div className="result-core-grid result-core-grid-clean" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px,1fr))', gap: '1.1rem' }}>
          <motion.div className="glass result-section-card result-section-card-clean" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.12, ease: E }}
            style={{ padding: 'clamp(1.25rem,3vw,2rem)', display: 'flex', flexDirection: 'column', gap: '1.25rem', borderLeft: '3px solid rgba(0,194,255,0.4)' }}>
            <div className="section-eyebrow">Care guidance</div>

            <div style={{ padding: '1rem 1.1rem', borderRadius: '0.9rem', background: 'rgba(0,194,255,0.05)', border: '1px solid rgba(0,194,255,0.14)', display: 'grid', gap: '0.8rem' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap' }}>
                <div style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(0,194,255,0.8)' }}>
                  Guidance summary
                </div>
                <div style={{ padding: '0.28rem 0.72rem', borderRadius: '999px', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', fontSize: '0.54rem', fontFamily: 'var(--mono)', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'rgba(0,194,255,0.85)' }}>
                  {analysis.guidance.source === 'mistral' ? 'Live guidance layer' : 'Fallback guidance'}
                </div>
              </div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.68 }}>
                {analysis.guidance.explanation}
              </div>
              <div style={{ padding: '0.85rem 0.95rem', borderRadius: '0.8rem', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                <div style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: '0.38rem' }}>
                  Action now
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.62 }}>
                  {analysis.guidance.urgency_guidance}
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
              <div style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-dim)' }}>
                Next steps
              </div>
              {analysis.guidance.next_steps.slice(0, 3).map((step, i) => (
                <div key={i} style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start', padding: '0.8rem 0.95rem', borderRadius: '0.8rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
                  <span style={{ fontFamily: 'var(--mono)', fontSize: '0.72rem', color: bandColor, fontWeight: 700, minWidth: 18 }}>{i + 1}.</span>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.55 }}>{step}</span>
                </div>
              ))}
            </div>

            {analysis.guidance.food_advice && (
              <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', lineHeight: 1.6, padding: '0.9rem 1rem', borderRadius: '0.8rem', background: 'rgba(0,229,150,0.04)', border: '1px solid rgba(0,229,150,0.12)' }}>
                {analysis.guidance.food_advice}
              </div>
            )}

            <GuidanceChatPanel analysis={analysis} />
          </motion.div>

          <motion.div className="glass result-section-card result-section-card-clean" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18, ease: E }}
            style={{ padding: 'clamp(1.25rem,3vw,2rem)', display: 'flex', flexDirection: 'column', gap: '1rem', borderLeft: `3px solid ${bandColor}` }}>
            <div className="section-eyebrow">Share or save</div>
            {!isAuthenticated && onOpenAuth && (
              <div style={{ padding: '1rem 1.1rem', borderRadius: '0.9rem', background: 'rgba(200,0,30,0.05)', border: '1px solid rgba(200,0,30,0.16)', display: 'grid', gap: '0.8rem' }}>
                <div>
                  <div style={{ fontSize: '0.58rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--accent-bright)', marginBottom: '0.4rem' }}>
                    Account save
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.65 }}>
                    Save this screening to your account so it shows up in history and future follow-up.
                  </div>
                </div>
                <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
                  <button
                    className="btn btn-glass"
                    style={{ padding: '0.7rem 0.95rem', fontSize: '0.65rem', borderRadius: '0.8rem' }}
                    onClick={() => onOpenAuth('login')}
                  >
                    Sign In to Save
                  </button>
                  <button
                    className="btn btn-primary"
                    style={{ padding: '0.7rem 0.95rem', fontSize: '0.65rem', borderRadius: '0.8rem' }}
                    onClick={() => onOpenAuth('register')}
                  >
                    Create Free Account
                  </button>
                </div>
              </div>
            )}
            {isAuthenticated && (
              <div style={{ padding: '0.95rem 1.1rem', borderRadius: '0.875rem', background: 'rgba(16,185,129,0.05)', border: '1px solid rgba(16,185,129,0.14)' }}>
                <div style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(16,185,129,0.85)', marginBottom: '0.45rem' }}>
                  Account sync
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.65 }}>
                  This run is linked to your signed-in session, so future screenings can build a real history and trend view.
                </div>
              </div>
            )}
            <div style={{ display: 'grid', gap: '0.75rem' }}>
              <motion.button className="btn btn-primary" whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.98 }}
                style={{ width: '100%', padding: '0.85rem', fontSize: '0.72rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
                onClick={handleShare}>
                <Share2 size={14} /> Share with Provider
              </motion.button>
              <motion.button className="btn btn-glass" whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.98 }}
                style={{ width: '100%', padding: '0.85rem', fontSize: '0.72rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', border: '1px solid rgba(200,0,30,0.3)', color: 'var(--accent-bright)' }}
                onClick={() => setShowEmailModal(true)}>
                <Mail size={14} /> Send Report to Email
              </motion.button>
              <motion.button className="btn btn-glass" whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.98 }}
                style={{ width: '100%', padding: '0.85rem', fontSize: '0.72rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
                onClick={onDownload}>
                <Download size={14} /> Export PDF Report
              </motion.button>
              <motion.button className="btn btn-glass" whileHover={{ scale: 1.01 }} whileTap={{ scale: 0.98 }}
                style={{ width: '100%', padding: '0.85rem', fontSize: '0.72rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
                onClick={onReset}>
                <RefreshCw size={13} /> {retakeRecommended ? 'Retake Image' : 'Start New Screening'}
              </motion.button>
            </div>
            <div style={{ padding: '0.95rem 1.1rem', borderRadius: '0.875rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
              <div style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: '0.45rem' }}>
                Safety
              </div>
              <div style={{ fontSize: '0.76rem', color: 'var(--text-dim)', lineHeight: 1.65 }}>
                Not a diagnostic device. Confirm results with clinical blood testing.
              </div>
            </div>
          </motion.div>
        </div>

        <motion.div className="glass" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.24, ease: E }}
          style={{ padding: '1rem 1.25rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <button
            onClick={() => setShowAdvanced((current) => !current)}
            style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', width: '100%', background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer', padding: 0, textAlign: 'left' }}
          >
            <div>
              <div className="section-eyebrow">Advanced details</div>
              <div style={{ marginTop: '0.35rem', fontSize: '0.78rem', color: 'var(--text-dim)', lineHeight: 1.6 }}>
                Signal breakdown, scenario tools, and model proof are still here if you want them.
              </div>
            </div>
            <span style={{ padding: '0.35rem 0.8rem', borderRadius: '999px', border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)', fontSize: '0.58rem', fontFamily: 'var(--mono)', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
              {showAdvanced ? 'Hide' : 'Show'}
            </span>
          </button>

          <AnimatePresence>
            {showAdvanced && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.28 }} style={{ overflow: 'hidden' }}>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px,1fr))', gap: '1rem', paddingTop: '0.5rem' }}>
                  <div style={{ padding: '1.1rem', borderRadius: '0.95rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <ScenarioSimulatorPanel analysis={analysis} onRetake={onReset} onShare={handleShare} />
                  </div>
                  <div style={{ padding: '1.1rem', borderRadius: '0.95rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <div className="section-eyebrow" style={{ marginBottom: '1rem' }}>Signal analysis</div>
                    <ExplainabilityPanel analysis={analysis} bandColor={bandColor} />
                  </div>
                  <div style={{ padding: '1.1rem', borderRadius: '0.95rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <MLProofPanel />
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </motion.div>

      </motion.div>
    </div>
  );
}
