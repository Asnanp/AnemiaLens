import { useEffect, useState, useRef } from 'react';
import { Download, Info, Share2, RefreshCw, Stethoscope, TrendingUp, TrendingDown, Minus, Clock, Camera, Mail, BarChart2, Zap, MessageSquare, Send, ChevronDown, Award } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { AnalyzeResponse, GuidanceChatMessage, InsightDriver, RuntimeStatusResponse } from '../../types';
import { getRuntimeStatus, sendEmailReport, sendGuidanceChat } from '../../api';
import { useAuth } from '../../hooks/useAuth';
import { MagneticButton } from '../MagneticButton';
import { SignalBar } from '../result/SignalBar';
import { useCountUp, getReliabilityStatus } from '../result/resultHelpers';
import { ConfidenceGauge } from '../result/ConfidenceGauge';
import { HbReferenceBand } from '../result/HbReferenceBand';

const E = [0.22, 1, 0.36, 1] as const;

/* ── Helpers ─────────────────────────────────────────────────────────── */

function CountUpMetric({ value, duration = 1600, delay = 200, postfix = '' }: { value: number; duration?: number; delay?: number; postfix?: string }) {
  const val = useCountUp(value, duration, delay);
  return <>{val}{postfix}</>;
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
        <span style={{ fontFamily: 'var(--mono)', fontWeight: 700, fontSize: '1.4rem', color, lineHeight: 1 }}><CountUpMetric value={value} duration={1600} delay={500} postfix="%" /></span>
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

function humanizeToken(value?: string | null, fallback = 'N/A'): string {
  if (!value) return fallback;
  return value.replace(/_/g, ' ');
}

function formatPercentMetric(value: number | null | undefined, digits = 1) {
  if (value === null || value === undefined) return '—';
  return `${(value * 100).toFixed(digits)}%`;
}

type SystemResultState = 'normal' | 'runtime_unavailable' | 'offline_symptom_only' | 'quality_blocked';

function getSystemResultState(analysis: AnalyzeResponse): SystemResultState {
  const qualityWarnings = analysis.decision_audit?.quality_warning_codes ?? [];
  const reviewFlags = analysis.decision_audit?.review_flags ?? [];

  if (analysis.prediction?.model_source === 'missing-model') return 'runtime_unavailable';
  if (!analysis.prediction && (qualityWarnings.includes('offline_mode') || reviewFlags.some((flag) => flag.toLowerCase().includes('offline')))) return 'offline_symptom_only';
  if (!analysis.prediction) return 'quality_blocked';
  return 'normal';
}

function getHemoglobinPresentation(analysis: AnalyzeResponse) {
  const value = analysis.prediction?.predicted_hemoglobin;
  if (value != null) {
    return { headline: `${value.toFixed(1)} g/dL`, detail: 'Hemoglobin estimate from scan', preview: `${value.toFixed(1)} g/dL` };
  }
  return { headline: 'Held back', detail: 'Scan quality insufficient for hemoglobin estimate', preview: 'Held back' };
}

/* ── Live AI Chat Panel ──────────────────────────────────────────────── */

function GuidanceChatPanel({ analysis }: { analysis: AnalyzeResponse }) {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState<GuidanceChatMessage[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

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
      setError(err instanceof Error ? err.message : 'Unable to reach the guidance assistant.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      className="glass"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.15, duration: 0.5, ease: E }}
      style={{
        padding: 'clamp(1.15rem, 2.5vw, 1.75rem)',
        borderLeft: '3px solid rgba(0,194,255,0.4)',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.85rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <MessageSquare size={15} style={{ color: 'rgba(0,194,255,0.8)' }} />
          <span style={{ fontSize: '0.65rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(0,194,255,0.8)', fontWeight: 700 }}>
            Live AI Guidance
          </span>
        </div>
        <span style={{ padding: '0.25rem 0.65rem', borderRadius: '999px', background: 'rgba(0,194,255,0.08)', border: '1px solid rgba(0,194,255,0.2)', fontSize: '0.5rem', fontFamily: 'var(--mono)', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'rgba(0,194,255,0.85)' }}>
          Context-aware
        </span>
      </div>

      <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', lineHeight: 1.6 }}>
        Ask about your result, what follow-up means, or whether a retake would help.
      </div>

      {messages.length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', maxHeight: 280, overflowY: 'auto', paddingRight: '0.2rem' }}>
          {messages.map((msg, i) => (
            <motion.div
              key={`${msg.role}-${i}`}
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              style={{
                padding: '0.75rem 0.9rem',
                borderRadius: '0.8rem',
                background: msg.role === 'assistant' ? 'rgba(0,194,255,0.06)' : 'rgba(255,255,255,0.03)',
                border: msg.role === 'assistant' ? '1px solid rgba(0,194,255,0.15)' : '1px solid rgba(255,255,255,0.06)',
              }}
            >
              <div style={{ fontSize: '0.5rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.1em', color: msg.role === 'assistant' ? 'rgba(0,194,255,0.8)' : 'var(--text-dim)', marginBottom: '0.3rem' }}>
                {msg.role === 'assistant' ? 'AI Assistant' : 'You'}
              </div>
              <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)', lineHeight: 1.65 }}>
                {msg.content}
              </div>
            </motion.div>
          ))}
          <div ref={messagesEndRef} />
        </div>
      )}

      <div style={{ display: 'flex', gap: '0.55rem', alignItems: 'stretch' }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              void handleSend();
            }
          }}
          placeholder="Ask about this screening result..."
          style={{
            flex: 1,
            minWidth: 0,
            padding: '0.8rem 1rem',
            borderRadius: '0.8rem',
            border: '1px solid rgba(255,255,255,0.1)',
            background: 'rgba(255,255,255,0.03)',
            color: 'var(--text)',
            fontSize: '0.8rem',
          }}
        />
        <MagneticButton
          className="btn btn-glass"
          onClick={() => void handleSend()}
          disabled={loading || !input.trim()}
          style={{
            padding: '0.8rem 1rem',
            borderRadius: '0.8rem',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.4rem',
            opacity: loading || !input.trim() ? 0.5 : 1,
          }}
        >
          <Send size={13} />
          {loading ? '...' : 'Ask'}
        </MagneticButton>
      </div>

      {error && (
        <div style={{ fontSize: '0.72rem', color: '#F59E0B', lineHeight: 1.55 }}>{error}</div>
      )}
    </motion.div>
  );
}

/* ── Signal Breakdown (Advanced) ─────────────────────────────────────── */

function ExplainabilityPanel({ analysis, bandColor }: { analysis: AnalyzeResponse; bandColor: string }) {
  const sb = analysis.clinical_brief?.signal_breakdown;
  if (!sb) return null;
  const imageContrib = sb.image_risk !== null ? (sb.image_risk ?? 0) * sb.image_weight : null;
  const symptomContrib = sb.symptom_score * sb.symptom_weight;
  const fused = sb.fused_score;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
      <div style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(0,194,255,0.7)' }}>
        Signal Contributions
      </div>
      {imageContrib !== null && <SignalBar label="Image Signal" value={imageContrib} color={bandColor} delay={0.2} />}
      <SignalBar label="Symptom Signal" value={symptomContrib} color="#F59E0B" delay={0.35} />
      <SignalBar label="Fused Score" value={fused} color={bandColor} delay={0.5} />
      <div style={{ display: 'flex', gap: '1.2rem', flexWrap: 'wrap' }}>
        {[
          { label: 'Image weight', val: `${Math.round(sb.image_weight * 100)}%` },
          { label: 'Symptom weight', val: `${Math.round(sb.symptom_weight * 100)}%` },
          { label: 'Burden', val: sb.symptom_burden },
        ].map(r => (
          <div key={r.label} style={{ fontSize: '0.62rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)' }}>
            {r.label}: <span style={{ color: 'var(--text-muted)', textTransform: 'capitalize' }}>{r.val}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Clinical Audit (Advanced) ───────────────────────────────────────── */

function ClinicalModePanel({ analysis }: { analysis: AnalyzeResponse }) {
  const audit = analysis.decision_audit;
  const meta = analysis.analysis_meta;
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.6rem' }}>
      <div style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(0,229,150,0.7)' }}>
        Clinical Audit
      </div>
      {[
        { label: 'Calibration', val: humanizeToken(audit.calibration_band) },
        { label: 'Threshold Margin', val: audit.threshold_margin !== null ? `${(audit.threshold_margin * 100).toFixed(1)}%` : 'N/A' },
        { label: 'Processing Path', val: humanizeToken(meta.processing_path) },
        { label: 'Safety Layers', val: meta.safety_layers?.join(', ') || 'None' },
      ].map(row => (
        <div key={row.label} style={{ display: 'flex', justifyContent: 'space-between', gap: '0.8rem', padding: '0.5rem 0.75rem', borderRadius: '0.5rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
          <span style={{ fontSize: '0.66rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)' }}>{row.label}</span>
          <span style={{ fontSize: '0.66rem', fontFamily: 'var(--mono)', color: 'var(--text-muted)', textTransform: 'capitalize' }}>{row.val}</span>
        </div>
      ))}
      {audit.review_flags && audit.review_flags.length > 0 && (
        <div style={{ padding: '0.65rem', borderRadius: '0.5rem', background: 'rgba(245,158,11,0.06)', border: '1px solid rgba(245,158,11,0.15)' }}>
          <div style={{ fontSize: '0.54rem', fontFamily: 'var(--mono)', color: 'rgba(245,158,11,0.8)', marginBottom: '0.3rem', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Review Flags</div>
          {audit.review_flags.map((f, i) => (
            <div key={i} style={{ fontSize: '0.66rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>• {f}</div>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── ML Proof (Advanced) ─────────────────────────────────────────────── */

function MLProofPanel() {
  const [runtimeStatus, setRuntimeStatus] = useState<RuntimeStatusResponse | null>(null);
  const [proofLoadFailed, setProofLoadFailed] = useState(false);

  useEffect(() => {
    let active = true;
    getRuntimeStatus()
      .then((status) => { if (active) { setRuntimeStatus(status); setProofLoadFailed(false); } })
      .catch(() => { if (active) setProofLoadFailed(true); });
    return () => { active = false; };
  }, []);

  const model = runtimeStatus?.model;
  const hasDeployedMetrics = model?.deployed_accuracy !== null && model?.deployed_accuracy !== undefined;
  const headlineAccuracy = hasDeployedMetrics ? model?.deployed_accuracy : model?.validation_accuracy;
  const headlineSubtitle = hasDeployedMetrics
    ? `deployed ROI screening${model?.deployed_validation_size ? ` · n=${model.deployed_validation_size}` : ''}`
    : model?.split_strategy ?? 'cross-validation';

  const metrics = hasDeployedMetrics
    ? [
        { label: 'Accuracy', value: formatPercentMetric(model?.deployed_accuracy), highlight: true },
        { label: 'Precision', value: formatPercentMetric(model?.deployed_precision) },
        { label: 'Recall', value: formatPercentMetric(model?.deployed_recall) },
        { label: 'F1', value: formatPercentMetric(model?.deployed_f1) },
      ]
    : [
        { label: 'Accuracy', value: formatPercentMetric(model?.validation_accuracy), highlight: true },
        { label: 'F1', value: formatPercentMetric(model?.validation_f1) },
        { label: 'Model', value: model?.primary_model ?? 'archive-fusion-v4' },
        { label: 'Dataset', value: model?.record_count ? `${model.record_count}` : '217' },
      ];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.45rem' }}>
        <BarChart2 size={13} style={{ color: 'rgba(0,194,255,0.8)' }} />
        <span style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(0,194,255,0.8)' }}>Model Performance</span>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '0.5rem' }}>
        {metrics.map(m => (
          <div key={m.label} style={{ padding: '0.7rem', borderRadius: '0.6rem', background: m.highlight ? 'rgba(0,194,255,0.07)' : 'rgba(255,255,255,0.02)', border: m.highlight ? '1px solid rgba(0,194,255,0.2)' : '1px solid rgba(255,255,255,0.05)' }}>
            <div style={{ fontSize: '0.5rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.2rem' }}>{m.label}</div>
            <div style={{ fontSize: '1rem', fontWeight: 700, fontFamily: 'var(--mono)', color: m.highlight ? 'rgba(0,194,255,0.95)' : 'var(--text)', lineHeight: 1 }}>{m.value}</div>
          </div>
        ))}
      </div>
      {headlineAccuracy != null && (
        <div style={{ fontSize: '0.66rem', color: 'var(--text-dim)', lineHeight: 1.6 }}>
          Headline: <span style={{ color: 'rgba(0,194,255,0.9)', fontWeight: 700 }}>{formatPercentMetric(headlineAccuracy)}</span> from {headlineSubtitle}
          {proofLoadFailed && ' · Status fetch failed'}
        </div>
      )}
    </div>
  );
}

/* ── Email Modal ─────────────────────────────────────────────────────── */

function EmailReportModal({ analysis, onClose }: { analysis: AnalyzeResponse; onClose: () => void }) {
  const { user } = useAuth();
  const [email, setEmail] = useState('');
  const [status, setStatus] = useState<'idle' | 'sending' | 'sent' | 'error'>('idle');
  const [errMsg, setErrMsg] = useState('');
  const [successMsg, setSuccessMsg] = useState('');
  const riskPct = Math.round((analysis.prediction?.anemia_risk ?? analysis.triage.score ?? 0) * 100);
  const hbPreview = getHemoglobinPresentation(analysis).preview;

  useEffect(() => {
    if (user?.email) setEmail(prev => prev || user.email);
  }, [user?.email]);

  const handleSend = async () => {
    const normalizedEmail = email.trim().toLowerCase();
    if (status === 'sending') return;
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(normalizedEmail)) { setErrMsg('Enter a valid email'); return; }
    setErrMsg('');
    setSuccessMsg('');
    setStatus('sending');
    try {
      const result = await sendEmailReport(
        normalizedEmail,
        analysis.handoff_summary.share_text,
        analysis.triage.label,
        analysis.prediction?.predicted_hemoglobin ?? null,
        analysis.prediction?.anemia_risk ?? analysis.triage.score ?? 0,
      );
      setSuccessMsg(result.message);
      setStatus('sent');
    } catch (e: unknown) {
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
        style={{ width: '100%', maxWidth: 480, borderRadius: '1.25rem', background: 'rgba(10,10,20,0.98)', border: '1px solid rgba(255,255,255,0.12)', padding: '1.75rem', display: 'flex', flexDirection: 'column', gap: '1rem', boxShadow: '0 40px 120px rgba(0,0,0,0.8)' }}>

        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <Mail size={18} style={{ color: 'var(--accent-bright)' }} />
            <span style={{ fontFamily: 'var(--serif)', fontSize: '1.1rem', fontWeight: 600 }}>Email Report</span>
          </div>
          <MagneticButton onClick={onClose} style={{ width: 32, height: 32, borderRadius: '0.7rem', border: '1px solid rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.03)', color: 'var(--text-dim)', cursor: 'pointer' }}>×</MagneticButton>
        </div>

        {status === 'sent' ? (
          <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
            <div style={{ width: 48, height: 48, borderRadius: '50%', background: 'rgba(16,185,129,0.12)', border: '1px solid rgba(16,185,129,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 1rem' }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="#10B981" strokeWidth="2.5" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>
            </div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: '0.85rem', color: 'rgba(16,185,129,0.9)' }}>{successMsg || `Sent to ${email.trim().toLowerCase()}`}</div>
            <div style={{ marginTop: '0.55rem', fontSize: '0.74rem', color: 'var(--text-dim)', lineHeight: 1.6 }}>
              If it does not appear shortly, check spam or promotions.
            </div>
            <MagneticButton onClick={onClose} style={{ marginTop: '1rem', padding: '0.7rem 1.5rem', borderRadius: '0.8rem', background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)', color: 'var(--text)', fontSize: '0.8rem', cursor: 'pointer' }}>Done</MagneticButton>
          </div>
        ) : (
          <>
            <div style={{ display: 'flex', gap: '0.75rem' }}>
              <div style={{ flex: 1, padding: '0.75rem', borderRadius: '0.7rem', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                <div style={{ fontSize: '0.5rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.3rem' }}>Risk</div>
                <div style={{ fontSize: '1rem', fontWeight: 700 }}>{riskPct}%</div>
              </div>
              <div style={{ flex: 1, padding: '0.75rem', borderRadius: '0.7rem', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                <div style={{ fontSize: '0.5rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.1em', marginBottom: '0.3rem' }}>Hemoglobin</div>
                <div style={{ fontSize: '1rem', fontWeight: 700 }}>{hbPreview}</div>
              </div>
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.4rem' }}>
              <label style={{ fontSize: '0.65rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Send to</label>
              <input type="email" placeholder="name@example.com" value={email}
                autoFocus
                onKeyDown={e => {
                  if (e.key === 'Enter') {
                    e.preventDefault();
                    void handleSend();
                  }
                }}
                onChange={e => {
                  setEmail(e.target.value);
                  setErrMsg('');
                  if (status !== 'sending') setStatus('idle');
                }}
                style={{ width: '100%', padding: '0.8rem 1rem', borderRadius: '0.8rem', fontSize: '0.85rem', background: 'rgba(255,255,255,0.04)', border: errMsg ? '1px solid rgba(239,68,68,0.5)' : '1px solid rgba(255,255,255,0.1)', color: 'var(--text)', outline: 'none', boxSizing: 'border-box' }}
              />
              {!errMsg && (
                <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', lineHeight: 1.5 }}>
                  We&apos;ll send the screening summary to this address.
                </div>
              )}
              {errMsg && <div style={{ fontSize: '0.7rem', color: '#EF4444' }}>{errMsg}</div>}
            </div>
            <div style={{ display: 'flex', gap: '0.65rem' }}>
              <MagneticButton onClick={onClose} style={{ flex: 1, padding: '0.75rem', borderRadius: '0.8rem', background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)', color: 'var(--text-dim)', fontSize: '0.78rem', cursor: 'pointer' }}>Cancel</MagneticButton>
              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.97 }} onClick={() => void handleSend()} disabled={status === 'sending' || !email.trim()}
                style={{ flex: 2, padding: '0.75rem', borderRadius: '0.8rem', background: 'linear-gradient(135deg, #C8001E, #E8294A)', border: 'none', color: '#fff', fontSize: '0.78rem', fontWeight: 700, cursor: status === 'sending' || !email.trim() ? 'not-allowed' : 'pointer', opacity: status === 'sending' || !email.trim() ? 0.6 : 1, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem' }}>
                <Mail size={13} />{status === 'sending' ? 'Sending…' : 'Send Report'}
              </motion.button>
            </div>
          </>
        )}
      </motion.div>
    </motion.div>
  );
}

/* ══════════════════════════════════════════════════════════════════════
   MAIN RESULT VIEW
   ══════════════════════════════════════════════════════════════════════ */

interface ResultViewProps {
  analysis: AnalyzeResponse;
  previewUrl?: string | null;
  onReset: () => void;
  onDownload: () => void;
  onOpenAuth?: (mode?: 'login' | 'register') => void;
}

const RISK_IMAGES: Record<string, string> = {
  low_risk: '/demo-cases/low-risk-demo.jpg',
  moderate_risk: '/demo-cases/moderate-risk-demo.jpg',
  high_concern: '/demo-cases/high-concern-demo.jpg',
  uncertain_retake_needed: '/demo-cases/low-risk-demo.jpg',
};

export function ResultView({ analysis, previewUrl, onReset, onDownload, onOpenAuth }: ResultViewProps) {
  const { isAuthenticated } = useAuth();
  const systemState = getSystemResultState(analysis);
  const runtimeUnavailable = systemState !== 'normal';
  const isHigh = analysis.triage.band === 'high_concern';
  const isModerate = analysis.triage.band === 'moderate_risk';
  const bandColor = isHigh ? '#EF4444' : isModerate ? '#F59E0B' : '#10B981';
  const bandBg = isHigh ? 'rgba(239,68,68,0.07)' : isModerate ? 'rgba(245,158,11,0.07)' : 'rgba(16,185,129,0.07)';
  const bandBorder = isHigh ? 'rgba(239,68,68,0.3)' : isModerate ? 'rgba(245,158,11,0.3)' : 'rgba(16,185,129,0.3)';

  const hbValue = analysis.prediction?.predicted_hemoglobin ?? null;
  const hasHbEstimate = hbValue !== null;
  const hbPresentation = getHemoglobinPresentation(analysis);
  const hbRaw = hbValue ?? 0;
  const risk = Math.round((analysis.prediction?.anemia_risk ?? analysis.triage.score ?? 0) * 100);
  const hbAnim = useCountUp(hbRaw, 1600, 200);
  const reliability = getReliabilityStatus(analysis);

  const [flashDone, setFlashDone] = useState(false);
  const [revealed, setRevealed] = useState(false);
  const [shareToast, setShareToast] = useState<string | null>(null);
  const [showEmailModal, setShowEmailModal] = useState(false);

  const retakeRecommended =
    analysis.triage.band === 'uncertain_retake_needed'
    || (analysis.prediction?.confidence ?? 0) < 0.55
    || analysis.quality.issues.some((issue) => issue.severity === 'warning');

  const riskImageUrl = RISK_IMAGES[analysis.triage.band] || RISK_IMAGES.low_risk;

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
      setShareToast('Share text ready');
    }
    setTimeout(() => setShareToast(null), 3000);
  };

  /* ── Blocked / Unavailable State ── */
  if (runtimeUnavailable) {
    const copy = systemState === 'offline_symptom_only'
      ? { badge: 'Offline — symptom only', title: 'Image was not analyzed.', detail: 'Reconnect and retake with an eyelid image for a model-backed result.', action: 'Reconnect & retake', accent: '#F59E0B' }
      : systemState === 'quality_blocked'
        ? { badge: 'Retake required', title: 'Image did not pass quality check.', detail: 'A cleaner image with better eye visibility is needed.', action: 'Retake image', accent: '#F59E0B' }
        : { badge: 'Model unavailable', title: 'Scan could not be completed.', detail: 'Retry once the screening model reconnects.', action: 'Retry screening', accent: '#38BDF8' };

    return (
      <motion.div className="glass-premium bg-noise" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45, ease: E }}
        style={{ padding: 'clamp(1.25rem, 3vw, 2rem)', border: `1px solid ${copy.accent}33`, borderLeft: `4px solid ${copy.accent}`, background: 'linear-gradient(180deg, rgba(18,18,28,0.95), rgba(18,18,28,0.85))' }}>
        <div style={{ display: 'grid', gap: '1.25rem' }}>
          <span style={{ padding: '0.4rem 1rem', borderRadius: '99px', fontSize: '0.6rem', fontFamily: 'var(--mono)', fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', background: `${copy.accent}14`, border: `1px solid ${copy.accent}33`, color: copy.accent, width: 'fit-content' }}>
            {copy.badge}
          </span>
          <div style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(1.6rem, 3.5vw, 2.6rem)', fontWeight: 600, lineHeight: 1.1, letterSpacing: '-0.02em', color: 'var(--text)' }}>
            {copy.title}
          </div>
          <p style={{ fontSize: '0.88rem', color: 'var(--text-muted)', lineHeight: 1.7, maxWidth: 580 }}>{copy.detail}</p>
          <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
            <MagneticButton className="btn btn-premium-primary" onClick={onReset}><RefreshCw size={14} style={{ marginRight: 6 }} /> {copy.action}</MagneticButton>
            <MagneticButton className="btn btn-premium-glass" onClick={onDownload}><Download size={14} style={{ marginRight: 6 }} /> Export report</MagneticButton>
          </div>
          <div style={{ padding: '0.85rem 1.15rem', borderRadius: '0.85rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', fontSize: '0.75rem', color: 'var(--text-dim)', lineHeight: 1.6 }}>
            This is a system state, not a medical result. Confirm any concern with a blood test.
          </div>
        </div>
      </motion.div>
    );
  }

  /* ── Normal Result ── */
  return (
    <div style={{ position: 'relative' }} className="bg-noise">

      {/* Emergency alert for high concern */}
      <AnimatePresence>
        {isHigh && revealed && (
          <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
            className="glass-premium"
            style={{ marginBottom: '1.5rem', padding: '1.25rem 1.5rem', border: '1px solid rgba(239,68,68,0.4)', borderLeft: '4px solid #EF4444', background: 'rgba(239,68,68,0.07)', display: 'flex', alignItems: 'center', gap: '1rem', boxShadow: '0 0 50px rgba(239,68,68,0.15)' }}>
            <motion.div animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 1.5, repeat: Infinity }}
              style={{ width: 12, height: 12, borderRadius: '50%', background: '#EF4444', flexShrink: 0, boxShadow: '0 0 16px #EF4444' }} />
            <div>
              <div style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', fontWeight: 700, letterSpacing: '0.12em', textTransform: 'uppercase', color: '#EF4444', marginBottom: '0.2rem' }}>Urgent Clinical Recommendation</div>
              <p style={{ fontSize: '0.82rem', color: '#FCA5A5', lineHeight: 1.5, margin: 0 }}>Visit a clinical laboratory or consulting practitioner within 24–48 hours to request a standard Complete Blood Count (CBC) test.</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Share toast */}
      <AnimatePresence>
        {shareToast && (
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: 20 }}
            className="glass-premium"
            style={{ position: 'fixed', bottom: '2rem', left: '50%', transform: 'translateX(-50%)', zIndex: 9999, padding: '0.8rem 1.5rem', border: '1px solid rgba(255,255,255,0.12)', fontFamily: 'var(--mono)', fontSize: '0.78rem', color: 'var(--text)', boxShadow: '0 12px 50px rgba(0,0,0,0.6)', whiteSpace: 'nowrap' }}>
            ✓ {shareToast}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Email modal */}
      <AnimatePresence>
        {showEmailModal && <EmailReportModal analysis={analysis} onClose={() => setShowEmailModal(false)} />}
      </AnimatePresence>

      {/* Flash overlay for high concern */}
      <AnimatePresence>
        {!flashDone && isHigh && (
          <>
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: [0, 0.5, 0] }} exit={{ opacity: 0 }}
              transition={{ duration: 0.6, times: [0, 0.3, 1] }}
              style={{ position: 'fixed', inset: 0, zIndex: 9000, background: bandColor, pointerEvents: 'none' }} />
            <motion.div initial={{ opacity: 0, scale: 0.7 }} animate={{ opacity: [0, 1, 1, 0], scale: [0.7, 1.05, 1, 0.9] }}
              transition={{ duration: 0.6, times: [0, 0.25, 0.6, 1] }}
              style={{ position: 'fixed', inset: 0, zIndex: 9001, display: 'flex', alignItems: 'center', justifyContent: 'center', pointerEvents: 'none' }}>
              <div style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(3rem,10vw,7rem)', fontWeight: 700, color: '#fff', textShadow: `0 0 60px ${bandColor}`, letterSpacing: '-0.04em' }}>
                {analysis.triage.label}
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* ── MAIN CONTENT ── */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: revealed ? 1 : 0 }} transition={{ duration: 0.4 }}
        style={{ display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

        {/* ══ HEADER META SUMMARY ROW ══ */}
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap', padding: '0.25rem 0.5rem' }}>
          <div>
            <div style={{ fontFamily: 'var(--mono)', fontSize: '0.6rem', color: 'var(--text-dim)', letterSpacing: '0.15em', textTransform: 'uppercase' }}>Screening Audit</div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: 4 }}>
              <span className="text-gold" style={{ fontFamily: 'var(--mono)' }}>ID: AL-{analysis.analysis_meta.request_id.slice(0, 8)}</span>
              <span>•</span>
              <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}><Award size={13} style={{ color: bandColor }} /> Calibrated Result</span>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.65rem' }}>
            <MagneticButton className="btn btn-premium-glass" style={{ padding: '0.6rem 1.2rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: 6 }} onClick={handleShare}>
              <Share2 size={13} /> Share
            </MagneticButton>
            <MagneticButton className="btn btn-premium-glass" style={{ padding: '0.6rem 1.2rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: 6 }} onClick={() => setShowEmailModal(true)}>
              <Mail size={13} /> Email
            </MagneticButton>
            <MagneticButton className="btn btn-premium-glass" style={{ padding: '0.6rem 1.2rem', fontSize: '0.75rem', display: 'flex', alignItems: 'center', gap: 6 }} onClick={onDownload}>
              <Download size={13} /> PDF Report
            </MagneticButton>
          </div>
        </div>

        {/* ══ HERO OVERVIEW CARD ══ */}
        <motion.div
          className="glass-premium"
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: E }}
          style={{
            padding: '0',
            border: `1px solid ${bandBorder}`,
            borderLeft: `4px solid ${bandColor}`,
            background: `linear-gradient(180deg, rgba(18,18,28,0.95), rgba(18,18,28,0.85)), ${bandBg}`,
            boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.06), 0 24px 64px rgba(0,0,0,0.35)',
            position: 'relative',
            overflow: 'hidden',
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          }}
        >
          {/* Eye Scan HUD Column */}
          <div style={{ position: 'relative', height: '100%', minHeight: 340, background: '#030308', overflow: 'hidden' }}>
            <img 
              src={previewUrl || riskImageUrl} 
              alt={analysis.triage.label}
              style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: 0.8 }}
            />

            {/* Cyan target-lock crop box */}
            {analysis.roi_preview?.roi_box && analysis.roi_preview.frame_width && analysis.roi_preview.frame_height && (
              <div
                style={{
                  position: 'absolute',
                  border: '2px solid rgba(0, 194, 255, 0.95)',
                  boxShadow: '0 0 0 1px rgba(0,0,0,0.45), 0 0 24px rgba(0, 194, 255, 0.65)',
                  borderRadius: '0.4rem',
                  background: 'rgba(0, 194, 255, 0.06)',
                  pointerEvents: 'none',
                  left: `${(analysis.roi_preview.roi_box.x / analysis.roi_preview.frame_width) * 100}%`,
                  top: `${(analysis.roi_preview.roi_box.y / analysis.roi_preview.frame_height) * 100}%`,
                  width: `${(analysis.roi_preview.roi_box.width / analysis.roi_preview.frame_width) * 100}%`,
                  height: `${(analysis.roi_preview.roi_box.height / analysis.roi_preview.frame_height) * 100}%`,
                }}
              >
                {/* target indicator label */}
                <div style={{
                  position: 'absolute',
                  top: '-1.5rem',
                  left: '0',
                  background: 'rgba(0, 194, 255, 0.9)',
                  color: '#04040A',
                  fontFamily: 'var(--mono)',
                  fontSize: '0.52rem',
                  fontWeight: 800,
                  padding: '0.15rem 0.45rem',
                  borderRadius: '0.2rem',
                  whiteSpace: 'nowrap',
                  textTransform: 'uppercase',
                  letterSpacing: '0.08em',
                  boxShadow: '0 2px 8px rgba(0,0,0,0.3)'
                }}>
                  CONJUNCTIVA TARGET LOCKED
                </div>
              </div>
            )}

            {/* HUD scan overlay lines & corners */}
            <div style={{ position: 'absolute', top: 16, left: 16, width: 20, height: 20, borderTop: '2px solid rgba(0, 194, 255, 0.65)', borderLeft: '2px solid rgba(0, 194, 255, 0.65)' }} />
            <div style={{ position: 'absolute', top: 16, right: 16, width: 20, height: 20, borderTop: '2px solid rgba(0, 194, 255, 0.65)', borderRight: '2px solid rgba(0, 194, 255, 0.65)' }} />
            <div style={{ position: 'absolute', bottom: 16, left: 16, width: 20, height: 20, borderBottom: '2px solid rgba(0, 194, 255, 0.65)', borderLeft: '2px solid rgba(0, 194, 255, 0.65)' }} />
            <div style={{ position: 'absolute', bottom: 16, right: 16, width: 20, height: 20, borderBottom: '2px solid rgba(0, 194, 255, 0.65)', borderRight: '2px solid rgba(0, 194, 255, 0.65)' }} />

            {/* Laser scanning bar */}
            <motion.div
              animate={{ top: ['4%', '96%', '4%'] }}
              transition={{ duration: 4.5, repeat: Infinity, ease: 'linear' }}
              style={{
                position: 'absolute',
                left: 0,
                width: '100%',
                height: '2px',
                background: 'linear-gradient(90deg, transparent, rgba(0, 194, 255, 0.8), transparent)',
                boxShadow: '0 0 10px rgba(0, 194, 255, 0.85)',
                zIndex: 2,
                pointerEvents: 'none',
              }}
            />

            <div style={{ position: 'absolute', inset: 0, background: `linear-gradient(to right, transparent 50%, rgba(18,18,28,0.96) 98%)` }} className="hud-overlay" />
          </div>

          {/* Diagnostic Info Column */}
          <div style={{ padding: 'clamp(1.5rem, 3.5vw, 2.5rem)', position: 'relative', zIndex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
            {/* Anemia Risk Band badge */}
            <span style={{ display: 'inline-block', padding: '0.4rem 1.15rem', borderRadius: '99px', fontSize: '0.62rem', fontFamily: 'var(--mono)', fontWeight: 800, letterSpacing: '0.12em', textTransform: 'uppercase', background: bandBg, border: `1px solid ${bandBorder}`, color: bandColor, marginBottom: '1.25rem', width: 'fit-content' }}>
              {analysis.triage.label}
            </span>

            {/* Metrics side-by-side */}
            <div style={{ display: 'flex', alignItems: 'center', gap: 'clamp(1.25rem, 3vw, 2.5rem)', flexWrap: 'wrap', marginBottom: '1.25rem' }}>
              {/* Hemoglobin estimation */}
              <div>
                {hasHbEstimate ? (
                  <>
                    <div style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(2.8rem, 6vw, 4.5rem)', fontWeight: 300, lineHeight: 1, letterSpacing: '-0.04em', color: bandColor, textShadow: `0 0 40px ${bandColor}20` }}>
                      {hbAnim.toFixed(1)}
                    </div>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', color: 'var(--text-dim)', letterSpacing: '0.18em', textTransform: 'uppercase', marginTop: '0.4rem' }}>g/dL Hemoglobin</div>
                  </>
                ) : (
                  <>
                    <div style={{ fontFamily: 'var(--mono)', fontSize: '0.6rem', color: bandColor, letterSpacing: '0.15em', textTransform: 'uppercase', marginBottom: '0.5rem' }}>Hemoglobin</div>
                    <div style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(1.6rem, 3.5vw, 2.4rem)', fontWeight: 600, lineHeight: 1.1, color: 'var(--text)' }}>{hbPresentation.headline}</div>
                    <div style={{ fontSize: '0.76rem', color: 'var(--text-dim)', lineHeight: 1.5, marginTop: '0.4rem', maxWidth: 280 }}>{hbPresentation.detail}</div>
                  </>
                )}
              </div>

              <div style={{ width: 1, height: 80, background: 'rgba(255,255,255,0.06)', flexShrink: 0 }} className="result-divider" />
              <RiskArc value={risk} color={bandColor} />
            </div>

            {/* Summary */}
            <p style={{ fontSize: '0.92rem', color: 'var(--text-muted)', lineHeight: 1.7, maxWidth: 700, marginBottom: '1.25rem' }}>
              {analysis.triage.summary}
            </p>

            {/* Disclaimer */}
            <div style={{ display: 'flex', gap: '0.75rem', alignItems: 'flex-start', padding: '0.85rem 1.15rem', borderRadius: '0.85rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
              <Info size={14} style={{ color: 'var(--accent-bright)', flexShrink: 0, marginTop: 2 }} />
              <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)', lineHeight: 1.6, margin: 0 }}>
                Screening aid only — not a clinical diagnosis. Confirm any critical values with standard lab hematology. {analysis.triage.disclaimer}
              </p>
            </div>
          </div>
        </motion.div>

        {/* ══ DIAGNOSTIC BENTO GRID ══ */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1.25rem' }} className="bento-grid-results">
          
          {/* Bento Card A: WHO Hemoglobin Distribution */}
          <motion.div
            className="glass-premium bg-noise"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.5, ease: E }}
            style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', display: 'flex', flexDirection: 'column', gap: '1rem' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Stethoscope size={15} style={{ color: 'var(--accent-bright)' }} />
              <span style={{ fontSize: '0.62rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-dim)', fontWeight: 700 }}>
                Hemoglobin Distribution
              </span>
            </div>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <HbReferenceBand hb={hbRaw} />
            </div>
            <div style={{ fontSize: '0.74rem', color: 'var(--text-dim)', lineHeight: 1.65, borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '0.75rem' }}>
              Maps the non-invasive hemoglobin estimation against standard WHO thresholds. Mild concern borders at 12.0 g/dL.
            </div>
          </motion.div>

          {/* Bento Card B: AI Signal Fusion */}
          <motion.div
            className="glass-premium bg-noise"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.18, duration: 0.5, ease: E }}
            style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', display: 'flex', flexDirection: 'column', gap: '1rem' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <Zap size={15} style={{ color: '#F59E0B' }} />
              <span style={{ fontSize: '0.62rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-dim)', fontWeight: 700 }}>
                AI Signal Fusion
              </span>
            </div>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <ExplainabilityPanel analysis={analysis} bandColor={bandColor} />
            </div>
            <div style={{ fontSize: '0.74rem', color: 'var(--text-dim)', lineHeight: 1.65, borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '0.75rem' }}>
              Breaks down the weighting between pixel-level micro-vascular eyelid signatures and systemic symptom scoring.
            </div>
          </motion.div>

          {/* Bento Card C: Scan Confidence & Trust */}
          <motion.div
            className="glass-premium bg-noise"
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.26, duration: 0.5, ease: E }}
            style={{ padding: '1.5rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', display: 'flex', flexDirection: 'column', gap: '1rem' }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <BarChart2 size={15} style={{ color: 'rgba(0,194,255,0.8)' }} />
              <span style={{ fontSize: '0.62rem', fontFamily: 'var(--mono)', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-dim)', fontWeight: 700 }}>
                Scan Confidence & Trust
              </span>
            </div>
            <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center' }}>
              <ConfidenceGauge analysis={analysis} color={bandColor} />
            </div>
            <div style={{ fontSize: '0.74rem', color: 'var(--text-dim)', lineHeight: 1.65, borderTop: '1px solid rgba(255,255,255,0.05)', paddingTop: '0.75rem' }}>
              Indicates standard model confidence combined with a spatial capture quality index (lighting, blur, frame coverage).
            </div>
          </motion.div>

        </div>

        {/* ══ AI CARE GUIDANCE CHAT ══ */}
        <GuidanceChatPanel analysis={analysis} />

        {/* ══ CLINICAL AUDIT & ACTIONS (Collapsible) ══ */}
        <motion.div
          className="glass-premium"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.32, ease: E }}
          style={{ padding: '1.15rem 1.5rem', display: 'flex', flexDirection: 'column', gap: '0.85rem' }}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.85rem' }}>
            
            {/* Auth prompt for non-authenticated */}
            {!isAuthenticated && onOpenAuth && (
              <div style={{ padding: '1rem 1.25rem', borderRadius: '1rem', background: 'rgba(200,0,30,0.04)', border: '1px solid rgba(200,0,30,0.15)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '0.75rem', flexWrap: 'wrap' }}>
                <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.5 }}>
                  Would you like to securely archive this screening to your patient health records?
                </div>
                <div style={{ display: 'flex', gap: '0.65rem' }}>
                  <MagneticButton className="btn btn-premium-glass" style={{ padding: '0.55rem 1rem', fontSize: '0.72rem' }} onClick={() => onOpenAuth('login')}>Sign In</MagneticButton>
                  <MagneticButton className="btn btn-premium-primary" style={{ padding: '0.55rem 1.15rem', fontSize: '0.72rem' }} onClick={() => onOpenAuth('register')}>Sign Up</MagneticButton>
                </div>
              </div>
            )}

            {/* Quick Context & Care next steps */}
            <div style={{ padding: '1.25rem', borderRadius: '1rem', background: 'rgba(0,194,255,0.03)', border: '1px solid rgba(0,194,255,0.1)' }}>
              <div style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'rgba(0,194,255,0.85)', marginBottom: '0.65rem', fontWeight: 700 }}>
                Suggested Action Guidelines
              </div>
              <div style={{ fontSize: '0.88rem', color: 'var(--text-muted)', lineHeight: 1.7, marginBottom: '0.85rem' }}>
                {analysis.guidance.explanation}
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: '0.75rem', marginBottom: '0.75rem' }}>
                {analysis.guidance.next_steps.slice(0, 3).map((step, i) => (
                  <div key={i} style={{ display: 'flex', gap: '0.65rem', alignItems: 'flex-start', fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.5, padding: '0.65rem 0.85rem', borderRadius: '0.75rem', background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.04)' }}>
                    <span style={{ fontFamily: 'var(--mono)', fontSize: '0.72rem', color: bandColor, fontWeight: 800 }}>{i + 1}.</span>
                    <span>{step}</span>
                  </div>
                ))}
              </div>
              {analysis.guidance.food_advice && (
                <div style={{ fontSize: '0.8rem', color: 'var(--text-dim)', lineHeight: 1.6, padding: '0.75rem 1rem', borderRadius: '0.75rem', background: 'rgba(0,229,150,0.04)', border: '1px solid rgba(0,229,150,0.1)' }}>
                  💡 <span style={{ color: 'rgba(0,229,150,0.95)', fontWeight: 700 }}>Dietary Note:</span> {analysis.guidance.food_advice}
                </div>
              )}
            </div>

            {/* Collapsible Clinical Logs & Model Proof */}
            <div style={{ borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '0.85rem' }}>
              <ChevronDownTrigger title="Clinical Processing Logs" label="Inspect raw decision paths, active calibrations, and deployment benchmarks.">
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem', paddingTop: '0.75rem' }}>
                  <div style={{ padding: '1rem', borderRadius: '0.85rem', background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <ClinicalModePanel analysis={analysis} />
                  </div>
                  <div style={{ padding: '1rem', borderRadius: '0.85rem', background: 'rgba(255,255,255,0.01)', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <MLProofPanel />
                  </div>
                </div>
              </ChevronDownTrigger>
            </div>

            {/* Bottom Actions Row */}
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', borderTop: '1px solid rgba(255,255,255,0.06)', paddingTop: '1rem', flexWrap: 'wrap' }}>
              <MagneticButton className="btn btn-premium-glass" style={{ padding: '0.8rem 1.75rem' }} onClick={onReset}>
                <RefreshCw size={13} style={{ marginRight: 6 }} /> {retakeRecommended ? 'Retake Eyelid Scan' : 'New Screening Scan'}
              </MagneticButton>
            </div>

          </div>
        </motion.div>

      </motion.div>
    </div>
  );
}

// Collapsible helper component for details
function ChevronDownTrigger({ title, label, children }: { title: string; label: string; children: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <MagneticButton
        onClick={() => setOpen(c => !c)}
        style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem', width: '100%', background: 'transparent', border: 'none', color: 'inherit', cursor: 'pointer', padding: 0, textAlign: 'left' }}
      >
        <div>
          <span style={{ fontSize: '0.58rem', fontFamily: 'var(--mono)', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-dim)' }}>{title}</span>
          <div style={{ marginTop: '0.2rem', fontSize: '0.76rem', color: 'var(--text-dim)', lineHeight: 1.4 }}>{label}</div>
        </div>
        <motion.div animate={{ rotate: open ? 180 : 0 }} transition={{ duration: 0.25 }}>
          <ChevronDown size={15} style={{ color: 'var(--text-dim)' }} />
        </motion.div>
      </MagneticButton>
      <AnimatePresence>
        {open && (
          <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.25 }} style={{ overflow: 'hidden' }}>
            {children}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
