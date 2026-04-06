import { Zap } from 'lucide-react';

interface RiskActionBadgeProps {
  band: string;
  runtimeUnavailable?: boolean;
  retakeRecommended?: boolean;
}

export function RiskActionBadge({
  band,
  runtimeUnavailable,
  retakeRecommended,
}: RiskActionBadgeProps) {
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
    ? { color: '#EF4444', bg: 'rgba(239,68,68,0.08)', border: 'rgba(239,68,68,0.25)', action: 'Consult a doctor immediately -- seek a CBC blood test within 24-48 hours.' }
    : band === 'moderate_risk'
    ? { color: '#F59E0B', bg: 'rgba(245,158,11,0.08)', border: 'rgba(245,158,11,0.25)', action: 'Consider scheduling a blood test soon. Monitor symptoms and maintain iron-rich diet.' }
    : { color: '#10B981', bg: 'rgba(16,185,129,0.08)', border: 'rgba(16,185,129,0.25)', action: 'Maintain a balanced diet. Rescreen in 3-6 months or if symptoms develop.' };
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
