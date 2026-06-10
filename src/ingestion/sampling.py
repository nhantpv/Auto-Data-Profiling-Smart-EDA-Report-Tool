import logging
import pandas as pd

logger = logging.getLogger(__name__)


def sample_if_large(df: pd.DataFrame, threshold: int = 500_000, seed: int = 42) -> pd.DataFrame:
    metadata = {
        "is_sampled": False,
        "original_n": int(len(df)),
        "sample_n": int(len(df)),
        "sample_method": None,
        "sample_seed": None,
    }
    if len(df) > threshold:
        logger.info("Dataset %d rows > %d. Sampling down.", len(df), threshold)
        sampled = df.sample(n=threshold, random_state=seed).reset_index(drop=True)
        sampled.attrs["sampling"] = {
            **metadata,
            "is_sampled": True,
            "sample_n": int(threshold),
            "sample_method": "random",
            "sample_seed": int(seed),
        }
        return sampled
    df.attrs["sampling"] = metadata
    return df
