import pandas as pd

from engines.graph_engine import accepted_relationships_from_graph, reconstruct_graph
from ontology.models import RelationshipInfo, SchemaEvaluationFindings, SchemaMeta


def _rel() -> RelationshipInfo:
    return RelationshipInfo(
        child_table="orders",
        child_column="user_id",
        parent_table="users",
        parent_column="id",
        relationship_type="inferred_fk",
        status="inferred",
        confidence=0.95,
    )


def _schema(rel: RelationshipInfo) -> SchemaEvaluationFindings:
    return SchemaEvaluationFindings(
        schema_meta=SchemaMeta(schema_file="inferred", total_tables=2, total_relationships=1),
        tables=[],
        relationships=[rel],
    )


def test_graph_skips_non_unique_parent_pk_and_emits_integrity_error():
    tables = {
        "orders": pd.DataFrame({"user_id": [1, 2, 2], "total": [10, 20, 30]}),
        "users": pd.DataFrame({"id": [1, 1, 2], "score": [100, 999, 200]}),
    }

    graph = reconstruct_graph(tables, _schema(_rel()))

    assert graph.edges == []
    assert graph.integrity_errors[0].error_type == "NON_UNIQUE_PARENT_PK"
    assert graph.integrity_errors[0].severity == "CRITICAL"
    assert graph.non_unique_pk_tables == ["users"]
    assert accepted_relationships_from_graph([_rel()], graph) == []


def test_graph_enriches_accepted_relationships_with_cardinality_and_role():
    tables = {
        "orders": pd.DataFrame({"user_id": [1, 2, 2], "total": [10, 20, 30]}),
        "users": pd.DataFrame({"id": [1, 2], "score": [100, 200]}),
    }

    graph = reconstruct_graph(tables, _schema(_rel()))
    accepted = accepted_relationships_from_graph([_rel()], graph)

    assert len(graph.edges) == 1
    assert graph.edges[0].cardinality == "1:N"
    assert graph.edges[0].role == "fact_to_dimension"
    assert accepted[0].cardinality == "1:N"
    assert accepted[0].role == "fact_to_dimension"
