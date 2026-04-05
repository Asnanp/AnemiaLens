import { ActionRow, FaqList, PageSurface, SectionBlock } from '../components/site/RoutePage';

const GENERAL_FAQS = [
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
] as const;

const PRIVACY_FAQS = [
  {
    question: 'Can someone use the app without creating an account?',
    answer:
      'Yes. The screening flow can be used as a guest. Accounts are most useful when someone wants saved history, email handoff, or a repeatable record over time.',
  },
  {
    question: 'What happens when the backend or model is unavailable?',
    answer:
      'The interface should move into a clear system state instead of pretending a normal screening result was produced. The product is being updated to keep that distinction visible everywhere.',
  },
  {
    question: 'Is the result enough for treatment decisions?',
    answer:
      'No. The result can help with triage and follow-up planning, but treatment decisions should depend on formal testing and clinician judgment.',
  },
] as const;

export default function FAQ() {
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
      actions={
        <ActionRow
          actions={[
            { to: '/', children: 'Start screening', variant: 'primary' },
            { to: '/how-it-works', children: 'See workflow', variant: 'secondary' },
          ]}
        />
      }
    >
      <SectionBlock
        eyebrow="General"
        title="What the workflow is meant to do."
        intro="These answers focus on how the product should be understood by a patient, clinician, or reviewer."
      >
        <FaqList items={GENERAL_FAQS} />
      </SectionBlock>

      <SectionBlock
        eyebrow="Use and safety"
        title="What happens around the result."
        intro="The system should stay honest when trust is low, when the model is unavailable, or when a case still needs formal testing."
      >
        <FaqList items={PRIVACY_FAQS} />
      </SectionBlock>
    </PageSurface>
  );
}
