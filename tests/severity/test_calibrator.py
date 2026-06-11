import pytest
from ontology.models import ColumnStats, Severity
from severity.calibrator import calibrate_columns, load_calibrator_table


def _col(type_="Numeric", p_missing=0.0, n_distinct=10, n_missing=0,
         additional_metrics=None, missingness_mechanism=None):
    return ColumnStats(
        type=type_,
        n_missing=n_missing,
        p_missing=p_missing,
        n_distinct=n_distinct,
        additional_metrics=additional_metrics or {},
        missingness_mechanism=missingness_mechanism,
    )


class TestLoadCalibratorTable:
    def test_loads_and_has_completeness(self):
        table = load_calibrator_table()
        assert "completeness" in table
        assert "thresholds" in table["completeness"]


class TestCalibrateCompleteness:
    def test_zero_missing_produces_no_finding(self):
        findings = calibrate_columns({"age": _col(p_missing=0.0)}, load_calibrator_table(), n=100)
        col_issues = [f for f in findings if f.affected_column == "age"]
        assert col_issues == []

    def test_p_missing_under_5pct_is_info(self):
        findings = calibrate_columns({"bmi": _col(p_missing=0.03)}, load_calibrator_table(), n=100)
        f = [x for x in findings if x.affected_column == "bmi"][0]
        assert f.severity == Severity.INFO
        assert f.issue_type == "MISSINGNESS"
        assert "Completeness" in f.dq_dimensions

    def test_p_missing_between_5_and_20pct_is_warn(self):
        findings = calibrate_columns({"bmi": _col(p_missing=0.10)}, load_calibrator_table(), n=100)
        f = next(x for x in findings if x.affected_column == "bmi")
        assert f.severity == Severity.WARN

    def test_p_missing_between_20_and_50pct_is_high(self):
        findings = calibrate_columns({"x": _col(p_missing=0.35)}, load_calibrator_table(), n=100)
        f = next(x for x in findings if x.affected_column == "x")
        assert f.severity == Severity.HIGH

    def test_p_missing_over_50pct_is_critical(self):
        findings = calibrate_columns({"x": _col(p_missing=0.60)}, load_calibrator_table(), n=100)
        f = next(x for x in findings if x.affected_column == "x")
        assert f.severity == Severity.CRITICAL


class TestCalibrateConstantColumn:
    def test_n_distinct_1_is_high(self):
        findings = calibrate_columns({"flag": _col(n_distinct=1)}, load_calibrator_table(), n=100)
        f = next(x for x in findings if x.affected_column == "flag")
        assert f.issue_type == "CONSTANT_COLUMN"
        assert f.severity == Severity.HIGH
        assert "Uniqueness" in f.dq_dimensions

    def test_n_distinct_0_is_high(self):
        findings = calibrate_columns({"empty": _col(n_distinct=0)}, load_calibrator_table(), n=100)
        f = next(x for x in findings if x.affected_column == "empty")
        assert f.severity == Severity.HIGH

    def test_n_distinct_2_no_constant_finding(self):
        findings = calibrate_columns({"binary": _col(n_distinct=2)}, load_calibrator_table(), n=100)
        constant = [f for f in findings if f.issue_type == "CONSTANT_COLUMN" and f.affected_column == "binary"]
        assert constant == []


class TestCalibrateImbalance:
    def test_categorical_imbalance_above_095_is_warn(self):
        col = _col(type_="Categorical", n_distinct=2, additional_metrics={"imbalance": 0.99})
        findings = calibrate_columns({"stroke": col}, load_calibrator_table(), n=100)
        f = next(x for x in findings if x.issue_type == "IMBALANCE")
        assert f.severity == Severity.WARN
        assert f.affected_column == "stroke"
        assert "Consistency" in f.dq_dimensions

    def test_categorical_imbalance_below_095_no_finding(self):
        col = _col(type_="Categorical", n_distinct=2, additional_metrics={"imbalance": 0.70})
        findings = calibrate_columns({"col": col}, load_calibrator_table(), n=100)
        imbalance = [f for f in findings if f.issue_type == "IMBALANCE"]
        assert imbalance == []

    def test_numeric_column_no_imbalance_finding(self):
        col = _col(type_="Numeric", additional_metrics={"imbalance": 0.99})
        findings = calibrate_columns({"val": col}, load_calibrator_table(), n=100)
        imbalance = [f for f in findings if f.issue_type == "IMBALANCE"]
        assert imbalance == []


class TestCalibrateMissingnessEscalation:
    """3b-3: only MAR escalates completeness severity by 1 tier."""

    def test_mar_escalates_warn_to_high(self):
        col = _col(p_missing=0.10, n_missing=10, missingness_mechanism="MAR")
        findings = calibrate_columns({"bmi": col}, load_calibrator_table(), n=100)
        f = next(x for x in findings if x.issue_type == "MISSINGNESS")
        assert f.severity == Severity.HIGH   # WARN+1 = HIGH

    def test_indeterminate_does_not_escalate(self):
        col = _col(p_missing=0.10, n_missing=10, missingness_mechanism="INDETERMINATE")
        findings = calibrate_columns({"x": col}, load_calibrator_table(), n=100)
        f = next(x for x in findings if x.issue_type == "MISSINGNESS")
        assert f.severity == Severity.WARN

    def test_mcar_consistent_no_escalation(self):
        col = _col(p_missing=0.10, n_missing=10, missingness_mechanism="MCAR_CONSISTENT")
        findings = calibrate_columns({"x": col}, load_calibrator_table(), n=100)
        f = next(x for x in findings if x.issue_type == "MISSINGNESS")
        assert f.severity == Severity.WARN   # unchanged

    def test_none_mechanism_no_escalation(self):
        col = _col(p_missing=0.10, n_missing=10, missingness_mechanism=None)
        findings = calibrate_columns({"x": col}, load_calibrator_table(), n=100)
        f = next(x for x in findings if x.issue_type == "MISSINGNESS")
        assert f.severity == Severity.WARN   # 3a behaviour unchanged

    def test_mar_caps_at_critical(self):
        # p_missing=0.6 → already CRITICAL; escalation stays CRITICAL (no overflow)
        col = _col(p_missing=0.60, n_missing=60, missingness_mechanism="MAR")
        findings = calibrate_columns({"x": col}, load_calibrator_table(), n=100)
        f = next(x for x in findings if x.issue_type == "MISSINGNESS")
        assert f.severity == Severity.CRITICAL

    def test_mar_escalates_info_to_warn(self):
        # p_missing=0.03 → INFO; MAR → WARN
        col = _col(p_missing=0.03, n_missing=3, missingness_mechanism="MAR")
        findings = calibrate_columns({"x": col}, load_calibrator_table(), n=100)
        f = next(x for x in findings if x.issue_type == "MISSINGNESS")
        assert f.severity == Severity.WARN


class TestCalibrateHighCardinality:
    def test_categorical_high_p_distinct_is_warn(self):
        # n_distinct=95, n=100 → p_distinct=0.95 > 0.9
        col = _col(type_="Categorical", n_distinct=95)
        findings = calibrate_columns({"city": col}, load_calibrator_table(), n=100)
        f = next(x for x in findings if x.issue_type == "HIGH_CARDINALITY")
        assert f.severity == Severity.WARN
        assert "Uniqueness" in f.dq_dimensions

    def test_categorical_low_p_distinct_no_finding(self):
        col = _col(type_="Categorical", n_distinct=5)
        findings = calibrate_columns({"gender": col}, load_calibrator_table(), n=100)
        hc = [f for f in findings if f.issue_type == "HIGH_CARDINALITY"]
        assert hc == []

    def test_numeric_no_high_cardinality_finding(self):
        col = _col(type_="Numeric", n_distinct=99)
        findings = calibrate_columns({"age": col}, load_calibrator_table(), n=100)
        hc = [f for f in findings if f.issue_type == "HIGH_CARDINALITY"]
        assert hc == []
