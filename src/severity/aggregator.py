from ontology.models import (
    AnomalyRecord, DatasetMeta, DatasetVerdict, IntegrityError, IssueDetailRef,
    IssueSummary, Severity, SEVERITY_ORDER, Verdict, VerdictSummary,
)
from config.threshold_registry import ThresholdRegistry


_THRESHOLDS = ThresholdRegistry()


def _effective(f: AnomalyRecord | IntegrityError) -> Severity:
    return f.compound_severity if f.compound_severity is not None else f.severity


def _severity_rank(severity: Severity) -> int:
    return SEVERITY_ORDER.index(severity)


def _affected_table_from_column(column: str | None) -> str | None:
    if not column or "." not in column:
        return None
    table, _ = column.split(".", 1)
    return table or None


def _risk_score(meta: DatasetMeta, findings: list[AnomalyRecord | IntegrityError]) -> float:
    if not findings:
        return 0.0
    weights = {
        Severity.INFO: 0.0,
        Severity.WARN: 1.0,
        Severity.HIGH: 5.0,
        Severity.CRITICAL: 20.0,
    }
    total_weight = sum(weights[_effective(f)] for f in findings)
    total_cells = max(meta.n * meta.n_var, 1)
    return round(total_weight / total_cells, 6)


def _issue_summary_for_dq(finding: AnomalyRecord, index: int) -> IssueSummary:
    return IssueSummary(
        source="data_quality_findings",
        issue_type=finding.issue_type,
        severity=finding.severity,
        effective_severity=_effective(finding),
        affected_table=_affected_table_from_column(finding.affected_column),
        affected_column=finding.affected_column,
        affected_count=finding.affected_count,
        confidence=finding.confidence,
        rationale=finding.description,
        detail_ref=IssueDetailRef(
            file="data_quality_findings.json",
            collection="anomalies",
            index=index,
        ),
    )


def _issue_summary_for_integrity(finding: IntegrityError, index: int) -> IssueSummary:
    return IssueSummary(
        source="schema_evaluation_findings",
        issue_type=finding.error_type,
        severity=finding.severity,
        effective_severity=_effective(finding),
        affected_table=finding.affected_table,
        affected_column=finding.affected_column,
        affected_count=finding.affected_count,
        confidence=finding.confidence,
        rationale=finding.description,
        detail_ref=IssueDetailRef(
            file="schema_evaluation_findings.json",
            collection="integrity_errors",
            index=index,
        ),
    )


def _top_issues(
    dq_findings: list[AnomalyRecord],
    integrity_errors: list[IntegrityError],
    limit: int = 10,
) -> list[IssueSummary]:
    issues = [
        _issue_summary_for_dq(finding, index)
        for index, finding in enumerate(dq_findings)
    ] + [
        _issue_summary_for_integrity(finding, index)
        for index, finding in enumerate(integrity_errors)
    ]
    issues.sort(
        key=lambda issue: (
            _severity_rank(issue.effective_severity),
            issue.affected_count,
            issue.confidence or 0.0,
        ),
        reverse=True,
    )
    return issues[:limit]


def aggregate(
    meta: DatasetMeta,
    dq_findings: list[AnomalyRecord],
    integrity_errors: list[IntegrityError] | None = None,
) -> DatasetVerdict:
    schema_findings = list(integrity_errors or [])
    all_findings = list(dq_findings) + schema_findings

    summary = VerdictSummary()
    for f in all_findings:
        sev = _effective(f)
        summary.total_issues += 1
        if sev == Severity.CRITICAL:
            summary.critical += 1
        elif sev == Severity.HIGH:
            summary.high += 1
        elif sev == Severity.WARN:
            summary.warn += 1
        else:
            summary.info += 1

    if summary.critical > 0:
        verdict = Verdict.NOT_READY
        rationale = f"{summary.critical} CRITICAL finding(s) — data not ready for use"
    elif summary.high > 0:
        verdict = Verdict.WARN
        rationale = f"{summary.high} HIGH finding(s) — review before use"
    else:
        verdict = Verdict.READY
        rationale = "No blocking issues — data READY" if summary.total_issues > 0 else "No issues found — data READY"

    # ── M1 density rule (ARCHITECT v5.4 §5.6) ──────────────────────────────
    # Many small WARNs spread across columns → escalate to at least WARN.
    if verdict == Verdict.READY and summary.total_issues > 0:
        warn_plus = [
            f for f in all_findings
            if _severity_rank(_effective(f)) >= _severity_rank(Severity.WARN)
        ]
        n_cols_affected = len(set(
            getattr(f, "affected_column", None)
            for f in warn_plus
            if getattr(f, "affected_column", None)
        ))
        share = n_cols_affected / max(meta.n_var, 1)
        if (
            share > _THRESHOLDS.get("density_share_gate")
            and n_cols_affected >= int(_THRESHOLDS.get("density_min_cols"))
        ):
            verdict = Verdict.WARN
            rationale = (
                f"Density rule: {len(warn_plus)} WARN+ issues across "
                f"{n_cols_affected} columns ({share:.0%} of columns) — review before use"
            )

    return DatasetVerdict(
        dataset_meta=meta,
        verdict=verdict,
        verdict_rationale=rationale,
        summary=summary,
        top_issues=_top_issues(list(dq_findings), schema_findings),
        risk_score=_risk_score(meta, all_findings),
    )
