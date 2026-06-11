import pandas as pd

from engines.cross_table_engine import compute_planned_correlations, validate_llm_plan
from ontology.models import RelationshipInfo


def _relationship() -> RelationshipInfo:
    return RelationshipInfo(
        child_table="orders",
        child_column="user_id",
        parent_table="users",
        parent_column="id",
        relationship_type="inferred_fk",
        status="inferred",
        confidence=0.95,
    )


def test_validate_llm_plan_rejects_unknown_pairs():
    raw_plan = {
        "correlation_pairs": [
            {
                "parent_table": "users",
                "parent_column": "id",
                "child_table": "orders",
                "child_column": "user_id",
                "aggregate_method": "mean",
            },
            {
                "parent_table": "users",
                "parent_column": "missing",
                "child_table": "orders",
                "child_column": "user_id",
                "aggregate_method": "mean",
            },
        ]
    }

    plan = validate_llm_plan(
        raw_plan,
        {"users": ["id"], "orders": ["user_id"]},
        [_relationship()],
    )

    assert len(plan.correlation_pairs) == 1
    assert plan.skipped_pairs


def test_compute_planned_correlations_returns_numeric_pairs():
    plan = validate_llm_plan(
        {
            "correlation_pairs": [
                {
                    "parent_table": "users",
                    "parent_column": "id",
                    "child_table": "orders",
                    "child_column": "user_id",
                    "aggregate_method": "mean",
                }
            ]
        },
        {"users": ["id"], "orders": ["user_id"]},
        [_relationship()],
    )

    records = compute_planned_correlations(
        {
            "users": pd.DataFrame({"id": [1, 2, 3, 4]}),
            "orders": pd.DataFrame({"user_id": [1, 2, 3, 4]}),
        },
        plan,
    )

    assert records[0].coefficient == 1.0
