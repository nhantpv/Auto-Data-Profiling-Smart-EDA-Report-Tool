import logging
import numpy as np
import pandas as pd
from pyod.models.iforest import IForest
from pyod.models.ecod import ECOD
from pyod.models.lof import LOF

logger = logging.getLogger(__name__)

_CONTAMINATION = 0.05
_DEFAULT_Z_GATE = 3.0  # ensemble z-gate; comfortable margin on both fixtures (verified)


def _zscore(scores: np.ndarray) -> np.ndarray:
    """Standardize to z-scores. Constant input -> zeros."""
    std = scores.std()
    if std == 0:
        return np.zeros_like(scores, dtype=float)
    return (scores - scores.mean()) / std


def run_anomaly_detection(
    df: pd.DataFrame,
    contamination: float = _CONTAMINATION,
    z_gate: float = _DEFAULT_Z_GATE,
) -> dict:
    numeric_df = df.select_dtypes(include="number")

    if numeric_df.shape[1] == 0:
        logger.warning("No numeric columns found. Skipping anomaly detection.")
        return {
            "outlier_indices": [],
            "anomaly_scores": [],
            "all_scores": [],
            "n_outliers": 0,
            "numeric_columns_used": [],
            "skipped": True,
        }

    non_constant = numeric_df.loc[:, numeric_df.nunique() > 1]
    if non_constant.shape[1] == 0:
        return {
            "outlier_indices": [], "anomaly_scores": [], "all_scores": [],
            "n_outliers": 0, "numeric_columns_used": [], "skipped": True,
        }

    clean_df = non_constant.dropna()
    clean_indices = clean_df.index.tolist()
    X = clean_df.values

    if len(X) < 3:
        return {
            "outlier_indices": [], "anomaly_scores": [], "all_scores": [],
            "n_outliers": 0, "numeric_columns_used": list(non_constant.columns),
            "skipped": True,
        }

    n_samples = len(X)
    lof_neighbors = min(20, n_samples - 1)

    models = [
        ("IForest", IForest(contamination=contamination, random_state=42)),
        ("ECOD", ECOD(contamination=contamination)),
        ("LOF", LOF(n_neighbors=lof_neighbors, contamination=contamination)),
    ]

    raw_scores = []
    for name, model in models:
        try:
            model.fit(X)
            raw_scores.append(model.decision_scores_)
        except Exception as e:
            logger.warning("%s failed: %s. Skipping this detector.", name, e)

    if len(raw_scores) == 0:
        return {
            "outlier_indices": [], "anomaly_scores": [], "all_scores": [],
            "n_outliers": 0, "numeric_columns_used": list(non_constant.columns),
            "skipped": True,
        }

    # Maximization combiner: robust to LOF sign-inversion on small n
    ensemble_z = np.max([_zscore(s) for s in raw_scores], axis=0)
    outlier_mask = ensemble_z >= z_gate
    display = 1.0 / (1.0 + np.exp(-ensemble_z))

    outlier_positions = np.where(outlier_mask)[0]
    outlier_original_indices = [clean_indices[i] for i in outlier_positions]
    outlier_scores = [round(float(display[i]), 4) for i in outlier_positions]

    sorted_pairs = sorted(zip(outlier_original_indices, outlier_scores), key=lambda x: -x[1])
    sorted_indices = [p[0] for p in sorted_pairs]
    sorted_scores = [p[1] for p in sorted_pairs]

    return {
        "outlier_indices": sorted_indices,
        "anomaly_scores": sorted_scores,
        "all_scores": [round(float(s), 4) for s in display],
        "n_outliers": len(sorted_indices),
        "numeric_columns_used": list(non_constant.columns),
        "skipped": False,
    }
