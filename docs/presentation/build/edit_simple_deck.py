
import os, shutil
from PIL import Image
from pptx import Presentation
from pptx.util import Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE_TYPE

BASE = r"C:\Users\shela\Downloads\csep\docs\presentation"
DECK = os.path.join(BASE, "INGRES_Simple_Presentation.pptx")
BACKUP = os.path.join(BASE, "INGRES_Simple_Presentation_streamlit_backup.pptx")
SHOTS = os.path.join(BASE, "build", "deck_simple_console")
TMP = os.path.join(SHOTS, "final")
os.makedirs(TMP, exist_ok=True)

if not os.path.exists(BACKUP):
    shutil.copy2(DECK, BACKUP)

prs = Presentation(DECK)

# slide index (1-based), source image, crop box (left, top, right, bottom)
JOBS = [
    (4,  "dashboard.png",   (0, 0, 1600, 865)),
    (5,  "copilot.png",     (0, 0, 1600, 1008)),
    (6,  "stations.png",    (0, 0, 1600, 915)),
    (7,  "explore.png",     (0, 0, 1600, 912)),
    (8,  "performance.png", (0, 0, 1600, 867)),
    (9,  "guardrails.png",  (0, 90, 1600, 910)),
    (10, "map.png",         (0, 170, 1280, 883)),
    (12, "settings.png",    (0, 90, 1600, 911)),
]

for slide_no, name, box in JOBS:
    slide = prs.slides[slide_no - 1]
    pics = [sh for sh in slide.shapes if sh.shape_type == MSO_SHAPE_TYPE.PICTURE]
    if not pics:
        print("WARN no picture on slide", slide_no)
        continue
    old = pics[0]
    frame = (old.left, old.top, old.width, old.height)

    src = Image.open(os.path.join(SHOTS, name)).convert("RGB")
    crop = src.crop(box)
    aspect = frame[2] / frame[3]
    w, h = crop.size
    if abs((w / h) - aspect) > 0.01:
        # fit crop to the frame aspect by trimming the longer side
        if w / h > aspect:
            nw = int(h * aspect)
            left = (w - nw) // 2
            crop = crop.crop((left, 0, left + nw, h))
        else:
            nh = int(w / aspect)
            top = (h - nh) // 2
            crop = crop.crop((0, top, w, top + nh))
    out = os.path.join(TMP, "s%02d.png" % slide_no)
    crop.save(out)

    sp = old._element
    sp.getparent().remove(sp)
    pic = slide.shapes.add_picture(out, frame[0], frame[1], frame[2], frame[3])
    pic.line.color.rgb = RGBColor(0x30, 0x36, 0x3D)
    pic.line.width = Pt(0.75)
    pic.shadow.inherit = False
    print("slide", slide_no, "->", name, crop.size)


def replace_text(slide, old, new, size=None):
    done = False
    for sh in slide.shapes:
        if not sh.has_text_frame:
            continue
        for p in sh.text_frame.paragraphs:
            for r in p.runs:
                if r.text == old:
                    r.text = new
                    if size:
                        r.font.size = Pt(size)
                    done = True
    return done


# Slide 11 — commands run the console
s11 = prs.slides[10]
for old, new, size in [
    ("streamlit run app/main.py", "python -m uvicorn frontend.api.server:app --port 8600", 9.5),
    ("# open http://localhost:8501", "# open http://127.0.0.1:8600", None),
]:
    print("slide11", old, "->", replace_text(s11, old, new, size))

# Slide 12 — settings wording
s12 = prs.slides[11]
print("slide12 title", replace_text(s12, "Pick your model in the sidebar.", "Pick your model in settings."))
print("slide12 caption", replace_text(s12, "The highlighted panel is the whole configuration surface.", "The settings panel is the whole configuration surface."))

# Slide 10 — repurpose live-sync slide to the interactive map
s10 = prs.slides[9]
print("slide10 tag", replace_text(s10, "09 · OFFICIAL LIVE SYNC", "09 · INTERACTIVE MAP"))
print("slide10 title", replace_text(s10, "Official data, one click.", "Every station, on the map."))

bullet_shape = None
for sh in s10.shapes:
    if sh.has_text_frame and sh.text_frame.text.strip().startswith("▸"):
        bullet_shape = sh
        break
if bullet_shape:
    tf = bullet_shape.text_frame
    size = None
    color = RGBColor(0xE6, 0xED, 0xF3)
    marker = RGBColor(0x2D, 0xD4, 0xBF)
    for p in tf.paragraphs:
        for r in p.runs:
            if r.text.strip() == "▸":
                marker = r.font.color.rgb if r.font.color and r.font.color.rgb else marker
            elif r.text.strip() and size is None:
                size = r.font.size.pt if r.font.size else 12
                color = r.font.color.rgb if r.font.color and r.font.color.rgb else color
    items = [
        "35 state boundaries · 3,042 stations plotted",
        "Green potable · red non-potable · grey no sample",
        "Pick a state: it highlights and zooms to fit",
        "Click a dot for its profile, then open the dossier",
    ]
    tf.clear()
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.space_after = Pt(8)
        p.line_spacing = 1.14
        r0 = p.add_run(); r0.text = "▸  "
        r0.font.size = Pt(size or 12); r0.font.bold = True; r0.font.color.rgb = marker
        r = p.add_run(); r.text = item
        r.font.size = Pt(size or 12); r.font.color.rgb = color
    print("slide10 bullets rebuilt at", size)

prs.save(DECK)
print("saved", DECK, "slides", len(prs.slides))
