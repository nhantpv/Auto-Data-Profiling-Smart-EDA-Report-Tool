from ontology.models import AnomalyRecord, IntegrityError, Severity
from reporting.dispatcher import dispatch


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


def test_dispatch_groups_warn_plus_records_by_issue_type():
    result = dispatch(
        anomalies=[
            _anomaly("MISSINGNESS", Severity.WARN, "age"),
            _anomaly("MISSINGNESS", Severity.HIGH, "income"),
            _anomaly("LOW_SIGNAL", Severity.INFO, "name"),
        ],
        integrity_errors=[
            IntegrityError(
                error_type="ORPHAN_FK",
                description="orphan",
                severity=Severity.CRITICAL,
                affected_table="orders",
                affected_column="user_id",
                affected_count=2,
            )
        ],
        top_n=1,
    )

    assert result.top_clusters[0].issue_type == "ORPHAN_FK"
    assert result.top_clusters[0].max_severity == "CRITICAL"
    assert result.remainder_count == 2
