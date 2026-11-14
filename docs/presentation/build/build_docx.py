
"""Build the INGRES technical report (DOCX)."""
import os
from docx import Document
from docx.shared import Pt, Inches, RGBColor, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BASE = os.path.dirname(os.path.abspath(__file__))
SHOTS = os.path.join(BASE, "..", "screenshots")
BUILD = BASE
OUT = os.path.join(BASE, "..", "INGRES_Project_Report.docx")

NAVY = RGBColor(0x0B, 0x3D, 0x63)
TEAL = RGBColor(0x0D, 0x94, 0x88)
INK = RGBColor(0x1F, 0x23, 0x28)
GRAY = RGBColor(0x57, 0x60, 0x6A)
LIGHT = RGBColor(0x6E, 0x77, 0x81)
ACCENT = "2DD4BF"
NAVY_HEX = "0B3D63"
CODE_BG = "F6F8FA"
CALLOUT_BG = "EFF8F7"

doc = Document()

# ── Page setup ───────────────────────────────────────────────────────────────
sec = doc.sections[0]
sec.page_width = Cm(21.0)
sec.page_height = Cm(29.7)
sec.top_margin = Cm(1.9)
sec.bottom_margin = Cm(1.8)
sec.left_margin = Cm(2.2)
sec.right_margin = Cm(2.2)
CONTENT_W = 6.55  # inches

# ── Base styles ──────────────────────────────────────────────────────────────
normal = doc.styles["Normal"]
normal.font.name = "Segoe UI"
normal.font.size = Pt(10.5)
normal.font.color.rgb = INK
normal.paragraph_format.space_after = Pt(6)
normal.paragraph_format.line_spacing = 1.16
try:
    normal.element.rPr.rFonts.set(qn("w:eastAsia"), "Segoe UI")
except Exception:
    pass

for name, size, color, before, after in [
    ("Heading 1", 19, NAVY, 6, 8),
    ("Heading 2", 13.5, TEAL, 12, 4),
    ("Heading 3", 11, INK, 8, 2),
]:
    st = doc.styles[name]
    st.font.name = "Segoe UI Semibold"
    st.font.size = Pt(size)
    st.font.bold = True
    st.font.color.rgb = color
    st.paragraph_format.space_before = Pt(before)
    st.paragraph_format.space_after = Pt(after)
    st.paragraph_format.keep_with_next = True

def shade_cell(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)

def set_table_borders(table, color="D0D7DE", size="4"):
    tblPr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), "single"); el.set(qn("w:sz"), size)
        el.set(qn("w:space"), "0"); el.set(qn("w:color"), color)
        borders.append(el)
    tblPr.append(borders)

def cell_margins(table, top=60, bottom=60, left=100, right=100):
    tblPr = table._tbl.tblPr
    mar = OxmlElement("w:tblCellMar")
    for edge, val in (("top", top), ("bottom", bottom), ("left", left), ("right", right)):
        el = OxmlElement("w:" + edge)
        el.set(qn("w:w"), str(val)); el.set(qn("w:type"), "dxa")
        mar.append(el)
    tblPr.append(mar)

def para_border(paragraph, color=ACCENT, size="18", position="bottom"):
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    el = OxmlElement("w:" + position)
    el.set(qn("w:val"), "single"); el.set(qn("w:sz"), size)
    el.set(qn("w:space"), "4"); el.set(qn("w:color"), color)
    pBdr.append(el)
    pPr.append(pBdr)

def add_field(paragraph, instruction):
    run = paragraph.add_run()
    f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin")
    it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instruction
    f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"), "end")
    run._r.append(f1); run._r.append(it); run._r.append(f2)
    return run

def H1(text, number=None, newpage=False):
    p = doc.add_paragraph(style="Heading 1")
    p.paragraph_format.space_before = Pt(12)
    if newpage:
        p.paragraph_format.page_break_before = True
    run = p.add_run((number + "  " if number else "") + text)
    para_border(p, ACCENT, "12")
    return p

def H2(text):
    return doc.add_paragraph(text, style="Heading 2")

def H3(text):
    return doc.add_paragraph(text, style="Heading 3")

def P(text, lead=None, size=10.5, color=INK, italic=False, after=6):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(after)
    if lead:
        r = p.add_run(lead)
        r.bold = True; r.font.size = Pt(size); r.font.color.rgb = NAVY
    r = p.add_run(text)
    r.font.size = Pt(size); r.font.color.rgb = color; r.italic = italic
    return p

def bullet(text, bold_lead=None):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.55)
    p.paragraph_format.first_line_indent = Cm(-0.35)
    p.paragraph_format.space_after = Pt(2)
    r = p.add_run("•  ")
    r.font.color.rgb = TEAL; r.bold = True
    if bold_lead:
        r2 = p.add_run(bold_lead); r2.bold = True; r2.font.color.rgb = INK
    r3 = p.add_run(text)
    return p

def code_block(text):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.3)
    p.paragraph_format.right_indent = Cm(0.3)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(8)
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), CODE_BG)
    pPr.append(shd)
    pBdr = OxmlElement("w:pBdr")
    for edge in ("top", "left", "bottom", "right"):
        el = OxmlElement("w:" + edge)
        el.set(qn("w:val"), "single"); el.set(qn("w:sz"), "4"); el.set(qn("w:space"), "4"); el.set(qn("w:color"), "D0D7DE")
        pBdr.append(el)
    pPr.append(pBdr)
    for i, line in enumerate(text.strip("\n").split("\n")):
        r = p.add_run(line)
        r.font.name = "Consolas"; r.font.size = Pt(8.1); r.font.color.rgb = INK
        if i < text.strip("\n").count("\n"):
            r.add_break()
    return p

def callout(title, text):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.cell(0, 0)
    cell.width = Inches(CONTENT_W)
    shade_cell(cell, CALLOUT_BG)
    set_table_borders(t, "9FE3DC", "4")
    cell_margins(t, 120, 120, 160, 160)
    p = cell.paragraphs[0]
    p.paragraph_format.space_after = Pt(3)
    r = p.add_run(title)
    r.bold = True; r.font.size = Pt(9.5); r.font.color.rgb = TEAL
    p2 = cell.add_paragraph()
    p2.paragraph_format.space_after = Pt(0)
    r2 = p2.add_run(text)
    r2.font.size = Pt(9.8)
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t

def table(headers, rows, widths, font=9, header_fill=NAVY_HEX, stripe="F6F8FA"):
    t = doc.add_table(rows=1, cols=len(headers))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    set_table_borders(t)
    cell_margins(t, 50, 50, 80, 80)
    hdr = t.rows[0]
    for i, h in enumerate(headers):
        c = hdr.cells[i]
        c.width = Inches(widths[i])
        shade_cell(c, header_fill)
        p = c.paragraphs[0]
        p.paragraph_format.space_after = Pt(0)
        r = p.add_run(h)
        r.bold = True; r.font.size = Pt(font); r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    # repeat header row
    trPr = hdr._tr.get_or_add_trPr()
    th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
    for ri, row in enumerate(rows):
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].width = Inches(widths[i])
            if ri % 2 == 1:
                shade_cell(cells[i], stripe)
            p = cells[i].paragraphs[0]
            p.paragraph_format.space_after = Pt(0)
            r = p.add_run(str(val))
            r.font.size = Pt(font)
            if i == 0:
                r.bold = True
    doc.add_paragraph().paragraph_format.space_after = Pt(2)
    return t

def figure(path, caption, width=CONTENT_W):
    t = doc.add_table(rows=1, cols=1)
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = t.cell(0, 0)
    cell.width = Inches(width)
    set_table_borders(t, "D0D7DE", "4")
    cell_margins(t, 40, 40, 40, 40)
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(path, width=Inches(width - 0.08))
    cap = cell.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    cap.paragraph_format.space_before = Pt(2)
    cap.paragraph_format.space_after = Pt(6)
    r = cap.add_run(caption)
    r.italic = True; r.font.size = Pt(8.8); r.font.color.rgb = LIGHT
    trPr = t.rows[0]._tr.get_or_add_trPr()
    cant = OxmlElement("w:cantSplit"); cant.set(qn("w:val"), "true"); trPr.append(cant)
    spacer(8)

def spacer(pts=4):
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(pts)
    return p

# ── Header / footer ─────────────────────────────────────────────────────────
header = sec.header
hp = header.paragraphs[0]
hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r = hp.add_run("INGRES · Technical Report")
r.font.size = Pt(8.5); r.font.color.rgb = LIGHT; r.font.name = "Segoe UI"
para_border(hp, "D0D7DE", "6")

footer = sec.footer
fp = footer.paragraphs[0]
fp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
r = fp.add_run("National Groundwater Intelligence Platform  ·  Page ")
r.font.size = Pt(8.5); r.font.color.rgb = LIGHT
add_field(fp, "PAGE")
r = fp.add_run(" of ")
r.font.size = Pt(8.5); r.font.color.rgb = LIGHT
add_field(fp, "NUMPAGES")

# ── Cover ───────────────────────────────────────────────────────────────────
spacer(60)
p = doc.add_paragraph()
r = p.add_run("SIH 2026  ·  PROBLEM CODE SIH26063")
r.font.size = Pt(9); r.font.color.rgb = TEAL; r.bold = True
p.paragraph_format.space_after = Pt(18)

p = doc.add_paragraph()
r = p.add_run("INGRES")
r.font.size = Pt(52); r.bold = True; r.font.color.rgb = NAVY
p.paragraph_format.space_after = Pt(2)

p = doc.add_paragraph()
r = p.add_run("National Groundwater Intelligence Platform")
r.font.size = Pt(20); r.font.color.rgb = TEAL
p.paragraph_format.space_after = Pt(10)
para_border(p, ACCENT, "20")

p = doc.add_paragraph()
r = p.add_run("Technical design and evaluation report")
r.font.size = Pt(13); r.font.color.rgb = GRAY
p.paragraph_format.space_after = Pt(14)

p = doc.add_paragraph()
r = p.add_run("An AI-assisted hydrogeological discovery system over the CGWB / NWIC national monitoring network — deterministic retrieval, pre-answer coverage checks, BIS water-quality intelligence and station-level provenance.")
r.font.size = Pt(10.8); r.font.color.rgb = INK
p.paragraph_format.line_spacing = 1.3
p.paragraph_format.space_after = Pt(24)

meta = [
    ("Platform", "Python 3.15  ·  Streamlit 1.66  ·  DuckDB 2.0  ·  Plotly 7.1"),
    ("Data source", "CGWB via the National Water Data Portal (nwdp.nwic.gov.in)"),
    ("Indexed record", "3,042 stations  ·  16,780 water-level observations  ·  11,978 quality tests"),
    ("Standards", "GEC-2015 resource assessment  ·  BIS 10500:2012 drinking water"),
    ("Evaluation", "30 benchmark queries  ·  25 passing unit tests  ·  100% provenance precision"),
    ("Prepared", "November 2026"),
]
t = doc.add_table(rows=0, cols=2)
t.autofit = False
set_table_borders(t, "E5E7EB", "4")
cell_margins(t, 70, 70, 100, 100)
for k, v in meta:
    cells = t.add_row().cells
    cells[0].width = Inches(1.55); cells[1].width = Inches(5.0)
    shade_cell(cells[0], "F6F8FA")
    p0 = cells[0].paragraphs[0]; p0.paragraph_format.space_after = Pt(0)
    r0 = p0.add_run(k); r0.bold = True; r0.font.size = Pt(9); r0.font.color.rgb = GRAY
    p1 = cells[1].paragraphs[0]; p1.paragraph_format.space_after = Pt(0)
    r1 = p1.add_run(v); r1.font.size = Pt(9); r1.font.color.rgb = INK

# ── Contents ────────────────────────────────────────────────────────────────
doc.add_page_break()
p = doc.add_paragraph()
r = p.add_run("Contents")
r.font.size = Pt(18); r.bold = True; r.font.color.rgb = NAVY
p.paragraph_format.space_after = Pt(10)
para_border(p, ACCENT, "12")

toc = [
    ("1", "Executive summary"),
    ("2", "The problem"),
    ("3", "Solution overview"),
    ("4", "System architecture"),
    ("5", "How a query is processed"),
    ("6", "Data model and ingestion"),
    ("7", "Technology stack and dependencies"),
    ("8", "Platform modules"),
    ("9", "Evaluation and performance"),
    ("10", "Safety, governance and limitations"),
    ("11", "Deployment and operation"),
    ("12", "Conclusion"),
    ("A", "Repository map"),
    ("B", "Command reference"),
    ("C", "References"),
]
for num, title in toc:
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.left_indent = Cm(0.2)
    r = p.add_run(num.rjust(2) + "   ")
    r.bold = True; r.font.color.rgb = TEAL; r.font.size = Pt(10)
    r = p.add_run(title)
    r.font.size = Pt(10.5); r.font.color.rgb = INK

# ═══════════════════════════════════════════════════════════════════════════
# 1 Executive summary
H1("Executive summary", "1", newpage=True)
P("INGRES is a groundwater intelligence platform that answers natural-language questions over the national CGWB monitoring record. It indexes 3,042 stations, 16,780 seasonal water-level observations, 11,978 laboratory chemistry samples and 100 GEC-2015 assessment units in a normalized DuckDB database, then answers questions through a pipeline that retrieves evidence before it writes a sentence.")
P("The central design assumption is that generative AI is useful in water management only after retrieval and verification. Every request is classified, checked against a coverage rulebook, answered from a read-only SQL query or the curated knowledge base, assembled into evidence, and only then narrated. Each answer carries a response state, a confidence level, the cited station records, the executed SQL and an explicit note about what the data does and does not cover. When the database cannot support an answer, the system says so rather than inventing a number.")
callout("Measured on 30 documented benchmark questions",
        "83.3% overall pass rate  ·  100% provenance precision  ·  83.3% SQL success  ·  63.3% coverage-detection recall  ·  32 ms mean latency  ·  38 ms P95 latency.")
P("INGRES runs with no API key at all: a deterministic hydro synthesizer keeps the system usable offline, while OpenRouter, Google Gemini, OpenAI or any OpenAI-compatible local endpoint can be configured for richer narrative generation. The interface is a six-page Streamlit application covering an executive dashboard, the AI copilot, station dossiers, a raw data catalog, a performance audit and live NWIC ingestion.")
H3("What this report covers")
for lead, text in [
    ("Architecture. ", "the seven-stage request pipeline and the data plane behind it."),
    ("Data. ", "the four-table schema, validation rules and the live NWIC ingestion path."),
    ("Technology. ", "the exact stack and why each dependency is present."),
    ("Evidence. ", "live captures of every module, plus the evaluation methodology and results."),
    ("Limits. ", "where the system refuses to answer, and what remains to be hardened."),
]:
    bullet(text, lead)

# ═══════════════════════════════════════════════════════════════════════════
H1("The problem", "2")
P("Groundwater is India's most consequential invisible resource. It supplies more than 60% of irrigated agriculture and roughly 85% of rural drinking water, yet the evidence layer that should guide decisions is fragmented, inconsistently formatted and rarely cited at the point of use.")
H2("2.1  Three bottlenecks")
P("Millions of readings are spread across manual quarterly hydrographs, telemetry from Digital Water Level Recorders, and laboratory chemistry sheets from CGWB and NWIC portals. The same district may appear under several spellings, the same station under both a legacy and a live identifier. Without a normalized schema, even simple questions — what is the pre-monsoon level in a district, and is it falling? — require manual joining of files that were never designed to be joined.", lead="Siloed and heterogeneous data.  ")
P("Generic assistants produce fluent, plausible and wrong groundwater answers: a fabricated depth, a station that does not exist, a trend inferred from three readings. In water security the failure is asymmetric — a confident wrong number is worse than an explicit refusal.", lead="Language models that invent numbers.  ")
P("Conventional search and chat interfaces rarely state which station produced a value, when it was measured, whether the quality flag is good, or whether the requested district is monitored at all. Decision-makers are left to reconstruct context that the system should have supplied.", lead="No provenance and no boundaries.  ")
H2("2.2  Why this is hard for generic RAG")
P("Document chunking is a poor fit for numerical monitoring data. A chunk of text cannot be aggregated by season, joined to a well's coordinates, filtered by a quality flag or validated against a drinking-water threshold. INGRES therefore treats structured retrieval as the primary path and reserves semantic search for genuinely conceptual questions, where citations come from a curated hydrogeology knowledge base.")

# ═══════════════════════════════════════════════════════════════════════════
H1("Solution overview", "3")
P("INGRES is built on five design principles, each of which is visible in the product rather than only in the architecture.")
H2("3.1  Design principles")
principles = [
    ("Retrieve before you generate. ", "The generator receives a dataframe, summary statistics, the executed SQL and a coverage verdict. It is never asked to recall a groundwater fact from model weights."),
    ("Deterministic where possible. ", "Common question shapes map to reviewed SQL templates. The language model is a fallback for query construction, not the first resort."),
    ("Make uncertainty explicit. ", "Six response states and four confidence levels are computed from data availability and quality, not written by the model."),
    ("Show the evidence. ", "Every answer exposes its station records, measurement dates, quality flags and the exact SQL that produced them, with a one-click CSV export."),
    ("Stay provider-independent. ", "OpenRouter, Gemini, OpenAI, a local Ollama/vLLM endpoint or the built-in offline synthesizer can drive the same pipeline."),
]
for lead, text in principles:
    bullet(text, lead)
H2("3.2  What the user gets")
P("A user can ask a question in plain language and receive: a direct answer grounded in retrieved records; the evidence table behind it; the executed query; a coverage note that states what is missing; a confidence judgement; and the option to export or escalate the case for human review. The same data supports an executive dashboard, a per-station dossier and a filterable catalog for independent verification.")

# ═══════════════════════════════════════════════════════════════════════════
H1("System architecture", "4")
P("The architecture separates presentation, orchestration, retrieval, generation and data. Figure 1 shows the request pipeline; the subsections below describe each stage.")
figure(os.path.join(BUILD, "architecture_light.png"), "Figure 1.  The INGRES request pipeline: UI, routing, coverage detection, hybrid retrieval, context assembly, generation and the provenance envelope, over a data plane of DuckDB, a curated knowledge base and live NWIC ingestion.", width=CONTENT_W)
H2("4.1  Presentation layer")
P("The Streamlit application is the only user-facing component. It holds no business logic: it renders metrics and charts, collects a question, calls the pipeline and displays the structured response. Six pages share a sidebar that exposes the active model provider and key status, and each page reads from the same DuckDB file.")
H2("4.2  Query router")
P("The router assigns one of seven intents — structured level, structured quality, structured assessment, semantic conceptual, ambiguous location, temporal out of range or unsupported — and extracts locations, parameters and time references. When a provider is online it asks the model for a strict JSON object; when it is not, a keyword heuristic with a known-location list takes over, so routing never blocks the request.")
H2("4.3  Coverage detector")
P("Before any answer is generated, five independent rules run against the question and the database. Each can return FULL, PARTIAL, INSUFFICIENT or OUT_OF_SCOPE, and the most severe finding wins. The rules are: temporal bounds (the documented monitoring window is 2015–2023), spatial ambiguity (vague regional phrases, unknown districts and fuzzy candidates), parameter availability (for example arsenic coverage), trend sample size (at least three years of data, with a caution below six), and station density (a single well is not spatially representative).")
H2("4.4  Hybrid retrieval")
P("Structured questions first attempt a reviewed SQL template. If no template applies, the model receives the live schema and domain rules and returns a candidate statement. Every candidate passes the same guard: dangerous DML/DDL keywords are rejected, a SELECT is required, and LIMIT 500 is injected when absent. Execution is read-only. Conceptual questions instead query a ten-chunk curated knowledge base using ChromaDB with sentence-transformer embeddings, falling back to TF-IDF cosine similarity when the vector stack is unavailable — as it is in the current environment. Location resolution and coordinate lookup sit alongside retrieval so the UI can render station maps.")
H2("4.5  Context assembly")
P("The assembled context is deliberately compact: the result dataframe rendered as markdown, computed statistics (mean, min, max, standard deviation, BIS exceedance counts, GEC category counts), the knowledge chunks and the coverage verdict. This is the only factual material the generator is allowed to use.")
H2("4.6  Response generation")
P("A strict prompt instructs the model to cite a station or record for every number, to separate what is available from what is missing, and to state confidence using defined criteria. The output is parsed into a structured response object: state, confidence, answer, evidence list, coverage note, recommendation, SQL and sources. Without a provider key, a deterministic synthesizer produces the same response envelope from the retrieved statistics.")
H2("4.7  Data plane")
P("DuckDB holds four normalized tables. A curated knowledge base holds ten hydrogeology passages drawn from CGWB and BIS guidance. The NWIC loader streams official CSV resources from nwdp.nwic.gov.in, validates coordinates and units, and upserts records idempotently.")

# ═══════════════════════════════════════════════════════════════════════════
H1("How a query is processed", "5")
P("The flow below describes a single request end to end. The worked example uses a real question against the indexed data.")
H2("5.1  Seven stages")
stages = [
    ("Route. ", "classify intent and extract entities."),
    ("Check coverage. ", "run the five rules and fix the coverage status before retrieval."),
    ("Retrieve. ", "execute reviewed or model-generated SQL read-only, or search the knowledge base."),
    ("Assemble. ", "summarize the dataframe and compute statistics that the answer may cite."),
    ("Generate. ", "produce a grounded narrative from the assembled context only."),
    ("Classify. ", "derive the response state and confidence from data availability and well coverage."),
    ("Prove. ", "attach the evidence table, executed SQL, sources, CSV export and review flag."),
]
for i, (lead, text) in enumerate(stages, 1):
    bullet(text, str(i) + ".  " + lead)
H2("5.2  Worked example: fluoride in Nalgonda")
P("Question: “What is the fluoride level in Nalgonda wells?” The router classifies it as a structured quality query and extracts the district. Coverage returns FULL because Nalgonda is monitored and the parameter exists. The template path generates the statement below; it passes the read-only guard and returns six laboratory samples from two stations.")
code_block("""SELECT w.district, w.state, q.sample_date, q.ph, q.tds_mg_l,
       q.fluoride_mg_l, q.arsenic_ug_l, q.nitrate_mg_l,
       q.potability, w.well_id
FROM gw_quality q
JOIN wells w ON q.well_id = w.well_id
WHERE LOWER(w.district) = LOWER('nalgonda')
ORDER BY q.sample_date DESC
LIMIT 500;""")
P("The context assembler summarizes the result and counts BIS exceedances. The generator receives the table and the statistics; the response carries GROUNDED with MEDIUM confidence because only two stations contribute. The evidence drawer exposes the rows below.")
table(
    ["Station", "Sample date", "Fluoride (mg/L)", "TDS (mg/L)", "Potability"],
    [
        ["GW_AP_NAL_002", "2019-03-10", "4.38", "652.2", "non_potable"],
        ["GW_AP_NAL_004", "2019-03-10", "3.14", "167.4", "non_potable"],
        ["GW_AP_NAL_002", "2021-03-10", "3.91", "261.6", "non_potable"],
        ["GW_AP_NAL_004", "2021-03-10", "2.29", "494.8", "non_potable"],
        ["GW_AP_NAL_002", "2023-03-10", "1.82", "588.5", "non_potable"],
        ["GW_AP_NAL_004", "2023-03-10", "1.97", "677.6", "non_potable"],
    ],
    [1.35, 1.05, 1.25, 1.05, 1.15],
)
P("Every row exceeds the BIS 10500 maximum permissible fluoride limit of 1.5 mg/L, and the derived potability flag is non_potable for all six samples. That conclusion is drawn from the dataframe, not from the model, which is the point of the design.")
H2("5.3  Response states")
table(
    ["State", "Meaning", "Typical trigger"],
    [
        ["GROUNDED", "Fully supported by retrieved records", "Rows returned and quality acceptable"],
        ["PARTIAL", "Partially supported; gaps stated", "Coverage partial or missing fraction above 0.3"],
        ["INFERRED", "Plausible inference, no direct measurement", "No rows, but relevant knowledge retrieved"],
        ["INSUFFICIENT", "Cannot answer from the database", "Insufficient coverage and no rows"],
        ["OUT_OF_SCOPE", "Outside the documented boundary", "Year before 2015 or in the future"],
        ["HUMAN_REVIEW", "Conflicting evidence needs an expert", "High variance across wells"],
    ],
    [1.15, 2.5, 2.6],
)
H2("5.4  Confidence levels")
table(
    ["Level", "Criteria"],
    [
        ["HIGH", "Direct measurement, good quality flag, at least three corroborating wells"],
        ["MEDIUM", "Aggregated or seasonal average, suspect flag, or fewer than three wells"],
        ["LOW", "Single reading, estimated value, or extrapolated evidence"],
        ["NONE", "No usable evidence — the response is a refusal, not an estimate"],
    ],
    [0.9, 5.4],
)

# ═══════════════════════════════════════════════════════════════════════════
H1("Data model and ingestion", "6")
P("The schema is intentionally narrow. Four tables cover station metadata, seasonal levels, chemical quality and GEC resource assessment; everything else is derived.")
H2("6.1  Tables")
table(
    ["Table", "Rows", "Key content"],
    [
        ["wells", "3,042", "Station ID, state, district, block, coordinates, aquifer type, borehole depth, installation year, source"],
        ["gw_levels", "16,780", "Season, measurement date, depth to water (mbgl), level relative to sea level, method, quality flag"],
        ["gw_quality", "11,978", "pH, TDS, fluoride, arsenic, nitrate, hardness, iron, laboratory ID, potability"],
        ["assessment_units", "100", "GEC block, recharge, extractable resource, extraction, stage of extraction, category, assessment year"],
    ],
    [1.25, 0.85, 4.5],
)
P("Referential integrity is enforced between levels, quality and wells. Domain constraints are enforced in two places: coordinates must fall inside India's bounding box (6–38°N, 68–98°E), and derived fields are computed by Pydantic validators rather than trusted from upstream text.")
H2("6.2  Derived standards")
P("Potability is derived from BIS 10500:2012 thresholds: TDS above 500 mg/L, fluoride above 1.5 mg/L, nitrate above 45 mg/L or arsenic above 10 µg/L flags a sample non-potable; a sample with no measured contaminants is marked unknown. GEC categories are derived from the stage of extraction: safe below 70%, semi-critical 70–90%, critical 90–100%, over-exploited above 100%, with saline units classified separately.")
table(
    ["Indicator", "Value in the indexed database"],
    [
        ["Samples classified potable / non-potable", "10,981  /  997"],
        ["Samples exceeding the TDS limit", "930"],
        ["Samples exceeding the nitrate limit", "97"],
        ["Samples exceeding the fluoride limit", "24"],
        ["Samples exceeding the arsenic limit", "13"],
        ["GEC units safe / semi-critical / critical / over-exploited / saline", "53 / 25 / 10 / 8 / 4"],
        ["Water-level observations flagged good / suspect / estimated", "16,214 / 420 / 146"],
    ],
    [3.5, 2.8],
)
H2("6.3  Live ingestion")
P("The NWIC loader downloads official quarterly water-level and chemical-quality CSV resources from the National Water Data Portal, then normalizes them: station IDs are constructed from state and station name, coordinates outside India are rejected, seasons are derived from the acquisition month, arsenic is converted from mg/L to µg/L, and potability is evaluated. Records are deduplicated by primary key and written with INSERT OR REPLACE, which makes repeated synchronizations safe.")
P("The current database is composed of 2,842 live NWIC stations and 200 seeded reference stations across twelve states. Observations span 2015 to 2025; the coverage detector deliberately applies the documented 2015–2023 window when judging whether a request is in scope.")

# ═══════════════════════════════════════════════════════════════════════════
H1("Technology stack and dependencies", "7")
P("The stack is small and deliberately conventional. Table 1 lists the components that matter, with the version verified in the running environment.")
table(
    ["Layer", "Component", "Version", "Why it is here"],
    [
        ["Runtime", "Python", "3.15.1", "Application runtime and scientific ecosystem"],
        ["Interface", "Streamlit", "1.66.1", "Six-page multi-page app, widgets, session state"],
        ["Charts", "Plotly", "7.1.0", "Interactive hydrographs, bars and distributions"],
        ["Tables", "pandas", "3.1.0", "Dataframe manipulation before and after SQL"],
        ["Database", "DuckDB", "2.0.0", "Columnar analytical SQL over a single file"],
        ["Validation", "Pydantic", "2.14.2", "Typed ingestion models and derived fields"],
        ["Vector store", "ChromaDB", "optional", "Semantic knowledge search when installed"],
        ["Embeddings", "sentence-transformers", "optional", "MiniLM embeddings; TF-IDF fallback exists"],
        ["Fallback search", "scikit-learn", "1.9.1", "TF-IDF cosine similarity for the knowledge base"],
        ["HTTP", "requests + tenacity", "2.34 / 9.2", "NWIC downloads and provider calls with retries"],
        ["Logging", "loguru", "0.7.3", "Structured pipeline diagnostics"],
        ["Config", "python-dotenv", "1.2.4", "Environment-driven provider configuration"],
        ["Testing", "pytest", "9.2.0", "25 passing unit tests across five modules"],
        ["Maps", "Streamlit-Folium / Leaflet", "declared", "Station maps inside the app"],
        ["Models", "OpenRouter · Gemini · OpenAI · custom", "—", "Provider choice, including local endpoints"],
        ["Offline", "Deterministic hydro synthesizer", "built-in", "Zero-key operation and graceful degradation"],
    ],
    [0.95, 1.6, 0.8, 3.2],
    font=8.5,
)
H2("7.1  Dependency philosophy")
P("Two rules shaped the dependency list. First, the analytical engine is the database: DuckDB provides joins, aggregation and window functions without a server, so the project ships as a file plus an app. Second, every optional dependency has a working fallback. ChromaDB and sentence-transformers are the preferred semantic stack, but scikit-learn TF-IDF keeps conceptual search functional when they are absent — and that is exactly how the current environment runs. The language model is likewise an accelerator, not a dependency: without a key, the deterministic synthesizer still produces a complete response envelope.")
H2("7.2  Model configuration")
P("The provider, API key, base URL and model name are read from environment variables and can be overridden in the sidebar. OpenRouter is the default, with Gemini, OpenAI and any OpenAI-compatible endpoint supported. The active provider and its online/offline status are shown in the sidebar so that a user always knows which engine produced the narrative.")

# ═══════════════════════════════════════════════════════════════════════════
H1("Platform modules", "8")
P("The application is organized around the decisions a groundwater analyst actually makes: what is the national posture, what does the evidence say about this question, what is happening at this station, can I verify it myself, is the system reliable, and where did the data come from. The captures below are from the running application.")
H2("8.1  Executive dashboard")
P("The landing page summarizes the national position: monitoring stations, water-table observations, indexed quality tests, potability rate and the number of over-exploited assessment units. A state-level bar chart places extraction stage against the 100% GEC critical threshold, and a contamination donut ranks TDS, nitrate, fluoride and arsenic exceedances. The dashboard is a monitoring surface, not a modeling surface: every number is a direct aggregate of the database.")
figure(os.path.join(SHOTS, "user_01_dashboard_kpis.png"), "Figure 2.  Executive dashboard: headline KPIs, extraction intensity by state against the 100% threshold, and the contamination watch.")
H2("8.2  AI copilot")
P("The copilot is the core interaction. A question is routed, coverage-checked, answered from retrieved evidence and returned with a response state and a confidence badge. The sidebar shows the active provider — in the capture below, OpenRouter is online — and the answer cites the SQL result behind it. The example asks which state has the most potable wells; the system answers Uttar Pradesh with 399 wells and flags the evidence as fully supported, with medium confidence.")
figure(os.path.join(SHOTS, "user_02_copilot.png"), "Figure 3.  AI copilot with a live OpenRouter provider: a grounded answer, confidence badges, and the provider/API configuration visible in the sidebar.")
P("The evidence drawer is where the scientific claim becomes auditable. It shows the coverage assessment, the cited stations, the retrieved records with dates and quality flags, the executed SQL, a CSV export and a human-review action. Figure 4 shows the drawer for the Nalgonda fluoride query used earlier.")
figure(os.path.join(SHOTS, "fig_evidence.png"), "Figure 4.  Evidence drawer for the Nalgonda fluoride query: BIS parameters, retrieved station records and the executed read-only SQL.")
H2("8.3  Station dossier")
P("The dossier answers the question “what do we know about this specific well?”. State, district and station filters cascade; the profile shows aquifer type, borehole depth, telemetry source, installation year and coordinates alongside a map. Health metrics report the number of readings, the latest water table, the share of validated readings and the latest observation date. A seasonal hydrograph uses a reversed depth axis so that a falling water table reads as a downward line, and a quality panel presents the latest sample against BIS limits.")
figure(os.path.join(SHOTS, "user_03_station_dossier.png"), "Figure 5.  Station dossier: cascading filters, station profile, coordinates and location map for a Kerala monitoring station.")
H2("8.4  Data explorer")
P("The data catalog exposes the same four tables that power the answers. Each tab offers filters appropriate to its table — state for stations, season and quality flag for levels, potability for chemistry, GEC category for assessment units — together with distributions and a station map. This page exists so that a reviewer can independently reproduce or challenge any claim the copilot makes.")
figure(os.path.join(SHOTS, "user_04_data_explorer.png"), "Figure 6.  Data explorer: monitoring-station catalog with a national map of indexed stations.")
H2("8.5  Performance and reliability")
P("The performance page reports operational service levels: SQL success rate, provenance precision, edge-case interception, benchmark pass rate and latency percentiles, together with reliability by question category and latency by query type. It also documents the failure modes the system is designed to survive — empty SQL results and missed coverage — and provides a button that re-runs the full 30-case audit against the live database and model.")
figure(os.path.join(SHOTS, "user_05_performance.png"), "Figure 7.  Performance and reliability panel: SLAs, reliability by category and latency distribution.")
H2("8.6  Safety guardrails")
P("Guardrails are presented as a first-class feature rather than an implementation detail: zero fabrication when records are missing, read-only SQL validation, automatic result caps, and human-in-the-loop escalation for conflicting observations.")
figure(os.path.join(SHOTS, "user_06_safety.png"), "Figure 8.  Safety guardrails: failure-mode distribution and the automated protections the pipeline enforces.")
H2("8.7  NWIC live synchronizer")
P("The final module makes the data supply chain visible. It reports portal reachability, lists the states for which official resources are registered, and streams quarterly telemetry and laboratory chemistry into DuckDB with a configurable per-state record cap. Ingestion is idempotent, so a user can re-synchronize without creating duplicates.")
figure(os.path.join(SHOTS, "user_07_nwic_sync.png"), "Figure 9.  NWIC live synchronizer: portal status, state selection, and 2,842 ingested CGWB stations with a geographic preview.")

# ═══════════════════════════════════════════════════════════════════════════
H1("Evaluation and performance", "9")
P("Evaluation is reproducible from a single command. The runner executes 30 documented questions — 12 normal, 8 edge, 6 incomplete and 4 ambiguous — against the same database and model configuration, and scores intent accuracy, SQL success, coverage detection, provenance and end-to-end latency.")
H2("9.1  Overall results")
table(
    ["Metric", "Result"],
    [
        ["Total test cases", "30"],
        ["Intent accuracy", "66.7%"],
        ["SQL success rate", "83.3%"],
        ["Coverage detection recall", "63.3%"],
        ["Provenance precision", "100.0%"],
        ["Overall pass rate", "83.3%"],
        ["Mean latency", "32 ms"],
        ["P95 latency", "38 ms"],
    ],
    [3.5, 2.0],
)
H2("9.2  Results by category")
table(
    ["Category", "Cases", "Passed", "Pass rate"],
    [
        ["Normal queries", "12", "8", "66.7%"],
        ["Edge conditions", "8", "8", "100.0%"],
        ["Incomplete records", "6", "5", "83.3%"],
        ["Ambiguous locations", "4", "4", "100.0%"],
    ],
    [2.6, 1.0, 1.0, 1.4],
)
P("The pattern is informative. Edge conditions and ambiguous locations pass completely: the coverage detector is reliable at refusing to answer when a question is out of range or under-specified. Normal structured queries are the weaker category, largely because some question shapes still fall outside the reviewed templates and the heuristic router can misread a location token. Incomplete-record cases pass when the system returns partial evidence with an explicit gap note.")
H2("9.3  Failure modes")
P("Two failure patterns account for every miss in the suite. Five cases returned no SQL rows, typically because a combination of district, season and year is not seeded; the mitigation is a fallback to the nearest available station or a regional aggregate, together with a clearer coverage message. Three cases were coverage misses, where a thin or ambiguous request was not flagged; the mitigation is threshold tuning and fuzzy alias matching in the geography resolver. Provenance precision remained at 100% throughout: no evaluated answer stated a fact without either a citation or an explicit statement that the data was unavailable.")
H2("9.4  Unit tests")
P("Twenty-five unit tests pass across schema validation, SQL safety, coverage rules, response-state logic and the NWIC loader. They cover the invariants that must never regress: disallowed SQL keywords are rejected, LIMIT is injected, coordinates outside India are refused, derived potability matches BIS thresholds, and response states follow the defined precedence.")

# ═══════════════════════════════════════════════════════════════════════════
H1("Safety, governance and limitations", "10")
H2("10.1  Guardrails")
for lead, text in [
    ("Read-only execution. ", "DROP, DELETE, UPDATE, INSERT, ALTER, TRUNCATE, CREATE, REPLACE and MERGE are rejected before execution; a statement must be a SELECT."),
    ("Bounded results. ", "LIMIT 500 is injected when a query does not specify one, protecting memory and response time."),
    ("Coverage refusal. ", "When data is missing, the system returns INSUFFICIENT or OUT_OF_SCOPE with an explanation instead of filling the gap."),
    ("Standards-based interpretation. ", "BIS 10500:2012 thresholds and GEC-2015 categories are applied mechanically, not judged by the model."),
    ("Human escalation. ", "Conflicting observations across wells produce a HUMAN_REVIEW state with a one-click flag for expert review."),
]:
    bullet(text, lead)
H2("10.2  Limitations and mitigations")
table(
    ["Limitation", "Impact", "Mitigation / current status"],
    [
        ["Offline synthesizer produces generic narrative", "Without a provider key, answers are less specific", "Evidence and SQL remain authoritative; configure a provider for full prose"],
        ["Semantic stack is optional", "ChromaDB and MiniLM are absent here", "TF-IDF fallback keeps conceptual search working"],
        ["Heuristic router", "Some tokens (for example 'districts' containing 'ts') can confuse location extraction", "Keyword list and precedence to be tightened; provider routing is more accurate"],
        ["Portal availability", "NWIC downloads can be intermittent", "Cached data remains queryable; status is shown in the UI"],
        ["Mixed DuckDB access modes", "Opening a read-only dashboard connection while a read-write pipeline connection is active can conflict", "Restart the server or keep one access mode per process"],
        ["Coverage window vs data years", "Records extend to 2025 while the detector caps at 2023", "Documented policy is conservative; widen deliberately after review"],
    ],
    [1.85, 2.1, 2.55],
    font=8.5,
)
H2("10.3  Data governance")
P("The platform distinguishes live NWIC records (data_source = CGWB-NWIC-Live) from seeded reference records (CGWB-NWIC), so provenance is never ambiguous. Quality flags are preserved from the source and surfaced in every evidence table. Derived fields — potability and GEC category — are computed deterministically and can be recomputed from raw columns at any time.")

# ═══════════════════════════════════════════════════════════════════════════
H1("Deployment and operation", "11")
H2("11.1  Local run")
code_block("""cd c:\\Users\\shela\\Downloads\\csep
pip install -r requirements.txt
python ingest_all_target_states.py        # optional: refresh live NWIC data
streamlit run app/main.py                 # open http://localhost:8501""")
H2("11.2  Configuration")
P("Copy .env.example to .env and set the provider. The application starts without any key; adding one upgrades the narrative quality without changing retrieval or provenance.")
code_block("""LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=sk-or-v1-...
LLM_MODEL=meta-llama/llama-3.3-70b-instruct
LLM_BASE_URL=https://openrouter.ai/api/v1""")
H2("11.3  Deployment options")
table(
    ["Target", "Approach", "Notes"],
    [
        ["Streamlit Community Cloud", "Push to GitHub; main file app/main.py; add secrets", "Simplest public demo"],
        ["Docker", "python:3.11-slim image; seed database; expose 8501", "Reproducible runtime, health endpoint"],
        ["Cloud VM", "systemd service behind nginx", "Persistent 24/7 operation"],
    ],
    [1.8, 2.7, 2.1],
)
H2("11.4  Verification commands")
code_block("""pytest tests -v            # 25 unit tests
python run_evaluation.py   # 30-case benchmark; writes docs/evaluation_report.md""")

# ═══════════════════════════════════════════════════════════════════════════
H1("Conclusion", "12")
P("INGRES demonstrates a defensible pattern for scientific AI: treat the database as the source of truth, make retrieval deterministic where possible, check coverage before generation, and make every claim auditable. The result is a system that answers groundwater questions with station-level evidence, states plainly when it cannot answer, and remains usable with no external model at all.")
P("The measured record — 100% provenance precision and 83.3% pass rate over 30 documented cases — is a starting point rather than a finish line. The highest-value next steps are tightening the heuristic router, expanding reviewed SQL templates to cover the remaining normal-query shapes, widening the live ingestion to more states, and adding a formal review workflow for flagged cases. None of those changes requires re-architecting the pipeline; each improves an already observable, already auditable system.")

# ═══════════════════════════════════════════════════════════════════════════
H1("Repository map", "A")
P("The project is organized around a core Python package, a Streamlit interface and a reproducible evaluation harness.")
code_block("""csep/
├── app/                       Streamlit application
│   ├── main.py                Executive dashboard
│   ├── components/            Provider settings, provenance card, badges, chat
│   └── pages/                 01 Copilot · 02 Dossier · 03 Explorer
│                              04 Performance · 05 NWIC Sync
├── ingres/                    Core intelligence package
│   ├── data/nwic_loader.py    Official NWIC download and normalization
│   ├── schema/                DuckDB DDL and Pydantic models
│   ├── retrieval/             Router, Text-to-SQL, coverage, vector search, geo
│   ├── generation/            LLM client, context assembly, response generator
│   └── evaluation/            Baseline and metrics
├── tests/                     25 unit tests + 30-case fixture
├── data/synthetic/ingres.duckdb
├── docs/                      Assumptions, schema, evaluation report
├── ingest_all_target_states.py
├── run_evaluation.py
└── requirements.txt""")

H1("Command reference", "B")
table(
    ["Command", "Purpose"],
    [
        ["streamlit run app/main.py", "Start the platform on port 8501"],
        ["python ingest_all_target_states.py", "Synchronize eight states from NWIC"],
        ["pytest tests -v", "Run the unit test suite"],
        ["python run_evaluation.py", "Run the 30-case benchmark and rewrite the report"],
        ["python data/synthetic/generate_synthetic.py", "Regenerate the seeded baseline dataset"],
    ],
    [2.9, 3.6],
)

H1("References", "C")
for ref in [
    "Central Ground Water Board (CGWB), Ministry of Jal Shakti — groundwater monitoring and resource assessment.",
    "National Water Data Portal, NWIC — nwdp.nwic.gov.in, quarterly water level and chemical quality datasets.",
    "Ground Water Resource Estimation Committee (GEC-2015) — methodology for dynamic groundwater resource assessment.",
    "Bureau of Indian Standards, IS 10500:2012 — drinking water specification.",
    "Smart India Hackathon 2026 — Problem Code SIH26063.",
]:
    bullet(ref)

doc.save(OUT)
print("saved", os.path.abspath(OUT))