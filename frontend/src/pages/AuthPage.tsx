/**
 * AuthPage Overhaul: "Living Glass" UI
 * Transitioning from "Generic AI" to a more human, premium, and artisanal experience.
 */

import { useEffect, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../hooks/useAuth';
import { 
  ScanEye, 
  ArrowRight, 
  User, 
  Mail, 
  Lock, 
  Eye, 
  EyeOff, 
  X, 
  Sparkles,
  ShieldCheck,
  Zap,
  Activity
} from 'lucide-react';

const EASE = [0.22, 1, 0.36, 1] as const;
const DEFAULT_GOOGLE_CLIENT_ID = '919623138739-ep5cvs1et5o790j3rmlilfpd0q9r9q9i.apps.googleusercontent.com';

type AuthPageProps = {
  onClose: () => void;
  onSuccess?: () => void;
  initialMode?: 'login' | 'register';
};

type GoogleCredentialResponse = {
  credential?: string;
};

type GoogleAccountsId = {
  initialize: (config: {
    client_id: string;
    callback: (response: GoogleCredentialResponse) => void;
    auto_select?: boolean;
    cancel_on_tap_outside?: boolean;
  }) => void;
  renderButton: (element: HTMLElement, options: Record<string, unknown>) => void;
};

function getGoogleAccountsId(): GoogleAccountsId | null {
  const maybeGoogle = (window as Window & {
    google?: {
      accounts?: {
        id?: GoogleAccountsId;
      };
    };
  }).google;
  return maybeGoogle?.accounts?.id ?? null;
}

const authBenefits = [
  { icon: <Activity size={14} />, text: 'Unified Screening History' },
  { icon: <ShieldCheck size={14} />, text: 'Private Health Records' },
  { icon: <Zap size={14} />, text: 'Real-time AI Insights' },
] as const;

function FieldIconShell({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        position: 'absolute',
        left: 16,
        top: '50%',
        transform: 'translateY(-50%)',
        color: 'var(--text-dim)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        pointerEvents: 'none',
        zIndex: 2
      }}
    >
      {children}
    </div>
  );
}

export default function AuthPage({ onClose, onSuccess, initialMode = 'login' }: AuthPageProps) {
  const { login, loginWithGoogle, register, error, clearError, isLoading } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [isHovered, setIsHovered] = useState(false);
  const [googleState, setGoogleState] = useState<'loading' | 'ready' | 'unavailable'>('loading');
  const [googleLoading, setGoogleLoading] = useState(false);
  const googleButtonRef = useRef<HTMLDivElement | null>(null);
  const googleClientId = (import.meta.env.VITE_GOOGLE_CLIENT_ID ?? DEFAULT_GOOGLE_CLIENT_ID).trim();
  
  const [compactViewport, setCompactViewport] = useState(() => (
    typeof window !== 'undefined' ? window.innerWidth < 720 : false
  ));

  const resetForm = (nextMode: 'login' | 'register', options?: { preserveEmail?: boolean }) => {
    setMode(nextMode);
    setPassword('');
    setFullName('');
    setShowPassword(false);
    setLocalError(null);
    clearError();
    if (!options?.preserveEmail) {
      setEmail('');
    }
  };

  useEffect(() => {
    resetForm(initialMode);
  }, [initialMode, clearError]);

  useEffect(() => {
    const onResize = () => setCompactViewport(window.innerWidth < 720);
    window.addEventListener('resize', onResize, { passive: true });
    return () => window.removeEventListener('resize', onResize);
  }, []);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  useEffect(() => {
    if (!googleClientId) {
      setGoogleState('unavailable');
      return;
    }

    let cancelled = false;
    let script: HTMLScriptElement | null = document.querySelector('script[data-google-identity="true"]');

    const renderGoogleButton = () => {
      if (cancelled || !googleButtonRef.current) return;
      const googleAccountsId = getGoogleAccountsId();
      if (!googleAccountsId) {
        setGoogleState('unavailable');
        return;
      }

      googleAccountsId.initialize({
        client_id: googleClientId,
        auto_select: false,
        cancel_on_tap_outside: true,
        callback: async (response) => {
          const credential = response.credential?.trim();
          if (!credential) {
            setLocalError('Google sign-in did not return a valid credential.');
            return;
          }

          clearError();
          setLocalError(null);
          setGoogleLoading(true);
          try {
            await loginWithGoogle(credential);
            onSuccess?.();
            onClose();
          } catch (err) {
            setLocalError(err instanceof Error ? err.message : 'Google sign-in failed.');
          } finally {
            setGoogleLoading(false);
          }
        },
      });

      googleButtonRef.current.innerHTML = '';
      googleAccountsId.renderButton(googleButtonRef.current, {
        theme: 'filled_black',
        size: 'large',
        shape: 'pill',
        text: mode === 'login' ? 'signin_with' : 'signup_with',
        logo_alignment: 'left',
        width: Math.round(googleButtonRef.current.getBoundingClientRect().width || (compactViewport ? 320 : 392)),
      });
      setGoogleState('ready');
    };

    const handleScriptError = () => {
      if (!cancelled) setGoogleState('unavailable');
    };

    const existingGoogle = getGoogleAccountsId();
    if (existingGoogle) {
      renderGoogleButton();
      return () => {
        cancelled = true;
      };
    }

    if (!script) {
      script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.defer = true;
      script.dataset.googleIdentity = 'true';
      document.body.appendChild(script);
    }

    script.addEventListener('load', renderGoogleButton);
    script.addEventListener('error', handleScriptError);

    return () => {
      cancelled = true;
      script?.removeEventListener('load', renderGoogleButton);
      script?.removeEventListener('error', handleScriptError);
    };
  }, [clearError, compactViewport, googleClientId, loginWithGoogle, mode, onClose, onSuccess]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();
    const normalizedEmail = email.trim().toLowerCase();
    const normalizedFullName = fullName.trim();

    if (!normalizedEmail || !password.trim()) {
      setLocalError('Required fields are missing.');
      return;
    }

    if (mode === 'register' && password.length < 8) {
      setLocalError('Security requires at least 8 characters.');
      return;
    }

    if (password.length > 128) {
      setLocalError('Passwords must stay within 128 characters.');
      return;
    }

    try {
      if (mode === 'login') {
        await login(normalizedEmail, password);
      } else {
        await register(normalizedEmail, password, normalizedFullName || undefined);
      }
      onSuccess?.();
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : '';
      if (mode === 'register' && /already exists/i.test(message)) {
        resetForm('login', { preserveEmail: true });
        setLocalError('This email already has an account. Sign in instead.');
      }
    }
  };

  const displayError = localError || error;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.4 }}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 10000,
        display: 'flex',
        alignItems: compactViewport ? 'flex-start' : 'center',
        justifyContent: 'center',
        background: 'radial-gradient(circle at center, rgba(10,10,30,0.9) 0%, rgba(4,4,10,0.98) 100%)',
        backdropFilter: 'blur(32px) saturate(150%)',
        WebkitBackdropFilter: 'blur(32px) saturate(150%)',
        padding: compactViewport ? '0.5rem' : '1.5rem',
        paddingTop: compactViewport ? 'max(env(safe-area-inset-top), 1rem)' : '1.5rem',
        overflowY: 'auto',
      }}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <motion.div
        className="auth-shell glass"
        initial={{ opacity: 0, y: 40, scale: 0.98, rotateX: 5 }}
        animate={{ opacity: 1, y: 0, scale: 1, rotateX: 0 }}
        exit={{ opacity: 0, y: 30, scale: 0.98 }}
        transition={{ duration: 0.6, ease: EASE }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        style={{
          width: compactViewport ? 'min(100vw - 1.5rem, 460px)' : 'min(500px, calc(100vw - 3rem))',
          borderRadius: '2rem',
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid rgba(255,255,255,0.1)',
          boxShadow: isHovered 
            ? '0 64px 120px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.15)'
            : '0 48px 100px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.1)',
          overflow: 'hidden',
          perspective: '1000px',
          transition: 'box-shadow 0.5s var(--ease)',
        }}
      >
        {/* Animated Background Glow */}
        <div style={{
          position: 'absolute',
          top: -100,
          left: -100,
          width: 300,
          height: 300,
          background: 'radial-gradient(circle, rgba(37,99,235,0.15) 0%, transparent 70%)',
          pointerEvents: 'none',
          zIndex: 0
        }} />

        <div style={{ padding: compactViewport ? '1.65rem 1.25rem 0' : '1.9rem 1.75rem 0', textAlign: 'center', position: 'relative', zIndex: 1 }}>
          <button
            type="button"
            onClick={onClose}
            style={{
              position: 'absolute',
              top: '0.5rem',
              right: '0.5rem',
              width: 40,
              height: 40,
              borderRadius: '12px',
              border: '1px solid rgba(255,255,255,0.08)',
              background: 'rgba(255,255,255,0.03)',
              color: 'var(--text-dim)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
              transition: 'all 0.2s',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.08)';
              e.currentTarget.style.color = 'var(--text)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'rgba(255,255,255,0.03)';
              e.currentTarget.style.color = 'var(--text-dim)';
            }}
          >
            <X size={18} />
          </button>

          <motion.div
            initial={{ scale: 0.8, opacity: 0 }}
            animate={{ scale: 1, opacity: 1 }}
            transition={{ delay: 0.2, duration: 0.5 }}
            style={{
              width: 56,
              height: 56,
              borderRadius: '18px',
              background: 'linear-gradient(135deg, #2563EB, #7C3AED)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              margin: '0 auto 1.1rem',
              boxShadow: '0 12px 32px rgba(37,99,235,0.4)',
            }}
          >
            <Sparkles size={24} color="#fff" />
          </motion.div>

          <div style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.5rem',
            padding: '0.5rem 1rem',
            borderRadius: '999px',
            background: 'rgba(37,99,235,0.08)',
            border: '1px solid rgba(37,99,235,0.2)',
            fontFamily: 'var(--mono)',
            fontSize: '0.65rem',
            letterSpacing: '0.1em',
            textTransform: 'uppercase',
            color: '#60A5FA',
            marginBottom: '0.8rem'
          }}>
            <ShieldCheck size={12} />
            Encrypted Access
          </div>

          <h2 style={{
            fontFamily: 'var(--serif)',
            fontSize: '2rem',
            fontWeight: 800,
            letterSpacing: '-0.02em',
            background: 'linear-gradient(to bottom, #fff 0%, #cbd5e1 100%)',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            marginBottom: '0.35rem'
          }}>
            {mode === 'login' ? 'Welcome Back' : 'Get Started'}
          </h2>

          <p style={{
            fontSize: '0.9rem',
            color: 'var(--text-muted)',
            lineHeight: 1.6,
            maxWidth: '320px',
            margin: '0 auto 1.4rem'
          }}>
            {mode === 'login' 
              ? 'Enter your credentials to access your screening laboratory.'
              : 'Create your secure account to begin your health intelligence journey.'}
          </p>

          <div style={{
            display: 'grid',
            gridTemplateColumns: compactViewport ? '1fr' : 'repeat(3, 1fr)',
            gap: '0.75rem',
            marginBottom: '1.6rem'
          }}>
            {authBenefits.map((b, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 + i * 0.1 }}
                style={{
                  padding: compactViewport ? '0.8rem 0.7rem' : '0.9rem 0.55rem',
                  borderRadius: '1rem',
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid rgba(255,255,255,0.05)',
                  display: 'flex',
                  flexDirection: compactViewport ? 'row' : 'column',
                  alignItems: 'center',
                  gap: '0.5rem',
                  justifyContent: 'center',
                }}
              >
                <div style={{ color: '#60A5FA' }}>{b.icon}</div>
                <span style={{ fontSize: '0.6rem', color: 'var(--text-dim)', fontWeight: 500, textAlign: 'center' }}>
                  {b.text}
                </span>
              </motion.div>
            ))}
          </div>
        </div>

        <div style={{
          display: 'flex',
          margin: compactViewport ? '0 1.25rem' : '0 1.75rem',
          padding: '0.25rem',
          borderRadius: '1rem',
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.06)',
        }}>
          {(['login', 'register'] as const).map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => {
                resetForm(tab, { preserveEmail: true });
              }}
              style={{
                flex: 1,
                padding: '0.75rem',
                fontSize: '0.75rem',
                fontWeight: 600,
                borderRadius: '0.75rem',
                background: mode === tab ? 'rgba(37,99,235,0.15)' : 'transparent',
                color: mode === tab ? '#60A5FA' : 'var(--text-muted)',
                border: 'none',
                cursor: 'pointer',
                transition: 'all 0.3s var(--ease)',
              }}
            >
              {tab === 'login' ? 'Sign In' : 'Sign Up'}
            </button>
          ))}
        </div>

        <div style={{ padding: compactViewport ? '1rem 1.25rem 0' : '1.15rem 1.75rem 0', display: 'grid', gap: '0.8rem' }}>
          <div style={{
            minHeight: 44,
            borderRadius: '1rem',
            border: '1px solid rgba(255,255,255,0.06)',
            background: 'rgba(255,255,255,0.02)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '0.5rem',
          }}>
            <div ref={googleButtonRef} style={{ width: '100%', display: googleState === 'ready' ? 'block' : 'none' }} />
            {googleState !== 'ready' && (
              <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)', textAlign: 'center' }}>
                {googleState === 'loading' ? 'Loading Google sign-in…' : 'Google sign-in is unavailable right now.'}
              </div>
            )}
          </div>

          {(googleLoading || googleState === 'ready') && (
            <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', textAlign: 'center' }}>
              {googleLoading ? 'Finishing Google sign-in…' : 'Use Google for one-tap access, or continue with email below.'}
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.9rem' }}>
            <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.08)' }} />
            <div style={{
              fontSize: '0.65rem',
              fontFamily: 'var(--mono)',
              letterSpacing: '0.12em',
              textTransform: 'uppercase',
              color: 'var(--text-dim)'
            }}>
              Or continue with email
            </div>
            <div style={{ flex: 1, height: 1, background: 'rgba(255,255,255,0.08)' }} />
          </div>
        </div>

        <form onSubmit={handleSubmit} style={{ padding: compactViewport ? '1.35rem 1.25rem 1.25rem' : '1.5rem 1.75rem 1.5rem' }}>
          <AnimatePresence mode="wait">
            {displayError && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                style={{
                  padding: '0.85rem 1rem',
                  marginBottom: '1.5rem',
                  borderRadius: '1rem',
                  background: 'rgba(239,68,68,0.1)',
                  border: '1px solid rgba(239,68,68,0.2)',
                  fontSize: '0.8rem',
                  color: '#F87171',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.75rem'
                }}
              >
                <Activity size={14} />
                {displayError}
              </motion.div>
            )}
          </AnimatePresence>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {mode === 'register' && (
              <div style={{ position: 'relative' }}>
                <FieldIconShell><User size={18} /></FieldIconShell>
                <input
                  type="text"
                  placeholder="Your full name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  autoComplete="name"
                  style={{
                    width: '100%',
                    padding: '1.1rem 1rem 1.1rem 3.25rem',
                    fontSize: '0.95rem',
                    borderRadius: '1.25rem',
                    background: 'rgba(255,255,255,0.03)',
                    color: '#fff',
                    border: '1px solid rgba(255,255,255,0.08)',
                    outline: 'none',
                    transition: 'all 0.3s var(--ease)',
                  }}
                  className="auth-input"
                />
              </div>
            )}

            <div style={{ position: 'relative' }}>
              <FieldIconShell><Mail size={18} /></FieldIconShell>
              <input
                type="email"
                placeholder="Email address"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                style={{
                  width: '100%',
                  padding: '1.1rem 1rem 1.1rem 3.25rem',
                  fontSize: '0.95rem',
                  borderRadius: '1.25rem',
                  background: 'rgba(255,255,255,0.03)',
                  color: '#fff',
                  border: '1px solid rgba(255,255,255,0.08)',
                  outline: 'none',
                  transition: 'all 0.3s var(--ease)',
                }}
                className="auth-input"
              />
            </div>

            <div style={{ position: 'relative' }}>
              <FieldIconShell><Lock size={18} /></FieldIconShell>
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder="Password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                minLength={mode === 'register' ? 8 : 1}
                maxLength={128}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                style={{
                  width: '100%',
                  padding: '1.1rem 3.25rem 1.1rem 3.25rem',
                  fontSize: '0.95rem',
                  borderRadius: '1.25rem',
                  background: 'rgba(255,255,255,0.03)',
                  color: '#fff',
                  border: '1px solid rgba(255,255,255,0.08)',
                  outline: 'none',
                  transition: 'all 0.3s var(--ease)',
                }}
                className="auth-input"
              />
              <button
                type="button"
                onClick={() => setShowPassword((p) => !p)}
                style={{
                  position: 'absolute',
                  right: 16,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  background: 'none',
                  border: 'none',
                  cursor: 'pointer',
                  color: 'var(--text-dim)',
                  padding: 4,
                  zIndex: 2
                }}
              >
                {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
              </button>
            </div>
          </div>

          <motion.button
            type="submit"
            disabled={isLoading || googleLoading}
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            style={{
              width: '100%',
              marginTop: '2rem',
              padding: '1.1rem',
              fontSize: '0.9rem',
              fontWeight: 700,
              borderRadius: '1.25rem',
              background: 'linear-gradient(135deg, #2563EB 0%, #7C3AED 100%)',
              color: '#fff',
              border: 'none',
              cursor: isLoading || googleLoading ? 'not-allowed' : 'pointer',
              boxShadow: '0 12px 32px rgba(37,99,235,0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.75rem',
              opacity: isLoading || googleLoading ? 0.7 : 1,
            }}
          >
            {isLoading || googleLoading ? (
              <motion.div
                animate={{ rotate: 360 }}
                transition={{ repeat: Infinity, duration: 1, ease: 'linear' }}
                style={{
                  width: 20,
                  height: 20,
                  border: '2px solid rgba(255,255,255,0.3)',
                  borderTopColor: '#fff',
                  borderRadius: '50%',
                }}
              />
            ) : (
              <>
                {mode === 'login' ? 'Enter Laboratory' : 'Create Intelligence Profile'}
                <ArrowRight size={18} />
              </>
            )}
          </motion.button>

          <button
            type="button"
            onClick={onClose}
            style={{
              width: '100%',
              marginTop: '1rem',
              padding: '0.75rem',
              fontSize: '0.7rem',
              fontFamily: 'var(--mono)',
              textTransform: 'uppercase',
              letterSpacing: '0.15em',
              background: 'transparent',
              color: 'var(--text-dim)',
              border: 'none',
              cursor: 'pointer',
              transition: 'color 0.2s',
            }}
            onMouseEnter={(e) => e.currentTarget.style.color = 'var(--text-muted)'}
            onMouseLeave={(e) => e.currentTarget.style.color = 'var(--text-dim)'}
          >
            Browse anonymously
          </button>
        </form>

        <style>{`
          .auth-input:focus {
            border-color: rgba(37,99,235,0.5) !important;
            background: rgba(255,255,255,0.05) !important;
            box-shadow: 0 0 0 4px rgba(37,99,235,0.1);
          }
          @keyframes spin {
            to { transform: rotate(360deg); }
          }
        `}</style>
      </motion.div>
    </motion.div>
  );
}
