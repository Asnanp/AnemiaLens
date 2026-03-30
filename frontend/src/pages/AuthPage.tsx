/**
 * AuthPage Overhaul: "Living Glass" UI
 * Transitioning from "Generic AI" to a more human, premium, and artisanal experience.
 */

import { useEffect, useState } from 'react';
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

type AuthPageProps = {
  onClose: () => void;
  onSuccess?: () => void;
  initialMode?: 'login' | 'register';
};

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
  const { login, register, error, clearError, isLoading } = useAuth();
  const [mode, setMode] = useState<'login' | 'register'>(initialMode);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);
  const [isHovered, setIsHovered] = useState(false);
  
  const [compactViewport, setCompactViewport] = useState(() => (
    typeof window !== 'undefined' ? window.innerWidth < 720 : false
  ));

  useEffect(() => {
    setMode(initialMode);
    setLocalError(null);
    clearError();
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

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLocalError(null);
    clearError();

    if (!email.trim() || !password.trim()) {
      setLocalError('Required fields are missing.');
      return;
    }

    if (mode === 'register' && password.length < 8) {
      setLocalError('Security requires at least 8 characters.');
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
      // Error handled by useAuth
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
          width: compactViewport ? 'min(100vw - 1.5rem, 460px)' : '460px',
          borderRadius: '2rem',
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid rgba(255,255,255,0.1)',
          boxShadow: isHovered 
            ? '0 64px 120px rgba(0,0,0,0.7), inset 0 1px 0 rgba(255,255,255,0.15)'
            : '0 48px 100px rgba(0,0,0,0.6), inset 0 1px 0 rgba(255,255,255,0.1)',
          overflow: 'hidden',
          maxHeight: 'min(94vh, 820px)',
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

        <div style={{ padding: '2.5rem 2rem 0', textAlign: 'center', position: 'relative', zIndex: 1 }}>
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
              margin: '0 auto 1.5rem',
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
            marginBottom: '1rem'
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
            marginBottom: '0.5rem'
          }}>
            {mode === 'login' ? 'Welcome Back' : 'Get Started'}
          </h2>

          <p style={{
            fontSize: '0.9rem',
            color: 'var(--text-muted)',
            lineHeight: 1.6,
            maxWidth: '320px',
            margin: '0 auto 2rem'
          }}>
            {mode === 'login' 
              ? 'Enter your credentials to access your screening laboratory.'
              : 'Create your secure account to begin your health intelligence journey.'}
          </p>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(3, 1fr)',
            gap: '0.75rem',
            marginBottom: '2.5rem'
          }}>
            {authBenefits.map((b, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.4 + i * 0.1 }}
                style={{
                  padding: '1rem 0.5rem',
                  borderRadius: '1.25rem',
                  background: 'rgba(255,255,255,0.02)',
                  border: '1px solid rgba(255,255,255,0.05)',
                  display: 'flex',
                  flexDirection: 'column',
                  alignItems: 'center',
                  gap: '0.5rem',
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
          margin: '0 2rem',
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
                setMode(tab);
                setLocalError(null);
                clearError();
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

        <form onSubmit={handleSubmit} style={{ padding: '2rem' }}>
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
                minLength={8}
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
            disabled={isLoading}
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
              cursor: isLoading ? 'not-allowed' : 'pointer',
              boxShadow: '0 12px 32px rgba(37,99,235,0.3)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '0.75rem',
              opacity: isLoading ? 0.7 : 1,
            }}
          >
            {isLoading ? (
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
