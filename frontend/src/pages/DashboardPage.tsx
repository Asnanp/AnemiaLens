/**
 * User dashboard — richer screening intelligence surface for signed-in users.
 */
import type { ReactNode } from 'react';
import { useEffect, useRef, useState, useCallback } from 'react';
import { motion, AnimatePresence, useInView } from 'framer-motion';
import { MagneticButton } from '../components/MagneticButton';
import {
  Activity, AlertTriangle, BarChart2, CheckCircle2, ChevronRight, Clock,
  Gauge, HeartPulse, History, Lightbulb, RefreshCw, ShieldCheck, Sparkles,
  Stethoscope, Trash2, TrendingDown, TrendingUp, UserCircle2,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { useHistory } from '../hooks/useHistory';
import { useStats } from '../hooks/useStats';

const E = [0.22, 1, 0.36, 1] as const;

import { AnimatedLineChart } from '../components/dashboard/AnimatedLineChart';
import { StatCard } from '../components/dashboard/StatCard';
import { DistributionDonut, DistributionBars, bandColor } from '../components/dashboard/DistributionCharts';
import { HealthInsightsCard, type Insight } from '../components/dashboard/HealthInsightsCard';

const RISK_IMAGES: Record<string, string> = {
  low_risk: '/demo-cases/low-risk-demo.jpg',
  moderate_risk: '/demo-cases/moderate-risk-demo.jpg',
  high_concern: '/demo-cases/high-concern-demo.jpg',
  uncertain_retake_needed: '/demo-cases/low-risk-demo.jpg',
};

function bandLabel(band?: string | null): string {
  switch (band) {
    case 'low_risk': return 'Low Risk';
    case 'moderate_risk': return 'Moderate';
    case 'high_concern': return 'High Concern';
    case 'uncertain_retake_needed': return 'Retake Needed';
    default: return (band ?? 'unknown').replace(/_/g, ' ');
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

function formatMaybeDateTime(date: string | null | undefined): string {
  if (!date) return 'Not recorded yet';
  return formatDateTime(date);
}

/* ------------------------------------------------------------------ */
/*  Skeleton                                                           */
/* ------------------------------------------------------------------ */

function SkeletonPulse({ style }: { style?: React.CSSProperties }) {
  return (
    <motion.div
      animate={{ opacity: [0.4, 0.7, 0.4] }}
      transition={{ duration: 1.6, repeat: Infinity, ease: 'easeInOut' }}
      style={{
        borderRadius: '0.75rem',
        background: 'rgba(255,255,255,0.06)',
        ...style,
      }}
    />
  );
}

function StatCardSkeleton() {
  return (
    <div style={{ padding: '1.1rem 1rem', borderRadius: '1rem', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', display: 'flex', flexDirection: 'column', gap: '0.7rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between' }}>
        <SkeletonPulse style={{ width: 60, height: 10 }} />
        <SkeletonPulse style={{ width: 34, height: 34, borderRadius: '0.85rem' }} />
      </div>
      <SkeletonPulse style={{ width: 50, height: 28 }} />
      <SkeletonPulse style={{ width: '80%', height: 10 }} />
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Health Insights Builder                                            */
/* ------------------------------------------------------------------ */

function buildInsights(
  screenings: Array<{ triage_band?: string | null; anemia_risk: number | null; confidence: number | null; created_at: string }>,
  bandCounts: Record<string, number>,
  totalScans: number,
  avgRisk: number,
  trendDelta: number,
  trendLabel: string,
): Insight[] {
  const insights: Insight[] = [];

  // Trend insight
  if (screenings.length >= 3) {
    insights.push({
      icon: trendDelta > 0.04 ? <TrendingUp size={15} /> : trendDelta < -0.04 ? <TrendingDown size={15} /> : <Activity size={15} />,
      tint: trendDelta > 0.04 ? '#EF4444' : trendDelta < -0.04 ? '#10B981' : '#00C2FF',
      title: trendDelta > 0.04 ? 'Risk is trending upward' : trendDelta < -0.04 ? 'Risk is improving' : 'Risk pattern is stable',
      body: `Your average risk over recent scans is ${Math.round(avgRisk * 100)}%. The pattern shows ${trendLabel.toLowerCase()} across your last ${screenings.length} screenings.`,
      action: trendDelta > 0.04 ? 'Consider scheduling a clinical follow-up.' : trendDelta < -0.04 ? 'Keep maintaining consistent screening habits.' : 'Continue regular monitoring cadence.',
    });
  }

  // High concern
  if ((bandCounts.high_concern ?? 0) > 0) {
    insights.push({
      icon: <AlertTriangle size={15} />,
      tint: '#EF4444',
      title: `${bandCounts.high_concern} high-concern scan${bandCounts.high_concern > 1 ? 's' : ''} detected`,
      body: 'One or more screenings flagged elevated risk. These cases benefit most from professional review and consistent re-screening.',
      action: 'Export your history report and share with a healthcare provider.',
    });
  }

  // Retake needed
  if ((bandCounts.uncertain_retake_needed ?? 0) > 0) {
    insights.push({
      icon: <Sparkles size={15} />,
      tint: '#8B5CF6',
      title: 'Image quality could be improved',
      body: `${bandCounts.uncertain_retake_needed} scan${bandCounts.uncertain_retake_needed > 1 ? 's were' : ' was'} marked as uncertain. Better lighting and framing can raise confidence scores significantly.`,
      action: 'Review the image-quality guide before your next scan.',
    });
  }

  // Confidence
  const screeningsWithConfidence = screenings.filter((s) => s.confidence !== null);
  if (screeningsWithConfidence.length > 0) {
    const avgConf = screeningsWithConfidence.reduce((s, sc) => s + (sc.confidence ?? 0), 0) / screeningsWithConfidence.length;
    if (avgConf < 0.6) {
      insights.push({
        icon: <Gauge size={15} />,
        tint: '#F59E0B',
        title: 'Average confidence is low',
        body: `Your mean confidence across ${screeningsWithConfidence.length} scans is ${Math.round(avgConf * 100)}%. Consistent lighting, focus, and framing will help improve result reliability.`,
        action: 'Aim for stable, well-lit conditions for your next screening.',
      });
    }
  }

  // Milestone
  if (totalScans >= 5 && totalScans < 7) {
    insights.push({
      icon: <HeartPulse size={15} />,
      tint: '#10B981',
      title: 'You are building a meaningful history',
      body: `${totalScans} screenings recorded — enough data is accumulating to spot real trends. Keep screening regularly for the best insights.`,
    });
  } else if (totalScans >= 10) {
    insights.push({
      icon: <ShieldCheck size={15} />,
      tint: '#10B981',
      title: 'Strong screening history established',
      body: `With ${totalScans} screenings, your data provides a reliable baseline for tracking changes over time.`,
    });
  }

  // First scan encouragement
  if (totalScans === 0) {
    insights.push({
      icon: <Lightbulb size={15} />,
      tint: '#FFD700',
      title: 'Ready for your first screening',
      body: 'Run your initial scan to start building a personal health history. The first result becomes your baseline.',
      action: 'Navigate to the Screening page to begin.',
    });
  }

  return insights;
}

/* ------------------------------------------------------------------ */
/*  Dashboard Page                                                     */
/* ------------------------------------------------------------------ */

export default function DashboardPage({ onClose }: { onClose: () => void }) {
  const { user, logout } = useAuth();
  const { screenings, total, isLoading, error, refresh, deleteScreening, loadMore } = useHistory();
  const { stats, isLoading: statsLoading, refresh: refreshStats } = useStats();

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
  const totalScans = stats?.total_scans ?? total;
  const scansThisMonth = stats?.scans_this_month ?? 0;
  const dashboardAvgRisk = stats?.avg_risk ?? avgRisk;
  const lastScanAt = stats?.last_scan_at ?? latest?.created_at ?? null;
  const accountTrustStatus = isLoading || statsLoading
    ? 'Syncing account'
    : totalScans > 0
      ? 'History secured'
      : 'Ready for first save';

  const insights = buildInsights(screenings, bandCounts, totalScans, avgRisk, trendDelta, trendLabel);

  const handleRefresh = useCallback(() => {
    refresh();
    refreshStats();
  }, [refresh, refreshStats]);

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
        className="dashboard-shell"
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
        {/* Header */}
        <div className="dashboard-header" style={{
          padding: 'clamp(1.25rem, 3vw, 2rem) clamp(1rem, 3vw, 2.5rem)',
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
                {user.email} | member since {formatShortDate(user.created_at)}
              </p>
            </div>
          </div>
          <div className="dashboard-header-actions" style={{ display: 'flex', gap: '0.65rem', flexWrap: 'wrap' }}>
            <MagneticButton onClick={handleRefresh} disabled={isLoading || statsLoading} className="btn btn-glass" style={{ padding: '0.5rem 0.95rem', fontSize: '0.62rem', borderRadius: '0.75rem', display: 'flex', alignItems: 'center', gap: '0.4rem' }}>
              <RefreshCw size={12} style={{ animation: isLoading || statsLoading ? 'spin 1s linear infinite' : 'none' }} /> Refresh
            </MagneticButton>
            <MagneticButton onClick={onClose} className="btn btn-glass" style={{ padding: '0.5rem 0.95rem', fontSize: '0.62rem', borderRadius: '0.75rem' }}>
              Close
            </MagneticButton>
            <MagneticButton onClick={() => { logout(); onClose(); }} className="btn btn-glass" style={{ padding: '0.5rem 0.95rem', fontSize: '0.62rem', borderRadius: '0.75rem', color: '#EF4444', borderColor: 'rgba(239,68,68,0.18)' }}>
              Sign Out
            </MagneticButton>
          </div>
        </div>

        <div style={{ padding: 'clamp(1.25rem, 3vw, 1.75rem) clamp(1rem, 3vw, 2.5rem) clamp(1.5rem, 4vw, 2.5rem)', display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>

          {/* Loading skeletons */}
          {(isLoading || statsLoading) && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.85rem' }}>
              {[0, 1, 2, 3].map((i) => <StatCardSkeleton key={i} />)}
            </div>
          )}

          {/* Screening Intelligence */}
          {!isLoading && !statsLoading && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '1rem' }}>
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
                      Your care log, not just a pile of saved scans.
                    </div>
                    <p style={{ fontSize: '0.82rem', color: 'var(--text-dim)', lineHeight: 1.7, maxWidth: 520 }}>
                      Track the pattern, not just the last result. The dashboard surfaces risk movement, confidence quality, and the latest follow-up context in one clear view.
                    </p>
                  </div>
                  <motion.div
                    whileHover={{ scale: 1.02 }}
                    style={{ minWidth: 150, padding: '0.85rem 1rem', borderRadius: '1rem', background: `${trendColor}10`, border: `1px solid ${trendColor}25` }}
                  >
                    <div style={{ fontSize: '0.55rem', fontFamily: 'var(--mono)', color: trendColor, textTransform: 'uppercase', letterSpacing: '0.11em', marginBottom: '0.3rem' }}>
                      Current Pattern
                    </div>
                    <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--text)' }}>{trendLabel}</div>
                    <div style={{ fontSize: '0.68rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
                      {screeningsWithRisk.length > 0 ? `${Math.round(dashboardAvgRisk * 100)}% average risk across saved scans` : 'Run a scan to start tracking'}
                    </div>
                  </motion.div>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem', alignItems: 'center' }}>
                  <div style={{ padding: '0.9rem 1rem', borderRadius: '1rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.06)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gap: '1rem', marginBottom: '0.55rem' }}>
                      <span style={{ fontSize: '0.58rem', fontFamily: 'var(--mono)', letterSpacing: '0.12em', textTransform: 'uppercase', color: 'var(--text-dim)' }}>
                        Risk Trajectory
                      </span>
                      <span style={{ fontSize: '0.62rem', fontFamily: 'var(--mono)', color: trendColor }}>
                        last {Math.min(recentRiskSeries.length, 6)} scans
                      </span>
                    </div>
                    <AnimatedLineChart values={recentRiskSeries} color={trendColor} />
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
                        ? `${formatDateTime(latest.created_at)}${latest.headline ? ` | ${latest.headline}` : ''}`
                        : 'Once you run a scan, the newest case summary appears here.'}
                    </div>
                  </div>
                </div>
              </motion.div>

              {/* Stat Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.85rem' }}>
                <StatCard icon={<Activity size={15} />} label="Total Scans" value={String(totalScans)} tint="#00C2FF" sub="Saved screening records" delay={0.1} />
                <StatCard icon={<Clock size={15} />} label="This Month" value={String(scansThisMonth)} tint="#A855F7" sub={lastScanAt ? `Last scan ${formatDateTime(lastScanAt)}` : 'No completed screenings yet'} delay={0.18} />
                <StatCard icon={<Gauge size={15} />} label="Avg Confidence" value={`${Math.round(avgConfidence * 100)}%`} tint="#10B981" sub="Mean confidence across stored runs" delay={0.26} />
                <StatCard icon={<AlertTriangle size={15} />} label="Flagged Cases" value={String(flaggedCount)} tint="#EF4444" sub="High concern + retake-needed cases" delay={0.34} />
              </div>
            </div>
          )}

          {/* Risk Distribution + Next Best Action */}
          {!isLoading && !statsLoading && (
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem' }}>
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
                <DistributionDonut counts={bandCounts} total={Math.max(total, screenings.length)} />
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
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '0.75rem' }}>
                  {[
                    { icon: <HeartPulse size={13} />, label: 'Avg risk', value: `${Math.round(avgRisk * 100)}%`, tint: '#F59E0B' },
                    { icon: <Stethoscope size={13} />, label: 'Latest band', value: latest ? bandLabel(latest.triage_band) : '—', tint: latest ? bandColor(latest.triage_band) : '#64748B' },
                    { icon: <Clock size={13} />, label: 'Newest scan', value: latest ? formatShortDate(latest.created_at) : '—', tint: '#00C2FF' },
                  ].map((tile) => (
                    <motion.div
                      key={tile.label}
                      whileHover={{ y: -3, background: 'rgba(255,255,255,0.04)' }}
                      style={{ padding: '0.8rem', borderRadius: '0.9rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: tile.tint, marginBottom: '0.45rem' }}>{tile.icon}</div>
                      <div style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-dim)', marginBottom: '0.18rem' }}>{tile.label}</div>
                      <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', lineHeight: 1.45 }}>{tile.value}</div>
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            </div>
          )}

          {/* Health Insights */}
          {!isLoading && !statsLoading && <HealthInsightsCard insights={insights} />}

          {/* Account Status */}
          {!isLoading && !statsLoading && (
            <motion.div
              initial={{ opacity: 0, y: 14 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.45, ease: E }}
              style={{
                padding: '1.25rem 1.35rem',
                borderRadius: '1.15rem',
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.06)',
                display: 'flex',
                flexDirection: 'column',
                gap: '0.95rem',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <UserCircle2 size={14} style={{ color: '#8B5CF6' }} />
                <span style={{ fontSize: '0.62rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.14em', color: '#8B5CF6' }}>
                  Account Status
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
                {[
                  {
                    label: 'Plan',
                    value: plan,
                    helper: user.role === 'admin' ? 'Operator access enabled' : 'Personal screening workspace',
                    icon: <ShieldCheck size={13} />,
                    tint: plan === 'Admin' ? '#EF4444' : plan === 'Pro' ? '#FFD700' : '#64748B',
                  },
                  {
                    label: 'Account sync',
                    value: accountTrustStatus,
                    helper: totalScans > 0 ? `${totalScans} results already secured in history` : 'New results can be saved right after screening',
                    icon: <CheckCircle2 size={13} />,
                    tint: '#10B981',
                  },
                  {
                    label: 'Member since',
                    value: formatShortDate(user.created_at),
                    helper: 'Profile is ready for repeat screening and follow-up tracking',
                    icon: <Clock size={13} />,
                    tint: '#00C2FF',
                  },
                  {
                    label: 'Last login',
                    value: formatMaybeDateTime(user.last_login_at),
                    helper: 'Secure auth is active for dashboard, history, and save-to-account actions',
                    icon: <UserCircle2 size={13} />,
                    tint: '#F59E0B',
                  },
                ].map((item) => (
                  <motion.div
                    key={item.label}
                    whileHover={{ y: -3, background: 'rgba(255,255,255,0.04)' }}
                    style={{ padding: '0.85rem 0.9rem', borderRadius: '0.95rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)', display: 'flex', flexDirection: 'column', gap: '0.45rem' }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', color: item.tint }}>{item.icon}</div>
                    <div style={{ fontSize: '0.56rem', fontFamily: 'var(--mono)', letterSpacing: '0.1em', textTransform: 'uppercase', color: 'var(--text-dim)' }}>{item.label}</div>
                    <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text)' }}>{item.value}</div>
                    <div style={{ fontSize: '0.7rem', color: 'var(--text-dim)', lineHeight: 1.55 }}>{item.helper}</div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}

          {/* History Section Header */}
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
            <motion.div
              initial={{ opacity: 0, y: 6 }}
              animate={{ opacity: 1, y: 0 }}
              style={{ padding: '0.85rem 1rem', borderRadius: '0.8rem', background: 'rgba(239,68,68,0.06)', border: '1px solid rgba(239,68,68,0.18)', fontSize: '0.75rem', color: '#FCA5A5' }}
            >
              {error}
            </motion.div>
          )}

          {screenings.length === 0 && !isLoading && (
            <motion.div
              initial={{ opacity: 0, scale: 0.97 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.4 }}
              style={{ padding: '3rem 1rem', textAlign: 'center', color: 'var(--text-dim)', fontSize: '0.82rem', borderRadius: '1.1rem', background: 'rgba(255,255,255,0.02)', border: '1px solid rgba(255,255,255,0.05)' }}
            >
              No screenings yet. Run your first scan to unlock trends, follow-up insights, and history export.
            </motion.div>
          )}

          {/* History Items */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.7rem' }}>
            <AnimatePresence>
              {screenings.map((screening, index) => (
                <motion.div
                  key={screening.uid}
                  initial={{ opacity: 0, x: -12 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 12 }}
                  transition={{ delay: index * 0.025, ease: E }}
                  whileHover={{ background: 'rgba(255,255,255,0.05)', borderColor: 'rgba(255,255,255,0.1)' }}
                  className="glass"
                  style={{
                    padding: '1rem 1.15rem',
                    display: 'grid',
                    gridTemplateColumns: '8px minmax(0, 1fr) auto',
                    gap: '1rem',
                    alignItems: 'stretch',
                    borderRadius: '0.85rem',
                    background: 'rgba(255,255,255,0.02)',
                    border: '1px solid rgba(255,255,255,0.06)',
                    transition: 'background 0.2s, border-color 0.2s',
                  }}
                >
                   <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <div style={{ width: 52, height: 52, borderRadius: '0.6rem', overflow: 'hidden', flexShrink: 0, border: '1px solid rgba(255,255,255,0.06)', background: '#000' }}>
                      <img 
                        src={RISK_IMAGES[screening.triage_band] || RISK_IMAGES.low_risk} 
                        alt="" 
                        style={{ width: '100%', height: '100%', objectFit: 'cover', opacity: 0.9 }} 
                      />
                    </div>
                    <div style={{ borderRadius: '999px', width: 4, height: 40, background: bandColor(screening.triage_band), boxShadow: `0 0 12px ${bandColor(screening.triage_band)}55`, flexShrink: 0 }} />
                  </div>
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
                      {screening.predicted_hemoglobin === null && (
                        <span style={{ padding: '0.28rem 0.55rem', borderRadius: '999px', fontSize: '0.58rem', fontFamily: 'var(--mono)', background: 'rgba(255,255,255,0.03)', border: '1px solid rgba(255,255,255,0.06)', color: 'var(--text-muted)' }}>
                          Hb unavailable
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

                  <MagneticButton
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
                  </MagneticButton>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>

          {screenings.length < total && (
            <MagneticButton
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
            </MagneticButton>
          )}
        </div>
      </motion.div>
    </motion.div>
  );
}
