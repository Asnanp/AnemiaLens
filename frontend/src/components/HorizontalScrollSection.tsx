import { useRef, type ReactNode, type CSSProperties } from 'react';
import {
  motion,
  useScroll,
  useTransform,
  useSpring,
  useReducedMotion,
} from 'framer-motion';

interface HorizontalScrollSectionProps {
  children: ReactNode;
  /** Number of "screens" worth of content (determines scroll height) */
  screens?: number;
  className?: string;
  style?: CSSProperties;
  /** ID for scroll-to targeting */
  id?: string;
}

export function HorizontalScrollSection({
  children,
  screens = 3,
  className,
  style,
  id,
}: HorizontalScrollSectionProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const reduceMotion = useReducedMotion();

  const { scrollYProgress } = useScroll({
    target: containerRef,
    offset: ['start start', 'end end'],
  });

  // Translate the inner track horizontally based on vertical scroll
  const rawX = useTransform(scrollYProgress, [0, 1], ['0%', '-75%']);
  const x = useSpring(rawX, {
    stiffness: 90,
    damping: 28,
    restDelta: 0.001,
  });

  // Subtle scale effect for depth
  const scale = useTransform(scrollYProgress, [0, 0.5, 1], [1, 1.02, 1]);

  if (reduceMotion) {
    return (
      <div id={id} className={className} style={style}>
        <div style={{ display: 'flex', gap: '2rem', overflowX: 'auto', padding: '2rem 0' }}>
          {children}
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      id={id}
      className={className}
      style={{
        position: 'relative',
        height: `${screens * 100}vh`,
        ...style,
      }}
    >
      <div
        className="horizontal-scroll-sticky"
        style={{
          position: 'sticky',
          top: 0,
          height: '100vh',
          display: 'flex',
          alignItems: 'center',
          overflow: 'hidden',
        }}
      >
        <motion.div
          className="horizontal-scroll-track"
          style={{
            x,
            scale,
            display: 'flex',
            gap: 'clamp(1.5rem, 3vw, 2.5rem)',
            paddingLeft: 'clamp(2rem, 6vw, 6rem)',
            paddingRight: '30vw',
            willChange: 'transform',
          }}
        >
          {children}
        </motion.div>
      </div>
    </div>
  );
}
