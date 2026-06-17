"""ProgressBus — thread-safe pipeline progress event emitter.

Mỗi job có một ProgressBus instance. Pipeline thread gọi emit() tại mỗi milestone.
JobRuntime drain thread poll và persist events vào job.json.

Thread model:
  - Pipeline thread: chỉ gọi emit() → put vào queue (non-blocking)
  - Drain thread: chỉ gọi drain() → get từ queue, append vào job.json
  - Không cần lock vì queue.Queue đã thread-safe

Usage:
    bus = get_bus(job_id)            # Trong JobRuntime._execute()
    bus.emit("📥 Đọc dữ liệu", 0.05, detail="orders.csv — 12,450 dòng")
    bus.close()                      # Sau khi pipeline xong
    release_bus(job_id)              # Cleanup
"""

from __future__ import annotations

import queue
import threading
from datetime import datetime, timezone
from typing import TypedDict


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

class StepEvent(TypedDict):
    step: str       # Tên bước hiển thị cho user
    step_id: str    # ASCII id cho frontend matching (e.g. "ingest", "ydata")
    detail: str     # Chi tiết phụ (số dòng, tên file, v.v.)
    progress: float # 0.0 – 1.0
    timestamp: str  # ISO 8601
    status: str     # "running" | "done" | "warn" | "error"


# ---------------------------------------------------------------------------
# ProgressBus
# ---------------------------------------------------------------------------

class ProgressBus:
    """Thread-safe event queue cho một pipeline job."""

    def __init__(self, job_id: str) -> None:
        self.job_id = job_id
        self._queue: queue.Queue[StepEvent | None] = queue.Queue()
        self._closed = False

    def emit(
        self,
        step: str,
        progress: float,
        detail: str = "",
        status: str = "done",
        step_id: str = "",
    ) -> None:
        """Gửi một step event. Non-blocking, safe từ bất kỳ thread nào.

        Args:
            step: Tên bước hiển thị cho user, ví dụ "📥 Đọc dữ liệu".
            progress: Tiến trình tổng thể từ 0.0 đến 1.0.
            detail: Chi tiết kỹ thuật tuỳ chọn.
            status: "done" | "running" | "warn" | "error".
            step_id: ASCII key cho frontend matching, e.g. "ingest", "ydata", "anomaly".
        """
        if self._closed:
            return
        event: StepEvent = {
            "step": step,
            "step_id": step_id,
            "detail": detail,
            "progress": float(max(0.0, min(1.0, progress))),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": status,
        }
        self._queue.put_nowait(event)

    def drain(self) -> list[StepEvent]:
        """Lấy tất cả events đang chờ trong queue.

        Non-blocking. Trả về list rỗng nếu không có gì.
        Được gọi bởi drain thread trong JobRuntime.
        """
        events: list[StepEvent] = []
        while True:
            try:
                event = self._queue.get_nowait()
                if event is None:   # sentinel → pipeline đã xong
                    break
                events.append(event)
            except queue.Empty:
                break
        return events

    def close(self) -> None:
        """Đánh dấu bus đã xong — gửi sentinel None vào queue."""
        if not self._closed:
            self._closed = True
            self._queue.put_nowait(None)


# ---------------------------------------------------------------------------
# NullBus — no-op khi pipeline chạy không có job_id (CLI mode)
# ---------------------------------------------------------------------------

class NullBus:
    """Drop-in replacement khi không cần logging (CLI, tests)."""

    def emit(self, step: str, progress: float, detail: str = "", status: str = "done", step_id: str = "") -> None:
        pass  # no-op

    def drain(self) -> list[StepEvent]:
        return []

    def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Global Bus Registry
# ---------------------------------------------------------------------------

_registry: dict[str, ProgressBus] = {}
_registry_lock = threading.Lock()


def get_bus(job_id: str) -> ProgressBus:
    """Lấy hoặc tạo ProgressBus cho job_id. Thread-safe."""
    with _registry_lock:
        if job_id not in _registry:
            _registry[job_id] = ProgressBus(job_id)
        return _registry[job_id]


def release_bus(job_id: str) -> None:
    """Xóa bus khỏi registry sau khi job hoàn thành. Thread-safe."""
    with _registry_lock:
        _registry.pop(job_id, None)
