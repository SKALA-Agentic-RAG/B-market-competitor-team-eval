"""
PDF export helpers for evaluation results.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any, Dict


_PDF_MIME_TYPE = "application/pdf"
_TEXT_MIME_TYPE = "text/plain"
_DEFAULT_FONT_NAME = "Helvetica"
_UNICODE_FONT_NAME = "ArialUnicodeMS"
_FONT_CANDIDATE_PATHS = [
    Path("/Library/Fonts/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
]


def _resolve_pdf_path(output_path: Path) -> Path:
    if output_path.suffix:
        return output_path.with_suffix(".pdf")
    return output_path.parent / f"{output_path.name}.pdf"


def _wrap_text_block(text: str, width: int = 100) -> str:
    wrapped_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line:
            wrapped_lines.append("")
            continue

        indent_width = len(line) - len(line.lstrip(" "))
        indent = line[:indent_width]
        content = line[indent_width:]
        available_width = max(24, width - indent_width)

        pieces = textwrap.wrap(
            content,
            width=available_width,
            replace_whitespace=False,
            drop_whitespace=False,
            break_long_words=False,
            break_on_hyphens=False,
        )

        if not pieces:
            wrapped_lines.append(indent)
            continue

        wrapped_lines.extend(f"{indent}{piece}" for piece in pieces)

    return "\n".join(wrapped_lines) + "\n"


def build_pdf_report_text(output_data: Dict[str, Any]) -> str:
    evaluations = output_data.get("evaluations", []) or []
    best_startup = output_data.get("best_startup") or "없음"
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "AI Startup Investment Evaluation Report",
        f"Created At: {created_at}",
        "",
        f"Best Startup: {best_startup}",
        f"Evaluation Count: {len(evaluations)}",
        "Decision Rule: investment_score >= 70 => invest",
        "",
        "===== SUMMARY =====",
    ]

    if evaluations:
        for index, evaluation in enumerate(evaluations, start=1):
            name = evaluation.get("startup_name", "Unknown")
            decision = (evaluation.get("investment_decision", {}) or {}).get("decision", "pass")
            score = float(evaluation.get("investment_score", 0.0) or 0.0)
            confidence = float(
                ((evaluation.get("investment_decision", {}) or {}).get("confidence", 0.0) or 0.0)
            )
            rationale = (evaluation.get("investment_decision", {}) or {}).get(
                "rationale", "정보 없음"
            )

            lines.extend(
                [
                    f"{index}. {name}",
                    f"   - decision: {decision}",
                    f"   - score: {score:.2f} / 100",
                    f"   - confidence: {confidence:.0%}",
                    f"   - rationale: {rationale}",
                    "",
                ]
            )
    else:
        lines.append("평가 결과 없음")
        lines.append("")

    lines.append("===== JSON REPORT =====")
    lines.append(json.dumps(output_data, ensure_ascii=False, indent=2))

    return _wrap_text_block("\n".join(lines))


def _find_report_font_path() -> Path | None:
    env_font = os.getenv("PDF_FONT_PATH")
    if env_font:
        candidate = Path(env_font).expanduser()
        if candidate.exists():
            return candidate

    for path in _FONT_CANDIDATE_PATHS:
        if path.exists():
            return path

    return None


def _build_reportlab_pdf(output_data: Dict[str, Any], pdf_path: Path) -> Path:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import Paragraph, Preformatted, SimpleDocTemplate, Spacer
    from xml.sax.saxutils import escape

    font_name = _DEFAULT_FONT_NAME
    font_path = _find_report_font_path()
    if font_path is not None:
        pdfmetrics.registerFont(TTFont(_UNICODE_FONT_NAME, str(font_path)))
        font_name = _UNICODE_FONT_NAME

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "PdfTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=18,
        leading=24,
        spaceAfter=12,
    )
    heading_style = ParagraphStyle(
        "PdfHeading",
        parent=styles["Heading2"],
        fontName=font_name,
        fontSize=13,
        leading=18,
        spaceBefore=8,
        spaceAfter=6,
    )
    body_style = ParagraphStyle(
        "PdfBody",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=10.5,
        leading=15,
        spaceAfter=6,
    )
    mono_style = ParagraphStyle(
        "PdfMono",
        parent=styles["Code"],
        fontName=font_name,
        fontSize=8.5,
        leading=11,
        spaceAfter=8,
    )

    best_startup = output_data.get("best_startup") or "없음"
    evaluations = output_data.get("evaluations", []) or []
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    story = [
        Paragraph("AI Startup Investment Evaluation Report", title_style),
        Paragraph(f"Created At: {escape(created_at)}", body_style),
        Paragraph(f"Best Startup: {escape(str(best_startup))}", body_style),
        Paragraph(f"Evaluation Count: {len(evaluations)}", body_style),
        Paragraph("Decision Rule: investment_score &gt;= 70 =&gt; invest", body_style),
        Spacer(1, 8),
        Paragraph("Summary", heading_style),
    ]

    if evaluations:
        for index, evaluation in enumerate(evaluations, start=1):
            name = str(evaluation.get("startup_name", "Unknown"))
            decision_obj = evaluation.get("investment_decision", {}) or {}
            decision = str(decision_obj.get("decision", "pass"))
            score = float(evaluation.get("investment_score", 0.0) or 0.0)
            confidence = float(decision_obj.get("confidence", 0.0) or 0.0)
            rationale = str(decision_obj.get("rationale", "정보 없음"))

            story.extend(
                [
                    Paragraph(f"{index}. {escape(name)}", heading_style),
                    Paragraph(f"decision: {escape(decision)}", body_style),
                    Paragraph(f"score: {score:.2f} / 100", body_style),
                    Paragraph(f"confidence: {confidence:.0%}", body_style),
                    Preformatted(
                        _wrap_text_block(f"rationale: {rationale}", width=90),
                        mono_style,
                    ),
                ]
            )

            report_content = evaluation.get("report_content")
            if report_content:
                story.append(Paragraph("Generated Report", heading_style))
                story.append(
                    Preformatted(_wrap_text_block(str(report_content), width=95), mono_style)
                )
    else:
        story.append(Paragraph("평가 결과 없음", body_style))

    story.append(Paragraph("JSON Report", heading_style))
    story.append(
        Preformatted(
            _wrap_text_block(json.dumps(output_data, ensure_ascii=False, indent=2), width=95),
            mono_style,
        )
    )

    doc = SimpleDocTemplate(
        str(pdf_path),
        pagesize=A4,
        leftMargin=36,
        rightMargin=36,
        topMargin=36,
        bottomMargin=36,
        title="AI Startup Investment Evaluation Report",
    )
    doc.build(story)
    return pdf_path


def _build_cupsfilter_pdf(output_data: Dict[str, Any], pdf_path: Path) -> Path:
    cupsfilter_path = shutil.which("cupsfilter")
    if not cupsfilter_path:
        raise RuntimeError("`cupsfilter` 명령을 찾을 수 없어 PDF를 생성할 수 없습니다.")

    pdf_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="agentic_rag_pdf_") as temp_dir:
        text_path = Path(temp_dir) / "evaluation_report.txt"
        text_path.write_text(build_pdf_report_text(output_data), encoding="utf-8")

        result = subprocess.run(
            [cupsfilter_path, "-i", _TEXT_MIME_TYPE, "-m", _PDF_MIME_TYPE, str(text_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        if result.returncode != 0:
            stderr = result.stderr.decode("utf-8", errors="replace").strip()
            raise RuntimeError(f"cupsfilter failed with exit code {result.returncode}: {stderr}")

        if not result.stdout.startswith(b"%PDF"):
            raise RuntimeError("생성된 출력이 유효한 PDF 형식이 아닙니다.")

        pdf_path.write_bytes(result.stdout)

    return pdf_path


def export_json_report_to_pdf(output_data: Dict[str, Any], output_path: Path) -> Path:
    pdf_path = _resolve_pdf_path(output_path)

    try:
        return _build_reportlab_pdf(output_data, pdf_path)
    except ModuleNotFoundError:
        return _build_cupsfilter_pdf(output_data, pdf_path)
    except Exception as reportlab_error:
        try:
            return _build_cupsfilter_pdf(output_data, pdf_path)
        except Exception as fallback_error:
            raise RuntimeError(
                "ReportLab PDF 생성과 cupsfilter fallback이 모두 실패했습니다. "
                f"reportlab_error={reportlab_error} | fallback_error={fallback_error}"
            ) from fallback_error
