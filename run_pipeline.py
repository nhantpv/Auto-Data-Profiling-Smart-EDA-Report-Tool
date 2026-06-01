"""Full EDA pipeline: CSV → data_quality_findings.json + dataset_verdict.json."""
import json
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

SRC = Path(__file__).parent / "src"
sys.path.insert(0, str(SRC))

from ingestion.csv_reader import load_csv
from engines.profiling_engine import run_profiling
from engines.anomaly_engine import run_anomaly_detection
from ontology.findings_builder import build_data_quality_findings
from severity.calibrator import calibrate_columns, load_calibrator_table
from severity.compound import apply_compound
from severity.aggregator import aggregate


def run(csv_path: str, out_dir: str = "output") -> dict:
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
    verdict = aggregate(findings.dataset_meta, all_dq)

    dq_path = out / "data_quality_findings.json"
    verdict_path = out / "dataset_verdict.json"
    dq_path.write_text(findings.model_dump_json(indent=2), encoding="utf-8")
    verdict_path.write_text(verdict.model_dump_json(indent=2), encoding="utf-8")

    print(f"data_quality_findings.json → {dq_path}")
    print(f"dataset_verdict.json       → {verdict_path}")
    return {"dq_path": str(dq_path), "verdict_path": str(verdict_path)}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_pipeline.py <csv_path> [out_dir]")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "output")
