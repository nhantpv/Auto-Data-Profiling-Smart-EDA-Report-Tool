import inspect
import sys
from pathlib import Path

import pytest

# run_pipeline.py lives at the repo root, not under src/.
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import run_pipeline


class TestParseMultiArgs:
    def test_basic_csvs_no_flags(self):
        parsed = run_pipeline._parse_multi_args(["a.csv", "b.csv"])
        assert parsed == (["a.csv", "b.csv"], "output", None, None, None)

    def test_all_flags_any_position(self):
        parsed = run_pipeline._parse_multi_args([
            "--out", "outdir", "a.csv", "--schema", "s.dbml", "b.csv",
            "--confirmed-schema", "c.json", "--fact-table", "orders",
        ])
        assert parsed == (
            ["a.csv", "b.csv"], "outdir", "s.dbml", "c.json", "orders",
        )

    def test_schema_flag_without_value_raises(self):
        """No IndexError when a flag is the last token."""
        with pytest.raises(ValueError):
            run_pipeline._parse_multi_args(["a.csv", "b.csv", "--schema"])

    def test_out_flag_without_value_raises(self):
        with pytest.raises(ValueError):
            run_pipeline._parse_multi_args(["a.csv", "b.csv", "--out"])

    def test_fewer_than_two_data_paths_raises(self):
        with pytest.raises(ValueError):
            run_pipeline._parse_multi_args(["a.csv", "--schema", "s.dbml"])

    def test_unknown_flag_raises(self):
        """Unknown flags must not be silently swallowed as data paths."""
        with pytest.raises(ValueError):
            run_pipeline._parse_multi_args(["a.csv", "b.csv", "--dbml", "s.dbml"])


class TestRunMultiSignature:
    def test_schema_is_optional(self):
        """ARCHITECT L2b.5 Quick Mode: multi-table runs without an explicit
        schema; tables and relationships are inferred from the data."""
        sig = inspect.signature(run_pipeline.run_multi)
        assert sig.parameters["schema_path"].default is None
