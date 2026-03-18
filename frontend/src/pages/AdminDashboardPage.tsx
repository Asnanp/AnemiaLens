/**
 * Admin Dashboard — Global Analytics
 */

import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '../hooks/useAuth';
import { RefreshCw, Users, Activity, BarChart2, AlertTriangle, ShieldCheck } from 'lucide-react';

const E = [0.22, 1, 0.36, 1] as const;

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
function endpoint(path: string): string {
  return API_BASE ? `${API_BASE}${path}` : path;
}

interface AdminStats {
  total_users: int;
  total_scans: int;
  scans_by_band: Record<string, int>;
  avg_processing_time_ms: float;
  blocked_scans: int;
}

export default function AdminDashboardPage({ onClose }: { onClose: () => void }) {
  const { user, getAccessToken } = useAuth();
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    const token = getAccessToken();
    if (!token) return;

    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(endpoint('/api/admin/stats'), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to load admin stats');
      const data = await res.json();
      setStats(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load stats');
    } finally {
      setIsLoading(false);
    }
  }, [getAccessToken]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  if (!user || user.role !== 'admin') {
    return null;
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      style={{
        position: 'fixed', inset: 0, zIndex: 10000,
        display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
        background: 'rgba(4,4,10,0.92)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        overflowY: 'auto',
        padding: '4rem 1rem',
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: E }}
        style={{
          width: 'min(880px, 100%)',
          borderRadius: '1.5rem',
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid rgba(255,255,255,0.06)',
          backdropFilter: 'blur(40px)',
          boxShadow: '0 48px 100px rgba(0,0,0,0.6)',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div style={{
          padding: '2rem 2.5rem',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          background: 'linear-gradient(90deg, rgba(200,0,30,0.08), transparent)',
        }}>
          <div>
            <h2 style={{ fontFamily: 'var(--serif)', fontSize: '1.4rem', fontWeight: 700, marginBottom: '0.3rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ShieldCheck size={20} style={{ color: '#EF4444' }} /> Admin Analytics
            </h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>
              System-wide usage and performance metrics
            </p>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button
              onClick={fetchStats}
              disabled={isLoading}
              className="btn btn-glass"
              style={{
                display: 'flex', alignItems: 'center', gap: '0.4rem',
                padding: '0.5rem 1rem', fontSize: '0.65rem', borderRadius: '0.625rem',
              }}
            >
              <RefreshCw size={12} style={{ animation: isLoading ? 'spin 1s linear infinite' : 'none' }} />
              Refresh
            </button>
            <button
              onClick={onClose}
              className="btn btn-glass"
              style={{ padding: '0.5rem 1rem', fontSize: '0.65rem', borderRadius: '0.625rem' }}
            >
              Close
            </button>
          </div>
        </div>

        {error && (
          <div style={{ padding: '1rem 2.5rem' }}>
            <div style={{ padding: '1rem', background: 'rgba(239,68,68,0.1)', color: '#FCA5A5', borderRadius: '0.75rem', border: '1px solid rgba(239,68,68,0.2)' }}>
              {error}
            </div>
          </div>
        )}

        {/* Quick stats */}
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem',
          padding: '1.5rem 2.5rem',
        }}>
          {[
            { icon: <Users size={16} />, label: 'Total Users', value: stats?.total_users ?? '-' },
            { icon: <Activity size={16} />, label: 'Total Scans', value: stats?.total_scans ?? '-' },
            { icon: <AlertTriangle size={16} />, label: 'Blocked (Quality)', value: stats?.blocked_scans ?? '-' },
            { icon: <BarChart2 size={16} />, label: 'Avg Inference Time', value: stats ? `${stats.avg_processing_time_ms.toFixed(0)}ms` : '-' },
          ].map((stat, i) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08, ease: E }}
              style={{
                padding: '1.25rem 1rem', borderRadius: '0.875rem',
                background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)',
                textAlign: 'center',
              }}
            >
              <div style={{ color: 'var(--accent-bright)', marginBottom: '0.6rem', display: 'flex', justifyContent: 'center' }}>{stat.icon}</div>
              <div style={{ fontFamily: 'var(--serif)', fontSize: '1.6rem', fontWeight: 700, marginBottom: '0.3rem' }}>{stat.value}</div>
              <div style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-dim)' }}>{stat.label}</div>
            </motion.div>
          ))}
        </div>

        {/* Breakdown */}
        {stats && (
          <div style={{ padding: '0 2.5rem 2.5rem' }}>
            <h3 style={{ fontSize: '0.85rem', fontWeight: 600, fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-muted)', marginBottom: '1rem' }}>
              Risk Triage Breakdown
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
              {Object.entries(stats.scans_by_band).map(([band, count]) => (
                <div key={band} style={{
                  padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '0.75rem',
                  border: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center'
                }}>
                  <span style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>{band.replace(/_/g, ' ')}</span>
                  <span style={{ fontSize: '1.1rem', fontWeight: 700 }}>{count}</span>
                </div>
              ))}
              {Object.keys(stats.scans_by_band).length === 0 && (
                <div style={{ padding: '1rem', color: 'var(--text-dim)', fontSize: '0.8rem' }}>No scans processed yet.</div>
              )}
            </div>
          </div>
        )}

      </motion.div>
    </motion.div>
  );
}
