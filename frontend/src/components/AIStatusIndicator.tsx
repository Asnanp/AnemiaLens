import { motion, useReducedMotion } from 'framer-motion';

/**
 * AI Status indicator — blinking teal dot with "System Active" text.
 * Shows in the navbar area to communicate the system is alive.
 */
export function AIStatusIndicator({ backendUp }: { backendUp: boolean }) {
  const reduceMotion = useReducedMotion();

  return (
    <div
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '0.5rem',
        padding: '0.35rem 0.75rem',
        borderRadius: 99,
        background: backendUp ? 'rgba(94,234,212,0.06)' : 'rgba(245,158,11,0.06)',
        border: `1px solid ${backendUp ? 'rgba(94,234,212,0.15)' : 'rgba(245,158,11,0.15)'}`,
      }}
    >
      <motion.span
        animate={
          reduceMotion
            ? undefined
            : {
                scale: [1, 1.3, 1],
                opacity: [0.7, 1, 0.7],
              }
        }
        transition={
          reduceMotion
            ? undefined
            : {
                duration: 2,
                repeat: Infinity,
                ease: 'easeInOut',
              }
        }
        style={{
          display: 'inline-block',
          width: 6,
          height: 6,
          borderRadius: '50%',
          background: backendUp ? 'var(--teal)' : '#F59E0B',
          boxShadow: backendUp
            ? '0 0 8px rgba(94,234,212,0.5)'
            : '0 0 8px rgba(245,158,11,0.5)',
          flexShrink: 0,
        }}
      />
      <span
        style={{
          fontFamily: 'var(--mono)',
          fontSize: '0.5rem',
          letterSpacing: '0.14em',
          textTransform: 'uppercase' as const,
          color: backendUp ? 'var(--teal-dim)' : 'rgba(245,158,11,0.6)',
        }}
      >
        {backendUp ? 'AI System Active' : 'Connecting'}
      </span>
    </div>
  );
}
