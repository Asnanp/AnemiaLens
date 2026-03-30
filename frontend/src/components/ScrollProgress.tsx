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
        height: 3,
        background: 'linear-gradient(90deg, var(--crimson), var(--accent-bright), #FF6B8A)',
        transformOrigin: '0%',
        scaleX,
        zIndex: 10000,
        boxShadow: '0 0 20px rgba(200,0,30,0.5)',
      }}
    />
  );
}
