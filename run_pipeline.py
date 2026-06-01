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


def run(csv_path: str, out_dir: str = "output", dbml_path: str | None = None) -> dict:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    df = load_csv(csv_path)
    profile = run_profiling(df)
    anomaly_result = run_anomaly_detection(df, profile_result=profile)
    findings = build_data_quality_findings(
        file_name=Path(csv_path).name,
        df=df,
        profile_result=profile,
        anomaly_result=anomaly_result,
    )

    table = load_calibrator_table()
    col_findings = calibrate_columns(findings.columns, table, n=findings.dataset_meta.n)
    all_dq = apply_compound(findings.anomalies + col_findings)

    # Schema path (optional)
    integrity_errors = None
    output_paths = {}
    if dbml_path:
        schema = build_schema_findings(df, csv_path, dbml_path)
        schema_path = out / "schema_evaluation_findings.json"
        schema_path.write_text(schema.model_dump_json(indent=2), encoding="utf-8")
        print(f"schema_evaluation_findings.json → {schema_path}")
        output_paths["schema_path"] = str(schema_path)
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


def run_multi(csv_paths: list, out_dir: str = "output", dbml_path: str = None) -> dict:
    """Multi-table mode: N CSVs + 1 DBML → schema_evaluation_findings.json + dataset_verdict.json.
    No data-quality profiling per table in this mode (per plan 1b scope).
    verdict meta: aggregate row count and var count across all loaded tables.
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    schema = validate_schema_multi(csv_paths, dbml_path)

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
        file_name=Path(dbml_path).name,
        n=total_n,
        n_var=total_vars,
        memory_size=0,
        p_cells_missing=0.0,
    )

    verdict = aggregate(meta, dq_findings=[], integrity_errors=schema.integrity_errors)

    schema_path = out / "schema_evaluation_findings.json"
    verdict_path = out / "dataset_verdict.json"
    schema_path.write_text(schema.model_dump_json(indent=2), encoding="utf-8")
    verdict_path.write_text(verdict.model_dump_json(indent=2), encoding="utf-8")

    print(f"schema_evaluation_findings.json → {schema_path}")
    print(f"dataset_verdict.json            → {verdict_path}")
    return {"schema_path": str(schema_path), "verdict_path": str(verdict_path)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py <csv_path> [out_dir] [schema.dbml]")
        print("       python run_pipeline.py --multi <csv1> <csv2> ... --dbml <schema.dbml> [--out <dir>]")
        sys.exit(1)

    if sys.argv[1] == "--multi":
        # multi-table mode: collect CSVs until --dbml flag
        args = sys.argv[2:]
        try:
            dbml_idx = args.index("--dbml")
        except ValueError:
            print("Error: --multi mode requires --dbml <schema.dbml>")
            sys.exit(1)
        csv_args = args[:dbml_idx]
        dbml_arg = args[dbml_idx + 1]
        out_arg = "output"
        if "--out" in args:
            out_arg = args[args.index("--out") + 1]
        run_multi(csv_args, out_arg, dbml_arg)
    else:
        csv_arg = sys.argv[1]
        out_arg = sys.argv[2] if len(sys.argv) > 2 else "output"
        dbml_arg = sys.argv[3] if len(sys.argv) > 3 else None
        run(csv_arg, out_arg, dbml_arg)
