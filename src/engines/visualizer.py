import logging
from pathlib import Path
from typing import Optional
import matplotlib
matplotlib.use("Agg")  # headless: works in test/CI
import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)


def draw_diagnostic_scatter(
    df: pd.DataFrame, anomaly_result: dict, out_dir: str
) -> Optional[str]:
    """Scatter 2 highest-variance numeric cols; mark ALL outliers red. Returns path or None."""
    if anomaly_result.get("skipped", True) or anomaly_result.get("n_outliers", 0) == 0:
        return None

    numeric = df.select_dtypes(include="number")
    cols = anomaly_result.get("numeric_columns_used") or list(numeric.columns)
    cols = [c for c in cols if c in numeric.columns]
    if len(cols) < 2:
        return None
    x_col, y_col = numeric[cols].var().sort_values(ascending=False).index[:2]

    outlier_idx = set(anomaly_result["outlier_indices"])
    is_out = df.index.isin(outlier_idx)

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out_path = str(Path(out_dir) / f"diagnostic_{x_col}_{y_col}.png")

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df.loc[~is_out, x_col], df.loc[~is_out, y_col],
               c="#9aa0a6", s=18, label="normal")
    ax.scatter(df.loc[is_out, x_col], df.loc[is_out, y_col],
               c="#d93025", s=42, label="outlier")
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(f"Diagnostic: {x_col} vs {y_col} ({len(outlier_idx)} outliers)")
    ax.legend()
    fig.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    logger.info("Diagnostic chart saved: %s", out_path)
    return out_path


def attach_diagnostic_charts(findings, df: pd.DataFrame, anomaly_result: dict, out_dir: str):
    """Fill diagnostic_chart for OUTLIER_ENSEMBLE records. Mutates findings in place."""
    chart = draw_diagnostic_scatter(df, anomaly_result, out_dir)
    if chart is None:
        return findings
    for rec in findings.anomalies:
        if rec.issue_type == "OUTLIER_ENSEMBLE":
            rec.diagnostic_chart = chart
    return findings
