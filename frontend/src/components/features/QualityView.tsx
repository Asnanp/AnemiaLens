import { CheckCircle, AlertTriangle, Info, RotateCcw, ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';
import type { QualityAssessment } from '../../types';

const E = [0.22, 1, 0.36, 1] as const;

interface QualityViewProps {
  quality: QualityAssessment;
  onContinue: () => void;
  onBack: () => void;
  loading: boolean;
}

function ScoreRing({ value, color, label }: { value: number; color: string; label: string }) {
  const r = 28;
  const circ = 2 * Math.PI * r;
  const dash = (value / 100) * circ;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.5rem' }}>
      <div style={{ position: 'relative', width: 72, height: 72 }}>
        <svg width="72" height="72" style={{ transform: 'rotate(-90deg)' }}>
          <circle cx="36" cy="36" r={r} fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="4" />
          <motion.circle
            cx="36"
            cy="36"
            r={r}
            fill="none"
            stroke={color}
            strokeWidth="4"
            strokeLinecap="round"
            strokeDasharray={circ}
            initial={{ strokeDashoffset: circ }}
            animate={{ strokeDashoffset: circ - dash }}
            transition={{ duration: 1.2, ease: E }}
            style={{ filter: `drop-shadow(0 0 6px ${color})` }}
          />
        </svg>
        <div
          style={{
            position: 'absolute',
            inset: 0,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            fontFamily: 'var(--mono)',
            fontWeight: 700,
            fontSize: '0.8rem',
            color,
          }}
        >
          {Math.round(value)}
        </div>
      </div>
      <span
        style={{
          fontSize: '0.58rem',
          fontFamily: 'var(--mono)',
          color: 'var(--text-dim)',
          letterSpacing: '0.1em',
          textTransform: 'uppercase',
          textAlign: 'center',
        }}
      >
        {label}
      </span>
    </div>
  );
}

export function QualityView({ quality, onContinue, onBack, loading }: QualityViewProps) {
  const blocking = quality.issues.filter((issue) => issue.severity === 'blocking').length;
  const passed = blocking === 0;
  const normalizeBlur = (value: number) => Math.max(0, Math.min(100, ((value - 55) / 165) * 100));
  const normalizeFraming = (value: number) => Math.max(0, Math.min(100, ((value - 0.75) / 1.1) * 100));
  const lightingCondition = quality.lighting_condition ?? 'unknown';
  const lightingConditionLabel = lightingCondition.replace(/_/g, ' ');

  const ringColor = (value: number) => (value >= 75 ? '#10B981' : value >= 40 ? '#F59E0B' : '#EF4444');

  const metrics = [
    { label: 'Sharpness', value: normalizeBlur(quality.blur_score) },
    { label: 'Lighting', value: (quality.lighting_score ?? 0) * 100 },
    { label: 'Framing', value: normalizeFraming(quality.framing_score) },
  ];

  const statusColor = passed ? '#10B981' : '#EF4444';
  const statusBg = passed ? 'rgba(16,185,129,0.07)' : 'rgba(239,68,68,0.07)';
  const statusBorder = passed ? 'rgba(16,185,129,0.25)' : 'rgba(239,68,68,0.25)';
  const statusGlow = passed ? 'rgba(16,185,129,0.1)' : 'rgba(239,68,68,0.12)';

  return (
    <div className="quality-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 300px', gap: '1.5rem', alignItems: 'start' }}>
      <motion.div
        className="glass"
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.55, ease: E }}
        style={{
          padding: '2.5rem',
          borderLeft: `3px solid ${statusColor}`,
          background: statusBg,
          boxShadow: `inset 0 1px 0 rgba(255,255,255,0.14), -4px 0 40px ${statusGlow}, 0 48px 100px rgba(0,0,0,0.6)`,
          position: 'relative',
          overflow: 'hidden',
        }}
      >
        <div
          style={{
            position: 'absolute',
            top: -60,
            right: -60,
            width: 240,
            height: 240,
            borderRadius: '50%',
            background: statusColor,
            filter: 'blur(100px)',
            opacity: 0.08,
            pointerEvents: 'none',
          }}
        />

        <div style={{ position: 'relative', zIndex: 1 }}>
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: '2rem', paddingBottom: '1.5rem', borderBottom: '1px solid rgba(255,255,255,0.07)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: 'spring', stiffness: 300, damping: 20, delay: 0.2 }}>
                {passed
                  ? <CheckCircle size={32} style={{ color: statusColor, filter: `drop-shadow(0 0 14px ${statusColor})` }} />
                  : <AlertTriangle size={32} style={{ color: statusColor, filter: `drop-shadow(0 0 14px ${statusColor})` }} />}
              </motion.div>
              <div>
                <h3 style={{ fontFamily: 'var(--serif)', fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em', lineHeight: 1 }}>Quality Assessment</h3>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginTop: '0.35rem' }}>
                  {passed ? 'Image passed all validation criteria - ready for analysis.' : 'Critical issues detected. Retake recommended for accuracy and stronger reliability.'}
                </p>
              </div>
            </div>
            <motion.span
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.3, duration: 0.4, ease: E }}
              style={{
                padding: '0.4rem 1.1rem',
                borderRadius: '99px',
                fontSize: '0.52rem',
                fontFamily: 'var(--mono)',
                fontWeight: 700,
                letterSpacing: '0.18em',
                textTransform: 'uppercase',
                background: statusBg,
                border: `1px solid ${statusBorder}`,
                color: statusColor,
                boxShadow: `0 0 16px ${statusGlow}`,
                whiteSpace: 'nowrap',
              }}
            >
              {passed ? 'READY' : 'ACTION REQUIRED'}
            </motion.span>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginBottom: '2rem', minHeight: 80 }}>
            {quality.issues.length === 0 ? (
              <motion.div
                initial={{ opacity: 0, scale: 0.97 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.25, duration: 0.5, ease: E }}
                style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', padding: '1.5rem 2rem', borderRadius: '1.25rem', background: 'rgba(16,185,129,0.05)', border: '1px solid rgba(16,185,129,0.15)' }}
              >
                <div style={{ width: 48, height: 48, borderRadius: '50%', background: 'rgba(16,185,129,0.12)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, boxShadow: '0 0 24px rgba(16,185,129,0.2)' }}>
                  <CheckCircle size={22} style={{ color: '#10B981' }} />
                </div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: '0.95rem', marginBottom: '0.2rem' }}>Perfect Condition</div>
                  <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>All quality metrics within optimal range.</p>
                </div>
              </motion.div>
            ) : quality.issues.map((issue, index) => (
              <motion.div
                key={`${issue.code}-${index}`}
                initial={{ opacity: 0, x: -16 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: index * 0.09, duration: 0.4, ease: E }}
                style={{
                  display: 'flex',
                  gap: '1rem',
                  alignItems: 'flex-start',
                  padding: '1.1rem 1.4rem',
                  borderRadius: '1rem',
                  background: issue.severity === 'blocking' ? 'rgba(239,68,68,0.06)' : 'rgba(245,158,11,0.06)',
                  border: issue.severity === 'blocking' ? '1px solid rgba(239,68,68,0.22)' : '1px solid rgba(245,158,11,0.22)',
                }}
              >
                <div
                  style={{
                    width: 30,
                    height: 30,
                    borderRadius: '0.6rem',
                    flexShrink: 0,
                    background: issue.severity === 'blocking' ? 'rgba(239,68,68,0.18)' : 'rgba(245,158,11,0.18)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: issue.severity === 'blocking' ? '#EF4444' : '#F59E0B',
                    fontFamily: 'var(--mono)',
                    fontWeight: 800,
                    fontSize: '0.9rem',
                  }}
                >
                  {issue.severity === 'blocking' ? '!' : '?'}
                </div>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.83rem', marginBottom: '0.2rem' }}>{issue.title}</div>
                  <p style={{ fontSize: '0.73rem', color: 'var(--text-muted)', lineHeight: 1.55 }}>{issue.message}</p>
                  {issue.severity === 'blocking' && (
                    <div style={{ marginTop: '0.5rem', fontSize: '0.65rem', color: '#F59E0B', fontFamily: 'var(--mono)', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
                      <span>{'->'}</span>
                      {issue.code === 'blur_detected' && 'Tip: Rest your phone on a surface and tap the eye to focus before shooting.'}
                      {issue.code === 'poor_lighting' && 'Tip: Move near a window or turn on room lights. Avoid direct flash.'}
                      {issue.code === 'bad_framing' && 'Tip: Pull down the lower eyelid gently and fill the frame with just the eye.'}
                      {issue.code === 'eye_not_visible' && 'Tip: Hold the phone 15-20 cm from the eye and keep the inner eyelid exposed.'}
                      {issue.code === 'resolution_too_low' && 'Tip: Move closer to the eye and ensure your camera is set to full resolution.'}
                    </div>
                  )}
                </div>
              </motion.div>
            ))}
          </div>

          <div style={{ display: 'flex', gap: '0.875rem' }}>
            <button className="btn btn-glass" style={{ flex: 1, gap: '0.5rem' }} onClick={onBack} disabled={loading}>
              <RotateCcw size={13} /> Retake Image
            </button>
            <button className="btn btn-primary" style={{ flex: 1, gap: '0.5rem', opacity: (!passed || loading) ? 0.4 : 1 }} onClick={onContinue} disabled={!passed || loading}>
              {loading ? 'Analyzing...' : <><ArrowRight size={13} /> Continue</>}
            </button>
          </div>
        </div>
      </motion.div>

      <motion.div
        className="glass"
        initial={{ opacity: 0, x: 24 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.55, delay: 0.12, ease: E }}
        style={{ padding: '2rem' }}
      >
        <div className="section-eyebrow" style={{ marginBottom: '1.75rem' }}>Validation Scores</div>

        <div style={{ display: 'flex', justifyContent: 'space-around', marginBottom: '2rem' }}>
          {metrics.map((metric, index) => (
            <motion.div key={metric.label} initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 + index * 0.1, duration: 0.4, ease: E }}>
              <ScoreRing value={metric.value} color={ringColor(metric.value)} label={metric.label} />
            </motion.div>
          ))}
        </div>

        <div style={{ padding: '1rem 1.1rem', borderRadius: '0.9rem', background: 'rgba(0,194,255,0.05)', border: '1px solid rgba(0,194,255,0.12)', marginBottom: '1.2rem' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', alignItems: 'center', marginBottom: '0.45rem', flexWrap: 'wrap' }}>
            <span style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', letterSpacing: '0.14em', textTransform: 'uppercase', color: 'rgba(0,194,255,0.72)' }}>
              Lighting Check
            </span>
            <span style={{ fontSize: '0.62rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.12em', color: ringColor((quality.lighting_score ?? 0) * 100) }}>
              {lightingConditionLabel}
            </span>
          </div>
          <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', lineHeight: 1.65, marginBottom: '0.8rem' }}>
            {quality.lighting_summary ?? 'Lighting analysis is unavailable for this scan.'}
          </p>
          <div style={{ display: 'grid', gap: '0.45rem', marginBottom: '0.8rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', fontSize: '0.66rem' }}>
              <span style={{ color: 'var(--text-dim)', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Condition</span>
              <span style={{ color: 'var(--text)', fontFamily: 'var(--mono)', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.08em' }}>{lightingConditionLabel}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: '0.75rem', fontSize: '0.66rem' }}>
              <span style={{ color: 'var(--text-dim)', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.1em' }}>Lighting score</span>
              <span style={{ color: ringColor((quality.lighting_score ?? 0) * 100), fontFamily: 'var(--mono)', fontWeight: 700 }}>{Math.round((quality.lighting_score ?? 0) * 100)}%</span>
            </div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.65rem' }}>
            {[
              { label: 'Glare Risk', value: (quality.glare_risk ?? 0) * 100, accent: '#F59E0B' },
              { label: 'Shadow Risk', value: (quality.shadow_risk ?? 0) * 100, accent: '#EF4444' },
            ].map((metric) => (
              <div key={metric.label} style={{ padding: '0.75rem 0.85rem', borderRadius: '0.75rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem', gap: '0.75rem' }}>
                  <span style={{ fontSize: '0.62rem', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>{metric.label}</span>
                  <span style={{ fontSize: '0.66rem', color: metric.accent, fontFamily: 'var(--mono)', fontWeight: 700 }}>{Math.round(metric.value)}%</span>
                </div>
                <div style={{ height: '4px', background: 'rgba(255,255,255,0.06)', borderRadius: '99px', overflow: 'hidden' }}>
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.max(0, Math.min(100, metric.value))}%` }}
                    transition={{ duration: 1.0, ease: E }}
                    style={{ height: '100%', borderRadius: '99px', background: `linear-gradient(90deg, ${metric.accent}66, ${metric.accent})` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        <div style={{ display: 'flex', flexDirection: 'column', gap: '1.1rem', paddingTop: '1.5rem', borderTop: '1px solid rgba(255,255,255,0.06)' }}>
          {metrics.map((metric, index) => (
            <div key={metric.label}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
                <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>{metric.label}</span>
                <span style={{ fontSize: '0.72rem', fontWeight: 700, fontFamily: 'var(--mono)', color: ringColor(metric.value) }}>{Math.round(metric.value)}%</span>
              </div>
              <div style={{ height: '3px', background: 'rgba(255,255,255,0.06)', borderRadius: '99px', overflow: 'hidden' }}>
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${metric.value}%` }}
                  transition={{ duration: 1.2, delay: 0.35 + index * 0.1, ease: E }}
                  style={{ height: '100%', borderRadius: '99px', background: `linear-gradient(90deg, ${ringColor(metric.value)}88, ${ringColor(metric.value)})`, boxShadow: `0 0 8px ${ringColor(metric.value)}66` }}
                />
              </div>
            </div>
          ))}
        </div>

        <div style={{ marginTop: '1.5rem', display: 'flex', gap: '0.6rem', alignItems: 'flex-start', padding: '0.875rem', borderRadius: '0.75rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
          <Info size={13} style={{ color: 'var(--accent-bright)', flexShrink: 0, marginTop: 1 }} />
          <p style={{ fontSize: '0.65rem', color: 'var(--text-dim)', lineHeight: 1.6, fontStyle: 'italic' }}>
            {lightingCondition === 'balanced'
              ? 'Capture quality is in a usable range. If you want a more defensible result, keep the eyelid steady and fully centered.'
              : 'Retaking under better lighting can significantly improve prediction reliability.'}
          </p>
        </div>
      </motion.div>
    </div>
  );
}
