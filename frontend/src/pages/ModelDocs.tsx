import { motion, useInView } from 'framer-motion';
import { useRef, useEffect, useState } from 'react';
import {
  Brain, Layers, ChevronRight, Cpu, Eye, Activity,
  GitBranch, Zap, BarChart3, AlertTriangle, CheckCircle2, Info
} from 'lucide-react';

const FADE_UP = {
  hidden: { opacity: 0, y: 32 },
  visible: (i = 0) => ({
    opacity: 1, y: 0,
    transition: { duration: 0.65, ease: 'easeOut' as const, delay: i * 0.1 }
  })
};

function AnimatedNumber({ target, suffix = '', decimals = 0 }: { target: number; suffix?: string; decimals?: number }) {
  const [current, setCurrent] = useState(0);
  const ref = useRef<HTMLSpanElement>(null);
  const inView = useInView(ref, { once: true });

  useEffect(() => {
    if (!inView) return;
    let start = 0;
    const duration = 1800;
    const step = () => {
      start += 16;
      const progress = Math.min(start / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      setCurrent(parseFloat((target * ease).toFixed(decimals)));
      if (progress < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }, [inView, target, decimals]);

  return <span ref={ref}>{current.toFixed(decimals)}{suffix}</span>;
}

const PIPELINE_STAGES = [
  {
    id: 'capture',
    icon: Eye,
    label: 'Image Capture',
    color: '#c8003c',
    desc: 'Conjunctival photo via smartphone. BGR → RGB normalisation, EXIF orientation correction.',
    detail: 'min 240×180px · JPEG/PNG · max 20MB'
  },
  {
    id: 'quality',
    icon: CheckCircle2,
    label: 'Quality Gate',
    color: '#f59e0b',
    desc: 'Laplacian blur score, brightness/contrast analysis, ROI framing detection.',
    detail: 'blur ≥ 45 · brightness 0.12–0.95 · contrast ≥ 0.05'
  },
  {
    id: 'features',
    icon: Layers,
    label: 'Feature Extraction',
    color: '#06b6d4',
    desc: '80+ clinical features: colorimetry (RGB/HSV/LAB), texture (LBP, GLCM), illumination metrics.',
    detail: 'center_red_green_gap · palpebral_brightness · shadow_fraction'
  },
  {
    id: 'ensemble',
    icon: GitBranch,
    label: 'Ensemble Stack',
    color: '#8b5cf6',
    desc: 'Archive V8 fusion model (color + texture + KNN + Hb regressor) fused by meta-classifier.',
    detail: 'archive-fusion-v8-clinical-robust.joblib'
  },
  {
    id: 'calibration',
    icon: Activity,
    label: 'Risk Calibration',
    color: '#10b981',
    desc: 'V8 runtime risk calibrator maps raw logit → calibrated probability. Threshold per source hint.',
    detail: 'runtime_risk_calibrator_v8.pkl · Platt scaling'
  },
  {
    id: 'triage',
    icon: AlertTriangle,
    label: 'Triage + Guidance',
    color: '#ef4444',
    desc: 'Signal breakdown across pallor, Hb, symptoms. Mistral-small LLM generates contextual guidance.',
    detail: 'high ≥ 0.65 · moderate ≥ 0.40 · uncertain < threshold'
  },
];

const MODEL_METRICS = [
  { label: 'Model Version', value: 'V8 Clinical Robust', sub: 'Archive Fusion Ensemble' },
  { label: 'Feature Vector', value: '80+', sub: 'Clinical features extracted' },
  { label: 'Ensemble Models', value: '5', sub: 'Color · Texture · KNN · Hb · Fusion' },
  { label: 'TTA Variants', value: '5', sub: 'Test-time augmentation passes' },
  { label: 'MC Dropout', value: '25', sub: 'Uncertainty sampling passes' },
  { label: 'Decision Threshold', value: '0.50', sub: 'Calibrated per source hint' },
];

export default function ModelDocs() {
  return (
    <main style={{ minHeight: '100vh', paddingTop: '8rem', paddingBottom: '6rem', color: 'var(--text-primary)' }}>
      <div style={{ maxWidth: 1200, margin: '0 auto', padding: '0 clamp(1rem, 4vw, 4rem)' }}>

        {/* Hero */}
        <motion.div
          initial="hidden" animate="visible" variants={FADE_UP}
          style={{ textAlign: 'center', marginBottom: '5rem' }}
        >
          <div className="section-eyebrow" style={{ marginBottom: '1.25rem' }}>
            <Brain size={14} style={{ display: 'inline', marginRight: '0.4rem' }} />
            Model Documentation
          </div>
          <h1 style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(2.8rem, 6vw, 5rem)', fontWeight: 700, lineHeight: 1.0, letterSpacing: '-0.03em', marginBottom: '1.5rem' }}>
            How AnemiaLens<br />
            <span style={{ fontStyle: 'italic', fontWeight: 300, color: 'var(--accent-bright)' }}>makes predictions</span>
          </h1>
          <p style={{ fontSize: '1.05rem', color: 'var(--text-muted)', maxWidth: 600, margin: '0 auto', lineHeight: 1.75 }}>
            A technical deep-dive into the full ML inference pipeline — from raw pixel to anemia risk score.
          </p>
        </motion.div>

        {/* Metric cards */}
        <motion.div
          initial="hidden" whileInView="visible" viewport={{ once: true }}
          style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '1rem', marginBottom: '5rem' }}
        >
          {MODEL_METRICS.map((m, i) => (
            <motion.div key={m.label} custom={i} variants={FADE_UP}
              className="glass"
              style={{ padding: '1.5rem', borderRadius: '1.25rem', textAlign: 'center',
                background: 'rgba(15,23,42,0.03)', border: '1px solid rgba(15,23,42,0.07)' }}>
              <div style={{ fontFamily: 'var(--mono)', fontSize: '1.8rem', fontWeight: 700, color: 'var(--accent-bright)', marginBottom: '0.3rem' }}>
                {m.value}
              </div>
              <div style={{ fontSize: '0.78rem', fontWeight: 600, marginBottom: '0.2rem' }}>{m.label}</div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>{m.sub}</div>
            </motion.div>
          ))}
        </motion.div>

        {/* Pipeline */}
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={FADE_UP} style={{ marginBottom: '5rem' }}>
          <div className="section-eyebrow" style={{ marginBottom: '1rem' }}>Inference Pipeline</div>
          <h2 style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(2rem, 4vw, 3rem)', fontWeight: 700, letterSpacing: '-0.03em', marginBottom: '3rem' }}>
            Six-stage screening architecture
          </h2>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
            {PIPELINE_STAGES.map((stage, i) => {
              const Icon = stage.icon;
              return (
                <motion.div key={stage.id} custom={i} variants={FADE_UP}
                  style={{ display: 'flex', gap: '1.5rem', alignItems: 'flex-start', position: 'relative', paddingBottom: i < PIPELINE_STAGES.length - 1 ? '2.5rem' : '0' }}>
                  {/* Connector line */}
                  {i < PIPELINE_STAGES.length - 1 && (
                    <div style={{ position: 'absolute', left: 20, top: 44, bottom: 0, width: 2,
                      background: `linear-gradient(to bottom, ${stage.color}40, transparent)` }} />
                  )}

                  {/* Icon node */}
                  <div style={{ width: 42, height: 42, borderRadius: '50%', flexShrink: 0,
                    background: `${stage.color}18`, border: `1.5px solid ${stage.color}50`,
                    display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1 }}>
                    <Icon size={18} color={stage.color} />
                  </div>

                  {/* Content */}
                  <div className="glass" style={{ flex: 1, padding: '1.25rem 1.5rem', borderRadius: '1rem',
                    background: 'rgba(15,23,42,0.025)', border: '1px solid rgba(15,23,42,0.06)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '0.5rem' }}>
                      <span style={{ fontFamily: 'var(--mono)', fontSize: '0.6rem', color: stage.color,
                        background: `${stage.color}14`, padding: '0.2rem 0.5rem', borderRadius: '0.35rem',
                        border: `1px solid ${stage.color}30` }}>STAGE {String(i + 1).padStart(2, '0')}</span>
                      <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>{stage.label}</span>
                    </div>
                    <p style={{ fontSize: '0.83rem', color: 'var(--text-muted)', lineHeight: 1.65, marginBottom: '0.6rem' }}>{stage.desc}</p>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', color: 'var(--text-dim)', padding: '0.3rem 0.6rem',
                      background: 'rgba(15,23,42,0.03)', borderRadius: '0.4rem', display: 'inline-block' }}>
                      {stage.detail}
                    </div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </motion.div>

        {/* EfficientNet section */}
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={FADE_UP}
          className="glass"
          style={{ padding: '2.5rem', borderRadius: '1.75rem', marginBottom: '3rem',
            background: 'rgba(200,0,60,0.05)', border: '1px solid rgba(200,0,60,0.15)' }}>
          <div style={{ display: 'flex', gap: '2rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
            <div style={{ flex: '1 1 300px' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '1rem' }}>
                <Cpu size={22} color="var(--accent-bright)" />
                <h3 style={{ fontSize: '1.4rem', fontWeight: 700, fontFamily: 'var(--serif)' }}>EfficientNet-B2 Backbone</h3>
              </div>
              <p style={{ color: 'var(--text-muted)', lineHeight: 1.7, marginBottom: '1.25rem', fontSize: '0.88rem' }}>
                Our secondary model uses EfficientNet-B2 (260×260) upgraded with a
                <strong style={{ color: 'var(--text-primary)' }}> CBAM spatial + channel attention module</strong>,
                <strong style={{ color: 'var(--text-primary)' }}> dual global pooling</strong> (avg ⊕ max → 2816-dim feature), and
                Monte Carlo dropout uncertainty estimation. During inference, 5 TTA variants × 25 MC passes = 125 forward samples per image.
              </p>
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {['CBAM Attention', 'Dual Pooling', '5-TTA', '25 MC Passes', 'Focal Loss', 'BN+GELU Head'].map(tag => (
                  <span key={tag} style={{ padding: '0.25rem 0.65rem', borderRadius: '0.5rem', fontSize: '0.62rem',
                    fontFamily: 'var(--mono)', fontWeight: 600, background: 'rgba(200,0,60,0.1)',
                    border: '1px solid rgba(200,0,60,0.2)', color: 'var(--accent-bright)' }}>
                    {tag}
                  </span>
                ))}
              </div>
            </div>
            <div style={{ flex: '0 0 auto' }}>
              {/* Architecture diagram (CSS-only) */}
              <div style={{ width: 220, display: 'flex', flexDirection: 'column', gap: '0.4rem', fontFamily: 'var(--mono)', fontSize: '0.62rem' }}>
                {[
                  { label: 'Input 260×260×3', bg: '#1a1a2e' },
                  { label: 'EfficientNet-B2 Features', bg: '#170d2e' },
                  { label: 'CBAM Channel Attn', bg: '#1a0d20' },
                  { label: 'CBAM Spatial Attn', bg: '#1a0d20' },
                  { label: 'AvgPool ⊕ MaxPool', bg: '#0d1a1a' },
                  { label: 'FC 2816→512 + BN + GELU', bg: '#0d1a10' },
                  { label: 'FC 512→128 + BN + GELU', bg: '#0d1a10' },
                  { label: 'FC 128→2 [risk, Hb]', bg: '#1a0a0d' },
                ].map((l, i) => (
                  <div key={i} style={{ padding: '0.45rem 0.75rem', background: l.bg,
                    border: '1px solid rgba(15,23,42,0.06)', borderRadius: '0.4rem',
                    color: 'rgba(15,23,42,0.65)', textAlign: 'center' }}>
                    {l.label}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </motion.div>

        {/* Disclaimer */}
        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={FADE_UP}
          style={{ padding: '1.25rem 1.75rem', borderRadius: '1rem', display: 'flex', gap: '1rem', alignItems: 'flex-start',
            background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.2)' }}>
          <Info size={18} color="#F59E0B" style={{ flexShrink: 0, marginTop: 2 }} />
          <p style={{ fontSize: '0.8rem', color: '#FCD34D', lineHeight: 1.65, margin: 0 }}>
            <strong>Screening aid only.</strong> AnemiaLens does not diagnose anemia and is not intended to replace the assessment of a qualified medical professional. All predictions are probabilistic estimates and must be confirmed by laboratory tests (CBC / hemoglobin assay).
          </p>
        </motion.div>

      </div>
    </main>
  );
}
