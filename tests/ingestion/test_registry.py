import pytest
import pandas as pd
from ingestion.registry import load_any


class TestLoadAny:
    def test_csv(self, clean_csv_path):
        assert len(load_any(clean_csv_path)) == 10

    def test_parquet(self, clean_csv_path, tmp_path):
        df = pd.read_csv(clean_csv_path)
        p = tmp_path / "x.parquet"
        df.to_parquet(p)
        assert len(load_any(str(p))) == 10

    def test_excel(self, clean_csv_path, tmp_path):
        df = pd.read_csv(clean_csv_path)
        p = tmp_path / "x.xlsx"
        df.to_excel(p, index=False)
        assert len(load_any(str(p))) == 10

    def test_json_records(self, clean_csv_path, tmp_path):
        df = pd.read_csv(clean_csv_path)
        p = tmp_path / "x.json"
        p.write_text(df.to_json(orient="records"), encoding="utf-8")
        assert len(load_any(str(p))) == 10

    def test_json_lines(self, clean_csv_path, tmp_path):
        df = pd.read_csv(clean_csv_path)
        p = tmp_path / "x.jsonl"
        p.write_text(df.to_json(orient="records", lines=True), encoding="utf-8")
        assert len(load_any(str(p))) == 10

    def test_unsupported(self, tmp_path):
        p = tmp_path / "x.txt"
        p.write_text("hi")
        with pytest.raises(ValueError):
            load_any(str(p))

    def test_missing(self):
        with pytest.raises(FileNotFoundError):
            load_any("nope.csv")
