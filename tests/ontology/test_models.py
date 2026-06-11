import pytest
from ontology.models import DatasetMeta, ColumnStats, AnomalyRecord, DataQualityFindings


class TestDatasetMeta:
    def test_valid_meta(self):
        meta = DatasetMeta(
            file_name="test.csv",
            n=1000,
            n_var=5,
            memory_size=1024,
            p_cells_missing=0.05,
            n_duplicates=10,
            p_duplicates=0.01,
            overview_charts={"heatmap": "path/to/img.png"},
        )
        assert meta.n == 1000
        assert meta.n_duplicates == 10

    def test_meta_defaults(self):
        meta = DatasetMeta(
            file_name="x.csv", n=1, n_var=1, memory_size=0, p_cells_missing=0.0
        )
        assert meta.overview_charts == {}
        assert meta.n_duplicates == 0


class TestColumnStats:
    def test_numeric_column(self):
        col = ColumnStats(
            type="Numeric",
            n_missing=10,
            p_missing=0.1,
            additional_metrics={"mean": 25.5, "std": 3.2},
        )
        assert col.additional_metrics["mean"] == 25.5

    def test_categorical_column(self):
        col = ColumnStats(
            type="Categorical",
            n_missing=0,
            p_missing=0.0,
            n_distinct=5,
            additional_metrics={},
        )
        assert col.n_distinct == 5


class TestAnomalyRecord:
    def test_valid_anomaly(self):
        rec = AnomalyRecord(
            issue_type="OUTLIER_ENSEMBLE",
            description="Found 10 outliers",
            severity="HIGH",
            dq_dimensions=["Accuracy"],
            ml_impact=["training_bias"],
            compound_severity="HIGH",
            confidence=0.92,
            affected_count=10,
            affected_percent=0.01,
            top_10_samples=[{"id": 1, "score": 0.99}],
            diagnostic_chart="path/to/chart.png",
            full_anomalies_export_path="path/to/export.csv",
        )
        assert rec.severity == "HIGH"
        assert rec.dq_dimensions == ["Accuracy"]
        assert rec.compound_severity == "HIGH"
        assert len(rec.top_10_samples) == 1

    def test_anomaly_optional_fields(self):
        rec = AnomalyRecord(
            issue_type="DUPLICATE",
            description="Found duplicates",
            severity="WARN",  # NOTE: uses WARN not MEDIUM (MEDIUM not in Severity enum)
            affected_count=5,
            affected_percent=0.005,
            top_10_samples=[],
        )
        assert rec.diagnostic_chart is None


class TestDataQualityFindings:
    def test_full_roundtrip(self):
        findings = DataQualityFindings(
            dataset_meta=DatasetMeta(
                file_name="test.csv", n=100, n_var=3,
                memory_size=500, p_cells_missing=0.02,
            ),
            columns={
                "age": ColumnStats(
                    type="Numeric", n_missing=2, p_missing=0.02,
                    additional_metrics={"mean": 30},
                ),
            },
            anomalies=[],
        )
        json_str = findings.model_dump_json()
        restored = DataQualityFindings.model_validate_json(json_str)
        assert restored.dataset_meta.file_name == "test.csv"
        assert restored.columns["age"].additional_metrics["mean"] == 30


from ontology.models import (
    Severity, SEVERITY_ORDER, Verdict, VerdictSummary, DatasetVerdict,
    IntegrityError, MissingFieldContext, RelationshipInfo, SchemaEvaluationFindings,
    SchemaMeta, TableInfo,
)


class TestSeverityOrder:
    def test_order_is_ascending(self):
        assert SEVERITY_ORDER == (Severity.INFO, Severity.WARN, Severity.HIGH, Severity.CRITICAL)


class TestDatasetVerdict:
    def test_roundtrip(self):
        dv = DatasetVerdict(
            dataset_meta=DatasetMeta(file_name="x.csv", n=10, n_var=2,
                                     memory_size=1, p_cells_missing=0.0),
            verdict=Verdict.WARN,
            verdict_rationale="1 CRITICAL orphan FK",
            summary=VerdictSummary(total_issues=3, critical=1, high=1, warn=1),
        )
        restored = DatasetVerdict.model_validate_json(dv.model_dump_json())
        assert restored.verdict == Verdict.WARN
        assert restored.summary.critical == 1


class TestColumnZeros:
    def test_n_zeros_optional(self):
        assert ColumnStats(type="Categorical", n_missing=0, p_missing=0.0).n_zeros is None
        assert ColumnStats(type="Numeric", n_missing=0, p_missing=0.0, n_zeros=5).n_zeros == 5


class TestAnomalyRecordAffectedColumn:
    def test_affected_column_set(self):
        rec = AnomalyRecord(
            issue_type="MISSINGNESS",
            description="bmi has 20% missing",
            severity="WARN",
            affected_count=200,
            affected_percent=0.2,
            top_10_samples=[],
            affected_column="bmi",
        )
        assert rec.affected_column == "bmi"

    def test_affected_column_default_none(self):
        rec = AnomalyRecord(
            issue_type="OUTLIER_ENSEMBLE",
            description="multivariate outliers",
            severity="HIGH",
            affected_count=5,
            affected_percent=0.05,
            top_10_samples=[],
        )
        assert rec.affected_column is None


class TestSchemaContextModels:
    def test_missing_field_context_roundtrip(self):
        err = IntegrityError(
            error_type="MISSING_COLUMN",
            description="missing school id",
            severity="CRITICAL",
            affected_table="students",
            affected_column="id_school",
            missing_field_context=MissingFieldContext(
                expected_column="id_school",
                inferred_meaning="school identifier or school attribute",
                candidate_aliases=["trường học"],
            ),
        )
        restored = IntegrityError.model_validate_json(err.model_dump_json())
        assert restored.missing_field_context is not None
        assert restored.missing_field_context.expected_column == "id_school"
        assert restored.missing_field_context.is_intentional_missing is None

    def test_relationships_roundtrip(self):
        schema = SchemaEvaluationFindings(
            schema_meta=SchemaMeta(schema_file="shop.dbml", total_tables=2, total_relationships=0),
            tables=[
                TableInfo(name="schools", columns=["id"]),
                TableInfo(name="students", columns=["id_school"]),
            ],
            relationships=[
                RelationshipInfo(
                    child_table="students",
                    child_column="id_school",
                    parent_table="schools",
                    parent_column="id",
                    relationship_type="inferred_fk",
                    status="missing_from_schema",
                    confidence=0.91,
                    evidence=["value_coverage=1.000"],
                )
            ],
        )
        restored = SchemaEvaluationFindings.model_validate_json(schema.model_dump_json())
        assert restored.relationships[0].relationship_type == "inferred_fk"
        assert restored.relationships[0].status == "missing_from_schema"


class TestArchitectV54Contract:
    """New contract fields per ARCHITECT v5.4 (§3, §5.5d, §9.2, §9.5, §9.6, §9.7)."""

    def test_provenance_enum_matches_architecture(self):
        from ontology.models import Provenance

        values = {p.value for p in Provenance}
        assert values == {"OBSERVED", "INFERRED", "INDETERMINATE", "DERIVED_CROSS_TABLE"}

    def test_disposition_enum_and_fields(self):
        from ontology.models import Disposition, IntegrityError, IssueSummary, Severity

        assert {d.value for d in Disposition} == {"BLOCK", "PREPROCESS", "REVIEW", "SIGNAL"}
        record = AnomalyRecord(
            issue_type="MISSINGNESS", description="x", severity=Severity.WARN,
            affected_count=1, affected_percent=0.1, top_10_samples=[],
        )
        assert record.disposition is None
        error = IntegrityError(
            error_type="ORPHAN_FOREIGN_KEY", description="x",
            severity=Severity.CRITICAL, affected_table="orders",
        )
        assert error.disposition is None
        summary = IssueSummary(
            source="dq", issue_type="MISSINGNESS", effective_severity=Severity.WARN,
            severity=Severity.WARN, rationale="x",
        )
        assert summary.disposition is None

    def test_column_stats_effective_severity_and_confidence(self):
        col = ColumnStats(type="Numeric", n_missing=0, p_missing=0.0)
        assert col.effective_severity is None
        assert col.confidence is None

    def test_issue_detail_ref_table_key(self):
        from ontology.models import IssueDetailRef

        ref = IssueDetailRef(file="f.json", collection="anomalies", index=0)
        assert ref.table is None

    def test_relationship_cardinality_and_role(self):
        from ontology.models import RelationshipInfo

        rel = RelationshipInfo(
            child_table="orders", child_column="user_id", parent_table="users",
            parent_column="id", relationship_type="fk", status="ok", confidence=1.0,
        )
        assert rel.cardinality is None
        assert rel.role is None

    def test_graph_edge_fanout_fields_and_table_roles(self):
        from ontology.models import GraphEdge, GraphResult

        edge = GraphEdge(
            child_table="orders", child_column="user_id",
            parent_table="users", parent_column="id",
        )
        assert edge.fan_out is False
        assert edge.join_amplification_ratio == 1.0
        assert edge.role == ""
        assert GraphResult().table_roles == {}

    def test_cross_table_pair_contract(self):
        from ontology.models import CrossTableCorrelationsArtifact, CrossTablePair

        pair = CrossTablePair(
            parent_table="users", parent_column="age",
            child_table="orders", child_column="amount", aggregate_method="mean",
        )
        assert pair.status == "OK"
        assert pair.unit_of_analysis == "parent"
        assert pair.provenance == "DERIVED_CROSS_TABLE"
        artifact = CrossTableCorrelationsArtifact()
        assert artifact.schema_version == "cross_table_correlations_v1"
        assert artifact.pairs == []

    def test_llm_plan_timestamp(self):
        from ontology.models import LlmCorrelationPlan

        assert LlmCorrelationPlan().timestamp == ""
