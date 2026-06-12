import pytest
import pandas as pd
from pathlib import Path
from ingestion.schema_reader import parse_schema
from engines.schema_engine import (
    check_foreign_keys,
    load_schema_inference_policy,
    match_table,
    validate_schema_multi,
    validate_table,
)

FIXTURES = Path(__file__).parent.parent / "fixtures"

# Inline DBML for parser tests (no file I/O needed)
_TWO_TABLE_DBML = """
Table users {
  id integer [pk]
  email varchar(255) [unique, not null]
  age integer
}
Table orders {
  order_id bigint [pk, not null]
  user_id integer
}
Ref: orders.user_id > users.id
"""

_ONE_TABLE_DBML = """
Table products {
  product_id integer [pk]
  name varchar [not null]
}
"""


# ──────────────────────────────────────────────
# 1a-1: parse_dbml
# ──────────────────────────────────────────────

class TestParseSchema:
    def _parse_inline(self, src, tmp_path):
        p = tmp_path / "schema.dbml"
        p.write_text(src)
        return parse_schema(str(p))["tables"]

    def test_returns_dict_of_tables(self, tmp_path):
        parsed = self._parse_inline(_TWO_TABLE_DBML, tmp_path)
        assert "users" in parsed
        assert "orders" in parsed

    def test_columns_present(self, tmp_path):
        parsed = self._parse_inline(_TWO_TABLE_DBML, tmp_path)
        assert "id" in parsed["users"]["columns"]
        assert "email" in parsed["users"]["columns"]

    def test_pk_flag(self, tmp_path):
        parsed = self._parse_inline(_TWO_TABLE_DBML, tmp_path)
        assert parsed["users"]["columns"]["id"]["pk"] is True
        assert parsed["users"]["columns"]["age"]["pk"] is False

    def test_unique_flag(self, tmp_path):
        parsed = self._parse_inline(_TWO_TABLE_DBML, tmp_path)
        assert parsed["users"]["columns"]["email"]["unique"] is True
        assert parsed["users"]["columns"]["age"]["unique"] is False

    def test_not_null_flag(self, tmp_path):
        parsed = self._parse_inline(_TWO_TABLE_DBML, tmp_path)
        assert parsed["users"]["columns"]["email"]["not_null"] is True
        assert parsed["users"]["columns"]["age"]["not_null"] is False

    def test_type_stripped_of_size(self, tmp_path):
        # varchar(255) should be stored as-is (raw); family lookup strips parens
        parsed = self._parse_inline(_TWO_TABLE_DBML, tmp_path)
        # type key exists
        assert "type" in parsed["users"]["columns"]["email"]


class TestSchemaInferencePolicy:
    def test_policy_file_overrides_thresholds(self, tmp_path):
        policy_path = tmp_path / "policy.json"
        policy_path.write_text(
            """
{
  "thresholds": {
    "alias_similarity": 0.91
  },
  "token_synonyms": {
    "campus": "school"
  }
}
""",
            encoding="utf-8",
        )

        policy = load_schema_inference_policy(policy_path)

        assert policy["thresholds"]["alias_similarity"] == 0.91
        assert policy["thresholds"]["primary_key_score"] == 0.55
        assert policy["token_synonyms"]["campus"] == "school"


class TestMatchTable:
    def _parse_inline(self, src, tmp_path):
        p = tmp_path / "schema.dbml"
        p.write_text(src)
        return parse_schema(str(p))["tables"]

    def test_single_table_auto_match(self, tmp_path):
        parsed = self._parse_inline(_ONE_TABLE_DBML, tmp_path)
        df = pd.DataFrame({"product_id": [1, 2], "name": ["a", "b"]})
        # any csv name, single table → auto
        assert match_table(df, parsed, "anything.csv") == "products"

    def test_multi_table_match_by_stem(self, tmp_path):
        parsed = self._parse_inline(_TWO_TABLE_DBML, tmp_path)
        df = pd.DataFrame({"id": [1], "email": ["a@b.com"], "age": [30]})
        assert match_table(df, parsed, "users.csv") == "users"

    def test_multi_table_match_case_insensitive(self, tmp_path):
        parsed = self._parse_inline(_TWO_TABLE_DBML, tmp_path)
        df = pd.DataFrame({"id": [1], "email": ["a@b.com"], "age": [30]})
        assert match_table(df, parsed, "Users.csv") == "users"

    def test_multi_table_no_match_raises(self, tmp_path):
        parsed = self._parse_inline(_TWO_TABLE_DBML, tmp_path)
        df = pd.DataFrame({"x": [1]})
        with pytest.raises(ValueError, match="Cannot match"):
            match_table(df, parsed, "invoices.csv")


# ──────────────────────────────────────────────
# 1a-2: validate_table
# ──────────────────────────────────────────────

_CUSTOMERS_DBML = """
Table customers {
  id integer [pk]
  email varchar [unique]
  age integer
  phone varchar
}
"""

_SIMPLE_DBML = """
Table items {
  id integer [pk]
  label varchar [not null]
  score float [unique]
}
"""


class TestValidateTableMissingExtra:
    def _parsed(self, src, tmp_path):
        p = tmp_path / "s.dbml"
        p.write_text(src)
        return parse_schema(str(p))["tables"]

    def test_missing_column_is_critical(self, tmp_path):
        parsed = self._parsed(_CUSTOMERS_DBML, tmp_path)
        # phone is in DBML but not in df
        df = pd.DataFrame({"id": [1], "email": ["a@b.com"], "age": [25]})
        errors = validate_table(df, "customers", parsed)
        missing = [e for e in errors if e.error_type == "MISSING_COLUMN"]
        assert any(e.affected_column == "phone" for e in missing)
        assert all(e.severity.value == "CRITICAL" for e in missing)

    def test_extra_column_is_info(self, tmp_path):
        parsed = self._parsed(_CUSTOMERS_DBML, tmp_path)
        df = pd.DataFrame({"id": [1], "email": ["a@b.com"], "age": [25], "phone": ["123"], "notes": ["hi"]})
        errors = validate_table(df, "customers", parsed)
        extra = [e for e in errors if e.error_type == "EXTRA_COLUMN"]
        assert any(e.affected_column == "notes" for e in extra)
        assert all(e.severity.value == "INFO" for e in extra)

    def test_no_errors_on_clean_match(self, tmp_path):
        parsed = self._parsed(_SIMPLE_DBML, tmp_path)
        df = pd.DataFrame({"id": [1, 2], "label": ["a", "b"], "score": [1.0, 2.0]})
        errors = validate_table(df, "items", parsed)
        assert errors == []

    def test_semantic_alias_is_reported_not_missing_or_extra(self, tmp_path):
        parsed = self._parsed(
            """
Table students {
  id integer [pk]
  id_school integer
}
""",
            tmp_path,
        )
        df = pd.DataFrame({"id": [1, 2], "trường học": [10, 20]})
        errors = validate_table(df, "students", parsed)

        alias = [e for e in errors if e.error_type == "COLUMN_ALIAS_INFERRED"]
        assert len(alias) == 1
        assert alias[0].affected_column == "id_school"
        assert alias[0].missing_field_context is not None
        assert alias[0].missing_field_context.candidate_aliases == ["trường học"]
        assert alias[0].missing_field_context.is_intentional_missing is None
        assert [e for e in errors if e.error_type == "MISSING_COLUMN"] == []
        assert [e for e in errors if e.error_type == "EXTRA_COLUMN"] == []


class TestValidateTableTypeMismatch:
    def _parsed(self, src, tmp_path):
        p = tmp_path / "s.dbml"
        p.write_text(src)
        return parse_schema(str(p))["tables"]

    def test_integer_with_nulls_no_mismatch(self, tmp_path):
        # int column with nulls → pandas reads as float64 → should NOT be TYPE_MISMATCH
        parsed = self._parsed(_CUSTOMERS_DBML, tmp_path)
        df = pd.DataFrame({"id": [1, 2], "email": ["a@b.com", "c@d.com"],
                           "age": [25, None], "phone": ["123", "456"]})
        errors = validate_table(df, "customers", parsed)
        type_errs = [e for e in errors if e.error_type == "TYPE_MISMATCH" and e.affected_column == "age"]
        assert type_errs == []

    def test_integer_col_with_strings_is_mismatch(self, tmp_path):
        # age column contains "thirty" → pandas reads as object (string family) → TYPE_MISMATCH HIGH
        parsed = self._parsed(_CUSTOMERS_DBML, tmp_path)
        df = pd.DataFrame({"id": [1, 2], "email": ["a@b.com", "c@d.com"],
                           "age": ["25", "thirty"], "phone": ["123", "456"]})
        errors = validate_table(df, "customers", parsed)
        type_errs = [e for e in errors if e.error_type == "TYPE_MISMATCH" and e.affected_column == "age"]
        assert len(type_errs) == 1
        assert type_errs[0].severity.value == "HIGH"


class TestValidateTablePkChecks:
    def _parsed(self, src, tmp_path):
        p = tmp_path / "s.dbml"
        p.write_text(src)
        return parse_schema(str(p))["tables"]

    def test_pk_duplicate_is_critical(self, tmp_path):
        parsed = self._parsed(_CUSTOMERS_DBML, tmp_path)
        df = pd.DataFrame({"id": [1, 1, 2], "email": ["a@b.com", "c@d.com", "e@f.com"],
                           "age": [25, 30, 35], "phone": ["1", "2", "3"]})
        errors = validate_table(df, "customers", parsed)
        pk_dup = [e for e in errors if e.error_type == "PK_DUPLICATE"]
        assert len(pk_dup) == 1
        assert pk_dup[0].severity.value == "CRITICAL"
        assert pk_dup[0].affected_count >= 1

    def test_pk_null_is_critical(self, tmp_path):
        parsed = self._parsed(_CUSTOMERS_DBML, tmp_path)
        df = pd.DataFrame({"id": [1, None, 3], "email": ["a@b.com", "c@d.com", "e@f.com"],
                           "age": [25, 30, 35], "phone": ["1", "2", "3"]})
        errors = validate_table(df, "customers", parsed)
        pk_null = [e for e in errors if e.error_type == "PK_NULL"]
        assert len(pk_null) == 1
        assert pk_null[0].severity.value == "CRITICAL"

    def test_clean_pk_no_errors(self, tmp_path):
        parsed = self._parsed(_CUSTOMERS_DBML, tmp_path)
        df = pd.DataFrame({"id": [1, 2, 3], "email": ["a@b.com", "c@d.com", "e@f.com"],
                           "age": [25, 30, 35], "phone": ["1", "2", "3"]})
        errors = validate_table(df, "customers", parsed)
        pk_errs = [e for e in errors if e.error_type in ("PK_DUPLICATE", "PK_NULL")]
        assert pk_errs == []


class TestValidateTableNotNullUnique:
    def _parsed(self, src, tmp_path):
        p = tmp_path / "s.dbml"
        p.write_text(src)
        return parse_schema(str(p))["tables"]

    def test_not_null_violation_is_high(self, tmp_path):
        parsed = self._parsed(_SIMPLE_DBML, tmp_path)
        df = pd.DataFrame({"id": [1, 2, 3], "label": ["a", None, "c"], "score": [1.0, 2.0, 3.0]})
        errors = validate_table(df, "items", parsed)
        nn = [e for e in errors if e.error_type == "NOT_NULL_VIOLATION"]
        assert len(nn) == 1
        assert nn[0].affected_column == "label"
        assert nn[0].severity.value == "HIGH"

    def test_unique_violation_is_high(self, tmp_path):
        parsed = self._parsed(_SIMPLE_DBML, tmp_path)
        df = pd.DataFrame({"id": [1, 2, 3], "label": ["a", "b", "c"], "score": [1.0, 1.0, 3.0]})
        errors = validate_table(df, "items", parsed)
        uv = [e for e in errors if e.error_type == "UNIQUE_VIOLATION"]
        assert len(uv) == 1
        assert uv[0].affected_column == "score"
        assert uv[0].severity.value == "HIGH"


# ──────────────────────────────────────────────
# 1b-1: normalize_refs
# ──────────────────────────────────────────────

def _db(src):
    return PyDBML(src)


_FK_DBML = """
Table users {
  id integer [pk]
  email varchar
}
Table orders {
  id integer [pk]
  user_id integer
  total decimal
}
Ref: orders.user_id > users.id
"""

_FK_REVERSE_DBML = """
Table users {
  id integer [pk]
}
Table orders {
  id integer [pk]
  user_id integer
}
Ref: users.id < orders.user_id
"""

_COMPOSITE_DBML = """
Table a {
  id integer [pk]
  code varchar
}
Table b {
  id integer [pk]
  a_id integer
  a_code varchar
}
Ref: b.(a_id, a_code) > a.(id, code)
"""

_DASH_DBML = """
Table a {
  id integer [pk]
}
Table b {
  id integer [pk]
  a_id integer
}
Ref: a.id - b.a_id
"""


class TestNormalizeRefs:
    def _parse_refs(self, src, tmp_path):
        p = tmp_path / "schema.dbml"
        p.write_text(src)
        return parse_schema(str(p))["refs"]

    def test_forward_ref_parsed_correctly(self, tmp_path):
        refs = self._parse_refs(_FK_DBML, tmp_path)
        assert len(refs) == 1
        r = refs[0]
        assert r["child_table"] == "orders"
        assert r["fk_col"] == "user_id"
        assert r["parent_table"] == "users"
        assert r["pk_col"] == "id"

    def test_reverse_ref_direction_flipped(self, tmp_path):
        refs = self._parse_refs(_FK_REVERSE_DBML, tmp_path)
        assert len(refs) == 1
        r = refs[0]
        assert r["child_table"] == "orders"
        assert r["fk_col"] == "user_id"
        assert r["parent_table"] == "users"
        assert r["pk_col"] == "id"

    def test_composite_ref_skipped(self, tmp_path):
        refs = self._parse_refs(_COMPOSITE_DBML, tmp_path)
        assert refs == []

    def test_dash_ref_skipped(self, tmp_path):
        refs = self._parse_refs(_DASH_DBML, tmp_path)
        assert refs == []


# ──────────────────────────────────────────────
# 1b-2: check_foreign_keys
# ──────────────────────────────────────────────

class TestCheckForeignKeys:
    def _refs_for_shop(self, tmp_path=None):
        import tempfile
        src = """
Table users {
  id integer [pk]
  email varchar
}
Table orders {
  id integer [pk]
  user_id integer
  total decimal
}
Ref: orders.user_id > users.id
"""
        if tmp_path is None:
            tmp_path = Path(tempfile.mkdtemp())
        p = tmp_path / "shop.dbml"
        p.write_text(src)
        return parse_schema(str(p))["refs"]

    def test_orphan_detected(self):
        refs = self._refs_for_shop()
        users = pd.DataFrame({"id": [1, 2, 3], "email": ["a@b.com", "b@b.com", "c@b.com"]})
        orders = pd.DataFrame({"id": [101, 102, 103], "user_id": [1, 2, 9999], "total": [10.0, 20.0, 30.0]})
        errors = check_foreign_keys({"users": users, "orders": orders}, refs)
        orphans = [e for e in errors if e.error_type == "ORPHAN_FOREIGN_KEY"]
        assert len(orphans) == 1
        assert orphans[0].affected_count == 1
        assert orphans[0].affected_column == "user_id"
        assert orphans[0].severity.value == "CRITICAL"
        assert any(s.get("user_id") == 9999 for s in orphans[0].top_10_samples)

    def test_fk_null_not_counted_as_orphan(self):
        refs = self._refs_for_shop()
        users = pd.DataFrame({"id": [1, 2, 3], "email": ["a@b.com", "b@b.com", "c@b.com"]})
        orders = pd.DataFrame({"id": [101, 102, 103, 104],
                               "user_id": [1, 2, None, 9999],
                               "total": [10.0, 20.0, 30.0, 40.0]})
        errors = check_foreign_keys({"users": users, "orders": orders}, refs)
        orphans = [e for e in errors if e.error_type == "ORPHAN_FOREIGN_KEY"]
        assert len(orphans) == 1
        assert orphans[0].affected_count == 1  # only 9999, not the null row

    def test_all_valid_fk_no_errors(self):
        refs = self._refs_for_shop()
        users = pd.DataFrame({"id": [1, 2, 3], "email": ["a@b.com", "b@b.com", "c@b.com"]})
        orders = pd.DataFrame({"id": [101, 102], "user_id": [1, 2], "total": [10.0, 20.0]})
        errors = check_foreign_keys({"users": users, "orders": orders}, refs)
        assert errors == []

    def test_parent_table_missing_emits_unchecked(self):
        refs = self._refs_for_shop()
        orders = pd.DataFrame({"id": [101], "user_id": [1], "total": [10.0]})
        # users not loaded
        errors = check_foreign_keys({"orders": orders}, refs)
        unchecked = [e for e in errors if e.error_type == "FK_UNCHECKED"]
        assert len(unchecked) == 1
        assert unchecked[0].severity.value == "WARN"

    def test_dtype_family_mismatch_emits_unchecked(self):
        refs = self._refs_for_shop()
        # parent id is int, child user_id is string → family mismatch
        users = pd.DataFrame({"id": [1, 2, 3], "email": ["a@b.com", "b@b.com", "c@b.com"]})
        orders = pd.DataFrame({"id": [101, 102], "user_id": ["1", "2"], "total": [10.0, 20.0]})
        errors = check_foreign_keys({"users": users, "orders": orders}, refs)
        unchecked = [e for e in errors if e.error_type == "FK_UNCHECKED"]
        assert len(unchecked) == 1
        assert "family" in unchecked[0].description.lower() or "type" in unchecked[0].description.lower()

    def test_fk_alias_column_is_checked_for_orphans(self):
        refs = [{
            "child_table": "students",
            "fk_col": "school_id",
            "parent_table": "schools",
            "pk_col": "id_school",
        }]
        schools = pd.DataFrame({"id_school": ["S01", "S02"], "school_name": ["A", "B"]})
        students = pd.DataFrame({"student_id": [1, 2], "truong_hoc": ["S01", "S99"]})

        errors = check_foreign_keys({"schools": schools, "students": students}, refs)

        orphans = [e for e in errors if e.error_type == "ORPHAN_FOREIGN_KEY"]
        assert len(orphans) == 1
        assert orphans[0].affected_column == "school_id"
        assert orphans[0].affected_count == 1
        assert any(sample.get("truong_hoc") == "S99" for sample in orphans[0].top_10_samples)


class TestRelationshipInference:
    def test_missing_fk_metadata_is_inferred_from_values_and_names(self, tmp_path):
        schema_path = tmp_path / "school.dbml"
        schema_path.write_text(
            """
Table schools {
  id integer [pk]
  name varchar
}
Table students {
  id integer [pk]
  id_school integer
}
""",
            encoding="utf-8",
        )
        schools_path = tmp_path / "schools.csv"
        students_path = tmp_path / "students.csv"
        pd.DataFrame({"id": [10, 20], "name": ["A", "B"]}).to_csv(schools_path, index=False)
        pd.DataFrame({"id": [1, 2, 3], "id_school": [10, 20, 10]}).to_csv(students_path, index=False)

        findings = validate_schema_multi([str(schools_path), str(students_path)], str(schema_path))
        inferred = [r for r in findings.relationships if r.relationship_type == "inferred_fk"]
        assert len(inferred) == 1
        assert inferred[0].child_table == "students"
        assert inferred[0].child_column == "id_school"
        assert inferred[0].parent_table == "schools"
        assert inferred[0].parent_column == "id"
        assert inferred[0].status == "missing_from_schema"
        assert inferred[0].decision == "accepted_for_safe_join"
        assert inferred[0].confidence_bucket == "HIGH_CONFIDENCE"
        assert inferred[0].blocked_reasons == []
        assert inferred[0].evidence_metrics["value_coverage"] == 1.0
        assert "value_coverage_passed" in inferred[0].decision_reasons

        missing_ref = [e for e in findings.integrity_errors if e.error_type == "MISSING_RELATIONSHIP_METADATA"]
        assert len(missing_ref) == 1
        assert missing_ref[0].relationship is not None
        assert missing_ref[0].relationship.child_column == "id_school"

    def test_schema_and_relationships_are_inferred_without_schema_file(self, tmp_path):
        schools_path = tmp_path / "schools.csv"
        classes_path = tmp_path / "classes.csv"
        students_path = tmp_path / "students.csv"
        pd.DataFrame({
            "id_school": ["S01", "S02"],
            "school_name": ["Alpha", "Beta"],
        }).to_csv(schools_path, index=False)
        pd.DataFrame({
            "class_id": ["C01", "C02"],
            "school_id": ["S01", "S02"],
        }).to_csv(classes_path, index=False)
        pd.DataFrame({
            "student_id": [1, 2, 3],
            "student_name": ["An", "Binh", "Chi"],
            "truong_hoc": ["S01", "S02", "S99"],
            "class_id": ["C01", "C99", "C02"],
        }).to_csv(students_path, index=False)

        findings = validate_schema_multi([str(schools_path), str(classes_path), str(students_path)], schema_path=None)

        assert findings.schema_meta.schema_file == "inferred_from_data"
        assert findings.schema_meta.total_tables == 3
        relationships = [r for r in findings.relationships if r.relationship_type == "inferred_fk"]
        relationship_keys = {
            (r.child_table, r.child_column, r.parent_table, r.parent_column, r.status)
            for r in relationships
        }
        assert ("students", "truong_hoc", "schools", "id_school", "inferred_from_data") in relationship_keys
        assert ("students", "class_id", "classes", "class_id", "inferred_from_data") in relationship_keys
        assert all(r.decision == "accepted_for_safe_join" for r in relationships)
        assert all(r.confidence_bucket == "HIGH_CONFIDENCE" for r in relationships)

        orphans = [e for e in findings.integrity_errors if e.error_type == "ORPHAN_FOREIGN_KEY"]
        orphan_keys = {(e.affected_table, e.affected_column) for e in orphans}
        assert ("students", "truong_hoc") in orphan_keys
        assert ("students", "class_id") in orphan_keys
        assert any(sample.get("truong_hoc") == "S99" for e in orphans for sample in e.top_10_samples)
        assert any(sample.get("class_id") == "C99" for e in orphans for sample in e.top_10_samples)

    def test_surrogate_key_overlap_does_not_infer_wrong_relationship(self, tmp_path):
        users_path = tmp_path / "users.csv"
        products_path = tmp_path / "products.csv"
        orders_path = tmp_path / "orders.csv"
        pd.DataFrame({"id": [1, 2, 3], "name": ["A", "B", "C"]}).to_csv(users_path, index=False)
        pd.DataFrame({"id": [1, 2, 3], "sku": ["P1", "P2", "P3"]}).to_csv(products_path, index=False)
        pd.DataFrame({"order_id": [10, 11, 12], "user_id": [1, 2, 3]}).to_csv(orders_path, index=False)

        findings = validate_schema_multi([str(users_path), str(products_path), str(orders_path)], schema_path=None)
        keys = {
            (r.child_table, r.child_column, r.parent_table, r.parent_column)
            for r in findings.relationships
        }

        assert ("orders", "user_id", "users", "id") in keys
        assert ("orders", "user_id", "products", "id") not in keys
        assert ("users", "id", "products", "id") not in keys

    def test_value_overlap_without_domain_name_does_not_infer_relationship(self, tmp_path):
        products_path = tmp_path / "products.csv"
        details_path = tmp_path / "order_details.csv"
        pd.DataFrame({
            "product_id": [1, 2, 3],
            "name": ["A", "B", "C"],
        }).to_csv(products_path, index=False)
        pd.DataFrame({
            "order_id": [100, 101, 102],
            "product_id": [1, 2, 3],
            "quantity": [1, 2, 3],
        }).to_csv(details_path, index=False)

        findings = validate_schema_multi([str(products_path), str(details_path)], schema_path=None)
        keys = {
            (r.child_table, r.child_column, r.parent_table, r.parent_column)
            for r in findings.relationships
        }

        assert ("order_details", "product_id", "products", "product_id") in keys
        assert ("order_details", "quantity", "products", "product_id") not in keys

    def test_inferred_primary_key_still_reports_duplicate_and_null(self, tmp_path):
        schools_path = tmp_path / "schools.csv"
        classes_path = tmp_path / "classes.csv"
        pd.DataFrame({
            "id_school": ["S01", "S01", None],
            "school_name": ["Alpha", "Duplicate", "Missing"],
        }).to_csv(schools_path, index=False)
        pd.DataFrame({
            "class_id": ["C01", "C02"],
            "school_id": ["S01", "S02"],
        }).to_csv(classes_path, index=False)

        findings = validate_schema_multi([str(schools_path), str(classes_path)], schema_path=None)

        pk_null = [e for e in findings.integrity_errors if e.error_type == "PK_NULL"]
        pk_dup = [e for e in findings.integrity_errors if e.error_type == "PK_DUPLICATE"]
        assert any(e.affected_table == "schools" and e.affected_column == "id_school" for e in pk_null)
        assert any(e.affected_table == "schools" and e.affected_column == "id_school" for e in pk_dup)
