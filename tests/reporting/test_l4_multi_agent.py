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


def test_multi_agent_l4_deterministic_fallback_passes_guardrail(monkeypatch):
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

    text, guardrail, result = generate_multi_agent_report(findings, verdict)

    assert "L4 Guarded EDA Report" in text
    assert guardrail.status == "passed"
    assert result.analyst_outputs[0].guardrail_passed is True


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
        return '{"executive_summary":"Dataset data.csv has 10 rows","verdict_explanation":"Needs review","priority_ranking":"MISSINGNESS"}'

    monkeypatch.setattr(l4_report, "_call_openai_async", fake_call)
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

    _text, guardrail, result = generate_multi_agent_report(findings, verdict)

    assert guardrail.status == "passed"
    assert result.analyst_outputs[0].retry_count == 1
    assert result.editor_output.retry_count == 1
