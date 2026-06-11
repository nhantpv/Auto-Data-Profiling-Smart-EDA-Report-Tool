from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
import urllib.error
import urllib.request
from typing import Any, Iterable

import pandas as pd
import pandas.api.types as pt

from ontology.models import (
    CorrelationPairPlan,
    CrossTableAnalysis,
    CrossTableCorrelation,
    LlmCorrelationPlan,
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


def _columns_for_table(meta: Any) -> set[str]:
    if isinstance(meta, pd.DataFrame):
        return {str(column) for column in meta.columns}
    if isinstance(meta, dict):
        columns = meta.get("columns", [])
        if isinstance(columns, dict):
            return {str(column) for column in columns}
        if isinstance(columns, list):
            result: set[str] = set()
            for column in columns:
                if isinstance(column, dict) and "name" in column:
                    result.add(str(column["name"]))
                else:
                    result.add(str(column))
            return result
    if isinstance(meta, (list, tuple, set)):
        return {str(column) for column in meta}
    return set()


def _relationship_exists(pair: CorrelationPairPlan, relationships: Iterable[RelationshipInfo]) -> bool:
    for rel in relationships:
        if (
            rel.parent_table == pair.parent_table
            and rel.parent_column == pair.parent_column
            and rel.child_table == pair.child_table
            and rel.child_column == pair.child_column
        ):
            return True
    return False


def validate_llm_plan(
    plan: dict[str, Any] | LlmCorrelationPlan,
    tables_meta: dict[str, Any],
    relationships: Iterable[RelationshipInfo],
) -> LlmCorrelationPlan:
    """Validate LLM Phase-1 output before any correlation is computed.

    The validator rejects unknown tables/columns, unsupported aggregate
    methods, and relationship pairs that do not exist in the deterministic
    schema graph.
    """
    raw = plan.model_dump(mode="json") if isinstance(plan, LlmCorrelationPlan) else plan
    valid_pairs: list[CorrelationPairPlan] = []
    skipped: list[dict[str, Any]] = list(raw.get("skipped_pairs", []))
    allowed_methods = {"mean", "sum", "count", "min", "max", "median"}
    table_columns = {
        table: _columns_for_table(meta)
        for table, meta in tables_meta.items()
    }

    for index, item in enumerate(raw.get("correlation_pairs", [])):
        try:
            pair = CorrelationPairPlan.model_validate(item)
        except Exception as exc:
            skipped.append({"index": index, "reason": f"invalid_pair_shape: {exc}"})
            continue

        reasons: list[str] = []
        if pair.parent_table not in table_columns:
            reasons.append(f"unknown_parent_table:{pair.parent_table}")
        if pair.child_table not in table_columns:
            reasons.append(f"unknown_child_table:{pair.child_table}")
        if pair.parent_table in table_columns and pair.parent_column not in table_columns[pair.parent_table]:
            reasons.append(f"unknown_parent_column:{pair.parent_table}.{pair.parent_column}")
        if pair.child_table in table_columns and pair.child_column not in table_columns[pair.child_table]:
            reasons.append(f"unknown_child_column:{pair.child_table}.{pair.child_column}")
        if pair.aggregate_method not in allowed_methods:
            reasons.append(f"unsupported_aggregate:{pair.aggregate_method}")
        if not _relationship_exists(pair, relationships):
            reasons.append("relationship_not_in_schema_graph")

        if reasons:
            skipped.append({"index": index, "pair": pair.model_dump(mode="json"), "reasons": reasons})
            continue
        valid_pairs.append(pair)

    return LlmCorrelationPlan(
        correlation_pairs=valid_pairs,
        skipped_pairs=skipped,
        model=str(raw.get("model", "")),
        temperature=float(raw.get("temperature", 0.0)),
        seed=int(raw.get("seed", 42)),
    )


def _extract_openai_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    parts: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts).strip()


def _call_openai_plan(prompt: str) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    model = os.getenv("SMART_EDA_L3B_MODEL", "gpt-4o-mini")
    request_body = {
        "model": model,
        "instructions": (
            "Return JSON only. Select only statistically meaningful cross-table "
            "correlation pairs from the deterministic schema evidence. Do not invent tables or columns."
        ),
        "input": prompt,
        "max_output_tokens": 900,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI correlation planner failed: HTTP {exc.code} {body}") from exc
    text = _extract_openai_text(payload)
    if not text:
        raise RuntimeError("OpenAI correlation planner returned empty text")
    return json.loads(text)


async def llm_plan_correlations(
    tables_meta: dict[str, Any],
    relationships: list[RelationshipInfo],
) -> LlmCorrelationPlan:
    """Phase 1: optional LLM planner, always validated before use."""
    if os.getenv("SMART_EDA_L3B_PROVIDER", "deterministic").strip().lower() != "openai":
        return LlmCorrelationPlan(
            correlation_pairs=[],
            skipped_pairs=[{"reason": "SMART_EDA_L3B_PROVIDER is not openai"}],
            model="deterministic",
        )

    prompt = json.dumps(
        {
            "tables_meta": {
                table: sorted(_columns_for_table(meta))
                for table, meta in tables_meta.items()
            },
            "relationships": [rel.model_dump(mode="json") for rel in relationships],
            "required_shape": {
                "correlation_pairs": [
                    {
                        "parent_table": "table_name",
                        "parent_column": "column_name",
                        "child_table": "table_name",
                        "child_column": "column_name",
                        "aggregate_method": "mean|sum|count|min|max|median",
                        "reasoning": "short evidence",
                        "confidence": "high|medium|low",
                    }
                ],
                "skipped_pairs": [],
                "model": os.getenv("SMART_EDA_L3B_MODEL", "gpt-4o-mini"),
                "temperature": 0.0,
                "seed": 42,
            },
        },
        ensure_ascii=False,
        indent=2,
    )
    try:
        raw_plan = await asyncio.to_thread(_call_openai_plan, prompt)
    except Exception as exc:
        return LlmCorrelationPlan(
            correlation_pairs=[],
            skipped_pairs=[{"reason": f"planner_failed:{exc}"}],
            model=os.getenv("SMART_EDA_L3B_MODEL", "gpt-4o-mini"),
        )
    return validate_llm_plan(raw_plan, tables_meta, relationships)


def compute_planned_correlations(
    tables: dict[str, pd.DataFrame],
    plan: LlmCorrelationPlan,
    limit: int = 25,
) -> list[CrossTableCorrelation]:
    """Phase 2: compute validated LLM-selected numeric correlations.

    MVP implementation is conservative: it computes Pearson only when both
    selected columns are numeric/parseable and there are at least 3 row-aligned
    observations. Unsafe joins are left to ``run_cross_table_analysis``.
    """
    records: list[CrossTableCorrelation] = []
    for pair in plan.correlation_pairs:
        parent = tables.get(pair.parent_table)
        child = tables.get(pair.child_table)
        if parent is None or child is None:
            continue
        if pair.parent_column not in parent.columns or pair.child_column not in child.columns:
            continue
        left = pd.to_numeric(parent[pair.parent_column], errors="coerce").reset_index(drop=True)
        right = pd.to_numeric(child[pair.child_column], errors="coerce").reset_index(drop=True)
        n = min(len(left), len(right))
        if n < 3:
            continue
        frame = pd.DataFrame({
            "left": left.iloc[:n],
            "right": right.iloc[:n],
        }).dropna()
        if len(frame) < 3 or frame["left"].nunique() <= 1 or frame["right"].nunique() <= 1:
            continue
        coefficient = frame["left"].corr(frame["right"], method="pearson")
        if pd.isna(coefficient):
            continue
        coefficient = round(float(coefficient), 4)
        records.append(CrossTableCorrelation(
            left_feature=f"{pair.parent_table}.{pair.parent_column}",
            right_feature=f"{pair.child_table}.{pair.child_column}",
            left_table=pair.parent_table,
            right_table=pair.child_table,
            method=f"pearson_row_aligned_{pair.aggregate_method}",
            coefficient=coefficient,
            abs_coefficient=round(abs(coefficient), 4),
            n=int(len(frame)),
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
        and rel.decision in {"accepted_for_safe_join", "declared_relationship"}
        and rel.confidence_bucket in {"HIGH_CONFIDENCE", "DECLARED"}
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
