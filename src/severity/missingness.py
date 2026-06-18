"""Missingness mechanism classification: MCAR_CONSISTENT / MAR / STRUCTURAL_ABSENT (per-column).

Thresholds are tunable constants — do not hardcode downstream.
QĐ-6a (ARCHITECT v5.4 §Mục 10): "MNAR?" is retired — cannot confirm from
observed data alone.  Only MCAR_CONSISTENT, MAR, INDETERMINATE, and
STRUCTURAL_ABSENT are emitted.

STRUCTURAL_ABSENT (added post-QĐ-6a): An optional field where NULL means
"not applicable" rather than "data is missing".  Detected heuristically by:
  - missing rate > STRUCTURAL_ABSENT_THRESHOLD (default 70%)
  - column is optional in schema (not pk, not not_null)
This label does NOT imply MNAR; it is a practical "do not impute" signal.

Per-column (H5 fix): each target column gets its own AUC score against all
other numeric columns, yielding an independent mechanism label.
"""
import logging
import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import cross_val_score
from config.threshold_registry import ThresholdRegistry

logger = logging.getLogger(__name__)

_THRESHOLDS = ThresholdRegistry()
_MAR_AUC_GATE = _THRESHOLDS.get("mar_auc_gate")
_MCAR_ALPHA = _THRESHOLDS.get("mcar_alpha")
_MAX_MISSINGNESS_ROWS = 10_000
_SAMPLE_RANDOM_STATE = 42

# Columns with missing_rate > this threshold AND optional schema declaration
# will be labelled STRUCTURAL_ABSENT (do not recommend imputation).
_STRUCTURAL_ABSENT_THRESHOLD = 0.70


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


def little_mcar_pvalue(df: pd.DataFrame) -> float | None:
    """Optional diagnostic placeholder for legacy callers.

    ARCHITECT v5.4 retired dataset-level Little's test as a decision driver
    because a single p-value cannot be broadcast safely to every column.
    """
    numeric = df.select_dtypes(include="number")
    if numeric.shape[1] < 2 or not numeric.isna().any().any():
        return None
    return None


# ── Per-column classification (H5 fix) ───────────────────────────────────────

def classify_missingness_per_column(
    col_missing: int,
    auc: float | None,
    total_rows: int = 0,
    schema_meta: dict | None = None,
) -> str | None:
    """Map (col_missing, auc) → mechanism label (per-column).

    Rules (ARCHITECT v5.4 §5.4 L2.5, QĐ-6a + STRUCTURAL_ABSENT extension):
        1. 0 missing → None
        2. optional column AND missing_rate > 70% → "STRUCTURAL_ABSENT"
           (NULL likely means 'not applicable'; do not impute)
        3. auc > _MAR_AUC_GATE → "MAR"
        4. auc is computable and ≤ gate → "MCAR_CONSISTENT"
        5. auc not computable (< 10 missing, no numeric predictors) → "INDETERMINATE"

    Args:
        col_missing: Number of missing values in this column.
        auc: CV-AUC from mar_auc(), or None if not computable.
        total_rows: Total rows in the table (needed for miss rate calculation).
        schema_meta: Column metadata dict from parsed schema
                     (keys: "pk", "not_null", "unique").  Pass None if no schema.
    """
    if col_missing == 0:
        return None

    # STRUCTURAL_ABSENT heuristic: optional field with very high missing rate
    if total_rows > 0 and schema_meta is not None:
        miss_rate = col_missing / total_rows
        is_optional = (
            not schema_meta.get("pk", False)
            and not schema_meta.get("not_null", False)
            and not schema_meta.get("composite_pk_member", False)
        )
        if miss_rate > _STRUCTURAL_ABSENT_THRESHOLD and is_optional:
            return "STRUCTURAL_ABSENT"

    # Fallback: column-name keyword heuristic when schema not available
    # These column names are commonly structurally optional across enterprise datasets
    _OPTIONAL_COL_KEYWORDS = {
        "fax", "company", "phone2", "mobile2", "suffix", "prefix",
        "middle_name", "middlename", "address2", "address3", "apt",
        "suite", "extension", "ext", "website", "url", "linkedin",
        "twitter", "note", "comment", "remark", "description2",
        "alternate_email", "secondary_email", "nickname", "alias",
    }
    if total_rows > 0:
        miss_rate = col_missing / total_rows
        # Extract column name from schema_meta or pass-through heuristic
        # We detect via col_name_hint if provided; caller must pass it
        # (This block activates only if schema_meta was None — no override)
        if schema_meta is None and miss_rate > _STRUCTURAL_ABSENT_THRESHOLD:
            # Check will be done by caller passing col_name_hint — see detect_missingness
            pass  # handled in detect_missingness with _col_name parameter

    if auc is not None and auc > _MAR_AUC_GATE:
        return "MAR"
    if auc is not None:
        return "MCAR_CONSISTENT"
    return "INDETERMINATE"



def classify_missingness(
    col_missing: int,
    mcar_pvalue: float | None,
    auc: float | None,
) -> str | None:
    """Legacy signature; classification now ignores dataset-level MCAR p-value."""
    return classify_missingness_per_column(col_missing, auc)


# ── Sampling helper ──────────────────────────────────────────────────────────

def sample_missingness_frame(
    df: pd.DataFrame,
    max_rows: int = _MAX_MISSINGNESS_ROWS,
    random_state: int = _SAMPLE_RANDOM_STATE,
) -> pd.DataFrame:
    """Deprecated compatibility helper.

    ARCHITECT v5.4 requires full-data missingness diagnostics.  Keep the
    function for older imports, but return the original frame unchanged.
    """
    return df


# ── Dataset-level entry point ─────────────────────────────────────────────────

def detect_missingness(
    df: pd.DataFrame,
    max_rows: int = _MAX_MISSINGNESS_ROWS,
    schema_cols: dict | None = None,
) -> dict[str, str | None]:
    """Per-column missingness classification via AUC (H5 fix).

    Each column with missing values gets an independent logistic-regression AUC
    against all other numeric columns.  The AUC determines whether missingness
    is MAR (predictable from other columns) or MCAR_CONSISTENT (random).

    Columns marked STRUCTURAL_ABSENT have > 70% missing AND are declared
    optional in the schema — they should NOT be imputed.

    Args:
        df: The table DataFrame.
        max_rows: Unused (kept for API compat); full data is always used.
        schema_cols: Column metadata from parsed DBML schema dict
                     {col_name: {"pk": bool, "not_null": bool, ...}}.
                     Pass None if no schema available.

    Returns ``{col_name: mechanism}`` only for columns that have missing values.
    Columns with no missing are omitted from the result.
    """
    missing_cols = [c for c in df.columns if df[c].isna().any()]
    if not missing_cols:
        return {}

    total_rows = len(df)
    # Known optional column name keywords (schema-free fallback for STRUCTURAL_ABSENT)
    _OPTIONAL_NAME_KEYWORDS = {
        "fax", "company", "phone2", "mobile2", "suffix", "prefix",
        "middlename", "middle_name", "address2", "address3", "apt",
        "suite", "extension", "website", "url", "linkedin", "twitter",
        "note", "comment", "remark", "nickname", "alias",
        "alternate_email", "secondary_email",
    }

    result: dict[str, str | None] = {}
    for col in missing_cols:
        n_missing = int(df[col].isna().sum()) if col in df.columns else 0
        auc = mar_auc(df, col) if col in df.columns else None
        col_schema_meta = (schema_cols or {}).get(col)
        mech = classify_missingness_per_column(n_missing, auc, total_rows, col_schema_meta)

        # Column-name keyword fallback: when no schema AND >70% missing AND known optional name
        if mech != "STRUCTURAL_ABSENT" and col_schema_meta is None and total_rows > 0:
            _miss_rate = n_missing / total_rows
            _col_lower = col.lower().replace(" ", "_")
            _is_known_optional = any(_kw in _col_lower for _kw in _OPTIONAL_NAME_KEYWORDS)
            if _miss_rate > _STRUCTURAL_ABSENT_THRESHOLD and _is_known_optional:
                mech = "STRUCTURAL_ABSENT"

        result[col] = mech
    return result


