import json
import sys
from pathlib import Path

from evaluation.artifact_contract import ArtifactEvalCase, evaluate_output_dir


def test_pipeline_artifact_eval_counts_charts_and_exports(realistic_outliers_path, tmp_path):
    sys.path.insert(0, str(Path(__file__).parents[2]))
    import run_pipeline

    run_pipeline.run(realistic_outliers_path, str(tmp_path), profiling_minimal=True)

    result = evaluate_output_dir(
        ArtifactEvalCase(
            id="outliers",
            output_dir=str(tmp_path),
            expect_charts=True,
            expect_anomaly_exports=True,
        )
    )

    assert result.passed is True
    assert result.guardrail_status == "passed"
    assert result.chart_count >= 1
    assert result.anomaly_export_count >= 1


def test_pipeline_artifact_eval_spec_exists():
    spec_path = Path(__file__).parents[2] / "examples/evaluation/pipeline_artifact_eval.json"
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    assert spec["schema_version"] == "pipeline_artifact_eval_v1"
    assert spec["cases"][0]["expect_charts"] is True
