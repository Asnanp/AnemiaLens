import { motion } from 'framer-motion';
import { CountUpMetric } from './CountUpMetric';

const E = [0.22, 1, 0.36, 1] as const;

export function RiskArc({ value, color }: { value: number; color: string }) {
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
        <span style={{ fontFamily: 'var(--mono)', fontWeight: 700, fontSize: '1.4rem', color, lineHeight: 1 }}>
          <CountUpMetric value={value} duration={1600} delay={500} postfix="%" />
        </span>
        <span style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', letterSpacing: '0.12em', textTransform: 'uppercase', marginTop: 4 }}>Risk Score</span>
      </div>
    </div>
  );
}
