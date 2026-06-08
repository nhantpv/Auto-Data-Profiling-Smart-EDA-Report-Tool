from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


REQUIRED_ARTIFACTS = {
    "data_quality_findings.json",
    "dataset_verdict.json",
    "summary_report.md",
    "l4_report.md",
    "guardrail_report.json",
}


class ArtifactEvalCase(BaseModel):
    id: str
    output_dir: str
    expect_charts: bool = False
    expect_anomaly_exports: bool = False


class ArtifactEvalResult(BaseModel):
    id: str
    output_dir: str
    passed: bool
    missing_required_artifacts: list[str] = Field(default_factory=list)
    guardrail_status: str | None = None
    chart_count: int = 0
    missing_charts: list[str] = Field(default_factory=list)
    anomaly_export_count: int = 0
    missing_anomaly_exports: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _iter_anomalies(data_quality: dict[str, Any]) -> list[dict[str, Any]]:
    if data_quality.get("schema_version") == "multi_table_data_quality_v1":
        anomalies: list[dict[str, Any]] = []
        for table in data_quality.get("tables", {}).values():
            findings = table.get("findings", {})
            anomalies.extend(findings.get("anomalies", []))
        return anomalies
    return data_quality.get("anomalies", [])


def _resolve_artifact(output_dir: Path, value: str | None) -> Path | None:
    if not value:
        return None
    path = Path(value)
    return path if path.is_absolute() else output_dir / path


def evaluate_output_dir(case: ArtifactEvalCase) -> ArtifactEvalResult:
    output_dir = Path(case.output_dir)
    missing_required = sorted(
        name for name in REQUIRED_ARTIFACTS
        if not (output_dir / name).is_file()
    )
    notes: list[str] = []
    guardrail_status = None
    chart_count = 0
    missing_charts: list[str] = []
    anomaly_export_count = 0
    missing_anomaly_exports: list[str] = []

    guardrail_path = output_dir / "guardrail_report.json"
    if guardrail_path.exists():
        guardrail_status = _read_json(guardrail_path).get("status")

    dq_path = output_dir / "data_quality_findings.json"
    if dq_path.exists():
        anomalies = _iter_anomalies(_read_json(dq_path))
        for anomaly in anomalies:
            chart_path = _resolve_artifact(output_dir, anomaly.get("diagnostic_chart"))
            if chart_path is not None:
                chart_count += 1
                if not chart_path.is_file():
                    missing_charts.append(str(chart_path))

            export_path = _resolve_artifact(output_dir, anomaly.get("full_anomalies_export_path"))
            if export_path is not None:
                anomaly_export_count += 1
                if not export_path.is_file():
                    missing_anomaly_exports.append(str(export_path))

    if case.expect_charts and chart_count == 0:
        notes.append("Expected at least one diagnostic chart but none were referenced.")
    if case.expect_anomaly_exports and anomaly_export_count == 0:
        notes.append("Expected at least one anomaly-row export but none were referenced.")

    passed = (
        not missing_required
        and guardrail_status == "passed"
        and not missing_charts
        and not missing_anomaly_exports
        and (chart_count > 0 or not case.expect_charts)
        and (anomaly_export_count > 0 or not case.expect_anomaly_exports)
    )
    return ArtifactEvalResult(
        id=case.id,
        output_dir=str(output_dir),
        passed=passed,
        missing_required_artifacts=missing_required,
        guardrail_status=guardrail_status,
        chart_count=chart_count,
        missing_charts=missing_charts,
        anomaly_export_count=anomaly_export_count,
        missing_anomaly_exports=missing_anomaly_exports,
        notes=notes,
    )


def evaluate_output_dirs(cases: list[ArtifactEvalCase]) -> dict[str, Any]:
    results = [evaluate_output_dir(case) for case in cases]
    passed = sum(1 for result in results if result.passed)
    return {
        "schema_version": "pipeline_artifact_eval_result_v1",
        "summary": {
            "cases": len(results),
            "passed": passed,
            "failed": len(results) - passed,
            "chart_count": sum(result.chart_count for result in results),
            "anomaly_export_count": sum(result.anomaly_export_count for result in results),
        },
        "results": [result.model_dump(mode="json") for result in results],
    }
