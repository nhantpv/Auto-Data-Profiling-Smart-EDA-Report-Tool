"""Missingness mechanism classification: MCAR_CONSISTENT / MAR (per-column).

Thresholds are tunable constants — do not hardcode downstream.
QĐ-6a (ARCHITECT v5.4 §Mục 10): "MNAR?" is retired — cannot confirm from
observed data alone.  Only MCAR_CONSISTENT, MAR, and INDETERMINATE are
emitted.

Per-column (H5 fix): each target column gets its own AUC score against all
other numeric columns, yielding an independent mechanism label.
"""
import logging
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

logger = logging.getLogger(__name__)

_MAR_AUC_GATE = 0.70   # AUC above which we label a column MAR (ARCHITECT v5.4)
_MAX_MISSINGNESS_ROWS = 10_000
_SAMPLE_RANDOM_STATE = 42


# ── MAR heuristic (logistic CV-AUC, per-column) ─────────────────────────────

def mar_auc(df: pd.DataFrame, col: str) -> float | None:
    """Predict is_missing(col) from other numeric columns via logistic regression CV.

    Returns mean CV-AUC or None when:
    - fewer than 10 missing values in col
    - no numeric predictor columns available
    - y is single-class (all missing or all present)
    - any other error
    """
    series = df[col]
    n_missing = series.isna().sum()
    if n_missing < 10:
        return None

    y = series.isna().astype(int).to_numpy()
    if y.min() == y.max():
        return None

    # Predictors: numeric columns OTHER than col, filled with median
    predictors = df.select_dtypes(include="number").drop(columns=[col], errors="ignore")
    if predictors.shape[1] == 0:
        return None

    X = predictors.fillna(predictors.median()).values
    try:
        clf = LogisticRegression(max_iter=200, random_state=42)
        scores = cross_val_score(clf, X, y, cv=3, scoring="roc_auc")
        return float(scores.mean())
    except Exception as exc:
        logger.debug("mar_auc failed for column '%s': %s", col, exc)
        return None


# ── Per-column classification (H5 fix) ───────────────────────────────────────

def classify_missingness_per_column(
    col_missing: int,
    auc: float | None,
) -> str | None:
    """Map (col_missing, auc) → mechanism label (per-column, no MNAR).

    Rules (ARCHITECT v5.4 §5.4 L2.5, QĐ-6a):
        1. 0 missing → None
        2. auc > _MAR_AUC_GATE → "MAR"
        3. auc is computable and ≤ gate → "MCAR_CONSISTENT"
        4. auc not computable (< 10 missing, no numeric predictors) → "INDETERMINATE"
    """
    if col_missing == 0:
        return None
    if auc is not None and auc > _MAR_AUC_GATE:
        return "MAR"
    if auc is not None:
        return "MCAR_CONSISTENT"
    return "INDETERMINATE"


# ── Sampling helper ──────────────────────────────────────────────────────────

def sample_missingness_frame(
    df: pd.DataFrame,
    max_rows: int = _MAX_MISSINGNESS_ROWS,
    random_state: int = _SAMPLE_RANDOM_STATE,
) -> pd.DataFrame:
    """Cap missingness diagnostics to max_rows while preserving missing rows.

    Large datasets can make logistic CV expensive.  We keep all rows with any
    missing value when they fit the cap, then fill the remaining budget with a
    deterministic sample of complete rows.
    """
    if len(df) <= max_rows:
        return df

    missing_mask = df.isna().any(axis=1)
    missing_rows = df.loc[missing_mask]
    if len(missing_rows) >= max_rows:
        return missing_rows.sample(n=max_rows, random_state=random_state).sort_index()

    complete_rows = df.loc[~missing_mask]
    remaining = max_rows - len(missing_rows)
    sampled_complete = complete_rows.sample(n=remaining, random_state=random_state)
    return pd.concat([missing_rows, sampled_complete]).sort_index()


# ── Dataset-level entry point ─────────────────────────────────────────────────

def detect_missingness(df: pd.DataFrame, max_rows: int = _MAX_MISSINGNESS_ROWS) -> dict[str, str | None]:
    """Per-column missingness classification via AUC (H5 fix).

    Each column with missing values gets an independent logistic-regression AUC
    against all other numeric columns.  The AUC determines whether missingness
    is MAR (predictable from other columns) or MCAR_CONSISTENT (random).

    Returns ``{col_name: mechanism}`` only for columns that have missing values.
    Columns with no missing are omitted from the result.
    """
    missing_cols = [c for c in df.columns if df[c].isna().any()]
    if not missing_cols:
        return {}

    sampled_df = sample_missingness_frame(df, max_rows=max_rows)

    result: dict[str, str | None] = {}
    for col in missing_cols:
        n_missing = sampled_df[col].isna().sum() if col in sampled_df.columns else 0
        auc = mar_auc(sampled_df, col) if col in sampled_df.columns else None
        mech = classify_missingness_per_column(n_missing, auc)
        result[col] = mech
    return result
