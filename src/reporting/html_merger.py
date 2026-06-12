"""HTML Merger — ghép multi-agent output + ydata HTML thành 1 file Tabbed HTML.

Xem ARCHITECT v5.4 §5.8 (2-Tier Delivery).
"""
from __future__ import annotations

import html
import math
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
    "{statistical_overview}", # HTML string (Data Science-style profile overview)
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


def _format_int(value: int | float | None) -> str:
    if value is None:
        return "-"
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return "-"


def _format_percent(value: float | None) -> str:
    if value is None:
        return "-"
    return f"{float(value) * 100:.1f}%"


def _bar_width(value: float | None) -> str:
    if value is None:
        return "0%"
    return f"{max(0.0, min(float(value), 1.0)) * 100:.1f}%"


def _shape_widths(rows: int, columns: int) -> tuple[str, str]:
    row_scale = math.log10(max(rows, 0) + 1)
    column_scale = math.log10(max(columns, 0) + 1)
    max_scale = max(row_scale, column_scale, 1.0)
    return (
        f"{max(6.0, (row_scale / max_scale) * 100):.1f}%",
        f"{max(6.0, (column_scale / max_scale) * 100):.1f}%",
    )


def _severity_bars_html(verdict: DatasetVerdict) -> str:
    rows = [
        ("critical", "Critical", verdict.summary.critical),
        ("high", "High", verdict.summary.high),
        ("warn", "Warn", verdict.summary.warn),
        ("info", "Info", verdict.summary.info),
    ]
    max_count = max(1, *(count for _key, _label, count in rows))
    items = []
    for key, label, count in rows:
        width = max(4, round((count / max_count) * 100)) if count else 0
        items.append(
            "<div class=\"stats-severity-row stats-severity-{key}\" style=\"--severity-width: {width}%\">"
            "<span>{label}</span><strong>{count}</strong>"
            "</div>".format(
                key=html.escape(key),
                width=width,
                label=html.escape(label),
                count=_format_int(count),
            )
        )
    return "".join(items)


def _statistical_overview(verdict: DatasetVerdict) -> str:
    meta = verdict.dataset_meta
    missing_rate = meta.p_cells_missing
    duplicate_rate = meta.p_duplicates
    total_issues = verdict.summary.total_issues
    row_width, column_width = _shape_widths(meta.n, meta.n_var)
    return f"""
<div class="stats-overview">
  <div class="stats-overview-copy">
    <p class="eyebrow">Statistical Workbench</p>
    <h2>Profile Diagnostics</h2>
    <p>Shape, missingness, duplicate pressure, and issue severity are summarized here before the full interactive profile.</p>
  </div>
  <div class="stats-kpi-grid" aria-label="Statistical profile summary">
    <div class="stats-kpi"><span>Rows</span><strong>{_format_int(meta.n)}</strong></div>
    <div class="stats-kpi"><span>Variables</span><strong>{_format_int(meta.n_var)}</strong></div>
    <div class="stats-kpi"><span>Total issues</span><strong>{_format_int(total_issues)}</strong></div>
    <div class="stats-kpi"><span>Memory</span><strong>{_format_int(meta.memory_size)} B</strong></div>
  </div>
  <div class="stats-diagnostic-grid">
    <article class="stats-card stats-card-wide">
      <div class="stats-card-heading">
        <span>Data Shape</span>
        <strong>{html.escape(meta.file_name)}</strong>
      </div>
      <div class="shape-plot" aria-label="Dataset shape summary">
        <div class="shape-axis">
          <span>Rows</span>
          <div class="shape-bar shape-rows" style="--shape-width: {row_width}"><i></i></div>
          <strong>{_format_int(meta.n)}</strong>
        </div>
        <div class="shape-axis">
          <span>Columns</span>
          <div class="shape-bar shape-columns" style="--shape-width: {column_width}"><i></i></div>
          <strong>{_format_int(meta.n_var)}</strong>
        </div>
      </div>
    </article>
    <article class="stats-card">
      <div class="stats-card-heading">
        <span>Completeness</span>
        <strong>{_format_percent(missing_rate)}</strong>
      </div>
      <div class="stats-meter" style="--meter-width: {_bar_width(missing_rate)}">
        <i></i>
      </div>
      <p>{_format_percent(missing_rate)} cells are missing in the profiled data.</p>
    </article>
    <article class="stats-card">
      <div class="stats-card-heading">
        <span>Duplicates</span>
        <strong>{_format_percent(duplicate_rate)}</strong>
      </div>
      <div class="stats-meter duplicate-meter" style="--meter-width: {_bar_width(duplicate_rate)}">
        <i></i>
      </div>
      <p>{_format_int(meta.n_duplicates)} duplicate rows detected.</p>
    </article>
    <article class="stats-card stats-card-wide">
      <div class="stats-card-heading">
        <span>Severity Distribution</span>
        <strong>{_format_int(total_issues)} findings</strong>
      </div>
      <div class="stats-severity-bars">
        {_severity_bars_html(verdict)}
      </div>
    </article>
  </div>
  <div class="profile-lens-strip" aria-label="Profile inspection lenses">
    <span>Overview</span>
    <span>Variables</span>
    <span>Missingness</span>
    <span>Correlations</span>
    <span>Samples</span>
  </div>
</div>
"""


def _agent_detail_lookup(result: MultiAgentResult) -> dict[str, dict]:
    lookup: dict[str, dict] = {}
    for detail in result.guardrail_report.get("agents", []) if result.guardrail_report else []:
        if not isinstance(detail, dict):
            continue
        cluster = detail.get("cluster")
        agent = detail.get("agent")
        if isinstance(cluster, str):
            lookup[cluster] = detail
        elif isinstance(agent, str):
            lookup[agent] = detail
    return lookup


def _provider_kind(provider: str) -> str:
    if provider.startswith("openai"):
        return "openai"
    if provider.startswith("deterministic"):
        return "deterministic"
    return "other"


def _agent_status_panel(result: MultiAgentResult) -> str:
    guardrail = result.guardrail_report or {}
    agents = [agent for agent in guardrail.get("agents", []) if isinstance(agent, dict)]
    if not agents:
        return ""

    provider = str(guardrail.get("provider") or ("deterministic" if result.used_fallback else "multi-agent"))
    fallback_text = "Fallback used" if result.used_fallback else "LLM output accepted"
    cards: list[str] = []
    for detail in agents:
        agent = str(detail.get("agent") or "agent")
        cluster = str(detail.get("cluster") or agent)
        detail_provider = str(detail.get("provider") or "unknown")
        status = str(detail.get("status") or "unknown")
        retry_count = detail.get("retry_count", 0)
        used_fallback = bool(detail.get("used_fallback"))
        kind = _provider_kind(detail_provider)
        cards.append(
            "<article class=\"agent-status-card agent-provider-{kind}\">"
            "<div class=\"agent-status-heading\">"
            "<span>{cluster}</span>"
            "<strong>{status}</strong>"
            "</div>"
            "<dl>"
            "<div><dt>Agent</dt><dd>{agent}</dd></div>"
            "<div><dt>Provider</dt><dd>{provider}</dd></div>"
            "<div><dt>Fallback</dt><dd>{fallback}</dd></div>"
            "<div><dt>Retries</dt><dd>{retries}</dd></div>"
            "</dl>"
            "</article>".format(
                kind=html.escape(kind),
                cluster=html.escape(cluster),
                status=html.escape(status),
                agent=html.escape(agent),
                provider=html.escape(detail_provider),
                fallback="yes" if used_fallback else "no",
                retries=html.escape(str(retry_count)),
            )
        )

    return (
        "<section class=\"llm-review-panel\">"
        "<div class=\"llm-review-copy\">"
        "<p class=\"eyebrow\">LLM Agent Review</p>"
        "<h2>Guardrailed L4 Comments</h2>"
        "<p>Agent notes below are shown with the provider that passed guardrail. "
        "If an LLM answer fails evidence checks, the report keeps the deterministic fallback visible instead of hiding it.</p>"
        "</div>"
        "<div class=\"llm-review-summary\">"
        f"<span>Final provider: {html.escape(provider)}</span>"
        f"<span>{html.escape(fallback_text)}</span>"
        "</div>"
        "<div class=\"agent-status-grid\">"
        f"{''.join(cards)}"
        "</div>"
        "</section>"
    )


def _agent_meta(detail: dict | None, fallback_label: str) -> str:
    if detail is None:
        return fallback_label
    provider = str(detail.get("provider") or "unknown")
    status = str(detail.get("status") or "unknown")
    retry_count = detail.get("retry_count", 0)
    used_fallback = bool(detail.get("used_fallback"))
    fallback = "fallback" if used_fallback else "llm"
    return f"{provider} · guardrail {status} · {fallback} · retries {retry_count}"


def _agent_content(result: MultiAgentResult) -> str:
    sections: list[str] = []
    details = _agent_detail_lookup(result)
    status_panel = _agent_status_panel(result)
    if status_panel:
        sections.append(status_panel)

    editor = result.editor_output
    if editor is not None:
        sections.append("<section class=\"ai-section editor-section\">")
        sections.append(f"<div class=\"agent-meta\">Editor · {html.escape(_agent_meta(details.get('editor'), 'guardrail passed'))}</div>")
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
            detail = details.get(output.cluster_type)
            sections.append(
                f"<article class=\"analyst-section guardrail-{status}\">"
                f"<div class=\"agent-meta\">{html.escape(output.cluster_type)} · {html.escape(_agent_meta(detail, f'guardrail {status}'))}</div>"
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
    provider = str(
        multi_agent_result.guardrail_report.get("provider")
        if multi_agent_result.guardrail_report
        else ("deterministic" if multi_agent_result.used_fallback else "multi-agent")
    )
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
        statistical_overview=_statistical_overview(verdict),
        ydata_escaped=html.escape(ydata_html, quote=True),
        guardrail_status=html.escape(guardrail_status),
        provider=html.escape(provider),
        model_info=html.escape(model_info),
        timestamp=html.escape(timestamp),
        css_content=_load_css(),
        js_content=_load_js(),
    )
