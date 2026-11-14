
"""Build the INGRES presentation deck (dark theme, 16:9)."""
import os
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

BASE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE, "..", "..", ".."))
SHOTS = os.path.join(BASE, "..", "screenshots")
OUT = os.path.join(BASE, "..", "INGRES_Presentation.pptx")

BG      = RGBColor(0x0E, 0x11, 0x17)
PANEL   = RGBColor(0x16, 0x1B, 0x22)
PANEL2  = RGBColor(0x1C, 0x24, 0x30)
BORDER  = RGBColor(0x30, 0x36, 0x3D)
TEXT    = RGBColor(0xE6, 0xED, 0xF3)
MUTED   = RGBColor(0x8B, 0x94, 0x9E)
TEAL    = RGBColor(0x2D, 0xD4, 0xBF)
BLUE    = RGBColor(0x58, 0xA6, 0xFF)
ORANGE  = RGBColor(0xF5, 0x9E, 0x0B)
RED     = RGBColor(0xF8, 0x71, 0x71)
GREEN   = RGBColor(0x3F, 0xD5, 0x8C)
WHITE   = RGBColor(0xFF, 0xFF, 0xFF)

BODY = "Segoe UI"
HEAD = "Segoe UI Semibold"
MONO = "Consolas"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]

TOTAL = 17

def new_slide(bg_color=BG):
    s = prs.slides.add_slide(BLANK)
    fill = s.background.fill
    fill.solid()
    fill.fore_color.rgb = bg_color
    return s

def box(slide, x, y, w, h, fill=PANEL, line=BORDER, radius=0.04, lw=1.0):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    try:
        shp.adjustments[0] = radius
    except Exception:
        pass
    shp.fill.solid()
    shp.fill.fore_color.rgb = fill
    shp.line.color.rgb = line
    shp.line.width = Pt(lw)
    shp.shadow.inherit = False
    return shp

def textbox(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP, margins=(0, 0, 0, 0)):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = Inches(margins[0]); tf.margin_right = Inches(margins[1])
    tf.margin_top = Inches(margins[2]); tf.margin_bottom = Inches(margins[3])
    return tf

def para(tf, text, size=16, color=TEXT, bold=False, font=BODY, align=PP_ALIGN.LEFT,
         space_before=0, space_after=4, line=1.12, first=False, italic=False):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_before = Pt(space_before)
    p.space_after = Pt(space_after)
    p.line_spacing = line
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size); r.font.bold = bold; r.font.name = font; r.font.italic = italic
    r.font.color.rgb = color
    return p

def tag(slide, text, color=TEAL):
    tf = textbox(slide, 0.62, 0.36, 8.0, 0.3)
    para(tf, text.upper(), size=10.5, color=color, bold=True, font=HEAD, first=True, space_after=0)

def heading(slide, title, sub=None, size=29):
    tf = textbox(slide, 0.62, 0.66, 12.1, 0.8)
    para(tf, title, size=size, color=TEXT, bold=True, font=HEAD, first=True, space_after=0, line=1.0)
    if sub:
        tf2 = textbox(slide, 0.62, 1.24, 12.1, 0.5)
        para(tf2, sub, size=13.5, color=MUTED, first=True, space_after=0, line=1.15)

def footer(slide, num):
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.62), Inches(7.05), Inches(12.09), Pt(0.75))
    line.fill.solid(); line.fill.fore_color.rgb = BORDER; line.line.fill.background(); line.shadow.inherit = False
    tf = textbox(slide, 0.62, 7.12, 7.5, 0.25)
    para(tf, "INGRES · National Groundwater Intelligence Platform", size=9, color=MUTED, first=True, space_after=0)
    tf2 = textbox(slide, 10.7, 7.12, 2.0, 0.25)
    para(tf2, "%02d / %d" % (num, TOTAL), size=9, color=MUTED, align=PP_ALIGN.RIGHT, first=True, space_after=0)

def notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text

def bullets(slide, x, y, w, h, items, size=14, gap=7, color=TEXT, bullet_color=TEAL, lead=0.24):
    tf = textbox(slide, x, y, w, h)
    first = True
    for it in items:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_before = Pt(0); p.space_after = Pt(gap); p.line_spacing = 1.12
        r0 = p.add_run(); r0.text = "▸  "
        r0.font.size = Pt(size); r0.font.name = BODY; r0.font.color.rgb = bullet_color; r0.font.bold = True
        r = p.add_run(); r.text = it
        r.font.size = Pt(size); r.font.name = BODY; r.font.color.rgb = color
    return tf

def metric(slide, x, y, w, value, label, color=TEAL, vsize=30, lsize=10.5):
    tf = textbox(slide, x, y, w, 0.75)
    para(tf, value, size=vsize, color=color, bold=True, font=HEAD, first=True, space_after=0, line=0.95)
    tf2 = textbox(slide, x, y + 0.55, w, 0.5)
    para(tf2, label.upper(), size=lsize, color=MUTED, bold=True, first=True, space_after=0, line=1.0)

def chip(slide, x, y, text, color=TEAL, fill=PANEL2, size=11):
    w = 0.105 * len(text) + 0.38
    shp = box(slide, x, y, w, 0.34, fill=fill, line=BORDER, radius=0.5)
    tf = shp.text_frame
    tf.word_wrap = False
    tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
    p = tf.paragraphs[0]; p.alignment = PP_ALIGN.CENTER
    r = p.add_run(); r.text = text
    r.font.size = Pt(size); r.font.name = BODY; r.font.color.rgb = color; r.font.bold = True
    return x + w

def picture(slide, filename, x, y, max_w, max_h, border=True):
    path = os.path.join(SHOTS, filename)
    iw, ih = Image.open(path).size
    scale = min(max_w / iw, max_h / ih)
    w, h = iw * scale, ih * scale
    left = x + (max_w - w) / 2
    top = y + (max_h - h) / 2
    pic = slide.shapes.add_picture(path, Inches(left), Inches(top), Inches(w), Inches(h))
    if border:
        pic.line.color.rgb = BORDER
        pic.line.width = Pt(0.75)
    pic.shadow.inherit = False
    return pic, (left, top, w, h)

def caption(slide, x, y, w, text):
    tf = textbox(slide, x, y, w, 0.35)
    para(tf, text, size=9.5, color=MUTED, italic=True, first=True, space_after=0)

# ─────────────────────────────────────────────────────────────────────────────
# 1 · Title
s = new_slide()
bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.16), Inches(7.5))
bar.fill.solid(); bar.fill.fore_color.rgb = TEAL; bar.line.fill.background(); bar.shadow.inherit = False

tf = textbox(s, 0.95, 1.65, 11.8, 1.3)
para(tf, "INGRES", size=74, color=WHITE, bold=True, font=HEAD, first=True, space_after=0, line=0.95)
tf = textbox(s, 0.98, 2.95, 11.8, 0.6)
para(tf, "National Groundwater Intelligence Platform", size=25, color=TEAL, font=HEAD, first=True, space_after=0)
line = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.98), Inches(3.72), Inches(4.2), Pt(2))
line.fill.solid(); line.fill.fore_color.rgb = BLUE; line.line.fill.background(); line.shadow.inherit = False
tf = textbox(s, 0.98, 3.98, 9.9, 1.0)
para(tf, "Grounded, cited answers over 3,042 CGWB monitoring stations — deterministic SQL, pre-answer coverage guardrails and BIS 10500 water-quality intelligence.",
     size=14.5, color=MUTED, first=True, space_after=0, line=1.35)

metrics = [("3,042", "MONITORING STATIONS"), ("16,780", "WATER-LEVEL RECORDS"), ("11,978", "LAB QUALITY TESTS"), ("100%", "PROVENANCE PRECISION")]
mx = 0.98
for value, label in metrics:
    tf = textbox(s, mx, 5.35, 2.6, 0.55)
    para(tf, value, size=26, color=WHITE, bold=True, font=HEAD, first=True, space_after=0, line=1.0)
    tf2 = textbox(s, mx, 5.92, 2.7, 0.3)
    para(tf2, label, size=9, color=MUTED, bold=True, first=True, space_after=0)
    mx += 2.95

tf = textbox(s, 0.98, 6.72, 8.5, 0.3)
para(tf, "SIH 2026 · Problem Code SIH26063 · CGWB / NWIC · GEC-2015 · BIS 10500:2012", size=10, color=MUTED, first=True, space_after=0)
tf = textbox(s, 9.6, 6.5, 3.1, 0.6)
para(tf, "Technical showcase", size=10, color=TEAL, align=PP_ALIGN.RIGHT, bold=True, first=True, space_after=0)
para(tf, "November 2026", size=10, color=MUTED, align=PP_ALIGN.RIGHT, space_after=0)
notes(s, "INGRES turns national groundwater data into verifiable answers. Everything shown in this deck is captured from the working Streamlit application.")

# 2 · Problem
s = new_slide()
tag(s, "01 · The problem")
heading(s, "India's groundwater data is rich. Its answers are not.",
        "Three bottlenecks keep decision-makers from trusted, station-level evidence.")
cards = [
    ("Siloed by design", "Millions of readings split across CGWB manual hydrographs, DWLR telemetry and laboratory sheets — with no single queryable source of truth.", ORANGE),
    ("Numbers that don't exist", "Generic LLMs fabricate water levels, invent stations and misread trends. For water security, a plausible answer is a dangerous answer.", RED),
    ("No provenance, no boundaries", "Answers arrive without station IDs, dates or quality flags — and never state when a district or season is simply not covered.", BLUE),
]
x = 0.62
for title, body, col in cards:
    box(s, x, 1.85, 3.88, 2.3, PANEL, BORDER)
    strip = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(1.85), Inches(0.07), Inches(2.3))
    strip.fill.solid(); strip.fill.fore_color.rgb = col; strip.line.fill.background(); strip.shadow.inherit = False
    tf = textbox(s, x + 0.3, 2.05, 3.35, 0.45)
    para(tf, title, size=17, color=col, bold=True, font=HEAD, first=True, space_after=0)
    tf = textbox(s, x + 0.3, 2.55, 3.35, 1.6)
    para(tf, body, size=12, color=TEXT, first=True, space_after=0, line=1.3)
    x += 4.1

stats = [("60%+", "of irrigated agriculture depends on groundwater"), ("85%", "of rural drinking water comes from aquifers"),
         ("8", "assessment units already over-exploited"), ("997", "laboratory samples fail BIS limits")]
x = 0.62
for value, label in stats:
    tf = textbox(s, x, 4.85, 2.95, 0.5)
    para(tf, value, size=27, color=WHITE, bold=True, font=HEAD, first=True, space_after=0, line=1.0)
    tf2 = textbox(s, x, 5.4, 2.85, 0.7)
    para(tf2, label, size=10.5, color=MUTED, first=True, space_after=0, line=1.2)
    x += 3.13
footer(s, 2)
notes(s, "Groundwater is India's invisible lifeline, but the evidence layer is fragmented and generative AI makes fabrication easy. These numbers are drawn from the indexed database and CGWB context.")

# 3 · Solution
s = new_slide()
tag(s, "02 · The solution")
heading(s, "A deterministic evidence engine — not another chatbot.",
        "INGRES retrieves first, checks coverage, then generates only from what the database proves.")
pillars = [
    ("Deterministic SQL", "Template-first Text-to-SQL over DuckDB. SELECT-only execution, automatic LIMIT 500, schema-aware generation.", TEAL),
    ("Pre-answer guardrails", "Five coverage rules run before generation: out-of-range years, vague places, missing parameters, thin trends, station density.", ORANGE),
    ("Cited provenance", "Every value carries station ID, date and quality flag. Evidence table, executed SQL and CSV export on every answer.", BLUE),
    ("Provider freedom", "OpenRouter, Gemini, OpenAI or local models — with a zero-key deterministic synthesizer as an offline fallback.", GREEN),
]
x = 0.62
for title, body, col in pillars:
    box(s, x, 1.9, 3.0, 2.45, PANEL, BORDER)
    tf = textbox(s, x + 0.22, 2.08, 2.6, 0.4)
    para(tf, title, size=15.5, color=col, bold=True, font=HEAD, first=True, space_after=0)
    tf = textbox(s, x + 0.22, 2.5, 2.58, 1.9)
    para(tf, body, size=11, color=TEXT, first=True, space_after=0, line=1.28)
    x += 3.07

box(s, 0.62, 4.9, 12.09, 1.3, PANEL2, BORDER)
vals = [("3,042", "stations indexed"), ("16,780", "seasonal observations"), ("11,978", "chemical samples"), ("100", "GEC-2015 units"), ("30", "benchmark queries")]
x = 0.95
for value, label in vals:
    tf = textbox(s, x, 5.15, 2.2, 0.5)
    para(tf, value, size=24, color=TEAL, bold=True, font=HEAD, first=True, space_after=0, line=1.0)
    tf2 = textbox(s, x, 5.65, 2.2, 0.3)
    para(tf2, label, size=9.5, color=MUTED, first=True, space_after=0)
    x += 2.36
footer(s, 3)
notes(s, "Four design pillars: deterministic retrieval, coverage checks before generation, provenance on every number, and provider flexibility with an offline fallback.")

# 4 · Dashboard
s = new_slide()
tag(s, "03 · Executive command center")
heading(s, "One screen for national groundwater posture.")
picture(s, "user_01_dashboard_kpis.png", 0.62, 1.55, 8.55, 4.95)
bullets(s, 9.42, 1.75, 3.35, 4.5, [
    "Live KPI strip: 3,042 stations, 16,780 observations, 11,978 lab tests",
    "Extraction intensity vs the 100% GEC critical threshold",
    "Contamination watch: TDS, fluoride, nitrate, arsenic",
    "Potability 91.7%; 8 over-exploited assessment units",
    "Every module reachable from the sidebar",
], size=12.5)
caption(s, 0.62, 6.62, 8.5, "Live capture — Executive dashboard, dark theme, indexed database.")
footer(s, 4)
notes(s, "The dashboard is the executive summary: national station counts, extraction intensity by state, and a contamination watch list.")

# 5 · Architecture (full bleed)
s = new_slide()
picture(s, os.path.join("..", "build", "architecture_dark.png"), 0.42, 0.35, 12.5, 6.25)
footer(s, 5)
notes(s, "The pipeline: router, coverage detector, hybrid retrieval, context assembly, generation, and a provenance envelope. The data plane is DuckDB plus a curated knowledge base plus live NWIC ingestion.")

# 6 · Query lifecycle
s = new_slide()
tag(s, "04 · How it works")
heading(s, "Seven stages between a question and a cited answer.")
steps = [
    ("1", "Route", "Intent + entities — structured level, quality, assessment, conceptual, ambiguous or out-of-scope."),
    ("2", "Check coverage", "Five deterministic rules return FULL, PARTIAL, INSUFFICIENT or OUT_OF_SCOPE before any generation."),
    ("3", "Retrieve", "Template SQL, or a schema-aware LLM query, executed read-only against DuckDB; vector KB for concepts."),
    ("4", "Assemble", "Dataframe to markdown, summary statistics, BIS violation counts and GEC category counts."),
    ("5", "Generate", "Strict grounding prompt with the retrieved table, statistics, SQL and coverage status."),
    ("6", "Classify", "Six response states and four confidence levels derived from data quality and well coverage."),
    ("7", "Prove", "Evidence table, executed SQL, source IDs, CSV export and a human-review escalation path."),
]
y = 1.62
for num, title, body in steps:
    tf = textbox(s, 0.62, y, 0.4, 0.45)
    para(tf, num, size=15, color=TEAL, bold=True, font=HEAD, first=True, space_after=0)
    tf = textbox(s, 1.02, y - 0.02, 1.75, 0.4)
    para(tf, title, size=14, color=TEXT, bold=True, font=HEAD, first=True, space_after=0)
    tf = textbox(s, 2.85, y, 4.5, 0.55)
    para(tf, body, size=10.5, color=MUTED, first=True, space_after=0, line=1.12)
    y += 0.73

box(s, 7.55, 1.62, 5.16, 4.95, PANEL, BORDER)
tf = textbox(s, 7.8, 1.78, 4.7, 0.3)
para(tf, "EXECUTED SQL — READ-ONLY, CAPPED", size=9.5, color=TEAL, bold=True, font=HEAD, first=True, space_after=0)
tf = textbox(s, 7.8, 2.1, 4.72, 2.2)
para(tf, "SELECT w.district, q.sample_date,", size=10, color=BLUE, font=MONO, first=True, space_after=0, line=1.25)
para(tf, "       q.fluoride_mg_l, q.potability", size=10, color=BLUE, font=MONO, space_after=0, line=1.25)
para(tf, "FROM gw_quality q", size=10, color=BLUE, font=MONO, space_after=0, line=1.25)
para(tf, "JOIN wells w ON q.well_id = w.well_id", size=10, color=BLUE, font=MONO, space_after=0, line=1.25)
para(tf, "WHERE LOWER(w.district) = 'nalgonda'", size=10, color=BLUE, font=MONO, space_after=0, line=1.25)
para(tf, "LIMIT 500;", size=10, color=BLUE, font=MONO, space_after=0, line=1.25)
line = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(7.8), Inches(3.5), Inches(4.65), Pt(0.75))
line.fill.solid(); line.fill.fore_color.rgb = BORDER; line.line.fill.background(); line.shadow.inherit = False
tf = textbox(s, 7.8, 3.62, 4.68, 0.8)
para(tf, "ANSWER + EVIDENCE", size=9.5, color=TEAL, bold=True, font=HEAD, first=True, space_after=4)
para(tf, "6 Nalgonda samples, fluoride 1.82–4.38 mg/L, all six flagged non-potable under BIS 10500 — station IDs and dates attached.", size=10, color=TEXT, space_after=0, line=1.2)
tf = textbox(s, 7.8, 4.5, 4.68, 0.9)
para(tf, "STATES", size=9.5, color=TEAL, bold=True, font=HEAD, first=True, space_after=4)
para(tf, "Grounded · Partial · Inferred · Insufficient · Out of scope · Human review", size=10, color=TEXT, space_after=0, line=1.2)
line2 = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(7.8), Inches(5.35), Inches(4.65), Pt(0.75))
line2.fill.solid(); line2.fill.fore_color.rgb = BORDER; line2.line.fill.background(); line2.shadow.inherit = False
tf = textbox(s, 7.8, 5.47, 4.68, 0.9)
para(tf, "GUARDRAILS", size=9.5, color=TEAL, bold=True, font=HEAD, first=True, space_after=4)
para(tf, "SELECT-only execution · LIMIT 500 · BIS threshold checks · human-review escalation", size=10, color=TEXT, space_after=0, line=1.2)
footer(s, 6)
notes(s, "The sample SQL is illustrative of the template used for a quality query. Every response carries the executed statement and the evidence rows.")

# 7 · Data foundation
s = new_slide()
tag(s, "05 · Data foundation")
heading(s, "Four normalized tables, one queryable truth.",
        "CGWB and NWIC data normalized to a schema that hydrogeologists and SQL can both reason about.")
tables = [
    ("wells", "3,042", "Station metadata: state, district, block, coordinates, aquifer type, borehole depth, installation year, source.", TEAL),
    ("gw_levels", "16,780", "Seasonal readings: pre-monsoon, post-monsoon, rabi, kharif — depth to water in mbgl, method, quality flag.", BLUE),
    ("gw_quality", "11,978", "Lab chemistry: pH, TDS, fluoride, arsenic, nitrate, hardness, iron, auto-derived BIS potability.", ORANGE),
    ("assessment_units", "100", "GEC-2015 blocks: recharge, extractable resource, extraction, stage of extraction, category.", GREEN),
]
x = 0.62
for name, count, body, col in tables:
    box(s, x, 1.85, 2.92, 2.55, PANEL, BORDER)
    tf = textbox(s, x + 0.22, 2.02, 2.5, 0.35)
    para(tf, name, size=13, color=col, bold=True, font=MONO, first=True, space_after=0)
    tf = textbox(s, x + 0.22, 2.38, 2.5, 0.5)
    para(tf, count, size=25, color=WHITE, bold=True, font=HEAD, first=True, space_after=0, line=1.0)
    tf = textbox(s, x + 0.22, 2.95, 2.5, 1.7)
    para(tf, body, size=10, color=TEXT, first=True, space_after=0, line=1.25)
    x += 3.05

tf = textbox(s, 0.62, 4.72, 12.0, 0.3)
para(tf, "STANDARDS ENFORCED AT INGESTION", size=9.5, color=MUTED, bold=True, font=HEAD, first=True, space_after=0)
x = 0.62
for label in ["BIS 10500:2012", "GEC-2015", "Pydantic v2", "Referential integrity"]:
    x = chip(s, x, 5.02, label, size=10) + 0.14
tf = textbox(s, 0.62, 5.65, 12.0, 0.9)
para(tf, "Potability is derived, not assumed: TDS > 500, fluoride > 1.5, nitrate > 45 or arsenic > 10 µg/L flags non-potable. GEC categories are derived from stage of extraction: safe < 70%, semi-critical 70–90%, critical 90–100%, over-exploited > 100%.",
     size=10.5, color=MUTED, first=True, space_after=0, line=1.25)
footer(s, 7)
notes(s, "The schema is deliberately narrow and normalized. Derived fields — potability and GEC category — are computed by Pydantic validators so every row carries the same interpretation.")

# 8 · Tech stack
s = new_slide()
tag(s, "06 · Technology")
heading(s, "Built on a deliberately small, auditable stack.",
        "Every dependency earns its place: query engine, retrieval, model access, evaluation.")
cols = [
    ("Application & UI", TEAL, [
        "Python 3.15 runtime",
        "Streamlit 1.66 — six-page app",
        "Plotly 7.1 interactive charts",
        "pandas 3.1 + NumPy",
        "Streamlit-Folium / Leaflet maps",
        "python-dotenv configuration",
    ]),
    ("Data & retrieval", BLUE, [
        "DuckDB 2.0 columnar SQL engine",
        "Pydantic 2 schema validation",
        "ChromaDB vector store (optional)",
        "sentence-transformers MiniLM (optional)",
        "scikit-learn TF-IDF fallback",
        "requests + tenacity + loguru",
    ]),
    ("AI, quality & ops", ORANGE, [
        "OpenRouter (default provider)",
        "Google Gemini / OpenAI APIs",
        "Any OpenAI-compatible local URL",
        "Offline deterministic synthesizer",
        "pytest 9 — 25 tests passing",
        "30-case benchmark + live audit",
    ]),
]
x = 0.62
for title, col, items in cols:
    box(s, x, 1.8, 3.88, 4.2, PANEL, BORDER)
    tf = textbox(s, x + 0.25, 1.98, 3.4, 0.4)
    para(tf, title, size=16, color=col, bold=True, font=HEAD, first=True, space_after=0)
    line = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x + 0.25), Inches(2.42), Inches(0.9), Pt(1.5))
    line.fill.solid(); line.fill.fore_color.rgb = col; line.line.fill.background(); line.shadow.inherit = False
    y = 2.6
    for it in items:
        tf = textbox(s, x + 0.25, y, 3.45, 0.45)
        para(tf, "·  " + it, size=11.5, color=TEXT, first=True, space_after=0, line=1.15)
        y += 0.52
    x += 4.1
tf = textbox(s, 0.62, 6.25, 12.0, 0.55)
para(tf, "Zero-key operation is a first-class path: without an API key the deterministic hydro synthesizer still answers, and the UI states this explicitly in the sidebar.",
     size=10.5, color=MUTED, italic=True, first=True, space_after=0, line=1.2)
footer(s, 8)
notes(s, "Versions shown match the verified environment: Streamlit 1.66.1, DuckDB 2.0.0, Plotly 7.1.0, pandas 3.1.0. ChromaDB is optional; the system degrades to TF-IDF.")

# 9 · Copilot
s = new_slide()
tag(s, "07 · AI copilot")
heading(s, "Ask in plain language. Get evidence back.")
picture(s, "user_02_copilot.png", 0.62, 1.55, 8.75, 4.95)
bullets(s, 9.55, 1.7, 3.2, 4.8, [
    "Intent-aware routing with keyword fallback",
    "Coverage checked before any SQL runs",
    "Live provider shown in the sidebar",
    "Evidence drawer: station IDs, dates, flags",
    "Executed SQL shown verbatim, CSV export",
    "Six response states + confidence badges",
], size=12)
caption(s, 0.62, 6.6, 8.6, "Live capture — OpenRouter online; “which state got the most potable wells?” → 399 wells, Fully Supported / Medium confidence.")
footer(s, 9)
notes(s, "This is the core interaction. The answer cites SQL results, and the sidebar shows which provider produced it. The evidence drawer exposes the retrieved rows and the query.")

# 10 · Dossier
s = new_slide()
tag(s, "08 · Station dossier")
heading(s, "Inspect any well like a hydrogeologist.")
picture(s, "user_03_station_dossier.png", 0.62, 1.55, 8.75, 4.95)
bullets(s, 9.55, 1.75, 3.2, 4.8, [
    "State → district → station drilling",
    "Aquifer, borehole depth, source, coordinates",
    "Telemetry health score and latest depth",
    "Seasonal hydrograph, reversed depth axis",
    "BIS potability radar per sample",
    "Raw telemetry logs with quality flags",
], size=12)
caption(s, 0.62, 6.6, 8.6, "Live capture — Kerala, Kollam station profile with location map and monitoring history.")
footer(s, 10)
notes(s, "The dossier answers 'what do we know about this specific well?' without any language model in the loop for the numbers.")

# 11 · Data explorer
s = new_slide()
tag(s, "09 · Data explorer")
heading(s, "Browse and filter the raw evidence.")
picture(s, "user_04_data_explorer.png", 0.62, 1.55, 8.75, 4.95)
bullets(s, 9.55, 1.75, 3.2, 4.8, [
    "Four tabs mirror the four tables",
    "Filter by state, season, flag, potability, GEC category",
    "Plotly distributions for depth, fluoride, TDS",
    "Leaflet maps of station coverage",
    "Designed for audit, not just demo",
], size=12)
caption(s, 0.62, 6.6, 8.6, "Live capture — monitoring-station catalog with map of indexed stations.")
footer(s, 11)
notes(s, "The explorer is the transparency layer: users can verify any claim by filtering the raw records themselves.")

# 12 · Performance
s = new_slide()
tag(s, "10 · Reliability")
heading(s, "Reliability is measured, not asserted.")
picture(s, "user_05_performance.png", 0.62, 1.55, 8.35, 4.7)
bullets(s, 9.15, 1.6, 3.6, 4.9, [
    "SQL success 83.3% across the 30-case suite",
    "Provenance precision 100% — zero false citations",
    "Edge-case interception 100%",
    "Mean latency 86 ms in the in-app SLA panel",
    "P95 128 ms; out-of-scope queries answer in 48 ms",
    "Live benchmark button re-runs the entire suite",
], size=11.5)
caption(s, 0.62, 6.4, 8.3, "Live capture — in-app SLA panel and guardrail documentation.")
footer(s, 12)
notes(s, "Two views of performance: the in-app SLA panel shown here, and the reproducible evaluation runner with lower latencies. The deck's evaluation slide uses the runner's numbers.")

# 13 · Safety
s = new_slide()
tag(s, "11 · Safety & governance")
heading(s, "Guardrails that make scientific use defensible.")
picture(s, "user_06_safety.png", 0.62, 1.6, 8.15, 4.6)
bullets(s, 9.0, 1.7, 3.7, 4.9, [
    "SELECT-only SQL; DROP/DELETE/UPDATE/INSERT/ALTER/TRUNCATE blocked",
    "Automatic LIMIT 500 protects memory",
    "BIS 10500 thresholds: fluoride 1.5, TDS 500, nitrate 45, arsenic 10",
    "Coverage detector refuses to fill gaps with invented values",
    "Conflicting observations escalate to human review",
], size=11.5)
caption(s, 0.62, 6.35, 8.15, "Live capture — failure-mode mitigations and automated protections.")
footer(s, 13)
notes(s, "The system is designed so that the failure mode is a refusal with an explanation, not a fabricated number.")

# 14 · NWIC
s = new_slide()
tag(s, "12 · Live ingestion")
heading(s, "Official data, synchronized in one click.")
picture(s, "user_07_nwic_sync.png", 0.62, 1.55, 8.3, 4.9)
bullets(s, 9.15, 1.75, 3.55, 4.8, [
    "Direct CKAN download from nwdp.nwic.gov.in",
    "Eight states registered as resources",
    "Coordinate validation within India bounds",
    "Season derived from acquisition date",
    "Arsenic converted mg/L → µg/L",
    "Deduplicated INSERT OR REPLACE into DuckDB",
], size=11.5)
caption(s, 0.62, 6.55, 8.3, "Live capture — 2,842 CGWB stations ingested; portal reachability shown in-app.")
footer(s, 14)
notes(s, "Ingestion is reproducible and idempotent. The portal status badge makes the live dependency visible instead of hiding it.")

# 15 · Evaluation
s = new_slide()
tag(s, "13 · Evaluation")
heading(s, "30 benchmark questions. Measured, reproducible.",
        "Runner: run_evaluation.py — normal, edge, incomplete and ambiguous cases against the same database.")
cards = [("83.3%", "overall pass rate", TEAL), ("100%", "provenance precision", GREEN), ("38 ms", "P95 latency", ORANGE)]
x = 0.62
for value, label, col in cards:
    box(s, x, 1.75, 2.92, 1.15, PANEL, BORDER)
    tf = textbox(s, x + 0.2, 1.88, 2.5, 0.5)
    para(tf, value, size=26, color=col, bold=True, font=HEAD, first=True, space_after=0, line=1.0)
    tf = textbox(s, x + 0.2, 2.42, 2.5, 0.3)
    para(tf, label.upper(), size=9, color=MUTED, bold=True, first=True, space_after=0)
    x += 3.1

cats = [("Normal queries", 66.7, "8 of 12", BLUE), ("Edge conditions", 100.0, "8 of 8", TEAL),
        ("Incomplete records", 83.3, "5 of 6", ORANGE), ("Ambiguous locations", 100.0, "4 of 4", GREEN)]
y = 3.3
for label, pct, detail, col in cats:
    tf = textbox(s, 0.62, y, 2.35, 0.3)
    para(tf, label, size=11, color=TEXT, first=True, space_after=0)
    track = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(3.05), Inches(y + 0.04), Inches(4.2), Inches(0.16))
    track.fill.solid(); track.fill.fore_color.rgb = PANEL2; track.line.fill.background(); track.shadow.inherit = False
    fillw = 4.2 * pct / 100.0
    bar = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(3.05), Inches(y + 0.04), Inches(fillw), Inches(0.16))
    bar.fill.solid(); bar.fill.fore_color.rgb = col; bar.line.fill.background(); bar.shadow.inherit = False
    tf = textbox(s, 7.4, y, 1.4, 0.3)
    para(tf, "%.1f%%" % pct, size=11, color=col, bold=True, font=HEAD, first=True, space_after=0)
    tf = textbox(s, 8.6, y, 1.2, 0.3)
    para(tf, detail, size=9.5, color=MUTED, first=True, space_after=0)
    y += 0.62

box(s, 9.95, 1.75, 2.76, 4.75, PANEL, BORDER)
tf = textbox(s, 10.15, 1.9, 2.4, 0.3)
para(tf, "METRICS", size=9.5, color=TEAL, bold=True, font=HEAD, first=True, space_after=0)
rows = [("Intent accuracy", "66.7%"), ("SQL success", "83.3%"), ("Coverage recall", "63.3%"),
        ("Provenance", "100.0%"), ("Pass rate", "83.3%"), ("Mean latency", "32 ms"), ("P95 latency", "38 ms")]
y = 2.25
for k, v in rows:
    tf = textbox(s, 10.15, y, 1.5, 0.3)
    para(tf, k, size=10, color=MUTED, first=True, space_after=0)
    tf = textbox(s, 11.55, y, 0.95, 0.3)
    para(tf, v, size=10, color=TEXT, bold=True, align=PP_ALIGN.RIGHT, first=True, space_after=0)
    y += 0.36
tf = textbox(s, 10.15, 5.9, 2.4, 0.6)
para(tf, "Failure modes: 5 empty SQL results, 3 coverage misses — both mapped to mitigations.", size=8.5, color=MUTED, first=True, space_after=0, line=1.2)
footer(s, 15)
notes(s, "The evaluation runner is the source of truth for these numbers; the in-app panel shows operational SLA targets. Provenance precision is the headline: every evaluated answer either cited evidence or explicitly said it could not.")

# 16 · Run it
s = new_slide()
tag(s, "14 · Run it")
heading(s, "Reproducible in four commands.")
box(s, 0.62, 1.75, 5.9, 2.85, PANEL, BORDER)
tf = textbox(s, 0.88, 1.92, 5.4, 0.3)
para(tf, "TERMINAL", size=9.5, color=TEAL, bold=True, font=HEAD, first=True, space_after=0)
tf = textbox(s, 0.88, 2.28, 5.4, 2.8)
para(tf, "cd c:\\Users\\shela\\Downloads\\csep", size=10.5, color=BLUE, font=MONO, first=True, space_after=6, line=1.25)
para(tf, "pip install -r requirements.txt", size=10.5, color=BLUE, font=MONO, space_after=6, line=1.25)
para(tf, "python ingest_all_target_states.py", size=10.5, color=BLUE, font=MONO, space_after=6, line=1.25)
para(tf, "streamlit run app/main.py", size=10.5, color=BLUE, font=MONO, space_after=6, line=1.25)
para(tf, "# open http://localhost:8501", size=10.5, color=MUTED, font=MONO, space_after=0, line=1.25)

box(s, 6.78, 1.75, 5.93, 2.85, PANEL, BORDER)
tf = textbox(s, 7.02, 1.92, 5.4, 0.3)
para(tf, "OPTIONAL MODEL CONFIG (.env)", size=9.5, color=ORANGE, bold=True, font=HEAD, first=True, space_after=0)
tf = textbox(s, 7.02, 2.28, 5.4, 2.8)
para(tf, "LLM_PROVIDER=openrouter", size=10.5, color=TEXT, font=MONO, first=True, space_after=5, line=1.25)
para(tf, "OPENROUTER_API_KEY=sk-or-v1-...", size=10.5, color=TEXT, font=MONO, space_after=5, line=1.25)
para(tf, "LLM_MODEL=meta-llama/llama-3.3-70b-instruct", size=10.5, color=TEXT, font=MONO, space_after=5, line=1.25)
para(tf, "LLM_BASE_URL=https://openrouter.ai/api/v1", size=10.5, color=TEXT, font=MONO, space_after=5, line=1.25)
para(tf, "# Gemini, OpenAI or local Ollama also supported", size=9.5, color=MUTED, font=MONO, space_after=0, line=1.2)

opts = [("Streamlit Cloud", "Push to GitHub, point at app/main.py, add secrets."),
        ("Docker", "Python 3.11 slim image, seed database, expose 8501."),
        ("Cloud VM", "systemd service for 24/7 uptime; nginx reverse proxy.")]
x = 0.62
for title, body in opts:
    box(s, x, 4.95, 3.95, 1.05, PANEL2, BORDER)
    tf = textbox(s, x + 0.2, 5.05, 3.55, 0.3)
    para(tf, title, size=12, color=TEAL, bold=True, font=HEAD, first=True, space_after=0)
    tf = textbox(s, x + 0.2, 5.37, 3.55, 0.6)
    para(tf, body, size=9.5, color=MUTED, first=True, space_after=0, line=1.15)
    x += 4.1
footer(s, 16)
notes(s, "The app runs with zero configuration and no API key; adding a provider key upgrades the narrative quality without changing the retrieval or provenance path.")

# 17 · Close
s = new_slide()
bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.16), Inches(7.5))
bar.fill.solid(); bar.fill.fore_color.rgb = TEAL; bar.line.fill.background(); bar.shadow.inherit = False
tf = textbox(s, 1.0, 2.2, 11.3, 1.0)
para(tf, "Verified. Cited. Auditable.", size=46, color=WHITE, bold=True, font=HEAD, first=True, space_after=0, line=1.0)
tf = textbox(s, 1.0, 3.25, 10.8, 1.2)
para(tf, "INGRES turns the national groundwater record into answers a hydrogeologist can defend — with the station, the date and the quality flag attached.",
     size=15, color=MUTED, first=True, space_after=0, line=1.35)
tf = textbox(s, 1.0, 4.75, 11.0, 0.4)
para(tf, "Data: CGWB / National Water Data Portal (nwdp.nwic.gov.in)", size=10.5, color=TEXT, first=True, space_after=2)
para(tf, "Standards: GEC-2015 resource assessment · BIS 10500:2012 drinking water", size=10.5, color=TEXT, space_after=2)
para(tf, "Problem Code SIH26063 · National Groundwater Intelligence Platform", size=10.5, color=MUTED, space_after=0)
footer(s, 17)
notes(s, "Close on the value proposition: auditable answers, not just fluent ones.")

prs.save(OUT)
print("saved", os.path.abspath(OUT), "slides:", len(prs.slides))