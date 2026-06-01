import pytest
import pandas as pd
from ontology.findings_builder import build_data_quality_findings
from ontology.models import DataQualityFindings, Severity


class TestBuildDataQualityFindings:
    def test_end_to_end(self, dirty_csv_path):
        """Full pipeline: load → profile → detect anomalies → build findings."""
        from ingestion.csv_reader import load_csv
        from engines.profiling_engine import run_profiling
        from engines.anomaly_engine import run_anomaly_detection

        df = load_csv(dirty_csv_path)
        profile_result = run_profiling(df)
        anomaly_result = run_anomaly_detection(df)

        findings = build_data_quality_findings(
            file_name="dirty_with_outliers.csv",
            df=df,
            profile_result=profile_result,
            anomaly_result=anomaly_result,
        )

        assert isinstance(findings, DataQualityFindings)
        assert findings.dataset_meta.file_name == "dirty_with_outliers.csv"
        assert findings.dataset_meta.n == 14
        assert len(findings.columns) > 0
        assert "age" in findings.columns or "Age" in findings.columns
        json_str = findings.model_dump_json(indent=2)
        assert len(json_str) > 100

    def test_clean_data_no_anomalies(self, clean_csv_path):
        from ingestion.csv_reader import load_csv
        from engines.profiling_engine import run_profiling
        from engines.anomaly_engine import run_anomaly_detection

        df = load_csv(clean_csv_path)
        profile_result = run_profiling(df)
        anomaly_result = run_anomaly_detection(df)

        findings = build_data_quality_findings(
            file_name="clean_10rows.csv",
            df=df,
            profile_result=profile_result,
            anomaly_result=anomaly_result,
        )
        total_affected = sum(a.affected_count for a in findings.anomalies)
        assert total_affected <= 2
        # PATCH 3c: clean data MUST NOT produce HIGH/CRITICAL findings
        assert all(a.severity in (Severity.INFO, Severity.WARN) for a in findings.anomalies)
