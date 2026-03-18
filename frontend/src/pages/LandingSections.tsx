import { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Zap, Globe, Microscope, Stethoscope, ArrowRight,
  ShieldCheck, Brain, MessageSquare, HeartPulse, Camera,
  ScanEye, Lock, Share2, ChevronRight
} from 'lucide-react';
import { EyeScanner } from '../components/features/VisualSystem';
import { E, GlassCard } from '../components/screening/SharedUI';

// ── COUNT-UP ──────────────────────────────────────────────────────────────────
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
  }, [target, duration, start]);
  return val;
}

function HeroStat({ raw, suffix, label, target, div }: { raw: string; suffix: string; label: string; target: number; div: number }) {
  const [started, setStarted] = useState(false);
  const count = useCountUp(target, 1600, started);

  useEffect(() => {
    const timer = setTimeout(() => setStarted(true), 800);
    return () => clearTimeout(timer);
  }, []);

  const display = div > 1 ? (count / div).toFixed(2) : String(count);

  return (
    <div className="hero-stat glass-border-animate" style={{ padding:'0.75rem 1rem', borderRadius:'0.875rem', background:'rgba(255,255,255,0.02)', border:'1px solid rgba(255,255,255,0.06)' }}>
      <div style={{ fontFamily:'var(--serif)', fontSize:'2.2rem', fontWeight:300, color:'var(--text)', lineHeight:1 }}>
        <span className="stat-number">{display}</span>
        <span className="text-crimson-gold" style={{ fontSize:'1.4rem' }}>{suffix}</span>
      </div>
      <div className="label-tag" style={{ marginTop:'0.4rem' }}>{label}</div>
    </div>
  );
}

// ── HERO ──────────────────────────────────────────────────────────────────────
export function Hero() {
  return (
    <section className="section-hero" style={{ position:'relative', zIndex:1, minHeight:'100vh', display:'flex', alignItems:'center', padding:'0 4rem' }}>
      <div className="hero-grid" style={{ display:'grid', gridTemplateColumns:'1.15fr 0.85fr', gap:'5rem', width:'100%', maxWidth:1400, margin:'0 auto' }}>

        <div style={{ display:'flex', flexDirection:'column', gap:'2.5rem', paddingTop:'7rem' }}>
          <motion.div initial={{ opacity:0, y:16 }} animate={{ opacity:1, y:0 }} transition={{ delay:0.2, duration:0.6 }}>
            <span className="stat-chip" style={{ gap:'0.5rem' }}>
              <span style={{ width:6, height:6, borderRadius:'50%', background:'var(--crimson)', display:'inline-block', animation:'blink 1.5s infinite' }} />
              <span className="label-tag" style={{ color:'var(--accent-bright)' }}>AI-Powered Screening Hub</span>
            </span>
          </motion.div>

          <h1 className="display-hero">
            <span className="hero-line-1" style={{ display:'block', fontWeight:900, color:'var(--text)' }}>See what</span>
            <span className="hero-line-2" style={{ display:'block', fontStyle:'italic', fontWeight:300, color:'var(--text-muted)', fontFamily:'var(--serif)' }}>your blood</span>
            <span className="hero-line-3" style={{ display:'block', fontWeight:900 }}>
              <span className="text-crimson-gold">reveals.</span>
            </span>
          </h1>

          <motion.p
            initial={{ opacity:0, y:20 }} animate={{ opacity:1, y:0 }}
            transition={{ delay:0.45, duration:0.7 }}
            style={{ fontSize:'1.05rem', color:'var(--text-muted)', lineHeight:1.7, maxWidth:460 }}
          >
            AnemiaLens transforms your smartphone into a first-pass screening tool. Clinical-grade vision AI analyzes conjunctival pallor so you can act sooner, safely.
          </motion.p>

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

          <motion.div
            initial={{ opacity:0 }} animate={{ opacity:1 }}
            transition={{ delay:0.7, duration:0.8 }}
            style={{ display:'flex', gap:'2rem', paddingTop:'2.5rem', borderTop:'1px solid var(--glass-border)', marginTop:'0.5rem', flexWrap:'wrap' }}
          >
            {[
              { raw:'1.92', suffix:'B+', label:'Anemia Cases Globally', target:192, div:100 },
              { raw:'92',   suffix:'%',  label:'Model Sensitivity',     target:92,  div:1 },
              { raw:'710',  suffix:'',   label:'Clinical Specimens',    target:710, div:1 },
            ].map(({ raw, suffix, label, target, div }) => (
              <HeroStat key={label} raw={raw} suffix={suffix} label={label} target={target} div={div} />
            ))}
          </motion.div>
        </div>

        <motion.div
          className="hero-eye"
          initial={{ opacity:0, scale:0.85 }} animate={{ opacity:1, scale:1 }}
          transition={{ duration:1.1, delay:0.2, ease:E }}
          style={{ display:'flex', alignItems:'center', justifyContent:'center', paddingTop:'6rem' }}
        >
          <div style={{ position:'relative', display:'flex', alignItems:'center', justifyContent:'center' }}>
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
            <div style={{
              position:'absolute', inset:-50, borderRadius:'50%',
              border:'1px solid rgba(255,255,255,0.05)',
              animation:'orbit-spin 25s linear infinite',
              pointerEvents:'none',
            }}>
              <div style={{ position:'absolute', top:-4, left:'50%', transform:'translateX(-50%)', width:8, height:8, borderRadius:'50%', background:'var(--accent-bright)', boxShadow:'0 0 12px var(--accent-bright)' }} />
            </div>
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

// ── CHALLENGE ─────────────────────────────────────────────────────────────────
const IMPACT_CARDS = [
  { icon: <Globe size={18} />,       title: 'Global Impact',       desc: 'Designed for low-resource settings and remote health workers.' },
  { icon: <Microscope size={18} />,  title: 'Clinical Credibility', desc: 'EfficientNet-B0 validated on 710 clinical specimens.' },
  { icon: <Stethoscope size={18} />, title: 'Safety-First Triage', desc: 'Non-diagnostic language with grounded GenAI guidance.' },
];

export function Challenge() {
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
            <span style={{ fontStyle:'italic', fontWeight:300 }} className="text-gold">Screening Gap.</span>
          </h2>
          <p style={{ fontSize:'0.95rem', color:'var(--text-muted)', lineHeight:1.75, marginBottom:'2.5rem' }}>
            Anemia affects 25% of the world's population, yet detection remains expensive and slow. Early action is delayed by clinic distance, blood testing costs, and lack of specialized hardware.
          </p>
          <div style={{ display:'flex', gap:'3rem' }}>
            {[['$0','Marginal Cost'],['100%','Smartphone-First']].map(([v,l]) => (
              <div key={l}>
                <div style={{ fontFamily:'var(--serif)', fontSize:'2.5rem', fontWeight:600 }} className="text-crimson-gold">{v}</div>
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
              <div className="icon-box" style={{
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
const WORKFLOW = [
  { icon: <Camera size={20} />,       title: 'Capture Image',    desc: 'High-res macro of the inner lower eyelid conjunctiva.' },
  { icon: <ShieldCheck size={20} />,  title: 'Quality Gate',     desc: 'Vision algorithms reject blurry or misframed images.' },
  { icon: <Brain size={20} />,        title: 'AI Prediction',    desc: 'EfficientNet-B0 estimates hemoglobin from pallor.' },
  { icon: <HeartPulse size={20} />,   title: 'Symptom Fusion',   desc: 'Fatigue, dizziness fused with image biomarkers.' },
  { icon: <MessageSquare size={20} />,title: 'GenAI Guidance',   desc: 'Mistral AI translates AI data into safe next steps.' },
];

export function WorkflowStepper() {
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
            <span style={{ fontStyle:'italic', fontWeight:300 }} className="text-gold">Screening Clarity.</span>
          </h2>
        </motion.div>

        <div className="workflow-5col" style={{ display:'grid', gridTemplateColumns:'repeat(5,1fr)', gap:'1.25rem', position:'relative' }}>
          <div className="workflow-connector" />
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
              <div className="step-badge">{String(i+1).padStart(2,'0')}</div>
              <div className="icon-box" style={{
                width:52, height:52, borderRadius:'1rem', margin:'0 auto',
                background: active===i ? 'linear-gradient(135deg, rgba(200,0,30,0.3) 0%, rgba(200,0,30,0.1) 100%)' : 'rgba(255,255,255,0.04)',
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

// ── TECH SECTION ──────────────────────────────────────────────────────────────
const TECH_LAYERS = [
  { icon: <Brain size={20} />,  title: 'Vision Screening Layer', desc: 'EfficientNet-B0 trained to analyze micro-vessel density and conjunctival pallor with sub-millimeter precision.' },
  { icon: <Zap size={20} />,   title: 'Grounded GenAI Layer',   desc: 'Mistral AI constrained by deterministic medical rules — safe, personalized guidance without hallucination.' },
  { icon: <Lock size={20} />,  title: 'Safety Triage System',   desc: 'Four-band triage (Low, Moderate, High, Retake) designed to prioritize user safety over false confidence.' },
];

export function TechSection() {
  return (
    <section id="technology" style={{ position:'relative', zIndex:1, padding:'10rem 4rem', background:'linear-gradient(180deg, transparent 0%, rgba(2,2,8,0.5) 100%)' }} className="section-pad">
      <div style={{ position:'absolute', width:500, height:500, borderRadius:'50%', background:'radial-gradient(circle, rgba(200,0,30,0.08) 0%, transparent 70%)', bottom:'0%', right:'-10%', filter:'blur(40px)', pointerEvents:'none' }} />

      <div className="tech-grid" style={{ maxWidth:1200, margin:'0 auto', display:'grid', gridTemplateColumns:'1fr 1fr', gap:'7rem', alignItems:'center' }}>
        <div style={{ display:'flex', flexDirection:'column', gap:'3rem' }}>
          <motion.div initial={{ opacity:0, y:30 }} whileInView={{ opacity:1, y:0 }} viewport={{ once:true }} transition={{ duration:0.7 }}>
            <div className="section-eyebrow" style={{ marginBottom:'1.25rem' }}>Architecture</div>
            <h2 style={{ fontFamily:'var(--serif)', fontSize:'clamp(2.2rem,4vw,3.5rem)', fontWeight:700, lineHeight:1.05, letterSpacing:'-0.03em' }}>
              The Intelligence<br/>
              <span style={{ fontStyle:'italic', fontWeight:300 }} className="text-gold">Framework.</span>
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
                <div className="tech-icon" style={{
                  width:52, height:52, borderRadius:'1rem', flexShrink:0,
                  background:'rgba(255,255,255,0.055)', border:'1px solid rgba(255,255,255,0.11)',
                  backdropFilter:'blur(20px)', WebkitBackdropFilter:'blur(20px)',
                  display:'flex', alignItems:'center', justifyContent:'center',
                  color:'var(--accent-bright)',
                  boxShadow:'inset 0 1px 0 rgba(255,255,255,0.12)',
                }}>{item.icon}</div>
                <div>
                  <h4 style={{ fontWeight:600, fontSize:'0.95rem', marginBottom:'0.4rem' }}>{item.title}</h4>
                  <p style={{ fontSize:'0.82rem', color:'var(--text-muted)', lineHeight:1.65 }}>{item.desc}</p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>

        <div style={{ display:'flex', flexDirection:'column', gap:'1.5rem' }}>
          {TECH_LAYERS.map((item, i) => (
            <motion.div
              key={item.title}
              className="glass glass-hover glass-shimmer"
              initial={{ opacity:0, x:30 }} whileInView={{ opacity:1, x:0 }}
              viewport={{ once:true }} transition={{ duration:0.6, delay:i*0.1, ease:E }}
              style={{ padding:'2rem', display:'flex', gap:'1.5rem', alignItems:'flex-start' }}
            >
              <div className="icon-box" style={{
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
export function Footer() {
  return (
    <footer style={{ position:'relative', zIndex:1 }} className="footer-glow">
      <div className="glass" style={{ borderRadius:0, padding:'5rem 4rem 3rem', background:'rgba(2,2,8,0.8)' }}>
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
