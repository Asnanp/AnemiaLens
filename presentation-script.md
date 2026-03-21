# AnemiaLens Presentation Script

---

## OPENING (Slides 1-3)

"This is AnemiaLens. It's a screening tool that checks for anemia using just a smartphone camera. You take a photo of the inner eyelid, and it gives you a risk assessment — no blood test needed.

We built this because anemia affects nearly 2 billion people globally, but most don't know they have it. In many areas, getting a blood test is expensive, takes days, or just doesn't happen.

The thing is, the signal is already there. When hemoglobin drops, the inner eyelid turns pale. Doctors have used this for decades. We just taught a phone to read it."

---

## DEMO TRANSITION

"Let me show you how it works."

**[Switch to website: https://anemia-lens.vercel.app]**

---

## LIVE DEMO

"I'll upload an eye image here."

**[Upload image]**

"First, it checks image quality — lighting, blur, framing — because bad input means unreliable output."

**[Show quality check passing]**

"Then it processes the image, extracts features from the conjunctiva, and combines that with any symptoms you report."

**[Wait for result]**

"Here's the result. It shows a risk level and an estimated hemoglobin value. It also explains why it gave this result — not just a black box.

And if the system isn't confident, it won't guess. It'll tell you to retake the photo. That's important for safety."

**[Switch back to slides]**

---

## ARCHITECTURE (Slide 4-7)

"So that's the user experience. Behind it, there's a full pipeline.

We extract 41 color and texture features from the eye image — things like pallor index, redness uniformity, hue distribution. Then an ensemble model combines those features with symptom data to predict anemia risk and hemoglobin level.

We trained it on 217 real patient images, and the pipeline is designed to match exactly what happens during inference — no domain gap between training and production.

We also built in uncertainty estimation, so the model knows when it doesn't know."

---

## AI TOOLS (Slide 6)

"Quick note on how this was built. We used Kiro for the frontend — it has a UI/UX skill that generated the entire design system in one command. Dark glassmorphism, responsive layout, accessibility features, all of it.

For the backend and ML, we used Amazon Q with a custom ML engineer agent. It handled feature engineering, pipeline retraining, and the FastAPI backend. Every line was reviewed and tested, but the AI did the heavy lifting."

---

## SAFETY (Slide 8)

"Now, safety. In medical AI, being confidently wrong is worse than being uncertain. So we built multiple guardrails.

There's an image quality gate that blocks bad inputs before any model runs. We expose the uncertainty score on every prediction. If uncertainty is too high, we hide the hemoglobin estimate. And we filter the AI-generated guidance to make sure it never makes diagnostic claims.

This is a screening tool, not a diagnosis. That distinction matters."

---

## WHO IT'S FOR (Slide 9)

"This is designed for low-resource clinics and community health workers in places like South Asia and Sub-Saharan Africa, where lab testing is limited or delayed.

The goal is simple: give people a fast, free first-pass signal so they know when they need a real blood test. Zero marginal cost per screening. Any smartphone. No hardware. No waiting."

---

## CLOSING (Slide 10)

"So that's AnemiaLens. A photo becomes an early warning signal.

Because something this common shouldn't go unnoticed.

Thank you."

---

## BACKUP SLIDES / Q&A PREP

**If asked about accuracy:**
"The model achieves around 70% accuracy with 89% recall on the validation set. Recall is prioritized because missing anemia is worse than a false alarm. The AUC is 0.80, which is solid for a screening tool."

**If asked about regulatory status:**
"This is a research prototype, not a medical device. It's not FDA-approved or CE-marked. It's designed as a decision support tool for healthcare workers, not for direct consumer diagnosis."

**If asked about data privacy:**
"Images are processed server-side but not stored permanently. We don't collect PHI. The system is designed to be deployed on-premise in clinics if needed."

**If asked about cost:**
"The app is free. The backend is hosted on Hugging Face Spaces right now. In production, server costs would still be minimal for a large number of screenings."

**If asked about next steps:**
"We're looking to partner with NGOs or health organizations for field validation. We also want to expand the dataset and add support for more languages."
