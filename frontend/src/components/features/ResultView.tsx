import { useEffect, useState } from 'react';
import { Download, Info, Share2, AlertCircle, RefreshCw, ChevronDown, ChevronUp, Stethoscope, TrendingUp, TrendingDown, Minus, Clock, Camera, Mail, BarChart2, Zap } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { AnalyzeResponse, InsightDriver } from '../../types';
import { sendEmailReport } from '../../api';
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
        { label: 'Calibration Band', val: audit.calibration_band?.replace(/_/g, ' ') ?? 'N/A' },
        { label: 'Threshold Margin', val: audit.threshold_margin !== null ? `${(audit.threshold_margin * 100).toFixed(1)}%` : 'N/A' },
        { label: 'Processing Path', val: meta.processing_path?.replace(/_/g, ' ') ?? 'N/A' },
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

function MLProofPanel() {
  const metrics = [
    { label: 'Accuracy', value: '70.5%', sub: '5-fold CV' },
    { label: 'Recall', value: '89.5%', sub: 'catches anemia', highlight: true },
    { label: 'AUC-ROC', value: '0.798', sub: 'discrimination' },
    { label: 'Hb MAE', value: '1.66', sub: 'g/dL error' },
  ];
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem', height: '100%' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
        <BarChart2 size={14} style={{ color: 'rgba(0,194,255,0.8)' }} />
        <span style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(0,194,255,0.8)' }}>Model Performance · Validated</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.625rem' }}>
        {metrics.map(m => (
          <div key={m.label} style={{ padding: '1rem', borderRadius: '0.75rem', background: m.highlight ? 'rgba(0,194,255,0.07)' : 'rgba(255,255,255,0.02)', border: m.highlight ? '1px solid rgba(0,194,255,0.25)' : '1px solid rgba(255,255,255,0.06)' }}>
            <div style={{ fontSize: '0.55rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.3rem' }}>{m.label}</div>
            <div style={{ fontSize: '1.3rem', fontWeight: 700, fontFamily: 'var(--mono)', color: m.highlight ? 'rgba(0,194,255,0.95)' : 'var(--text)', lineHeight: 1 }}>{m.value}</div>
            <div style={{ fontSize: '0.55rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>{m.sub}</div>
          </div>
        ))}
      </div>
      <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', lineHeight: 1.7, padding: '0.75rem 1rem', borderRadius: '0.625rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', marginTop: 'auto' }}>
        217 real patient images · India + Italy · ExtraTrees ensemble · pipeline-aligned training
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
        style={{ width: '100%', maxWidth: 460, borderRadius: '1.5rem', background: 'rgba(10,10,20,0.98)', border: '1px solid rgba(255,255,255,0.12)', padding: '2.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem', boxShadow: '0 40px 120px rgba(0,0,0,0.8)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.875rem' }}>
          <div style={{ width: 40, height: 40, borderRadius: '0.875rem', background: 'rgba(200,0,30,0.12)', border: '1px solid rgba(200,0,30,0.25)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Mail size={18} style={{ color: 'var(--accent-bright)' }} />
          </div>
          <div>
            <div style={{ fontFamily: 'var(--serif)', fontSize: '1.2rem', color: 'var(--text)', fontWeight: 600 }}>Send Report to Email</div>
            <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '0.15rem' }}>Receive your screening summary in your inbox</div>
          </div>
        </div>

        {status === 'sent' ? (
          <div style={{ textAlign: 'center', padding: '2rem 0' }}>
            <div style={{ width: 56, height: 56, borderRadius: '50%', background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1rem' }}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="2.5" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>
            </div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: '0.9rem', color: 'rgba(16,185,129,0.9)', marginBottom: '0.5rem' }}>Report sent successfully</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>Check your inbox (and spam folder)</div>
            <button onClick={onClose} style={{ marginTop: '1.5rem', padding: '0.7rem 2rem', borderRadius: '0.875rem', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--text)', fontSize: '0.8rem', cursor: 'pointer' }}>Close</button>
          </div>
        ) : (
          <>
            <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.7 }}>
              Sends your screening result — risk level, hemoglobin estimate, and next steps — directly to your email.
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              <label style={{ fontSize: '0.7rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Email Address</label>
              <input type="email" placeholder="your@email.com" value={email}
                onChange={e => { setEmail(e.target.value); setErrMsg(''); if (status === 'error') setStatus('idle'); }}
                style={{ width: '100%', padding: '0.875rem 1.125rem', borderRadius: '0.875rem', fontSize: '0.9rem', background: 'rgba(255,255,255,0.04)', border: errMsg ? '1px solid rgba(239,68,68,0.5)' : '1px solid rgba(255,255,255,0.1)', color: 'var(--text)', outline: 'none', boxSizing: 'border-box', transition: 'border 0.2s' }}
              />
              {errMsg && <div style={{ fontSize: '0.72rem', color: '#EF4444' }}>{errMsg}</div>}
            </div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', lineHeight: 1.6, padding: '0.75rem 1rem', borderRadius: '0.75rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', fontStyle: 'italic' }}>
              This is a screening aid, not a diagnosis. Always confirm with a clinical blood test (CBC).
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

function RiskActionBadge({ band }: { band: string }) {
  const config = band === 'high_concern'
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

function ConfidenceGauge({ confidence, color }: { confidence: number; color: string }) {
  const pct = Math.round(confidence * 100);
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
      <div style={{ fontSize: '0.6rem', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>
        {pct >= 70 ? 'High confidence result' : pct >= 45 ? 'Moderate confidence — consider retake' : 'Low confidence — retake recommended'}
      </div>
    </div>
  );
}

interface ResultViewProps {
  analysis: AnalyzeResponse;
  onReset: () => void;
  onDownload: () => void;
}

export function ResultView({ analysis, onReset, onDownload }: ResultViewProps) {
  const isHigh     = analysis.triage.band === 'high_concern';
  const isModerate = analysis.triage.band === 'moderate_risk';
  const bandColor  = isHigh ? '#EF4444' : isModerate ? '#F59E0B' : '#10B981';
  const bandBg     = isHigh ? 'rgba(239,68,68,0.07)' : isModerate ? 'rgba(245,158,11,0.07)' : 'rgba(16,185,129,0.07)';
  const bandBorder = isHigh ? 'rgba(239,68,68,0.3)'  : isModerate ? 'rgba(245,158,11,0.3)'  : 'rgba(16,185,129,0.3)';
  const bandGlow   = isHigh ? 'rgba(239,68,68,0.2)'  : isModerate ? 'rgba(245,158,11,0.15)' : 'rgba(16,185,129,0.15)';

  const hbRaw  = analysis.prediction?.predicted_hemoglobin ?? 0;
  const risk   = Math.round((analysis.prediction?.anemia_risk ?? analysis.triage.score ?? 0) * 100);
  const hbAnim = useCountUp(hbRaw, 1600, 200);

  const [flashDone,     setFlashDone]     = useState(false);
  const [revealed,      setRevealed]      = useState(false);
  const [clinicalMode,  setClinicalMode]  = useState(false);
  const [shareToast,    setShareToast]    = useState<string | null>(null);
  const [showEmailModal,setShowEmailModal]= useState(false);

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
        {!flashDone && (
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
        style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>

        {/* ── ROW 1: HERO CARD ── */}
        <motion.div className="glass" initial={{ opacity: 0, y: 24 }} animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: E }}
          style={{ padding: 'clamp(1.5rem,4vw,3rem)', borderLeft: `4px solid ${bandColor}`, background: bandBg, boxShadow: `inset 0 1px 0 rgba(255,255,255,0.1), -8px 0 80px ${bandGlow}`, position: 'relative', overflow: 'hidden' }}>
          <motion.div animate={{ scale: [1, 1.2, 1], opacity: [0.1, 0.18, 0.1] }} transition={{ duration: 6, repeat: Infinity }}
            style={{ position: 'absolute', top: -120, right: -120, width: 500, height: 500, borderRadius: '50%', background: bandColor, filter: 'blur(160px)', pointerEvents: 'none' }} />

          <div style={{ position: 'relative', zIndex: 1 }}>
            {/* Badges row */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '2rem', flexWrap: 'wrap' }}>
              <span style={{ padding: '0.4rem 1.125rem', borderRadius: '99px', fontSize: '0.6rem', fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.15em', textTransform: 'uppercase', background: bandBg, border: `1px solid ${bandBorder}`, color: bandColor }}>
                {analysis.triage.label}
              </span>
              {analysis.guidance.source === 'mistral' && (
                <span style={{ padding: '0.4rem 1rem', borderRadius: '99px', fontSize: '0.6rem', fontFamily: 'var(--mono)', fontWeight: 600, letterSpacing: '0.12em', textTransform: 'uppercase', background: 'rgba(0,194,255,0.07)', border: '1px solid rgba(0,194,255,0.25)', color: 'rgba(0,194,255,0.9)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                  <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'rgba(0,194,255,0.9)', display: 'inline-block' }} />
                  Mistral AI
                </span>
              )}
              <span style={{ marginLeft: 'auto', fontSize: '0.6rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', letterSpacing: '0.15em', textTransform: 'uppercase' }}>
                No lab · No needle · Just a smartphone
              </span>
              <button onClick={() => setClinicalMode(v => !v)} style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.4rem 1rem', borderRadius: '99px', fontSize: '0.6rem', fontFamily: 'var(--mono)', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', background: clinicalMode ? 'rgba(0,229,150,0.12)' : 'rgba(255,255,255,0.04)', border: clinicalMode ? '1px solid rgba(0,229,150,0.35)' : '1px solid rgba(255,255,255,0.1)', color: clinicalMode ? 'rgba(0,229,150,0.9)' : 'var(--text-dim)', cursor: 'pointer', transition: 'all 0.2s' }}>
                <Stethoscope size={11} />{clinicalMode ? 'Clinical ON' : 'Clinical Mode'}{clinicalMode ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
              </button>
            </div>

            {/* Metrics row */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 'clamp(1.5rem,4vw,3.5rem)', flexWrap: 'wrap', marginBottom: '2rem' }}>
              <div>
                <div style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(3.5rem,8vw,7rem)', fontWeight: 300, lineHeight: 1, letterSpacing: '-0.04em', color: bandColor, textShadow: `0 0 80px ${bandColor}40` }}>
                  {hbAnim.toFixed(1)}
                </div>
                <div style={{ fontFamily: 'var(--mono)', fontSize: '0.68rem', color: 'var(--text-dim)', letterSpacing: '0.2em', textTransform: 'uppercase', marginTop: '0.5rem' }}>g/dL Hemoglobin</div>
              </div>
              <div style={{ width: 1, height: 90, background: 'rgba(255,255,255,0.08)', flexShrink: 0 }} className="result-divider" />
              <RiskArc value={risk} color={bandColor} />
              <div style={{ width: 1, height: 90, background: 'rgba(255,255,255,0.08)', flexShrink: 0 }} className="result-divider" />
              <div style={{ display: 'flex', gap: '2rem', flexWrap: 'wrap' }}>
                {[
                  { label: 'Triage Score', val: `${Math.round((analysis.triage.score ?? 0) * 100)}%` },
                  { label: 'Confidence', val: `${Math.round((analysis.prediction?.confidence ?? 0) * 100)}%` },
                  { label: 'Reliability', val: analysis.prediction?.reliability_flag ?? 'N/A' },
                ].map(s => (
                  <div key={s.label}>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: '0.6rem', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.15em', marginBottom: '0.3rem' }}>{s.label}</div>
                    <div style={{ fontFamily: 'var(--mono)', fontWeight: 700, fontSize: '1.15rem', color: 'var(--text)' }}>{s.val}</div>
                  </div>
                ))}
              </div>
            </div>

            <p style={{ fontSize: '0.95rem', color: 'var(--text-muted)', lineHeight: 1.75, maxWidth: 720, marginBottom: '1.75rem' }}>
              {analysis.triage.summary}
            </p>

            {/* WHO band + Confidence + Action — 3 col */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
              {hbRaw > 0 && (
                <div style={{ padding: '1.25rem 1.5rem', borderRadius: '0.875rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.07)', gridColumn: 'span 1' }}>
                  <HbReferenceBand hb={hbRaw} />
                </div>
              )}
              <div style={{ padding: '1.25rem 1.5rem', borderRadius: '0.875rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.07)' }}>
                <ConfidenceGauge confidence={analysis.prediction?.confidence ?? 0} color={bandColor} />
              </div>
              <RiskActionBadge band={analysis.triage.band} />
            </div>

            {/* Disclaimer */}
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start', padding: '1rem 1.25rem', borderRadius: '0.875rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
              <Info size={14} style={{ color: 'var(--accent-bright)', flexShrink: 0, marginTop: 2 }} />
              <p style={{ fontSize: '0.72rem', color: 'var(--text-dim)', lineHeight: 1.6 }}>{analysis.triage.disclaimer}</p>
            </div>
          </div>
        </motion.div>

        {/* ── ROW 2: MISTRAL GUIDANCE (full width, only if mistral) ── */}
        {analysis.guidance.source === 'mistral' && (
          <motion.div initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.5, ease: E }}
            style={{ borderRadius: '1.25rem', overflow: 'hidden', border: '1px solid rgba(0,194,255,0.25)', boxShadow: '0 0 80px rgba(0,194,255,0.07)' }}>
            <div style={{ padding: '0.875rem 1.5rem', display: 'flex', alignItems: 'center', gap: '0.75rem', background: 'rgba(0,194,255,0.08)', borderBottom: '1px solid rgba(0,194,255,0.15)' }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: 'rgba(0,194,255,1)', boxShadow: '0 0 8px rgba(0,194,255,0.8)' }} />
              <span style={{ fontFamily: 'var(--mono)', fontSize: '0.6rem', fontWeight: 700, letterSpacing: '0.18em', textTransform: 'uppercase', color: 'rgba(0,194,255,0.9)' }}>
                Mistral AI · {analysis.guidance.model_used ?? 'mistral-small-latest'}
              </span>
              <span style={{ marginLeft: 'auto', fontFamily: 'var(--mono)', fontSize: '0.52rem', color: 'rgba(0,194,255,0.5)', letterSpacing: '0.1em' }}>AI-GENERATED CLINICAL GUIDANCE</span>
            </div>
            <div style={{ padding: 'clamp(1.25rem,4vw,2rem) clamp(1.25rem,4vw,2.5rem)', background: 'rgba(0,10,30,0.6)' }}>
              <div style={{ marginBottom: '1.5rem', padding: '1.25rem 1.5rem', borderRadius: '0.875rem', background: 'rgba(0,194,255,0.05)', border: '1px solid rgba(0,194,255,0.12)', borderLeft: '3px solid rgba(0,194,255,0.6)' }}>
                <div style={{ fontFamily: 'var(--mono)', fontSize: '0.52rem', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(0,194,255,0.5)', marginBottom: '0.6rem' }}>Assessment</div>
                <p style={{ fontSize: '1rem', color: 'var(--text)', lineHeight: 1.8 }}>{analysis.guidance.explanation}</p>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px,1fr))', gap: '1rem', marginBottom: '1.5rem' }}>
                <div style={{ padding: '1rem 1.25rem', borderRadius: '0.875rem', background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.2)', borderLeft: '3px solid rgba(239,68,68,0.6)' }}>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: '0.52rem', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(239,68,68,0.8)', marginBottom: '0.5rem' }}>Urgency</div>
                  <p style={{ fontSize: '0.88rem', color: 'var(--text)', lineHeight: 1.65 }}>{analysis.guidance.urgency_guidance}</p>
                </div>
                <div style={{ padding: '1rem 1.25rem', borderRadius: '0.875rem', background: 'rgba(0,229,150,0.06)', border: '1px solid rgba(0,229,150,0.2)', borderLeft: '3px solid rgba(0,229,150,0.6)' }}>
                  <div style={{ fontFamily: 'var(--mono)', fontSize: '0.52rem', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(0,229,150,0.8)', marginBottom: '0.5rem' }}>Dietary Advice</div>
                  <p style={{ fontSize: '0.88rem', color: 'var(--text)', lineHeight: 1.65 }}>{analysis.guidance.food_advice || 'Maintain a balanced, iron-rich diet.'}</p>
                </div>
              </div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: '0.52rem', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(0,194,255,0.6)', marginBottom: '0.75rem' }}>Recommended Next Steps</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {analysis.guidance.next_steps.map((step, i) => (
                  <motion.div key={i} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.3 + i * 0.08, ease: E }}
                    style={{ display: 'flex', gap: '1rem', alignItems: 'center', padding: '0.75rem 1rem', borderRadius: '0.625rem', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: '0.72rem', color: 'rgba(0,194,255,0.7)', fontWeight: 700, flexShrink: 0, minWidth: 24 }}>{i + 1}.</span>
                    <span style={{ fontSize: '0.88rem', color: 'var(--text)', lineHeight: 1.5 }}>{step}</span>
                  </motion.div>
                ))}
              </div>
            </div>
          </motion.div>
        )}

        {/* ── ROW 3: 2-col top + 3-col bottom grid ── */}
        {/* Top 2: Clinical Guidance + Signal Analysis */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px,1fr))', gap: '1.5rem' }}>

          {/* Clinical Guidance */}
          <motion.div className="glass" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15, ease: E }}
            style={{ padding: 'clamp(1.25rem,3vw,2rem)', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem' }}>
              <div className="section-eyebrow">Clinical Guidance</div>
              <span style={{ padding: '0.3rem 0.75rem', borderRadius: '99px', fontSize: '0.55rem', fontFamily: 'var(--mono)', fontWeight: 600, letterSpacing: '0.1em', textTransform: 'uppercase', background: analysis.guidance.source === 'mistral' ? 'rgba(0,194,255,0.08)' : 'rgba(255,255,255,0.04)', border: analysis.guidance.source === 'mistral' ? '1px solid rgba(0,194,255,0.25)' : '1px solid rgba(255,255,255,0.08)', color: analysis.guidance.source === 'mistral' ? 'rgba(0,194,255,0.9)' : 'var(--text-dim)' }}>
                {analysis.guidance.source === 'mistral' ? 'Mistral AI' : 'Rule-based'}
              </span>
            </div>
            <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)', lineHeight: 1.7, padding: '1rem 1.125rem', borderRadius: '0.75rem', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)' }}>
              {analysis.guidance.explanation}
            </p>
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start' }}>
              <div style={{ width: 32, height: 32, borderRadius: '0.625rem', flexShrink: 0, background: 'rgba(200,0,30,0.12)', border: '1px solid rgba(200,0,30,0.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <AlertCircle size={14} style={{ color: 'var(--accent-bright)' }} />
              </div>
              <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.6, paddingTop: '0.3rem' }}>{analysis.guidance.urgency_guidance}</p>
            </div>
            <ul style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {analysis.guidance.next_steps.slice(0, 4).map((step, i) => (
                <li key={i} style={{ display: 'flex', gap: '0.625rem', alignItems: 'flex-start' }}>
                  <div style={{ width: 16, height: 16, borderRadius: '50%', border: '1px solid rgba(255,255,255,0.1)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: 3 }}>
                    <div style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--accent-bright)' }} />
                  </div>
                  <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)', lineHeight: 1.55 }}>{step}</span>
                </li>
              ))}
            </ul>
            {analysis.guidance.food_advice && (
              <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)', lineHeight: 1.6, padding: '0.875rem 1rem', borderRadius: '0.75rem', background: 'rgba(0,229,150,0.04)', border: '1px solid rgba(0,229,150,0.12)', display: 'flex', gap: '0.625rem', alignItems: 'flex-start' }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="rgba(0,229,150,0.7)" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0, marginTop: 1 }}>
                  <path d="M2 22c1.25-1.25 2.5-2.5 3.75-3.75"/><path d="M22 2s-7 0-11 4c-2.5 2.5-3 6-3 6s3.5-.5 6-3c4-4 4-11 4-11z"/>
                </svg>
                {analysis.guidance.food_advice}
              </div>
            )}
          </motion.div>

          {/* Signal Analysis */}
          <motion.div className="glass" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.22, ease: E }}
            style={{ padding: 'clamp(1.25rem,3vw,2rem)', display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
            <div className="section-eyebrow">Signal Analysis</div>
            <ExplainabilityPanel analysis={analysis} bandColor={bandColor} />
            <AnimatePresence>
              {clinicalMode && (
                <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.3 }} style={{ overflow: 'hidden' }}>
                  <div style={{ paddingTop: '1rem', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
                    <ClinicalModePanel analysis={analysis} />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
            <motion.button className="btn btn-glass" whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
              style={{ marginTop: 'auto', width: '100%', padding: '0.75rem', fontSize: '0.7rem', borderRadius: '0.875rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
              onClick={onDownload}>
              <Download size={14} /> Export PDF Report
            </motion.button>
          </motion.div>
        </div>

        {/* Bottom 3: Handoff + Insight Pack + ML Proof */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px,1fr))', gap: '1.5rem' }}>

          {/* Handoff + Actions */}
          <motion.div className="glass" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.28, ease: E }}
            style={{ padding: 'clamp(1.25rem,3vw,2rem)', display: 'flex', flexDirection: 'column', gap: '1.25rem', borderLeft: '3px solid rgba(200,0,30,0.4)' }}>
            <div className="section-eyebrow">Handoff Summary</div>
            <div style={{ padding: '1.25rem', borderRadius: '0.875rem', background: 'rgba(0,0,0,0.35)', border: '1px solid rgba(255,255,255,0.05)', fontFamily: 'var(--mono)', fontSize: '0.68rem', color: 'var(--text-muted)', lineHeight: 1.9, flex: 1, maxHeight: 200, overflowY: 'auto' }}>
              {analysis.handoff_summary.share_text}
            </div>
            <motion.button className="btn btn-primary" whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
              style={{ width: '100%', padding: '0.8rem', fontSize: '0.72rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
              onClick={handleShare}>
              <Share2 size={14} /> Share with Provider
            </motion.button>
            <motion.button className="btn btn-glass" whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
              style={{ width: '100%', padding: '0.8rem', fontSize: '0.72rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem', border: '1px solid rgba(200,0,30,0.35)', color: 'var(--accent-bright)' }}
              onClick={() => setShowEmailModal(true)}>
              <Mail size={14} /> Send Report to Email
            </motion.button>
            <div style={{ padding: '1rem', borderRadius: '0.875rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
              <p style={{ fontSize: '0.65rem', color: 'var(--text-dim)', lineHeight: 1.65, fontStyle: 'italic', marginBottom: '0.875rem' }}>
                Not a diagnostic device. Confirm results with clinical blood testing.
              </p>
              <motion.button className="btn btn-glass" whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }}
                style={{ width: '100%', padding: '0.7rem', fontSize: '0.68rem', borderRadius: '0.75rem', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
                onClick={onReset}>
                <RefreshCw size={13} /> New Screening
              </motion.button>
            </div>
          </motion.div>

          {/* Insight Pack */}
          <motion.div className="glass" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35, ease: E }}
            style={{ padding: 'clamp(1.25rem,3vw,2rem)', display: 'flex', flexDirection: 'column', borderLeft: '3px solid rgba(255,165,0,0.4)' }}>
            <InsightPackPanel analysis={analysis} />
          </motion.div>

          {/* ML Proof */}
          <motion.div className="glass" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.42, ease: E }}
            style={{ padding: 'clamp(1.25rem,3vw,2rem)', display: 'flex', flexDirection: 'column', borderLeft: '3px solid rgba(0,194,255,0.4)' }}>
            <MLProofPanel />
          </motion.div>
        </div>

      </motion.div>
    </div>
  );
}
