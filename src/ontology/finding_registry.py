"""Finding Registry — Central SSOT cho tất cả findings.

Xem ARCHITECT v5.4 §L3 Finding Registry.
Dedup, assign finding_id, và cung cấp truy vấn.
"""
from __future__ import annotations

import hashlib
import logging

from ontology.models import (
    AnomalyRecord,
    IntegrityError,
    Provenance,
    Severity,
    SEVERITY_ORDER,
)

logger = logging.getLogger(__name__)


def _severity_rank(sev: Severity) -> int:
    """Return numeric rank for severity comparison."""
    return SEVERITY_ORDER.index(sev)


def _effective_severity(record: AnomalyRecord | IntegrityError) -> Severity:
    """Return compound_severity if set, else severity."""
    return record.compound_severity if record.compound_severity is not None else record.severity


class FindingRegistry:
    """Central registry — mọi finding đi qua đây trước khi vào report.

    Provides:
    - Deterministic ``finding_id`` generation from issue metadata
    - Dedup by finding_id (keeps higher-severity record)
    - Query interface for downstream consumers (Dispatcher, Editor, etc.)
    """

    def __init__(self) -> None:
        self._records: dict[str, AnomalyRecord] = {}
        self._integrity: dict[str, IntegrityError] = {}

    def register_anomaly(self, record: AnomalyRecord) -> AnomalyRecord:
        """Đăng ký 1 anomaly, gán finding_id nếu chưa có, dedup.

        Dedup rule: nếu cùng finding_id → giữ record có effective severity cao hơn.

        Returns:
            Record đã có finding_id (có thể là bản gốc hoặc bản đã có trong registry).
        """
        if record.finding_id is None:
            record = record.model_copy(update={
                "finding_id": self._generate_id(
                    record.issue_type,
                    record.affected_column,
                ),
            })

        fid = record.finding_id
        assert fid is not None

        existing = self._records.get(fid)
        if existing is not None:
            # Dedup: keep higher severity
            if _severity_rank(_effective_severity(record)) > _severity_rank(_effective_severity(existing)):
                logger.debug("FindingRegistry: replacing %s (severity upgrade)", fid)
                self._records[fid] = record
            else:
                logger.debug("FindingRegistry: dedup %s (keeping existing)", fid)
                return existing
        else:
            self._records[fid] = record

        return self._records[fid]

    def register_integrity_error(self, error: IntegrityError) -> IntegrityError:
        """Đăng ký 1 integrity error, gán finding_id.

        Dedup rule: cùng finding_id → giữ severity cao hơn.

        Returns:
            Error đã có finding_id.
        """
        if error.finding_id is None:
            error = error.model_copy(update={
                "finding_id": self._generate_id(
                    error.error_type,
                    error.affected_column,
                    error.affected_table,
                ),
            })

        fid = error.finding_id
        assert fid is not None

        existing = self._integrity.get(fid)
        if existing is not None:
            if _severity_rank(_effective_severity(error)) > _severity_rank(_effective_severity(existing)):
                logger.debug("FindingRegistry: replacing integrity %s (severity upgrade)", fid)
                self._integrity[fid] = error
            else:
                return existing
        else:
            self._integrity[fid] = error

        return self._integrity[fid]

    def register_anomalies(self, records: list[AnomalyRecord]) -> list[AnomalyRecord]:
        """Batch register — convenience method.

        Returns:
            List of registered (possibly deduped) records.
        """
        return [self.register_anomaly(r) for r in records]

    def register_integrity_errors(self, errors: list[IntegrityError]) -> list[IntegrityError]:
        """Batch register integrity errors."""
        return [self.register_integrity_error(e) for e in errors]

    def get_all_anomalies(self) -> list[AnomalyRecord]:
        """Trả tất cả anomalies đã đăng ký (deduped)."""
        return list(self._records.values())

    def get_all_integrity_errors(self) -> list[IntegrityError]:
        """Trả tất cả integrity errors đã đăng ký."""
        return list(self._integrity.values())

    def count(self) -> int:
        """Tổng số findings."""
        return len(self._records) + len(self._integrity)

    def get_by_id(self, finding_id: str) -> AnomalyRecord | IntegrityError | None:
        """Lookup finding by ID."""
        return self._records.get(finding_id) or self._integrity.get(finding_id)

    def get_by_type(self, issue_type: str) -> list[AnomalyRecord]:
        """Get all anomalies of a specific issue_type."""
        return [r for r in self._records.values() if r.issue_type == issue_type]

    @staticmethod
    def _generate_id(
        issue_type: str,
        column: str | None,
        table: str | None = None,
    ) -> str:
        """Tạo deterministic finding_id từ issue metadata.

        Uses SHA-256 truncated to 12 hex chars. Deterministic: same inputs
        always produce the same ID.
        """
        raw = f"{issue_type}|{column or ''}|{table or ''}"
        return hashlib.sha256(raw.encode()).hexdigest()[:12]

    def __repr__(self) -> str:
        return f"FindingRegistry(anomalies={len(self._records)}, integrity={len(self._integrity)})"
