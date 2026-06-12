"""HTML Merger — ghép multi-agent output + ydata HTML thành 1 file Tabbed HTML.

Xem ARCHITECT v5.4 §5.8 (2-Tier Delivery).
"""
from __future__ import annotations

import html
import math
import re
from datetime import datetime, timezone
from pathlib import Path

from ontology.models import DatasetVerdict, IssueSummary, MultiAgentResult


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
    "{profile_viewer_html}", # HTML string (links/cards for standalone profiles)
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
<div>{profile_viewer_html}</div>
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


_INLINE_CODE_RE = re.compile(r"`([^`]+)`")
_INLINE_STRONG_RE = re.compile(r"\*\*([^*]+)\*\*")


def _inline_markdown(text: str) -> str:
    """Safe inline Markdown for emphasis inside report copy."""
    parts: list[str] = []
    position = 0
    for match in _INLINE_CODE_RE.finditer(text):
        if match.start() > position:
            plain = html.escape(text[position:match.start()])
            plain = _INLINE_STRONG_RE.sub(r"<strong>\1</strong>", plain)
            parts.append(plain)
        parts.append(f"<code>{html.escape(match.group(1))}</code>")
        position = match.end()
    if position < len(text):
        plain = html.escape(text[position:])
        plain = _INLINE_STRONG_RE.sub(r"<strong>\1</strong>", plain)
        parts.append(plain)
    return "".join(parts)


def _paragraph(text: str) -> str:
    return f"<p>{_inline_markdown(text)}</p>"


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
    output.extend(f"<th>{_inline_markdown(cell)}</th>" for cell in head)
    output.append("</tr></thead>")
    if body:
        output.append("<tbody>")
        for row in body:
            output.append("<tr>")
            output.extend(f"<td>{_inline_markdown(cell)}</td>" for cell in row)
            output.append("</tr>")
        output.append("</tbody>")
    output.append("</table>")
    return "".join(output)


def _markdown_to_html(markdown: str) -> str:
    """Small safe Markdown subset; enough for deterministic L4 output."""
    output: list[str] = []
    table_buffer: list[str] = []
    list_buffer: list[str] = []

    def flush_table() -> None:
        nonlocal table_buffer
        if table_buffer:
            output.append(_markdown_table(table_buffer))
            table_buffer = []

    def flush_list() -> None:
        nonlocal list_buffer
        if list_buffer:
            output.append("<ul class=\"insight-list\">")
            output.extend(f"<li>{_inline_markdown(item)}</li>" for item in list_buffer)
            output.append("</ul>")
            list_buffer = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()
        if line.strip().startswith("|") and line.strip().endswith("|"):
            flush_list()
            table_buffer.append(line)
            continue
        flush_table()

        stripped = line.strip()
        if not stripped:
            flush_list()
            continue
        if stripped.startswith("### "):
            flush_list()
            output.append(f"<h4>{_inline_markdown(stripped[4:])}</h4>")
        elif stripped.startswith("## "):
            flush_list()
            output.append(f"<h3>{_inline_markdown(stripped[3:])}</h3>")
        elif stripped.startswith("# "):
            flush_list()
            output.append(f"<h3>{_inline_markdown(stripped[2:])}</h3>")
        elif stripped.startswith("- "):
            list_buffer.append(stripped[2:])
        else:
            flush_list()
            output.append(_paragraph(stripped))
    flush_list()
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


def _bounded_pct(value: float | None) -> float:
    if value is None:
        return 0.0
    return max(0.0, min(float(value), 1.0)) * 100


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


def _severity_stack_html(verdict: DatasetVerdict) -> str:
    total = max(1, verdict.summary.total_issues)
    rows = [
        ("critical", "Critical", verdict.summary.critical),
        ("high", "High", verdict.summary.high),
        ("warn", "Warn", verdict.summary.warn),
        ("info", "Info", verdict.summary.info),
    ]
    segments = []
    legend = []
    for key, label, count in rows:
        width = 0 if count == 0 else max(4.0, (count / total) * 100)
        segments.append(
            "<span class=\"severity-stack-segment severity-stack-{key}\" "
            "style=\"--stack-width: {width}%\" title=\"{label}: {count}\"></span>".format(
                key=html.escape(key),
                width=f"{width:.1f}",
                label=html.escape(label),
                count=_format_int(count),
            )
        )
        legend.append(
            "<span><i class=\"severity-dot severity-dot-{key}\"></i>{label} <strong>{count}</strong></span>".format(
                key=html.escape(key),
                label=html.escape(label),
                count=_format_int(count),
            )
        )
    if verdict.summary.total_issues == 0:
        segments = ["<span class=\"severity-stack-segment severity-stack-ready\" style=\"--stack-width: 100%\"></span>"]
    return (
        "<div class=\"severity-stack\" aria-label=\"Severity stack\">"
        f"{''.join(segments)}"
        "</div>"
        "<div class=\"severity-stack-legend\">"
        f"{''.join(legend)}"
        "</div>"
    )


def _severity_key(value: str | None) -> str:
    normalized = (value or "INFO").lower()
    if normalized not in {"critical", "high", "warn", "info"}:
        return "info"
    return normalized


def _verdict_headline(verdict: DatasetVerdict) -> str:
    if verdict.verdict.value == "NOT_READY":
        return "Do not use this dataset for downstream analysis yet."
    if verdict.verdict.value == "WARN":
        return "Usable only after analyst review."
    return "No blocking data-quality issues detected."


def _scope_for_issue(issue: IssueSummary) -> str:
    if issue.affected_table and issue.affected_column:
        return f"{issue.affected_table}.{issue.affected_column}"
    return issue.affected_column or issue.affected_table or "dataset"


def _risk_percent(verdict: DatasetVerdict) -> float:
    if verdict.risk_score is not None:
        return max(0.0, min(float(verdict.risk_score) * 100, 100.0))
    total = verdict.summary.total_issues
    if total == 0:
        return 0.0
    weighted = (
        verdict.summary.critical * 4
        + verdict.summary.high * 3
        + verdict.summary.warn * 2
        + verdict.summary.info
    )
    return (weighted / max(total * 4, 1)) * 100


def _issue_impact_bars(verdict: DatasetVerdict) -> str:
    if not verdict.top_issues:
        return "<p class=\"muted-copy\">No ranked issues were available for an impact chart.</p>"
    max_affected = max(1, *(issue.affected_count for issue in verdict.top_issues))
    rows = []
    for issue in verdict.top_issues[:6]:
        width = max(3.0, (issue.affected_count / max_affected) * 100) if issue.affected_count else 0
        rows.append(
            "<div class=\"impact-row impact-{severity}\" style=\"--impact-width: {width}%\">"
            "<div><strong>{issue_type}</strong><span>{scope}</span></div>"
            "<em>{affected}</em>"
            "</div>".format(
                severity=html.escape(_severity_key(issue.effective_severity.value)),
                width=f"{width:.1f}",
                issue_type=html.escape(issue.issue_type),
                scope=html.escape(_scope_for_issue(issue)),
                affected=_format_int(issue.affected_count),
            )
        )
    return "".join(rows)


_CHART_COPY = {
    "missingness_bar": ("Missingness Bar", "Column-level completeness scan."),
    "dtype_distribution": ("Type Donut", "Data type mix across columns."),
    "numeric_distributions": ("Histogram Grid", "Numeric distribution snapshots."),
    "numeric_boxplot": ("Box Plot", "Standardized numeric spread."),
    "correlation_heatmap": ("Correlation Heatmap", "Pairwise numeric association view."),
    "categorical_top_values": ("Category Bar", "Most frequent values in a categorical field."),
}


def _chart_copy(chart_key: str) -> tuple[str, str, str]:
    table_name = ""
    normalized_key = chart_key
    if "." in chart_key:
        table_name, normalized_key = chart_key.rsplit(".", 1)
    title, description = _CHART_COPY.get(
        normalized_key,
        (normalized_key.replace("_", " ").title(), "Generated quick-look visualization."),
    )
    return table_name, title, description


def _overview_chart_gallery(verdict: DatasetVerdict) -> str:
    charts = verdict.dataset_meta.overview_charts
    if not charts:
        return (
            "<div class=\"chart-gallery-empty\">"
            "<strong>No generated PNG charts were attached.</strong>"
            "<p>Verdict-level visual summaries are still shown above; rerun the pipeline to generate chart artifacts.</p>"
            "</div>"
        )

    preferred = [
        "missingness_bar",
        "dtype_distribution",
        "numeric_distributions",
        "numeric_boxplot",
        "correlation_heatmap",
        "categorical_top_values",
    ]

    def sort_key(item: tuple[str, str]) -> tuple[int, str]:
        key, _path = item
        normalized = key.rsplit(".", 1)[-1]
        try:
            rank = preferred.index(normalized)
        except ValueError:
            rank = len(preferred)
        return rank, key

    cards = []
    for chart_key, chart_path in sorted(charts.items(), key=sort_key)[:18]:
        table_name, title, description = _chart_copy(chart_key)
        table_badge = f"<span>{html.escape(table_name)}</span>" if table_name else ""
        cards.append(
            "<article class=\"chart-card\">"
            "<div class=\"chart-card-copy\">"
            f"{table_badge}"
            f"<strong>{html.escape(title)}</strong>"
            f"<p>{html.escape(description)}</p>"
            "</div>"
            "<div class=\"chart-frame\">"
            f"<img src=\"{html.escape(chart_path, quote=True)}\" alt=\"{html.escape(title, quote=True)}\" loading=\"lazy\">"
            "</div>"
            "</article>"
        )
    return "<div class=\"chart-gallery\">" + "".join(cards) + "</div>"


def _visual_overview(verdict: DatasetVerdict) -> str:
    meta = verdict.dataset_meta
    risk = _risk_percent(verdict)
    missing = _bounded_pct(meta.p_cells_missing)
    duplicates = _bounded_pct(meta.p_duplicates)
    return f"""
<section class="visual-overview">
  <div class="section-heading">
    <p class="eyebrow">Visual Data Science Overview</p>
    <h2>Charts to inspect immediately</h2>
    <p class="muted-copy">Fast visual triage before opening the full statistical profile.</p>
  </div>
  <div class="visual-grid">
    <article class="visual-card visual-risk-card">
      <span>Heuristic risk</span>
      <div class="risk-donut" style="--risk-angle: {risk * 3.6:.1f}deg"><strong>{risk:.1f}%</strong></div>
      <p>Risk score is derived from the severity-weighted findings density.</p>
    </article>
    <article class="visual-card">
      <span>Completeness and duplicates</span>
      <div class="dual-meter">
        <div style="--meter-width: {missing:.1f}%"><label>Missing cells</label><i></i><strong>{missing:.1f}%</strong></div>
        <div style="--meter-width: {duplicates:.1f}%"><label>Duplicate rows</label><i></i><strong>{duplicates:.1f}%</strong></div>
      </div>
    </article>
    <article class="visual-card visual-stack-card">
      <span>Severity mix</span>
      {_severity_stack_html(verdict)}
    </article>
    <article class="visual-card visual-impact-card">
      <span>Issue impact bars</span>
      {_issue_impact_bars(verdict)}
    </article>
  </div>
  <div class="generated-chart-section">
    <div class="section-heading">
      <p class="eyebrow">Generated Data Charts</p>
      <h2>Profile visuals attached to this run</h2>
    </div>
    {_overview_chart_gallery(verdict)}
  </div>
</section>
"""


def _science_brief(verdict: DatasetVerdict) -> str:
    summary = verdict.summary
    meta = verdict.dataset_meta
    return f"""
<section class="science-brief science-brief-{html.escape(verdict.verdict.value)}">
  <div class="science-brief-copy">
    <p class="eyebrow">Data Science Brief</p>
    <h2>{html.escape(_verdict_headline(verdict))}</h2>
    <p><strong>Decision signal:</strong> {html.escape(verdict.verdict_rationale)}</p>
  </div>
  <div class="science-scoreboard" aria-label="Decision metrics">
    <div class="science-score science-score-critical"><span>Critical</span><strong>{_format_int(summary.critical)}</strong></div>
    <div class="science-score science-score-high"><span>High</span><strong>{_format_int(summary.high)}</strong></div>
    <div class="science-score science-score-warn"><span>Warn</span><strong>{_format_int(summary.warn)}</strong></div>
    <div class="science-score"><span>Missing cells</span><strong>{_format_percent(meta.p_cells_missing)}</strong></div>
  </div>
</section>
"""


def _issue_spotlight(verdict: DatasetVerdict) -> str:
    if not verdict.top_issues:
        return (
            "<section class=\"priority-spotlight\">"
            "<div class=\"section-heading\"><p class=\"eyebrow\">Immediate Attention</p>"
            "<h2>No ranked issue details were included.</h2></div>"
            "<p class=\"muted-copy\">The report can still be reviewed through the executive interpretation and statistical profile.</p>"
            "</section>"
        )

    cards: list[str] = []
    for index, issue in enumerate(verdict.top_issues[:4], start=1):
        severity = issue.effective_severity.value
        key = _severity_key(severity)
        cards.append(
            "<article class=\"priority-card priority-{key}\">"
            "<div class=\"priority-rank\">#{rank}</div>"
            "<div class=\"priority-card-body\">"
            "<div class=\"priority-card-title\">"
            "<span>{severity}</span>"
            "<strong>{issue_type}</strong>"
            "</div>"
            "<p><strong>Scope:</strong> <code>{scope}</code></p>"
            "<p><strong>Affected rows:</strong> <code>{affected}</code></p>"
            "<p>{rationale}</p>"
            "</div>"
            "</article>".format(
                key=html.escape(key),
                rank=index,
                severity=html.escape(severity),
                issue_type=html.escape(issue.issue_type),
                scope=html.escape(_scope_for_issue(issue)),
                affected=_format_int(issue.affected_count),
                rationale=html.escape(issue.rationale),
            )
        )
    return (
        "<section class=\"priority-spotlight\">"
        "<div class=\"section-heading\"><p class=\"eyebrow\">Immediate Attention</p>"
        "<h2>Issues that should drive the next action</h2></div>"
        "<div class=\"priority-grid\">"
        f"{''.join(cards)}"
        "</div>"
        "</section>"
    )


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


def _profile_viewer_html(ydata_html: str) -> str:
    """Render statistical profile access without nesting full reports in this report."""
    stripped = ydata_html.strip()
    if stripped.startswith("<!-- smart-eda-profile-fragment -->"):
        return stripped
    return (
        "<section class=\"profile-viewer profile-export-panel\" aria-label=\"Statistical profile export\">"
        "<div class=\"profile-viewer-header\">"
        "<div><p class=\"eyebrow\">Profile Export</p><h2>Standalone Statistical Profile</h2></div>"
        "<span class=\"profile-badge\">opens separately</span>"
        "</div>"
        "<div class=\"profile-export-body\">"
        "<p>The statistical profile is kept outside the Smart EDA report to avoid nested reports. "
        "This run used an inline legacy profile payload; regenerate through the pipeline to create standalone profile files.</p>"
        "<details class=\"legacy-profile-detail\">"
        "<summary>View legacy embedded profile</summary>"
        f"<iframe srcdoc=\"{html.escape(ydata_html, quote=True)}\" class=\"ydata-frame\" title=\"Legacy statistical profile\"></iframe>"
        "</details>"
        "</div>"
        "</section>"
    )


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


def _agent_trace_meta(detail: dict | None) -> str:
    if detail is None:
        return "guardrail status unavailable"
    provider = str(detail.get("provider") or "unknown")
    retry_count = detail.get("retry_count", 0)
    used_fallback = bool(detail.get("used_fallback"))
    mode = "fallback" if used_fallback else "llm"
    return f"{provider} · {mode} · retries {retry_count}"


def _editor_card(label: str, value: str | None, tone: str) -> str:
    if not value:
        return ""
    return (
        f"<article class=\"editor-insight-card editor-insight-{html.escape(tone)}\">"
        f"<span>{html.escape(label)}</span>"
        f"<p>{_inline_markdown(value)}</p>"
        "</article>"
    )


_ISSUE_COPY = {
    "PK_DUPLICATE": (
        "Primary-key integrity blocker",
        "Primary-key values are duplicated, so entity identity and downstream joins are unsafe until deduped.",
    ),
    "ORPHAN_FOREIGN_KEY": (
        "Relationship integrity blocker",
        "Foreign-key values point to missing parent records; joins can drop rows or attach the wrong context.",
    ),
    "NON_UNIQUE_PARENT_PK": (
        "Safe-join blocker",
        "Parent keys are not unique, so a join can multiply rows and bias cross-table analysis.",
    ),
    "PK_NULL": (
        "Entity identity blocker",
        "Primary-key nulls mean some records cannot be uniquely addressed or reliably joined.",
    ),
    "MISSINGNESS": (
        "Completeness risk",
        "Missing values reduce feature reliability and should be handled before modeling or reporting.",
    ),
    "DUPLICATE": (
        "Row duplication risk",
        "Duplicate rows can inflate counts, aggregates, and model training signals.",
    ),
}


def _cluster_copy(issue_type: str) -> tuple[str, str]:
    return _ISSUE_COPY.get(
        issue_type,
        (
            "Quality signal",
            "This cluster contains evidence that should be reviewed before using the dataset.",
        ),
    )


def _issue_rank(severity: str | None) -> int:
    return {"INFO": 0, "WARN": 1, "HIGH": 2, "CRITICAL": 3}.get(severity or "INFO", 0)


def _cluster_issues(verdict: DatasetVerdict, cluster_type: str) -> list[IssueSummary]:
    return [issue for issue in verdict.top_issues if issue.issue_type == cluster_type]


def _cluster_max_severity(issues: list[IssueSummary], markdown: str) -> str:
    if issues:
        return max((issue.effective_severity.value for issue in issues), key=_issue_rank)
    match = re.search(r"\b(CRITICAL|HIGH|WARN|INFO)\b", markdown)
    return match.group(1) if match else "INFO"


def _cluster_affected_count(issues: list[IssueSummary]) -> int | None:
    if not issues:
        return None
    return sum(issue.affected_count for issue in issues)


def _cluster_count_from_markdown(markdown: str) -> int | None:
    patterns = (
        r"\btotal\s+count(?:\s+of\s+issues)?[^\d]+(\d+)\b",
        r"\bcount(?:\s+of\s+issues)?[^\d]+(\d+)\b",
    )
    for pattern in patterns:
        match = re.search(pattern, markdown, re.IGNORECASE)
        if match:
            return int(match.group(1))
    return None


def _cluster_scopes(issues: list[IssueSummary], markdown: str) -> list[str]:
    scopes = [_scope_for_issue(issue) for issue in issues if _scope_for_issue(issue) != "dataset"]
    if not scopes:
        scopes = _QUALIFIED_REFERENCE_FROM_TEXT.findall(markdown)
    unique_scopes: list[str] = []
    for scope in scopes:
        if scope not in unique_scopes:
            unique_scopes.append(scope)
    return unique_scopes[:5]


_QUALIFIED_REFERENCE_FROM_TEXT = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*\b")


def _important_observations(issues: list[IssueSummary], markdown: str) -> list[str]:
    observations: list[str] = []
    seen: set[str] = set()
    for issue in issues[:3]:
        scope = _scope_for_issue(issue)
        text = f"**{issue.effective_severity.value}** on `{scope}`: {issue.rationale}"
        plain_key = re.sub(r"\s+", " ", text.replace("`", "")).strip().lower()
        if plain_key in seen:
            continue
        seen.add(plain_key)
        observations.append(text)
    if observations:
        return observations

    skip_prefixes = (
        "issue type",
        "issue_type",
        "total count",
        "count of issues",
        "maximum severity",
        "max_severity",
        "affected columns",
        "severity",
        "affected count",
        "affected column",
        "data quality dimension",
        "provenance",
        "finding id",
        "finding_id",
        "error type",
    )
    for raw_line in markdown.splitlines():
        line = raw_line.strip().lstrip("-").strip()
        plain = line.replace("`", "")
        if not plain or plain.startswith("#"):
            continue
        if plain.lower().startswith(skip_prefixes):
            continue
        if any(keyword in plain.lower() for keyword in ("duplicate", "missing", "null", "reference", "join", "bias")):
            if plain.lower().startswith("description:") and ":" in line:
                line = line.split(":", 1)[1].strip()
                plain = line.replace("`", "")
            plain_key = re.sub(r"\s+", " ", plain).strip().lower()
            if plain_key in seen:
                continue
            seen.add(plain_key)
            observations.append(line)
        if len(observations) >= 3:
            break
    return observations[:3]


def _cluster_evidence_card(
    output: object,
    verdict: DatasetVerdict,
    detail: dict | None,
    status: str,
) -> str:
    cluster_type = str(getattr(output, "cluster_type"))
    markdown = str(getattr(output, "markdown"))
    issues = _cluster_issues(verdict, cluster_type)
    severity = _cluster_max_severity(issues, markdown)
    severity_key = _severity_key(severity)
    affected_count = _cluster_affected_count(issues)
    scopes = _cluster_scopes(issues, markdown)
    kicker, statement = _cluster_copy(cluster_type)
    observations = _important_observations(issues, markdown)
    finding_count = len(issues) if issues else _cluster_count_from_markdown(markdown)

    metrics = [
        ("Severity", severity),
        ("Findings", _format_int(finding_count) if finding_count is not None else "See notes"),
        ("Affected rows", _format_int(affected_count) if affected_count is not None else "See notes"),
    ]
    metric_html = "".join(
        "<div><span>{label}</span><strong>{value}</strong></div>".format(
            label=html.escape(label),
            value=html.escape(value),
        )
        for label, value in metrics
    )
    scopes_html = "".join(f"<code>{html.escape(scope)}</code>" for scope in scopes)
    if not scopes_html:
        scopes_html = "<span class=\"muted-copy\">No scoped column was reported.</span>"
    observations_html = "".join(f"<li>{_inline_markdown(item)}</li>" for item in observations)
    if not observations_html:
        observations_html = "<li>No concise observation was available; open the full notes for details.</li>"

    return (
        f"<article class=\"analyst-section guardrail-{html.escape(status)}\">"
        f"<div class=\"cluster-summary-card cluster-{html.escape(severity_key)}\">"
        "<div class=\"cluster-summary-header\">"
        "<div>"
        f"<span class=\"cluster-kicker\">{html.escape(kicker)}</span>"
        f"<h3>{html.escape(cluster_type)}</h3>"
        f"<p>{html.escape(statement)}</p>"
        "</div>"
        f"<span class=\"cluster-severity severity-{html.escape(severity)}\">{html.escape(severity)}</span>"
        "</div>"
        f"<div class=\"cluster-metrics\">{metric_html}</div>"
        "<div class=\"cluster-scope-row\">"
        "<span>Scope</span>"
        f"<div>{scopes_html}</div>"
        "</div>"
        "<div class=\"cluster-observations\">"
        "<span>What to notice</span>"
        f"<ul>{observations_html}</ul>"
        "</div>"
        "<div class=\"cluster-trace\">"
        f"<span>{html.escape(_agent_trace_meta(detail))}</span>"
        f"<strong>guardrail {html.escape(status)}</strong>"
        "</div>"
        "<details class=\"analyst-detail\">"
        "<summary>View full analyst notes</summary>"
        "<div class=\"analyst-detail-body\">"
        f"{_markdown_to_html(markdown)}"
        "</div>"
        "</details>"
        "</div>"
        "</article>"
    )


def _agent_content(result: MultiAgentResult, verdict: DatasetVerdict) -> str:
    sections: list[str] = []
    sections.append(_science_brief(verdict))
    sections.append(_visual_overview(verdict))
    sections.append(_issue_spotlight(verdict))

    details = _agent_detail_lookup(result)
    status_panel = _agent_status_panel(result)
    if status_panel:
        sections.append(status_panel)
    editor = result.editor_output
    if editor is not None:
        editor_cards = "".join([
            _editor_card("Read first", editor.executive_summary, "primary"),
            _editor_card("Why this verdict", editor.verdict_explanation, "rationale"),
            _editor_card("Cross-table note", editor.cross_table_evaluation, "cross"),
            _editor_card("Priority focus", editor.priority_ranking, "priority"),
        ])
        sections.append(
            "<section class=\"ai-section editor-section\">"
            "<div class=\"section-heading\">"
            "<p class=\"eyebrow\">Executive Interpretation</p>"
            "<h2>What the data scientist should notice first</h2>"
            "</div>"
            f"<div class=\"agent-meta\">Editor · {html.escape(_agent_meta(details.get('editor'), 'guardrail passed'))}</div>"
            f"<div class=\"editor-insight-grid\">{editor_cards}</div>"
            "</section>"
        )

    if result.analyst_outputs:
        sections.append("<section class=\"ai-section analyst-sections\">")
        sections.append(
            "<div class=\"section-heading\">"
            "<p class=\"eyebrow\">Evidence Review</p>"
            "<h2>Guardrailed analyst notes</h2>"
            "</div>"
        )
        for output in result.analyst_outputs:
            status = "passed" if output.guardrail_passed else "failed"
            detail = details.get(output.cluster_type)
            sections.append(_cluster_evidence_card(output, verdict, detail, status))
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
        ai_analysis_content=_agent_content(multi_agent_result, verdict),
        statistical_overview=_statistical_overview(verdict),
        profile_viewer_html=_profile_viewer_html(ydata_html),
        guardrail_status=html.escape(guardrail_status),
        provider=html.escape(provider),
        model_info=html.escape(model_info),
        timestamp=html.escape(timestamp),
        css_content=_load_css(),
        js_content=_load_js(),
    )
