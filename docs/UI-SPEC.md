# AnemiaLens UI Spec

## Direction
- Theme: light, calm, professional medical product
- Core workflow: upload image, run quality check, add symptoms, read result
- UX goal: one clear action per screen, no dashboard clutter

## Visual Rules
- Use `Figtree` for headings and `Noto Sans` for body copy
- Prefer soft white surfaces, muted green accents, and warm neutral backgrounds
- Avoid dark neon styling, decorative motion, and demo-style chrome

## Layout Rules
- Keep a single centered content column
- Use a compact step rail with four steps only
- Use two-column layouts only when comparison adds value
- Collapse all multi-column sections to one column on mobile

## Screen Order
1. Capture image
2. Evaluate image quality
3. Add symptoms
4. Show result, reliability, guidance, and shareable summary

## Copy Rules
- Speak plainly and avoid internal language
- Keep “screening aid, not a diagnosis” visible
- Make the next action obvious after every major state

## Anti-Patterns
- Overdesigned visuals
- Too many cards competing at once
- Persona modes, judge modes, or hidden workflow logic
- Letting prediction appear before image quality is checked
