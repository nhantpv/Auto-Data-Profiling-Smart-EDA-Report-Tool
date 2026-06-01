import json
import logging
import pandas as pd
from ydata_profiling import ProfileReport

logger = logging.getLogger(__name__)


def _count_duplicates(df: pd.DataFrame) -> int:
    """Count duplicate rows, ignoring single-column integer indices (e.g. 'id')."""
    non_id_cols = [c for c in df.columns if not (c.lower() == "id" and pd.api.types.is_integer_dtype(df[c]))]
    subset = non_id_cols if non_id_cols else list(df.columns)
    return int(df.duplicated(subset=subset).sum())


def run_profiling(df: pd.DataFrame, minimal: bool = True) -> dict:
    logger.info("Running profiling on DataFrame with %d rows, %d cols.", len(df), len(df.columns))
    profile = ProfileReport(df, minimal=minimal, progress_bar=False)
    raw_json_str = profile.to_json()
    result = json.loads(raw_json_str)
    if "table" in result and "n_duplicates" not in result["table"]:
        result["table"]["n_duplicates"] = _count_duplicates(df)
    logger.info("Profiling complete. Found %d variables.", len(result.get("variables", {})))
    return result
