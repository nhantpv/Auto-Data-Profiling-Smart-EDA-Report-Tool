import logging
import pandas as pd

logger = logging.getLogger(__name__)


def attach_full_data_metadata(df: pd.DataFrame) -> pd.DataFrame:
    """Attach no-sampling metadata required by the L0 data contract."""
    metadata = {
        "is_sampled": False,
        "original_n": int(len(df)),
        "sample_n": int(len(df)),
        "sample_method": None,
        "sample_seed": None,
    }
    df.attrs["sampling"] = metadata
    return df


def sample_if_large(df: pd.DataFrame, threshold: int = 500_000, seed: int = 42) -> pd.DataFrame:
    """Deprecated compatibility shim.

    ARCHITECT v5.4 requires no runtime sampling.  The function name is kept so
    older imports do not break, but it only attaches full-data metadata.
    """
    if len(df) > threshold:
        logger.info("Dataset %d rows > %d. No-sampling policy keeps full data.", len(df), threshold)
    return attach_full_data_metadata(df)
