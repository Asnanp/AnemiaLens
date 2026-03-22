import type { ReactNode } from 'react';
import { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Activity,
  AlertTriangle,
  BrainCircuit,
  Clock3,
  Crown,
  Gauge,
  RefreshCw,
  ScanEye,
  Search,
  ShieldCheck,
  Sparkles,
  UserCheck,
  UserCog,
  UserX,
  Users,
  Zap,
} from 'lucide-react';

import { toast } from '../components/Toast';
import { useAuth } from '../hooks/useAuth';

const E = [0.22, 1, 0.36, 1] as const;
const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
const monoStyle = {
  fontFamily: 'var(--mono)',
  fontSize: '0.66rem',
  letterSpacing: '0.12em',
  textTransform: 'uppercase',
  color: 'var(--text-dim)',
} as const;
const panelStyle = {
  padding: '1.15rem',
  borderRadius: '1rem',
  background: 'rgba(255,255,255,0.03)',
  border: '1px solid rgba(255,255,255,0.08)',
} as const;

function endpoint(path: string): string {
  return API_BASE ? `${API_BASE}${path}` : path;
}

type Tab = 'overview' | 'users';
type PlanFilter = 'all' | 'pro' | 'free';
type StatusFilter = 'all' | 'active' | 'inactive';

interface AdminTrendPoint {
  date: string;
  label: string;
  scans: number;
  blocked: number;
}

interface AdminRecentScreening {
  uid: string;
  triage_band: string;
  triage_label: string;
  screening_label: string | null;
  confidence: number | null;
  predicted_hemoglobin: number | null;
  processing_time_ms: number;
  guidance_source: string;
  processing_path: string;
  headline: string | null;
  blocked: boolean;
  created_at: string;
}

interface AdminStats {
  total_users: number;
  active_users: number;
  total_scans: number;
  scans_by_band: Record<string, number>;
  avg_processing_time_ms: number;
  blocked_scans: number;
  blocked_rate: number;
  pro_users: number;
  free_users: number;
  pro_adoption_rate: number;
  avg_confidence: number;
  avg_risk: number;
  recent_scans_24h: number;
  scans_last_7_days: AdminTrendPoint[];
  processing_paths: Record<string, number>;
  guidance_sources: Record<string, number>;
  recent_screenings: AdminRecentScreening[];
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

function pct(value: number): string {
  return `${Math.round(value * 100)}%`;
}

function ms(value: number): string {
  return `${Math.round(value)}ms`;
}

function labelise(value?: string | null): string {
  return (value ?? 'unknown').replace(/_/g, ' ');
}

function age(value: string): string {
  const minutes = Math.max(1, Math.round((Date.now() - new Date(value).getTime()) / 60000));
  if (minutes < 60) return `${minutes}m ago`;
  if (minutes < 1440) return `${Math.round(minutes / 60)}h ago`;
  return `${Math.round(minutes / 1440)}d ago`;
}

function initials(user: AdminUser): string {
  const fullName = user.full_name?.trim();
  if (fullName) return fullName.split(/\s+/).slice(0, 2).map(part => part[0]?.toUpperCase() ?? '').join('');
  return user.email.slice(0, 2).toUpperCase();
}

function health(stats: AdminStats | null) {
  if (!stats) return { label: 'Loading', color: '#94A3B8', detail: 'Collecting operator telemetry.' };
  if (stats.blocked_rate > 0.25 || stats.avg_processing_time_ms > 3200) {
    return { label: 'Attention', color: '#F97316', detail: 'Latency or blocked captures need intervention.' };
  }
  if (stats.blocked_rate > 0.15 || stats.avg_processing_time_ms > 2200) {
    return { label: 'Stable', color: '#FBBF24', detail: 'Pipeline is healthy with clear tuning headroom.' };
  }
  return { label: 'Strong', color: '#22C55E', detail: 'Latency and quality gate rate are inside target.' };
}

function bandTone(band: string): string {
  if (band.includes('high')) return '#F97316';
  if (band.includes('moderate')) return '#FBBF24';
  return '#34D399';
}

function StatCard({ icon, label, value, detail, accent }: { icon: ReactNode; label: string; value: string; detail: string; accent: string }) {
  return (
    <div style={panelStyle}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', marginBottom: '0.85rem' }}>
        <span style={{ width: 38, height: 38, borderRadius: '0.8rem', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: `${accent}16`, border: `1px solid ${accent}32`, color: accent }}>{icon}</span>
        <span style={monoStyle}>{label}</span>
      </div>
      <div style={{ fontFamily: 'var(--serif)', fontSize: '1.95rem', lineHeight: 1, marginBottom: '0.4rem' }}>{value}</div>
      <div style={{ color: 'var(--text-dim)', fontSize: '0.78rem', lineHeight: 1.6 }}>{detail}</div>
    </div>
  );
}

function DistributionRow({ label, value, total, accent }: { label: string; value: number; total: number; accent: string }) {
  const width = total > 0 ? Math.max(8, (value / total) * 100) : 0;
  return (
    <div style={{ display: 'grid', gap: '0.45rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', fontSize: '0.8rem' }}>
        <span>{label}</span>
        <span style={{ color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>{value}{total > 0 ? ` / ${pct(value / total)}` : ''}</span>
      </div>
      <div style={{ height: 8, borderRadius: 999, background: 'rgba(255,255,255,0.06)', overflow: 'hidden' }}>
        <div style={{ height: '100%', width: `${width}%`, borderRadius: 999, background: accent, boxShadow: `0 0 22px ${accent}44` }} />
      </div>
    </div>
  );
}

export default function AdminDashboardPage({ onClose }: { onClose: () => void }) {
  const { user, getAccessToken } = useAuth();
  const [tab, setTab] = useState<Tab>('overview');
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [totalUsers, setTotalUsers] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [togglingUid, setTogglingUid] = useState<string | null>(null);
  const [search, setSearch] = useState('');
  const [planFilter, setPlanFilter] = useState<PlanFilter>('all');
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all');

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
    const nextTier = current === 'pro' ? 'free' : 'pro';
    setTogglingUid(uid);
    try {
      const res = await fetch(endpoint(`/api/admin/users/${uid}/plan`), {
        method: 'PATCH',
        headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
        body: JSON.stringify({ subscription_tier: nextTier }),
      });
      if (!res.ok) throw new Error('Failed to update plan');
      setUsers(prev => prev.map(item => item.uid === uid ? { ...item, subscription_tier: nextTier } : item));
      toast.success(`User plan updated to ${nextTier}`);
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
      const res = await fetch(endpoint(`/api/admin/users/${uid}/active`), { method: 'PATCH', headers: { Authorization: `Bearer ${token}` } });
      if (!res.ok) throw new Error('Failed to toggle user status');
      const data = await res.json();
      setUsers(prev => prev.map(item => item.uid === uid ? { ...item, is_active: data.is_active } : item));
      toast.success(`User ${data.is_active ? 'activated' : 'deactivated'}`);
    } catch {
      toast.error('Failed to toggle user status');
    } finally {
      setTogglingUid(null);
    }
  };

  if (!user || user.role !== 'admin') return null;

  const pulse = health(stats);
  const maxTrend = Math.max(...(stats?.scans_last_7_days.map(point => point.scans) ?? [1]), 1);
  const filteredUsers = users.filter(item => {
    const matchesSearch = !search || [item.email, item.full_name ?? '', item.role].some(value => value.toLowerCase().includes(search.toLowerCase()));
    const matchesPlan = planFilter === 'all' || item.subscription_tier === planFilter;
    const matchesStatus = statusFilter === 'all' || (statusFilter === 'active' && item.is_active) || (statusFilter === 'inactive' && !item.is_active);
    return matchesSearch && matchesPlan && matchesStatus;
  });

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} transition={{ duration: 0.3 }} style={{ position: 'fixed', inset: 0, zIndex: 10000, background: 'rgba(4,4,10,0.92)', backdropFilter: 'blur(24px)', WebkitBackdropFilter: 'blur(24px)', overflowY: 'auto', padding: '3rem 1rem' }} onClick={event => { if (event.target === event.currentTarget) onClose(); }}>
      <motion.div initial={{ opacity: 0, y: 28 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5, ease: E }} style={{ width: 'min(1160px, 100%)', margin: '0 auto', borderRadius: '1.6rem', overflow: 'hidden', background: 'linear-gradient(180deg, rgba(8,15,26,0.98), rgba(10,10,18,0.98))', border: '1px solid rgba(255,255,255,0.08)', boxShadow: '0 40px 120px rgba(0,0,0,0.55)' }}>
        <div style={{ padding: '2rem', borderBottom: '1px solid rgba(255,255,255,0.08)', background: 'radial-gradient(circle at top left, rgba(34,211,238,0.16), transparent 35%), radial-gradient(circle at top right, rgba(244,63,94,0.14), transparent 28%)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1.2rem', flexWrap: 'wrap' }}>
            <div style={{ maxWidth: 720 }}>
              <div style={{ ...monoStyle, display: 'inline-flex', alignItems: 'center', gap: '0.45rem', padding: '0.35rem 0.7rem', borderRadius: 999, background: 'rgba(255,255,255,0.06)', border: '1px solid rgba(255,255,255,0.08)', marginBottom: '1rem' }}><ShieldCheck size={12} color={pulse.color} />Operator Command Center</div>
              <h2 style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(2rem,4vw,3.2rem)', lineHeight: 0.97, letterSpacing: '-0.04em', marginBottom: '0.9rem' }}>Run the product like a real clinical screening platform.</h2>
              <p style={{ color: 'var(--text-dim)', lineHeight: 1.7, fontSize: '0.9rem', maxWidth: 620 }}>See throughput, blocked captures, inference path mix, guidance delivery, and user operations in one surface.</p>
            </div>
            <div style={{ display: 'grid', gap: '0.9rem', minWidth: 280 }}>
              <div style={{ ...panelStyle, display: 'grid', gap: '0.45rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'center' }}>
                  <span style={monoStyle}>System Pulse</span>
                  <span style={{ ...monoStyle, padding: '0.22rem 0.55rem', borderRadius: 999, background: `${pulse.color}18`, border: `1px solid ${pulse.color}35`, color: pulse.color }}>{pulse.label}</span>
                </div>
                <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>{pulse.detail}</div>
                {stats && <div style={{ display: 'flex', gap: '0.6rem', flexWrap: 'wrap' }}>
                  <span className="stat-chip" style={{ background: 'rgba(255,255,255,0.04)' }}><Users size={12} /> {stats.active_users}/{stats.total_users} active</span>
                  <span className="stat-chip" style={{ background: 'rgba(255,255,255,0.04)' }}><Sparkles size={12} /> {pct(stats.pro_adoption_rate)} pro</span>
                  <span className="stat-chip" style={{ background: 'rgba(255,255,255,0.04)' }}><Clock3 size={12} /> {ms(stats.avg_processing_time_ms)}</span>
                </div>}
              </div>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '0.75rem', flexWrap: 'wrap' }}>
                <button onClick={() => { void (tab === 'overview' ? fetchStats() : fetchUsers()); }} disabled={isLoading} className="btn btn-glass" style={{ padding: '0.6rem 1rem', fontSize: '0.68rem', borderRadius: '0.75rem', gap: '0.45rem' }}><RefreshCw size={13} style={{ animation: isLoading ? 'spin 1s linear infinite' : 'none' }} />Refresh</button>
                <button onClick={onClose} className="btn btn-glass" style={{ padding: '0.6rem 1rem', fontSize: '0.68rem', borderRadius: '0.75rem' }}>Close</button>
              </div>
            </div>
          </div>
        </div>

        <div style={{ padding: '0 2rem 2rem' }}>
          <div style={{ display: 'flex', gap: '0.45rem', paddingTop: '1.15rem', marginBottom: '1.35rem', borderBottom: '1px solid rgba(255,255,255,0.08)' }}>
            {([{ id: 'overview', label: 'Overview' }, { id: 'users', label: `Users (${totalUsers || 0})` }] as const).map(item => (
              <button key={item.id} onClick={() => setTab(item.id)} style={{ ...monoStyle, padding: '0.72rem 1rem', borderRadius: '0.8rem 0.8rem 0 0', border: '1px solid rgba(255,255,255,0.08)', borderBottom: 'none', background: tab === item.id ? 'rgba(34,211,238,0.12)' : 'transparent', color: tab === item.id ? '#67E8F9' : 'var(--text-dim)', cursor: 'pointer' }}>{item.label}</button>
            ))}
          </div>

          {error && <div style={{ marginBottom: '1rem', padding: '0.9rem 1rem', borderRadius: '0.9rem', background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.22)', color: '#FCA5A5', fontSize: '0.8rem' }}>{error}</div>}

          {tab === 'overview' && stats && (
            <div style={{ display: 'grid', gap: '1rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(210px, 1fr))', gap: '0.9rem' }}>
                <StatCard icon={<ScanEye size={16} />} label="Total Scans" value={String(stats.total_scans)} detail={`${stats.recent_scans_24h} scans in the last 24 hours`} accent="#22D3EE" />
                <StatCard icon={<AlertTriangle size={16} />} label="Blocked Rate" value={pct(stats.blocked_rate)} detail={`${stats.blocked_scans} captures blocked by quality`} accent="#F97316" />
                <StatCard icon={<Gauge size={16} />} label="Confidence" value={pct(stats.avg_confidence)} detail={`${pct(stats.avg_risk)} average risk signal`} accent="#38BDF8" />
                <StatCard icon={<Zap size={16} />} label="Latency" value={ms(stats.avg_processing_time_ms)} detail={`${pct(stats.pro_adoption_rate)} paid adoption`} accent="#F43F5E" />
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0,1.15fr) minmax(0,0.85fr)', gap: '0.9rem' }}>
                <div style={{ ...panelStyle, display: 'grid', gap: '0.9rem' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
                    <div><div style={monoStyle}>Seven-Day Throughput</div><div style={{ fontSize: '1rem', fontWeight: 600, marginTop: '0.35rem' }}>Capture volume and blocked-case pressure</div></div>
                    <span className="stat-chip" style={{ background: 'rgba(255,255,255,0.04)' }}><Activity size={12} /> {stats.recent_scans_24h} in 24h</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, minmax(0, 1fr))', gap: '0.65rem', alignItems: 'end', minHeight: 210 }}>
                    {stats.scans_last_7_days.map(point => {
                      const totalHeight = Math.max(24, (point.scans / maxTrend) * 150);
                      const blockedHeight = point.scans > 0 ? Math.max(4, (point.blocked / point.scans) * totalHeight) : 0;
                      return <div key={point.date} style={{ display: 'grid', gap: '0.5rem', justifyItems: 'center' }}>
                        <div style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', color: 'var(--text-dim)' }}>{point.scans}</div>
                        <div style={{ width: '100%', maxWidth: 42, height: 160, borderRadius: 999, background: 'rgba(255,255,255,0.05)', display: 'flex', alignItems: 'flex-end', padding: 4 }}>
                          <div style={{ width: '100%', height: totalHeight, borderRadius: 999, background: 'linear-gradient(180deg, rgba(34,211,238,0.95), rgba(8,145,178,0.55))', position: 'relative', overflow: 'hidden' }}>
                            {blockedHeight > 0 && <div style={{ position: 'absolute', left: 0, right: 0, bottom: 0, height: blockedHeight, background: 'linear-gradient(180deg, rgba(249,115,22,0.95), rgba(249,115,22,0.45))' }} />}
                          </div>
                        </div>
                        <div style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', color: 'var(--text-dim)' }}>{point.label}</div>
                      </div>;
                    })}
                  </div>
                </div>

                <div style={{ ...panelStyle, display: 'grid', gap: '0.9rem' }}>
                  <div><div style={monoStyle}>Risk Mix</div><div style={{ fontSize: '1rem', fontWeight: 600, marginTop: '0.35rem' }}>Triage distribution across the whole platform</div></div>
                  {Object.entries(stats.scans_by_band).sort((a, b) => b[1] - a[1]).map(([band, count]) => <DistributionRow key={band} label={labelise(band)} value={count} total={stats.total_scans} accent={bandTone(band)} />)}
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '0.9rem' }}>
                <div style={{ ...panelStyle, display: 'grid', gap: '0.9rem' }}>
                  <div><div style={monoStyle}>Inference Paths</div><div style={{ fontSize: '1rem', fontWeight: 600, marginTop: '0.35rem' }}>How work is routing through the pipeline</div></div>
                  {Object.entries(stats.processing_paths).sort((a, b) => b[1] - a[1]).map(([path, count]) => <DistributionRow key={path} label={labelise(path)} value={count} total={stats.total_scans} accent="#38BDF8" />)}
                </div>
                <div style={{ ...panelStyle, display: 'grid', gap: '0.9rem' }}>
                  <div><div style={monoStyle}>Guidance Mix</div><div style={{ fontSize: '1rem', fontWeight: 600, marginTop: '0.35rem' }}>Which advisory engine is reaching users</div></div>
                  {Object.entries(stats.guidance_sources).sort((a, b) => b[1] - a[1]).map(([source, count]) => <DistributionRow key={source} label={labelise(source)} value={count} total={stats.total_scans} accent="#22C55E" />)}
                </div>
                <div style={{ ...panelStyle, display: 'grid', gap: '0.8rem' }}>
                  <div><div style={monoStyle}>Operator Snapshot</div><div style={{ fontSize: '1rem', fontWeight: 600, marginTop: '0.35rem' }}>Quick reads for the team</div></div>
                  {[
                    { icon: <Users size={14} />, label: 'Active users', value: `${stats.active_users}/${stats.total_users}`, accent: '#22C55E' },
                    { icon: <BrainCircuit size={14} />, label: 'Average confidence', value: pct(stats.avg_confidence), accent: '#38BDF8' },
                    { icon: <Crown size={14} />, label: 'Pro seats', value: String(stats.pro_users), accent: '#FBBF24' },
                  ].map(item => <div key={item.label} style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'center', padding: '0.85rem 0.9rem', borderRadius: '0.85rem', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '0.7rem', fontSize: '0.8rem' }}><span style={{ width: 32, height: 32, borderRadius: '0.75rem', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', background: `${item.accent}16`, border: `1px solid ${item.accent}30`, color: item.accent }}>{item.icon}</span>{item.label}</span>
                    <span style={{ fontFamily: 'var(--serif)', fontSize: '1.2rem' }}>{item.value}</span>
                  </div>)}
                </div>
              </div>

              <div style={{ ...panelStyle, display: 'grid', gap: '0.9rem' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', flexWrap: 'wrap' }}>
                  <div><div style={monoStyle}>Recent Cases</div><div style={{ fontSize: '1rem', fontWeight: 600, marginTop: '0.35rem' }}>Latest scans flowing through the live product</div></div>
                  <span className="stat-chip" style={{ background: 'rgba(255,255,255,0.04)' }}><Sparkles size={12} /> Live feed</span>
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '0.8rem' }}>
                  {stats.recent_screenings.map(caseItem => {
                    const tone = bandTone(caseItem.triage_band);
                    return <div key={caseItem.uid} style={{ padding: '1rem', borderRadius: '0.95rem', background: `${tone}12`, border: `1px solid ${tone}30`, display: 'grid', gap: '0.7rem' }}>
                      <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem' }}>
                        <div><div style={{ ...monoStyle, color: tone }}>{labelise(caseItem.triage_band)}</div><div style={{ fontSize: '0.94rem', fontWeight: 600, marginTop: '0.35rem', lineHeight: 1.4 }}>{caseItem.headline || caseItem.triage_label}</div></div>
                        <span style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', color: 'var(--text-dim)' }}>{age(caseItem.created_at)}</span>
                      </div>
                      <div style={{ display: 'flex', gap: '0.45rem', flexWrap: 'wrap' }}>
                        <span className="stat-chip" style={{ background: 'rgba(255,255,255,0.04)' }}><Gauge size={12} /> {caseItem.confidence != null ? pct(caseItem.confidence) : 'n/a'}</span>
                        <span className="stat-chip" style={{ background: 'rgba(255,255,255,0.04)' }}><Clock3 size={12} /> {ms(caseItem.processing_time_ms)}</span>
                        <span className="stat-chip" style={{ background: 'rgba(255,255,255,0.04)' }}><BrainCircuit size={12} /> {labelise(caseItem.guidance_source)}</span>
                      </div>
                      <div style={{ color: 'var(--text-dim)', fontSize: '0.76rem', lineHeight: 1.7 }}>
                        <div>Path: {labelise(caseItem.processing_path)}</div>
                        <div>Hb: {caseItem.predicted_hemoglobin != null ? caseItem.predicted_hemoglobin.toFixed(1) : 'n/a'} g/dL</div>
                        <div>Status: {caseItem.blocked ? 'Blocked by quality gate' : caseItem.screening_label || 'Completed'}</div>
                      </div>
                    </div>;
                  })}
                </div>
              </div>
            </div>
          )}

          {tab === 'users' && (
            <div style={{ display: 'grid', gap: '1rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(220px,1.4fr) repeat(2, minmax(150px,0.7fr)) auto', gap: '0.75rem' }}>
                <label style={{ ...panelStyle, display: 'flex', alignItems: 'center', gap: '0.7rem' }}>
                  <Search size={14} color="#67E8F9" />
                  <input value={search} onChange={event => setSearch(event.target.value)} placeholder="Search by name, email, or role" style={{ width: '100%', background: 'transparent', border: 'none', outline: 'none', color: 'var(--text)', fontSize: '0.82rem' }} />
                </label>
                <select value={planFilter} onChange={event => setPlanFilter(event.target.value as PlanFilter)} style={{ ...panelStyle, color: 'var(--text)', fontSize: '0.8rem' }}>
                  <option value="all">All plans</option>
                  <option value="pro">Pro only</option>
                  <option value="free">Free only</option>
                </select>
                <select value={statusFilter} onChange={event => setStatusFilter(event.target.value as StatusFilter)} style={{ ...panelStyle, color: 'var(--text)', fontSize: '0.8rem' }}>
                  <option value="all">All statuses</option>
                  <option value="active">Active</option>
                  <option value="inactive">Inactive</option>
                </select>
                <div style={{ ...panelStyle, display: 'flex', alignItems: 'center', justifyContent: 'center', ...monoStyle }}>{filteredUsers.length} visible</div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))', gap: '0.8rem' }}>
                <StatCard icon={<UserCog size={16} />} label="Operators" value={String(users.filter(item => item.role === 'admin').length)} detail="Admin accounts with elevated controls" accent="#F43F5E" />
                <StatCard icon={<UserCheck size={16} />} label="Active Accounts" value={String(users.filter(item => item.is_active).length)} detail="Accounts currently able to use the platform" accent="#22C55E" />
                <StatCard icon={<Crown size={16} />} label="Pro Accounts" value={String(users.filter(item => item.subscription_tier === 'pro').length)} detail="Accounts converted to the paid tier" accent="#FBBF24" />
              </div>

              <div style={{ display: 'grid', gap: '0.8rem' }}>
                {filteredUsers.map(item => <div key={item.uid} style={{ ...panelStyle, display: 'grid', gridTemplateColumns: 'auto 1fr auto', gap: '1rem', alignItems: 'center', opacity: item.is_active ? 1 : 0.62 }}>
                  <div style={{ width: 48, height: 48, borderRadius: '1rem', display: 'flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--mono)', fontSize: '0.82rem', background: item.subscription_tier === 'pro' ? 'linear-gradient(135deg, rgba(251,191,36,0.22), rgba(249,115,22,0.1))' : 'rgba(255,255,255,0.06)', border: `1px solid ${item.subscription_tier === 'pro' ? 'rgba(251,191,36,0.28)' : 'rgba(255,255,255,0.08)'}`, color: item.subscription_tier === 'pro' ? '#FBBF24' : 'var(--text-muted)' }}>{initials(item)}</div>
                  <div style={{ minWidth: 0, display: 'grid', gap: '0.45rem' }}>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.45rem', alignItems: 'center' }}>
                      <span style={{ fontSize: '0.92rem', fontWeight: 600 }}>{item.full_name || item.email}</span>
                      {item.full_name && <span style={{ color: 'var(--text-dim)', fontSize: '0.76rem' }}>{item.email}</span>}
                      {item.subscription_tier === 'pro' && <span className="stat-chip" style={{ background: 'rgba(251,191,36,0.12)', color: '#FBBF24' }}><Crown size={12} /> Pro</span>}
                      {item.role === 'admin' && <span className="stat-chip" style={{ background: 'rgba(244,63,94,0.12)', color: '#FB7185' }}><ShieldCheck size={12} /> Admin</span>}
                      {!item.is_active && <span className="stat-chip" style={{ background: 'rgba(248,113,113,0.12)', color: '#FCA5A5' }}><AlertTriangle size={12} /> Inactive</span>}
                    </div>
                    <div style={{ display: 'flex', gap: '0.8rem', flexWrap: 'wrap', color: 'var(--text-dim)', fontSize: '0.76rem' }}>
                      <span>{item.scan_count} scans</span>
                      <span>Joined {new Date(item.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}</span>
                      <span>Role: {labelise(item.role)}</span>
                    </div>
                  </div>
                  {item.role !== 'admin' && <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                    <button onClick={() => togglePlan(item.uid, item.subscription_tier)} disabled={togglingUid === item.uid} className="btn btn-glass" style={{ padding: '0.5rem 0.85rem', fontSize: '0.62rem', borderRadius: '0.75rem', gap: '0.35rem', color: item.subscription_tier === 'pro' ? '#FBBF24' : '#67E8F9', opacity: togglingUid === item.uid ? 0.5 : 1 }}><Crown size={11} />{item.subscription_tier === 'pro' ? 'Set Free' : 'Set Pro'}</button>
                    <button onClick={() => toggleActive(item.uid)} disabled={togglingUid === item.uid} className="btn btn-glass" style={{ padding: '0.5rem 0.85rem', fontSize: '0.62rem', borderRadius: '0.75rem', gap: '0.35rem', color: item.is_active ? '#FCA5A5' : '#86EFAC', opacity: togglingUid === item.uid ? 0.5 : 1 }}>{item.is_active ? <UserX size={11} /> : <UserCheck size={11} />}{item.is_active ? 'Deactivate' : 'Activate'}</button>
                  </div>}
                </div>)}
                {!isLoading && filteredUsers.length === 0 && <div style={{ ...panelStyle, padding: '2rem', textAlign: 'center', color: 'var(--text-dim)' }}>No users matched the current filters.</div>}
              </div>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
