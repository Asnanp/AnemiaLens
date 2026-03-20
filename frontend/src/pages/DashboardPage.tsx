/**
 * User dashboard — screening history and account info.
 */
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../hooks/useAuth';
import { useHistory } from '../hooks/useHistory';
import {
  History, Trash2, RefreshCw, ChevronRight,
  Activity, Clock, Shield, TrendingUp, X,
} from 'lucide-react';

const E = [0.22, 1, 0.36, 1] as const;

function bandColor(band: string): string {
  switch (band) {
    case 'low_risk': return '#10B981';
    case 'moderate_risk': return '#F59E0B';
    case 'high_concern': return '#EF4444';
    case 'uncertain_retake_needed': return '#8B5CF6';
    default: return '#64748B';
  }
}

function bandLabel(band: string): string {
  switch (band) {
    case 'low_risk': return 'Low Risk';
    case 'moderate_risk': return 'Moderate';
    case 'high_concern': return 'High Concern';
    case 'uncertain_retake_needed': return 'Retake Needed';
    default: return band;
  }
}

export default function DashboardPage({ onClose }: { onClose: () => void }) {
  const { user, logout } = useAuth();
  const { screenings, total, isLoading, error, refresh, deleteScreening, loadMore } = useHistory();

  if (!user) return null;

  const avgRisk = screenings.length > 0
    ? screenings.filter(s => s.anemia_risk !== null)
        .reduce((sum, s) => sum + (s.anemia_risk ?? 0), 0) /
      Math.max(screenings.filter(s => s.anemia_risk !== null).length, 1)
    : 0;

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      style={{
        position: 'fixed', inset: 0, zIndex: 10000,
        display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
        background: 'rgba(4,4,10,0.9)', backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)', overflowY: 'auto', padding: '4rem 1rem',
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <motion.div
        initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: E }}
        style={{
          width: 'min(820px, 100%)', borderRadius: '1.5rem',
          background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.07)',
          backdropFilter: 'blur(40px)', boxShadow: '0 48px 100px rgba(0,0,0,0.6)',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div style={{
          padding: '1.75rem 2.5rem',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{
              width: 44, height: 44, borderRadius: '0.875rem',
              background: 'rgba(200,0,30,0.12)',
              border: '1px solid rgba(200,0,30,0.2)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '1rem', fontWeight: 800, fontFamily: 'var(--mono)',
              color: 'var(--accent-bright)',
            }}>
              {(user.full_name?.[0] || user.email[0]).toUpperCase()}
            </div>
            <div>
              <span style={{ fontFamily: 'var(--serif)', fontSize: '1.1rem', fontWeight: 700 }}>
                {user.full_name || user.email.split('@')[0]}
              </span>
              <p style={{ fontSize: '0.7rem', color: 'var(--text-dim)', marginTop: '0.1rem' }}>
                {user.email}
              </p>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.625rem' }}>
            <button onClick={onClose} className="btn btn-glass"
              style={{ padding: '0.45rem 0.875rem', fontSize: '0.62rem', borderRadius: '0.625rem' }}>
              Close
            </button>
            <button onClick={() => { logout(); onClose(); }} className="btn btn-glass"
              style={{ padding: '0.45rem 0.875rem', fontSize: '0.62rem', borderRadius: '0.625rem', color: '#EF4444', borderColor: 'rgba(239,68,68,0.2)' }}>
              Sign Out
            </button>
          </div>
        </div>

        {/* Stats grid */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '0.875rem', padding: '1.5rem 2.5rem' }}>
          {[
            { icon: <Activity size={15} />, label: 'Total Scans', value: String(total) },
            { icon: <TrendingUp size={15} />, label: 'Avg Risk', value: `${(avgRisk * 100).toFixed(0)}%` },
            { icon: <Clock size={15} />, label: 'Member Since', value: new Date(user.created_at).toLocaleDateString('en-US', { month: 'short', year: 'numeric' }) },
            { icon: <Shield size={15} />, label: 'Plan', value: 'Free' },
          ].map((stat, i) => (
            <motion.div key={stat.label}
              initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.07, ease: E }}
              style={{
                padding: '1rem', borderRadius: '0.875rem', textAlign: 'center',
                background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)',
              }}
            >
              <div style={{ color: 'var(--accent-bright)', marginBottom: '0.4rem', display: 'flex', justifyContent: 'center' }}>{stat.icon}</div>
              <div style={{ fontFamily: 'var(--serif)', fontSize: '1.2rem', fontWeight: 700, marginBottom: '0.15rem' }}>{stat.value}</div>
              <div style={{ fontSize: '0.58rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-dim)' }}>{stat.label}</div>
            </motion.div>
          ))}
        </div>

        {/* History header */}
        <div style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '0.5rem 2.5rem 0.75rem',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            <History size={15} style={{ color: 'var(--accent-bright)' }} />
            <span style={{ fontFamily: 'var(--mono)', fontSize: '0.65rem', textTransform: 'uppercase', letterSpacing: '0.1em', fontWeight: 600 }}>
              Screening History
            </span>
          </div>
          <button onClick={refresh} disabled={isLoading}
            style={{
              display: 'flex', alignItems: 'center', gap: '0.4rem',
              padding: '0.4rem 0.75rem', fontSize: '0.6rem',
              fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.1em',
              background: 'rgba(255,255,255,0.04)', color: 'var(--text-dim)',
              border: '1px solid rgba(255,255,255,0.06)', borderRadius: '0.5rem', cursor: 'pointer',
            }}
          >
            <RefreshCw size={11} style={{ animation: isLoading ? 'spin 1s linear infinite' : 'none' }} />
            Refresh
          </button>
        </div>

        {/* History list */}
        <div style={{ padding: '0 2.5rem 2rem' }}>
          {error && (
            <div style={{
              padding: '0.75rem 1rem', borderRadius: '0.625rem',
              background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.15)',
              fontSize: '0.75rem', color: '#FCA5A5', marginBottom: '1rem',
            }}>{error}</div>
          )}

          {screenings.length === 0 && !isLoading && (
            <div style={{ padding: '3rem 1rem', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.82rem' }}>
              No screenings yet. Run your first scan to see results here.
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
            <AnimatePresence>
              {screenings.map((s, i) => (
                <motion.div key={s.uid}
                  initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 12 }} transition={{ delay: i * 0.03, ease: E }}
                  className="glass glass-hover"
                  style={{ padding: '0.875rem 1.125rem', display: 'flex', alignItems: 'center', gap: '0.875rem', cursor: 'pointer' }}
                >
                  <div style={{
                    width: 6, height: 32, borderRadius: 3, flexShrink: 0,
                    background: bandColor(s.triage_band),
                    boxShadow: `0 0 8px ${bandColor(s.triage_band)}50`,
                  }} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.2rem' }}>
                      <span style={{
                        fontSize: '0.52rem', fontFamily: 'var(--mono)', textTransform: 'uppercase',
                        letterSpacing: '0.1em', padding: '0.12rem 0.45rem', borderRadius: '0.3rem',
                        background: `${bandColor(s.triage_band)}15`, color: bandColor(s.triage_band),
                        border: `1px solid ${bandColor(s.triage_band)}30`, fontWeight: 600,
                      }}>
                        {bandLabel(s.triage_band)}
                      </span>
                      {s.screening_label && (
                        <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                          {s.screening_label.replace(/_/g, ' ')}
                        </span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>
                      {new Date(s.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' })}
                      {s.anemia_risk !== null && <span style={{ marginLeft: '0.75rem' }}>Risk: {(s.anemia_risk * 100).toFixed(0)}%</span>}
                      {s.predicted_hemoglobin !== null && <span style={{ marginLeft: '0.75rem' }}>Hb: {s.predicted_hemoglobin.toFixed(1)} g/dL</span>}
                    </div>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); deleteScreening(s.uid); }}
                    style={{
                      background: 'rgba(239,68,68,0.07)', border: '1px solid rgba(239,68,68,0.12)',
                      borderRadius: '0.45rem', padding: '0.35rem', cursor: 'pointer',
                      color: 'rgba(239,68,68,0.55)', transition: 'all 0.2s', flexShrink: 0,
                    }}
                    title="Delete"
                  >
                    <Trash2 size={12} />
                  </button>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>

          {screenings.length < total && (
            <button onClick={loadMore} disabled={isLoading}
              style={{
                display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.4rem',
                width: '100%', padding: '0.75rem', marginTop: '0.875rem',
                fontSize: '0.65rem', fontFamily: 'var(--mono)', textTransform: 'uppercase',
                letterSpacing: '0.1em', background: 'rgba(255,255,255,0.03)',
                color: 'var(--text-muted)', border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '0.75rem', cursor: 'pointer',
              }}
            >
              Load More <ChevronRight size={12} />
            </button>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}