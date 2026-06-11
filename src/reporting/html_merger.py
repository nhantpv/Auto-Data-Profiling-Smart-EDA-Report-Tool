"""HTML Merger — ghép multi-agent output + ydata HTML thành 1 file Tabbed HTML.

Xem ARCHITECT v5.4 §5.8 (2-Tier Delivery).
"""
from __future__ import annotations

import html
from pathlib import Path
from typing import Optional

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
    # TODO: Member B implement
    raise NotImplementedError("merge_to_tabbed_html() — Member B implement")
