from __future__ import annotations

import json
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles

import run_pipeline
from webapp.runtime import JobRuntime


APP_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = APP_ROOT.parents[1]
STATIC_DIR = APP_ROOT / "static"
RUNTIME_DIR = PROJECT_ROOT / "runtime"
UPLOAD_DIR = RUNTIME_DIR / "uploads"
JOBS_DIR = RUNTIME_DIR / "jobs"
EXAMPLES_DIR = PROJECT_ROOT / "examples" / "sample_datasets"
EXAMPLES_MANIFEST = EXAMPLES_DIR / "manifest.json"

ALLOWED_DATA_SUFFIXES = {".csv", ".xlsx", ".xls", ".parquet", ".json", ".jsonl", ".ndjson"}
ALLOWED_SCHEMA_SUFFIXES = {".dbml", ".sql"}
KNOWN_OUTPUTS = {
    "data_quality_findings.json",
    "schema_evaluation_findings.json",
    "dataset_verdict.json",
    "summary_report.md",
    "l4_report.md",
    "guardrail_report.json",
}
MAX_UPLOAD_BYTES = int(os.getenv("SMART_EDA_MAX_UPLOAD_MB", "100")) * 1024 * 1024
MAX_MULTI_FILES = int(os.getenv("SMART_EDA_MAX_MULTI_FILES", "10"))
JOB_WORKERS = int(os.getenv("SMART_EDA_JOB_WORKERS", "2"))
_JOB_ID_RE = re.compile(r"^[a-f0-9]{12}$")
_JOB_RUNTIME: JobRuntime | None = None


app = FastAPI(title="Smart EDA Local Production", version="0.1.0", docs_url="/api/docs")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def _runtime() -> JobRuntime:
    global _JOB_RUNTIME
    if _JOB_RUNTIME is None or _JOB_RUNTIME.jobs_dir != JOBS_DIR:
        _JOB_RUNTIME = JobRuntime(JOBS_DIR, max_workers=JOB_WORKERS)
    return _JOB_RUNTIME


def _ensure_runtime() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    JOBS_DIR.mkdir(parents=True, exist_ok=True)


def _new_job_dirs() -> tuple[str, Path, Path]:
    _ensure_runtime()
    job_id = uuid.uuid4().hex[:12]
    upload_dir = UPLOAD_DIR / job_id
    output_dir = JOBS_DIR / job_id
    upload_dir.mkdir(parents=True, exist_ok=False)
    output_dir.mkdir(parents=True, exist_ok=False)
    return job_id, upload_dir, output_dir


def _validate_job_id(job_id: str) -> str:
    if not _JOB_ID_RE.match(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return job_id


def _safe_upload_name(upload: UploadFile, allowed_suffixes: set[str]) -> str:
    raw_name = Path(upload.filename or "").name
    suffix = Path(raw_name).suffix.lower()
    if not raw_name or suffix not in allowed_suffixes:
        supported = ", ".join(sorted(allowed_suffixes))
        raise HTTPException(status_code=400, detail=f"Unsupported file '{raw_name}'. Supported: {supported}")
    return raw_name


def _save_upload(upload: UploadFile, target_dir: Path, allowed_suffixes: set[str]) -> Path:
    name = _safe_upload_name(upload, allowed_suffixes)
    target = target_dir / name
    if target.exists():
        stem = target.stem
        suffix = target.suffix
        counter = 2
        while target.exists():
            target = target_dir / f"{stem}_{counter}{suffix}"
            counter += 1
    size = 0
    with target.open("wb") as f:
        while chunk := upload.file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                target.unlink(missing_ok=True)
                max_mb = MAX_UPLOAD_BYTES // (1024 * 1024)
                raise HTTPException(status_code=413, detail=f"Upload exceeds {max_mb} MB per file.")
            f.write(chunk)
    return target


def _read_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _job_response(job_id: str, output_dir: Path) -> dict:
    job_id = _validate_job_id(job_id)
    try:
        meta = _runtime().get(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found") from None

    report_path = output_dir / "l4_report.md"
    if not report_path.exists():
        report_path = output_dir / "summary_report.md"
    files = sorted(
        p.name for p in output_dir.iterdir()
        if p.is_file() and (p.name in KNOWN_OUTPUTS or p.suffix.lower() == ".csv")
    )
    raw_error = meta.get("error")
    public_error = None
    if isinstance(raw_error, dict):
        public_error = {
            "type": raw_error.get("type"),
            "detail": raw_error.get("detail"),
        }
    return {
        "job_id": job_id,
        "status": meta.get("status", "unknown"),
        "progress": meta.get("progress", 0.0),
        "message": meta.get("message", ""),
        "error": public_error,
        "files": files,
        "report": report_path.read_text(encoding="utf-8") if report_path.exists() else "",
        "dataset_verdict": _read_json(output_dir / "dataset_verdict.json"),
        "data_quality_findings": _read_json(output_dir / "data_quality_findings.json"),
        "schema_evaluation_findings": _read_json(output_dir / "schema_evaluation_findings.json"),
        "guardrail_report": _read_json(output_dir / "guardrail_report.json"),
        "links": {
            name: f"/api/jobs/{job_id}/files/{name}"
            for name in files
        },
    }


def _submit_pipeline_job(job_id: str, mode: str, spec: dict) -> dict:
    def runner() -> dict:
        if mode == "single":
            return run_pipeline.run(
                spec["data_paths"][0],
                spec["output_dir"],
                spec.get("schema_path"),
                profiling_minimal=bool(spec.get("profiling_minimal", False)),
            )
        if mode == "multi":
            return run_pipeline.run_multi(
                spec["data_paths"],
                spec["output_dir"],
                spec.get("schema_path"),
            )
        raise RuntimeError(f"Unsupported job mode: {mode}")

    return _runtime().submit(job_id=job_id, mode=mode, spec=spec, runner=runner)


def _load_examples() -> list[dict]:
    if not EXAMPLES_MANIFEST.exists():
        return []
    examples = json.loads(EXAMPLES_MANIFEST.read_text(encoding="utf-8"))
    if not isinstance(examples, list):
        raise HTTPException(status_code=500, detail="Example manifest must be a list.")
    return examples


def _example_by_id(example_id: str) -> dict:
    for example in _load_examples():
        if example.get("id") == example_id:
            return example
    raise HTTPException(status_code=404, detail="Example dataset not found")


def _example_source_path(relative_path: str, allowed_suffixes: set[str]) -> Path:
    source = (EXAMPLES_DIR / relative_path).resolve()
    root = EXAMPLES_DIR.resolve()
    if not source.is_relative_to(root) or not source.is_file():
        raise HTTPException(status_code=404, detail=f"Example file not found: {relative_path}")
    if source.suffix.lower() not in allowed_suffixes:
        supported = ", ".join(sorted(allowed_suffixes))
        raise HTTPException(status_code=400, detail=f"Unsupported example file '{source.name}'. Supported: {supported}")
    return source


def _copy_example_file(relative_path: str, target_dir: Path, allowed_suffixes: set[str]) -> Path:
    source = _example_source_path(relative_path, allowed_suffixes)
    target = target_dir / source.name
    shutil.copy2(source, target)
    return target


@app.get("/", response_class=HTMLResponse)
def index() -> str:
    return (STATIC_DIR / "index.html").read_text(encoding="utf-8")


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon() -> PlainTextResponse:
    return PlainTextResponse("", status_code=204)


@app.get("/api/examples")
def list_examples() -> JSONResponse:
    return JSONResponse({"examples": _load_examples()})


@app.post("/api/examples/{example_id}/run")
def run_example_job(example_id: str, profiling_minimal: bool = False) -> JSONResponse:
    example = _example_by_id(example_id)
    mode = example.get("mode")
    data_files = example.get("data_files") or []
    schema_file = example.get("schema_file")
    if not isinstance(data_files, list) or not data_files:
        raise HTTPException(status_code=400, detail="Example dataset has no data files.")

    job_id, upload_dir, output_dir = _new_job_dirs()
    try:
        data_paths = [
            _copy_example_file(str(relative_path), upload_dir, ALLOWED_DATA_SUFFIXES)
            for relative_path in data_files
        ]
        schema_path = (
            _copy_example_file(str(schema_file), upload_dir, ALLOWED_SCHEMA_SUFFIXES)
            if schema_file
            else None
        )

        if mode == "single":
            spec = {
                "data_paths": [str(data_paths[0])],
                "schema_path": str(schema_path) if schema_path else None,
                "output_dir": str(output_dir),
                "profiling_minimal": profiling_minimal,
            }
        elif mode == "multi":
            spec = {
                "data_paths": [str(path) for path in data_paths],
                "schema_path": str(schema_path) if schema_path else None,
                "output_dir": str(output_dir),
            }
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported example mode: {mode}")

        _submit_pipeline_job(job_id, str(mode), spec)
        return JSONResponse(_job_response(job_id, output_dir), status_code=202)
    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse({"job_id": job_id, "status": "failed", "detail": str(exc)}, status_code=500)


@app.post("/api/jobs")
def run_single_job(
    data_file: Annotated[UploadFile, File(...)],
    schema_file: Annotated[UploadFile | None, File()] = None,
    profiling_minimal: Annotated[bool, Form()] = False,
) -> JSONResponse:
    job_id, upload_dir, output_dir = _new_job_dirs()
    try:
        data_path = _save_upload(data_file, upload_dir, ALLOWED_DATA_SUFFIXES)
        schema_path = None
        if schema_file is not None and schema_file.filename:
            schema_path = _save_upload(schema_file, upload_dir, ALLOWED_SCHEMA_SUFFIXES)

        spec = {
            "data_paths": [str(data_path)],
            "schema_path": str(schema_path) if schema_path else None,
            "output_dir": str(output_dir),
            "profiling_minimal": profiling_minimal,
        }
        _submit_pipeline_job(job_id, "single", spec)
        return JSONResponse(_job_response(job_id, output_dir), status_code=202)
    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse({"job_id": job_id, "status": "failed", "detail": str(exc)}, status_code=500)


@app.post("/api/jobs/multi")
def run_multi_job(
    data_files: Annotated[list[UploadFile], File(...)],
    schema_file: Annotated[UploadFile | None, File()] = None,
) -> JSONResponse:
    if len(data_files) < 2:
        raise HTTPException(status_code=400, detail="Multi-table mode requires at least two data files.")
    if len(data_files) > MAX_MULTI_FILES:
        raise HTTPException(status_code=400, detail=f"Multi-table mode supports at most {MAX_MULTI_FILES} data files.")

    job_id, upload_dir, output_dir = _new_job_dirs()
    try:
        data_paths = [_save_upload(upload, upload_dir, ALLOWED_DATA_SUFFIXES) for upload in data_files]
        schema_path = None
        if schema_file is not None and schema_file.filename:
            schema_path = _save_upload(schema_file, upload_dir, ALLOWED_SCHEMA_SUFFIXES)

        spec = {
            "data_paths": [str(path) for path in data_paths],
            "schema_path": str(schema_path) if schema_path else None,
            "output_dir": str(output_dir),
        }
        _submit_pipeline_job(job_id, "multi", spec)
        return JSONResponse(_job_response(job_id, output_dir), status_code=202)
    except HTTPException:
        raise
    except Exception as exc:
        return JSONResponse({"job_id": job_id, "status": "failed", "detail": str(exc)}, status_code=500)


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> JSONResponse:
    job_id = _validate_job_id(job_id)
    output_dir = JOBS_DIR / job_id
    if not output_dir.exists():
        raise HTTPException(status_code=404, detail="Job not found")
    return JSONResponse(_job_response(job_id, output_dir))


@app.post("/api/jobs/{job_id}/cancel")
def cancel_job(job_id: str) -> JSONResponse:
    job_id = _validate_job_id(job_id)
    try:
        meta = _runtime().cancel(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found") from None
    return JSONResponse(_job_response(job_id, JOBS_DIR / job_id) | {"message": meta.get("message", "")})


@app.post("/api/jobs/{job_id}/retry")
def retry_job(job_id: str) -> JSONResponse:
    job_id = _validate_job_id(job_id)
    try:
        old_meta = _runtime().get(job_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Job not found") from None
    old_spec = old_meta.get("spec")
    if not isinstance(old_spec, dict):
        raise HTTPException(status_code=400, detail="Job cannot be retried because its spec is missing.")
    new_job_id, _upload_dir, output_dir = _new_job_dirs()
    spec = dict(old_spec)
    spec["output_dir"] = str(output_dir)
    mode = str(old_meta.get("mode") or "single")
    _submit_pipeline_job(new_job_id, mode, spec)
    return JSONResponse(_job_response(new_job_id, output_dir), status_code=202)


@app.get("/api/jobs/{job_id}/files/{file_name}")
def get_job_file(job_id: str, file_name: str):
    job_id = _validate_job_id(job_id)
    path = JOBS_DIR / job_id / file_name
    if file_name not in KNOWN_OUTPUTS and path.suffix.lower() != ".csv":
        raise HTTPException(status_code=404, detail="File not found")
    if not path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    if file_name.endswith(".md"):
        return PlainTextResponse(path.read_text(encoding="utf-8"))
    if file_name.endswith(".csv"):
        return FileResponse(path, media_type="text/csv", filename=file_name)
    return FileResponse(path, media_type="application/json", filename=file_name)
