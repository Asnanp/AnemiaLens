/**
 * AnemiaLens - Main App Shell
 * Guest-first screening with account save, history, and dashboard flows.
 */

import { Suspense, lazy, useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import AboutUs from './pages/AboutUs';
import HowItWorks from './pages/HowItWorks';
import ForProviders from './pages/ForProviders';
import FAQ from './pages/FAQ';
import Contact from './pages/Contact';
import Science from './pages/Science';
import Pricing from './pages/Pricing';
import Blog from './pages/Blog';
import Testimonials from './pages/Testimonials';
import { motion, AnimatePresence } from 'framer-motion';
import { useScreening } from './hooks/useScreening';
import { AuthProvider, useAuth } from './hooks/useAuth';
import { ErrorBoundary } from './components/ErrorBoundary';
import { UploadZone } from './components/features/UploadZone';
import {
  STEPS_META, QwenLoadingOverlay, E, WakeBanner, Cursor, LuxuryParticles,
} from './components/screening/SharedUI';
import { Hero } from './pages/HeroSection';
import { ArrowRight, ChevronRight, Menu, User, X } from 'lucide-react';
import { SmoothScroll } from './components/SmoothScroll';
import { ScrollProgress } from './components/ScrollProgress';
import { Enhanced3DBackground } from './components/Enhanced3DBackground';

import { toast, ToastContainer } from './components/Toast';
import { saveScreeningToAccount } from './api';
import type { AnalyzeResponse } from './types';

const loadAuthPage = () => import('./pages/AuthPage');
const AuthPage = lazy(loadAuthPage);
const loadQualityView = () => import('./components/features/QualityView');
const QualityView = lazy(async () => ({ default: (await loadQualityView()).QualityView }));
const loadIntakeView = () => import('./components/features/IntakeView');
const IntakeView = lazy(async () => ({ default: (await loadIntakeView()).IntakeView }));
const loadResultView = () => import('./components/features/ResultView');
const ResultView = lazy(async () => ({ default: (await loadResultView()).ResultView }));
const loadDashboardPage = () => import('./pages/DashboardPage');
const DashboardPage = lazy(loadDashboardPage);
const loadAdminDashboardPage = () => import('./pages/AdminDashboardPage');
const AdminDashboardPage = lazy(loadAdminDashboardPage);
const loadLandingSections = () => import('./pages/LandingSections');
const Challenge = lazy(async () => ({ default: (await loadLandingSections()).Challenge }));
const DifferentiatorsSection = lazy(async () => ({ default: (await loadLandingSections()).DifferentiatorsSection }));
const WorkflowStepper = lazy(async () => ({ default: (await loadLandingSections()).WorkflowStepper }));
const TechSection = lazy(async () => ({ default: (await loadLandingSections()).TechSection }));
const Footer = lazy(async () => ({ default: (await loadLandingSections()).Footer }));
const loadVisualSystem = () => import('./components/features/VisualSystem');
const AuroraCanvas = lazy(async () => ({ default: (await loadVisualSystem()).AuroraCanvas }));
const loadSupabaseTest = () => import('./components/SupabaseTest');
const SupabaseTest = lazy(async () => ({ default: (await loadSupabaseTest()).SupabaseTest }));

const NAV_LINKS = [
  { label: 'How It Works', path: '/how-it-works' },
  { label: 'Science', path: '/science' },
  { label: 'Pricing', path: '/pricing' },
  { label: 'Blog', path: '/blog' },
  { label: 'Testimonials', path: '/testimonials' },
  { label: 'Contact', path: '/contact' },
] as const;

function toTitleCaseWord(value: string) {
  if (!value) return '';
  return value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();
}

function getAccountBadge(user?: { full_name?: string | null; email?: string | null } | null) {
  const rawName = user?.full_name?.trim() || '';
  const firstToken = rawName.split(/[\s._-]+/).find(Boolean) ?? '';
  const canShowName =
    /^[A-Za-z]{2,12}$/.test(firstToken)
    && /[a-z]/.test(rawName);
  const normalized = canShowName ? toTitleCaseWord(firstToken) : 'Signed in';
  const initialSource = canShowName
    ? normalized
    : (user?.email?.trim()?.charAt(0).toUpperCase() || 'A');
  return { label: 'Dashboard', initial: initialSource, hint: normalized };
}

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

function InlineSurfaceLoader({ label }: { label: string }) {
  return (
    <div
      className="glass"
      style={{
        padding: '1.25rem 1.5rem',
        borderRadius: '1rem',
        display: 'grid',
        gap: '0.6rem',
        background: 'rgba(255,255,255,0.025)',
        border: '1px solid rgba(255,255,255,0.07)',
      }}
    >
      <div
        style={{
          fontSize: '0.58rem',
          fontFamily: 'var(--mono)',
          letterSpacing: '0.14em',
          textTransform: 'uppercase',
          color: 'var(--text-dim)',
        }}
      >
        Loading
      </div>
      <div style={{ fontSize: '0.88rem', color: 'var(--text-muted)', lineHeight: 1.65 }}>{label}</div>
    </div>
  );
}

function SectionFallback({ minHeight = 360 }: { minHeight?: number }) {
  return (
    <div
      style={{
        minHeight,
        width: '100%',
        borderRadius: '1.5rem',
        background: 'linear-gradient(180deg, rgba(255,255,255,0.02), rgba(255,255,255,0.01))',
        border: '1px solid rgba(255,255,255,0.04)',
      }}
    />
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
  const [compactViewport, setCompactViewport] = useState(() => window.innerWidth <= 1080);

  useEffect(() => {
    const fn = () => setScrolled(window.scrollY > 50);
    window.addEventListener('scroll', fn, { passive: true });
    return () => window.removeEventListener('scroll', fn);
  }, []);

  useEffect(() => {
    const onResize = () => setCompactViewport(window.innerWidth <= 1080);
    window.addEventListener('resize', onResize, { passive: true });
    return () => window.removeEventListener('resize', onResize);
  }, []);

  const accountBadge = getAccountBadge(user);

  const scrollTo = (id: string) => {
    setMenuOpen(false);
    setTimeout(() => {
      const target = document.getElementById(id);
      if (!target) return;
      const header = document.querySelector('header');
      const headerHeight = header?.getBoundingClientRect().height ?? 0;
      const top = target.getBoundingClientRect().top + window.scrollY - headerHeight - 28;
      window.scrollTo({ top: Math.max(top, 0), behavior: 'smooth' });
    }, 150);
  };

  const openAuth = (mode: 'login' | 'register') => {
    setMenuOpen(false);
    setAuthMode(mode);
    setShowAuth(true);
  };

  return (
    <>
      <motion.header
        initial={compactViewport ? false : { y: -80, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        transition={{ duration: compactViewport ? 0.25 : 0.8, ease: E }}
        style={{
          position: 'fixed',
          top: compactViewport
            ? (scrolled ? 'max(env(safe-area-inset-top), 0.4rem)' : 'calc(env(safe-area-inset-top) + 0.5rem)')
            : (scrolled ? '0.75rem' : '1.5rem'),
          left: 0,
          right: 0,
          margin: '0 auto',
          zIndex: 100,
          width: compactViewport ? 'calc(100vw - 1rem)' : 'min(1120px, calc(100vw - 1rem))',
          transition: 'top 0.3s ease',
        }}
      >
        <div
          className="glass nav-pill"
          style={{
            padding: compactViewport ? '0.78rem 0.9rem' : '0.95rem 1.15rem',
            display: 'flex', alignItems: 'center', justifyContent: 'space-between',
            borderRadius: compactViewport
              ? (menuOpen ? '1.35rem 1.35rem 0 0' : '1.35rem')
              : (menuOpen ? '1.5rem 1.5rem 0 0' : '99px'),
            background: scrolled ? 'rgba(7,10,18,0.86)' : 'rgba(10,13,22,0.74)',
            backdropFilter: 'blur(24px) saturate(145%)',
            WebkitBackdropFilter: 'blur(24px) saturate(145%)',
            transition: 'background 0.3s, box-shadow 0.3s, border-radius 0.3s',
          }}
        >
          <button
            type="button"
            className="nav-brand-group"
            onClick={() => window.scrollTo({ top: 0, behavior: 'smooth' })}
            style={{ background: 'none', border: 'none', padding: 0, cursor: 'pointer' }}
          >
            <div className="nav-logo-badge nav-brand-mark">AL</div>
            <div className="nav-brand-copy">
              <span className="nav-brand-title">
                Anemia<span style={{ color: 'var(--accent-bright)' }}>Lens</span>
              </span>
              <span className="nav-brand-subtitle">Safer first-pass anemia screening</span>
            </div>
            {backendUp && (
              <span className="stat-chip nav-status-chip">
                <span className="nav-status-dot" />
                Live
              </span>
            )}
          </button>

          <nav className="nav-desktop nav-link-row">
            {NAV_LINKS.map(({ label, path }) => (
              <Link
                key={label}
                to={path}
                className="label-tag nav-link nav-link-button"
                style={{ color: 'var(--text-muted)', background: 'none', border: 'none', textDecoration: 'none' }}
              >
                {label}
              </Link>
            ))}
          </nav>

          {!compactViewport ? (
            <div className="nav-desktop nav-actions">
              {!isAuthenticated ? (
                <>
                  <button className="btn btn-glass nav-secondary-action" onClick={() => openAuth('login')}>
                    Sign In
                  </button>
                  <button className="nav-inline-action" onClick={() => openAuth('register')}>
                    Create account
                  </button>
                </>
              ) : (
                <>
                  {user?.role === 'admin' && (
                    <button
                      className="btn btn-glass nav-secondary-action nav-admin-action"
                      onMouseEnter={() => { void loadAdminDashboardPage(); }}
                      onFocus={() => { void loadAdminDashboardPage(); }}
                      onClick={() => setShowAdmin(true)}
                    >
                      Admin
                    </button>
                  )}
                  <button
                    className="btn btn-glass nav-secondary-action nav-dashboard-action"
                    onMouseEnter={() => { void loadDashboardPage(); }}
                    onFocus={() => { void loadDashboardPage(); }}
                    onClick={() => setShowDashboard(true)}
                    title={accountBadge.hint}
                  >
                    <span className="nav-account-avatar" aria-hidden="true">{accountBadge.initial}</span>
                    <span className="nav-account-copy">
                      <span className="nav-account-label">{accountBadge.label}</span>
                      <span className="nav-account-meta">{accountBadge.hint}</span>
                    </span>
                  </button>
                </>
              )}
              <a className="btn btn-primary nav-primary-cta" href="/#screening" style={{ textDecoration: 'none' }}>
                Start Screening <ArrowRight size={12} />
              </a>
            </div>
          ) : (
            <div className="nav-mobile-utility">
              {backendUp && (
                <span className="nav-mobile-status-pill">
                  <span className="nav-status-dot" />
                  Live
                </span>
              )}
              <button className="nav-hamburger" onClick={() => setMenuOpen((open) => !open)} aria-label="Toggle menu" aria-expanded={menuOpen}>
                {menuOpen ? <X size={18} /> : <Menu size={18} />}
              </button>
            </div>
          )}
        </div>

        <AnimatePresence>
          {menuOpen && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }} transition={{ duration: 0.3 }}
              style={{ overflow: 'hidden', background: 'rgba(7,10,18,0.95)', backdropFilter: 'blur(24px)',
                borderTop: '1px solid rgba(255,255,255,0.06)', borderRadius: '0 0 1.5rem 1.5rem' }}>
              <div className="nav-mobile-panel">
                <div className="nav-mobile-meta">
                  <div>
                    <div className="label-tag" style={{ color: 'var(--text-dim)', marginBottom: '0.45rem' }}>Navigate</div>
                    <div style={{ fontSize: '0.95rem', fontWeight: 600, lineHeight: 1.4 }}>Explore the platform, then jump straight into screening.</div>
                  </div>
                  <div className="nav-mobile-status">
                    <span className="nav-status-dot" />
                    {backendUp ? 'Backend live' : 'Backend reconnecting'}
                  </div>
                </div>
                {NAV_LINKS.map(({ label, path }, i) => (
                  <Link key={label} to={path}
                    onClick={() => setMenuOpen(false)}
                    className="nav-mobile-link"
                    style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'inherit', textDecoration: 'none' }}>
                    <motion.div
                      initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: i * 0.06 }}
                      style={{ display: 'flex', alignItems: 'center', width: '100%', justifyContent: 'space-between' }}
                    >
                      {label}<ChevronRight size={14} />
                    </motion.div>
                  </Link>
                ))}
                <div style={{ height: 1, background: 'rgba(255,255,255,0.06)', margin: '0.4rem 0 0.1rem' }} />
                {!isAuthenticated && (
                  <div className="nav-mobile-actions">
                    <button
                      className="btn btn-glass nav-mobile-action"
                      onClick={() => openAuth('login')}
                    >
                      Sign In
                    </button>
                    <button
                      className="btn btn-glass nav-mobile-action nav-register-action"
                      onClick={() => openAuth('register')}
                    >
                      Create Account
                    </button>
                  </div>
                )}
            {isAuthenticated && (
              <div className="nav-mobile-actions">
                    {user?.role === 'admin' && (
                      <button
                        className="btn btn-glass nav-mobile-action nav-admin-action"
                        onMouseEnter={() => { void loadAdminDashboardPage(); }}
                        onFocus={() => { void loadAdminDashboardPage(); }}
                        onClick={() => {
                          setMenuOpen(false);
                          setShowAdmin(true);
                        }}
                      >
                        Admin Panel
                      </button>
                    )}
                    <button
                      className="btn btn-glass nav-mobile-action"
                      onMouseEnter={() => { void loadDashboardPage(); }}
                      onFocus={() => { void loadDashboardPage(); }}
                      onClick={() => {
                        setMenuOpen(false);
                        setShowDashboard(true);
                      }}
                    >
                      <User size={14} /> Open Dashboard
                    </button>
                    <div className="nav-mobile-account-note">
                      Signed in as {accountBadge.hint}
                    </div>
                  </div>
                )}
                <button className="btn btn-primary nav-mobile-cta"
                  onClick={() => { setMenuOpen(false); scrollTo('screening'); }}>
                  Start Screening
                </button>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </motion.header>

      <AnimatePresence>
        {showAuth && (
          <Suspense fallback={<OverlayLoader title="Opening Account Access" detail="Loading secure sign-in and registration." />}>
            <AuthPage
              initialMode={authMode}
              onClose={() => setShowAuth(false)}
            />
          </Suspense>
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
    quality, roiPreview, analysis, loading, error, backendUp,
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
      className="section-pad screening-shell"
      style={{
        position: 'relative',
        zIndex: 1,
        padding: 'clamp(5rem, 10vw, 10rem) clamp(1rem, 4vw, 4rem)',
        overflow: 'hidden',
      }}
    >
      <div className="screening-ambient" />
      <div style={{ maxWidth: 1200, margin: '0 auto' }}>
        <motion.div initial={{ opacity: 0, y: 30 }} whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }} transition={{ duration: 0.7 }}
          className="screening-heading-shell"
          style={{ textAlign: 'center', marginBottom: 'clamp(2.5rem, 6vw, 5rem)' }}>
          <div className="section-eyebrow" style={{ marginBottom: '1.25rem' }}>Guided Screening</div>
          <h2 style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(2.5rem,5vw,4.5rem)', fontWeight: 700, lineHeight: 1.0, letterSpacing: '-0.03em' }}>
            Run a screening in<br />
            <span style={{ fontStyle: 'italic', fontWeight: 300 }} className="text-gold">four clear steps.</span>
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
            <Suspense fallback={<OverlayLoader title="Opening Account Access" detail="Loading secure sign-in and save-to-account flow." />}>
              <AuthPage
                initialMode={authMode}
                onClose={() => setShowAuth(false)}
                onSuccess={() => {
                  if (pendingSave) {
                    toast.info('Signing in complete. Saving this screening to your account.');
                  }
                }}
              />
            </Suspense>
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
            {step === 1 && quality && (
              <Suspense fallback={<InlineSurfaceLoader label="Preparing image quality review." />}>
                <QualityView
                  quality={quality}
                  roiPreview={roiPreview}
                  onContinue={() => setStep(2)}
                  onBack={() => setStep(0)}
                  loading={loading}
                />
              </Suspense>
            )}
            {step === 2 && !loading && (
              <Suspense fallback={<InlineSurfaceLoader label="Preparing symptom and patient intake." />}>
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
              </Suspense>
            )}
            {step === 2 && loading && <QwenLoadingOverlay />}
            {step === 3 && analysis && (
              <Suspense fallback={<InlineSurfaceLoader label="Preparing your screening result and report actions." />}>
                <ResultView analysis={analysis} onReset={reset} onDownload={handleDownload} onOpenAuth={(mode = 'login') => openAuth(mode, true)} />
              </Suspense>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </section>
  );
}

function AppContent() {
  const { backendUp } = useScreening();
  const showSupabaseTest = import.meta.env.DEV && import.meta.env.VITE_SHOW_SUPABASE_TEST === 'true';
  const [compactVisualMode, setCompactVisualMode] = useState(() => window.innerWidth <= 900);

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

  useEffect(() => {
    const warm = () => {
      void loadLandingSections();
      void loadVisualSystem();
      void loadAuthPage();
      void loadQualityView();
      void loadIntakeView();
      void loadResultView();
      void loadDashboardPage();
      void loadAdminDashboardPage();
      if (showSupabaseTest) void loadSupabaseTest();
    };

    if ('requestIdleCallback' in window) {
      const idleId = window.requestIdleCallback(() => warm(), { timeout: 1800 });
      return () => window.cancelIdleCallback(idleId);
    }

    const timer = setTimeout(warm, 1200);
    return () => clearTimeout(timer);
  }, [showSupabaseTest]);

  useEffect(() => {
    const onResize = () => setCompactVisualMode(window.innerWidth <= 900);
    window.addEventListener('resize', onResize, { passive: true });
    return () => window.removeEventListener('resize', onResize);
  }, []);

  return (
    <div style={{ position: 'relative', minHeight: '100vh', background: 'var(--void)' }}>
      <ScrollProgress />
      <AnimatePresence><WakeBanner /></AnimatePresence>
      {!compactVisualMode && <Cursor />}
      {!compactVisualMode && <LuxuryParticles />}
      {!compactVisualMode && (
        <Suspense fallback={null}>
          <Enhanced3DBackground />
        </Suspense>
      )}
      <Navbar backendUp={backendUp} />
      <main style={{ position: 'relative', zIndex: 1 }}>
        <Routes>
          <Route path="/" element={
            <>
              <Hero />
              <div className="section-divider" />
              <Suspense fallback={<SectionFallback />}>
                <Challenge />
              </Suspense>
              <div className="section-divider" />
              <Suspense fallback={<SectionFallback />}>
                <DifferentiatorsSection />
              </Suspense>
              <div className="section-divider" />
              <Suspense fallback={<SectionFallback minHeight={280} />}>
                <WorkflowStepper />
              </Suspense>
              <div className="section-divider" />
              <ScreeningSection />
              <div className="section-divider" />
              <Suspense fallback={<SectionFallback />}>
                <TechSection />
              </Suspense>
            </>
          } />
          <Route path="/about" element={<AboutUs />} />
          <Route path="/how-it-works" element={<HowItWorks />} />
          <Route path="/providers" element={<ForProviders />} />
          <Route path="/faq" element={<FAQ />} />
          <Route path="/contact" element={<Contact />} />
          <Route path="/science" element={<Science />} />
          <Route path="/pricing" element={<Pricing />} />
          <Route path="/blog" element={<Blog />} />
          <Route path="/testimonials" element={<Testimonials />} />
        </Routes>
      </main>
      <Suspense fallback={null}>
        <Footer />
      </Suspense>
      {showSupabaseTest && (
        <Suspense fallback={null}>
          <SupabaseTest />
        </Suspense>
      )}
      <ToastContainer />
    </div>
  );
}

export default function App() {
  return (
    <ErrorBoundary>
      <AuthProvider>
        <Router>
          <SmoothScroll>
            <AppContent />
          </SmoothScroll>
        </Router>
      </AuthProvider>
    </ErrorBoundary>
  );
}
