from ontology.models import Severity, SEVERITY_ORDER


def _is_participating(severity: Severity) -> bool:
    return severity != Severity.INFO


def _compound_for_group(group: list) -> Severity | None:
    participating = [f for f in group if _is_participating(f.severity)]
    if len(participating) < 2:
        return None

    max_sev = max(participating, key=lambda x: SEVERITY_ORDER.index(x.severity)).severity
    high_or_above = sum(
        1
        for f in participating
        if SEVERITY_ORDER.index(f.severity) >= SEVERITY_ORDER.index(Severity.HIGH)
    )

    if max_sev == Severity.CRITICAL or high_or_above >= 2:
        return Severity.CRITICAL
    if max_sev == Severity.HIGH:
        return Severity.HIGH
    return Severity.HIGH


def apply_compound(findings: list) -> list:
    # Group by affected_column; multivariate findings (None column) stay solo
    column_groups: dict[str | None, list] = {}
    for f in findings:
        key = f.affected_column if f.affected_column is not None else id(f)
        column_groups.setdefault(key, []).append(f)

    result = []
    for key, group in column_groups.items():
        is_solo = isinstance(key, int)  # id(f) sentinel → multivariate
        compound = None if is_solo else _compound_for_group(group)
        if compound is None:
            for f in group:
                f.compound_severity = f.severity
        else:
            for f in group:
                f.compound_severity = compound if _is_participating(f.severity) else f.severity
        result.extend(group)

    return result
