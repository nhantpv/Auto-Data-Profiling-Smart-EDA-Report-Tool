import logging
import numpy as np
import pandas as pd
from typing import Dict, Any
from ontology.models import (
    DatasetMeta, ColumnStats, AnomalyRecord, DataQualityFindings, Severity,
)
from severity.missingness import detect_missingness

logger = logging.getLogger(__name__)


def _extract_column_stats(variables: Dict[str, Any], mechs: Dict[str, Any] | None = None) -> Dict[str, ColumnStats]:
    columns = {}
    for col_name, col_data in variables.items():
        col_type = col_data.get("type", "Unknown")
        type_map = {
            "Numeric": "Numeric", "Categorical": "Categorical",
            "Boolean": "Boolean", "DateTime": "DateTime",
            "Unsupported": "Unsupported",
        }
        simple_type = type_map.get(col_type, col_type)

        n_missing = col_data.get("n_missing", 0)
        p_missing = col_data.get("p_missing", 0.0)
        n_distinct = col_data.get("n_distinct", None)
        n_zeros = col_data.get("n_zeros", None)  # PATCH 2: numeric only; categorical = None

        extra = {}
        if simple_type == "Numeric":
            for key in ["mean", "std", "min", "max", "median", "skewness", "kurtosis"]:
                if key in col_data:
                    v = col_data[key]
                    extra[key] = round(v, 4) if isinstance(v, float) else v
        elif simple_type == "Categorical":
            if "imbalance" in col_data:
                extra["imbalance"] = round(col_data["imbalance"], 4)

        columns[col_name] = ColumnStats(
            type=simple_type,
            n_missing=int(n_missing),
            p_missing=float(p_missing),
            n_zeros=int(n_zeros) if n_zeros is not None else None,  # PATCH 2
            n_distinct=int(n_distinct) if n_distinct is not None else None,
            missingness_mechanism=(mechs or {}).get(col_name),
            additional_metrics=extra,
        )
    return columns


def build_data_quality_findings(
    file_name: str,
    df: pd.DataFrame,
    profile_result: dict,
    anomaly_result: dict,
) -> DataQualityFindings:
    table = profile_result.get("table", {})

    meta = DatasetMeta(
        file_name=file_name,
        n=int(table.get("n", len(df))),
        n_var=int(table.get("n_var", len(df.columns))),
        memory_size=int(table.get("memory_size", 0)),
        p_cells_missing=float(table.get("p_cells_missing", 0.0)),
        n_duplicates=int(table.get("n_duplicates", 0)),
        p_duplicates=float(table.get("p_duplicates", 0.0)),
    )

    mechs = detect_missingness(df)
    columns = _extract_column_stats(profile_result.get("variables", {}), mechs=mechs)

    anomalies = []

    # Outlier record
    if not anomaly_result.get("skipped", True) and anomaly_result.get("n_outliers", 0) > 0:
        outlier_indices = anomaly_result["outlier_indices"]
        outlier_scores = anomaly_result["anomaly_scores"]
        n_outliers = anomaly_result["n_outliers"]

        top_k = min(10, n_outliers)
        top_samples = []
        for idx, score in zip(outlier_indices[:top_k], outlier_scores[:top_k]):
            row = df.iloc[idx].to_dict()
            row["_anomaly_score"] = score
            row["_row_index"] = int(idx)
            top_samples.append(row)

        ratio = n_outliers / meta.n
        anomalies.append(AnomalyRecord(
            issue_type="OUTLIER_ENSEMBLE",
            description=f"Phát hiện {n_outliers} dòng dị biệt ({ratio*100:.1f}% data)",
            severity=Severity.HIGH if ratio > 0.05 else Severity.WARN,
            dq_dimensions=["Accuracy"],
            ml_impact=["training_bias"] if ratio > 0.05 else [],
            confidence=round(float(np.mean(outlier_scores)), 4) if outlier_scores else None,
            affected_count=n_outliers,
            affected_percent=round(ratio, 4),
            top_10_samples=top_samples,
        ))

    # Duplicate record
    if meta.n_duplicates > 0:
        dup_df = df[df.duplicated(keep=False)]
        dup_samples = dup_df.head(10).to_dict(orient="records")
        anomalies.append(AnomalyRecord(
            issue_type="DUPLICATE",
            description=f"Phát hiện {meta.n_duplicates} dòng trùng lặp ({meta.p_duplicates*100:.1f}% data)",
            severity=Severity.WARN if meta.p_duplicates < 0.05 else Severity.HIGH,
            dq_dimensions=["Uniqueness"],
            ml_impact=["training_bias"] if meta.p_duplicates > 0.05 else [],
            affected_count=meta.n_duplicates,
            affected_percent=meta.p_duplicates,
            top_10_samples=dup_samples,
        ))

    return DataQualityFindings(
        dataset_meta=meta,
        columns=columns,
        anomalies=anomalies,
    )
