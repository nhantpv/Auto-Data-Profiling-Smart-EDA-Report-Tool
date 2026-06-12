import json

import pandas as pd

from engines import cross_table_engine
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


def test_call_openai_plan_strips_json_fences(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")

    class FakeResponse:
        def __enter__(self):
            return self

        def __exit__(self, _exc_type, _exc, _tb):
            return False

        def read(self):
            return json.dumps({
                "output_text": (
                    "```json\n"
                    '{"correlation_pairs": [], "skipped_pairs": [{"reason": "none"}]}'
                    "\n```"
                )
            }).encode("utf-8")

    def fake_urlopen(_request, timeout):
        assert timeout == 30
        return FakeResponse()

    monkeypatch.setattr(cross_table_engine.urllib.request, "urlopen", fake_urlopen)

    raw = cross_table_engine._call_openai_plan("{}")

    assert raw["correlation_pairs"] == []
    assert raw["skipped_pairs"][0]["reason"] == "none"


def test_validate_llm_plan_rejects_unknown_pairs():
    raw_plan = {
        "correlation_pairs": [
            {
                "parent_table": "users",
                "parent_column": "id",
                "parent_value_column": "credit_score",
                "child_table": "orders",
                "child_column": "user_id",
                "child_value_column": "total",
                "aggregate_method": "mean",
            },
            {
                "parent_table": "users",
                "parent_column": "missing",
                "parent_value_column": "credit_score",
                "child_table": "orders",
                "child_column": "user_id",
                "child_value_column": "total",
                "aggregate_method": "mean",
            },
        ]
    }

    plan = validate_llm_plan(
        raw_plan,
        {"users": ["id", "credit_score"], "orders": ["user_id", "total"]},
        [_relationship()],
    )

    assert len(plan.correlation_pairs) == 1
    assert plan.skipped_pairs


def test_validate_llm_plan_normalizes_string_skipped_pairs():
    plan = validate_llm_plan(
        {
            "correlation_pairs": [],
            "skipped_pairs": ["No meaningful numeric measure pair exists."],
        },
        {"users": ["id", "credit_score"], "orders": ["user_id", "total"]},
        [_relationship()],
    )

    assert plan.skipped_pairs == [{"reason": "No meaningful numeric measure pair exists."}]


def test_validate_llm_plan_rejects_identifier_measures_and_same_table():
    same_table_relationship = RelationshipInfo(
        child_table="users",
        child_column="manager_id",
        parent_table="users",
        parent_column="id",
        relationship_type="inferred_fk",
        status="inferred",
        confidence=0.95,
    )
    raw_plan = {
        "correlation_pairs": [
            {
                "parent_table": "users",
                "parent_column": "id",
                "parent_value_column": "id",
                "child_table": "orders",
                "child_column": "user_id",
                "child_value_column": "order_id",
                "aggregate_method": "mean",
            },
            {
                "parent_table": "users",
                "parent_column": "id",
                "parent_value_column": "credit_score",
                "child_table": "users",
                "child_column": "manager_id",
                "child_value_column": "salary",
                "aggregate_method": "mean",
            },
        ]
    }

    plan = validate_llm_plan(
        raw_plan,
        {"users": ["id", "manager_id", "credit_score", "salary"], "orders": ["user_id", "order_id"]},
        [_relationship(), same_table_relationship],
    )

    assert not plan.correlation_pairs
    reasons = [reason for item in plan.skipped_pairs for reason in item["reasons"]]
    assert "parent_value_column_matches_join_key" in reasons
    assert "identifier_child_value_column:order_id" in reasons
    assert "same_table_pair" in reasons


def test_compute_planned_correlations_returns_numeric_pairs():
    n = 40
    plan = validate_llm_plan(
        {
            "correlation_pairs": [
                {
                    "parent_table": "users",
                    "parent_column": "id",
                    "parent_value_column": "credit_score",
                    "child_table": "orders",
                    "child_column": "user_id",
                    "child_value_column": "total",
                    "aggregate_method": "mean",
                }
            ]
        },
        {"users": ["id", "credit_score"], "orders": ["user_id", "total"]},
        [_relationship()],
    )

    records = compute_planned_correlations(
        {
            "users": pd.DataFrame({
                "id": list(range(1, n + 1)),
                "credit_score": [float(i) for i in range(1, n + 1)],
            }),
            "orders": pd.DataFrame({
                "user_id": list(range(1, n + 1)),
                "total": [float(i) for i in range(1, n + 1)],
            }),
        },
        plan,
    )

    assert records[0].coefficient == 1.0
    assert records[0].method == "pearson_aggregate_before_join_mean"


def test_compute_planned_correlations_uses_measure_columns_before_join():
    n = 40
    plan = validate_llm_plan(
        {
            "correlation_pairs": [
                {
                    "parent_table": "users",
                    "parent_column": "id",
                    "parent_value_column": "credit_score",
                    "child_table": "orders",
                    "child_column": "user_id",
                    "child_value_column": "total",
                    "aggregate_method": "sum",
                }
            ]
        },
        {"users": ["id", "credit_score"], "orders": ["user_id", "total"]},
        [_relationship()],
    )

    records = compute_planned_correlations(
        {
            "users": pd.DataFrame({
                "id": list(range(1, n + 1)),
                "credit_score": [float(i) for i in range(1, n + 1)],
            }),
            "orders": pd.DataFrame({
                "user_id": list(range(1, n + 1)),
                "total": [float(i * 10) for i in range(1, n + 1)],
            }),
        },
        plan,
    )

    assert records
    assert records[0].left_feature == "users.credit_score"
    assert records[0].right_feature == "orders.sum(total)_by_user_id"
