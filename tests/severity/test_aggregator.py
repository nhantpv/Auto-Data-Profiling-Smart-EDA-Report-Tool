import pytest
from ontology.models import (
    AnomalyRecord, DatasetMeta, Severity, Verdict, VerdictSummary, DatasetVerdict,
)
from severity.aggregator import aggregate


def _meta():
    return DatasetMeta(file_name="t.csv", n=100, n_var=5, memory_size=512, p_cells_missing=0.0)


def _rec(severity, compound_severity=None, col=None):
    r = AnomalyRecord(
        issue_type="TEST",
        description="test",
        severity=Severity(severity),
        affected_count=1,
        affected_percent=0.01,
        affected_column=col,
        top_10_samples=[],
    )
    if compound_severity:
        r.compound_severity = Severity(compound_severity)
    return r


class TestAggregateVerdict:
    def test_empty_findings_is_ready(self):
        v = aggregate(_meta(), [])
        assert v.verdict == Verdict.READY
        assert v.summary.total_issues == 0

    def test_only_info_warn_is_ready(self):
        v = aggregate(_meta(), [_rec("INFO"), _rec("WARN")])
        assert v.verdict == Verdict.READY

    def test_one_high_is_warn_verdict(self):
        v = aggregate(_meta(), [_rec("HIGH")])
        assert v.verdict == Verdict.WARN

    def test_one_critical_is_not_ready(self):
        v = aggregate(_meta(), [_rec("CRITICAL")])
        assert v.verdict == Verdict.NOT_READY

    def test_critical_dominates_high(self):
        v = aggregate(_meta(), [_rec("HIGH"), _rec("CRITICAL")])
        assert v.verdict == Verdict.NOT_READY

    def test_compound_severity_used_over_base(self):
        # base=WARN but compound=CRITICAL → NOT_READY
        v = aggregate(_meta(), [_rec("WARN", compound_severity="CRITICAL")])
        assert v.verdict == Verdict.NOT_READY

    def test_compound_severity_none_falls_back_to_base(self):
        v = aggregate(_meta(), [_rec("HIGH", compound_severity=None)])
        assert v.verdict == Verdict.WARN

    def test_warn_density_uses_affected_column_share(self):
        v = aggregate(_meta(), [
            _rec("WARN", col="a"),
            _rec("WARN", col="b"),
        ])

        assert v.verdict == Verdict.WARN
        assert "of columns" in v.verdict_rationale


class TestAggregateVerdictSummary:
    def test_counts_by_tier(self):
        findings = [
            _rec("INFO"),
            _rec("WARN"),
            _rec("WARN"),
            _rec("HIGH"),
            _rec("CRITICAL"),
        ]
        v = aggregate(_meta(), findings)
        assert v.summary.total_issues == 5
        assert v.summary.info == 1
        assert v.summary.warn == 2
        assert v.summary.high == 1
        assert v.summary.critical == 1

    def test_compound_severity_counted_not_base(self):
        # base=WARN compound=CRITICAL → counted as CRITICAL
        findings = [_rec("WARN", compound_severity="CRITICAL")]
        v = aggregate(_meta(), findings)
        assert v.summary.critical == 1
        assert v.summary.warn == 0

    def test_integrity_errors_none_ok(self):
        v = aggregate(_meta(), [_rec("WARN")], integrity_errors=None)
        assert v.verdict == Verdict.READY

    def test_top_issues_sorted_by_effective_severity(self):
        v = aggregate(_meta(), [
            _rec("WARN", col="status"),
            _rec("HIGH", col="amount"),
        ])
        assert [issue.affected_column for issue in v.top_issues[:2]] == ["amount", "status"]
        assert v.top_issues[0].detail_ref is not None
        assert v.top_issues[0].detail_ref.file == "data_quality_findings.json"


class TestAggregateRationale:
    def test_rationale_mentions_verdict(self):
        v = aggregate(_meta(), [_rec("CRITICAL", col="bmi")])
        assert "CRITICAL" in v.verdict_rationale or "NOT_READY" in v.verdict_rationale

    def test_rationale_ready_when_empty(self):
        v = aggregate(_meta(), [])
        assert "READY" in v.verdict_rationale or "no" in v.verdict_rationale.lower()


class TestAggregateRoundtrip:
    def test_serialize_deserialize(self):
        v = aggregate(_meta(), [_rec("HIGH")])
        restored = DatasetVerdict.model_validate_json(v.model_dump_json())
        assert restored.verdict == Verdict.WARN
        assert restored.summary.high == 1
