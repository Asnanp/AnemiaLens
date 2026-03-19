/**
 * Admin Dashboard — Global Analytics + User Management
 */

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAuth } from '../hooks/useAuth';
import { toast } from '../components/Toast';
import {
  RefreshCw, Users, Activity, BarChart2, AlertTriangle,
  ShieldCheck, Crown, UserX, UserCheck, ChevronRight,
} from 'lucide-react';

const E = [0.22, 1, 0.36, 1] as const;

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
function endpoint(path: string): string {
  return API_BASE ? `${API_BASE}${path}` : path;
}

interface AdminStats {
  total_users: number;
  total_scans: number;
  scans_by_band: Record<string, number>;
  avg_processing_time_ms: number;
  blocked_scans: number;
  pro_users: number;
  free_users: number;
}

interface AdminUser {
  uid: string;
  email: string;
  full_name: string | null;
  role: string;
  subscription_tier: string;
  scan_count: number;
  is_active: boolean;
  created_at: string;
}

type Tab = 'stats' | 'users';

export default function AdminDashboardPage({ onClose }: { onClose: () => void }) {
  const { user, getAccessToken } = useAuth();
  const [tab, setTab] = useState<Tab>('stats');
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [togglingUid, setTogglingUid] = useState<string | null>(null);

  const fetchStats = useCallback(async () => {
    const token = getAccessToken();
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(endpoint('/api/admin/stats'), { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error('Failed to load admin stats');
      setStats(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load stats');
    } finally {
      setIsLoading(false);
    }
  }, [getAccessToken]);

  const fetchUsers = useCallback(async () => {
    const token = getAccessToken();
    if (!token) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(endpoint('/api/admin/users?page=1&page_size=50'), { headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error('Failed to load users');
      const data = await res.json();
      setUsers(data.users);
      setTotalUsers(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load users');
    } finally {
      setIsLoading(false);
    }
  }, [getAccessToken]);

  useEffect(() => { fetchStats(); }, [fetchStats]);
  useEffect(() => { if (tab === 'users') fetchUsers(); }, [tab, fetchUsers]);

  const togglePlan = async (uid: string, current: string) => {
    const token = getAccessToken();
    if (!token) return;
    const newTier = current === 'pro' ? 'free' : 'pro';
    setTogglingUid(uid);
    try {
      const res = await fetch(endpoint(`/api/admin/users/${uid}/plan`), {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ subscription_tier: newTier }),
      });
      if (!res.ok) throw new Error('Failed to update plan');
      setUsers(prev => prev.map(u => u.uid === uid ? { ...u, subscription_tier: newTier } : u));
      toast.success(`User plan updated to ${newTier}`);
    } catch {
      toast.error('Failed to update plan');
    } finally {
      setTogglingUid(null);
    }
  };

  const toggleActive = async (uid: string) => {
    const token = getAccessToken();
    if (!token) return;
    setTogglingUid(uid);
    try {
      const res = await fetch(endpoint(`/api/admin/users/${uid}/active`), {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to toggle active');
      const data = await res.json();
      setUsers(prev => prev.map(u => u.uid === uid ? { ...u, is_active: data.is_active } : u));
      toast.success(`User ${data.is_active ? 'activated' : 'deactivated'}`);
    } catch {
      toast.error('Failed to toggle user status');
    } finally {
      setTogglingUid(null);
    }
  };

  if (!user || user.role !== 'admin') return null;

  return (
    <motion.div
      initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      style={{
        position: 'fixed', inset: 0, zIndex: 10000,
        display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
        background: 'rgba(4,4,10,0.92)', backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)', overflowY: 'auto', padding: '4rem 1rem',
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <motion.div
        initial={{ opacity: 0, y: 30 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: E }}
        style={{
          width: 'min(920px, 100%)', borderRadius: '1.5rem',
          background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)',
          backdropFilter: 'blur(40px)', boxShadow: '0 48px 100px rgba(0,0,0,0.6)',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div style={{ padding: '2rem 2.5rem', borderBottom: '1px solid rgba(255,255,255,0.06)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'linear-gradient(90deg, rgba(200,0,30,0.08), transparent)' }}>
          <div>
            <h2 style={{ fontFamily: 'var(--serif)', fontSize: '1.4rem', fontWeight: 700, marginBottom: '0.3rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
              <ShieldCheck size={20} style={{ color: '#EF4444' }} /> Admin Panel
            </h2>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-dim)' }}>System-wide analytics and user management</p>
          </div>
          <div style={{ display: 'flex', gap: '0.75rem' }}>
            <button onClick={() => tab === 'stats' ? fetchStats() : fetchUsers()} disabled={isLoading} className="btn btn-glass"
              style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', padding: '0.5rem 1rem', fontSize: '0.65rem', borderRadius: '0.625rem' }}>
              <RefreshCw size={12} style={{ animation: isLoading ? 'spin 1s linear infinite' : 'none' }} /> Refresh
            </button>
            <button onClick={onClose} className="btn btn-glass" style={{ padding: '0.5rem 1rem', fontSize: '0.65rem', borderRadius: '0.625rem' }}>Close</button>
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display: 'flex', gap: '0.25rem', padding: '1rem 2.5rem 0', borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
          {(['stats', 'users'] as Tab[]).map(t => (
            <button key={t} onClick={() => setTab(t)}
              style={{
                padding: '0.5rem 1.25rem', fontSize: '0.65rem', fontFamily: 'var(--mono)',
                textTransform: 'uppercase', letterSpacing: '0.1em', borderRadius: '0.5rem 0.5rem 0 0',
                background: tab === t ? 'rgba(200,0,30,0.1)' : 'transparent',
                color: tab === t ? 'var(--accent-bright)' : 'var(--text-dim)',
                border: tab === t ? '1px solid rgba(200,0,30,0.2)' : '1px solid transparent',
                borderBottom: 'none', cursor: 'pointer', fontWeight: tab === t ? 700 : 400,
              }}
            >
              {t === 'stats' ? 'Analytics' : `Users (${totalUsers || '—'})`}
            </button>
          ))}
        </div>

        {error && (
          <div style={{ padding: '1rem 2.5rem' }}>
            <div style={{ padding: '1rem', background: 'rgba(239,68,68,0.1)', color: '#FCA5A5', borderRadius: '0.75rem', border: '1px solid rgba(239,68,68,0.2)', fontSize: '0.78rem' }}>{error}</div>
          </div>
        )}

        {/* Stats Tab */}
        {tab === 'stats' && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '1rem', padding: '1.5rem 2.5rem' }}>
              {[
                { icon: <Users size={16} />, label: 'Total Users', value: stats?.total_users ?? '-' },
                { icon: <Activity size={16} />, label: 'Total Scans', value: stats?.total_scans ?? '-' },
                { icon: <Crown size={16} />, label: 'Pro Users', value: stats?.pro_users ?? '-' },
                { icon: <AlertTriangle size={16} />, label: 'Blocked Scans', value: stats?.blocked_scans ?? '-' },
              ].map((stat, i) => (
                <motion.div key={stat.label}
                  initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08, ease: E }}
                  style={{ padding: '1.25rem 1rem', borderRadius: '0.875rem', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', textAlign: 'center' }}
                >
                  <div style={{ color: 'var(--accent-bright)', marginBottom: '0.6rem', display: 'flex', justifyContent: 'center' }}>{stat.icon}</div>
                  <div style={{ fontFamily: 'var(--serif)', fontSize: '1.6rem', fontWeight: 700, marginBottom: '0.3rem' }}>{stat.value}</div>
                  <div style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-dim)' }}>{stat.label}</div>
                </motion.div>
              ))}
            </div>
            {stats && (
              <div style={{ padding: '0 2.5rem 2.5rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
                  <h3 style={{ fontSize: '0.75rem', fontWeight: 600, fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.1em', color: 'var(--text-muted)' }}>Risk Triage Breakdown</h3>
                  <span style={{ fontSize: '0.65rem', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>Avg inference: {stats.avg_processing_time_ms.toFixed(0)}ms</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
                  {Object.entries(stats.scans_by_band).map(([band, count]) => (
                    <div key={band} style={{ padding: '1rem', background: 'rgba(255,255,255,0.02)', borderRadius: '0.75rem', border: '1px solid rgba(255,255,255,0.05)', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.72rem', color: 'var(--text-dim)' }}>{band.replace(/_/g, ' ')}</span>
                      <span style={{ fontSize: '1.1rem', fontWeight: 700 }}>{count}</span>
                    </div>
                  ))}
                  {Object.keys(stats.scans_by_band).length === 0 && (
                    <div style={{ padding: '1rem', color: 'var(--text-dim)', fontSize: '0.8rem' }}>No scans processed yet.</div>
                  )}
                </div>
              </div>
            )}
          </>
        )}

        {/* Users Tab */}
        {tab === 'users' && (
          <div style={{ padding: '1.5rem 2.5rem 2.5rem' }}>
            {users.length === 0 && !isLoading && (
              <div style={{ padding: '2rem', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.8rem' }}>No users found.</div>
            )}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
              {users.map((u, i) => (
                <motion.div key={u.uid}
                  initial={{ opacity: 0, x: -12 }} animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: i * 0.025, ease: E }}
                  style={{
                    display: 'flex', alignItems: 'center', gap: '0.875rem',
                    padding: '0.875rem 1rem', borderRadius: '0.75rem',
                    background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)',
                    opacity: u.is_active ? 1 : 0.5,
                  }}
                >
                  {/* Avatar */}
                  <div style={{ width: 32, height: 32, borderRadius: '0.5rem', background: u.subscription_tier === 'pro' ? 'linear-gradient(135deg, rgba(255,215,0,0.2), rgba(255,165,0,0.1))' : 'rgba(255,255,255,0.06)', border: `1px solid ${u.subscription_tier === 'pro' ? 'rgba(255,215,0,0.3)' : 'rgba(255,255,255,0.1)'}`, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.7rem', fontWeight: 700, color: u.subscription_tier === 'pro' ? '#FFD700' : 'var(--text-muted)', flexShrink: 0 }}>
                    {(u.full_name?.[0] || u.email[0]).toUpperCase()}
                  </div>
                  {/* Info */}
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', marginBottom: '0.15rem' }}>
                      <span style={{ fontSize: '0.78rem', fontWeight: 600, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{u.email}</span>
                      {u.subscription_tier === 'pro' && (
                        <span style={{ fontSize: '0.45rem', fontFamily: 'var(--mono)', fontWeight: 700, padding: '0.1rem 0.35rem', borderRadius: '99px', background: 'linear-gradient(135deg, #FFD700, #FFA500)', color: '#000', textTransform: 'uppercase', letterSpacing: '0.08em', flexShrink: 0 }}>PRO</span>
                      )}
                      {u.role === 'admin' && (
                        <span style={{ fontSize: '0.45rem', fontFamily: 'var(--mono)', fontWeight: 700, padding: '0.1rem 0.35rem', borderRadius: '99px', background: 'rgba(239,68,68,0.15)', color: '#EF4444', border: '1px solid rgba(239,68,68,0.3)', textTransform: 'uppercase', letterSpacing: '0.08em', flexShrink: 0 }}>ADMIN</span>
                      )}
                    </div>
                    <div style={{ fontSize: '0.62rem', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>
                      {u.scan_count} scans · joined {new Date(u.created_at).toLocaleDateString('en-US', { month: 'short', year: 'numeric' })}
                    </div>
                  </div>
                  {/* Actions */}
                  {u.role !== 'admin' && (
                    <div style={{ display: 'flex', gap: '0.4rem', flexShrink: 0 }}>
                      <button
                        onClick={() => togglePlan(u.uid, u.subscription_tier)}
                        disabled={togglingUid === u.uid}
                        style={{
                          display: 'flex', alignItems: 'center', gap: '0.3rem',
                          padding: '0.35rem 0.625rem', fontSize: '0.58rem',
                          fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.06em',
                          background: u.subscription_tier === 'pro' ? 'rgba(255,215,0,0.08)' : 'rgba(255,255,255,0.04)',
                          color: u.subscription_tier === 'pro' ? '#FFD700' : 'var(--text-dim)',
                          border: `1px solid ${u.subscription_tier === 'pro' ? 'rgba(255,215,0,0.2)' : 'rgba(255,255,255,0.08)'}`,
                          borderRadius: '0.4rem', cursor: 'pointer', opacity: togglingUid === u.uid ? 0.5 : 1,
                        }}
                        title={u.subscription_tier === 'pro' ? 'Downgrade to Free' : 'Upgrade to Pro'}
                      >
                        <Crown size={9} /> {u.subscription_tier === 'pro' ? 'Downgrade' : 'Upgrade'}
                      </button>
                      <button
                        onClick={() => toggleActive(u.uid)}
                        disabled={togglingUid === u.uid}
                        style={{
                          display: 'flex', alignItems: 'center', gap: '0.3rem',
                          padding: '0.35rem 0.625rem', fontSize: '0.58rem',
                          fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.06em',
                          background: u.is_active ? 'rgba(239,68,68,0.07)' : 'rgba(16,185,129,0.07)',
                          color: u.is_active ? '#EF4444' : '#10B981',
                          border: `1px solid ${u.is_active ? 'rgba(239,68,68,0.15)' : 'rgba(16,185,129,0.15)'}`,
                          borderRadius: '0.4rem', cursor: 'pointer', opacity: togglingUid === u.uid ? 0.5 : 1,
                        }}
                        title={u.is_active ? 'Deactivate user' : 'Activate user'}
                      >
                        {u.is_active ? <UserX size={9} /> : <UserCheck size={9} />}
                        {u.is_active ? 'Deactivate' : 'Activate'}
                      </button>
                    </div>
                  )}
                </motion.div>
              ))}
            </div>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
}
