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
            "test.csv", df, run_profiling(df), run_anomaly_detection(df),
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
        assert f.columns["city"].type in ("Categorical", "Text")
        assert all(c.type != "Unknown" for c in f.columns.values())

    def test_exports_full_outlier_rows_and_uses_row_position(self, tmp_path):
        profile = {
            "table": {
                "n": 3,
                "n_var": 2,
                "memory_size": 0,
                "p_cells_missing": 0.0,
                "n_duplicates": 0,
                "p_duplicates": 0.0,
            },
            "variables": {
                "id": {"type": "Numeric", "n_missing": 0, "p_missing": 0.0, "n_distinct": 3},
                "value": {"type": "Numeric", "n_missing": 0, "p_missing": 0.0, "n_distinct": 3},
            },
        }
        df = pd.DataFrame({"id": [1, 2, 3], "value": [10, 20, 999]}, index=[10, 20, 30])
        anomaly_result = {
            "skipped": False,
            "n_outliers": 1,
            "outlier_indices": [30],
            "outlier_positions": [2],
            "anomaly_scores": [0.99],
        }

        findings = build_data_quality_findings(
            "custom.csv",
            df,
            profile,
            anomaly_result,
            mechs={},
            artifact_dir=tmp_path,
            artifact_prefix="custom",
        )

        outlier = next(a for a in findings.anomalies if a.issue_type == "OUTLIER_ENSEMBLE")
        assert outlier.top_10_samples[0]["value"] == 999
        assert outlier.top_10_samples[0]["_row_index"] == 30
        assert outlier.top_10_samples[0]["_row_position"] == 2
        assert outlier.full_anomalies_export_path is not None
        exported = pd.read_csv(outlier.full_anomalies_export_path)
        assert exported.loc[0, "value"] == 999
