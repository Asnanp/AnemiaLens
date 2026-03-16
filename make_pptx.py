from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

prs = Presentation()
prs.slide_width  = Inches(13.33)
prs.slide_height = Inches(7.5)

DARK_BG   = RGBColor(0x0D, 0x1B, 0x2A)
ACCENT    = RGBColor(0x00, 0xC2, 0xFF)
WHITE     = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT     = RGBColor(0xB0, 0xC4, 0xDE)
GREEN     = RGBColor(0x00, 0xE5, 0x96)
YELLOW    = RGBColor(0xFF, 0xD6, 0x00)

def blank_slide(prs):
    layout = prs.slide_layouts[6]
    slide  = prs.slides.add_slide(layout)
    bg = slide.background.fill
    bg.solid()
    bg.fore_color.rgb = DARK_BG
    return slide

def add_box(slide, text, l, t, w, h, size=28, bold=False, color=WHITE,
            align=PP_ALIGN.LEFT, wrap=True):
    txb = slide.shapes.add_textbox(Inches(l), Inches(t), Inches(w), Inches(h))
    txb.word_wrap = wrap
    tf = txb.text_frame
    tf.word_wrap = wrap
    p  = tf.paragraphs[0]
    p.alignment = align
    run = p.add_run()
    run.text = text
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = color
    return txb

def accent_bar(slide, t=1.1):
    bar = slide.shapes.add_shape(1, Inches(0.5), Inches(t), Inches(0.06), Inches(0.55))
    bar.fill.solid(); bar.fill.fore_color.rgb = ACCENT
    bar.line.fill.background()

def slide_number(slide, n):
    add_box(slide, str(n), 12.6, 7.1, 0.5, 0.3, size=11, color=LIGHT, align=PP_ALIGN.RIGHT)

# ── Slide 1 — Title ──────────────────────────────────────────────────────────
s1 = blank_slide(prs)
add_box(s1, "AnemiaLens", 0.5, 1.5, 9, 1.4, size=60, bold=True, color=ACCENT)
add_box(s1, "Non-invasive anemia screening from a single eye photo", 0.5, 3.0, 10, 0.8, size=24, color=LIGHT)
add_box(s1, "Live: anemia-lens.vercel.app", 0.5, 4.0, 8, 0.5, size=18, color=GREEN)
add_box(s1, "GitHub: github.com/Asnanp/AnemiaLens", 0.5, 4.6, 8, 0.5, size=18, color=LIGHT)
accent_bar(s1, 1.4)
slide_number(s1, 1)

# ── Slide 2 — Problem ────────────────────────────────────────────────────────
s2 = blank_slide(prs)
accent_bar(s2)
add_box(s2, "The Problem", 0.7, 0.9, 10, 0.7, size=36, bold=True, color=WHITE)
lines = [
    "2 billion people worldwide suffer from anemia",
    "Traditional diagnosis requires blood tests — invasive, costly, inaccessible",
    "Rural & low-income communities have no access to labs",
    "Delayed diagnosis leads to preventable complications",
    "Children and pregnant women are most at risk",
]
for i, line in enumerate(lines):
    add_box(s2, f"• {line}", 0.7, 1.9 + i*0.9, 11.5, 0.75, size=20, color=LIGHT)
slide_number(s2, 2)

# ── Slide 3 — Solution ───────────────────────────────────────────────────────
s3 = blank_slide(prs)
accent_bar(s3)
add_box(s3, "The Solution", 0.7, 0.9, 10, 0.7, size=36, bold=True, color=WHITE)
add_box(s3, "AnemiaLens uses the palpebral conjunctiva (inner eyelid) — a clinically validated\nindicator of hemoglobin levels — analyzed by AI from a smartphone photo.",
        0.7, 1.75, 11.5, 1.1, size=19, color=LIGHT)
stats = [
    ("94.2%", "Deployed Accuracy"),
    ("88.9%", "Sensitivity (Recall)"),
    ("94.5%", "AUC Score"),
    ("90.2%", "F1 Score"),
]
for i, (val, label) in enumerate(stats):
    x = 0.7 + i * 3.1
    add_box(s3, val,   x, 3.1, 2.8, 0.7, size=34, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
    add_box(s3, label, x, 3.85, 2.8, 0.45, size=15, color=LIGHT, align=PP_ALIGN.CENTER)
add_box(s3, "Try it live at anemia-lens.vercel.app", 0.7, 4.7, 11.5, 0.5, size=18, color=GREEN)
slide_number(s3, 3)

# ── Slide 4 — How it Works ───────────────────────────────────────────────────
s4 = blank_slide(prs)
accent_bar(s4)
add_box(s4, "How It Works", 0.7, 0.9, 10, 0.7, size=36, bold=True, color=WHITE)
steps = [
    ("1", "Capture",        "User photographs inner eyelid with smartphone"),
    ("2", "Quality Check",  "AI validates image sharpness, framing & lighting"),
    ("3", "ROI Extraction", "EfficientNet-B0 isolates the conjunctiva region"),
    ("4", "Prediction",     "Ensemble model estimates hemoglobin & anemia risk"),
    ("5", "Triage",         "Risk band assigned: Low / Moderate / High Concern"),
    ("6", "GenAI Guidance", "Qwen 2.5 generates personalized next-step advice in plain language"),
]
for i, (num, title, desc) in enumerate(steps):
    row = i // 3
    col = i % 3
    x = 0.5 + col * 4.25
    y = 1.85 + row * 2.3
    box = s4.shapes.add_shape(1, Inches(x), Inches(y), Inches(3.9), Inches(2.0))
    box.fill.solid(); box.fill.fore_color.rgb = RGBColor(0x10, 0x28, 0x3E)
    box.line.color.rgb = ACCENT
    add_box(s4, f"{num}. {title}", x+0.12, y+0.1, 3.65, 0.45, size=16, bold=True, color=ACCENT)
    add_box(s4, desc, x+0.12, y+0.55, 3.65, 1.3, size=13, color=LIGHT, wrap=True)
slide_number(s4, 4)

# ── Slide 5 — Technology Stack ───────────────────────────────────────────────
s5 = blank_slide(prs)
accent_bar(s5)
add_box(s5, "Technology Stack", 0.7, 0.9, 10, 0.7, size=36, bold=True, color=WHITE)
tech = [
    ("Frontend",  "React + Vite",              "Deployed on Vercel",              ACCENT),
    ("Backend",   "FastAPI / Flask",            "Deployed on Render",              GREEN),
    ("Vision AI", "EfficientNet-B0",            "Conjunctiva ROI + Hb prediction", YELLOW),
    ("GenAI",     "Qwen 2.5 via HuggingFace",  "Personalized guidance generation",RGBColor(0xFF,0x7A,0x00)),
    ("Runtime",   "Python 3.12",               "Ensemble + CatBoost stack",       LIGHT),
]
for i, (layer, name, detail, col) in enumerate(tech):
    y = 1.85 + i * 0.98
    add_box(s5, layer,  0.7,  y, 2.2,  0.7, size=16, bold=True, color=col)
    add_box(s5, name,   3.1,  y, 4.0,  0.7, size=16, bold=True, color=WHITE)
    add_box(s5, detail, 7.3,  y, 5.5,  0.7, size=15, color=LIGHT)
    line = s5.shapes.add_shape(1, Inches(0.7), Inches(y+0.72), Inches(12.1), Inches(0.02))
    line.fill.solid(); line.fill.fore_color.rgb = RGBColor(0x1E, 0x3A, 0x52)
    line.line.fill.background()
slide_number(s5, 5)

# ── Slide 6 — Live Demo ──────────────────────────────────────────────────────
s6 = blank_slide(prs)
accent_bar(s6)
add_box(s6, "Live Demo", 0.7, 0.9, 10, 0.7, size=36, bold=True, color=WHITE)
add_box(s6, "Try it yourself — no install, no signup required.", 0.7, 1.85, 11.5, 0.6, size=22, color=LIGHT)

url_box = s6.shapes.add_shape(1, Inches(1.5), Inches(2.8), Inches(10.3), Inches(1.1))
url_box.fill.solid(); url_box.fill.fore_color.rgb = RGBColor(0x00, 0x2A, 0x40)
url_box.line.color.rgb = ACCENT
add_box(s6, "anemia-lens.vercel.app", 1.5, 2.85, 10.3, 0.9, size=32, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)

demo_steps = [
    "Open the URL on any device with a camera",
    "Take a close-up photo of your inner lower eyelid",
    "Get instant AI-powered anemia risk assessment",
    "Receive personalized guidance from Qwen 2.5 GenAI",
]
for i, step in enumerate(demo_steps):
    add_box(s6, f"  {i+1}.  {step}", 0.7, 4.15 + i*0.62, 11.5, 0.55, size=18, color=LIGHT)
slide_number(s6, 6)

# ── Slide 7 — AI-Native Development ─────────────────────────────────────────
s7 = blank_slide(prs)
accent_bar(s7)
add_box(s7, "Built AI-Native", 0.7, 0.9, 10, 0.7, size=36, bold=True, color=WHITE)
add_box(s7, "Every layer of AnemiaLens was built using AI-native tools and workflows.",
        0.7, 1.75, 11.5, 0.6, size=19, color=LIGHT)
ai_items = [
    (ACCENT,  "Code Generation",    "Claude & Codex used for architecture, API design, and component scaffolding"),
    (GREEN,   "Model Training",     "EfficientNet-B0 fine-tuned with AI-assisted hyperparameter selection"),
    (YELLOW,  "GenAI Integration",  "Qwen 2.5 via HuggingFace Inference API for real-time guidance generation"),
    (RGBColor(0xFF,0x7A,0x00), "Testing & Debug", "AI-assisted test generation, error analysis, and edge case discovery"),
    (LIGHT,   "Deployment",         "Vercel (frontend) + Render (backend) — zero-config AI-recommended setup"),
]
for i, (col, title, desc) in enumerate(ai_items):
    y = 2.55 + i * 0.92
    dot = s7.shapes.add_shape(9, Inches(0.7), Inches(y+0.12), Inches(0.22), Inches(0.22))
    dot.fill.solid(); dot.fill.fore_color.rgb = col
    dot.line.fill.background()
    add_box(s7, title, 1.1, y, 2.8, 0.6, size=17, bold=True, color=col)
    add_box(s7, desc,  4.1, y, 8.8, 0.6, size=16, color=LIGHT)
slide_number(s7, 7)

# ── Slide 8 — Closing ────────────────────────────────────────────────────────
s8 = blank_slide(prs)
add_box(s8, "AnemiaLens", 0.5, 1.2, 12, 1.1, size=54, bold=True, color=ACCENT, align=PP_ALIGN.CENTER)
add_box(s8, "Making anemia screening accessible to everyone, everywhere.",
        0.5, 2.5, 12.3, 0.7, size=22, color=LIGHT, align=PP_ALIGN.CENTER)

info = [
    ("Live App",  "anemia-lens.vercel.app",          GREEN),
    ("GitHub",    "github.com/Asnanp/AnemiaLens",    ACCENT),
    ("Built with","AI-native tools — Claude, Codex, HuggingFace", LIGHT),
]
for i, (label, val, col) in enumerate(info):
    y = 3.55 + i * 0.78
    add_box(s8, label + ":", 1.8, y, 2.2, 0.6, size=18, bold=True, color=LIGHT, align=PP_ALIGN.RIGHT)
    add_box(s8, val,         4.2, y, 8.0, 0.6, size=18, bold=True, color=col)

accent_bar(s8, 6.8)
slide_number(s8, 8)

prs.save("AnemiaLens_Presentation_v2.pptx")
print("Done — AnemiaLens_Presentation_v2.pptx")
