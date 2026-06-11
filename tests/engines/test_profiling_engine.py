import pytest
from engines.profiling_engine import run_profiling, run_profiling_html


class TestRunProfiling:
    def test_returns_dict(self, clean_csv_path):
        from ingestion.csv_reader import load_csv
        df = load_csv(clean_csv_path)
        result = run_profiling(df)
        assert isinstance(result, dict)

    def test_has_table_key(self, clean_csv_path):
        from ingestion.csv_reader import load_csv
        df = load_csv(clean_csv_path)
        result = run_profiling(df)
        assert "table" in result
        assert result["table"]["n"] == 10

    def test_has_variables_key(self, clean_csv_path):
        from ingestion.csv_reader import load_csv
        df = load_csv(clean_csv_path)
        result = run_profiling(df)
        assert "variables" in result
        assert "age" in result["variables"] or "Age" in result["variables"]

    def test_duplicates_detected(self, dirty_csv_path):
        from ingestion.csv_reader import load_csv
        df = load_csv(dirty_csv_path)
        result = run_profiling(df)
        assert result["table"]["n_duplicates"] >= 2

    def test_run_profiling_html_returns_html(self, clean_csv_path):
        from ingestion.csv_reader import load_csv
        df = load_csv(clean_csv_path)
        html = run_profiling_html(df, minimal=True)
        assert "<html" in html.lower()
        assert "Statistical Details" in html
