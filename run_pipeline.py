"""Full EDA pipeline: data file -> findings JSON + verdict [+ schema findings]."""
import json
import html as html_lib
import sys
import warnings
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")

SRC = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC))

from ingestion.registry import load_any
from ingestion.schema_reader import parse_schema
from engines.profiling_engine import run_profiling, run_profiling_html
from engines.anomaly_engine import run_anomaly_detection
from engines.visualizer import attach_diagnostic_charts
from engines.cross_table_engine import run_cross_table_analysis
from engines.graph_engine import accepted_relationships_from_graph, reconstruct_graph
from engines.schema_gate import apply_schema_gate
from engines.schema_engine import (
    build_schema_findings, load_tables, load_tables_by_path, validate_schema_multi,
)
from ontology.findings_builder import build_data_quality_findings
from ontology.models import (
    AnomalyRecord, ArtifactManifest, ArtifactRecord, DataQualityFindings,
    DatasetMeta,
)
from severity.calibrator import calibrate_columns, load_calibrator_table
from severity.compound import apply_compound
from severity.aggregator import aggregate
from severity.missingness import detect_missingness
from reporting.summary_renderer import render_markdown_report
from reporting.l4_report import generate_multi_agent_report
from reporting.html_merger import merge_to_tabbed_html


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
    if path.name == "cross_table_analysis.json":
        return "cross_table_analysis_json"
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


def _multi_table_ydata_html(tables: dict[str, pd.DataFrame], minimal: bool = True) -> str:
    if not tables:
        return _safe_ydata_html(None, minimal=minimal)

    sections = [
        "<!doctype html><html><head><meta charset=\"utf-8\">",
        "<style>",
        "body{font-family:Arial,sans-serif;margin:0;background:#f8fafc;color:#111827;}",
        "header{padding:16px 20px;background:#ffffff;border-bottom:1px solid #e5e7eb;}",
        "main{padding:16px 20px;display:grid;gap:18px;}",
        "section{background:#ffffff;border:1px solid #e5e7eb;border-radius:8px;overflow:hidden;}",
        "h1{font-size:20px;margin:0;} h2{font-size:16px;margin:0;padding:12px 14px;border-bottom:1px solid #e5e7eb;}",
        "iframe{width:100%;height:720px;border:0;display:block;background:white;}",
        "</style></head><body>",
        f"<header><h1>Statistical profiles ({len(tables)} tables)</h1></header><main>",
    ]
    for table_name, df in tables.items():
        profile_html = _safe_ydata_html(df, minimal=minimal)
        sections.extend([
            "<section>",
            f"<h2>{html_lib.escape(table_name)}</h2>",
            f"<iframe title=\"{html_lib.escape(table_name)} profile\" srcdoc=\"{html_lib.escape(profile_html, quote=True)}\"></iframe>",
            "</section>",
        ])
    sections.append("</main></body></html>")
    return "".join(sections)


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
    table = load_calibrator_table()
    col_findings = calibrate_columns(findings.columns, table, n=findings.dataset_meta.n)
    all_dq = apply_compound(findings.anomalies + col_findings)
    findings.anomalies = all_dq
    return findings, all_dq


def _prefix_issue(issue: AnomalyRecord, table_name: str) -> AnomalyRecord:
    affected_column = (
        f"{table_name}.{issue.affected_column}"
        if issue.affected_column
        else None
    )
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
    for table_name, findings in table_findings.items():
        for column, stats in findings.columns.items():
            columns[f"{table_name}.{column}"] = stats
        anomalies.extend(_prefix_issue(issue, table_name) for issue in findings.anomalies)
    return DataQualityFindings(dataset_meta=meta, columns=columns, anomalies=anomalies)


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
) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    df = load_any(data_path)
    profile = run_profiling(df, minimal=profiling_minimal)
    anomaly_result = run_anomaly_detection(df)

    # Layer 2.5a — Missingness classification (MCAR/MAR/MNAR)
    mechs = detect_missingness(df)

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

    table = load_calibrator_table()
    col_findings = calibrate_columns(findings.columns, table, n=findings.dataset_meta.n)
    all_dq = apply_compound(findings.anomalies + col_findings)
    findings.anomalies = all_dq

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
    l4_report, guardrail_report, multi_agent_result = generate_multi_agent_report(findings, verdict, schema)
    smart_html = merge_to_tabbed_html(
        multi_agent_result,
        verdict,
        _safe_ydata_html(df, minimal=profiling_minimal),
        guardrail_status=guardrail_report.status,
        model_info=guardrail_report.provider,
    )
    dq_path.write_text(findings.model_dump_json(indent=2), encoding="utf-8")
    verdict_path.write_text(verdict.model_dump_json(indent=2), encoding="utf-8")
    report_path.write_text(render_markdown_report(findings, verdict, schema), encoding="utf-8")
    l4_report_path.write_text(l4_report, encoding="utf-8")
    guardrail_path.write_text(guardrail_report.model_dump_json(indent=2), encoding="utf-8")
    html_report_path.write_text(smart_html, encoding="utf-8")
    artifact_manifest_path = _write_artifact_manifest(out)

    print(f"data_quality_findings.json → {dq_path}")
    print(f"dataset_verdict.json       → {verdict_path}")
    print(f"summary_report.md          → {report_path}")
    print(f"l4_report.md               → {l4_report_path}")
    print(f"guardrail_report.json      → {guardrail_path}")
    print(f"smart_eda_report.html      → {html_report_path}")
    print(f"artifact_manifest.json     → {artifact_manifest_path}")
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
) -> dict:
    """Multi-table mode: N data files + optional schema -> schema findings + verdict.
    When schema_path is omitted, table schemas and relationships are inferred from data.
    Data-quality profiling is run per table and summarized across all loaded tables.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    schema = validate_schema_multi(data_paths, schema_path)

    table_names = _table_names_for_paths(data_paths)
    table_sources = {
        table_name: Path(path).name
        for table_name, path in zip(table_names, data_paths)
    }
    table_findings: dict[str, DataQualityFindings] = {}
    for table_name, path in zip(table_names, data_paths):
        findings, _dq_findings = _profile_data_quality(
            str(path),
            out,
            artifact_prefix=table_name,
            profiling_minimal=False,
        )
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

    cross_tables = _load_tables_for_cross_analysis(data_paths, schema_path)
    schema_gate = apply_schema_gate(schema, cross_tables, confirmed_schema_path, fact_table)
    gated_schema = schema.model_copy(update={"relationships": schema_gate.relationships})
    graph_result = reconstruct_graph(cross_tables, gated_schema)
    graph_relationships = accepted_relationships_from_graph(schema_gate.relationships, graph_result)
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
    verdict = aggregate(
        meta,
        dq_findings=combined_findings.anomalies,
        integrity_errors=schema_for_output.integrity_errors,
    )
    cross_table_analysis = run_cross_table_analysis(
        cross_tables,
        graph_relationships,
        out,
        fact_table=schema_gate.fact_table,
    )

    dq_path = out / "data_quality_findings.json"
    schema_out = out / "schema_evaluation_findings.json"
    schema_gate_path = out / "schema_gate.json"
    graph_path = out / "relationship_graph.json"
    cross_table_path = out / "cross_table_analysis.json"
    verdict_path = out / "dataset_verdict.json"
    report_path = out / "summary_report.md"
    l4_report_path = out / "l4_report.md"
    guardrail_path = out / "guardrail_report.json"
    html_report_path = out / "smart_eda_report.html"
    l4_report, guardrail_report, multi_agent_result = generate_multi_agent_report(
        combined_findings,
        verdict,
        schema_for_output,
        cross_table_analysis,
    )
    smart_html = merge_to_tabbed_html(
        multi_agent_result,
        verdict,
        _multi_table_ydata_html(cross_tables, minimal=True),
        guardrail_status=guardrail_report.status,
        model_info=guardrail_report.provider,
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

    print(f"data_quality_findings.json       → {dq_path}")
    print(f"schema_evaluation_findings.json → {schema_out}")
    print(f"schema_gate.json                → {schema_gate_path}")
    print(f"relationship_graph.json         → {graph_path}")
    print(f"cross_table_analysis.json       → {cross_table_path}")
    print(f"dataset_verdict.json            → {verdict_path}")
    print(f"summary_report.md               → {report_path}")
    print(f"l4_report.md                    → {l4_report_path}")
    print(f"guardrail_report.json           → {guardrail_path}")
    print(f"smart_eda_report.html           → {html_report_path}")
    print(f"artifact_manifest.json          → {artifact_manifest_path}")
    return {
        "dq_path": str(dq_path),
        "schema_path": str(schema_out),
        "schema_gate_path": str(schema_gate_path),
        "graph_path": str(graph_path),
        "cross_table_path": str(cross_table_path),
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
        print("       python run_pipeline.py --multi <data1> <data2> ... [--schema <file.dbml|file.sql>] [--confirmed-schema <file.json>] [--fact-table <table>] [--out <dir>]")
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
        data_args = args
        if len(data_args) < 2:
            print("Error: --multi mode requires at least two data files")
            sys.exit(1)
        run_multi(data_args, out_arg, schema_arg, confirmed_schema_arg, fact_table_arg)
    else:
        data_arg = sys.argv[1]
        out_arg = sys.argv[2] if len(sys.argv) > 2 else "output"
        schema_arg = sys.argv[3] if len(sys.argv) > 3 else None
        run(data_arg, out_arg, schema_arg)
