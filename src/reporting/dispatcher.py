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
    # TODO: Member B implement
    raise NotImplementedError("dispatch() — Member B implement")
