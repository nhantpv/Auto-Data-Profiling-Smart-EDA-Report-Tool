"""Tests for ingestion.schema_reader — Adapter Pattern for .dbml / .sql parsing."""
import pytest
from ingestion.schema_reader import parse_schema


# ── Shared DDL / DBML sources ─────────────────────────────────────────────────

_SHOP_DBML = """\
Table users {
  id integer [pk]
  email varchar [unique]
}
Table orders {
  id integer [pk]
  user_id integer
  total decimal
}
Ref: orders.user_id > users.id
"""

_SHOP_SQL = """\
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    email VARCHAR(255) UNIQUE
);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    total DECIMAL,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
"""

_INLINE_REF_SQL = """\
CREATE TABLE users (id INTEGER PRIMARY KEY);
CREATE TABLE orders (
    id INTEGER PRIMARY KEY,
    user_id INTEGER REFERENCES users(id)
);
"""

_ALTER_FK_SQL = """\
CREATE TABLE users (id INTEGER PRIMARY KEY);
CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER);
ALTER TABLE orders ADD FOREIGN KEY (user_id) REFERENCES users(id);
"""

_SINGLE_TABLE_SQL = """\
CREATE TABLE items (
    id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    price DECIMAL
);
"""


# ── TestParseSchemaAutoDetect ─────────────────────────────────────────────────


class TestParseSchemaAutoDetect:
    def test_dbml_file_detected(self, tmp_path):
        p = tmp_path / "schema.dbml"
        p.write_text(_SHOP_DBML)
        result = parse_schema(str(p))
        assert "tables" in result
        assert "refs" in result
        assert "meta" in result

    def test_sql_file_detected(self, tmp_path):
        p = tmp_path / "schema.sql"
        p.write_text(_SHOP_SQL)
        result = parse_schema(str(p))
        assert "tables" in result
        assert "refs" in result
        assert "meta" in result

    def test_unsupported_ext_raises(self, tmp_path):
        p = tmp_path / "schema.yaml"
        p.write_text("tables: []")
        with pytest.raises(ValueError, match="Unsupported schema format"):
            parse_schema(str(p))


# ── TestDbmlAdapter ───────────────────────────────────────────────────────────


class TestDbmlAdapter:
    def _parse(self, src, tmp_path):
        p = tmp_path / "s.dbml"
        p.write_text(src)
        return parse_schema(str(p))

    def test_tables_parsed(self, tmp_path):
        result = self._parse(_SHOP_DBML, tmp_path)
        assert "users" in result["tables"]
        assert "orders" in result["tables"]

    def test_columns_extracted(self, tmp_path):
        result = self._parse(_SHOP_DBML, tmp_path)
        cols = result["tables"]["users"]["columns"]
        assert "id" in cols
        assert cols["id"]["pk"] is True

    def test_refs_extracted(self, tmp_path):
        result = self._parse(_SHOP_DBML, tmp_path)
        assert len(result["refs"]) == 1
        r = result["refs"][0]
        assert r["child_table"] == "orders"
        assert r["fk_col"] == "user_id"
        assert r["parent_table"] == "users"
        assert r["pk_col"] == "id"

    def test_meta_correct(self, tmp_path):
        result = self._parse(_SHOP_DBML, tmp_path)
        assert result["meta"]["total_tables"] == 2
        assert result["meta"]["total_relationships"] == 1
        assert result["meta"]["file_name"] == "s.dbml"


# ── TestSqlDdlAdapter ────────────────────────────────────────────────────────


class TestSqlDdlAdapter:
    def _parse(self, src, tmp_path):
        p = tmp_path / "s.sql"
        p.write_text(src)
        return parse_schema(str(p))

    def test_basic_create_table(self, tmp_path):
        result = self._parse(_SINGLE_TABLE_SQL, tmp_path)
        assert "items" in result["tables"]
        cols = result["tables"]["items"]["columns"]
        assert "id" in cols
        assert "name" in cols
        assert "price" in cols

    def test_pk_flag_set_correctly(self, tmp_path):
        result = self._parse(_SINGLE_TABLE_SQL, tmp_path)
        cols = result["tables"]["items"]["columns"]
        assert cols["id"]["pk"] is True
        assert cols["name"]["pk"] is False

    def test_not_null_flag(self, tmp_path):
        result = self._parse(_SINGLE_TABLE_SQL, tmp_path)
        cols = result["tables"]["items"]["columns"]
        # PK is implicitly not_null
        assert cols["id"]["not_null"] is True
        # Explicit NOT NULL
        assert cols["name"]["not_null"] is True
        # No NOT NULL → nullable
        assert cols["price"]["not_null"] is False

    def test_table_level_fk(self, tmp_path):
        result = self._parse(_SHOP_SQL, tmp_path)
        assert len(result["refs"]) == 1
        r = result["refs"][0]
        assert r["child_table"] == "orders"
        assert r["fk_col"] == "user_id"
        assert r["parent_table"] == "users"
        assert r["pk_col"] == "id"

    def test_inline_references_fk(self, tmp_path):
        result = self._parse(_INLINE_REF_SQL, tmp_path)
        assert len(result["refs"]) == 1
        r = result["refs"][0]
        assert r["child_table"] == "orders"
        assert r["fk_col"] == "user_id"

    def test_alter_table_fk(self, tmp_path):
        result = self._parse(_ALTER_FK_SQL, tmp_path)
        assert len(result["refs"]) == 1
        r = result["refs"][0]
        assert r["child_table"] == "orders"
        assert r["fk_col"] == "user_id"
        assert r["parent_table"] == "users"

    def test_meta_correct(self, tmp_path):
        result = self._parse(_SHOP_SQL, tmp_path)
        assert result["meta"]["total_tables"] == 2
        assert result["meta"]["total_relationships"] == 1


# ── TestUnifiedOutputFormat ───────────────────────────────────────────────────


class TestUnifiedOutputFormat:
    """Both adapters MUST produce the same structure for equivalent schemas."""

    def test_dbml_and_sql_produce_same_tables(self, tmp_path):
        dbml_p = tmp_path / "a.dbml"
        dbml_p.write_text(_SHOP_DBML)
        sql_p = tmp_path / "b.sql"
        sql_p.write_text(_SHOP_SQL)

        dbml_result = parse_schema(str(dbml_p))
        sql_result = parse_schema(str(sql_p))

        assert set(dbml_result["tables"].keys()) == set(sql_result["tables"].keys())
        for tname in dbml_result["tables"]:
            dbml_cols = set(dbml_result["tables"][tname]["columns"].keys())
            sql_cols = set(sql_result["tables"][tname]["columns"].keys())
            assert dbml_cols == sql_cols, f"Column mismatch for table '{tname}'"

    def test_dbml_and_sql_produce_same_refs(self, tmp_path):
        dbml_p = tmp_path / "a.dbml"
        dbml_p.write_text(_SHOP_DBML)
        sql_p = tmp_path / "b.sql"
        sql_p.write_text(_SHOP_SQL)

        dbml_refs = parse_schema(str(dbml_p))["refs"]
        sql_refs = parse_schema(str(sql_p))["refs"]

        assert len(dbml_refs) == len(sql_refs)
        for dr, sr in zip(dbml_refs, sql_refs):
            assert dr["child_table"] == sr["child_table"]
            assert dr["fk_col"] == sr["fk_col"]
            assert dr["parent_table"] == sr["parent_table"]
            assert dr["pk_col"] == sr["pk_col"]
