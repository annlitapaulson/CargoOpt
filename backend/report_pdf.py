import io
import os
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas
from reportlab.platypus import (BaseDocTemplate, Frame, Image, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle)

# ---------- Arial (real Windows font files) ----------
FONT_DIR = r"C:\Windows\Fonts"
for _name, _file in [("Arial", "arial.ttf"), ("Arial-Bold", "arialbd.ttf"),
                     ("Arial-Italic", "ariali.ttf"), ("Arial-BoldItalic", "arialbi.ttf")]:
    pdfmetrics.registerFont(TTFont(_name, os.path.join(FONT_DIR, _file)))
pdfmetrics.registerFontFamily("Arial", normal="Arial", bold="Arial-Bold",
                              italic="Arial-Italic", boldItalic="Arial-BoldItalic")

# ---------- Layout ----------
PAGE_W, PAGE_H = A4
MARGIN = 0.5 * inch
CONTENT_W = PAGE_W - 2 * MARGIN
HEADER_H = 56
FOOTER_H = 44
SMALL = 10                      # header / footer font size
LOGO_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")

NAVY = colors.HexColor("#1f3a5f")
GREY = colors.HexColor("#6b7280")
LIGHT = colors.HexColor("#f3f4f6")
LINE = colors.HexColor("#d1d5db")
WATERMARK = colors.Color(0.82, 0.82, 0.82)
RED = colors.HexColor("#b91c1c")
GREEN = colors.HexColor("#15803d")

# ---------- Text styles: heading 18, sub-heading 16, content 14 ----------
BODY = ParagraphStyle("body", fontName="Arial", fontSize=12, leading=16, spaceAfter=4)
H1 = ParagraphStyle("h1", fontName="Arial-Bold", fontSize=18, leading=22, textColor=NAVY,
                    spaceBefore=12, spaceAfter=6, keepWithNext=1)
H2 = ParagraphStyle("h2", fontName="Arial-Bold", fontSize=16, leading=20, textColor=NAVY,
                    spaceBefore=8, spaceAfter=4, keepWithNext=1)
CELL = ParagraphStyle("cell", parent=BODY, spaceAfter=0, leading=15)
CELL_B = ParagraphStyle("cell_b", parent=CELL, fontName="Arial-Bold")
CELL_H = ParagraphStyle("cell_h", parent=CELL, fontName="Arial-Bold", textColor=colors.white)
OK_STYLE = ParagraphStyle("ok", parent=BODY, textColor=GREEN)
BAD_STYLE = ParagraphStyle("bad", parent=BODY, textColor=RED)

ABOUT_TEXT = [
    "CargoOpt is an AI-based container loading and ship stowage optimizer. It was created to help "
    "ship planners decide where each container should go on a vessel, so that the ship stays "
    "balanced and stable, heavy containers sit low, fragile and hazardous cargo is kept apart, and "
    "containers can be unloaded port by port without moving other cargo.",
    "CargoOpt searches for the best arrangement with two methods, a Genetic Algorithm (GA) and "
    "Reinforcement Learning (RL), and checks every result against stacking, weight, balance, "
    "hazardous and fragile, and port-order rules. It also estimates fuel use, CO2 emissions and "
    "the CII grade for the chosen voyage, and shows the plan in a live 3D viewer.",
]


def esc(value):
    return escape(str(value))


def p(text, style=BODY):
    return Paragraph(text, style)


def kv_table(rows):
    data = [[Paragraph(esc(k), CELL_B), Paragraph(esc(v), CELL)] for k, v in rows]
    table = Table(data, colWidths=[200, CONTENT_W - 200])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return table


def grid_table(header, rows, widths):
    data = [[Paragraph(esc(h), CELL_H) for h in header]]
    for row in rows:
        data.append([Paragraph(esc(cell), CELL) for cell in row])
    table = Table(data, colWidths=widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.5, LINE),
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
    ]))
    return table


class NumberedCanvas(canvas.Canvas):
    """Draws header, footer, 'cargoopt' watermark and 'Page X of Y' on every page."""

    def __init__(self, *args, **kwargs):
        canvas.Canvas.__init__(self, *args, **kwargs)
        self._saved_pages = []

    def showPage(self):
        self._saved_pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._saved_pages)
        for state in self._saved_pages:
            self.__dict__.update(state)
            self.decorate(total)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def decorate(self, total):
        self.saveState()
        top = PAGE_H - MARGIN

        # header: logo on the left, text on the right
        box_w, box_h = 170, 46
        box_y = top - box_h - 2
        if os.path.exists(LOGO_PATH):
            reader = ImageReader(LOGO_PATH)
            iw, ih = reader.getSize()
            scale = min(box_w / iw, box_h / ih)
            w, h = iw * scale, ih * scale
            self.drawImage(reader, MARGIN, box_y + (box_h - h) / 2, width=w, height=h, mask="auto")
        else:
            self.setFillColor(NAVY)
            self.roundRect(MARGIN, box_y, 130, box_h, 8, fill=1, stroke=0)
            self.setFillColor(colors.white)
            self.setFont("Arial-Bold", 18)
            self.drawCentredString(MARGIN + 65, box_y + 15, "CargoOpt")
        self.setFillColor(NAVY)
        self.setFont("Arial-Bold", 12)
        self.drawRightString(PAGE_W - MARGIN, top - 28, "CargoOpt - Voyage Report")
        self.setStrokeColor(LINE)
        self.setLineWidth(0.7)
        self.line(MARGIN, top - HEADER_H + 2, PAGE_W - MARGIN, top - HEADER_H + 2)

        # footer: line, light 'cargoopt' watermark, page text
        self.line(MARGIN, MARGIN + FOOTER_H - 4, PAGE_W - MARGIN, MARGIN + FOOTER_H - 4)
        self.setFillColor(WATERMARK)
        self.setFont("Arial-Bold", 16)
        self.drawCentredString(PAGE_W / 2, MARGIN + 18, "cargoopt")
        self.setFillColor(GREY)
        self.setFont("Arial", SMALL)
        self.drawCentredString(PAGE_W / 2, MARGIN + 3, f"CargoOpt | Page {self._pageNumber} of {total}")
        self.restoreState()


def build_report(data, screenshots=None):
    buffer = io.BytesIO()
    doc = BaseDocTemplate(buffer, pagesize=A4, leftMargin=MARGIN, rightMargin=MARGIN,
                          topMargin=MARGIN, bottomMargin=MARGIN,
                          title="Voyage report", author="CargoOpt")
    frame = Frame(MARGIN, MARGIN + FOOTER_H, CONTENT_W,
                  PAGE_H - 2 * MARGIN - HEADER_H - FOOTER_H,
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0, id="main")
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame])])

    now = datetime.now().strftime("%d %B %Y, %I:%M %p")
    em = data["emissions"]
    st = data["stability"]
    story = []

    # ----- title -----
    story.append(p("CargoOpt Voyage Report", H1))
    story.append(p(f"Generated on {esc(now)}"))
    if data.get("voyage_name"):
        story.append(p(f"Voyage: {esc(data['voyage_name'])}"))

    # ----- 1. ship and container details -----
    story.append(p("1. Ship and Container Details", H1))
    story.append(p("Ship", H2))
    story.append(kv_table([
        ("Ship name", data["ship_name"]),
        ("Bay sections", data["sections"]),
        ("Total bays", data["n_bays"]),
        ("Containers", data["n_containers"]),
        ("Total cargo", f"{em['total_cargo_tons']:.1f} tons"),
    ]))
    story.append(p("Containers", H2))
    story.append(p(f"Placement taken from the {esc(data['used'])} result (best score). "
                   "Rows: odd = port side, even = starboard side. Tier 1 = bottom."))
    rows = []
    for c in data["containers"]:
        flags = []
        if c["is_fragile"]:
            flags.append("Fragile")
        if c["is_hazardous"]:
            flags.append("Hazardous")
        rows.append([
            c["container_id"],
            f"{c['weight']:,.0f}",
            f"{c['length']} x {c['width']} x {c['height']}",
            c["destination_port"] or "-",
            ", ".join(flags) or "-",
            f"Sec {c['bay_number']}, Row {c['row']}, Tier {c['tier']}",
        ])
    story.append(grid_table(["ID", "Weight (kg)", "Size L x W x H (m)", "Port", "Flags", "Position"],
                            rows, [76, 72, 120, 96, 80, CONTENT_W - 444]))

    # ----- 2. optimizer scores -----
    story.append(p("2. Optimizer Scores (GA vs RL)", H1))
    score_rows = []
    for key, label in (("ga", "Genetic Algorithm (GA)"), ("rl", "Reinforcement Learning (RL)")):
        r = data[key]
        score_rows.append([label, f"{r['score']:.2f}", f"{r['seconds']:.2f}", len(r["violations"])])
    story.append(grid_table(["Method", "Score", "Time (s)", "Rule violations"],
                            score_rows, [170, 100, 100, CONTENT_W - 370]))
    story.append(Spacer(1, 6))
    story.append(p(f"Result used in this report: {esc(data['used'])}."))

    # ----- 3. voyage report -----
    story.append(p("3. Voyage Report", H1))
    story.append(p("Fuel and Emissions", H2))
    story.append(kv_table([
        ("Distance", f"{em['voyage_distance_nm']} nm"),
        ("Cargo", f"{em['total_cargo_tons']:.1f} tons"),
        ("Fuel", f"{em['fuel_kg']:.2f} kg"),
        ("CO2", f"{em['co2_kg']:.2f} kg"),
        ("CII grade", em["cii_grade"]),
    ]))
    story.append(p("Stability", H2))
    story.append(kv_table([
        ("Port side weight", f"{st['left_weight_kg']:,.0f} kg"),
        ("Starboard side weight", f"{st['right_weight_kg']:,.0f} kg"),
        ("Imbalance", f"{st['imbalance_percent']:.2f}%"),
        ("Balanced", "Yes" if st["is_balanced"] else "No"),
        ("Center of gravity height", f"{st['center_of_gravity_height_m']:.2f} m"),
    ]))

    # ----- 4. rule check -----
    story.append(p("4. Rule Check", H1))
    for key, label in (("ga", "Genetic Algorithm (GA)"), ("rl", "Reinforcement Learning (RL)")):
        story.append(p(label, H2))
        violations = data[key]["violations"]
        if not violations:
            story.append(p("All rules satisfied.", OK_STYLE))
        else:
            for v in violations:
                story.append(p("&bull; " + esc(v), BAD_STYLE))

    # ----- 5. unload plan -----
    story.append(p("5. Unload Plan", H1))
    story.append(p("Ports are listed in unloading order. Inside a port, the top tier is unloaded first."))
    for entry in data["unload_plan"]:
        story.append(p(entry["port"], H2))
        for n, c in enumerate(entry["containers"], start=1):
            story.append(p(f"{n}. {esc(c['container_id'])} (section {c['bay_number']}, tier {c['tier']})"))

    # ----- 6. 3D views -----
    story.append(PageBreak())
    story.append(p("6. 3D Ship Views", H1))
    if screenshots:
        img_w = CONTENT_W / 2 - 12
        caption = ParagraphStyle("caption", parent=BODY, fontSize=11, leading=14,
                                 alignment=1, spaceAfter=0)
        cells = []
        for title, png in screenshots:
            reader = ImageReader(io.BytesIO(png))
            iw, ih = reader.getSize()
            img = Image(io.BytesIO(png), width=img_w, height=img_w * ih / iw)
            cells.append([img, Spacer(1, 3), Paragraph(esc(title), caption)])
        rows = [cells[i:i + 2] for i in range(0, len(cells), 2)]
        if len(rows[-1]) == 1:
            rows[-1].append("")
        table = Table(rows, colWidths=[CONTENT_W / 2, CONTENT_W / 2])
        table.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.5, LINE),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 6),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ]))
        story.append(table)
    else:
        story.append(p("No 3D screenshots were provided."))

    # ----- last page: about -----
    story.append(PageBreak())
    story.append(p("About CargoOpt", H1))
    for paragraph in ABOUT_TEXT:
        story.append(p(esc(paragraph)))

    doc.build(story, canvasmaker=NumberedCanvas)
    return buffer.getvalue()