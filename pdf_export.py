"""
Turns a research paper (Markdown text produced by the LLM) into a PDF.

Uses ReportLab, which is pure Python (pip install reportlab) and works
on Windows, macOS and Linux without extra system libraries.
"""

import io
import os
import re
from datetime import datetime
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    HRFlowable,
    ListFlowable,
    ListItem,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
)


# ---------------------------------------------------------
# Fonts
#
# ReportLab's built-in Helvetica only supports Western
# European characters. If a Unicode TrueType font is found
# on the machine (Arial on Windows, DejaVu on Linux, ...)
# it is used so that other characters are not lost.
# ---------------------------------------------------------

_FONT_CANDIDATES = [
    # (regular, bold, italic, bold-italic)
    (
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/ariali.ttf",
        "C:/Windows/Fonts/arialbi.ttf",
    ),
    (
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Oblique.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-BoldOblique.ttf",
    ),
    (
        "/Library/Fonts/Arial.ttf",
        "/Library/Fonts/Arial Bold.ttf",
        "/Library/Fonts/Arial Italic.ttf",
        "/Library/Fonts/Arial Bold Italic.ttf",
    ),
]

_FONT_FAMILY = None  # (name, is_unicode)


def _get_font_family():
    global _FONT_FAMILY

    if _FONT_FAMILY is not None:
        return _FONT_FAMILY

    for regular, bold, italic, bold_italic in _FONT_CANDIDATES:
        if all(os.path.exists(p) for p in (regular, bold, italic, bold_italic)):
            try:
                pdfmetrics.registerFont(TTFont("ResearchFont", regular))
                pdfmetrics.registerFont(TTFont("ResearchFont-Bold", bold))
                pdfmetrics.registerFont(TTFont("ResearchFont-Italic", italic))
                pdfmetrics.registerFont(
                    TTFont("ResearchFont-BoldItalic", bold_italic)
                )
                pdfmetrics.registerFontFamily(
                    "ResearchFont",
                    normal="ResearchFont",
                    bold="ResearchFont-Bold",
                    italic="ResearchFont-Italic",
                    boldItalic="ResearchFont-BoldItalic",
                )
                _FONT_FAMILY = ("ResearchFont", True)
                return _FONT_FAMILY
            except Exception:
                continue

    _FONT_FAMILY = ("Helvetica", False)
    return _FONT_FAMILY


def _clean(text, unicode_ok):
    """Normalise text so the chosen font can draw every character."""

    text = str(text or "").replace("\r\n", "\n").replace("\r", "\n")

    # Zero-width / control characters that render as black boxes.
    text = re.sub(r"[\u200b\u200c\u200d\ufeff]", "", text)
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)

    if unicode_ok:
        # Replace characters the font has no glyph for (e.g. Chinese
        # in Arial/DejaVu) with "?" instead of drawing empty boxes.
        try:
            glyphs = pdfmetrics.getFont("ResearchFont").face.charToGlyph
            text = "".join(
                ch if (ch in "\n\t " or ord(ch) in glyphs) else "?"
                for ch in text
            )
        except Exception:
            pass
    else:
        # Built-in Helvetica uses cp1252; replace anything outside it.
        text = text.replace("\u2011", "-").replace("\u2212", "-")
        text = text.encode("cp1252", errors="replace").decode("cp1252")

    return text


# ---------------------------------------------------------
# Inline Markdown -> ReportLab mini-markup
# ---------------------------------------------------------

def _inline(text):
    # Escape first so that "<", ">" and "&" in the AI text can never
    # break the PDF markup. Our own tags are added afterwards.
    text = escape(text)

    text = re.sub(
        r"\[([^\]]+)\]\((https?://[^)\s]+)\)",
        r'<link href="\2" color="#1a5fb4">\1</link>',
        text,
    )
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"`([^`\n]+)`", r'<font face="Courier">\1</font>', text)

    return text


# ---------------------------------------------------------
# Block level Markdown -> flowables
# ---------------------------------------------------------

_HEADING = re.compile(r"^\s{0,3}(#{1,6})\s+(.*?)\s*#*\s*$")
_BULLET = re.compile(r"^\s*[-*\u2022]\s+(.*)$")
_NUMBERED = re.compile(r"^\s*\d+[.)]\s+(.*)$")
_RULE = re.compile(r"^\s*([-*_])(\s*\1){2,}\s*$")


def _markdown_to_flowables(text, styles):
    flowables = []
    paragraph = []
    list_items = []
    list_kind = None

    def flush_paragraph():
        if paragraph:
            flowables.append(
                Paragraph(_inline(" ".join(paragraph)), styles["body"])
            )
            paragraph.clear()

    def flush_list():
        nonlocal list_kind
        if list_items:
            flowables.append(
                ListFlowable(
                    [
                        ListItem(Paragraph(_inline(item), styles["body"]))
                        for item in list_items
                    ],
                    bulletType="bullet" if list_kind == "bullet" else "1",
                    bulletFontName=styles["body"].fontName,
                    bulletFontSize=9,
                    leftIndent=16,
                    start="\u2022" if list_kind == "bullet" else None,
                    **({} if list_kind == "bullet" else {"bulletFormat": "%s."}),
                )
            )
            flowables.append(Spacer(1, 4))
            list_items.clear()
        list_kind = None

    for raw_line in text.split("\n"):
        line = raw_line.rstrip()

        if not line.strip():
            flush_paragraph()
            flush_list()
            continue

        if _RULE.match(line):
            flush_paragraph()
            flush_list()
            flowables.append(
                HRFlowable(width="100%", thickness=0.5, color=colors.lightgrey)
            )
            continue

        heading = _HEADING.match(line)
        if heading:
            flush_paragraph()
            flush_list()
            level = min(len(heading.group(1)), 3)
            flowables.append(
                Paragraph(_inline(heading.group(2)), styles[f"h{level}"])
            )
            continue

        bullet = _BULLET.match(line)
        numbered = None if bullet else _NUMBERED.match(line)

        if bullet or numbered:
            flush_paragraph()
            kind = "bullet" if bullet else "number"
            if list_kind and list_kind != kind:
                flush_list()
            list_kind = kind
            list_items.append((bullet or numbered).group(1))
            continue

        # Indented continuation of a list item
        if list_items and raw_line.startswith((" ", "\t")):
            list_items[-1] += " " + line.strip()
            continue

        flush_list()
        paragraph.append(line.strip())

    flush_paragraph()
    flush_list()

    return flowables


# ---------------------------------------------------------
# Public function
# ---------------------------------------------------------

def build_pdf(topic, content, sources=None, tools_used=None,
              version_label="", model=""):
    """
    Build a PDF and return it as bytes.
    """

    font, unicode_ok = _get_font_family()
    bold = f"{font}-Bold" if unicode_ok else "Helvetica-Bold"

    ink = colors.HexColor("#38321c")
    accent = colors.HexColor("#8c5027")
    muted = colors.HexColor("#665f45")

    styles = {
        "title": ParagraphStyle(
            "title", fontName=bold, fontSize=22, leading=28,
            textColor=ink, spaceAfter=6,
        ),
        "meta": ParagraphStyle(
            "meta", fontName=font, fontSize=9, leading=13,
            textColor=muted, spaceAfter=2,
        ),
        "h1": ParagraphStyle(
            "h1", fontName=bold, fontSize=16, leading=21,
            textColor=accent, spaceBefore=16, spaceAfter=6,
        ),
        "h2": ParagraphStyle(
            "h2", fontName=bold, fontSize=13, leading=18,
            textColor=ink, spaceBefore=12, spaceAfter=4,
        ),
        "h3": ParagraphStyle(
            "h3", fontName=bold, fontSize=11, leading=15,
            textColor=ink, spaceBefore=10, spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "body", fontName=font, fontSize=10.5, leading=15.5,
            textColor=ink, spaceAfter=7, alignment=TA_JUSTIFY,
        ),
        "source": ParagraphStyle(
            "source", fontName=font, fontSize=8.5, leading=12,
            textColor=muted, spaceAfter=2, wordWrap="CJK",
        ),
    }

    topic = _clean(topic, unicode_ok).strip() or "Research Report"
    content = _clean(content, unicode_ok)

    story = [
        Paragraph(_inline(topic), styles["title"]),
    ]

    meta_parts = []
    if version_label:
        meta_parts.append(_clean(version_label, unicode_ok))
    if model:
        meta_parts.append("Model: " + _clean(model, unicode_ok))
    meta_parts.append(datetime.now().strftime("Generated %Y-%m-%d %H:%M"))

    story.append(Paragraph(escape("  |  ".join(meta_parts)), styles["meta"]))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1, color=accent))
    story.append(Spacer(1, 6))

    story.extend(_markdown_to_flowables(content, styles))

    # Sources and tools
    sources = [s for s in (sources or []) if isinstance(s, str) and s.strip()]
    tools_used = [t for t in (tools_used or []) if isinstance(t, str) and t.strip()]

    if sources:
        story.append(Paragraph("Sources", styles["h1"]))
        for number, url in enumerate(sources, start=1):
            safe = escape(_clean(url.strip(), unicode_ok))
            if url.strip().startswith(("http://", "https://")):
                text = f'{number}. <link href="{safe}" color="#1a5fb4">{safe}</link>'
            else:
                text = f"{number}. {safe}"
            story.append(Paragraph(text, styles["source"]))

    if tools_used:
        story.append(Paragraph("Tools used", styles["h2"]))
        story.append(
            Paragraph(
                escape(", ".join(_clean(t, unicode_ok) for t in tools_used)),
                styles["source"],
            )
        )

    story.append(Spacer(1, 10))
    story.append(
        Paragraph(
            "<i>AI-generated content. Verify important claims against the "
            "listed sources before relying on them.</i>",
            styles["meta"],
        )
    )

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont(font, 8)
        canvas.setFillColor(muted)
        canvas.drawString(20 * mm, 10 * mm, "Research AI")
        canvas.drawRightString(A4[0] - 20 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=18 * mm,
        bottomMargin=20 * mm,
        title=topic[:200],
        author="Research AI",
    )

    doc.build(story, onFirstPage=footer, onLaterPages=footer)

    return buffer.getvalue()