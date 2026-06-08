import pandas as pd
import json

_ENCODINGS = ["utf-8", "utf-8-sig", "latin-1"]


class CSVReader:
    suffixes = (".csv",)
    def read(self, path: str) -> pd.DataFrame:
        for enc in _ENCODINGS:
            try:
                return pd.read_csv(path, encoding=enc)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Cannot read {path} with encodings {_ENCODINGS}")


class ExcelReader:
    suffixes = (".xlsx", ".xls")
    def read(self, path: str) -> pd.DataFrame:
        return pd.read_excel(path)


class ParquetReader:
    suffixes = (".parquet",)
    def read(self, path: str) -> pd.DataFrame:
        return pd.read_parquet(path)


class JSONReader:
    suffixes = (".json", ".jsonl", ".ndjson")

    def read(self, path: str) -> pd.DataFrame:
        if path.lower().endswith((".jsonl", ".ndjson")):
            return pd.read_json(path, lines=True)

        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        if isinstance(raw, list):
            return pd.json_normalize(raw)
        if isinstance(raw, dict):
            records = raw.get("data") or raw.get("records") or raw.get("rows")
            if isinstance(records, list):
                return pd.json_normalize(records)
            return pd.json_normalize(raw)
        raise ValueError(f"Unsupported JSON root type in {path}: {type(raw).__name__}")
