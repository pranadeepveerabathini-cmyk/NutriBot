"""
NutriBot SaaS — PDF Meal Plan Exporter.
Generates styled PDF files for meal plans using ReportLab.
"""

import io
import re
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable


def generate_meal_plan_pdf(plan_title: str, plan_text: str, user_name: str = "Valued User") -> io.BytesIO:
    """
    Converts markdown meal plan text into a polished PDF document buffer.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor("#1e40af"),
        fontName="Helvetica-Bold",
        alignment=0,
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#64748b"),
        spaceAfter=15
    )

    h2_style = ParagraphStyle(
        'Heading2Custom',
        parent=styles['Heading2'],
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#0f172a"),
        fontName="Helvetica-Bold",
        spaceBefore=12,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'BodyCustom',
        parent=styles['Normal'],
        fontSize=9.5,
        leading=14,
        textColor=colors.HexColor("#334155"),
        spaceAfter=4
    )

    disclaimer_style = ParagraphStyle(
        'Disclaimer',
        parent=styles['Normal'],
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#94a3b8"),
        alignment=1,
        spaceBefore=15
    )

    story = []

    # Header section
    story.append(Paragraph("🥗 NutriBot — Personalised Nutrition Plan", title_style))
    story.append(Paragraph(f"Prepared for: <b>{user_name}</b> | Goal: <b>{plan_title}</b>", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceAfter=12))

    # Clean & format text lines
    lines = plan_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            story.append(Spacer(1, 4))
            continue

        # Format headings
        if line.startswith('#'):
            clean_head = re.sub(r'^#+\s*', '', line)
            clean_head = clean_head.replace('**', '')
            story.append(Paragraph(clean_head, h2_style))
        elif line.startswith('**') and line.endswith('**'):
            clean_bold = line.strip('*')
            story.append(Paragraph(f"<b>{clean_bold}</b>", h2_style))
        else:
            # Inline bold markdown conversion
            formatted_line = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', line)
            if formatted_line.startswith('- ') or formatted_line.startswith('* '):
                formatted_line = f"• {formatted_line[2:]}"
            story.append(Paragraph(formatted_line, body_style))

    # Disclaimer Footer
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#e2e8f0"), spaceBefore=15, spaceAfter=8))
    story.append(Paragraph("⚠️ Disclaimer: NutriBot provides AI-generated nutrition suggestions for educational purposes. Consult a certified nutritionist or physician before starting any diet.", disclaimer_style))

    doc.build(story)
    buffer.seek(0)
    return buffer
