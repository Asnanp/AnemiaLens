/**
 * AnemiaLens - Main App Shell
 * Guest-first screening with account save, history, and dashboard flows.
 */

import { Suspense, lazy, useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useScreening } from './hooks/useScreening';
import { AuthProvider, useAuth } from './hooks/useAuth';
import { ErrorBoundary } from './components/ErrorBoundary';
import { UploadZone } from './components/features/UploadZone';
import { QualityView } from './components/features/QualityView';
import { IntakeView } from './components/features/IntakeView';
import { ResultView } from './components/features/ResultView';
import { ThreeBackground, AuroraCanvas } from './components/features/VisualSystem';
import AuthPage from './pages/AuthPage';
import {
  WakeBanner, LuxuryParticles, Cursor, MarqueeTicker,
  STEPS_META, QwenLoadingOverlay, E,
} from './components/screening/SharedUI';
import {
  Hero, Challenge, DifferentiatorsSection, WorkflowStepper, TechSection, Footer,
} from './pages/LandingSections';
import { ArrowRight, ChevronRight, User } from 'lucide-react';

import { SupabaseTest } from './components/SupabaseTest';
import { toast, ToastContainer } from './components/Toast';
import { saveScreeningToAccount } from './api';
import type { AnalyzeResponse } from './types';

const loadDashboardPage = () => import('./pages/DashboardPage');
const DashboardPage = lazy(loadDashboardPage);
const loadAdminDashboardPage = () => import('./pages/AdminDashboardPage');
const AdminDashboardPage = lazy(loadAdminDashboardPage);

const NAV_LINKS = [
  { label: 'Proof', id: 'proof' },
  { label: 'Technology', id: 'technology' },
  { label: 'Workflow', id: 'workflow' },
  { label: 'Screening', id: 'screening' },
] as const;

function OverlayLoader({ title, detail }: { title: string; detail: string }) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 10000,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'rgba(4,4,10,0.92)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        padding: '1.5rem',
      }}
    >
      <div
        className="glass"
        style={{
          width: 'min(420px, 100%)',
          padding: '1.75rem',
          borderRadius: '1.5rem',
          textAlign: 'center',
          display: 'grid',
          gap: '0.85rem',
          background: 'rgba(255,255,255,0.035)',
          border: '1px solid rgba(255,255,255,0.08)',
          boxShadow: '0 28px 70px rgba(0,0,0,0.45)',
        }}
      >
        <div
          style={{
            width: 56,
            height: 56,
            borderRadius: '50%',
            margin: '0 auto',
            border: '2px solid rgba(200,0,30,0.16)',
            borderTopColor: 'var(--accent-bright)',
            animation: 'spin 0.9s linear infinite',
          }}
        />
        <div style={{ fontFamily: 'var(--serif)', fontSize: '1.4rem', letterSpacing: '-0.03em' }}>{title}</div>
        <div style={{ fontSize: '0.8rem', lineHeight: 1.6, color: 'var(--text-dim)' }}>{detail}</div>
      </div>
    </motion.div>
  );
}

function Navbar({ backendUp }: { backendUp: boolean }) {
  const { isAuthenticated, user } = useAuth();
  const [scrolled, setScrolled] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [showDashboard, setShowDashboard] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', fn, { passive: true });
    return () => window.removeEventListener('scroll', fn);
  }, []);

  const scrollTo = (id: string) => {
    setMenuOpen(false);
    setTimeout(() => document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' }), 150);
  };

  const openAuth = (mode: 'login' | 'register') => {
    setMenuOpen(false);
    setAuthMode(mode);
    setShowAuth(true);
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
            transition: 'background 0.3s, box-shadow 0.3s, border-radius 0.3s',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{
              width: 32, height: 32, borderRadius: '10px',
              background: 'linear-gradient(135deg, #C8001E 0%, #E8294A 100%)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '0.6rem', fontWeight: 800, color: '#fff',
              fontFamily: 'var(--mono)', flexShrink: 0,
            }}>AL</div>
            <span style={{ fontWeight: 700, fontSize: '0.95rem', letterSpacing: '-0.02em' }}>
              Anemia<span style={{ color: 'var(--accent-bright)' }}>Lens</span>
            </span>
            {backendUp && (
              <span className="stat-chip" style={{ padding: '0.2rem 0.6rem', fontSize: '0.5rem', gap: '0.3rem' }}>
                <span style={{ width: 5, height: 5, borderRadius: '50%', background: '#10B981', display: 'inline-block' }} />
                Live
              </span>
            )}
          </div>

          <nav className="nav-desktop" style={{ display: 'flex', gap: '2rem' }}>
            {NAV_LINKS.map(({ label, id }) => (
              <a key={label} href={`#${id}`} className="label-tag nav-link"
                style={{ color: 'var(--text-muted)' }}>{label}</a>
            ))}
          </nav>

          <div className="nav-desktop" style={{ display: 'flex', gap: '0.75rem', alignItems: 'center' }}>
            {!isAuthenticated && (
              <>
                <button
                  className="btn btn-glass"
                  style={{ padding: '0.5rem 1rem', fontSize: '0.65rem', borderRadius: '99px' }}
                  onClick={() => openAuth('login')}
                >
                  Sign In
                </button>
                <button
                  className="btn btn-glass"
                  style={{
                    padding: '0.5rem 1rem',
                    fontSize: '0.65rem',
                    borderRadius: '99px',
                    border: '1px solid rgba(200,0,30,0.3)',
                    color: 'var(--accent-bright)',
                  }}
                  onClick={() => openAuth('register')}
                >
                  Create Account
                </button>
              </>
            )}
            {isAuthenticated && (
              <>
                {user?.role === 'admin' && (
                  <button className="btn btn-glass"
                    style={{ padding: '0.5rem 1rem', fontSize: '0.65rem', borderRadius: '99px', color: '#EF4444' }}
                    onMouseEnter={() => { void loadAdminDashboardPage(); }}
                    onFocus={() => { void loadAdminDashboardPage(); }}
                    onClick={() => setShowAdmin(true)}>Admin Panel</button>
                )}
                <button className="btn btn-glass"
                  style={{ padding: '0.5rem 1rem', fontSize: '0.65rem', borderRadius: '99px', gap: '0.4rem' }}
                  onMouseEnter={() => { void loadDashboardPage(); }}
                  onFocus={() => { void loadDashboardPage(); }}
                  onClick={() => setShowDashboard(true)}>
                  <User size={12} />{user?.full_name?.split(' ')[0] || 'Dashboard'}
                </button>
              </>
            )}
            <button className="btn btn-glass"
              style={{ padding: '0.55rem 1.25rem', fontSize: '0.65rem', borderRadius: '99px',
                boxShadow: 'inset 0 0 0 1px rgba(200,0,30,0.4)' }}
              onClick={() => scrollTo('screening')}>
              Get Started <ArrowRight size={12} />
            </button>
          </div>

          <button className="nav-hamburger" onClick={() => setMenuOpen(o => !o)}
            aria-label="Toggle menu"
            style={{ display: 'none', flexDirection: 'column', gap: '5px', width: 36, height: 36,
              background: 'none', border: 'none', cursor: 'pointer', padding: '4px', borderRadius: '8px' }}>
            <span style={{ display: 'block', width: 20, height: 1.5, background: 'var(--text)', borderRadius: 2 }} />
            <span style={{ display: 'block', width: 14, height: 1.5, background: 'var(--text)', borderRadius: 2, alignSelf: 'flex-end' }} />
            <span style={{ display: 'block', width: 20, height: 1.5, background: 'var(--text)', borderRadius: 2 }} />
          </button>
        </div>

        <AnimatePresence>
          {menuOpen && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.3 }}
              style={{ overflow: 'hidden', background: 'rgba(4,4,10,0.92)', backdropFilter: 'blur(32px)',
                borderTop: '1px solid rgba(255,255,255,0.06)', borderRadius: '0 0 1.5rem 1.5rem' }}>
              <div style={{ padding: '1.25rem 1.75rem 1.75rem', display: 'flex', flexDirection: 'column', gap: '0.25rem' }}>
                {NAV_LINKS.map(({ label, id }, i) => (
                  <motion.a key={label} href={`#${id}`}
                    initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.06 }}
                    onClick={() => scrollTo(id)}
                    style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between',
                      padding: '0.875rem 1rem', borderRadius: '0.875rem',
                      fontFamily: 'var(--mono)', fontSize: '0.72rem', textTransform: 'uppercase',
                      letterSpacing: '0.15em', color: 'var(--text-muted)' }}>
                    {label}<ChevronRight size={14} />
                  </motion.a>
                ))}
                <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '0.5rem 0' }} />
                {!isAuthenticated && (
                  <>
                    <button
                      className="btn btn-glass"
                      style={{ width: '100%', padding: '0.875rem', fontSize: '0.72rem', borderRadius: '0.875rem' }}
                      onClick={() => openAuth('login')}
                    >
                      Sign In
                    </button>
                    <button
                      className="btn btn-glass"
                      style={{ width: '100%', padding: '0.875rem', fontSize: '0.72rem', borderRadius: '0.875rem', border: '1px solid rgba(200,0,30,0.25)', color: 'var(--accent-bright)' }}
                      onClick={() => openAuth('register')}
                    >
                      Create Account
                    </button>
                  </>
                )}
                <button className="btn btn-primary"
                  style={{ width: '100%', padding: '0.875rem', fontSize: '0.72rem', borderRadius: '0.875rem' }}
                  onClick={() => { setMenuOpen(false); scrollTo('screening'); }}>
                  Get Started
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.header>

      <AnimatePresence>
        {showAuth && (
          <AuthPage
            initialMode={authMode}
            onClose={() => setShowAuth(false)}
          />
        )}
        {showDashboard && (
          <Suspense fallback={<OverlayLoader title="Preparing Dashboard" detail="Loading your screening intelligence workspace." />}>
            <DashboardPage onClose={() => setShowDashboard(false)} />
          </Suspense>
        )}
        {showAdmin && (
          <Suspense fallback={<OverlayLoader title="Opening Admin Console" detail="Fetching platform analytics and operator controls." />}>
            <AdminDashboardPage onClose={() => setShowAdmin(false)} />
          </Suspense>
        )}
      </AnimatePresence>
    </>
  );
}

function ScreeningSection() {
  const { isAuthenticated } = useAuth();
  const {
    step, setStep, file, previewUrl, symptoms, toggleSymptom,
    patientProfile, updatePatientProfile,
    quality, analysis, loading, error, backendUp,
    pickFile, runQuality, runAnalysis, loadSample, reset, symptomOnlyAssess, symptomLabels,
  } = useScreening();
  const [showAuth, setShowAuth] = useState(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [pendingSave, setPendingSave] = useState<AnalyzeResponse | null>(null);
  const [savingResult, setSavingResult] = useState(false);

  const handleDownload = async () => {
    if (!analysis) return;
    try {
      const { generatePdfReport } = await import('./utils/pdfExport');
      await generatePdfReport(analysis);
    } catch (e) {
      console.error('PDF export failed', e);
    }
  };

  const canStep = (i: number) =>
    i === 0 || (i === 1 && !!file) || (i === 2 && !!quality) || (i === 3 && !!analysis);

  const openAuth = (mode: 'login' | 'register', saveCurrent = false) => {
    setAuthMode(mode);
    if (saveCurrent && analysis) {
      setPendingSave(analysis);
    }
    setShowAuth(true);
  };

  useEffect(() => {
    if (!isAuthenticated || !pendingSave || savingResult) return;

    let active = true;
    setSavingResult(true);

    saveScreeningToAccount(pendingSave)
      .then(() => {
        if (!active) return;
        toast.success('Current screening saved to your account history.');
        setPendingSave(null);
      })
      .catch((err) => {
        if (!active) return;
        toast.error(err instanceof Error ? err.message : 'Could not save this screening to your account.');
      })
      .finally(() => {
        if (active) setSavingResult(false);
      });

    return () => {
      active = false;
    };
  }, [isAuthenticated, pendingSave, savingResult]);

  return (
    <section
      id="screening"
      style={{
        position: 'relative',
        zIndex: 1,
        padding: 'clamp(5rem, 10vw, 10rem) clamp(1rem, 4vw, 4rem)',
        overflow: 'hidden',
      }}
      className="section-pad"
    >
      <div className="screening-ambient" />
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <motion.div initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }} transition={{ duration: 0.7 }}
          style={{ textAlign: 'center', marginBottom: 'clamp(2.5rem, 6vw, 5rem)' }}>
          <div className="section-eyebrow" style={{ marginBottom: '1.25rem' }}>Diagnostic Hub</div>
          <h2 style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(2.5rem,5vw,4.5rem)', fontWeight: 700, lineHeight: 1.0, letterSpacing: '-0.03em' }}>
            Interactive<br />
            <span style={{ fontStyle: 'italic', fontWeight: 300 }} className="text-gold">Screening Experience.</span>
          </h2>
        </motion.div>

        <div className="screening-progress" style={{ marginBottom: 'clamp(2rem, 5vw, 4rem)' }}>
          {STEPS_META.map((s, i) => (
            <div key={s.label} style={{ display: 'contents' }}>
              <div
                className={`screening-step-node ${step === i ? 'active' : ''} ${step > i ? 'done' : ''}`}
                onClick={() => canStep(i) && setStep(i)}
                style={{ opacity: canStep(i) ? 1 : 0.45, cursor: canStep(i) ? 'pointer' : 'default' }}>
                <div className={`screening-step-circle ${step === i ? 'active' : ''} ${step > i ? 'done' : ''}`}>
                  {step > i
                    ? <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>
                    : <span style={{ fontFamily: 'var(--mono)', fontSize: '0.65rem' }}>{String(i + 1).padStart(2, '0')}</span>}
                </div>
                <span className="screening-step-label">{s.label}</span>
              </div>
              {i < STEPS_META.length - 1 && <div className={`screening-step-line ${step > i ? 'done' : ''}`} />}
            </div>
          ))}
        </div>

        <AnimatePresence>
          {showAuth && (
            <AuthPage
              initialMode={authMode}
              onClose={() => setShowAuth(false)}
              onSuccess={() => {
                if (pendingSave) {
                  toast.info('Signing in complete. Saving this screening to your account.');
                }
              }}
            />
          )}
          {!backendUp && step < 3 && (
            <motion.div initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              style={{ padding: '0.875rem 1.5rem', marginBottom: '1.5rem', borderRadius: '0.875rem',
                background: 'rgba(245,158,11,0.07)', border: '1px solid rgba(245,158,11,0.25)',
                display: 'flex', alignItems: 'center', gap: '0.875rem', flexWrap: 'wrap' }}>
              <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#F59E0B', flexShrink: 0 }} />
              <span style={{ fontSize: '0.78rem', color: '#FCD34D', flex: 1 }}>
                Backend unavailable. You can still run a symptom-only assessment.
              </span>
              {step === 2 && (
                <button onClick={symptomOnlyAssess}
                  style={{ padding: '0.4rem 1rem', fontSize: '0.65rem', fontFamily: 'var(--mono)',
                    background: 'rgba(245,158,11,0.15)', border: '1px solid rgba(245,158,11,0.3)',
                    borderRadius: '0.5rem', color: '#FCD34D', cursor: 'pointer', fontWeight: 600,
                    textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                  Symptom-Only Assessment
                </button>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {error && (
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
              className="glass"
              style={{ padding: '1.25rem 1.75rem', marginBottom: '2rem', borderLeft: '3px solid #EF4444',
                background: 'rgba(239,68,68,0.06)', display: 'flex', alignItems: 'center', gap: '1rem' }}>
              <span style={{ fontSize: '0.85rem', color: '#FCA5A5' }}>{error}</span>
              <button onClick={reset} className="label-tag" style={{ marginLeft: 'auto', color: '#FCA5A5', cursor: 'pointer' }}>Dismiss</button>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence mode="wait">
          <motion.div key={step} initial={{ opacity: 0, x: 24 }} animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -24 }} transition={{ duration: 0.45, ease: E }}>
            {step === 0 && (
              <div
                className="capture-grid"
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
                  gap: 'clamp(1.5rem, 4vw, 4rem)',
                  alignItems: 'start',
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2rem' }}>
                  <div>
                    <div className="section-eyebrow" style={{ marginBottom: '0.75rem' }}>Phase 01</div>
                    <h3 style={{ fontFamily: 'var(--serif)', fontSize: '2.2rem', fontWeight: 700, lineHeight: 1.1, letterSpacing: '-0.03em', marginBottom: '1rem' }}>Initial Image Capture</h3>
                    <p style={{ color: 'var(--text-muted)', lineHeight: 1.7, fontSize: '0.9rem' }}>
                      High-resolution macro capture of the conjunctival region. Align your phone horizontally with the lower eyelid pulled down.
                    </p>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                    <div className="label-tag" style={{ marginBottom: '0.5rem' }}>Protocol Check</div>
                    {['Bright, indirect natural daylight', 'No flash or harsh shadows', 'Lower eyelid fully exposed', 'One eye centered in frame'].map(tip => (
                      <div key={tip} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                        <div style={{ width: 18, height: 18, borderRadius: '50%', background: 'rgba(200,0,30,0.15)', border: '1px solid rgba(200,0,30,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                          <svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="var(--accent-bright)" strokeWidth="3" strokeLinecap="round"><polyline points="20 6 9 17 4 12" /></svg>
                        </div>
                        <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>{tip}</span>
                      </div>
                    ))}
                  </div>
                  <div>
                    <div className="label-tag" style={{ marginBottom: '1rem' }}>Demo Profiles</div>
                    <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap' }}>
                      {[
                        { id: 'low', label: 'Low Risk', img: '/demo-cases/low-risk-demo.jpg' },
                        { id: 'moderate', label: 'Moderate', img: '/demo-cases/moderate-risk-demo.jpg' },
                        { id: 'high', label: 'High Concern', img: '/demo-cases/high-concern-demo.jpg' },
                      ].map(s => (
                        <button key={s.id} className="btn btn-glass glass-shimmer"
                          style={{ padding: '0.5rem 1rem', fontSize: '0.65rem', gap: '0.5rem', borderRadius: '0.75rem' }}
                          onClick={() => loadSample(s.img, { fatigue: false, dizziness: false, pale_skin: false, shortness_of_breath: false, heavy_menstrual_bleeding: null, poor_diet_low_iron: false }, s.id)}>
                          <img src={s.img} alt={s.label} style={{ width: 20, height: 20, borderRadius: 4, objectFit: 'cover' }} />
                          {s.label}
                        </button>
                      ))}
                    </div>
                  </div>
                  {!isAuthenticated && (
                    <div style={{ padding: '1rem 1.1rem', borderRadius: '1rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', display: 'grid', gap: '0.8rem' }}>
                      <div>
                        <div className="label-tag" style={{ marginBottom: '0.6rem' }}>Account layer</div>
                        <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', lineHeight: 1.65 }}>
                          Screen as a guest if you want, then create an account to save results, open your dashboard, and build a real screening history over time.
                        </div>
                      </div>
                      <div style={{ display: 'flex', gap: '0.7rem', flexWrap: 'wrap' }}>
                        <button className="btn btn-glass" style={{ padding: '0.6rem 1rem', fontSize: '0.65rem', borderRadius: '0.8rem' }} onClick={() => openAuth('login')}>
                          Sign In
                        </button>
                        <button className="btn btn-glass" style={{ padding: '0.6rem 1rem', fontSize: '0.65rem', borderRadius: '0.8rem', border: '1px solid rgba(200,0,30,0.25)', color: 'var(--accent-bright)' }} onClick={() => openAuth('register')}>
                          Create Account
                        </button>
                      </div>
                    </div>
                  )}
                </div>
                <UploadZone onFileSelect={pickFile} previewUrl={previewUrl} onClear={reset} onRunQuality={runQuality} loading={loading} disabled={!file} />
              </div>
            )}
            {step === 1 && quality && <QualityView quality={quality} onContinue={() => setStep(2)} onBack={() => setStep(0)} loading={loading} />}
            {step === 2 && !loading && (
              <IntakeView
                symptoms={symptoms}
                patientProfile={patientProfile}
                toggleSymptom={toggleSymptom}
                updatePatientProfile={updatePatientProfile}
                onContinue={runAnalysis}
                onBack={() => setStep(1)}
                loading={loading}
                symptomLabels={symptomLabels}
              />
            )}
            {step === 2 && loading && <QwenLoadingOverlay />}
            {step === 3 && analysis && <ResultView analysis={analysis} onReset={reset} onDownload={handleDownload} onOpenAuth={(mode = 'login') => openAuth(mode, true)} />}
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}

function AppContent() {
  const { backendUp } = useScreening();
  const showSupabaseTest = import.meta.env.DEV && import.meta.env.VITE_SHOW_SUPABASE_TEST === 'true';

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
    <div style={{ position: 'relative', minHeight: '100vh', background: 'var(--void)' }}>
      <AnimatePresence><WakeBanner /></AnimatePresence>
      <Cursor />
      <LuxuryParticles />
      <AuroraCanvas />
      <ThreeBackground />
      <Navbar backendUp={backendUp} />
      <main style={{ position: 'relative', zIndex: 1 }}>
        <Hero />
        <MarqueeTicker />
        <div className="section-divider" />
        <Challenge />
        <div className="section-divider" />
        <DifferentiatorsSection />
        <div className="section-divider" />
        <WorkflowStepper />
        <div className="section-divider" />
        <ScreeningSection />
        <div className="section-divider" />
        <TechSection />
      </main>
      <Footer />
      {showSupabaseTest && <SupabaseTest />}
      <ToastContainer />
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
