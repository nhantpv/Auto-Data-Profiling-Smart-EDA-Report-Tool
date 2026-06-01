import pytest
import pandas as pd
import numpy as np
from engines.anomaly_engine import run_anomaly_detection


class TestAnomalyDetection:
    def test_returns_expected_keys(self, realistic_outliers_path):
        from ingestion.csv_reader import load_csv
        df = load_csv(realistic_outliers_path)
        result = run_anomaly_detection(df)
        assert "outlier_indices" in result
        assert "anomaly_scores" in result
        assert "n_outliers" in result

    def test_detects_outliers_in_dirty_data(self, realistic_outliers_path):
        from ingestion.csv_reader import load_csv
        df = load_csv(realistic_outliers_path)
        res = run_anomaly_detection(df)
        assert res["n_outliers"] >= 1
        gross_idx = df.index[df["age"] == 150].tolist()[0]
        assert gross_idx in res["outlier_indices"]

    def test_clean_data_yields_no_outliers(self, clean_csv_path):
        """Clean data MUST yield 0 outliers (clean max ensemble_z 2.29 < _DEFAULT_Z_GATE 3.0)."""
        from ingestion.csv_reader import load_csv
        df = load_csv(clean_csv_path)
        assert run_anomaly_detection(df)["n_outliers"] == 0

    def test_no_numeric_columns(self):
        """DataFrame with only text columns should return skipped=True."""
        df = pd.DataFrame({"name": ["A", "B", "C"], "city": ["X", "Y", "Z"]})
        result = run_anomaly_detection(df)
        assert result["n_outliers"] == 0
        assert result["skipped"] is True

    def test_scores_are_normalized(self, realistic_outliers_path):
        from ingestion.csv_reader import load_csv
        df = load_csv(realistic_outliers_path)
        result = run_anomaly_detection(df)
        if len(result["anomaly_scores"]) > 0:
            assert all(0 <= s <= 1 for s in result["anomaly_scores"])
