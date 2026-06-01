from pathlib import Path
from typing import List
import pandas as pd
from ingestion.base import DataReader
from ingestion.readers import CSVReader, ExcelReader, ParquetReader
from ingestion.sampling import sample_if_large

_READERS: List[DataReader] = [CSVReader(), ExcelReader(), ParquetReader()]


def _pick_reader(path: str) -> DataReader:
    suffix = Path(path).suffix.lower()
    for r in _READERS:
        if suffix in r.suffixes:
            return r
    supported = sorted({s for r in _READERS for s in r.suffixes})
    raise ValueError(f"Unsupported format '{suffix}'. Supported: {supported}")


def load_any(path: str, sample_threshold: int = 500_000, seed: int = 42) -> pd.DataFrame:
    if not Path(path).exists():
        raise FileNotFoundError(f"File not found: {path}")
    df = _pick_reader(path).read(path)
    return sample_if_large(df, sample_threshold, seed)
