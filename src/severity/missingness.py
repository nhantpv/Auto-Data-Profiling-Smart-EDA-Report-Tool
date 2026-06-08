"""Missingness mechanism classification: MCAR / MAR / MNAR? (heuristic).

Thresholds are tunable constants — do not hardcode downstream.
MNAR? is tentative only: MNAR cannot be confirmed from observed data alone.
Little's test is an indicator, not a verdict (pyampute docs caveat).
"""
import logging
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score

logger = logging.getLogger(__name__)

_MAR_AUC_GATE = 0.65   # logistic CV-AUC above which we label a column MAR
_MCAR_ALPHA   = 0.05   # significance level for Little's MCAR test
_MAX_MISSINGNESS_ROWS = 10_000
_SAMPLE_RANDOM_STATE = 42


# ── Little's MCAR test ────────────────────────────────────────────────────────

def little_mcar_pvalue(df_numeric: pd.DataFrame) -> float | None:
    """Run Little's MCAR test on a numeric DataFrame.

    Returns p-value (float) or None if test cannot be run (errors, <2 columns,
    collinear covariance, no missing values that form usable patterns).
    """
    numeric = df_numeric.select_dtypes(include="number")
    if numeric.shape[1] < 2:
        return None
    if numeric.isna().sum().sum() == 0:
        return None
    try:
        from pyampute.exploration.mcar_statistical_tests import MCARTest
        p = MCARTest(method="little").little_mcar_test(numeric)
        return float(p)
    except Exception as exc:
        logger.debug("Little's MCAR test failed: %s", exc)
        return None


# ── MAR heuristic (logistic CV-AUC) ─────────────────────────────────────────

def mar_auc(df: pd.DataFrame, col: str) -> float | None:
    """Predict is_missing(col) from other numeric columns via logistic regression CV.

    Returns mean CV-AUC or None when:
    - fewer than 10 missing values in col
    - no numeric predictor columns available
    - y is single-class (all missing or all present)
    - any other error
    """
    series = df[col]
    n_missing = int(series.isna().sum())
    if n_missing < 10:
        return None

    y = series.isna().astype(int).values
    if len(np.unique(y)) < 2:
        return None

    # Predictors: numeric columns OTHER than col, filled with median
    predictors = df.select_dtypes(include="number").drop(columns=[col], errors="ignore")
    if predictors.shape[1] == 0:
        return None

    X = predictors.fillna(predictors.median()).values
    try:
        clf = LogisticRegression(max_iter=200, random_state=42)
        scores = cross_val_score(clf, X, y, cv=3, scoring="roc_auc")
        return float(np.mean(scores))
    except Exception as exc:
        logger.debug("mar_auc failed for column '%s': %s", col, exc)
        return None


# ── Classification logic ──────────────────────────────────────────────────────

def classify_missingness(
    col_missing: int,
    mcar_p: float | None,
    auc: float | None,
) -> str | None:
    """Map (col_missing, mcar_p, auc) → mechanism label.

    Priority:
    1. 0 missing → None
    2. auc > _MAR_AUC_GATE → "MAR"
    3. mcar_p >= _MCAR_ALPHA → "MCAR"
    4. mcar_p < _MCAR_ALPHA → "MNAR?"  (tentative — cannot confirm from data)
    5. else → None
    """
    if col_missing == 0:
        return None
    if auc is not None and auc > _MAR_AUC_GATE:
        return "MAR"
    if mcar_p is not None and mcar_p >= _MCAR_ALPHA:
        return "MCAR"
    if mcar_p is not None and mcar_p < _MCAR_ALPHA:
        return "MNAR?"
    return None


# ── Dataset-level entry point ─────────────────────────────────────────────────

def sample_missingness_frame(
    df: pd.DataFrame,
    max_rows: int = _MAX_MISSINGNESS_ROWS,
    random_state: int = _SAMPLE_RANDOM_STATE,
) -> pd.DataFrame:
    """Cap missingness diagnostics to max_rows while preserving missing rows.

    Large datasets can make Little's MCAR test and logistic CV expensive. We keep
    all rows with any missing value when they fit the cap, then fill the
    remaining budget with a deterministic sample of complete rows.
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


def detect_missingness(df: pd.DataFrame, max_rows: int = _MAX_MISSINGNESS_ROWS) -> dict:
    """Run one Little's test (dataset-level) then per-column MAR AUC.

    Returns {col_name: mechanism} only for columns that have missing values.
    Columns with no missing are omitted from the result.
    """
    missing_cols = [c for c in df.columns if df[c].isna().any()]
    if not missing_cols:
        return {}

    sampled_df = sample_missingness_frame(df, max_rows=max_rows)
    numeric_df = sampled_df.select_dtypes(include="number")
    mcar_p = little_mcar_pvalue(numeric_df)

    result = {}
    for col in missing_cols:
        n_missing = int(sampled_df[col].isna().sum()) if col in sampled_df.columns else 0
        auc = mar_auc(sampled_df, col) if col in numeric_df.columns else None
        mech = classify_missingness(n_missing, mcar_p, auc)
        result[col] = mech
    return result
