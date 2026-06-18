"""Full EDA pipeline: data file -> findings JSON + verdict [+ schema findings]."""
import json
import html as html_lib
import logging
import sys
import warnings
from pathlib import Path
from dotenv import load_dotenv

import pandas as pd

warnings.filterwarnings("ignore")
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("smart_eda")

SRC = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC))

from config.env_loader import load_project_dotenv

load_project_dotenv(Path(__file__).parent)

from ingestion.registry import load_any
from ingestion.schema_reader import parse_schema
from engines.profiling_engine import run_profiling, run_profiling_html
from engines.anomaly_engine import run_anomaly_detection
from engines.visualizer import (
    attach_diagnostic_charts,
    attach_overview_charts,
    draw_relationship_network,
    draw_stacked_bar_issues,
    draw_top_correlations_bar,
)
from engines.cross_table_engine import run_cross_table_analysis
from engines.graph_engine import accepted_relationships_from_graph, reconstruct_graph
from engines.schema_gate import apply_schema_gate
from engines.schema_engine import (
    build_schema_findings, load_tables, load_tables_by_path, validate_schema_multi,
)
from ontology.findings_builder import build_data_quality_findings
from ontology.models import (
    AnomalyRecord, ArtifactManifest, ArtifactRecord, DataQualityFindings,
    CrossTableAnalysis, CrossTableCorrelation, DatasetMeta,
)
from severity.calibrator import calibrate_columns, load_calibrator_table
from severity.compound import apply_compound
from severity.aggregator import aggregate
from severity.missingness import detect_missingness
from reporting.summary_renderer import render_markdown_report
from reporting.l4_report import generate_multi_agent_report
from reporting.html_merger import merge_to_tabbed_html
from webapp.progress_bus import NullBus, get_bus


def _safe_artifact_stem(name: str) -> str:
    stem = Path(name).stem or "dataset"
    safe = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in stem)
    return safe.strip("_") or "dataset"


def _table_names_for_paths(data_paths: list) -> list[str]:
    used: set[str] = set()
    names: list[str] = []
    for path in data_paths:
        base = _safe_artifact_stem(str(path))
        name = base
        index = 2
        while name in used:
            name = f"{base}_{index}"
            index += 1
        used.add(name)
        names.append(name)
    return names


def _artifact_kind(path: Path) -> str:
    if path.name.startswith("statistical_profile") and path.suffix == ".html":
        return "statistical_profile_html"
    if path.name == "cross_table_analysis.json":
        return "cross_table_analysis_json"
    if path.name == "cross_table_correlations.csv":
        return "cross_table_correlations_csv"
    if path.name == "relationship_graph.json":
        return "relationship_graph_json"
    if path.name == "schema_gate.json":
        return "schema_gate_json"
    if path.name.endswith("_findings.json"):
        return "findings_json"
    if path.name == "dataset_verdict.json":
        return "verdict_json"
    if path.name == "guardrail_report.json":
        return "guardrail_json"
    if path.suffix == ".md":
        return "report_markdown"
    if path.suffix == ".html":
        return "report_html"
    if path.suffix == ".png":
        return "diagnostic_chart"
    if path.suffix == ".csv":
        return "row_export"
    return "artifact"


def _artifact_source_layer(path: Path) -> str:
    if path.name == "data_quality_findings.json":
        return "L3_ONTOLOGY"
    if path.name == "schema_evaluation_findings.json":
        return "L2_SCHEMA"
    if path.name == "dataset_verdict.json":
        return "L2_5_SEVERITY"
    if path.name == "guardrail_report.json":
        return "L4_GUARDRAIL"
    if path.name == "cross_table_analysis.json":
        return "L4_CROSS_TABLE"
    if path.name == "cross_table_correlations.csv":
        return "L4_CROSS_TABLE"
    if path.name == "relationship_graph.json":
        return "L2C_GRAPH"
    if path.name == "schema_gate.json":
        return "L2B5_SCHEMA_GATE"
    if path.name == "cross_table_dataset_preview.csv":
        return "L4_CROSS_TABLE"
    if path.name in {"summary_report.md", "l4_report.md"}:
        return "L4_REPORTING"
    if path.name == "smart_eda_report.html":
        return "L4_REPORTING"
    if path.name.startswith("statistical_profile") and path.suffix == ".html":
        return "L1_PROFILING"
    if path.suffix == ".png":
        return "L3_5_CHARTS"
    if path.suffix == ".csv":
        return "L3_ARTIFACT_EXPORT"
    return "PIPELINE"


def _write_artifact_manifest(out: Path) -> Path:
    artifacts = []
    used_ids: set[str] = set()
    for path in sorted(out.iterdir()):
        if not path.is_file() or path.name == "artifact_manifest.json":
            continue
        artifact_id = _safe_artifact_stem(path.name)
        if artifact_id in used_ids:
            index = 2
            base = artifact_id
            while artifact_id in used_ids:
                artifact_id = f"{base}_{index}"
                index += 1
        used_ids.add(artifact_id)
        artifacts.append(ArtifactRecord(
            artifact_id=artifact_id,
            kind=_artifact_kind(path),
            path=path.name,
            source_layer=_artifact_source_layer(path),
        ))
    manifest = ArtifactManifest(artifacts=artifacts)
    manifest_path = out / "artifact_manifest.json"
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return manifest_path


def _load_tables_for_cross_analysis(data_paths: list, schema_path: str | None) -> dict:
    if schema_path:
        parsed = parse_schema(schema_path)["tables"]
        return load_tables(data_paths, parsed)
    return load_tables_by_path(data_paths)


def _get_composite_pk_tables(schema_path: str | None) -> set[str]:
    """Return names of tables with composite PKs declared in DBML `indexes` block.

    These are junction/bridge tables (e.g. PlaylistTrack) where individual
    columns are intentionally non-unique.  The set is used to suppress
    NON_UNIQUE_PARENT_PK false positives in graph_engine.reconstruct_graph().
    """
    if not schema_path:
        return set()
    try:
        parsed = parse_schema(schema_path)["tables"]
        return {
            table_name
            for table_name, table_meta in parsed.items()
            if table_meta.get("composite_pk_columns")
        }
    except Exception as exc:
        logger.warning("_get_composite_pk_tables: failed to parse schema '%s': %s", schema_path, exc)
        return set()



def _safe_ydata_html(df: pd.DataFrame | None, minimal: bool = True) -> str:
    if df is None:
        return (
            "<!doctype html><html><body>"
            "<h1>Statistical profile</h1>"
            "<p>Multi-table statistical details are available in the JSON artifacts.</p>"
            "</body></html>"
        )
    try:
        return run_profiling_html(df, minimal=minimal)
    except Exception as exc:
        return (
            "<!doctype html><html><body>"
            "<h1>Statistical profile unavailable</h1>"
            f"<p>{html_lib.escape(str(exc))}</p>"
            "</body></html>"
        )


def _profile_artifact_fragment(profiles: list[dict[str, str]]) -> str:
    if not profiles:
        return (
            "<!-- smart-eda-profile-fragment -->"
            "<section class=\"profile-viewer profile-export-panel\" aria-label=\"Statistical profile exports\">"
            "<div class=\"profile-viewer-header\">"
            "<div><p class=\"eyebrow\">Profile Export</p><h2>No standalone profile was generated</h2></div>"
            "<span class=\"profile-badge\">JSON artifacts available</span>"
            "</div>"
            "<div class=\"profile-export-body\"><p>Statistical details are available in the JSON artifacts for this run.</p></div>"
            "</section>"
        )

    cards = []
    for profile in profiles:
        file_name = profile["file_name"]
        table_name = profile["table_name"]
        rows = profile["rows"]
        columns = profile["columns"]
        cards.append(
            "<article class=\"profile-export-card\">"
            "<div>"
            f"<span>{html_lib.escape(table_name)}</span>"
            f"<strong>{html_lib.escape(file_name)}</strong>"
            f"<p>{html_lib.escape(rows)} rows · {html_lib.escape(columns)} columns</p>"
            "</div>"
            f"<a href=\"{html_lib.escape(file_name)}\" target=\"_blank\" rel=\"noopener\">Open profile</a>"
            "</article>"
        )
    return (
        "<!-- smart-eda-profile-fragment -->"
        "<section class=\"profile-viewer profile-export-panel\" aria-label=\"Statistical profile exports\">"
        "<div class=\"profile-viewer-header\">"
        "<div><p class=\"eyebrow\">Profile Exports</p><h2>Standalone Statistical Profiles</h2></div>"
        "<span class=\"profile-badge\">opens separately</span>"
        "</div>"
        "<div class=\"profile-export-body\">"
        "<p>Full ydata profiles are exported as separate HTML files to keep the Smart EDA report focused and avoid nested reports.</p>"
        "<div class=\"profile-export-grid\">"
        f"{''.join(cards)}"
        "</div>"
        "</div>"
        "</section>"
    )


def _write_single_ydata_profile(df: pd.DataFrame, out: Path, minimal: bool = True) -> str:
    file_name = "statistical_profile.html"
    (out / file_name).write_text(_safe_ydata_html(df, minimal=minimal), encoding="utf-8")
    return _profile_artifact_fragment([{
        "table_name": "dataset",
        "file_name": file_name,
        "rows": str(len(df)),
        "columns": str(len(df.columns)),
    }])


def _write_multi_ydata_profiles(tables: dict[str, pd.DataFrame], out: Path, minimal: bool = True) -> str:
    profiles: list[dict[str, str]] = []
    for table_name, df in tables.items():
        safe_name = _safe_artifact_stem(table_name)
        file_name = f"statistical_profile_{safe_name}.html"
        (out / file_name).write_text(_safe_ydata_html(df, minimal=minimal), encoding="utf-8")
        profiles.append({
            "table_name": table_name,
            "file_name": file_name,
            "rows": str(len(df)),
            "columns": str(len(df.columns)),
        })
    return _profile_artifact_fragment(profiles)


def _display_feature(feature: str) -> str:
    return feature.replace("__via__", ".via.").replace("__", ".")


def _correlation_table_html(
    title: str,
    source: str,
    correlations: list[CrossTableCorrelation],
) -> str:
    if not correlations:
        return ""
    rows = []
    for corr in correlations[:25]:
        rows.append(
            "<tr>"
            f"<td>{html_lib.escape(source)}</td>"
            f"<td>{corr.coefficient:.4f}</td>"
            f"<td>{html_lib.escape(corr.method)}</td>"
            f"<td>{corr.n:,}</td>"
            f"<td><code>{html_lib.escape(_display_feature(corr.left_feature))}</code></td>"
            f"<td><code>{html_lib.escape(_display_feature(corr.right_feature))}</code></td>"
            "</tr>"
        )
    return (
        f"<h3>{html_lib.escape(title)}</h3>"
        "<div class=\"cross-table-correlation-table\">"
        "<table>"
        "<thead><tr>"
        "<th>Source</th><th>Coefficient</th><th>Method</th><th>N</th><th>Left feature</th><th>Right feature</th>"
        "</tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "</div>"
    )


_WARNING_TRANSLATIONS: dict[str, str] = {
    # L3b planner
    "L3b planner skipped": "Bộ lập kế hoạch tương quan đã bỏ qua",
    "SMART_EDA_L3B_PROVIDER is not openai": "Chế độ deterministic — không dùng LLM để lập kế hoạch tương quan",
    "planner_skipped_inside_running_event_loop": "Bộ lập kế hoạch bỏ qua (chạy trong async loop)",
    # Numeric features
    "Not enough numeric cross-table features for Pearson correlation":
        "Không đủ cột số để tính tương quan Pearson giữa các bảng",
    "No cross-table numeric correlations passed the MVP filters":
        "Không có cặp tương quan nào vượt ngưỡng lọc tối thiểu",
    "No cross-table numeric correlations passed the current filters":
        "Không tìm thấy tương quan số nào đáng kể giữa các bảng",
    # Join / fanout
    "Unsafe fan-out detected": "Phát hiện fan-out không an toàn khi JOIN",
    "Removed": "Đã loại bỏ",
    "exact duplicate row": "hàng trùng lặp",
    # Status codes
    "skipped_no_direct_relationships": "Bỏ qua — không có quan hệ trực tiếp",
    "skipped_no_tables": "Bỏ qua — không có bảng nào được nạp",
    "completed": "Hoàn thành",
}

_STATUS_TRANSLATIONS: dict[str, str] = {
    "completed": "Hoàn thành",
    "skipped_no_direct_relationships": "Bỏ qua — thiếu quan hệ trực tiếp",
    "skipped_no_tables": "Bỏ qua — không có bảng",
    "skipped_no_schema": "Bỏ qua — chưa có schema",
}

_HIDE_WARNING_PREFIXES = (
    "L3b planner skipped",          # debug-level count
    "L3b planner produced",         # debug-level count
    "planned_pair_skipped:",        # internal detail
    "Fact table selected automatically",   # info-level
)


def _translate_warning(raw: str) -> str | None:
    """Map a raw English warning string to a user-friendly Vietnamese string.

    Returns None if the warning is debug/internal and should be hidden.
    """
    for prefix in _HIDE_WARNING_PREFIXES:
        if raw.startswith(prefix):
            return None
    for key, translated in _WARNING_TRANSLATIONS.items():
        if key in raw:
            return translated + (f": {raw.split(':', 1)[1].strip()}" if ":" in raw else "")
    # Keep non-matched warnings but prefix them clearly
    return f"⚠ {raw}"


def _cross_table_correlation_fragment(analysis: CrossTableAnalysis) -> str:
    planned = _correlation_table_html(
        "Planned Aggregate Correlations",
        "llm_validated_plan",
        analysis.planned_correlations,
    )
    scanned = _correlation_table_html(
        "Safe-Join Numeric Correlations",
        "safe_join_scan",
        analysis.correlations,
    )
    body = planned + scanned
    if not body:
        body = (
            "<p>Không tìm thấy tương quan số đáng kể giữa các bảng trong lần chạy này. "
            "Điều này thường xảy ra khi bộ dữ liệu chủ yếu chứa dữ liệu dạng văn bản (text) "
            "và không có cột số để tính Pearson correlation.</p>"
        )

    warnings_html = ""
    if analysis.warnings:
        translated = [_translate_warning(w) for w in analysis.warnings[:12]]
        visible = [t for t in translated if t is not None]
        if visible:
            items = "".join(f"<li>{html_lib.escape(w)}</li>" for w in visible)
            warnings_html = f'<ul class="insight-list">{items}</ul>'

    status_label = _STATUS_TRANSLATIONS.get(analysis.status, analysis.status)

    return (
        "<!-- smart-eda-cross-correlation -->"
        '<section class="profile-viewer profile-export-panel" aria-label="Cross-table correlations">'
        '<div class="profile-viewer-header">'
        '<div><p class="eyebrow">Cross-Table</p><h2>Tương Quan Liên Bảng</h2></div>'
        f'<span class="profile-badge">{html_lib.escape(status_label)}</span>'
        "</div>"
        '<div class="profile-export-body">'
        "<p>Phân tích kiểm tra mức độ tương quan giữa các cột số ở các bảng có quan hệ FK/PK. "
        "Hệ thống thực hiện JOIN an toàn (không gây fan-out) trước khi tính hệ số Pearson.</p>"
        f"{body}"
        f"{warnings_html}"
        "</div>"
        "</section>"
        "<!-- /smart-eda-cross-correlation -->"
    )


def _write_cross_table_correlations_csv(analysis: CrossTableAnalysis, out: Path) -> Path:
    rows = []
    for source, correlations in (
        ("llm_validated_plan", analysis.planned_correlations),
        ("safe_join_scan", analysis.correlations),
    ):
        for corr in correlations:
            rows.append({
                "source": source,
                "left_feature": corr.left_feature,
                "right_feature": corr.right_feature,
                "left_table": corr.left_table,
                "right_table": corr.right_table,
                "method": corr.method,
                "coefficient": corr.coefficient,
                "abs_coefficient": corr.abs_coefficient,
                "n": corr.n,
            })
    path = out / "cross_table_correlations.csv"
    pd.DataFrame(rows, columns=[
        "source",
        "left_feature",
        "right_feature",
        "left_table",
        "right_table",
        "method",
        "coefficient",
        "abs_coefficient",
        "n",
    ]).to_csv(path, index=False)
    return path


def _profile_data_quality(
    data_path: str,
    out: Path,
    artifact_prefix: str,
    profiling_minimal: bool = False,
) -> tuple[DataQualityFindings, list]:
    df = load_any(data_path)
    profile = run_profiling(df, minimal=profiling_minimal)
    anomaly_result = run_anomaly_detection(df)
    mechs = detect_missingness(df)
    findings = build_data_quality_findings(
        file_name=Path(data_path).name,
        df=df,
        profile_result=profile,
        anomaly_result=anomaly_result,
        mechs=mechs,
        artifact_dir=out,
        artifact_prefix=artifact_prefix,
    )
    findings = attach_diagnostic_charts(
        findings,
        df,
        anomaly_result,
        str(out),
        artifact_prefix=artifact_prefix,
    )
    findings = attach_overview_charts(
        findings,
        df,
        str(out),
        artifact_prefix=artifact_prefix,
    )
    table = load_calibrator_table()
    col_findings = calibrate_columns(findings.columns, table, n=findings.dataset_meta.n)
    all_dq = apply_compound(findings.anomalies + col_findings)
    findings.anomalies = all_dq
    return findings, all_dq


def _prefix_issue(issue: AnomalyRecord, table_name: str) -> AnomalyRecord:
    if issue.affected_column:
        # Column-level anomaly: prefix "table.column"
        affected_column = f"{table_name}.{issue.affected_column}"
    else:
        # Row-level anomaly (e.g. OUTLIER_ENSEMBLE): set to table_name so dispatcher knows the table
        affected_column = table_name
    return issue.model_copy(update={
        "description": f"[{table_name}] {issue.description}",
        "affected_column": affected_column,
    })


def _combine_multi_findings(
    table_findings: dict[str, DataQualityFindings],
    meta: DatasetMeta,
) -> DataQualityFindings:
    columns = {}
    anomalies = []
    overview_charts = {}
    for table_name, findings in table_findings.items():
        for column, stats in findings.columns.items():
            columns[f"{table_name}.{column}"] = stats
        anomalies.extend(_prefix_issue(issue, table_name) for issue in findings.anomalies)
        for chart_key, chart_path in findings.dataset_meta.overview_charts.items():
            overview_charts[f"{table_name}.{chart_key}"] = chart_path
    return DataQualityFindings(
        dataset_meta=meta.model_copy(update={"overview_charts": overview_charts}),
        columns=columns,
        anomalies=anomalies,
    )


def _multi_data_quality_bundle(
    table_sources: dict[str, str],
    table_findings: dict[str, DataQualityFindings],
    combined: DataQualityFindings,
) -> dict:
    return {
        "schema_version": "multi_table_data_quality_v1",
        "summary": {
            "total_tables": len(table_findings),
            "total_rows": combined.dataset_meta.n,
            "total_columns": combined.dataset_meta.n_var,
            "total_anomalies": sum(len(f.anomalies) for f in table_findings.values()),
            "p_cells_missing": combined.dataset_meta.p_cells_missing,
            "n_duplicates": combined.dataset_meta.n_duplicates,
            "p_duplicates": combined.dataset_meta.p_duplicates,
        },
        "tables": {
            table_name: {
                "source_file": table_sources[table_name],
                "findings": json.loads(findings.model_dump_json()),
            }
            for table_name, findings in table_findings.items()
        },
        "combined_findings": json.loads(combined.model_dump_json()),
    }


def run(
    data_path: str,
    out_dir: str = "output",
    schema_path: str | None = None,
    profiling_minimal: bool = False,
    job_id: str | None = None,
) -> dict:
    bus = get_bus(job_id) if job_id else NullBus()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    bus.emit("📥 Đọc dữ liệu", 0.05, detail=Path(data_path).name, status="running", step_id="ingest")
    logger.info("[L0] Đọc dữ liệu: %s", data_path)
    df = load_any(data_path)
    bus.emit("📊 Phân tích thống kê (YData)", 0.15, detail=f"{len(df):,} dòng · {len(df.columns)} cột", status="running", step_id="ydata")
    logger.info("[L1] Profiling YData: %s dòng, %s cột", len(df), len(df.columns))
    profile = run_profiling(df, minimal=profiling_minimal)
    bus.emit("⚠️ Phát hiện dị biệt (PyOD)", 0.28, status="running", step_id="anomaly")
    logger.info("[L2] Phát hiện anomaly (PyOD)")
    anomaly_result = run_anomaly_detection(df)

    # Layer 2.5a — Missingness classification (MCAR/MAR/MNAR)
    bus.emit("🔍 Phân loại missing values", 0.36, status="running", step_id="missing")
    logger.info("[L2.5a] Phân loại missing values (MCAR/MAR/MNAR)")
    # Pass schema_cols so STRUCTURAL_ABSENT heuristic can check optional fields.
    _schema_cols_for_mech: dict | None = None
    if schema_path:
        try:
            _parsed_mech = parse_schema(schema_path)["tables"]
            _stem_mech = Path(data_path).stem.lower()
            _tbl_mech = next((v for k, v in _parsed_mech.items() if k.lower() == _stem_mech), None)
            _schema_cols_for_mech = _tbl_mech.get("columns") if _tbl_mech else None
        except Exception:
            _schema_cols_for_mech = None
    mechs = detect_missingness(df, schema_cols=_schema_cols_for_mech)

    # Layer 3 — Build findings JSON
    findings = build_data_quality_findings(
        file_name=Path(data_path).name,
        df=df,
        profile_result=profile,
        anomaly_result=anomaly_result,
        mechs=mechs,
        artifact_dir=out,
        artifact_prefix=_safe_artifact_stem(data_path),
    )
    findings = attach_diagnostic_charts(
        findings,
        df,
        anomaly_result,
        str(out),
        artifact_prefix=_safe_artifact_stem(data_path),
    )
    findings = attach_overview_charts(
        findings,
        df,
        str(out),
        artifact_prefix=_safe_artifact_stem(data_path),
    )

    bus.emit("📐 Hiệu chỉnh & tổng hợp severity", 0.52, status="running", step_id="severity")
    logger.info("[L2.5] Calibrate & compound severity")
    table = load_calibrator_table()
    col_findings = calibrate_columns(findings.columns, table, n=findings.dataset_meta.n)
    all_dq = apply_compound(findings.anomalies + col_findings)

    # ── Single-table fix ────────────────────────────────────────────────────
    # In multi-table mode, _prefix_issue() adds "tablename.column" prefix so
    # dispatcher._affected_table() can extract the table name from the dot.
    # In single-table mode this prefix is absent, so each column name becomes
    # its own "table" → each column gets its own tab in the report.
    # Fix: apply the same prefix here using the dataset file stem.
    dataset_stem = _safe_artifact_stem(data_path)
    all_dq = [_prefix_issue(issue, dataset_stem) for issue in all_dq]
    findings.anomalies = all_dq
    # ────────────────────────────────────────────────────────────────────────

    # Schema path (optional)
    integrity_errors = None
    schema = None
    output_paths = {}
    if schema_path:
        schema = build_schema_findings(df, data_path, schema_path)
        schema_out = out / "schema_evaluation_findings.json"
        schema_out.write_text(schema.model_dump_json(indent=2), encoding="utf-8")
        print(f"schema_evaluation_findings.json → {schema_out}")
        output_paths["schema_path"] = str(schema_out)
        integrity_errors = schema.integrity_errors

    verdict = aggregate(findings.dataset_meta, all_dq, integrity_errors=integrity_errors)

    dq_path = out / "data_quality_findings.json"
    verdict_path = out / "dataset_verdict.json"
    report_path = out / "summary_report.md"
    l4_report_path = out / "l4_report.md"
    guardrail_path = out / "guardrail_report.json"
    html_report_path = out / "smart_eda_report.html"
    bus.emit("🧠 Phân tích LLM (Senior Data Scientist)", 0.78, status="running", step_id="llm")
    logger.info("[L4] Gọi LLM — Senior Data Scientist report")
    l4_report, guardrail_report, multi_agent_result = generate_multi_agent_report(findings, verdict, schema)
    bus.emit("📄 Xuất báo cáo HTML", 0.92, status="running", step_id="export")
    logger.info("[L4] Xuất báo cáo HTML")
    profile_fragment = _write_single_ydata_profile(df, out, minimal=profiling_minimal)
    # Phase 3: Build data samples (5 rows) for each table tab
    from reporting.html_merger import _build_data_sample_html as _sample_html
    _tbl_stem = Path(str(data_path)).stem
    _data_samples = {_tbl_stem: _sample_html(df, _tbl_stem)}

    smart_html = merge_to_tabbed_html(
        multi_agent_result,
        verdict,
        profile_fragment,
        guardrail_status=guardrail_report.status,
        model_info=guardrail_report.provider,
        all_table_names=[_tbl_stem],
        out_dir=str(out),
        findings=findings,
        table_data_samples=_data_samples,
    )
    dq_path.write_text(findings.model_dump_json(indent=2), encoding="utf-8")
    verdict_path.write_text(verdict.model_dump_json(indent=2), encoding="utf-8")
    report_path.write_text(render_markdown_report(findings, verdict, schema), encoding="utf-8")
    l4_report_path.write_text(l4_report, encoding="utf-8")
    guardrail_path.write_text(guardrail_report.model_dump_json(indent=2), encoding="utf-8")
    html_report_path.write_text(smart_html, encoding="utf-8")
    artifact_manifest_path = _write_artifact_manifest(out)

    print(f"data_quality_findings.json -> {dq_path}")
    print(f"dataset_verdict.json       -> {verdict_path}")
    print(f"summary_report.md          -> {report_path}")
    print(f"l4_report.md               -> {l4_report_path}")
    print(f"guardrail_report.json      -> {guardrail_path}")
    print(f"smart_eda_report.html      -> {html_report_path}")
    print(f"artifact_manifest.json     -> {artifact_manifest_path}")
    output_paths.update({
        "dq_path": str(dq_path),
        "verdict_path": str(verdict_path),
        "report_path": str(report_path),
        "l4_report_path": str(l4_report_path),
        "guardrail_path": str(guardrail_path),
        "html_report_path": str(html_report_path),
        "artifact_manifest_path": str(artifact_manifest_path),
    })
    return output_paths


def run_multi(
    data_paths: list,
    out_dir: str = "output",
    schema_path: str | None = None,
    confirmed_schema_path: str | None = None,
    fact_table: str | None = None,
    profiling_minimal: bool = False,
    job_id: str | None = None,
) -> dict:
    """Multi-table mode: N data files + optional schema -> schema findings + verdict.
    When schema_path is omitted, table schemas and relationships are inferred from data.
    Data-quality profiling is run per table and summarized across all loaded tables.
    """
    bus = get_bus(job_id) if job_id else NullBus()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    bus.emit("📥 Đọc & xác thực dữ liệu", 0.05, detail=f"{len(data_paths)} file(s)", status="running", step_id="ingest")
    logger.info("[L0] Đọc & xác thực %d files", len(data_paths))
    schema = validate_schema_multi(data_paths, schema_path)

    bus.emit("🗂️ Phân tích schema", 0.08, detail=f"{schema.schema_meta.total_tables} bảng", status="done", step_id="schema")
    logger.info("[L2] Schema: %d bảng, %d relationships",
                schema.schema_meta.total_tables, len(schema.relationships))
    table_names = _table_names_for_paths(data_paths)
    table_sources = {
        table_name: Path(path).name
        for table_name, path in zip(table_names, data_paths)
    }
    table_findings: dict[str, DataQualityFindings] = {}
    n_tables = len(data_paths)
    for i, (table_name, path) in enumerate(zip(table_names, data_paths)):
        pct_ydata = 0.12 + (i / n_tables) * 0.13   # 12% → 25%
        bus.emit(
            f"📊 Thống kê YData — {table_name}",
            pct_ydata,
            detail=Path(path).name,
            status="running",
            step_id="ydata",
        )
        logger.info("[L1] YData profiling — %s (%s)", table_name, Path(path).name)
        findings, _dq_findings = _profile_data_quality(
            str(path),
            out,
            artifact_prefix=table_name,
            profiling_minimal=profiling_minimal,
        )
        n_rows = findings.dataset_meta.n
        n_anomalies = len(findings.anomalies)
        bus.emit(
            f"⚠️ Dị biệt (PyOD) — {table_name}",
            0.25 + (i / n_tables) * 0.08,  # 25% → 33%
            detail=f"{n_rows:,} dòng · {n_anomalies} anomaly",
            status="done",
            step_id="anomaly",
        )
        logger.info("[L2] Anomaly — %s: %d dòng, %d anomalies", table_name, n_rows, n_anomalies)
        table_findings[table_name] = findings

    total_n = sum(f.dataset_meta.n for f in table_findings.values())
    total_original_n = sum(f.dataset_meta.original_n or f.dataset_meta.n for f in table_findings.values())
    total_vars = sum(f.dataset_meta.n_var for f in table_findings.values())
    total_cells = sum(f.dataset_meta.n * f.dataset_meta.n_var for f in table_findings.values())
    missing_cells = sum(
        f.dataset_meta.p_cells_missing * f.dataset_meta.n * f.dataset_meta.n_var
        for f in table_findings.values()
    )
    total_duplicates = sum(f.dataset_meta.n_duplicates for f in table_findings.values())
    meta = DatasetMeta(
        file_name=Path(schema_path).name if schema_path else "inferred_from_data",
        n=total_n,
        n_var=total_vars,
        memory_size=0,
        p_cells_missing=round(missing_cells / total_cells, 6) if total_cells else 0.0,
        n_duplicates=total_duplicates,
        p_duplicates=round(total_duplicates / total_n, 6) if total_n else 0.0,
        is_sampled=any(f.dataset_meta.is_sampled for f in table_findings.values()),
        original_n=total_original_n,
        sample_n=total_n,
        sample_method="per_table_random" if any(f.dataset_meta.is_sampled for f in table_findings.values()) else None,
        sample_seed=42 if any(f.dataset_meta.is_sampled for f in table_findings.values()) else None,
    )
    combined_findings = _combine_multi_findings(table_findings, meta)
    bus.emit("📐 Tổng hợp & hiệu chỉnh severity", 0.36, status="running", step_id="severity")
    logger.info("[L2.5] Tổng hợp severity & compound scoring")

    cross_tables = _load_tables_for_cross_analysis(data_paths, schema_path)
    bus.emit("🔗 Dựng đồ thị quan hệ (Graph Engine)", 0.45, status="running", step_id="graph")
    logger.info("[L2C] Graph Engine: dựng đồ thị quan hệ")
    schema_gate = apply_schema_gate(schema, cross_tables, confirmed_schema_path, fact_table)
    gated_schema = schema.model_copy(update={"relationships": schema_gate.relationships})
    graph_result = reconstruct_graph(
        cross_tables,
        gated_schema,
        composite_pk_tables=_get_composite_pk_tables(schema_path),
    )

    graph_relationships = accepted_relationships_from_graph(schema_gate.relationships, graph_result)
    bus.emit(
        "🔑 Kiểm tra toàn vẹn FK/PK (Schema Gate)",
        0.52,
        detail=f"{len(graph_relationships)} relationship(s) · {len(schema_gate.warnings)} cảnh báo",
        status="done",
        step_id="gate",
    )
    logger.info("[L2B5] Schema Gate: %d relationships, %d cảnh báo, %d integrity errors",
                len(graph_relationships), len(schema_gate.warnings), len(graph_result.integrity_errors))
    schema_meta_for_output = schema.schema_meta.model_copy(update={
        "total_relationships": len(graph_relationships),
    })
    schema_for_output = schema.model_copy(update={
        "schema_meta": schema_meta_for_output,
        "relationships": graph_relationships,
        "integrity_errors": [*schema.integrity_errors, *graph_result.integrity_errors],
    })
    schema_gate_for_output = schema_gate.model_copy(update={
        "relationships": graph_relationships,
        "warnings": [*schema_gate.warnings, *graph_result.warnings],
    })
    bus.emit("⚖️ Tổng hợp verdict chất lượng", 0.60, status="running", step_id="verdict")
    logger.info("[L3] Tổng hợp verdict chất lượng dữ liệu")
    verdict = aggregate(
        combined_findings.dataset_meta,
        dq_findings=combined_findings.anomalies,
        integrity_errors=schema_for_output.integrity_errors,
    )
    logger.info("[L3] Verdict: %s", verdict.verdict)
    bus.emit("📈 Phân tích tương quan liên bảng", 0.65, status="running", step_id="corr")
    logger.info("[L4] Cross-table analysis")
    cross_table_analysis = run_cross_table_analysis(
        cross_tables,
        graph_relationships,
        out,
        fact_table=schema_gate.fact_table,
    )

    # Vẽ chart sơ đồ quan hệ và gắn vào verdict.dataset_meta.overview_charts
    bus.emit("🎨 Vẽ biểu đồ & sơ đồ quan hệ", 0.72, status="running", step_id="charts")
    logger.info("[L3.5] Vẽ biểu đồ quan hệ và diagnostic charts")
    network_chart_file = draw_relationship_network(
        schema_for_output, str(out), artifact_prefix="multi"
    )
    stacked_bar_file = draw_stacked_bar_issues(
        verdict, str(out), artifact_prefix="multi"
    )
    corr_chart_file = draw_top_correlations_bar(
        cross_table_analysis, str(out), artifact_prefix="multi"
    )
    extra_charts: dict[str, str] = {}
    if network_chart_file:
        extra_charts["relationship_network"] = network_chart_file
    if stacked_bar_file:
        extra_charts["stacked_bar_issues"] = stacked_bar_file
    if corr_chart_file:
        extra_charts["top_correlations_bar"] = corr_chart_file
    if extra_charts:
        updated_meta = verdict.dataset_meta.model_copy(
            update={"overview_charts": {**verdict.dataset_meta.overview_charts, **extra_charts}}
        )
        verdict = verdict.model_copy(update={"dataset_meta": updated_meta})

    dq_path = out / "data_quality_findings.json"
    schema_out = out / "schema_evaluation_findings.json"
    schema_gate_path = out / "schema_gate.json"
    graph_path = out / "relationship_graph.json"
    cross_table_path = out / "cross_table_analysis.json"
    cross_table_correlations_path = _write_cross_table_correlations_csv(cross_table_analysis, out)
    verdict_path = out / "dataset_verdict.json"
    report_path = out / "summary_report.md"
    l4_report_path = out / "l4_report.md"
    guardrail_path = out / "guardrail_report.json"
    html_report_path = out / "smart_eda_report.html"
    bus.emit("🧠 Phân tích LLM (Senior Data Scientist)", 0.80, status="running", step_id="llm")
    logger.info("[L4] Gọi LLM — Senior Data Scientist report")
    l4_report, guardrail_report, multi_agent_result = generate_multi_agent_report(
        combined_findings,
        verdict,
        schema_for_output,
        cross_table_analysis,
    )
    logger.info("[L4] LLM xong — guardrail: %s", guardrail_report.status)
    bus.emit("📄 Xuất báo cáo HTML", 0.92, status="running", step_id="export")
    logger.info("[L4] Xuất báo cáo HTML")
    profile_fragment = (
        _write_multi_ydata_profiles(cross_tables, out, minimal=profiling_minimal)
        + _cross_table_correlation_fragment(cross_table_analysis)
    )
    # Phase 3: Build data samples (5 rows) for each table tab
    from reporting.html_merger import _build_data_sample_html as _sample_html_mt
    _data_samples_mt = {
        tbl: _sample_html_mt(tbl_df, tbl)
        for tbl, tbl_df in cross_tables.items()
    }

    smart_html = merge_to_tabbed_html(
        multi_agent_result,
        verdict,
        profile_fragment,
        guardrail_status=guardrail_report.status,
        model_info=guardrail_report.provider,
        all_table_names=list(cross_tables.keys()),
        out_dir=str(out),
        findings=combined_findings,
        table_data_samples=_data_samples_mt,
    )
    dq_path.write_text(
        json.dumps(
            _multi_data_quality_bundle(table_sources, table_findings, combined_findings),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    schema_out.write_text(schema_for_output.model_dump_json(indent=2), encoding="utf-8")
    schema_gate_path.write_text(schema_gate_for_output.model_dump_json(indent=2), encoding="utf-8")
    graph_path.write_text(graph_result.model_dump_json(indent=2), encoding="utf-8")
    cross_table_path.write_text(cross_table_analysis.model_dump_json(indent=2), encoding="utf-8")
    verdict_path.write_text(verdict.model_dump_json(indent=2), encoding="utf-8")
    report_path.write_text(render_markdown_report(combined_findings, verdict, schema_for_output), encoding="utf-8")
    l4_report_path.write_text(l4_report, encoding="utf-8")
    guardrail_path.write_text(guardrail_report.model_dump_json(indent=2), encoding="utf-8")
    html_report_path.write_text(smart_html, encoding="utf-8")
    artifact_manifest_path = _write_artifact_manifest(out)

    logger.info("[OUTPUT] data_quality_findings.json       -> %s", dq_path)
    logger.info("[OUTPUT] schema_evaluation_findings.json  -> %s", schema_out)
    logger.info("[OUTPUT] schema_gate.json                 -> %s", schema_gate_path)
    logger.info("[OUTPUT] relationship_graph.json          -> %s", graph_path)
    logger.info("[OUTPUT] cross_table_analysis.json        -> %s", cross_table_path)
    logger.info("[OUTPUT] dataset_verdict.json             -> %s", verdict_path)
    logger.info("[OUTPUT] smart_eda_report.html            -> %s", html_report_path)
    logger.info("[DONE]   Pipeline hoàn thành. Verdict: %s — %d issues",
                verdict.verdict, verdict.summary.total_issues if verdict.summary else 0)
    return {
        "dq_path": str(dq_path),
        "schema_path": str(schema_out),
        "schema_gate_path": str(schema_gate_path),
        "graph_path": str(graph_path),
        "cross_table_path": str(cross_table_path),
        "cross_table_correlations_path": str(cross_table_correlations_path),
        "verdict_path": str(verdict_path),
        "report_path": str(report_path),
        "l4_report_path": str(l4_report_path),
        "guardrail_path": str(guardrail_path),
        "html_report_path": str(html_report_path),
        "artifact_manifest_path": str(artifact_manifest_path),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py <data_path> [out_dir] [schema.dbml|schema.sql]")
        print("       Supported data: .csv, .xlsx, .xls, .parquet, .json, .jsonl, .ndjson")
        print("       python run_pipeline.py --multi <data1> <data2> ... [--schema <file.dbml|file.sql>] [--confirmed-schema <file.json>] [--fact-table <table>] [--minimal-profile] [--out <dir>]")
        sys.exit(1)

    if sys.argv[1] == "--multi":
        args = sys.argv[2:]
        out_arg = "output"
        if "--out" in args:
            out_idx = args.index("--out")
            out_arg = args[out_idx + 1]
            del args[out_idx:out_idx + 2]
        schema_arg = None
        if "--schema" in args:
            schema_idx = args.index("--schema")
            schema_arg = args[schema_idx + 1]
            del args[schema_idx:schema_idx + 2]
        confirmed_schema_arg = None
        if "--confirmed-schema" in args:
            confirmed_idx = args.index("--confirmed-schema")
            confirmed_schema_arg = args[confirmed_idx + 1]
            del args[confirmed_idx:confirmed_idx + 2]
        fact_table_arg = None
        if "--fact-table" in args:
            fact_idx = args.index("--fact-table")
            fact_table_arg = args[fact_idx + 1]
            del args[fact_idx:fact_idx + 2]
        profiling_minimal_arg = False
        if "--minimal-profile" in args:
            profiling_minimal_arg = True
            args.remove("--minimal-profile")
        data_args = args
        if len(data_args) < 2:
            print("Error: --multi mode requires at least two data files")
            sys.exit(1)
        run_multi(
            data_args,
            out_arg,
            schema_arg,
            confirmed_schema_arg,
            fact_table_arg,
            profiling_minimal=profiling_minimal_arg,
        )
    else:
        data_arg = sys.argv[1]
        out_arg = sys.argv[2] if len(sys.argv) > 2 else "output"
        schema_arg = sys.argv[3] if len(sys.argv) > 3 else None
        run(data_arg, out_arg, schema_arg)
