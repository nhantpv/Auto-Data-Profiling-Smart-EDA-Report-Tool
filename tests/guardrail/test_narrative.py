from ontology.models import (
    DataQualityFindings,
    DatasetMeta,
    DatasetVerdict,
    Verdict,
    VerdictSummary,
)
from guardrail import validate_narrative
from reporting.l4_report import generate_l4_report


def _verdict() -> DatasetVerdict:
    return DatasetVerdict(
        dataset_meta=DatasetMeta(
            file_name="data.csv",
            n=12,
            n_var=3,
            memory_size=0,
            p_cells_missing=0.25,
            n_duplicates=2,
            p_duplicates=0.1667,
        ),
        verdict=Verdict.NOT_READY,
        verdict_rationale="Critical issues found",
        summary=VerdictSummary(total_issues=2, critical=1, high=1, warn=0, info=0),
    )


def _findings() -> DataQualityFindings:
    return DataQualityFindings(
        dataset_meta=_verdict().dataset_meta,
        columns={},
        anomalies=[],
    )


def test_guardrail_rejects_hallucinated_number():
    report = validate_narrative("Dataset has `999` rows.", _findings(), _verdict())

    assert report.status == "failed"
    assert report.violations[0].check == "number_allowed_set"
    assert report.violations[0].value == "999"


def test_guardrail_rejects_hallucinated_backticked_reference():
    report = validate_narrative("Column `customer_id` is risky.", _findings(), _verdict())

    assert report.status == "failed"
    assert report.violations[0].check == "reference_allowed_set"
    assert report.violations[0].value == "customer_id"


def test_generated_l4_report_passes_guardrail(monkeypatch):
    monkeypatch.delenv("SMART_EDA_L4_PROVIDER", raising=False)

    text, report = generate_l4_report(_findings(), _verdict())

    assert "L4 Guarded EDA Report" in text
    assert report.status == "passed"
    assert report.checked_numbers
