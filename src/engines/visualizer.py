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
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)
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


def _horizontal_boxplot(ax, values: list[np.ndarray], labels: list[str]) -> dict:
    try:
        return ax.boxplot(values, orientation="horizontal", tick_labels=labels, patch_artist=True)
    except TypeError:  # pragma: no cover - matplotlib < 3.9 compatibility
        return ax.boxplot(values, vert=False, labels=labels, patch_artist=True)


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
            labels = [str(x) for x in dtype_counts.index]
            pie_out = ax.pie(
                dtype_counts.to_numpy(),
                labels=labels,
                autopct="%1.0f%%",
                startangle=90,
                colors=colors[:len(dtype_counts)],
                wedgeprops={"width": 0.38, "edgecolor": "white"},
            )
            wedges = pie_out[0]
            _texts = pie_out[1]
            autotexts = pie_out[2] if len(pie_out) > 2 else []
            for autotext in autotexts:
                autotext.set_fontweight("bold")
                autotext.set_color("#17201d")
            ax.legend(wedges, labels, title="Type", loc="center left", bbox_to_anchor=(1, 0.5))
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
                bp = _horizontal_boxplot(ax, box_values, labels)
                for patch in bp["boxes"]:
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
        categorical = sampled.select_dtypes(include=["object", "category", "bool"])  # type: ignore
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
    ax.scatter(df[x_col][~is_out], df[y_col][~is_out],
               c="#9aa0a6", s=18, label="normal")
    ax.scatter(df[x_col][is_out], df[y_col][is_out],
               c="#d93025", s=42, label="outlier")
    ax.set_xlabel(x_col)
    ax.set_ylabel(y_col)
    ax.set_title(f"Diagnostic: {x_col} vs {y_col} ({outlier_count} outliers)")
    ax.legend()
    fig.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    logger.info("Diagnostic chart saved: %s", out_path)
    return file_name


def draw_anomaly_score_bar(
    anomaly_result: dict,
    out_dir: str,
    artifact_prefix: str | None = None,
) -> Optional[str]:
    """Draw a bar chart of top 100 anomaly scores for outliers."""
    if anomaly_result.get("skipped", True) or anomaly_result.get("n_outliers", 0) == 0:
        return None

    # We want to plot the top scores.
    # anomaly_result has "anomaly_scores", "outlier_positions", "outlier_indices"
    scores = anomaly_result.get("anomaly_scores", [])
    positions = anomaly_result.get("outlier_positions", [])
    indices = anomaly_result.get("outlier_indices", [])
    
    if not scores:
        return None

    # Plot top 50 or so outliers to make the bar chart readable
    top_n = min(50, len(scores))
    top_scores = scores[:top_n]
    top_indices = [str(idx) for idx in indices[:top_n]]

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    prefix = f"{_safe_name(artifact_prefix)}__" if artifact_prefix else ""
    file_name = f"{prefix}outlier_score_bar.png"
    out_path = Path(out_dir) / file_name

    fig, ax = plt.subplots(figsize=(10, max(4.2, len(top_scores) * 0.2)))
    
    # Reverse to have highest score at the top
    y_pos = np.arange(len(top_indices))[::-1]
    
    ax.barh(y_pos, top_scores, align='center', color="#d93025", alpha=0.8)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(top_indices)
    
    ax.set_xlabel("Anomaly Score (Ensemble Z-Score Probability)")
    ax.set_ylabel("Row Index")
    ax.set_title(f"Top {top_n} Outlier Scores")
    
    ax.grid(axis='x', linestyle='--', alpha=0.6)
    
    fig.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    logger.info("Outlier score bar chart saved: %s", out_path)
    return file_name


def attach_diagnostic_charts(
    findings,
    df: pd.DataFrame,
    anomaly_result: dict,
    out_dir: str,
    artifact_prefix: str | None = None,
):
    """Fill diagnostic_chart for OUTLIER_ENSEMBLE records. Mutates findings in place.

    Đồng thời inject chart path vào dataset_meta.overview_charts với key
    "outlier_score_bar" để _table_charts_for() tự lọc và hiển thị trong tab bảng.
    """
    chart_score = draw_anomaly_score_bar(anomaly_result, out_dir, artifact_prefix=artifact_prefix)
    chart_scatter = draw_diagnostic_scatter(df, anomaly_result, out_dir, artifact_prefix=artifact_prefix)
    
    if not chart_score and not chart_scatter:
        return findings

    # Dùng scatter làm biểu tượng chính cho AnomalyRecord nếu cần
    main_chart = chart_scatter or chart_score

    for rec in findings.anomalies:
        if rec.issue_type == "OUTLIER_ENSEMBLE":
            rec.diagnostic_chart = main_chart
            
    # Inject vào overview_charts để html_merger có thể render trong tab bảng
    current = findings.dataset_meta.overview_charts or {}
    updates = {}
    if chart_score:
        updates["outlier_score_bar"] = chart_score
    if chart_scatter:
        updates["outlier_scatter"] = chart_scatter
        
    findings.dataset_meta.overview_charts = {**current, **updates}
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
            # Support both dict and IssueSummary / dataclass objects
            def _get(obj, key, default=None):
                if isinstance(obj, dict):
                    return obj.get(key, default)
                return getattr(obj, key, default)

            table_val = _get(issue, "affected_table") or _get(issue, "affected_column", "dataset")
            table = str(table_val) if table_val is not None else "dataset"
            severity_val = _get(issue, "severity", "WARN")
            severity = severity_val.value if hasattr(severity_val, "value") else str(severity_val)
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
    """ER-style diagram: tables as boxes with column lists, FK connector lines.

    Mimics the classic ERD look — coloured header, column rows,
    PK / FK markers, and styled connector lines with cardinality labels.
    """
    try:
        if not schema or not schema.relationships:
            return None

        # ── Collect table / column info ──────────────────────────────────────
        tables_in_rels: set[str] = set()
        for rel in schema.relationships:
            tables_in_rels.add(rel.child_table)
            tables_in_rels.add(rel.parent_table)

        if not tables_in_rels:
            return None

        # Map table name → column list (from schema.tables)
        col_map: dict[str, list[str]] = {}
        for tbl in (schema.tables or []):
            if tbl.name in tables_in_rels:
                col_map[tbl.name] = list(tbl.columns)

        # PK columns (from relationships parent_column)
        pk_map: dict[str, set[str]] = {}
        for rel in schema.relationships:
            pk_map.setdefault(rel.parent_table, set()).add(rel.parent_column)

        # FK columns (from relationships child_column)
        fk_map: dict[str, set[str]] = {}
        for rel in schema.relationships:
            fk_map.setdefault(rel.child_table, set()).add(rel.child_column)

        # Tables with integrity errors → red header
        error_tables: set[str] = set()
        for err in (schema.integrity_errors or []):
            error_tables.add(err.affected_table)

        # ── Layout constants (all in data coords) ────────────────────────────
        BOX_W        = 3.2    # box width
        HEADER_H     = 0.55   # header row height
        ROW_H        = 0.35   # column row height
        COL_PADDING  = 0.15   # left text padding
        H_GAP        = 1.8    # horizontal gap between boxes
        V_GAP        = 2.0    # vertical gap between layers

        table_list = sorted(tables_in_rels)
        n = len(table_list)

        # Compute box heights
        def box_height(tname: str) -> float:
            cols = col_map.get(tname, [])
            return HEADER_H + max(1, len(cols)) * ROW_H

        # ── Topological / hierarchical layout (BFS by in-degree) ─────────────
        # Build adjacency: child_table → parent_table (FK direction)
        children_of: dict[str, set[str]] = {t: set() for t in table_list}
        parents_of: dict[str, set[str]] = {t: set() for t in table_list}
        for rel in schema.relationships:
            if rel.child_table in parents_of and rel.parent_table in parents_of:
                parents_of[rel.child_table].add(rel.parent_table)
                children_of[rel.parent_table].add(rel.child_table)

        # Compute depth layer via Kahn's topological sort (cycle-safe — each node processed once)
        layer: dict[str, int] = {}
        in_deg: dict[str, int] = {t: len(parents_of[t]) for t in table_list}

        from collections import deque
        # Seed: nodes with no incoming FK edges (reference/lookup tables)
        current_layer: list[str] = [t for t in table_list if in_deg[t] == 0]
        lyr_idx = 0
        while current_layer:
            for t in current_layer:
                layer[t] = lyr_idx
            next_layer: list[str] = []
            for t in current_layer:
                for child in children_of[t]:
                    in_deg[child] -= 1
                    if in_deg[child] == 0:
                        next_layer.append(child)
            current_layer = next_layer
            lyr_idx += 1

        # Assign remaining nodes (in cycles) to last layer + 1
        for t in table_list:
            if t not in layer:
                layer[t] = lyr_idx



        # Group tables by layer
        from collections import defaultdict
        layers_map: dict[int, list[str]] = defaultdict(list)
        for t, lyr in sorted(layer.items()):
            layers_map[lyr].append(t)
        n_layers = max(layers_map) + 1 if layers_map else 1

        # Assign (x, y) positions — each layer is a horizontal row
        positions: dict[str, tuple[float, float]] = {}
        for lyr_idx in range(n_layers):
            members = layers_map.get(lyr_idx, [])
            members_sorted = sorted(members)  # stable order within layer
            count = len(members_sorted)
            # Total width of this layer
            layer_total_w = count * BOX_W + (count - 1) * H_GAP
            # Centre-align this layer within the widest layer
            max_layer_count = max(len(v) for v in layers_map.values())
            max_total_w = max_layer_count * BOX_W + (max_layer_count - 1) * H_GAP
            x_offset = (max_total_w - layer_total_w) / 2.0
            y = -lyr_idx * V_GAP
            for member_idx, tname in enumerate(members_sorted):
                x = x_offset + member_idx * (BOX_W + H_GAP)
                positions[tname] = (x, y)

        # ── Figure setup ─────────────────────────────────────────────────────
        max_layer_count = max(len(v) for v in layers_map.values())
        total_w = max_layer_count * (BOX_W + H_GAP) + 0.5
        total_h = (n_layers - 1) * V_GAP + max(
            box_height(t) for t in table_list
        ) + 1.5

        fig_w = max(10, total_w + 1.0)
        fig_h = max(6, total_h + 1.5)

        fig, ax = plt.subplots(figsize=(fig_w, fig_h))
        ax.set_aspect("equal")
        ax.axis("off")
        ax.set_xlim(-0.5, total_w + 0.5)
        ax.set_ylim(-total_h - 1.0, 1.2)


        # ── Draw table boxes ─────────────────────────────────────────────────
        HEADER_FILL   = "#1565C0"   # blue header (normal)
        ERROR_FILL    = "#C62828"   # red header (integrity error)
        HEADER_TEXT   = "#FFFFFF"
        BODY_FILL     = "#FAFAFA"
        BODY_FILL_ALT = "#F0F4FF"   # alternating row
        BORDER_COLOR  = "#90A4AE"
        PK_COLOR      = "#1565C0"
        FK_COLOR      = "#6A1B9A"
        NORMAL_COLOR  = "#37474F"

        def draw_table(ax, tname: str, x: float, y: float) -> dict:
            """Draw one table box; return dict of column anchor points {col: (cx, cy)}."""
            cols = col_map.get(tname, [])
            pks  = pk_map.get(tname, set())
            fks  = fk_map.get(tname, set())
            h    = box_height(tname)

            # Outer border
            border = plt.Rectangle(
                (x, y - h), BOX_W, h,
                linewidth=1.5, edgecolor=BORDER_COLOR,
                facecolor="white", zorder=2,
            )
            ax.add_patch(border)

            # Header
            hdr_fill = ERROR_FILL if tname in error_tables else HEADER_FILL
            hdr = plt.Rectangle(
                (x, y - HEADER_H), BOX_W, HEADER_H,
                linewidth=0, edgecolor="none",
                facecolor=hdr_fill, zorder=3,
            )
            ax.add_patch(hdr)
            ax.text(
                x + BOX_W / 2, y - HEADER_H / 2,
                tname,
                ha="center", va="center",
                fontsize=9, fontweight="bold",
                color=HEADER_TEXT, zorder=4,
            )

            # Column rows
            anchor_y: dict[str, float] = {}
            for idx, col in enumerate(cols):
                row_y = y - HEADER_H - idx * ROW_H
                row_fill = BODY_FILL if idx % 2 == 0 else BODY_FILL_ALT
                row_rect = plt.Rectangle(
                    (x, row_y - ROW_H), BOX_W, ROW_H,
                    linewidth=0, edgecolor="none",
                    facecolor=row_fill, zorder=2,
                )
                ax.add_patch(row_rect)

                # Column label
                is_pk = col in pks
                is_fk = col in fks
                if is_pk:
                    prefix, col_color, col_weight = "★ ", PK_COLOR, "bold"
                elif is_fk:
                    prefix, col_color, col_weight = "◇ ", FK_COLOR, "normal"
                else:
                    prefix, col_color, col_weight = "  ", NORMAL_COLOR, "normal"
                ax.text(
                    x + COL_PADDING, row_y - ROW_H / 2,
                    f"{prefix}{col}",
                    ha="left", va="center",
                    fontsize=7.5, color=col_color, fontweight=col_weight,
                    zorder=4,
                )

                # Horizontal separator
                ax.plot(
                    [x, x + BOX_W], [row_y - ROW_H, row_y - ROW_H],
                    color="#ECEFF1", linewidth=0.5, zorder=3,
                )
                anchor_y[col] = row_y - ROW_H / 2

            if not cols:
                ax.text(
                    x + COL_PADDING, y - HEADER_H - ROW_H / 2,
                    "  (no columns)",
                    ha="left", va="center",
                    fontsize=7.5, color="#B0BEC5", style="italic", zorder=4,
                )

            return anchor_y

        col_anchors: dict[str, dict[str, float]] = {}
        for tname, (x, y) in positions.items():
            col_anchors[tname] = draw_table(ax, tname, x, y)

        # ── Draw FK connector lines ───────────────────────────────────────────
        EDGE_COLOR   = "#1976D2"
        EDGE_COLOR_E = "#D32F2F"

        cardinality_labels = {
            "1:N": "1:N", "N:1": "N:1",
            "1:1": "1:1", "N:M": "N:M",
            "M:N": "M:N", None: "",
        }

        def midpoint_label(x1, y1, x2, y2, label: str, color: str) -> None:
            mx, my = (x1 + x2) / 2, (y1 + y2) / 2
            ax.text(
                mx, my, label,
                ha="center", va="center",
                fontsize=7, color=color,
                bbox=dict(facecolor="white", edgecolor="none", alpha=0.75, pad=1),
                zorder=6,
            )

        # Track how many arrows connect the same pair of tables (for varying rad)
        edge_pair_count: dict[tuple[str, str], int] = {}

        for rel in schema.relationships:
            child_t  = rel.child_table
            parent_t = rel.parent_table
            if child_t not in positions or parent_t not in positions:
                continue

            cx, cy = positions[child_t]
            px, py = positions[parent_t]

            fk_col = rel.child_column
            pk_col = rel.parent_column
            fk_y = col_anchors.get(child_t, {}).get(fk_col, cy - box_height(child_t) / 2)
            pk_y = col_anchors.get(parent_t, {}).get(pk_col, py - box_height(parent_t) / 2)

            child_layer = layer.get(child_t, 0)
            parent_layer = layer.get(parent_t, 0)

            # Count edges between this pair to offset arc radius
            pair_key = (min(child_t, parent_t), max(child_t, parent_t))
            pair_idx = edge_pair_count.get(pair_key, 0)
            edge_pair_count[pair_key] = pair_idx + 1

            has_err = child_t in error_tables or parent_t in error_tables
            ec = EDGE_COLOR_E if has_err else EDGE_COLOR

            if parent_layer < child_layer:
                # Normal direction: parent above child → connect bottom of parent to top of child
                x1 = cx + BOX_W / 2   # child top-center
                y1 = cy               # top of child box
                x2 = px + BOX_W / 2   # parent bottom-center
                y2 = py - box_height(parent_t)  # bottom of parent box
                # Small horizontal offset for multiple FKs to same parent
                x1 += pair_idx * 0.2
                x2 += pair_idx * 0.2
                rad = 0.0
            else:
                # Same layer or back-edge → use side connections with arc
                if px >= cx:
                    x1, x2 = cx + BOX_W, px
                else:
                    x1, x2 = cx, px + BOX_W
                y1, y2 = fk_y, pk_y
                rad = 0.15 + pair_idx * 0.1

            ax.annotate(
                "",
                xy=(x2, y2),
                xytext=(x1, y1),
                arrowprops=dict(
                    arrowstyle="-|>",
                    color=ec,
                    lw=1.5,
                    connectionstyle=f"arc3,rad={rad}",
                ),
                zorder=5,
            )

            card = rel.cardinality or ""
            if card and card != "UNKNOWN":
                lbl = cardinality_labels.get(card, card)
                midpoint_label(x1, y1, x2, y2, lbl, ec)


        # ── Legend ───────────────────────────────────────────────────────────
        legend_y = 0.98
        fig.text(0.01, legend_y, "★ Primary Key   ◇ Foreign Key   ",
                 fontsize=7.5, color="#546E7A",
                 va="top", ha="left")
        if error_tables:
            fig.text(0.5, legend_y,
                     f"🔴 Integrity issues: {', '.join(sorted(error_tables))}",
                     fontsize=7.5, color=ERROR_FILL, va="top", ha="center")

        fig.suptitle("Entity Relationship Diagram", fontsize=11,
                     fontweight="bold", color="#1A237E", y=1.0)
        fig.tight_layout(pad=0.5)

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
                # CrossTableCorrelation serialized as dict uses left_feature/right_feature
                left  = c.get("left_feature") or c.get("parent_column") or "?"
                right = c.get("right_feature") or c.get("child_column") or "?"
                coeff = c.get("coefficient", 0)
            else:
                left  = getattr(c, "left_feature", None) or getattr(c, "parent_column", "?")
                right = getattr(c, "right_feature", None) or getattr(c, "child_column", "?")
                coeff = getattr(c, "coefficient", 0)
            # Shorten long feature names for readability (keep table.column format)
            def _short(feat: str) -> str:
                clean = feat.replace("__via__", ".via.").replace("__", ".")
                parts = clean.split(".")
                if len(parts) > 2:
                    return f"{parts[0]}.{parts[-1]}"
                return clean
            label = f"{_short(left)} ↔ {_short(right)}"
            labels.append(label)
            coefficients.append(coeff)

        # Standard vertical spacing per horizontal bar
        row_h = 0.45
        fig, ax = plt.subplots(figsize=(10, max(3, len(labels) * row_h)))
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

