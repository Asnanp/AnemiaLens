import type { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { Lightbulb } from 'lucide-react';

const E = [0.22, 1, 0.36, 1] as const;

export interface Insight {
  icon: ReactNode;
  tint: string;
  title: string;
  body: string;
  action?: string;
}

export function HealthInsightsCard({ insights }: { insights: Insight[] }) {
  if (insights.length === 0) return null;

  return (
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
        <Lightbulb size={14} style={{ color: '#FFD700' }} />
        <span style={{ fontSize: '0.62rem', fontFamily: 'var(--mono)', textTransform: 'uppercase', letterSpacing: '0.14em', color: '#FFD700' }}>
          Health Insights
        </span>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.65rem' }}>
        {insights.map((insight, idx) => (
          <motion.div
            key={insight.title}
            initial={{ opacity: 0, x: -12 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 12 }}
            transition={{ duration: 0.4, ease: E, delay: idx * 0.08 }}
            whileHover={{ x: 4, background: 'rgba(255,255,255,0.04)' }}
            style={{
              padding: '0.9rem 1rem',
              borderRadius: '0.9rem',
              background: 'rgba(255,255,255,0.02)',
              border: `1px solid ${insight.tint}18`,
              display: 'grid',
              gridTemplateColumns: '32px 1fr',
              gap: '0.75rem',
              alignItems: 'start',
            }}
          >
            <div style={{
              width: 32, height: 32, borderRadius: '0.7rem', display: 'flex', alignItems: 'center', justifyContent: 'center',
              background: `${insight.tint}12`, border: `1px solid ${insight.tint}22`, color: insight.tint, flexShrink: 0,
            }}>
              {insight.icon}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.25rem', minWidth: 0 }}>
              <div style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text)' }}>{insight.title}</div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-dim)', lineHeight: 1.6 }}>{insight.body}</div>
              {insight.action && (
                <div style={{ fontSize: '0.66rem', color: insight.tint, fontFamily: 'var(--mono)', marginTop: '0.15rem' }}>
                  {insight.action}
                </div>
              )}
            </div>
          </motion.div>
        ))}
      </div>
    </motion.div>
  );
}
