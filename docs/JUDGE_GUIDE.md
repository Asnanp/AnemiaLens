# Judge Guide

## What to notice first

AnemiaLens is strongest when judged as a full system, not as a single model.

- The app blocks weak images before prediction.
- It combines image signal with symptom fusion.
- It exposes confidence, uncertainty, and reliability.
- It uses grounded GenAI for safe next-step guidance.
- It produces a clinician-ready handoff summary and clinical brief.

## Best demo path

1. Run a bad image or the retake demo case.
2. Show that the quality gate blocks prediction.
3. Run a moderate or high-concern case.
4. Show symptom fusion changing the triage story.
5. Open the GenAI guidance panel and point out the grounded trace.
6. Copy or download the handoff report.

## Why this is more than a basic AI demo

- The product includes both model output and safety controls.
- The GenAI layer is grounded and bounded instead of free-form.
- The backend exposes provenance, decision audit, and clinical brief data.
- The system is designed for real deployment constraints: mobile flow, fallback mode, and lightweight runtime.

## Categories this project targets well

- Best backend/functionality
- Best documentation
- Strong overall placement if demo quality is clean

## What judges can verify quickly

- backend tests pass
- frontend builds
- runtime status exposes loaded model and guidance strategy
- generated guidance is explicitly non-diagnostic
- poor images are blocked before inference
