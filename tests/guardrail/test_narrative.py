from ontology.models import (
    AnomalyRecord,
    DataQualityFindings,
    DatasetMeta,
    DatasetVerdict,
    Severity,
    Verdict,
    VerdictSummary,
)
from guardrail import validate_narrative
from guardrail.narrative import verify_analyst_output
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


def test_guardrail_rejects_causal_language():
    report = validate_narrative("Column `data.csv` causes the issue.", _findings(), _verdict())

    assert report.status == "failed"
    assert any(v.check == "causation_language_ban" for v in report.violations)


def test_guardrail_allows_numeric_tolerance_and_year_passthrough():
    report = validate_narrative(
        "Dataset `data.csv` has `12.00001` rows, `16.67%` duplicates, and was reviewed in `2026`.",
        _findings(),
        _verdict(),
    )

    assert report.status == "passed"


def test_guardrail_allows_agent_level_provenance_and_raw_percent():
    findings = _findings()
    findings.anomalies = [
        AnomalyRecord(
            issue_type="MISSINGNESS",
            description="missing",
            severity=Severity.WARN,
            affected_count=1,
            affected_percent=0.0833,
            affected_column="age",
            top_10_samples=[],
        )
    ]

    report = validate_narrative(
        "Issue `MISSINGNESS` has provenance `OBSERVED` and raw rate `0.0833` on `age`.",
        findings,
        _verdict(),
    )

    assert report.status == "passed"


def test_agent_guardrail_allows_schema_table_column_aliases():
    evidence = {
        "issue_type": "ORPHAN_FOREIGN_KEY",
        "count": 1,
        "issues": [
            {
                "error_type": "ORPHAN_FOREIGN_KEY",
                "affected_table": "orders",
                "affected_column": "customer_id",
                "relationship": {
                    "child_table": "orders",
                    "child_column": "customer_id",
                    "parent_table": "customers",
                    "parent_column": "id",
                },
            }
        ],
    }

    report = verify_analyst_output(
        "### `ORPHAN_FOREIGN_KEY`\n\nRelationship `orders.customer_id -> customers.id` has `1 row(s)` to review.",
        evidence,
    )

    assert report.status == "passed"


def test_agent_guardrail_extracts_table_columns_from_description_text():
    evidence = {
        "issue_type": "ORPHAN_FOREIGN_KEY",
        "issues": [
            {
                "description": "1 row(s) in orders.customer_id reference non-existent customers.id",
                "affected_count": 1,
            }
        ],
    }

    report = verify_analyst_output(
        "### `ORPHAN_FOREIGN_KEY`\n\n`orders.customer_id` cannot resolve to `customers.id` for `1 row(s)`.",
        evidence,
    )

    assert report.status == "passed"


def test_final_guardrail_allows_structural_field_references():
    report = validate_narrative(
        "Analyst cited `issue_type`, `affected_count`, and `max_severity` for dataset `data.csv`.",
        _findings(),
        _verdict(),
    )

    assert report.status == "passed"


def test_final_guardrail_allows_values_from_full_json_evidence():
    findings = _findings()
    findings.anomalies = [
        AnomalyRecord(
            issue_type="MISSINGNESS",
            description="[schools] Column 'id_school' has 25.0% missing values",
            severity=Severity.HIGH,
            dq_dimensions=["Completeness"],
            ml_impact=["training_bias"],
            affected_count=1,
            affected_percent=0.25,
            affected_column="schools.id_school",
            top_10_samples=[],
        )
    ]

    report = validate_narrative(
        "The `Completeness` dimension includes `training_bias` risk: "
        "`[schools] Column 'id_school' has 25.0% missing values`.",
        findings,
        _verdict(),
    )

    assert report.status == "passed"


def test_generated_l4_report_passes_guardrail(monkeypatch):
    monkeypatch.delenv("SMART_EDA_L4_PROVIDER", raising=False)

    text, report = generate_l4_report(_findings(), _verdict())

    assert "L4 Guarded EDA Report" in text
    assert report.status == "passed"
    assert report.checked_numbers
