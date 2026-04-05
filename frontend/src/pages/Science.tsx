import { Activity, BrainCircuit, ClipboardCheck, Eye, Microscope, ShieldCheck } from 'lucide-react';

import {
  ActionRow,
  CardGrid,
  FeatureCard,
  MetricStrip,
  PageSurface,
  SectionBlock,
  TimelineList,
} from '../components/site/RoutePage';

const SCIENCE_TIMELINE = [
  {
    number: '01',
    title: 'Capture the lower inner eyelid',
    detail:
      'The workflow begins with a guided lower-eyelid image because the inside eyelid carries the pallor signal the screen is trying to read.',
  },
  {
    number: '02',
    title: 'Block weak images before inference',
    detail:
      'Lighting, blur, framing, and eyelid visibility are reviewed before the model is allowed to make a stronger-looking call.',
  },
  {
    number: '03',
    title: 'Fuse image signal with case context',
    detail:
      'Symptoms and optional patient details sit beside the image so the result is not treated like a photograph can tell the whole story alone.',
  },
  {
    number: '04',
    title: 'Return a careful screening summary',
    detail:
      'The output keeps risk, trust, and follow-up guidance together so uncertainty stays visible instead of being hidden behind one number.',
  },
] as const;

const SCIENCE_METRICS = [
  { label: 'Image target', value: 'Lower eyelid', detail: 'The screening is built around the lower inner eyelid, not a general eye photo.' },
  { label: 'Workflow', value: '4 stages', detail: 'Capture, quality review, intake, and result stay separate so each stage has one job.' },
  { label: 'Output', value: 'Risk + trust', detail: 'The result returns a screening band and a reliability story instead of overclaiming certainty.' },
] as const;

export default function Science() {
  return (
    <PageSurface
      eyebrow="Science and safety"
      title={
        <>
          Why the screening stays
          <br />
          careful before it speaks.
        </>
      }
      intro="AnemiaLens is designed around a simple rule: a lower-eyelid image can support a screening decision only when the capture is strong enough and the limits stay visible. The product is built to slow down at the right moments before it shows a next step."
      badges={['Quality gate first', 'Lower-eyelid ROI', 'Screening support only']}
      stats={SCIENCE_METRICS}
      actions={
        <ActionRow
          actions={[
            { to: '/how-it-works', children: 'See the workflow', variant: 'primary' },
            { to: '/providers', children: 'Clinical use', variant: 'secondary' },
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
            gap: '1rem',
          }}
        >
          <div className="section-eyebrow">Inside the model path</div>
          <div style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(1.8rem, 2.8vw, 2.4rem)', lineHeight: 1.02, letterSpacing: '-0.04em' }}>
            The product checks trust before it lets the model lead.
          </div>
          <div className="route-mini-list">
            <div className="route-mini-list-item">
              <ClipboardCheck size={15} />
              <span>Image viability is reviewed before prediction.</span>
            </div>
            <div className="route-mini-list-item">
              <BrainCircuit size={15} />
              <span>The model reads the image with context instead of acting on the photo alone.</span>
            </div>
            <div className="route-mini-list-item">
              <ShieldCheck size={15} />
              <span>Concerning results are framed as a follow-up prompt, not a diagnosis.</span>
            </div>
          </div>
        </div>
      }
    >
      <SectionBlock
        eyebrow="What the product is designed to do"
        title="A safer screening stack, not a single-score gimmick."
        intro="The product experience matters as much as the model. These layers are what keep the result readable, reviewable, and less likely to overstate what a weak image can support."
      >
        <CardGrid>
          <FeatureCard
            icon={Eye}
            kicker="Image signal"
            title="Lower-eyelid image only"
            detail="The screening is centered on one guided lower-eyelid capture so the target remains specific and repeatable."
          />
          <FeatureCard
            icon={ShieldCheck}
            kicker="Quality gate"
            title="Weak captures are stopped early"
            detail="Lighting, blur, framing, and eyelid visibility are reviewed before the result engine moves forward."
          />
          <FeatureCard
            icon={Activity}
            kicker="Result design"
            title="Risk and reliability stay separate"
            detail="The user sees the screening signal and the trust story together so uncertainty is not hidden."
          />
          <FeatureCard
            icon={Microscope}
            kicker="Clinical posture"
            title="Follow-up stays explicit"
            detail="Concerning results still point to hemoglobin or CBC confirmation rather than pretending the photo closed the case."
          />
        </CardGrid>
      </SectionBlock>

      <SectionBlock
        eyebrow="Method sequence"
        title="The model path only happens after the capture passes the gate."
        intro="This is the intended order of operations. The point is not speed at any cost; it is to keep the system honest about what it can and cannot support."
      >
        <TimelineList steps={SCIENCE_TIMELINE} />
      </SectionBlock>

      <SectionBlock
        eyebrow="Safety stance"
        title="A healthcare screening should reduce false confidence, not just look advanced."
        intro="AnemiaLens is built to make the next step clearer. That means image quality can block the flow, reliability can stay low even when a risk band exists, and concerning cases should still be verified clinically."
      >
        <MetricStrip
          items={[
            {
              label: 'Retake first',
              value: 'Allowed',
              detail: 'The product can ask for a better image instead of pretending the first one was enough.',
            },
            {
              label: 'Clinical follow-up',
              value: 'Required',
              detail: 'A photo-based screen does not replace formal hemoglobin testing or clinician review.',
            },
            {
              label: 'Confidence posture',
              value: 'Visible',
              detail: 'Trust information stays in the result so the user sees when the system is uncertain.',
            },
          ]}
        />
      </SectionBlock>
    </PageSurface>
  );
}
