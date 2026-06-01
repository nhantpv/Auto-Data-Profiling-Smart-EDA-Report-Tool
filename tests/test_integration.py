"""End-to-end integration test: CSV → Profile → Anomaly → JSON output."""
import pytest
import json
from pathlib import Path
from ingestion.csv_reader import load_csv
from engines.profiling_engine import run_profiling
from engines.anomaly_engine import run_anomaly_detection
from engines.visualizer import attach_diagnostic_charts
from ontology.findings_builder import build_data_quality_findings
from ontology.models import DataQualityFindings


class TestFullPipeline:
    def test_dirty_csv_produces_valid_json(self, realistic_outliers_path, tmp_path):
        # Step 1: Ingestion
        df = load_csv(realistic_outliers_path)
        assert len(df) == 32

        # Step 2: Layer 1 — Profiling
        profile = run_profiling(df)
        assert "table" in profile

        # Step 3: Layer 2 — Anomaly Detection
        anomalies = run_anomaly_detection(df)
        assert anomalies["n_outliers"] >= 0

        # Step 4: Layer 3 — Build Findings
        findings = build_data_quality_findings(
            file_name="outliers_realistic.csv",
            df=df,
            profile_result=profile,
            anomaly_result=anomalies,
        )

        # Step 5: Layer 3.5 — Attach diagnostic charts (PATCH 5c)
        findings = attach_diagnostic_charts(
            findings, df, anomalies, out_dir=str(tmp_path / "charts")
        )
        # If outliers detected, every OUTLIER_ENSEMBLE record must have diagnostic_chart set
        outlier_recs = [a for a in findings.anomalies if a.issue_type == "OUTLIER_ENSEMBLE"]
        for r in outlier_recs:
            assert r.diagnostic_chart is not None
            assert Path(r.diagnostic_chart).exists()

        # Step 6: Export to JSON
        output_path = tmp_path / "data_quality_findings.json"
        output_path.write_text(findings.model_dump_json(indent=2), encoding="utf-8")

        # Step 7: Verify round-trip
        with open(output_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        restored = DataQualityFindings.model_validate(raw)
        assert restored.dataset_meta.n == 32
        assert len(restored.anomalies) >= 1  # at least outliers or duplicates
