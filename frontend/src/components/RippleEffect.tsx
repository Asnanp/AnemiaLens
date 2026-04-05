import { useState, useLayoutEffect, MouseEvent } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

interface Ripple {
  x: number;
  y: number;
  size: number;
  key: number;
}

export function useRipple() {
  const [ripples, setRipples] = useState<Ripple[]>([]);

  const addRipple = (event: MouseEvent<HTMLElement>) => {
    const trigger = event.currentTarget;
    const rect = trigger.getBoundingClientRect();
    const size = Math.max(rect.width, rect.height);
    const x = event.clientX - rect.left - size / 2;
    const y = event.clientY - rect.top - size / 2;

    const newRipple = { x, y, size, key: Date.now() };
    setRipples((prev) => [...prev, newRipple]);
  };

  const RippleElements = (
    <div style={{ position: 'absolute', inset: 0, overflow: 'hidden', borderRadius: 'inherit', pointerEvents: 'none', zIndex: 0 }}>
      <AnimatePresence>
        {ripples.map((ripple) => (
          <motion.span
            key={ripple.key}
            initial={{ opacity: 0.35, scale: 0 }}
            animate={{ opacity: 0, scale: 2 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.6, ease: 'easeOut' }}
            onAnimationComplete={() => {
              setRipples((prev) => prev.filter((r) => r.key !== ripple.key));
            }}
            style={{
              position: 'absolute',
              top: ripple.y,
              left: ripple.x,
              width: ripple.size,
              height: ripple.size,
              backgroundColor: 'rgba(255, 255, 255, 0.4)',
              borderRadius: '50%',
              pointerEvents: 'none',
            }}
          />
        ))}
      </AnimatePresence>
    </div>
  );

  return { addRipple, RippleElements };
}
