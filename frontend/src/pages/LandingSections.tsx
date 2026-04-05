import { AnimatePresence, motion } from 'framer-motion';
import {
  Activity,
  ArrowRight,
  CheckCircle2,
  FileText,
  Globe,
  Microscope,
  ScanEye,
  ShieldCheck,
  Users,
} from 'lucide-react';
import { useState } from 'react';

import { E, GlassCard } from '../components/screening/SharedUI';
import { scrollToId } from '../utils/scroll';
import { MagneticButton } from '../components/MagneticButton';

const WORKFLOW_STEPS = [
  {
    id: '01',
    label: 'Capture',
    micro: 'Frame one clear eyelid image',
    title: 'Guide the lower inner eyelid',
    detail: 'The person is asked for one clear lower-eyelid image in bright indirect light.',
    checksLabel: 'Capture setup',
    checks: [
      'Bright, indirect natural daylight',
      'No flash or harsh shadows',
      'Lower eyelid fully exposed',
      'One eye centered in frame',
    ],
    pulse: 'Image framing and exposure are being watched before the image is accepted.',
    paceLabel: 'Capture tempo',
    paceValue: 'Slow enough to frame once',
  },
  {
    id: '02',
    label: 'Quality',
    micro: 'Check whether the image is usable',
    title: 'Check whether the image is usable',
    detail: 'Lighting, blur, framing, and eyelid visibility are reviewed before the model is trusted.',
    checksLabel: 'Quality gate',
    checks: [
      'Blur, glare, and shadows are screened before inference.',
      'Weak captures are stopped early instead of dressed up as confident results.',
      'Trust stays visible beside the signal so the person sees how repeatable the image was.',
    ],
    pulse: 'This is the safety gate that keeps a weak image from turning into a loud claim.',
    paceLabel: 'Gate posture',
    paceValue: 'Retake before overclaiming',
  },
  {
    id: '03',
    label: 'Intake',
    micro: 'Add patient context carefully',
    title: 'Add symptom and patient context',
    detail: 'Symptoms and patient details can adjust the final triage instead of relying on the image alone.',
    checksLabel: 'Context merge',
    checks: [
      'Symptoms are layered in only after the image clears the gate.',
      'The person is not asked for unnecessary detail when the image already needs a retake.',
      'Context is used to support triage, not to override a weak image.',
    ],
    pulse: 'The image signal and the case context become one story instead of two separate guesses.',
    paceLabel: 'Context role',
    paceValue: 'Image first, context second',
  },
  {
    id: '04',
    label: 'Result',
    micro: 'Keep trust and next step together',
    title: 'Show risk, trust, and next step together',
    detail: 'The result stays grounded in what the scan can support and what follow-up should happen next.',
    checksLabel: 'Care handoff',
    checks: [
      'Risk, trust, and next-step guidance are shown in the same place.',
      'Share-ready output survives beyond the first screen for clinician follow-up.',
      'A weak result stays cautious instead of pretending to be final.',
    ],
    pulse: 'The result should feel like a care summary, not a flashy verdict.',
    paceLabel: 'Care outcome',
    paceValue: 'Guidance tied to trust',
  },
] as const;

const WORKFLOW_VISUALS = [
  {
    icon: ScanEye,
    eyebrow: 'Capture feed',
    title: 'Frame one clean lower-eyelid image',
    detail: 'The capture stage is about alignment, calm lighting, and getting the lower inner eyelid fully visible before anything else happens.',
    status: 'Capture quality watched live',
    tone: 'rose',
    chips: ['Image guidance', 'Indirect daylight', 'One calm frame'],
    cards: [
      {
        label: 'Frame lock',
        value: 'Lower eyelid centered',
        detail: 'The person only needs one clear, well-placed image.',
      },
      {
        label: 'Lighting',
        value: 'Balanced natural light',
        detail: 'No flash or harsh shadow should compete with the tissue color.',
      },
      {
        label: 'Retake rule',
        value: 'Retry if the eyelid is clipped',
        detail: 'The flow pauses early when the image does not show enough of the inner eyelid.',
      },
    ],
    support: [
      {
        label: 'Why this matters',
        value: 'A calm, well-framed first image reduces unnecessary retakes and keeps the screening conservative from the start.',
      },
      {
        label: 'Next step',
        value: 'Once the image is framed well, the system moves into image review before any risk story is shown.',
      },
    ],
  },
  {
    icon: ShieldCheck,
    eyebrow: 'Quality review',
    title: 'Gate weak images before the model speaks',
    detail: 'Blur, glare, and framing are checked first so a weak image does not produce a confident-looking result.',
    status: 'Lighting and visibility checks active',
    tone: 'teal',
    chips: ['Blur check', 'Glare screen', 'ROI visible'],
    cards: [
      {
        label: 'Image review',
        value: 'Weak captures stop here',
        detail: 'Low-trust images are held back instead of being dressed up as confident results.',
      },
      {
        label: 'Trust signal',
        value: 'Reliability stays visible',
        detail: 'The person sees whether the image was repeatable before the triage story becomes loud.',
      },
      {
        label: 'Retake guidance',
        value: 'Retry before overclaiming',
        detail: 'The system keeps a cautious posture when the capture quality is uncertain.',
      },
    ],
    support: [
      {
        label: 'Why this matters',
        value: 'Healthcare screening should stop weak evidence early rather than letting a weak image look medically certain.',
      },
      {
        label: 'Next step',
        value: 'Once trust is acceptable, symptoms and case context can support the screening call.',
      },
    ],
  },
  {
    icon: Users,
    eyebrow: 'Intake merge',
    title: 'Add case context before final triage',
    detail: 'Symptoms and patient context are merged only after the image clears the gate, so the screening story stays structured.',
    status: 'Context layer is now contributing',
    tone: 'violet',
    chips: ['Symptoms optional', 'Image stays primary', 'Case context logged'],
    cards: [
      {
        label: 'Patient context',
        value: 'Symptoms support the read',
        detail: 'Fatigue, dizziness, or low iron intake can shape follow-up without replacing the image signal.',
      },
      {
        label: 'Decision balance',
        value: 'Image first, context second',
        detail: 'The flow avoids asking for extra detail when the image itself still needs a retake.',
      },
      {
        label: 'Audit trail',
        value: 'Reasoning stays traceable',
        detail: 'The final triage story keeps the image and patient context tied together in one record.',
      },
    ],
    support: [
      {
        label: 'Why this matters',
        value: 'A care summary is more useful when it respects both the image signal and what the person is actually feeling.',
      },
      {
        label: 'Next step',
        value: 'After context is merged, the system can show risk, trust, and follow-up together on one result surface.',
      },
    ],
  },
  {
    icon: FileText,
    eyebrow: 'Result surface',
    title: 'Keep risk, trust, and next step together',
    detail: 'The final screen should feel like a care summary, with the follow-up guidance visible beside the screening signal.',
    status: 'Summary and follow-up prepared',
    tone: 'amber',
    chips: ['Risk band', 'Trust level', 'Next step'],
    cards: [
      {
        label: 'Care summary',
        value: 'Risk and trust stay together',
        detail: 'The result does not separate the signal from the confidence story.',
      },
      {
        label: 'Follow-up',
        value: 'A clear next action appears',
        detail: 'Retake, monitor, or seek blood testing are shown in plain language beside the screening result.',
      },
      {
        label: 'Share-ready',
        value: 'The summary can travel',
        detail: 'Email, PDF, and saved history keep the result useful after the first screen.',
      },
    ],
    support: [
      {
        label: 'Why this matters',
        value: 'A useful screening result is calm, honest, and connected to the next real-world follow-up action.',
      },
      {
        label: 'Next step',
        value: 'The person can rescreen, save the result, or bring the summary into a clinician conversation.',
      },
    ],
  },
] as const;

const FOOTER_COLUMNS = [
  {
    title: 'Explore',
    links: [
      { label: 'How it works', href: '/how-it-works' },
      { label: 'Science', href: '/science' },
      { label: 'FAQ', href: '/faq' },
    ],
  },
  {
    title: 'Use',
    links: [
      { label: 'Start screening', href: '#screening' },
      { label: 'For providers', href: '/providers' },
      { label: 'Create account', href: '#screening' },
    ],
  },
] as const;

export function Challenge() {
  return null;
}

export function DifferentiatorsSection() {
  return null;
}

export function WorkflowStepper() {
  const [activeIndex, setActiveIndex] = useState(0);
  const activeStep = WORKFLOW_STEPS[activeIndex];
  const activeVisual = WORKFLOW_VISUALS[activeIndex];
  const ActiveIcon = activeVisual.icon;
  const progressPct = `${((activeIndex + 1) / WORKFLOW_STEPS.length) * 100}%`;

  return (
    <section id="workflow-sequence" className="workflow-sequence-section workflow-static-section">
      <div className="landing-shell workflow-static-shell">
        <motion.div
          className="workflow-static-header"
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.8, ease: E }}
        >
          <div className="workflow-static-intro">
            <div className="section-eyebrow">Care workflow</div>
            <h2 className="workflow-static-title">A calmer screening flow with room to understand each step.</h2>
            <p className="workflow-static-summary">
              The experience stays structured instead of flashy: capture one usable image, confirm
              the image deserves trust, add patient context only when it helps, then show the next
              care step in plain language.
            </p>
          </div>
        </motion.div>

        <div className="workflow-static-grid">
          <motion.div
            className="workflow-static-preview glass"
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.25 }}
            transition={{ duration: 0.65, ease: E }}
          >
            <AnimatePresence mode="wait" initial={false}>
              <motion.div
                key={activeStep.id}
                className="workflow-static-preview-stack"
                initial={{ opacity: 0, y: 18 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -12 }}
                transition={{ duration: 0.32, ease: E }}
              >
                <div className="workflow-static-preview-top">
                  <div>
                    <div className="workflow-static-preview-eyebrow">Current step</div>
                    <h3 className="workflow-static-preview-title">{activeStep.label}</h3>
                    <p className="workflow-static-preview-copy">{activeStep.micro}</p>
                  </div>
                  <div className="workflow-static-preview-badge">{activeStep.id} / 04</div>
                </div>

                <div className="workflow-static-preview-stage-row">
                  {WORKFLOW_STEPS.map((step, index) => (
                    <button
                      key={step.id}
                      type="button"
                      className={`workflow-static-preview-stage ${index === activeIndex ? 'active' : ''} ${index < activeIndex ? 'done' : ''}`}
                      onClick={() => setActiveIndex(index)}
                      aria-pressed={index === activeIndex}
                    >
                      <span>{step.id}</span>
                      <div>{step.label}</div>
                    </button>
                  ))}
                </div>

                <div className="workflow-static-preview-surface">
                  <div className="workflow-static-preview-surface-top">
                    <span className="workflow-static-preview-surface-chip">{activeVisual.eyebrow}</span>
                    <span className="workflow-static-preview-surface-chip workflow-static-preview-surface-chip-muted">
                      {activeVisual.status}
                    </span>
                  </div>

                  <div className={`workflow-static-preview-surface-shell workflow-static-preview-surface-shell-${activeVisual.tone}`}>
                    <div className="workflow-static-preview-surface-core">
                      <div className={`workflow-static-preview-surface-orb workflow-static-preview-surface-orb-${activeVisual.tone}`}>
                        <ActiveIcon size={24} />
                      </div>
                      <div className="workflow-static-preview-surface-copy">
                        <div className="workflow-static-preview-surface-title">{activeVisual.title}</div>
                        <div className="workflow-static-preview-surface-text">{activeVisual.detail}</div>
                      </div>
                    </div>

                    <div className="workflow-static-preview-signal-strip">
                      {activeVisual.chips.map((chip) => (
                        <div key={chip} className="workflow-static-preview-signal-chip">
                          {chip}
                        </div>
                      ))}
                    </div>

                    <div className="workflow-static-preview-card-grid">
                      {activeVisual.cards.map((card, cardIndex) => (
                        <GlassCard key={card.label} className="workflow-static-preview-card">
                          <motion.div
                            initial={{ opacity: 0, y: 10 }}
                            animate={{ opacity: 1, y: 0 }}
                            transition={{ duration: 0.28, delay: cardIndex * 0.05, ease: E }}
                          >
                            <div className="workflow-static-preview-card-label">{card.label}</div>
                            <div className="workflow-static-preview-card-value">{card.value}</div>
                            <div className="workflow-static-preview-card-detail">{card.detail}</div>
                          </motion.div>
                        </GlassCard>
                      ))}
                    </div>

                    <div className="workflow-static-preview-support-row">
                      {activeVisual.support.map((item) => (
                        <div key={item.label} className="workflow-static-preview-support-card">
                          <div className="workflow-static-preview-support-label">{item.label}</div>
                          <div className="workflow-static-preview-support-value">{item.value}</div>
                        </div>
                      ))}
                    </div>

                    <div className="workflow-static-preview-surface-rail">
                      <motion.span
                        key={activeStep.id}
                        className="workflow-static-preview-surface-rail-fill"
                        initial={{ width: 0 }}
                        animate={{ width: progressPct }}
                        transition={{ duration: 0.45, ease: E }}
                      />
                    </div>
                  </div>
                </div>

                <div className="workflow-static-preview-meta">
                  <div className="workflow-static-preview-meta-card">
                    <span className="workflow-static-preview-meta-label">Step focus</span>
                    <span className="workflow-static-preview-meta-value">{activeVisual.status}</span>
                  </div>
                  <div className="workflow-static-preview-meta-card">
                    <span className="workflow-static-preview-meta-label">Care posture</span>
                    <span className="workflow-static-preview-meta-value">{activeStep.paceValue}</span>
                  </div>
                </div>

                <div className="workflow-static-preview-note">
                  <ShieldCheck size={16} />
                  <div>{activeStep.pulse}</div>
                </div>
              </motion.div>
            </AnimatePresence>

          </motion.div>

          <div className="workflow-static-steps-panel">
            <div className="workflow-static-steps">
            {WORKFLOW_STEPS.map((step, index) => {
              const isActive = index === activeIndex;
              return (
                <motion.button
                  key={step.id}
                  type="button"
                  className={`workflow-static-step ${isActive ? 'workflow-static-step-active' : ''}`}
                  onClick={() => setActiveIndex(index)}
                  whileHover={{ y: -3 }}
                  whileTap={{ scale: 0.995 }}
                  transition={{ duration: 0.18, ease: E }}
                  aria-pressed={isActive}
                >
                  <div className="workflow-static-step-head">
                    <div className="workflow-static-step-kicker">
                      <span className="workflow-static-step-index">{step.id}</span>
                      <span className="workflow-static-step-label">{step.label}</span>
                    </div>
                    <span className="workflow-static-step-state">{isActive ? 'Current step' : 'View step'}</span>
                  </div>

                  <div className="workflow-static-step-title">{step.title}</div>
                  <div className="workflow-static-step-copy">{step.micro}</div>

                  <AnimatePresence initial={false}>
                    {isActive ? (
                      <motion.div
                        className="workflow-static-step-body"
                        initial={{ opacity: 0, height: 0, y: 8 }}
                        animate={{ opacity: 1, height: 'auto', y: 0 }}
                        exit={{ opacity: 0, height: 0, y: -8 }}
                        transition={{ duration: 0.28, ease: E }}
                      >
                        <div className="workflow-static-step-checklist">
                          {step.checks.map((item) => (
                            <div key={item} className="workflow-static-step-check">
                              <CheckCircle2 size={15} />
                              {item}
                            </div>
                          ))}
                        </div>

                        <div className="workflow-static-step-foot">
                          <div className="workflow-static-step-foot-card">
                            <span className="workflow-static-step-foot-label">Care note</span>
                            <span className="workflow-static-step-foot-value">{step.pulse}</span>
                          </div>
                          <div className="workflow-static-step-foot-card">
                            <span className="workflow-static-step-foot-label">{step.paceLabel}</span>
                            <span className="workflow-static-step-foot-value">{step.paceValue}</span>
                          </div>
                        </div>
                      </motion.div>
                    ) : null}
                  </AnimatePresence>
                </motion.button>
              );
            })}
            </div>

            <MagneticButton
              className="btn-primary workflow-static-primary-button"
              onClick={() => scrollToId('screening')}
              style={{ padding: '0.8rem 1.4rem' }}
            >
              <ScanEye size={16} />
              Start screening
            </MagneticButton>
          </div>
        </div>
      </div>
    </section>
  );
}

export function TechSection() {
  return null;
}

export function Footer() {
  return (
    <footer className="footer-premium-shell">
      <div className="footer-premium-grid">
        <div className="footer-brand-column">
          <div className="footer-brand">
            <div className="footer-brand-mark">AL</div>
            <div>
              <div className="footer-brand-title">
                Anemia<span>Lens</span>
              </div>
              <div className="footer-brand-subtitle">Smartphone-based anemia screening</div>
            </div>
          </div>
          <p className="footer-copy">
            A smartphone-first screening flow built to check image quality, show risk carefully, and
            support the next clinical step.
          </p>
          <div className="footer-badges">
            <span className="footer-chip">
              <Globe size={13} />
              Guest access
            </span>
            <span className="footer-chip">
              <Microscope size={13} />
              PDF and email handoff
            </span>
            <span className="footer-chip">
              <Users size={13} />
              Saved history
            </span>
          </div>
        </div>

        <div className="footer-links-grid">
          {FOOTER_COLUMNS.map((column) => (
            <div key={column.title}>
              <div className="footer-column-title">{column.title}</div>
              <div className="footer-link-list">
                {column.links.map((link) => (
                  <a key={link.label} href={link.href} className="footer-link">
                    {link.label}
                    <ArrowRight size={12} />
                  </a>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="footer-bottom-bar">
        <div className="footer-meta">(c) 2026 AnemiaLens. Screening support, not diagnosis.</div>
        <div className="footer-disclaimer">
          Confirm concerning results with clinical blood testing and clinician review.
        </div>
      </div>
    </footer>
  );
}
