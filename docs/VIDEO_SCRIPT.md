# Video Script

## Goal

Deliver a 3 to 5 minute submission video that proves social impact, GenAI relevance, and real functionality.

## Suggested 4-minute structure

### 0:00 to 0:30 - Problem

"Anemia is common, but early screening still depends on clinic access and blood testing. We built AnemiaLens to turn a smartphone eye image into a safe first-pass screening workflow."

### 0:30 to 1:15 - Safety gate

- Show the capture flow.
- Run quality check on a bad image.
- Say: "The app blocks blurry or badly framed inputs before prediction so it does not over-claim from weak images."

### 1:15 to 2:10 - Screening plus symptom fusion

- Run a valid case.
- Show the result, confidence, and triage band.
- Toggle or show symptoms.
- Say: "The final triage is not image-only. The backend fuses symptom burden with the model signal."

### 2:10 to 3:05 - GenAI layer

- Open the guidance step.
- Point to the grounded GenAI trace card.
- Say: "Qwen turns the structured screening result into plain-language, non-diagnostic guidance using only the current result, uncertainty, symptoms, and locale."

### 3:05 to 3:40 - Handoff and continuity

- Copy or download the handoff report.
- Show recent history or trend.
- Say: "This makes the result usable beyond the demo by supporting clinician handoff and repeat follow-up."

### 3:40 to 4:00 - Close

"AnemiaLens is not a diagnostic device. It is a safer, mobile-first screening system that helps users know when to retake, when to monitor, and when to seek care."

## Must-show checklist

- quality gate blocking a weak image
- one successful risk analysis
- confidence or uncertainty output
- grounded GenAI guidance
- handoff summary export
