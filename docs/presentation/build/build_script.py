
"""Build a presenter script (DOCX + Markdown) for the INGRES deck."""
import os
from docx import Document
from docx.shared import Pt, Cm, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BASE = os.path.dirname(os.path.abspath(__file__))
OUT_DOCX = os.path.join(BASE, "..", "INGRES_Presenter_Script.docx")
OUT_MD = os.path.join(BASE, "..", "INGRES_Presenter_Script.md")

NAVY = RGBColor(0x0B, 0x3D, 0x63)
TEAL = RGBColor(0x0D, 0x94, 0x88)
INK = RGBColor(0x1F, 0x23, 0x28)
GRAY = RGBColor(0x57, 0x60, 0x6A)
LIGHT = RGBColor(0x6E, 0x77, 0x81)

doc = Document()
sec = doc.sections[0]
sec.page_width = Cm(21.0); sec.page_height = Cm(29.7)
sec.top_margin = Cm(1.7); sec.bottom_margin = Cm(1.6)
sec.left_margin = Cm(2.0); sec.right_margin = Cm(2.0)

normal = doc.styles["Normal"]
normal.font.name = "Segoe UI"; normal.font.size = Pt(10.5); normal.font.color.rgb = INK
normal.paragraph_format.space_after = Pt(5); normal.paragraph_format.line_spacing = 1.14

for name, size, color in [("Heading 1", 17, NAVY), ("Heading 2", 12.5, TEAL)]:
    st = doc.styles[name]
    st.font.name = "Segoe UI Semibold"; st.font.size = Pt(size); st.font.bold = True
    st.font.color.rgb = color
    st.paragraph_format.space_before = Pt(10 if name == "Heading 1" else 12)
    st.paragraph_format.space_after = Pt(4)
    st.paragraph_format.keep_with_next = True

def shade(paragraph, hexcolor):
    pPr = paragraph._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hexcolor)
    pPr.append(shd)

def left_border(paragraph, color="9FE3DC", size="18"):
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    el = OxmlElement("w:left")
    el.set(qn("w:val"), "single"); el.set(qn("w:sz"), size)
    el.set(qn("w:space"), "6"); el.set(qn("w:color"), color)
    pBdr.append(el); pPr.append(pBdr)

def add_field(paragraph, instruction):
    run = paragraph.add_run()
    f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instruction
    f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "end")
    run._r.append(f1); run._r.append(it); run._r.append(f2)

def H1(text):
    p = doc.add_paragraph(style="Heading 1")
    p.paragraph_format.space_before = Pt(14)
    p.add_run(text)
    return p

def H2(text):
    return doc.add_paragraph(text, style="Heading 2")

def P(text, size=10.5, color=INK, italic=False, after=5, bold=False):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    r = p.add_run(text); r.font.size = Pt(size); r.font.color.rgb = color; r.italic = italic; r.bold = bold
    return p

def bullet(text, lead=None):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    p.paragraph_format.first_line_indent = Cm(-0.3)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("-  "); r.font.color.rgb = TEAL; r.bold = True
    if lead:
        r2 = p.add_run(lead); r2.bold = True
    p.add_run(text)
    return p

def say(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.35)
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after = Pt(7)
    shade(p, "EFF8F7"); left_border(p)
    r = p.add_run("“" + text + "”")
    r.font.size = Pt(10.8); r.italic = True; r.font.color.rgb = NAVY
    return p

def cue(label, text):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(label + "  ")
    r.font.size = Pt(8.5); r.bold = True; r.font.color.rgb = TEAL
    r2 = p.add_run(text); r2.font.size = Pt(9.5); r2.font.color.rgb = GRAY
    return p

def slide(num, title, timing, show, text):
    H2("Slide %d  ·  %s      [%s]" % (num, title, timing))
    cue("SHOW", show)
    say(text)

hp = sec.header.paragraphs[0]
hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r = hp.add_run("INGRES · Presenter script")
r.font.size = Pt(8); r.font.color.rgb = LIGHT
fp = sec.footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r = fp.add_run("Page "); r.font.size = Pt(8); r.font.color.rgb = LIGHT
add_field(fp, "PAGE")
r = fp.add_run(" of "); r.font.size = Pt(8); r.font.color.rgb = LIGHT
add_field(fp, "NUMPAGES")

p = doc.add_paragraph()
r = p.add_run("PRESENTER SCRIPT")
r.font.size = Pt(9); r.bold = True; r.font.color.rgb = TEAL
p.paragraph_format.space_after = Pt(2)
p = doc.add_paragraph()
r = p.add_run("INGRES — 10-minute demo")
r.font.size = Pt(30); r.bold = True; r.font.color.rgb = NAVY
p.paragraph_format.space_after = Pt(2)
p = doc.add_paragraph()
r = p.add_run("National Groundwater Intelligence Platform")
r.font.size = Pt(13); r.font.color.rgb = GRAY
p.paragraph_format.space_after = Pt(12)

P("How to use this script: “SHOW” is what to point at, the shaded quote is what to say, and “IF ASKED” is your backup answer. Times are guides, not rules. The full deck runs about 10 minutes; the 6-minute cut is at the end.", size=10, color=GRAY)

H1("Before you start (30 seconds of prep)")
bullet("Streamlit running at http://localhost:8501; keep one browser tab on the dashboard and one on the Copilot.", "App:  ")
bullet("Know your three numbers: 3,042 stations, 16,780 water-level records, 11,978 lab tests.", "Numbers:  ")
bullet("If the app fails, the deck screenshots are the backup. Do not debug in front of judges.", "Backup:  ")
bullet("Do not click “Ingest Selected States” during the demo — it downloads and writes to the database.", "Avoid:  ")

H1("The three sentences that carry the whole pitch")
P("If you forget everything else, say these three lines at some point:")
bullet("It answers from the database, not from the model.", "1.  ")
bullet("Every number comes with a receipt: station, date and quality flag.", "2.  ")
bullet("When the data can’t support an answer, it says so instead of guessing.", "3.  ")

H1("Slide-by-slide")

slide(1, "Title", "0:30",
      "Title slide. Stay on the big INGRES wordmark; do not read the subtitle.",
      "Groundwater is India’s invisible lifeline — most of our farming and most of our rural drinking water depends on it. But the answers we need are buried in millions of readings across government portals. INGRES is our attempt to make that data answer questions a hydrogeologist can actually defend.")

slide(2, "The problem", "0:45",
      "Point at the three cards in order, then sweep the four statistics at the bottom.",
      "There are three problems. First, the data is siloed — manual readings, sensor telemetry and lab reports live in different places. Second, generic AI invents numbers. For water security, a confident wrong number is worse than no answer. Third, normal answers don’t tell you which station they came from, or whether the district is even monitored. These four numbers show why it matters: over half our irrigation and most rural drinking water depend on this resource.")

slide(3, "Solution overview", "0:50",
      "Point at the four pillars, left to right. Land on the bottom strip of five numbers.",
      "So we flipped the order. Normally AI reads a question and tries to remember an answer. We make the database answer first, and the AI is only allowed to explain what the database returned. Four pieces make that work: deterministic SQL, a coverage check before we answer, evidence attached to every claim, and freedom to use any model — or no model at all.")

slide(4, "Executive dashboard", "0:40",
      "Point at the KPI row, then the bar chart, then the donut.",
      "This is the national picture on one screen. 3,042 stations, 16,780 observations, 11,978 lab tests. The bar chart is extraction intensity by state — the red dashed line is the 100% critical threshold, and Rajasthan and Gujarat are above it. On the right, contamination: TDS, nitrate, fluoride and arsenic exceedances. This page is pure aggregation — no model involved.")

slide(5, "Architecture", "0:50",
      "Trace left to right with your hand or cursor: UI → router → coverage → retrieval → assembly → generation → response. Then drop to the data plane.",
      "Here’s the whole machine. A question comes in from Streamlit, gets classified, gets checked against the data we actually have, then retrieves rows from DuckDB or the knowledge base. Only after that does the model write anything. The bottom row is the foundation: the database, a small hydrogeology knowledge base, and the live feed from the national water portal.")

slide(6, "How a query is processed", "0:50",
      "Point at steps 2 and 7 while speaking. Let them read the SQL on the right.",
      "Seven steps, but two matter most. Step two: before we answer, we check coverage — is this district monitored, is this year in range, is there enough data for a trend. Step seven: we hand back the evidence — the rows, the SQL, the sources, and a button to send it for expert review. The SQL on the right is real: it only queries, caps results at 500 rows, and can never delete or update anything.")

slide(7, "Data foundation", "0:35",
      "Touch each table card. Point at the standards chips.",
      "Four tables, deliberately boring. Stations, seasonal levels, chemical samples, and GEC assessment units. Everything else is derived: potability is computed from BIS drinking-water limits, and the GEC category is computed from the stage of extraction. So the same rule applies to every row, not to each answer.")

slide(8, "Technology stack", "0:35",
      "Point at DuckDB and Streamlit, then at the optional items.",
      "The stack is small on purpose. Streamlit for the interface, DuckDB as a single-file analytical database — no server to manage — Plotly for charts, and Pydantic to validate data on the way in. The semantic search stack is optional; if it isn’t installed, a TF-IDF fallback still works. And the language model is optional too: with no API key, a deterministic synthesizer keeps the system usable.")

slide(9, "AI copilot", "1:00",
      "Point at the sidebar provider badge, the question, the green confidence badge, then the answer and SQL.",
      "This is the core interaction. The sidebar shows which model is live — here OpenRouter is online. The question is: which state has the most potable wells? The answer is Uttar Pradesh, 399 wells, marked fully supported with medium confidence. Notice it says “source: SQL query result” — the number comes from a query, not from the model’s memory. Below, every answer can open into its evidence drawer: station IDs, dates, quality flags, the exact SQL and a CSV export.")

slide(10, "Station dossier", "0:40",
      "Point at the cascading filters, the profile fields, and the map. If the hydrograph is visible, point at the reversed axis.",
      "Now zoom into one well. Pick a state, a district, a station. You get the aquifer type, borehole depth, installation year, coordinates and a map. The health score is the share of readings with a good quality flag. The hydrograph has the depth axis reversed, so a falling water table actually looks like a falling line — which is how a hydrogeologist reads it.")

slide(11, "Data explorer", "0:35",
      "Point at the four tabs and the map.",
      "This page exists so nobody has to take our word for it. The same four tables are browsable and filterable here: state, season, quality flag, potability, GEC category. If a judge doubts a number in the copilot, this is where you prove it.")

slide(12, "Performance", "0:40",
      "Point at the top KPI row, then the two charts.",
      "We measure the system instead of claiming it works. SQL success is 83.3% across our benchmark, provenance precision is 100% — meaning no answer cited something that didn’t exist — and edge cases are intercepted 100% of the time. Latency is in the tens of milliseconds. The button at the bottom re-runs the whole 30-case audit live.")

slide(13, "Safety", "0:35",
      "Point at the four guardrail bullets on the right.",
      "Safety is the feature, not the footnote. The SQL is read-only — no delete, no update, no drop. Results are capped. Drinking-water thresholds are fixed constants, not the model’s opinion. And if observations conflict, the case goes to human review instead of being smoothed over.")

slide(14, "NWIC live sync", "0:40",
      "Point at the portal status, the state selector, then the station table and map.",
      "The data supply chain is visible too. This page streams official quarterly readings from the National Water Data Portal — 2,842 stations ingested so far across eight states. Ingestion is idempotent: re-running it updates records instead of duplicating them. If the portal is down, the cached database still answers questions; the status badge tells you which mode you’re in.")

slide(15, "Evaluation", "0:45",
      "Point at the three big cards, then the four category bars. Be honest about the normal-query bar.",
      "Thirty documented questions, four categories. Overall pass rate 83.3%, provenance 100%, P95 latency 38 milliseconds. Edge cases and ambiguous locations pass completely, which is the point — the guardrails hold. Normal structured queries are our weakest area at 66.7%, mostly because some question shapes aren’t templated yet and the fallback router can misread a location. We’d rather show that than hide it.")

slide(16, "Run it", "0:30",
      "Point at the four terminal lines. Do not read the env block aloud.",
      "It runs in four commands and needs no API key. If a provider key is added, the prose gets better — but retrieval, coverage and provenance stay exactly the same. That separation is deliberate.")

slide(17, "Close", "0:30",
      "Return to the closing slide and slow down.",
      "Verified. Cited. Auditable. That’s the whole idea — not a chatbot that sounds right, but a system a hydrogeologist can defend in front of a review committee. Thank you — happy to take questions.")

H1("Numbers to memorise")
table_rows = [
    ("Stations / observations / lab tests", "3,042  /  16,780  /  11,978"),
    ("GEC assessment units", "100  (8 over-exploited)"),
    ("Potable samples", "91.7%  (997 non-potable)"),
    ("Benchmark pass rate", "83.3%  (25 of 30)"),
    ("Provenance precision", "100%"),
    ("SQL success", "83.3%"),
    ("Latency", "32 ms mean  ·  38 ms P95"),
    ("Unit tests", "25 passing"),
]
t = doc.add_table(rows=0, cols=2)
t.autofit = False
for k, v in table_rows:
    cells = t.add_row().cells
    cells[0].width = Inches(3.2); cells[1].width = Inches(3.2)
    p0 = cells[0].paragraphs[0]; p0.paragraph_format.space_after = Pt(1)
    r0 = p0.add_run(k); r0.font.size = Pt(9.5); r0.bold = True
    p1 = cells[1].paragraphs[0]; p1.paragraph_format.space_after = Pt(1)
    r1 = p1.add_run(v); r1.font.size = Pt(9.5); r1.font.color.rgb = NAVY

H1("Likely questions, short answers")
qa = [
    ("Why not just use ChatGPT?", "Because it invents numbers. We retrieve first and cite every value; the model only explains what the database returned."),
    ("Is the data real?", "Yes — official CGWB datasets streamed from the National Water Data Portal; 2,842 live stations in the current database."),
    ("What happens when data is missing?", "The coverage detector flags it before generation. The answer says what is missing and why, instead of filling the gap."),
    ("How accurate is it?", "83.3% pass on 30 documented questions, with 100% provenance precision. We publish the weak spots too — normal queries are at 66.7%."),
    ("Why DuckDB?", "Single file, no server, full analytical SQL. It lets the whole platform ship as a repository plus one database file."),
    ("Does it need an API key?", "No. Without a key a deterministic synthesizer answers; with a key the narrative quality improves but the retrieval path does not change."),
    ("Can it scale?", "The retrieval is plain SQL, so it can move to a warehouse. The database is the bottleneck, not the interface."),
    ("What’s next?", "Tighten the fallback router, add more reviewed SQL templates, widen ingestion, and formalise the expert-review workflow."),
]
for q, a in qa:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("Q: " + q); r.bold = True; r.font.size = Pt(9.8); r.font.color.rgb = NAVY
    p2 = doc.add_paragraph()
    p2.paragraph_format.left_indent = Cm(0.4)
    p2.paragraph_format.space_after = Pt(6)
    r2 = p2.add_run("A: " + a); r2.font.size = Pt(9.8)

H1("If something breaks")
bullet("restart with streamlit run app/main.py, then check http://localhost:8501/_stcore/health.", "App:  ")
bullet("the database still answers; the NWIC page shows limited access. Say that out loud — it is the designed fallback.", "Network:  ")
bullet("that is the coverage detector working. Explain it, don’t apologise for it.", "A query returns Insufficient data:  ")
bullet("type it anyway. If it returns partial or insufficient, that demonstrates the guardrail.", "An unknown query:  ")
bullet("drop slides 7, 8, 11 and 16. The story still holds in six minutes.", "Running long:  ")

H1("The six-minute cut")
P("Slides 1 → 2 → 3 → 4 → 9 (demo) → 13 → 15 → 17. Skip the architecture diagram unless someone asks; the three sentences and the live copilot carry the pitch.")

doc.save(OUT_DOCX)

md = []
md.append("# INGRES — presenter script (10-minute demo)\n")
md.append("SHOW = what to point at. The quote is what to say.\n")
md.append("## Before you start\n")
md.append("- App running at http://localhost:8501; keep dashboard and Copilot tabs open.")
md.append("- Numbers: 3,042 stations · 16,780 water-level records · 11,978 lab tests · 100 GEC units.")
md.append("- Backup: the deck screenshots. Do not debug in front of judges.")
md.append("- Do not click Ingest Selected States during the demo.\n")
md.append("## The three sentences\n")
md.append("1. It answers from the database, not from the model.")
md.append("2. Every number comes with a receipt: station, date and quality flag.")
md.append("3. When the data cannot support an answer, it says so instead of guessing.\n")
md.append("## Slide-by-slide\n")
slides_md = [
    (1, "Title", "0:30", "Title slide; stay on the wordmark.",
     "Groundwater is India’s invisible lifeline — most farming and most rural drinking water depends on it. But the answers are buried in millions of readings across government portals. INGRES makes that data answer questions a hydrogeologist can defend."),
    (2, "The problem", "0:45", "Point at the three cards, then the four statistics.",
     "Three problems: data is siloed; generic AI invents numbers; answers do not say which station they came from. A confident wrong number is worse than no answer in water security."),
    (3, "Solution", "0:50", "Point at the four pillars, then the number strip.",
     "We flipped the order: the database answers first, the AI only explains what it returned. Deterministic SQL, a coverage check, evidence on every claim, and freedom to use any model or none."),
    (4, "Dashboard", "0:40", "KPIs, then bar chart, then donut.",
     "The national picture: 3,042 stations, 16,780 observations, 11,978 lab tests; extraction intensity against the 100% threshold; contamination watch. Pure aggregation, no model."),
    (5, "Architecture", "0:50", "Trace left to right; then the data plane.",
     "Question to route to coverage to retrieval to assembly to generation to response. The data plane is DuckDB, a small knowledge base and live NWIC ingestion."),
    (6, "Query lifecycle", "0:50", "Point at steps 2 and 7; let them read the SQL.",
     "Two steps matter most: coverage checked before answering, and evidence handed back at the end — rows, SQL, sources, expert-review option."),
    (7, "Data foundation", "0:35", "Four table cards; standards chips.",
     "Four tables: stations, levels, quality, GEC units. Potability and GEC category are derived by rule, so every row is interpreted the same way."),
    (8, "Tech stack", "0:35", "DuckDB, Streamlit, optional items.",
     "Small on purpose: Streamlit, single-file DuckDB, Plotly, Pydantic. The semantic stack and the model are optional — offline still works."),
    (9, "Copilot", "1:00", "Provider badge, question, confidence badge, SQL.",
     "Live provider on the left; ask which state has the most potable wells; 399 wells, fully supported. The number cites the SQL result, and the evidence drawer has station IDs, dates and flags."),
    (10, "Dossier", "0:40", "Filters, profile, map, hydrograph.",
     "Zoom into one well: aquifer, depth, coordinates, health score. The depth axis is reversed so a falling water table looks like a falling line."),
    (11, "Explorer", "0:35", "Four tabs and the map.",
     "Anyone can verify the numbers themselves: filter the same four tables by state, season, flag, potability or GEC category."),
    (12, "Performance", "0:40", "KPI row; two charts.",
     "Measured, not claimed: 83.3% SQL success, 100% provenance precision, edge cases intercepted. The button reruns the 30-case audit live."),
    (13, "Safety", "0:35", "Four guardrails on the right.",
     "Read-only SQL, capped results, fixed BIS thresholds, and human review for conflicts. Refusal is the designed failure mode."),
    (14, "NWIC sync", "0:40", "Status, selector, table, map.",
     "Official data streams from the national portal — 2,842 stations so far. Re-running updates instead of duplicating. If the portal is down, cached data still answers."),
    (15, "Evaluation", "0:45", "Three cards, four bars; be honest about normal queries.",
     "30 questions: 83.3% pass, 100% provenance, P95 38 ms. Edge cases and ambiguity pass completely; normal queries are the weak spot at 66.7% — we show it rather than hide it."),
    (16, "Run it", "0:30", "Four terminal lines.",
     "Four commands, no API key required. A provider key improves the prose but not the retrieval, coverage or provenance."),
    (17, "Close", "0:30", "Closing slide; slow down.",
     "Verified. Cited. Auditable. Not a chatbot that sounds right, but a system a hydrogeologist can defend."),
]
for num, title, timing, show, text in slides_md:
    md.append("### Slide %d · %s  [%s]\n" % (num, title, timing))
    md.append("**SHOW:** " + show + "\n")
    md.append("> " + text + "\n")
md.append("## Numbers\n")
md.append("| Metric | Value |")
md.append("|---|---|")
for k, v in table_rows:
    md.append("| %s | %s |" % (k, v))
md.append("\n## Likely questions\n")
for q, a in qa:
    md.append("- **%s** — %s" % (q, a))
md.append("\n## If something breaks\n")
md.append("- App: restart with streamlit run app/main.py; health at http://localhost:8501/_stcore/health.")
md.append("- Network: cached data still answers; NWIC shows limited access.")
md.append("- Refusal: explain the coverage guardrail instead of apologising.")
md.append("- Running long: drop slides 7, 8, 11, 16 — six-minute cut.")
md.append("\n## Six-minute cut\n")
md.append("Slides 1 → 2 → 3 → 4 → 9 (demo) → 13 → 15 → 17.")

with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write("\n".join(md))
print("saved", os.path.abspath(OUT_DOCX))
print("saved", os.path.abspath(OUT_MD))
