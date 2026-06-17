import logging
from pathlib import Path
from typing import Optional
import matplotlib
matplotlib.use("Agg")  # headless: works in test/CI
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _safe_name(value: str) -> str:
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in str(value))
    return safe.strip("_") or "field"


def _chart_file_name(chart_name: str, artifact_prefix: str | None = None) -> str:
    prefix = f"{_safe_name(artifact_prefix)}__" if artifact_prefix else ""
    return f"{prefix}overview_{_safe_name(chart_name)}.png"


def _save_chart(fig, out_dir: str, file_name: str) -> str:
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out_path = Path(out_dir) / file_name
    fig.savefig(out_path, dpi=120, bbox_inches="tight")
    plt.close(fig)
    return file_name


def _chart_sample(df: pd.DataFrame, max_rows: int = 10000) -> pd.DataFrame:
    if len(df) <= max_rows:
        return df
    return df.sample(max_rows, random_state=42)


def _dtype_label(series: pd.Series) -> str:
    if pd.api.types.is_bool_dtype(series):
        return "Boolean"
    if pd.api.types.is_numeric_dtype(series):
        return "Numeric"
    if pd.api.types.is_datetime64_any_dtype(series):
        return "DateTime"
    if isinstance(series.dtype, pd.CategoricalDtype) or pd.api.types.is_object_dtype(series):
        return "Categorical"
    return "Other"


def _horizontal_boxplot(ax, values: list[np.ndarray], labels: list[str]) -> None:
    try:
        ax.boxplot(values, orientation="horizontal", tick_labels=labels, patch_artist=True)
    except TypeError:  # pragma: no cover - matplotlib < 3.9 compatibility
        ax.boxplot(values, vert=False, labels=labels, patch_artist=True)


def create_overview_charts(
    df: pd.DataFrame,
    out_dir: str,
    artifact_prefix: str | None = None,
) -> dict[str, str]:
    """Create quick-look charts for the final HTML report.

    Returns a mapping of chart key -> relative PNG file name. Individual chart
    failures are logged and skipped so visualization never blocks profiling.
    """
    charts: dict[str, str] = {}
    if df is None or df.empty:
        return charts

    sampled = _chart_sample(df)

    def save(chart_key: str, fig) -> None:
        file_name = _chart_file_name(chart_key, artifact_prefix=artifact_prefix)
        charts[chart_key] = _save_chart(fig, out_dir, file_name)
        logger.info("Overview chart saved: %s", Path(out_dir) / file_name)

    # Missingness bar chart. All-zero missingness should still communicate a
    # meaningful state instead of rendering an apparently empty plot.
    try:
        missing_pct_all = sampled.isna().mean()
        missing_pct = missing_pct_all[missing_pct_all > 0].sort_values(ascending=False).head(12)
        if not missing_pct_all.empty:
            fig, ax = plt.subplots(figsize=(9, 4.8))
            if missing_pct.empty:
                completeness_pct = (1 - missing_pct_all).sort_values(ascending=True).head(12)
                y_labels = [str(label) for label in completeness_pct.index][::-1]
                values = (completeness_pct.to_numpy() * 100)[::-1]
                ax.barh(y_labels, values, color="#0f766e")
                ax.set_xlabel("Complete cells (%)")
                ax.set_title("No missing values detected")
                ax.set_xlim(0, 100)
                for position, value in enumerate(values):
                    ax.text(
                        min(99, value - 1),
                        position,
                        f"{value:.0f}%",
                        va="center",
                        ha="right",
                        color="white",
                        fontweight="bold",
                    )
            else:
                y_labels = [str(label) for label in missing_pct.index][::-1]
                values = (missing_pct.to_numpy() * 100)[::-1]
                colors = ["#b42318" if value >= 20 else "#b45309" for value in values]
                ax.barh(y_labels, values, color=colors)
                ax.set_xlabel("Missing cells (%)")
                ax.set_title("Missingness by column")
                x_max = max(5, min(100, float(values.max()) * 1.15 if len(values) else 5))
                ax.set_xlim(0, x_max)
                for position, value in enumerate(values):
                    ax.text(
                        min(x_max, value + x_max * 0.015),
                        position,
                        f"{value:.1f}%",
                        va="center",
                        ha="left",
                        color="#17201d",
                    )
            ax.grid(axis="x", alpha=0.22)
            save("missingness_bar", fig)
    except Exception as exc:  # pragma: no cover - defensive visualization fallback
        logger.warning("Skipping missingness overview chart: %s", exc)

    # Column type distribution donut
    try:
        dtype_counts = pd.Series([_dtype_label(sampled[column]) for column in sampled.columns]).value_counts()
        if not dtype_counts.empty:
            fig, ax = plt.subplots(figsize=(6.4, 4.8))
            colors = ["#0f766e", "#334e9f", "#b45309", "#15803d", "#728079"]
            wedges, _texts, autotexts = ax.pie(
                dtype_counts.to_numpy(),
                labels=dtype_counts.index,
                autopct="%1.0f%%",
                startangle=90,
                colors=colors[:len(dtype_counts)],
                wedgeprops={"width": 0.38, "edgecolor": "white"},
            )
            for autotext in autotexts:
                autotext.set_fontweight("bold")
                autotext.set_color("#17201d")
            ax.legend(wedges, dtype_counts.index, title="Type", loc="center left", bbox_to_anchor=(1, 0.5))
            ax.set_title("Column type distribution")
            save("dtype_distribution", fig)
    except Exception as exc:  # pragma: no cover - defensive visualization fallback
        logger.warning("Skipping dtype overview chart: %s", exc)

    numeric = sampled.select_dtypes(include="number").replace([np.inf, -np.inf], np.nan)
    numeric = numeric.dropna(axis=1, how="all")

    # Numeric histogram grid
    try:
        if not numeric.empty:
            selected = numeric.var(numeric_only=True).sort_values(ascending=False).head(4).index.tolist()
            if selected:
                fig, axes = plt.subplots(2, 2, figsize=(10, 6.6))
                axes_flat = axes.flatten()
                for axis, column in zip(axes_flat, selected):
                    values = numeric[column].dropna()
                    axis.hist(values, bins=min(30, max(8, int(np.sqrt(len(values))))) if len(values) else 8, color="#0f766e", alpha=0.82)
                    axis.set_title(str(column))
                    axis.grid(axis="y", alpha=0.18)
                for axis in axes_flat[len(selected):]:
                    axis.axis("off")
                fig.suptitle("Numeric distribution snapshots", fontweight="bold")
                save("numeric_distributions", fig)
    except Exception as exc:  # pragma: no cover - defensive visualization fallback
        logger.warning("Skipping numeric distribution overview chart: %s", exc)

    # Standardized box plot for numeric spread
    try:
        if not numeric.empty:
            selected = numeric.var(numeric_only=True).sort_values(ascending=False).head(6).index.tolist()
            box_values = []
            labels = []
            for column in selected:
                values = numeric[column].dropna()
                std = values.std()
                if len(values) < 2 or std == 0 or pd.isna(std):
                    continue
                z_values = ((values - values.mean()) / std).clip(-5, 5)
                box_values.append(z_values.to_numpy())
                labels.append(str(column))
            if box_values:
                fig, ax = plt.subplots(figsize=(9, max(4.2, len(box_values) * 0.55)))
                _horizontal_boxplot(ax, box_values, labels)
                for patch in ax.artists:
                    patch.set_facecolor("#e6f4f1")
                    patch.set_edgecolor("#0f766e")
                ax.axvline(0, color="#728079", linewidth=1, alpha=0.7)
                ax.set_xlabel("Standardized value")
                ax.set_title("Standardized numeric spread")
                ax.grid(axis="x", alpha=0.2)
                save("numeric_boxplot", fig)
    except Exception as exc:  # pragma: no cover - defensive visualization fallback
        logger.warning("Skipping numeric boxplot overview chart: %s", exc)

    # Correlation heatmap
    try:
        if numeric.shape[1] >= 2:
            selected = numeric.var(numeric_only=True).sort_values(ascending=False).head(8).index.tolist()
            corr = numeric[selected].corr().fillna(0)
            fig, ax = plt.subplots(figsize=(7.4, 6.2))
            image = ax.imshow(corr.to_numpy(), cmap="RdBu_r", vmin=-1, vmax=1)
            ax.set_xticks(range(len(corr.columns)))
            ax.set_yticks(range(len(corr.index)))
            ax.set_xticklabels(corr.columns, rotation=45, ha="right")
            ax.set_yticklabels(corr.index)
            ax.set_title("Numeric correlation heatmap")
            fig.colorbar(image, ax=ax, fraction=0.046, pad=0.04)
            save("correlation_heatmap", fig)
    except Exception as exc:  # pragma: no cover - defensive visualization fallback
        logger.warning("Skipping correlation overview chart: %s", exc)

    # Top categorical values
    try:
        categorical = sampled.select_dtypes(include=["object", "category", "bool"])
        if not categorical.empty:
            scored_columns = categorical.nunique(dropna=True).sort_values(ascending=False)
            selected_column = scored_columns.index[0]
            value_counts = categorical[selected_column].astype("string").fillna("<missing>").value_counts().head(10)
            if not value_counts.empty:
                fig, ax = plt.subplots(figsize=(9, 4.8))
                labels = [str(label) for label in value_counts.index][::-1]
                values = value_counts.to_numpy()[::-1]
                ax.barh(labels, values, color="#334e9f")
                ax.set_xlabel("Rows")
                ax.set_title(f"Top values in {selected_column}")
                ax.grid(axis="x", alpha=0.2)
                save("categorical_top_values", fig)
    except Exception as exc:  # pragma: no cover - defensive visualization fallback
        logger.warning("Skipping categorical overview chart: %s", exc)

    return charts


def draw_diagnostic_scatter(
    df: pd.DataFrame,
    anomaly_result: dict,
    out_dir: str,
    artifact_prefix: str | None = None,
) -> Optional[str]:
    """Scatter 2 highest-variance numeric cols; mark ALL outliers red. Returns filename or None."""
    if anomaly_result.get("skipped", True) or anomaly_result.get("n_outliers", 0) == 0:
        return None

    numeric = df.select_dtypes(include="number")
    cols = anomaly_result.get("numeric_columns_used") or list(numeric.columns)
    cols = [c for c in cols if c in numeric.columns]
    if len(cols) < 2:
        return None
    x_col, y_col = numeric[cols].var().sort_values(ascending=False).index[:2]

    outlier_positions = anomaly_result.get("outlier_positions")
    if outlier_positions is not None:
        is_out = np.zeros(len(df), dtype=bool)
        valid_positions = [int(pos) for pos in outlier_positions if 0 <= int(pos) < len(df)]
        is_out[valid_positions] = True
        outlier_count = len(valid_positions)
    else:
        outlier_idx = set(anomaly_result["outlier_indices"])
        is_out = df.index.isin(outlier_idx)
        outlier_count = len(outlier_idx)

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    prefix = f"{_safe_name(artifact_prefix)}__" if artifact_prefix else ""
    file_name = f"{prefix}diagnostic_{_safe_name(x_col)}_{_safe_name(y_col)}.png"
    out_path = Path(out_dir) / file_name

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df.loc[~is_out, x_col], df.loc[~is_out, y_col],
               c="#9aa0a6", s=18, label="normal")
    ax.scatter(df.loc[is_out, x_col], df.loc[is_out, y_col],
               c="#d93025", s=42, label="outlier")
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(f"Diagnostic: {x_col} vs {y_col} ({outlier_count} outliers)")
    ax.legend()
    fig.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    logger.info("Diagnostic chart saved: %s", out_path)
    return file_name


def attach_diagnostic_charts(
    findings,
    df: pd.DataFrame,
    anomaly_result: dict,
    out_dir: str,
    artifact_prefix: str | None = None,
):
    """Fill diagnostic_chart for OUTLIER_ENSEMBLE records. Mutates findings in place."""
    chart = draw_diagnostic_scatter(df, anomaly_result, out_dir, artifact_prefix=artifact_prefix)
    if chart is None:
        return findings
    for rec in findings.anomalies:
        if rec.issue_type == "OUTLIER_ENSEMBLE":
            rec.diagnostic_chart = chart
    return findings


def attach_overview_charts(
    findings,
    df: pd.DataFrame,
    out_dir: str,
    artifact_prefix: str | None = None,
):
    """Fill dataset_meta.overview_charts with quick-look PNG artifacts."""
    charts = create_overview_charts(df, out_dir, artifact_prefix=artifact_prefix)
    if charts:
        findings.dataset_meta.overview_charts = {
            **findings.dataset_meta.overview_charts,
            **charts,
        }
    return findings


# ============================================================
# L4 Charts — for the structured report
# ============================================================

def draw_stacked_bar_issues(
    verdict,
    out_dir: str,
    artifact_prefix: str | None = None,
) -> Optional[str]:
    """Stacked bar chart: issue count by table and severity level.

    Shows CRITICAL/HIGH/WARN distribution across tables → Phần 1 Executive Dashboard.
    """
    try:
        if not verdict.top_issues:
            return None

        # Group by (table, severity)
        table_severity: dict[str, dict[str, int]] = {}
        for issue in verdict.top_issues:
            table = issue.get("affected_table") or issue.get("affected_column", "dataset")
            severity = issue.get("severity", "WARN")
            table_severity.setdefault(table, {"CRITICAL": 0, "HIGH": 0, "WARN": 0})
            if severity in table_severity[table]:
                table_severity[table][severity] += 1

        if not table_severity:
            return None

        tables = list(table_severity.keys())
        critical = [table_severity[t].get("CRITICAL", 0) for t in tables]
        high = [table_severity[t].get("HIGH", 0) for t in tables]
        warn = [table_severity[t].get("WARN", 0) for t in tables]

        fig, ax = plt.subplots(figsize=(max(6, len(tables) * 1.2), 4))
        x = np.arange(len(tables))
        width = 0.6

        ax.bar(x, critical, width, label="CRITICAL", color="#e74c3c")
        ax.bar(x, high, width, bottom=critical, label="HIGH", color="#f39c12")
        ax.bar(
            x, warn, width,
            bottom=[c + h for c, h in zip(critical, high)],
            label="WARN", color="#f1c40f",
        )

        ax.set_xticks(x)
        ax.set_xticklabels(tables, rotation=30, ha="right", fontsize=9)
        ax.set_ylabel("Issue Count")
        ax.set_title("Issues by Table & Severity")
        ax.legend(loc="upper right", fontsize=8)
        fig.tight_layout()

        file_name = _chart_file_name("stacked_bar_issues", artifact_prefix)
        return _save_chart(fig, out_dir, file_name)
    except Exception as exc:
        logger.warning("draw_stacked_bar_issues failed: %s", exc)
        return None


def draw_relationship_network(
    schema,
    out_dir: str,
    artifact_prefix: str | None = None,
) -> Optional[str]:
    """Relationship network graph: tables as nodes, FK edges with integrity color.

    Uses networkx (lazy import) → Phần 3a Schema Evaluation.
    """
    try:
        import networkx as nx
    except ImportError:
        logger.warning("networkx not installed — skipping relationship graph")
        return None

    try:
        if not schema or not schema.relationships:
            return None

        G = nx.DiGraph()
        edge_colors = []
        edge_labels = {}

        # Collect integrity error tables for coloring
        error_tables = set()
        if schema.integrity_errors:
            for err in schema.integrity_errors:
                error_tables.add(err.affected_table)

        for rel in schema.relationships:
            child = rel.child_table
            parent = rel.parent_table
            G.add_edge(child, parent)
            # Color edge based on integrity
            has_error = child in error_tables or parent in error_tables
            edge_colors.append("#e74c3c" if has_error else "#27ae60")
            label = rel.cardinality if rel.cardinality != "UNKNOWN" else ""
            edge_labels[(child, parent)] = label

        if G.number_of_edges() == 0:
            return None

        fig, ax = plt.subplots(figsize=(max(8, G.number_of_nodes() * 1.5), 6))
        pos = nx.spring_layout(G, seed=42, k=2)
        nx.draw_networkx_nodes(G, pos, ax=ax, node_size=1200, node_color="#3498db", alpha=0.9)
        nx.draw_networkx_labels(G, pos, ax=ax, font_size=9, font_weight="bold")
        nx.draw_networkx_edges(
            G, pos, ax=ax,
            edge_color=edge_colors,
            width=2,
            arrows=True,
            arrowsize=15,
            connectionstyle="arc3,rad=0.1",
        )
        nx.draw_networkx_edge_labels(G, pos, edge_labels, ax=ax, font_size=7)
        ax.set_title("Table Relationship Network")
        ax.axis("off")
        fig.tight_layout()

        file_name = _chart_file_name("relationship_network", artifact_prefix)
        return _save_chart(fig, out_dir, file_name)
    except Exception as exc:
        logger.warning("draw_relationship_network failed: %s", exc)
        return None


def draw_top_correlations_bar(
    cross_table_analysis,
    out_dir: str,
    top_n: int = 10,
    artifact_prefix: str | None = None,
) -> Optional[str]:
    """Horizontal bar chart of top N cross-table correlations by |coefficient|.

    → Phần 3b Cross Correlation.
    """
    try:
        if not cross_table_analysis or not cross_table_analysis.correlations:
            return None

        # Sort by absolute coefficient
        corrs = sorted(
            cross_table_analysis.correlations,
            key=lambda c: abs(c.get("coefficient", 0) if isinstance(c, dict) else abs(getattr(c, "coefficient", 0))),
            reverse=True,
        )[:top_n]

        if not corrs:
            return None

        labels = []
        coefficients = []
        for c in corrs:
            if isinstance(c, dict):
                label = f"{c.get('parent_column', '?')} ↔ {c.get('child_column', '?')}"
                coeff = c.get("coefficient", 0)
            else:
                label = f"{getattr(c, 'parent_column', '?')} ↔ {getattr(c, 'child_column', '?')}"
                coeff = getattr(c, "coefficient", 0)
            labels.append(label)
            coefficients.append(coeff)

        fig, ax = plt.subplots(figsize=(8, max(3, len(labels) * 0.4)))
        colors = ["#e74c3c" if abs(c) > 0.8 else "#f39c12" if abs(c) > 0.5 else "#27ae60" for c in coefficients]
        y_pos = np.arange(len(labels))
        ax.barh(y_pos, coefficients, color=colors, height=0.6)
        ax.set_yticks(y_pos)
        ax.set_yticklabels(labels, fontsize=8)
        ax.set_xlabel("Correlation Coefficient")
        ax.set_title(f"Top {len(labels)} Cross-Table Correlations")
        ax.axvline(x=0, color="grey", linewidth=0.5)
        fig.tight_layout()

        file_name = _chart_file_name("top_correlations", artifact_prefix)
        return _save_chart(fig, out_dir, file_name)
    except Exception as exc:
        logger.warning("draw_top_correlations_bar failed: %s", exc)
        return None

