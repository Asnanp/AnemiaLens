import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';

const E = [0.22, 1, 0.36, 1] as const;

export function bandColor(band?: string | null): string {
  switch (band) {
    case 'low_risk': return '#10B981';
    case 'moderate_risk': return '#F59E0B';
    case 'high_concern': return '#EF4444';
    case 'uncertain_retake_needed': return '#8B5CF6';
    default: return '#64748B';
  }
}

export function DistributionDonut({ counts, total }: { counts: Record<string, number>; total: number }) {
  const ref = useRef<SVGSVGElement>(null);
  const inView = useInView(ref, { once: true });

  const rows = [
    { key: 'low_risk', label: 'Low Risk' },
    { key: 'moderate_risk', label: 'Moderate' },
    { key: 'high_concern', label: 'High Concern' },
    { key: 'uncertain_retake_needed', label: 'Retake Needed' },
  ] as const;

  const segments = rows.map((r) => ({ ...r, count: counts[r.key] ?? 0, color: bandColor(r.key) }));
  const nonEmpty = segments.filter((s) => s.count > 0);
  const radius = 42;
  const circumference = 2 * Math.PI * radius;

  if (total === 0 || nonEmpty.length === 0) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 120, color: 'var(--text-dim)', fontSize: '0.72rem' }}>
        No distribution data yet
      </div>
    );
  }

  let accumulatedOffset = 0;

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '1.25rem', flexWrap: 'wrap' }}>
      {/* Donut */}
      <svg ref={ref} width="110" height="110" viewBox="0 0 110 110">
        {segments.map((seg) => {
          const pct = total > 0 ? seg.count / total : 0;
          const dashLen = pct * circumference;
          const dashGap = circumference - dashLen;
          const offset = accumulatedOffset;
          accumulatedOffset += dashLen;

          return (
            <motion.circle
              key={seg.key}
              cx="55"
              cy="55"
              r={radius}
              fill="none"
              stroke={seg.color}
              strokeWidth="10"
              strokeDasharray={`${dashLen} ${dashGap}`}
              strokeDashoffset={-offset}
              strokeLinecap="round"
              transform="rotate(-90 55 55)"
              initial={{ strokeDasharray: `0 ${circumference}`, opacity: 0 }}
              animate={inView ? { strokeDasharray: `${dashLen} ${dashGap}`, opacity: 1 } : { strokeDasharray: `0 ${circumference}`, opacity: 0 }}
              transition={{ duration: 0.9, ease: E, delay: 0.15 }}
            />
          );
        })}
        <text x="55" y="52" textAnchor="middle" fill="var(--text)" fontSize="18" fontWeight="700" fontFamily="var(--serif, serif)">{total}</text>
        <text x="55" y="64" textAnchor="middle" fill="var(--text-dim)" fontSize="8" fontFamily="var(--mono, monospace)">TOTAL</text>
      </svg>

      {/* Legend bars */}
      <div style={{ flex: 1, minWidth: 140, display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
        {segments.map((seg, idx) => {
          const pct = total > 0 ? (seg.count / total) * 100 : 0;
          return (
            <div key={seg.key}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.25rem', fontSize: '0.68rem' }}>
                <span style={{ color: seg.color }}>{seg.label}</span>
                <span style={{ fontFamily: 'var(--mono)', color: 'var(--text-dim)' }}>{seg.count} ({pct.toFixed(0)}%)</span>
              </div>
              <div style={{ height: 6, borderRadius: 999, background: 'rgba(255,255,255,0.05)', overflow: 'hidden' }}>
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${pct}%` }}
                  transition={{ duration: 0.8, ease: E, delay: 0.2 + idx * 0.1 }}
                  style={{ height: '100%', borderRadius: 999, background: `linear-gradient(90deg, ${seg.color}44, ${seg.color})` }}
                />
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

export function DistributionBars({ counts, total }: { counts: Record<string, number>; total: number }) {
  const rows = [
    { key: 'low_risk', label: 'Low risk' },
    { key: 'moderate_risk', label: 'Moderate' },
    { key: 'high_concern', label: 'High concern' },
    { key: 'uncertain_retake_needed', label: 'Retake needed' },
  ] as const;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {rows.map((row, idx) => {
        const count = counts[row.key] ?? 0;
        const pct = total > 0 ? (count / total) * 100 : 0;
        const color = bandColor(row.key);
        return (
          <div key={row.key}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              <span>{row.label}</span>
              <span style={{ fontFamily: 'var(--mono)', color }}>{count}</span>
            </div>
            <div style={{ height: 8, borderRadius: 999, background: 'rgba(255,255,255,0.05)', overflow: 'hidden' }}>
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.9, ease: E, delay: idx * 0.1 }}
                style={{ height: '100%', borderRadius: 999, background: `linear-gradient(90deg, ${color}55, ${color})` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
