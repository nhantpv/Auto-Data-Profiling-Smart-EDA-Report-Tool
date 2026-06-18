"""HTML Merger — ghép multi-agent output + ydata HTML thành 1 file Tabbed HTML.

Xem ARCHITECT v5.4 §5.8 (2-Tier Delivery).
"""
from __future__ import annotations

import base64
import html
import math
import re
from datetime import datetime, timezone
from pathlib import Path

from ontology.models import DatasetVerdict, IssueSummary, MultiAgentResult


# ── Standalone-HTML helpers ───────────────────────────────────────────────────

def _img_to_data_uri(path: Path) -> str:
    """Read a PNG/JPG file and return a data: URI string for inline embedding."""
    try:
        data = path.read_bytes()
        b64 = base64.b64encode(data).decode("ascii")
        suffix = path.suffix.lower().lstrip(".")
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "gif": "image/gif", "svg": "image/svg+xml"}.get(suffix, "image/png")
        return f"data:{mime};base64,{b64}"
    except Exception:
        return ""  # silently skip missing files


def _ydata_to_srcdoc(html_path: Path) -> str:
    """Read a YData HTML profile file and return an HTML-escaped string for srcdoc."""
    try:
        content = html_path.read_text(encoding="utf-8", errors="replace")
        # Escape for use inside srcdoc="..."
        return content.replace("&", "&amp;").replace('"', "&quot;")
    except Exception:
        return ""


def _inline_assets(html_str: str, out_dir: Path) -> str:
    """Post-process assembled HTML to make it fully self-contained.

    Pass 1: Replace img src="*.png|jpg|..." → base64 data URI
    Pass 2: Replace iframe src="*.html"    → srcdoc="..." (escaped HTML content)

    Both passes skip absolute URLs and already-inlined data URIs.
    """
    IMG_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"}

    # ── Pass 1: Images ────────────────────────────────────────────────────────
    # Match:  src="relative/path/to/file.png"  (inside any tag)
    #         also handles single-quoted variants
    _SRC_RE = re.compile(
        r'\bsrc=(["\'])((?!data:|https?://|//)[^"\'>\s]+)(\1)',
        re.IGNORECASE,
    )

    def _replace_src(m: re.Match) -> str:
        quote = m.group(1)
        path_val = m.group(2)
        suffix = Path(path_val).suffix.lower()

        if suffix in IMG_EXTS:
            candidate = out_dir / path_val
            if candidate.exists():
                data_uri = _img_to_data_uri(candidate)
                if data_uri:
                    return f'src={quote}{data_uri}{quote}'

        return m.group(0)  # leave unchanged

    html_str = _SRC_RE.sub(_replace_src, html_str)

    # ── Pass 2: YData iframes ────────────────────────────────────────────────
    # Match full <iframe ...> tag so we can replace src= inside it
    _IFRAME_RE = re.compile(
        r'(<iframe\b[^>]*?\bsrc=)(["\'])([^"\'>\s]+\.html)\2([^>]*>)',
        re.IGNORECASE | re.DOTALL,
    )

    def _replace_iframe(m: re.Match) -> str:
        prefix = m.group(1)   # "<iframe ... src="  — everything up to the value
        quote  = m.group(2)   # quote char
        path_val = m.group(3) # e.g. "statistical_profile_xxx.html"
        suffix_tag = m.group(4)  # rest of tag after closing quote

        if path_val.startswith(("http:", "https:", "//")):
            return m.group(0)

        candidate = out_dir / path_val
        if candidate.exists():
            srcdoc_val = _ydata_to_srcdoc(candidate)
            if srcdoc_val:
                # Replace src= with srcdoc= keeping all other attributes intact
                # prefix already contains "<iframe ... src=" — swap "src=" → "srcdoc="
                new_prefix = re.sub(r'\bsrc=$', 'srcdoc=', prefix)
                return f'{new_prefix}"{srcdoc_val}"{suffix_tag}'

        return m.group(0)

    html_str = _IFRAME_RE.sub(_replace_iframe, html_str)

    return html_str


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
    """Mô tả những gì phát hiện được — không giả định use-case của người dùng."""
    critical = verdict.summary.critical
    high = verdict.summary.high
    warn = verdict.summary.warn
    if verdict.verdict.value == "NOT_READY":
        issues = []
        if critical:
            issues.append(f"{critical} vấn đề nghiêm trọng")
        if high:
            issues.append(f"{high} vấn đề mức cao")
        desc = ", ".join(issues) if issues else "nhiều vấn đề nghiêm trọng"
        return f"Dữ liệu có {desc} — cần xử lý trước khi sử dụng."
    if verdict.verdict.value == "WARN":
        desc = f"{warn} điểm cần chú ý" if warn else "một số điểm cần chú ý"
        return f"Dữ liệu có {desc} — khuyến nghị xem xét kỹ trước khi đưa vào sử dụng."
    return "Không phát hiện vấn đề chặn — dữ liệu đã qua kiểm tra chất lượng cơ bản."



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
    "missingness_bar": ("Missingness Bar", "Quét mức độ đầy đủ theo cột."),
    "dtype_distribution": ("Type Donut", "Phân bổ kiểu dữ liệu theo cột."),
    "numeric_distributions": ("Histogram Grid", "Phân phối các biến số."),
    "numeric_boxplot": ("Box Plot", "Phân tán biến số sau chuẩn hóa."),
    "correlation_heatmap": ("Correlation Heatmap", "Mối tương quan từng cặp biến số."),
    "categorical_top_values": ("Category Bar", "Giá trị phổ biến nhất trong biến phân loại."),
    # Charts mới từ Luồng 3
    "stacked_bar_issues": ("Issues by Table", "Phân bổ vấn đề theo bảng và mức độ nghiêm trọng."),
    "relationship_network": ("Table Network", "Sơ đồ mối quan hệ giữa các bảng (FK/PK)."),
    "top_correlations_bar": ("Top Correlations", "Top 10 cặp cột có tương quan mạnh nhất."),
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
    verdict_val = verdict.verdict.value
    # Derive human-readable formula explanation based on verdict
    if verdict_val == "READY":
        formula_explain = (
            f"<strong>READY</strong>: {_format_int(summary.critical)} critical, "
            f"{_format_int(summary.high)} high, {_format_int(summary.warn)} warn — "
            "Zero critical issues and at most 2 high-severity findings → dataset approved for use."
        )
    elif verdict_val == "NOT_READY":
        formula_explain = (
            f"<strong>NOT_READY</strong>: {_format_int(summary.critical)} critical issue(s) detected — "
            "any CRITICAL finding blocks dataset use until resolved."
        )
    else:  # WARN
        formula_explain = (
            f"<strong>WARN</strong>: {_format_int(summary.critical)} critical, "
            f"{_format_int(summary.high)} high — "
            "No critical issues but high-severity findings require review before production use."
        )
    return f"""
<section class="science-brief science-brief-{html.escape(verdict_val)}">
  <div class="science-brief-copy">
    <p class="eyebrow">Data Science Brief</p>
    <h2>{html.escape(_verdict_headline(verdict))}</h2>
    <p><strong>Decision signal:</strong> {html.escape(verdict.verdict_rationale)}</p>
    <details class="verdict-formula-details">
      <summary>Xem công thức phán quyết ▾</summary>
      <div class="verdict-formula-body">
        <p>{formula_explain}</p>
        <table class="verdict-formula-table">
          <thead><tr><th>Verdict</th><th>Điều kiện</th></tr></thead>
          <tbody>
            <tr class="{"vf-active" if verdict_val == "READY" else ""}"><td>✅ READY</td><td>0 Critical AND ≤ 2 High</td></tr>
            <tr class="{"vf-active" if verdict_val == "WARN" else ""}"><td>⚠️ WARN</td><td>0 Critical AND &gt; 2 High</td></tr>
            <tr class="{"vf-active" if verdict_val == "NOT_READY" else ""}"><td>❌ NOT_READY</td><td>≥ 1 Critical</td></tr>
          </tbody>
        </table>
      </div>
    </details>
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
            '<section class="priority-spotlight">'
            '<div class="section-heading"><p class="eyebrow">Vấn Đề Cần Chú Ý</p>'
            '<h2>Không có vấn đề nào được phân hạng.</h2></div>'
            '<p class="muted-copy">Xem xét báo cáo thống kê chi tiết ở từng tab bảng.</p>'
            '</section>'
        )

    # Dedup: giữ issue có severity cao nhất cho mỗi (issue_type, affected_table, affected_column) combo
    seen: dict[tuple, object] = {}
    for issue in verdict.top_issues:
        key = (issue.issue_type, issue.affected_table, issue.affected_column)
        existing = seen.get(key)
        if existing is None or issue.effective_severity.value > existing.effective_severity.value:
            seen[key] = issue
    deduped = list(seen.values())

    rows: list[str] = []
    for issue in deduped:
        severity = issue.effective_severity.value
        key = _severity_key(severity)

        # Use affected_table directly (it's a proper field on IssueSummary)
        table_name = issue.affected_table or "—"

        # affected_column: for multi-table pipeline it may still have "table.col" prefix
        raw_col = issue.affected_column or "—"
        if raw_col != "—" and "." in raw_col:
            # Strip table prefix added by _prefix_issue if present
            _tbl, col_part = raw_col.split(".", 1)
            # If stripped table matches affected_table, use col_part; else keep raw
            if issue.affected_table and _tbl == issue.affected_table:
                col_name = col_part
            else:
                col_name = raw_col  # unexpected format, show as-is
        else:
            col_name = raw_col  # no prefix, already just the column name

        affected = _format_int(issue.affected_count) if issue.affected_count else "—"
        rows.append(
            f'<tr class="severity-row-{html.escape(key)}">'
            f'<td><code class="table-name">{html.escape(table_name)}</code></td>'
            f'<td><code>{html.escape(col_name)}</code></td>'
            f'<td><code>{html.escape(issue.issue_type)}</code></td>'
            f'<td><span class="badge-{html.escape(key)}">{html.escape(severity)}</span></td>'
            f'<td class="number-cell">{affected}</td>'
            f'<td class="rationale-cell">{html.escape(issue.rationale)}</td>'
            f'</tr>'
        )
    return (
        '<section class="priority-spotlight">'
        '<div class="section-heading">'
        '<p class="eyebrow">Vấn Đề Cần Chú Ý</p>'
        '<h2>Các vấn đề có tác động lớn nhất</h2>'
        '<p class="muted-copy">Liệt kê theo mức độ nghiêm trọng giảm dần.</p>'
        '</div>'
        '<div class="table-scroll-wrapper">'
        '<table class="issue-spotlight-table">'
        '<thead><tr>'
        '<th>Bảng</th><th>Cột</th><th>Loại vấn đề</th><th>Mức độ</th><th>Dòng bị ảnh hưởng</th><th>Nhận xét</th>'
        '</tr></thead>'
        '<tbody>'
        f"{''.join(rows)}"
        '</tbody></table></div>'
        '</section>'
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
    "COMPOSITE_PK_DUPLICATE": (
        "Composite primary-key integrity blocker",
        "The combined key tuple is not unique — rows share the same composite PK, violating the uniqueness constraint on the junction table.",
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



def _structured_table_result_card(
    result: object,
    chart_paths: dict[str, str] | None = None,
    col_stats: dict | None = None,
) -> str:
    """Render AnalystTableResult thành HTML card — nhúng chart và stats cùng chỗ."""
    from reporting.l4_report import render_table_result_html
    return render_table_result_html(
        result,  # type: ignore[arg-type]
        chart_paths=chart_paths or {},
        col_stats=col_stats or {},
    )


def _table_charts_for(table_name: str, overview_charts: dict[str, str]) -> dict[str, str]:
    """Lọc chart liên quan đến bảng cụ thể từ overview_charts."""
    result: dict[str, str] = {}
    prefix = f"{table_name}."
    for key, path in overview_charts.items():
        if key.startswith(prefix):
            short_key = key[len(prefix):]
            result[short_key] = path
        elif "." not in key:
            # Chart không có prefix bảng → dùng cho tất cả (single-table mode)
            result[key] = path
    return result


def _parse_profile_links(profile_fragment: str) -> dict[str, str]:
    """Extract {table_name → filename} từ profile_fragment HTML (được tạo bởi run_pipeline.py).

    HTML format của _profile_artifact_fragment:
      <article class="profile-export-card">
        <div>
          <span>table_name</span>
          <strong>filename.html</strong>
          ...
        </div>
        <a href="statistical_profile_xxx.html" ...>Open profile</a>
      </article>
    """
    import re as _re
    links: dict[str, str] = {}

    # Strategy 1: Tìm từng <article class="profile-export-card"> và extract span + href
    article_pattern = _re.compile(
        r'<article[^>]*profile-export-card[^>]*>(.*?)</article>',
        _re.DOTALL | _re.IGNORECASE,
    )
    span_pattern = _re.compile(r'<span>([^<]+)</span>', _re.IGNORECASE)
    href_pattern = _re.compile(
        r'<a\s[^>]*href="(statistical_profile[^"]*\.html)"',
        _re.IGNORECASE,
    )
    for article_match in article_pattern.finditer(profile_fragment):
        article_html = article_match.group(1)
        span_m = span_pattern.search(article_html)
        href_m = href_pattern.search(article_html)
        if span_m and href_m:
            table_name = span_m.group(1).strip()
            filename = href_m.group(1).strip()
            links[table_name] = filename

    # Strategy 2 (fallback): Pair <span>name</span>...<a href="statistical_profile_*.html">
    if not links:
        pair_pattern = _re.compile(
            r'<span>([^<]+)</span>.*?<a[^>]+href="(statistical_profile[^"]*\.html)"',
            _re.DOTALL,
        )
        for m in pair_pattern.finditer(profile_fragment):
            links[m.group(1).strip()] = m.group(2).strip()

    # Strategy 3 (single-table fallback)
    if not links:
        single = _re.search(r'href="(statistical_profile\.html)"', profile_fragment)
        if single:
            links["dataset"] = single.group(1)

    return links


def _col_stats_for_table(
    table_name: str,
    findings_columns: dict | None,
) -> dict:
    """Lọc ColumnStats của các cột thuộc bảng này."""
    if not findings_columns:
        return {}
    result = {}
    prefix = f"{table_name}."
    for col_key, stats in findings_columns.items():
        if col_key.startswith(prefix):
            result[col_key[len(prefix):]] = stats
        elif "." not in col_key:
            result[col_key] = stats
    return result


def _build_data_sample_html(df: object, table_name: str, n_rows: int = 5) -> str:
    """Build a compact HTML data sample table for a given DataFrame.

    Returns empty string if df is None or import fails.
    """
    try:
        import pandas as pd  # type: ignore
        if df is None or not isinstance(df, pd.DataFrame) or df.empty:
            return ""
        sample = df.head(n_rows)
        # Build header
        th_cells = "".join(f"<th>{html.escape(str(c))}</th>" for c in sample.columns)
        # Build rows
        tr_rows: list[str] = []
        for _, row in sample.iterrows():
            tds = []
            for val in row:
                if val is None or (isinstance(val, float) and __import__('math').isnan(val)):
                    tds.append('<td class="null-cell">NULL</td>')
                else:
                    cell_str = str(val)
                    if len(cell_str) > 60:
                        cell_str = cell_str[:57] + "..."
                    tds.append(f"<td>{html.escape(cell_str)}</td>")
            tr_rows.append(f"<tr>{''.join(tds)}</tr>")
        return (
            '<section class="data-sample-section">'
            '<div class="section-heading">'
            '<p class="eyebrow">Data Sample</p>'
            f'<h3>5 dòng đầu — <code>{html.escape(table_name)}</code></h3>'
            '</div>'
            '<div class="data-sample-wrapper">'
            '<table class="data-sample-table">'
            f'<thead><tr>{th_cells}</tr></thead>'
            f'<tbody>{"".join(tr_rows)}</tbody>'
            '</table></div></section>'
        )
    except Exception:
        return ""


def _table_tab_panel(
    table_result: object,
    tab_id: str,
    overview_charts: dict[str, str],
    profile_links: dict[str, str],
    findings_columns: dict | None,
    is_active: bool = False,
    table_data_samples: dict[str, str] | None = None,
) -> str:
    """Render nội dung 1 tab bảng: AI insights trước, YData stats ở dưới."""
    table_name: str = getattr(table_result, "table_name", "")
    chart_paths = _table_charts_for(table_name, overview_charts)
    col_stats = _col_stats_for_table(table_name, findings_columns)

    # Fuzzy profile lookup: thử tên gốc, tên normalized (- → _), và tên khác convention
    def _lookup_profile(name: str) -> str | None:
        if name in profile_links:
            return profile_links[name]
        norm = name.replace("-", "_").replace(" ", "_")
        if norm in profile_links:
            return profile_links[norm]
        # Thử reverse (underscore → hyphen)
        hyph = name.replace("_", "-")
        if hyph in profile_links:
            return profile_links[hyph]
        # Case-insensitive fallback
        name_lower = name.lower()
        for k, v in profile_links.items():
            if k.lower().replace("-", "_") == name_lower.replace("-", "_"):
                return v
        return None

    profile_file = _lookup_profile(table_name) or profile_links.get("dataset")

    # YData profile section — đặt ở DƯỚI phần AI analysis
    ydata_section = ""
    if profile_file:
        ydata_section = (
            f'<div class="ydata-profile-embed">'
            f'<div class="ydata-profile-header">'
            f'<span class="ydata-label">📊 Thống kê Ydata — <strong>{html.escape(table_name)}</strong></span>'
            f'<a href="{html.escape(profile_file, quote=True)}" target="_blank" rel="noopener" '
            f'class="ydata-fullscreen-btn">↗ Mở toàn màn hình</a>'
            f'</div>'
            f'<iframe src="{html.escape(profile_file, quote=True)}" '
            f'class="ydata-iframe" '
            f'title="YData profile — {html.escape(table_name)}" '
            f'loading="lazy" '
            f'sandbox="allow-scripts allow-same-origin">'
            f'</iframe>'
            f'</div>'
        )

    sample_html = (table_data_samples or {}).get(table_name, "")

    content = _structured_table_result_card(table_result, chart_paths, col_stats)
    active_attr = ' class="tab-content active"' if is_active else ' class="tab-content"'
    hidden_attr = "" if is_active else " hidden"
    return (
        f'<section id="tab-{tab_id}"{active_attr}'
        f' role="tabpanel" aria-labelledby="tab-button-{tab_id}"{hidden_attr}>'
        f'{content}'
        f'{sample_html}'
        f'{ydata_section}'
        f'</section>'
    )


def _missingness_diagnostic_table(findings: object) -> str:
    """Render bảng tổng hợp MCAR/MAR/INDETERMINATE cho toàn bộ cột có missing.

    Hiển thị kể cả cột dưới anomaly threshold — cài mà badge inline không có.
    Return empty string nếu không có cột nào có mechanism được phân loại.
    """
    if findings is None:
        return ""
    columns = getattr(findings, "columns", {}) or {}
    rows = []
    for name, stats in columns.items():
        mechanism = getattr(stats, "missingness_mechanism", None)
        p_missing = getattr(stats, "p_missing", None)
        if mechanism is None or not p_missing or p_missing <= 0:
            continue
        # Display name: strip table prefix for single-table mode
        display_name = name.split(".", 1)[1] if "." in name else name
        _MECH_INFO = {
            "MAR": (
                "cstat-mar",
                "MAR ⚠️",
                "Missing At Random — pattern có thể dự đoán từ cột khác. Dùng conditional impute.",
            ),
            "MCAR_CONSISTENT": (
                "cstat-mcar",
                "MCAR ✅",
                "Missing Completely At Random — ngẫu nhiên thực sự. Impute mean/median an toàn.",
            ),
            "INDETERMINATE": (
                "cstat-indet",
                "INDET. ?",
                "Quá ít giá trị thiếu để xác định cơ chế. Kiểm tra lại khi có thêm dữ liệu.",
            ),
            "STRUCTURAL_ABSENT": (
                "cstat-structural",
                "OPTIONAL 🔵",
                "Cột tùy chọn — NULL có thể có nghĩa 'không áp dụng' (vd: Fax, Company). "
                "KHÔNG nên impute. Xác nhận với chủ sở hữu dữ liệu trước khi xử lý.",
            ),
        }
        css_cls, badge_label, action_text = _MECH_INFO.get(
            mechanism, ("cstat-indet", html.escape(mechanism), "")
        )

        rows.append(
            f'<tr>'
            f'<td><code>{html.escape(display_name)}</code></td>'
            f'<td class="number-cell">{p_missing * 100:.1f}%</td>'
            f'<td><span class="cstat-pill {css_cls}">{badge_label}</span></td>'
            f'<td class="rationale-cell">{html.escape(action_text)}</td>'
            f'</tr>'
        )
    if not rows:
        return ""
    header = (
        '<section class="ai-section" style="margin-top:20px">'
        '<div class="section-heading">'
        '<p class="eyebrow">Phân Tích Missing Value</p>'
        '<h2>Missingness Diagnostic — Cơ Chế Thiếu Dữ Liệu</h2>'
        '</div>'
        '<div class="table-scroll-wrapper" style="margin-top:12px">'
        '<table class="issue-spotlight-table">'
        '<thead><tr>'
        '<th>Cột</th><th>% Thiếu</th><th>Cơ chế</th><th>Hành động khuyến nghị</th>'
        '</tr></thead>'
        '<tbody>'
    )
    footer = '</tbody></table></div></section>'
    return header + "".join(rows) + footer


def _overview_tab_panel(
    result: MultiAgentResult,
    verdict: DatasetVerdict,
    profile_fragment: str,
    is_active: bool = True,
    findings: object = None,
) -> str:
    """Tab Tổng quan: verdict brief + issue table + executive summary + cross-table.

    Không có chart per-table (missingness/boxplot) — những chart đó thuộc về tab từng bảng.
    Profile links đã gắn vào từng tab bảng, không cần lặp ở đây.
    """
    sections: list[str] = []

    # 1. Science brief (verdict headline + score counts)
    sections.append(_science_brief(verdict))

    # 2. Profile Diagnostics (shape/KPI) — hiện sớm để reader có context ngay
    sections.append(f'<div class="stats-workbench">{_statistical_overview(verdict)}</div>')

    # 3. Missingness Diagnostic table — hiển thị toàn bộ cột có missing (kể cả dưới threshold)
    miss_table = _missingness_diagnostic_table(findings)
    if miss_table:
        sections.append(miss_table)

    # 3. Issue spotlight — dạng bảng (Bảng|Đột|Loại|Mức độ|Dòng bị ảnh hưởng)
    sections.append(_issue_spotlight(verdict))

    # 4. Executive summary + Feature usability từ Editor
    if result.editor_structured is not None:
        from reporting.l4_report import render_editor_structured_html
        details = _agent_detail_lookup(result)
        agent_meta_str = _agent_meta(details.get("structured_editor"), "guardrail passed")
        rendered = render_editor_structured_html(result.editor_structured)

        # ── Fallback banner (Issue 2B) ─────────────────────────────────────
        # Detect which case: no API key vs LLM failed guardrail
        editor_detail = details.get("structured_editor")
        used_fb = result.used_fallback or bool(
            editor_detail and editor_detail.get("used_fallback")
        )
        retry_count = (editor_detail or {}).get("retry_count", 0)
        llm_was_attempted = bool(retry_count and retry_count > 0)

        fallback_banner = ""
        if used_fb:
            if llm_was_attempted:
                # Guardrail failure after N retries
                fallback_banner = (
                    '<div class="fallback-banner fallback-banner-retry">'
                    '<span class="fallback-icon">⚠️</span>'
                    '<div>'
                    '<strong>Phân tích LLM không vượt qua guardrail</strong> '
                    f'(sau {retry_count} lần thử). '
                    'Nội dung bên dưới là phân tích <strong>rule-based tự động</strong>, '
                    'không phải nhận định của AI — độ sâu và tính cá nhân hoá bị giới hạn. '
                    'Kiểm tra log để biết lý do guardrail reject.'
                    '</div>'
                    '</div>'
                )
            else:
                # No API key configured
                fallback_banner = (
                    '<div class="fallback-banner fallback-banner-nokey">'
                    '<span class="fallback-icon">⚠️</span>'
                    '<div>'
                    '<strong>Phân tích AI không khả dụng</strong> — '
                    'API key chưa được cấu hình (<code>SMART_EDA_L4_PROVIDER=openai</code> '
                    'và <code>OPENAI_API_KEY</code> chưa set trong <code>.env</code>). '
                    'Nội dung bên dưới là phân tích <strong>rule-based tự động</strong> '
                    'dựa trên các ngưỡng cố định — không có insight từ LLM.'
                    '</div>'
                    '</div>'
                )

        sections.append(
            '<section class="ai-section editor-section">'
            '<div class="section-heading">'
            '<p class="eyebrow">Tóm Tắt Điều Hành</p>'
            '<h2>Đánh Giá Tổng Thể Chất Lượng Dữ Liệu</h2>'
            '</div>'
            f'<div class="agent-meta">AI Editor · {html.escape(agent_meta_str)}</div>'
            f'{fallback_banner}'
            f'{rendered}'
            '</section>'
        )


    # 4. Cross-table: network chart + text evaluation + correlation tables
    cross_eval = getattr(getattr(result, "editor_structured", None), "cross_table_evaluation", None)
    network_chart = verdict.dataset_meta.overview_charts.get("relationship_network")
    stacked_chart = verdict.dataset_meta.overview_charts.get("stacked_bar_issues")
    corr_chart = verdict.dataset_meta.overview_charts.get("top_correlations_bar")

    # Extract correlation fragment HTML (from _cross_table_correlation_fragment in run_pipeline.py)
    # It's embedded after the profile-export-panel section in profile_fragment
    cross_corr_html = ""
    if "<!-- smart-eda-cross-correlation -->" in profile_fragment:
        import re as _re
        m = _re.search(
            r'<!-- smart-eda-cross-correlation -->(.*?)<!-- /smart-eda-cross-correlation -->',
            profile_fragment,
            _re.DOTALL,
        )
        if m:
            cross_corr_html = m.group(1).strip()

    # Luôn render section cross-table (dù trống vẫn giải thích lý do)
    cross_parts = [
        '<section class="ai-section cross-table-section">',
        '<div class="section-heading">',
        '<p class="eyebrow">Quan Hệ Liên Bảng</p>',
        '<h2>Sơ Đồ Schema &amp; Đánh Giá Cross-Table</h2>',
        '</div>',
    ]
    if cross_eval:
        cross_parts.append(f'<p class="cross-table-eval-text">{html.escape(cross_eval)}</p>')
    elif not network_chart:
        # Không có DBML schema → giải thích
        cross_parts.append(
            '<div class="cross-table-no-schema">'
            '<p class="muted-copy">⚠️ Không phát hiện được sơ đồ schema (FK/PK) tự động.</p>'
            '<p class="muted-copy">Để hệ thống nhận diện mối quan hệ liên bảng, '
            'hãy upload file <code>.dbml</code> schema cùng với dữ liệu CSV.</p>'
            '</div>'
        )
    if network_chart:
        cross_parts.append(
            '<div class="chart-card chart-card-wide">'
            '<div class="chart-card-copy">'
            '<strong>Sơ đồ quan hệ giữa các bảng (FK/PK)</strong>'
            '<p>Mũi tên thể hiện chiều khoá ngoại. Node màu đỏ có vấn đề toàn vẹn.</p>'
            '</div>'
            f'<div class="chart-frame"><img src="{html.escape(network_chart, quote=True)}" '
            f'alt="Table relationship network" loading="lazy"></div>'
            '</div>'
        )
    if stacked_chart:
        cross_parts.append(
            '<div class="chart-card">'
            '<div class="chart-card-copy"><strong>Phân bổ vấn đề theo bảng</strong></div>'
            f'<div class="chart-frame"><img src="{html.escape(stacked_chart, quote=True)}" '
            f'alt="Issues by table stacked bar" loading="lazy"></div></div>'
        )
    if corr_chart:
        cross_parts.append(
            '<div class="chart-card">'
            '<div class="chart-card-copy"><strong>Top tương quan cross-table</strong></div>'
            f'<div class="chart-frame"><img src="{html.escape(corr_chart, quote=True)}" '
            f'alt="Top correlations bar" loading="lazy"></div></div>'
        )
    if cross_corr_html:
        cross_parts.append(cross_corr_html)
    cross_parts.append('</section>')
    sections.append("\n".join(cross_parts))

    # 6. Appendix
    if result.appendix_html:
        sections.append(result.appendix_html)

    # 7. Guardrailed L4 Comments — xuống cuối (log/debug level, user ít quan tâm)
    status_panel = _agent_status_panel(result)
    if status_panel:
        sections.append(status_panel)

    content = "\n".join(sections)
    active_attr = ' class="tab-content active"' if is_active else ' class="tab-content"'
    hidden_attr = "" if is_active else " hidden"
    return (
        f'<section id="tab-overview"{active_attr}'
        f' role="tabpanel" aria-labelledby="tab-button-overview"{hidden_attr}>'
        f'{content}'
        f'</section>'
    )



def _agent_content(result: MultiAgentResult, verdict: DatasetVerdict) -> str:
    """Legacy helper — kept for backward compat with tests.

    Trong luồng mới, merge_to_tabbed_html dùng _overview_tab_panel + _table_tab_panel.
    """
    sections: list[str] = []
    sections.append(_science_brief(verdict))
    sections.append(_visual_overview(verdict))
    sections.append(_issue_spotlight(verdict))

    details = _agent_detail_lookup(result)
    status_panel = _agent_status_panel(result)
    if status_panel:
        sections.append(status_panel)

    if result.editor_structured is not None:
        from reporting.l4_report import render_editor_structured_html
        agent_meta_str = _agent_meta(details.get("structured_editor"), "guardrail passed")
        rendered = render_editor_structured_html(result.editor_structured)
        sections.append(
            '<section class="ai-section editor-section">'
            '<div class="section-heading">'
            '<p class="eyebrow">Phân Tích AI — Senior Data Scientist</p>'
            '<h2>Tóm Tắt Điều Hành & Đánh Giá Cột</h2>'
            '</div>'
            f'<div class="agent-meta">Editor · {html.escape(agent_meta_str)}</div>'
            f'{rendered}'
            '</section>'
        )

    if result.analyst_table_results:
        sections.append('<section class="ai-section analyst-sections">')
        sections.append(
            '<div class="section-heading">'
            '<p class="eyebrow">Kiểm Tra Chi Tiết Từng Bảng</p>'
            '<h2>Phân Tích Chuyên Sâu Theo Bảng</h2>'
            '</div>'
        )
        for table_result in result.analyst_table_results:
            sections.append(_structured_table_result_card(table_result))
        sections.append('</section>')

    elif result.analyst_outputs:
        sections.append('<section class="ai-section analyst-sections">')
        sections.append(
            '<div class="section-heading">'
            '<p class="eyebrow">Evidence Review</p>'
            '<h2>Guardrailed analyst notes</h2>'
            '</div>'
        )
        for output in result.analyst_outputs:
            status = "passed" if output.guardrail_passed else "failed"
            detail = details.get(output.cluster_type)
            sections.append(_cluster_evidence_card(output, verdict, detail, status))
        sections.append('</section>')

    if result.appendix_html:
        sections.append(result.appendix_html)
    return "\n".join(sections) if sections else "<p>Không có phần phân tích AI nào được tạo ra.</p>"


def _build_user_guide_html() -> str:
    """Render tab Hướng dẫn sử dụng — nội dung tĩnh, không cần data runtime."""
    return """
<div class="table-health-section" style="max-width:900px;margin:0 auto;">

  <div class="section-heading" style="margin-bottom:24px;">
    <p class="eyebrow">Tài liệu hệ thống</p>
    <h2>📖 Hướng Dẫn Đọc Report Smart EDA</h2>
  </div>

  <!-- Quy ước severity -->
  <section class="ai-section" style="margin-bottom:28px;">
    <div class="section-heading">
      <h3 style="margin:0 0 12px;">⚡ Quy Ước Mức Độ Nghiêm Trọng</h3>
    </div>
    <div class="table-scroll-wrapper">
    <table class="issue-spotlight-table">
      <thead><tr>
        <th>Mức</th><th>Ý nghĩa</th><th>Điều kiện kích hoạt</th><th>Hành động khuyến nghị</th>
      </tr></thead>
      <tbody>
        <tr class="severity-row-critical">
          <td><span class="badge-critical">CRITICAL</span></td>
          <td>Dữ liệu không thể dùng cho phân tích</td>
          <td>Thiếu &gt;60% giá trị, trùng lặp &gt;80%, vi phạm FK nghiêm trọng</td>
          <td>Dừng pipeline, yêu cầu thu thập lại dữ liệu nguồn</td>
        </tr>
        <tr class="severity-row-high">
          <td><span class="badge-high">HIGH</span></td>
          <td>Vấn đề nghiêm trọng ảnh hưởng độ chính xác</td>
          <td>Thiếu 30–60%, outlier &gt;10%, type mismatch, cardinality bất thường</td>
          <td>Xử lý trước khi đưa vào model ML hoặc báo cáo chính thức</td>
        </tr>
        <tr class="severity-row-warn">
          <td><span class="badge-warn">WARN</span></td>
          <td>Cần chú ý, có thể ảnh hưởng kết quả</td>
          <td>Thiếu 5–30%, phân phối lệch cao, giá trị ngoại lệ nhẹ</td>
          <td>Đánh giá context, quyết định có cần xử lý không</td>
        </tr>
        <tr class="severity-row-info">
          <td><span class="badge-info">INFO</span></td>
          <td>Quan sát tham khảo, không phải lỗi</td>
          <td>Thiếu &lt;5%, distinct count thấp, zero count cao</td>
          <td>Ghi nhận, không cần hành động khẩn cấp</td>
        </tr>
      </tbody>
    </table>
    </div>
  </section>

  <!-- Missingness mechanism -->
  <section class="ai-section" style="margin-bottom:28px;">
    <div class="section-heading">
      <h3 style="margin:0 0 12px;">🔍 Cơ Chế Thiếu Dữ Liệu (Missingness Mechanism)</h3>
    </div>
    <p style="color:var(--text-secondary);font-size:14px;margin:0 0 12px;">
      Hệ thống phân loại pattern thiếu dữ liệu bằng thuật toán phân loại nhị phân (AUC-based).
      Kết quả giúp chọn chiến lược imputation phù hợp.
    </p>
    <div class="table-scroll-wrapper">
    <table class="issue-spotlight-table">
      <thead><tr>
        <th>Cơ chế</th><th>Ý nghĩa</th><th>Cách xác định</th><th>Chiến lược Imputation</th>
      </tr></thead>
      <tbody>
        <tr>
          <td><span class="cstat-pill cstat-mar">MAR ⚠️</span></td>
          <td><strong>Missing At Random</strong> — pattern thiếu có thể dự đoán từ cột khác</td>
          <td>Classifier AUC cao (&gt;0.65): biết cột bị thiếu hay không từ các cột khác</td>
          <td>⚠️ KHÔNG dùng mean/median blind. Dùng conditional impute theo nhóm hoặc model-based (KNN, MICE)</td>
        </tr>
        <tr>
          <td><span class="cstat-pill cstat-mcar">MCAR ✅</span></td>
          <td><strong>Missing Completely At Random</strong> — hoàn toàn ngẫu nhiên</td>
          <td>Classifier AUC thấp (≈0.5): không có pattern nào dự đoán được</td>
          <td>✅ An toàn khi dùng mean/median hoặc mode. Listwise deletion ít ảnh hưởng bias</td>
        </tr>
        <tr>
          <td><span class="cstat-pill cstat-mnar" style="background:#7c3aed;color:#fff;">MNAR ⛔</span></td>
          <td><strong>Missing Not At Random</strong> — giá trị thiếu liên quan đến <em>chính giá trị đó</em> (ví dụ: lương cao thường bỏ trống)</td>
          <td>Không thể phát hiện chắc chắn từ data — cần domain knowledge. Thường xuất hiện ở dữ liệu self-reported</td>
          <td>⛔ Không được impute naively — sẽ tạo bias hệ thống. Cần collect thêm dữ liệu hoặc mô hình hoá MNAR explicitly</td>
        </tr>
        <tr>
          <td><span class="cstat-pill cstat-structural" style="background:#0369a1;color:#fff;">STRUCTURAL 🏗️</span></td>
          <td><strong>Structural Absent</strong> — cột được thiết kế để trống theo business logic (ví dụ: cột <code>fax</code> trong bảng <code>customer</code>)</td>
          <td>Tỷ lệ null rất cao (thường &gt;90%) nhưng không phải lỗi — đây là đặc tính thiết kế</td>
          <td>✅ Không cần impute. Có thể drop hoặc giữ làm binary indicator (0/1 có fax hay không)</td>
        </tr>
        <tr>
          <td><span class="cstat-pill cstat-indet">INDET. ?</span></td>
          <td><strong>Indeterminate</strong> — quá ít giá trị thiếu để xác định</td>
          <td>Số lượng missing &lt; ngưỡng tối thiểu để train classifier đáng tin</td>
          <td>Xử lý thận trọng như MAR, kiểm tra lại khi có thêm dữ liệu</td>
        </tr>
      </tbody>
    </table>
    </div>
  </section>


  <!-- Loại lỗi phổ biến -->
  <section class="ai-section" style="margin-bottom:28px;">
    <div class="section-heading">
      <h3 style="margin:0 0 12px;">📋 Danh Mục Vấn Đề Hệ Thống Phát Hiện</h3>
    </div>
    <div class="table-scroll-wrapper">
    <table class="issue-spotlight-table">
      <thead><tr>
        <th>Loại vấn đề</th><th>Cách phát hiện</th><th>Ảnh hưởng phân tích</th>
      </tr></thead>
      <tbody>
        <tr>
          <td><code>PK_DUPLICATE</code></td>
          <td>Đếm giá trị trùng trên cột được khai báo là Primary Key</td>
          <td>JOIN nhân rows, aggregation sai, entity identity bị phá vỡ</td>
        </tr>
        <tr>
          <td><code>COMPOSITE_PK_DUPLICATE</code></td>
          <td>Kiểm tra uniqueness của tổ hợp (col1, col2) trong junction table</td>
          <td>Vi phạm uniqueness constraint, JOIN cho kết quả sai</td>
        </tr>
        <tr>
          <td><code>PK_NULL</code></td>
          <td>Kiểm tra NULL trên cột Primary Key</td>
          <td>Không thể identify entity, JOIN bị mất dữ liệu</td>
        </tr>
        <tr>
          <td><code>ORPHAN_FOREIGN_KEY</code></td>
          <td>Left join bảng con sang bảng cha, đếm rows không match</td>
          <td>JOIN trả về NULL hoặc mất dữ liệu, aggregation thiếu</td>
        </tr>
        <tr>
          <td><code>NON_UNIQUE_PARENT_PK</code></td>
          <td>Kiểm tra uniqueness của PK trong bảng cha được tham chiếu</td>
          <td>JOIN nhân rows phía child, tạo Cartesian product ngầm</td>
        </tr>
        <tr>
          <td><code>HIGH_MISSING_RATE</code></td>
          <td>% giá trị null vượt ngưỡng (mặc định 30%)</td>
          <td>Bias trong model, kết quả thống kê không đại diện</td>
        </tr>
        <tr>
          <td><code>HIGH_CARDINALITY</code></td>
          <td>Số giá trị distinct quá cao so với n_rows (thường &gt;50%)</td>
          <td>One-hot encoding không hiệu quả, có thể là ID column bị nhầm</td>
        </tr>
        <tr>
          <td><code>LOW_VARIANCE / CONSTANT</code></td>
          <td>Std ≈ 0 hoặc chỉ có 1 giá trị duy nhất</td>
          <td>Feature vô dụng trong ML, cần loại bỏ</td>
        </tr>
        <tr>
          <td><code>CONSTANT_COLUMN</code></td>
          <td>Tất cả giá trị trong cột giống hệt nhau (variance = 0)</td>
          <td>Zero information content, luôn nên loại khỏi feature set</td>
        </tr>
        <tr>
          <td><code>OUTLIER_RATE_HIGH</code></td>
          <td>PyOD ensemble (IForest + LOF + CBLOF) detect điểm bất thường</td>
          <td>Skew distribution, ảnh hưởng mean/std, model bị kéo lệch</td>
        </tr>
        <tr>
          <td><code>SKEWNESS_HIGH</code></td>
          <td>|skewness| &gt; 2 hoặc |kurtosis| &gt; 7</td>
          <td>Cần log-transform hoặc box-cox trước khi đưa vào linear model</td>
        </tr>
        <tr>
          <td><code>DUPLICATE_ROWS</code></td>
          <td>Hash toàn bộ row, đếm duplicate &gt; ngưỡng</td>
          <td>Overfit, bias trong tập train nếu không loại trước split</td>
        </tr>
        <tr>
          <td><code>TYPE_MISMATCH</code></td>
          <td>Schema DBML/SQL khai báo type khác với type thực tế suy ra</td>
          <td>Silent error trong pipeline downstream, parse fail ở production</td>
        </tr>
        <tr>
          <td><code>NOT_NULL_VIOLATION</code></td>
          <td>Cột được khai báo NOT NULL nhưng có giá trị null trong thực tế</td>
          <td>Vi phạm contract dữ liệu, downstream sẽ fail nếu enforce NOT NULL</td>
        </tr>
        <tr>
          <td><code>UNIQUE_VIOLATION</code></td>
          <td>Cột được khai báo UNIQUE nhưng có giá trị trùng lặp</td>
          <td>Vi phạm constraint, có thể là dấu hiệu của lỗi ETL hoặc merge sai</td>
        </tr>
        <tr>
          <td><code>FK_INTEGRITY_VIOLATION</code></td>
          <td>Foreign key không match giữa bảng con và bảng cha</td>
          <td>JOIN trả về NULL rows, aggregation sai, report thiếu dữ liệu</td>
        </tr>
        <tr>
          <td><code>PATTERN_ANOMALY</code></td>
          <td>Regex/format check (email, phone, date) — tỉ lệ fail cao</td>
          <td>Dữ liệu thô cần normalize/validate trước downstream</td>
        </tr>
        <tr>
          <td><code>INCONSISTENT_FORMAT</code></td>
          <td>Phát hiện hỗn hợp format trong cùng một cột (date format, encoding)</td>
          <td>Parse error, silent data loss khi xử lý hàng loạt</td>
        </tr>
      </tbody>
    </table>
    </div>
  </section>

  <!-- Cách đọc report -->

  <section class="ai-section">
    <div class="section-heading">
      <h3 style="margin:0 0 12px;">🗂️ Cách Điều Hướng Report</h3>
    </div>
    <div class="stats-diagnostic-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:14px;">
      <div style="padding:16px;border:1px solid var(--border);border-radius:var(--radius);background:var(--surface-soft);">
        <strong>Tổng Quan</strong>
        <p style="margin:8px 0 0;color:var(--text-secondary);font-size:13px;">
          Verdict tổng thể, bảng Missingness Diagnostic, bảng Issue Spotlight, tóm tắt điều hành từ AI, biểu đồ quan hệ liên bảng.
        </p>
      </div>
      <div style="padding:16px;border:1px solid var(--border);border-radius:var(--radius);background:var(--surface-soft);">
        <strong>Tab Bảng (Tên dataset)</strong>
        <p style="margin:8px 0 0;color:var(--text-secondary);font-size:13px;">
          Chi tiết từng vấn đề theo cột, badge MAR/MCAR/INDET inline, biểu đồ phân phối, thống kê YData nhúng.
        </p>
      </div>
      <div style="padding:16px;border:1px solid var(--border-subtle);border-radius:var(--radius);background:var(--brand-soft);">
        <strong>📖 Hướng dẫn (tab này)</strong>
        <p style="margin:8px 0 0;color:var(--text-secondary);font-size:13px;">
          Giải thích quy ước mức độ, cơ chế missingness, danh mục lỗi, và cách điều hướng report.
        </p>
      </div>
    </div>
    <p style="margin:18px 0 0;color:var(--text-muted);font-size:12px;">
      Smart EDA Report — tự động bởi pipeline AI đa tầng (YData Profiling → PyOD Anomaly → Severity Calibration → LLM Editor).
      Guardrail tự động đánh giá độ tin cậy của phần phân tích AI.
    </p>
  </section>

</div>
"""


def merge_to_tabbed_html(
    multi_agent_result: MultiAgentResult,
    verdict: DatasetVerdict,
    ydata_html: str,
    guardrail_status: str = "passed",
    model_info: str = "Analyst: gpt-4o-mini, Editor: gpt-4o",
    timestamp: str = "",
    findings_columns: dict | None = None,
    all_table_names: list[str] | None = None,
    out_dir: str | None = None,
    findings: object = None,
    table_data_samples: dict[str, str] | None = None,
) -> str:
    """Ghép tất cả thành 1 file HTML với dynamic tabs.

    Tab layout:
      - [Tổng quan] — verdict, executive summary, cross-table, statistical overview
      - [Bảng X] × N — AI insights + charts + col stats + link ydata cho từng bảng
        (kể cả bảng sạch không có issues nếu all_table_names được truyền vào)

    Args:
        multi_agent_result: Kết quả từ L4 multi-agent pipeline
        verdict: DatasetVerdict từ L2.5 aggregator
        ydata_html: profile_fragment HTML từ run_pipeline (chứa link đến .html files)
        guardrail_status: "passed" | "partial" | "failed"
        model_info: Thông tin model đã dùng
        timestamp: ISO timestamp
        findings_columns: dict[col_name, ColumnStats] để hiển thị inline stats
        all_table_names: Danh sách tất cả tên bảng cần hiển thị (kể cả bảng sạch)

    Returns:
        Complete HTML string → ghi ra smart_eda_report.html
    """
    template = _load_template()
    verdict_value = verdict.verdict.value
    icon_by_verdict = {
        "READY": "✓",
        "WARN": "⚠",
        "NOT_READY": "✗",
    }
    if not timestamp:
        timestamp = datetime.now(timezone.utc).isoformat()
    provider = str(
        multi_agent_result.guardrail_report.get("provider")
        if multi_agent_result.guardrail_report
        else ("deterministic" if multi_agent_result.used_fallback else "multi-agent")
    )

    overview_charts = verdict.dataset_meta.overview_charts or {}
    profile_links = _parse_profile_links(ydata_html)
    table_results = multi_agent_result.analyst_table_results

    # ── Build dynamic tabs ──
    tab_buttons_parts: list[str] = []
    tab_panels_parts: list[str] = []

    # Tab Tổng quan (luôn là tab đầu tiên, luôn active)
    tab_buttons_parts.append(
        '<button id="tab-button-overview" class="tab active" type="button" '
        'role="tab" aria-selected="true" aria-controls="tab-overview" data-tab="overview">'
        '<span>Tổng Quan</span>'
        '<small>Verdict &amp; Kết luận</small>'
        '</button>'
    )
    tab_panels_parts.append(
        _overview_tab_panel(multi_agent_result, verdict, ydata_html, is_active=True, findings=findings)
    )

    # Tab cho từng bảng
    safe_ids: dict[str, int] = {}
    for table_result in table_results:
        table_name: str = getattr(table_result, "table_name", "unknown")
        # Tạo safe tab id
        safe_base = "".join(c if c.isalnum() or c in "-_" else "_" for c in table_name)[:20]
        count = safe_ids.get(safe_base, 0)
        safe_ids[safe_base] = count + 1
        tab_id = safe_base if count == 0 else f"{safe_base}_{count}"

        max_sev = getattr(table_result, "column_issues", [])
        sev_icon = ""
        if max_sev:
            worst = max((i.severity for i in max_sev), key=lambda s: {"WARN": 1, "HIGH": 2, "CRITICAL": 3}.get(s, 0))
            sev_icon = {"CRITICAL": "🔴 ", "HIGH": "🟠 ", "WARN": "🟡 "}.get(worst, "")

        tab_buttons_parts.append(
            f'<button id="tab-button-{html.escape(tab_id)}" class="tab" type="button" '
            f'role="tab" aria-selected="false" aria-controls="tab-{html.escape(tab_id)}" '
            f'data-tab="{html.escape(tab_id)}">'
            f'<span>{sev_icon}{html.escape(table_name)}</span>'
            f'<small>Phân tích chi tiết</small>'
            f'</button>'
        )
        tab_panels_parts.append(
            _table_tab_panel(
                table_result,
                tab_id=tab_id,
                overview_charts=overview_charts,
                profile_links=profile_links,
                findings_columns=findings_columns,
                is_active=False,
                table_data_samples=table_data_samples,
            )
        )
    # Track which tables already have AI analysis (normalize for fuzzy match)
    analyzed_table_names: set[str] = {getattr(tr, "table_name", "") for tr in table_results}
    # Build normalized set: both raw name and hyphens-as-underscores variant
    analyzed_normalized: set[str] = set()
    for tn in analyzed_table_names:
        analyzed_normalized.add(tn.lower())
        analyzed_normalized.add(tn.lower().replace("-", "_"))
        analyzed_normalized.add(tn.lower().replace("_", "-"))

    # Thêm tab cho bảng sạch (trong all_table_names nhưng không có trong table_results)
    if all_table_names:
        for clean_table_name in all_table_names:
            # Bỏ qua nếu tên (hoặc variant normalized) đã có trong tab AI
            clean_norm = clean_table_name.lower().replace("-", "_")
            if (
                clean_table_name in analyzed_table_names
                or clean_table_name.lower() in analyzed_normalized
                or clean_norm in analyzed_normalized
            ):
                continue  # Đã có tab AI ở trên
            # Bỏ qua nếu tên trông như đường dẫn file (có / hoặc \ hoặc quá dài)
            if "/" in clean_table_name or "\\" in clean_table_name or len(clean_table_name) > 64:
                continue
            safe_base = "".join(c if c.isalnum() or c in "-_" else "_" for c in clean_table_name)[:20]
            count = safe_ids.get(safe_base, 0)
            safe_ids[safe_base] = count + 1
            tab_id = safe_base if count == 0 else f"{safe_base}_{count}"
            profile_file = profile_links.get(clean_table_name)
            ydata_embed_html = ""
            if profile_file:
                ydata_embed_html = (
                    f'<div class="ydata-profile-embed">'
                    f'<div class="ydata-profile-header">'
                    f'<span class="ydata-label">📊 Thống kê Ydata — <strong>{html.escape(clean_table_name)}</strong></span>'
                    f'<a href="{html.escape(profile_file, quote=True)}" target="_blank" rel="noopener" '
                    f'class="ydata-fullscreen-btn">↗ Mở toàn màn hình</a>'
                    f'</div>'
                    f'<iframe src="{html.escape(profile_file, quote=True)}" '
                    f'class="ydata-iframe" '
                    f'title="YData profile — {html.escape(clean_table_name)}" '
                    f'loading="lazy" '
                    f'sandbox="allow-scripts allow-same-origin">'
                    f'</iframe>'
                    f'</div>'
                )
            tab_buttons_parts.append(
                f'<button id="tab-button-{html.escape(tab_id)}" class="tab" type="button" '
                f'role="tab" aria-selected="false" aria-controls="tab-{html.escape(tab_id)}" '
                f'data-tab="{html.escape(tab_id)}">'
                f'<span>\u2705 {html.escape(clean_table_name)}</span>'
                f'<small>Không có vấn đề</small>'
                f'</button>'
            )
            tab_panels_parts.append(
                f'<section id="tab-{html.escape(tab_id)}" class="tab-content" role="tabpanel" '
                f'aria-labelledby="tab-button-{html.escape(tab_id)}" hidden>'
                f'<div class="clean-table-banner">'
                f'<span class="clean-icon">✅</span>'
                f'<div><strong>{html.escape(clean_table_name)}</strong>'
                f'<p>Không phát hiện vấn đề ở mức WARN trở lên. Bảng này được đánh giá ở mức INFO hoặc sạch.</p>'
                f'</div></div>'
                f'{ydata_embed_html}'
                f'</section>'
            )

    if not table_results:
        tab_buttons_parts.append(
            '<button id="tab-button-ai" class="tab" type="button" '
            'role="tab" aria-selected="false" aria-controls="tab-ai" data-tab="ai">'
            '<span>Phân Tích AI</span><small>Nhận định &amp; bằng chứng</small></button>'
        )
        tab_panels_parts.append(
            '<section id="tab-ai" class="tab-content" role="tabpanel" '
            'aria-labelledby="tab-button-ai" hidden>'
            + (ydata_html if ydata_html.strip() else "")
            + _agent_content(multi_agent_result, verdict)
            + '</section>'
        )

    # ── Tab Hướng dẫn sử dụng (luôn là tab cuối cùng) ──
    tab_buttons_parts.append(
        '<button id="tab-button-guide" class="tab" type="button" '
        'role="tab" aria-selected="false" aria-controls="tab-guide" data-tab="guide">'
        '<span>\U0001f4d6 H\u01b0\u1edbng d\u1eabn</span><small>C\u00e1ch \u0111\u1ecdc report</small>'
        '</button>'
    )
    tab_panels_parts.append(
        '<section id="tab-guide" class="tab-content" role="tabpanel" '
        'aria-labelledby="tab-button-guide" hidden>'
        + _build_user_guide_html()
        + '</section>'
    )

    assembled = template.format(
        verdict_class=html.escape(verdict_value),
        verdict_value=html.escape(verdict_value),
        verdict_icon=icon_by_verdict.get(verdict_value, ""),
        verdict_rationale=html.escape(_verdict_headline(verdict)),
        file_name=html.escape(verdict.dataset_meta.file_name),
        n=verdict.dataset_meta.n,
        n_var=verdict.dataset_meta.n_var,
        p_cells_missing=html.escape(f"{verdict.dataset_meta.p_cells_missing * 100:.1f}%"),
        tab_buttons="\n".join(tab_buttons_parts),
        tab_panels="\n".join(tab_panels_parts),
        guardrail_status=html.escape(guardrail_status),
        provider=html.escape(provider),
        model_info=html.escape(model_info),
        timestamp=html.escape(timestamp),
        css_content=_load_css(),
        js_content=_load_js(),
    )

    # Inline all external assets so the downloaded file is fully self-contained
    if out_dir:
        assembled = _inline_assets(assembled, Path(out_dir))

    return assembled




def _structured_editor_section(editor: object, details: dict) -> str:
    """Render EditorStructuredOutput thành section HTML."""
    from reporting.l4_report import render_editor_structured_html
    rendered = render_editor_structured_html(editor)  # type: ignore[arg-type]
    agent_meta = _agent_meta(details.get("structured_editor"), "guardrail passed")
    return (
        "<section class=\"ai-section editor-section\">"
        "<div class=\"section-heading\">"
        "<p class=\"eyebrow\">Phân Tích AI — Senior Data Scientist</p>"
        "<h2>Tóm Tắt Điều Hành &amp; Đánh Giá Feature</h2>"
        "</div>"
        f"<div class=\"agent-meta\">Editor · {html.escape(agent_meta)}</div>"
        f"{rendered}"
        "</section>"
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

    # ── Luồng 3 (Structured JSON pipeline) ──
    if result.editor_structured is not None:
        sections.append(_structured_editor_section(result.editor_structured, details))

    if result.analyst_table_results:
        sections.append("<section class=\"ai-section analyst-sections\">")
        sections.append(
            "<div class=\"section-heading\">"
            "<p class=\"eyebrow\">Kiểm Tra Chi Tiết Từng Bảng</p>"
            "<h2>Phân Tích Chuyên Sâu Theo Bảng</h2>"
            "</div>"
        )
        for table_result in result.analyst_table_results:
            sections.append(_structured_table_result_card(table_result))
        sections.append("</section>")

    # ── Luồng 2 legacy fallback (nếu vẫn dùng analyst_outputs) ──
    elif result.analyst_outputs:
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
    return "\n".join(sections) if sections else "<p>Không có phần phân tích AI nào được tạo ra.</p>"


