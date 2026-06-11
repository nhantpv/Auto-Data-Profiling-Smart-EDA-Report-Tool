from pathlib import Path
from ingestion.readers import CSVReader
from ingestion.sampling import attach_full_data_metadata
import pandas as pd


def load_csv(file_path: str, sample_threshold: int = 500_000, random_seed: int = 42) -> pd.DataFrame:
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    return attach_full_data_metadata(CSVReader().read(file_path))
