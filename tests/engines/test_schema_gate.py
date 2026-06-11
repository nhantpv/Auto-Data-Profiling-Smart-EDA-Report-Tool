import json

import pandas as pd

from engines.schema_gate import apply_schema_gate
from ontology.models import RelationshipInfo, SchemaEvaluationFindings, SchemaMeta, TableInfo


def _schema() -> SchemaEvaluationFindings:
    return SchemaEvaluationFindings(
        schema_meta=SchemaMeta(schema_file="inferred_from_data", total_tables=2, total_relationships=1),
        tables=[
            TableInfo(name="orders", columns=["id", "user_id"]),
            TableInfo(name="users", columns=["id"]),
        ],
        relationships=[
            RelationshipInfo(
                child_table="orders",
                child_column="user_id",
                parent_table="users",
                parent_column="id",
                relationship_type="inferred_fk",
                status="inferred_from_data",
                confidence=0.95,
            )
        ],
    )


def test_schema_gate_quick_mode_selects_fact_table():
    tables = {
        "orders": pd.DataFrame({"id": [1, 2], "user_id": [10, 11]}),
        "users": pd.DataFrame({"id": [10, 11]}),
    }

    result = apply_schema_gate(_schema(), tables)

    assert result.mode == "quick"
    assert result.schema_status == "inferred"
    assert result.fact_table == "orders"
    assert result.relationships[0].child_table == "orders"


def test_schema_gate_precise_mode_uses_confirmation_file(tmp_path):
    confirmation = tmp_path / "confirmed.json"
    confirmation.write_text(
        json.dumps({
            "mode": "precise",
            "schema_status": "confirmed",
            "fact_table": "orders",
            "relationships": [
                {
                    "child_table": "orders",
                    "child_column": "user_id",
                    "parent_table": "users",
                    "parent_column": "id",
                }
            ],
        }),
        encoding="utf-8",
    )
    tables = {
        "orders": pd.DataFrame({"id": [1, 2], "user_id": [10, 11]}),
        "users": pd.DataFrame({"id": [10, 11]}),
    }

    result = apply_schema_gate(_schema(), tables, confirmation)

    assert result.mode == "precise"
    assert result.schema_status == "confirmed"
    assert result.fact_table == "orders"
    assert result.relationships[0].status == "confirmed_by_user"
