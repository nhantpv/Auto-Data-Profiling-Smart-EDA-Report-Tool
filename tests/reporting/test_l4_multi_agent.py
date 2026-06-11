import asyncio

from ontology.models import (
    AnomalyRecord,
    DataQualityFindings,
    DatasetMeta,
    DatasetVerdict,
    Severity,
    Verdict,
    VerdictSummary,
)
from reporting.dispatcher import dispatch
from reporting.l4_report import _run_analyst, generate_multi_agent_report


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


def _anomaly(issue_type: str, severity: Severity, column: str) -> AnomalyRecord:
    return AnomalyRecord(
        issue_type=issue_type,
        description=issue_type,
        severity=severity,
        affected_count=3,
        affected_percent=0.3,
        affected_column=column,
        top_10_samples=[],
    )


def _meta() -> DatasetMeta:
    return DatasetMeta(
        file_name="data.csv",
        n=10,
        n_var=8,
        memory_size=0,
        p_cells_missing=0.1,
    )


def _verdict() -> DatasetVerdict:
    return DatasetVerdict(
        dataset_meta=_meta(),
        verdict=Verdict.WARN,
        verdict_rationale="Needs review",
        summary=VerdictSummary(total_issues=7, warn=6, info=1),
    )


def test_appendix_lists_findings_outside_top_clusters(monkeypatch):
    monkeypatch.delenv("SMART_EDA_L4_PROVIDER", raising=False)
    anomalies = [
        _anomaly(f"TYPE_{letter}", Severity.WARN, f"col_{letter.lower()}")
        for letter in "ABCDEF"
    ] + [_anomaly("LOW_SIGNAL", Severity.INFO, "name")]
    findings = DataQualityFindings(dataset_meta=_meta(), columns={}, anomalies=anomalies)

    _text, _guardrail, result = generate_multi_agent_report(findings, _verdict())

    # 6 WARN types sorted descending → TYPE_A falls outside the top 5;
    # INFO findings never reach a cluster. Both must appear in the appendix.
    assert "TYPE_A" in result.appendix_html
    assert "LOW_SIGNAL" in result.appendix_html
    assert "TYPE_F" not in result.appendix_html


def test_analyst_retries_up_to_three_times_then_falls_back(monkeypatch):
    monkeypatch.setenv("SMART_EDA_L4_PROVIDER", "openai")
    calls = {"count": 0}

    async def fake_call(prompt, instructions, model_env, default_model):
        calls["count"] += 1
        return "Value `9999999` is invented."

    monkeypatch.setattr("reporting.l4_report._call_openai_async", fake_call)
    cluster = dispatch([_anomaly("MISSINGNESS", Severity.WARN, "age")]).top_clusters[0]

    output, _detail = asyncio.run(_run_analyst(cluster))

    assert calls["count"] == 3
    assert output.retry_count == 3
    assert output.guardrail_passed is True  # deterministic fallback passes


def test_guardrail_report_contains_per_agent_details(monkeypatch):
    monkeypatch.delenv("SMART_EDA_L4_PROVIDER", raising=False)
    findings = DataQualityFindings(
        dataset_meta=_meta(),
        columns={},
        anomalies=[_anomaly("MISSINGNESS", Severity.WARN, "age")],
    )

    _text, guardrail, result = generate_multi_agent_report(findings, _verdict())

    agents = guardrail.agents
    assert len(agents) == 2
    assert agents[0]["agent"] == "analyst"
    assert agents[0]["cluster"] == "MISSINGNESS"
    assert agents[1]["agent"] == "editor"
    assert result.guardrail_report["agents"] == agents
