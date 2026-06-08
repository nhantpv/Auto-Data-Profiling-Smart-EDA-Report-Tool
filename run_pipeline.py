"""Full EDA pipeline: data file -> findings JSON + verdict [+ schema findings]."""
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

SRC = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC))

from ingestion.registry import load_any
from engines.profiling_engine import run_profiling
from engines.anomaly_engine import run_anomaly_detection
from engines.schema_engine import build_schema_findings, validate_schema_multi
from ontology.findings_builder import build_data_quality_findings
from ontology.models import AnomalyRecord, DataQualityFindings, DatasetMeta
from severity.calibrator import calibrate_columns, load_calibrator_table
from severity.compound import apply_compound
from severity.aggregator import aggregate
from severity.missingness import detect_missingness
from reporting.summary_renderer import render_markdown_report
from reporting.l4_report import generate_l4_report


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
    table = load_calibrator_table()
    col_findings = calibrate_columns(findings.columns, table, n=findings.dataset_meta.n)
    all_dq = apply_compound(findings.anomalies + col_findings)
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

    table = load_calibrator_table()
    col_findings = calibrate_columns(findings.columns, table, n=findings.dataset_meta.n)
    all_dq = apply_compound(findings.anomalies + col_findings)

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
    l4_report, guardrail_report = generate_l4_report(findings, verdict, schema)
    dq_path.write_text(findings.model_dump_json(indent=2), encoding="utf-8")
    verdict_path.write_text(verdict.model_dump_json(indent=2), encoding="utf-8")
    report_path.write_text(render_markdown_report(findings, verdict, schema), encoding="utf-8")
    l4_report_path.write_text(l4_report, encoding="utf-8")
    guardrail_path.write_text(guardrail_report.model_dump_json(indent=2), encoding="utf-8")

    print(f"data_quality_findings.json → {dq_path}")
    print(f"dataset_verdict.json       → {verdict_path}")
    print(f"summary_report.md          → {report_path}")
    print(f"l4_report.md               → {l4_report_path}")
    print(f"guardrail_report.json      → {guardrail_path}")
    output_paths.update({
        "dq_path": str(dq_path),
        "verdict_path": str(verdict_path),
        "report_path": str(report_path),
        "l4_report_path": str(l4_report_path),
        "guardrail_path": str(guardrail_path),
    })
    return output_paths


def run_multi(data_paths: list, out_dir: str = "output", schema_path: str | None = None) -> dict:
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
    all_dq = []
    for table_name, path in zip(table_names, data_paths):
        findings, dq_findings = _profile_data_quality(
            str(path),
            out,
            artifact_prefix=table_name,
            profiling_minimal=True,
        )
        table_findings[table_name] = findings
        all_dq.extend(dq_findings)

    total_n = sum(f.dataset_meta.n for f in table_findings.values())
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
    )
    combined_findings = _combine_multi_findings(table_findings, meta)

    verdict = aggregate(meta, dq_findings=all_dq, integrity_errors=schema.integrity_errors)

    dq_path = out / "data_quality_findings.json"
    schema_out = out / "schema_evaluation_findings.json"
    verdict_path = out / "dataset_verdict.json"
    report_path = out / "summary_report.md"
    l4_report_path = out / "l4_report.md"
    guardrail_path = out / "guardrail_report.json"
    l4_report, guardrail_report = generate_l4_report(combined_findings, verdict, schema)
    dq_path.write_text(
        json.dumps(
            _multi_data_quality_bundle(table_sources, table_findings, combined_findings),
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    schema_out.write_text(schema.model_dump_json(indent=2), encoding="utf-8")
    verdict_path.write_text(verdict.model_dump_json(indent=2), encoding="utf-8")
    report_path.write_text(render_markdown_report(combined_findings, verdict, schema), encoding="utf-8")
    l4_report_path.write_text(l4_report, encoding="utf-8")
    guardrail_path.write_text(guardrail_report.model_dump_json(indent=2), encoding="utf-8")

    print(f"data_quality_findings.json       → {dq_path}")
    print(f"schema_evaluation_findings.json → {schema_out}")
    print(f"dataset_verdict.json            → {verdict_path}")
    print(f"summary_report.md               → {report_path}")
    print(f"l4_report.md                    → {l4_report_path}")
    print(f"guardrail_report.json           → {guardrail_path}")
    return {
        "dq_path": str(dq_path),
        "schema_path": str(schema_out),
        "verdict_path": str(verdict_path),
        "report_path": str(report_path),
        "l4_report_path": str(l4_report_path),
        "guardrail_path": str(guardrail_path),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py <data_path> [out_dir] [schema.dbml|schema.sql]")
        print("       Supported data: .csv, .xlsx, .xls, .parquet, .json, .jsonl, .ndjson")
        print("       python run_pipeline.py --multi <data1> <data2> ... [--schema <file.dbml|file.sql>] [--out <dir>]")
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
        data_args = args
        if len(data_args) < 2:
            print("Error: --multi mode requires at least two data files")
            sys.exit(1)
        run_multi(data_args, out_arg, schema_arg)
    else:
        data_arg = sys.argv[1]
        out_arg = sys.argv[2] if len(sys.argv) > 2 else "output"
        schema_arg = sys.argv[3] if len(sys.argv) > 3 else None
        run(data_arg, out_arg, schema_arg)
