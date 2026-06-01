from ontology.models import AnomalyRecord, Severity, SEVERITY_ORDER

_MULTIVARIATE_TYPES = {"OUTLIER_ENSEMBLE", "DUPLICATE"}


def _escalate(max_sev: Severity, count: int) -> Severity:
    idx = SEVERITY_ORDER.index(max_sev)
    return SEVERITY_ORDER[min(idx + (count - 1), len(SEVERITY_ORDER) - 1)]


def apply_compound(findings: list) -> list:
    # Group by affected_column; multivariate findings (None column) stay solo
    column_groups: dict[str | None, list] = {}
    for f in findings:
        key = f.affected_column if f.affected_column is not None else id(f)
        column_groups.setdefault(key, []).append(f)

    result = []
    for key, group in column_groups.items():
        is_solo = isinstance(key, int)  # id(f) sentinel → multivariate
        if is_solo or len(group) == 1:
            for f in group:
                f.compound_severity = f.severity
        else:
            max_sev = max(group, key=lambda x: SEVERITY_ORDER.index(x.severity)).severity
            escalated = _escalate(max_sev, len(group))
            for f in group:
                f.compound_severity = escalated
        result.extend(group)

    return result
