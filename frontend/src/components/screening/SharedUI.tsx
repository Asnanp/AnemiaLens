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
            border: '2px solid rgba(200,0,30,0.4)', borderTopColor: 'var(--accent-bright)',
            animation: 'spin 0.8s linear infinite', flexShrink: 0,
          }} />
          <span style={{ fontFamily: 'var(--mono)', fontSize: '0.6rem', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
            Backend waking up — first load takes ~60s on Render free tier{dots}
          </span>
        </>
      ) : (
        <span style={{ fontFamily: 'var(--mono)', fontSize: '0.6rem', letterSpacing: '0.15em', textTransform: 'uppercase', color: 'rgba(239,68,68,0.8)' }}>
          Backend unreachable — please refresh or try again shortly
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
    color: i % 3 === 0 ? 'rgba(200,0,30,0.5)' : i % 3 === 1 ? 'rgba(232,41,74,0.35)' : 'rgba(255,255,255,0.15)',
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
  'Smartphone-first — no hardware required',
];

export function MarqueeTicker() {
  const items = [...TICKER_ITEMS, ...TICKER_ITEMS];
  return (
    <div className="marquee-strip" style={{
      position:'relative', zIndex:2, overflow:'hidden',
      borderTop:'1px solid rgba(200,0,30,0.15)',
      borderBottom:'1px solid rgba(200,0,30,0.15)',
      background:'linear-gradient(90deg, rgba(200,0,30,0.04) 0%, rgba(200,0,30,0.02) 50%, rgba(200,0,30,0.04) 100%)',
      padding:'0.875rem 0',
    }}>
      <div style={{ position:'absolute', left:0, top:0, bottom:0, width:120, background:'linear-gradient(90deg, var(--void), transparent)', zIndex:2, pointerEvents:'none' }} />
      <div style={{ position:'absolute', right:0, top:0, bottom:0, width:120, background:'linear-gradient(270deg, var(--void), transparent)', zIndex:2, pointerEvents:'none' }} />
      <div className="marquee-track">
        {items.map((item, i) => (
          <span key={i} className="marquee-item">
            <span style={{ color:'var(--accent-bright)', marginRight:'0.5rem' }}>◆</span>
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
      rpos.current.x = lerp(rpos.current.x, pos.current.x, 0.10);
      rpos.current.y = lerp(rpos.current.y, pos.current.y, 0.10);
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
      const tiltX = ((shimY / r.height) - 0.5) * -8;
      const tiltY = ((shimX / r.width) - 0.5) * 8;
      el.style.transform = `perspective(1000px) rotateX(${tiltX}deg) rotateY(${tiltY}deg) translateY(-6px)`;
      el.style.setProperty('--shimmer-x', `${shimX}px`);
      el.style.setProperty('--shimmer-y', `${shimY}px`);
    };
    const onLeave = () => {
      el.style.transform = 'perspective(1000px) rotateX(0) rotateY(0) translateY(0)';
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
        background:'radial-gradient(300px at var(--shimmer-x, 50%) var(--shimmer-y, 50%), rgba(255,255,255,0.10), rgba(255,255,255,0.03) 60%, transparent)',
      }} />
      {children}
    </div>
  );
};

// ── STEP META ─────────────────────────────────────────────────────────────────
export const STEPS_META = [
  { label: 'Capture',  icon: <Camera size={13} /> },
  { label: 'Quality',  icon: <ShieldCheck size={13} /> },
  { label: 'Symptoms', icon: <HeartPulse size={13} /> },
  { label: 'Result',   icon: <Brain size={13} /> },
] as const;

// ── LOADING OVERLAY ───────────────────────────────────────────────────────────
export function QwenLoadingOverlay() {
  const stages = [
    { label: 'Running vision model', done: true },
    { label: 'Analyzing conjunctival pallor', done: true },
    { label: 'Calculating triage band', done: true },
    { label: 'Mistral AI generating guidance...', done: false },
  ];
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
      style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 420, gap: '2rem' }}
    >
      <motion.div
        animate={{ scale: [1, 1.12, 1], opacity: [0.7, 1, 0.7] }}
        transition={{ duration: 1.8, repeat: Infinity, ease: 'easeInOut' }}
        style={{ width: 72, height: 72, borderRadius: '50%', background: 'rgba(0,194,255,0.1)', border: '1px solid rgba(0,194,255,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}
      >
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="rgba(0,194,255,0.9)" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2a4 4 0 0 1 4 4c0 .34-.04.67-.1 1H16a3 3 0 0 1 3 3v1a3 3 0 0 1-1.5 2.6V14a3 3 0 0 1-3 3h-5a3 3 0 0 1-3-3v-.4A3 3 0 0 1 5 11v-1a3 3 0 0 1 3-3h.1A4 4 0 0 1 12 2z"/>
          <path d="M9 17v2m6-2v2M9 21h6"/>
        </svg>
      </motion.div>

      <div style={{ textAlign: 'center' }}>
        <div style={{ fontFamily: 'var(--serif)', fontSize: '1.4rem', fontWeight: 700, marginBottom: '0.4rem' }}>
          AI Analysis in Progress
        </div>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
          Mistral AI is generating your personalized guidance
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', width: '100%', maxWidth: 340 }}>
        {stages.map((s, i) => (
          <motion.div key={i}
            initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.15 }}
            style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.65rem 1rem', borderRadius: '0.75rem', background: 'rgba(255,255,255,0.03)', border: `1px solid ${s.done ? 'rgba(0,229,150,0.2)' : 'rgba(0,194,255,0.2)'}` }}
          >
            {s.done ? (
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#00E596" strokeWidth="2.5" strokeLinecap="round"><polyline points="20 6 9 17 4 12"/></svg>
            ) : (
              <span style={{ display: 'inline-block', width: 14, height: 14, border: '2px solid rgba(0,194,255,0.3)', borderTopColor: 'rgba(0,194,255,0.9)', borderRadius: '50%', animation: 'spin 0.8s linear infinite', flexShrink: 0 }} />
            )}
            <span style={{ fontSize: '0.75rem', color: s.done ? 'var(--text-muted)' : 'rgba(0,194,255,0.9)', fontFamily: 'var(--mono)' }}>{s.label}</span>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
