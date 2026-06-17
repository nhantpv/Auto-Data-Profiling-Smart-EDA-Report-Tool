"""Unified Schema Reader — auto-detect .dbml/.sql, return standardised dict.

This module implements the Adapter Pattern to decouple schema_engine.py
from any specific parser library.  All adapters MUST return the same
``UnifiedSchemaResult`` dict structure so that downstream validators
(validate_table, check_foreign_keys) work identically regardless of
input format.

Unified output contract
-----------------------
{
    "tables": {
        "<table_name>": {
            "columns": {
                "<col_name>": {
                    "type": str,       # raw SQL / DBML type, e.g. "integer", "varchar(255)"
                    "pk": bool,
                    "unique": bool,
                    "not_null": bool,
                }
            }
        }
    },
    "refs": [
        {
            "child_table": str,
            "fk_col": str,
            "parent_table": str,
            "pk_col": str,
        }
    ],
    "meta": {
        "file_name": str,
        "total_tables": int,
        "total_relationships": int,
    }
}
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Public entry point ────────────────────────────────────────────────────────


def parse_schema(schema_path: str) -> dict:
    """Auto-detect format by file extension and delegate to the right adapter."""
    ext = Path(schema_path).suffix.lower()
    if ext == ".dbml":
        return _parse_dbml(schema_path)
    if ext == ".sql":
        return _parse_sql_ddl(schema_path)
    raise ValueError(
        f"Unsupported schema format: '{ext}'. Supported: .dbml, .sql"
    )


# ── Adapter 1: DBML (pydbml) ─────────────────────────────────────────────────


def _normalise_dbml_types(text: str) -> str:
    """Normalise non-standard DBML type aliases that pydbml rejects.

    WikiDB and other generators use ``string``, ``bool``, ``float``, etc.
    pydbml only accepts standard SQL / DBML types.  We replace these
    before handing the text to the parser so that no ParseSyntaxException
    is raised.

    Uses ``\\b`` word-boundary anchors so that only standalone type tokens
    are replaced — column names containing the same letters are untouched.
    Longer aliases are processed first to prevent partial matches.
    """
    import re as _re

    # (non-standard alias, standard replacement)
    # Longer/more-specific aliases MUST come before shorter ones.
    _aliases: list[tuple[str, str]] = [
        ("datetime",        "timestamp"),   # before "date"
        ("double",          "float8"),      # before "float"
        ("bytes",           "blob"),        # before "byte"
        ("number",          "decimal"),     # before "num"
        ("string",          "varchar"),
        ("boolean",         "boolean"),     # already valid, no-op — prevents bool→booleanean
        ("bool",            "boolean"),
        ("float",           "float8"),
        ("int",             "integer"),
        ("long",            "bigint"),
        ("short",           "smallint"),
        ("byte",            "smallint"),
        ("char",            "varchar"),
        ("num",             "decimal"),
        ("text",            "text"),        # already valid, no-op
        ("date",            "date"),        # already valid, no-op
        ("timestamp",       "timestamp"),   # already valid, no-op
        ("decimal",         "decimal"),     # already valid, no-op
    ]
    for alias, replacement in _aliases:
        if alias == replacement:
            continue  # skip no-op entries
        # \b matches at a word boundary (transition between \w and \W).
        # This ensures we only replace standalone type tokens, not substrings
        # inside column names (e.g. "int" won't match inside "integer" or
        # "int_value" since _ is a \w char).
        pattern = r'\b' + _re.escape(alias) + r'\b'
        text = _re.sub(pattern, replacement, text)
    return text



def _parse_dbml(path: str) -> dict:
    """Parse a ``.dbml`` file via *pydbml* and return the unified dict."""
    from pydbml import PyDBML  # pyrefly: ignore [missing-import]

    raw_text = Path(path).read_text(encoding="utf-8")
    text = _normalise_dbml_types(raw_text)
    try:
        db = PyDBML(text)
    except Exception as exc:
        # Re-raise with a human-readable message pointing to the file
        raise ValueError(
            f"Could not parse DBML file '{Path(path).name}': {exc}\n\n"
            "Common causes:\n"
            "  • Non-standard column type (e.g. 'string' → use 'varchar')\n"
            "  • Column name with spaces — wrap in double-quotes: \"column name\"\n"
            "  • Missing closing brace '}' for a Table block\n"
            f"Original error: {exc}"
        ) from exc

    # --- tables ---
    tables: dict = {}
    for t in db.tables:
        cols: dict = {}
        for c in t.columns:
            cols[c.name] = {
                "type": str(c.type),
                "pk": bool(c.pk),
                "unique": bool(c.unique),
                "not_null": bool(c.not_null),
            }
        tables[t.name] = {"columns": cols}

    # --- refs (cut-paste of old normalize_refs logic) ---
    refs: list[dict] = []
    for r in db.refs:
        if r.type == "-":
            logger.info("Skipping one-to-one ref '%s' (not supported)", r)
            continue
        if len(r.col1) > 1 or len(r.col2) > 1:
            logger.info("Skipping composite FK ref '%s' (not supported)", r)
            continue
        if r.type == ">":
            child_table = r.col1[0].table.name
            fk_col = r.col1[0].name
            parent_table = r.col2[0].table.name
            pk_col = r.col2[0].name
        else:  # '<'
            child_table = r.col2[0].table.name
            fk_col = r.col2[0].name
            parent_table = r.col1[0].table.name
            pk_col = r.col1[0].name
        refs.append(
            {
                "child_table": child_table,
                "fk_col": fk_col,
                "parent_table": parent_table,
                "pk_col": pk_col,
            }
        )

    return {
        "tables": tables,
        "refs": refs,
        "meta": {
            "file_name": Path(path).name,
            "total_tables": len(tables),
            "total_relationships": len(refs),
        },
    }


# ── Adapter 2: SQL DDL (simple-ddl-parser) ────────────────────────────────────


def _parse_sql_ddl(path: str) -> dict:
    """Parse a ``.sql`` DDL file via *simple-ddl-parser* and return the unified dict.

    Handles three FK declaration styles:
    1. Inline column-level ``REFERENCES`` (stored in ``col["references"]``).
    2. Table-level ``FOREIGN KEY`` constraint (merged into column references by the parser).
    3. ``ALTER TABLE … ADD FOREIGN KEY`` (stored in ``tbl["alter"]["columns"]``).
    """
    from simple_ddl_parser import DDLParser  # pyrefly: ignore [missing-import]

    ddl_text = Path(path).read_text(encoding="utf-8")
    raw = DDLParser(ddl_text, normalize_names=True).run(group_by_type=True)

    tables: dict = {}
    refs: list[dict] = []

    for tbl in raw.get("tables", []):
        table_name = tbl["table_name"]
        pk_cols = set(tbl.get("primary_key", []))

        columns: dict = {}
        for col in tbl.get("columns", []):
            col_name = col["name"]
            is_pk = col_name in pk_cols
            columns[col_name] = {
                "type": _strip_size(col.get("type", "unknown")),
                "pk": is_pk,
                "unique": col.get("unique", False) or is_pk,
                "not_null": not col.get("nullable", True) or is_pk,
            }

            # Inline REFERENCES or table-level FOREIGN KEY
            # (simple-ddl-parser merges both into col["references"])
            ref_info = col.get("references")
            if ref_info and ref_info.get("table"):
                ref_col = ref_info.get("column")
                if ref_col:  # skip if reference column is missing
                    refs.append(
                        {
                            "child_table": table_name,
                            "fk_col": col_name,
                            "parent_table": ref_info["table"],
                            "pk_col": ref_col,
                        }
                    )

        # ALTER TABLE … ADD FOREIGN KEY
        alter = tbl.get("alter", {})
        alter_cols = alter.get("columns", []) if isinstance(alter, dict) else []
        for acol in alter_cols:
            ref_info = acol.get("references")
            if ref_info and ref_info.get("table"):
                ref_col = ref_info.get("column")
                fk_col_name = acol.get("name")
                if ref_col and fk_col_name:
                    refs.append(
                        {
                            "child_table": table_name,
                            "fk_col": fk_col_name,
                            "parent_table": ref_info["table"],
                            "pk_col": ref_col,
                        }
                    )

        tables[table_name] = {"columns": columns}

    return {
        "tables": tables,
        "refs": refs,
        "meta": {
            "file_name": Path(path).name,
            "total_tables": len(tables),
            "total_relationships": len(refs),
        },
    }


def _strip_size(sql_type: str) -> str:
    """Strip size/precision from SQL type: ``VARCHAR(255)`` → ``varchar``."""
    return re.sub(r"\(.*?\)", "", sql_type).strip().lower()
