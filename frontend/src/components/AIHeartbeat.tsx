import { motion, useReducedMotion } from 'framer-motion';

/**
 * Ambient AI heartbeat — a very faint, slow-pulsing gradient that breathes
 * behind the page. Communicates "the system is alive" without being distracting.
 */
export function AIHeartbeat() {
  const reduceMotion = useReducedMotion();

  if (reduceMotion) return null;

  return (
    <div
      aria-hidden="true"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 0,
        pointerEvents: 'none',
        overflow: 'hidden',
      }}
    >
      {/* Primary crimson pulse */}
      <motion.div
        animate={{
          scale: [1, 1.06, 1],
          opacity: [0.12, 0.22, 0.12],
        }}
        transition={{
          duration: 8,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        style={{
          position: 'absolute',
          top: '8%',
          left: '12%',
          width: '50vw',
          height: '50vw',
          maxWidth: 800,
          maxHeight: 800,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(200,0,30,0.15) 0%, rgba(200,0,30,0.04) 40%, transparent 70%)',
          filter: 'blur(80px)',
        }}
      />

      {/* Secondary teal drift */}
      <motion.div
        animate={{
          x: [0, 30, 0],
          y: [0, -20, 0],
          opacity: [0.08, 0.16, 0.08],
        }}
        transition={{
          duration: 12,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        style={{
          position: 'absolute',
          bottom: '10%',
          right: '8%',
          width: '40vw',
          height: '40vw',
          maxWidth: 650,
          maxHeight: 650,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(94,234,212,0.10) 0%, rgba(94,234,212,0.03) 40%, transparent 70%)',
          filter: 'blur(70px)',
        }}
      />

      {/* Tertiary pink accent */}
      <motion.div
        animate={{
          x: [0, -15, 0],
          y: [0, 12, 0],
          opacity: [0.06, 0.12, 0.06],
        }}
        transition={{
          duration: 15,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          transform: 'translate(-50%, -50%)',
          width: '35vw',
          height: '35vw',
          maxWidth: 500,
          maxHeight: 500,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(255,107,138,0.08) 0%, transparent 60%)',
          filter: 'blur(60px)',
        }}
      />
    </div>
  );
}
