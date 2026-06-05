import logging
import re
from pathlib import Path
import pandas as pd
import pandas.api.types as pt
from ingestion.schema_reader import parse_schema
from ontology.models import IntegrityError, Severity, SchemaEvaluationFindings, SchemaMeta, TableInfo

logger = logging.getLogger(__name__)

# ── Type family mapping ───────────────────────────────────────────────────────

DBML_FAMILY = {
    "integer": "numeric", "int": "numeric", "bigint": "numeric",
    "smallint": "numeric", "tinyint": "numeric",
    "decimal": "numeric", "numeric": "numeric", "float": "numeric",
    "double": "numeric", "real": "numeric", "money": "numeric",
    "varchar": "string", "char": "string", "text": "string", "string": "string",
    "boolean": "boolean", "bool": "boolean",
    "date": "datetime", "datetime": "datetime", "timestamp": "datetime",
}

_SEVERITY = {
    "MISSING_COLUMN":      (Severity.CRITICAL, ["Consistency"]),
    "PK_DUPLICATE":        (Severity.CRITICAL, ["Uniqueness"]),
    "PK_NULL":             (Severity.CRITICAL, ["Completeness"]),
    "ORPHAN_FOREIGN_KEY":  (Severity.CRITICAL, ["Consistency"]),
    "TYPE_MISMATCH":       (Severity.HIGH,     ["Validity"]),
    "UNIQUE_VIOLATION":    (Severity.HIGH,     ["Uniqueness"]),
    "NOT_NULL_VIOLATION":  (Severity.HIGH,     ["Completeness"]),
    "EXTRA_COLUMN":        (Severity.INFO,     ["Consistency"]),
    "FK_UNCHECKED":        (Severity.WARN,     ["Consistency"]),
}


def _base_type(dbml_type: str) -> str:
    """Strip size/precision: varchar(255) → varchar."""
    return re.sub(r"\(.*?\)", "", dbml_type).strip().lower()


def _pandas_family(dtype) -> str:
    if pt.is_bool_dtype(dtype):
        return "boolean"
    if pt.is_numeric_dtype(dtype):
        return "numeric"
    if pt.is_datetime64_any_dtype(dtype):
        return "datetime"
    return "string"


def _err(error_type: str, table: str, col: str | None, count: int,
         description: str, samples: list) -> IntegrityError:
    sev, dims = _SEVERITY[error_type]
    return IntegrityError(
        error_type=error_type,
        description=description,
        severity=sev,
        affected_table=table,
        affected_count=count,
        affected_column=col,
        dq_dimensions=dims,
        top_10_samples=samples[:10],
    )


# ── 1a-1: Matcher ─────────────────────────────────────────────────────────────


def match_table(df: pd.DataFrame, parsed: dict, csv_path: str) -> str:
    """Return the DBML table name that corresponds to this CSV."""
    if len(parsed) == 1:
        return next(iter(parsed))
    stem = Path(csv_path).stem.lower()
    for name in parsed:
        if name.lower() == stem:
            return name
    raise ValueError(
        f"Cannot match '{csv_path}' to any DBML table {list(parsed.keys())}. "
        "Rename CSV to match a table name or use a single-table DBML."
    )


# ── 1a-2: Single-table validators ────────────────────────────────────────────

def validate_table(df: pd.DataFrame, table_name: str, parsed: dict) -> list:
    schema_cols = parsed[table_name]["columns"]
    df_cols = set(df.columns)
    errors = []

    # MISSING_COLUMN / EXTRA_COLUMN
    for col in schema_cols:
        if col not in df_cols:
            errors.append(_err("MISSING_COLUMN", table_name, col, 0,
                               f"Column '{col}' declared in schema but absent from data", []))
    for col in df_cols:
        if col not in schema_cols:
            errors.append(_err("EXTRA_COLUMN", table_name, col, len(df),
                               f"Column '{col}' present in data but not declared in schema", []))

    # Per-column checks (only columns present in both)
    for col, meta in schema_cols.items():
        if col not in df_cols:
            continue
        series = df[col]

        # TYPE_MISMATCH — family-level comparison
        raw_type = _base_type(meta["type"])
        dbml_fam = DBML_FAMILY.get(raw_type)
        if dbml_fam is not None:
            pandas_fam = _pandas_family(series.dtype)
            if dbml_fam != pandas_fam:
                samples = series.dropna().head(10).tolist()
                errors.append(_err("TYPE_MISMATCH", table_name, col, len(df),
                                   f"Column '{col}': expected family '{dbml_fam}', got '{pandas_fam}' (dtype={series.dtype})",
                                   [{"value": v} for v in samples]))

        # PK checks
        if meta["pk"]:
            null_mask = series.isna()
            if null_mask.any():
                n = int(null_mask.sum())
                samples = df[null_mask].head(10).to_dict(orient="records")
                errors.append(_err("PK_NULL", table_name, col, n,
                                   f"PK column '{col}' has {n} null value(s)", samples))
            dup_mask = series.notna() & series.duplicated(keep=False)
            if dup_mask.any():
                n = int(dup_mask.sum())
                samples = df[dup_mask].head(10).to_dict(orient="records")
                errors.append(_err("PK_DUPLICATE", table_name, col, n,
                                   f"PK column '{col}' has {n} duplicate value(s)", samples))
            continue  # pk implies unique; skip separate unique/not_null checks

        # NOT_NULL_VIOLATION (non-pk, not_null declared)
        if meta["not_null"]:
            null_mask = series.isna()
            if null_mask.any():
                n = int(null_mask.sum())
                samples = df[null_mask].head(10).to_dict(orient="records")
                errors.append(_err("NOT_NULL_VIOLATION", table_name, col, n,
                                   f"Column '{col}' has {n} null(s) but is declared NOT NULL", samples))

        # UNIQUE_VIOLATION (non-pk, unique declared)
        if meta["unique"]:
            non_null = series.dropna()
            if non_null.duplicated().any():
                dup_mask = series.notna() & series.duplicated(keep=False)
                n = int(dup_mask.sum())
                samples = df[dup_mask].head(10).to_dict(orient="records")
                errors.append(_err("UNIQUE_VIOLATION", table_name, col, n,
                                   f"Column '{col}' has {n} duplicate value(s) but is declared UNIQUE", samples))

    return errors


# ── (normalize_refs moved to ingestion/schema_reader.py) ─────────────────────


# ── 1b-2: Orphan FK check ────────────────────────────────────────────────────

def check_foreign_keys(tables: dict, refs: list) -> list:
    """Check referential integrity across loaded tables.
    FK null rows are NOT orphans. Family mismatch → FK_UNCHECKED (no false positives).
    """
    errors = []
    for ref in refs:
        child_t = ref["child_table"]
        fk_col = ref["fk_col"]
        parent_t = ref["parent_table"]
        pk_col = ref["pk_col"]

        # Missing table or column → FK_UNCHECKED
        if child_t not in tables or parent_t not in tables:
            missing = child_t if child_t not in tables else parent_t
            errors.append(IntegrityError(
                error_type="FK_UNCHECKED",
                description=f"Cannot check FK {child_t}.{fk_col} → {parent_t}.{pk_col}: table '{missing}' not loaded",
                severity=Severity.WARN,
                affected_table=child_t,
                affected_column=fk_col,
                dq_dimensions=["Consistency"],
            ))
            continue

        child_df = tables[child_t]
        parent_df = tables[parent_t]

        if fk_col not in child_df.columns or pk_col not in parent_df.columns:
            errors.append(IntegrityError(
                error_type="FK_UNCHECKED",
                description=f"Cannot check FK {child_t}.{fk_col} → {parent_t}.{pk_col}: column absent",
                severity=Severity.WARN,
                affected_table=child_t,
                affected_column=fk_col,
                dq_dimensions=["Consistency"],
            ))
            continue

        fk_series = child_df[fk_col]
        pk_series = parent_df[pk_col]

        # Family mismatch guard → FK_UNCHECKED (avoid false orphans)
        fk_fam = _pandas_family(fk_series.dtype)
        pk_fam = _pandas_family(pk_series.dtype)
        if fk_fam != pk_fam:
            errors.append(IntegrityError(
                error_type="FK_UNCHECKED",
                description=(f"Cannot check FK {child_t}.{fk_col} → {parent_t}.{pk_col}: "
                             f"type family mismatch ({fk_fam} vs {pk_fam})"),
                severity=Severity.WARN,
                affected_table=child_t,
                affected_column=fk_col,
                dq_dimensions=["Consistency"],
            ))
            continue

        # Empty parent → every non-null FK would be orphan; emit UNCHECKED
        parent_keys = set(pk_series.dropna())
        if not parent_keys:
            errors.append(IntegrityError(
                error_type="FK_UNCHECKED",
                description=f"Parent table '{parent_t}' has no rows; cannot validate FK {child_t}.{fk_col}",
                severity=Severity.WARN,
                affected_table=child_t,
                affected_column=fk_col,
                dq_dimensions=["Consistency"],
            ))
            continue

        orphan_mask = fk_series.notna() & ~fk_series.isin(parent_keys)
        n = int(orphan_mask.sum())
        if n > 0:
            samples = child_df[orphan_mask][[fk_col]].head(10).to_dict(orient="records")
            errors.append(IntegrityError(
                error_type="ORPHAN_FOREIGN_KEY",
                description=f"{n} row(s) in {child_t}.{fk_col} reference non-existent {parent_t}.{pk_col}",
                severity=Severity.CRITICAL,
                affected_table=child_t,
                affected_column=fk_col,
                affected_count=n,
                dq_dimensions=["Consistency"],
                top_10_samples=samples,
            ))
    return errors


# ── 1b-3: Multi-table ingestion + validation ──────────────────────────────────

def load_tables(csv_paths: list, parsed_tables: dict) -> dict:
    """Match each CSV to a schema table by filename stem. Unmatched → log + skip."""
    from ingestion.csv_reader import load_csv
    result = {}
    for path in csv_paths:
        stem = Path(path).stem.lower()
        matched = next((name for name in parsed_tables if name.lower() == stem), None)
        if matched is None:
            logger.warning("CSV '%s' does not match any schema table — skipping.", path)
            continue
        result[matched] = load_csv(path)
    return result


def validate_schema_multi(csv_paths: list, schema_path: str) -> SchemaEvaluationFindings:
    """Run 7 single-table validators + FK checks. Supports .dbml and .sql."""
    schema = parse_schema(schema_path)
    parsed = schema["tables"]
    tables = load_tables(csv_paths, parsed)

    errors = []
    for tname, df in tables.items():
        errors += validate_table(df, tname, parsed)
    errors += check_foreign_keys(tables, schema["refs"])

    meta = SchemaMeta(
        schema_file=schema["meta"]["file_name"],
        total_tables=schema["meta"]["total_tables"],
        total_relationships=schema["meta"]["total_relationships"],
    )
    table_infos = [
        TableInfo(name=tname, columns=list(tcols["columns"].keys()))
        for tname, tcols in parsed.items()
    ]
    return SchemaEvaluationFindings(schema_meta=meta, tables=table_infos, integrity_errors=errors)


# ── 1a-3: Build SchemaEvaluationFindings ─────────────────────────────────────

def build_schema_findings(df: pd.DataFrame, csv_path: str, schema_path: str) -> SchemaEvaluationFindings:
    schema = parse_schema(schema_path)
    parsed = schema["tables"]
    table_name = match_table(df, parsed, csv_path)
    errors = validate_table(df, table_name, parsed)

    meta = SchemaMeta(
        schema_file=schema["meta"]["file_name"],
        total_tables=schema["meta"]["total_tables"],
        total_relationships=schema["meta"]["total_relationships"],
    )
    table_infos = [
        TableInfo(name=tname, columns=list(tcols["columns"].keys()))
        for tname, tcols in parsed.items()
    ]

    return SchemaEvaluationFindings(
        schema_meta=meta,
        tables=table_infos,
        integrity_errors=errors,
    )
