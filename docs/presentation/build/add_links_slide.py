"""Append a 'Project Links' slide to the Canva deck."""

from pathlib import Path

from lxml import etree

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.opc.constants import RELATIONSHIP_TYPE as RT
from pptx.util import Inches, Pt

DECK = Path("docs/presentation/INGRES_Project_Deck_Canva.pptx")

BG = RGBColor.from_string("090B12")
INK = RGBColor.from_string("F5F7FB")
MUTED = RGBColor.from_string("8F9BAD")
SUBTLE = RGBColor.from_string("6F7C90")
ACCENT = RGBColor.from_string("7FE2E0")
LINE = RGBColor.from_string("242A3A")

MONO = "IBM Plex Mono Medium"
SANS = "IBM Plex Sans"
DISPLAY = "Akzidenz-Grotesk Bold"

prs = Presentation(str(DECK))

# Re-running the script replaces the slide instead of stacking duplicates.
for existing in list(prs.slides)[1:]:
    texts = [
        run.text.strip()
        for shape in existing.shapes
        if shape.has_text_frame
        for para in shape.text_frame.paragraphs
        for run in para.runs
    ]
    if "Project Links" in texts:
        sld_ids = prs.slides._sldIdLst
        for sld_id in list(sld_ids):
            if int(sld_id.get("id")) == int(existing.slide_id):
                prs.part.drop_rel(sld_id.rId)
                sld_ids.remove(sld_id)
                break

slide = prs.slides.add_slide(prs.slides[11].slide_layout)

fill = slide.background.fill
fill.solid()
fill.fore_color.rgb = BG

W = prs.slide_width / 914400
MARGIN = 1.17


def textbox(x, y, w, h, runs, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    for i, spec in enumerate(runs):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = spec.get("align", PP_ALIGN.LEFT)
        p.line_spacing = spec.get("line", 1.1)
        if "space_before" in spec:
            p.space_before = Pt(spec["space_before"])
        for r in spec["runs"]:
            run = p.add_run()
            run.text = r["t"]
            f = run.font
            f.name = r.get("font", SANS)
            f.size = Pt(r.get("size", 20))
            f.bold = r.get("bold", False)
            f.color.rgb = r.get("color", INK)
            if r.get("spc"):
                run.font._rPr.set("spc", str(r["spc"]))
            if r.get("link"):
                run.hyperlink.address = r["link"]
    return box


def hairline(y):
    shape = slide.shapes.add_shape(
        MSO_SHAPE.RECTANGLE, Inches(MARGIN), Inches(y), Inches(W - 2 * MARGIN), Inches(0.012)
    )
    shape.fill.solid()
    shape.fill.fore_color.rgb = LINE
    shape.line.fill.background()
    shape.shadow.inherit = False


textbox(MARGIN, 0.72, 10, 0.3, [{
    "runs": [{"t": "PROJECT LINKS", "font": MONO, "size": 13.5, "bold": True,
              "color": ACCENT, "spc": 210}],
}])

textbox(MARGIN, 1.08, 17.6, 1.25, [{
    "runs": [{"t": "Project Links", "font": DISPLAY, "size": 72, "bold": True, "color": INK}],
}])

textbox(MARGIN, 2.42, 16.5, 0.5, [{
    "runs": [{"t": "Every link is live and needs no login.", "font": SANS, "size": 21,
              "color": MUTED}],
}])

rows = [
    ("REPOSITORY", "github.com/ShelasAL/ingres-console",
     "https://github.com/ShelasAL/ingres-console",
     "Source code, tests and documentation"),
    ("LIVE CONSOLE", "ingres-console.vercel.app",
     "https://ingres-console.vercel.app",
     "Ask questions from any browser"),
    ("DATASET", "github.com/ShelasAL/ingres-console/blob/master/data/synthetic/ingres.duckdb",
     "https://github.com/ShelasAL/ingres-console/blob/master/data/synthetic/ingres.duckdb",
     "DuckDB file used by this build, 9 MB"),
    ("DATA SOURCE", "nwdp.nwic.gov.in",
     "https://nwdp.nwic.gov.in",
     "CGWB / NWIC National Water Data Portal"),
    ("DOCUMENTATION", "github.com/ShelasAL/ingres-console/blob/master/docs/FRAMEWORK.md",
     "https://github.com/ShelasAL/ingres-console/blob/master/docs/FRAMEWORK.md",
     "How the system is built, file by file"),
]

top = 3.42
step = 1.26
for i, (label, shown, url, note) in enumerate(rows):
    y = top + i * step
    hairline(y)
    textbox(MARGIN, y + 0.18, 3.2, 0.28, [{
        "runs": [{"t": label, "font": MONO, "size": 12, "bold": True,
                  "color": MUTED, "spc": 150}],
    }])
    textbox(4.65, y + 0.1, W - 4.65 - MARGIN, 0.62, [
        {"runs": [{"t": shown, "font": SANS, "size": 20, "color": ACCENT, "link": url}]},
        {"runs": [{"t": note, "font": SANS, "size": 13, "color": SUBTLE}], "space_before": 4},
    ])

textbox(MARGIN, 9.86, 16.4, 0.35, [{
    "runs": [{"t": "Dataset is a synthetic sample modelled on the CGWB / NWIC record.",
              "font": SANS, "size": 13, "color": SUBTLE}],
}])

textbox(MARGIN, 10.52, 12, 0.25, [{
    "runs": [{"t": "INGRES  /  NATIONAL GROUNDWATER INTELLIGENCE", "font": MONO,
              "size": 12, "color": SUBTLE, "spc": 160}],
}])

# Hyperlinks inherit the theme's blue. Recolour the theme's link entries to the
# console accent so they sit inside the palette.
theme_part = prs.slide_masters[0].part.part_related_by(RT.THEME)
xml = theme_part.blob if hasattr(theme_part, "blob") else None
if xml:
    root = etree.fromstring(xml)
    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}
    changed = False
    for tag in ("hlink", "folHlink"):
        node = root.find(f".//a:clrScheme/a:{tag}/a:srgbClr", ns)
        if node is not None:
            node.set("val", "7FE2E0")
            changed = True
    if changed:
        theme_part._blob = etree.tostring(root, xml_declaration=True,
                                          encoding="UTF-8", standalone=True)

prs.save(str(DECK))
print("slides:", len(prs.slides))
