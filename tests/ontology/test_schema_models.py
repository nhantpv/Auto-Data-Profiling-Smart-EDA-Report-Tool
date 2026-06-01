import pytest
from ontology.models import SchemaMeta, TableInfo, IntegrityError, SchemaEvaluationFindings


class TestSchemaEvaluationFindings:
    def test_valid_schema_findings(self):
        findings = SchemaEvaluationFindings(
            schema_meta=SchemaMeta(
                dbml_file="ecommerce.dbml",
                total_tables=3,
                total_relationships=2,
            ),
            tables=[
                TableInfo(name="orders", columns=["id", "user_id", "total"]),
                TableInfo(name="users", columns=["id", "name"]),
            ],
            integrity_errors=[
                IntegrityError(
                    error_type="ORPHAN_FOREIGN_KEY",
                    description="15 orders have invalid user_id",
                    severity="CRITICAL",
                    affected_table="orders",
                    affected_count=15,
                    top_10_samples=[{"order_id": 101, "invalid_user_id": 9999}],
                )
            ],
        )
        assert findings.schema_meta.total_tables == 3
        assert len(findings.integrity_errors) == 1
        assert findings.integrity_errors[0].severity == "CRITICAL"

    def test_empty_errors(self):
        findings = SchemaEvaluationFindings(
            schema_meta=SchemaMeta(
                dbml_file="clean.dbml", total_tables=2, total_relationships=1
            ),
            tables=[TableInfo(name="t1", columns=["id"])],
            integrity_errors=[],
        )
        assert len(findings.integrity_errors) == 0

    def test_roundtrip_json(self):
        findings = SchemaEvaluationFindings(
            schema_meta=SchemaMeta(
                dbml_file="x.dbml", total_tables=1, total_relationships=0
            ),
            tables=[],
            integrity_errors=[],
        )
        json_str = findings.model_dump_json()
        restored = SchemaEvaluationFindings.model_validate_json(json_str)
        assert restored.schema_meta.dbml_file == "x.dbml"


class TestIntegrityErrorAffectedColumn:
    def test_affected_column_set(self):
        err = IntegrityError(
            error_type="TYPE_MISMATCH",
            description="age has wrong type",
            severity="HIGH",
            affected_table="users",
            affected_column="age",
        )
        assert err.affected_column == "age"

    def test_affected_column_default_none(self):
        err = IntegrityError(
            error_type="ORPHAN_FOREIGN_KEY",
            description="orphan rows",
            severity="CRITICAL",
            affected_table="orders",
        )
        assert err.affected_column is None
