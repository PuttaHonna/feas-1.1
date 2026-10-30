"""
Forensic Evidence Analysis System (FEAS) - ReportLab PDF Templates & Canvas
Provides numbered canvas, forensic headers, security watermarks, and typography styles.
"""

from datetime import datetime, timezone
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfgen import canvas


class NumberedCanvas(canvas.Canvas):
    """
    Custom canvas that records page counts and renders a strict forensic header/footer
    with page numbering, classification marking, and verification notice.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count: int):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#334155"))

        # Top Forensic Banner
        self.setStrokeColor(colors.HexColor("#0f172a"))
        self.setLineWidth(1)
        self.line(40, 760, 572, 760)
        self.drawString(40, 766, "FORENSIC EVIDENCE ANALYSIS SYSTEM (FEAS) — OFFICIAL COURT REPORT")
        self.drawRightString(572, 766, "CHAIN OF CUSTODY: LEVEL-1 AUDIT")

        # Bottom Footer
        self.line(40, 45, 572, 45)
        self.setFont("Helvetica", 8)
        self.drawString(40, 32, "CONFIDENTIAL — STRICT JUDICIAL EVIDENTIARY DISCLOSURE ONLY")
        self.drawRightString(572, 32, f"Page {self._pageNumber} of {page_count}")
        
        # Sub-second timestamp
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        self.drawCentredString(306, 32, f"Generated: {now_utc}")
        
        self.restoreState()


def get_forensic_styles():
    """Build and return custom ReportLab typography styles."""
    styles = getSampleStyleSheet()

    styles.add(ParagraphStyle(
        name="ForensicTitle",
        fontName="Helvetica-Bold",
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=12
    ))

    styles.add(ParagraphStyle(
        name="ForensicSubtitle",
        fontName="Helvetica",
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#475569"),
        spaceAfter=15
    ))

    styles.add(ParagraphStyle(
        name="ForensicH1",
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        textColor=colors.HexColor("#1e293b"),
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    ))

    styles.add(ParagraphStyle(
        name="ForensicH2",
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceBefore=10,
        spaceAfter=6,
        keepWithNext=True
    ))

    styles.add(ParagraphStyle(
        name="ForensicBody",
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1e293b")
    ))

    styles.add(ParagraphStyle(
        name="ForensicBodyBold",
        fontName="Helvetica-Bold",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#0f172a")
    ))

    styles.add(ParagraphStyle(
        name="ForensicCode",
        fontName="Courier",
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#0f172a")
    ))

    styles.add(ParagraphStyle(
        name="VerdictAlert",
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#b91c1c")
    ))

    return styles
