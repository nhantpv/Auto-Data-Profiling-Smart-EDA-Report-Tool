import pandas as pd
import json

_ENCODINGS = ["utf-8", "utf-8-sig", "latin-1"]
_SEMANTIC_MISSING_TOKENS = frozenset({
    "",
    "?",
    "na",
    "n/a",
    "nan",
    "none",
    "null",
    "missing",
    "unknown",
})


def normalize_semantic_missing(df: pd.DataFrame) -> pd.DataFrame:
    """Convert common text missing-value markers to pandas missing values."""
    normalized = df.copy()
    for column in normalized.columns:
        series = normalized[column]
        if not (
            pd.api.types.is_object_dtype(series)
            or pd.api.types.is_string_dtype(series)
            or isinstance(series.dtype, pd.CategoricalDtype)
        ):
            continue
        marker_mask = series.astype("string").str.strip().str.lower().isin(_SEMANTIC_MISSING_TOKENS)
        if marker_mask.any():
            normalized.loc[marker_mask, column] = pd.NA
    return normalized


class CSVReader:
    suffixes = (".csv",)
    def read(self, path: str) -> pd.DataFrame:
        for enc in _ENCODINGS:
            try:
                return normalize_semantic_missing(pd.read_csv(path, encoding=enc))
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Cannot read {path} with encodings {_ENCODINGS}")


class ExcelReader:
    suffixes = (".xlsx", ".xls")
    def read(self, path: str) -> pd.DataFrame:
        return normalize_semantic_missing(pd.read_excel(path))


class ParquetReader:
    suffixes = (".parquet",)
    def read(self, path: str) -> pd.DataFrame:
        return normalize_semantic_missing(pd.read_parquet(path))


class JSONReader:
    suffixes = (".json", ".jsonl", ".ndjson")

    def read(self, path: str) -> pd.DataFrame:
        if path.lower().endswith((".jsonl", ".ndjson")):
            return normalize_semantic_missing(pd.read_json(path, lines=True))

        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        if isinstance(raw, list):
            return normalize_semantic_missing(pd.json_normalize(raw))
        if isinstance(raw, dict):
            records = raw.get("data") or raw.get("records") or raw.get("rows")
            if isinstance(records, list):
                return normalize_semantic_missing(pd.json_normalize(records))
            return normalize_semantic_missing(pd.json_normalize(raw))
        raise ValueError(f"Unsupported JSON root type in {path}: {type(raw).__name__}")
