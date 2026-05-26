import { useRef, useState, useCallback, useEffect } from 'react';
import type { PointerEvent as ReactPointerEvent } from 'react';
import {
  motion,
  AnimatePresence,
  useMotionTemplate,
  useMotionValue,
  useReducedMotion,
  useScroll,
  useSpring,
  useTransform,
} from 'framer-motion';
import { Activity, ArrowRight, CheckCircle2, FileText, ScanEye, ShieldCheck, Sparkles } from 'lucide-react';

import { E } from '../components/screening/SharedUI';
import { scrollToId } from '../utils/scroll';
import { FloatingParticles } from '../components/FloatingParticles';
import { MagneticButton } from '../components/MagneticButton';
import { useParallax } from '../hooks/useScrollAnimation';
import { orbitalFloat, pulseGlow } from '../utils/springAnimations';

/* ────────────────────────────────────────────────────────────────────────── */

const HERO_SIGNALS = [
  { icon: ShieldCheck, label: 'Quality gate before inference' },
  { icon: Activity,    label: 'Trust stays visible beside risk' },
  { icon: Sparkles,    label: 'Care-ready summary output' },
] as const;

const HERO_SUPPORT = [
  {
    icon: ShieldCheck,
    kicker: 'Safety layer',
    title: 'Weak captures are stopped early',
    copy: 'Framing, blur, and light are checked before the model is allowed to shape the result.',
  },
  {
    icon: Activity,
    kicker: 'Decision layer',
    title: 'Image signal stays grounded',
    copy: 'Symptoms support the triage story only after the image has earned enough trust.',
  },
  {
    icon: FileText,
    kicker: 'Follow-up layer',
    title: 'The result stays useful after the screen',
    copy: 'Risk, trust, and next-step guidance stay together for the person or clinician.',
  },
] as const;

const HERO_FLOW = [
  { id: '01', label: 'Capture', micro: 'Guide one eyelid image' },
  { id: '02', label: 'Quality', micro: 'Check whether it is usable' },
  { id: '03', label: 'Intake',  micro: 'Merge context carefully' },
  { id: '04', label: 'Result',  micro: 'Keep trust and next step together' },
] as const;

const HERO_STAGE_DETAILS = [
  {
    eyebrow: 'Capture live',
    title: 'Guide the lower inner eyelid before scoring starts',
    detail: 'The first step checks framing and light before the image enters the screening flow.',
    checks: ['Indirect daylight preferred', 'Lower inner eyelid fully visible', 'Single calm capture'],
    metrics: [
      { label: 'Framing lock', value: 86, tone: 'rose' },
      { label: 'Light balance', value: 73, tone: 'teal' },
      { label: 'Stability', value: 79, tone: 'violet' },
    ],
  },
  {
    eyebrow: 'Quality gate',
    title: 'Stop weak captures before the model overclaims',
    detail: 'Blur, glare, and eyelid visibility are checked before the model is trusted.',
    checks: ['Blur and glare screened first', 'Weak images pause for retake', 'Trust stays visible beside the result'],
    metrics: [
      { label: 'ROI lock', value: 77, tone: 'rose' },
      { label: 'Glare screen', value: 88, tone: 'teal' },
      { label: 'Trust gate', value: 71, tone: 'violet' },
    ],
  },
  {
    eyebrow: 'Context merge',
    title: 'Add symptom context only after the image clears the gate',
    detail: 'Symptoms shape the triage story after the image has already earned basic trust.',
    checks: ['Image remains primary', 'Symptoms shape triage', 'Weak scans do not skip the gate'],
    metrics: [
      { label: 'Image weight', value: 78, tone: 'rose' },
      { label: 'Context fit', value: 61, tone: 'teal' },
      { label: 'Decision margin', value: 68, tone: 'violet' },
    ],
  },
  {
    eyebrow: 'Care summary',
    title: 'Risk, trust, and next step stay together',
    detail: 'The final surface keeps the screening signal, confidence, and follow-up guidance in one calm place.',
    checks: ['Risk shown beside trust', 'Guidance remains cautious', 'Share-ready handoff preserved'],
    metrics: [
      { label: 'Signal clarity', value: 83, tone: 'rose' },
      { label: 'Guidance fit', value: 92, tone: 'teal' },
      { label: 'Handoff ready', value: 87, tone: 'violet' },
    ],
  },
] as const;

/* ────────── Letter-by-letter headline component ────────── */

const containerVariant = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.15,
      delayChildren: 0.1,
    },
  },
};

const lineVariant = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.025,
    },
  },
};

const charVariant = {
  hidden: { opacity: 0, y: 15, filter: 'blur(4px)' },
  visible: {
    opacity: 1,
    y: 0,
    filter: 'blur(0px)',
    transition: { ease: [0.16, 1, 0.3, 1], duration: 0.5 },
  },
};

function AnimatedHeadline() {
  const reduceMotion = useReducedMotion();
  const lines = [
    { text: 'Safer anemia screening', accent: false },
    { text: 'from one guided', accent: false },
    { text: 'lower-eyelid image.', accent: true },
  ];

  if (reduceMotion) {
    return (
      <h1 className="home-hero-title">
        <span className="home-hero-title-line">Safer anemia screening</span>
        <span className="home-hero-title-line">from one guided</span>
        <span className="home-hero-title-line home-hero-title-accent">lower-eyelid image.</span>
      </h1>
    );
  }
  
  return (
    <motion.h1
      className="home-hero-title"
      initial={{ opacity: 1 }}
      animate={{ opacity: 1 }}
    >
      {lines.map((line, lineIdx) => (
        <motion.span 
          key={lineIdx} 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 + lineIdx * 0.15, duration: 0.8, ease: E }}
          className={`home-hero-title-line ${line.accent ? 'home-hero-title-accent' : ''}`}
        >
          {line.text}
        </motion.span>
      ))}
    </motion.h1>
  );
}

/* ────────── Main Hero component ────────── */

export function Hero() {
  const sectionRef = useRef<HTMLElement | null>(null);
  const frameRef = useRef<HTMLDivElement | null>(null);
  const reduceMotion = useReducedMotion();
  const [activeStage, setActiveStage] = useState(0);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ['start start', 'end start'],
  });

  const pointerX = useMotionValue(50);
  const pointerY = useMotionValue(38);
  const pointerXSpring = useSpring(pointerX, { stiffness: 100, damping: 20, mass: 0.9 });
  const pointerYSpring = useSpring(pointerY, { stiffness: 100, damping: 20, mass: 0.9 });

  const shellY = useTransform(scrollYProgress, [0, 1], [0, reduceMotion ? 0 : 80]);
  const shellOpacity = useTransform(scrollYProgress, [0, 0.85], [1, reduceMotion ? 1 : 0.7]);
  const shellScale = useTransform(scrollYProgress, [0, 1], [1, reduceMotion ? 1 : 0.98]);
  const supportY = useTransform(scrollYProgress, [0, 1], [0, reduceMotion ? 0 : 48]);
  const stageY = useTransform(scrollYProgress, [0, 1], [0, reduceMotion ? 0 : 60]);
  const activeStageDetail = HERO_STAGE_DETAILS[activeStage];

  const frameGlow = useMotionTemplate`
    radial-gradient(circle at ${pointerXSpring}% ${pointerYSpring}%, rgba(94, 234, 212, 0.12), transparent 44%),
    linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.015))
  `;

  const handlePointerMove = useCallback((event: ReactPointerEvent<HTMLElement>) => {
    const target = frameRef.current ?? sectionRef.current;
    if (reduceMotion || !target) return;
    const bounds = target.getBoundingClientRect();
    const nextX = ((event.clientX - bounds.left) / Math.max(bounds.width, 1)) * 100;
    const nextY = ((event.clientY - bounds.top) / Math.max(bounds.height, 1)) * 100;
    pointerX.set(Math.min(100, Math.max(0, nextX)));
    pointerY.set(Math.min(100, Math.max(0, nextY)));
  }, [reduceMotion, pointerX, pointerY]);

  const handlePointerLeave = useCallback(() => {
    if (reduceMotion) return;
    pointerX.set(50);
    pointerY.set(38);
  }, [reduceMotion, pointerX, pointerY]);

  return (
    <section
      ref={sectionRef}
      className="home-hero section-hero"
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
    >
      {/* ── Liquid ambient gradient background ── */}
      <motion.div
        aria-hidden="true"
        className="home-hero-aura home-hero-aura-primary"
        animate={reduceMotion ? undefined : {
          scale: [1, 1.08, 1],
          opacity: [0.4, 0.65, 0.4],
        }}
        transition={reduceMotion ? undefined : {
          duration: 14,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        style={{
          background: 'radial-gradient(circle, rgba(200,0,30,0.18) 0%, rgba(200,0,30,0.04) 40%, transparent 70%)',
        }}
      />
      <motion.div
        aria-hidden="true"
        className="home-hero-aura home-hero-aura-secondary"
        animate={reduceMotion ? undefined : {
          x: [0, 35, 0],
          y: [0, -25, 0],
          opacity: [0.15, 0.35, 0.15],
        }}
        transition={reduceMotion ? undefined : {
          duration: 18,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        style={{
          background: 'radial-gradient(circle, rgba(94,234,212,0.12) 0%, rgba(94,234,212,0.02) 40%, transparent 70%)',
        }}
      />
      <motion.div
        aria-hidden="true"
        className="home-hero-aura home-hero-aura-tertiary"
        animate={reduceMotion ? undefined : {
          x: [0, -20, 0],
          y: [0, 18, 0],
          opacity: [0.10, 0.25, 0.10],
        }}
        transition={reduceMotion ? undefined : {
          duration: 16,
          repeat: Infinity,
          ease: 'easeInOut',
        }}
        style={{
          background: 'radial-gradient(circle, rgba(255,107,138,0.10) 0%, transparent 60%)',
        }}
      />

      {/* ── Floating AI particles ── */}
      <FloatingParticles
        count={30}
        colors={[
          'rgba(94, 234, 212, VAL)',
          'rgba(200, 0, 30, VAL)',
          'rgba(255, 107, 138, VAL)',
          'rgba(255, 255, 255, VAL)',
        ]}
        style={{ position: 'absolute', inset: 0, zIndex: 0 }}
      />

      <motion.div
        className="home-hero-shell"
        style={{ y: shellY, opacity: shellOpacity, scale: shellScale }}
        initial={{ opacity: 0, y: 32 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.9, ease: E }}
      >
        {/* Eyebrow chip */}
        <motion.div
          className="hero-eyebrow-chip"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.04, ease: E }}
        >
          <motion.span
            className="hero-eyebrow-dot"
            animate={reduceMotion ? undefined : { scale: [1, 1.4, 1], opacity: [0.6, 1, 0.6] }}
            transition={reduceMotion ? undefined : { duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
            style={{ background: 'var(--teal)', boxShadow: '0 0 8px rgba(94,234,212,0.5)' }}
          />
          Smartphone screening support
        </motion.div>

        {/* Signal pills */}
        <motion.div
          className="home-hero-signal-row"
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.08, ease: E }}
        >
          {HERO_SIGNALS.map(({ icon: Icon, label }, index) => (
            <motion.div
              key={label}
              className="home-hero-signal-pill glass"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              whileHover={reduceMotion ? undefined : { y: -2, borderColor: 'rgba(94,234,212,0.2)' }}
              transition={{ duration: 0.45, delay: 0.12 + index * 0.08, ease: E }}
            >
              <Icon size={13} style={{ color: 'var(--teal)' }} />
              <span>{label}</span>
            </motion.div>
          ))}
        </motion.div>

        {/* ── Letter-by-letter animated headline ── */}
        <AnimatedHeadline />

        {/* Text frame with pointer-following glow */}
        <motion.div
          ref={frameRef}
          className="home-hero-text-frame glass"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.62, delay: 0.5, ease: E }}
          style={reduceMotion ? undefined : { backgroundImage: frameGlow }}
        >
          <p className="home-hero-summary">
            AnemiaLens helps a person or clinician check whether a lower-eyelid image is usable,
            review the screening signal with context, and decide the next follow-up step without
            overclaiming what the photo can say.
          </p>

          <div className="home-hero-actions">
            <MagneticButton
              className="btn-primary"
              onClick={() => scrollToId('screening')}
            >
              {/* Micro pulse glow behind button */}
              {!reduceMotion && (
                <motion.span
                  aria-hidden="true"
                  animate={{ scale: [1, 1.15, 1], opacity: [0.3, 0.6, 0.3] }}
                  transition={{ duration: 2.5, repeat: Infinity, ease: 'easeInOut' }}
                  style={{
                    position: 'absolute',
                    inset: -4,
                    borderRadius: 99,
                    background: 'rgba(200,0,30,0.2)',
                    filter: 'blur(12px)',
                    zIndex: -1,
                  }}
                />
              )}
              <ScanEye size={16} />
              Start screening
            </MagneticButton>
            <MagneticButton className="btn-glass" onClick={() => scrollToId('workflow-sequence')}>
              See care workflow
              <ArrowRight size={14} />
            </MagneticButton>
          </div>

          <div className="home-hero-note">
            <ShieldCheck size={15} style={{ color: 'var(--teal)', flexShrink: 0 }} />
            <span>
              Screening support only. Concerning results still need hemoglobin or CBC confirmation.
            </span>
          </div>
        </motion.div>

        {/* ── Support cards ── */}
        <motion.div
          className="home-hero-support"
          style={{ y: supportY }}
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.62, delay: 0.6, ease: E }}
        >
          {HERO_SUPPORT.map(({ icon: Icon, kicker, title, copy }, index) => (
            <motion.div
              key={title}
              className="home-hero-support-card glass"
              whileHover={reduceMotion ? undefined : { y: -3, borderColor: 'rgba(94,234,212,0.15)' }}
              transition={{ duration: 0.2 }}
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <div className="home-hero-support-icon" style={{
                background: 'rgba(94,234,212,0.08)',
                border: '1px solid rgba(94,234,212,0.15)',
              }}>
                <Icon size={16} style={{ color: 'var(--teal)' }} />
              </div>
              <div>
                <div className="home-hero-support-kicker">{kicker}</div>
                <div className="home-hero-support-title">{title}</div>
                <div className="home-hero-support-copy">{copy}</div>
              </div>
            </motion.div>
          ))}
        </motion.div>

        {/* ── Live care sequence / stage board ── */}
        <motion.div
          className="home-hero-stage-board glass"
          style={{ y: stageY }}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.7, ease: E }}
        >
          <div className="home-hero-stage-board-top">
            <div>
              <div className="home-hero-stage-board-label">Live care sequence</div>
              <div className="home-hero-stage-board-title">
                The screening flow stays active before the final result exists.
              </div>
            </div>
            <div className="home-hero-stage-board-status" style={{
              color: 'var(--teal)',
              borderColor: 'rgba(94,234,212,0.2)',
              background: 'rgba(94,234,212,0.05)',
            }}>
              Guided and conservative
            </div>
          </div>

          {/* Stage pills with animated trace line */}
          <div className="home-hero-stage-track">
            {!reduceMotion && (
              <motion.span
                aria-hidden="true"
                className="home-hero-stage-trace"
                animate={{ x: ['-8%', '102%', '-8%'] }}
                transition={{ duration: 10, repeat: Infinity, ease: 'easeInOut' }}
                style={{ background: 'linear-gradient(90deg, transparent, var(--teal), transparent)' }}
              />
            )}
            {HERO_FLOW.map((stage, index) => (
              <motion.button
                key={stage.id}
                type="button"
                className={`home-hero-stage-pill ${index === activeStage ? 'home-hero-stage-pill-active' : ''} ${index < activeStage ? 'home-hero-stage-pill-done' : ''}`}
                onClick={() => setActiveStage(index)}
                whileHover={reduceMotion ? undefined : { y: -2 }}
                whileTap={reduceMotion ? undefined : { scale: 0.995 }}
                transition={{ duration: 0.2 }}
                style={index === activeStage ? {
                  borderColor: 'rgba(94,234,212,0.3)',
                  boxShadow: '0 0 20px rgba(94,234,212,0.08)',
                } : undefined}
              >
                <span className="home-hero-stage-index" style={
                  index === activeStage ? { color: 'var(--teal)' } : undefined
                }>{stage.id}</span>
                <div className="home-hero-stage-copy">
                  <div className="home-hero-stage-label">{stage.label}</div>
                  <div className="home-hero-stage-micro">{stage.micro}</div>
                </div>
              </motion.button>
            ))}
          </div>

          {/* Stage detail card */}
          <AnimatePresence mode="wait">
            <motion.div
              key={activeStageDetail.eyebrow}
              className="home-hero-stage-card-row home-hero-stage-card-row-single"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.38, ease: E }}
            >
              <div className="home-hero-stage-card home-hero-stage-card-wide">
                <div className="home-hero-stage-card-eyebrow" style={{ color: 'var(--teal)' }}>
                  {activeStageDetail.eyebrow}
                </div>
                <div className="home-hero-stage-card-title">{activeStageDetail.title}</div>
                <div className="home-hero-stage-card-detail">{activeStageDetail.detail}</div>
                <div className="home-hero-stage-checklist">
                  {activeStageDetail.checks.map((item) => (
                    <div key={item} className="home-hero-stage-check">
                      <CheckCircle2 size={14} style={{ color: 'var(--teal)' }} />
                      {item}
                    </div>
                  ))}
                </div>
                <div className="home-hero-stage-note-grid">
                  {activeStageDetail.metrics.map((metric, index) => (
                    <div key={metric.label} className="home-hero-stage-note-card">
                      <div className="home-hero-stage-note-head">
                        <span>{metric.label}</span>
                        <span>{metric.value}%</span>
                      </div>
                      <div className="home-hero-stage-note-track">
                        <motion.span
                          className={`home-hero-stage-note-fill ${metric.tone}`}
                          initial={{ width: 0 }}
                          animate={{ width: `${metric.value}%` }}
                          transition={{ duration: 0.75, delay: index * 0.06, ease: E }}
                          style={
                            metric.tone === 'teal'
                              ? { background: 'linear-gradient(90deg, rgba(94,234,212,0.3), rgba(94,234,212,0.6))' }
                              : metric.tone === 'rose'
                              ? { background: 'linear-gradient(90deg, rgba(200,0,30,0.3), rgba(200,0,30,0.6))' }
                              : undefined
                          }
                        />
                      </div>
                    </div>
                  ))}
                </div>
                <div className="home-hero-stage-card-detail home-hero-stage-card-detail-muted">
                  The experience keeps moving, but it stays cautious until the image earns trust.
                </div>
              </div>
            </motion.div>
          </AnimatePresence>
        </motion.div>
      </motion.div>
    </section>
  );
}
