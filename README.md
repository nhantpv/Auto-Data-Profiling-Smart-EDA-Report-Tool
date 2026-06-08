# Auto-Data-Profiling-Smart-EDA-Report-Tool

Automated data profiling and smart EDA reporting tool.

## Setup

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Run

Production-style localhost app:

```bash
uvicorn webapp.app:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

Built-in dirty sample datasets are available in the left panel of the localhost app.
The source files live in `examples/sample_datasets/` and include:

- `students_csv_dirty`: CSV with PK, missing-value, type, extra-column, and outlier issues.
- `orders_json_dirty`: JSON with invalid order records and schema drift.
- `school_multi_relations`: multi-table CSV set with FK orphans, missing table, duplicate PKs, and alias columns.
- `school_multi_infer_schema`: multi-table CSV set with no DBML/DDL; schema and relationships are inferred from data.

Single-table profiling:

```bash
python run_pipeline.py tests/fixtures/outliers_realistic.csv output
```

With schema validation:

```bash
python run_pipeline.py tests/fixtures/schema_bad.csv output tests/fixtures/schema_bad.dbml
```

Multi-table validation:

```bash
python run_pipeline.py --multi tests/fixtures/multi/users.csv tests/fixtures/multi/orders.csv --schema tests/fixtures/multi/shop.dbml --out output
```

Multi-table inferred schema validation:

```bash
python run_pipeline.py --multi examples/sample_datasets/school_multi_relations/schools.csv examples/sample_datasets/school_multi_relations/classes.csv examples/sample_datasets/school_multi_relations/students.csv --out output
```

Supported data inputs: `.csv`, `.xlsx`, `.xls`, `.parquet`, `.json`, `.jsonl`, `.ndjson`.
Supported schema inputs: `.dbml`, `.sql`.

The web API runs pipelines as background jobs. Submit endpoints return `202` with
a `job_id`; poll `GET /api/jobs/{job_id}` for `queued`, `running`, `completed`,
`failed`, or `cancelled`.

Production-style local controls:

- `SMART_EDA_MAX_UPLOAD_MB`: per-file upload limit, default `100`.
- `SMART_EDA_MAX_MULTI_FILES`: maximum uploaded data files in multi-table mode, default `10`.
- `SMART_EDA_JOB_WORKERS`: background worker count, default `2`.
- `SMART_EDA_L4_PROVIDER`: `deterministic` by default; set to `openai` to try an LLM narrative.
- `SMART_EDA_L4_MODEL`: OpenAI model id when `SMART_EDA_L4_PROVIDER=openai`, default `gpt-5`.
- `OPENAI_API_KEY`: required only for OpenAI L4 mode.

Outputs include:

- `data_quality_findings.json`
- `schema_evaluation_findings.json` when schema or multi-table mode is used
- `dataset_verdict.json`
- `summary_report.md`
- `l4_report.md`
- `guardrail_report.json`
- `*__diagnostic_*.png` when outlier diagnostic charts are available
- `*__outlier_rows.csv` and `*__duplicate_rows.csv` when full anomaly-row exports are available

Multi-table mode writes `data_quality_findings.json` as a
`multi_table_data_quality_v1` bundle with one findings payload per table and a
combined cross-table summary.

Schema alias/key/relationship inference defaults live in
`config/schema_inference_policy.json` so domain synonyms and thresholds can be
tuned without editing `src/engines/schema_engine.py`.

Schema relationship inference can be benchmarked against labelled cases:

```bash
python scripts/evaluate_schema_relationships.py
```

Pipeline artifact output, including L3.5 diagnostic charts and anomaly-row
exports, can be checked with:

```bash
python scripts/evaluate_pipeline_artifacts.py
```

## Test

```bash
pytest tests/ -q
```
