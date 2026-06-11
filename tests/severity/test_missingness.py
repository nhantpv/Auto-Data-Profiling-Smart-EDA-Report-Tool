import pytest
import numpy as np
import pandas as pd
from severity.missingness import (
    little_mcar_pvalue, mar_auc, classify_missingness, detect_missingness,
    sample_missingness_frame, _MAR_AUC_GATE, _MCAR_ALPHA, _MAX_MISSINGNESS_ROWS,
)

RNG = np.random.default_rng(42)


def _mcar_df(n=300):
    """Purely MCAR: missing in col 'a' independent of everything."""
    df = pd.DataFrame({
        "a": RNG.normal(0, 1, n),
        "b": RNG.normal(0, 1, n),
        "c": RNG.normal(0, 1, n),
    })
    mask = RNG.random(n) < 0.2
    df.loc[mask, "a"] = np.nan  # type: ignore[index]
    return df


def _mar_df(n=300):
    """MAR: missing in 'target' is determined by value of 'predictor'."""
    rng = np.random.default_rng(7)
    predictor = rng.normal(0, 1, n)
    target = rng.normal(0, 1, n)
    # high predictor → target missing
    missing_mask = predictor > 0.5
    target_with_missing = target.copy().astype(float)
    target_with_missing[missing_mask] = np.nan
    return pd.DataFrame({"predictor": predictor, "target": target_with_missing, "noise": rng.normal(0,1,n)})


class TestConstants:
    def test_gate_values(self):
        assert _MAR_AUC_GATE == 0.65
        assert _MCAR_ALPHA == 0.05


class TestLittleMcarPvalue:
    def test_returns_float_for_valid_df(self):
        df = _mcar_df()
        p = little_mcar_pvalue(df)
        assert p is None or isinstance(p, float)

    def test_mcar_data_high_pvalue(self):
        df = _mcar_df()
        p = little_mcar_pvalue(df)
        # MCAR data should not reject H0 (p >= 0.05) — may be None if test fails
        if p is not None:
            assert p >= _MCAR_ALPHA

    def test_single_column_returns_none(self):
        """One numeric column — Little's test needs ≥2."""
        df = pd.DataFrame({"a": [1.0, None, 3.0, None, 5.0]})
        p = little_mcar_pvalue(df)
        assert p is None

    def test_no_missing_returns_none_or_float(self):
        """No missing → test may error or return trivial p; must not crash."""
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0]})
        p = little_mcar_pvalue(df)
        assert p is None or isinstance(p, float)

    def test_collinear_does_not_crash(self):
        """Collinear columns make covariance singular — must return None, not raise."""
        df = pd.DataFrame({"a": [1.0, None, 3.0, None, 5.0] * 10,
                           "b": [2.0, None, 6.0, None, 10.0] * 10})  # b = 2*a
        p = little_mcar_pvalue(df)
        assert p is None or isinstance(p, float)


class TestMarAuc:
    def test_mar_column_above_gate(self):
        df = _mar_df()
        auc = mar_auc(df, "target")
        if auc is not None:
            assert auc > _MAR_AUC_GATE

    def test_mcar_column_near_chance(self):
        df = _mcar_df()
        auc = mar_auc(df, "a")
        # MCAR: AUC should be near 0.5, not above gate
        if auc is not None:
            assert auc < _MAR_AUC_GATE + 0.15  # some slack for small sample noise

    def test_no_numeric_predictors_returns_none(self):
        df = pd.DataFrame({"a": [1.0, None, 3.0], "text": ["x", "y", "z"]})
        auc = mar_auc(df, "a")
        assert auc is None

    def test_fewer_than_10_missing_returns_none(self):
        df = pd.DataFrame({"a": [None] * 5 + list(range(95)),
                           "b": list(range(100))}, dtype=float)
        auc = mar_auc(df, "a")
        assert auc is None

    def test_no_crash_on_one_class_target(self):
        """All missing or all present → single-class y → must not raise."""
        df = pd.DataFrame({"a": [None] * 100, "b": list(range(100))}, dtype=float)
        auc = mar_auc(df, "a")
        assert auc is None


class TestClassifyMissingness:
    def test_zero_missing_returns_none(self):
        assert classify_missingness(0, 0.9, 0.8) is None

    def test_high_auc_returns_mar(self):
        assert classify_missingness(50, 0.01, 0.80) == "MAR"

    def test_auc_below_gate_returns_mcar_consistent(self):
        assert classify_missingness(50, 0.30, 0.40) == "MCAR_CONSISTENT"

    def test_low_mcar_pvalue_no_longer_returns_mnar(self):
        assert classify_missingness(50, 0.01, 0.40) == "MCAR_CONSISTENT"

    def test_both_none_returns_indeterminate(self):
        assert classify_missingness(50, None, None) == "INDETERMINATE"

    def test_mcar_p_none_auc_below_gate_returns_mcar_consistent(self):
        assert classify_missingness(50, None, 0.50) == "MCAR_CONSISTENT"

    def test_mcar_p_none_auc_above_gate_returns_mar(self):
        assert classify_missingness(50, None, 0.80) == "MAR"


class TestDetectMissingness:
    def test_missing_col_gets_mechanism(self):
        df = _mcar_df()
        result = detect_missingness(df)
        assert "a" in result
        assert result["a"] in ("MCAR_CONSISTENT", "MAR", "INDETERMINATE")

    def test_non_missing_col_not_in_result(self):
        df = _mcar_df()
        result = detect_missingness(df)
        assert "b" not in result
        assert "c" not in result

    def test_no_missing_returns_empty_dict(self):
        df = pd.DataFrame({"a": [1.0, 2.0, 3.0], "b": [4.0, 5.0, 6.0]})
        result = detect_missingness(df)
        assert result == {}

    def test_mar_col_detected(self):
        df = _mar_df()
        result = detect_missingness(df)
        assert "target" in result
        assert result["target"] == "MAR"

    def test_missingness_helper_keeps_full_frame(self):
        df = pd.DataFrame({
            "a": np.arange(20_000, dtype=float),
            "b": np.arange(20_000, dtype=float),
        })
        df.loc[:49, "a"] = np.nan

        sampled = sample_missingness_frame(df)

        assert len(sampled) == len(df)
        assert sampled["a"].isna().sum() == 50

    def test_detect_missingness_runs_diagnostics_on_full_frame(self, monkeypatch):
        seen_lengths = []

        def fake_mcar(frame):
            seen_lengths.append(len(frame))
            return None

        def fake_auc(frame, col):
            seen_lengths.append(len(frame))
            return None

        monkeypatch.setattr("severity.missingness.little_mcar_pvalue", fake_mcar)
        monkeypatch.setattr("severity.missingness.mar_auc", fake_auc)

        df = pd.DataFrame({
            "a": np.arange(20_000, dtype=float),
            "b": np.arange(20_000, dtype=float),
        })
        df.loc[:99, "a"] = np.nan

        result = detect_missingness(df)

        assert result == {"a": "INDETERMINATE"}
        assert seen_lengths
        assert max(seen_lengths) == len(df)
