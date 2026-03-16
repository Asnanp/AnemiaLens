from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
import copy

prs = Presentation()
prs.slide_width  = Inches(13.33)
prs.slide_height = Inches(7.5)

# ── Palette ──────────────────────────────────────────────────────────────────
VOID    = RGBColor(0x02, 0x02, 0x08)
CRIMSON = RGBColor(0xC8, 0x00, 0x1E)
BRIGHT  = RGBColor(0xE8, 0x29, 0x4A)
WHITE   = RGBColor(0xF2, 0xF0, 0xEC)
MUTED   = RGBColor(0x8A, 0x88, 0x84)
DIM     = RGBColor(0x44, 0x42, 0x40)
GREEN   = RGBColor(0x10, 0xB9, 0x81)
AMBER   = RGBColor(0xF5, 0x9E, 0x0B)
CARD    = RGBColor(0x0A, 0x0A, 0x14)

W = prs.slide_width
H = prs.slide_height

blank_layout = prs.slide_layouts[6]  # completely blank

# ── Helpers ───────────────────────────────────────────────────────────────────
def add_bg(slide, color=VOID):
    bg = slide.shapes.add_shape(1, 0, 0, W, H)
    bg.fill.solid(); bg.fill.fore_color.rgb = color
    bg.line.fill.background()
    return bg

def add_rect(slide, x, y, w, h, fill, alpha=None, line_color=None, line_w=Pt(0)):
    s = slide.shapes.add_shape(1, x, y, w, h)
    s.fill.solid(); s.fill.fore_color.rgb = fill
    if line_color:
        s.line.color.rgb = line_color
        s.line.width = line_w
    else:
        s.line.fill.background()
    return s

def add_text(slide, text, x, y, w, h, size=Pt(14), bold=False, color=WHITE,
             align=PP_ALIGN.LEFT, italic=False, font="Calibri"):
    tb = slide.shapes.add_textbox(x, y, w, h)
    tf = tb.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = size
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color
    run.font.name = font
    return tb

def add_label(slide, text, x, y, w=Inches(4)):
    add_text(slide, text.upper(), x, y, w, Inches(0.3),
             size=Pt(8), bold=True, color=CRIMSON, font="Courier New")

def add_card(slide, x, y, w, h, title, body, title_color=WHITE):
    add_rect(slide, x, y, w, h, CARD, line_color=DIM, line_w=Pt(0.75))
    add_text(slide, title, x+Inches(0.2), y+Inches(0.15), w-Inches(0.4), Inches(0.4),
             size=Pt(13), bold=True, color=title_color)
    add_text(slide, body, x+Inches(0.2), y+Inches(0.55), w-Inches(0.4), h-Inches(0.7),
             size=Pt(10), color=MUTED)

def crimson_bar(slide, x, y, h=Inches(0.06)):
    add_rect(slide, x, y, Inches(0.5), h, CRIMSON)

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 1 — TITLE
# ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(blank_layout)
add_bg(s)

# Left crimson accent bar
add_rect(s, 0, 0, Inches(0.18), H, CRIMSON)

# Eyebrow
add_text(s, "HACKATHON 2026  ·  AI FOR HEALTH", Inches(0.5), Inches(1.6),
         Inches(8), Inches(0.4), size=Pt(9), bold=True, color=CRIMSON, font="Courier New")

# Title
add_text(s, "AnemiaLens", Inches(0.5), Inches(2.1),
         Inches(9), Inches(1.6), size=Pt(72), bold=True, color=WHITE, font="Calibri")

# Subtitle
add_text(s, "Smartphone-first anemia screening powered by\ncomputer vision and grounded GenAI.",
         Inches(0.5), Inches(3.75), Inches(7.5), Inches(1.0),
         size=Pt(18), color=MUTED, font="Calibri")

# Stat chips row
chips = [("1.6B+", "People Affected"), ("92%", "Sensitivity"), ("$0", "Marginal Cost")]
for i, (val, lbl) in enumerate(chips):
    cx = Inches(0.5) + i * Inches(2.6)
    add_rect(s, cx, Inches(5.1), Inches(2.3), Inches(0.9), CARD, line_color=DIM, line_w=Pt(0.75))
    add_text(s, val,  cx+Inches(0.15), Inches(5.15), Inches(2.0), Inches(0.4),
             size=Pt(22), bold=True, color=CRIMSON, font="Calibri")
    add_text(s, lbl,  cx+Inches(0.15), Inches(5.55), Inches(2.0), Inches(0.3),
             size=Pt(9), color=MUTED, font="Courier New")

# Team / event tag bottom right
add_text(s, "3-Minute Demo  ·  2026", Inches(9.5), Inches(6.9),
         Inches(3.5), Inches(0.4), size=Pt(9), color=DIM, align=PP_ALIGN.RIGHT, font="Courier New")

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 2 — THE PROBLEM
# ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(blank_layout)
add_bg(s)
add_rect(s, 0, 0, Inches(0.18), H, CRIMSON)
add_label(s, "The Problem", Inches(0.5), Inches(0.4))
add_text(s, "Bridging the Screening Gap.", Inches(0.5), Inches(0.75),
         Inches(9), Inches(1.1), size=Pt(44), bold=True, color=WHITE, font="Calibri")

# Big stat left
add_rect(s, Inches(0.5), Inches(2.0), Inches(3.8), Inches(3.8), CARD, line_color=CRIMSON, line_w=Pt(1.5))
add_text(s, "25%", Inches(0.6), Inches(2.2), Inches(3.6), Inches(1.4),
         size=Pt(72), bold=True, color=CRIMSON, font="Calibri")
add_text(s, "of the world's population\nhas anemia", Inches(0.6), Inches(3.6),
         Inches(3.6), Inches(0.8), size=Pt(13), color=MUTED, font="Calibri")
add_text(s, "Yet most cases go undetected\ndue to cost and access barriers.",
         Inches(0.6), Inches(4.5), Inches(3.6), Inches(1.0), size=Pt(11), color=DIM, font="Calibri")

# Pain points right
pain = [
    ("💸  Cost", "Blood tests cost $5–$30 — unaffordable in low-income settings."),
    ("🏥  Distance", "Nearest clinic can be hours away for rural communities."),
    ("⏱  Delay", "Results take days. Anemia worsens silently in the meantime."),
    ("📉  Awareness", "Symptoms are vague — fatigue, dizziness — easy to dismiss."),
]
for i, (title, desc) in enumerate(pain):
    py = Inches(2.0) + i * Inches(1.1)
    add_rect(s, Inches(4.7), py, Inches(8.3), Inches(0.95), CARD, line_color=DIM, line_w=Pt(0.75))
    add_text(s, title, Inches(4.9), py+Inches(0.08), Inches(3.0), Inches(0.35),
             size=Pt(12), bold=True, color=WHITE, font="Calibri")
    add_text(s, desc, Inches(4.9), py+Inches(0.42), Inches(8.0), Inches(0.45),
             size=Pt(10), color=MUTED, font="Calibri")

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 3 — THE SOLUTION
# ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(blank_layout)
add_bg(s)
add_rect(s, 0, 0, Inches(0.18), H, CRIMSON)
add_label(s, "The Solution", Inches(0.5), Inches(0.4))
add_text(s, "Your phone is the lab.", Inches(0.5), Inches(0.75),
         Inches(10), Inches(1.1), size=Pt(44), bold=True, color=WHITE, font="Calibri")

add_text(s, "AnemiaLens analyzes the inner lower eyelid (conjunctiva) — when hemoglobin drops,\nthis tissue loses its pink color. Our model detects that pallor non-invasively.",
         Inches(0.5), Inches(1.85), Inches(12.3), Inches(0.9),
         size=Pt(13), color=MUTED, font="Calibri")

# 3 pillars
pillars = [
    ("📷  Capture", "Photograph the inner lower eyelid with any smartphone camera. No special hardware required."),
    ("🧠  Analyze", "EfficientNet-B0 estimates hemoglobin level from conjunctival pallor. Validated on 710 clinical specimens."),
    ("📋  Act", "Structured clinical brief generated instantly. Share with a doctor in one tap."),
]
for i, (title, desc) in enumerate(pillars):
    px = Inches(0.5) + i * Inches(4.25)
    add_rect(s, px, Inches(2.9), Inches(4.0), Inches(3.5), CARD, line_color=CRIMSON, line_w=Pt(1.0))
    add_rect(s, px, Inches(2.9), Inches(4.0), Inches(0.08), CRIMSON)
    add_text(s, title, px+Inches(0.2), Inches(3.1), Inches(3.6), Inches(0.5),
             size=Pt(16), bold=True, color=WHITE, font="Calibri")
    add_text(s, desc, px+Inches(0.2), Inches(3.7), Inches(3.6), Inches(2.4),
             size=Pt(11), color=MUTED, font="Calibri")

# Bottom bar
add_rect(s, Inches(0.5), Inches(6.6), Inches(12.3), Inches(0.55), CARD, line_color=DIM, line_w=Pt(0.75))
add_text(s, "Zero blood draw  ·  Zero hardware  ·  Zero marginal cost  ·  Works offline",
         Inches(0.6), Inches(6.65), Inches(12.0), Inches(0.4),
         size=Pt(11), bold=True, color=CRIMSON, align=PP_ALIGN.CENTER, font="Courier New")

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 4 — HOW IT WORKS (5-step flow)
# ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(blank_layout)
add_bg(s)
add_rect(s, 0, 0, Inches(0.18), H, CRIMSON)
add_label(s, "How It Works", Inches(0.5), Inches(0.4))
add_text(s, "Five steps to screening clarity.", Inches(0.5), Inches(0.75),
         Inches(10), Inches(1.0), size=Pt(40), bold=True, color=WHITE, font="Calibri")

steps = [
    ("01", "Capture", "Photograph inner lower eyelid in bright daylight."),
    ("02", "Quality Gate", "AI rejects blurry or misframed images before analysis."),
    ("03", "Vision AI", "EfficientNet-B0 estimates hemoglobin from pallor."),
    ("04", "Symptom Fusion", "Patient symptoms fuse with image biomarkers."),
    ("05", "Clinical Brief", "Triage band + handoff summary generated instantly."),
]
for i, (num, title, desc) in enumerate(steps):
    sx = Inches(0.5) + i * Inches(2.52)
    # connector line
    if i < 4:
        add_rect(s, sx+Inches(2.1), Inches(2.55), Inches(0.42), Inches(0.06), DIM)
    # card
    add_rect(s, sx, Inches(2.0), Inches(2.3), Inches(3.8), CARD, line_color=DIM, line_w=Pt(0.75))
    add_rect(s, sx, Inches(2.0), Inches(2.3), Inches(0.07), CRIMSON)
    add_text(s, num, sx+Inches(0.15), Inches(2.1), Inches(0.8), Inches(0.5),
             size=Pt(28), bold=True, color=CRIMSON, font="Calibri")
    add_text(s, title, sx+Inches(0.15), Inches(2.65), Inches(2.0), Inches(0.45),
             size=Pt(13), bold=True, color=WHITE, font="Calibri")
    add_text(s, desc, sx+Inches(0.15), Inches(3.15), Inches(2.0), Inches(2.4),
             size=Pt(10), color=MUTED, font="Calibri")

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 5 — TECH STACK
# ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(blank_layout)
add_bg(s)
add_rect(s, 0, 0, Inches(0.18), H, CRIMSON)
add_label(s, "Technology", Inches(0.5), Inches(0.4))
add_text(s, "The Intelligence Framework.", Inches(0.5), Inches(0.75),
         Inches(10), Inches(1.0), size=Pt(40), bold=True, color=WHITE, font="Calibri")

layers = [
    ("Vision Layer", "EfficientNet-B0",
     "Trained on 710 conjunctival specimens. Predicts hemoglobin (g/dL) and anemia risk score from a single image. Runs in <2s on CPU.",
     CRIMSON),
    ("GenAI Layer", "Qwen-2.5 (Grounded)",
     "Generates safe, personalized clinical guidance. Constrained by deterministic medical rules — cannot hallucinate a diagnosis. Every output is rule-validated.",
     AMBER),
    ("Safety Layer", "4-Band Triage System",
     "Low / Moderate / High Concern / Retake. Designed to prioritize patient safety over false confidence. Non-diagnostic language throughout.",
     GREEN),
]
for i, (layer, model, desc, color) in enumerate(layers):
    ly = Inches(2.0) + i * Inches(1.6)
    add_rect(s, Inches(0.5), ly, Inches(12.3), Inches(1.45), CARD, line_color=color, line_w=Pt(1.0))
    add_rect(s, Inches(0.5), ly, Inches(0.12), Inches(1.45), color)
    add_text(s, layer.upper(), Inches(0.75), ly+Inches(0.1), Inches(2.5), Inches(0.3),
             size=Pt(8), bold=True, color=color, font="Courier New")
    add_text(s, model, Inches(0.75), ly+Inches(0.38), Inches(3.5), Inches(0.5),
             size=Pt(18), bold=True, color=WHITE, font="Calibri")
    add_text(s, desc, Inches(4.5), ly+Inches(0.2), Inches(8.1), Inches(1.0),
             size=Pt(11), color=MUTED, font="Calibri")

# Stack tags bottom
tags = ["React + Vite", "FastAPI", "EfficientNet-B0", "Qwen-2.5", "Python 3.11", "No cloud dependency"]
for i, tag in enumerate(tags):
    tx = Inches(0.5) + i * Inches(2.1)
    add_rect(s, tx, Inches(6.75), Inches(1.95), Inches(0.45), CARD, line_color=DIM, line_w=Pt(0.75))
    add_text(s, tag, tx+Inches(0.1), Inches(6.78), Inches(1.75), Inches(0.35),
             size=Pt(9), color=MUTED, align=PP_ALIGN.CENTER, font="Courier New")

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 6 — DEMO RESULTS (mock output)
# ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(blank_layout)
add_bg(s)
add_rect(s, 0, 0, Inches(0.18), H, CRIMSON)
add_label(s, "Live Demo Output", Inches(0.5), Inches(0.4))
add_text(s, "Real screening result.", Inches(0.5), Inches(0.75),
         Inches(10), Inches(1.0), size=Pt(40), bold=True, color=WHITE, font="Calibri")

# Triage card
add_rect(s, Inches(0.5), Inches(1.9), Inches(5.8), Inches(4.8), CARD,
         line_color=AMBER, line_w=Pt(1.5))
add_rect(s, Inches(0.5), Inches(1.9), Inches(0.12), Inches(4.8), AMBER)
add_text(s, "MODERATE RISK", Inches(0.75), Inches(2.0), Inches(5.0), Inches(0.4),
         size=Pt(9), bold=True, color=AMBER, font="Courier New")
add_text(s, "9.8", Inches(0.75), Inches(2.4), Inches(3.0), Inches(1.4),
         size=Pt(80), bold=True, color=AMBER, font="Calibri")
add_text(s, "g/dL  Hemoglobin", Inches(0.75), Inches(3.8), Inches(5.0), Inches(0.4),
         size=Pt(12), color=MUTED, font="Courier New")
add_text(s, "Hemoglobin below normal range. Clinical follow-up\nrecommended within 1–2 weeks.",
         Inches(0.75), Inches(4.3), Inches(5.2), Inches(0.8),
         size=Pt(11), color=MUTED, font="Calibri")

# Stat chips
stats = [("68%", "Anemia Risk"), ("88%", "Confidence"), ("Band 2", "Triage")]
for i, (val, lbl) in enumerate(stats):
    sx = Inches(0.75) + i * Inches(1.8)
    add_rect(s, sx, Inches(5.3), Inches(1.6), Inches(0.9), VOID, line_color=DIM, line_w=Pt(0.75))
    add_text(s, val, sx+Inches(0.1), Inches(5.35), Inches(1.4), Inches(0.4),
             size=Pt(18), bold=True, color=WHITE, font="Calibri")
    add_text(s, lbl, sx+Inches(0.1), Inches(5.72), Inches(1.4), Inches(0.3),
             size=Pt(8), color=MUTED, font="Courier New")

# Handoff terminal
add_rect(s, Inches(6.6), Inches(1.9), Inches(6.4), Inches(4.8), RGBColor(0x00,0x00,0x00),
         line_color=CRIMSON, line_w=Pt(1.0))
add_text(s, "CLINICAL HANDOFF BRIEF", Inches(6.8), Inches(2.0), Inches(6.0), Inches(0.35),
         size=Pt(8), bold=True, color=CRIMSON, font="Courier New")
terminal_lines = [
    ("Provider:",       "EfficientNet-B0"),
    ("Risk Score:",     "68.4% (Moderate)"),
    ("Hb Estimate:",    "9.8 g/dL"),
    ("Confidence:",     "88%"),
    ("Triage Band:",    "Band 2 — Monitor"),
    ("Symptoms:",       "Fatigue, Dizziness"),
    ("Next Step:",      "CBC within 1–2 weeks"),
    ("Disclaimer:",     "Screening only. Not diagnostic."),
]
for i, (key, val) in enumerate(terminal_lines):
    ty = Inches(2.5) + i * Inches(0.42)
    add_text(s, key, Inches(6.8), ty, Inches(1.8), Inches(0.38),
             size=Pt(10), color=CRIMSON, font="Courier New")
    add_text(s, val, Inches(8.7), ty, Inches(4.0), Inches(0.38),
             size=Pt(10), color=WHITE, font="Courier New")

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 7 — IMPACT & SDGs
# ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(blank_layout)
add_bg(s)
add_rect(s, 0, 0, Inches(0.18), H, CRIMSON)
add_label(s, "Impact", Inches(0.5), Inches(0.4))
add_text(s, "Designed for the last mile.", Inches(0.5), Inches(0.75),
         Inches(10), Inches(1.0), size=Pt(40), bold=True, color=WHITE, font="Calibri")

impacts = [
    ("Community Health Workers",
     "Deploy in rural India, sub-Saharan Africa, or any low-resource setting. No training beyond a 5-minute guide."),
    ("Pregnant Women & Children",
     "The highest-risk groups — who are also least likely to access a clinic. AnemiaLens meets them where they are."),
    ("School & Field Nurses",
     "Rapid triage in schools, refugee camps, and disaster zones. Results in under 60 seconds."),
    ("Telemedicine Platforms",
     "Structured clinical brief integrates directly into existing telehealth workflows via share/export."),
]
for i, (title, desc) in enumerate(impacts):
    ix = Inches(0.5) + (i % 2) * Inches(6.3)
    iy = Inches(2.0) + (i // 2) * Inches(2.1)
    add_rect(s, ix, iy, Inches(6.0), Inches(1.85), CARD, line_color=DIM, line_w=Pt(0.75))
    add_rect(s, ix, iy, Inches(0.08), Inches(1.85), CRIMSON)
    add_text(s, title, ix+Inches(0.2), iy+Inches(0.12), Inches(5.6), Inches(0.4),
             size=Pt(13), bold=True, color=WHITE, font="Calibri")
    add_text(s, desc, ix+Inches(0.2), iy+Inches(0.55), Inches(5.6), Inches(1.1),
             size=Pt(10), color=MUTED, font="Calibri")

# SDG badges
add_rect(s, Inches(0.5), Inches(6.35), Inches(12.3), Inches(0.8), CARD, line_color=DIM, line_w=Pt(0.75))
add_text(s, "UN SDG 3: Good Health & Well-Being   ·   UN SDG 10: Reduced Inequalities   ·   UN SDG 1: No Poverty",
         Inches(0.6), Inches(6.45), Inches(12.0), Inches(0.5),
         size=Pt(11), bold=True, color=CRIMSON, align=PP_ALIGN.CENTER, font="Courier New")

# ─────────────────────────────────────────────────────────────────────────────
# SLIDE 8 — CLOSE / CALL TO ACTION
# ─────────────────────────────────────────────────────────────────────────────
s = prs.slides.add_slide(blank_layout)
add_bg(s)
add_rect(s, 0, 0, Inches(0.18), H, CRIMSON)

# Big crimson accent block
add_rect(s, Inches(0.5), Inches(1.5), Inches(12.3), Inches(0.08), CRIMSON)

add_text(s, "AnemiaLens doesn't replace doctors.", Inches(0.5), Inches(1.8),
         Inches(12.3), Inches(1.1), size=Pt(36), bold=True, color=WHITE,
         align=PP_ALIGN.CENTER, font="Calibri")
add_text(s, "It gets patients to doctors sooner,\nwith better information, at zero cost.",
         Inches(0.5), Inches(2.9), Inches(12.3), Inches(1.2),
         size=Pt(28), color=MUTED, align=PP_ALIGN.CENTER, font="Calibri")

add_rect(s, Inches(0.5), Inches(4.2), Inches(12.3), Inches(0.08), CRIMSON)

# Final stats row
final_stats = [
    ("1.6B+", "People we can reach"),
    ("92%",   "Sensitivity"),
    ("$0",    "Marginal cost per screening"),
    ("<60s",  "Time to result"),
]
for i, (val, lbl) in enumerate(final_stats):
    fx = Inches(0.5) + i * Inches(3.1)
    add_text(s, val, fx, Inches(4.6), Inches(2.9), Inches(0.9),
             size=Pt(40), bold=True, color=CRIMSON, align=PP_ALIGN.CENTER, font="Calibri")
    add_text(s, lbl, fx, Inches(5.5), Inches(2.9), Inches(0.4),
             size=Pt(10), color=MUTED, align=PP_ALIGN.CENTER, font="Courier New")

add_text(s, "Thank you.", Inches(0.5), Inches(6.2),
         Inches(12.3), Inches(0.8), size=Pt(22), bold=True, color=WHITE,
         align=PP_ALIGN.CENTER, font="Calibri")

# ─────────────────────────────────────────────────────────────────────────────
prs.save("AnemiaLens_Presentation.pptx")
print("Done → AnemiaLens_Presentation.pptx")
