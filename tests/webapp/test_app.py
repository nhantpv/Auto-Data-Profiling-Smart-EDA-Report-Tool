import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from webapp import app as web_app


def _write_outputs(out_dir: str, include_dq: bool = True, include_schema: bool = False) -> None:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    if include_dq:
        (out / "data_quality_findings.json").write_text(
            json.dumps({"dataset_meta": {"file_name": "data.csv"}, "columns": {}, "anomalies": []}),
            encoding="utf-8",
        )
    if include_schema:
        (out / "schema_evaluation_findings.json").write_text(
            json.dumps({"schema_meta": {"schema_file": "schema.dbml"}, "tables": [], "integrity_errors": []}),
            encoding="utf-8",
        )
    (out / "dataset_verdict.json").write_text(
        json.dumps({
            "dataset_meta": {
                "file_name": "data.csv",
                "n": 2,
                "n_var": 2,
                "memory_size": 0,
                "p_cells_missing": 0.0,
                "n_duplicates": 0,
                "p_duplicates": 0.0,
            },
            "verdict": "READY",
            "verdict_rationale": "No issues found",
            "summary": {"total_issues": 0, "critical": 0, "high": 0, "warn": 0, "info": 0},
        }),
        encoding="utf-8",
    )
    (out / "summary_report.md").write_text("# Smart EDA Summary Report\n\nREADY\n", encoding="utf-8")
    (out / "l4_report.md").write_text("# L4 Guarded EDA Report\n\nREADY\n", encoding="utf-8")
    (out / "smart_eda_report.html").write_text("<!doctype html><html><body>Smart report</body></html>", encoding="utf-8")
    (out / "guardrail_report.json").write_text(json.dumps({"status": "passed"}), encoding="utf-8")
    (out / "data__diagnostic_x_y.png").write_bytes(b"\x89PNG\r\n\x1a\n")


def _client(tmp_path, monkeypatch):
    monkeypatch.setattr(web_app, "UPLOAD_DIR", tmp_path / "uploads")
    monkeypatch.setattr(web_app, "JOBS_DIR", tmp_path / "jobs")
    return TestClient(web_app.app)


def _await_job(client: TestClient, payload: dict) -> dict:
    job_id = payload["job_id"]
    for _ in range(60):
        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        current = response.json()
        if current["status"] in {"completed", "failed", "cancelled"}:
            return current
        time.sleep(0.05)
    raise AssertionError(f"Job {job_id} did not finish")


def test_health_and_index(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    assert client.get("/health").json() == {"status": "ok"}
    response = client.get("/")
    assert response.status_code == 200
    assert "Data Quality Workbench" in response.text


def test_single_job_upload_returns_outputs(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    def fake_run(data_path, out_dir, schema_path=None, profiling_minimal=False):
        assert Path(data_path).suffix == ".csv"
        assert profiling_minimal is True
        _write_outputs(out_dir, include_dq=True, include_schema=schema_path is not None)
        return {}

    monkeypatch.setattr(web_app.run_pipeline, "run", fake_run)
    response = client.post(
        "/api/jobs",
        files={
            "data_file": ("data.csv", b"id,value\n1,10\n2,20\n", "text/csv"),
            "schema_file": ("schema.dbml", b"Table data { id integer [pk] }", "text/plain"),
        },
        data={"profiling_minimal": "true"},
    )

    assert response.status_code == 202
    payload = _await_job(client, response.json())
    assert payload["status"] == "completed"
    assert payload["dataset_verdict"]["verdict"] == "READY"
    assert "summary_report.md" in payload["files"]
    assert "l4_report.md" in payload["files"]
    assert "smart_eda_report.html" in payload["files"]
    assert payload["report_url"].endswith("/report")
    assert "data__diagnostic_x_y.png" in payload["files"]
    assert payload["guardrail_report"]["status"] == "passed"
    assert "schema_evaluation_findings.json" in payload["files"]


def test_multi_job_with_schema_returns_report(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    def fake_run_multi(data_paths, out_dir, schema_path=None):
        assert len(data_paths) == 2
        assert Path(schema_path).suffix == ".dbml"
        _write_outputs(out_dir, include_dq=False, include_schema=True)
        return {}

    monkeypatch.setattr(web_app.run_pipeline, "run_multi", fake_run_multi)
    response = client.post(
        "/api/jobs/multi",
        files=[
            ("data_files", ("users.csv", b"id\n1\n", "text/csv")),
            ("data_files", ("orders.csv", b"id,user_id\n10,1\n", "text/csv")),
            ("schema_file", ("shop.dbml", b"Table users { id integer [pk] }", "text/plain")),
        ],
    )

    assert response.status_code == 202
    payload = _await_job(client, response.json())
    assert payload["report"].startswith("# L4")
    assert "dataset_verdict.json" in payload["files"]


def test_multi_job_without_schema_infers_relationships(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    def fake_run_multi(data_paths, out_dir, schema_path=None):
        assert len(data_paths) == 2
        assert schema_path is None
        _write_outputs(out_dir, include_dq=False, include_schema=True)
        return {}

    monkeypatch.setattr(web_app.run_pipeline, "run_multi", fake_run_multi)
    response = client.post(
        "/api/jobs/multi",
        files=[
            ("data_files", ("schools.csv", b"id_school\nS01\n", "text/csv")),
            ("data_files", ("students.csv", b"student_id,truong_hoc\n1,S01\n", "text/csv")),
        ],
    )

    assert response.status_code == 202
    payload = _await_job(client, response.json())
    assert payload["status"] == "completed"
    assert "schema_evaluation_findings.json" in payload["files"]


def test_multi_job_accepts_confirmed_schema_and_fact_table(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    def fake_run_multi(data_paths, out_dir, schema_path=None, confirmed_schema_path=None, fact_table=None):
        assert len(data_paths) == 2
        assert schema_path is None
        assert Path(confirmed_schema_path).suffix == ".json"
        assert fact_table == "orders"
        _write_outputs(out_dir, include_dq=False, include_schema=True)
        return {}

    monkeypatch.setattr(web_app.run_pipeline, "run_multi", fake_run_multi)
    response = client.post(
        "/api/jobs/multi",
        files=[
            ("data_files", ("users.csv", b"id\n1\n", "text/csv")),
            ("data_files", ("orders.csv", b"id,user_id\n10,1\n", "text/csv")),
            ("confirmed_schema_file", ("confirmed.json", b'{"fact_table":"orders"}', "application/json")),
        ],
        data={"fact_table": "orders"},
    )

    assert response.status_code == 202
    payload = _await_job(client, response.json())
    assert payload["status"] == "completed"


def test_job_report_endpoint_serves_html(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    def fake_run(data_path, out_dir, schema_path=None, profiling_minimal=False):
        _write_outputs(out_dir)
        return {}

    monkeypatch.setattr(web_app.run_pipeline, "run", fake_run)
    response = client.post(
        "/api/jobs",
        files={"data_file": ("data.csv", b"id,value\n1,10\n", "text/csv")},
    )
    payload = _await_job(client, response.json())
    report = client.get(f"/api/jobs/{payload['job_id']}/report")

    assert report.status_code == 200
    assert "text/html" in report.headers["content-type"]
    assert "Smart report" in report.text


def test_schema_suggestions_and_confirm_endpoints(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)

    def fake_run_multi(data_paths, out_dir, schema_path=None):
        _write_outputs(out_dir, include_dq=False, include_schema=True)
        out = Path(out_dir)
        (out / "schema_gate.json").write_text(
            json.dumps({
                "schema_version": "schema_gate_v1",
                "schema_status": "inferred",
                "fact_table": "orders",
                "relationships": [
                    {
                        "child_table": "orders",
                        "child_column": "user_id",
                        "parent_table": "users",
                        "parent_column": "id",
                        "confidence": 0.95,
                    }
                ],
            }),
            encoding="utf-8",
        )
        (out / "schema_evaluation_findings.json").write_text(
            json.dumps({
                "schema_meta": {"schema_file": "inferred", "total_tables": 2, "total_relationships": 1},
                "tables": [
                    {"name": "users", "columns": ["id"]},
                    {"name": "orders", "columns": ["id", "user_id"]},
                ],
                "integrity_errors": [],
                "relationships": [
                    {
                        "child_table": "orders",
                        "child_column": "user_id",
                        "parent_table": "users",
                        "parent_column": "id",
                        "confidence": 0.95,
                    }
                ],
            }),
            encoding="utf-8",
        )
        return {}

    monkeypatch.setattr(web_app.run_pipeline, "run_multi", fake_run_multi)
    response = client.post(
        "/api/jobs/multi",
        files=[
            ("data_files", ("users.csv", b"id\n1\n", "text/csv")),
            ("data_files", ("orders.csv", b"id,user_id\n10,1\n", "text/csv")),
        ],
    )
    payload = _await_job(client, response.json())
    suggestions = client.get(f"/api/jobs/{payload['job_id']}/schema-suggestions")
    assert suggestions.status_code == 200
    assert suggestions.json()["suggested_pks"]["users"][0]["column"] == "id"

    confirm = client.post(
        f"/api/jobs/{payload['job_id']}/schema-confirm",
        json={"fact_table": "orders", "confirmed_fks": suggestions.json()["relationships"]},
    )
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "saved"


def test_rejects_unsupported_upload(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    response = client.post(
        "/api/jobs",
        files={"data_file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


def test_rejects_upload_over_limit(tmp_path, monkeypatch):
    monkeypatch.setattr(web_app, "MAX_UPLOAD_BYTES", 4)
    client = _client(tmp_path, monkeypatch)

    response = client.post(
        "/api/jobs",
        files={"data_file": ("data.csv", b"id\n12345\n", "text/csv")},
    )

    assert response.status_code == 413


def test_retry_job_reuses_saved_inputs(tmp_path, monkeypatch):
    client = _client(tmp_path, monkeypatch)
    calls = {"count": 0}

    def fake_run(data_path, out_dir, schema_path=None, profiling_minimal=False):
        calls["count"] += 1
        assert Path(data_path).exists()
        _write_outputs(out_dir)
        return {}

    monkeypatch.setattr(web_app.run_pipeline, "run", fake_run)
    response = client.post(
        "/api/jobs",
        files={"data_file": ("data.csv", b"id,value\n1,10\n", "text/csv")},
    )
    first = _await_job(client, response.json())

    retry_response = client.post(f"/api/jobs/{first['job_id']}/retry")
    assert retry_response.status_code == 202
    second = _await_job(client, retry_response.json())

    assert second["status"] == "completed"
    assert second["job_id"] != first["job_id"]
    assert calls["count"] == 2


def test_lists_example_datasets(tmp_path, monkeypatch):
    examples_dir = tmp_path / "examples"
    examples_dir.mkdir()
    (examples_dir / "manifest.json").write_text(
        json.dumps([
            {
                "id": "dirty_csv",
                "title": "Dirty CSV",
                "mode": "single",
                "data_files": ["dirty/data.csv"],
                "schema_file": "dirty/schema.dbml",
            }
        ]),
        encoding="utf-8",
    )
    monkeypatch.setattr(web_app, "EXAMPLES_DIR", examples_dir)
    monkeypatch.setattr(web_app, "EXAMPLES_MANIFEST", examples_dir / "manifest.json")
    client = _client(tmp_path, monkeypatch)

    response = client.get("/api/examples")

    assert response.status_code == 200
    assert response.json()["examples"][0]["id"] == "dirty_csv"


def test_run_single_example_dataset(tmp_path, monkeypatch):
    examples_dir = tmp_path / "examples"
    sample_dir = examples_dir / "dirty"
    sample_dir.mkdir(parents=True)
    (sample_dir / "data.csv").write_text("id,value\n1,10\n", encoding="utf-8")
    (sample_dir / "schema.dbml").write_text("Table data { id integer [pk] }", encoding="utf-8")
    (examples_dir / "manifest.json").write_text(
        json.dumps([
            {
                "id": "dirty_csv",
                "title": "Dirty CSV",
                "mode": "single",
                "data_files": ["dirty/data.csv"],
                "schema_file": "dirty/schema.dbml",
            }
        ]),
        encoding="utf-8",
    )
    monkeypatch.setattr(web_app, "EXAMPLES_DIR", examples_dir)
    monkeypatch.setattr(web_app, "EXAMPLES_MANIFEST", examples_dir / "manifest.json")
    client = _client(tmp_path, monkeypatch)

    def fake_run(data_path, out_dir, schema_path=None, profiling_minimal=False):
        assert Path(data_path).name == "data.csv"
        assert Path(schema_path).name == "schema.dbml"
        assert profiling_minimal is True
        _write_outputs(out_dir, include_dq=True, include_schema=True)
        return {}

    monkeypatch.setattr(web_app.run_pipeline, "run", fake_run)
    response = client.post("/api/examples/dirty_csv/run?profiling_minimal=true")

    assert response.status_code == 202
    payload = _await_job(client, response.json())
    assert payload["status"] == "completed"
    assert "summary_report.md" in payload["files"]


def test_run_multi_example_dataset(tmp_path, monkeypatch):
    examples_dir = tmp_path / "examples"
    sample_dir = examples_dir / "shop"
    sample_dir.mkdir(parents=True)
    (sample_dir / "users.csv").write_text("id\n1\n", encoding="utf-8")
    (sample_dir / "orders.csv").write_text("id,user_id\n10,1\n", encoding="utf-8")
    (sample_dir / "schema.dbml").write_text("Table users { id integer [pk] }", encoding="utf-8")
    (examples_dir / "manifest.json").write_text(
        json.dumps([
            {
                "id": "shop_multi",
                "title": "Shop Multi",
                "mode": "multi",
                "data_files": ["shop/users.csv", "shop/orders.csv"],
                "schema_file": "shop/schema.dbml",
            }
        ]),
        encoding="utf-8",
    )
    monkeypatch.setattr(web_app, "EXAMPLES_DIR", examples_dir)
    monkeypatch.setattr(web_app, "EXAMPLES_MANIFEST", examples_dir / "manifest.json")
    client = _client(tmp_path, monkeypatch)

    def fake_run_multi(data_paths, out_dir, schema_path=None):
        assert [Path(path).name for path in data_paths] == ["users.csv", "orders.csv"]
        assert Path(schema_path).name == "schema.dbml"
        _write_outputs(out_dir, include_dq=False, include_schema=True)
        return {}

    monkeypatch.setattr(web_app.run_pipeline, "run_multi", fake_run_multi)
    response = client.post("/api/examples/shop_multi/run")

    assert response.status_code == 202
    payload = _await_job(client, response.json())
    assert payload["dataset_verdict"]["verdict"] == "READY"


def test_run_multi_example_without_schema_dataset(tmp_path, monkeypatch):
    examples_dir = tmp_path / "examples"
    sample_dir = examples_dir / "shop"
    sample_dir.mkdir(parents=True)
    (sample_dir / "users.csv").write_text("id\n1\n", encoding="utf-8")
    (sample_dir / "orders.csv").write_text("id,user_id\n10,1\n", encoding="utf-8")
    (examples_dir / "manifest.json").write_text(
        json.dumps([
            {
                "id": "shop_infer",
                "title": "Shop Infer",
                "mode": "multi",
                "data_files": ["shop/users.csv", "shop/orders.csv"],
            }
        ]),
        encoding="utf-8",
    )
    monkeypatch.setattr(web_app, "EXAMPLES_DIR", examples_dir)
    monkeypatch.setattr(web_app, "EXAMPLES_MANIFEST", examples_dir / "manifest.json")
    client = _client(tmp_path, monkeypatch)

    def fake_run_multi(data_paths, out_dir, schema_path=None):
        assert [Path(path).name for path in data_paths] == ["users.csv", "orders.csv"]
        assert schema_path is None
        _write_outputs(out_dir, include_dq=False, include_schema=True)
        return {}

    monkeypatch.setattr(web_app.run_pipeline, "run_multi", fake_run_multi)
    response = client.post("/api/examples/shop_infer/run")

    assert response.status_code == 202
    payload = _await_job(client, response.json())
    assert payload["status"] == "completed"
