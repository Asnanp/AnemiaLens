import { motion, useReducedMotion } from 'framer-motion';
import { ArrowLeft, Home, ScanEye } from 'lucide-react';
import { Link } from 'react-router-dom';
import { MagneticButton } from '../components/MagneticButton';

const E = [0.22, 1, 0.36, 1] as const;

export default function NotFoundPage() {
  const reduceMotion = useReducedMotion();

  return (
    <section
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '2rem 1.5rem',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Ambient background orbs */}
      <div
        aria-hidden="true"
        style={{ position: 'absolute', inset: 0, pointerEvents: 'none', zIndex: 0 }}
      >
        <motion.div
          animate={reduceMotion ? undefined : { scale: [1, 1.15, 1], opacity: [0.3, 0.5, 0.3] }}
          transition={reduceMotion ? undefined : { duration: 8, repeat: Infinity, ease: 'easeInOut' }}
          style={{
            position: 'absolute',
            top: '20%',
            left: '30%',
            width: 350,
            height: 350,
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(200,0,30,0.15) 0%, transparent 70%)',
          }}
        />
        <motion.div
          animate={reduceMotion ? undefined : { scale: [1, 1.1, 1], opacity: [0.2, 0.4, 0.2] }}
          transition={reduceMotion ? undefined : { duration: 12, repeat: Infinity, ease: 'easeInOut' }}
          style={{
            position: 'absolute',
            bottom: '25%',
            right: '20%',
            width: 280,
            height: 280,
            borderRadius: '50%',
            background: 'radial-gradient(circle, rgba(94,234,212,0.10) 0%, transparent 70%)',
          }}
        />
      </div>

      <motion.div
        initial={reduceMotion ? false : { opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.7, ease: E }}
        style={{
          position: 'relative',
          zIndex: 1,
          textAlign: 'center',
          maxWidth: 540,
        }}
      >
        {/* Large 404 text */}
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.6, delay: 0.1, ease: E }}
          style={{
            fontFamily: 'var(--serif)',
            fontSize: 'clamp(6rem, 15vw, 10rem)',
            fontWeight: 800,
            lineHeight: 1,
            letterSpacing: '-0.05em',
            background: 'linear-gradient(135deg, rgba(200,0,30,0.4) 0%, rgba(200,0,30,0.15) 50%, rgba(94,234,212,0.2) 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            backgroundClip: 'text',
            userSelect: 'none',
          }}
        >
          404
        </motion.div>

        {/* Eyebrow */}
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.2, ease: E }}
          style={{
            fontFamily: 'var(--mono)',
            fontSize: '0.62rem',
            textTransform: 'uppercase',
            letterSpacing: '0.2em',
            color: 'var(--teal)',
            marginBottom: '1rem',
          }}
        >
          Page not found
        </motion.div>

        {/* Title */}
        <motion.h1
          initial={reduceMotion ? false : { opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.3, ease: E }}
          style={{
            fontFamily: 'var(--serif)',
            fontSize: 'clamp(1.5rem, 3vw, 2rem)',
            fontWeight: 600,
            letterSpacing: '-0.02em',
            lineHeight: 1.3,
            color: 'var(--text-primary)',
            marginBottom: '0.75rem',
          }}
        >
          This page doesn't exist
        </motion.h1>

        {/* Description */}
        <motion.p
          initial={reduceMotion ? false : { opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.4, ease: E }}
          style={{
            fontSize: '0.88rem',
            lineHeight: 1.6,
            color: 'var(--text-secondary)',
            marginBottom: '2rem',
          }}
        >
          The page you're looking for may have been moved or removed.
          Head back to the homepage or start a new screening.
        </motion.p>

        {/* Actions */}
        <motion.div
          initial={reduceMotion ? false : { opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.5, ease: E }}
          style={{
            display: 'flex',
            flexWrap: 'wrap',
            gap: '0.75rem',
            justifyContent: 'center',
          }}
        >
          <Link to="/">
            <MagneticButton className="btn-primary">
              <Home size={15} />
              Go home
            </MagneticButton>
          </Link>
          <Link to="/">
            <MagneticButton className="btn-glass">
              <ScanEye size={15} />
              Start screening
            </MagneticButton>
          </Link>
        </motion.div>
      </motion.div>
    </section>
  );
}
