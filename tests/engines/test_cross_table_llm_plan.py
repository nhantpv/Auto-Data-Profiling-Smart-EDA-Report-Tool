import numpy as np
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


def _plan(parent_column: str = "age", child_column: str = "amount"):
    return validate_llm_plan(
        {
            "correlation_pairs": [
                {
                    "parent_table": "users",
                    "parent_column": parent_column,
                    "child_table": "orders",
                    "child_column": child_column,
                    "aggregate_method": "mean",
                }
            ]
        },
        {"users": ["id", "age"], "orders": ["user_id", "amount"]},
        [_relationship()],
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


def test_compute_planned_correlations_aggregates_before_join():
    user_ids = list(range(1, 41))
    users = pd.DataFrame({"id": user_ids, "age": user_ids})
    orders = pd.DataFrame({
        "user_id": user_ids * 2,
        "amount": [uid * 2.0 for uid in user_ids * 2],
    })

    records = compute_planned_correlations(
        {"users": users, "orders": orders},
        _plan(),
        [_relationship()],
    )

    assert len(records) == 1
    assert records[0].method == "spearman_agg_mean"
    assert records[0].coefficient == 1.0
    assert records[0].n == 40


def test_compute_planned_correlations_skips_too_few_units():
    user_ids = list(range(1, 11))
    users = pd.DataFrame({"id": user_ids, "age": user_ids})
    orders = pd.DataFrame({"user_id": user_ids, "amount": [uid * 2.0 for uid in user_ids]})

    records = compute_planned_correlations(
        {"users": users, "orders": orders},
        _plan(),
        [_relationship()],
    )

    assert records == []


def test_compute_planned_correlations_skips_high_null_overlap():
    user_ids = list(range(1, 41))
    # Both sides null on the same 32/40 parent rows (80% > 70% gate).
    age = [float(uid) if uid <= 8 else np.nan for uid in user_ids]
    users = pd.DataFrame({"id": user_ids, "age": age})
    orders = pd.DataFrame({
        "user_id": user_ids,
        "amount": [uid * 2.0 if uid <= 8 else np.nan for uid in user_ids],
    })

    records = compute_planned_correlations(
        {"users": users, "orders": orders},
        _plan(),
        [_relationship()],
    )

    assert records == []
