import { Camera, FileText, HeartPulse, ShieldCheck } from 'lucide-react';

import {
  ActionRow,
  CardGrid,
  FeatureCard,
  MetricStrip,
  PageSurface,
  SectionBlock,
  TimelineList,
} from '../components/site/RoutePage';

const HOW_IT_WORKS_STEPS = [
  {
    number: '01',
    title: 'Capture the lower inner eyelid',
    detail:
      'The flow begins with one guided lower-eyelid image in bright indirect light, with the eyelid fully visible and centered in frame.',
  },
  {
    number: '02',
    title: 'Run image quality review',
    detail:
      'The app checks blur, lighting, framing, and eyelid visibility first so a weak image does not become a confident-looking result.',
  },
  {
    number: '03',
    title: 'Add symptom and patient context',
    detail:
      'Symptoms and optional patient details are added only after the image passes its gate so the screening stays structured.',
  },
  {
    number: '04',
    title: 'Read the result with the next step',
    detail:
      'The final surface keeps risk, reliability, and follow-up guidance together so the user knows what the safest next move is.',
  },
] as const;

export default function HowItWorks() {
  return (
    <PageSurface
      eyebrow="How it works"
      title={
        <>
          One guided capture,
          <br />
          four clearer stages.
        </>
      }
      intro="The workflow is meant to feel simple for the person using it, but careful in the places that matter. Each stage has one job, so the product can slow down before it makes a stronger claim."
      badges={['Capture first', 'Quality before inference', 'Result with follow-up']}
      stats={[
        { label: 'Image', value: '1 capture', detail: 'The process starts with one guided lower-eyelid photo.' },
        { label: 'Stages', value: '4 steps', detail: 'Capture, quality, intake, and result each have a clear role.' },
        { label: 'Output', value: 'Care summary', detail: 'The result combines risk, trust, and next-step guidance.' },
      ]}
      actions={
        <ActionRow
          actions={[
            { to: '/', children: 'Open screening', variant: 'primary' },
            { to: '/science', children: 'Read science', variant: 'secondary' },
          ]}
        />
      }
      side={
        <div
          className="glass route-side-panel"
          style={{
            padding: '1.35rem',
            borderRadius: '1.4rem',
            background: 'rgba(8, 12, 20, 0.8)',
            display: 'grid',
            gap: '0.9rem',
          }}
        >
          <div className="section-eyebrow">Capture rules</div>
          <div style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(1.7rem, 2.6vw, 2.25rem)', lineHeight: 1.04, letterSpacing: '-0.04em' }}>
            The image is checked before the result is trusted.
          </div>
          <div className="route-mini-list">
            <div className="route-mini-list-item">
              <ShieldCheck size={15} />
              <span>Bright indirect daylight is preferred.</span>
            </div>
            <div className="route-mini-list-item">
              <ShieldCheck size={15} />
              <span>No flash or harsh shadows on the eyelid.</span>
            </div>
            <div className="route-mini-list-item">
              <ShieldCheck size={15} />
              <span>The lower eyelid should be fully visible and centered.</span>
            </div>
          </div>
        </div>
      }
    >
      <SectionBlock
        eyebrow="Workflow"
        title="Each stage does one job."
        intro="That separation is what makes the experience easier to trust. The product should not be capturing, explaining, and overclaiming all at the same time."
      >
        <TimelineList steps={HOW_IT_WORKS_STEPS} />
      </SectionBlock>

      <SectionBlock
        eyebrow="Inside the result"
        title="What comes back after the screening runs."
        intro="The goal is a calmer result surface that can be acted on by a patient, caregiver, or clinician without hiding uncertainty."
      >
        <CardGrid>
          <FeatureCard
            icon={Camera}
            kicker="Capture state"
            title="Image quality remains visible"
            detail="The result should still show whether the capture was strong enough to trust or whether a retake would improve the read."
          />
          <FeatureCard
            icon={ShieldCheck}
            kicker="Trust layer"
            title="Reliability stays separate from risk"
            detail="A moderate or low risk band should never hide the fact that the image itself was weak or unstable."
          />
          <FeatureCard
            icon={HeartPulse}
            kicker="Context"
            title="Symptoms can shape the triage story"
            detail="The flow allows symptom and patient details to influence the summary instead of pretending the image is all that matters."
          />
          <FeatureCard
            icon={FileText}
            kicker="Follow-up"
            title="Next steps are part of the result"
            detail="The output keeps the action guidance beside the screening summary so the person using it knows what to do next."
          />
        </CardGrid>
      </SectionBlock>

      <SectionBlock
        eyebrow="Care posture"
        title="Built to guide the next move, not replace diagnosis."
        intro="The workflow is strongest when it supports screening, review, and follow-up. Concerning results still need formal hemoglobin or CBC confirmation."
      >
        <MetricStrip
          items={[
            { label: 'Retake path', value: 'Available', detail: 'The flow can stop and ask for a better image when the capture is weak.' },
            { label: 'Reliability', value: 'Visible', detail: 'Trust remains part of the output instead of disappearing behind a percentage.' },
            { label: 'Clinical follow-up', value: 'Still required', detail: 'The product does not remove the need for clinician review and blood testing.' },
          ]}
        />
      </SectionBlock>
    </PageSurface>
  );
}
