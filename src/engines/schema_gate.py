from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from engines.cross_table_engine import choose_fact_table
from ontology.models import RelationshipInfo, SchemaEvaluationFindings, SchemaGateResult


def _relationship_from_dict(raw: dict[str, Any]) -> RelationshipInfo:
    return RelationshipInfo(
        child_table=str(raw["child_table"]),
        child_column=str(raw["child_column"]),
        parent_table=str(raw["parent_table"]),
        parent_column=str(raw["parent_column"]),
        relationship_type=str(raw.get("relationship_type", "confirmed_fk")),
        status=str(raw.get("status", "confirmed_by_user")),
        confidence=float(raw.get("confidence", 1.0)),
        evidence=list(raw.get("evidence", ["Confirmed by user in L2b.5"])),
        decision=str(raw.get("decision", "declared_relationship")),
        confidence_bucket=str(raw.get("confidence_bucket", "DECLARED")),
        decision_reasons=list(raw.get("decision_reasons", ["confirmed_by_user"])),
        blocked_reasons=list(raw.get("blocked_reasons", [])),
        evidence_metrics=dict(raw.get("evidence_metrics", {"confirmed_by_user": True})),
    )


def _validate_fact_table(fact_table: str | None, tables: dict[str, pd.DataFrame], warnings: list[str]) -> str | None:
    if fact_table is None:
        return None
    if fact_table in tables:
        return fact_table
    warnings.append(f"Requested fact table '{fact_table}' is not loaded; falling back to automatic choice.")
    return None


def _validate_relationships(
    relationships: list[RelationshipInfo],
    tables: dict[str, pd.DataFrame],
) -> tuple[list[RelationshipInfo], list[str]]:
    valid: list[RelationshipInfo] = []
    warnings: list[str] = []
    for rel in relationships:
        child = tables.get(rel.child_table)
        parent = tables.get(rel.parent_table)
        reasons: list[str] = []
        if child is None:
            reasons.append(f"missing_child_table:{rel.child_table}")
        elif rel.child_column not in child.columns:
            reasons.append(f"missing_child_column:{rel.child_table}.{rel.child_column}")
        if parent is None:
            reasons.append(f"missing_parent_table:{rel.parent_table}")
        elif rel.parent_column not in parent.columns:
            reasons.append(f"missing_parent_column:{rel.parent_table}.{rel.parent_column}")
        if reasons:
            warnings.append(
                f"Skipped relationship {rel.child_table}.{rel.child_column} -> "
                f"{rel.parent_table}.{rel.parent_column}: {', '.join(reasons)}"
            )
            continue
        valid.append(rel)
    return valid, warnings


def load_schema_confirmation(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def apply_schema_gate(
    schema: SchemaEvaluationFindings,
    tables: dict[str, pd.DataFrame],
    confirmation_path: str | Path | None = None,
    fact_table_override: str | None = None,
) -> SchemaGateResult:
    """L2b.5 gate.

    Quick Mode: no confirmation file; use schema/inferred relationships with
    explicit ``schema_status=inferred`` and an automatic fact table suggestion.
    Precise Mode: JSON confirmation may override relationships and fact table.
    """
    warnings: list[str] = []
    mode = "quick"
    source = "auto"
    schema_status = "inferred"
    relationships = list(schema.relationships)
    fact_table = fact_table_override

    if confirmation_path is not None:
        raw = load_schema_confirmation(confirmation_path)
        mode = str(raw.get("mode", "precise"))
        source = str(confirmation_path)
        schema_status = str(raw.get("schema_status", "confirmed"))
        fact_table = str(raw.get("fact_table")) if raw.get("fact_table") else fact_table
        if "relationships" in raw:
            relationships = [_relationship_from_dict(item) for item in raw.get("relationships", [])]

    relationships, relationship_warnings = _validate_relationships(relationships, tables)
    warnings.extend(relationship_warnings)
    fact_table = _validate_fact_table(fact_table, tables, warnings)
    if fact_table is None:
        fact_table = choose_fact_table(tables, relationships)
        if fact_table is not None:
            warnings.append(f"Fact table selected automatically: {fact_table}")

    return SchemaGateResult(
        mode=mode,
        schema_status=schema_status,
        fact_table=fact_table,
        relationships=relationships,
        warnings=warnings,
        source=source,
    )
