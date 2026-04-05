import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { onWakeStatus } from '../../api';
import {
  Camera, ShieldCheck, HeartPulse, Brain, ArrowRight,
  ScanEye, ChevronRight
} from 'lucide-react';

export const E = [0.22, 1, 0.36, 1] as const;

// ── WAKE BANNER ───────────────────────────────────────────────────────────────
export function WakeBanner() {
  const [status, setStatus] = useState<'waking' | 'ready' | 'failed'>('waking');
  const [dots, setDots] = useState('');

  useEffect(() => {
    const unsub = onWakeStatus(setStatus);
    return () => { unsub(); };
  }, []);

  useEffect(() => {
    if (status !== 'waking') return;
    const t = setInterval(() => setDots(d => d.length >= 3 ? '' : d + '.'), 500);
    return () => clearInterval(t);
  }, [status]);

  if (status === 'ready') return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.4 }}
      style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 9999,
        background: status === 'failed' ? 'rgba(239,68,68,0.12)' : 'rgba(200,0,30,0.10)',
        backdropFilter: 'blur(20px)',
        borderBottom: status === 'failed' ? '1px solid rgba(239,68,68,0.25)' : '1px solid rgba(200,0,30,0.2)',
        padding: '0.55rem 1.5rem',
        display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.75rem',
      }}
    >
      {status === 'waking' ? (
        <>
          <span style={{
            display: 'inline-block', width: 10, height: 10, borderRadius: '50%',
            border: '2px solid rgba(94,234,212,0.3)', borderTopColor: 'var(--teal)',
            animation: 'spin 0.8s linear infinite', flexShrink: 0,
          }} />
          <span style={{ fontFamily: 'var(--mono)', fontSize: '0.6rem', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            Backend waking up - first load can take ~60s while Hugging Face Spaces spins up{dots}
          </span>
        </>
      ) : (
        <span style={{ fontFamily: 'var(--mono)', fontSize: '0.6rem', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(239,68,68,0.8)' }}>
          Backend unreachable - please refresh or try again shortly
        </span>
      )}
    </motion.div>
  );
}

// ── LUXURY PARTICLES ──────────────────────────────────────────────────────────
export function LuxuryParticles() {
  const particles = Array.from({ length: 18 }, (_, i) => ({
    id: i,
    size: Math.random() * 3 + 1,
    left: Math.random() * 100,
    duration: Math.random() * 20 + 15,
    delay: Math.random() * 20,
    color: i % 3 === 0 ? 'rgba(200,0,30,0.5)' : i % 3 === 1 ? 'rgba(94,234,212,0.35)' : 'rgba(255,255,255,0.15)',
  }));
  return (
    <>
      {particles.map(p => (
        <div
          key={p.id}
          className="luxury-particle"
          style={{
            width: p.size, height: p.size,
            left: `${p.left}%`,
            background: p.color,
            boxShadow: `0 0 ${p.size * 3}px ${p.color}`,
            animationDuration: `${p.duration}s`,
            animationDelay: `${p.delay}s`,
          }}
        />
      ))}
    </>
  );
}

// ── MARQUEE TICKER ────────────────────────────────────────────────────────────
const TICKER_ITEMS = [
  '1.92B+ people affected by anemia globally',
  '92% model sensitivity on clinical specimens',
  '710 validated conjunctival images',
  '$0 marginal cost per screening',
  'EfficientNet-B0 vision backbone',
  'Mistral AI grounded GenAI guidance',
  'Four-band safety triage system',
  'Smartphone-first - no hardware required',
];

export function MarqueeTicker() {
  const items = [...TICKER_ITEMS, ...TICKER_ITEMS];
  return (
    <div className="marquee-strip" style={{
      position:'relative', zIndex:2, overflow:'hidden',
      borderTop:'1px solid rgba(94,234,212,0.12)',
      borderBottom:'1px solid rgba(94,234,212,0.12)',
      background:'linear-gradient(90deg, rgba(94,234,212,0.03) 0%, rgba(94,234,212,0.01) 50%, rgba(94,234,212,0.03) 100%)',
      padding:'0.875rem 0',
    }}>
      <div style={{ position:'absolute', left:0, top:0, bottom:0, width:120, background:'linear-gradient(90deg, var(--void), transparent)', zIndex:2, pointerEvents:'none' }} />
      <div style={{ position:'absolute', right:0, top:0, bottom:0, width:120, background:'linear-gradient(270deg, var(--void), transparent)', zIndex:2, pointerEvents:'none' }} />
      <div className="marquee-track">
        {items.map((item, i) => (
          <span key={i} className="marquee-item">
            <span
              style={{
                display: 'inline-block',
                width: 5,
                height: 5,
                borderRadius: '50%',
                background: 'var(--teal)',
                marginRight: '0.55rem',
                boxShadow: '0 0 8px rgba(94,234,212,0.4)',
              }}
            />
            {item}
          </span>
        ))}
      </div>
    </div>
  );
}

// ── CUSTOM CURSOR ─────────────────────────────────────────────────────────────
export function Cursor() {
  const dot  = useRef<HTMLDivElement>(null);
  const ring = useRef<HTMLDivElement>(null);
  const pos  = useRef({ x: 0, y: 0 });
  const rpos = useRef({ x: 0, y: 0 });

  useEffect(() => {
    const onMove = (e: MouseEvent) => { pos.current = { x: e.clientX, y: e.clientY }; };
    window.addEventListener('mousemove', onMove, { passive: true });
    let raf: number;
    const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
    const tick = () => {
      raf = requestAnimationFrame(tick);
      rpos.current.x = lerp(rpos.current.x, pos.current.x, 0.08);
      rpos.current.y = lerp(rpos.current.y, pos.current.y, 0.08);
      if (dot.current)  dot.current.style.transform  = `translate(calc(${pos.current.x}px - 50%), calc(${pos.current.y}px - 50%))`;
      if (ring.current) ring.current.style.transform = `translate(calc(${rpos.current.x}px - 50%), calc(${rpos.current.y}px - 50%))`;
    };
    tick();
    return () => { window.removeEventListener('mousemove', onMove); cancelAnimationFrame(raf); };
  }, []);

  return (
    <>
      <div id="cursor-dot"  ref={dot}  />
      <div id="cursor-ring" ref={ring} />
    </>
  );
}

// ── GLASS CARD ────────────────────────────────────────────────────────────────
function useMagneticTilt(ref: React.RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let raf: number | null = null;

    const onMove = (e: MouseEvent) => {
      const r = el.getBoundingClientRect();
      const shimX = e.clientX - r.left;
      const shimY = e.clientY - r.top;
      const tiltX = ((shimY / r.height) - 0.5) * -6;
      const tiltY = ((shimX / r.width) - 0.5) * 6;
      el.style.transform = `perspective(800px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) translateY(-4px)`;
      el.style.setProperty('--shimmer-x', `${shimX}px`);
      el.style.setProperty('--shimmer-y', `${shimY}px`);
    };
    const onLeave = () => {
      el.style.transform = 'perspective(800px) rotateX(0) rotateY(0) translateY(0)';
      el.style.setProperty('--shimmer-x', '50%');
      el.style.setProperty('--shimmer-y', '50%');
      if (raf) { cancelAnimationFrame(raf); raf = null; }
    };
    el.addEventListener('mousemove', onMove, { passive: true });
    el.addEventListener('mouseleave', onLeave);
    return () => {
      el.removeEventListener('mousemove', onMove);
      el.removeEventListener('mouseleave', onLeave);
      if (raf) cancelAnimationFrame(raf);
    };
  }, [ref]);
}

export const GlassCard = ({ children, className = '', style = {}, ...props }: React.HTMLAttributes<HTMLDivElement>) => {
  const ref = useRef<HTMLDivElement>(null);
  useMagneticTilt(ref);
  return (
    <div
      ref={ref}
      className={`glass glass-hover glass-shimmer ${className}`}
      style={{ ...style, '--shimmer-x':'50%', '--shimmer-y':'50%', transition:'transform 0.4s cubic-bezier(0.22,1,0.36,1), box-shadow 0.4s' } as React.CSSProperties}
      {...props}
    >
      <div style={{
        position:'absolute', inset:0, borderRadius:'inherit', pointerEvents:'none', zIndex:4,
        background:'radial-gradient(300px at var(--shimmer-x, 50%) var(--shimmer-y, 50%), rgba(94,234,212,0.06), rgba(255,255,255,0.02) 60%, transparent)',
      }} />
      {children}
    </div>
  );
};

// ── STEP META ─────────────────────────────────────────────────────────────────
export const STEPS_META = [
  { label: 'Capture',  icon: <Camera size={13} /> },
  { label: 'Quality',  icon: <ShieldCheck size={13} /> },
  { label: 'Intake', icon: <HeartPulse size={13} /> },
  { label: 'Result',   icon: <Brain size={13} /> },
] as const;

// ── AI THINKING MOMENT — the critical emotional pause ─────────────────────────
export function QwenLoadingOverlay() {
  const [phase, setPhase] = useState(0);
  const [progress, setProgress] = useState(0);

  const messages = [
    'Analyzing hemoglobin signals…',
    'Evaluating image quality markers…',
    'Correlating clinical indicators…',
    'Preparing screening result…',
  ];

  useEffect(() => {
    const progressInterval = setInterval(() => {
      setProgress((p) => {
        if (p >= 92) return p;
        return p + 0.4 + Math.random() * 0.3;
      });
    }, 50);

    const timers = messages.map((_, i) =>
      setTimeout(() => setPhase(i), i * 1800 + 600)
    );

    return () => {
      clearInterval(progressInterval);
      timers.forEach(clearTimeout);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: 480,
        gap: '2.5rem',
        position: 'relative',
      }}
    >
      {/* Breathing background glow */}
      <motion.div
        aria-hidden="true"
        animate={{ scale: [1, 1.15, 1], opacity: [0.15, 0.3, 0.15] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
        style={{
          position: 'absolute',
          width: 300,
          height: 300,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(94,234,212,0.12) 0%, transparent 70%)',
          filter: 'blur(60px)',
          pointerEvents: 'none',
        }}
      />

      {/* Scanning ring */}
      <div style={{ position: 'relative' }}>
        <motion.div
          animate={{ scale: [1, 1.08, 1], opacity: [0.5, 0.9, 0.5] }}
          transition={{ duration: 2.2, repeat: Infinity, ease: 'easeInOut' }}
          style={{
            width: 80,
            height: 80,
            borderRadius: '50%',
            background: 'rgba(94,234,212,0.06)',
            border: '1px solid rgba(94,234,212,0.2)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
          }}
        >
          <motion.div
            animate={{ rotate: 360 }}
            transition={{ duration: 3, repeat: Infinity, ease: 'linear' }}
            style={{
              width: 56,
              height: 56,
              borderRadius: '50%',
              border: '1.5px solid rgba(94,234,212,0.1)',
              borderTopColor: 'var(--teal)',
            }}
          />
        </motion.div>
        {/* Scan line sweep */}
        <motion.div
          animate={{ top: ['10%', '90%', '10%'] }}
          transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
          style={{
            position: 'absolute',
            left: 0,
            right: 0,
            height: 1,
            background: 'linear-gradient(90deg, transparent, var(--teal), transparent)',
            boxShadow: '0 0 8px rgba(94,234,212,0.4)',
          }}
        />
      </div>

      {/* Title */}
      <div style={{ textAlign: 'center', position: 'relative', zIndex: 1 }}>
        <div style={{
          fontFamily: 'var(--serif)',
          fontSize: '1.5rem',
          fontWeight: 700,
          letterSpacing: '-0.02em',
          marginBottom: '0.5rem',
        }}>
          Screening analysis in progress
        </div>
        <div style={{
          fontSize: '0.75rem',
          color: 'var(--text-dim)',
          maxWidth: 380,
          margin: '0 auto',
          lineHeight: 1.6,
        }}>
          The result is being prepared from the capture and intake you already completed.
        </div>
      </div>

      {/* Progress bar */}
      <div style={{
        width: '100%',
        maxWidth: 320,
        position: 'relative',
        zIndex: 1,
      }}>
        <div style={{
          height: 3,
          borderRadius: 99,
          background: 'rgba(255,255,255,0.06)',
          overflow: 'hidden',
        }}>
          <motion.div
            style={{
              height: '100%',
              borderRadius: 99,
              background: 'linear-gradient(90deg, var(--crimson), var(--pink-glow), var(--teal))',
              width: `${progress}%`,
              boxShadow: '0 0 12px rgba(94,234,212,0.3)',
            }}
            transition={{ duration: 0.05 }}
          />
        </div>
      </div>

      {/* Sequential messages */}
      <div style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '0.65rem',
        width: '100%',
        maxWidth: 360,
        position: 'relative',
        zIndex: 1,
      }}>
        {messages.map((msg, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -16 }}
            animate={{
              opacity: i <= phase ? 1 : 0.2,
              x: i <= phase ? 0 : -8,
            }}
            transition={{ delay: i * 0.15, duration: 0.4 }}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
              padding: '0.6rem 1rem',
              borderRadius: '0.75rem',
              background: i <= phase ? 'rgba(255,255,255,0.03)' : 'transparent',
              border: `1px solid ${
                i < phase
                  ? 'rgba(94,234,212,0.15)'
                  : i === phase
                  ? 'rgba(94,234,212,0.25)'
                  : 'rgba(255,255,255,0.04)'
              }`,
            }}
          >
            {i < phase ? (
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--teal)" strokeWidth="2.5" strokeLinecap="round">
                <polyline points="20 6 9 17 4 12"/>
              </svg>
            ) : i === phase ? (
              <span style={{
                display: 'inline-block',
                width: 12,
                height: 12,
                border: '1.5px solid rgba(94,234,212,0.2)',
                borderTopColor: 'var(--teal)',
                borderRadius: '50%',
                animation: 'spin 0.8s linear infinite',
                flexShrink: 0,
              }} />
            ) : (
              <span style={{
                display: 'inline-block',
                width: 12,
                height: 12,
                borderRadius: '50%',
                border: '1px solid rgba(255,255,255,0.08)',
                flexShrink: 0,
              }} />
            )}
            <span style={{
              fontSize: '0.72rem',
              color: i < phase
                ? 'var(--text-muted)'
                : i === phase
                ? 'var(--teal)'
                : 'var(--text-dim)',
              fontFamily: 'var(--mono)',
              letterSpacing: '0.02em',
            }}>
              {msg}
            </span>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
