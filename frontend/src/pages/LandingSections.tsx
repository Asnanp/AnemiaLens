import { motion } from 'framer-motion';
import {
  ArrowRight,
  Brain,
  Camera,
  CheckCircle2,
  ClipboardCheck,
  FileText,
  Globe,
  HeartPulse,
  Microscope,
  ScanEye,
  ShieldCheck,
  Stethoscope,
  Users,
} from 'lucide-react';
import { E } from '../components/screening/SharedUI';

const PLATFORM_PILLARS = [
  {
    icon: Camera,
    title: 'Guided capture',
    detail: 'The app shows how to position the eye instead of assuming the user gets it right first try.',
  },
  {
    icon: ShieldCheck,
    title: 'Image check',
    detail: 'Lighting, clarity, and framing are reviewed before the result is trusted.',
  },
  {
    icon: FileText,
    title: 'Saved report',
    detail: 'The result can be emailed, exported, and reopened later from an account.',
  },
] as const;

const CLINICAL_SAFETY_ITEMS = [
  {
    title: 'It explains the call',
    detail: 'The result connects the image, symptoms, and capture quality so it does not feel like a random score.',
  },
  {
    title: 'Trust is shown separately',
    detail: 'A result can lean low risk and still warn that the image was weak or hard to read.',
  },
  {
    title: 'Weak photos lead to safer next steps',
    detail: 'If the image is weak, the app asks for a retake or follow-up instead of pretending certainty.',
  },
] as const;

const PROVIDER_FLOW = [
  {
    title: 'Capture the eyelid image',
    detail: 'The app starts with one guided photo of the inner lower eyelid.',
  },
  {
    title: 'Check whether the image is usable',
    detail: 'Bad lighting, loose framing, or weak eyelid visibility are caught early.',
  },
  {
    title: 'Combine image and symptoms',
    detail: 'Risk, confidence, reliability, and explanation are generated together.',
  },
  {
    title: 'Save or share the result',
    detail: 'The final output can be emailed or reviewed later in the account dashboard.',
  },
] as const;

const TECH_LAYERS = [
  {
    icon: ScanEye,
    title: 'Lower-eyelid image model',
    detail: 'The pipeline focuses on the inner eyelid, checks the crop, and runs the screening model on that region.',
  },
  {
    icon: Brain,
    title: 'Risk and reliability layer',
    detail: 'The backend keeps risk, confidence, and trust level separate instead of collapsing them into one number.',
  },
  {
    icon: Stethoscope,
    title: 'Guidance and reporting',
    detail: 'The result is turned into clear wording, next-step guidance, and a shareable case summary.',
  },
] as const;

const EVIDENCE_POINTS = [
  { value: 'ROI crop', label: 'Focus on the inner eyelid' },
  { value: 'Quality gate', label: 'Flags weak photos before trust rises' },
  { value: 'Guidance', label: 'Plain next-step wording in the result' },
  { value: 'Case history', label: 'Save and reopen past screenings' },
] as const;

export function Challenge() {
  return (
    <section id="platform" className="landing-section landing-band-light section-pad">
      <div className="landing-shell">
        <motion.div
          initial={{ opacity: 0, y: 28 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: E }}
          className="landing-intro"
        >
          <div className="section-eyebrow">How it works</div>
          <h2 className="landing-title">
            A straightforward path
            <span> from photo to next step.</span>
          </h2>
          <p className="landing-summary">
            Open the app, take a photo of the inner lower eyelid, confirm the image is usable,
            and review the result. If you want, you can save it to an account or share it later.
          </p>
        </motion.div>

        <div className="landing-split landing-platform-grid">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, ease: E }}
            className="landing-feature-panel glass"
          >
            <div className="landing-panel-eyebrow">In one session</div>
            <div className="landing-panel-title">What the person actually does</div>
            <p className="landing-panel-copy">
              The flow is simple on purpose. The user is guided through the photo, the image
              review, optional symptoms, and the result without having to understand the model.
            </p>

            <div className="landing-bullet-list">
              <div className="landing-bullet-item">
                <CheckCircle2 size={16} />
                Take one photo of the inner lower eyelid.
              </div>
              <div className="landing-bullet-item">
                <CheckCircle2 size={16} />
                Review lighting and framing before the result appears.
              </div>
              <div className="landing-bullet-item">
                <CheckCircle2 size={16} />
                Add symptoms only if they matter for the case.
              </div>
              <div className="landing-bullet-item">
                <CheckCircle2 size={16} />
                Read the result and decide whether to retake, monitor, or follow up.
              </div>
            </div>
          </motion.div>

          <div className="landing-card-stack">
            {PLATFORM_PILLARS.map((pillar, index) => {
              const Icon = pillar.icon;
              return (
                <motion.div
                  key={pillar.title}
                  initial={{ opacity: 0, x: 20 }}
                  whileInView={{ opacity: 1, x: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.55, delay: index * 0.08, ease: E }}
                  className="landing-capability-card glass"
                >
                  <div className="landing-icon-wrap">
                    <Icon size={18} />
                  </div>
                  <div>
                    <div className="landing-card-title">{pillar.title}</div>
                    <div className="landing-card-detail">{pillar.detail}</div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}

export function DifferentiatorsSection() {
  return (
    <section id="safety" className="landing-section section-pad">
      <div className="landing-shell">
        <div className="landing-split landing-safety-grid">
          <motion.div
            initial={{ opacity: 0, y: 24 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, ease: E }}
            className="landing-safety-copy"
          >
            <div className="section-eyebrow">When the image is weak</div>
            <h2 className="landing-title">
              The app does not pretend
              <span> a weak photo is a strong result.</span>
            </h2>
            <p className="landing-summary">
              That matters more than a big percentage. Reliability is shown separately so a poor
              image does not look more trustworthy than it really is.
            </p>

            <div className="landing-safety-note glass">
              <div className="landing-panel-eyebrow">Why this matters</div>
              <div className="landing-panel-title">A useful result has to be honest</div>
              <p className="landing-panel-copy">
                If the image is poor, the product should say that clearly. That is how you avoid
                false reassurance and make a retake or follow-up feel justified.
              </p>
            </div>
          </motion.div>

          <div className="landing-card-stack">
            {CLINICAL_SAFETY_ITEMS.map((item, index) => (
              <motion.div
                key={item.title}
                initial={{ opacity: 0, y: 18 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.55, delay: index * 0.08, ease: E }}
                className="landing-capability-card glass"
              >
                <div className="landing-icon-wrap landing-icon-calm">
                  <ShieldCheck size={18} />
                </div>
                <div>
                  <div className="landing-card-title">{item.title}</div>
                  <div className="landing-card-detail">{item.detail}</div>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}

export function WorkflowStepper() {
  return (
    <section id="providers" className="landing-section landing-band-light section-pad">
      <div className="landing-shell">
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.7, ease: E }}
          className="landing-intro"
        >
          <div className="section-eyebrow">Review and follow-up</div>
          <h2 className="landing-title">
            Results are easy
            <span> to revisit and share.</span>
          </h2>
          <p className="landing-summary">
            The screening helps more when a patient, clinician, or health worker can come back to
            it later and understand what happened quickly.
          </p>
        </motion.div>

        <div className="landing-split landing-provider-grid">
          <div className="provider-timeline glass">
            {PROVIDER_FLOW.map((item, index) => (
              <div key={item.title} className="provider-timeline-row">
                <div className="provider-timeline-index">{String(index + 1).padStart(2, '0')}</div>
                <div className="provider-timeline-copy">
                  <div className="landing-card-title">{item.title}</div>
                  <div className="landing-card-detail">{item.detail}</div>
                </div>
              </div>
            ))}
          </div>

          <div className="landing-card-stack">
            <div className="landing-feature-panel glass">
              <div className="landing-panel-eyebrow">What can be shared</div>
              <div className="landing-panel-title">What leaves the app</div>
              <div className="landing-bullet-list">
                <div className="landing-bullet-item">
                  <ClipboardCheck size={16} />
                  Risk label, confidence, and trust level
                </div>
                <div className="landing-bullet-item">
                  <HeartPulse size={16} />
                  Short summary of what the model saw
                </div>
                <div className="landing-bullet-item">
                  <FileText size={16} />
                  Email or PDF handoff for follow-up
                </div>
              </div>
            </div>

            <div className="landing-feature-panel glass">
              <div className="landing-panel-eyebrow">For repeat use</div>
              <div className="landing-panel-title">History matters</div>
              <p className="landing-panel-copy">
                Accounts, saved results, and dashboard review make the app easier to use more than
                once instead of behaving like a one-time demo.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}

export function TechSection() {
  return (
    <section id="technology" className="landing-section section-pad">
      <div className="landing-shell">
        <div className="landing-split landing-tech-grid">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.7, ease: E }}
          >
            <div className="section-eyebrow">Under the hood</div>
            <h2 className="landing-title">
              The model sits inside
              <span> a full screening workflow.</span>
            </h2>
            <p className="landing-summary">
              AnemiaLens does more than output one score. It checks image quality, runs the
              screening model, formats the explanation, and stores the case for later review.
            </p>
          </motion.div>

          <div className="landing-card-stack">
            {TECH_LAYERS.map((item, index) => {
              const Icon = item.icon;
              return (
                <motion.div
                  key={item.title}
                  initial={{ opacity: 0, y: 18 }}
                  whileInView={{ opacity: 1, y: 0 }}
                  viewport={{ once: true }}
                  transition={{ duration: 0.55, delay: index * 0.08, ease: E }}
                  className="landing-capability-card glass"
                >
                  <div className="landing-icon-wrap">
                    <Icon size={18} />
                  </div>
                  <div>
                    <div className="landing-card-title">{item.title}</div>
                    <div className="landing-card-detail">{item.detail}</div>
                  </div>
                </motion.div>
              );
            })}
          </div>
        </div>

        <div className="evidence-grid">
          {EVIDENCE_POINTS.map((item) => (
            <div key={item.label} className="evidence-card glass">
              <div className="evidence-value">{item.value}</div>
              <div className="evidence-label">{item.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}

const FOOTER_COLUMNS = [
  {
    title: 'Explore',
    links: [
      { label: 'How it works', href: '#platform' },
      { label: 'When the image is weak', href: '#safety' },
      { label: 'Review and follow-up', href: '#providers' },
    ],
  },
  {
    title: 'Use',
    links: [
      { label: 'Start screening', href: '#screening' },
      { label: 'Under the hood', href: '#technology' },
      { label: 'Create account', href: '#screening' },
    ],
  },
] as const;

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
            Built to make first-pass anemia screening easier to understand, easier to repeat, and
            easier to share.
          </p>
          <div className="footer-badges">
            <span className="footer-chip">
              <Globe size={13} />
              Guest access
            </span>
            <span className="footer-chip">
              <Microscope size={13} />
              Email and PDF reports
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
