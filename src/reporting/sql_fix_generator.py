"""SQL Fix Snippet Generator — LLM-assisted diagnostic SQL for issue cards.

Generates SQL SELECT/diagnostic queries for each detected issue type so the
user can immediately verify findings against their database.  Falls back to
a deterministic template if the LLM call fails or is not configured.

Usage:
    from reporting.sql_fix_generator import generate_sql_for_issue

    snippet = generate_sql_for_issue(
        issue_type="PK_DUPLICATE",
        table_name="PlaylistTrack",
        column_name="TrackId",
        database_type="sqlite",   # or "postgres", "mysql", "mssql"
        extra_context={"composite_pk": ["PlaylistId", "TrackId"]},
    )
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)


# ── Template-based fallback SQL (deterministic, zero latency) ────────────────

_TEMPLATES: dict[str, str] = {
    "PK_DUPLICATE": """\
-- Tìm duplicate trong cột PK '{col}'
SELECT {col}, COUNT(*) AS cnt
FROM {table}
GROUP BY {col}
HAVING COUNT(*) > 1
ORDER BY cnt DESC
LIMIT 20;""",

    "COMPOSITE_PK_DUPLICATE": """\
-- Tìm duplicate tuple composite PK ({cols})
SELECT {cols}, COUNT(*) AS cnt
FROM {table}
GROUP BY {cols}
HAVING COUNT(*) > 1
ORDER BY cnt DESC
LIMIT 20;""",

    "PK_NULL": """\
-- Tìm NULL trong cột PK '{col}'
SELECT *
FROM {table}
WHERE {col} IS NULL
LIMIT 20;""",

    "ORPHAN_FOREIGN_KEY": """\
-- Tìm FK orphan: {child_table}.{col} không match {parent_table}
SELECT c.*
FROM {table} c
LEFT JOIN {parent_table} p ON c.{col} = p.{parent_col}
WHERE p.{parent_col} IS NULL
  AND c.{col} IS NOT NULL
LIMIT 20;""",

    "NON_UNIQUE_PARENT_PK": """\
-- Kiểm tra tính duy nhất của PK trong bảng parent '{table}'
SELECT {col}, COUNT(*) AS cnt
FROM {table}
GROUP BY {col}
HAVING COUNT(*) > 1
ORDER BY cnt DESC
LIMIT 20;""",

    "MISSINGNESS": """\
-- Thống kê missing trong cột '{col}'
SELECT
    COUNT(*) AS total_rows,
    SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) AS null_count,
    ROUND(100.0 * SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) / COUNT(*), 2) AS null_pct
FROM {table};""",

    "NOT_NULL_VIOLATION": """\
-- Tìm NULL vi phạm ràng buộc NOT NULL của '{col}'
SELECT *
FROM {table}
WHERE {col} IS NULL
LIMIT 20;""",

    "UNIQUE_VIOLATION": """\
-- Tìm duplicate vi phạm ràng buộc UNIQUE của '{col}'
SELECT {col}, COUNT(*) AS cnt
FROM {table}
WHERE {col} IS NOT NULL
GROUP BY {col}
HAVING COUNT(*) > 1
ORDER BY cnt DESC
LIMIT 20;""",

    "TYPE_MISMATCH": """\
-- Kiểm tra kiểu dữ liệu của cột '{col}'
SELECT
    {col},
    TYPEOF({col}) AS detected_type
FROM {table}
WHERE {col} IS NOT NULL
LIMIT 20;""",

    "DUPLICATE": """\
-- Tìm duplicate rows trong bảng '{table}'
SELECT *, COUNT(*) AS row_count
FROM {table}
GROUP BY {all_cols}
HAVING COUNT(*) > 1
ORDER BY row_count DESC
LIMIT 20;""",

    "HIGH_CARDINALITY": """\
-- Thống kê cardinality của cột '{col}'
SELECT
    COUNT(DISTINCT {col}) AS distinct_count,
    COUNT(*) AS total_rows,
    ROUND(100.0 * COUNT(DISTINCT {col}) / COUNT(*), 2) AS cardinality_pct
FROM {table};""",

    "CONSTANT_COLUMN": """\
-- Kiểm tra tính hằng số của cột '{col}'
SELECT DISTINCT {col}, COUNT(*) AS cnt
FROM {table}
GROUP BY {col};""",
}


def _template_sql(
    issue_type: str,
    table_name: str,
    column_name: str,
    extra_context: dict[str, Any] | None = None,
) -> str:
    """Return a template-based SQL snippet for the given issue type."""
    ctx = extra_context or {}
    tmpl = _TEMPLATES.get(issue_type)
    if tmpl is None:
        return f"-- No diagnostic SQL template available for {issue_type}"

    # Build format kwargs with safe defaults
    fmt: dict[str, str] = {
        "table": table_name,
        "col": column_name,
        "cols": ", ".join(ctx.get("composite_pk", [column_name])),
        "parent_table": ctx.get("parent_table", "parent_table"),
        "parent_col": ctx.get("parent_col", "id"),
        "all_cols": ", ".join(ctx.get("all_cols", [column_name])),
        "child_table": table_name,
    }
    try:
        return tmpl.format(**fmt)
    except KeyError:
        return tmpl  # return raw template if formatting fails


# ── LLM-assisted SQL generation ───────────────────────────────────────────────

_LLM_PROMPT_TEMPLATE = """\
You are a data quality SQL expert. Generate a concise diagnostic SQL query for the following data issue.

**Issue type**: {issue_type}
**Table**: {table_name}
**Column**: {column_name}
**Database**: {database_type}
**Context**: {context_desc}

Requirements:
- Return ONLY the SQL query (no markdown fences, no explanation)
- Query must be runnable on {database_type}
- Include a comment line at top explaining what it checks
- Use LIMIT 20 to prevent large result sets
- Be concise (max 15 lines)

SQL:"""


def _llm_sql(
    issue_type: str,
    table_name: str,
    column_name: str,
    database_type: str = "sqlite",
    extra_context: dict[str, Any] | None = None,
) -> str | None:
    """Call LLM to generate a contextual SQL snippet. Returns None on failure."""
    try:
        import google.generativeai as genai  # type: ignore
    except ImportError:
        logger.debug("google-generativeai not installed; skipping LLM SQL generation")
        return None

    api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.debug("No GOOGLE_API_KEY/GEMINI_API_KEY; skipping LLM SQL generation")
        return None

    ctx = extra_context or {}
    context_desc = "; ".join(f"{k}={v}" for k, v in ctx.items()) or "none"

    prompt = _LLM_PROMPT_TEMPLATE.format(
        issue_type=issue_type,
        table_name=table_name,
        column_name=column_name,
        database_type=database_type,
        context_desc=context_desc,
    )

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(
            model_name=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
        )
        response = model.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.0,
                max_output_tokens=512,
            ),
        )
        sql_text = response.text.strip()
        # Strip any accidental markdown fences
        if sql_text.startswith("```"):
            lines = sql_text.splitlines()
            sql_text = "\n".join(
                l for l in lines if not l.startswith("```")
            ).strip()
        return sql_text if sql_text else None
    except Exception as exc:
        logger.warning("LLM SQL generation failed for %s.%s: %s", table_name, column_name, exc)
        return None


# ── Public API ────────────────────────────────────────────────────────────────

def generate_sql_for_issue(
    issue_type: str,
    table_name: str,
    column_name: str,
    database_type: str = "sqlite",
    extra_context: dict[str, Any] | None = None,
    prefer_llm: bool = True,
) -> str:
    """Generate a diagnostic SQL snippet for a detected data quality issue.

    Tries LLM first (contextual, database-aware) and falls back to a
    deterministic template if the LLM call fails or is unconfigured.

    Args:
        issue_type: e.g. "PK_DUPLICATE", "ORPHAN_FOREIGN_KEY"
        table_name: The affected table name
        column_name: The affected column name (or composite col string)
        database_type: "sqlite" | "postgres" | "mysql" | "mssql"
        extra_context: Additional info (e.g. composite_pk list, parent_table)
        prefer_llm: If True, attempt LLM generation first

    Returns:
        SQL string ready to embed in the HTML report.
    """
    if prefer_llm:
        llm_result = _llm_sql(
            issue_type=issue_type,
            table_name=table_name,
            column_name=column_name,
            database_type=database_type,
            extra_context=extra_context,
        )
        if llm_result:
            return llm_result

    # Fallback to template
    return _template_sql(issue_type, table_name, column_name, extra_context)


def generate_sql_batch(
    issues: list[dict[str, Any]],
    database_type: str = "sqlite",
    prefer_llm: bool = True,
) -> dict[str, str]:
    """Generate SQL snippets for a batch of issues.

    Args:
        issues: List of dicts with keys: issue_type, table_name, column_name,
                and optionally extra_context.
        database_type: Target database dialect.
        prefer_llm: Whether to try LLM generation.

    Returns:
        Dict mapping "{table_name}.{column_name}.{issue_type}" → SQL string.
    """
    results: dict[str, str] = {}
    for issue in issues:
        key = "{}.{}.{}".format(
            issue.get("table_name", ""),
            issue.get("column_name", ""),
            issue.get("issue_type", ""),
        )
        results[key] = generate_sql_for_issue(
            issue_type=issue.get("issue_type", "UNKNOWN"),
            table_name=issue.get("table_name", "unknown_table"),
            column_name=issue.get("column_name", "unknown_col"),
            database_type=database_type,
            extra_context=issue.get("extra_context"),
            prefer_llm=prefer_llm,
        )
    return results
