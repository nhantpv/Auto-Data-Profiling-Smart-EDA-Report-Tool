"""Graph Reconstruction — L2c: xây relationship graph + JOIN_CARDINALITY.

Xem ARCHITECT v5.4 §5.5 (L2c).

Input: tables dict + schema (InferredSchema hoặc ConfirmedSchema)
Output: GraphResult (edges với cardinality, PK runtime check)
"""
from __future__ import annotations

import pandas as pd

from ontology.models import (
    GraphEdge,
    GraphResult,
    RelationshipInfo,
    SchemaEvaluationFindings,
)


def reconstruct_graph(
    tables: dict[str, pd.DataFrame],
    schema: SchemaEvaluationFindings | None = None,
) -> GraphResult:
    """
    1. Đọc relationships từ schema (hoặc infer nếu schema=None)
    2. Xây relationship graph
    3. Gắn JOIN_CARDINALITY cho mỗi edge (1:1 / 1:N / N:N)
    4. Runtime PK uniqueness check (v5.3)
    5. Emit NON_UNIQUE_PARENT_PK nếu vi phạm

    Returns:
        GraphResult với edges[], warnings[], non_unique_pk_tables[]
    """
    # TODO: Member A implement
    raise NotImplementedError("reconstruct_graph() — Member A implement")


def classify_cardinality(
    child_df: pd.DataFrame,
    child_column: str,
    parent_df: pd.DataFrame,
    parent_column: str,
) -> str:
    """Xác định cardinality: 1:1, 1:N, hoặc N:N."""
    # TODO: Member A implement
    raise NotImplementedError("classify_cardinality() — Member A implement")


def check_pk_uniqueness(df: pd.DataFrame, pk_column: str) -> bool:
    """Runtime check: PK column có unique không. Emit warning nếu không."""
    # TODO: Member A implement
    raise NotImplementedError("check_pk_uniqueness() — Member A implement")
