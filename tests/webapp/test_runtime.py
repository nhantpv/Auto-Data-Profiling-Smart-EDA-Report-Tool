from __future__ import annotations

import time
from threading import Event, Lock

from webapp.runtime import JobRuntime


def _wait_for(predicate, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.02)
    raise AssertionError("Timed out waiting for condition.")


def test_job_runtime_limits_concurrency_and_cancels_queued_job(tmp_path):
    runtime = JobRuntime(tmp_path / "jobs", max_workers=2)
    release = Event()
    lock = Lock()
    started: list[str] = []

    def make_runner(name: str):
        def runner():
            with lock:
                started.append(name)
            release.wait(timeout=2)
            return {"name": name}

        return runner

    runtime.submit("jobaaaa0001", "single", {"name": "one"}, make_runner("one"))
    runtime.submit("jobbbbb0002", "single", {"name": "two"}, make_runner("two"))
    runtime.submit("jobcccc0003", "single", {"name": "three"}, make_runner("three"))

    _wait_for(lambda: sorted(started) == ["one", "two"])
    cancelled = runtime.cancel("jobcccc0003")
    release.set()
    _wait_for(lambda: runtime.get("jobaaaa0001")["status"] == "completed")
    _wait_for(lambda: runtime.get("jobbbbb0002")["status"] == "completed")

    assert cancelled["status"] == "cancelled"
    assert runtime.get("jobcccc0003")["status"] == "cancelled"
    assert sorted(started) == ["one", "two"]
