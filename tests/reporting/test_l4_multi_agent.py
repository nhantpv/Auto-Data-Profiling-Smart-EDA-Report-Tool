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
    monkeypatch.delenv("SMART_EDA_L4_PROVIDER", raising=False)
    findings, verdict = _sample_l4_inputs()

    text, guardrail, result = generate_multi_agent_report(findings, verdict)

    assert "L4 Guarded EDA Report" in text
    assert guardrail.status == "passed"
    assert result.analyst_outputs[0].guardrail_passed is True
    assert guardrail.agents
    assert result.guardrail_report["agents"]


def test_multi_agent_l4_retries_llm_until_guardrail_passes(monkeypatch):
    monkeypatch.setattr(l4_report, "_llm_enabled", lambda: True)
    calls = {"analyst": 0, "editor": 0}

    async def fake_call(prompt, instructions, model_env, default_model):
        if model_env == "SMART_EDA_L4_ANALYST_MODEL":
            calls["analyst"] += 1
            if calls["analyst"] == 1:
                return "Dataset has `999` rows."
            return "### `MISSINGNESS`\n\nAffected scope: `age`. Affected rows: `1`."
        calls["editor"] += 1
        if calls["editor"] == 1:
            return '{"executive_summary":"Dataset has 999 rows","verdict_explanation":"Needs review","priority_ranking":"MISSINGNESS"}'
        return (
            "```json\n"
            '{"executive_summary":"Dataset `data.csv` has `10` rows",'
            '"verdict_explanation":"Needs review","priority_ranking":"MISSINGNESS"}'
            "\n```"
        )

    monkeypatch.setattr(l4_report, "_call_openai_async", fake_call)
    findings, verdict = _sample_l4_inputs()

    _text, guardrail, result = generate_multi_agent_report(findings, verdict)

    assert guardrail.status == "passed"
    assert result.analyst_outputs[0].retry_count == 1
    assert result.editor_output.retry_count == 1
    assert guardrail.agents[-1]["agent"] == "editor"


def test_multi_agent_l4_records_llm_errors_on_fallback(monkeypatch):
    monkeypatch.setattr(l4_report, "_llm_enabled", lambda: True)

    async def fake_call(_prompt, _instructions, _model_env, _default_model):
        raise RuntimeError("HTTP 400 bad request")

    monkeypatch.setattr(l4_report, "_call_openai_async", fake_call)
    findings, verdict = _sample_l4_inputs()

    _text, guardrail, result = generate_multi_agent_report(findings, verdict)

    assert guardrail.status == "passed"
    assert guardrail.used_fallback is True
    assert result.used_fallback is True
    assert guardrail.llm_errors
    assert guardrail.agents
    assert any("HTTP 400 bad request" in error for error in guardrail.llm_errors)


def test_multi_agent_l4_repairs_editor_causal_language(monkeypatch):
    monkeypatch.setattr(l4_report, "_llm_enabled", lambda: True)

    async def fake_call(_prompt, _instructions, model_env, _default_model):
        if model_env == "SMART_EDA_L4_ANALYST_MODEL":
            return "### `MISSINGNESS`\n\nAffected scope: `age`. Affected rows: `1`."
        return (
            '{"executive_summary":"Dataset `data.csv` has `10` rows.",'
            '"verdict_explanation":"Verdict `WARN` due to `MISSINGNESS` in `age`.",'
            '"priority_ranking":"`MISSINGNESS`"}'
        )

    monkeypatch.setattr(l4_report, "_call_openai_async", fake_call)
    findings, verdict = _sample_l4_inputs()

    _text, guardrail, result = generate_multi_agent_report(findings, verdict)

    assert guardrail.status == "passed"
    assert result.used_fallback is False
    assert result.editor_output.verdict_explanation == "Verdict `WARN` with `MISSINGNESS` in `age`."
    assert guardrail.agents[-1]["provider"] == "openai-editor-repaired"


def test_multi_agent_l4_renders_full_appendix_html(monkeypatch):
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
