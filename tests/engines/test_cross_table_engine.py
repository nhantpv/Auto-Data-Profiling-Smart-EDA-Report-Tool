from pathlib import Path

import pandas as pd

from engines.cross_table_engine import run_cross_table_analysis
from ontology.models import RelationshipInfo


def _rel(child_table="orders", child_column="user_id", parent_table="users", parent_column="id"):
    return RelationshipInfo(
        child_table=child_table,
        child_column=child_column,
        parent_table=parent_table,
        parent_column=parent_column,
        relationship_type="explicit_fk",
        status="declared_in_schema",
        confidence=1.0,
    )


def test_safe_join_preserves_fact_rows_and_exports_preview(tmp_path):
    orders = pd.DataFrame({
        "order_id": [101, 102, 103, 104],
        "user_id": [1, 2, 2, 3],
        "total": [10.0, 20.0, 30.0, 40.0],
    })
    users = pd.DataFrame({
        "id": [1, 2, 3],
        "credit_score": [100, 200, 300],
    })

    analysis = run_cross_table_analysis({"orders": orders, "users": users}, [_rel()], tmp_path)

    assert analysis.status == "completed"
    assert analysis.fact_table == "orders"
    assert analysis.denormalized_rows == len(orders)
    assert analysis.join_steps[0].status == "joined"
    assert analysis.join_steps[0].before_rows == len(orders)
    assert analysis.join_steps[0].after_rows == len(orders)
    assert analysis.join_steps[0].match_rate == 1.0
    assert analysis.preview_csv_path is not None
    assert Path(analysis.preview_csv_path).exists()
    assert any(
        corr.left_table != corr.right_table
        and "orders__total" in {corr.left_feature, corr.right_feature}
        for corr in analysis.correlations
    )


def test_duplicate_parent_key_is_collapsed_before_join_to_prevent_fanout(tmp_path):
    orders = pd.DataFrame({
        "order_id": [101, 102],
        "user_id": [1, 2],
        "total": [10.0, 20.0],
    })
    users = pd.DataFrame({
        "id": [1, 1, 2],
        "credit_score": [100, 999, 200],
    })

    analysis = run_cross_table_analysis({"orders": orders, "users": users}, [_rel()], tmp_path)
    step = analysis.join_steps[0]

    assert step.status == "joined"
    assert step.parent_key_unique is False
    assert step.after_rows == step.before_rows == len(orders)
    assert any("collapsed" in warning for warning in step.warnings)
