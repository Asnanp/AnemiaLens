/**
 * User dashboard — richer screening intelligence surface for signed-in users.
 */
import type { ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Activity, AlertTriangle, BarChart2, ChevronRight, Clock, Crown,
  Gauge, HeartPulse, History, RefreshCw, Shield, Sparkles, Stethoscope,
  Trash2,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { useHistory } from '../hooks/useHistory';

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
    default: return band.replace(/_/g, ' ');
  }
}

function planLabel(role: string, tier: string): string {
  if (role === 'admin') return 'Admin';
  return tier === 'pro' ? 'Pro' : 'Free';
}

function formatShortDate(date: string): string {
  return new Date(date).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function formatDateTime(date: string): string {
  return new Date(date).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function TrendSparkline({ values, color }: { values: number[]; color: string }) {
  if (values.length === 0) {
    return (
      <div style={{ height: 72, borderRadius: '1rem', border: '1px dashed rgba(255,255,255,0.08)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--text-dim)', fontSize: '0.7rem' }}>
        No trend data yet
      </div>
    );
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const points = values.map((value, index) => {
    const x = values.length === 1 ? 10 : (index / (values.length - 1)) * 100;
    const normalized = max === min ? 0.5 : (value - min) / (max - min);
    const y = 90 - normalized * 70;
    return `${x},${y}`;
  }).join(' ');

  return (
    <svg viewBox="0 0 100 100" preserveAspectRatio="none" style={{ width: '100%', height: 88 }}>
      <defs>
        <linearGradient id="dashboardTrend" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stopColor={`${color}22`} />
          <stop offset="100%" stopColor={`${color}cc`} />
        </linearGradient>
      </defs>
      <polyline
        fill="none"
        stroke="url(#dashboardTrend)"
        strokeWidth="4"
        strokeLinecap="round"
        strokeLinejoin="round"
        points={points}
      />
      {values.map((value, index) => {
        const x = values.length === 1 ? 10 : (index / (values.length - 1)) * 100;
        const normalized = max === min ? 0.5 : (value - min) / (max - min);
        const y = 90 - normalized * 70;
        return (
          <circle key={`${value}-${index}`} cx={x} cy={y} r="3.4" fill={color} style={{ filter: `drop-shadow(0 0 8px ${color})` }} />
        );
      })}
    </svg>
  );
}

function StatCard({
  icon,
  label,
  value,
  tint,
  sub,
}: {
  icon: ReactNode;
  label: string;
  value: string;
  tint: string;
  sub?: string;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, ease: E }}
      style={{
        padding: '1.1rem 1rem',
        borderRadius: '1rem',
        background: 'rgba(255,255,255,0.03)',
        border: '1px solid rgba(255,255,255,0.06)',
        display: 'flex',
        flexDirection: 'column',
        gap: '0.7rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '1rem' }}>
        <span style={{ fontSize: '0.6rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.12em', color: 'var(--text-dim)' }}>{label}</span>
        <div style={{ width: 34, height: 34, borderRadius: '0.85rem', display: 'flex', alignItems: 'center', justifyContent: 'center', background: `${tint}14`, border: `1px solid ${tint}28`, color: tint }}>
          {icon}
        </div>
      </div>
      <div style={{ fontFamily: 'var(--serif)', fontSize: '1.55rem', fontWeight: 700, lineHeight: 1.05 }}>{value}</div>
      {sub && <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', lineHeight: 1.55 }}>{sub}</div>}
    </motion.div>
  );
}

function DistributionBars({ counts, total }: { counts: Record<string, number>; total: number }) {
  const rows = [
    { key: 'low_risk', label: 'Low risk' },
    { key: 'moderate_risk', label: 'Moderate' },
    { key: 'high_concern', label: 'High concern' },
    { key: 'uncertain_retake_needed', label: 'Retake needed' },
  ] as const;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      {rows.map((row) => {
        const count = counts[row.key] ?? 0;
        const pct = total > 0 ? (count / total) * 100 : 0;
        const color = bandColor(row.key);
        return (
          <div key={row.key}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.35rem', fontSize: '0.7rem', color: 'var(--text-muted)' }}>
              <span>{row.label}</span>
              <span style={{ fontFamily: 'var(--mono)', color }}>{count}</span>
            </div>
            <div style={{ height: 8, borderRadius: 999, background: 'rgba(255,255,255,0.05)', overflow: 'hidden' }}>
              <motion.div
                initial={{ width: 0 }}
                animate={{ width: `${pct}%` }}
                transition={{ duration: 0.9, ease: E }}
                style={{ height: '100%', borderRadius: 999, background: `linear-gradient(90deg, ${color}55, ${color})` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function DashboardPage({ onClose }: { onClose: () => void }) {
  const { user, logout } = useAuth();
  const { screenings, total, isLoading, error, refresh, deleteScreening, loadMore } = useHistory();

  if (!user) return null;

  const screeningsWithRisk = screenings.filter((screening) => screening.anemia_risk !== null);
  const screeningsWithConfidence = screenings.filter((screening) => screening.confidence !== null);
  const avgRisk = screeningsWithRisk.length > 0
    ? screeningsWithRisk.reduce((sum, screening) => sum + (screening.anemia_risk ?? 0), 0) / screeningsWithRisk.length
    : 0;
  const avgConfidence = screeningsWithConfidence.length > 0
    ? screeningsWithConfidence.reduce((sum, screening) => sum + (screening.confidence ?? 0), 0) / screeningsWithConfidence.length
    : 0;
  const bandCounts = screenings.reduce<Record<string, number>>((acc, screening) => {
    acc[screening.triage_band] = (acc[screening.triage_band] ?? 0) + 1;
    return acc;
  }, {});
  const flaggedCount = (bandCounts.high_concern ?? 0) + (bandCounts.uncertain_retake_needed ?? 0);
  const latest = screenings[0] ?? null;
  const recentRiskSeries = screeningsWithRisk
    .slice(0, 6)
    .reverse()
    .map((screening) => Math.round((screening.anemia_risk ?? 0) * 100));
  const latestThreeAvg = screeningsWithRisk.slice(0, 3).reduce((sum, screening) => sum + (screening.anemia_risk ?? 0), 0) / Math.max(Math.min(screeningsWithRisk.length, 3), 1);
  const previousThreeAvg = screeningsWithRisk.slice(3, 6).reduce((sum, screening) => sum + (screening.anemia_risk ?? 0), 0) / Math.max(Math.min(Math.max(screeningsWithRisk.length - 3, 0), 3), 1);
  const trendDelta = screeningsWithRisk.length >= 4 ? latestThreeAvg - previousThreeAvg : 0;
  const trendLabel = trendDelta > 0.04 ? 'rising attention' : trendDelta < -0.04 ? 'improving trend' : 'stable pattern';
  const trendColor = trendDelta > 0.04 ? '#EF4444' : trendDelta < -0.04 ? '#10B981' : '#00C2FF';
  const plan = planLabel(user.role, user.subscription_tier);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      transition={{ duration: 0.3 }}
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 10000,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        background: 'rgba(4,4,10,0.92)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
        overflowY: 'auto',
        padding: '4rem 1rem',
      }}
      onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}
    >
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: E }}
        style={{
          width: 'min(1080px, 100%)',
          borderRadius: '1.75rem',
          background: 'rgba(255,255,255,0.03)',
          border: '1px solid rgba(255,255,255,0.07)',
          backdropFilter: 'blur(40px)',
          boxShadow: '0 48px 100px rgba(0,0,0,0.6)',
          overflow: 'hidden',
        }}
      >
        <div style={{
          padding: '2rem 2.5rem',
          borderBottom: '1px solid rgba(255,255,255,0.06)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: '1rem',
          background: 'linear-gradient(135deg, rgba(200,0,30,0.08), rgba(0,194,255,0.04))',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
            <div style={{
              width: 48,
              height: 48,
              borderRadius: '1rem',
              background: 'linear-gradient(135deg, rgba(200,0,30,0.2), rgba(0,194,255,0.12))',
              border: '1px solid rgba(255,255,255,0.09)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '1rem',
              fontWeight: 800,
              fontFamily: 'var(--mono)',
              color: 'var(--text)',
            }}>
              {(user.full_name?.[0] || user.email[0]).toUpperCase()}
            </div>
            <div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem', flexWrap: 'wrap' }}>
                <span style={{ fontFamily: 'var(--serif)', fontSize: '1.25rem', fontWeight: 700 }}>
                  {user.full_name || user.email.split('@')[0]}
                </span>
                <span style={{ padding: '0.22rem 0.55rem', borderRadius: '999px', fontSize: '0.52rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.11em', color: plan === 'Pro' ? '#FFD700' : plan === 'Admin' ? '#EF4444' : 'var(--text-dim)', background: plan === 'Pro' ? 'rgba(255,215,0,0.12)' : plan === 'Admin' ? 'rgba(239,68,68,0.12)' : 'rgba(255,255,255,0.04)', border: plan === 'Pro' ? '1px solid rgba(255,215,0,0.25)' : plan === 'Admin' ? '1px solid rgba(239,68,68,0.25)' : '1px solid rgba(255,255,255,0.08)' }}>
                  {plan}
                </span>
              </div>
              <p style={{ fontSize: '0.72rem', color: 'var(--text-dim)', marginTop: '0.15rem' }}>
                {user.email} · member since {formatShortDate(user.created_at)}
              </p>
            </div>
          </div>
          <div style={{ display: 'flex', gap: '0.65rem', flexWrap: 'wrap' }}>
            <button onClick={refresh} disabled={isLoading} className="btn btn-glass" style={{ padding: '0.5rem 0.95rem', fontSize: '0.62rem', borderRadius: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <RefreshCw size={12} style={{ animation: isLoading ? 'spin 1s linear infinite' : 'none' }} /> Refresh
            </button>
            <button onClick={onClose} className="btn btn-glass" style={{ padding: '0.5rem 0.95rem', fontSize: '0.62rem', borderRadius: '0.75rem' }}>
              Close
            </button>
            <button onClick={() => { logout(); onClose(); }} className="btn btn-glass" style={{ padding: '0.5rem 0.95rem', fontSize: '0.62rem', borderRadius: '0.75rem', color: '#EF4444', borderColor: 'rgba(239,68,68,0.18)' }}>
              Sign Out
            </button>
          </div>
        </div>

        <div style={{ padding: '1.75rem 2.5rem 2.5rem', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.25fr) minmax(0, 0.95fr)', gap: '1rem' }}>
            <motion.div
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, ease: E }}
              style={{
                padding: '1.4rem 1.5rem',
                borderRadius: '1.25rem',
                background: 'linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02))',
                border: '1px solid rgba(255,255,255,0.07)',
                display: 'flex',
                flexDirection: 'column',
                gap: '1rem',
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', alignItems: 'flex-start', flexWrap: 'wrap' }}>
                <div>
                  <div className="section-eyebrow" style={{ marginBottom: '0.55rem' }}>Screening Intelligence</div>
                  <div style={{ fontFamily: 'var(--serif)', fontSize: '1.9rem', fontWeight: 700, lineHeight: 1.08, letterSpacing: '-0.03em', marginBottom: '0.5rem' }}>
                    Your screening history now feels like a living case log.
                  </div>
                  <p style={{ fontSize: '0.82rem', color: 'var(--text-dim)', lineHeight: 1.7, maxWidth: 520 }}>
                    Track the pattern, not just the last result. The dashboard now summarizes risk movement, confidence quality, and the latest follow-up context at a glance.
                  </p>
                </div>
                <div style={{ minWidth: 150, padding: '0.85rem 1rem', borderRadius: '1rem', background: `${trendColor}10`, border: `1px solid ${trendColor}25` }}>
                  <div style={{ fontSize: '0.55rem', fontFamily: 'var(--mono)', color: trendColor, textTransform: 'uppercase', letterSpacing: '0.11em', marginBottom: '0.3rem' }}>
                    Current Pattern
                  </div>
                  <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text)' }}>{trendLabel}</div>
                  <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
                    {screeningsWithRisk.length > 0 ? `${Math.round(avgRisk * 100)}% average risk across saved scans` : 'Run a scan to start tracking'}
                  </div>
                </div>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) 220px', gap: '1rem', alignItems: 'center' }}>
                <div style={{ padding: '0.9rem 1rem', borderRadius: '1rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', marginBottom: '0.55rem' }}>
                    <span style={{ fontSize: '0.58rem', fontFamily: 'var(--mono)', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-dim)' }}>
                      Risk Trajectory
                    </span>
                    <span style={{ fontSize: '0.62rem', fontFamily: 'var(--mono)', color: trendColor }}>
                      last {Math.min(recentRiskSeries.length, 6)} scans
                    </span>
                  </div>
                  <TrendSparkline values={recentRiskSeries} color={trendColor} />
                </div>
                <div style={{ padding: '0.9rem 1rem', borderRadius: '1rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)', display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  <div>
                    <div style={{ fontSize: '0.55rem', fontFamily: 'var(--mono)', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: '0.25rem' }}>
                      Latest saved scan
                    </div>
                    <div style={{ fontSize: '0.92rem', fontWeight: 700, color: latest ? bandColor(latest.triage_band) : 'var(--text)' }}>
                      {latest ? bandLabel(latest.triage_band) : 'No saved scans'}
                    </div>
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', lineHeight: 1.6 }}>
                    {latest
                      ? `${formatDateTime(latest.created_at)}${latest.headline ? ` · ${latest.headline}` : ''}`
                      : 'Once you run a scan, the newest case summary appears here.'}
                  </div>
                </div>
              </div>
            </motion.div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0, 1fr))', gap: '0.85rem' }}>
              <StatCard icon={<Activity size={15} />} label="Total Scans" value={String(total)} tint="#00C2FF" sub="Saved screening records" />
              <StatCard icon={<Gauge size={15} />} label="Avg Confidence" value={`${Math.round(avgConfidence * 100)}%`} tint="#10B981" sub="Mean confidence across stored runs" />
              <StatCard icon={<AlertTriangle size={15} />} label="Flagged Cases" value={String(flaggedCount)} tint="#EF4444" sub="High concern + retake-needed cases" />
              <StatCard icon={plan === 'Pro' ? <Crown size={15} /> : <Shield size={15} />} label="Plan" value={plan} tint={plan === 'Pro' ? '#FFD700' : plan === 'Admin' ? '#EF4444' : '#94A3B8'} sub={plan === 'Pro' ? 'Expanded screening access enabled' : plan === 'Admin' ? 'Administrative control access' : 'Standard screening access'} />
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: '1rem' }}>
            <motion.div
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, ease: E }}
              style={{ padding: '1.25rem 1.35rem', borderRadius: '1.15rem', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
                <BarChart2 size={14} style={{ color: 'rgba(0,194,255,0.8)' }} />
                <span style={{ fontSize: '0.62rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.14em', color: 'rgba(0,194,255,0.8)' }}>
                  Risk Distribution
                </span>
              </div>
              <DistributionBars counts={bandCounts} total={Math.max(total, screenings.length)} />
            </motion.div>

            <motion.div
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, ease: E }}
              style={{ padding: '1.25rem 1.35rem', borderRadius: '1.15rem', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', display: 'flex', flexDirection: 'column', gap: '0.95rem' }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <Sparkles size={14} style={{ color: 'var(--accent-bright)' }} />
                <span style={{ fontSize: '0.62rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.14em', color: 'var(--accent-bright)' }}>
                  Next Best Action
                </span>
              </div>
              <div style={{ padding: '0.95rem 1rem', borderRadius: '0.95rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--text)', marginBottom: '0.35rem' }}>
                  {flaggedCount > 0
                    ? 'Review flagged cases and prioritize clinical follow-up.'
                    : screenings.length > 0
                      ? 'Your recent history looks stable. Focus on repeatable image quality.'
                      : 'Run the first scan to unlock history insights.'}
                </div>
                <div style={{ fontSize: '0.74rem', color: 'var(--text-dim)', lineHeight: 1.65 }}>
                  {flaggedCount > 0
                    ? `${flaggedCount} saved scans currently sit in high-concern or retake-needed bands. Use exported reports or provider sharing for those cases first.`
                    : latest
                      ? `The newest saved scan was ${bandLabel(latest.triage_band).toLowerCase()} on ${formatShortDate(latest.created_at)}. Consistent lighting and framing are still the fastest way to improve confidence.`
                      : 'Once screening data exists, this panel will summarize the most actionable next step automatically.'}
                </div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0, 1fr))', gap: '0.75rem' }}>
                {[
                  { icon: <HeartPulse size={13} />, label: 'Avg risk', value: `${Math.round(avgRisk * 100)}%`, tint: '#F59E0B' },
                  { icon: <Stethoscope size={13} />, label: 'Latest band', value: latest ? bandLabel(latest.triage_band) : '—', tint: latest ? bandColor(latest.triage_band) : '#64748B' },
                  { icon: <Clock size={13} />, label: 'Newest scan', value: latest ? formatShortDate(latest.created_at) : '—', tint: '#00C2FF' },
                ].map((tile) => (
                  <div key={tile.label} style={{ padding: '0.8rem', borderRadius: '0.9rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: tile.tint, marginBottom: '0.45rem' }}>{tile.icon}</div>
                    <div style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: '0.18rem' }}>{tile.label}</div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', lineHeight: 1.45 }}>{tile.value}</div>
                  </div>
                ))}
              </div>
            </motion.div>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap', paddingTop: '0.25rem' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.55rem' }}>
              <History size={15} style={{ color: 'var(--accent-bright)' }} />
              <span style={{ fontFamily: 'var(--mono)', fontSize: '0.66rem', textTransform: 'uppercase', letterSpacing: '0.12em', fontWeight: 600 }}>
                Screening History
              </span>
            </div>
            <span style={{ fontSize: '0.7rem', color: 'var(--text-dim)' }}>
              {screenings.length} loaded of {total} saved scans
            </span>
          </div>

          {error && (
            <div style={{ padding: '0.85rem 1rem', borderRadius: '0.8rem', background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.18)', fontSize: '0.75rem', color: '#FCA5A5' }}>
              {error}
            </div>
          )}

          {screenings.length === 0 && !isLoading && (
            <div style={{ padding: '3rem 1rem', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.82rem', borderRadius: '1.1rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}>
              No screenings yet. Run your first scan to unlock trends, follow-up insights, and history export.
            </div>
          )}

          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.7rem' }}>
            <AnimatePresence>
              {screenings.map((screening, index) => (
                <motion.div
                  key={screening.uid}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 12 }}
                  transition={{ delay: index * 0.025, ease: E }}
                  className="glass glass-hover"
                  style={{
                    padding: '1rem 1.15rem',
                    display: 'grid',
                    gridTemplateColumns: '8px minmax(0, 1fr) auto',
                    gap: '1rem',
                    alignItems: 'stretch',
                  }}
                >
                  <div style={{ borderRadius: '999px', background: bandColor(screening.triage_band), boxShadow: `0 0 12px ${bandColor(screening.triage_band)}55` }} />
                  <div style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: '0.55rem' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                      <span style={{ fontSize: '0.52rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.1em', padding: '0.16rem 0.45rem', borderRadius: '0.35rem', background: `${bandColor(screening.triage_band)}15`, color: bandColor(screening.triage_band), border: `1px solid ${bandColor(screening.triage_band)}30`, fontWeight: 700 }}>
                        {bandLabel(screening.triage_band)}
                      </span>
                      {screening.urgency_label && (
                        <span style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
                          {screening.urgency_label}
                        </span>
                      )}
                      <span style={{ fontSize: '0.68rem', color: 'var(--text-dim)' }}>
                        {formatDateTime(screening.created_at)}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--text)' }}>
                      {screening.headline || screening.triage_label}
                    </div>

                    <div style={{ display: 'flex', gap: '0.55rem', flexWrap: 'wrap' }}>
                      {screening.anemia_risk !== null && (
                        <span style={{ padding: '0.28rem 0.55rem', borderRadius: '999px', fontSize: '0.58rem', fontFamily: 'var(--mono)', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', color: 'var(--text-muted)' }}>
                          Risk {(screening.anemia_risk * 100).toFixed(0)}%
                        </span>
                      )}
                      {screening.predicted_hemoglobin !== null && (
                        <span style={{ padding: '0.28rem 0.55rem', borderRadius: '999px', fontSize: '0.58rem', fontFamily: 'var(--mono)', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', color: 'var(--text-muted)' }}>
                          Hb {screening.predicted_hemoglobin.toFixed(1)} g/dL
                        </span>
                      )}
                      {screening.confidence !== null && (
                        <span style={{ padding: '0.28rem 0.55rem', borderRadius: '999px', fontSize: '0.58rem', fontFamily: 'var(--mono)', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', color: 'var(--text-muted)' }}>
                          Confidence {(screening.confidence * 100).toFixed(0)}%
                        </span>
                      )}
                      <span style={{ padding: '0.28rem 0.55rem', borderRadius: '999px', fontSize: '0.58rem', fontFamily: 'var(--mono)', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', color: 'var(--text-muted)' }}>
                        {screening.processing_time_ms.toFixed(0)}ms
                      </span>
                      <span style={{ padding: '0.28rem 0.55rem', borderRadius: '999px', fontSize: '0.58rem', fontFamily: 'var(--mono)', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', color: 'var(--text-muted)' }}>
                        {screening.guidance_source}
                      </span>
                    </div>
                  </div>

                  <button
                    onClick={(event) => { event.stopPropagation(); deleteScreening(screening.uid); }}
                    style={{
                      alignSelf: 'center',
                      background: 'rgba(239,68,68,0.07)',
                      border: '1px solid rgba(239,68,68,0.12)',
                      borderRadius: '0.55rem',
                      padding: '0.4rem',
                      cursor: 'pointer',
                      color: 'rgba(239,68,68,0.6)',
                      transition: 'all 0.2s',
                    }}
                    title="Delete screening"
                  >
                    <Trash2 size={13} />
                  </button>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>

          {screenings.length < total && (
            <button
              onClick={loadMore}
              disabled={isLoading}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '0.45rem',
                width: '100%',
                padding: '0.85rem',
                fontSize: '0.65rem',
                fontFamily: 'var(--mono)',
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                background: 'rgba(255,255,255,0.03)',
                color: 'var(--text-muted)',
                border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '0.85rem',
                cursor: 'pointer',
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
