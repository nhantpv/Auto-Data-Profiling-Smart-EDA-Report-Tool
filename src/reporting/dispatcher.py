"""L4 Dispatcher — Python thuần, 0 LLM call.

Gom findings + schema errors → lọc >= WARN → group by issue_type →
rank severity → trả top 5 clusters + remainder.

Xem ARCHITECT v5.4 §5.9(a) Dispatcher.
"""
from __future__ import annotations

from ontology.models import (
    AnomalyRecord,
    DispatchResult,
    IntegrityError,
    IssueCluster,
    Severity,
    SEVERITY_ORDER,
)


def _severity_rank(severity: Severity | None) -> int:
    if severity is None:
        return 0
    return SEVERITY_ORDER.index(severity)


def _effective_severity(record: AnomalyRecord | IntegrityError) -> Severity:
    return record.compound_severity if record.compound_severity is not None else record.severity


def _issue_type(record: AnomalyRecord | IntegrityError) -> str:
    if isinstance(record, IntegrityError):
        return record.error_type
    return record.issue_type


def _affected_column(record: AnomalyRecord | IntegrityError) -> str | None:
    if record.affected_column:
        return record.affected_column
    if isinstance(record, IntegrityError):
        return record.affected_table
    return None


def dispatch(
    anomalies: list[AnomalyRecord],
    integrity_errors: list[IntegrityError] | None = None,
    top_n: int = 5,
) -> DispatchResult:
    """
    1. Gom anomalies + integrity_errors thành danh sách chung
    2. Lọc severity >= WARN (bỏ INFO)
    3. Group by issue_type
    4. Rank: CRITICAL > HIGH > WARN, phụ = len(affected_columns)
    5. Trả top_n clusters + remainder count

    Returns:
        DispatchResult với top_clusters (tối đa top_n) và remainder_count
    """
    grouped: dict[str, list[AnomalyRecord | IntegrityError]] = {}
    for record in [*anomalies, *(integrity_errors or [])]:
        if _severity_rank(_effective_severity(record)) < _severity_rank(Severity.WARN):
            continue
        grouped.setdefault(_issue_type(record), []).append(record)

    clusters: list[IssueCluster] = []
    for issue_type, records in grouped.items():
        max_severity = max((_effective_severity(record) for record in records), key=_severity_rank)
        affected_columns = sorted({
            column
            for record in records
            for column in [_affected_column(record)]
            if column
        })
        issues = [
            record.model_dump(mode="json", exclude_none=True, exclude={"top_10_samples"})
            for record in records
        ]
        clusters.append(IssueCluster(
            issue_type=issue_type,
            issues=issues,
            affected_columns=affected_columns,
            max_severity=max_severity.value,
            json_slice={
                "issue_type": issue_type,
                "count": len(records),
                "max_severity": max_severity.value,
                "affected_columns": affected_columns,
                "issues": issues[:10],
            },
        ))

    clusters.sort(
        key=lambda cluster: (
            _severity_rank(Severity(cluster.max_severity)),
            len(cluster.issues),
            len(cluster.affected_columns),
            cluster.issue_type,
        ),
        reverse=True,
    )
    top_clusters = clusters[:top_n]
    remainder_count = sum(len(cluster.issues) for cluster in clusters[top_n:])
    return DispatchResult(top_clusters=top_clusters, remainder_count=remainder_count)
