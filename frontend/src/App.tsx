import { useEffect, useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useScreening } from './hooks/useScreening';
import { UploadZone } from './components/features/UploadZone';
import { QualityView } from './components/features/QualityView';
import { SymptomView } from './components/features/SymptomView';
import { ResultView } from './components/features/ResultView';
import { ThreeBackground, AuroraCanvas, EyeScanner } from './components/features/VisualSystem';
import {
  Zap, Download, Globe, Microscope, Stethoscope, ArrowRight,
  ShieldCheck, Brain, MessageSquare, HeartPulse, Camera,
  ScanEye, Lock, Share2, ChevronRight
} from 'lucide-react';

const E = [0.22, 1, 0.36, 1] as const;

// ── MARQUEE TICKER ────────────────────────────────────────────────────────────
const TICKER_ITEMS = [
  '1.6B+ people affected by anemia globally',
  '92% model sensitivity on clinical specimens',
  '710 validated conjunctival images',
  '$0 marginal cost per screening',
  'EfficientNet-B0 vision backbone',
  'Qwen-2.5 grounded GenAI guidance',
  'Four-band safety triage system',
  'Smartphone-first — no hardware required',
];

function MarqueeTicker() {
  const items = [...TICKER_ITEMS, ...TICKER_ITEMS];
  return (
    <div className="marquee-strip" style={{
      position:'relative', zIndex:2, overflow:'hidden',
      borderTop:'1px solid rgba(200,0,30,0.15)',
      borderBottom:'1px solid rgba(200,0,30,0.15)',
      background:'linear-gradient(90deg, rgba(200,0,30,0.04) 0%, rgba(200,0,30,0.02) 50%, rgba(200,0,30,0.04) 100%)',
      padding:'0.875rem 0',
    }}>
      {/* fade edges */}
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

// ── #3 MAGNETIC GLASS TILT HOOK ───────────────────────────────────────────────
function useMagneticTilt(ref: React.RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let shimX = 0, shimY = 0;
    let raf: number | null = null;

    const onMove = (e: MouseEvent) => {
      const r = el.getBoundingClientRect();
      shimX = e.clientX - r.left;
      shimY = e.clientY - r.top;
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

// ── GLASS CARD — magnetic tilt + shimmer ─────────────────────────────────────
const GlassCard = ({ children, className = '', style = {}, ...props }: React.HTMLAttributes<HTMLDivElement>) => {
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

// ── DATA ──────────────────────────────────────────────────────────────────────
const STEPS_META = [
  { label: 'Capture',  icon: <Camera size={13} /> },
  { label: 'Quality',  icon: <ShieldCheck size={13} /> },
  { label: 'Symptoms', icon: <HeartPulse size={13} /> },
  { label: 'Result',   icon: <Brain size={13} /> },
] as const;

const WORKFLOW = [
  { icon: <Camera size={20} />,       title: 'Capture Image',    desc: 'High-res macro of the inner lower eyelid conjunctiva.' },
  { icon: <ShieldCheck size={20} />,  title: 'Quality Gate',     desc: 'Vision algorithms reject blurry or misframed images.' },
  { icon: <Brain size={20} />,        title: 'AI Prediction',    desc: 'EfficientNet-B0 estimates hemoglobin from pallor.' },
  { icon: <HeartPulse size={20} />,   title: 'Symptom Fusion',   desc: 'Fatigue, dizziness fused with image biomarkers.' },
  { icon: <MessageSquare size={20} />,title: 'GenAI Guidance',   desc: 'Qwen-2.5 translates AI data into safe next steps.' },
];

const IMPACT_CARDS = [
  { icon: <Globe size={18} />,       title: 'Global Impact',       desc: 'Designed for low-resource settings and remote health workers.' },
  { icon: <Microscope size={18} />,  title: 'Clinical Credibility', desc: 'EfficientNet-B0 validated on 710 clinical specimens.' },
  { icon: <Stethoscope size={18} />, title: 'Safety-First Triage', desc: 'Non-diagnostic language with grounded GenAI guidance.' },
];

const TECH_LAYERS = [
  { icon: <Brain size={20} />,  title: 'Vision Screening Layer', desc: 'EfficientNet-B0 trained to analyze micro-vessel density and conjunctival pallor with sub-millimeter precision.' },
  { icon: <Zap size={20} />,   title: 'Grounded GenAI Layer',   desc: 'Qwen-2.5 constrained by deterministic medical rules — safe, personalized guidance without hallucination.' },
  { icon: <Lock size={20} />,  title: 'Safety Triage System',   desc: 'Four-band triage (Low, Moderate, High, Retake) designed to prioritize user safety over false confidence.' },
];

// ── #7 PREMIUM CURSOR ─────────────────────────────────────────────────────────
function Cursor() {
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
      // Use transform instead of left/top — avoids layout, GPU composited
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

// ── #10 NAVBAR — living glass + mobile hamburger ──────────────────────────────
const NAV_LINKS = ['Technology', 'Workflow', 'Screening'] as const;

function Navbar({ backendUp }: { backendUp: boolean }) {
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', fn, { passive: true });
    return () => window.removeEventListener('scroll', fn);
  }, []);

  // Close menu on scroll
  useEffect(() => {
    if (!menuOpen) return;
    const fn = () => setMenuOpen(false);
    window.addEventListener('scroll', fn, { passive: true, once: true });
    return () => window.removeEventListener('scroll', fn);
  }, [menuOpen]);

  const scrollTo = (id: string) => {
    setMenuOpen(false);
    setTimeout(() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' }), 150);
  };

  return (
    <motion.header
      initial={{ y: -80, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.8, ease: E }}
      style={{
        position: 'fixed',
        top: scrolled ? '0.75rem' : '1.5rem',
        left: '50%', transform: 'translateX(-50%)',
        zIndex: 100, width: 'min(900px, calc(100vw - 2rem))',
        transition: 'top 0.3s ease',
      }}
    >
      {/* ── Pill bar ── */}
      <div
        className="glass nav-pill"
        style={{
          padding: '0.875rem 1.75rem',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
          borderRadius: menuOpen ? '1.5rem 1.5rem 0 0' : '99px',
          background: scrolled ? 'rgba(0,0,0,0.45)' : 'rgba(255,255,255,0.055)',
          backdropFilter: 'blur(32px) saturate(180%)',
          WebkitBackdropFilter: 'blur(32px) saturate(180%)',
          boxShadow: scrolled
            ? 'inset 0 1px 0 rgba(255,255,255,0.22), 0 24px 48px rgba(0,0,0,0.6)'
            : 'inset 0 1px 0 rgba(255,255,255,0.22), 0 16px 40px rgba(0,0,0,0.4)',
          transition: 'background 0.3s, box-shadow 0.3s, border-radius 0.3s',
        }}
      >
        {/* Logo */}
        <div style={{ display:'flex', alignItems:'center', gap:'0.75rem' }}>
          <div className="nav-logo-badge" style={{
            width:32, height:32, borderRadius:'10px',
            background:'linear-gradient(135deg, #C8001E 0%, #E8294A 100%)',
            display:'flex', alignItems:'center', justifyContent:'center',
            fontSize:'0.6rem', fontWeight:800, color:'#fff', letterSpacing:'0.05em',
            fontFamily:'var(--mono)', flexShrink:0,
          }}>AL</div>
          <span style={{ fontWeight:700, fontSize:'0.95rem', letterSpacing:'-0.02em' }}>
            Anemia<span style={{ color:'var(--accent-bright)' }}>Lens</span>
          </span>
          {backendUp && (
            <span className="stat-chip" style={{ padding:'0.2rem 0.6rem', fontSize:'0.5rem', gap:'0.3rem' }}>
              <span style={{ width:5, height:5, borderRadius:'50%', background:'#10B981', display:'inline-block', boxShadow:'0 0 6px #10B981' }} />
              Live
            </span>
          )}
        </div>

        {/* Desktop nav links */}
        <nav className="nav-desktop" style={{ display:'flex', gap:'2rem' }}>
          {NAV_LINKS.map(l => (
            <a key={l} href={`#${l.toLowerCase()}`} className="label-tag nav-link"
              style={{ color:'var(--text-muted)' }}
            >{l}</a>
          ))}
        </nav>

        {/* Desktop CTA */}
        <button
          className="btn btn-glass nav-desktop"
          style={{ padding:'0.55rem 1.25rem', fontSize:'0.65rem', borderRadius:'99px',
            boxShadow:'inset 0 0 0 1px rgba(200,0,30,0.4), inset 0 1px 0 rgba(255,100,100,0.15), 0 0 20px rgba(200,0,30,0.1)' }}
          onClick={() => scrollTo('screening')}
        >
          Get Started <ArrowRight size={12} />
        </button>

        {/* Mobile hamburger */}
        <button
          className="nav-hamburger"
          onClick={() => setMenuOpen(o => !o)}
          aria-label={menuOpen ? 'Close menu' : 'Open menu'}
          style={{
            display:'none', flexDirection:'column', justifyContent:'center', alignItems:'center',
            gap:'5px', width:36, height:36, background:'none', border:'none',
            cursor:'pointer', padding:'4px', borderRadius:'8px',
          }}
        >
          <motion.span animate={{ rotate: menuOpen ? 45 : 0, y: menuOpen ? 7 : 0 }}
            transition={{ duration: 0.25, ease: E }}
            style={{ display:'block', width:20, height:1.5, background:'var(--text)', borderRadius:2, transformOrigin:'center' }} />
          <motion.span animate={{ opacity: menuOpen ? 0 : 1, scaleX: menuOpen ? 0 : 1 }}
            transition={{ duration: 0.2 }}
            style={{ display:'block', width:14, height:1.5, background:'var(--text)', borderRadius:2, alignSelf:'flex-end' }} />
          <motion.span animate={{ rotate: menuOpen ? -45 : 0, y: menuOpen ? -7 : 0 }}
            transition={{ duration: 0.25, ease: E }}
            style={{ display:'block', width:20, height:1.5, background:'var(--text)', borderRadius:2, transformOrigin:'center' }} />
        </button>
      </div>

      {/* ── Mobile drawer ── */}
      <AnimatePresence>
        {menuOpen && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.3, ease: E }}
            style={{
              overflow: 'hidden',
              background: 'rgba(4,4,10,0.92)',
              backdropFilter: 'blur(32px) saturate(180%)',
              WebkitBackdropFilter: 'blur(32px) saturate(180%)',
              borderTop: '1px solid rgba(255,255,255,0.06)',
              borderRadius: '0 0 1.5rem 1.5rem',
              boxShadow: '0 24px 48px rgba(0,0,0,0.6)',
            }}
          >
            <div style={{ padding: '1.25rem 1.75rem 1.75rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
              {NAV_LINKS.map((l, i) => (
                <motion.a
                  key={l}
                  href={`#${l.toLowerCase()}`}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.06, duration: 0.3, ease: E }}
                  onClick={() => scrollTo(l.toLowerCase())}
                  style={{
                    display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                    padding: '0.875rem 1rem', borderRadius: '0.875rem',
                    fontFamily: 'var(--mono)', fontSize: '0.72rem', fontWeight: 500,
                    textTransform: 'uppercase', letterSpacing: '0.15em',
                    color: 'var(--text-muted)',
                    transition: 'background 0.2s, color 0.2s',
                  }}
                  onTouchStart={e => (e.currentTarget.style.background = 'rgba(255,255,255,0.05)')}
                  onTouchEnd={e => (e.currentTarget.style.background = 'transparent')}
                >
                  {l}
                  <ChevronRight size={14} style={{ color: 'var(--text-dim)' }} />
                </motion.a>
              ))}

              {/* Divider */}
              <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '0.5rem 0' }} />

              {/* CTA full-width */}
              <motion.button
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.22, duration: 0.3, ease: E }}
                className="btn btn-primary"
                style={{ width: '100%', padding: '0.875rem', fontSize: '0.72rem', borderRadius: '0.875rem' }}
                onClick={() => scrollTo('screening')}
              >
                <ScanEye size={15} /> Start Screening
              </motion.button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.header>
  );
}

// ── #6 HERO — variable font animation ────────────────────────────────────────
function Hero() {
  return (
    <section className="section-hero" style={{ position:'relative', zIndex:1, minHeight:'100vh', display:'flex', alignItems:'center', padding:'0 4rem' }}>
      <div className="hero-grid" style={{ display:'grid', gridTemplateColumns:'1.15fr 0.85fr', gap:'5rem', width:'100%', maxWidth:1400, margin:'0 auto' }}>

        {/* Left */}
        <div style={{ display:'flex', flexDirection:'column', gap:'2.5rem', paddingTop:'7rem' }}>
          {/* Eyebrow */}
          <motion.div initial={{ opacity:0, y:16 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.2, duration:0.6 }}>
            <span className="stat-chip" style={{ gap:'0.5rem' }}>
              <span style={{ width:6, height:6, borderRadius:'50%', background:'var(--crimson)', display:'inline-block', animation:'blink 1.5s infinite' }} />
              <span className="label-tag" style={{ color:'var(--accent-bright)' }}>AI-Powered Screening Hub</span>
            </span>
          </motion.div>

          {/* Headline */}
          <h1 className="display-hero">
            <span className="hero-line-1" style={{ display:'block', fontWeight:900, color:'var(--text)' }}>See what</span>
            <span className="hero-line-2" style={{ display:'block', fontStyle:'italic', fontWeight:300, color:'var(--text-muted)', fontFamily:'var(--serif)' }}>your blood</span>
            <span className="hero-line-3" style={{ display:'block', fontWeight:900 }}>
              <span style={{ background:'linear-gradient(135deg, var(--accent-bright) 0%, #FF6B8A 100%)', WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent', backgroundClip:'text' }}>reveals.</span>
            </span>
          </h1>

          {/* Sub */}
          <motion.p
            initial={{ opacity:0, y:20 }} animate={{ opacity:1, y:0 }}
            transition={{ delay:0.45, duration:0.7 }}
            style={{ fontSize:'1.05rem', color:'var(--text-muted)', lineHeight:1.7, maxWidth:460 }}
          >
            AnemiaLens transforms your smartphone into a first-pass screening tool. Clinical-grade vision AI analyzes conjunctival pallor so you can act sooner, safely.
          </motion.p>

          {/* CTAs */}
          <motion.div
            initial={{ opacity:0, y:20 }} animate={{ opacity:1, y:0 }}
            transition={{ delay:0.55, duration:0.7 }}
            style={{ display:'flex', gap:'1rem', flexWrap:'wrap' }}
          >
            <button className="btn btn-primary"
              onClick={() => document.getElementById('screening')?.scrollIntoView({ behavior:'smooth' })}>
              <ScanEye size={15} /> Start Screening
            </button>
            <button className="btn btn-glass">
              Impact Narrative <ArrowRight size={13} />
            </button>
          </motion.div>

          {/* Stats — large serif display like prototype */}
          <motion.div
            initial={{ opacity:0 }} animate={{ opacity:1 }}
            transition={{ delay:0.7, duration:0.8 }}
            style={{ display:'flex', gap:'3.5rem', paddingTop:'2.5rem', borderTop:'1px solid var(--glass-border)', marginTop:'0.5rem' }}
          >
            {[['1.6B+','Anemia Cases Globally'],['92%','Model Sensitivity'],['710','Clinical Specimens']].map(([val, label]) => (
              <div key={label}>
                <div style={{ fontFamily:'var(--serif)', fontSize:'2.2rem', fontWeight:300, color:'var(--text)', lineHeight:1 }}>
                  {val.replace(/[^0-9.]/g,'')}
                  <span style={{ background:'linear-gradient(135deg, var(--accent-bright) 0%, #FF6B8A 100%)', WebkitBackgroundClip:'text', WebkitTextFillColor:'transparent', backgroundClip:'text', fontSize:'1.4rem' }}>{val.replace(/[0-9.]/g,'')}</span>
                </div>
                <div className="label-tag" style={{ marginTop:'0.4rem' }}>{label}</div>
              </div>
            ))}
          </motion.div>
        </div>

        {/* Right — Eye with orbit rings */}
        <motion.div
          className="hero-eye"
          initial={{ opacity:0, scale:0.85 }} animate={{ opacity:1, scale:1 }}
          transition={{ duration:1.1, delay:0.2, ease:E }}
          style={{ display:'flex', alignItems:'center', justifyContent:'center', paddingTop:'6rem' }}
        >
          <div style={{ position:'relative', display:'flex', alignItems:'center', justifyContent:'center' }}>
            {/* Pulse rings */}
            {[0,1,2].map(i => (
              <div key={i} style={{
                position:'absolute',
                inset: `${-20 - i*22}px`,
                borderRadius:'50%',
                border:`1px solid rgba(200,0,30,${0.15 - i*0.04})`,
                animation:`pulse-ring ${2 + i*0.8}s ease-out ${i*0.6}s infinite`,
                pointerEvents:'none',
              }} />
            ))}
            {/* Orbit ring 1 — clockwise */}
            <div style={{
              position:'absolute', inset:-50, borderRadius:'50%',
              border:'1px solid rgba(255,255,255,0.05)',
              animation:'orbit-spin 25s linear infinite',
              pointerEvents:'none',
            }}>
              <div style={{ position:'absolute', top:-4, left:'50%', transform:'translateX(-50%)', width:8, height:8, borderRadius:'50%', background:'var(--accent-bright)', boxShadow:'0 0 12px var(--accent-bright)' }} />
            </div>
            {/* Orbit ring 2 — counter-clockwise */}
            <div style={{
              position:'absolute', inset:-75, borderRadius:'50%',
              border:'1px dashed rgba(200,0,30,0.15)',
              animation:'orbit-spin 40s linear infinite reverse',
              pointerEvents:'none',
            }}>
              <div style={{ position:'absolute', bottom:-4, left:'50%', transform:'translateX(-50%)', width:5, height:5, borderRadius:'50%', background:'rgba(200,0,30,0.6)' }} />
            </div>
            <EyeScanner />
          </div>
        </motion.div>
      </div>
    </section>
  );
}

// ── CHALLENGE SECTION ─────────────────────────────────────────────────────────
function Challenge() {
  const cardRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = cardRef.current;
    if (!el) return;
    const onMove = (e: MouseEvent) => {
      const r = el.getBoundingClientRect();
      const x = (e.clientX - r.left) / r.width - 0.5;
      const y = (e.clientY - r.top) / r.height - 0.5;
      el.style.transform = `perspective(800px) rotateY(${x*8}deg) rotateX(${-y*8}deg) scale3d(1.02,1.02,1.02)`;
    };
    const onLeave = () => { el.style.transform = 'perspective(800px) rotateY(0deg) rotateX(0deg) scale3d(1,1,1)'; };
    el.addEventListener('mousemove', onMove);
    el.addEventListener('mouseleave', onLeave);
    return () => { el.removeEventListener('mousemove', onMove); el.removeEventListener('mouseleave', onLeave); };
  }, []);

  return (
    <section style={{ position:'relative', zIndex:1, padding:'10rem 4rem' }} className="section-pad">
      {/* Ambient orb */}
      <div style={{ position:'absolute', width:500, height:500, borderRadius:'50%', background:'radial-gradient(circle, rgba(200,0,30,0.08) 0%, transparent 70%)', top:'20%', right:'-10%', filter:'blur(40px)', pointerEvents:'none' }} />

      <div className="challenge-grid" style={{ maxWidth:1200, margin:'0 auto', display:'grid', gridTemplateColumns:'1fr 1fr', gap:'6rem', alignItems:'center' }}>

        <motion.div
          ref={cardRef}
          className="glass glass-shimmer reveal"
          initial={{ opacity:0, x:-30 }} whileInView={{ opacity:1, x:0 }}
          viewport={{ once:true }} transition={{ duration:0.8, ease:E }}
          style={{
            padding:'3.5rem', borderLeft:'3px solid var(--crimson)',
            boxShadow:'inset 0 1px 0 rgba(255,255,255,0.12), -4px 0 40px rgba(200,0,30,0.12), 0 48px 100px rgba(0,0,0,0.6)',
            transition:'transform 0.1s ease',
          }}
        >
          <div className="section-eyebrow" style={{ marginBottom:'1.5rem' }}>The Challenge</div>
          <h2 style={{ fontFamily:'var(--serif)', fontSize:'clamp(2.2rem,4vw,3.2rem)', fontWeight:700, lineHeight:1.05, letterSpacing:'-0.03em', marginBottom:'1.75rem' }}>
            Bridging the<br/>
            <span style={{ fontStyle:'italic', fontWeight:300, color:'var(--text-muted)' }}>Screening Gap.</span>
          </h2>
          <p style={{ fontSize:'0.95rem', color:'var(--text-muted)', lineHeight:1.75, marginBottom:'2.5rem' }}>
            Anemia affects 25% of the world's population, yet detection remains expensive and slow. Early action is delayed by clinic distance, blood testing costs, and lack of specialized hardware.
          </p>
          <div style={{ display:'flex', gap:'3rem' }}>
            {[['$0','Marginal Cost'],['100%','Smartphone-First']].map(([v,l]) => (
              <div key={l}>
                <div style={{ fontFamily:'var(--serif)', fontSize:'2.5rem', fontWeight:600, color:'var(--text)' }}>{v}</div>
                <div className="label-tag" style={{ marginTop:'0.3rem' }}>{l}</div>
              </div>
            ))}
          </div>
        </motion.div>

        <div style={{ display:'flex', flexDirection:'column', gap:'1.25rem' }}>
          {IMPACT_CARDS.map((c, i) => (
            <motion.div
              key={c.title}
              className="glass glass-hover glass-shimmer"
              initial={{ opacity:0, x:30 }} whileInView={{ opacity:1, x:0 }}
              viewport={{ once:true }} transition={{ duration:0.6, delay:i*0.1, ease:E }}
              style={{ padding:'1.75rem 2rem', display:'flex', gap:'1.5rem', alignItems:'center' }}
            >
              <div style={{
                width:48, height:48, borderRadius:'0.875rem', flexShrink:0,
                background:'linear-gradient(135deg, rgba(200,0,30,0.2) 0%, rgba(200,0,30,0.06) 100%)',
                border:'1px solid rgba(200,0,30,0.25)',
                display:'flex', alignItems:'center', justifyContent:'center',
                color:'var(--accent-bright)',
                boxShadow:'0 0 20px rgba(200,0,30,0.15)',
              }}>{c.icon}</div>
              <div>
                <h4 style={{ fontWeight:700, fontSize:'0.9rem', marginBottom:'0.3rem' }}>{c.title}</h4>
                <p style={{ fontSize:'0.78rem', color:'var(--text-muted)', lineHeight:1.55 }}>{c.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── WORKFLOW STEPPER ──────────────────────────────────────────────────────────
function WorkflowStepper() {
  const [active, setActive] = useState<number | null>(null);
  return (
    <section id="workflow" style={{ position:'relative', zIndex:1, padding:'10rem 4rem', background:'linear-gradient(180deg, transparent 0%, rgba(2,2,8,0.6) 50%, transparent 100%)' }} className="section-pad">
      <div style={{ maxWidth:1200, margin:'0 auto' }}>
        <motion.div
          initial={{ opacity:0, y:30 }} whileInView={{ opacity:1, y:0 }}
          viewport={{ once:true }} transition={{ duration:0.7 }}
          style={{ textAlign:'center', marginBottom:'6rem' }}
        >
          <div className="section-eyebrow" style={{ marginBottom:'1.25rem' }}>The Architecture</div>
          <h2 style={{ fontFamily:'var(--serif)', fontSize:'clamp(2.5rem,5vw,4.5rem)', fontWeight:700, lineHeight:1.0, letterSpacing:'-0.03em' }}>
            Five Steps to<br/>
            <span style={{ fontStyle:'italic', fontWeight:300, color:'var(--text-muted)' }}>Screening Clarity.</span>
          </h2>
        </motion.div>

        {/* 5-column grid */}
        <div className="workflow-5col" style={{ display:'grid', gridTemplateColumns:'repeat(5,1fr)', gap:'1.25rem', position:'relative' }}>
          {/* Connector line */}
          <div style={{ position:'absolute', top:52, left:'10%', right:'10%', height:1, background:'linear-gradient(90deg, transparent, var(--glass-border) 20%, var(--glass-border) 80%, transparent)', zIndex:0, pointerEvents:'none' }} />

          {WORKFLOW.map((step, i) => (
            <motion.div
              key={step.title}
              className="glass glass-hover"
              initial={{ opacity:0, y:40 }} whileInView={{ opacity:1, y:0 }}
              viewport={{ once:true }} transition={{ duration:0.6, delay:i*0.1, ease:E }}
              onClick={() => setActive(active===i ? null : i)}
              style={{
                padding:'2rem 1.25rem', textAlign:'center', display:'flex', flexDirection:'column', gap:'1rem',
                position:'relative', zIndex:1, cursor:'pointer',
                background: active===i ? 'linear-gradient(135deg, rgba(200,0,30,0.12) 0%, rgba(200,0,30,0.04) 100%)' : undefined,
                borderColor: active===i ? 'rgba(200,0,30,0.3)' : undefined,
                boxShadow: active===i ? '0 20px 60px rgba(0,0,0,0.5), 0 0 30px rgba(200,0,30,0.12)' : undefined,
              }}
            >
              <div style={{
                width:52, height:52, borderRadius:'1rem', margin:'0 auto',
                background: active===i
                  ? 'linear-gradient(135deg, rgba(200,0,30,0.3) 0%, rgba(200,0,30,0.1) 100%)'
                  : 'rgba(255,255,255,0.04)',
                border:`1px solid ${active===i ? 'rgba(200,0,30,0.35)' : 'var(--glass-border)'}`,
                display:'flex', alignItems:'center', justifyContent:'center',
                color: active===i ? 'var(--accent-bright)' : 'var(--text-muted)',
                transition:'all 0.3s var(--ease)',
                boxShadow: active===i ? '0 0 20px rgba(200,0,30,0.25)' : 'none',
              }}>{step.icon}</div>

              <div style={{ fontSize:'0.5rem', fontFamily:'var(--mono)', color:'var(--text-dim)', textTransform:'uppercase', letterSpacing:'0.15em' }}>Step {i+1}</div>
              <h4 style={{ fontWeight:700, fontSize:'0.8rem', textTransform:'uppercase', letterSpacing:'0.05em', color: active===i ? 'var(--text)' : 'var(--text-muted)' }}>{step.title}</h4>
              <p style={{ fontSize:'0.7rem', color:'var(--text-dim)', lineHeight:1.6 }}>{step.desc}</p>

              {i < WORKFLOW.length-1 && (
                <div style={{ position:'absolute', top:48, right:-10, zIndex:10, color:'var(--text-dim)' }}>
                  <ChevronRight size={18} />
                </div>
              )}
            </motion.div>
          ))}
        </div>

        {/* Expanded detail panel */}
        <div className={`step-panel ${active !== null ? 'open' : ''}`}>
          <AnimatePresence mode="wait">
            {active !== null && (
              <motion.div
                key={active}
                initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }}
                exit={{ opacity:0, y:-8 }}
                transition={{ duration:0.35, ease:E }}
              >
                <GlassCard style={{ padding:'2.5rem 3rem', display:'flex', gap:'2rem', alignItems:'center', marginTop:'1.5rem' }}>
                  <div style={{
                    width:56, height:56, borderRadius:'1rem', flexShrink:0,
                    background:'linear-gradient(135deg, rgba(200,0,30,0.25) 0%, rgba(200,0,30,0.08) 100%)',
                    border:'1px solid rgba(200,0,30,0.3)',
                    display:'flex', alignItems:'center', justifyContent:'center',
                    color:'var(--accent-bright)', boxShadow:'0 0 24px rgba(200,0,30,0.2)',
                  }}>{WORKFLOW[active].icon}</div>
                  <div>
                    <h3 style={{ fontWeight:700, fontSize:'1.1rem', marginBottom:'0.5rem' }}>{WORKFLOW[active].title}</h3>
                    <p style={{ color:'var(--text-muted)', fontSize:'0.9rem', lineHeight:1.65 }}>{WORKFLOW[active].desc}</p>
                  </div>
                  <div style={{ marginLeft:'auto', color:'var(--text-dim)' }}><ChevronRight size={20} /></div>
                </GlassCard>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </section>
  );
}

// ── QWEN LOADING OVERLAY ──────────────────────────────────────────────────────
function QwenLoadingOverlay() {
  const stages = [
    { label: 'Running vision model', done: true },
    { label: 'Analyzing conjunctival pallor', done: true },
    { label: 'Calculating triage band', done: true },
    { label: 'Qwen 2.5 generating guidance...', done: false },
  ];
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }}
      style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 420, gap: '2rem' }}
    >
      {/* Pulsing brain icon */}
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
          Qwen 2.5 is generating your personalized guidance
        </div>
      </div>

      {/* Stage list */}
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

// ── SCREENING SECTION ─────────────────────────────────────────────────────────
function ScreeningSection() {
  const {
    step, setStep, file, previewUrl, symptoms, toggleSymptom,
    quality, analysis, loading, error, backendUp,
    pickFile, runQuality, runAnalysis, loadSample, reset, symptomLabels
  } = useScreening();

  const handleDownload = (shareText: string) => {
    const blob = new Blob([shareText], { type:'text/plain' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href = url; a.download = 'anemialens-report.txt'; a.click();
    URL.revokeObjectURL(url);
  };

  const canStep = (i: number) =>
    i===0 || (i===1 && !!file) || (i===2 && !!quality) || (i===3 && !!analysis);

  return (
    <section id="screening" style={{ position:'relative', zIndex:1, padding:'10rem 4rem' }} className="section-pad">
      <div style={{ maxWidth:1200, margin:'0 auto' }}>
        <motion.div
          initial={{ opacity:0, y:30 }} whileInView={{ opacity:1, y:0 }}
          viewport={{ once:true }} transition={{ duration:0.7 }}
          style={{ textAlign:'center', marginBottom:'5rem' }}
        >
          <div className="section-eyebrow" style={{ marginBottom:'1.25rem' }}>Diagnostic Hub</div>
          <h2 style={{ fontFamily:'var(--serif)', fontSize:'clamp(2.5rem,5vw,4.5rem)', fontWeight:700, lineHeight:1.0, letterSpacing:'-0.03em' }}>
            Interactive<br/>
            <span style={{ fontStyle:'italic', fontWeight:300, color:'var(--text-muted)' }}>Screening Experience.</span>
          </h2>
        </motion.div>

        {/* ── Premium progress stepper ── */}
        <div className="screening-progress" style={{ marginBottom:'4rem' }}>
          {STEPS_META.map((s, i) => (
            <>
              <div
                key={s.label}
                className={`screening-step-node ${step===i?'active':''} ${step>i?'done':''}`}
                onClick={() => canStep(i) && setStep(i)}
                style={{ opacity: canStep(i) ? 1 : 0.45, cursor: canStep(i) ? 'pointer' : 'default' }}
              >
                <div className={`screening-step-circle ${step===i?'active':''} ${step>i?'done':''}`}>
                  {step > i
                    ? <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="20 6 9 17 4 12"/></svg>
                    : <span style={{ fontFamily:'var(--mono)', fontSize:'0.65rem' }}>{String(i+1).padStart(2,'0')}</span>
                  }
                </div>
                <span className="screening-step-label">{s.label}</span>
              </div>
              {i < STEPS_META.length-1 && (
                <div className={`screening-step-line ${step>i?'done':''}`} />
              )}
            </>
          ))}
        </div>

        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0 }}
              className="glass"
              style={{ padding:'1.25rem 1.75rem', marginBottom:'2rem', borderLeft:'3px solid #EF4444',
                background:'rgba(239,68,68,0.06)', display:'flex', alignItems:'center', gap:'1rem' }}
            >
              <span style={{ fontSize:'0.85rem', color:'#FCA5A5' }}>{error}</span>
              <button onClick={reset} className="label-tag" style={{ marginLeft:'auto', color:'#FCA5A5', cursor:'none' }}>Dismiss</button>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence mode="wait">
          <motion.div
            key={step}
            initial={{ opacity:0, x:24 }} animate={{ opacity:1, x:0 }} exit={{ opacity:0, x:-24 }}
            transition={{ duration:0.45, ease:E }}
          >
            {step===0 && (
              <div className="capture-grid" style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:'4rem', alignItems:'start' }}>
                <div style={{ display:'flex', flexDirection:'column', gap:'2rem' }}>
                  <div>
                    <div className="section-eyebrow" style={{ marginBottom:'0.75rem' }}>Phase 01</div>
                    <h3 style={{ fontFamily:'var(--serif)', fontSize:'2.2rem', fontWeight:700, lineHeight:1.1, letterSpacing:'-0.03em', marginBottom:'1rem' }}>Initial Image Capture</h3>
                    <p style={{ color:'var(--text-muted)', lineHeight:1.7, fontSize:'0.9rem' }}>
                      High-resolution macro capture of the conjunctival region. Align your phone horizontally with the lower eyelid pulled down.
                    </p>
                  </div>
                  <div style={{ display:'flex', flexDirection:'column', gap:'0.75rem' }}>
                    <div className="label-tag" style={{ marginBottom:'0.5rem' }}>Protocol Check</div>
                    {['Bright, indirect natural daylight','No flash or harsh shadows','Lower eyelid fully exposed','One eye centered in frame'].map(tip => (
                      <div key={tip} style={{ display:'flex', alignItems:'center', gap:'0.75rem' }}>
                        <div style={{ width:18, height:18, borderRadius:'50%', background:'rgba(200,0,30,0.15)', border:'1px solid rgba(200,0,30,0.3)', display:'flex', alignItems:'center', justifyContent:'center', flexShrink:0 }}>
                          <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="var(--accent-bright)" strokeWidth="3" strokeLinecap="round"><polyline points="20 6 9 17 4 12"/></svg>
                        </div>
                        <span style={{ fontSize:'0.82rem', color:'var(--text-muted)' }}>{tip}</span>
                      </div>
                    ))}
                  </div>
                  <div>
                    <div className="label-tag" style={{ marginBottom:'1rem' }}>Demo Profiles</div>
                    <div style={{ display:'flex', gap:'0.75rem', flexWrap:'wrap' }}>
                      {[
                        { id:'low',      label:'Low Risk',     img:'/demo-cases/low-risk-demo.jpg' },
                        { id:'moderate', label:'Moderate',     img:'/demo-cases/moderate-risk-demo.jpg' },
                        { id:'high',     label:'High Concern', img:'/demo-cases/high-concern-demo.jpg' },
                      ].map(s => (
                        <button key={s.id} className="btn btn-glass glass-shimmer"
                          style={{ padding:'0.5rem 1rem', fontSize:'0.65rem', gap:'0.5rem', borderRadius:'0.75rem' }}
                          onClick={() => loadSample(s.img, { fatigue:false, dizziness:false, pale_skin:false, shortness_of_breath:false, heavy_menstrual_bleeding:null, poor_diet_low_iron:false }, s.id)}
                        >
                          <img src={s.img} alt={s.label} style={{ width:20, height:20, borderRadius:4, objectFit:'cover' }} />
                          {s.label}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>
                <UploadZone onFileSelect={pickFile} previewUrl={previewUrl} onClear={reset} onRunQuality={runQuality} loading={loading} disabled={!file} />
              </div>
            )}
            {step===1 && quality && <QualityView quality={quality} onContinue={() => setStep(2)} onBack={() => setStep(0)} loading={loading} />}
            {step===2 && !loading && <SymptomView symptoms={symptoms} toggleSymptom={toggleSymptom} onContinue={runAnalysis} onBack={() => setStep(1)} loading={loading} symptomLabels={symptomLabels} />}
            {step===2 && loading && <QwenLoadingOverlay />}
            {step===3 && analysis && <ResultView analysis={analysis} onReset={reset} onDownload={() => handleDownload(analysis.handoff_summary.share_text)} />}
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}

// ── #9 TERMINAL CARD — char-by-char typewriter ────────────────────────────────
// ── #11 TECH SECTION — icon rotate on hover ───────────────────────────────────
function TechSection() {
  return (
    <section id="technology" style={{ position:'relative', zIndex:1, padding:'10rem 4rem', background:'linear-gradient(180deg, transparent 0%, rgba(2,2,8,0.5) 100%)' }} className="section-pad">
      {/* Ambient orb */}
      <div style={{ position:'absolute', width:500, height:500, borderRadius:'50%', background:'radial-gradient(circle, rgba(200,0,30,0.08) 0%, transparent 70%)', bottom:'0%', right:'-10%', filter:'blur(40px)', pointerEvents:'none' }} />

      <div className="tech-grid" style={{ maxWidth:1200, margin:'0 auto', display:'grid', gridTemplateColumns:'1fr 1fr', gap:'7rem', alignItems:'center' }}>

        <div style={{ display:'flex', flexDirection:'column', gap:'3rem' }}>
          <motion.div initial={{ opacity:0, y:30 }} whileInView={{ opacity:1, y:0 }} viewport={{ once:true }} transition={{ duration:0.7 }}>
            <div className="section-eyebrow" style={{ marginBottom:'1.25rem' }}>Architecture</div>
            <h2 style={{ fontFamily:'var(--serif)', fontSize:'clamp(2.2rem,4vw,3.5rem)', fontWeight:700, lineHeight:1.05, letterSpacing:'-0.03em' }}>
              The Intelligence<br/>
              <span style={{ fontStyle:'italic', fontWeight:300, color:'var(--text-muted)' }}>Framework.</span>
            </h2>
          </motion.div>

          <div style={{ display:'flex', flexDirection:'column', gap:'2.25rem' }}>
            {TECH_LAYERS.map((item, i) => (
              <motion.div
                key={item.title}
                initial={{ opacity:0, x:-20 }} whileInView={{ opacity:1, x:0 }}
                viewport={{ once:true }} transition={{ duration:0.6, delay:i*0.1, ease:E }}
                style={{ display:'flex', gap:'1.75rem' }}
              >
                <div
                  className="tech-icon"
                  style={{
                    width:52, height:52, borderRadius:'1rem', flexShrink:0,
                    background:'rgba(255,255,255,0.055)', border:'1px solid rgba(255,255,255,0.11)',
                    backdropFilter:'blur(20px)', WebkitBackdropFilter:'blur(20px)',
                    display:'flex', alignItems:'center', justifyContent:'center',
                    color:'var(--accent-bright)',
                    boxShadow:'inset 0 1px 0 rgba(255,255,255,0.12)',
                  }}
                >{item.icon}</div>
                <div>
                  <h4 style={{ fontWeight:600, fontSize:'0.95rem', marginBottom:'0.4rem' }}>{item.title}</h4>
                  <p style={{ fontSize:'0.82rem', color:'var(--text-muted)', lineHeight:1.65 }}>{item.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        {/* Tech layer cards — right side */}
        <div style={{ display:'flex', flexDirection:'column', gap:'1.5rem' }}>
          {TECH_LAYERS.map((item, i) => (
            <motion.div
              key={item.title}
              className="glass glass-hover glass-shimmer"
              initial={{ opacity:0, x:30 }} whileInView={{ opacity:1, x:0 }}
              viewport={{ once:true }} transition={{ duration:0.6, delay:i*0.1, ease:E }}
              style={{ padding:'2rem', display:'flex', gap:'1.5rem', alignItems:'flex-start' }}
            >
              <div style={{
                width:52, height:52, borderRadius:'1rem', flexShrink:0,
                background:'linear-gradient(135deg, rgba(200,0,30,0.2) 0%, rgba(200,0,30,0.06) 100%)',
                border:'1px solid rgba(200,0,30,0.25)',
                display:'flex', alignItems:'center', justifyContent:'center',
                color:'var(--accent-bright)',
                boxShadow:'0 0 20px rgba(200,0,30,0.15)',
              }}>{item.icon}</div>
              <div>
                <h4 style={{ fontWeight:700, fontSize:'0.95rem', marginBottom:'0.4rem' }}>{item.title}</h4>
                <p style={{ fontSize:'0.82rem', color:'var(--text-muted)', lineHeight:1.65 }}>{item.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── FOOTER ────────────────────────────────────────────────────────────────────
function Footer() {
  return (
    <footer style={{ position:'relative', zIndex:1, borderTop:'1px solid var(--glass-border)' }}>
      <div className="glass" style={{ borderRadius:0, padding:'5rem 4rem 3rem', background:'rgba(2,2,8,0.7)' }}>
        <div style={{ maxWidth:1400, margin:'0 auto' }}>
          <div style={{ display:'grid', gridTemplateColumns:'1.5fr 1fr 1fr', gap:'5rem', marginBottom:'4rem' }}>
            <div>
              <div style={{ display:'flex', alignItems:'center', gap:'0.75rem', marginBottom:'1.5rem' }}>
                <div style={{ width:38, height:38, borderRadius:'10px', background:'linear-gradient(135deg, #C8001E, #E8294A)', display:'flex', alignItems:'center', justifyContent:'center', fontSize:'0.7rem', fontWeight:900, color:'#fff', fontFamily:'var(--mono)', boxShadow:'0 6px 20px rgba(200,0,30,0.4)' }}>AL</div>
                <span style={{ fontWeight:800, fontSize:'1.1rem', letterSpacing:'-0.02em' }}>Anemia<span style={{ color:'var(--accent-bright)' }}>Lens</span></span>
              </div>
              <p style={{ fontSize:'0.82rem', color:'var(--text-dim)', lineHeight:1.8, maxWidth:340, marginBottom:'2rem' }}>
                Smartphone-first anemia screening powered by computer vision and grounded GenAI. Designed for accessibility, safety, and clinical credibility.
              </p>
              <div style={{ display:'flex', gap:'0.6rem', flexWrap:'wrap' }}>
                {['UN SDG 3: Good Health','UN SDG 10: Reduced Inequality'].map(tag => (
                  <span key={tag} className="stat-chip" style={{ fontSize:'0.52rem', padding:'0.3rem 0.75rem' }}>{tag}</span>
                ))}
              </div>
            </div>
            {[
              { title:'Technology', links:['Vision Backbone','GenAI Grounding','Safety Gating','Clinical Brief'] },
              { title:'Resources',  links:['Impact Narrative','Research Hub','Deployment Guide','Legal Disclaimer'] },
            ].map(col => (
              <div key={col.title}>
                <div className="label-tag" style={{ color:'var(--text)', marginBottom:'1.5rem' }}>{col.title}</div>
                <ul style={{ listStyle:'none', display:'flex', flexDirection:'column', gap:'0.875rem' }}>
                  {col.links.map(l => (
                    <li key={l} style={{ fontSize:'0.82rem', color:'var(--text-dim)', cursor:'pointer', transition:'color 0.2s' }}
                      onMouseEnter={e => (e.currentTarget.style.color = 'var(--text)')}
                      onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-dim)')}
                    >{l}</li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
          <div style={{ paddingTop:'2.5rem', borderTop:'1px solid var(--glass-border)', display:'flex', justifyContent:'space-between', alignItems:'center', flexWrap:'wrap', gap:'1rem' }}>
            <div className="label-tag">© 2026 AnemiaLens AI Diagnostics. All rights reserved.</div>
            <div style={{ fontSize:'0.6rem', color:'var(--text-dim)', maxWidth:520, textAlign:'right', fontStyle:'italic', lineHeight:1.6 }}>
              Disclaimer: AnemiaLens is a screening tool, not a diagnostic device. Results must be confirmed with clinical blood testing.
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
}

// ── ROOT — #8 liquid scroll momentum ─────────────────────────────────────────
export default function App() {
  const { backendUp } = useScreening();



  // Scroll reveal with stagger
  useEffect(() => {
    const obs = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (!entry.isIntersecting) return;
        const el = entry.target as HTMLElement;
        const children = Array.from(el.querySelectorAll<HTMLElement>('.reveal-child'));
        if (children.length) {
          children.forEach((child, i) => { setTimeout(() => child.classList.add('visible'), i * 80); });
        } else {
          el.classList.add('visible');
        }
        obs.unobserve(el);
      });
    }, { threshold: 0.1 });
    document.querySelectorAll('.reveal, .reveal-group').forEach(el => obs.observe(el));
    return () => obs.disconnect();
  }, []);

  return (
    <div style={{ position:'relative', minHeight:'100vh', background:'var(--void)' }}>
      <Cursor />
      <AuroraCanvas />
      <ThreeBackground />
      <Navbar backendUp={backendUp} />
      <main style={{ position:'relative', zIndex:1 }}>
        <Hero />
        <MarqueeTicker />
        <div className="section-divider" />
        <Challenge />
        <div className="section-divider" />
        <WorkflowStepper />
        <div className="section-divider" />
        <ScreeningSection />
        <div className="section-divider" />
        <TechSection />
      </main>
      <Footer />
    </div>
  );
}
