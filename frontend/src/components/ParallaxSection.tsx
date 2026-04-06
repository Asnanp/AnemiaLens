import { useRef } from 'react';
import { motion, useScroll, useSpring, useTransform, useReducedMotion } from 'framer-motion';
import { springPresets, type SpringPresetKey } from '../utils/springAnimations';

interface ParallaxSectionProps {
  children: React.ReactNode;
  speed?: number;
  className?: string;
  style?: React.CSSProperties;
  /** Spring preset for parallax smoothing. Default: 'gentle' */
  spring?: SpringPresetKey;
}

export function ParallaxSection({ children, speed = 0.5, className, style, spring = 'gentle' }: ParallaxSectionProps) {
  const ref = useRef(null);
  const reduceMotion = useReducedMotion();
  const { scrollYProgress } = useScroll({
    target: ref,
    offset: ['start end', 'end start']
  });

  const springConfig = springPresets[spring];
  const rawY = useTransform(scrollYProgress, [0, 1], ['0%', `${speed * 100}%`]);
  const y = useSpring(rawY, reduceMotion ? { stiffness: 0, damping: 0 } : springConfig);

  if (reduceMotion) {
    return (
      <div ref={ref} className={className} style={style}>
        {children}
      </div>
    );
  }

  return (
    <div ref={ref} className={className} style={style}>
      <motion.div style={{ y }}>
        {children}
      </motion.div>
    </div>
  );
}
