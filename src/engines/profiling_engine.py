import json
import logging
import warnings
import pandas as pd

try:
    from data_profiling import ProfileReport
except ImportError:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        from ydata_profiling import ProfileReport

logger = logging.getLogger(__name__)


_FULL_PROFILE_CORRELATIONS = {
    "auto": {"calculate": True, "warn_high_correlations": True},
    "pearson": {"calculate": True, "warn_high_correlations": True},
    "spearman": {"calculate": True, "warn_high_correlations": False},
    "kendall": {"calculate": False},
    "phi_k": {"calculate": False},
    "cramers": {"calculate": True, "warn_high_correlations": True},
}


def _profile_report_kwargs(minimal: bool, title: str | None = None) -> dict:
    kwargs = {
        "minimal": minimal,
        "progress_bar": False,
    }
    if title is not None:
        kwargs["title"] = title
    if not minimal:
        kwargs["correlations"] = _FULL_PROFILE_CORRELATIONS
    return kwargs


def _count_duplicates(df: pd.DataFrame) -> int:
    """Count duplicate rows, ignoring single-column integer indices (e.g. 'id')."""
    non_id_cols = [c for c in df.columns if not (c.lower() == "id" and pd.api.types.is_integer_dtype(df[c]))]
    subset = non_id_cols if non_id_cols else list(df.columns)
    return int(df.duplicated(subset=subset).sum())


def run_profiling(df: pd.DataFrame, minimal: bool = False) -> dict:
    logger.info("Running profiling on DataFrame with %d rows, %d cols.", len(df), len(df.columns))
    profile = ProfileReport(df, **_profile_report_kwargs(minimal))
    raw_json_str = profile.to_json()
    result = json.loads(raw_json_str)
    if "table" in result:
        n_duplicates = _count_duplicates(df)
        result["table"]["n_duplicates"] = n_duplicates
        result["table"]["p_duplicates"] = n_duplicates / len(df) if len(df) else 0.0
    logger.info("Profiling complete. Found %d variables.", len(result.get("variables", {})))
    return result


def run_profiling_html(df: pd.DataFrame, minimal: bool = False) -> str:
    """Run ydata-profiling and return the original HTML report.

    The returned HTML is embedded into ``smart_eda_report.html`` via
    ``iframe srcdoc`` so the statistical details remain interactive.
    """
    logger.info("Rendering profiling HTML for DataFrame with %d rows, %d cols.", len(df), len(df.columns))
    profile = ProfileReport(df, **_profile_report_kwargs(minimal, title="Statistical Details"))
    return profile.to_html()
