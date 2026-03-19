/**
 * Demo Stripe Checkout Modal
 * Looks like a real Stripe checkout. On submit it calls the backend
 * which auto-upgrades the user (demo mode — no real charge).
 */
import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Lock, CreditCard, Crown, Check, Loader2 } from 'lucide-react';
import { endpoint } from '../api';

const E = [0.22, 1, 0.36, 1] as const;

interface Props {
  onClose: () => void;
  onSuccess: () => void;
  userEmail: string;
}

function formatCard(v: string) {
  return v.replace(/\D/g, '').slice(0, 16).replace(/(.{4})/g, '$1 ').trim();
}
function formatExpiry(v: string) {
  const d = v.replace(/\D/g, '').slice(0, 4);
  return d.length >= 3 ? `${d.slice(0, 2)}/${d.slice(2)}` : d;
}

export function StripeCheckoutModal({ onClose, onSuccess, userEmail }: Props) {
  const [card, setCard] = useState('4242 4242 4242 4242');
  const [expiry, setExpiry] = useState('12/28');
  const [cvc, setCvc] = useState('424');
  const [name, setName] = useState('Demo User');
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');

  const isValid = card.replace(/\s/g, '').length === 16 && expiry.length === 5 && cvc.length >= 3 && name.trim().length > 1;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValid || loading) return;
    setError('');
    setLoading(true);
    try {
      // Read token — same key used by useAuth
      const raw = localStorage.getItem('anemialens.tokens');
      const accessToken = raw ? JSON.parse(raw).access_token : null;

      if (!accessToken) {
        setError('Not logged in. Please sign in and try again.');
        return;
      }

      const res = await fetch(endpoint('/api/billing/create-checkout-session'), {
        method: 'POST',
        headers: { Authorization: `Bearer ${accessToken}` },
        signal: AbortSignal.timeout(20000),
      });

      if (!res.ok) {
        let msg = `Request failed (${res.status})`;
        try { const b = await res.json(); msg = b.detail || b.error || msg; } catch { /* use default */ }
        setError(msg);
        return;
      }

      const data = await res.json();

      // Demo mode: backend returns /?payment_success=true — intercept and show success
      if (data.checkout_url) {
        if (data.checkout_url.includes('payment_success=true')) {
          setDone(true);
          setTimeout(() => { onSuccess(); }, 2000);
        } else {
          // Real Stripe URL — redirect
          window.location.href = data.checkout_url;
        }
      } else {
        setError('Unexpected response from server.');
      }
    } catch (err) {
      if (err instanceof Error && err.name === 'TimeoutError') {
        setError('Request timed out. Check your connection and try again.');
      } else {
        setError(err instanceof Error ? err.message : 'Payment processing failed.');
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      style={{
        position: 'fixed', inset: 0, zIndex: 30000,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'rgba(0,0,0,0.75)', backdropFilter: 'blur(12px)',
        padding: '1rem',
      }}
      onClick={(e) => { if (e.target === e.currentTarget && !loading) onClose(); }}
    >
      <motion.div
        initial={{ opacity: 0, scale: 0.94, y: 16 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.94, y: 16 }}
        transition={{ duration: 0.35, ease: E }}
        style={{
          width: 'min(460px, 100%)',
          borderRadius: '1.25rem',
          background: '#0f0f1a',
          border: '1px solid rgba(255,255,255,0.1)',
          boxShadow: '0 48px 100px rgba(0,0,0,0.8)',
          overflow: 'hidden',
        }}
      >
        {/* Success state */}
        <AnimatePresence>
          {done && (
            <motion.div
              initial={{ opacity: 0 }} animate={{ opacity: 1 }}
              style={{
                position: 'absolute', inset: 0, zIndex: 10,
                display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
                background: '#0f0f1a', gap: '1.25rem', padding: '2rem',
              }}
            >
              <motion.div
                initial={{ scale: 0 }} animate={{ scale: 1 }}
                transition={{ type: 'spring', stiffness: 300, damping: 20 }}
                style={{
                  width: 72, height: 72, borderRadius: '50%',
                  background: 'linear-gradient(135deg, #FFD700, #FFA500)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  boxShadow: '0 0 40px rgba(255,215,0,0.4)',
                }}
              >
                <Check size={32} color="#000" strokeWidth={3} />
              </motion.div>
              <div style={{ textAlign: 'center' }}>
                <div style={{ fontFamily: 'var(--serif)', fontSize: '1.4rem', fontWeight: 700, marginBottom: '0.4rem' }}>
                  Payment Successful!
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
                  Welcome to AnemiaLens Pro. Activating your account...
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Header */}
        <div style={{
          padding: '1.5rem 1.75rem 1.25rem',
          borderBottom: '1px solid rgba(255,255,255,0.07)',
          display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div style={{
              width: 36, height: 36, borderRadius: '0.625rem',
              background: 'linear-gradient(135deg, #FFD700, #FFA500)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Crown size={18} color="#000" />
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: '0.95rem' }}>AnemiaLens Pro</div>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)' }}>Unlimited screenings</div>
            </div>
          </div>
          <button onClick={onClose} disabled={loading} style={{
            background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.1)',
            borderRadius: '0.5rem', padding: '0.35rem', cursor: 'pointer', color: 'var(--text-dim)',
          }}>
            <X size={14} />
          </button>
        </div>

        {/* Price */}
        <div style={{
          padding: '1.25rem 1.75rem',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div>
            <div style={{ fontSize: '0.78rem', fontWeight: 600 }}>Pro Monthly Plan</div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', marginTop: '0.15rem' }}>
              Billed monthly · Cancel anytime
            </div>
          </div>
          <div style={{ textAlign: 'right' }}>
            <div style={{ fontFamily: 'var(--serif)', fontSize: '1.5rem', fontWeight: 700 }}>$9.99</div>
            <div style={{ fontSize: '0.6rem', color: 'var(--text-dim)' }}>/ month</div>
          </div>
        </div>

        {/* Demo banner */}
        <div style={{
          margin: '0 1.75rem',
          padding: '0.6rem 0.875rem',
          borderRadius: '0.625rem',
          background: 'rgba(99,91,255,0.08)',
          border: '1px solid rgba(99,91,255,0.25)',
          display: 'flex', alignItems: 'center', gap: '0.6rem',
          marginTop: '1rem',
        }}>
          <span style={{
            fontSize: '0.6rem', fontFamily: 'var(--mono)', fontWeight: 700,
            padding: '0.15rem 0.45rem', borderRadius: '0.3rem',
            background: 'rgba(99,91,255,0.25)', color: '#a5b4fc',
            textTransform: 'uppercase', letterSpacing: '0.08em', flexShrink: 0,
          }}>Demo</span>
          <span style={{ fontSize: '0.68rem', color: 'rgba(165,180,252,0.8)', lineHeight: 1.4 }}>
            Test mode — fake details pre-filled. No real charge will occur.
          </span>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ padding: '1.5rem 1.75rem', display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          {/* Email (pre-filled) */}
          <div>
            <label style={{ fontSize: '0.65rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-dim)', display: 'block', marginBottom: '0.4rem' }}>
              Email
            </label>
            <input
              type="email" value={userEmail} readOnly
              style={{
                width: '100%', padding: '0.7rem 0.875rem', borderRadius: '0.625rem',
                background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.1)',
                color: 'var(--text-muted)', fontSize: '0.82rem', outline: 'none',
                boxSizing: 'border-box',
              }}
            />
          </div>

          {/* Card number */}
          <div>
            <label style={{ fontSize: '0.65rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-dim)', display: 'block', marginBottom: '0.4rem' }}>
              Card Number
            </label>
            <div style={{ position: 'relative' }}>
              <input
                type="text" placeholder="4242 4242 4242 4242"
                value={card} onChange={e => setCard(formatCard(e.target.value))}
                maxLength={19} autoComplete="cc-number"
                style={{
                  width: '100%', padding: '0.7rem 2.5rem 0.7rem 0.875rem', borderRadius: '0.625rem',
                  background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.12)',
                  color: 'var(--text)', fontSize: '0.85rem', outline: 'none',
                  fontFamily: 'var(--mono)', letterSpacing: '0.05em', boxSizing: 'border-box',
                  transition: 'border-color 0.2s',
                }}
                onFocus={e => e.target.style.borderColor = 'rgba(255,215,0,0.4)'}
                onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.12)'}
              />
              <CreditCard size={16} style={{ position: 'absolute', right: '0.875rem', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-dim)' }} />
            </div>
          </div>

          {/* Expiry + CVC */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '0.75rem' }}>
            <div>
              <label style={{ fontSize: '0.65rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-dim)', display: 'block', marginBottom: '0.4rem' }}>
                Expiry
              </label>
              <input
                type="text" placeholder="MM/YY"
                value={expiry} onChange={e => setExpiry(formatExpiry(e.target.value))}
                maxLength={5} autoComplete="cc-exp"
                style={{
                  width: '100%', padding: '0.7rem 0.875rem', borderRadius: '0.625rem',
                  background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.12)',
                  color: 'var(--text)', fontSize: '0.85rem', outline: 'none',
                  fontFamily: 'var(--mono)', boxSizing: 'border-box', transition: 'border-color 0.2s',
                }}
                onFocus={e => e.target.style.borderColor = 'rgba(255,215,0,0.4)'}
                onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.12)'}
              />
            </div>
            <div>
              <label style={{ fontSize: '0.65rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-dim)', display: 'block', marginBottom: '0.4rem' }}>
                CVC
              </label>
              <input
                type="text" placeholder="123"
                value={cvc} onChange={e => setCvc(e.target.value.replace(/\D/g, '').slice(0, 4))}
                maxLength={4} autoComplete="cc-csc"
                style={{
                  width: '100%', padding: '0.7rem 0.875rem', borderRadius: '0.625rem',
                  background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.12)',
                  color: 'var(--text)', fontSize: '0.85rem', outline: 'none',
                  fontFamily: 'var(--mono)', boxSizing: 'border-box', transition: 'border-color 0.2s',
                }}
                onFocus={e => e.target.style.borderColor = 'rgba(255,215,0,0.4)'}
                onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.12)'}
              />
            </div>
          </div>

          {/* Name */}
          <div>
            <label style={{ fontSize: '0.65rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-dim)', display: 'block', marginBottom: '0.4rem' }}>
              Name on Card
            </label>
            <input
              type="text" placeholder="John Doe"
              value={name} onChange={e => setName(e.target.value)}
              autoComplete="cc-name"
              style={{
                width: '100%', padding: '0.7rem 0.875rem', borderRadius: '0.625rem',
                background: 'rgba(255,255,255,0.05)', border: '1px solid rgba(255,255,255,0.12)',
                color: 'var(--text)', fontSize: '0.85rem', outline: 'none',
                boxSizing: 'border-box', transition: 'border-color 0.2s',
              }}
              onFocus={e => e.target.style.borderColor = 'rgba(255,215,0,0.4)'}
              onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.12)'}
            />
          </div>

          {error && (
            <div style={{ fontSize: '0.72rem', color: '#FCA5A5', padding: '0.6rem 0.875rem', borderRadius: '0.5rem', background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }}>
              {error}
            </div>
          )}

          {/* Submit */}
          <button
            type="submit" disabled={!isValid || loading}
            style={{
              width: '100%', padding: '0.875rem',
              borderRadius: '0.75rem', border: 'none',
              background: isValid && !loading
                ? 'linear-gradient(135deg, #FFD700, #FFA500)'
                : 'rgba(255,255,255,0.08)',
              color: isValid && !loading ? '#000' : 'var(--text-dim)',
              fontWeight: 700, fontSize: '0.85rem',
              fontFamily: 'var(--mono)', letterSpacing: '0.05em', textTransform: 'uppercase',
              cursor: isValid && !loading ? 'pointer' : 'not-allowed',
              transition: 'all 0.25s',
              display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem',
              boxShadow: isValid && !loading ? '0 0 30px rgba(255,215,0,0.2)' : 'none',
            }}
          >
            {loading ? (
              <><Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} /> Processing...</>
            ) : (
              <><Lock size={14} /> Pay $9.99 / month — Demo</>
            )}
          </button>

          {/* Stripe badge */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem', marginTop: '-0.25rem' }}>
            <Lock size={10} style={{ color: 'var(--text-dim)' }} />
            <span style={{ fontSize: '0.6rem', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>
              Secured by <span style={{ color: '#635BFF', fontWeight: 700 }}>Stripe</span> · Test mode · No real charge
            </span>
          </div>
        </form>
      </motion.div>
    </motion.div>
  );
}
