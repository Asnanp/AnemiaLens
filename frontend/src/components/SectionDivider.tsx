import { useRef } from 'react';
import {
  motion,
  useScroll,
  useTransform,
  useReducedMotion,
} from 'framer-motion';

interface SectionDividerProps {
  tone?: 'coral' | 'teal' | 'neutral';
  className?: string;
}

const TONE_COLORS = {
  coral: {
    from: 'rgba(241, 90, 119, 0)',
    mid: 'rgba(241, 90, 119, 0.65)',
    to: 'rgba(241, 90, 119, 0)',
    glow: 'rgba(241, 90, 119, 0.18)',
  },
  teal: {
    from: 'rgba(67, 216, 194, 0)',
    mid: 'rgba(67, 216, 194, 0.55)',
    to: 'rgba(67, 216, 194, 0)',
    glow: 'rgba(67, 216, 194, 0.15)',
  },
  neutral: {
    from: 'rgba(255, 255, 255, 0)',
    mid: 'rgba(255, 255, 255, 0.14)',
    to: 'rgba(255, 255, 255, 0)',
    glow: 'rgba(255, 255, 255, 0.06)',
  },
};

export function SectionDivider({ tone = 'neutral', className }: SectionDividerProps) {
  const ref = useRef<HTMLDivElement>(null);
  const reduceMotion = useReducedMotion();
  const colors = TONE_COLORS[tone];

  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start 0.9', 'start 0.4'],
  });

  const scaleX = useTransform(scrollYProgress, [0, 1], [0, 1]);
  const opacity = useTransform(scrollYProgress, [0, 0.4, 1], [0, 1, 1]);

  if (reduceMotion) {
    return (
      <div
        className={className}
        style={{
          width: '100%',
          maxWidth: '62rem',
          margin: '0 auto',
          height: 1,
          background: `linear-gradient(90deg, ${colors.from}, ${colors.mid}, ${colors.to})`,
        }}
      />
    );
  }

  return (
    <div
      ref={ref}
      className={className}
      style={{
        width: '100%',
        maxWidth: '62rem',
        margin: '0 auto',
        padding: '1rem 0',
        position: 'relative',
      }}
    >
      <motion.div
        style={{
          height: 1,
          background: `linear-gradient(90deg, ${colors.from}, ${colors.mid}, ${colors.to})`,
          transformOrigin: 'center',
          scaleX,
          opacity,
          willChange: 'transform, opacity',
        }}
      />
      <motion.div
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '40%',
          height: 16,
          borderRadius: 999,
          background: colors.glow,
          filter: 'blur(12px)',
          opacity,
          pointerEvents: 'none',
        }}
      />
    </div>
  );
}
