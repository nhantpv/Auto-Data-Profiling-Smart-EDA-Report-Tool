from ontology.models import (
    AnomalyRecord,
    DataQualityFindings,
    DatasetMeta,
    DatasetVerdict,
    Severity,
    Verdict,
    VerdictSummary,
)
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
