import pytest
from pathlib import Path
from ingestion.csv_reader import load_csv
from engines.anomaly_engine import run_anomaly_detection
from engines.visualizer import draw_diagnostic_scatter


class TestVisualizer:
    def test_chart_created_for_dirty(self, realistic_outliers_path, tmp_path):
        df = load_csv(realistic_outliers_path)
        res = run_anomaly_detection(df)
        path = draw_diagnostic_scatter(df, res, str(tmp_path), artifact_prefix="dirty")
        if res["n_outliers"] > 0:
            assert path is not None and Path(path).exists()
            assert Path(path).name.startswith("dirty__diagnostic_")

    def test_no_chart_when_skipped(self, tmp_path):
        res = {"skipped": True, "n_outliers": 0}
        assert draw_diagnostic_scatter(None, res, str(tmp_path)) is None

    def test_chart_uses_outlier_positions_for_non_default_index(self, tmp_path):
        import pandas as pd

        df = pd.DataFrame(
            {"x": [1, 2, 100], "y": [1, 2, 100]},
            index=[10, 20, 30],
        )
        res = {
            "skipped": False,
            "n_outliers": 1,
            "outlier_indices": [30],
            "outlier_positions": [2],
            "numeric_columns_used": ["x", "y"],
        }

        path = draw_diagnostic_scatter(df, res, str(tmp_path), artifact_prefix="indexed")

        assert path is not None
        assert Path(path).exists()
