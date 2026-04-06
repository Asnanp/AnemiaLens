import { motion } from 'framer-motion';

const EASE = [0.22, 1, 0.36, 1] as const;

interface SignalBarProps {
  label: string;
  value: number;
  color: string;
  delay?: number;
}

export function SignalBar({ label, value, color, delay = 0 }: SignalBarProps) {
  const pct = Math.round(Math.min(Math.max(value, 0), 1) * 100);
  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.4rem' }}>
        <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)', fontFamily: 'var(--mono)' }}>{label}</span>
        <span style={{ fontSize: '0.75rem', fontWeight: 700, fontFamily: 'var(--mono)', color }}>{pct}%</span>
      </div>
      <div style={{ height: 7, borderRadius: 99, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
        <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }}
          transition={{ duration: 1.2, delay, ease: EASE }}
          style={{ height: '100%', borderRadius: 99, background: `linear-gradient(90deg, var(--crimson), ${color})`, boxShadow: `0 0 8px ${color}60` }}
        />
      </div>
    </div>
  );
}
