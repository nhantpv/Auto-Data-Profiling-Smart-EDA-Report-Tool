from __future__ import annotations

import logging
import threading
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Callable
import json
import traceback

from webapp.progress_bus import ProgressBus, get_bus, release_bus


JobCallable = Callable[[], dict[str, Any] | None]

_DRAIN_INTERVAL_S = 0.5   # Drain interval: 500ms

logger = logging.getLogger("smart_eda.runtime")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobRuntime:
    def __init__(self, jobs_dir: Path, max_workers: int = 2) -> None:
        self.jobs_dir = jobs_dir
        self.jobs_dir.mkdir(parents=True, exist_ok=True)
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="smart-eda-job")
        self._futures: dict[str, Future] = {}
        self._lock = Lock()

    def submit(
        self,
        job_id: str,
        mode: str,
        spec: dict[str, Any],
        runner: JobCallable,
    ) -> dict[str, Any]:
        logger.info("[JOB] Submit job_id=%s mode=%s", job_id, mode)
        self._write_meta(job_id, {
            "job_id": job_id,
            "mode": mode,
            "status": "queued",
            "progress": 0.02,
            "message": "⏳ Đang xếp hàng...",
            "steps": [],
            "created_at": _now(),
            "updated_at": _now(),
            "started_at": None,
            "completed_at": None,
            "error": None,
            "spec": spec,
            "result": None,
        })
        future = self._executor.submit(self._execute, job_id, runner)
        with self._lock:
            self._futures[job_id] = future
        return self.get(job_id)

    def get(self, job_id: str) -> dict[str, Any]:
        path = self._meta_path(job_id)
        if not path.exists():
            raise FileNotFoundError(job_id)
        return json.loads(path.read_text(encoding="utf-8"))

    def cancel(self, job_id: str) -> dict[str, Any]:
        meta = self.get(job_id)
        with self._lock:
            future = self._futures.get(job_id)
        if meta["status"] in {"completed", "failed", "cancelled"}:
            return meta
        if future is not None and future.cancel():
            meta.update({
                "status": "cancelled",
                "progress": 1.0,
                "message": "Đã hủy trước khi thực thi",
                "updated_at": _now(),
                "completed_at": _now(),
            })
            self._write_meta(job_id, meta)
            return meta
        meta.update({
            "message": "Hủy đã yêu cầu; job đang chạy và không thể dừng an toàn.",
            "updated_at": _now(),
        })
        self._write_meta(job_id, meta)
        return meta

    def _drain_loop(self, job_id: str, bus: ProgressBus, stop_event: threading.Event) -> None:
        """Background thread: drain bus và cập nhật job.json mỗi 500ms."""
        while not stop_event.is_set():
            stop_event.wait(_DRAIN_INTERVAL_S)
            self._flush_bus(job_id, bus)
        # Final drain sau khi pipeline xong
        self._flush_bus(job_id, bus)

    def _flush_bus(self, job_id: str, bus: ProgressBus) -> None:
        """Lấy tất cả events từ bus và persist vào job.json."""
        events = bus.drain()
        if not events:
            return
        try:
            meta = self.get(job_id)
            current_steps: list = meta.get("steps", [])
            # Đổi step cuối sang "done" trước khi thêm step mới
            if current_steps and current_steps[-1].get("status") == "running":
                current_steps[-1]["status"] = "done"
            for event in events:
                current_steps.append(event)
            # Progress và message theo event cuối
            last = events[-1]
            meta.update({
                "progress": last["progress"],
                "message": last["step"],
                "steps": current_steps,
                "updated_at": _now(),
            })
            self._write_meta(job_id, meta)
        except Exception:
            pass  # Drain failure không được crash pipeline

    def _execute(self, job_id: str, runner: JobCallable) -> None:
        bus = get_bus(job_id)
        stop_drain = threading.Event()
        drain_thread = threading.Thread(
            target=self._drain_loop,
            args=(job_id, bus, stop_drain),
            name=f"drain-{job_id}",
            daemon=True,
        )

        meta = self.get(job_id)
        meta.update({
            "status": "running",
            "progress": 0.03,
            "message": "🚀 Pipeline khởi động...",
            "started_at": _now(),
            "updated_at": _now(),
        })
        self._write_meta(job_id, meta)
        logger.info("[JOB] Bắt đầu chạy job_id=%s", job_id)
        drain_thread.start()

        try:
            result = runner() or {}
            bus.close()
            stop_drain.set()
            drain_thread.join(timeout=3.0)

            meta = self.get(job_id)
            elapsed = ""
            if meta.get("started_at"):
                try:
                    start = datetime.fromisoformat(meta["started_at"])
                    secs = int((datetime.now(timezone.utc) - start).total_seconds())
                    elapsed = f" — {secs}s"
                except Exception:
                    pass
            meta.update({
                "status": "completed",
                "progress": 1.0,
                "message": f"✅ Hoàn thành{elapsed}",
                "completed_at": _now(),
                "updated_at": _now(),
                "error": None,
                "result": result,
            })
            self._write_meta(job_id, meta)
            logger.info("[JOB] Hoàn thành job_id=%s (%s)", job_id, elapsed.strip(" — ") or "?s")
        except Exception as exc:  # pragma: no cover
            bus.close()
            stop_drain.set()
            drain_thread.join(timeout=3.0)

            meta = self.get(job_id)
            meta.update({
                "status": "failed",
                "progress": 1.0,
                "message": "❌ Pipeline thất bại",
                "completed_at": _now(),
                "updated_at": _now(),
                "error": {
                    "type": exc.__class__.__name__,
                    "detail": str(exc),
                    "traceback": traceback.format_exc(limit=8),
                },
            })
            self._write_meta(job_id, meta)
            logger.error("[JOB] THẤT BẠI job_id=%s — %s: %s", job_id, exc.__class__.__name__, exc)
            logger.debug("[JOB] Traceback:\n%s", traceback.format_exc())
        finally:
            release_bus(job_id)

    def _meta_path(self, job_id: str) -> Path:
        return self.jobs_dir / job_id / "job.json"

    def _write_meta(self, job_id: str, meta: dict[str, Any]) -> None:
        job_dir = self.jobs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        path = job_dir / "job.json"
        tmp = job_dir / "job.json.tmp"
        tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
