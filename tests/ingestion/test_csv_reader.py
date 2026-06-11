import pytest
import pandas as pd
from ingestion.csv_reader import load_csv


class TestLoadCsv:
    def test_load_clean_csv(self, clean_csv_path):
        df = load_csv(clean_csv_path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10
        assert list(df.columns) == ["id", "name", "age", "salary"]

    def test_load_dirty_csv(self, dirty_csv_path):
        df = load_csv(dirty_csv_path)
        assert len(df) == 14

    def test_low_sample_threshold_still_keeps_full_data(self, dirty_csv_path):
        df = load_csv(dirty_csv_path, sample_threshold=10)
        assert len(df) == 14
        assert df.attrs["sampling"]["is_sampled"] is False
        assert df.attrs["sampling"]["sample_n"] == 14

    def test_no_sampling_metadata_is_attached(self, clean_csv_path):
        df = load_csv(clean_csv_path, sample_threshold=100)
        assert len(df) == 10
        assert df.attrs["sampling"]["is_sampled"] is False
        assert df.attrs["sampling"]["sample_n"] == 10

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_csv("nonexistent.csv")

    def test_no_sampling_is_reproducible(self, dirty_csv_path):
        df1 = load_csv(dirty_csv_path, sample_threshold=10)
        df2 = load_csv(dirty_csv_path, sample_threshold=10)
        pd.testing.assert_frame_equal(df1, df2)
