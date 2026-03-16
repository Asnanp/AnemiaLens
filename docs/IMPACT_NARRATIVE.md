# Impact Narrative

## Problem

Anemia is often under-screened because early detection usually depends on blood testing, clinic access, travel, time, and cost. For many people, those frictions delay action until symptoms become worse.

## Our approach

AnemiaLens turns a smartphone into a first-pass screening and triage tool:

1. The user captures an image of the inner lower eyelid.
2. The app blocks blurry, dark, or badly framed images before prediction.
3. The model estimates anemia-like risk from conjunctival pallor.
4. A short symptom questionnaire adds real-world context.
5. The system returns a non-diagnostic triage band plus grounded next steps.

## Who it helps

- Students and families who may delay testing until symptoms worsen
- Community health workers who need a fast screening workflow
- Users in low-resource settings who need a lightweight mobile-first experience
- Caregivers who need a safer handoff summary before formal evaluation

## Why this matters

The product is useful even when it does not produce a positive result. It helps in three different ways:

- It blocks unsafe captures instead of producing false confidence from bad images.
- It creates an interpretable screening result with confidence and uncertainty.
- It helps users decide whether to retake, monitor, or seek formal review.

## What makes the solution credible

- Safety gate before inference
- Structured symptom fusion instead of image-only claims
- Non-diagnostic triage language
- Grounded GenAI guidance with deterministic fallback
- Shareable clinician handoff text

## What success looks like

The app is successful if it helps users:

- capture a usable image correctly on the first or second try,
- avoid acting on low-quality or high-uncertainty output,
- understand the next step in plain language,
- and reach formal medical testing sooner when the screening result is concerning.

## Social-good angle

This project fits social-good goals because it improves early access to health screening without requiring expensive hardware or specialist interpretation at the point of use. It is designed for practical, deployable screening support rather than lab replacement.
