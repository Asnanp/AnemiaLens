/**
 * Combined login/register page with premium glassmorphism design.
 */

import { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../hooks/useAuth';
import { ScanEye, ArrowRight, User, Mail, Lock, Eye, EyeOff, X } from 'lucide-react';

const E = [0.22, 1, 0.36, 1] as const;

type AuthPageProps = {
  onClose: () => void;
  onSuccess?: () => void;
  initialMode?: 'login' | 'register';
};

export default function AuthPage({ onClose, onSuccess, initialMode = 'login' }: AuthPageProps) {
  const { login, register, error, clearError, isLoading } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    setMode(initialMode);
    setLocalError(null);
    clearError();
  }, [initialMode, clearError]);

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [onClose]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!email.trim() || !password.trim()) {
      setLocalError('Please fill in all required fields.');
      return;
    }
    if (mode === 'register' && password.length < 8) {
      setLocalError('Password must be at least 8 characters.');
      return;
    }

    try {
      if (mode === 'login') {
        await login(email, password);
      } else {
        await register(email, password, fullName || undefined);
      }
      onSuccess?.();
      onClose();
    } catch {
      // Error is handled by auth context
    }
  };

  const displayError = localError || error;
  const authHighlights = [
    'Save every screening into your account history',
    'Reopen reports and track confidence over time',
    'Keep sharing and follow-up tools in one place',
  ];

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      style={{
        position: 'fixed', inset: 0, zIndex: 10000,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'rgba(4,4,10,0.85)',
        backdropFilter: 'blur(20px)',
        WebkitBackdropFilter: 'blur(20px)',
        padding: '1rem',
        overflowY: 'auto',
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <motion.div
        className="auth-shell"
        initial={{ opacity: 0, y: 30, scale: 0.95 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 20, scale: 0.95 }}
        transition={{ duration: 0.4, ease: E }}
        style={{
          width: 'min(440px, calc(100vw - 2rem))',
          borderRadius: '1.5rem',
          background: 'rgba(255,255,255,0.04)',
          border: '1px solid rgba(255,255,255,0.08)',
          backdropFilter: 'blur(40px)',
          boxShadow: '0 48px 100px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.12)',
          overflow: 'hidden',
          maxHeight: 'min(90vh, 780px)',
          overflowY: 'auto',
        }}
      >
        {/* Header */}
        <div style={{
          padding: '1.8rem 1.5rem 0',
          textAlign: 'center',
          position: 'relative',
        }}>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close authentication modal"
            style={{
              position: 'absolute',
              top: '1rem',
              right: '1rem',
              width: 36,
              height: 36,
              borderRadius: '999px',
              border: '1px solid rgba(255,255,255,0.08)',
              background: 'rgba(255,255,255,0.03)',
              color: 'var(--text-dim)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              cursor: 'pointer',
            }}
          >
            <X size={16} />
          </button>
          <div style={{
            width: 48, height: 48, borderRadius: '14px',
            background: 'linear-gradient(135deg, #C8001E, #E8294A)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            margin: '0 auto 1.25rem',
            fontSize: '0.8rem', fontWeight: 900, color: '#fff',
            fontFamily: 'var(--mono)',
            boxShadow: '0 8px 24px rgba(200,0,30,0.4)',
          }}>AL</div>

          <h2 style={{
            fontFamily: 'var(--serif)', fontSize: '1.6rem', fontWeight: 700,
            marginBottom: '0.4rem',
          }}>
            {mode === 'login' ? 'Welcome back' : 'Create account'}
          </h2>
          <p style={{
            fontSize: '0.78rem', color: 'var(--text-dim)', lineHeight: 1.6,
          }}>
            {mode === 'login'
              ? 'Sign in to access your screening history and saved results.'
              : 'Join AnemiaLens to save screenings and track your health journey.'}
          </p>

          <div
            className="auth-benefit-grid"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(120px, 1fr))',
              gap: '0.65rem',
              marginTop: '1.25rem',
              textAlign: 'left',
            }}
          >
            {authHighlights.map((item) => (
              <div
                key={item}
                style={{
                  padding: '0.8rem 0.85rem',
                  borderRadius: '0.95rem',
                  background: 'rgba(255,255,255,0.03)',
                  border: '1px solid rgba(255,255,255,0.06)',
                  display: 'flex',
                  gap: '0.55rem',
                  alignItems: 'flex-start',
                }}
              >
                <span
                  style={{
                    width: 7,
                    height: 7,
                    borderRadius: '50%',
                    marginTop: '0.35rem',
                    background: 'var(--accent-bright)',
                    boxShadow: '0 0 10px rgba(232,41,74,0.35)',
                    flexShrink: 0,
                  }}
                />
                <span style={{ fontSize: '0.7rem', lineHeight: 1.55, color: 'var(--text-muted)' }}>{item}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Tab toggle */}
        <div style={{
          display: 'flex', margin: '1.5rem 1.5rem 0', borderRadius: '0.75rem',
          background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)',
          overflow: 'hidden',
        }}>
          {(['login', 'register'] as const).map(m => (
            <button
              key={m}
              onClick={() => { setMode(m); setLocalError(null); clearError(); }}
              style={{
                flex: 1, padding: '0.65rem', fontSize: '0.68rem',
                fontFamily: 'var(--mono)', textTransform: 'uppercase',
                letterSpacing: '0.12em', fontWeight: 600,
                background: mode === m ? 'rgba(200,0,30,0.15)' : 'transparent',
                color: mode === m ? 'var(--accent-bright)' : 'var(--text-dim)',
                border: 'none', cursor: 'pointer',
                transition: 'all 0.2s',
                borderRight: m === 'login' ? '1px solid rgba(255,255,255,0.06)' : 'none',
              }}
            >
              {m === 'login' ? 'Sign In' : 'Sign Up'}
            </button>
          ))}
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ padding: '1.4rem 1.5rem 1.75rem' }}>
          <AnimatePresence mode="wait">
            {displayError && (
              <motion.div
                initial={{ opacity: 0, y: -8 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}
                style={{
                  padding: '0.65rem 1rem', marginBottom: '1rem', borderRadius: '0.625rem',
                  background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)',
                  fontSize: '0.75rem', color: '#FCA5A5',
                }}
              >
                {displayError}
              </motion.div>
            )}
          </AnimatePresence>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.875rem' }}>
            {mode === 'register' && (
              <div style={{ position: 'relative' }}>
                <User size={14} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
                <input
                  type="text"
                  placeholder="Full name (optional)"
                  value={fullName}
                  onChange={e => setFullName(e.target.value)}
                  style={{
                    width: '100%', padding: '0.85rem 1rem 0.85rem 2.5rem',
                    fontSize: '0.82rem', borderRadius: '0.75rem',
                    background: 'rgba(255,255,255,0.04)', color: 'var(--text)',
                    border: '1px solid rgba(255,255,255,0.08)',
                    outline: 'none', fontFamily: 'inherit',
                    transition: 'border-color 0.2s',
                  }}
                  onFocus={e => e.target.style.borderColor = 'rgba(200,0,30,0.4)'}
                  onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.08)'}
                />
              </div>
            )}

            <div style={{ position: 'relative' }}>
              <Mail size={14} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
              <input
                type="email"
                placeholder="Email address"
                value={email}
                onChange={e => setEmail(e.target.value)}
                required
                style={{
                  width: '100%', padding: '0.85rem 1rem 0.85rem 2.5rem',
                  fontSize: '0.82rem', borderRadius: '0.75rem',
                  background: 'rgba(255,255,255,0.04)', color: 'var(--text)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  outline: 'none', fontFamily: 'inherit',
                  transition: 'border-color 0.2s',
                }}
                onFocus={e => e.target.style.borderColor = 'rgba(200,0,30,0.4)'}
                onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.08)'}
              />
            </div>

            <div style={{ position: 'relative' }}>
              <Lock size={14} style={{ position: 'absolute', left: 14, top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
              <input
                type={showPassword ? 'text' : 'password'}
                placeholder="Password"
                value={password}
                onChange={e => setPassword(e.target.value)}
                required
                minLength={8}
                style={{
                  width: '100%', padding: '0.85rem 2.5rem 0.85rem 2.5rem',
                  fontSize: '0.82rem', borderRadius: '0.75rem',
                  background: 'rgba(255,255,255,0.04)', color: 'var(--text)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  outline: 'none', fontFamily: 'inherit',
                  transition: 'border-color 0.2s',
                }}
                onFocus={e => e.target.style.borderColor = 'rgba(200,0,30,0.4)'}
                onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.08)'}
              />
              <button
                type="button"
                onClick={() => setShowPassword(p => !p)}
                style={{
                  position: 'absolute', right: 10, top: '50%', transform: 'translateY(-50%)',
                  background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-dim)',
                  padding: 4,
                }}
              >
                {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
              </button>
            </div>
          </div>

          <div
            style={{
              marginTop: '1rem',
              padding: '0.85rem 0.95rem',
              fontSize: '0.72rem',
              color: 'var(--text-dim)',
              lineHeight: 1.65,
              borderRadius: '0.85rem',
              background: 'rgba(255,255,255,0.025)',
              border: '1px solid rgba(255,255,255,0.06)',
            }}
          >
            {mode === 'login'
              ? 'Sign in to reopen your dashboard, saved reports, and screening history.'
              : 'Create an account to save current and future screenings into your personal history.'}
          </div>

          <button
            type="submit"
            disabled={isLoading}
            className="btn btn-primary"
            style={{
              width: '100%', marginTop: '1.25rem', padding: '0.85rem',
              fontSize: '0.75rem', borderRadius: '0.75rem',
              opacity: isLoading ? 0.6 : 1,
            }}
          >
            {isLoading ? (
              <span style={{
                display: 'inline-block', width: 14, height: 14,
                border: '2px solid rgba(255,255,255,0.3)',
                borderTopColor: '#fff', borderRadius: '50%',
                animation: 'spin 0.8s linear infinite',
              }} />
            ) : (
              <>
                <ScanEye size={14} />
                {mode === 'login' ? 'Sign In' : 'Create Account'}
                <ArrowRight size={13} />
              </>
            )}
          </button>

          {/* Close */}
          <button
            type="button"
            onClick={onClose}
            style={{
              width: '100%', marginTop: '0.75rem', padding: '0.65rem',
              fontSize: '0.68rem', fontFamily: 'var(--mono)',
              textTransform: 'uppercase', letterSpacing: '0.1em',
              background: 'transparent', color: 'var(--text-dim)',
              border: 'none', cursor: 'pointer',
            }}
          >
            Continue without account
          </button>
        </form>
      </motion.div>
    </motion.div>
  );
}
