"""Build the 7-slide INGRES demo deck.

Run with the Python that has python-pptx installed:
  %LOCALAPPDATA%\\Programs\\Python\\Python312\\python.exe build_demo_deck.py
"""

import os
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parents[3]
SHOTS = ROOT / "docs" / "presentation" / "screenshots" / "deck_new"
OUT = ROOT / "docs" / "presentation" / "INGRES_Demo_Deck.pptx"

W, H = 13.333, 7.5
ML, MR = 0.92, 0.92
CW = W - ML - MR

# Palette taken from the console theme.
BG = "090B12"
CARD = "12151F"
CARD_2 = "161A26"
LINE = "242A3A"
LINE_SOFT = "1B2130"
INK = "EEF2F8"
MUTED = "A6B2C6"
SUBTLE = "76839A"
ACCENT = "7FE2E0"
ACCENT_DIM = "4FB9BE"
BLUE = "7FA6FF"
WARN = "E5B455"
DANGER = "F07B72"
SUCCESS = "4FD19A"

FONT = "Segoe UI"
MONO = "Cascadia Code"


def rgb(hex_str):
    return RGBColor.from_string(hex_str)


def blank(prs):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = rgb(BG)
    return slide


def no_shadow(shape):
    try:
        shape.shadow.inherit = False
    except Exception:
        pass


def rect(slide, x, y, w, h, fill=CARD, line=None, line_w=0.75, radius=None):
    kind = MSO_SHAPE.ROUNDED_RECTANGLE if radius is not None else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(kind, Inches(x), Inches(y), Inches(w), Inches(h))
    if radius is not None:
        shape.adjustments[0] = radius
    if fill:
        shape.fill.solid()
        shape.fill.fore_color.rgb = rgb(fill)
    else:
        shape.fill.background()
    if line:
        shape.line.color.rgb = rgb(line)
        shape.line.width = Pt(line_w)
    else:
        shape.line.fill.background()
    no_shadow(shape)
    return shape


def text(slide, x, y, w, h, paras, anchor=MSO_ANCHOR.TOP):
    box = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = 0
    tf.margin_right = 0
    tf.margin_top = 0
    tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    for i, para_spec in enumerate(paras):
        para = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        para.alignment = para_spec.get("align", PP_ALIGN.LEFT)
        if "space_before" in para_spec:
            para.space_before = Pt(para_spec["space_before"])
        if "space_after" in para_spec:
            para.space_after = Pt(para_spec["space_after"])
        para.line_spacing = para_spec.get("line", 1.14)
        runs = para_spec.get("runs")
        if runs is None:
            runs = [{
                "t": para_spec.get("t", ""),
                "size": para_spec.get("size", 14),
                "color": para_spec.get("color", INK),
                "bold": para_spec.get("bold", False),
                "italic": para_spec.get("italic", False),
                "font": para_spec.get("font", FONT),
                "spc": para_spec.get("spc"),
            }]
        for run_spec in runs:
            run = para.add_run()
            run.text = run_spec.get("t", "")
            f = run.font
            f.size = Pt(run_spec.get("size", 14))
            f.bold = run_spec.get("bold", False)
            f.italic = run_spec.get("italic", False)
            f.name = run_spec.get("font", FONT)
            f.color.rgb = rgb(run_spec.get("color", INK))
            if run_spec.get("spc"):
                run.font._rPr.set("spc", str(run_spec["spc"]))
    return box


def eyebrow(slide, label, y=0.58):
    text(slide, ML, y, CW, 0.25, [{
        "t": label.upper(), "size": 10, "color": ACCENT_DIM, "bold": True, "spc": 220,
    }])


def headline(slide, title, y=0.92, size=31, w=CW, color=INK):
    text(slide, ML, y, w, 1.15, [{
        "t": title, "size": size, "color": color, "bold": True, "line": 1.03,
    }])


def subhead(slide, message, y=1.86, w=9.9):
    text(slide, ML, y, w, 0.5, [{
        "t": message, "size": 13.5, "color": MUTED, "line": 1.28,
    }])


def footer(slide, page, total=7):
    text(slide, ML, 6.92, 8.0, 0.22, [{
        "t": "INGRES  ·  National Groundwater Intelligence Platform",
        "size": 8.5, "color": SUBTLE, "spc": 40,
    }])
    text(slide, W - MR - 1.2, 6.92, 1.2, 0.22, [{
        "t": f"{page:02d} / {total:02d}", "size": 8.5, "color": SUBTLE, "align": PP_ALIGN.RIGHT,
    }])


def notes(slide, message):
    slide.notes_slide.notes_text_frame.text = message


def accent_bar(slide, x, y, w=1.1, color=ACCENT, h=0.045):
    rect(slide, x, y, w, h, fill=color)


def stat(slide, x, y, w, value, label, note=None):
    paras = [{"t": value, "size": 27, "color": INK, "bold": True, "line": 1.0}]
    paras.append({"t": label.upper(), "size": 8.5, "color": SUBTLE, "spc": 140, "space_before": 6})
    if note:
        paras.append({"t": note, "size": 9, "color": SUBTLE, "space_before": 2})
    text(slide, x, y, w, 1.0, paras)


def build():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)

    # ---------------------------------------------------------------- slide 1
    s = blank(prs)
    rect(s, 0, 0, W, 0.06, fill=ACCENT)
    rect(s, 0, 0.06, W * 0.42, 0.06, fill=BLUE)

    # Faint contour rings, echoing a water-table map.
    for radius in (1.35, 1.95, 2.55):
        ring = s.shapes.add_shape(
            MSO_SHAPE.OVAL,
            Inches(12.05 - radius), Inches(2.55 - radius),
            Inches(radius * 2), Inches(radius * 2),
        )
        ring.fill.background()
        ring.line.color.rgb = rgb("18202E")
        ring.line.width = Pt(1)
        no_shadow(ring)

    text(s, ML, 0.82, 8.0, 0.25, [{
        "t": "SIH 2026  ·  PROBLEM CODE SIH26063  ·  CGWB / NWIC",
        "size": 9.5, "color": SUBTLE, "spc": 180,
    }])

    text(s, ML, 1.28, 10.0, 2.5, [
        {"t": "INGRES", "size": 66, "color": INK, "bold": True, "line": 0.92},
        {"t": "Groundwater answers you can check.", "size": 30, "color": ACCENT,
         "bold": False, "space_before": 10},
    ])

    text(s, ML, 3.62, 8.35, 1.1, [{
        "t": "Ask a plain-English question about India's groundwater. The answer is "
             "assembled from the official record — with the station, the date and the "
             "standard behind every number.",
        "size": 14.5, "color": MUTED, "line": 1.4,
    }])

    rect(s, ML, 4.95, CW, 0.012, fill=LINE)
    stat(s, ML, 5.22, 2.7, "3,042", "monitoring stations", "12 states · 257 districts")
    stat(s, ML + 2.9, 5.22, 2.7, "16,780", "water-level readings", "2015 – 2025")
    stat(s, ML + 5.8, 5.22, 2.7, "11,978", "laboratory samples", "BIS 10500 parameters")
    stat(s, ML + 8.7, 5.22, 2.7, "100", "GEC assessment units", "2020 and 2022")

    notes(s, "INGRES reads the CGWB and NWIC record and answers questions about it. "
             "The one promise: no number appears in an answer unless the database returned it.")

    # ---------------------------------------------------------------- slide 2
    s = blank(prs)
    eyebrow(s, "01 · The problem")
    headline(s, "The data exists. The answer doesn't.")
    subhead(s, "India runs on groundwater, but its record is scattered across portals, "
               "spreadsheets and laboratory sheets.")

    cards = [
        ("01", "Data is scattered",
         "Millions of readings in different formats, spread across CGWB and NWIC portals."),
        ("02", "AI invents numbers",
         "A general chatbot will happily produce a well, a value or a trend that never existed."),
        ("03", "No receipts",
         "Even a correct answer rarely says which station, which date, or which limit it used."),
    ]
    top = 2.5
    for i, (num, title, body) in enumerate(cards):
        x = ML + i * 3.9
        rect(s, x, top, 3.62, 2.02, fill=CARD, line=LINE, radius=0.05)
        text(s, x + 0.34, top + 0.28, 2.9, 0.25, [{
            "t": num, "size": 10, "color": ACCENT_DIM, "font": MONO, "spc": 120,
        }])
        text(s, x + 0.34, top + 0.62, 2.95, 0.45, [{
            "t": title, "size": 16.5, "color": INK, "bold": True, "line": 1.05,
        }])
        text(s, x + 0.34, top + 1.08, 2.95, 0.8, [{
            "t": body, "size": 11.5, "color": MUTED, "line": 1.34,
        }])

    rect(s, ML, 5.02, 0.035, 0.46, fill=ACCENT)
    text(s, ML + 0.28, 5.02, 10.6, 0.5, [{
        "t": "In water security, a confident wrong number is worse than no answer.",
        "size": 19, "color": INK, "line": 1.2,
    }])
    text(s, ML + 0.28, 5.62, 10.4, 0.5, [{
        "t": "Groundwater supplies over 60% of India's irrigated farming and about 85% of "
             "rural drinking water. The evidence for both is in this record.",
        "size": 11.5, "color": SUBTLE, "line": 1.3,
    }])

    footer(s, 2)
    notes(s, "Three reasons the answer is hard to trust: the data is scattered, general AI "
             "invents numbers, and answers arrive without receipts. The third one is the "
             "reason the first two are dangerous.")

    # ---------------------------------------------------------------- slide 3
    s = blank(prs)
    eyebrow(s, "02 · What it is")
    headline(s, "One screen: ask in plain English,\nget an answer you can check.", size=29)
    text_y = 2.34
    points = [
        ("Ask normally", "Type the question — no SQL, no filters, no forms."),
        ("Database first", "The database answers; the model only explains what it returned."),
        ("Receipts attached", "Coverage, confidence, the executed SQL and the station sources."),
        ("Honest refusals", "If the data cannot support an answer, INGRES says why."),
    ]
    for i, (title, body) in enumerate(points):
        y = text_y + i * 0.94
        rect(s, ML, y + 0.08, 0.035, 0.56, fill=ACCENT if i % 2 == 0 else BLUE)
        text(s, ML + 0.26, y, 3.7, 0.3, [{
            "t": title, "size": 13, "color": INK, "bold": True,
        }])
        text(s, ML + 0.26, y + 0.28, 3.8, 0.6, [{
            "t": body, "size": 10.5, "color": MUTED, "line": 1.28,
        }])

    shot_w = 7.15
    shot_h = shot_w * 491 / 1028
    shot_x, shot_y = 5.22, 2.2
    rect(s, shot_x - 0.06, shot_y - 0.06, shot_w + 0.12, shot_h + 0.12, fill="11141D", line=LINE)
    s.shapes.add_picture(str(SHOTS / "copilot_answer.png"), Inches(shot_x), Inches(shot_y),
                         width=Inches(shot_w), height=Inches(shot_h))
    text(s, shot_x, shot_y + shot_h + 0.18, shot_w, 0.3, [{
        "t": "A live answer: model summary, BIS exceedances, coverage note, timing and sources.",
        "size": 9.5, "color": SUBTLE,
    }])
    text(s, ML, 6.02, 4.0, 0.6, [{
        "t": "Read-only by design: the system can query the record, never change it.",
        "size": 10.5, "color": SUBTLE, "line": 1.3,
    }])

    footer(s, 3)
    notes(s, "This is the whole product: one question box. The answer arrives with badges, a "
             "plain-language summary, a coverage note and the station IDs it came from.")

    # ---------------------------------------------------------------- slide 4
    s = blank(prs)
    eyebrow(s, "03 · How it works")
    headline(s, "Five steps. The model writes only the last one.")
    subhead(s, "Retrieval first, generation second — the order is what makes the answer trustworthy.")

    steps = [
        ("01", "Understand", "The question becomes an intent and a place."),
        ("02", "Retrieve", "A reviewed, read-only SQL query reads the database."),
        ("03", "Check", "Coverage: is there data for that place and period?"),
        ("04", "Explain", "The model writes the answer from the returned rows."),
        ("05", "Show", "Summary, evidence, SQL, sources, confidence."),
    ]
    top = 2.55
    for i, (num, title, body) in enumerate(steps):
        x = ML + i * 2.33
        rect(s, x, top, 2.13, 2.1, fill=CARD if i < 4 else CARD_2,
             line=LINE if i < 4 else ACCENT_DIM, radius=0.06)
        text(s, x + 0.26, top + 0.26, 1.6, 0.25, [{
            "t": num, "size": 10, "color": ACCENT_DIM, "font": MONO,
        }])
        text(s, x + 0.26, top + 0.56, 1.7, 0.3, [{
            "t": title, "size": 14.5, "color": INK, "bold": True,
        }])
        text(s, x + 0.26, top + 0.96, 1.68, 1.0, [{
            "t": body, "size": 10.5, "color": MUTED, "line": 1.34,
        }])

    rect(s, ML, 5.05, CW, 0.9, fill="10131C", line=LINE_SOFT, radius=0.1)
    text(s, ML + 0.36, 5.26, CW - 0.72, 0.5, [{
        "runs": [
            {"t": "No number is generated. ", "size": 14, "color": INK, "bold": True},
            {"t": "Every value in an answer is copied from rows the database returned, "
                  "and a fabricated station ID falls back to the plain record.",
             "size": 14, "color": MUTED},
        ],
        "line": 1.2,
    }])

    footer(s, 4)
    notes(s, "Step three is the one generic chatbots skip: coverage is checked before the model "
             "is allowed to answer. Step four explains rows; it never supplies values.")

    # ---------------------------------------------------------------- slide 5
    s = blank(prs)
    eyebrow(s, "04 · Technology and why")
    headline(s, "Small, boring technology — chosen on purpose.")
    subhead(s, "Every choice trades scale for something a water agency needs more: "
               "auditability, speed and the freedom to work offline.", w=10.6)

    tech = [
        ("DuckDB", "One database file, no server. Analytical SQL over 31,800 records "
                   "in milliseconds — the whole platform ships as a repo plus a file."),
        ("Starlette + Uvicorn", "A small Python API that serves the interface and the "
                                "answers, with no extra packages to install."),
        ("Plain ES-module UI", "No build step and no framework, so the console loads fast "
                               "and anyone can read the code behind it."),
        ("Any model — or none", "OpenRouter, Gemini, OpenAI or a custom endpoint. Without a "
                                "key, the deterministic answer still works."),
    ]
    for i, (title, body) in enumerate(tech):
        col, row = i % 2, i // 2
        x = ML + col * (5.62 + 0.19)
        y = 2.4 + row * 1.62
        rect(s, x, y, 5.62, 1.46, fill=CARD, line=LINE, radius=0.07)
        rect(s, x, y, 0.035, 1.46, fill=ACCENT if i % 3 == 0 else BLUE)
        text(s, x + 0.3, y + 0.22, 2.1, 0.3, [{
            "t": title, "size": 13.5, "color": INK, "bold": True,
        }])
        text(s, x + 0.3, y + 0.6, 4.98, 0.7, [{
            "t": body, "size": 10.5, "color": MUTED, "line": 1.3,
        }])

    rect(s, ML, 5.66, CW, 1.02, fill="10131C", line=LINE_SOFT, radius=0.08)
    text(s, ML + 0.4, 5.86, CW - 0.8, 0.68, [{
        "runs": [
            {"t": "Standards fixed in code. ", "size": 13, "color": INK, "bold": True},
            {"t": "BIS 10500:2012 limits, GEC-2015 categories and potability are derived "
                  "by rule — so the same threshold applies to every row, in every answer.",
             "size": 13, "color": MUTED},
        ],
        "line": 1.35,
    }])

    footer(s, 5)
    notes(s, "Nothing here is fashionable. DuckDB keeps the deployment to one file, the API uses "
             "two standard packages, the UI has no build step, and the model is a swappable part.")

    # ---------------------------------------------------------------- slide 6
    s = blank(prs)
    eyebrow(s, "05 · What it solves")
    headline(s, "Real questions, answered from the record.")
    subhead(s, "The same engine handles quality, levels, potability, extraction, counts and "
               "single-station lookups.")

    examples = [
        ("Summarize groundwater quality in Bihar.",
         "Mean TDS 462.6 mg/L, fluoride 0.61, nitrate 43.98. 77 wells sit above the TDS "
         "limit; arsenic spikes in Patna and Bhagalpur.", ACCENT, False,
         "Quality · 500 samples"),
        ("Compare water levels in Jaipur and Pune.",
         "Jaipur averages 31.3 m below ground, Pune 7.8 m — Jaipur is 23.5 m deeper.",
         BLUE, False, "Levels · two districts"),
        ("What is the fluoride level in Paris?",
         "Not answerable. Paris is not in this database, which covers Indian states and "
         "districts only.", WARN, True, "Guardrail · out of scope"),
    ]
    for i, (question, answer, colour, refusal, tag) in enumerate(examples):
        x = ML + i * 3.9
        rect(s, x, 2.45, 3.62, 2.9, fill=CARD, line=LINE, radius=0.05)
        rect(s, x, 2.45, 3.62, 0.045, fill=colour)
        text(s, x + 0.3, 2.7, 3.02, 0.55, [{
            "t": question, "size": 10.5, "color": SUBTLE, "italic": True, "line": 1.3,
        }])
        if refusal:
            text(s, x + 0.3, 3.22, 3.02, 0.36, [{
                "t": "Refused, with a reason", "size": 16.5, "color": colour, "bold": True,
            }])
            text(s, x + 0.3, 3.62, 3.02, 1.2, [{
                "t": answer, "size": 11.5, "color": MUTED, "line": 1.4,
            }])
        else:
            text(s, x + 0.3, 3.22, 3.02, 1.55, [{
                "t": answer, "size": 11.5, "color": INK, "line": 1.42,
            }])
        rect(s, x + 0.3, 4.72, 3.02, 0.01, fill=LINE)
        text(s, x + 0.3, 4.84, 3.02, 0.25, [{
            "t": tag.upper(), "size": 8, "color": SUBTLE, "spc": 130,
        }])

    text(s, ML, 5.68, CW, 0.4, [{
        "runs": [
            {"t": "Refusal is a feature, not a failure: ", "size": 11, "color": INK, "bold": True},
            {"t": "a misspelled district or a foreign city is rejected instead of answered "
                  "with the wrong state's data.", "size": 11, "color": MUTED},
        ],
    }])

    footer(s, 6)
    notes(s, "Three live examples. The first shows a state summary, the second a comparison "
             "with a delta, the third shows the guardrail: Paris is refused, not guessed.")

    # ---------------------------------------------------------------- slide 7
    s = blank(prs)
    eyebrow(s, "06 · Where it stands")
    headline(s, "Built to be checked, not trusted blindly.")
    subhead(s, "A working system today — with limits we would rather state than hide.", w=9.5)

    columns = [
        ("Honest limits", SUBTLE, [
            "12 states and 257 districts indexed so far — not all of India.",
            "Quality sampling is uneven; some districts have very few lab results.",
            "A model key improves the prose, not the retrieval.",
        ]),
        ("What comes next", ACCENT, [
            "Wider NWIC ingestion, state by state, on a schedule.",
            "More reviewed query templates and side-by-side comparisons.",
            "An expert-review workflow for contested answers.",
        ]),
    ]
    for i, (title, colour, items) in enumerate(columns):
        x = ML + i * (5.62 + 0.19)
        rect(s, x, 2.45, 5.62, 2.5, fill=CARD, line=LINE, radius=0.05)
        text(s, x + 0.36, 2.7, 4.9, 0.3, [{
            "t": title.upper(), "size": 9.5, "color": colour, "bold": True, "spc": 160,
        }])
        paras = []
        for item in items:
            paras.append({
                "runs": [
                    {"t": "—  ", "size": 12.5, "color": colour},
                    {"t": item, "size": 12.5, "color": MUTED},
                ],
                "space_before": 12, "line": 1.3,
            })
        text(s, x + 0.36, 3.12, 4.9, 1.7, paras)

    rect(s, ML, 5.42, CW, 0.012, fill=LINE)
    text(s, ML, 5.62, CW, 0.55, [{
        "t": "Verified.  Cited.  Auditable.", "size": 26, "color": INK, "bold": True,
    }])
    text(s, ML, 6.2, CW, 0.4, [{
        "t": "Not a chatbot that sounds right — a system a hydrogeologist can defend.",
        "size": 12, "color": SUBTLE,
    }])

    footer(s, 7)
    notes(s, "Close on the limits: twelve states indexed, sampling is uneven, and the model is "
             "optional. The claim is not perfection; it is that every answer can be checked.")

    prs.core_properties.title = "INGRES — Groundwater answers you can check"
    prs.core_properties.subject = "National Groundwater Intelligence Platform · SIH 2026 · SIH26063"
    prs.core_properties.author = "INGRES team"
    prs.core_properties.keywords = "groundwater, CGWB, NWIC, BIS 10500, GEC-2015, DuckDB"

    prs.save(OUT)
    print("Wrote", OUT)
    print("Slides:", len(prs.slides.__iter__.__self__._sldIdLst))


if __name__ == "__main__":
    build()
