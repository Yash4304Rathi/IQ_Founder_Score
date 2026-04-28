"""PDF export for IQ Founder Score reports."""

from __future__ import annotations

import io
import re
from datetime import datetime, timezone
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Brand colours ──────────────────────────────────────────────────────────────
ACCENT      = colors.HexColor("#D4720A")
ACCENT_LIGHT= colors.HexColor("#FEF3E8")
TEXT        = colors.HexColor("#111111")
TEXT_MUTED  = colors.HexColor("#717171")
SURFACE     = colors.HexColor("#F7F6F4")
BORDER      = colors.HexColor("#E5E3DF")
WHITE       = colors.white
GREEN       = colors.HexColor("#166534")
GREEN_BG    = colors.HexColor("#EDFAF2")
RED         = colors.HexColor("#991B1B")
RED_BG      = colors.HexColor("#FFF1F1")
YELLOW      = colors.HexColor("#854D0E")
YELLOW_BG   = colors.HexColor("#FEFCE8")

PAGE_W, PAGE_H = A4
MARGIN = 18 * mm


def _styles():
    base = getSampleStyleSheet()
    S = {}

    def add(name, **kw):
        S[name] = ParagraphStyle(name, **kw)

    add("wordmark",
        fontName="Helvetica-Bold", fontSize=7, textColor=WHITE,
        leading=10, spaceAfter=0)
    add("title",
        fontName="Helvetica-Bold", fontSize=22, textColor=TEXT,
        leading=26, spaceAfter=2)
    add("subtitle",
        fontName="Helvetica", fontSize=9, textColor=TEXT_MUTED,
        leading=13, spaceAfter=0)
    add("section_label",
        fontName="Helvetica-Bold", fontSize=7, textColor=TEXT_MUTED,
        leading=10, spaceAfter=4, spaceBefore=14,
        textTransform="uppercase", letterSpacing=1.4)
    add("body",
        fontName="Helvetica", fontSize=9, textColor=TEXT,
        leading=14, spaceAfter=0)
    add("body_bold",
        fontName="Helvetica-Bold", fontSize=9, textColor=TEXT,
        leading=14, spaceAfter=0)
    add("score_num",
        fontName="Helvetica-Bold", fontSize=36, textColor=WHITE,
        leading=40, alignment=TA_CENTER)
    add("score_denom",
        fontName="Helvetica", fontSize=8, textColor=WHITE,
        leading=10, alignment=TA_CENTER)
    add("tier_label",
        fontName="Helvetica-Bold", fontSize=10, textColor=TEXT,
        leading=14)
    add("one_liner",
        fontName="Helvetica-Oblique", fontSize=9, textColor=TEXT_MUTED,
        leading=14, leftIndent=8, borderPadding=(0, 0, 0, 6))
    add("analyst_note",
        fontName="Helvetica", fontSize=9, textColor=TEXT,
        leading=14, leftIndent=10)
    add("bullet",
        fontName="Helvetica", fontSize=9, textColor=TEXT,
        leading=13, leftIndent=10, firstLineIndent=-6, spaceAfter=2)
    add("dim_label",
        fontName="Helvetica-Bold", fontSize=8, textColor=TEXT,
        leading=11)
    add("dim_reason",
        fontName="Helvetica", fontSize=7.5, textColor=TEXT_MUTED,
        leading=11)
    add("footer",
        fontName="Helvetica", fontSize=7, textColor=TEXT_MUTED,
        leading=10, alignment=TA_CENTER)
    add("url",
        fontName="Helvetica", fontSize=8, textColor=ACCENT,
        leading=11)
    return S


def _hr(width=None):
    return HRFlowable(
        width=width or "100%", thickness=0.5,
        color=BORDER, spaceAfter=8, spaceBefore=4
    )


def _pill_text(label: str, modifier: str = "None") -> str:
    """Return a coloured inline pill using reportlab markup."""
    colour_map = {
        "IQ Fast-Track": "#166534",
        "Strong Fit":    "#166534",
        "Watchlist":     "#854D0E",
        "Pass for Now":  "#991B1B",
        "Not a Fit":     "#991B1B",
        "Wildcard":      "#166534",
        "Red Flag":      "#991B1B",
    }
    c = colour_map.get(label, "#717171")
    return f'<font color="{c}"><b>{label}</b></font>'


def _safe(text) -> str:
    if not text:
        return ""
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def generate_pdf(run: dict) -> bytes:
    """Render a full IQ Founder Score report to PDF bytes."""
    result   = run.get("result") or {}
    profile  = run.get("profile") or {}
    match    = run.get("match") or {}

    founder  = _safe(run.get("founder_name", "Unknown Founder"))
    company  = _safe(run.get("company_name", ""))
    url      = run.get("linkedin_url", "")
    ts       = datetime.now(timezone.utc).strftime("%d %b %Y")

    total    = result.get("total_score", 0)
    tier     = result.get("tier", "—")
    modifier = result.get("modifier", "None")
    mod_pts  = result.get("modifier_points", 0)
    summary  = _safe(result.get("summary", ""))
    one_liner= _safe(result.get("one_line_signal", ""))
    note     = _safe(result.get("iq_analyst_note", ""))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN,  bottomMargin=MARGIN,
        title=f"IQ Founder Score — {founder}",
        author="India Quotient",
    )

    S = _styles()
    story = []

    # ── Header bar ─────────────────────────────────────────────────────────────
    badge_cell = Paragraph("IQ", S["wordmark"])
    badge_tbl  = Table([[badge_cell]], colWidths=[14*mm], rowHeights=[10*mm])
    badge_tbl.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), ACCENT),
        ("ALIGN",      (0,0), (-1,-1), "CENTER"),
        ("VALIGN",     (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING",(0,0), (-1,-1), 4),
        ("RIGHTPADDING",(0,0),(-1,-1), 4),
    ]))

    header_label = Paragraph(
        "INDIA QUOTIENT · INTERNAL TOOL",
        ParagraphStyle("hl", fontName="Helvetica-Bold", fontSize=6.5,
                       textColor=TEXT_MUTED, leading=9, letterSpacing=1.2)
    )
    date_p = Paragraph(ts, ParagraphStyle("dp", fontName="Helvetica", fontSize=8,
                                          textColor=TEXT_MUTED, leading=10,
                                          alignment=TA_RIGHT))

    content_w = PAGE_W - 2 * MARGIN
    hdr_tbl = Table(
        [[badge_tbl, header_label, date_p]],
        colWidths=[18*mm, content_w - 18*mm - 30*mm, 30*mm],
    )
    hdr_tbl.setStyle(TableStyle([
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
    ]))
    story.append(hdr_tbl)
    story.append(Spacer(1, 5*mm))
    story.append(_hr())

    # ── Title ──────────────────────────────────────────────────────────────────
    story.append(Paragraph(f"Founder Score Report", S["title"]))
    title_detail = f"{founder}"
    if company:
        title_detail += f" · {company}"
    story.append(Paragraph(title_detail, S["subtitle"]))
    if url:
        story.append(Paragraph(
            f'<a href="{url}" color="#D4720A">{url}</a>', S["url"]
        ))
    story.append(Spacer(1, 5*mm))
    story.append(_hr())

    # ── Score + Tier + Summary ─────────────────────────────────────────────────
    # Score badge (coloured box)
    score_inner = Table(
        [[Paragraph(str(total), S["score_num"])],
         [Paragraph("out of 100", S["score_denom"])]],
        colWidths=[28*mm],
    )
    score_inner.setStyle(TableStyle([
        ("ALIGN",       (0,0),(-1,-1), "CENTER"),
        ("VALIGN",      (0,0),(-1,-1), "MIDDLE"),
        ("TOPPADDING",  (0,0),(-1,-1), 4),
        ("BOTTOMPADDING",(0,0),(-1,-1), 4),
    ]))
    score_badge = Table([[score_inner]], colWidths=[32*mm], rowHeights=[22*mm])
    score_badge.setStyle(TableStyle([
        ("BACKGROUND",   (0,0),(-1,-1), ACCENT),
        ("ALIGN",        (0,0),(-1,-1), "CENTER"),
        ("VALIGN",       (0,0),(-1,-1), "MIDDLE"),
        ("ROUNDEDCORNERS", (0,0),(-1,-1), [3]),
    ]))

    # Tier cell
    tier_color_map = {
        "IQ Fast-Track": GREEN,
        "Strong Fit":    GREEN,
        "Watchlist":     YELLOW,
        "Pass for Now":  RED,
        "Not a Fit":     RED,
    }
    tier_c = tier_color_map.get(tier, TEXT_MUTED)
    mod_label = (
        f"{'+ ' if mod_pts > 0 else ''}{mod_pts} {modifier}"
        if modifier != "None"
        else "No modifier"
    )
    mod_c = GREEN if modifier == "Wildcard" else (RED if modifier == "Red Flag" else TEXT_MUTED)

    tier_content = [
        Paragraph("TIER", S["section_label"]),
        Paragraph(
            f'<font color="{tier_c.hexval() if hasattr(tier_c,"hexval") else "#111"}">'
            f'<b>{_safe(tier)}</b></font>',
            S["tier_label"]
        ),
        Spacer(1, 3),
        Paragraph(
            f'<font color="{mod_c.hexval() if hasattr(mod_c,"hexval") else "#717171"}">{_safe(mod_label)}</font>',
            S["body"]
        ),
    ]
    if result.get("modifier_reasoning"):
        tier_content.append(Paragraph(_safe(result["modifier_reasoning"]), S["dim_reason"]))

    tier_cell = tier_content

    # Summary cell
    sum_content = [
        Paragraph("SUMMARY", S["section_label"]),
        Paragraph(summary, S["body"]),
    ]
    if one_liner:
        sum_content += [
            Spacer(1, 4),
            Paragraph(f'"{one_liner}"', S["one_liner"]),
        ]

    cw = content_w
    top_tbl = Table(
        [[score_badge, tier_cell, sum_content]],
        colWidths=[36*mm, 44*mm, cw - 36*mm - 44*mm],
        spaceBefore=0,
    )
    top_tbl.setStyle(TableStyle([
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(-1,-1), 8),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
    ]))
    story.append(top_tbl)
    story.append(Spacer(1, 5*mm))
    story.append(_hr())

    # ── IQ Analyst Note ────────────────────────────────────────────────────────
    if note:
        story.append(Paragraph("IQ ANALYST NOTE", S["section_label"]))
        note_tbl = Table(
            [[Paragraph(note, S["analyst_note"])]],
            colWidths=[cw],
        )
        note_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), SURFACE),
            ("LINEAFTER",     (0,0),(0,-1),  0, WHITE),
            ("LINEBEFORE",    (0,0),(0,-1),  3, ACCENT),
            ("TOPPADDING",    (0,0),(-1,-1), 8),
            ("BOTTOMPADDING", (0,0),(-1,-1), 8),
            ("LEFTPADDING",   (0,0),(-1,-1), 10),
            ("RIGHTPADDING",  (0,0),(-1,-1), 10),
            ("BOX",           (0,0),(-1,-1), 0.5, BORDER),
        ]))
        story.append(note_tbl)
        story.append(Spacer(1, 5*mm))
        story.append(_hr())

    # ── Dimension Breakdown ────────────────────────────────────────────────────
    story.append(Paragraph("DIMENSION BREAKDOWN", S["section_label"]))

    DIMS = [
        ("Founder / Operator",  "founder_operator_experience", 25),
        ("Education",           "educational_pedigree",        20),
        ("Elite Employer",      "elite_employer_signal",       20),
        ("Trajectory",          "trajectory_progression",      10),
        ("Domain Depth",        "domain_depth",                10),
        ("Network",             "network_ecosystem",           10),
        ("Communication",       "communication_quality",        5),
    ]

    dim_rows = []
    for label, key, max_pts in DIMS:
        d     = result.get(key) or {}
        score = d.get("score", 0)
        rsn   = _safe(d.get("reasoning", ""))
        frac  = score / max_pts if max_pts else 0
        bar_c = GREEN if frac >= 0.75 else (YELLOW if frac >= 0.45 else RED)

        bar_w     = 28 * mm
        filled_w  = bar_w * frac
        empty_w   = bar_w - filled_w

        bar_data  = [[""]]
        bar_tbl   = Table(bar_data, colWidths=[bar_w], rowHeights=[4])
        bar_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), BORDER),
            ("TOPPADDING",    (0,0),(-1,-1), 0),
            ("BOTTOMPADDING", (0,0),(-1,-1), 0),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ]))
        filled_tbl = Table([[""]], colWidths=[max(filled_w, 0.1)], rowHeights=[4])
        filled_tbl.setStyle(TableStyle([
            ("BACKGROUND",    (0,0),(-1,-1), bar_c),
            ("TOPPADDING",    (0,0),(-1,-1), 0),
            ("BOTTOMPADDING", (0,0),(-1,-1), 0),
            ("LEFTPADDING",   (0,0),(-1,-1), 0),
            ("RIGHTPADDING",  (0,0),(-1,-1), 0),
        ]))

        label_p  = Paragraph(f"<b>{_safe(label)}</b>", S["dim_label"])
        score_p  = Paragraph(f"<b>{score}/{max_pts}</b>", S["dim_label"])
        reason_p = Paragraph(rsn, S["dim_reason"])

        dim_rows.append([label_p, score_p, reason_p])

    dim_tbl = Table(
        dim_rows,
        colWidths=[36*mm, 16*mm, cw - 52*mm],
        spaceBefore=2,
    )
    dim_tbl.setStyle(TableStyle([
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("TOPPADDING",   (0,0),(-1,-1), 5),
        ("BOTTOMPADDING",(0,0),(-1,-1), 5),
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(-1,-1), 6),
        ("LINEBELOW",    (0,0),(-1,-2), 0.4, BORDER),
        ("BACKGROUND",   (0,0),(-1,-1), WHITE),
        ("ROWBACKGROUNDS",(0,0),(-1,-1), [WHITE, SURFACE]),
    ]))
    story.append(dim_tbl)
    story.append(Spacer(1, 5*mm))
    story.append(_hr())

    # ── Strengths + Concerns ───────────────────────────────────────────────────
    def _bullet_list(items, dot_color=ACCENT):
        paras = []
        for item in items or []:
            paras.append(Paragraph(
                f'<font color="{dot_color.hexval() if hasattr(dot_color,"hexval") else "#D4720A"}">▪</font>  {_safe(item)}',
                S["bullet"]
            ))
        return paras or [Paragraph("—", S["body"])]

    str_items = _bullet_list(result.get("strengths"), ACCENT)
    con_items = _bullet_list(result.get("concerns"), RED)

    sc_tbl = Table(
        [[
            [Paragraph("STRENGTHS", S["section_label"])] + str_items,
            [Paragraph("CONCERNS",  S["section_label"])] + con_items,
        ]],
        colWidths=[cw/2 - 4*mm, cw/2 - 4*mm],
        spaceBefore=0,
    )
    sc_tbl.setStyle(TableStyle([
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(0,-1),  8),
        ("RIGHTPADDING", (1,0),(1,-1),  0),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
    ]))
    story.append(sc_tbl)
    story.append(Spacer(1, 5*mm))
    story.append(_hr())

    # ── Missing Info + Diligence Questions ─────────────────────────────────────
    mis_items = _bullet_list(result.get("missing_information"), TEXT_MUTED)
    dil_items = []
    for i, q in enumerate(result.get("next_questions_for_diligence") or [], 1):
        dil_items.append(Paragraph(
            f'<font color="#D4720A"><b>{i}.</b></font>  {_safe(q)}',
            S["bullet"]
        ))
    if not dil_items:
        dil_items = [Paragraph("—", S["body"])]

    md_tbl = Table(
        [[
            [Paragraph("MISSING INFORMATION", S["section_label"])] + mis_items,
            [Paragraph("DILIGENCE QUESTIONS", S["section_label"])] + dil_items,
        ]],
        colWidths=[cw/2 - 4*mm, cw/2 - 4*mm],
        spaceBefore=0,
    )
    md_tbl.setStyle(TableStyle([
        ("VALIGN",       (0,0),(-1,-1), "TOP"),
        ("LEFTPADDING",  (0,0),(-1,-1), 0),
        ("RIGHTPADDING", (0,0),(0,-1),  8),
        ("RIGHTPADDING", (1,0),(1,-1),  0),
        ("TOPPADDING",   (0,0),(-1,-1), 0),
        ("BOTTOMPADDING",(0,0),(-1,-1), 0),
    ]))
    story.append(md_tbl)
    story.append(Spacer(1, 8*mm))
    story.append(_hr())

    # ── Footer ─────────────────────────────────────────────────────────────────
    conf = match.get("match_confidence", "")
    footer_text = (
        f"Generated by IQ Founder Score · {ts}  |  "
        f"Profile confidence: {conf}  |  "
        f"Source: {run.get('url_source', '')}  |  "
        f"Internal use only — India Quotient"
    )
    story.append(Paragraph(footer_text, S["footer"]))

    doc.build(story)
    return buf.getvalue()


def report_filename(founder_name: str, company_name: str) -> str:
    def slug(s: str) -> str:
        s = (s or "").strip()
        s = re.sub(r"[^\w\s-]", "", s)
        s = re.sub(r"[\s-]+", "_", s)
        return s.lower()

    parts = [p for p in [slug(founder_name), slug(company_name)] if p]
    parts.append("evaluation")
    return "_".join(parts) + ".pdf"
