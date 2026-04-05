import { motion, useScroll, useSpring } from 'framer-motion';

export function ScrollProgress() {
  const { scrollYProgress } = useScroll();
  const scaleX = useSpring(scrollYProgress, {
    stiffness: 100,
    damping: 30,
    restDelta: 0.001
  });

  return (
    <motion.div
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        height: 2,
        background: 'linear-gradient(90deg, var(--crimson), var(--pink-glow), var(--teal))',
        transformOrigin: '0%',
        scaleX,
        zIndex: 10000,
        boxShadow: '0 0 16px rgba(200,0,30,0.35), 0 0 30px rgba(94,234,212,0.15)',
      }}
    />
  );
}
