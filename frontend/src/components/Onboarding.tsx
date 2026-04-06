import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ArrowRight,
  ChevronRight,
  ChevronLeft,
  Shield,
  Eye,
  Sparkles,
  X,
  Lock,
  Smartphone,
  Activity,
  CheckCircle2,
} from 'lucide-react';

import { E } from '../components/screening/SharedUI';

/* ── Types ─────────────────────────────────────────────────────────────── */

export type OnboardingStep = {
  id: string;
  eyebrow: string;
  title: string;
  subtitle: string;
  features: string[];
  icon: React.ElementType;
  accent: 'crimson' | 'teal' | 'violet';
  illustration: React.ReactNode;
};

/* ── Step Definitions ──────────────────────────────────────────────────── */

const STEPS: OnboardingStep[] = [
  {
    id: 'what',
    eyebrow: 'What it does',
    title: 'Screen for anemia risk\nfrom a single photo.',
    subtitle:
      'AnemiaLens analyzes a lower-eyelid image with an AI model trained to estimate hemoglobin levels — no blood draw needed for a first-pass check.',
    features: [
      'Instant risk assessment in seconds',
      'Confidence and reliability scores shown alongside every result',
      'Works on any smartphone camera',
    ],
    icon: Eye,
    accent: 'crimson',
    illustration: (
      <div className="onboarding-illustration onboarding-illustration--what">
        {/* Central phone frame */}
        <motion.div
          className="onboarding-phone"
          initial={{ y: 30, opacity: 0 }}
          animate={{ y: 0, opacity: 1 }}
          transition={{ duration: 0.7, delay: 0.2, ease: E }}
        >
          <div className="onboarding-phone__screen">
            {/* Eye region mock */}
            <div className="onboarding-phone__eye">
              <div className="onboarding-phone__eye-iris" />
              <div className="onboarding-phone__eye-glint" />
            </div>
            {/* Scanning line */}
            <motion.div
              className="onboarding-phone__scan-line"
              animate={{ top: ['15%', '80%', '15%'] }}
              transition={{ duration: 3, repeat: Infinity, ease: 'easeInOut' }}
            />
            {/* Result pills */}
            <div className="onboarding-phone__results">
              <div className="onboarding-phone__pill onboarding-phone__pill--risk">
                <Activity size={10} />
                <span>Risk Score</span>
              </div>
              <div className="onboarding-phone__pill onboarding-phone__pill--confidence">
                <Sparkles size={10} />
                <span>Confidence</span>
              </div>
            </div>
          </div>
          <div className="onboarding-phone__notch" />
        </motion.div>

        {/* Floating orbs */}
        <motion.div
          className="onboarding-orb onboarding-orb--crimson"
          animate={{ y: [0, -16, 0], scale: [1, 1.05, 1] }}
          transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="onboarding-orb onboarding-orb--teal"
          animate={{ y: [0, -12, 0], x: [0, 8, 0] }}
          transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut', delay: 0.5 }}
        />
        <motion.div
          className="onboarding-orb onboarding-orb--violet"
          animate={{ y: [0, -10, 0], x: [0, -6, 0] }}
          transition={{ duration: 4.5, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
        />
      </div>
    ),
  },
  {
    id: 'how',
    eyebrow: 'How it works',
    title: 'Four guided steps\nto a clear result.',
    subtitle:
      'Upload a photo, pass a quality gate, add symptom context, and receive a structured screening report — each step transparent and explainable.',
    features: [
      'Quality gate stops blurry or poorly lit images before analysis',
      'Symptom intake adds clinical context for better triage',
      'Multi-agent pipeline: image quality, screening, triage, guidance',
    ],
    icon: Smartphone,
    accent: 'teal',
    illustration: (
      <div className="onboarding-illustration onboarding-illustration--how">
        {/* Pipeline steps */}
        <div className="onboarding-pipeline">
          {[
            { label: 'Capture', icon: Smartphone, delay: 0 },
            { label: 'Quality', icon: Shield, delay: 0.15 },
            { label: 'Intake', icon: Activity, delay: 0.3 },
            { label: 'Result', icon: CheckCircle2, delay: 0.45 },
          ].map(({ label, icon: StepIcon, delay }, i) => (
            <motion.div
              key={label}
              className="onboarding-pipeline__node"
              initial={{ opacity: 0, scale: 0.6 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.5, delay: delay + 0.2, ease: E }}
            >
              <div className="onboarding-pipeline__icon">
                <StepIcon size={18} />
              </div>
              <span className="onboarding-pipeline__label">{label}</span>
              {i < 3 && (
                <motion.div
                  className="onboarding-pipeline__connector"
                  initial={{ scaleX: 0 }}
                  animate={{ scaleX: 1 }}
                  transition={{ duration: 0.4, delay: delay + 0.4, ease: E }}
                  style={{ transformOrigin: 'left center' }}
                >
                  <ChevronRight size={12} />
                </motion.div>
              )}
            </motion.div>
          ))}
        </div>

        {/* Animated flow line */}
        <motion.div
          className="onboarding-flow-particle"
          animate={{ x: ['-120%', '120%'] }}
          transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut', repeatDelay: 0.5 }}
        />

        {/* Floating accent dots */}
        <motion.div
          className="onboarding-orb onboarding-orb--teal onboarding-orb--sm"
          animate={{ y: [0, -14, 0], x: [0, 10, 0] }}
          transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="onboarding-orb onboarding-orb--crimson onboarding-orb--sm"
          animate={{ y: [0, -8, 0], x: [0, -10, 0] }}
          transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut', delay: 0.8 }}
        />
      </div>
    ),
  },
  {
    id: 'privacy',
    eyebrow: 'Privacy & Safety',
    title: 'Your data stays\nprivate and secure.',
    subtitle:
      'Screenings are processed locally and on your device where possible. We never sell your data, and you control what gets stored.',
    features: [
      'Images are not stored on servers without your explicit consent',
      'No facial recognition — only the lower-eyelid region is analyzed',
      'You can delete any screening history at any time',
    ],
    icon: Lock,
    accent: 'violet',
    illustration: (
      <div className="onboarding-illustration onboarding-illustration--privacy">
        {/* Shield icon */}
        <motion.div
          className="onboarding-shield"
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.7, delay: 0.2, ease: E }}
        >
          <Lock size={40} strokeWidth={1.5} />
          {/* Checkmark ring */}
          <motion.div
            className="onboarding-shield__check"
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.4, delay: 0.7, ease: E }}
          >
            <CheckCircle2 size={16} />
          </motion.div>
        </motion.div>

        {/* Privacy badges floating around */}
        {[
          { label: 'Encrypted', delay: 0.4 },
          { label: 'No Tracking', delay: 0.6 },
          { label: 'Your Control', delay: 0.8 },
        ].map(({ label, delay }) => (
          <motion.div
            key={label}
            className="onboarding-badge"
            initial={{ opacity: 0, y: 20, rotate: -5 }}
            animate={{ opacity: 1, y: 0, rotate: 0 }}
            transition={{ duration: 0.5, delay, ease: E }}
          >
            <Sparkles size={10} />
            <span>{label}</span>
          </motion.div>
        ))}

        {/* Soft glow rings */}
        <motion.div
          className="onboarding-ring onboarding-ring--1"
          animate={{ scale: [1, 1.08, 1], opacity: [0.15, 0.25, 0.15] }}
          transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="onboarding-ring onboarding-ring--2"
          animate={{ scale: [1, 1.06, 1], opacity: [0.1, 0.18, 0.1] }}
          transition={{ duration: 5, repeat: Infinity, ease: 'easeInOut', delay: 1 }}
        />
      </div>
    ),
  },
];

const ACCENT_COLORS: Record<string, { bg: string; text: string; glow: string; pill: string; pillText: string }> = {
  crimson: {
    bg: 'rgba(200, 0, 30, 0.06)',
    text: 'var(--color-primary-light)',
    glow: 'rgba(200, 0, 30, 0.15)',
    pill: 'rgba(200, 0, 30, 0.12)',
    pillText: 'var(--color-primary-light)',
  },
  teal: {
    bg: 'rgba(94, 234, 212, 0.06)',
    text: 'var(--color-secondary)',
    glow: 'rgba(94, 234, 212, 0.15)',
    pill: 'rgba(94, 234, 212, 0.12)',
    pillText: 'var(--color-secondary)',
  },
  violet: {
    bg: 'rgba(139, 92, 246, 0.06)',
    text: 'var(--color-accent-light)',
    glow: 'rgba(139, 92, 246, 0.15)',
    pill: 'rgba(139, 92, 246, 0.12)',
    pillText: 'var(--color-accent-light)',
  },
};

/* ── Progress Dots ─────────────────────────────────────────────────────── */

function ProgressDots({ current, total, accent }: { current: number; total: number; accent: string }) {
  return (
    <div className="onboarding-dots" role="tablist" aria-label="Onboarding progress">
      {Array.from({ length: total }).map((_, i) => (
        <motion.div
          key={i}
          className={`onboarding-dot ${i <= current ? 'onboarding-dot--active' : ''}`}
          animate={
            i === current
              ? {
                  backgroundColor: ACCENT_COLORS[accent]?.text || ACCENT_COLORS.teal.text,
                  scale: 1.3,
                }
              : i < current
              ? {
                  backgroundColor: 'rgba(255,255,255,0.3)',
                  scale: 1,
                }
              : {
                  backgroundColor: 'rgba(255,255,255,0.12)',
                  scale: 1,
                }
          }
          transition={{ duration: 0.3, ease: E }}
        />
      ))}
    </div>
  );
}

/* ── Step Content ──────────────────────────────────────────────────────── */

function StepContent({ step, direction }: { step: OnboardingStep; direction: 'left' | 'right' }) {
  const accent = ACCENT_COLORS[step.accent] || ACCENT_COLORS.teal;

  return (
    <motion.div
      className="onboarding-step"
      key={step.id}
      initial={{ opacity: 0, x: direction === 'left' ? 60 : -60 }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: direction === 'left' ? -60 : 60 }}
      transition={{ duration: 0.45, ease: E }}
    >
      {/* Icon */}
      <motion.div
        className="onboarding-step__icon"
        style={{ background: accent.bg, color: accent.text }}
        initial={{ scale: 0.5, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        transition={{ duration: 0.4, delay: 0.1, ease: E }}
      >
        <step.icon size={28} strokeWidth={1.5} />
      </motion.div>

      {/* Eyebrow */}
      <motion.div
        className="onboarding-step__eyebrow"
        style={{ color: accent.text }}
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.15, ease: E }}
      >
        {step.eyebrow}
      </motion.div>

      {/* Title */}
      <motion.h2
        className="onboarding-step__title"
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, delay: 0.2, ease: E }}
      >
        {step.title}
      </motion.h2>

      {/* Subtitle */}
      <motion.p
        className="onboarding-step__subtitle"
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4, delay: 0.3, ease: E }}
      >
        {step.subtitle}
      </motion.p>

      {/* Features */}
      <ul className="onboarding-step__features">
        {step.features.map((feature, i) => (
          <motion.li
            key={feature}
            initial={{ opacity: 0, x: -16 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.35, delay: 0.35 + i * 0.08, ease: E }}
          >
            <CheckCircle2 size={14} style={{ color: accent.text, flexShrink: 0 }} />
            <span>{feature}</span>
          </motion.li>
        ))}
      </ul>
    </motion.div>
  );
}

/* ── Main Onboarding Component ─────────────────────────────────────────── */

type OnboardingProps = {
  onComplete: () => void;
  onSkip: () => void;
};

const DIRECTION_THRESHOLD = 50;

export function Onboarding({ onComplete, onSkip }: OnboardingProps) {
  const [current, setCurrent] = useState(0);
  const [direction, setDirection] = useState<'left' | 'right'>('left');
  const [isExiting, setIsExiting] = useState(false);

  const step = STEPS[current];
  const isLast = current === STEPS.length - 1;

  const navigate = useCallback(
    (nextIndex: number) => {
      setDirection(nextIndex > current ? 'left' : 'right');
      setCurrent(nextIndex);
    },
    [current]
  );

  const handleNext = useCallback(() => {
    if (isLast) {
      handleComplete();
    } else {
      navigate(current + 1);
    }
  }, [isLast, current, navigate]);

  const handleComplete = useCallback(() => {
    setIsExiting(true);
    setTimeout(() => {
      onComplete();
    }, 400);
  }, [onComplete]);

  const handleSkip = useCallback(() => {
    setIsExiting(true);
    setTimeout(() => {
      onSkip();
    }, 300);
  }, [onSkip]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowRight' && current < STEPS.length - 1) {
        navigate(current + 1);
      } else if (e.key === 'ArrowLeft' && current > 0) {
        navigate(current - 1);
      } else if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleNext();
      }
    },
    [current, navigate, handleNext]
  );

  const accent = ACCENT_COLORS[step.accent] || ACCENT_COLORS.teal;

  return (
    <motion.div
      className="onboarding"
      initial={{ opacity: 0 }}
      animate={isExiting ? { opacity: 0, scale: 0.97 } : { opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.97 }}
      transition={{ duration: 0.4, ease: E }}
      onKeyDown={handleKeyDown}
      role="dialog"
      aria-modal="true"
      aria-label="Welcome to AnemiaLens"
      tabIndex={0}
    >
      {/* Ambient background */}
      <div className="onboarding__bg" />
      <motion.div
        className="onboarding__glow"
        style={{ background: `radial-gradient(circle, ${accent.glow} 0%, transparent 65%)` }}
        animate={{ opacity: [0.5, 0.8, 0.5] }}
        transition={{ duration: 4, repeat: Infinity, ease: 'easeInOut' }}
      />

      {/* Close / Skip */}
      <div className="onboarding__header">
        <button
          type="button"
          className="onboarding__skip"
          onClick={handleSkip}
          aria-label="Skip onboarding"
        >
          Skip
        </button>
        <button
          type="button"
          className="onboarding__close"
          onClick={handleComplete}
          aria-label="Close onboarding"
        >
          <X size={18} />
        </button>
      </div>

      {/* Main content card */}
      <div className="onboarding__card">
        <div className="onboarding__inner">
          {/* Left: illustration */}
          <div className="onboarding__visual">
            <AnimatePresence mode="wait">{step.illustration}</AnimatePresence>
          </div>

          {/* Right: step content */}
          <div className="onboarding__content">
            <AnimatePresence mode="wait" custom={direction}>
              <StepContent key={step.id} step={step} direction={direction} />
            </AnimatePresence>

            {/* Navigation */}
            <div className="onboarding__footer">
              <ProgressDots current={current} total={STEPS.length} accent={step.accent} />

              <div className="onboarding__actions">
                {current > 0 && (
                  <motion.button
                    type="button"
                    className="onboarding__back"
                    onClick={() => navigate(current - 1)}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    exit={{ opacity: 0, x: -10 }}
                    whileHover={{ x: -3 }}
                    transition={{ duration: 0.2 }}
                    aria-label="Previous step"
                  >
                    <ChevronLeft size={16} />
                  </motion.button>
                )}

                <motion.button
                  type="button"
                  className={`onboarding__next ${isLast ? 'onboarding__next--final' : ''}`}
                  onClick={handleNext}
                  whileHover={{ scale: 1.02, y: -1 }}
                  whileTap={{ scale: 0.98 }}
                  transition={{ duration: 0.2 }}
                >
                  {isLast ? (
                    <>
                      Start Screening
                      <ArrowRight size={16} />
                    </>
                  ) : (
                    <>
                      Next
                      <ChevronRight size={16} />
                    </>
                  )}
                </motion.button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

export default Onboarding;
