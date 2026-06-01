import logging
import pandas as pd

logger = logging.getLogger(__name__)


def sample_if_large(df: pd.DataFrame, threshold: int = 500_000, seed: int = 42) -> pd.DataFrame:
    if len(df) > threshold:
        logger.info("Dataset %d rows > %d. Sampling down.", len(df), threshold)
        return df.sample(n=threshold, random_state=seed).reset_index(drop=True)
    return df
