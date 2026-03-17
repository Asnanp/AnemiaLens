# AnemiaLens — Full Presentation Script
### 4.5 Minutes | Hackathon Delivery | Your Voice, Your Tone

---

## SLIDE 1 — Title Slide
**[Open with confidence. Pause 2 seconds before speaking.]**

"Every year, over 1.92 billion people live with anemia.

Most of them don't know it.

Not because the disease is rare — but because the test requires a needle, a lab, and a clinic they can't reach.

We asked one question: what if your phone could be the first step?

This is AnemiaLens."

**[Click to next slide.]**

---

## SLIDE 2 — The Problem
**[Slow down here. Let the numbers land.]**

"Anemia is the world's most widespread nutritional disorder. It causes fatigue, cognitive decline, pregnancy complications, and in severe cases — death.

But here's the gap nobody talks about:

The gold standard test — a complete blood count — requires a lab. In rural India, sub-Saharan Africa, Southeast Asia — that lab might be 40 kilometers away. It costs money. It takes time. And by the time someone gets there, the window for early intervention is already closing.

We're not trying to replace the lab. We're trying to get people to the lab sooner — with a signal they can act on today."

**[Click to next slide.]**

---

## SLIDE 3 — The Solution
**[Pick up the energy slightly. This is the reveal.]**

"AnemiaLens is a smartphone-first anemia screening tool.

You pull down your lower eyelid — right here — and take a photo of the conjunctiva. That pink tissue. Its color is a direct proxy for hemoglobin levels in the blood.

Our system analyzes that image in seconds. It estimates your hemoglobin, calculates a risk score, fuses it with your symptoms, and generates a triage band — Low, Moderate, High Concern, or Retake.

Then Mistral AI translates all of that into plain-language guidance. Not a diagnosis. A safe, grounded next step.

Zero hardware. Zero cost per screening. Just a phone."

**[Click to next slide.]**

---

## SLIDE 4 — Architecture
**[Technical slide. Speak clearly, don't rush.]**

"Let me walk you through what's actually happening under the hood.

The image goes through a quality gate first — blur detection, brightness check, framing validation. Bad images get rejected before they ever reach the model. That's intentional. Garbage in, garbage out.

If the image passes, it hits our vision backbone — EfficientNet-B0, trained on 710 validated conjunctival specimens. It outputs a hemoglobin estimate and a risk probability.

That gets fused with symptom data — fatigue, dizziness, shortness of breath, menstrual bleeding — through what we call the Clinical Feature Ensemble. A confidence-weighted blend of the vision model, a gradient boosting classifier, and a regression head.

The triage engine maps that to a safety band. And then Mistral AI — constrained by deterministic medical rules — generates personalized guidance that references the actual hemoglobin value, the actual risk percentage, the actual symptoms.

No hallucination. No generic advice. Grounded output.

Generative AI here isn't a gimmick — it's the bridge between a model prediction and something a real person can act on."

**[Click to next slide.]**

---

## SLIDE 5 — Live Demo
**[Switch to browser. Open anemia-lens.vercel.app. Speak while navigating.]**

"Let me show you this live.

This is the actual deployed product — running on Vercel, with the backend on Render.

I'm going to use our High Concern demo image — a real conjunctival photo from the dataset.

[Upload the image]

You can see the quality gate passing — brightness, contrast, framing all green.

[Move to symptoms]

I'll add fatigue and dizziness — common anemia symptoms.

[Click Analyze]

While it's running — the model is doing inference, the triage engine is scoring, and Mistral is generating guidance in real time.

[Result appears]

There it is. 13.9 grams per deciliter hemoglobin estimate. 54% risk score. High Concern band.

And look at the Mistral guidance — it's referencing the actual hemoglobin value, the actual risk percentage, the specific symptoms I entered. It's telling this person to see a doctor within the next few weeks. Concrete. Safe. Actionable.

That's the whole loop — image in, guidance out — in under 10 seconds."

**[Click to next slide.]**

---

## SLIDE 6 — Impact
**[Bring the energy back down. This is the heart of the pitch.]**

"We validated this on 710 clinical specimens from a real-world dataset collected in India. 92% sensitivity. That means 92 out of 100 anemic cases get flagged.

But the number I keep coming back to is 1.92 billion.

That's not an abstract statistic. That's a pregnant woman in rural Bangladesh who doesn't know her hemoglobin is at 8. That's a child in Nigeria who's been tired for months and nobody's connected the dots yet.

AnemiaLens doesn't diagnose them. But it gives them a signal. It gives a community health worker a tool. It gives a family a reason to go to the clinic.

In low-resource settings, that signal is the difference between early intervention and a preventable complication."

**[Click to next slide.]**

---

## SLIDE 7 — What's Next
**[Forward-looking. Confident but grounded.]**

"We're not done.

The next version adds multi-language support — Hindi, Swahili, Bahasa — so the guidance reaches people in their own language.

We're exploring federated learning so the model improves from real-world usage without centralizing sensitive health data.

And we're in early conversations with community health programs in India and Southeast Asia about pilot deployments.

The infrastructure is already live. The model is already deployed. We're not pitching a prototype — we're pitching a product that works today and scales tomorrow."

**[Click to next slide.]**

---

## SLIDE 8 — Closing
**[Slow. Deliberate. Look up from the screen.]**

"Anemia is not a rare disease. It's not a complex disease. It's a disease that kills and disables because detection is too slow and too expensive for the people who need it most.

We built AnemiaLens because we believe a smartphone should be enough to start that conversation.

Not to replace the doctor. Not to replace the lab. But to make sure more people get there — sooner, safer, with a signal they can trust.

Thank you."

**[Pause. Don't rush off. Let it land.]**

---

## TIMING GUIDE

| Slide | Content | Time |
|-------|---------|------|
| 1 | Title / Hook | 25s |
| 2 | Problem | 45s |
| 3 | Solution | 50s |
| 4 | Architecture | 60s |
| 5 | Live Demo | 75s |
| 6 | Impact | 40s |
| 7 | What's Next | 30s |
| 8 | Closing | 25s |
| **Total** | | **~4:30** |

---

## QUICK REFERENCE — KEY FACTS TO KNOW COLD

- **1.92 billion** — global anemia burden (GBD Study 2021, The Lancet)
- **710** — validated conjunctival specimens in training dataset
- **92%** — model sensitivity
- **EfficientNet-B0** — vision backbone
- **Mistral AI (mistral-small-latest)** — GenAI guidance layer
- **4-band triage** — Low / Moderate / High Concern / Retake
- **Hemoglobin estimate** — from conjunctival pallor analysis
- **Clinical Feature Ensemble** — confidence-weighted fusion of vision model + XGBoost + regression
- **Live URLs** — frontend: `anemia-lens.vercel.app` | backend: `anemialens-3.onrender.com`
- **Demo image** — High Concern, ~13.9 g/dL, 54% risk

---

## IF JUDGES ASK

**"Is this a diagnosis?"**
> "No — and that's by design. Every output is framed as screening guidance. The language is non-diagnostic. We have a safety filter that blocks any claim of certainty. The goal is to get people to a clinician, not replace one."

**"How accurate is it?"**
> "92% sensitivity on 710 validated specimens. That's the recall — how many true anemia cases we catch. We prioritize sensitivity over specificity because in a screening context, a false negative is more dangerous than a false positive."

**"Why conjunctival pallor?"**
> "It's the most accessible and validated non-invasive proxy for hemoglobin. Clinicians have used it for decades. We're automating what a trained eye already does."

**"Why Mistral AI?"**
> "We needed a model that could generate grounded, safe, personalized guidance — not generic advice. Mistral's JSON mode lets us constrain the output structure. We pass the actual hemoglobin value, risk percentage, triage band, and active symptoms directly into the prompt. The model references real data, not assumptions."

**"What's the business model?"**
> "B2B2C — licensing to community health programs, NGOs, and telehealth platforms. The marginal cost per screening is effectively zero once deployed."
