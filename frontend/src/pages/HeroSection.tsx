import { Suspense, lazy, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowRight, ScanEye } from 'lucide-react';

import { E } from '../components/screening/SharedUI';

const loadVisualSystem = () => import('../components/features/VisualSystem');
const EyeScanner = lazy(async () => {
  const module = await loadVisualSystem();
  return { default: module.EyeScanner };
});

function useCountUp(target: number, duration = 1400, start = false) {
  const [val, setVal] = useState(0);

  useEffect(() => {
    if (!start) return;

    let startTime: number | null = null;
    const step = (ts: number) => {
      if (!startTime) startTime = ts;
      const progress = Math.min((ts - startTime) / duration, 1);
      const ease = 1 - Math.pow(1 - progress, 3);
      setVal(Math.floor(ease * target));
      if (progress < 1) requestAnimationFrame(step);
    };

    requestAnimationFrame(step);
  }, [duration, start, target]);

  return val;
}

function HeroStat({
  suffix,
  label,
  target,
  div,
}: {
  suffix: string;
  label: string;
  target: number;
  div: number;
}) {
  const [started, setStarted] = useState(false);
  const count = useCountUp(target, 1600, started);

  useEffect(() => {
    const timer = setTimeout(() => setStarted(true), 800);
    return () => clearTimeout(timer);
  }, []);

  const display = div > 1 ? (count / div).toFixed(2) : String(count);

  return (
    <div
      className="hero-stat glass-border-animate"
      style={{
        padding: '0.75rem 1rem',
        borderRadius: '0.875rem',
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.06)',
      }}
    >
      <div
        style={{
          fontFamily: 'var(--serif)',
          fontSize: '2.2rem',
          fontWeight: 300,
          color: 'var(--text)',
          lineHeight: 1,
        }}
      >
        <span className="stat-number">{display}</span>
        <span className="text-crimson-gold" style={{ fontSize: '1.4rem' }}>
          {suffix}
        </span>
      </div>
      <div className="label-tag" style={{ marginTop: '0.4rem' }}>
        {label}
      </div>
    </div>
  );
}

function HeroScannerFallback() {
  return (
    <div
      className="eye-wrap animate-float"
      style={{
        position: 'relative',
        width: 'min(420px, 70vw)',
        aspectRatio: '1 / 1',
        borderRadius: '50%',
        border: '1px solid rgba(200,0,30,0.2)',
        background:
          'radial-gradient(circle at 50% 50%, rgba(200,0,30,0.24), rgba(200,0,30,0.02) 42%, transparent 72%)',
        boxShadow: '0 0 80px rgba(200,0,30,0.2)',
      }}
    >
      <div
        style={{
          position: 'absolute',
          inset: '14%',
          borderRadius: '50%',
          border: '1px solid rgba(255,255,255,0.08)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: '28%',
          borderRadius: '50%',
          border: '1px solid rgba(200,0,30,0.28)',
        }}
      />
      <div
        style={{
          position: 'absolute',
          inset: 0,
          display: 'grid',
          placeItems: 'center',
          fontFamily: 'var(--mono)',
          fontSize: '0.62rem',
          letterSpacing: '0.18em',
          textTransform: 'uppercase',
          color: 'var(--text-dim)',
        }}
      >
        Loading scanner
      </div>
    </div>
  );
}

export function Hero() {
  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  };

  const trustPoints = [
    {
      title: 'Quality gate first',
      detail: 'Bad captures are blocked before the app makes a clinical claim.',
    },
    {
      title: 'Clear confidence',
      detail: 'Confidence and reliability stay separate so uncertainty is visible.',
    },
    {
      title: 'Share-ready output',
      detail: 'Email and PDF handoff keep the result easy to share with a provider.',
    },
  ];

  return (
    <section
      className="section-hero"
      style={{
        position: 'relative',
        zIndex: 1,
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        padding: '0 4rem',
      }}
    >
      <div
        className="hero-grid"
        style={{
          display: 'grid',
          gridTemplateColumns: '1.15fr 0.85fr',
          gap: '5rem',
          width: '100%',
          maxWidth: 1400,
          margin: '0 auto',
        }}
      >
        <div className="hero-copy-shell" style={{ display: 'flex', flexDirection: 'column', gap: '2rem', paddingTop: '7rem' }}>
          <motion.div
            initial={{ opacity: 0, y: 16 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2, duration: 0.6 }}
          >
            <span className="stat-chip" style={{ gap: '0.5rem' }}>
              <span
                style={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: 'var(--crimson)',
                  display: 'inline-block',
                  animation: 'blink 1.5s infinite',
                }}
              />
              <span className="label-tag" style={{ color: 'var(--accent-bright)' }}>
                AI-Powered Screening Hub
              </span>
            </span>
          </motion.div>

          <h1 className="display-hero">
            <span className="hero-line-1" style={{ display: 'block', fontWeight: 900, color: 'var(--text)' }}>
              See what
            </span>
            <span
              className="hero-line-2"
              style={{
                display: 'block',
                fontStyle: 'italic',
                fontWeight: 300,
                color: 'var(--text-muted)',
                fontFamily: 'var(--serif)',
              }}
            >
              your blood
            </span>
            <span className="hero-line-3" style={{ display: 'block', fontWeight: 900 }}>
              <span className="text-crimson-gold">reveals.</span>
            </span>
          </h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.45, duration: 0.7 }}
            style={{ fontSize: '1.05rem', color: 'var(--text-muted)', lineHeight: 1.7, maxWidth: 460 }}
          >
            AnemiaLens transforms your smartphone into a first-pass screening tool. Clinical-grade vision AI analyzes
            conjunctival pallor so you can act sooner, safely.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.55, duration: 0.7 }}
            className="hero-actions"
            style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}
          >
            <button className="btn btn-primary" onClick={() => scrollTo('screening')}>
              <ScanEye size={15} /> Start Screening
            </button>
            <button className="btn btn-glass" onClick={() => scrollTo('proof')}>
              See Workflow <ArrowRight size={13} />
            </button>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.62, duration: 0.7 }}
            className="hero-proof-grid"
            style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.8rem', maxWidth: 760 }}
          >
            {trustPoints.map((point) => (
              <div
                key={point.title}
                className="hero-proof-card"
                style={{
                  padding: '0.95rem 1rem',
                  borderRadius: '1rem',
                  background: 'rgba(255,255,255,0.025)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  display: 'grid',
                  gap: '0.45rem',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.65rem' }}>
                  <span
                    aria-hidden="true"
                    style={{
                      width: 8,
                      height: 8,
                      borderRadius: '50%',
                      background: 'var(--accent-bright)',
                      boxShadow: '0 0 14px rgba(232,41,74,0.45)',
                      flexShrink: 0,
                    }}
                  />
                  <span style={{ fontSize: '0.66rem', color: 'var(--text)', lineHeight: 1.35, fontWeight: 700 }}>
                    {point.title}
                  </span>
                </div>
                <span style={{ fontSize: '0.73rem', color: 'var(--text-muted)', lineHeight: 1.6 }}>
                  {point.detail}
                </span>
              </div>
            ))}
          </motion.div>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.7, duration: 0.8 }}
            style={{
              display: 'flex',
              gap: '1rem',
              paddingTop: '1.75rem',
              borderTop: '1px solid var(--glass-border)',
              marginTop: '0.5rem',
              flexWrap: 'wrap',
            }}
            className="hero-stat-row"
          >
            {[
              { suffix: 'B+', label: 'Anemia Cases Globally', target: 192, div: 100 },
              { suffix: '%', label: 'Model Sensitivity', target: 92, div: 1 },
              { suffix: '', label: 'Clinical Specimens', target: 710, div: 1 },
            ].map(({ suffix, label, target, div }) => (
              <HeroStat key={label} suffix={suffix} label={label} target={target} div={div} />
            ))}
          </motion.div>
        </div>

        <motion.div
          className="hero-eye"
          initial={{ opacity: 0, scale: 0.85 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 1.1, delay: 0.2, ease: E }}
          style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', paddingTop: '6rem' }}
        >
          <div style={{ position: 'relative', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            {[0, 1, 2].map((i) => (
              <div
                key={i}
                style={{
                  position: 'absolute',
                  inset: `${-20 - i * 22}px`,
                  borderRadius: '50%',
                  border: `1px solid rgba(200,0,30,${0.15 - i * 0.04})`,
                  animation: `pulse-ring ${2 + i * 0.8}s ease-out ${i * 0.6}s infinite`,
                  pointerEvents: 'none',
                }}
              />
            ))}
            <div
              style={{
                position: 'absolute',
                inset: -50,
                borderRadius: '50%',
                border: '1px solid rgba(255,255,255,0.05)',
                animation: 'orbit-spin 25s linear infinite',
                pointerEvents: 'none',
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  top: -4,
                  left: '50%',
                  transform: 'translateX(-50%)',
                  width: 8,
                  height: 8,
                  borderRadius: '50%',
                  background: 'var(--accent-bright)',
                  boxShadow: '0 0 12px var(--accent-bright)',
                }}
              />
            </div>
            <div
              style={{
                position: 'absolute',
                inset: -75,
                borderRadius: '50%',
                border: '1px dashed rgba(200,0,30,0.15)',
                animation: 'orbit-spin 40s linear infinite reverse',
                pointerEvents: 'none',
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  bottom: -4,
                  left: '50%',
                  transform: 'translateX(-50%)',
                  width: 5,
                  height: 5,
                  borderRadius: '50%',
                  background: 'rgba(200,0,30,0.6)',
                }}
              />
            </div>
            <Suspense fallback={<HeroScannerFallback />}>
              <EyeScanner />
            </Suspense>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
