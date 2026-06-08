from __future__ import annotations

from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Callable
import json
import traceback


JobCallable = Callable[[], dict[str, Any] | None]


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
        self._write_meta(job_id, {
            "job_id": job_id,
            "mode": mode,
            "status": "queued",
            "progress": 0.05,
            "message": "Queued",
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
                "message": "Cancelled before execution",
                "updated_at": _now(),
                "completed_at": _now(),
            })
            self._write_meta(job_id, meta)
            return meta
        meta.update({
            "message": "Cancel requested; job is already running and cannot be interrupted safely.",
            "updated_at": _now(),
        })
        self._write_meta(job_id, meta)
        return meta

    def _execute(self, job_id: str, runner: JobCallable) -> None:
        meta = self.get(job_id)
        meta.update({
            "status": "running",
            "progress": 0.25,
            "message": "Pipeline running",
            "started_at": _now(),
            "updated_at": _now(),
        })
        self._write_meta(job_id, meta)
        try:
            result = runner() or {}
            meta = self.get(job_id)
            meta.update({
                "status": "completed",
                "progress": 1.0,
                "message": "Completed",
                "completed_at": _now(),
                "updated_at": _now(),
                "error": None,
                "result": result,
            })
            self._write_meta(job_id, meta)
        except Exception as exc:  # pragma: no cover - traceback branch still covered via status.
            meta = self.get(job_id)
            meta.update({
                "status": "failed",
                "progress": 1.0,
                "message": "Pipeline failed",
                "completed_at": _now(),
                "updated_at": _now(),
                "error": {
                    "type": exc.__class__.__name__,
                    "detail": str(exc),
                    "traceback": traceback.format_exc(limit=8),
                },
            })
            self._write_meta(job_id, meta)

    def _meta_path(self, job_id: str) -> Path:
        return self.jobs_dir / job_id / "job.json"

    def _write_meta(self, job_id: str, meta: dict[str, Any]) -> None:
        job_dir = self.jobs_dir / job_id
        job_dir.mkdir(parents=True, exist_ok=True)
        path = job_dir / "job.json"
        tmp = job_dir / "job.json.tmp"
        tmp.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)
