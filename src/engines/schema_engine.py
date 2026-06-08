import logging
import json
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
import pandas as pd
import pandas.api.types as pt
from ingestion.schema_reader import parse_schema
from ontology.models import (
    IntegrityError,
    MissingFieldContext,
    RelationshipInfo,
    Severity,
    SchemaEvaluationFindings,
    SchemaMeta,
    TableInfo,
)

logger = logging.getLogger(__name__)
_POLICY_PATH = Path(__file__).parent.parent.parent / "config" / "schema_inference_policy.json"

_DEFAULT_SCHEMA_POLICY = {
    "generic_tokens": ["id", "ma", "code", "key", "fk", "pk", "uuid", "no", "number"],
    "phrase_synonyms": {
        "truonghoc": "school",
        "hocsinh": "student",
        "sinhvien": "student",
        "lophoc": "class",
        "giaovien": "teacher",
        "khachhang": "customer",
        "nguoidung": "user",
        "donhang": "order",
        "sanpham": "product",
    },
    "token_synonyms": {
        "truong": "school",
        "school": "school",
        "schools": "school",
        "hoc": "study",
        "hocsinh": "student",
        "student": "student",
        "students": "student",
        "sinhvien": "student",
        "lop": "class",
        "class": "class",
        "classes": "class",
        "gv": "teacher",
        "teacher": "teacher",
        "teachers": "teacher",
        "khachhang": "customer",
        "customer": "customer",
        "customers": "customer",
        "user": "user",
        "users": "user",
        "order": "order",
        "orders": "order",
        "product": "product",
        "products": "product",
    },
    "thresholds": {
        "alias_similarity": 0.82,
        "table_match_score": 0.5,
        "primary_key_score": 0.55,
        "relationship_value_coverage": 0.6,
        "relationship_name_score": 0.35,
        "relationship_confidence": 0.65,
    },
    "primary_key_weights": {
        "identifier_token": 0.35,
        "generic_identifier_exact": 0.4,
        "table_concept_match": 0.35,
        "table_identifier_pattern": 0.4,
        "first_column": 0.1,
        "unique_key": 0.15,
    },
    "relationship_weights": {
        "coverage": 0.45,
        "name_score": 0.35,
        "parent_unique_bonus": 0.2,
    },
}


def load_schema_inference_policy(path: str | Path | None = None) -> dict:
    policy = json.loads(json.dumps(_DEFAULT_SCHEMA_POLICY))
    policy_path = Path(path) if path is not None else _POLICY_PATH
    if not policy_path.exists():
        return policy
    try:
        loaded = json.loads(policy_path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Cannot load schema inference policy %s: %s", policy_path, exc)
        return policy
    for section, value in loaded.items():
        if section.startswith("_"):
            continue
        if isinstance(value, dict) and isinstance(policy.get(section), dict):
            policy[section].update(value)
        else:
            policy[section] = value
    return policy


_SCHEMA_POLICY = load_schema_inference_policy()
_THRESHOLDS = _SCHEMA_POLICY["thresholds"]
_PK_WEIGHTS = _SCHEMA_POLICY["primary_key_weights"]
_REL_WEIGHTS = _SCHEMA_POLICY["relationship_weights"]

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
    "MISSING_TABLE":       (Severity.WARN,     ["Completeness"]),
    "COLUMN_ALIAS_INFERRED": (Severity.WARN,   ["Consistency"]),
    "MISSING_RELATIONSHIP_METADATA": (Severity.WARN, ["Consistency"]),
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


def _err(
    error_type: str,
    table: str,
    col: str | None,
    count: int,
    description: str,
    samples: list,
    missing_field_context: MissingFieldContext | None = None,
    relationship: RelationshipInfo | None = None,
) -> IntegrityError:
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
        missing_field_context=missing_field_context,
        relationship=relationship,
    )


_GENERIC_TOKENS = set(_SCHEMA_POLICY["generic_tokens"])
_PHRASE_SYNONYMS = dict(_SCHEMA_POLICY["phrase_synonyms"])
_TOKEN_SYNONYMS = dict(_SCHEMA_POLICY["token_synonyms"])


def _strip_accents(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch))


def _singular(token: str) -> str:
    if token.endswith("ies") and len(token) > 4:
        return f"{token[:-3]}y"
    if token.endswith("sses") and len(token) > 5:
        return token[:-2]
    if token.endswith("ss"):
        return token
    if token.endswith("s") and len(token) > 3:
        return token[:-1]
    return token


def _identifier_tokens(name: str) -> list[str]:
    text = _strip_accents(str(name)).lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return [_singular(tok) for tok in text.split() if tok]


def _concept_tokens(name: str) -> set[str]:
    raw_tokens = _identifier_tokens(name)
    collapsed = "".join(raw_tokens)
    concepts: set[str] = set()
    if collapsed in _PHRASE_SYNONYMS:
        concepts.add(_PHRASE_SYNONYMS[collapsed])
    for tok in raw_tokens:
        mapped = _TOKEN_SYNONYMS.get(tok, tok)
        mapped = _singular(mapped)
        if mapped not in _GENERIC_TOKENS:
            concepts.add(mapped)
    return concepts


def _normalised_identifier(name: str) -> str:
    return "".join(_identifier_tokens(name))


def _name_similarity(left: str, right: str) -> float:
    left_norm = _normalised_identifier(left)
    right_norm = _normalised_identifier(right)
    if not left_norm or not right_norm:
        return 0.0
    ratio = SequenceMatcher(None, left_norm, right_norm).ratio()
    if _concept_tokens(left) & _concept_tokens(right):
        return max(ratio, 0.86)
    return ratio


def _best_column_alias(expected: str, df_cols: set[str], threshold: float | None = None) -> tuple[str | None, float]:
    threshold = _THRESHOLDS["alias_similarity"] if threshold is None else threshold
    best_col = None
    best_score = 0.0
    for actual in df_cols:
        if actual == expected:
            continue
        score = _name_similarity(expected, actual)
        if score > best_score:
            best_col = actual
            best_score = score
    if best_col is None or best_score < threshold:
        return None, best_score
    return best_col, best_score


def _meaning_from_column(column: str) -> str | None:
    concepts = sorted(_concept_tokens(column))
    if not concepts:
        return None
    if "school" in concepts:
        return "school identifier or school attribute"
    return ", ".join(concepts)


def _missing_context(
    table: str,
    expected: str,
    schema_cols: dict,
    df_cols: set[str],
    aliases: list[str],
) -> MissingFieldContext:
    return MissingFieldContext(
        expected_column=expected,
        table_context=(
            f"Table '{table}' expects {len(schema_cols)} schema column(s); "
            f"loaded data has {len(df_cols)} column(s)."
        ),
        inferred_meaning=_meaning_from_column(expected),
        is_intentional_missing=None,
        intentional_missing_basis="unknown; source owner confirmation required",
        candidate_aliases=aliases,
    )


# ── 1a-1: Matcher ─────────────────────────────────────────────────────────────


def _match_table_by_columns(df: pd.DataFrame, parsed: dict, used: set[str]) -> str | None:
    df_cols = set(df.columns)
    best_name = None
    best_score = 0.0
    for table_name, meta in parsed.items():
        if table_name in used:
            continue
        schema_cols = list(meta["columns"].keys())
        if not schema_cols:
            continue
        matched = 0
        for expected in schema_cols:
            if expected in df_cols:
                matched += 1
                continue
            alias, _ = _best_column_alias(expected, df_cols)
            if alias is not None:
                matched += 1
        score = matched / len(schema_cols)
        if score > best_score:
            best_name = table_name
            best_score = score
    if best_name is None or best_score < _THRESHOLDS["table_match_score"]:
        return None
    return best_name


def match_table(df: pd.DataFrame, parsed: dict, csv_path: str) -> str:
    """Return the DBML table name that corresponds to this CSV."""
    if len(parsed) == 1:
        return next(iter(parsed))
    stem = Path(csv_path).stem.lower()
    for name in parsed:
        if name.lower() == stem:
            return name
    matched = _match_table_by_columns(df, parsed, used=set())
    if matched is not None:
        return matched
    raise ValueError(
        f"Cannot match '{csv_path}' to any DBML table {list(parsed.keys())}. "
        "Rename the data file to match a table name, provide a single-table schema, "
        "or include enough overlapping columns for semantic matching."
    )


# ── 1a-2: Single-table validators ────────────────────────────────────────────

def validate_table(df: pd.DataFrame, table_name: str, parsed: dict) -> list:
    schema_cols = parsed[table_name]["columns"]
    df_cols = set(df.columns)
    errors = []
    alias_map: dict[str, str] = {}

    # MISSING_COLUMN / EXTRA_COLUMN
    for col in schema_cols:
        if col not in df_cols:
            alias, score = _best_column_alias(col, df_cols)
            if alias is not None:
                alias_map[col] = alias
                context = _missing_context(table_name, col, schema_cols, df_cols, [alias])
                errors.append(_err(
                    "COLUMN_ALIAS_INFERRED", table_name, col, len(df),
                    (
                        f"Column '{col}' declared in schema is absent, but data column "
                        f"'{alias}' is a likely alias (name similarity={score:.2f})"
                    ),
                    [],
                    missing_field_context=context,
                ))
            else:
                context = _missing_context(table_name, col, schema_cols, df_cols, [])
                errors.append(_err(
                    "MISSING_COLUMN", table_name, col, 0,
                    f"Column '{col}' declared in schema but absent from data",
                    [],
                    missing_field_context=context,
                ))
    for col in df_cols:
        if col not in schema_cols and col not in alias_map.values():
            errors.append(_err("EXTRA_COLUMN", table_name, col, len(df),
                               f"Column '{col}' present in data but not declared in schema", []))

    # Per-column checks (only columns present in both)
    for col, meta in schema_cols.items():
        data_col = col if col in df_cols else alias_map.get(col)
        if data_col is None:
            continue
        series = df[data_col]

        # TYPE_MISMATCH — family-level comparison
        raw_type = _base_type(meta["type"])
        dbml_fam = DBML_FAMILY.get(raw_type)
        if dbml_fam is not None:
            pandas_fam = _pandas_family(series.dtype)
            if dbml_fam != pandas_fam:
                samples = series.dropna().head(10).tolist()
                errors.append(_err("TYPE_MISMATCH", table_name, col, len(df),
                                   f"Column '{col}' (data column '{data_col}'): expected family '{dbml_fam}', got '{pandas_fam}' (dtype={series.dtype})",
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

def _resolve_declared_column(expected: str, df: pd.DataFrame) -> tuple[str | None, float | None]:
    if expected in df.columns:
        return expected, None
    alias, score = _best_column_alias(expected, set(df.columns))
    if alias is None:
        return None, None
    return alias, score


def _column_display(declared: str, actual: str) -> str:
    if declared == actual:
        return declared
    return f"{declared} (data column '{actual}')"


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
        actual_fk_col, _ = _resolve_declared_column(fk_col, child_df)
        actual_pk_col, _ = _resolve_declared_column(pk_col, parent_df)

        if actual_fk_col is None or actual_pk_col is None:
            missing_parts = []
            if actual_fk_col is None:
                missing_parts.append(f"{child_t}.{fk_col}")
            if actual_pk_col is None:
                missing_parts.append(f"{parent_t}.{pk_col}")
            errors.append(IntegrityError(
                error_type="FK_UNCHECKED",
                description=(
                    f"Cannot check FK {child_t}.{fk_col} → {parent_t}.{pk_col}: "
                    f"column absent ({', '.join(missing_parts)})"
                ),
                severity=Severity.WARN,
                affected_table=child_t,
                affected_column=fk_col,
                dq_dimensions=["Consistency"],
            ))
            continue

        fk_series = child_df[actual_fk_col]
        pk_series = parent_df[actual_pk_col]
        fk_label = _column_display(fk_col, actual_fk_col)
        pk_label = _column_display(pk_col, actual_pk_col)

        # Family mismatch guard → FK_UNCHECKED (avoid false orphans)
        fk_fam = _pandas_family(fk_series.dtype)
        pk_fam = _pandas_family(pk_series.dtype)
        if fk_fam != pk_fam:
            errors.append(IntegrityError(
                error_type="FK_UNCHECKED",
                description=(f"Cannot check FK {child_t}.{fk_col} → {parent_t}.{pk_col}: "
                             f"type family mismatch ({fk_fam} vs {pk_fam}) using "
                             f"{child_t}.{fk_label} → {parent_t}.{pk_label}"),
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
                description=f"Parent table '{parent_t}' has no rows; cannot validate FK {child_t}.{fk_label}",
                severity=Severity.WARN,
                affected_table=child_t,
                affected_column=fk_col,
                dq_dimensions=["Consistency"],
            ))
            continue

        orphan_mask = fk_series.notna() & ~fk_series.isin(parent_keys)
        n = int(orphan_mask.sum())
        if n > 0:
            samples = child_df[orphan_mask][[actual_fk_col]].head(10).to_dict(orient="records")
            errors.append(IntegrityError(
                error_type="ORPHAN_FOREIGN_KEY",
                description=(
                    f"{n} row(s) in {child_t}.{fk_label} reference non-existent "
                    f"{parent_t}.{pk_label}"
                ),
                severity=Severity.CRITICAL,
                affected_table=child_t,
                affected_column=fk_col,
                affected_count=n,
                dq_dimensions=["Consistency"],
                top_10_samples=samples,
            ))
    return errors


def _ref_key(child_table: str, child_column: str, parent_table: str, parent_column: str) -> tuple[str, str, str, str]:
    return (
        child_table.lower(),
        child_column.lower(),
        parent_table.lower(),
        parent_column.lower(),
    )


def _normalise_value(value) -> str:
    return _strip_accents(str(value)).strip().lower()


def _value_coverage(child: pd.Series, parent: pd.Series) -> tuple[float, int, int]:
    child_values = child.dropna()
    if child_values.empty:
        return 0.0, 0, 0
    parent_values = {_normalise_value(v) for v in parent.dropna()}
    if not parent_values:
        return 0.0, int(len(child_values)), int(len(child_values))
    matches = child_values.map(lambda v: _normalise_value(v) in parent_values)
    matched_count = int(matches.sum())
    total = int(len(child_values))
    return matched_count / total, total, total - matched_count


def _is_unique_key(series: pd.Series) -> bool:
    non_null = series.dropna()
    return bool(len(non_null) > 0 and non_null.nunique(dropna=True) == len(non_null))


def _safe_table_name(path: str, used: set[str]) -> str:
    base = re.sub(r"[^A-Za-z0-9_]+", "_", Path(path).stem).strip("_") or "table"
    name = base
    index = 2
    while name in used:
        name = f"{base}_{index}"
        index += 1
    used.add(name)
    return name


def load_tables_by_path(data_paths: list) -> dict:
    """Load files directly and use file stems as table names."""
    from ingestion.registry import load_any

    tables = {}
    used: set[str] = set()
    for path in data_paths:
        tables[_safe_table_name(path, used)] = load_any(path)
    return tables


def _inferred_column_type(series: pd.Series) -> str:
    if pt.is_bool_dtype(series.dtype):
        return "boolean"
    if pt.is_integer_dtype(series.dtype):
        return "integer"
    if pt.is_float_dtype(series.dtype) or pt.is_numeric_dtype(series.dtype):
        return "decimal"
    if pt.is_datetime64_any_dtype(series.dtype):
        return "timestamp"
    return "varchar"


def _primary_key_score(table_name: str, column: str, series: pd.Series, position: int) -> float:
    tokens = set(_identifier_tokens(column))
    concepts = _concept_tokens(column)
    table_concepts = _concept_tokens(table_name)
    normalised = _normalised_identifier(column)
    table_norm = _normalised_identifier(table_name)

    score = 0.0
    if tokens & {"id", "key", "code", "uuid"}:
        score += _PK_WEIGHTS["identifier_token"]
    if normalised in {"id", "uuid"}:
        score += _PK_WEIGHTS["generic_identifier_exact"]
    if concepts & table_concepts:
        score += _PK_WEIGHTS["table_concept_match"]
    if table_norm and normalised in {
        f"{table_norm}id",
        f"id{table_norm}",
        f"{table_norm}code",
        f"code{table_norm}",
    }:
        score += _PK_WEIGHTS["table_identifier_pattern"]
    if position == 0:
        score += _PK_WEIGHTS["first_column"]
    if _is_unique_key(series):
        score += _PK_WEIGHTS["unique_key"]
    return score


def _infer_primary_key(table_name: str, df: pd.DataFrame) -> str | None:
    best_col = None
    best_score = 0.0
    for position, column in enumerate(df.columns):
        score = _primary_key_score(table_name, column, df[column], position)
        if score > best_score:
            best_col = column
            best_score = score
    if best_col is None or best_score < _THRESHOLDS["primary_key_score"]:
        return None
    return best_col


def infer_parsed_schema(tables: dict) -> dict:
    """Infer the internal schema shape used by validators from loaded tables."""
    parsed = {}
    for table_name, df in tables.items():
        pk_col = _infer_primary_key(table_name, df)
        columns = {}
        for column in df.columns:
            is_pk = column == pk_col
            columns[column] = {
                "type": _inferred_column_type(df[column]),
                "pk": is_pk,
                "unique": is_pk,
                "not_null": is_pk,
            }
        parsed[table_name] = {"columns": columns}
    return parsed


def _candidate_parent_columns(table_name: str, df: pd.DataFrame, parsed: dict) -> list[str]:
    schema_cols = parsed.get(table_name, {}).get("columns", {})
    candidates: list[str] = []
    for col, meta in schema_cols.items():
        if col in df.columns and (meta.get("pk") or meta.get("unique")):
            candidates.append(col)
    for col in df.columns:
        tokens = set(_identifier_tokens(col))
        normalised = _normalised_identifier(col)
        is_generic_id = normalised in {"id", "uuid"}
        is_unique_identifier = bool(tokens & {"id", "ma", "code", "key", "uuid"} and _is_unique_key(df[col]))
        if col not in candidates and (is_generic_id or is_unique_identifier):
            candidates.append(col)
    return candidates


def _relationship_name_score(child_col: str, parent_col: str, parent_table: str) -> float:
    child_concepts = _concept_tokens(child_col)
    parent_col_concepts = _concept_tokens(parent_col)
    parent_table_concepts = _concept_tokens(parent_table)
    parent_col_tokens = set(_identifier_tokens(parent_col))

    if child_concepts & parent_col_concepts:
        return 0.9
    if child_concepts & parent_table_concepts and parent_col_tokens <= _GENERIC_TOKENS:
        return 0.92
    if child_concepts & parent_table_concepts:
        return 0.75
    return max(_name_similarity(child_col, parent_col), _name_similarity(child_col, parent_table))


def _explicit_relationships(refs: list) -> list[RelationshipInfo]:
    return [
        RelationshipInfo(
            child_table=ref["child_table"],
            child_column=ref["fk_col"],
            parent_table=ref["parent_table"],
            parent_column=ref["pk_col"],
            relationship_type="explicit_fk",
            status="declared_in_schema",
            confidence=1.0,
            evidence=["Declared in schema metadata"],
        )
        for ref in refs
    ]


def infer_relationships(
    tables: dict,
    parsed: dict,
    refs: list,
    inferred_status: str = "missing_from_schema",
) -> list[RelationshipInfo]:
    explicit_keys = {
        _ref_key(ref["child_table"], ref["fk_col"], ref["parent_table"], ref["pk_col"])
        for ref in refs
    }
    relationships = _explicit_relationships(refs)

    for child_t, child_df in tables.items():
        for parent_t, parent_df in tables.items():
            if child_t == parent_t:
                continue
            for parent_col in _candidate_parent_columns(parent_t, parent_df, parsed):
                if parent_col not in parent_df.columns:
                    continue
                parent_unique_bonus = _REL_WEIGHTS["parent_unique_bonus"] if _is_unique_key(parent_df[parent_col]) else 0.0
                for child_col in child_df.columns:
                    key = _ref_key(child_t, child_col, parent_t, parent_col)
                    if key in explicit_keys:
                        continue
                    coverage, total, unmatched = _value_coverage(child_df[child_col], parent_df[parent_col])
                    if coverage < _THRESHOLDS["relationship_value_coverage"]:
                        continue
                    name_score = _relationship_name_score(child_col, parent_col, parent_t)
                    if name_score < _THRESHOLDS["relationship_name_score"] and parent_unique_bonus == 0.0:
                        continue
                    confidence = round(min(
                        0.99,
                        (_REL_WEIGHTS["coverage"] * coverage)
                        + (_REL_WEIGHTS["name_score"] * name_score)
                        + parent_unique_bonus,
                    ), 3)
                    if confidence < _THRESHOLDS["relationship_confidence"]:
                        continue
                    relationships.append(RelationshipInfo(
                        child_table=child_t,
                        child_column=child_col,
                        parent_table=parent_t,
                        parent_column=parent_col,
                        relationship_type="inferred_fk",
                        status=inferred_status,
                        confidence=confidence,
                        evidence=[
                            f"value_coverage={coverage:.3f} ({total - unmatched}/{total} non-null child values found in parent)",
                            f"unmatched_non_null_child_values={unmatched}",
                            f"name_score={name_score:.3f}",
                        ],
                    ))

    return relationships


def _missing_relationship_errors(relationships: list[RelationshipInfo]) -> list[IntegrityError]:
    errors = []
    for rel in relationships:
        if rel.relationship_type != "inferred_fk" or rel.status != "missing_from_schema":
            continue
        errors.append(_err(
            "MISSING_RELATIONSHIP_METADATA",
            rel.child_table,
            rel.child_column,
            0,
            (
                f"Likely relationship {rel.child_table}.{rel.child_column} -> "
                f"{rel.parent_table}.{rel.parent_column} is present in data but not declared in schema"
            ),
            [],
            relationship=rel,
        ))
    return errors


# ── 1b-3: Multi-table ingestion + validation ──────────────────────────────────

def load_tables(data_paths: list, parsed_tables: dict) -> dict:
    """Match each data file to a schema table by stem, then by column similarity."""
    from ingestion.registry import load_any
    result = {}
    used: set[str] = set()
    for path in data_paths:
        df = load_any(path)
        stem = Path(path).stem.lower()
        matched = next((name for name in parsed_tables if name.lower() == stem and name not in used), None)
        if matched is None:
            matched = _match_table_by_columns(df, parsed_tables, used)
        if matched is None:
            logger.warning("Data file '%s' does not match any schema table — skipping.", path)
            continue
        result[matched] = df
        used.add(matched)
    return result


def _relationship_refs(relationships: list[RelationshipInfo]) -> list[dict]:
    return [
        {
            "child_table": rel.child_table,
            "fk_col": rel.child_column,
            "parent_table": rel.parent_table,
            "pk_col": rel.parent_column,
        }
        for rel in relationships
        if rel.relationship_type == "inferred_fk"
    ]


def validate_schema_multi(data_paths: list, schema_path: str | None = None) -> SchemaEvaluationFindings:
    """Validate multi-table data with an explicit schema or an inferred schema."""
    inferred_schema = schema_path is None
    if inferred_schema:
        tables = load_tables_by_path(data_paths)
        parsed = infer_parsed_schema(tables)
        schema = {
            "tables": parsed,
            "refs": [],
            "meta": {
                "file_name": "inferred_from_data",
                "total_tables": len(parsed),
                "total_relationships": 0,
            },
        }
    else:
        schema = parse_schema(schema_path)
        parsed = schema["tables"]
        tables = load_tables(data_paths, parsed)

    errors = []
    for missing_t in sorted(set(parsed) - set(tables)):
        errors.append(_err(
            "MISSING_TABLE",
            missing_t,
            None,
            0,
            f"Table '{missing_t}' declared in schema but no matching data file was loaded",
            [],
        ))
    for tname, df in tables.items():
        errors += validate_table(df, tname, parsed)
    relationships = infer_relationships(
        tables,
        parsed,
        schema["refs"],
        inferred_status="inferred_from_data" if inferred_schema else "missing_from_schema",
    )
    refs_to_check = _relationship_refs(relationships) if inferred_schema else schema["refs"]
    errors += check_foreign_keys(tables, refs_to_check)
    if not inferred_schema:
        errors += _missing_relationship_errors(relationships)

    meta = SchemaMeta(
        schema_file=schema["meta"]["file_name"],
        total_tables=schema["meta"]["total_tables"],
        total_relationships=len(relationships) if inferred_schema else schema["meta"]["total_relationships"],
    )
    table_infos = [
        TableInfo(name=tname, columns=list(tcols["columns"].keys()))
        for tname, tcols in parsed.items()
    ]
    return SchemaEvaluationFindings(
        schema_meta=meta,
        tables=table_infos,
        integrity_errors=errors,
        relationships=relationships,
    )


# ── 1a-3: Build SchemaEvaluationFindings ─────────────────────────────────────

def build_schema_findings(df: pd.DataFrame, data_path: str, schema_path: str) -> SchemaEvaluationFindings:
    schema = parse_schema(schema_path)
    parsed = schema["tables"]
    table_name = match_table(df, parsed, data_path)
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
        relationships=_explicit_relationships(schema["refs"]),
    )
