import { useState, useMemo } from 'react';
import { motion, AnimatePresence, useReducedMotion } from 'framer-motion';
import { Search, ShieldCheck, Activity, FileText, Lock, Smartphone, HelpCircle } from 'lucide-react';
import { ActionRow, FaqList, PageSurface, SectionBlock, CardGrid, FeatureCard } from '../components/site/RoutePage';

const E = [0.22, 1, 0.36, 1] as const;

const FAQ_CATEGORIES = [
  {
    id: 'general',
    icon: HelpCircle,
    label: 'General',
    eyebrow: 'General',
    title: 'What the workflow is meant to do.',
    intro: 'These answers focus on how the product should be understood by a patient, clinician, or reviewer.',
    faqs: [
      {
        question: 'What is AnemiaLens actually meant to do?',
        answer:
          'It is a first-pass smartphone screening workflow. The product reviews whether a lower-eyelid image is usable, combines that image signal with optional symptom context, and returns a cautious next-step summary.',
      },
      {
        question: 'Does it diagnose anemia from a photo?',
        answer:
          'No. It is a screening aid only. Concerning results still need formal hemoglobin or CBC confirmation and clinician review.',
      },
      {
        question: 'Why can the app ask for a retake?',
        answer:
          'Because a weak image should not be dressed up as a confident result. If lighting, blur, framing, or eyelid visibility are not strong enough, the safer action is to ask for a better capture.',
      },
      {
        question: 'How accurate is the screening?',
        answer:
          'The model uses a multi-stage ensemble pipeline calibrated against clinical data. However, accuracy depends on image quality, lighting conditions, and proper framing. The confidence score shown alongside every result reflects how much trust the system has in its own output.',
      },
      {
        question: 'What kind of image works best?',
        answer:
          'A clear photo of the lower inner eyelid (conjunctiva) captured in indirect natural daylight. Avoid flash, harsh shadows, or extreme angles. The quality gate will tell you if the capture needs improvement.',
      },
    ],
  },
  {
    id: 'privacy',
    icon: Lock,
    label: 'Privacy & Safety',
    eyebrow: 'Use and safety',
    title: 'What happens around the result.',
    intro: 'The system should stay honest when trust is low, when the model is unavailable, or when a case still needs formal testing.',
    faqs: [
      {
        question: 'Can someone use the app without creating an account?',
        answer:
          'Yes. The screening flow can be used as a guest. Accounts are most useful when someone wants saved history, email handoff, or a repeatable record over time.',
      },
      {
        question: 'What happens when the backend or model is unavailable?',
        answer:
          'The interface moves into a clear system state instead of pretending a normal screening result was produced. An offline symptom-only assessment is available as a fallback.',
      },
      {
        question: 'Is the result enough for treatment decisions?',
        answer:
          'No. The result can help with triage and follow-up planning, but treatment decisions should depend on formal testing and clinician judgment.',
      },
      {
        question: 'Is my eye image stored on a server?',
        answer:
          'Images are processed in-memory for screening and are not permanently stored unless you explicitly save the result to your account. Guest screenings are discarded after the session ends.',
      },
    ],
  },
  {
    id: 'technical',
    icon: Activity,
    label: 'Technical',
    eyebrow: 'Technical',
    title: 'How the system works under the hood.',
    intro: 'For developers, clinicians, and reviewers who want to understand the pipeline architecture.',
    faqs: [
      {
        question: 'What ML models power the screening?',
        answer:
          'AnemiaLens uses a multi-stage ensemble: an archive fusion model trained on conjunctival image features, with optional EfficientNet deep learning backup. Runtime calibration adjusts outputs for deployment reliability.',
      },
      {
        question: 'What is the quality gate?',
        answer:
          'Before the ML model runs, images pass through blur detection, brightness/contrast analysis, framing assessment, and glare/shadow screening. This prevents the model from producing overconfident results on poor captures.',
      },
      {
        question: 'How does the confidence score work?',
        answer:
          'Confidence combines capture quality (image signal strength), model stability (prediction uncertainty), and threshold proximity. A low confidence score means the system is less sure — not that the result is wrong.',
      },
      {
        question: 'Can the system run offline?',
        answer:
          'A symptom-only fallback mode is available when the backend is unreachable. This provides a basic risk assessment based on reported symptoms alone, without image analysis.',
      },
    ],
  },
  {
    id: 'clinical',
    icon: ShieldCheck,
    label: 'Clinical',
    eyebrow: 'Clinical context',
    title: 'For clinicians evaluating the tool.',
    intro: 'How the screening output relates to clinical workflows and when to trust versus override the result.',
    faqs: [
      {
        question: 'Can I use this for clinical triage?',
        answer:
          'AnemiaLens can support initial triage by helping identify which patients warrant hemoglobin testing sooner. It is not a diagnostic tool and should not replace clinical judgment or standard lab workup.',
      },
      {
        question: 'What does the hemoglobin estimate mean?',
        answer:
          'When available, the hemoglobin estimate is a rough surrogate derived from image features. It can be suppressed when the model has low confidence or conflicting signals. Always confirm with lab values.',
      },
      {
        question: 'How should I interpret the triage bands?',
        answer:
          'Low Risk: unlikely to have significant anemia. Moderate: further evaluation recommended. High Concern: prompt follow-up advised. Uncertain: image quality was insufficient for reliable screening.',
      },
    ],
  },
] as const;

export default function FAQ() {
  const [searchQuery, setSearchQuery] = useState('');
  const reduceMotion = useReducedMotion();

  const filteredCategories = useMemo(() => {
    if (!searchQuery.trim()) return FAQ_CATEGORIES;
    const query = searchQuery.toLowerCase();
    return FAQ_CATEGORIES.map(cat => ({
      ...cat,
      faqs: cat.faqs.filter(
        faq =>
          faq.question.toLowerCase().includes(query) ||
          faq.answer.toLowerCase().includes(query)
      ),
    })).filter(cat => cat.faqs.length > 0);
  }, [searchQuery]);

  const totalFaqs = FAQ_CATEGORIES.reduce((sum, cat) => sum + cat.faqs.length, 0);

  return (
    <PageSurface
      eyebrow="FAQ"
      title={
        <>
          Common questions,
          <br />
          answered more
          <br />
          carefully.
        </>
      }
      intro="The product works best when people understand both what it helps with and where its limits are. These are the questions most likely to shape safe use."
      badges={['Screening support only', 'Guest access available', 'Clinical follow-up still matters']}
      stats={[
        { label: 'Questions covered', value: `${totalFaqs}`, detail: 'Across general, safety, technical, and clinical topics.' },
        { label: 'Categories', value: `${FAQ_CATEGORIES.length}`, detail: 'Organized for patients, clinicians, and developers.' },
      ]}
      actions={
        <ActionRow
          actions={[
            { to: '/', children: 'Start screening', variant: 'primary' },
            { to: '/how-it-works', children: 'See workflow', variant: 'secondary' },
          ]}
        />
      }
    >
      {/* Search bar */}
      <motion.div
        initial={reduceMotion ? false : { opacity: 0, y: 14 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, ease: E }}
        style={{
          position: 'relative',
          maxWidth: 480,
        }}
      >
        <Search
          size={16}
          style={{
            position: 'absolute',
            left: 14,
            top: '50%',
            transform: 'translateY(-50%)',
            color: 'var(--text-dim)',
            pointerEvents: 'none',
          }}
        />
        <input
          type="text"
          placeholder="Search questions…"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          style={{
            width: '100%',
            padding: '0.85rem 1rem 0.85rem 2.6rem',
            borderRadius: '999px',
            border: '1px solid rgba(255,255,255,0.1)',
            background: 'rgba(255,255,255,0.03)',
            backdropFilter: 'blur(16px)',
            color: 'var(--text)',
            fontFamily: 'var(--sans)',
            fontSize: '0.88rem',
            outline: 'none',
            transition: 'border-color 0.3s, box-shadow 0.3s',
          }}
          onFocus={(e) => {
            e.currentTarget.style.borderColor = 'rgba(94,234,212,0.3)';
            e.currentTarget.style.boxShadow = '0 0 20px rgba(94,234,212,0.08)';
          }}
          onBlur={(e) => {
            e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)';
            e.currentTarget.style.boxShadow = 'none';
          }}
        />
      </motion.div>

      {/* Category quick-nav */}
      <motion.div
        initial={reduceMotion ? false : { opacity: 0, y: 10 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5, delay: 0.1, ease: E }}
        style={{ display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}
      >
        {FAQ_CATEGORIES.map(cat => {
          const Icon = cat.icon;
          return (
            <a
              key={cat.id}
              href={`#faq-${cat.id}`}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.4rem',
                padding: '0.5rem 0.9rem',
                borderRadius: '999px',
                fontSize: '0.68rem',
                fontFamily: 'var(--mono)',
                textTransform: 'uppercase',
                letterSpacing: '0.12em',
                color: 'var(--text-muted)',
                background: 'rgba(255,255,255,0.03)',
                border: '1px solid rgba(255,255,255,0.08)',
                textDecoration: 'none',
                transition: 'all 0.25s ease',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.borderColor = 'rgba(94,234,212,0.2)';
                e.currentTarget.style.color = 'var(--text)';
                e.currentTarget.style.background = 'rgba(255,255,255,0.05)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)';
                e.currentTarget.style.color = 'var(--text-muted)';
                e.currentTarget.style.background = 'rgba(255,255,255,0.03)';
              }}
            >
              <Icon size={13} />
              {cat.label} ({cat.faqs.length})
            </a>
          );
        })}
      </motion.div>

      {/* FAQ sections */}
      <AnimatePresence mode="wait">
        {filteredCategories.length === 0 ? (
          <motion.div
            key="no-results"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
            style={{
              textAlign: 'center',
              padding: '3rem 1rem',
              color: 'var(--text-dim)',
              fontSize: '0.92rem',
            }}
          >
            No questions match "{searchQuery}". Try a different search.
          </motion.div>
        ) : (
          filteredCategories.map((cat) => (
            <div key={cat.id} id={`faq-${cat.id}`}>
              <SectionBlock
                eyebrow={cat.eyebrow}
                title={cat.title}
                intro={cat.intro}
              >
                <FaqList items={cat.faqs} />
              </SectionBlock>
            </div>
          ))
        )}
      </AnimatePresence>
    </PageSurface>
  );
}
