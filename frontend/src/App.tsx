/**
 * AnemiaLens — Main App Shell
 *
 * Phase 2 refactor: All section components extracted to dedicated files.
 * This file is now a clean composition root (~250 lines vs original 1138).
 *
 * Additions:
 * - ErrorBoundary (catches rendering crashes)
 * - AuthProvider (JWT auth context)
 * - Auth modal + Dashboard modal
 * - Navbar auth integration (Sign In / Dashboard buttons)
 */

import { useEffect, useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useScreening } from './hooks/useScreening';
import { AuthProvider, useAuth } from './hooks/useAuth';
import { ErrorBoundary } from './components/ErrorBoundary';
import { UploadZone } from './components/features/UploadZone';
import { QualityView } from './components/features/QualityView';
import { SymptomView } from './components/features/SymptomView';
import { ResultView } from './components/features/ResultView';
import { ThreeBackground, AuroraCanvas } from './components/features/VisualSystem';
import {
  WakeBanner, LuxuryParticles, Cursor, MarqueeTicker,
  STEPS_META, QwenLoadingOverlay, E,
} from './components/screening/SharedUI';
import {
  Hero, Challenge, WorkflowStepper, TechSection, Footer, PricingSection,
} from './pages/LandingSections';
import { ScanEye, ArrowRight, ChevronRight, User } from 'lucide-react';

// ── Lazy-loaded pages ─────────────────────────────────────────────────────────
import AuthPage from './pages/AuthPage';
import DashboardPage from './pages/DashboardPage';
import AdminDashboardPage from './pages/AdminDashboardPage';
import { generatePdfReport } from './utils/pdfExport';
import { SupabaseTest } from './components/SupabaseTest';
import { ToastContainer } from './components/Toast';
import { StripeCheckoutModal } from './components/StripeCheckoutModal';


// ── NAVBAR — with auth integration ────────────────────────────────────────────
const NAV_LINKS = ['Technology', 'Workflow', 'Screening'] as const;

function Navbar({ backendUp }: { backendUp: boolean }) {
  const { isAuthenticated, user } = useAuth();
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [showAuth, setShowAuth] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', fn, { passive: true });
    return () => window.removeEventListener('scroll', fn);
  }, []);

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
    <>
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

          {/* Desktop nav */}
          <nav className="nav-desktop" style={{ display:'flex', gap:'2rem' }}>
            {NAV_LINKS.map(l => (
              <a key={l} href={`#${l.toLowerCase()}`} className="label-tag nav-link"
                style={{ color:'var(--text-muted)' }}
              >{l}</a>
            ))}
          </nav>

          {/* Desktop CTA + Auth */}
          <div className="nav-desktop" style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            {isAuthenticated ? (
              <>
                {user?.role === 'admin' && (
                  <button
                    className="btn btn-glass"
                    style={{ padding:'0.5rem 1rem', fontSize:'0.65rem', borderRadius:'99px', gap:'0.4rem', color: '#EF4444' }}
                    onClick={() => setShowAdmin(true)}
                  >
                    Admin Panel
                  </button>
                )}
                <button
                  className="btn btn-glass"
                  style={{ padding:'0.5rem 1rem', fontSize:'0.65rem', borderRadius:'99px', gap:'0.4rem' }}
                  onClick={() => setShowDashboard(true)}
                >
                  <User size={12} />
                  {user?.full_name?.split(' ')[0] || 'Dashboard'}
                </button>
              </>
            ) : (
              <button
                className="btn btn-glass"
                style={{ padding:'0.5rem 1rem', fontSize:'0.65rem', borderRadius:'99px' }}
                onClick={() => setShowAuth(true)}
              >
                Sign In
              </button>
            )}
            <button
              className="btn btn-glass"
              style={{ padding:'0.55rem 1.25rem', fontSize:'0.65rem', borderRadius:'99px',
                boxShadow:'inset 0 0 0 1px rgba(200,0,30,0.4), inset 0 1px 0 rgba(255,100,100,0.15), 0 0 20px rgba(200,0,30,0.1)' }}
              onClick={() => scrollTo('screening')}
            >
              Get Started <ArrowRight size={12} />
            </button>
          </div>

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

        {/* Mobile drawer */}
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
                    }}
                  >
                    {l}
                    <ChevronRight size={14} style={{ color: 'var(--text-dim)' }} />
                  </motion.a>
                ))}

                <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '0.5rem 0' }} />

                {isAuthenticated ? (
                  <>
                    <motion.button
                      initial={{ opacity: 0, y: 8 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.22, duration: 0.3, ease: E }}
                      className="btn btn-glass"
                      style={{ width: '100%', padding: '0.875rem', fontSize: '0.72rem', borderRadius: '0.875rem' }}
                      onClick={() => { setMenuOpen(false); setShowDashboard(true); }}
                    >
                      <User size={15} /> Dashboard
                    </motion.button>
                    {user?.role === 'admin' && (
                      <motion.button
                        initial={{ opacity: 0, y: 8 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: 0.26, duration: 0.3, ease: E }}
                        className="btn btn-glass"
                        style={{ width: '100%', padding: '0.875rem', fontSize: '0.72rem', borderRadius: '0.875rem', color: '#EF4444' }}
                        onClick={() => { setMenuOpen(false); setShowAdmin(true); }}
                      >
                        Admin Panel
                      </motion.button>
                    )}
                  </>
                ) : (
                  <motion.button
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.22, duration: 0.3, ease: E }}
                    className="btn btn-primary"
                    style={{ width: '100%', padding: '0.875rem', fontSize: '0.72rem', borderRadius: '0.875rem' }}
                    onClick={() => { setMenuOpen(false); setShowAuth(true); }}
                  >
                    <ScanEye size={15} /> Sign In
                  </motion.button>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.header>

      {/* Modals */}
      <AnimatePresence>
        {showAuth && <AuthPage onClose={() => setShowAuth(false)} />}
        {showDashboard && <DashboardPage onClose={() => setShowDashboard(false)} />}
        {showAdmin && <AdminDashboardPage onClose={() => setShowAdmin(false)} />}
      </AnimatePresence>
    </>
  );
}

// ── SCREENING SECTION ─────────────────────────────────────────────────────────
function ScreeningSection() {
  const {
    step, setStep, file, previewUrl, symptoms, toggleSymptom,
    quality, analysis, loading, error, backendUp, isOfflineMode,
    pickFile, runQuality, runAnalysis, loadSample, reset, symptomOnlyAssess, symptomLabels
  } = useScreening();

  const handleDownload = async () => {
    if (!analysis) return;
    try {
      await generatePdfReport(analysis);
    } catch (e) {
      console.error('PDF export failed', e);
    }
  };

  const canStep = (i: number) =>
    i===0 || (i===1 && !!file) || (i===2 && !!quality) || (i===3 && !!analysis);

  return (
    <section id="screening" style={{ position:'relative', zIndex:1, padding:'10rem 4rem', overflow:'hidden' }} className="section-pad">
      <div className="screening-ambient" />
      <div style={{ maxWidth:1200, margin:'0 auto' }}>
        <motion.div
          initial={{ opacity:0, y:30 }} whileInView={{ opacity:1, y:0 }}
          viewport={{ once:true }} transition={{ duration:0.7 }}
          style={{ textAlign:'center', marginBottom:'5rem' }}
        >
          <div className="section-eyebrow" style={{ marginBottom:'1.25rem' }}>Diagnostic Hub</div>
          <h2 style={{ fontFamily:'var(--serif)', fontSize:'clamp(2.5rem,5vw,4.5rem)', fontWeight:700, lineHeight:1.0, letterSpacing:'-0.03em' }}>
            Interactive<br/>
            <span style={{ fontStyle:'italic', fontWeight:300 }} className="text-gold">Screening Experience.</span>
          </h2>
        </motion.div>

        {/* Progress stepper */}
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

        {/* Offline mode banner */}
        <AnimatePresence>
          {!backendUp && step < 3 && (
            <motion.div
              initial={{ opacity:0, y:-8 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0 }}
              style={{ padding:'0.875rem 1.5rem', marginBottom:'1.5rem', borderRadius:'0.875rem',
                background:'rgba(245,158,11,0.07)', border:'1px solid rgba(245,158,11,0.25)',
                display:'flex', alignItems:'center', gap:'0.875rem', flexWrap:'wrap' }}
            >
              <div style={{ width:8, height:8, borderRadius:'50%', background:'#F59E0B', flexShrink:0 }} />
              <span style={{ fontSize:'0.78rem', color:'#FCD34D', flex:1 }}>
                Backend unavailable. You can still run a symptom-only assessment.
              </span>
              {step === 2 && (
                <button
                  onClick={symptomOnlyAssess}
                  style={{ padding:'0.4rem 1rem', fontSize:'0.65rem', fontFamily:'var(--mono)',
                    background:'rgba(245,158,11,0.15)', border:'1px solid rgba(245,158,11,0.3)',
                    borderRadius:'0.5rem', color:'#FCD34D', cursor:'pointer', fontWeight:600,
                    textTransform:'uppercase', letterSpacing:'0.08em' }}
                >
                  Symptom-Only Assessment
                </button>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {error && (
            <motion.div
              initial={{ opacity:0, y:10 }} animate={{ opacity:1, y:0 }} exit={{ opacity:0 }}
              className="glass"
              style={{ padding:'1.25rem 1.75rem', marginBottom:'2rem', borderLeft:'3px solid #EF4444',
                background:'rgba(239,68,68,0.06)', display:'flex', alignItems:'center', gap:'1rem' }}
            >
              <span style={{ fontSize:'0.85rem', color:'#FCA5A5' }}>{error}</span>
              <button onClick={reset} className="label-tag" style={{ marginLeft:'auto', color:'#FCA5A5', cursor:'pointer' }}>Dismiss</button>
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
            {step===3 && analysis && <ResultView analysis={analysis} onReset={reset} onDownload={handleDownload} />}
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}

// ── ROOT APP ──────────────────────────────────────────────────────────────────
function AppContent() {
  const { backendUp } = useScreening();
  const { isAuthenticated, user } = useAuth();
  const [showAuth, setShowAuth] = useState(false);
  const [showStripeFromPricing, setShowStripeFromPricing] = useState(false);

  const handlePricingUpgrade = () => {
    if (isAuthenticated) {
      setShowStripeFromPricing(true);
    } else {
      setShowAuth(true);
    }
  };

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
      <AnimatePresence><WakeBanner /></AnimatePresence>
      <Cursor />
      <LuxuryParticles />
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
        <PricingSection onUpgrade={handlePricingUpgrade} />
        <div className="section-divider" />
        <TechSection />
      </main>
      <Footer />
      <SupabaseTest />
      <ToastContainer />
      <AnimatePresence>
        {showAuth && <AuthPage onClose={() => setShowAuth(false)} />}
        {showStripeFromPricing && user && (
          <StripeCheckoutModal
            userEmail={user.email}
            onClose={() => setShowStripeFromPricing(false)}
            onSuccess={() => { setShowStripeFromPricing(false); window.location.reload(); }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <AppContent />
      </AuthProvider>
    </ErrorBoundary>
  );
}
