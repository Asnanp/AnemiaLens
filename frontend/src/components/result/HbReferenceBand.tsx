import { motion } from 'framer-motion';

const EASE = [0.22, 1, 0.36, 1] as const;

const WHO_BANDS = [
  { label: 'Severe', max: 8, color: '#EF4444', bg: 'rgba(239,68,68,0.15)' },
  { label: 'Moderate', max: 11, color: '#F59E0B', bg: 'rgba(245,158,11,0.12)' },
  { label: 'Mild', max: 12, color: '#FBBF24', bg: 'rgba(251,191,36,0.1)' },
  { label: 'Normal', max: 18, color: '#10B981', bg: 'rgba(16,185,129,0.1)' },
];

interface HbReferenceBandProps {
  hb: number;
}

export function HbReferenceBand({ hb }: HbReferenceBandProps) {
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
        <span style={{ fontSize: '0.7rem', fontFamily: 'var(--mono)', color: activeBand.color, fontWeight: 700 }}>{activeBand.label} {hb < 12 ? '\u26A0' : '\u2713'}</span>
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
        <motion.div initial={{ left: '0%' }} animate={{ left: `${markerPct}%` }} transition={{ duration: 1.4, delay: 0.4, ease: EASE }}
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
