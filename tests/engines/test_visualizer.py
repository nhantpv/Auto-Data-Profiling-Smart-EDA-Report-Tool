import pytest
from pathlib import Path
from ingestion.csv_reader import load_csv
from engines.anomaly_engine import run_anomaly_detection
from engines.visualizer import create_overview_charts, draw_diagnostic_scatter


class TestVisualizer:
    def test_chart_created_for_dirty(self, realistic_outliers_path, tmp_path):
        df = load_csv(realistic_outliers_path)
        res = run_anomaly_detection(df)
        path = draw_diagnostic_scatter(df, res, str(tmp_path), artifact_prefix="dirty")
        if res["n_outliers"] > 0:
            assert path is not None and (tmp_path / path).exists()
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
        assert (tmp_path / path).exists()

    def test_overview_charts_created_for_mixed_dataset(self, tmp_path):
        import pandas as pd

        df = pd.DataFrame({
            "age": [18, 22, 30, None, 44, 51, 60, 63],
            "income": [1200, 1800, 2200, 2600, 3200, 4100, 5000, 5900],
            "score": [0.2, 0.4, 0.5, 0.5, 0.7, 0.8, 0.9, 0.95],
            "segment": ["A", "A", "B", "B", "B", "C", "C", "C"],
        })

        charts = create_overview_charts(df, str(tmp_path), artifact_prefix="mixed")

        assert "missingness_bar" in charts
        assert "dtype_distribution" in charts
        assert "numeric_distributions" in charts
        assert "numeric_boxplot" in charts
        assert "correlation_heatmap" in charts
        assert "categorical_top_values" in charts
        for file_name in charts.values():
            assert Path(file_name).name == file_name
            assert (tmp_path / file_name).exists()

    def test_missingness_chart_for_complete_dataset_shows_completion_bars(self, tmp_path):
        import numpy as np
        import pandas as pd
        from PIL import Image

        df = pd.DataFrame({
            "order_id": [1, 2, 3, 4],
            "product_id": [10, 11, 12, 13],
            "quantity": [3, 4, 1, 2],
            "segment": ["A", "B", "A", "C"],
        })

        charts = create_overview_charts(df, str(tmp_path), artifact_prefix="complete")

        assert "missingness_bar" in charts
        image = Image.open(tmp_path / charts["missingness_bar"]).convert("RGB")
        pixels = np.array(image)
        green_pixels = int(
            (
                (pixels[:, :, 0] < 80)
                & (pixels[:, :, 1] > 90)
                & (pixels[:, :, 2] > 80)
            ).sum()
        )
        assert green_pixels > image.width * image.height * 0.02
