import type { ReactNode } from 'react';
import { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';

const E = [0.22, 1, 0.36, 1] as const;

/* ------------------------------------------------------------------ */
/*  Animated counter hook                                              */
/* ------------------------------------------------------------------ */

export function useAnimatedCounter(end: number, durationMs = 1200, enabled = true) {
  const [value, setValue] = useState(0);
  const rafRef = useRef<number>();

  useEffect(() => {
    if (!enabled) { setValue(end); return; }
    const start = performance.now();
    const from = 0;

    const tick = (now: number) => {
      const elapsed = now - start;
      const progress = Math.min(elapsed / durationMs, 1);
      // ease-out cubic
      const eased = 1 - Math.pow(1 - progress, 3);
      setValue(Math.round(from + (end - from) * eased));
      if (progress < 1) {
        rafRef.current = requestAnimationFrame(tick);
      }
    };

    rafRef.current = requestAnimationFrame(tick);
    return () => { if (rafRef.current) cancelAnimationFrame(rafRef.current); };
  }, [end, durationMs, enabled]);

  return value;
}

export function StatCard({
  icon,
  label,
  value,
  tint,
  sub,
  delay = 0,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  tint: string;
  sub?: string;
  delay?: number;
}) {
  const numericValue = parseInt(value.replace(/[^0-9-]/g, ''), 10);
  const isNumeric = !isNaN(numericValue) && value.includes(String(numericValue));
  const animatedValue = useAnimatedCounter(numericValue, 1100, isNumeric);
  const displayValue = isNumeric ? (value.includes('%') ? `${animatedValue}%` : String(animatedValue)) : value;

  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: E, delay }}
      style={{
        padding: '1.1rem 1rem',
        borderRadius: '1rem',
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.7rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
        <span style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--text-dim)' }}>{label}</span>
        <motion.div
          whileHover={{ scale: 1.08, rotate: -4 }}
          style={{ width: 34, height: 34, borderRadius: '0.85rem', display: 'flex', alignItems: 'center', justifyContent: 'center', background: `${tint}14`, border: `1px solid ${tint}28`, color: tint }}
        >
          {icon}
        </motion.div>
      </div>
      <motion.div
        style={{ fontFamily: 'var(--serif)', fontSize: '1.55rem', fontWeight: 700, lineHeight: 1.05 }}
        initial={{ opacity: 0, y: 6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: delay + 0.15 }}
      >
        {displayValue}
      </motion.div>
      {sub && <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', lineHeight: 1.55 }}>{sub}</div>}
    </motion.div>
  );
}
