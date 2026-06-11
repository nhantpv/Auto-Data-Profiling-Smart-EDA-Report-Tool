"""Finding Registry — Central SSOT cho tất cả findings.

Xem ARCHITECT v5.4 §L3 Finding Registry.
Dedup, assign finding_id, và cung cấp truy vấn.

Member A implement.
"""
from __future__ import annotations

import hashlib
from typing import Iterator

from ontology.models import AnomalyRecord, IntegrityError


class FindingRegistry:
    """Central registry — mọi finding đi qua đây trước khi vào report."""

    def __init__(self) -> None:
        self._records: dict[str, AnomalyRecord] = {}
        self._integrity: dict[str, IntegrityError] = {}

    def register_anomaly(self, record: AnomalyRecord) -> AnomalyRecord:
        """
        Đăng ký 1 anomaly, gán finding_id nếu chưa có, dedup.

        Returns:
            Record đã có finding_id
        """
        # TODO: Member A implement
        raise NotImplementedError("register_anomaly() — Member A implement")

    def register_integrity_error(self, error: IntegrityError) -> IntegrityError:
        """Đăng ký 1 integrity error, gán finding_id."""
        # TODO: Member A implement
        raise NotImplementedError("register_integrity_error() — Member A implement")

    def get_all_anomalies(self) -> list[AnomalyRecord]:
        """Trả tất cả anomalies đã đăng ký (deduped)."""
        return list(self._records.values())

    def get_all_integrity_errors(self) -> list[IntegrityError]:
        """Trả tất cả integrity errors đã đăng ký."""
        return list(self._integrity.values())

    def count(self) -> int:
        """Tổng số findings."""
        return len(self._records) + len(self._integrity)

    @staticmethod
    def _generate_id(issue_type: str, column: str | None, table: str | None = None) -> str:
        """Tạo deterministic finding_id từ issue metadata."""
        raw = f"{issue_type}|{column or ''}|{table or ''}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]
