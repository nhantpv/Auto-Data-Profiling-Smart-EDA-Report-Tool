from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
import pandas.api.types as pt

from ontology.models import (
    CrossTableAnalysis,
    CrossTableCorrelation,
    RelationshipInfo,
    SafeJoinStep,
)


_JOIN_KEY = "__smart_eda_join_key"
_ID_TOKENS = {"id", "uuid", "key", "code"}


def _normalise_join_value(value) -> str | None:
    if pd.isna(value):
        return None
    text = str(value).strip()
    if text == "":
        return None
    try:
        as_float = float(text)
    except ValueError:
        return text.lower()
    if as_float.is_integer():
        return str(int(as_float))
    return str(as_float)


def _normalise_key(series: pd.Series) -> pd.Series:
    return series.map(_normalise_join_value)


def _source_table(feature: str) -> str:
    if "__via__" in feature:
        return feature.split("__via__", 1)[0]
    return feature.split("__", 1)[0]


def _column_leaf(feature: str) -> str:
    if "__via__" in feature:
        return feature.rsplit("__", 1)[-1]
    if "__" in feature:
        return feature.split("__", 1)[1]
    return feature


def _is_identifier_column(feature: str) -> bool:
    leaf = _column_leaf(feature).lower()
    tokens = {token for token in leaf.replace("-", "_").split("_") if token}
    return bool(tokens & _ID_TOKENS)


def _numeric_measure_density(df: pd.DataFrame) -> float:
    if df.empty or len(df.columns) == 0:
        return 0.0
    numeric = 0
    for column in df.columns:
        if _is_identifier_column(str(column)):
            continue
        if pt.is_numeric_dtype(df[column]):
            numeric += 1
    return numeric / len(df.columns)


def choose_fact_table(tables: dict[str, pd.DataFrame], relationships: Iterable[RelationshipInfo]) -> str | None:
    if not tables:
        return None
    outgoing = {name: 0 for name in tables}
    incoming = {name: 0 for name in tables}
    for rel in relationships:
        if rel.child_table in outgoing:
            outgoing[rel.child_table] += 1
        if rel.parent_table in incoming:
            incoming[rel.parent_table] += 1

    return max(
        tables,
        key=lambda name: (
            outgoing.get(name, 0),
            len(tables[name]),
            _numeric_measure_density(tables[name]),
            -incoming.get(name, 0),
            name,
        ),
    )


def _prepare_parent(
    parent: pd.DataFrame,
    parent_column: str,
) -> tuple[pd.DataFrame, int, bool, list[str]]:
    warnings: list[str] = []
    original_rows = len(parent)
    prepared = parent.drop_duplicates().copy()
    exact_removed = original_rows - len(prepared)
    if exact_removed:
        warnings.append(f"Removed {exact_removed} exact duplicate row(s) from parent table before join.")

    prepared[_JOIN_KEY] = _normalise_key(prepared[parent_column])
    prepared = prepared[prepared[_JOIN_KEY].notna()].copy()
    parent_key_unique = not prepared[_JOIN_KEY].duplicated().any()
    if not parent_key_unique:
        duplicate_keys = int(prepared[_JOIN_KEY].duplicated(keep=False).sum())
        warnings.append(
            f"Parent key is not unique after exact dedupe; collapsed {duplicate_keys} duplicate-key row(s) with first()."
        )
        prepared = prepared.groupby(_JOIN_KEY, as_index=False, dropna=True).first()
    return prepared, exact_removed, parent_key_unique, warnings


def _prefix_frame(df: pd.DataFrame, prefix: str) -> pd.DataFrame:
    return df.rename(columns={column: f"{prefix}__{column}" for column in df.columns})


def _safe_join(
    current: pd.DataFrame,
    tables: dict[str, pd.DataFrame],
    rel: RelationshipInfo,
    step_index: int,
) -> tuple[pd.DataFrame, SafeJoinStep]:
    warnings: list[str] = []
    before_rows = len(current)
    if rel.parent_table not in tables:
        step = SafeJoinStep(
            child_table=rel.child_table,
            child_column=rel.child_column,
            parent_table=rel.parent_table,
            parent_column=rel.parent_column,
            status="skipped_missing_parent_table",
            before_rows=before_rows,
            after_rows=before_rows,
            parent_rows=0,
            parent_rows_after_dedupe=0,
            parent_key_unique=False,
            matched_rows=0,
            match_rate=0.0,
            warnings=[f"Parent table '{rel.parent_table}' was not loaded."],
        )
        return current, step

    child_key = f"{rel.child_table}__{rel.child_column}"
    if child_key not in current.columns:
        step = SafeJoinStep(
            child_table=rel.child_table,
            child_column=rel.child_column,
            parent_table=rel.parent_table,
            parent_column=rel.parent_column,
            status="skipped_missing_child_column",
            before_rows=before_rows,
            after_rows=before_rows,
            parent_rows=len(tables[rel.parent_table]),
            parent_rows_after_dedupe=len(tables[rel.parent_table]),
            parent_key_unique=False,
            matched_rows=0,
            match_rate=0.0,
            warnings=[f"Child column '{child_key}' is absent from the current fact frame."],
        )
        return current, step

    parent = tables[rel.parent_table]
    if rel.parent_column not in parent.columns:
        step = SafeJoinStep(
            child_table=rel.child_table,
            child_column=rel.child_column,
            parent_table=rel.parent_table,
            parent_column=rel.parent_column,
            status="skipped_missing_parent_column",
            before_rows=before_rows,
            after_rows=before_rows,
            parent_rows=len(parent),
            parent_rows_after_dedupe=len(parent),
            parent_key_unique=False,
            matched_rows=0,
            match_rate=0.0,
            warnings=[f"Parent column '{rel.parent_table}.{rel.parent_column}' is absent."],
        )
        return current, step

    parent_prepared, _exact_removed, parent_key_unique, parent_warnings = _prepare_parent(parent, rel.parent_column)
    warnings.extend(parent_warnings)
    parent_keys = set(parent_prepared[_JOIN_KEY].dropna())
    left_key = f"{_JOIN_KEY}_{step_index}"
    current = current.copy()
    current[left_key] = _normalise_key(current[child_key])
    non_null_child = current[left_key].notna()
    matched_rows = int(current.loc[non_null_child, left_key].isin(parent_keys).sum())
    match_rate = round(matched_rows / int(non_null_child.sum()), 4) if int(non_null_child.sum()) else 0.0

    parent_prefix = f"{rel.parent_table}__via__{rel.child_column}"
    right = _prefix_frame(parent_prepared, parent_prefix)
    right_key = f"{parent_prefix}__{_JOIN_KEY}"
    parent_join_key = f"{parent_prefix}__{rel.parent_column}"
    before_columns = set(current.columns)
    joined = current.merge(right, how="left", left_on=left_key, right_on=right_key, sort=False)
    joined = joined.drop(columns=[left_key, right_key], errors="ignore")
    joined = joined.drop(columns=[parent_join_key], errors="ignore")

    after_rows = len(joined)
    status = "joined"
    if after_rows != before_rows:
        warnings.append(
            f"Unsafe fan-out detected: rows changed from {before_rows} to {after_rows}; reverting this join."
        )
        joined = current.drop(columns=[left_key], errors="ignore")
        after_rows = before_rows
        status = "reverted_fanout"

    added_columns = [
        column
        for column in joined.columns
        if column not in before_columns and column != left_key
    ]
    step = SafeJoinStep(
        child_table=rel.child_table,
        child_column=rel.child_column,
        parent_table=rel.parent_table,
        parent_column=rel.parent_column,
        status=status,
        before_rows=before_rows,
        after_rows=after_rows,
        parent_rows=len(parent),
        parent_rows_after_dedupe=len(parent_prepared),
        parent_key_unique=parent_key_unique,
        matched_rows=matched_rows,
        match_rate=match_rate,
        added_columns=added_columns,
        warnings=warnings,
    )
    return joined, step


def _numeric_feature_frame(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    numeric: dict[str, pd.Series] = {}
    excluded: list[str] = []
    for column in df.columns:
        if _is_identifier_column(column):
            excluded.append(f"{column}: identifier-like column excluded from correlation")
            continue
        null_rate = float(df[column].isna().mean()) if len(df) else 1.0
        if null_rate > 0.70:
            excluded.append(f"{column}: null_rate>{0.70:.2f} after safe join")
            continue
        if pt.is_numeric_dtype(df[column]):
            values = pd.to_numeric(df[column], errors="coerce")
        else:
            values = pd.to_numeric(df[column], errors="coerce")
            parse_rate = float(values.notna().mean()) if len(values) else 0.0
            if parse_rate < 0.80:
                excluded.append(f"{column}: non-numeric or parse_rate<0.80")
                continue
        if values.nunique(dropna=True) <= 1:
            excluded.append(f"{column}: constant or empty numeric feature")
            continue
        numeric[column] = values
    return pd.DataFrame(numeric), excluded


def _correlations(df: pd.DataFrame, limit: int = 25) -> list[CrossTableCorrelation]:
    numeric, _ = _numeric_feature_frame(df)
    records: list[CrossTableCorrelation] = []
    columns = list(numeric.columns)
    for left_index, left in enumerate(columns):
        for right in columns[left_index + 1:]:
            left_table = _source_table(left)
            right_table = _source_table(right)
            if left_table == right_table:
                continue
            pair = numeric[[left, right]].dropna()
            if len(pair) < 3:
                continue
            coefficient = pair[left].corr(pair[right], method="pearson")
            if pd.isna(coefficient):
                continue
            coefficient = round(float(coefficient), 4)
            records.append(CrossTableCorrelation(
                left_feature=left,
                right_feature=right,
                left_table=left_table,
                right_table=right_table,
                method="pearson",
                coefficient=coefficient,
                abs_coefficient=round(abs(coefficient), 4),
                n=int(len(pair)),
            ))
    records.sort(key=lambda item: (item.abs_coefficient, item.n), reverse=True)
    return records[:limit]


def run_cross_table_analysis(
    tables: dict[str, pd.DataFrame],
    relationships: list[RelationshipInfo],
    out_dir: str | Path | None = None,
    preview_limit: int = 1000,
) -> CrossTableAnalysis:
    warnings: list[str] = []
    fact_table = choose_fact_table(tables, relationships)
    if fact_table is None:
        return CrossTableAnalysis(status="skipped_no_tables", warnings=["No tables were loaded."])

    direct_relationships = [
        rel for rel in relationships
        if rel.child_table == fact_table and rel.parent_table in tables
    ]
    direct_relationships.sort(key=lambda rel: (rel.confidence, rel.parent_table, rel.child_column), reverse=True)
    if not direct_relationships:
        return CrossTableAnalysis(
            status="skipped_no_direct_relationships",
            fact_table=fact_table,
            denormalized_rows=len(tables[fact_table]),
            denormalized_columns=len(tables[fact_table].columns),
            analysis_rows=len(tables[fact_table]),
            warnings=[f"Fact table '{fact_table}' has no direct relationships to join."],
        )

    denormalized = _prefix_frame(tables[fact_table].copy(), fact_table)
    join_steps: list[SafeJoinStep] = []
    for index, rel in enumerate(direct_relationships):
        denormalized, step = _safe_join(denormalized, tables, rel, index)
        join_steps.append(step)
        warnings.extend(step.warnings)

    analysis_df = denormalized.drop_duplicates().reset_index(drop=True)
    exact_removed = len(denormalized) - len(analysis_df)
    if exact_removed:
        warnings.append(f"Removed {exact_removed} exact duplicate row(s) from denormalized analysis frame.")
    numeric_frame, excluded_columns = _numeric_feature_frame(analysis_df)
    correlations = _correlations(analysis_df)
    if numeric_frame.shape[1] < 2:
        warnings.append("Not enough numeric cross-table features for Pearson correlation.")
    if not correlations:
        warnings.append("No cross-table numeric correlations passed the MVP filters.")

    preview_path = None
    if out_dir is not None:
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        path = out / "cross_table_dataset_preview.csv"
        analysis_df.head(preview_limit).to_csv(path, index=False)
        preview_path = str(path)

    return CrossTableAnalysis(
        status="completed",
        fact_table=fact_table,
        denormalized_rows=len(denormalized),
        denormalized_columns=len(denormalized.columns),
        analysis_rows=len(analysis_df),
        exact_duplicate_rows_removed=exact_removed,
        join_steps=join_steps,
        correlations=correlations,
        excluded_columns=excluded_columns,
        warnings=warnings,
        preview_csv_path=preview_path,
    )
