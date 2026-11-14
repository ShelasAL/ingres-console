
"""Build a simplified 13-slide INGRES deck."""
import os
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

BASE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(BASE, "..", "screenshots")
OUT = os.path.join(BASE, "..", "INGRES_Simple_Presentation.pptx")

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
WHITE   = RGBColor(0xFF, 0xFF, 0xFF)
BODY = "Segoe UI"
HEAD = "Segoe UI Semibold"
MONO = "Consolas"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
TOTAL = 13

def new_slide():
    s = prs.slides.add_slide(BLANK)
    f = s.background.fill
    f.solid(); f.fore_color.rgb = BG
    return s

def box(slide, x, y, w, h, fill=PANEL, line=BORDER, radius=0.05):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    try: shp.adjustments[0] = radius
    except Exception: pass
    shp.fill.solid(); shp.fill.fore_color.rgb = fill
    shp.line.color.rgb = line; shp.line.width = Pt(1)
    shp.shadow.inherit = False
    return shp

def text(slide, x, y, w, h, content, size=15, color=TEXT, bold=False, font=BODY,
         align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, line=1.12, italic=False):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    tf.vertical_anchor = anchor
    tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
    lines = content if isinstance(content, list) else [content]
    first = True
    for item in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align
        p.space_after = Pt(4); p.line_spacing = line
        r = p.add_run(); r.text = item
        r.font.size = Pt(size); r.font.bold = bold; r.font.name = font; r.font.italic = italic
        r.font.color.rgb = color
    return tb

def tag(slide, value):
    text(slide, 0.62, 0.34, 8, 0.3, value.upper(), size=10, color=TEAL, bold=True, font=HEAD)

def heading(slide, value, sub=None, size=27):
    text(slide, 0.62, 0.62, 12.1, 0.75, value, size=size, color=WHITE, bold=True, font=HEAD, line=1.0)
    if sub:
        text(slide, 0.62, 1.18, 12.1, 0.4, sub, size=13, color=MUTED)

def bullets(slide, x, y, w, items, size=13, gap=8):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(4.8))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
    first = True
    for item in items:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(gap); p.line_spacing = 1.14
        r0 = p.add_run(); r0.text = "▸  "
        r0.font.size = Pt(size); r0.font.color.rgb = TEAL; r0.font.bold = True
        r = p.add_run(); r.text = item
        r.font.size = Pt(size); r.font.color.rgb = TEXT
    return tb

def picture(slide, name, x, y, max_w, max_h, border=True, path_override=None):
    path = path_override or os.path.join(SHOTS, name)
    iw, ih = Image.open(path).size
    scale = min(max_w / iw, max_h / ih)
    w, h = iw * scale, ih * scale
    left = x + (max_w - w) / 2
    top = y + (max_h - h) / 2
    pic = slide.shapes.add_picture(path, Inches(left), Inches(top), Inches(w), Inches(h))
    if border:
        pic.line.color.rgb = BORDER; pic.line.width = Pt(0.75)
    pic.shadow.inherit = False
    return pic, (left, top, w, h)

def footer(slide, num):
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.62), Inches(7.05), Inches(12.09), Pt(0.75))
    line.fill.solid(); line.fill.fore_color.rgb = BORDER
    line.line.fill.background(); line.shadow.inherit = False
    text(slide, 0.62, 7.12, 7, 0.25, "INGRES · National Groundwater Intelligence Platform", size=9, color=MUTED)
    text(slide, 11.0, 7.12, 1.7, 0.25, "%02d / %d" % (num, TOTAL), size=9, color=MUTED, align=PP_ALIGN.RIGHT)

def notes(slide, value):
    slide.notes_slide.notes_text_frame.text = value

# 1 Title
s = new_slide()
bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.16), Inches(7.5))
bar.fill.solid(); bar.fill.fore_color.rgb = TEAL; bar.line.fill.background(); bar.shadow.inherit = False
text(s, 0.95, 1.7, 11, 1.2, "INGRES", size=72, color=WHITE, bold=True, font=HEAD)
text(s, 0.98, 2.95, 11, 0.6, "Groundwater answers with receipts.", size=26, color=TEAL, font=HEAD)
line = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.98), Inches(3.72), Inches(4.0), Pt(2))
line.fill.solid(); line.fill.fore_color.rgb = BLUE; line.line.fill.background(); line.shadow.inherit = False
text(s, 0.98, 3.95, 9.8, 0.9,
     "Ask a question about India’s groundwater. Get an answer that points to the station, the date and the quality flag behind it.",
     size=15, color=MUTED)
vals = [("3,042", "stations"), ("16,780", "level records"), ("11,978", "lab tests"), ("100%", "provenance")]
x = 0.98
for v, l in vals:
    text(s, x, 5.35, 2.3, 0.5, v, size=25, color=WHITE, bold=True, font=HEAD)
    text(s, x, 5.88, 2.3, 0.3, l.upper(), size=9, color=MUTED, bold=True)
    x += 2.85
text(s, 0.98, 6.7, 9, 0.3, "SIH 2026 · Problem Code SIH26063 · CGWB / NWIC", size=10, color=MUTED)
notes(s, "One line: we make national groundwater data answer questions with evidence attached.")

# 2 Problem
s = new_slide()
tag(s, "01 · The problem")
heading(s, "Three reasons groundwater answers are hard to trust.")
cards = [
    ("Data is everywhere", "Readings sit in government portals, spreadsheets and lab sheets.", ORANGE),
    ("AI makes numbers up", "A confident wrong number is worse than no answer.", RED),
    ("No receipts", "You can’t tell which well, which date, or whether it was measured.", BLUE),
]
x = 0.62
for title, body, col in cards:
    box(s, x, 1.75, 3.88, 1.95)
    strip = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(x), Inches(1.75), Inches(0.07), Inches(1.95))
    strip.fill.solid(); strip.fill.fore_color.rgb = col; strip.line.fill.background(); strip.shadow.inherit = False
    text(s, x + 0.28, 1.95, 3.3, 0.4, title, size=17, color=col, bold=True, font=HEAD)
    text(s, x + 0.28, 2.42, 3.3, 1.2, body, size=12, color=TEXT)
    x += 4.1
text(s, 0.62, 3.95, 12, 0.4, "In water security, a plausible answer is a dangerous answer.", size=16, color=TEAL, font=HEAD)
stats = [("60%+", "of irrigation depends on groundwater"), ("85%", "of rural drinking water"), ("997", "samples fail BIS limits")]
sx = 0.62
for val, lab in stats:
    text(s, sx, 4.6, 3.8, 0.55, val, size=28, color=WHITE, bold=True, font=HEAD)
    text(s, sx, 5.18, 3.8, 0.5, lab, size=10.5, color=MUTED)
    sx += 4.1
footer(s, 2)
notes(s, "Keep it short: siloed data, invented numbers, no provenance.")

# 3 What we did
s = new_slide()
tag(s, "02 · The solution")
heading(s, "What we did — four simple ideas.", "No magic: retrieve from the database, check what is missing, then explain.")
ideas = [
    ("SQL database", "Every number comes from a readable query over DuckDB, not from the model’s memory.", TEAL),
    ("Guardrails", "Read-only SQL, capped results, and a coverage check before any answer.", ORANGE),
    ("Flags & evidence", "Station, date, quality flag and confidence attached to every claim.", BLUE),
    ("Provider freedom", "OpenRouter, Gemini, OpenAI, a local model — or no key at all.", RGBColor(0x3F, 0xD5, 0x8C)),
]
x = 0.62
for title, body, col in ideas:
    box(s, x, 1.85, 2.92, 1.95)
    text(s, x + 0.22, 2.05, 2.5, 0.4, title, size=15.5, color=col, bold=True, font=HEAD)
    text(s, x + 0.22, 2.5, 2.5, 1.8, body, size=11, color=TEXT)
    x += 3.05
box(s, 0.62, 4.35, 12.09, 1.35, PANEL2, BORDER)
text(s, 0.9, 4.58, 11.6, 0.4, "The model never invents a value. It explains values the database already returned.", size=16, color=WHITE, font=HEAD)
text(s, 0.9, 5.08, 11.6, 0.35, "That is the whole design — retrieval first, generation second.", size=11.5, color=MUTED)
footer(s, 3)
notes(s, "Four ideas only: SQL, guardrails, evidence, provider choice.")

# 4 Dashboard
s = new_slide()
tag(s, "03 · One screen")
heading(s, "The national picture on one screen.")
picture(s, "user_01_dashboard_kpis.png", 0.62, 1.55, 8.45, 4.95)
bullets(s, 9.4, 1.75, 3.35, [
    "3,042 stations, 16,780 readings, 11,978 tests",
    "Extraction against the 100% critical line",
    "Contamination: TDS, fluoride, nitrate, arsenic",
], size=12.5)
footer(s, 4)
notes(s, "No model here — just aggregates over the database.")

# 5 Copilot
s = new_slide()
tag(s, "04 · AI copilot")
heading(s, "Ask in plain language. Get the receipt.")
picture(s, "fig_copilot_main.png", 0.62, 1.55, 8.7, 4.95)
bullets(s, 9.55, 1.75, 3.2, [
    "Answer cites the SQL result",
    "Confidence badge on every answer",
    "Evidence drawer: station, date, flag",
    "CSV export and human review",
], size=12)
footer(s, 5)
notes(s, "Point at the badge and the source line: the number comes from the query.")

# 6 Dossier
s = new_slide()
tag(s, "05 · Station dossier")
heading(s, "Zoom into any station.")
picture(s, "user_03_station_dossier.png", 0.62, 1.55, 8.6, 4.95)
bullets(s, 9.45, 1.75, 3.3, [
    "State → district → station",
    "Aquifer, depth, coordinates, map",
    "Health score and latest reading",
    "Seasonal hydrograph and BIS limits",
], size=12)
footer(s, 6)
notes(s, "This is the well-level view, no language model needed for the numbers.")

# 7 Explorer
s = new_slide()
tag(s, "06 · Raw evidence")
heading(s, "Browse and filter the evidence yourself.")
picture(s, "user_04_data_explorer.png", 0.62, 1.55, 8.6, 4.95)
bullets(s, 9.45, 1.75, 3.3, [
    "Four tabs: stations, levels, quality, GEC",
    "Filter by state, season, flag, potability",
    "Maps and distributions",
], size=12.5)
footer(s, 7)
notes(s, "If someone doubts a number, this is where you prove it.")

# 8 Performance
s = new_slide()
tag(s, "07 · Performance")
heading(s, "We measure the model — and let you re-run it.")
picture(s, "user_05_performance.png", 0.62, 1.55, 8.45, 4.85)
bullets(s, 9.3, 1.7, 3.45, [
    "83.3% pass on 30 benchmark questions",
    "100% provenance precision",
    "Edge cases intercepted",
    "Benchmark button reruns the audit live",
], size=12)
footer(s, 8)
notes(s, "Show the button; if time allows, run it live.")

# 9 Guardrails
s = new_slide()
tag(s, "08 · Guardrails")
heading(s, "Guardrails make the answer defensible.")
picture(s, "user_06_safety.png", 0.62, 1.55, 8.35, 4.85)
bullets(s, 9.2, 1.75, 3.5, [
    "Read-only SQL; DROP and DELETE blocked",
    "Automatic LIMIT 500",
    "BIS limits are fixed, not guessed",
    "Conflicting data goes to human review",
], size=12)
footer(s, 9)
notes(s, "Refusal is the designed failure mode, not a bug.")

# 10 NWIC
s = new_slide()
tag(s, "09 · Official live sync")
heading(s, "Official data, one click.")
picture(s, "user_07_nwic_sync.png", 0.62, 1.55, 8.4, 4.95)
bullets(s, 9.25, 1.75, 3.45, [
    "Streams from nwdp.nwic.gov.in",
    "2,842 stations ingested",
    "Re-running updates, never duplicates",
], size=12.5)
footer(s, 10)
notes(s, "If the portal is down, say so — the cached database still answers.")

# 11 Reproducible
s = new_slide()
tag(s, "10 · Reproducible")
heading(s, "Run it yourself, in four commands.")
box(s, 0.62, 1.75, 7.55, 3.9)
text(s, 0.9, 1.95, 7, 0.3, "TERMINAL", size=9.5, color=TEAL, bold=True, font=HEAD)
code_lines = [
    "cd c:\\Users\\shela\\Downloads\\csep",
    "pip install -r requirements.txt",
    "streamlit run app/main.py",
    "# open http://localhost:8501",
]
y = 2.35
for line in code_lines:
    text(s, 0.9, y, 7.0, 0.35, line, size=11.5, color=BLUE if not line.startswith("#") else MUTED, font=MONO)
    y += 0.5
text(s, 0.9, 4.75, 7.0, 0.7, "Optional: add an API key in .env for richer prose. Retrieval and provenance stay the same.", size=9.5, color=MUTED)
box(s, 8.5, 1.75, 4.2, 3.9)
text(s, 8.75, 1.95, 3.7, 0.35, "ALSO INCLUDED", size=9.5, color=ORANGE, bold=True, font=HEAD)
text(s, 8.75, 2.35, 3.7, 3.0, [
    "25 passing unit tests",
    "30-case benchmark runner",
    "One DuckDB file, no server",
    "Works without an API key",
], size=12, color=TEXT, line=1.3)
text(s, 0.62, 5.95, 12, 0.45, "The database is the product. Everything else is presentation.", size=15, color=TEAL, font=HEAD)
footer(s, 11)
notes(s, "Emphasise: no server, no key required, tests included.")

# 12 Copilot settings
s = new_slide()
tag(s, "11 · Copilot settings")
heading(s, "Pick your model in the sidebar.")
pic, geo = picture(s, "user_02_copilot.png", 0.62, 1.55, 8.9, 4.95)
left, top, w, h = geo
# highlight the sidebar region
hw = w * (305.0 / 1713.0)
outline = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left + 0.01), Inches(top + 0.01), Inches(hw - 0.02), Inches(h - 0.02))
outline.fill.background(); outline.line.color.rgb = TEAL; outline.line.width = Pt(2)
outline.shadow.inherit = False
bullets(s, 9.65, 1.75, 3.1, [
    "Choose provider: OpenRouter, Gemini, OpenAI or local",
    "Paste a key, or stay offline",
    "Model name + live status badge",
], size=11.5)
text(s, 9.65, 5.55, 3.1, 0.8, "The highlighted panel is the whole configuration surface.", size=9.5, color=MUTED, italic=True)
footer(s, 12)
notes(s, "Switching provider changes the prose, not the retrieval.")

# 13 Close
s = new_slide()
bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.16), Inches(7.5))
bar.fill.solid(); bar.fill.fore_color.rgb = TEAL; bar.line.fill.background(); bar.shadow.inherit = False
text(s, 1.0, 2.25, 11, 1.0, "Answers with receipts.", size=46, color=WHITE, bold=True, font=HEAD)
text(s, 1.0, 3.25, 10.5, 0.9, "INGRES makes India’s groundwater record answer questions a hydrogeologist can defend.", size=16, color=MUTED)
text(s, 1.0, 4.9, 11, 1.0, [
    "Data: CGWB / National Water Data Portal",
    "Standards: GEC-2015 · BIS 10500:2012",
    "SIH 2026 · Problem Code SIH26063",
], size=10.5, color=TEXT)
footer(s, 13)
notes(s, "Close on the one line: answers with receipts.")

prs.save(OUT)
print("saved", os.path.abspath(OUT), "slides:", len(prs.slides))