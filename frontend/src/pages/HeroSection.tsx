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
import { useRef, useState } from 'react';

import { E } from '../components/screening/SharedUI';
import { scrollToId } from '../utils/scroll';

const HERO_METRICS = [
  { value: '1', eyebrow: 'Capture', label: 'guided lower-eyelid frame', signal: 0.94 },
  { value: '4', eyebrow: 'Flow', label: 'capture, quality, intake, result', signal: 0.82 },
  { value: 'Care', eyebrow: 'Output', label: 'risk, trust, and next step together', signal: 0.9 },
] as const;

const HERO_SIGNALS = [
  { icon: ShieldCheck, label: 'Quality gate before inference' },
  { icon: Activity, label: 'Trust stays visible beside risk' },
  { icon: Sparkles, label: 'Care-ready summary output' },
] as const;

const HERO_SUPPORT = [
  {
    icon: ShieldCheck,
    kicker: 'Safety layer',
    title: 'Weak captures are stopped early',
    copy: 'The experience checks framing, blur, and lighting before the model is allowed to speak loudly.',
  },
  {
    icon: Activity,
    kicker: 'Decision layer',
    title: 'Image signal stays grounded in context',
    copy: 'Symptoms and patient details support the triage story after the image clears the trust gate.',
  },
  {
    icon: FileText,
    kicker: 'Follow-up layer',
    title: 'The result is built to survive after the screen',
    copy: 'Risk, reliability, and handoff guidance stay together for the person, family, or clinician.',
  },
] as const;

const HERO_FLOW = [
  { id: '01', label: 'Capture', micro: 'Guide one eyelid image' },
  { id: '02', label: 'Quality', micro: 'Check whether it is usable' },
  { id: '03', label: 'Intake', micro: 'Merge context carefully' },
  { id: '04', label: 'Result', micro: 'Keep trust and next step together' },
] as const;

const HERO_STAGE_DETAILS = [
  {
    eyebrow: 'Capture live',
    title: 'Guide the lower inner eyelid before scoring starts',
    detail: 'The first step watches framing and light before the image is allowed into the screening flow.',
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
    detail: 'Blur, glare, and eyelid visibility are checked before the model is trusted with the image signal.',
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
    detail: 'Symptoms and patient details support the triage story after the image has already earned basic trust.',
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
    detail: 'The final surface keeps the screening signal, confidence story, and follow-up guidance in one calm place.',
    checks: ['Risk shown beside trust', 'Guidance remains cautious', 'Share-ready handoff preserved'],
    metrics: [
      { label: 'Signal clarity', value: 83, tone: 'rose' },
      { label: 'Guidance fit', value: 92, tone: 'teal' },
      { label: 'Handoff ready', value: 87, tone: 'violet' },
    ],
  },
] as const;

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
  const pointerXSpring = useSpring(pointerX, { stiffness: 120, damping: 18, mass: 0.8 });
  const pointerYSpring = useSpring(pointerY, { stiffness: 120, damping: 18, mass: 0.8 });

  const shellY = useTransform(scrollYProgress, [0, 1], [0, reduceMotion ? 0 : 74]);
  const shellOpacity = useTransform(scrollYProgress, [0, 0.88], [1, reduceMotion ? 1 : 0.78]);
  const shellScale = useTransform(scrollYProgress, [0, 1], [1, reduceMotion ? 1 : 0.985]);
  const metricsY = useTransform(scrollYProgress, [0, 1], [0, reduceMotion ? 0 : 30]);
  const supportY = useTransform(scrollYProgress, [0, 1], [0, reduceMotion ? 0 : 42]);
  const stageY = useTransform(scrollYProgress, [0, 1], [0, reduceMotion ? 0 : 54]);
  const activeStageDetail = HERO_STAGE_DETAILS[activeStage];

  const frameGlow = useMotionTemplate`
    radial-gradient(circle at ${pointerXSpring}% ${pointerYSpring}%, rgba(243, 166, 179, 0.14), transparent 44%),
    linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.012))
  `;

  const handlePointerMove = (event: ReactPointerEvent<HTMLElement>) => {
    const target = frameRef.current ?? sectionRef.current;
    if (reduceMotion || !target) return;
    const bounds = target.getBoundingClientRect();
    const nextX = ((event.clientX - bounds.left) / Math.max(bounds.width, 1)) * 100;
    const nextY = ((event.clientY - bounds.top) / Math.max(bounds.height, 1)) * 100;
    pointerX.set(Math.min(100, Math.max(0, nextX)));
    pointerY.set(Math.min(100, Math.max(0, nextY)));
  };

  const handlePointerLeave = () => {
    if (reduceMotion) return;
    pointerX.set(50);
    pointerY.set(38);
  };

  return (
    <section
      ref={sectionRef}
      className="home-hero section-hero"
      onPointerMove={handlePointerMove}
      onPointerLeave={handlePointerLeave}
    >
      <motion.div
        aria-hidden="true"
        className="home-hero-aura home-hero-aura-primary"
        animate={reduceMotion ? undefined : { scale: [1, 1.05, 1], opacity: [0.56, 0.78, 0.56] }}
        transition={reduceMotion ? undefined : { duration: 12, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        aria-hidden="true"
        className="home-hero-aura home-hero-aura-secondary"
        animate={reduceMotion ? undefined : { x: [0, 28, 0], y: [0, -22, 0], opacity: [0.22, 0.42, 0.22] }}
        transition={reduceMotion ? undefined : { duration: 16, repeat: Infinity, ease: 'easeInOut' }}
      />
      <motion.div
        aria-hidden="true"
        className="home-hero-aura home-hero-aura-tertiary"
        animate={reduceMotion ? undefined : { x: [0, -18, 0], y: [0, 16, 0], opacity: [0.18, 0.34, 0.18] }}
        transition={reduceMotion ? undefined : { duration: 13, repeat: Infinity, ease: 'easeInOut' }}
      />

      <motion.div
        className="home-hero-shell"
        style={{ y: shellY, opacity: shellOpacity, scale: shellScale }}
        initial={{ opacity: 0, y: 28 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.85, ease: E }}
      >
        <motion.div
          className="hero-eyebrow-chip"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.55, delay: 0.04, ease: E }}
        >
          <span className="hero-eyebrow-dot" />
          Smartphone screening support
        </motion.div>

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
              whileHover={reduceMotion ? undefined : { y: -2 }}
              transition={{ duration: 0.45, delay: 0.12 + index * 0.08, ease: E }}
            >
              <Icon size={13} />
              <span>{label}</span>
            </motion.div>
          ))}
        </motion.div>

        <motion.h1
          className="home-hero-title"
          initial={{ opacity: 0, y: 26 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.1, ease: E }}
        >
          Safer anemia screening
          <br />
          from one guided
          <br />
          <span>lower-eyelid image.</span>
        </motion.h1>

        <motion.div
          ref={frameRef}
          className="home-hero-text-frame glass"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.62, delay: 0.18, ease: E }}
          style={reduceMotion ? undefined : { backgroundImage: frameGlow }}
        >
          <p className="home-hero-summary">
            AnemiaLens helps a person or clinician check whether a lower-eyelid image is usable,
            review the screening signal with context, and decide the next follow-up step without
            overclaiming what the photo can say.
          </p>

          <div className="home-hero-actions">
            <button className="btn btn-primary" onClick={() => scrollToId('screening')}>
              <ScanEye size={16} />
              Start screening
            </button>
            <button className="btn btn-glass" onClick={() => scrollToId('workflow-sequence')}>
              See care workflow
              <ArrowRight size={14} />
            </button>
          </div>

          <div className="home-hero-note">
            <ShieldCheck size={15} />
            <span>
              Screening support only. Concerning results still need hemoglobin or CBC confirmation.
            </span>
          </div>
        </motion.div>

        <motion.div
          className="home-hero-metrics"
          style={{ y: metricsY }}
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, delay: 0.42, ease: E }}
        >
          {HERO_METRICS.map((metric, index) => (
            <motion.div
              key={metric.eyebrow}
              className="home-hero-metric-card glass"
              whileHover={reduceMotion ? undefined : { y: -4, scale: 1.01 }}
              transition={{ duration: 0.2 }}
            >
              <div className="home-hero-metric-value">{metric.value}</div>
              <div className="home-hero-metric-copy">
                <div className="home-hero-metric-eyebrow">{metric.eyebrow}</div>
                <div className="home-hero-metric-label">{metric.label}</div>
                <div className="home-hero-metric-bar">
                  <motion.span
                    className="home-hero-metric-bar-fill"
                    initial={{ scaleX: 0 }}
                    animate={{ scaleX: metric.signal }}
                    transition={{ duration: 0.85, delay: 0.55 + index * 0.1, ease: E }}
                  />
                </div>
              </div>
            </motion.div>
          ))}
        </motion.div>

        <motion.div
          className="home-hero-support"
          style={{ y: supportY }}
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.62, delay: 0.5, ease: E }}
        >
          {HERO_SUPPORT.map(({ icon: Icon, kicker, title, copy }, index) => (
            <motion.div
              key={title}
              className="home-hero-support-card glass"
              whileHover={reduceMotion ? undefined : { y: -3 }}
              transition={{ duration: 0.2 }}
              initial={{ opacity: 0, y: 18 }}
              animate={{ opacity: 1, y: 0 }}
              style={reduceMotion ? undefined : { animationDelay: `${index * 1.6}s` }}
            >
              <div className="home-hero-support-icon">
                <Icon size={16} />
              </div>
              <div>
                <div className="home-hero-support-kicker">{kicker}</div>
                <div className="home-hero-support-title">{title}</div>
                <div className="home-hero-support-copy">{copy}</div>
              </div>
            </motion.div>
          ))}
        </motion.div>

        <motion.div
          className="home-hero-stage-board glass"
          style={{ y: stageY }}
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.7, delay: 0.58, ease: E }}
        >
          <div className="home-hero-stage-board-top">
            <div>
              <div className="home-hero-stage-board-label">Live care sequence</div>
              <div className="home-hero-stage-board-title">The screening flow stays active before the final result exists.</div>
            </div>
            <div className="home-hero-stage-board-status">Guided and conservative</div>
          </div>

          <div className="home-hero-stage-track">
            {!reduceMotion && (
              <motion.span
                aria-hidden="true"
                className="home-hero-stage-trace"
                animate={{ x: ['-8%', '102%', '-8%'] }}
                transition={{ duration: 8.6, repeat: Infinity, ease: 'easeInOut' }}
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
              >
                <span className="home-hero-stage-index">{stage.id}</span>
                <div className="home-hero-stage-copy">
                  <div className="home-hero-stage-label">{stage.label}</div>
                  <div className="home-hero-stage-micro">{stage.micro}</div>
                </div>
              </motion.button>
            ))}
          </div>

          <AnimatePresence mode="wait">
            <motion.div
              key={activeStageDetail.eyebrow}
              className="home-hero-stage-card-row"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -12 }}
              transition={{ duration: 0.38, ease: E }}
            >
              <div className="home-hero-stage-card">
                <div className="home-hero-stage-card-eyebrow">{activeStageDetail.eyebrow}</div>
                <div className="home-hero-stage-card-title">{activeStageDetail.title}</div>
                <div className="home-hero-stage-card-detail">{activeStageDetail.detail}</div>
                <div className="home-hero-stage-checklist">
                  {activeStageDetail.checks.map((item) => (
                    <div key={item} className="home-hero-stage-check">
                      <CheckCircle2 size={14} />
                      {item}
                    </div>
                  ))}
                </div>
              </div>

              <div className="home-hero-stage-card home-hero-stage-card-metrics">
                <div className="home-hero-stage-card-eyebrow">Live metrics</div>
                <div className="home-hero-stage-meter-grid">
                  {activeStageDetail.metrics.map((metric, index) => (
                    <div key={metric.label} className="home-hero-stage-meter">
                      <div className="home-hero-stage-meter-head">
                        <span>{metric.label}</span>
                        <span>{metric.value}%</span>
                      </div>
                      <div className="home-hero-stage-meter-track">
                        <motion.span
                          className={`home-hero-stage-meter-fill ${metric.tone}`}
                          initial={{ width: 0 }}
                          animate={{ width: `${metric.value}%` }}
                          transition={{ duration: 0.75, delay: index * 0.06, ease: E }}
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
