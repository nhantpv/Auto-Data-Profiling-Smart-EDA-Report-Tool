"""Graph Reconstruction — L2c: xây relationship graph + JOIN_CARDINALITY.

Xem ARCHITECT v5.4 §5.5 (L2c).

Input: tables dict + schema (SchemaEvaluationFindings)
Output: GraphResult (edges với cardinality, PK runtime check)
"""
from __future__ import annotations

import logging

import pandas as pd

from ontology.models import (
    GraphEdge,
    GraphResult,
    RelationshipInfo,
    SchemaEvaluationFindings,
)

logger = logging.getLogger(__name__)


def check_pk_uniqueness(df: pd.DataFrame, pk_column: str) -> bool:
    """Runtime check: PK column có unique không.

    Args:
        df: DataFrame chứa PK column.
        pk_column: Tên column cần check.

    Returns:
        True nếu column unique (valid PK), False nếu có duplicates.
    """
    if pk_column not in df.columns:
        logger.warning("check_pk_uniqueness: column '%s' not found", pk_column)
        return False
    return bool(df[pk_column].is_unique)


def classify_cardinality(
    child_df: pd.DataFrame,
    child_column: str,
    parent_df: pd.DataFrame,
    parent_column: str,
) -> str:
    """Xác định cardinality: 1:1, 1:N, hoặc N:N.

    Logic:
        - parent_column unique AND child_column unique → 1:1
        - parent_column unique AND child_column NOT unique → 1:N
        - parent_column NOT unique → N:N (invalid FK design)

    Args:
        child_df: Child table DataFrame.
        child_column: FK column in child table.
        parent_df: Parent table DataFrame.
        parent_column: PK column in parent table.

    Returns:
        Cardinality string: "1:1", "1:N", or "N:N".
    """
    if child_column not in child_df.columns or parent_column not in parent_df.columns:
        return "UNKNOWN"

    parent_unique = parent_df[parent_column].is_unique
    child_unique = child_df[child_column].is_unique

    if parent_unique and child_unique:
        return "1:1"
    if parent_unique and not child_unique:
        return "1:N"
    return "N:N"


def reconstruct_graph(
    tables: dict[str, pd.DataFrame],
    schema: SchemaEvaluationFindings | None = None,
) -> GraphResult:
    """Reconstruct relationship graph with cardinality and PK validation.

    1. Lấy relationships từ schema.relationships
    2. Với mỗi relationship:
       a. classify_cardinality(child_df, child_col, parent_df, parent_col)
       b. check_pk_uniqueness(parent_df, parent_col)
       c. Tạo GraphEdge
    3. Nếu PK không unique → thêm vào non_unique_pk_tables + warning

    Args:
        tables: Dict mapping table_name → DataFrame.
        schema: Parsed schema with relationships. If None, returns empty graph.

    Returns:
        GraphResult với edges[], warnings[], non_unique_pk_tables[]
    """
    if schema is None or not schema.relationships:
        return GraphResult(
            warnings=["No schema or relationships provided — graph is empty"],
        )

    edges: list[GraphEdge] = []
    warnings: list[str] = []
    non_unique_pk_tables: list[str] = []
    seen_non_unique: set[str] = set()

    for rel in schema.relationships:
        child_table = rel.child_table
        parent_table = rel.parent_table
        child_column = rel.child_column
        parent_column = rel.parent_column

        # Validate tables exist
        child_df = tables.get(child_table)
        parent_df = tables.get(parent_table)
        if child_df is None:
            warnings.append(f"Table '{child_table}' not found in loaded tables")
            continue
        if parent_df is None:
            warnings.append(f"Table '{parent_table}' not found in loaded tables")
            continue

        # Validate columns exist
        if child_column not in child_df.columns:
            warnings.append(f"Column '{child_column}' not found in table '{child_table}'")
            continue
        if parent_column not in parent_df.columns:
            warnings.append(f"Column '{parent_column}' not found in table '{parent_table}'")
            continue

        # Classify cardinality
        cardinality = classify_cardinality(child_df, child_column, parent_df, parent_column)

        # PK runtime uniqueness check (v5.3)
        pk_unique = check_pk_uniqueness(parent_df, parent_column)
        if not pk_unique and parent_table not in seen_non_unique:
            seen_non_unique.add(parent_table)
            non_unique_pk_tables.append(parent_table)
            warnings.append(
                f"NON_UNIQUE_PARENT_PK: '{parent_table}.{parent_column}' "
                f"has duplicate values — join may inflate rows"
            )

        edges.append(GraphEdge(
            child_table=child_table,
            child_column=child_column,
            parent_table=parent_table,
            parent_column=parent_column,
            cardinality=cardinality,
            pk_runtime_unique=pk_unique,
            confidence=rel.confidence,
        ))

    logger.info(
        "reconstruct_graph: %d edges, %d warnings, %d non-unique PK tables",
        len(edges), len(warnings), len(non_unique_pk_tables),
    )

    return GraphResult(
        edges=edges,
        warnings=warnings,
        non_unique_pk_tables=non_unique_pk_tables,
    )
