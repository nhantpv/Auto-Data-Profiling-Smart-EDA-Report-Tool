"""Tests cho L4 Structured Multi-Agent pipeline."""
import json

from ontology.models import (
    AnomalyRecord,
    DataQualityFindings,
    DatasetMeta,
    DatasetVerdict,
    Severity,
    Verdict,
    VerdictSummary,
)
from reporting import l4_report
from reporting.l4_report import generate_multi_agent_report


def _sample_l4_inputs():
    meta = DatasetMeta(
        file_name="data.csv",
        n=10,
        n_var=2,
        memory_size=0,
        p_cells_missing=0.1,
    )
    findings = DataQualityFindings(
        dataset_meta=meta,
        columns={},
        anomalies=[
            AnomalyRecord(
                issue_type="MISSINGNESS",
                description="missing",
                severity=Severity.WARN,
                affected_count=1,
                affected_percent=0.1,
                affected_column="age",
                top_10_samples=[],
            )
        ],
    )
    verdict = DatasetVerdict(
        dataset_meta=meta,
        verdict=Verdict.WARN,
        verdict_rationale="Needs review",
        summary=VerdictSummary(total_issues=1, warn=1),
    )
    return findings, verdict


def test_call_openai_uses_chat_completions_payload(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.delenv("SMART_EDA_L4_API_MODE", raising=False)
    captured = {}

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, _exc_type, _exc, _tb):
            return False

        def read(self):
            return json.dumps({
                "choices": [{"message": {"content": "ok"}}],
            }).encode("utf-8")

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["body"] = json.loads(request.data.decode("utf-8"))
        captured["timeout"] = timeout
        return FakeResponse()

    monkeypatch.setattr(l4_report.urllib.request, "urlopen", fake_urlopen)

    text = l4_report._call_openai("user prompt", "system prompt", "SMART_EDA_TEST_MODEL", "gpt-test")

    assert text == "ok"
    assert captured["url"] == "https://api.openai.com/v1/chat/completions"
    assert captured["body"]["messages"] == [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "user prompt"},
    ]
    assert "instructions" not in captured["body"]
    assert "input" not in captured["body"]


def test_multi_agent_l4_deterministic_fallback_passes_guardrail(monkeypatch):
    """Fallback deterministc: không cần LLM, vẫn trả HTML hợp lệ."""
    monkeypatch.delenv("SMART_EDA_L4_PROVIDER", raising=False)
    findings, verdict = _sample_l4_inputs()

    text, guardrail, result = generate_multi_agent_report(findings, verdict)

    # Structured pipeline trả HTML với các element tiếng Việt
    assert "executive-summary" in text
    assert "data.csv" in text
    assert guardrail.status == "passed"
    assert result.analyst_table_results[0].guardrail_passed is True
    assert result.guardrail_report["agents"]


def test_multi_agent_l4_retries_llm_until_valid_json(monkeypatch):
    """LLM trả JSON hợp lệ sau lần retry — analyst và editor đều dùng JSON schema mới."""
    monkeypatch.setattr(l4_report, "_llm_enabled", lambda: True)
    calls = {"analyst": 0, "editor": 0}

    analyst_json = json.dumps({
        "table_name": "default",
        "table_overview": "Bảng có 1 vấn đề.",
        "column_issues": [{
            "column_name": "age",
            "severity": "WARN",
            "problem": "Thiếu 1 giá trị (10.0%).",
            "ml_consequence": "Có thể ảnh hưởng đến các mô hình Linear Regression.",
            "suggested_action": "Nên xem xét imputation.",
            "evidence_ref": None,
        }],
    })

    editor_json = json.dumps({
        "executive_summary": "Dataset data.csv có 10 dòng và 2 cột.",
        "feature_usability": [{"column": "age", "status": "needs_work", "reason": "Thiếu giá trị."}],
        "fix_priority": ["default.age"],
        "cross_table_evaluation": None,
        "verdict_explanation": "Cần xem xét lại.",
    })

    async def fake_call(prompt, instructions, model_env, default_model):
        if model_env == "SMART_EDA_L4_ANALYST_MODEL":
            calls["analyst"] += 1
            if calls["analyst"] == 1:
                return "invalid json"
            return analyst_json
        calls["editor"] += 1
        return editor_json

    monkeypatch.setattr(l4_report, "_call_openai_async", fake_call)
    findings, verdict = _sample_l4_inputs()

    _text, guardrail, result = generate_multi_agent_report(findings, verdict)

    assert guardrail.status == "passed"
    # Analyst phải retry 1 lần do invalid json lần đầu
    assert result.analyst_table_results[0].retry_count == 1
    assert result.guardrail_report["agents"]


def test_multi_agent_l4_records_llm_errors_on_fallback(monkeypatch):
    """Khi LLM lỗi liên tục → fallback deterministc, guardrail vẫn pass."""
    monkeypatch.setattr(l4_report, "_llm_enabled", lambda: True)

    async def fake_call(_prompt, _instructions, _model_env, _default_model):
        raise RuntimeError("HTTP 400 bad request")

    monkeypatch.setattr(l4_report, "_call_openai_async", fake_call)
    findings, verdict = _sample_l4_inputs()

    _text, guardrail, result = generate_multi_agent_report(findings, verdict)

    assert guardrail.status == "passed"
    assert result.used_fallback is True
    llm_errors = result.guardrail_report.get("llm_errors", [])
    assert any("HTTP 400 bad request" in error for error in llm_errors)


def test_multi_agent_l4_renders_appendix_html(monkeypatch):
    """Phụ lục HTML được render đúng khi có nhiều issues."""
    monkeypatch.delenv("SMART_EDA_L4_PROVIDER", raising=False)
    meta = DatasetMeta(
        file_name="data.csv",
        n=10,
        n_var=2,
        memory_size=0,
        p_cells_missing=0.1,
    )
    findings = DataQualityFindings(
        dataset_meta=meta,
        columns={},
        anomalies=[
            AnomalyRecord(
                issue_type=f"ISSUE_{index}",
                description="issue",
                severity=Severity.WARN,
                affected_count=index + 1,
                affected_percent=0.1,
                affected_column=f"col_{index}",
                top_10_samples=[],
            )
            for index in range(6)
        ],
    )
    verdict = DatasetVerdict(
        dataset_meta=meta,
        verdict=Verdict.WARN,
        verdict_rationale="Needs review",
        summary=VerdictSummary(total_issues=6, warn=6),
    )

    _text, guardrail, result = generate_multi_agent_report(findings, verdict)

    assert guardrail.status == "passed"
    assert "<table>" in result.appendix_html
    assert "ISSUE_0" in result.appendix_html
    assert "col_0" in result.appendix_html
