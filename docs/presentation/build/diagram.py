
"""Generate the INGRES architecture diagram (dark for slides, light for the report)."""
from PIL import Image, ImageDraw, ImageFont
import os, math

OUT = os.path.dirname(os.path.abspath(__file__))
FONT_DIR = r"C:\Windows\Fonts"

def font(size, bold=False):
    name = "segoeuib.ttf" if bold else "segoeui.ttf"
    try:
        return ImageFont.truetype(os.path.join(FONT_DIR, name), size)
    except Exception:
        return ImageFont.truetype(os.path.join(FONT_DIR, "arial.ttf"), size)

def build(theme, path):
    if theme == "dark":
        bg, panel, panel2, border = "#0E1117", "#161B22", "#1C2430", "#30363D"
        text, muted, accent, accent2, warn = "#E6EDF3", "#8B949E", "#2DD4BF", "#58A6FF", "#F59E0B"
    else:
        bg, panel, panel2, border = "#FFFFFF", "#F6F8FA", "#EEF2F6", "#D0D7DE"
        text, muted, accent, accent2, warn = "#1F2328", "#57606A", "#0D9488", "#0969DA", "#B45309"

    W, H = 1800, 900
    im = Image.new("RGB", (W, H), bg)
    d = ImageDraw.Draw(im)
    f_title = font(26, True)
    f_h = font(20, True)
    f_body = font(15)
    f_small = font(14)
    f_tiny = font(12)
    f_label = font(15, True)

    def box(x, y, w, h, fill, outline, r=12, width=2):
        d.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=fill, outline=outline, width=width)

    def lines_centered(lines, x, y, w, fnt, fill, gap=5):
        cy = y
        for ln in lines:
            if not ln:
                cy += 8
                continue
            tw = d.textlength(ln, font=fnt)
            d.text((x + (w - tw) / 2, cy), ln, font=fnt, fill=fill)
            cy += d.textbbox((0, 0), ln, font=fnt)[3] + gap
        return cy

    def arrow(x1, y1, x2, y2, color, width=3):
        d.line([x1, y1, x2, y2], fill=color, width=width)
        ang = math.atan2(y2 - y1, x2 - x1)
        L, spread = 13, 0.45
        p1 = (x2 - L * math.cos(ang - spread), y2 - L * math.sin(ang - spread))
        p2 = (x2 - L * math.cos(ang + spread), y2 - L * math.sin(ang + spread))
        d.polygon([(x2, y2), p1, p2], fill=color)

    d.text((60, 38), "INGRES — REQUEST PIPELINE", font=f_title, fill=text)
    d.text((60, 76), "From natural-language hydrology question to a cited, state-annotated answer",
           font=f_small, fill=muted)

    # 1 · UI band
    box(60, 126, W - 120, 110, panel, border)
    d.text((84, 142), "1 · STREAMLIT ENTERPRISE UI", font=f_label, fill=accent)
    pills = ["Dashboard", "AI Copilot", "Station Dossier", "Data Explorer", "Performance", "NWIC Sync"]
    px = 84
    for p in pills:
        tw = d.textlength(p, font=f_body) + 26
        box(px, 176, tw, 38, panel2, border, r=19, width=1)
        d.text((px + 13, 185), p, font=f_body, fill=text)
        px += tw + 12

    # 2..7 pipeline
    y, bh, bw, gap = 300, 205, 246, 20
    specs = [
        ("2 · QUERY\nROUTER", "Intent + entities\nLLM classifier\nkeyword fallback", accent2),
        ("3 · COVERAGE\nDETECTOR", "5 pre-answer rules\ntemporal · spatial\nparameter · density", warn),
        ("4 · HYBRID\nRETRIEVAL", "SQL templates +\nsafe Text-to-SQL\n+ vector KB", accent),
        ("5 · CONTEXT\nASSEMBLER", "Dataframe → markdown\nstatistics · BIS\nGEC counts", accent2),
        ("6 · RESPONSE\nGENERATOR", "Grounded prompt\n6 states · 6 levels\noffline fallback", accent),
        ("7 · RESPONSE", "Answer · evidence\nconfidence · coverage\nCSV · review flag", warn),
    ]
    positions = []
    for i, (title, body, col) in enumerate(specs):
        x = 60 + i * (bw + gap)
        positions.append((x, y, bw, bh))
        box(x, y, bw, bh, panel, border)
        d.rounded_rectangle([x + 2, y + 2, x + bw - 2, y + 9], radius=3, fill=col)
        cy = lines_centered(title.split("\n"), x + 14, y + 30, bw - 28, f_label, col, gap=2)
        lines_centered([ln for seg in body.split("\n") for ln in [seg]], x + 14, cy + 16, bw - 28, f_body, text, gap=6)

    for i in range(len(positions) - 1):
        x1 = positions[i][0] + positions[i][2]
        x2 = positions[i + 1][0]
        arrow(x1 + 2, y + bh // 2, x2 - 3, y + bh // 2, accent)

    # Data plane
    dy = 600
    box(60, dy, W - 120, 200, panel, border)
    d.text((84, dy + 16), "DATA PLANE", font=f_label, fill=accent)
    colx = [84, 660, 1220]
    d.text((colx[0], dy + 46), "DuckDB 2.0", font=f_h, fill=text)
    d.text((colx[0], dy + 76), "wells · gw_levels · gw_quality · assessment_units", font=f_small, fill=muted)
    d.text((colx[0], dy + 100), "3,042 stations · 16,780 levels", font=f_small, fill=muted)
    d.text((colx[0], dy + 124), "11,978 quality samples · 100 GEC units", font=f_small, fill=muted)
    d.line([(640, dy + 40), (640, dy + 186)], fill=border, width=2)
    d.text((colx[1], dy + 46), "Knowledge base", font=f_h, fill=text)
    d.text((colx[1], dy + 76), "10 curated hydrogeology chunks", font=f_small, fill=muted)
    d.text((colx[1], dy + 100), "ChromaDB + MiniLM embeddings", font=f_small, fill=muted)
    d.text((colx[1], dy + 124), "automatic TF-IDF fallback", font=f_small, fill=muted)
    d.line([(1200, dy + 40), (1200, dy + 186)], fill=border, width=2)
    d.text((colx[2], dy + 46), "NWIC / CGWB live sync", font=f_h, fill=text)
    d.text((colx[2], dy + 76), "nwdp.nwic.gov.in CKAN CSV", font=f_small, fill=muted)
    d.text((colx[2], dy + 100), "coordinate + BIS validation", font=f_small, fill=muted)
    d.text((colx[2], dy + 124), "INSERT OR REPLACE into DuckDB", font=f_small, fill=muted)

    d.text((60, 852), "CGWB / NWIC data · GEC-2015 resource assessment · BIS 10500:2012 potability",
           font=f_tiny, fill=muted)
    d.text((W - 60 - d.textlength("INGRES · National Groundwater Intelligence Platform", font=f_tiny), 852),
           "INGRES · National Groundwater Intelligence Platform", font=f_tiny, fill=muted)

    im.save(path, "PNG")
    print("saved", path, im.size)

build("dark", os.path.join(OUT, "architecture_dark.png"))
build("light", os.path.join(OUT, "architecture_light.png"))
