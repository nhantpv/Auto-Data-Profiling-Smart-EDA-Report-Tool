"""Threshold Registry — config-driven, không hardcode ngưỡng.

Xem ARCHITECT v5.4 §Mục 10.
Thay vì hardcode z=3.0 trong code, mọi ngưỡng đi qua registry.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

from ontology.models import ThresholdEntry

logger = logging.getLogger(__name__)

_DEFAULT_CONFIG = Path(__file__).parent.parent.parent / "config" / "calibrator_table.json"


class ThresholdRegistry:
    """Central registry cho tất cả ngưỡng số trong pipeline.

    Loads thresholds from the calibrator_table.json config file and provides
    type-safe lookup with maturity tracking.
    """

    def __init__(self, config_path: str | Path | None = None) -> None:
        """Load thresholds từ config file.

        Args:
            config_path: Path tới calibrator_table.json hoặc custom config.
                         None → dùng default config.
        """
        path = Path(config_path) if config_path else _DEFAULT_CONFIG
        self._entries: dict[str, ThresholdEntry] = {}
        if path.exists():
            self._load(path)
        else:
            logger.warning("ThresholdRegistry: config not found at %s", path)

    def _load(self, path: Path) -> None:
        """Parse calibrator_table.json → ThresholdEntry instances.

        Each top-level key (except ``_meta``) that contains ``thresholds``
        produces one entry per threshold tier.  Keys without ``thresholds``
        (e.g. constant_column with a fixed rule) produce a single entry
        whose ``value`` is the severity weight.
        """
        raw = json.loads(path.read_text(encoding="utf-8"))
        meta = raw.get("_meta", {})
        calibration_status = meta.get("calibration_status", "heuristic_v0")
        policy_version = meta.get("version", "0.1")

        for section_key, section in raw.items():
            if section_key == "_meta" or not isinstance(section, dict):
                continue

            thresholds = section.get("thresholds")
            if thresholds:
                # Multiple tiers: e.g. completeness has 4 tiers
                for i, tier in enumerate(thresholds):
                    entry_key = f"{section_key}.tier_{i}"
                    self._entries[entry_key] = ThresholdEntry(
                        key=entry_key,
                        value=tier["max"],
                        maturity=calibration_status,
                        policy_version=policy_version,
                        description=f"{section_key} tier {i}: max={tier['max']} → {tier['severity']}",
                    )
                # Also register the full threshold list as a convenience key
                # Value = number of tiers for reference
                self._entries[section_key] = ThresholdEntry(
                    key=section_key,
                    value=float(len(thresholds)),
                    maturity=calibration_status,
                    policy_version=policy_version,
                    description=section.get("basis", section_key),
                )
            else:
                # Fixed-rule entry (e.g. constant_column, high_cardinality)
                severity_weight = {"INFO": 1.0, "WARN": 2.0, "HIGH": 5.0, "CRITICAL": 20.0}
                sev = section.get("severity", "WARN")
                self._entries[section_key] = ThresholdEntry(
                    key=section_key,
                    value=severity_weight.get(sev, 2.0),
                    maturity=calibration_status,
                    policy_version=policy_version,
                    description=section.get("rule", section_key),
                )

        # Register well-known hardcoded thresholds so callers can migrate
        self._register_hardcoded_defaults(calibration_status, policy_version)

    def _register_hardcoded_defaults(self, maturity: str, version: str) -> None:
        """Register thresholds that were previously hardcoded in various modules."""
        defaults = [
            ("mar_auc_gate", 0.65, "Logistic AUC above which column is labelled MAR"),
            ("outlier_z_score", 3.0, "Z-score threshold for outlier detection"),
            ("null_overlap_gate", 0.70, "Null overlap threshold for cross-table joins"),
            ("imbalance_gate", 0.95, "Imbalance ratio above which column is flagged"),
            ("high_cardinality_gate", 0.90, "p_distinct above which categorical is flagged"),
            ("density_share_gate", 0.20, "M1: share of WARN+ findings for density rule"),
            ("density_min_cols", 2.0, "M1: minimum columns affected for density rule"),
        ]
        for key, value, desc in defaults:
            if key not in self._entries:
                self._entries[key] = ThresholdEntry(
                    key=key,
                    value=value,
                    maturity=maturity,
                    policy_version=version,
                    description=desc,
                )

    def get(self, key: str, default: float | None = None) -> float:
        """Lấy giá trị ngưỡng theo key.

        Args:
            key: Threshold key (e.g. "mar_auc_gate", "completeness.tier_0")
            default: Fallback value if key not found. None → raise KeyError.

        Returns:
            Threshold value as float.

        Raises:
            KeyError: If key not found and no default provided.
        """
        entry = self._entries.get(key)
        if entry is not None:
            return entry.value
        if default is not None:
            return default
        raise KeyError(f"ThresholdRegistry: key '{key}' not found. Available: {list(self._entries.keys())}")

    def maturity(self, key: str) -> str:
        """Lấy maturity level của ngưỡng.

        Returns:
            Maturity string (e.g. "heuristic_v0_not_benchmark_calibrated").

        Raises:
            KeyError: If key not found.
        """
        entry = self._entries.get(key)
        if entry is None:
            raise KeyError(f"ThresholdRegistry: key '{key}' not found")
        return entry.maturity

    def all_entries(self) -> dict[str, ThresholdEntry]:
        """Trả toàn bộ entries (copy)."""
        return dict(self._entries)

    def __contains__(self, key: str) -> bool:
        return key in self._entries

    def __len__(self) -> int:
        return len(self._entries)

    def __repr__(self) -> str:
        return f"ThresholdRegistry({len(self._entries)} entries)"
