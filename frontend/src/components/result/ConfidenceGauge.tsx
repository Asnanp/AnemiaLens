import { motion } from 'framer-motion';
import type { AnalyzeResponse } from '../../types';
import { getReliabilityStatus } from './resultHelpers';

const EASE = [0.22, 1, 0.36, 1] as const;

interface ConfidenceGaugeProps {
  analysis: AnalyzeResponse;
  color: string;
}

export function ConfidenceGauge({ analysis, color }: ConfidenceGaugeProps) {
  const pct = Math.round((analysis.prediction?.confidence ?? 0) * 100);
  const reliability = getReliabilityStatus(analysis);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.12em' }}>Confidence</span>
        <span style={{ fontSize: '0.9rem', fontWeight: 700, fontFamily: 'var(--mono)', color }}>{pct}%</span>
      </div>
      <div style={{ height: 7, borderRadius: 99, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
        <motion.div initial={{ width: 0 }} animate={{ width: `${pct}%` }} transition={{ duration: 1.4, delay: 0.6, ease: EASE }}
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
