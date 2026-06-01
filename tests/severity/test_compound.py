import pytest
from ontology.models import AnomalyRecord, Severity
from severity.compound import apply_compound


def _rec(issue_type, severity, affected_column=None):
    return AnomalyRecord(
        issue_type=issue_type,
        description=f"{issue_type} on {affected_column}",
        severity=Severity(severity),
        affected_count=1,
        affected_percent=0.01,
        affected_column=affected_column,
        top_10_samples=[],
    )


class TestApplyCompoundSingleFinding:
    def test_single_finding_compound_equals_original(self):
        findings = [_rec("MISSINGNESS", "WARN", "bmi")]
        result = apply_compound(findings)
        assert result[0].compound_severity == Severity.WARN

    def test_multivariate_outlier_not_escalated(self):
        findings = [_rec("OUTLIER_ENSEMBLE", "HIGH", None)]
        result = apply_compound(findings)
        assert result[0].compound_severity == Severity.HIGH

    def test_duplicate_not_escalated(self):
        findings = [_rec("DUPLICATE", "WARN", None)]
        result = apply_compound(findings)
        assert result[0].compound_severity == Severity.WARN


class TestApplyCompoundEscalation:
    def test_two_findings_on_same_column_escalate_by_one(self):
        # age: HIGH + WARN → compound HIGH+1 = CRITICAL
        findings = [
            _rec("OUTLIER_ENSEMBLE", "HIGH", "age"),
            _rec("MISSINGNESS", "WARN", "age"),
        ]
        result = apply_compound(findings)
        for f in result:
            if f.affected_column == "age":
                assert f.compound_severity == Severity.CRITICAL

    def test_three_findings_escalate_by_two(self):
        # col: WARN + WARN + WARN → max=WARN, idx=1, +2 = idx 3 = CRITICAL
        findings = [
            _rec("MISSINGNESS", "WARN", "x"),
            _rec("IMBALANCE", "WARN", "x"),
            _rec("HIGH_CARDINALITY", "WARN", "x"),
        ]
        result = apply_compound(findings)
        for f in result:
            assert f.compound_severity == Severity.CRITICAL

    def test_escalation_caps_at_critical(self):
        # col: CRITICAL + CRITICAL → stays CRITICAL (can't go higher)
        findings = [
            _rec("MISSINGNESS", "CRITICAL", "y"),
            _rec("CONSTANT_COLUMN", "HIGH", "y"),
        ]
        result = apply_compound(findings)
        for f in result:
            if f.affected_column == "y":
                assert f.compound_severity == Severity.CRITICAL

    def test_different_columns_escalated_independently(self):
        # col_a: 1 finding → WARN; col_b: 2 findings → HIGH escalates to CRITICAL
        findings = [
            _rec("MISSINGNESS", "WARN", "col_a"),
            _rec("MISSINGNESS", "HIGH", "col_b"),
            _rec("IMBALANCE", "WARN", "col_b"),
        ]
        result = apply_compound(findings)
        col_a = [f for f in result if f.affected_column == "col_a"]
        col_b = [f for f in result if f.affected_column == "col_b"]
        assert col_a[0].compound_severity == Severity.WARN
        for f in col_b:
            assert f.compound_severity == Severity.CRITICAL

    def test_multivariate_alongside_column_findings(self):
        # OUTLIER_ENSEMBLE stays at severity, col finding escalates normally
        findings = [
            _rec("OUTLIER_ENSEMBLE", "HIGH", None),
            _rec("MISSINGNESS", "WARN", "bmi"),
            _rec("CONSTANT_COLUMN", "HIGH", "bmi"),
        ]
        result = apply_compound(findings)
        outlier = next(f for f in result if f.issue_type == "OUTLIER_ENSEMBLE")
        assert outlier.compound_severity == Severity.HIGH
        bmi = [f for f in result if f.affected_column == "bmi"]
        for f in bmi:
            assert f.compound_severity == Severity.CRITICAL
