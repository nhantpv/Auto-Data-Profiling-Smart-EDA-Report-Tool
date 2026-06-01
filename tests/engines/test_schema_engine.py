import pytest
import pandas as pd
from pathlib import Path
from engines.schema_engine import parse_dbml, match_table, validate_table

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

class TestParseDbml:
    def _parse_inline(self, src, tmp_path):
        p = tmp_path / "schema.dbml"
        p.write_text(src)
        return parse_dbml(str(p))

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


class TestMatchTable:
    def _parse_inline(self, src, tmp_path):
        p = tmp_path / "schema.dbml"
        p.write_text(src)
        return parse_dbml(str(p))

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
        return parse_dbml(str(p))

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


class TestValidateTableTypeMismatch:
    def _parsed(self, src, tmp_path):
        p = tmp_path / "s.dbml"
        p.write_text(src)
        return parse_dbml(str(p))

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
        return parse_dbml(str(p))

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
        return parse_dbml(str(p))

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
