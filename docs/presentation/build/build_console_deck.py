
"""Build the short 'INGRES console update' deck."""
import os
from PIL import Image
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

BASE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(BASE, "deck_console")
OUT = os.path.join(BASE, "..", "INGRES_Console_Update.pptx")

BG     = RGBColor(0x0E, 0x11, 0x17)
PANEL  = RGBColor(0x16, 0x1B, 0x22)
PANEL2 = RGBColor(0x1C, 0x24, 0x30)
BORDER = RGBColor(0x30, 0x36, 0x3D)
TEXT   = RGBColor(0xE6, 0xED, 0xF3)
MUTED  = RGBColor(0x8B, 0x94, 0x9E)
TEAL   = RGBColor(0x2D, 0xD4, 0xBF)
BLUE   = RGBColor(0x58, 0xA6, 0xFF)
AMBER  = RGBColor(0xF5, 0xB1, 0x4C)
ROSE   = RGBColor(0xF8, 0x71, 0x71)
GREEN  = RGBColor(0x3F, 0xD5, 0x8C)
WHITE  = RGBColor(0xFF, 0xFF, 0xFF)

BODY = "Segoe UI"
HEAD = "Segoe UI Semibold"
MONO = "Consolas"

prs = Presentation()
prs.slide_width = Inches(13.333)
prs.slide_height = Inches(7.5)
BLANK = prs.slide_layouts[6]
TOTAL = 11


def new_slide():
    s = prs.slides.add_slide(BLANK)
    f = s.background.fill
    f.solid(); f.fore_color.rgb = BG
    return s


def box(slide, x, y, w, h, fill=PANEL, line=BORDER, radius=0.05):
    shp = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y), Inches(w), Inches(h))
    try:
        shp.adjustments[0] = radius
    except Exception:
        pass
    shp.fill.solid(); shp.fill.fore_color.rgb = fill
    shp.line.color.rgb = line; shp.line.width = Pt(1)
    shp.shadow.inherit = False
    return shp


def text(slide, x, y, w, h, content, size=15, color=TEXT, bold=False, font=BODY,
         align=PP_ALIGN.LEFT, line=1.14):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
    lines = content if isinstance(content, list) else [content]
    first = True
    for item in lines:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.alignment = align
        p.space_after = Pt(4); p.line_spacing = line
        r = p.add_run(); r.text = item
        r.font.size = Pt(size); r.font.bold = bold; r.font.name = font
        r.font.color.rgb = color
    return tb


def tag(slide, value):
    text(slide, 0.62, 0.34, 9, 0.3, value.upper(), size=10, color=TEAL, bold=True, font=HEAD)


def heading(slide, value, sub=None, size=28):
    text(slide, 0.62, 0.62, 12.1, 0.8, value, size=size, color=WHITE, bold=True, font=HEAD, line=1.0)
    if sub:
        text(slide, 0.62, 1.22, 12.1, 0.45, sub, size=13, color=MUTED)


def bullets(slide, x, y, w, items, size=13, gap=8, h=4.9):
    tb = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame; tf.word_wrap = True
    tf.margin_left = 0; tf.margin_right = 0; tf.margin_top = 0; tf.margin_bottom = 0
    first = True
    for item in items:
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        p.space_after = Pt(gap); p.line_spacing = 1.16
        r0 = p.add_run(); r0.text = "▸  "
        r0.font.size = Pt(size); r0.font.color.rgb = TEAL; r0.font.bold = True
        r = p.add_run(); r.text = item
        r.font.size = Pt(size); r.font.color.rgb = TEXT
    return tb


def picture(slide, name, x, y, max_w, max_h):
    path = os.path.join(SHOTS, name)
    iw, ih = Image.open(path).size
    scale = min(max_w / iw, max_h / ih)
    w, h = iw * scale, ih * scale
    left = x + (max_w - w) / 2
    top = y + (max_h - h) / 2
    pic = slide.shapes.add_picture(path, Inches(left), Inches(top), Inches(w), Inches(h))
    pic.line.color.rgb = BORDER; pic.line.width = Pt(0.75)
    pic.shadow.inherit = False
    return pic


def footer(slide, num, note="INGRES · National Groundwater Intelligence Platform"):
    line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.62), Inches(7.06), Inches(12.09), Pt(0.75))
    line.fill.solid(); line.fill.fore_color.rgb = BORDER
    line.line.fill.background(); line.shadow.inherit = False
    text(slide, 0.62, 7.13, 8.5, 0.25, note, size=9, color=MUTED)
    text(slide, 11.4, 7.13, 1.3, 0.25, "%02d / %d" % (num, TOTAL), size=9, color=MUTED, align=PP_ALIGN.RIGHT)


def notes(slide, value):
    slide.notes_slide.notes_text_frame.text = value


def stat(slide, x, y, w, value, label, color=TEAL):
    text(slide, x, y, w, 0.55, value, size=26, color=color, bold=True, font=HEAD, line=1.0)
    text(slide, x, y + 0.5, w, 0.3, label.upper(), size=9, color=MUTED, bold=True)


# 1 ─ Title
s = new_slide()
bar = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(0.16), Inches(7.5))
bar.fill.solid(); bar.fill.fore_color.rgb = TEAL; bar.line.fill.background(); bar.shadow.inherit = False

text(s, 0.95, 1.35, 11, 0.35, "INGRES  ·  UPDATE  ·  NOVEMBER 2026", size=11, color=TEAL, bold=True, font=HEAD)
text(s, 0.95, 1.8, 11.5, 1.0, "A second frontend,", size=44, color=WHITE, bold=True, font=HEAD, line=1.0)
text(s, 0.95, 2.7, 11.5, 1.0, "and answers that finally work.", size=44, color=WHITE, bold=True, font=HEAD, line=1.0)
line = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.98), Inches(3.95), Inches(4.2), Pt(2))
line.fill.solid(); line.fill.fore_color.rgb = BLUE; line.line.fill.background(); line.shadow.inherit = False
text(s, 0.98, 4.2, 10.4, 0.8,
     "Same evidence engine, two interfaces: the original Streamlit app and a new console with an interactive India map.",
     size=15, color=MUTED, line=1.35)

stat(s, 0.98, 5.55, 3.0, "3,042", "stations indexed")
stat(s, 4.0, 5.55, 3.0, "35", "state boundaries")
stat(s, 7.0, 5.55, 3.2, "243", "wells in Kerala", AMBER)
stat(s, 10.0, 5.55, 2.6, "25/25", "tests passing", GREEN)
footer(s, 1)
notes(s, "Short update: we added a console frontend and fixed the SQL that was refusing Kerala questions.")

# 2 ─ What it does
s = new_slide()
tag(s, "01 · What it does")
heading(s, "Ask a groundwater question. Get the receipt.",
        "Every number comes from the database, with the station and date attached.")
bullets(s, 0.62, 1.95, 7.3, [
    "Answers come from a read-only SQL query over DuckDB — not from the model's memory.",
    "Each answer cites the station, the date and the quality flag behind it.",
    "When the data cannot support an answer, the system says so instead of guessing.",
    "Works with OpenRouter, Gemini, OpenAI, a local model — or no key at all.",
], size=14, gap=12, h=3.4)
box(s, 8.15, 1.95, 4.55, 4.3, PANEL)
stat(s, 8.45, 2.15, 2.0, "3,042", "stations", TEAL)
stat(s, 10.6, 2.15, 2.0, "16,780", "level readings", BLUE)
stat(s, 8.45, 3.35, 2.0, "11,978", "lab tests", AMBER)
stat(s, 10.6, 3.35, 2.0, "100%", "provenance", GREEN)
text(s, 8.45, 4.6, 4.0, 1.3,
     "GEC-2015 resource assessment · BIS 10500:2012 drinking-water limits · CGWB / NWIC monitoring data.",
     size=10.5, color=MUTED, line=1.3)
footer(s, 2)
notes(s, "One sentence: retrieval first, generation second, evidence always.")

# 3 ─ Two frontends
s = new_slide()
tag(s, "02 · Two frontends")
heading(s, "Same engine. Two ways in.", "The UI is the only thing that changed.")
box(s, 0.62, 2.0, 5.95, 3.6, PANEL)
text(s, 0.92, 2.22, 5.3, 0.4, "STREAMLIT  ·  ORIGINAL", size=10, color=BLUE, bold=True, font=HEAD)
text(s, 0.92, 2.6, 5.3, 0.5, "Six pages, zero setup", size=19, color=WHITE, bold=True, font=HEAD)
text(s, 0.92, 3.15, 5.35, 2.2, [
    "Dashboard, Copilot, Dossier, Explorer, Performance, NWIC sync",
    "Provider setup in the sidebar",
    "Runs on port 8501",
], size=12, color=TEXT, line=1.35)

box(s, 6.78, 2.0, 5.93, 3.6, PANEL2)
text(s, 7.08, 2.22, 5.3, 0.4, "CONSOLE  ·  NEW", size=10, color=TEAL, bold=True, font=HEAD)
text(s, 7.08, 2.6, 5.3, 0.5, "Faster, with a real map", size=19, color=WHITE, bold=True, font=HEAD)
text(s, 7.08, 3.15, 5.35, 2.2, [
    "Dashboard, Map, Copilot, Stations, Explore, Performance",
    "State boundaries, potability colours, zoom and pan",
    "Runs on port 8600",
], size=12, color=TEXT, line=1.35)

text(s, 0.62, 5.95, 12.1, 0.6,
     "Both read the same DuckDB file, run the same router, coverage check and SQL guard.",
     size=13, color=MUTED)
footer(s, 3)
notes(s, "Position the console as an alternative view, not a replacement. The original app is untouched.")

# 4 ─ Dashboard
s = new_slide()
tag(s, "03 · Console")
heading(s, "The national picture, on one screen.")
picture(s, "dashboard.png", 0.62, 1.55, 8.25, 4.95)
bullets(s, 9.15, 1.75, 3.55, [
    "3,042 stations, 16,780 readings, 11,978 tests",
    "Extraction intensity vs the 100% limit",
    "Contamination watch: TDS, fluoride, nitrate, arsenic",
    "All figures are direct aggregates",
], size=12.5, gap=10)
footer(s, 4)
notes(s, "No model involved on this page — pure aggregation.")

# 5 ─ Map
s = new_slide()
tag(s, "04 · Console map")
heading(s, "Every station, on the actual map.")
picture(s, "map.png", 0.62, 1.55, 8.2, 4.95)
bullets(s, 9.05, 1.6, 3.65, [
    "35 state boundaries, all 3,042 stations",
    "Green = potable · red = non-potable · grey = no sample",
    "White ring marks a suspect or estimated reading",
    "Pick a state: it highlights and zooms to fit",
    "Click a dot for its profile, then open the dossier",
    "Scroll to zoom, drag to pan",
], size=11.5, gap=8)
footer(s, 5)
notes(s, "This is the slide to demo live if there is time.")

# 6 ─ Copilot
s = new_slide()
tag(s, "05 · Console copilot")
heading(s, "Type a question. Read the evidence.")
picture(s, "copilot.png", 0.62, 1.55, 8.2, 4.95)
bullets(s, 9.05, 1.7, 3.65, [
    "Enter or the Ask button submits",
    "Answer shows confidence and coverage",
    "Evidence table, CSV export, executed SQL",
    "Works without an API key (deterministic mode)",
], size=12, gap=10)
footer(s, 6)
notes(s, "Mention that the query and the rows are both visible.")

# 7 ─ Dossier
s = new_slide()
tag(s, "06 · Console dossier")
heading(s, "Zoom into any well.")
picture(s, "stations.png", 0.62, 1.55, 8.25, 4.95)
bullets(s, 9.15, 1.75, 3.55, [
    "State → district → station",
    "Aquifer, depth, coordinates",
    "Seasonal hydrograph (depth axis reversed)",
    "BIS potability cards per sample",
], size=12.5, gap=10)
footer(s, 7)
notes(s, "Reached from the map or the Stations page.")

# 8 ─ Performance
s = new_slide()
tag(s, "07 · Console performance")
heading(s, "Measured, and re-runnable.")
picture(s, "performance.png", 0.62, 1.55, 8.25, 4.95)
bullets(s, 9.15, 1.75, 3.55, [
    "30-case benchmark, one click",
    "83.3% pass · 100% provenance precision",
    "Latency by query type",
    "Results table per test case",
], size=12.5, gap=10)
footer(s, 8)
notes(s, "Same benchmark as the report, executed live.")

# 9 ─ Fixes
s = new_slide()
tag(s, "08 · Fixed this round")
heading(s, "What was broken, and what changed.")
items = [
    ("State vs district in SQL", "Kerala was filtered as a district, so the query returned 0 rows. Locations are now resolved as state or district first.", ROSE),
    ("Potability templates", "Added count and ranking queries: how many wells are potable, and which well is most potable.", TEAL),
    ("Offline answers", "The console plans structured queries itself, so no-key demos return real numbers instead of generic text.", BLUE),
    ("Small UI defects", "White input text, Enter now submits, map clicks select a station, smaller dots with potability colours.", AMBER),
]
y = 1.7
for title, body, col in items:
    box(s, 0.62, y, 12.09, 1.12, PANEL)
    strip = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.62), Inches(y), Inches(0.07), Inches(1.12))
    strip.fill.solid(); strip.fill.fore_color.rgb = col
    strip.line.fill.background(); strip.shadow.inherit = False
    text(s, 0.95, y + 0.14, 3.3, 0.4, title, size=13.5, color=col, bold=True, font=HEAD)
    text(s, 4.35, y + 0.16, 8.1, 0.85, body, size=11.5, color=TEXT, line=1.25)
    y += 1.24
footer(s, 9)
notes(s, "Be explicit that the Kerala failure was a SQL filter bug, not the model.")

# 10 ─ Proof
s = new_slide()
tag(s, "09 · Proof")
heading(s, "The answers now, with real rows.")
box(s, 0.62, 1.75, 5.95, 2.1, PANEL)
text(s, 0.92, 1.95, 5.4, 0.3, "WELLS POTABLE IN KERALA", size=9.5, color=TEAL, bold=True, font=HEAD)
text(s, 0.92, 2.3, 5.4, 0.6, "159 of 243", size=30, color=WHITE, bold=True, font=HEAD)
text(s, 0.92, 2.95, 5.4, 0.7, "65.4% potable · 3 non-potable · 81 without a sample", size=11.5, color=MUTED)

box(s, 6.78, 1.75, 5.93, 2.1, PANEL)
text(s, 7.08, 1.95, 5.4, 0.3, "MOST POTABLE WELLS (KERALA)", size=9.5, color=BLUE, bold=True, font=HEAD)
text(s, 7.08, 2.3, 5.4, 0.6, "162 ranked", size=30, color=WHITE, bold=True, font=HEAD)
text(s, 7.08, 2.95, 5.4, 0.7, "Top wells at 100% of 23 samples · ordered by share of potable samples", size=11.5, color=MUTED)

for i, (value, label, col) in enumerate([
    ("3,042", "stations mapped", TEAL),
    ("313", "non-potable stations", ROSE),
    ("25 / 25", "unit tests passing", GREEN),
    ("24 / 30", "benchmark passed", AMBER),
]):
    x = 0.62 + i * 3.06
    box(s, x, 4.15, 2.9, 1.55, PANEL2)
    stat(s, x + 0.25, 4.32, 2.4, value, label, col)

text(s, 0.62, 6.05, 12.1, 0.6,
     "Definitions: potable = latest laboratory sample · ranking = share of potable samples · wells without samples counted separately.",
     size=10.5, color=MUTED)
footer(s, 10)
notes(s, "These are the two questions that failed before; use them as the proof point.")

# 11 ─ Run it
s = new_slide()
tag(s, "10 · Run it")
heading(s, "Two commands, two ports.")
box(s, 0.62, 1.9, 5.95, 2.9, PANEL)
text(s, 0.92, 2.1, 5.3, 0.3, "STREAMLIT  ·  PORT 8501", size=9.5, color=BLUE, bold=True, font=HEAD)
text(s, 0.92, 2.5, 5.4, 1.9, [
    "streamlit run app/main.py",
    "",
    "Restart it after this update:",
    "the SQL fix loads on startup.",
], size=11.5, color=TEXT, font=MONO, line=1.35)
box(s, 6.78, 1.9, 5.93, 2.9, PANEL2)
text(s, 7.08, 2.1, 5.3, 0.3, "CONSOLE  ·  PORT 8600", size=9.5, color=TEAL, bold=True, font=HEAD)
text(s, 7.08, 2.5, 5.4, 1.9, [
    "python -m uvicorn frontend.api.server:app --port 8600",
    "",
    "Open http://127.0.0.1:8600",
], size=10.5, color=TEXT, font=MONO, line=1.35)

text(s, 0.62, 5.3, 12.1, 0.9, "Two views. One source of truth.",
     size=34, color=WHITE, bold=True, font=HEAD)
text(s, 0.62, 6.15, 12.1, 0.5,
     "CGWB / NWIC data · GEC-2015 · BIS 10500:2012 · SIH 2026 (SIH26063)",
     size=10.5, color=MUTED)
footer(s, 11)
notes(s, "Close on the two ports and the restart note.")

prs.save(OUT)
print("saved", os.path.abspath(OUT), "slides:", len(prs.slides))
