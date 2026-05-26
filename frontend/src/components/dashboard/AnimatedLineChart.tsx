import { useRef } from 'react';
import { motion, useInView } from 'framer-motion';

export function AnimatedLineChart({ values, color, height = 100 }: { values: number[]; color: string; height?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const inView = useInView(ref, { once: true, margin: '-20px' });

  if (values.length === 0) {
    return (
      <div style={{ height: 72, borderRadius: '1rem', border: '1px dashed rgba(255,255,255,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)', fontSize: '0.7rem' }}>
        No trend data yet
      </div>
    );
  }

  const padding = 8;
  const w = 260;
  const h = height;
  const min = Math.min(...values);
  const max = Math.max(...values);
  const range = max - min || 1;

  const points = values.map((v, i) => ({
    x: padding + (values.length === 1 ? w / 2 : (i / (values.length - 1)) * (w - padding * 2)),
    y: padding + (1 - (v - min) / range) * (h - padding * 2),
  }));

  const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ');
  const areaPath = `${linePath} L${points[points.length - 1].x},${h} L${points[0].x},${h} Z`;

  // Grid lines
  const gridLines = [0, 0.25, 0.5, 0.75, 1].map((t) => ({
    y: padding + (1 - t) * (h - padding * 2),
    label: Math.round(min + t * range),
  }));

  return (
    <div ref={ref} style={{ width: '100%', height }}>
      <svg viewBox={`0 0 ${w} ${h}`} style={{ width: '100%', height: '100%' }} preserveAspectRatio="none">
        <defs>
          <linearGradient id={`areaGrad-${color.replace('#', '')}`} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={color} stopOpacity="0.3" />
            <stop offset="100%" stopColor={color} stopOpacity="0.02" />
          </linearGradient>
          <linearGradient id={`lineGrad-${color.replace('#', '')}`} x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor={color} stopOpacity="0.5" />
            <stop offset="100%" stopColor={color} stopOpacity="1" />
          </linearGradient>
          <filter id={`glow-${color.replace('#', '')}`}>
            <feGaussianBlur stdDeviation="2" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>

        {/* Grid */}
        {gridLines.map((g, i) => (
          <g key={i}>
            <line x1={padding} x2={w - padding} y1={g.y} y2={g.y} stroke="rgba(255,255,255,0.06)" strokeWidth="1" strokeDasharray="3 3" />
            <text x={2} y={g.y + 3} fill="rgba(255,255,255,0.25)" fontSize="7" fontFamily="var(--mono, monospace)">{g.label}</text>
          </g>
        ))}

        {/* Area fill */}
        <motion.path
          d={areaPath}
          fill={`url(#areaGrad-${color.replace('#', '')})`}
          initial={{ opacity: 0 }}
          animate={inView ? { opacity: 1 } : { opacity: 0 }}
          transition={{ duration: 0.8, delay: 0.2 }}
        />

        {/* Line */}
        <motion.path
          d={linePath}
          fill="none"
          stroke={`url(#lineGrad-${color.replace('#', '')})`}
          strokeWidth="2.5"
          strokeLinecap="round"
          strokeLinejoin="round"
          filter={`url(#glow-${color.replace('#', '')})`}
          initial={{ pathLength: 0, opacity: 0 }}
          animate={inView ? { pathLength: 1, opacity: 1 } : { pathLength: 0, opacity: 0 }}
          transition={{ duration: 1.2, ease: 'easeInOut', delay: 0.1 }}
        />

        {/* Dots */}
        {points.map((p, i) => (
          <motion.circle
            key={i}
            cx={p.x}
            cy={p.y}
            r="3"
            fill={color}
            stroke="rgba(4,4,10,0.6)"
            strokeWidth="1.5"
            initial={{ scale: 0, opacity: 0 }}
            animate={inView ? { scale: 1, opacity: 1 } : { scale: 0, opacity: 0 }}
            transition={{ duration: 0.35, delay: 0.4 + i * 0.08, type: 'spring', stiffness: 200 }}
          />
        ))}
      </svg>
    </div>
  );
}
