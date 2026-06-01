import pytest
from pathlib import Path
from ingestion.csv_reader import load_csv
from engines.anomaly_engine import run_anomaly_detection
from engines.visualizer import draw_diagnostic_scatter


class TestVisualizer:
    def test_chart_created_for_dirty(self, realistic_outliers_path, tmp_path):
        df = load_csv(realistic_outliers_path)
        res = run_anomaly_detection(df)
        path = draw_diagnostic_scatter(df, res, str(tmp_path))
        if res["n_outliers"] > 0:
            assert path is not None and Path(path).exists()

    def test_no_chart_when_skipped(self, tmp_path):
        res = {"skipped": True, "n_outliers": 0}
        assert draw_diagnostic_scatter(None, res, str(tmp_path)) is None
