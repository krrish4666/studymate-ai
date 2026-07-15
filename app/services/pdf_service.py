import io
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4, letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm, inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, ListFlowable, ListItem,
    Table, TableStyle, PageBreak,
)


class PdfService:
    def generate_notes_pdf(self, content: str, title: str = "Study Notes") -> io.BytesIO:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, title=title)
        styles = self._styles()
        story = [
            Paragraph(f"StudyMate AI HUB", styles["Title"]),
            Paragraph(f"<b>{title}</b>", styles["Heading1"]),
            Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles["Normal"]),
            Spacer(1, 12),
        ]
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 6))
            elif line.startswith("### "):
                story.append(Paragraph(line[4:], styles["Heading3"]))
            elif line.startswith("## "):
                story.append(Paragraph(line[3:], styles["Heading2"]))
            elif line.startswith("# "):
                story.append(Paragraph(line[2:], styles["Heading1"]))
            elif line.startswith("- ") or line.startswith("* "):
                story.append(Paragraph(f"•  {line[2:]}", styles["Normal"]))
            else:
                story.append(Paragraph(line, styles["Normal"]))

        doc.build(story)
        buf.seek(0)
        return buf

    def generate_flashcards_pdf(self, flashcards: list[dict], title: str = "Flashcards") -> io.BytesIO:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, title=title)
        styles = self._styles()
        story = [
            Paragraph(f"StudyMate AI HUB", styles["Title"]),
            Paragraph(f"<b>{title}</b>", styles["Heading1"]),
            Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles["Normal"]),
            Spacer(1, 12),
        ]
        for i, fc in enumerate(flashcards, 1):
            story.append(Paragraph(f"<b>Card {i}</b>", styles["Heading3"]))
            story.append(Paragraph(f"<b>Q:</b> {fc.get('question', '')}", styles["Normal"]))
            story.append(Paragraph(f"<b>A:</b> {fc.get('answer', '')}", styles["Normal"]))
            story.append(Spacer(1, 10))

        doc.build(story)
        buf.seek(0)
        return buf

    def generate_quiz_pdf(self, questions: list[dict], title: str = "MCQ Quiz") -> io.BytesIO:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, title=title)
        styles = self._styles()
        story = [
            Paragraph(f"StudyMate AI HUB", styles["Title"]),
            Paragraph(f"<b>{title}</b>", styles["Heading1"]),
            Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles["Normal"]),
            Spacer(1, 12),
        ]
        for i, q in enumerate(questions, 1):
            story.append(Paragraph(f"<b>Question {i}:</b> {q.get('question', '')}", styles["Normal"]))
            options = q.get("options", [])
            correct = q.get("correctAnswer", 0)
            labels = ["A", "B", "C", "D"]
            for j, opt in enumerate(options):
                marker = "✓ " if j == correct else "  "
                story.append(Paragraph(f"{marker}{labels[j]}. {opt}", styles["Normal"]))
            story.append(Spacer(1, 10))

        doc.build(story)
        buf.seek(0)
        return buf

    def generate_mindmap_pdf(self, mindmap: dict, title: str = "Mind Map") -> io.BytesIO:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, title=title)
        styles = self._styles()
        story = [
            Paragraph(f"StudyMate AI HUB", styles["Title"]),
            Paragraph(f"<b>{title}</b>", styles["Heading1"]),
            Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles["Normal"]),
            Spacer(1, 12),
        ]

        def add_node(node: dict, depth: int = 0):
            indent = "&nbsp;" * (depth * 4)
            prefix = {0: "●", 1: "○", 2: "▪", 3: "▫"}.get(depth, "•")
            style = ["Normal", "Heading2", "Heading3", "Normal"][min(depth, 3)]
            story.append(Paragraph(f"{indent}{prefix} {node.get('label', '')}", styles[style]))
            for child in node.get("children", []):
                add_node(child, depth + 1)

        add_node(mindmap)
        doc.build(story)
        buf.seek(0)
        return buf

    def generate_revision_pdf(self, content: str, title: str = "Revision Cheat Sheet") -> io.BytesIO:
        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, title=title, leftMargin=15*mm, rightMargin=15*mm)
        styles = self._styles()
        story = [
            Paragraph(f"StudyMate AI HUB", styles["Title"]),
            Paragraph(f"<b>{title}</b>", styles["Heading1"]),
            Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", styles["Normal"]),
            Spacer(1, 8),
        ]
        for line in content.split("\n"):
            line = line.strip()
            if not line:
                story.append(Spacer(1, 4))
            elif line.startswith("### "):
                story.append(Paragraph(line[4:], styles["Heading3"]))
            elif line.startswith("## "):
                story.append(Paragraph(line[3:], styles["Heading2"]))
            elif line.startswith("# "):
                story.append(Paragraph(line[2:], styles["Heading1"]))
            elif line.startswith("- ") or line.startswith("* "):
                story.append(Paragraph(f"•  {line[2:]}", styles["Normal"]))
            else:
                story.append(Paragraph(line, styles["Normal"]))

        doc.build(story)
        buf.seek(0)
        return buf

    def _styles(self):
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="Title2",
            parent=styles["Title"],
            fontSize=20,
            textColor=HexColor("#d97706"),
            spaceAfter=6,
        ))
        return styles


pdf_service = PdfService()
