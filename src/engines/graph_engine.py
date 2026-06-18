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
    IntegrityError,
    RelationshipInfo,
    SchemaEvaluationFindings,
    Severity,
)
from ontology.finding_registry import FindingRegistry
from ontology.issue_catalog import get_causes, get_fixes

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


def classify_relationship_role(cardinality: str, child_table: str, parent_table: str) -> str:
    """Classify the role of an accepted relationship edge.

    L2c does not force a single global fact table.  The role is local to this
    edge and describes how the child side should be interpreted by downstream
    cross-table analysis.
    """
    if cardinality == "1:N":
        return "fact_to_dimension"
    if cardinality == "1:1":
        return "one_to_one"
    if cardinality == "N:N":
        return "invalid_many_to_many"
    return "unknown"


def _relationship_key(
    child_table: str,
    child_column: str,
    parent_table: str,
    parent_column: str,
) -> tuple[str, str, str, str]:
    return (
        child_table.lower(),
        child_column.lower(),
        parent_table.lower(),
        parent_column.lower(),
    )


def accepted_relationships_from_graph(
    relationships: list[RelationshipInfo],
    graph: GraphResult,
) -> list[RelationshipInfo]:
    """Return relationships that survived L2c runtime graph checks."""
    edge_by_key = {
        _relationship_key(edge.child_table, edge.child_column, edge.parent_table, edge.parent_column): edge
        for edge in graph.edges
    }
    accepted: list[RelationshipInfo] = []
    for rel in relationships:
        edge = edge_by_key.get(
            _relationship_key(rel.child_table, rel.child_column, rel.parent_table, rel.parent_column)
        )
        if edge is None:
            continue
        accepted.append(rel.model_copy(update={
            "cardinality": edge.cardinality,
            "role": edge.role,
        }))
    return accepted


def reconstruct_graph(
    tables: dict[str, pd.DataFrame],
    schema: SchemaEvaluationFindings | None = None,
    composite_pk_tables: set[str] | None = None,
) -> GraphResult:
    """Reconstruct relationship graph with cardinality and PK validation.

    1. Lấy relationships từ schema.relationships
    2. Với mỗi relationship:
       a. classify_cardinality(child_df, child_col, parent_df, parent_col)
       b. check_pk_uniqueness(parent_df, parent_col)
       c. Tạo GraphEdge
    3. Nếu PK không unique → thêm vào non_unique_pk_tables + warning
       (EXCEPTION: junction/bridge tables with composite PK are skipped —
       their individual columns are intentionally non-unique)

    Args:
        tables: Dict mapping table_name → DataFrame.
        schema: Parsed schema with relationships. If None, returns empty graph.
        composite_pk_tables: Set of table names known to have composite PKs
            (e.g. PlaylistTrack). NON_UNIQUE_PARENT_PK is suppressed for these.

    Returns:
        GraphResult với edges[], warnings[], non_unique_pk_tables[]
    """
    if schema is None or not schema.relationships:
        return GraphResult(
            warnings=["No schema or relationships provided — graph is empty"],
        )

    _composite_pk_tables: set[str] = composite_pk_tables or set()

    edges: list[GraphEdge] = []
    integrity_errors: list[IntegrityError] = []
    warnings: list[str] = []
    non_unique_pk_tables: list[str] = []
    seen_non_unique: set[str] = set()
    registry = FindingRegistry()

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

        # PK runtime uniqueness check.
        # Junction tables (composite PK) intentionally have non-unique individual
        # columns — suppress NON_UNIQUE_PARENT_PK for them to avoid false positives.
        pk_unique = check_pk_uniqueness(parent_df, parent_column)
        if not pk_unique and parent_table not in _composite_pk_tables:
            duplicate_count = int(parent_df[parent_column].duplicated(keep=False).sum())
            if parent_table not in seen_non_unique:
                seen_non_unique.add(parent_table)
                non_unique_pk_tables.append(parent_table)
            warning = (
                f"NON_UNIQUE_PARENT_PK: '{parent_table}.{parent_column}' "
                f"has duplicate values; safe join must collapse parent rows "
                f"before using edge {child_table}.{child_column} -> "
                f"{parent_table}.{parent_column}"
            )
            warnings.append(warning)
            integrity_errors.append(registry.register_integrity_error(IntegrityError(
                error_type="NON_UNIQUE_PARENT_PK",
                description=warning,
                severity=Severity.CRITICAL,
                affected_table=parent_table,
                affected_column=parent_column,
                affected_count=duplicate_count,
                dq_dimensions=["Uniqueness"],
                ml_impact=["join_fanout", "cross_table_correlation_bias"],
                relationship=rel,
                top_10_samples=parent_df[parent_df[parent_column].duplicated(keep=False)]
                .head(10)
                .to_dict(orient="records"),
                probable_causes=get_causes("NON_UNIQUE_PARENT_PK"),
                suggested_fix=get_fixes("NON_UNIQUE_PARENT_PK"),
            )))
        elif not pk_unique and parent_table in _composite_pk_tables:
            # Junction table: log info but don't raise integrity error
            logger.info(
                "Skipping NON_UNIQUE_PARENT_PK for junction table '%s.%s' "
                "(composite PK — individual column non-uniqueness is expected)",
                parent_table, parent_column,
            )

        role = classify_relationship_role(cardinality, child_table, parent_table)

        edges.append(GraphEdge(
            child_table=child_table,
            child_column=child_column,
            parent_table=parent_table,
            parent_column=parent_column,
            cardinality=cardinality,
            role=role,
            pk_runtime_unique=pk_unique,
            confidence=rel.confidence,
        ))

    logger.info(
        "reconstruct_graph: %d edges, %d warnings, %d non-unique PK tables",
        len(edges), len(warnings), len(non_unique_pk_tables),
    )

    return GraphResult(
        edges=edges,
        integrity_errors=integrity_errors,
        warnings=warnings,
        non_unique_pk_tables=non_unique_pk_tables,
    )
