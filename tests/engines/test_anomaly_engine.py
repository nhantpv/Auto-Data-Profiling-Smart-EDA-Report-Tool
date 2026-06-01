import pytest
import pandas as pd
import numpy as np
from engines.anomaly_engine import run_anomaly_detection


class TestAnomalyDetection:
    def test_returns_expected_keys(self, dirty_csv_path):
        from ingestion.csv_reader import load_csv
        df = load_csv(dirty_csv_path)
        result = run_anomaly_detection(df, z_gate=1.5)
        assert "outlier_indices" in result
        assert "anomaly_scores" in result
        assert "n_outliers" in result

    def test_detects_outliers_in_dirty_data(self, dirty_csv_path):
        from ingestion.csv_reader import load_csv
        df = load_csv(dirty_csv_path)
        result = run_anomaly_detection(df, z_gate=1.5)
        assert result["n_outliers"] >= 1
        assert len(result["outlier_indices"]) == result["n_outliers"]

    def test_clean_data_yields_no_outliers(self, clean_csv_path):
        """Clean data MUST yield 0 outliers (intent, not just 'few') — authorized combiner."""
        from ingestion.csv_reader import load_csv
        df = load_csv(clean_csv_path)
        result = run_anomaly_detection(df, z_gate=1.5)
        assert result["n_outliers"] == 0

    def test_no_numeric_columns(self):
        """DataFrame with only text columns should return skipped=True."""
        df = pd.DataFrame({"name": ["A", "B", "C"], "city": ["X", "Y", "Z"]})
        result = run_anomaly_detection(df)
        assert result["n_outliers"] == 0
        assert result["skipped"] is True

    def test_scores_are_normalized(self, dirty_csv_path):
        from ingestion.csv_reader import load_csv
        df = load_csv(dirty_csv_path)
        result = run_anomaly_detection(df, z_gate=1.5)
        if len(result["anomaly_scores"]) > 0:
            assert all(0 <= s <= 1 for s in result["anomaly_scores"])
