#!/usr/bin/env python3
"""Document generator for the MOEI / Sheikh Zayed Housing Programme
"AI Agent for Housing Loan Arrears Rescheduling".

Generates a polished, government-service-style PDF pack for seven
beneficiaries — one folder per citizen — plus a document index and README.

NOTE
----
All beneficiary records, Emirates IDs, reference numbers, QR placeholders and
contact details are fictional and were created for this prototype. Entity names
(employer, bank, clinic) are generic placeholders, not real institutions.

Usage
-----
    python scripts/generate_demo_documents.py            # generate everything
    python scripts/generate_demo_documents.py --case SZHP-1001
    python scripts/generate_demo_documents.py --list     # list cases and exit

Deterministic: re-running overwrites the generated files. No randomness, no
network, no system clock used for content (all dates come from the data file).

Dependencies: reportlab (required); arabic-reshaper + python-bidi (optional —
Arabic falls back to a Latin transliteration note if absent).
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path

# Make console output UTF-8 safe on Windows (cp1252 chokes on ✓, —, Arabic …).
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except (AttributeError, ValueError):  # pragma: no cover
    pass

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data" / "demo_cases.json"
OUT_ROOT = ROOT / "demo_documents"
INDEX_FILE = OUT_ROOT / "document_index.json"
README_FILE = OUT_ROOT / "README.md"

# ---------------------------------------------------------------------------
# reportlab imports (hard dependency)
# ---------------------------------------------------------------------------
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.lib.colors import HexColor, Color
    from reportlab.pdfgen import canvas as rl_canvas
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
except ImportError:  # pragma: no cover
    sys.exit(
        "reportlab is required. Install it with:\n"
        "    python -m pip install reportlab arabic-reshaper python-bidi"
    )

# ---------------------------------------------------------------------------
# Optional Arabic shaping
# ---------------------------------------------------------------------------
try:
    import arabic_reshaper
    from bidi.algorithm import get_display

    ARABIC_OK = True
except ImportError:  # pragma: no cover
    ARABIC_OK = False


def _has_arabic(text: str) -> bool:
    return any("؀" <= ch <= "ۿ" for ch in (text or ""))


def shape_ar(text: str) -> str:
    """Reshape + bidi an Arabic string for correct RTL rendering, or pass through."""
    if not text:
        return text
    if ARABIC_OK:
        try:
            return get_display(arabic_reshaper.reshape(text))
        except Exception:
            return text
    return text


# ---------------------------------------------------------------------------
# Design system — colours, fonts, geometry
# ---------------------------------------------------------------------------
NAVY = HexColor("#0B2E4F")
NAVY_DARK = HexColor("#08243E")
TEAL = HexColor("#0E8A8A")
TEAL_SOFT = HexColor("#E6F4F4")
GRAY = HexColor("#5B6470")
GRAY_LIGHT = HexColor("#EEF1F4")
GRAY_LINE = HexColor("#D5DBE1")
INK = HexColor("#1A2230")
WHITE = HexColor("#FFFFFF")
GREEN = HexColor("#1E7D43")
GREEN_SOFT = HexColor("#E7F4EC")
AMBER = HexColor("#B8860B")
AMBER_SOFT = HexColor("#FBF1DA")
RED = HexColor("#B3261E")
RED_SOFT = HexColor("#FBE7E6")
WATER = Color(0.78, 0.80, 0.84, alpha=0.45)

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm
CONTENT_W = PAGE_W - 2 * MARGIN

FONT = "Helvetica"
FONT_B = "Helvetica-Bold"
FONT_I = "Helvetica-Oblique"
FONT_AR = "Helvetica"  # replaced with a real TTF below if available

WATERMARK_TEXT = ""  # no watermark
FOOTER_TEXT = "Sheikh Zayed Housing Programme — Ministry of Energy and Infrastructure."


def _register_arabic_font() -> str:
    """Register a system TTF that contains Arabic glyphs; return its name."""
    candidates = [
        (r"C:\Windows\Fonts\tahoma.ttf", "Tahoma"),
        (r"C:\Windows\Fonts\arial.ttf", "ArialUni"),
        ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "DejaVuSans"),
        ("/Library/Fonts/Arial.ttf", "ArialUni"),
    ]
    for path, name in candidates:
        if Path(path).exists():
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name
            except Exception:
                continue
    return FONT  # fall back to Helvetica (Arabic will not render, English will)


FONT_AR = _register_arabic_font()


# ---------------------------------------------------------------------------
# Status → colour helpers
# ---------------------------------------------------------------------------
def result_colors(result: str) -> tuple[Color, Color]:
    r = (result or "").strip().lower()
    if r in ("pass", "approved", "active"):
        return GREEN, GREEN_SOFT
    if r in ("fail", "rejected", "blocked", "human review required"):
        return RED, RED_SOFT
    if r in ("warn", "not applicable", "n/a"):
        return AMBER, AMBER_SOFT
    return GRAY, GRAY_LIGHT


def status_palette(status: str) -> tuple[Color, Color]:
    s = (status or "").lower()
    if "approv" in s:
        return GREEN, GREEN_SOFT
    if "block" in s or "reject" in s or "human review" in s:
        return RED, RED_SOFT
    if "hardship" in s or "additional" in s or "maintain" in s or "officer" in s:
        return AMBER, AMBER_SOFT
    return NAVY, TEAL_SOFT


def aed(value) -> str:
    if value is None:
        return "—"
    if isinstance(value, str):
        return value
    try:
        return f"AED {value:,.0f}"
    except (TypeError, ValueError):
        return str(value)


# ---------------------------------------------------------------------------
# DocCanvas — a thin layout engine over reportlab's canvas
# ---------------------------------------------------------------------------
@dataclass
class DocMeta:
    title_en: str
    title_ar: str
    org: str
    case_id: str
    beneficiary: str
    badge: str | None = None
    badge_kind: str = "navy"  # navy | green | amber | red


class DocCanvas:
    """Wraps a reportlab canvas with a consistent header/watermark/footer and a
    simple top-down content cursor (self.y)."""

    def __init__(self, path: Path, meta: DocMeta):
        self.path = path
        self.meta = meta
        self.c = rl_canvas.Canvas(str(path), pagesize=A4)
        self.c.setTitle(f"{meta.title_en} — {meta.case_id}")
        self.c.setAuthor("Sheikh Zayed Housing Programme — MOEI")
        self.c.setSubject(meta.title_en)
        self.page_num = 0
        self.y = 0.0
        self._begin_page()

    # -- page lifecycle ----------------------------------------------------
    def _begin_page(self):
        self.page_num += 1
        self._draw_watermark()
        self._draw_header()
        self._draw_footer()
        self.y = PAGE_H - 46 * mm  # below header band

    def _new_page(self):
        self.c.showPage()
        self._begin_page()

    def ensure(self, needed: float):
        """Start a new page if less than `needed` vertical space remains."""
        if self.y - needed < 24 * mm:
            self._new_page()

    def finish(self):
        self.c.save()

    # -- chrome ------------------------------------------------------------
    def _draw_watermark(self):
        if not WATERMARK_TEXT:
            return
        c = self.c
        c.saveState()
        c.translate(PAGE_W / 2, PAGE_H / 2)
        c.rotate(33)
        c.setFont(FONT_B, 22)
        c.setFillColor(WATER)
        # three stacked diagonal lines so the mark covers the whole page
        for dy in (90 * mm, 0, -90 * mm):
            c.drawCentredString(0, dy, WATERMARK_TEXT)
        c.restoreState()

    def _draw_header(self):
        c = self.c
        m = self.meta
        # navy band
        c.setFillColor(NAVY)
        c.rect(0, PAGE_H - 34 * mm, PAGE_W, 34 * mm, fill=1, stroke=0)
        # teal accent rule
        c.setFillColor(TEAL)
        c.rect(0, PAGE_H - 35 * mm, PAGE_W, 1 * mm, fill=1, stroke=0)

        # neutral monogram (no real logo)
        c.setFillColor(TEAL)
        c.roundRect(MARGIN, PAGE_H - 27 * mm, 16 * mm, 16 * mm, 3 * mm, fill=1, stroke=0)
        c.setFillColor(WHITE)
        c.setFont(FONT_B, 13)
        c.drawCentredString(MARGIN + 8 * mm, PAGE_H - 20.2 * mm, "SZHP")

        tx = MARGIN + 22 * mm
        c.setFillColor(WHITE)
        c.setFont(FONT_B, 13)
        c.drawString(tx, PAGE_H - 14 * mm, m.org)
        c.setFont(FONT, 9.5)
        c.setFillColor(HexColor("#BFD2E2"))
        c.drawString(tx, PAGE_H - 19 * mm, m.title_en)
        if FONT_AR != FONT and m.title_ar:
            c.setFont(FONT_AR, 10)
            c.drawString(tx, PAGE_H - 24.5 * mm, shape_ar(m.title_ar))

        # right column: case id + classification tag
        c.setFont(FONT, 8.5)
        c.setFillColor(HexColor("#BFD2E2"))
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - 13 * mm, f"Case: {m.case_id}")
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - 17.5 * mm, m.beneficiary)
        c.setFillColor(HexColor("#7FA8C9"))
        c.setFont(FONT_B, 7)
        c.drawRightString(PAGE_W - MARGIN, PAGE_H - 23 * mm, "OFFICIAL · CONFIDENTIAL")

        # optional status badge under the band
        if m.badge:
            self._badge_top(m.badge, m.badge_kind)

    def _badge_top(self, text: str, kind: str):
        c = self.c
        palette = {
            "navy": (NAVY, TEAL_SOFT),
            "green": (GREEN, GREEN_SOFT),
            "amber": (AMBER, AMBER_SOFT),
            "red": (RED, RED_SOFT),
        }
        fg, bg = palette.get(kind, (NAVY, TEAL_SOFT))
        c.setFont(FONT_B, 9)
        w = c.stringWidth(text, FONT_B, 9) + 12 * mm
        x = PAGE_W - MARGIN - w
        y = PAGE_H - 42 * mm
        c.setFillColor(bg)
        c.roundRect(x, y, w, 7 * mm, 2 * mm, fill=1, stroke=0)
        c.setFillColor(fg)
        c.drawCentredString(x + w / 2, y + 2.1 * mm, text.upper())

    def _draw_footer(self):
        c = self.c
        c.setStrokeColor(GRAY_LINE)
        c.setLineWidth(0.6)
        c.line(MARGIN, 16 * mm, PAGE_W - MARGIN, 16 * mm)
        c.setFont(FONT_I, 7.6)
        c.setFillColor(GRAY)
        c.drawString(MARGIN, 11.5 * mm, FOOTER_TEXT)
        c.drawRightString(PAGE_W - MARGIN, 11.5 * mm, f"Page {self.page_num}")

    # -- content primitives ------------------------------------------------
    def doc_title(self, title: str, subtitle: str | None = None):
        c = self.c
        self.ensure(20 * mm)
        c.setFillColor(NAVY)
        c.setFont(FONT_B, 17)
        c.drawString(MARGIN, self.y, title)
        self.y -= 6.5 * mm
        if subtitle:
            c.setFont(FONT, 9.5)
            c.setFillColor(GRAY)
            self.y -= 1 * mm
            for line in self._wrap(subtitle, FONT, 9.5, CONTENT_W):
                c.drawString(MARGIN, self.y, line)
                self.y -= 5 * mm
        c.setStrokeColor(TEAL)
        c.setLineWidth(1.4)
        c.line(MARGIN, self.y, MARGIN + 60 * mm, self.y)
        self.y -= 7 * mm

    def section(self, label: str):
        c = self.c
        self.ensure(14 * mm)
        self.y -= 2 * mm
        c.setFillColor(NAVY)
        if _has_arabic(label) and FONT_AR != FONT:
            c.setFont(FONT_AR, 11.5)
            c.drawRightString(PAGE_W - MARGIN, self.y, shape_ar(label))
        else:
            c.setFont(FONT_B, 11.5)
            c.drawString(MARGIN, self.y, label)
        self.y -= 2.5 * mm
        c.setStrokeColor(GRAY_LINE)
        c.setLineWidth(0.6)
        c.line(MARGIN, self.y, PAGE_W - MARGIN, self.y)
        self.y -= 6 * mm

    def paragraph(self, text: str, size: float = 9.5, color: Color = INK, gap: float = 2 * mm):
        c = self.c
        for line in self._wrap(text, FONT, size, CONTENT_W):
            self.ensure(7 * mm)
            c.setFont(FONT, size)
            c.setFillColor(color)
            c.drawString(MARGIN, self.y, line)
            self.y -= size * 0.46 + 1.6 * mm
        self.y -= gap

    def arabic_paragraph(self, text: str, size: float = 10, color: Color = INK, gap: float = 2 * mm):
        c = self.c
        if FONT_AR == FONT:
            self.paragraph("[Arabic text — install arabic-reshaper + python-bidi to render]",
                           size=8.5, color=GRAY, gap=gap)
            return
        # naive wrap by width on the shaped string
        for raw in self._wrap_ar(text, FONT_AR, size, CONTENT_W):
            self.ensure(7 * mm)
            c.setFont(FONT_AR, size)
            c.setFillColor(color)
            c.drawRightString(PAGE_W - MARGIN, self.y, shape_ar(raw))
            self.y -= size * 0.5 + 1.8 * mm
        self.y -= gap

    def callout(self, text: str, kind: str = "navy", title: str | None = None):
        palette = {
            "navy": (NAVY, TEAL_SOFT),
            "green": (GREEN, GREEN_SOFT),
            "amber": (AMBER, AMBER_SOFT),
            "red": (RED, RED_SOFT),
            "gray": (GRAY, GRAY_LIGHT),
        }
        fg, bg = palette.get(kind, (NAVY, TEAL_SOFT))
        c = self.c
        lines = []
        if title:
            lines.append(("title", title))
        for ln in self._wrap(text, FONT, 9.5, CONTENT_W - 14 * mm):
            lines.append(("body", ln))
        h = 6 * mm + len(lines) * 5 * mm
        self.ensure(h + 4 * mm)
        top = self.y
        c.setFillColor(bg)
        c.roundRect(MARGIN, top - h, CONTENT_W, h, 2.5 * mm, fill=1, stroke=0)
        c.setFillColor(fg)
        c.rect(MARGIN, top - h, 1.6 * mm, h, fill=1, stroke=0)
        ty = top - 6 * mm
        for kind_, ln in lines:
            if kind_ == "title":
                c.setFont(FONT_B, 9.8)
                c.setFillColor(fg)
            else:
                c.setFont(FONT, 9.5)
                c.setFillColor(INK)
            c.drawString(MARGIN + 6 * mm, ty, ln)
            ty -= 5 * mm
        self.y = top - h - 4 * mm

    def key_value_table(self, rows: list[tuple[str, str]], col1: float = 62 * mm):
        """Two-column label/value table with zebra striping."""
        c = self.c
        rh = 8 * mm
        for i, (k, v) in enumerate(rows):
            value_lines = self._wrap(str(v), FONT, 9.5, CONTENT_W - col1 - 6 * mm) or [""]
            row_h = max(rh, 4 * mm + len(value_lines) * 4.6 * mm)
            self.ensure(row_h + 2 * mm)
            top = self.y
            if i % 2 == 0:
                c.setFillColor(GRAY_LIGHT)
                c.rect(MARGIN, top - row_h, CONTENT_W, row_h, fill=1, stroke=0)
            c.setFont(FONT_B, 9)
            c.setFillColor(NAVY)
            for kl in self._wrap(str(k), FONT_B, 9, col1 - 6 * mm):
                c.drawString(MARGIN + 3 * mm, top - 5.4 * mm, kl)
                break  # keys are short; single line
            c.setFont(FONT, 9.5)
            c.setFillColor(INK)
            vy = top - 5.4 * mm
            for vl in value_lines:
                c.drawString(MARGIN + col1, vy, vl)
                vy -= 4.6 * mm
            self.y = top - row_h
        self.y -= 3 * mm

    def simple_table(self, headers: list[str], rows: list[list[str]],
                     aligns: list[str] | None = None, status_col: int | None = None):
        """Grid table with a navy header row, zebra body, optional coloured status cell."""
        c = self.c
        n = len(headers)
        col_w = CONTENT_W / n
        aligns = aligns or ["left"] * n
        header_h = 8 * mm
        row_h = 7 * mm

        def draw_header():
            top = self.y
            c.setFillColor(NAVY)
            c.rect(MARGIN, top - header_h, CONTENT_W, header_h, fill=1, stroke=0)
            c.setFillColor(WHITE)
            c.setFont(FONT_B, 8.6)
            for j, htxt in enumerate(headers):
                self._cell_text(htxt, MARGIN + j * col_w, top - 5.3 * mm, col_w, aligns[j])
            self.y = top - header_h

        self.ensure(header_h + row_h * 2)
        draw_header()
        for i, row in enumerate(rows):
            self.ensure(row_h + 2 * mm)
            if self.y - row_h < 24 * mm:
                draw_header()
            top = self.y
            if i % 2 == 1:
                c.setFillColor(GRAY_LIGHT)
                c.rect(MARGIN, top - row_h, CONTENT_W, row_h, fill=1, stroke=0)
            for j, val in enumerate(row):
                x = MARGIN + j * col_w
                if status_col is not None and j == status_col:
                    fg, bg = result_colors(val)
                    pad = 1.4 * mm
                    bw = min(col_w - 3 * mm, c.stringWidth(val, FONT_B, 8) + 6 * mm)
                    c.setFillColor(bg)
                    c.roundRect(x + 2 * mm, top - row_h + 1.4 * mm, bw, row_h - 2.8 * mm,
                                1.4 * mm, fill=1, stroke=0)
                    c.setFillColor(fg)
                    c.setFont(FONT_B, 8)
                    c.drawString(x + 2 * mm + 3 * mm, top - 4.9 * mm, val)
                else:
                    c.setFillColor(INK)
                    c.setFont(FONT, 8.4)
                    self._cell_text(str(val), x, top - 4.9 * mm, col_w, aligns[j])
            self.y = top - row_h
        # outer border + column rules
        # (light grid for readability)
        c.setStrokeColor(GRAY_LINE)
        c.setLineWidth(0.5)
        self.y -= 4 * mm

    def signature_block(self, name: str, role: str):
        c = self.c
        self.ensure(24 * mm)
        self.y -= 6 * mm
        c.setStrokeColor(GRAY)
        c.setLineWidth(0.7)
        c.line(MARGIN, self.y, MARGIN + 60 * mm, self.y)
        self.y -= 5 * mm
        c.setFont(FONT_B, 9)
        c.setFillColor(NAVY)
        c.drawString(MARGIN, self.y, name)
        self.y -= 4.6 * mm
        c.setFont(FONT, 8.5)
        c.setFillColor(GRAY)
        c.drawString(MARGIN, self.y, role)
        c.drawString(MARGIN, self.y - 4.6 * mm, "Signed electronically")
        self.y -= 10 * mm

    def qr_placeholder(self, label: str = "Scan to verify"):
        c = self.c
        size = 26 * mm
        x = PAGE_W - MARGIN - size
        self.ensure(size + 4 * mm)
        top = self.y
        c.setStrokeColor(GRAY_LINE)
        c.setLineWidth(0.8)
        c.setFillColor(GRAY_LIGHT)
        c.roundRect(x, top - size, size, size, 2 * mm, fill=1, stroke=1)
        # faux QR finder squares
        c.setFillColor(GRAY)
        for (dx, dy) in ((3, 3), (3, size / mm - 9), (size / mm - 9, 3)):
            c.rect(x + dx * mm, top - size + dy * mm, 6 * mm, 6 * mm, fill=0, stroke=1)
            c.rect(x + (dx + 2) * mm, top - size + (dy + 2) * mm, 2 * mm, 2 * mm, fill=1, stroke=0)
        c.setFont(FONT, 6.6)
        c.setFillColor(GRAY)
        c.drawCentredString(x + size / 2, top - size / 2, label)
        # do not advance y far — caller continues alongside
        self.y = top  # leave cursor; this floats on the right

    # -- text wrapping -----------------------------------------------------
    def _wrap(self, text: str, font: str, size: float, max_w: float) -> list[str]:
        if text is None:
            return [""]
        text = str(text)
        out: list[str] = []
        for para in text.split("\n"):
            words = para.split(" ")
            line = ""
            for w in words:
                trial = (line + " " + w).strip()
                if self.c.stringWidth(trial, font, size) <= max_w:
                    line = trial
                else:
                    if line:
                        out.append(line)
                    line = w
            out.append(line)
        return out

    def _wrap_ar(self, text: str, font: str, size: float, max_w: float) -> list[str]:
        out: list[str] = []
        for para in text.split("\n"):
            words = para.split(" ")
            line = ""
            for w in words:
                trial = (line + " " + w).strip()
                if self.c.stringWidth(shape_ar(trial), font, size) <= max_w:
                    line = trial
                else:
                    if line:
                        out.append(line)
                    line = w
            out.append(line)
        return out

    def _cell_text(self, text: str, x: float, y: float, col_w: float, align: str):
        c = self.c
        # truncate to fit
        t = text
        while c.stringWidth(t, c._fontname, c._fontsize) > col_w - 4 * mm and len(t) > 3:
            t = t[:-2]
        if t != text:
            t = t.rstrip() + "…"
        if align == "right":
            c.drawRightString(x + col_w - 2 * mm, y, t)
        elif align == "center":
            c.drawCentredString(x + col_w / 2, y, t)
        else:
            c.drawString(x + 2 * mm, y, t)


# ---------------------------------------------------------------------------
# Helper: build DocMeta for a case
# ---------------------------------------------------------------------------
def meta_for(case: dict, title_en: str, title_ar: str, org: str,
             badge: str | None = None, badge_kind: str = "navy") -> DocMeta:
    return DocMeta(
        title_en=title_en,
        title_ar=title_ar,
        org=org,
        case_id=case["case_id"],
        beneficiary=case["full_name"],
        badge=badge,
        badge_kind=badge_kind,
    )


# ===========================================================================
# DOCUMENT GENERATORS
# Each returns nothing; writes one PDF to `path`.
# ===========================================================================
def generate_uae_pass_profile(case: dict, path: Path):
    p = case["citizen_profile"]
    d = DocCanvas(path, meta_for(case, "Verified Identity Profile",
                                 "ملف الهوية الموثق", "UAE PASS",
                                 badge="UAE PASS · Verified", badge_kind="green"))
    d.doc_title("Digital Identity Profile",
                "Retrieved via UAE PASS for the arrears-rescheduling workflow.")
    d.key_value_table([
        ("Full Name", p["full_name"]),
        ("Full Name (Arabic)", p.get("full_name_ar", "—")),
        ("Case / Beneficiary ID", case["case_id"]),
        ("Emirates ID", p["emirates_id"]),
        ("Nationality", p["nationality"]),
        ("Date of Birth", p["date_of_birth"]),
        ("Mobile", p["mobile"]),
        ("Email", p["email"]),
        ("Family Book Number", p["family_book_number"]),
        ("Marital Status", p["marital_status"]),
        ("Number of Dependents", str(p["dependents"])),
        ("Employment Status", p["employment_status"]),
        ("Login Timestamp", p["login_timestamp"]),
        ("Data Source", p["data_source"]),
    ])
    d.callout(
        "Identity verified through UAE PASS and retrieved for the arrears-rescheduling "
        "assessment. This profile is confidential.",
        kind="navy", title="Verified identity")
    d.finish()


def generate_application_form(case: dict, path: Path):
    a = case["application"]
    d = DocCanvas(path, meta_for(case, "Rescheduling Application",
                                 "طلب إعادة الجدولة", "Sheikh Zayed Housing Programme",
                                 badge="Application", badge_kind="navy"))
    d.doc_title("Arrears Rescheduling — Application Form",
                "Beneficiary-initiated request submitted through the citizen portal.")
    d.key_value_table([
        ("Application ID", a["application_id"]),
        ("Beneficiary ID", case["beneficiary_id"]),
        ("Beneficiary Name", case["full_name"]),
        ("Request Date", a["request_date"]),
        ("Selected Request Type", a["request_type"]),
    ])
    d.section("Reason for Rescheduling")
    d.paragraph(a["reason"])

    d.section("Uploaded Document Checklist")
    checklist = a.get("uploaded_documents", [])
    rows = [[doc.replace("_", " ").title(), "Uploaded"] for doc in checklist]
    d.simple_table(["Document", "Status"], rows, aligns=["left", "center"], status_col=1)

    d.section("Citizen Declaration")
    d.paragraph(
        "I declare that the information provided in this application is true and complete to the "
        "best of my knowledge, and I authorise the programme to verify it against official records.")

    d.section("Digital Consent")
    box = "[x]" if a.get("consent") else "[ ]"
    d.callout(f"{box}  {a['consent_text']}", kind="green",
              title="Consent to data retrieval")
    d.signature_block(case["full_name"], "Beneficiary (digital consent recorded)")
    d.finish()


def generate_salary_certificate(case: dict, path: Path, suspicious: bool = False):
    s = case["salary"]
    badge = "Flagged" if suspicious else "Salary Certificate"
    kind = "red" if suspicious else "navy"
    title = "Salary Certificate" + (" (Disputed)" if suspicious else "")
    d = DocCanvas(path, meta_for(case, title, "شهادة راتب", "Emirates Employer Services LLC",
                                 badge=badge, badge_kind=kind))
    d.doc_title(title, "Issued by Emirates Employer Services LLC.")
    # QR floats right; key-values flow left
    save_y = d.y
    d.qr_placeholder(s.get("qr_placeholder") or "Scan to verify")
    d.y = save_y
    rows = [
        ("Employer Name", s.get("employer_name", "—")),
        ("Employee Name", case["full_name"]),
        ("Emirates ID",
         s.get("emirates_id_on_certificate", case["citizen_profile"]["emirates_id"])),
        ("Job Title", s.get("job_title", "—")),
        ("Employment Start Date", s.get("employment_start_date", "—")),
        ("Basic Salary", aed(s.get("basic_salary"))),
        ("Allowances", aed(s.get("allowances"))),
        ("Gross Monthly Salary", aed(s.get("gross_monthly_salary"))),
        ("Deductions", aed(s.get("deductions"))),
        ("Net Salary", aed(s.get("net_salary"))),
        ("Issue Date", s.get("issue_date", "—")),
        ("Reference Number", s.get("reference_number", "—")),
    ]
    d.key_value_table(rows, col1=58 * mm)
    if suspicious:
        d.callout(
            "This certificate is presented as part of a fraud-review scenario. The agent flagged: "
            "an overstated salary versus bank transfers, a missing reference/QR, a stale issue date, "
            "an employer-name mismatch, and a one-digit Emirates ID mismatch.",
            kind="red", title="Authenticity warnings raised by the Document Auditor")
    else:
        d.callout(
            "Issued by the employer's Human Resources department and verified against bank salary "
            "transfers during the assessment.",
            kind="green", title="Verified salary")
    d.signature_block("Authorized Signatory", "Human Resources — Emirates Employer Services LLC")
    d.finish()


def generate_income_statement(case: dict, path: Path, label_override: str | None = None,
                              mismatch: bool = False):
    inc = case["income_statement"]
    badge = "Income — Mismatch" if mismatch else "Income Statement"
    d = DocCanvas(path, meta_for(case, "Income Statement", "كشف الدخل", "Union Bank",
                                 badge=badge, badge_kind="red" if mismatch else "navy"))
    title = label_override or inc.get("label") or "6-Month Salary Transfer Statement"
    d.doc_title(title, "Salary credits observed on the beneficiary's account.")
    rows = [
        [m["month"], aed(m["gross"]), aed(m["net"]), m["transfer_date"], m.get("notes", "")]
        for m in inc["months"]
    ]
    d.simple_table(
        ["Month", "Gross", "Net", "Transfer Date", "Notes"],
        rows, aligns=["left", "right", "right", "center", "left"])
    trend = inc.get("income_trend", "stable")
    trend_kind = {"stable": "green", "reduced": "amber", "stopped": "red", "mismatch": "red"}.get(trend, "navy")
    d.key_value_table([
        ("Average Monthly Income (net)", aed(inc.get("average_monthly_income"))),
        ("Income Trend", trend.title()),
    ])
    if mismatch:
        d.callout(
            f"Bank-observed income averages {aed(inc.get('average_monthly_income'))} net, which "
            f"contradicts the AED 35,000 gross claimed on the salary certificate. The agent treats "
            f"the verified bank figure as authoritative and escalates the discrepancy.",
            kind="red", title="Income trend: MISMATCH")
    else:
        d.callout(f"Income trend assessed as '{trend}'.", kind=trend_kind)
    d.finish()


def generate_obligations_letter(case: dict, path: Path):
    o = case["obligations"]
    d = DocCanvas(path, meta_for(case, "Financial Obligations Letter",
                                 "خطاب الالتزامات المالية", "Union Bank / Al Etihad Credit Bureau",
                                 badge="Obligations", badge_kind="navy"))
    d.doc_title("Statement of Financial Obligations",
                "Aggregated monthly commitments — credit-bureau extract.")
    d.simple_table(
        ["Obligation", "Monthly (AED)"],
        [
            ["Personal loan installment", f"{o['personal_loan']:,.0f}"],
            ["Car loan installment", f"{o['car_loan']:,.0f}"],
            ["Credit card minimum payment", f"{o['credit_card_min']:,.0f}"],
            ["Other obligations", f"{o['other']:,.0f}"],
            ["Total monthly obligations", f"{o['total_monthly_obligations']:,.0f}"],
        ],
        aligns=["left", "right"])
    ratio = o.get("obligation_to_income_ratio_pct")
    rk = "red" if (ratio or 0) >= 60 else ("amber" if (ratio or 0) >= 40 else "green")
    d.key_value_table([
        ("Total Monthly Obligations", aed(o["total_monthly_obligations"])),
        ("Obligation-to-Income Ratio", f"{ratio}%" if ratio is not None else "—"),
        ("Issue Date", o["issue_date"]),
        ("Bank Reference", o["reference_number"]),
    ])
    d.callout(
        f"Obligation-to-income ratio is {ratio}%. "
        + ("This exceeds the 60% prudential threshold — disposable income is thin."
           if (ratio or 0) >= 60 else "This is within prudential range."),
        kind=rk, title="Obligation ratio")
    d.finish()


def generate_direct_debit_proof(case: dict, path: Path):
    dd = case["direct_debit"]
    d = DocCanvas(path, meta_for(case, "Direct Debit Mandate Proof",
                                 "إثبات التحصيل المباشر", "Union Bank",
                                 badge="Direct Debit", badge_kind="navy"))
    d.doc_title("Direct Debit Mandate & Collection Proof",
                "Mandate status and recent collection attempts.")
    d.key_value_table([
        ("Masked Account Number", dd["masked_account"]),
        ("Direct Debit Mandate Status", dd["mandate_status"]),
        ("Last Successful Debit", dd["last_successful_debit"]),
        ("Mandate Expiry Date", dd["mandate_expiry"]),
        ("Failure Reason", dd["failure_reason"]),
    ])
    d.section("Failed Debit Attempts")
    rows = [[dt, "Failed", dd["failure_reason"]] for dt in dd.get("failed_debit_dates", [])]
    if not rows:
        rows = [["—", "—", "No failed attempts on record"]]
    d.simple_table(["Date", "Result", "Reason"], rows,
                   aligns=["left", "center", "left"], status_col=1)
    d.finish()


def generate_moei_loan_statement(case: dict, path: Path):
    ln = case["loan"]
    d = DocCanvas(path, meta_for(case, "MOEI Loan Statement",
                                 "كشف القرض", "MOEI Loan System",
                                 badge="Loan System", badge_kind="navy"))
    d.doc_title("Housing Loan Statement",
                "Authoritative loan record retrieved from the MOEI Loan System.")
    d.key_value_table([
        ("Beneficiary ID", case["beneficiary_id"]),
        ("Original Loan Amount", aed(ln["original_loan_amount"])),
        ("Remaining Loan Balance", aed(ln["remaining_balance"])),
        ("Original Approved Repayment Period", f"{ln['original_approved_period_months']} months"),
        ("Remaining Repayment Period", f"{ln['remaining_period_months']} months"),
        ("Current Monthly Installment", aed(ln["current_installment"])),
        ("Loan Start Date", ln["loan_start_date"]),
        ("Loan Maturity Date", ln["loan_maturity_date"]),
    ])
    d.callout(
        "RULE CHECK — The proposed new schedule must not exceed the original approved repayment "
        f"period of {ln['original_approved_period_months']} months. This constraint is enforced by "
        "the Policy Engine and the Legal Clock agents.",
        kind="navy", title="Period constraint")
    d.callout("Data source: MOEI Loan System.", kind="gray")
    d.finish()


def generate_arrears_statement(case: dict, path: Path):
    ar = case["arrears"]
    d = DocCanvas(path, meta_for(case, "Arrears Statement",
                                 "كشف المتأخرات", "MOEI Loan System",
                                 badge="Arrears", badge_kind="amber"))
    d.doc_title("Arrears Statement",
                "Outstanding overdue position on the housing loan.")
    d.key_value_table([
        ("Total Arrears Amount", aed(ar["arrears_amount"])),
        ("Number of Unpaid Installments", str(ar["unpaid_installments"])),
        ("Oldest Unpaid Installment Date", ar["oldest_unpaid_date"]),
        ("Latest Unpaid Installment Date", ar["latest_unpaid_date"]),
        ("Days Past Due", str(ar["days_past_due"])),
        ("Collection / Legal Risk Stage", ar["risk_stage"]),
    ])
    dpd = ar.get("days_past_due", 0)
    rk = "red" if dpd >= 240 else ("amber" if dpd >= 90 else "green")
    d.callout(
        f"{ar['unpaid_installments']} installments unpaid, {dpd} days past due. "
        f"Risk stage: {ar['risk_stage']}.",
        kind=rk, title="Collections position")
    d.finish()


def generate_payment_history(case: dict, path: Path):
    ph = case["payment_history"]
    d = DocCanvas(path, meta_for(case, "Payment History",
                                 "سجل المدفوعات", "MOEI Loan System",
                                 badge="Payment History", badge_kind="navy"))
    d.doc_title("Installment Payment History",
                "Month-by-month payment performance.")
    rows = [
        [r["month"], aed(r["expected"]), aed(r["paid"]), r["status"],
         str(r["late_days"]), r["failed_debit"]]
        for r in ph
    ]
    d.simple_table(
        ["Month", "Expected", "Paid", "Status", "Late Days", "Failed Debit"],
        rows,
        aligns=["left", "right", "right", "center", "center", "center"],
        status_col=3)
    paid = sum(1 for r in ph if r["status"] == "Paid")
    missed = sum(1 for r in ph if r["status"] in ("Missed", "Failed Debit"))
    d.key_value_table([
        ("Months Shown", str(len(ph))),
        ("On-time / Paid", str(paid)),
        ("Missed / Failed Debit", str(missed)),
    ])
    d.finish()


def generate_active_request_record(case: dict, path: Path):
    rq = case["active_request"]
    d = DocCanvas(path, meta_for(case, "Active Request Record",
                                 "سجل الطلب النشط", "MOEI Case Management System",
                                 badge="Conflict", badge_kind="red"))
    d.doc_title("Existing Active Request — Conflict Record",
                "Prior rescheduling request already in the workflow.")
    d.key_value_table([
        ("Existing Application ID", rq["existing_application_id"]),
        ("Existing Request Type", rq["request_type"]),
        ("Submitted Date", rq["submitted_date"]),
        ("Current Status", rq["status"]),
        ("Assigned Unit", rq["assigned_unit"]),
    ])
    d.callout("Active request exists. New request blocked.", kind="red",
              title="Conflict result")
    d.finish()


def generate_medical_treatment_letter(case: dict, path: Path):
    h = case["hardship"]
    d = DocCanvas(path, meta_for(case, "Medical Treatment Letter",
                                 "خطاب العلاج الطبي", "Specialist Medical Center",
                                 badge="Medical", badge_kind="amber"))
    d.doc_title("Medical Treatment Letter",
                "Supporting document for a temporary medical-hardship request.")
    d.callout(
        "This letter supports a temporary medical-hardship request and is treated as confidential "
        "health information used solely for the rescheduling assessment.",
        kind="amber", title="Confidential — medical")
    d.key_value_table([
        ("Clinic / Hospital", h["clinic_name"]),
        ("Patient Name", h["patient_name"]),
        ("Treatment Reason", h["treatment_reason"]),
        ("Treatment Period", f"{h['treatment_period_months']} months"),
        ("Expected End Date", h["expected_end_date"]),
        ("Hardship Classification", h["classification"]),
        ("Medical Reference", h["medical_reference"]),
    ])
    d.signature_block("Attending Physician", "Specialist Medical Center")
    d.finish()


def generate_unemployment_letter(case: dict, path: Path):
    h = case["hardship"]
    d = DocCanvas(path, meta_for(case, "Unemployment / Separation Letter",
                                 "خطاب إنهاء الخدمة", "Emirates Employer Services LLC",
                                 badge="Unemployment", badge_kind="amber"))
    d.doc_title("Employment Separation Letter",
                "Confirms loss of stable income — basis for the hardship route.")
    d.key_value_table([
        ("Previous Employer", h["previous_employer"]),
        ("Last Working Date", h["last_working_date"]),
        ("Reason for Separation", h["reason_for_separation"]),
        ("Current Income Status", h["current_income_status"]),
        ("Expected Re-employment / Pension Date", h.get("expected_reemployment_date", "—")),
        ("Reference", "HR-SEP-" + case["case_id"].split("-")[-1]),
    ])
    d.callout(
        "With no stable income, the agent must not increase the monthly burden. The recommended "
        "route is to defer arrears and hold (or pause) the installment until income is re-verified.",
        kind="amber", title="Hardship implication")
    d.signature_block("Authorized Signatory", "Human Resources — Emirates Employer Services LLC")
    d.finish()


def generate_family_status_record(case: dict, path: Path):
    p = case["citizen_profile"]
    inc = case.get("income_statement") or {}
    avg = inc.get("average_monthly_income")
    dependents = p["dependents"]
    family_size = dependents + 1
    per_member = (avg / family_size) if (avg and family_size) else None
    special = {
        "unemployment_hardship": "Sole earner currently unemployed; 4 dependents.",
        "medical_hardship": "Primary earner undergoing medical treatment abroad.",
    }.get(case["scenario"], "None recorded.")
    d = DocCanvas(path, meta_for(case, "Family Status Record",
                                 "سجل الحالة العائلية", "MOEI / Civil Status Records",
                                 badge="Family Status", badge_kind="navy"))
    d.doc_title("Family Status Record",
                "Household composition used in the affordability and hardship assessment.")
    d.key_value_table([
        ("Marital Status", p["marital_status"]),
        ("Number of Dependents", str(dependents)),
        ("Family Size", str(family_size)),
        ("Monthly Household Income", aed(avg) if avg is not None else "Unknown / under review"),
        ("Average Income per Family Member",
         aed(per_member) if per_member is not None else "—"),
        ("Special Circumstances", special),
    ])
    d.finish()


def generate_missing_documents_notice(case: dict, path: Path):
    d = DocCanvas(path, meta_for(case, "Additional Information Required",
                                 "مطلوب معلومات إضافية", "Sheikh Zayed Housing Programme",
                                 badge="Info Required", badge_kind="amber"))
    d.doc_title("Notice — Additional Information Required",
                "Issued automatically by the AI agent when required documents are missing.")
    d.key_value_table([
        ("Case ID", case["case_id"]),
        ("Beneficiary", case["full_name"]),
        ("Status", case["expected_status"]),
        ("Submission Deadline", case.get("submission_deadline", "—")),
    ])
    d.section("Missing Required Documents")
    rows = [[m.replace("_", " ").title(), "Missing"] for m in case.get("missing_documents", [])]
    d.simple_table(["Document", "Status"], rows, aligns=["left", "center"], status_col=1)
    d.section("Required Action")
    d.paragraph(
        "Please upload the documents listed above through the citizen portal before the submission "
        "deadline. The case will then be re-assessed automatically. No human review is required "
        "unless the documents remain missing after the deadline.")
    d.section("Explanation (English)")
    d.paragraph(case["bilingual_summary"]["en"])
    d.section("التوضيح (بالعربية)")
    d.arabic_paragraph(case["bilingual_summary"]["ar"])
    d.finish()


def generate_human_review_notice(case: dict, path: Path):
    d = DocCanvas(path, meta_for(case, "Human Review Required",
                                 "مطلوب مراجعة بشرية", "Sheikh Zayed Housing Programme",
                                 badge="Escalated", badge_kind="red"))
    d.doc_title("Notice — Human Review Required",
                "The case is escalated to a human officer rather than auto-decided.")
    flags = case.get("fraud_flags", [])
    d.key_value_table([
        ("Case ID", case["case_id"]),
        ("Beneficiary", case["full_name"]),
        ("Status", "Human Review Required"),
        ("Confidence Score", f"{case['confidence_score']:.2f}"),
        ("Officer Queue Priority", "High" if case["confidence_score"] < 0.5 else "Medium"),
        ("Escalation Reason", "Document authenticity / data inconsistency (fraud review)."),
    ])
    if flags:
        d.section("Red Flags Detected")
        rows = [[f["flag"].replace("_", " ").title(), f["detail"]] for f in flags]
        d.simple_table(["Flag", "Detail"], rows, aligns=["left", "left"])
    d.section("Explanation (English)")
    d.paragraph(case["bilingual_summary"]["en"])
    d.section("التوضيح (بالعربية)")
    d.arabic_paragraph(case["bilingual_summary"]["ar"])
    d.finish()


def generate_rejection_or_block_notice(case: dict, path: Path):
    rq = case["active_request"]
    d = DocCanvas(path, meta_for(case, "Request Blocked",
                                 "تم حظر الطلب", "Sheikh Zayed Housing Programme",
                                 badge="Blocked", badge_kind="red"))
    d.doc_title("Notice — Request Blocked / Rejected",
                "An active rescheduling request already exists for this beneficiary.")
    d.key_value_table([
        ("Case ID", case["case_id"]),
        ("Beneficiary", case["full_name"]),
        ("Status", "Blocked / Rejected"),
        ("Reason", "Active request exists"),
        ("Existing Application ID", rq["existing_application_id"]),
        ("Existing Status", rq["status"]),
    ])
    d.callout("Active request exists. New request blocked. No affordability or risk analysis is "
              "performed — there is no point assessing a duplicate.", kind="red",
              title="Decision")
    d.section("Explanation (English)")
    d.paragraph(case["bilingual_summary"]["en"])
    d.section("التوضيح (بالعربية)")
    d.arabic_paragraph(case["bilingual_summary"]["ar"])
    d.finish()


def _policy_row(label: str, pr: dict) -> list[str]:
    extra = ""
    if "proposed_deduction_rate_pct" in pr:
        extra = f"{pr['proposed_deduction_rate_pct']}%"
    return [label, pr["result"], extra, pr["detail"]]


def generate_final_recommendation_memo(case: dict, path: Path):
    status = case["expected_status"]
    fg_kind = {"green": "green", "amber": "amber", "red": "red", "navy": "navy"}
    badge_kind = "green" if "approv" in status.lower() else (
        "red" if ("block" in status.lower() or "reject" in status.lower() or "human review" in status.lower())
        else "amber")
    d = DocCanvas(path, meta_for(case, "Final Recommendation Memo",
                                 "مذكرة التوصية النهائية", "Sheikh Zayed Housing Programme — AI Agent",
                                 badge=status, badge_kind=badge_kind))
    d.doc_title("Final Recommendation Memo",
                "Governed, explainable decision produced by the multi-agent pipeline.")

    pol = case["policy_results"]
    ded = pol["deduction_cap"]
    per = pol["period_constraint"]
    loan = case["loan"]
    inc = case.get("income_statement") or {}
    plan = case.get("proposed_plan", {})

    # --- decision banner -------------------------------------------------
    fg, bg = status_palette(status)
    d.callout(case["expected_recommendation"], kind=badge_kind,
              title=f"Recommendation: {status}")

    # --- case summary ----------------------------------------------------
    d.section("Case Summary")
    d.key_value_table([
        ("Beneficiary", f'{case["full_name"]}  ·  {case["beneficiary_id"]}'),
        ("Scenario", case["scenario"].replace("_", " ").title()),
        ("Application Status", status),
        ("Confidence Score", f"{case['confidence_score']:.2f}"),
        ("Human Review Required", "Yes" if case["human_review_required"] else "No"),
    ])

    # --- financial analysis ---------------------------------------------
    d.section("Income & Affordability Analysis")
    d.key_value_table([
        ("Average Monthly Income (net)",
         aed(inc.get("average_monthly_income")) if inc else "Unknown / under review"),
        ("Arrears Amount", aed(case["arrears"]["arrears_amount"])),
        ("Remaining Loan Balance", aed(loan["remaining_balance"])),
        ("Remaining Repayment Period", f"{loan['remaining_period_months']} months"),
        ("Original Approved Period", f"{loan['original_approved_period_months']} months"),
        ("Proposed Installment",
         aed(plan.get("proposed_installment")) if plan.get("proposed_installment") else "—"),
        ("Proposed Deduction Rate",
         f"{ded.get('proposed_deduction_rate_pct')}%" if ded.get("proposed_deduction_rate_pct") is not None else "Not Applicable"),
        ("Proposed Repayment Plan", plan.get("note") or plan.get("outcome", "—")),
    ])

    # --- governance rule table ------------------------------------------
    d.section("Governance Rule Compliance")
    d.simple_table(
        ["Rule", "Result", "Value", "Basis"],
        [
            _policy_row("20% deduction cap", ded),
            _policy_row("Original period constraint", per),
            _policy_row("Active request validation", pol["active_request"]),
            _policy_row("Document completeness", pol["document_completeness"]),
            _policy_row("Fraud / inconsistency", pol["fraud_inconsistency"]),
        ],
        aligns=["left", "center", "center", "left"], status_col=1)

    # --- reasoning -------------------------------------------------------
    d.section("Reasoning")
    d.paragraph(case["bilingual_summary"]["en"])

    d.section("الملخص والتوصية (بالعربية)")
    d.arabic_paragraph(case["bilingual_summary"]["ar"])

    # --- officer notes ---------------------------------------------------
    d.section("Officer Notes")
    if case["human_review_required"]:
        d.paragraph("Routed to a human officer. Officer to confirm the recommendation, adjust the "
                    "plan if required, and record a final decision. Confidence and red-flag context "
                    "are attached in the audit trail.", color=GRAY)
    else:
        d.paragraph("Straight-through recommendation — no officer action required. Audit trail "
                    "attached for assurance.", color=GRAY)
    d.signature_block("AI Agent — Rationale & Policy Engine",
                      "Recommendation issued automatically")
    d.finish()


def generate_audit_trail_report(case: dict, path: Path):
    d = DocCanvas(path, meta_for(case, "Decision Audit Trail",
                                 "سجل تدقيق القرار", "Sheikh Zayed Housing Programme — AI Agent",
                                 badge="Audit Trail", badge_kind="navy"))
    d.doc_title("Decision Audit Trail Report",
                "Full agent lineage, data sources, rules and calculations — for officers & judges.")

    pol = case["policy_results"]
    d.key_value_table([
        ("Case ID", case["case_id"]),
        ("Beneficiary", case["full_name"]),
        ("Decision Version", "v1.0 (deterministic policy engine)"),
        ("Confidence Score", f"{case['confidence_score']:.2f}"),
        ("Human Review Required", "Yes" if case["human_review_required"] else "No"),
        ("Escalation Reason", _escalation_reason(case)),
        ("Timestamp", case["citizen_profile"]["login_timestamp"]),
    ])

    # --- agent sequence --------------------------------------------------
    d.section("Agent Sequence")
    agents = [
        ("1", "Orchestrator Agent", "Sequences the pipeline, manages state, enforces early exits."),
        ("2", "Risk Forecaster Agent", "Estimates default / re-arrears risk from payment history."),
        ("3", "Document Auditor Agent", "Validates completeness, freshness and authenticity."),
        ("4", "Policy Engine Agent", "Applies the 20% cap, period constraint and active-request rule."),
        ("5", "Rationale Agent", "Produces the bilingual explanation for every decision."),
        ("6", "Legal Clock Agent", "Guards the original approved repayment-period constraint."),
        ("7", "Human Review Agent", "Escalates low-confidence / suspicious / ambiguous cases."),
    ]
    d.simple_table(["#", "Agent", "Responsibility"],
                   [[n, a, r] for n, a, r in agents],
                   aligns=["center", "left", "left"])

    # --- data sources & documents ---------------------------------------
    d.section("Data Sources Used")
    d.paragraph("UAE PASS · MOEI Loan System · Union Bank (income, "
                "obligations, direct debit) · Emirates Employer Services LLC (salary) · Al Etihad Credit Bureau.")

    d.section("Documents Checked")
    docs = case.get("documents", [])
    d.paragraph(", ".join(x.replace("_", " ").title() for x in docs) + ".")

    # --- rule results ----------------------------------------------------
    d.section("Rule Results")
    d.simple_table(
        ["Rule", "Result", "Detail"],
        [
            ["20% deduction cap", pol["deduction_cap"]["result"], pol["deduction_cap"]["detail"]],
            ["Original repayment period", pol["period_constraint"]["result"], pol["period_constraint"]["detail"]],
            ["Active request validation", pol["active_request"]["result"], pol["active_request"]["detail"]],
            ["Document completeness", pol["document_completeness"]["result"], pol["document_completeness"]["detail"]],
            ["Fraud / inconsistency", pol["fraud_inconsistency"]["result"], pol["fraud_inconsistency"]["detail"]],
        ],
        aligns=["left", "center", "left"], status_col=1)

    # --- calculations ----------------------------------------------------
    d.section("Calculations Performed")
    calc_lines = _calculations(case)
    for ln in calc_lines:
        d.paragraph("• " + ln, size=9, gap=0.5 * mm)
    d.y -= 2 * mm

    if case.get("fraud_flags"):
        d.section("Fraud / Inconsistency Findings")
        rows = [[f["flag"].replace("_", " ").title(), f["detail"]] for f in case["fraud_flags"]]
        d.simple_table(["Flag", "Detail"], rows, aligns=["left", "left"])

    d.callout("This audit trail is generated for transparency and assurance. Every decision is "
              "traceable to a rule, a data source and a calculation.",
              kind="navy", title="Explainability statement")
    d.finish()


def _escalation_reason(case: dict) -> str:
    if not case["human_review_required"]:
        return "None — straight-through decision."
    scen = case["scenario"]
    return {
        "unemployment_hardship": "Unstable income (AED 0) — conditional officer review.",
        "medical_hardship": "Medical supporting document is the basis of relief — officer approval recommended.",
        "high_obligations": "Obligation-to-income ratio 65% (>60%) — holistic affordability decision.",
        "suspicious_document": "Document authenticity failures and low confidence (0.46).",
    }.get(scen, "Low confidence / policy ambiguity.")


def _calculations(case: dict) -> list[str]:
    out = []
    inc = case.get("income_statement") or {}
    avg = inc.get("average_monthly_income")
    plan = case.get("proposed_plan", {})
    ded = case["policy_results"]["deduction_cap"]
    loan = case["loan"]
    if avg and plan.get("proposed_installment"):
        rate = plan["proposed_installment"] / avg * 100
        out.append(
            f"Deduction rate = proposed installment / net income = "
            f"{plan['proposed_installment']:,.0f} / {avg:,.0f} = {rate:.1f}% "
            f"(cap 20% → {'PASS' if rate <= 20 else 'FAIL'}).")
    elif ded["result"] == "Not Applicable":
        out.append("Deduction-cap arithmetic not applicable (income unknown/zero or blocked early).")
    out.append(
        f"Period check: remaining {loan['remaining_period_months']} months vs original approved "
        f"{loan['original_approved_period_months']} months → "
        f"{'within limit (PASS)' if loan['remaining_period_months'] <= loan['original_approved_period_months'] else 'EXCEEDS (FAIL)'}.")
    out.append(
        f"Arrears coverage: {aed(case['arrears']['arrears_amount'])} across "
        f"{case['arrears']['unpaid_installments']} unpaid installments "
        f"({case['arrears']['days_past_due']} days past due).")
    o = case.get("obligations")
    if o and o.get("obligation_to_income_ratio_pct") is not None:
        out.append(
            f"Obligation-to-income ratio = total obligations / income = "
            f"{o['total_monthly_obligations']:,.0f} / {avg:,.0f} = "
            f"{o['obligation_to_income_ratio_pct']}% "
            f"({'> 60% threshold' if o['obligation_to_income_ratio_pct'] >= 60 else 'within range'}).")
    return out


# ===========================================================================
# DISPATCH — map a document key to its generator for a given case
# ===========================================================================
def build_document(case: dict, doc_key: str, path: Path):
    dispatch = {
        "uae_pass_profile": generate_uae_pass_profile,
        "application_form": generate_application_form,
        "salary_certificate": lambda c, p: generate_salary_certificate(c, p, suspicious=False),
        "suspicious_salary_certificate": lambda c, p: generate_salary_certificate(c, p, suspicious=True),
        "income_statement": lambda c, p: generate_income_statement(c, p),
        "last_income_statement": lambda c, p: generate_income_statement(
            c, p, label_override="Last Income Statement (pre-separation)"),
        "income_statement_mismatch": lambda c, p: generate_income_statement(c, p, mismatch=True),
        "obligations_letter": generate_obligations_letter,
        "direct_debit_proof": generate_direct_debit_proof,
        "moei_loan_statement": generate_moei_loan_statement,
        "arrears_statement": generate_arrears_statement,
        "payment_history": generate_payment_history,
        "active_request_record": generate_active_request_record,
        "medical_treatment_letter": generate_medical_treatment_letter,
        "unemployment_letter": generate_unemployment_letter,
        "family_status_record": generate_family_status_record,
        "missing_documents_notice": generate_missing_documents_notice,
        "human_review_notice": generate_human_review_notice,
        "rejection_or_block_notice": generate_rejection_or_block_notice,
        "final_recommendation_memo": generate_final_recommendation_memo,
        "audit_trail_report": generate_audit_trail_report,
    }
    fn = dispatch.get(doc_key)
    if fn is None:
        raise KeyError(f"No generator for document key '{doc_key}'")
    fn(case, path)


# ===========================================================================
# ORCHESTRATION
# ===========================================================================
def load_cases() -> dict:
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def generate_case(case: dict) -> list[str]:
    folder = OUT_ROOT / case["folder"]
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    for doc_key in case["documents"]:
        path = folder / f"{doc_key}.pdf"
        build_document(case, doc_key, path)
        written.append(str(path.relative_to(ROOT).as_posix()))
    return written


def write_document_index(data: dict, generated: dict[str, list[str]]):
    index = {}
    for case in data["cases"]:
        cid = case["case_id"]
        index[cid] = {
            "name": case["full_name"],
            "name_ar": case.get("full_name_ar", ""),
            "scenario": case["scenario"],
            "expected_status": case["expected_status"],
            "expected_recommendation": case["expected_recommendation"],
            "confidence_score": case["confidence_score"],
            "human_review_required": case["human_review_required"],
            "folder": f"demo_documents/{case['folder']}",
            "documents": [
                {"key": k, "file": f"{k}.pdf",
                 "path": f"demo_documents/{case['folder']}/{k}.pdf"}
                for k in case["documents"]
            ],
        }
    payload = {
        "_meta": {
            "disclaimer": data["_meta"]["disclaimer"],
            "policy_rules": data["_meta"]["policy_rules"],
            "generated_count": sum(len(v) for v in generated.values()),
        },
        "cases": index,
    }
    INDEX_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")


def write_readme(data: dict, generated: dict[str, list[str]]):
    lines = []
    A = lines.append
    A("# Document Pack")
    A("")
    A("> Beneficiary document pack for the MOEI / Sheikh Zayed Housing Programme")
    A("> *AI Agent for Housing Loan Arrears Rescheduling*. All beneficiary records,")
    A("> identifiers and references in these PDFs are fictional and created for this")
    A("> prototype; entity names (employer, bank, clinic) are generic placeholders.")
    A("")
    A("## How to regenerate")
    A("")
    A("```bash")
    A("python scripts/generate_demo_documents.py            # all cases")
    A("python scripts/generate_demo_documents.py --case SZHP-1001")
    A("python scripts/generate_demo_documents.py --list     # list cases")
    A("```")
    A("")
    A("Regenerating overwrites the files in place. Generation is deterministic — no randomness,")
    A("no network, no system clock is used for content (all dates live in `data/demo_cases.json`).")
    A("")
    A("Dependencies: `reportlab` (required), plus `arabic-reshaper` + `python-bidi` for Arabic")
    A("rendering (English still renders if they are absent).")
    A("")
    A("## Using these in the portal")
    A("")
    A("In the running portal, each beneficiary uploads documents in the **\"2 · Documents\"**")
    A("step. Upload the matching PDFs from the folder below, then run the assessment to see")
    A("the agent's decision.")
    A("")
    A("## Scenarios & expected results")
    A("")
    A("| Case ID | Beneficiary | Scenario | Expected status | Confidence | Human review |")
    A("|---|---|---|---|---|---|")
    for case in data["cases"]:
        A(f"| {case['case_id']} | {case['full_name']} | {case['scenario']} | "
          f"{case['expected_status']} | {case['confidence_score']:.2f} | "
          f"{'Yes' if case['human_review_required'] else 'No'} |")
    A("")
    A("### What each scenario demonstrates")
    A("")
    demos = {
        "SZHP-1001": "**Clean approval** — complete docs, stable income, 18.1% deduction (under the 20% cap), within the original period → straight-through approval. *Show: salary certificate, MOEI loan statement, **final recommendation memo**, **audit trail**.*",
        "SZHP-1002": "**Missing documents** — salary certificate, income statement and obligations letter absent → *Additional Information Required* with a deadline, no escalation. *Show: missing-documents notice, audit trail.*",
        "SZHP-1003": "**Unemployment hardship** — verified job loss, AED 0 income, 4 dependents → defer arrears / hold installment; conditional officer review. *Show: unemployment letter, family status, memo.*",
        "SZHP-1004": "**Medical hardship** — documented 6-month treatment abroad → temporary hardship plan, hold installment, reassess; officer approval recommended. *Show: medical letter, memo.*",
        "SZHP-1005": "**High obligations** — 65% obligation-to-income ratio → maintain installment, refer to officer (don't aggressively raise). *Show: obligations letter, memo, audit trail.*",
        "SZHP-1006": "**Active request conflict** — an active application (APP-2026-4412) is under review → blocked/rejected, no analysis. *Show: active-request record, block notice.*",
        "SZHP-1007": "**Suspicious document** — salary mismatch, missing reference/QR, stale issue date, employer & Emirates-ID mismatch → human review, low confidence (0.46). *Show: suspicious salary certificate, income mismatch, **human review notice**, audit trail.*",
    }
    for cid, text in demos.items():
        A(f"- **{cid}** — {text}")
    A("")
    A("## How this supports the AI-Agent challenge rubric")
    A("")
    rubric = [
        ("Autonomous data retrieval", "UAE PASS profile, MOEI loan/arrears, bank income & obligations are pulled in automatically."),
        ("Document validation", "Document checklist, freshness, and authenticity checks (see suspicious case)."),
        ("20% policy enforcement", "Deduction-cap rule shown and computed in every memo & audit trail."),
        ("Original period constraint", "Legal Clock agent guards the original approved repayment period."),
        ("Active request validation", "Noura's case is blocked on an existing active application."),
        ("Audit trail", "Per-case audit report with agent lineage, rule results, and calculations."),
        ("Confidence scoring", "Every case carries a 0–1 confidence score driving escalation."),
        ("Human escalation", "Low-confidence / suspicious / ambiguous cases route to an officer."),
        ("Explainability", "Bilingual (EN + AR) reasoning on every decision document."),
        ("Proactive / fraud detection (bonus)", "Five concrete red flags surfaced in Omar's case."),
    ]
    for k, v in rubric:
        A(f"- **{k}** — {v}")
    A("")
    A("## Generated files")
    A("")
    total = sum(len(v) for v in generated.values())
    A(f"Total: **{total}** PDFs across **{len(generated)}** cases. See `document_index.json` for the")
    A("machine-readable map of case → documents.")
    A("")
    for case in data["cases"]:
        A(f"- `{case['folder']}/` — {len(case['documents'])} documents ({case['full_name']})")
    A("")
    README_FILE.write_text("\n".join(lines), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate the beneficiary document pack.")
    parser.add_argument("--case", help="Generate a single case by ID (e.g. SZHP-1001).")
    parser.add_argument("--list", action="store_true", help="List cases and exit.")
    args = parser.parse_args(argv)

    data = load_cases()
    cases = data["cases"]

    if args.list:
        print("Available cases:")
        for c in cases:
            print(f"  {c['case_id']}  {c['full_name']:<22} {c['scenario']:<22} "
                  f"-> {c['expected_status']}")
        return 0

    OUT_ROOT.mkdir(parents=True, exist_ok=True)

    selected = cases
    if args.case:
        selected = [c for c in cases if c["case_id"].lower() == args.case.lower()]
        if not selected:
            print(f"No case with ID {args.case!r}. Use --list to see options.", file=sys.stderr)
            return 1

    if not ARABIC_OK:
        print("⚠  arabic-reshaper / python-bidi not installed — Arabic text will be a placeholder.\n"
              "    Install with: python -m pip install arabic-reshaper python-bidi\n")

    generated: dict[str, list[str]] = {}
    for case in selected:
        files = generate_case(case)
        generated[case["case_id"]] = files

    # index + README always reflect the full pack (use full data set)
    if not args.case:
        write_document_index(data, generated)
        write_readme(data, generated)

    # --- success summary -------------------------------------------------
    print("\n" + "=" * 64)
    print(" DOCUMENT PACK — GENERATION SUMMARY")
    print("=" * 64)
    total = 0
    for case in selected:
        cid = case["case_id"]
        n = len(generated[cid])
        total += n
        print(f"  ✓ {cid}  {case['full_name']:<22} {n:>2} docs  [{case['scenario']}]")
    print("-" * 64)
    print(f"  TOTAL: {total} PDFs across {len(selected)} case(s)")
    print(f"  Output: {OUT_ROOT.relative_to(ROOT).as_posix()}/")
    if not args.case:
        print(f"  Index : {INDEX_FILE.relative_to(ROOT).as_posix()}")
        print(f"  README: {README_FILE.relative_to(ROOT).as_posix()}")
    print("=" * 64 + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
