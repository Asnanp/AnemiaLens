import type { CSSProperties, ReactNode } from 'react';
import { Link } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import type { LucideIcon } from 'lucide-react';

export const PAGE_EASE = [0.22, 1, 0.36, 1] as const;
const MotionLink = motion(Link);

const shellStyle: CSSProperties = {
  position: 'relative',
  minHeight: '100vh',
  overflow: 'hidden',
  background:
    'radial-gradient(circle at 15% 15%, rgba(255, 59, 99, 0.14), transparent 30%), radial-gradient(circle at 85% 20%, rgba(99, 102, 241, 0.14), transparent 28%), radial-gradient(circle at 70% 75%, rgba(34, 211, 238, 0.08), transparent 25%), linear-gradient(180deg, #020408 0%, #04070d 42%, #020408 100%)',
  color: 'var(--text)',
};

const contentStyle: CSSProperties = {
  width: 'min(1180px, calc(100vw - 2rem))',
  margin: '0 auto',
};

type ActionLinkProps = {
  to: string;
  children: ReactNode;
  variant?: 'primary' | 'secondary';
};

type SurfaceStat = {
  label: string;
  value: string;
  detail?: string;
};

type PageSurfaceProps = {
  eyebrow: string;
  title: ReactNode;
  intro: ReactNode;
  badges?: readonly string[];
  stats?: readonly SurfaceStat[];
  actions?: ReactNode;
  side?: ReactNode;
  children: ReactNode;
};

type SectionBlockProps = {
  eyebrow?: string;
  title: ReactNode;
  intro?: ReactNode;
  children: ReactNode;
  align?: 'left' | 'center';
};

type FeatureCardProps = {
  icon?: LucideIcon;
  title: string;
  detail: ReactNode;
  kicker?: string;
};

type TimelineStep = {
  number: string;
  title: string;
  detail: ReactNode;
};

type FAQItem = {
  question: string;
  answer: ReactNode;
};

export function PageSurface({ eyebrow, title, intro, badges = [], stats = [], actions, side, children }: PageSurfaceProps) {
  const reduceMotion = useReducedMotion();

  return (
    <main style={shellStyle}>
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          inset: 0,
          pointerEvents: 'none',
          opacity: 0.65,
          backgroundImage:
            'linear-gradient(rgba(255,255,255,0.022) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.022) 1px, transparent 1px)',
          backgroundSize: '120px 120px',
          maskImage: 'radial-gradient(circle at center, black 35%, transparent 100%)',
        }}
      />
      <motion.div
        aria-hidden="true"
        style={{
          position: 'absolute',
          top: '10%',
          left: '-8%',
          width: '28rem',
          height: '28rem',
          borderRadius: '999px',
          background: 'radial-gradient(circle, rgba(255,59,99,0.18) 0%, transparent 70%)',
          filter: 'blur(42px)',
        }}
        animate={reduceMotion ? undefined : { y: [0, 16, 0] }}
        transition={reduceMotion ? undefined : { duration: 12, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        aria-hidden="true"
        style={{
          position: 'absolute',
          right: '-10%',
          top: '14%',
          width: '30rem',
          height: '30rem',
          borderRadius: '999px',
          background: 'radial-gradient(circle, rgba(99,102,241,0.16) 0%, transparent 68%)',
          filter: 'blur(52px)',
        }}
        animate={reduceMotion ? undefined : { y: [0, -14, 0] }}
        transition={reduceMotion ? undefined : { duration: 14, repeat: Infinity, ease: 'easeInOut' }}
      />

      <div style={{ position: 'relative', zIndex: 1, paddingTop: 'clamp(7rem, 12vw, 9rem)', paddingBottom: 'clamp(4.5rem, 8vw, 6.5rem)' }}>
        <div style={contentStyle}>
          <section
            style={{
              display: 'grid',
              gap: 'clamp(2rem, 4vw, 3.2rem)',
            }}
          >
            <div
              className="glass route-page-hero-shell"
              style={{
                display: 'grid',
                gridTemplateColumns: side ? 'minmax(0, 1.08fr) minmax(320px, 0.92fr)' : '1fr',
                gap: 'clamp(1.5rem, 4vw, 3rem)',
                alignItems: 'start',
                padding: 'clamp(1.5rem, 3.6vw, 2.4rem)',
                borderRadius: '2rem',
                background: 'rgba(255,255,255,0.02)',
              }}
            >
              <motion.div
                className="route-page-hero-copy"
                initial={reduceMotion ? false : { opacity: 0, y: 24 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.75, ease: PAGE_EASE }}
                style={{ display: 'grid', gap: '1.1rem', alignContent: 'start' }}
              >
                <div className="section-eyebrow">{eyebrow}</div>
                <h1
                  style={{
                    fontFamily: 'var(--serif)',
                    fontSize: 'clamp(3rem, 6.4vw, 6.2rem)',
                    lineHeight: 0.92,
                    letterSpacing: '-0.05em',
                    fontWeight: 700,
                    maxWidth: '13ch',
                  }}
                >
                  {title}
                </h1>
                <p
                  style={{
                    maxWidth: '60ch',
                    color: 'var(--text-secondary)',
                    fontSize: 'clamp(1rem, 1.35vw, 1.15rem)',
                    lineHeight: 1.82,
                  }}
                >
                  {intro}
                </p>

                {badges.length > 0 && (
                  <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.7rem', paddingTop: '0.2rem' }}>
                    {badges.map((badge) => (
                      <span
                        key={badge}
                        style={{
                          padding: '0.52rem 0.86rem',
                          borderRadius: '999px',
                          fontSize: '0.66rem',
                          letterSpacing: '0.14em',
                          textTransform: 'uppercase',
                          fontFamily: 'var(--mono)',
                          color: 'var(--text)',
                          background: 'rgba(255,255,255,0.04)',
                          border: '1px solid rgba(255,255,255,0.08)',
                        }}
                      >
                        {badge}
                      </span>
                    ))}
                  </div>
                )}

                {actions && <div style={{ display: 'flex', flexWrap: 'wrap', gap: '0.75rem', paddingTop: '0.35rem' }}>{actions}</div>}
              </motion.div>

              {side && (
                <motion.div
                  className="route-page-hero-side"
                  initial={reduceMotion ? false : { opacity: 0, y: 24 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.8, delay: 0.1, ease: PAGE_EASE }}
                  style={{ minWidth: 0, alignSelf: 'stretch' }}
                >
                  {side}
                </motion.div>
              )}
            </div>

            {stats.length > 0 && (
              <motion.div
                initial={reduceMotion ? false : { opacity: 0, y: 18 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true, amount: 0.2 }}
                transition={{ duration: 0.7, ease: PAGE_EASE }}
                style={{
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
                  gap: '1rem',
                }}
              >
                {stats.map((stat) => (
                  <motion.div
                    key={stat.label}
                    className="glass"
                    whileHover={reduceMotion ? undefined : { y: -4, scale: 1.01 }}
                    style={{
                      padding: '1.2rem 1.25rem',
                      borderRadius: '1.25rem',
                      background: 'rgba(255,255,255,0.025)',
                      minHeight: '10.5rem',
                      display: 'grid',
                      alignContent: 'start',
                      gap: '0.55rem',
                    }}
                  >
                    <div className="label-tag">{stat.label}</div>
                    <div style={{ fontFamily: 'var(--serif)', fontSize: '1.8rem', fontWeight: 700, lineHeight: 1 }}>{stat.value}</div>
                    {stat.detail && (
                      <div style={{ color: 'var(--text-dim)', fontSize: '0.82rem', lineHeight: 1.7 }}>
                        {stat.detail}
                      </div>
                    )}
                  </motion.div>
                ))}
              </motion.div>
            )}

            <div
              style={{
                height: 1,
                background: 'linear-gradient(90deg, transparent, rgba(255,255,255,0.08), transparent)',
              }}
            />

            <div style={{ display: 'grid', gap: 'clamp(2.8rem, 6vw, 5rem)' }}>
              {children}
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

export function SectionBlock({ eyebrow, title, intro, children, align = 'left' }: SectionBlockProps) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 28 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.18 }}
      transition={{ duration: 0.7, ease: PAGE_EASE }}
      style={{
        display: 'grid',
        gap: '1.35rem',
        textAlign: align,
        alignItems: 'start',
      }}
    >
      {(eyebrow || intro) && (
        <div style={{ display: 'grid', gap: '0.8rem', maxWidth: '74rem' }}>
          {eyebrow && <div className="section-eyebrow">{eyebrow}</div>}
          {title && (
            <h2
              style={{
                fontFamily: 'var(--serif)',
                fontSize: 'clamp(2.2rem, 4.2vw, 4rem)',
                lineHeight: 0.98,
                letterSpacing: '-0.04em',
                fontWeight: 700,
              }}
            >
              {title}
            </h2>
          )}
          {intro && (
            <p style={{ color: 'var(--text-secondary)', maxWidth: '72ch', lineHeight: 1.82, marginInline: align === 'center' ? 'auto' : 0 }}>
              {intro}
            </p>
          )}
        </div>
      )}
      {children}
    </motion.section>
  );
}

export function CardGrid({ children }: { children: ReactNode }) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
        gap: '1rem',
      }}
    >
      {children}
    </div>
  );
}

export function FeatureCard({ icon: Icon, title, detail, kicker }: FeatureCardProps) {
  return (
    <motion.div
      className="glass"
      initial={{ opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.24 }}
      transition={{ duration: 0.58, ease: PAGE_EASE }}
      whileHover={{ y: -5, scale: 1.01 }}
      style={{
        padding: '1.4rem',
        borderRadius: '1.35rem',
        background: 'rgba(255,255,255,0.025)',
        display: 'grid',
        gap: '0.95rem',
        minHeight: '13.5rem',
        alignContent: 'start',
      }}
    >
      {kicker && <div className="label-tag">{kicker}</div>}
      {Icon && (
        <div
          style={{
            width: 42,
            height: 42,
            borderRadius: '1rem',
            display: 'grid',
            placeItems: 'center',
            color: 'var(--accent-bright)',
            background: 'rgba(255,59,99,0.1)',
            border: '1px solid rgba(255,59,99,0.18)',
          }}
        >
          <Icon size={18} />
        </div>
      )}
      <div style={{ display: 'grid', gap: '0.4rem' }}>
        <div style={{ fontFamily: 'var(--serif)', fontSize: '1.45rem', lineHeight: 1.04, letterSpacing: '-0.035em' }}>{title}</div>
        <div style={{ color: 'var(--text-secondary)', lineHeight: 1.75, fontSize: '0.94rem' }}>{detail}</div>
      </div>
    </motion.div>
  );
}

export function MetricStrip({ items }: { items: SurfaceStat[] }) {
  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(170px, 1fr))',
        gap: '0.9rem',
      }}
    >
      {items.map((item) => (
        <motion.div
          key={item.label}
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.24 }}
          transition={{ duration: 0.56, ease: PAGE_EASE }}
          whileHover={{ y: -4 }}
          style={{
            padding: '1rem 1.1rem',
            borderRadius: '1.1rem',
            background: 'rgba(255,255,255,0.03)',
            border: '1px solid rgba(255,255,255,0.08)',
          }}
        >
          <div className="label-tag" style={{ marginBottom: '0.4rem' }}>{item.label}</div>
          <div style={{ fontFamily: 'var(--serif)', fontWeight: 700, fontSize: '1.45rem', lineHeight: 1 }}>{item.value}</div>
          {item.detail && <div style={{ marginTop: '0.45rem', color: 'var(--text-dim)', fontSize: '0.78rem', lineHeight: 1.55 }}>{item.detail}</div>}
        </motion.div>
      ))}
    </div>
  );
}

export function QuoteCard({ quote, name, role }: { quote: ReactNode; name: string; role: string }) {
  return (
    <motion.div
      className="glass"
      initial={{ opacity: 0, y: 18 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, amount: 0.24 }}
      transition={{ duration: 0.56, ease: PAGE_EASE }}
      whileHover={{ y: -4 }}
      style={{
        padding: '1.35rem',
        borderRadius: '1.2rem',
        background: 'rgba(255,255,255,0.025)',
        display: 'grid',
        gap: '1rem',
      }}
    >
      <div style={{ color: 'var(--text)', lineHeight: 1.8, fontSize: '0.96rem' }}>{quote}</div>
      <div style={{ display: 'grid', gap: '0.15rem' }}>
        <div style={{ fontWeight: 700 }}>{name}</div>
        <div style={{ color: 'var(--text-dim)', fontSize: '0.78rem' }}>{role}</div>
      </div>
    </motion.div>
  );
}

export function TimelineList({ steps }: { steps: readonly TimelineStep[] }) {
  const reduceMotion = useReducedMotion();

  return (
    <div style={{ display: 'grid', gap: '1rem' }}>
      {steps.map((step) => (
        <motion.div
          key={step.number}
          className="glass"
          style={{
            padding: '1.2rem 1.25rem',
            borderRadius: '1.25rem',
            display: 'grid',
            gridTemplateColumns: 'auto minmax(0, 1fr)',
            gap: '1rem',
            alignItems: 'start',
            background: 'rgba(255,255,255,0.025)',
          }}
          initial={reduceMotion ? false : { opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.24 }}
          transition={{ duration: 0.6, ease: PAGE_EASE }}
        >
          <div
            style={{
              width: 54,
              height: 54,
              borderRadius: '999px',
              display: 'grid',
              placeItems: 'center',
              border: '1px solid rgba(255,255,255,0.1)',
              background: 'rgba(255,255,255,0.03)',
              fontFamily: 'var(--mono)',
              fontSize: '0.66rem',
              letterSpacing: '0.14em',
              textTransform: 'uppercase',
              color: 'var(--accent-bright)',
            }}
          >
            {step.number}
          </div>
          <div style={{ display: 'grid', gap: '0.45rem' }}>
            <div style={{ fontFamily: 'var(--serif)', fontSize: '1.45rem', lineHeight: 1.04, letterSpacing: '-0.03em' }}>{step.title}</div>
            <div style={{ color: 'var(--text-secondary)', lineHeight: 1.75, fontSize: '0.94rem', maxWidth: '62ch' }}>{step.detail}</div>
          </div>
        </motion.div>
      ))}
    </div>
  );
}

export function FaqList({ items }: { items: readonly FAQItem[] }) {
  return (
    <div style={{ display: 'grid', gap: '0.9rem' }}>
      {items.map((item) => (
        <motion.details
          key={item.question}
          className="glass"
          initial={{ opacity: 0, y: 18 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.24 }}
          transition={{ duration: 0.56, ease: PAGE_EASE }}
          style={{
            padding: '1rem 1.1rem',
            borderRadius: '1.1rem',
            background: 'rgba(255,255,255,0.025)',
          }}
        >
          <summary
            style={{
              cursor: 'pointer',
              listStyle: 'none',
              fontWeight: 700,
              letterSpacing: '-0.02em',
            }}
          >
            {item.question}
          </summary>
          <div style={{ marginTop: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.75, fontSize: '0.92rem' }}>
            {item.answer}
          </div>
        </motion.details>
      ))}
    </div>
  );
}

export function ActionRow({ actions }: { actions: readonly ActionLinkProps[] }) {
  return (
    <>
      {actions.map((action, index) => (
        <MotionLink
          key={`${action.to}-${index}`}
          to={action.to}
          whileHover={{ y: -3, scale: 1.01 }}
          whileTap={{ scale: 0.99 }}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.5rem',
            padding: '0.92rem 1.25rem',
            borderRadius: '999px',
            fontSize: '0.74rem',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            textDecoration: 'none',
            fontWeight: 700,
            border: action.variant === 'primary' ? '1px solid rgba(255,59,99,0.28)' : '1px solid rgba(255,255,255,0.1)',
            color: action.variant === 'primary' ? '#fff' : 'var(--text)',
            background:
              action.variant === 'primary'
                ? 'linear-gradient(135deg, #FF3B63 0%, #E8294A 100%)'
                : 'rgba(255,255,255,0.04)',
            boxShadow:
              action.variant === 'primary'
                ? '0 18px 44px rgba(255,59,99,0.18), inset 0 1px 0 rgba(255,255,255,0.26)'
                : 'inset 0 1px 0 rgba(255,255,255,0.08)',
            transition: 'transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease, background 180ms ease',
          }}
        >
          {action.children}
        </MotionLink>
      ))}
    </>
  );
}
