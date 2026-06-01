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

    def test_missingness_mechanism_wired(self):
        """Columns with missing values should get missingness_mechanism set."""
        from engines.profiling_engine import run_profiling
        from engines.anomaly_engine import run_anomaly_detection
        import numpy as np

        rng = np.random.default_rng(7)
        predictor = rng.normal(0, 1, 200)
        target = rng.normal(0, 1, 200).astype(float)
        target[predictor > 0.5] = np.nan  # MAR: missing depends on predictor
        df = pd.DataFrame({"predictor": predictor, "target": target,
                           "noise": rng.normal(0, 1, 200)})
        findings = build_data_quality_findings(
            "test.csv", df, run_profiling(df), run_anomaly_detection(df, profile_result=run_profiling(df)),
        )
        assert findings.columns["target"].missingness_mechanism == "MAR"
        # predictor has no missing → mechanism should be None
        assert findings.columns["predictor"].missingness_mechanism is None

    def test_no_missing_mechanism_is_none(self):
        """Columns without missing values must have missingness_mechanism=None."""
        from engines.profiling_engine import run_profiling
        from engines.anomaly_engine import run_anomaly_detection

        df = pd.DataFrame({"a": [1, 2, 3, 4, 5], "b": [6, 7, 8, 9, 10]})
        findings = build_data_quality_findings(
            "test.csv", df, run_profiling(df), run_anomaly_detection(df),
        )
        for cs in findings.columns.values():
            assert cs.missingness_mechanism is None

    def test_categorical_column_typed_correctly(self):
        from engines.profiling_engine import run_profiling
        from engines.anomaly_engine import run_anomaly_detection

        df = pd.DataFrame({
            "city": ["HN", "HCM", "HN", "DN", "HN", "HCM", "HN", "DN", "HN", "HCM"],
            "val":  [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        })
        f = build_data_quality_findings("c.csv", df, run_profiling(df), run_anomaly_detection(df))
        assert f.columns["city"].type == "Categorical"
        assert all(c.type != "Unknown" for c in f.columns.values())
