import { motion } from 'framer-motion';
import {
  ArrowRight,
  CheckCircle2,
  Mail,
  ScanEye,
  ShieldCheck,
  Stethoscope,
} from 'lucide-react';

import { E } from '../components/screening/SharedUI';

const HERO_PROOF = [
  {
    title: 'Checks the image first',
    detail: 'Lighting, blur, and eyelid visibility are reviewed before a result is shown.',
    icon: ShieldCheck,
  },
  {
    title: 'Shows what affected the result',
    detail: 'Risk, reliability, and the reason for the call appear together.',
    icon: Stethoscope,
  },
  {
    title: 'Easy to share later',
    detail: 'Email and PDF summaries help with follow-up after screening.',
    icon: Mail,
  },
] as const;

const HERO_METRICS = [
  { value: '1 photo', label: 'Inner lower eyelid' },
  { value: '4 steps', label: 'Capture to result' },
  { value: 'Email + PDF', label: 'Simple handoff' },
] as const;

const HERO_FLOW = [
  {
    step: '01',
    title: 'Take one photo',
    detail: 'Capture the inner lower eyelid with the in-app guide.',
    accent: 'capture',
  },
  {
    step: '02',
    title: 'Check whether it is usable',
    detail: 'The app reviews lighting, framing, and visible detail before moving on.',
    accent: 'review',
  },
  {
    step: '03',
    title: 'Add symptoms if needed',
    detail: 'Fatigue, dizziness, or pale skin can be added as extra context.',
    accent: 'capture',
  },
  {
    step: '04',
    title: 'Read the result',
    detail: 'The result shows risk, reliability, and the next suggested step.',
    accent: 'result',
  },
] as const;

const CARE_PANELS = [
  {
    eyebrow: 'Patient',
    title: 'Plain-language result',
    detail: 'The person sees a simple summary and whether they should retake, monitor, or follow up.',
  },
  {
    eyebrow: 'Clinician',
    title: 'Short case summary',
    detail: 'A provider gets the image story, symptom context, and a report that is easy to review.',
  },
] as const;

export function Hero() {
  const scrollTo = (id: string) => {
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth' });
  };

  return (
    <section className="hero-premium-shell section-hero">
      <div className="hero-premium-grid">
        <motion.div
          className="hero-copy-column"
          initial={{ opacity: 0, y: 28 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.75, ease: E }}
        >
          <div className="hero-eyebrow-chip">
            <span className="hero-eyebrow-dot" />
            Smartphone anemia screening
          </div>

          <div className="hero-copy-stack">
            <h1 className="hero-premium-title">
              Screen anemia from
              <span> a single eyelid photo.</span>
            </h1>
            <p className="hero-premium-summary">
              Take a photo of the inner lower eyelid. AnemiaLens checks whether the image is
              usable, estimates anemia risk, and shows a clear next step. If the photo is weak,
              it says so.
            </p>
          </div>

          <div className="hero-premium-actions">
            <button className="btn btn-primary" onClick={() => scrollTo('screening')}>
              <ScanEye size={16} />
              Start screening
            </button>
            <button className="btn btn-glass" onClick={() => scrollTo('platform')}>
              See how it works
              <ArrowRight size={14} />
            </button>
          </div>

          <div className="hero-proof-strip">
            {HERO_PROOF.map((item) => {
              const Icon = item.icon;
              return (
                <div key={item.title} className="hero-proof-item">
                  <div className="hero-proof-icon">
                    <Icon size={15} />
                  </div>
                  <div>
                    <div className="hero-proof-title">{item.title}</div>
                    <div className="hero-proof-detail">{item.detail}</div>
                  </div>
                </div>
              );
            })}
          </div>

          <div className="hero-metric-strip">
            {HERO_METRICS.map((item) => (
              <div key={item.label} className="hero-metric-card">
                <div className="hero-metric-value">{item.value}</div>
                <div className="hero-metric-label">{item.label}</div>
              </div>
            ))}
          </div>
        </motion.div>

        <motion.div
          className="hero-product-column"
          initial={{ opacity: 0, y: 36 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.9, delay: 0.1, ease: E }}
        >
          <div className="hero-product-frame glass">
            <div className="hero-product-topbar">
              <div>
                <div className="hero-product-label">Example screening</div>
                <div className="hero-product-heading">What the app shows</div>
              </div>
              <div className="hero-product-status">
                <span className="nav-status-dot" />
                Preview
              </div>
            </div>

            <div className="hero-product-story">
              <div className="hero-product-story-copy">
                <div className="hero-product-stage-title">From photo to follow-up</div>
                <div className="hero-product-stage-text">
                  The image is checked first. Then the result is shown with risk, reliability,
                  and a short explanation that can be shared later.
                </div>
              </div>
              <div className="hero-product-badge">
                <ShieldCheck size={16} />
                Image checked first
              </div>
            </div>

            <div className="hero-workflow-stack">
              {HERO_FLOW.map((item) => (
                <div key={item.step} className={`hero-workflow-card hero-workflow-${item.accent}`}>
                  <div className="hero-workflow-step">{item.step}</div>
                  <div>
                    <div className="hero-workflow-title">{item.title}</div>
                    <div className="hero-workflow-detail">{item.detail}</div>
                  </div>
                  <CheckCircle2 size={16} className="hero-workflow-check" />
                </div>
              ))}
            </div>

            <div className="hero-care-grid">
              {CARE_PANELS.map((panel) => (
                <div key={panel.eyebrow} className="hero-care-card">
                  <div className="hero-care-eyebrow">{panel.eyebrow}</div>
                  <div className="hero-care-title">{panel.title}</div>
                  <div className="hero-care-detail">{panel.detail}</div>
                </div>
              ))}
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
}
