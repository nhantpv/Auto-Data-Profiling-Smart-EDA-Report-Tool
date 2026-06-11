"""HTML Merger — ghép multi-agent output + ydata HTML thành 1 file Tabbed HTML.

Xem ARCHITECT v5.4 §5.8 (2-Tier Delivery).
"""
from __future__ import annotations

import html
from datetime import datetime, timezone
from pathlib import Path

from ontology.models import DatasetVerdict, MultiAgentResult


# Template placeholder keys — C tạo template phải có đúng các placeholders này
TEMPLATE_PLACEHOLDERS = [
    "{verdict_class}",       # READY | WARN | NOT_READY
    "{verdict_value}",       # READY | WARN | NOT_READY
    "{verdict_icon}",        # ✅ | ⚠️ | ❌
    "{verdict_rationale}",   # string
    "{file_name}",           # string
    "{n}",                   # int
    "{n_var}",               # int
    "{p_cells_missing}",     # "12.3%"
    "{ai_analysis_content}", # HTML string (Editor + Analysts + Appendix)
    "{ydata_escaped}",       # HTML-escaped ydata string
    "{guardrail_status}",    # "passed" | "partial" | "failed"
    "{provider}",            # "multi-agent" | "deterministic"
    "{model_info}",          # string
    "{timestamp}",           # ISO string
    "{css_content}",         # CSS string (inline)
    "{js_content}",          # JS string (inline)
]


_TEMPLATES_DIR = Path(__file__).parent / "templates"


def _load_template() -> str:
    """Load HTML template từ C's file. Fallback nếu chưa có."""
    template_path = _TEMPLATES_DIR / "report_template.html"
    if template_path.exists():
        return template_path.read_text(encoding="utf-8")
    # Fallback minimal — để B có thể test không cần C
    return """<!DOCTYPE html>
<html lang="vi">
<head><meta charset="utf-8"><title>Smart EDA Report</title></head>
<body>
<h1>{verdict_icon} {verdict_value}</h1>
<p>{verdict_rationale}</p>
<div>{ai_analysis_content}</div>
<hr>
<iframe srcdoc="{ydata_escaped}" style="width:100%;height:90vh;border:none;"></iframe>
<footer><p>Guardrail: {guardrail_status} · {provider} · {model_info}</p></footer>
</body>
</html>"""


def _load_css() -> str:
    css_path = _TEMPLATES_DIR / "styles.css"
    if css_path.exists():
        return css_path.read_text(encoding="utf-8")
    return ""


def _load_js() -> str:
    js_path = _TEMPLATES_DIR / "tab.js"
    if js_path.exists():
        return js_path.read_text(encoding="utf-8")
    return """
function showTab(id) {
  document.querySelectorAll('.tab-content').forEach(el => el.style.display='none');
  document.querySelectorAll('.tab').forEach(el => el.classList.remove('active'));
  document.getElementById('tab-'+id).style.display='block';
  event.target.classList.add('active');
}
"""


def _paragraph(text: str) -> str:
    return f"<p>{html.escape(text)}</p>"


def _markdown_table(lines: list[str]) -> str:
    rows: list[list[str]] = []
    for line in lines:
        cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
        if cells and not all(set(cell) <= {"-", ":", " "} for cell in cells):
            rows.append(cells)
    if not rows:
        return ""
    head = rows[0]
    body = rows[1:]
    output = ["<table>", "<thead><tr>"]
    output.extend(f"<th>{html.escape(cell)}</th>" for cell in head)
    output.append("</tr></thead>")
    if body:
        output.append("<tbody>")
        for row in body:
            output.append("<tr>")
            output.extend(f"<td>{html.escape(cell)}</td>" for cell in row)
            output.append("</tr>")
        output.append("</tbody>")
    output.append("</table>")
    return "".join(output)


def _markdown_to_html(markdown: str) -> str:
    """Small safe Markdown subset; enough for deterministic L4 output."""
    output: list[str] = []
    table_buffer: list[str] = []

    def flush_table() -> None:
        nonlocal table_buffer
        if table_buffer:
            output.append(_markdown_table(table_buffer))
            table_buffer = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.strip().startswith("|") and line.strip().endswith("|"):
            table_buffer.append(line)
            continue
        flush_table()

        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("### "):
            output.append(f"<h3>{html.escape(stripped[4:])}</h3>")
        elif stripped.startswith("## "):
            output.append(f"<h2>{html.escape(stripped[3:])}</h2>")
        elif stripped.startswith("# "):
            output.append(f"<h1>{html.escape(stripped[2:])}</h1>")
        elif stripped.startswith("- "):
            output.append(f"<li>{html.escape(stripped[2:])}</li>")
        else:
            output.append(_paragraph(stripped))
    flush_table()
    return "\n".join(output)


def _agent_content(result: MultiAgentResult) -> str:
    sections: list[str] = []
    editor = result.editor_output
    if editor is not None:
        sections.append("<section class=\"ai-section editor-section\">")
        sections.append("<h2>Executive Summary</h2>")
        if editor.executive_summary:
            sections.append(_paragraph(editor.executive_summary))
        if editor.verdict_explanation:
            sections.append("<h2>Decision Rationale</h2>")
            sections.append(_paragraph(editor.verdict_explanation))
        if editor.cross_table_evaluation:
            sections.append("<h2>Cross-table Evaluation</h2>")
            sections.append(_paragraph(editor.cross_table_evaluation))
        if editor.priority_ranking:
            sections.append("<h2>Priority Ranking</h2>")
            sections.append(_paragraph(editor.priority_ranking))
        sections.append("</section>")

    if result.analyst_outputs:
        sections.append("<section class=\"ai-section analyst-sections\">")
        sections.append("<h2>Analyst Sections</h2>")
        for output in result.analyst_outputs:
            status = "passed" if output.guardrail_passed else "failed"
            sections.append(
                f"<article class=\"analyst-section guardrail-{status}\">"
                f"<div class=\"agent-meta\">{html.escape(output.cluster_type)} · guardrail {status}</div>"
            )
            sections.append(_markdown_to_html(output.markdown))
            sections.append("</article>")
        sections.append("</section>")

    if result.appendix_html:
        sections.append(result.appendix_html)
    return "\n".join(sections) if sections else "<p>No AI analysis sections were generated.</p>"


def merge_to_tabbed_html(
    multi_agent_result: MultiAgentResult,
    verdict: DatasetVerdict,
    ydata_html: str,
    guardrail_status: str = "passed",
    model_info: str = "Analyst: gpt-4o-mini, Editor: gpt-4o",
    timestamp: str = "",
) -> str:
    """
    Ghép tất cả thành 1 file HTML duy nhất với 2 tab.

    Tab 1 (AI Analysis): Editor output + Analyst outputs + Appendix
    Tab 2 (Statistical Details): ydata HTML nguyên bản qua <iframe srcdoc>

    Args:
        multi_agent_result: Kết quả từ L4 multi-agent pipeline
        verdict: DatasetVerdict từ L2.5 aggregator
        ydata_html: Nguyên bản HTML từ ProfileReport.to_html()
        guardrail_status: "passed" | "partial" | "failed"
        model_info: Thông tin model đã dùng
        timestamp: ISO timestamp

    Returns:
        Complete HTML string → ghi ra smart_eda_report.html
    """
    template = _load_template()
    verdict_value = verdict.verdict.value
    icon_by_verdict = {
        "READY": "OK",
        "WARN": "WARN",
        "NOT_READY": "BLOCKED",
    }
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()
    provider = "deterministic" if multi_agent_result.used_fallback else "multi-agent"
    return template.format(
        verdict_class=html.escape(verdict_value),
        verdict_value=html.escape(verdict_value),
        verdict_icon=icon_by_verdict.get(verdict_value, ""),
        verdict_rationale=html.escape(verdict.verdict_rationale),
        file_name=html.escape(verdict.dataset_meta.file_name),
        n=verdict.dataset_meta.n,
        n_var=verdict.dataset_meta.n_var,
        p_cells_missing=html.escape(f"{verdict.dataset_meta.p_cells_missing * 100:.1f}%"),
        ai_analysis_content=_agent_content(multi_agent_result),
        ydata_escaped=html.escape(ydata_html, quote=True),
        guardrail_status=html.escape(guardrail_status),
        provider=html.escape(provider),
        model_info=html.escape(model_info),
        timestamp=html.escape(timestamp),
        css_content=_load_css(),
        js_content=_load_js(),
    )
