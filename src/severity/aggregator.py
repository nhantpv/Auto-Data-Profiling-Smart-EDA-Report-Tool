from ontology.models import (
    AnomalyRecord, DatasetMeta, DatasetVerdict, IntegrityError,
    Severity, Verdict, VerdictSummary,
)


def _effective(f: AnomalyRecord) -> Severity:
    return f.compound_severity if f.compound_severity is not None else f.severity


def aggregate(
    meta: DatasetMeta,
    dq_findings: list,
    integrity_errors: list | None = None,
) -> DatasetVerdict:
    all_findings = list(dq_findings) + list(integrity_errors or [])

    summary = VerdictSummary()
    for f in all_findings:
        sev = _effective(f) if isinstance(f, AnomalyRecord) else (
            f.compound_severity if f.compound_severity is not None else f.severity
        )
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

    return DatasetVerdict(
        dataset_meta=meta,
        verdict=verdict,
        verdict_rationale=rationale,
        summary=summary,
    )
