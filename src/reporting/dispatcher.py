"""L4 Dispatcher — Python thuần, 0 LLM call.

Gom findings + schema errors → lọc >= WARN → group by table →
rank severity → trả top 5 table_clusters + remainder.

Xem ARCHITECT v5.4 §5.9(a) Dispatcher.
"""
from __future__ import annotations

from typing import Any, Dict

from ontology.models import (
    AnomalyRecord,
    ColumnStats,
    DispatchResult,
    IntegrityError,
    IssueCluster,
    Severity,
    SEVERITY_ORDER,
    TableCluster,
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


def _affected_table(record: AnomalyRecord | IntegrityError) -> str:
    """Trả về tên bảng chứa record. Dùng cho gom theo table."""
    if isinstance(record, IntegrityError):
        return record.affected_table
    # AnomalyRecord không có affected_table trực tiếp,
    # dùng "default" cho single-file CSV
    return "default"


def _trim_samples(record: AnomalyRecord | IntegrityError, max_samples: int = 5) -> dict[str, Any]:
    """Dump record thành dict, giữ tối đa max_samples samples thay vì exclude."""
    data = record.model_dump(mode="json", exclude_none=True)
    if "top_10_samples" in data:
        data["top_10_samples"] = data["top_10_samples"][:max_samples]
    return data


# ============================================================
# Legacy dispatch — giữ nguyên cho backward compatibility
# ============================================================

def dispatch(
    anomalies: list[AnomalyRecord],
    integrity_errors: list[IntegrityError] | None = None,
    top_n: int = 5,
) -> DispatchResult:
    """
    Legacy: Gom theo issue_type.
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


# ============================================================
# New dispatch — gom theo Table, inject column stats
# ============================================================

def dispatch_by_table(
    anomalies: list[AnomalyRecord],
    integrity_errors: list[IntegrityError] | None = None,
    columns: Dict[str, ColumnStats] | None = None,
    top_n: int = 5,
) -> DispatchResult:
    """Gom theo TABLE thay vì issue_type.

    1. Gom anomalies + integrity_errors theo affected_table
    2. Lọc severity >= WARN (bỏ INFO)
    3. Mỗi table cluster chứa TẤT CẢ issues + column stats của bảng đó
    4. Rank: CRITICAL > HIGH > WARN, phụ = len(issues)
    5. Trả top_n table_clusters + remainder count

    Args:
        anomalies: Danh sách anomaly records từ L3.
        integrity_errors: Danh sách integrity errors từ schema engine.
        columns: Dict tên cột → ColumnStats, inject vào json_slice cho LLM.
        top_n: Số bảng tối đa gửi cho Analyst agents.

    Returns:
        DispatchResult với table_clusters (tối đa top_n) và remainder_count.
    """
    # Group by table name
    grouped: dict[str, list[AnomalyRecord | IntegrityError]] = {}
    for record in [*anomalies, *(integrity_errors or [])]:
        if _severity_rank(_effective_severity(record)) < _severity_rank(Severity.WARN):
            continue
        table_name = _affected_table(record)
        grouped.setdefault(table_name, []).append(record)

    table_clusters: list[TableCluster] = []
    for table_name, records in grouped.items():
        max_severity = max(
            (_effective_severity(record) for record in records),
            key=_severity_rank,
        )
        affected_columns = sorted({
            column
            for record in records
            for column in [_affected_column(record)]
            if column
        })
        issues = [_trim_samples(record) for record in records]

        # Inject column statistics cho các cột bị ảnh hưởng
        col_stats: dict[str, Any] = {}
        if columns:
            for col_name in affected_columns:
                if col_name in columns:
                    col_stats[col_name] = columns[col_name].model_dump(exclude_none=True)

        table_clusters.append(TableCluster(
            table_name=table_name,
            issues=issues,
            affected_columns=affected_columns,
            max_severity=max_severity.value,
            column_statistics=col_stats,
            json_slice={
                "table_name": table_name,
                "issue_count": len(records),
                "max_severity": max_severity.value,
                "affected_columns": affected_columns,
                "column_statistics": col_stats,
                "issues": issues[:15],  # Nhiều hơn legacy vì gom theo bảng
            },
        ))

    table_clusters.sort(
        key=lambda tc: (
            _severity_rank(Severity(tc.max_severity)),
            len(tc.issues),
            len(tc.affected_columns),
            tc.table_name,
        ),
        reverse=True,
    )

    # Cũng chạy legacy dispatch để giữ backward compat
    legacy_result = dispatch(anomalies, integrity_errors, top_n)

    top_tables = table_clusters[:top_n]
    remainder_count = sum(len(tc.issues) for tc in table_clusters[top_n:])
    return DispatchResult(
        top_clusters=legacy_result.top_clusters,
        table_clusters=top_tables,
        remainder_count=remainder_count,
    )
