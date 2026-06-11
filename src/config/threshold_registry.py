"""Threshold Registry — config-driven, không hardcode ngưỡng.

Xem ARCHITECT v5.4 §Mục 10.
Thay vì hardcode z=3.0 trong code, mọi ngưỡng đi qua registry.

Member A implement.
"""
from __future__ import annotations

import json
from pathlib import Path

from ontology.models import ThresholdEntry


_DEFAULT_CONFIG = Path(__file__).parent / "calibrator_table.json"


class ThresholdRegistry:
    """Central registry cho tất cả ngưỡng số trong pipeline."""

    def __init__(self, config_path: str | Path | None = None):
        """
        Load thresholds từ config file.

        Args:
            config_path: Path tới calibrator_table.json hoặc custom config.
                         None → dùng default config.
        """
        path = Path(config_path) if config_path else _DEFAULT_CONFIG
        self._entries: dict[str, ThresholdEntry] = {}
        if path.exists():
            self._load(path)

    def _load(self, path: Path) -> None:
        """Parse config JSON → ThresholdEntry instances."""
        # TODO: Member A implement
        raise NotImplementedError("ThresholdRegistry._load() — Member A implement")

    def get(self, key: str, default: float | None = None) -> float:
        """Lấy giá trị ngưỡng theo key. Raise KeyError nếu không có và không có default."""
        # TODO: Member A implement
        raise NotImplementedError("ThresholdRegistry.get() — Member A implement")

    def maturity(self, key: str) -> str:
        """Lấy maturity level của ngưỡng."""
        # TODO: Member A implement
        raise NotImplementedError("ThresholdRegistry.maturity() — Member A implement")

    def all_entries(self) -> dict[str, ThresholdEntry]:
        """Trả toàn bộ entries."""
        return dict(self._entries)
