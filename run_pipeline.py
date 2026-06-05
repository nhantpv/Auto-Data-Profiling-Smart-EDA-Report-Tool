"""Full EDA pipeline: CSV → data_quality_findings.json + dataset_verdict.json [+ schema_evaluation_findings.json]."""
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

SRC = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC))

from ingestion.csv_reader import load_csv
from engines.profiling_engine import run_profiling
from engines.anomaly_engine import run_anomaly_detection
from engines.schema_engine import build_schema_findings, validate_schema_multi
from ontology.findings_builder import build_data_quality_findings
from ontology.models import DatasetMeta
from severity.calibrator import calibrate_columns, load_calibrator_table
from severity.compound import apply_compound
from severity.aggregator import aggregate
from severity.missingness import detect_missingness


def run(csv_path: str, out_dir: str = "output", schema_path: str | None = None) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    df = load_csv(csv_path)
    profile = run_profiling(df)
    anomaly_result = run_anomaly_detection(df)

    # Layer 2.5a — Missingness classification (MCAR/MAR/MNAR)
    mechs = detect_missingness(df)

    # Layer 3 — Build findings JSON
    findings = build_data_quality_findings(
        file_name=Path(csv_path).name,
        df=df,
        profile_result=profile,
        anomaly_result=anomaly_result,
        mechs=mechs,
    )

    table = load_calibrator_table()
    col_findings = calibrate_columns(findings.columns, table, n=findings.dataset_meta.n)
    all_dq = apply_compound(findings.anomalies + col_findings)

    # Schema path (optional)
    integrity_errors = None
    output_paths = {}
    if schema_path:
        schema = build_schema_findings(df, csv_path, schema_path)
        schema_out = out / "schema_evaluation_findings.json"
        schema_out.write_text(schema.model_dump_json(indent=2), encoding="utf-8")
        print(f"schema_evaluation_findings.json → {schema_out}")
        output_paths["schema_path"] = str(schema_out)
        integrity_errors = schema.integrity_errors

    verdict = aggregate(findings.dataset_meta, all_dq, integrity_errors=integrity_errors)

    dq_path = out / "data_quality_findings.json"
    verdict_path = out / "dataset_verdict.json"
    dq_path.write_text(findings.model_dump_json(indent=2), encoding="utf-8")
    verdict_path.write_text(verdict.model_dump_json(indent=2), encoding="utf-8")

    print(f"data_quality_findings.json → {dq_path}")
    print(f"dataset_verdict.json       → {verdict_path}")
    output_paths.update({"dq_path": str(dq_path), "verdict_path": str(verdict_path)})
    return output_paths


def run_multi(csv_paths: list, out_dir: str = "output", schema_path: str | None = None) -> dict:
    """Multi-table mode: N CSVs + 1 schema (.dbml/.sql) → schema_evaluation_findings.json + dataset_verdict.json.
    No data-quality profiling per table in this mode (per plan 1b scope).
    verdict meta: aggregate row count and var count across all loaded tables.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    if schema_path is None:
        raise ValueError("--multi mode requires --schema <file.dbml|file.sql>")

    schema = validate_schema_multi(csv_paths, schema_path)

    # Build a synthetic meta for the verdict (totals across tables)
    total_n = 0
    total_vars = 0
    for path in csv_paths:
        try:
            df = load_csv(path)
            total_n += len(df)
            total_vars += len(df.columns)
        except Exception:
            pass
    meta = DatasetMeta(
        file_name=Path(schema_path).name if schema_path else "unknown",
        n=total_n,
        n_var=total_vars,
        memory_size=0,
        p_cells_missing=0.0,
    )

    verdict = aggregate(meta, dq_findings=[], integrity_errors=schema.integrity_errors)

    schema_out = out / "schema_evaluation_findings.json"
    verdict_path = out / "dataset_verdict.json"
    schema_out.write_text(schema.model_dump_json(indent=2), encoding="utf-8")
    verdict_path.write_text(verdict.model_dump_json(indent=2), encoding="utf-8")

    print(f"schema_evaluation_findings.json → {schema_out}")
    print(f"dataset_verdict.json            → {verdict_path}")
    return {"schema_path": str(schema_out), "verdict_path": str(verdict_path)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py <csv_path> [out_dir] [schema.dbml|schema.sql]")
        print("       python run_pipeline.py --multi <csv1> <csv2> ... --schema <file.dbml|file.sql> [--out <dir>]")
        sys.exit(1)

    if sys.argv[1] == "--multi":
        # multi-table mode: collect CSVs until --schema flag
        args = sys.argv[2:]
        try:
            schema_idx = args.index("--schema")
        except ValueError:
            print("Error: --multi mode requires --schema <file.dbml|file.sql>")
            sys.exit(1)
        csv_args = args[:schema_idx]
        schema_arg = args[schema_idx + 1]
        out_arg = "output"
        if "--out" in args:
            out_arg = args[args.index("--out") + 1]
        run_multi(csv_args, out_arg, schema_arg)
    else:
        csv_arg = sys.argv[1]
        out_arg = sys.argv[2] if len(sys.argv) > 2 else "output"
        schema_arg = sys.argv[3] if len(sys.argv) > 3 else None
        run(csv_arg, out_arg, schema_arg)
