import { useRef, useEffect } from 'react';
import { motion, useInView, useAnimation, useReducedMotion, type Variants } from 'framer-motion';
import { springPresets, springTransition, type SpringPresetKey } from '../utils/springAnimations';

interface ScrollRevealProps {
  children: React.ReactNode;
  className?: string;
  delay?: number;
  direction?: 'up' | 'down' | 'left' | 'right' | 'scale';
  once?: boolean;
  /** Spring preset name for the reveal animation. Default: 'default' */
  spring?: SpringPresetKey;
  /** Distance to travel on entrance (px). Default: 64 */
  distance?: number;
}

export function ScrollReveal({
  children,
  className = '',
  delay = 0,
  direction = 'up',
  once = true,
  spring = 'default',
  distance = 64,
}: ScrollRevealProps) {
  const ref = useRef(null);
  const reduceMotion = useReducedMotion();
  const isInView = useInView(ref, { once, amount: 0.2 });
  const controls = useAnimation();

  const springConfig = springPresets[spring];

  useEffect(() => {
    if (isInView) {
      controls.start('visible');
    } else if (!once) {
      controls.start('hidden');
    }
  }, [isInView, controls, once]);

  const variants: Variants = {
    hidden: {
      opacity: 0,
      y: direction === 'up' ? distance : direction === 'down' ? -distance : 0,
      x: direction === 'left' ? distance : direction === 'right' ? -distance : 0,
      scale: direction === 'scale' ? 0.85 : 1,
    },
    visible: {
      opacity: 1,
      y: 0,
      x: 0,
      scale: 1,
      transition: {
        delay,
        ...springConfig,
      },
    },
  };

  if (reduceMotion) {
    return (
      <div className={className}>
        {children}
      </div>
    );
  }

  return (
    <motion.div
      ref={ref}
      initial="hidden"
      animate={controls}
      variants={variants}
      className={className}
    >
      {children}
    </motion.div>
  );
}
