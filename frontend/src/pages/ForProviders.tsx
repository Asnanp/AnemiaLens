import { ClipboardList, FileText, ShieldCheck, Stethoscope, Workflow } from 'lucide-react';

import {
  ActionRow,
  CardGrid,
  FeatureCard,
  MetricStrip,
  PageSurface,
  SectionBlock,
  TimelineList,
} from '../components/site/RoutePage';

const PROVIDER_STEPS = [
  {
    number: '01',
    title: 'Screen at the point of first contact',
    detail:
      'A staff member or patient can capture the lower inner eyelid before lab work is available, giving the clinical team an earlier first-pass signal.',
  },
  {
    number: '02',
    title: 'Review the capture and trust story',
    detail:
      'The workflow shows whether the image was strong enough to interpret instead of forcing staff to trust a weak capture.',
  },
  {
    number: '03',
    title: 'Use the result as triage support',
    detail:
      'Risk, reliability, and next-step guidance arrive together so the output can support prioritization and follow-up planning.',
  },
  {
    number: '04',
    title: 'Hand off or save the case summary',
    detail:
      'Email, PDF, and saved account history keep the screening usable after the first screen instead of leaving it trapped in the UI.',
  },
] as const;

export default function ForProviders() {
  return (
    <PageSurface
      eyebrow="Provider workflow"
      title={
        <>
          Built to support
          <br />
          triage, review, and
          <br />
          follow-up.
        </>
      }
      intro="AnemiaLens is aimed at first-pass screening support. The goal is to help teams review image quality, look at a cautious risk signal, and move patients toward the right next step without presenting a phone photo as a diagnosis."
      badges={['Screening support', 'Reviewable output', 'Share-ready summary']}
      stats={[
        { label: 'Capture', value: '1 image', detail: 'One guided lower-eyelid image starts the workflow.' },
        { label: 'Review path', value: 'Risk + trust', detail: 'Clinicians can see both the screening result and how reliable the capture was.' },
        { label: 'Handoff', value: 'Email + PDF', detail: 'Results can move into follow-up rather than staying trapped in the app.' },
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
            gap: '1rem',
          }}
        >
          <div className="section-eyebrow">Where it fits</div>
          <div style={{ fontFamily: 'var(--serif)', fontSize: 'clamp(1.8rem, 2.8vw, 2.4rem)', lineHeight: 1.02, letterSpacing: '-0.04em' }}>
            A calmer layer before formal blood testing.
          </div>
          <div className="route-mini-list">
            <div className="route-mini-list-item">
              <Workflow size={15} />
              <span>Supports the front end of triage rather than replacing diagnostic work.</span>
            </div>
            <div className="route-mini-list-item">
              <ClipboardList size={15} />
              <span>Works best when the team needs a structured first-pass screen with visible uncertainty.</span>
            </div>
            <div className="route-mini-list-item">
              <FileText size={15} />
              <span>Produces a report surface that can survive beyond the first device screen.</span>
            </div>
          </div>
        </div>
      }
    >
      <SectionBlock
        eyebrow="Use cases"
        title="The system is strongest when it supports an existing care path."
        intro="This is not a replacement for clinical review. It is more useful as an earlier, structured screening layer that helps teams decide whether to retake, monitor, or move toward formal testing."
      >
        <CardGrid>
          <FeatureCard
            icon={Stethoscope}
            kicker="Triage support"
            title="Earlier screening signal"
            detail="A guided image can be collected before lab values are available, helping the team prioritize the next step."
          />
          <FeatureCard
            icon={ShieldCheck}
            kicker="Quality control"
            title="Weak captures are flagged"
            detail="The product keeps image trust visible instead of letting low-quality photos masquerade as reliable evidence."
          />
          <FeatureCard
            icon={ClipboardList}
            kicker="Context fusion"
            title="Symptoms stay in the picture"
            detail="Symptoms and patient context can influence the screening summary instead of leaving the image to speak alone."
          />
          <FeatureCard
            icon={FileText}
            kicker="After the screen"
            title="Shareable summary"
            detail="Email, PDF, and saved history help the result move into review and follow-up instead of dying in the session."
          />
        </CardGrid>
      </SectionBlock>

      <SectionBlock
        eyebrow="Clinical sequence"
        title="What a provider-facing use of the product should look like."
        intro="The flow should stay simple enough for a real clinic or outreach setting while keeping the result honest about its limits."
      >
        <TimelineList steps={PROVIDER_STEPS} />
      </SectionBlock>

      <SectionBlock
        eyebrow="Adoption posture"
        title="Best used as a first-pass screening layer."
        intro="The product is most defensible when it is used to guide attention and follow-up, not when it is treated like the phone image alone can close the case."
      >
        <MetricStrip
          items={[
            { label: 'Best role', value: 'Triage support', detail: 'Useful before or alongside formal testing, not instead of it.' },
            { label: 'Most valuable output', value: 'Clear next step', detail: 'Teams can see whether the case should be retaken, monitored, or reviewed clinically.' },
            { label: 'Safety guardrail', value: 'Clinical confirmation', detail: 'Concerning screens still need hemoglobin or CBC confirmation.' },
          ]}
        />
      </SectionBlock>
    </PageSurface>
  );
}
