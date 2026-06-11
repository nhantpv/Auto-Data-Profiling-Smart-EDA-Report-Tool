"""Build DataQualityFindings from profiling + anomaly detection results.

Integrates FindingRegistry for dedup/ID assignment and ThresholdRegistry
for config-driven threshold references (ARCHITECT v5.4 §L3).
"""
import logging
import numpy as np
import pandas as pd
from typing import Dict, Any
from pathlib import Path
from ontology.models import (
    DatasetMeta, ColumnStats, AnomalyRecord, DataQualityFindings, Provenance, Severity,
)
from ontology.finding_registry import FindingRegistry
from config.threshold_registry import ThresholdRegistry
from severity.missingness import detect_missingness
from severity.calibrator import load_calibrator_table

logger = logging.getLogger(__name__)

# Module-level singletons (lazy-init)
_threshold_registry: ThresholdRegistry | None = None


def _get_threshold_registry() -> ThresholdRegistry:
    """Lazy singleton for ThresholdRegistry."""
    global _threshold_registry
    if _threshold_registry is None:
        _threshold_registry = ThresholdRegistry()
    return _threshold_registry


def _safe_artifact_stem(name: str) -> str:
    stem = Path(name).stem or "dataset"
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in stem)
    return safe.strip("_") or "dataset"


def _write_csv_artifact(df: pd.DataFrame, artifact_dir: str | Path | None, file_name: str) -> str | None:
    if artifact_dir is None:
        return None
    out = Path(artifact_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / file_name
    df.to_csv(path, index=False)
    return str(path)


def _outlier_rows(
    df: pd.DataFrame,
    anomaly_result: dict,
    max_samples: int | None = None,
) -> pd.DataFrame:
    scores = anomaly_result.get("anomaly_scores", [])
    positions = anomaly_result.get("outlier_positions")
    labels = anomaly_result.get("outlier_indices", [])

    if positions is not None:
        rows = df.iloc[list(positions)]
        row_positions = list(positions)
        row_labels = labels
    else:
        rows = df.loc[list(labels)]
        row_positions = [df.index.get_loc(label) for label in labels]
        row_labels = labels

    if max_samples is not None:
        rows = rows.head(max_samples)
        row_positions = row_positions[:max_samples]
        row_labels = row_labels[:max_samples]
        scores = scores[:max_samples]

    exported = rows.copy()
    exported["_anomaly_score"] = list(scores)[:len(exported)]
    exported["_row_index"] = row_labels[:len(exported)]
    exported["_row_position"] = row_positions[:len(exported)]
    return exported


def _threshold_severity(value: float, thresholds: list, fallback: Severity = Severity.WARN) -> Severity:
    """Lookup severity from calibrator thresholds. Falls back if no thresholds."""
    if not thresholds:
        return fallback
    for entry in thresholds:
        if value < entry["max"]:
            return Severity(entry["severity"])
    return Severity.CRITICAL


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
        n_zeros = col_data.get("n_zeros", None)

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
            n_zeros=int(n_zeros) if n_zeros is not None else None,
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
    mechs: dict | None = None,
    artifact_dir: str | Path | None = None,
    artifact_prefix: str | None = None,
) -> DataQualityFindings:
    """Build DataQualityFindings with FindingRegistry integration.

    All anomalies are registered in a FindingRegistry which:
    - Assigns deterministic ``finding_id``
    - Deduplicates by ID (keeps higher severity)
    - Attaches ``threshold_ref`` for config-driven thresholds
    - Sets ``provenance`` to OBSERVED (directly measured from data)
    """
    table = profile_result.get("table", {})
    sampling = df.attrs.get("sampling", {})

    meta = DatasetMeta(
        file_name=file_name,
        n=int(table.get("n", len(df))),
        n_var=int(table.get("n_var", len(df.columns))),
        memory_size=int(table.get("memory_size", 0)),
        p_cells_missing=float(table.get("p_cells_missing", 0.0)),
        n_duplicates=int(table.get("n_duplicates", 0)),
        p_duplicates=float(table.get("p_duplicates", 0.0)),
        is_sampled=bool(sampling.get("is_sampled", False)),
        original_n=sampling.get("original_n"),
        sample_n=sampling.get("sample_n"),
        sample_method=sampling.get("sample_method"),
        sample_seed=sampling.get("sample_seed"),
    )

    if mechs is None:
        mechs = detect_missingness(df)
    columns = _extract_column_stats(profile_result.get("variables", {}), mechs=mechs)

    cal_table = load_calibrator_table()
    registry = FindingRegistry()
    threshold_reg = _get_threshold_registry()

    anomalies: list[AnomalyRecord] = []
    artifact_stem = artifact_prefix or _safe_artifact_stem(file_name)

    # Outlier record
    if not anomaly_result.get("skipped", True) and anomaly_result.get("n_outliers", 0) > 0:
        outlier_scores = anomaly_result["anomaly_scores"]
        n_outliers = anomaly_result["n_outliers"]

        full_outlier_rows = _outlier_rows(df, anomaly_result)
        top_samples = _outlier_rows(df, anomaly_result, max_samples=10).to_dict(orient="records")
        outlier_export = _write_csv_artifact(
            full_outlier_rows,
            artifact_dir,
            f"{artifact_stem}__outlier_rows.csv",
        )

        ratio = n_outliers / meta.n
        outlier_cfg = cal_table.get("outlier_ensemble", {})
        outlier_sev = _threshold_severity(ratio, outlier_cfg.get("thresholds", []))
        record = AnomalyRecord(
            issue_type="OUTLIER_ENSEMBLE",
            description=f"Phát hiện {n_outliers} dòng dị biệt ({ratio*100:.1f}% data)",
            severity=outlier_sev,
            dq_dimensions=[outlier_cfg.get("dq_dimension", "Accuracy")],
            ml_impact=["training_bias"] if ratio > 0.05 else [],
            confidence=round(float(np.mean(outlier_scores)), 4) if outlier_scores else None,
            provenance=Provenance.OBSERVED,
            threshold_ref="outlier_ensemble",
            affected_count=n_outliers,
            affected_percent=round(ratio, 4),
            top_10_samples=top_samples,
            full_anomalies_export_path=outlier_export,
        )
        anomalies.append(registry.register_anomaly(record))

    # Duplicate record
    if meta.n_duplicates > 0:
        duplicate_positions = np.flatnonzero(df.duplicated(keep=False).to_numpy()).tolist()
        dup_df = df.iloc[duplicate_positions].copy()
        dup_df["_row_index"] = df.index[duplicate_positions].tolist()
        dup_df["_row_position"] = duplicate_positions
        dup_samples = dup_df.head(10).to_dict(orient="records")
        duplicate_export = _write_csv_artifact(
            dup_df,
            artifact_dir,
            f"{artifact_stem}__duplicate_rows.csv",
        )
        dup_cfg = cal_table.get("duplicate", {})
        dup_sev = _threshold_severity(meta.p_duplicates, dup_cfg.get("thresholds", []))
        record = AnomalyRecord(
            issue_type="DUPLICATE",
            description=f"Phát hiện {meta.n_duplicates} dòng trùng lặp ({meta.p_duplicates*100:.1f}% data)",
            severity=dup_sev,
            dq_dimensions=[dup_cfg.get("dq_dimension", "Uniqueness")],
            ml_impact=["training_bias"] if meta.p_duplicates > 0.05 else [],
            provenance=Provenance.OBSERVED,
            threshold_ref="duplicate",
            affected_count=meta.n_duplicates,
            affected_percent=meta.p_duplicates,
            top_10_samples=dup_samples,  # type: ignore[arg-type]
            full_anomalies_export_path=duplicate_export,
        )
        anomalies.append(registry.register_anomaly(record))

    logger.info(
        "build_data_quality_findings: %d anomalies registered in FindingRegistry",
        registry.count(),
    )

    return DataQualityFindings(
        dataset_meta=meta,
        columns=columns,
        anomalies=anomalies,
    )
