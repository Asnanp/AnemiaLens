import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { Activity, CheckCircle2, XCircle, Clock, Cpu, Database, Zap, RefreshCw } from 'lucide-react';
import { endpoint } from '../api';

const FADE_UP = {
  hidden: { opacity: 0, y: 24 },
  visible: (i = 0) => ({ opacity: 1, y: 0, transition: { duration: 0.55, ease: 'easeOut' as const, delay: i * 0.08 } })
};

interface HealthData {
  status: string;
  model_ready: boolean;
  guidance_strategy?: string;
}

interface ReadyzData {
  status: string;
  model_ready: boolean;
  guidance_client_ready?: boolean;
  guidance_strategy?: string;
  guidance_fallback_reason?: string;
}

// Uses dynamic endpoint helper for production routing proxy

function StatusBadge({ ok, label }: { ok: boolean; label: string }) {
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: '0.35rem',
      padding: '0.25rem 0.7rem', borderRadius: '2rem', fontSize: '0.68rem',
      fontWeight: 600, fontFamily: 'var(--mono)',
      background: ok ? 'rgba(16,185,129,0.12)' : 'rgba(239,68,68,0.12)',
      border: `1px solid ${ok ? 'rgba(16,185,129,0.3)' : 'rgba(239,68,68,0.3)'}`,
      color: ok ? '#34d399' : '#f87171',
    }}>
      {ok ? <CheckCircle2 size={11} /> : <XCircle size={11} />}
      {label}
    </span>
  );
}

function PingBar({ label, url, icon: Icon }: { label: string; url: string; icon: any }) {
  const [status, setStatus] = useState<'loading' | 'ok' | 'error'>('loading');
  const [latency, setLatency] = useState<number | null>(null);

  const probe = async () => {
    setStatus('loading');
    const t0 = Date.now();
    try {
      await fetch(url, { signal: AbortSignal.timeout(8000) });
      setLatency(Date.now() - t0);
      setStatus('ok');
    } catch {
      setStatus('error');
      setLatency(null);
    }
  };

  useEffect(() => { probe(); }, [url]);

  const color = status === 'ok' ? '#10b981' : status === 'error' ? '#ef4444' : '#f59e0b';

  return (
    <div className="glass" style={{ padding: '1.25rem 1.5rem', borderRadius: '1.1rem', display: 'flex', alignItems: 'center', gap: '1rem',
      background: 'rgba(15,23,42,0.025)', border: '1px solid rgba(15,23,42,0.06)' }}>
      <div style={{ width: 36, height: 36, borderRadius: '50%', background: `${color}15`, border: `1.5px solid ${color}40`,
        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
        <Icon size={16} color={color} />
      </div>
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 600, fontSize: '0.88rem', marginBottom: '0.2rem' }}>{label}</div>
        <div style={{ fontFamily: 'var(--mono)', fontSize: '0.62rem', color: 'var(--text-dim)' }}>{url}</div>
      </div>
      <div style={{ textAlign: 'right', flexShrink: 0 }}>
        {status === 'loading' ? (
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#f59e0b', animation: 'pulse 1.2s ease-in-out infinite' }} />
        ) : (
          <>
            <StatusBadge ok={status === 'ok'} label={status === 'ok' ? 'Online' : 'Offline'} />
            {latency !== null && (
              <div style={{ fontFamily: 'var(--mono)', fontSize: '0.6rem', color: 'var(--text-dim)', marginTop: '0.25rem' }}>
                {latency}ms
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

function HealthPanel() {
  const [health, setHealth] = useState<HealthData | null>(null);
  const [readyz, setReadyz] = useState<ReadyzData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState(new Date());

  const refresh = async () => {
    setLoading(true);
    try {
      const [h, r] = await Promise.allSettled([
        fetch(endpoint('/health'), { signal: AbortSignal.timeout(15000) }).then(res => res.json()),
        fetch(endpoint('/readyz'), { signal: AbortSignal.timeout(15000) }).then(res => res.json()),
      ]);
      if (h.status === 'fulfilled') setHealth(h.value);
      if (r.status === 'fulfilled') setReadyz(r.value);
      setLastRefresh(new Date());
    } catch { /* silent */ }
    finally { setLoading(false); }
  };

  useEffect(() => { refresh(); }, []);

  return (
    <div className="glass" style={{ padding: '2rem', borderRadius: '1.5rem', background: 'rgba(15,23,42,0.03)', border: '1px solid rgba(15,23,42,0.07)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <h3 style={{ fontFamily: 'var(--serif)', fontSize: '1.3rem', fontWeight: 700 }}>Backend Health</h3>
        <button onClick={refresh} style={{ background: 'none', border: '1px solid rgba(15,23,42,0.1)', borderRadius: '0.5rem',
          padding: '0.35rem 0.75rem', color: 'var(--text-muted)', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.4rem', fontSize: '0.7rem' }}>
          <RefreshCw size={11} />
          Refresh
        </button>
      </div>

      {loading ? (
        <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
          <div style={{ width: 8, height: 8, borderRadius: '50%', background: '#f59e0b', animation: 'pulse 1s ease-in-out infinite' }} />
          Probing backend…
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1rem' }}>
          {[
            { label: 'Service Status', value: health?.status ?? 'unknown', ok: health?.status === 'ok' },
            { label: 'Model Ready', value: health?.model_ready ? 'Yes' : 'No', ok: !!health?.model_ready },
            { label: 'Readiness', value: readyz?.status ?? 'unknown', ok: readyz?.status === 'ready' },
            { label: 'Guidance AI', value: readyz?.guidance_strategy ?? '—', ok: !!readyz?.guidance_client_ready },
          ].map(item => (
            <div key={item.label} style={{ padding: '1rem', borderRadius: '0.75rem', background: 'rgba(15,23,42,0.03)', border: '1px solid rgba(15,23,42,0.05)' }}>
              <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', fontFamily: 'var(--mono)', marginBottom: '0.4rem' }}>{item.label}</div>
              <div style={{ fontWeight: 600, fontSize: '0.9rem', color: item.ok ? '#34d399' : '#f87171' }}>{item.value}</div>
            </div>
          ))}
        </div>
      )}

      <div style={{ marginTop: '1rem', fontSize: '0.6rem', color: 'var(--text-dim)', fontFamily: 'var(--mono)' }}>
        Last refreshed: {lastRefresh.toLocaleTimeString()}
      </div>
    </div>
  );
}

const ENDPOINT_PINGS = [
  { label: 'Health Check', url: endpoint('/health'), icon: Activity },
  { label: 'Readiness Probe', url: endpoint('/readyz'), icon: CheckCircle2 },
  { label: 'Runtime Status', url: endpoint('/api/runtime-status'), icon: Cpu },
];

export default function StatusPage() {
  return (
    <main style={{ minHeight: '100vh', paddingTop: '8rem', paddingBottom: '6rem', color: 'var(--text-primary)' }}>
      <div style={{ maxWidth: 1100, margin: '0 auto', padding: '0 clamp(1rem, 4vw, 4rem)' }}>

        <motion.div initial="hidden" animate="visible" variants={FADE_UP} style={{ textAlign: 'center', marginBottom: '4rem' }}>
          <div className="section-eyebrow" style={{ marginBottom: '1rem' }}>
            <Activity size={13} style={{ display: 'inline', marginRight: '0.35rem' }} />
            System Status
          </div>
          <h1 style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(2.5rem, 5vw, 4rem)', fontWeight: 700, letterSpacing: '-0.03em', marginBottom: '1rem' }}>
            Live Platform Status
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.95rem', maxWidth: 500, margin: '0 auto' }}>
            Real-time health, model readiness, and endpoint latency for the AnemiaLens backend.
          </p>
        </motion.div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem', marginBottom: '3rem' }}>
          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={FADE_UP}>
            <HealthPanel />
          </motion.div>

          <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} custom={1} variants={FADE_UP}>
            <div className="glass" style={{ padding: '2rem', borderRadius: '1.5rem', background: 'rgba(15,23,42,0.03)', border: '1px solid rgba(15,23,42,0.07)' }}>
              <h3 style={{ fontFamily: 'var(--serif)', fontSize: '1.3rem', fontWeight: 700, marginBottom: '1.5rem' }}>Platform Info</h3>
              {[
                { icon: Zap, label: 'Backend Host', value: 'Hugging Face Spaces' },
                { icon: Database, label: 'Database', value: 'Supabase PostgreSQL' },
                { icon: Cpu, label: 'Primary Model', value: 'Archive Fusion V8' },
                { icon: Clock, label: 'Cold Start', value: '60s–120s (sleeping state)' },
              ].map((item) => {
                const Icon = item.icon;
                return (
                  <div key={item.label} style={{ display: 'flex', gap: '0.75rem', padding: '0.85rem 0', borderBottom: '1px solid rgba(15,23,42,0.04)' }}>
                    <Icon size={16} color="var(--text-dim)" style={{ flexShrink: 0, marginTop: 2 }} />
                    <div>
                      <div style={{ fontSize: '0.65rem', color: 'var(--text-dim)', fontFamily: 'var(--mono)', marginBottom: '0.1rem' }}>{item.label}</div>
                      <div style={{ fontSize: '0.85rem', fontWeight: 600 }}>{item.value}</div>
                    </div>
                  </div>
                );
              })}
            </div>
          </motion.div>
        </div>

        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={FADE_UP} style={{ marginBottom: '2rem' }}>
          <h2 style={{ fontFamily: 'var(--serif)', fontSize: '1.6rem', fontWeight: 700, marginBottom: '1.5rem' }}>Endpoint Probes</h2>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
            {ENDPOINT_PINGS.map((ep, i) => (
              <motion.div key={ep.url} custom={i} variants={FADE_UP}>
                <PingBar {...ep} />
              </motion.div>
            ))}
          </div>
        </motion.div>

        <motion.div initial="hidden" whileInView="visible" viewport={{ once: true }} variants={FADE_UP}
          style={{ padding: '1rem 1.5rem', borderRadius: '0.875rem', background: 'rgba(99,102,241,0.06)',
            border: '1px solid rgba(99,102,241,0.2)', fontSize: '0.75rem', color: '#a5b4fc' }}>
          ℹ️ Hugging Face Spaces enter a sleeping state after periods of inactivity. The first request triggers a 60s–120s cold-start boot.
          Subsequent requests are fast once the Space is warm.
        </motion.div>
      </div>
    </main>
  );
}
