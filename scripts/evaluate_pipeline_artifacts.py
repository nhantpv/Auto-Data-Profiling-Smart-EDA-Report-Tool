from __future__ import annotations

import argparse
import contextlib
import json
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(SRC))

import run_pipeline
from evaluation.artifact_contract import ArtifactEvalCase, evaluate_output_dirs


def _resolve(value: str | None) -> str | None:
    if value is None:
        return None
    path = Path(value)
    return str(path if path.is_absolute() else PROJECT_ROOT / path)


def _run_case(raw_case: dict, base_out: Path) -> ArtifactEvalCase:
    case_id = raw_case["id"]
    mode = raw_case.get("mode", "single")
    output_dir = base_out / case_id
    output_dir.mkdir(parents=True, exist_ok=True)
    data_paths = [_resolve(path) for path in raw_case.get("data_files", [])]
    schema_path = _resolve(raw_case.get("schema_file"))

    if mode == "single":
        if len(data_paths) != 1:
            raise ValueError(f"Case {case_id}: single mode requires exactly one data file")
        with contextlib.redirect_stdout(sys.stderr):
            run_pipeline.run(
                data_paths[0],
                str(output_dir),
                schema_path,
                profiling_minimal=bool(raw_case.get("profiling_minimal", True)),
            )
    elif mode == "multi":
        with contextlib.redirect_stdout(sys.stderr):
            run_pipeline.run_multi(data_paths, str(output_dir), schema_path)
    else:
        raise ValueError(f"Case {case_id}: unsupported mode '{mode}'")

    return ArtifactEvalCase(
        id=case_id,
        output_dir=str(output_dir),
        expect_charts=bool(raw_case.get("expect_charts", False)),
        expect_anomaly_exports=bool(raw_case.get("expect_anomaly_exports", False)),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate pipeline output artifact contract.")
    parser.add_argument(
        "--spec",
        default="examples/evaluation/pipeline_artifact_eval.json",
        help="Evaluation spec JSON path.",
    )
    parser.add_argument("--work-dir", default=None, help="Directory for pipeline output cases.")
    parser.add_argument("--out", default=None, help="Optional output JSON path.")
    args = parser.parse_args()

    spec_path = Path(args.spec)
    if not spec_path.is_absolute():
        spec_path = PROJECT_ROOT / spec_path
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    if args.work_dir:
        work_dir = Path(args.work_dir)
        if not work_dir.is_absolute():
            work_dir = PROJECT_ROOT / work_dir
        work_dir.mkdir(parents=True, exist_ok=True)
        cases = [_run_case(raw_case, work_dir) for raw_case in spec.get("cases", [])]
        result = evaluate_output_dirs(cases)
    else:
        with tempfile.TemporaryDirectory(prefix="smart-eda-artifact-eval-") as tmp:
            cases = [_run_case(raw_case, Path(tmp)) for raw_case in spec.get("cases", [])]
            result = evaluate_output_dirs(cases)

    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        out_path = Path(args.out)
        if not out_path.is_absolute():
            out_path = PROJECT_ROOT / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    print(text)
    return 0 if result["summary"]["failed"] == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
