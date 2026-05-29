# AI SPEC — M3: Interpreter-Only L4 + TestGen-Plugin End-to-End Demo

## 1. PROJECT OVERVIEW

- **Project name:** `vsf-l4-demo`
- **One-line description:** End-to-end demo `TestGen → L3 (M1 schema) → interpreter-only L4 narrator` với token-level numerical guardrail, chạy trên SQLite sample.
- **Problem being solved:** Chưa có OSS demo chứng minh "LLM narrator cho dataops findings có thể đạt ≥ 90 % giảm hallucination" — vendor (Acceldata, Monte Carlo) đóng nguồn; OSS (PandasAI, LIDA, ydata-profiling) cho LLM tự execute trên raw data (risk cao). Dự án cần demo defensible cho Framing D Element 3.
- **Core value proposition:** "Mọi số trong narrative trace ngược về 1 finding_id. Auditable LLM cho dataops." Pragmatic deliverable ≤ 1 tháng vs ≥ 3 tháng greenfield, validate kiến trúc 4-layer deterministic-first.

## 2. TECH STACK

- **Language:** Python 3.10+ (locked `>=3.10,<3.13`).
- **Runtime:** CPython + Docker compose (TestGen container + Postgres + demo CLI).
- **Key libraries (locked):**
  - `vsf-l3-schema==0.1.0` — schema từ M1.
  - `anthropic==0.34.*` — Claude API client (primary LLM).
  - `openai==1.40.*` — GPT-4 client (secondary, cho judge eval).
  - `psycopg[binary]==3.2.*` — đọc TestGen Postgres results.
  - `sqlalchemy==2.0.*` — abstraction over SQLite + Postgres.
  - `pydantic==2.7.*`, `jsonschema==4.22.*` (inherit từ M1).
  - `tenacity==9.*` — LLM retry với backoff.
  - `click==8.1.*` — CLI.
  - `diskcache==5.*` — cache LLM response (replay mode).
  - `pytest==8.*`, `pytest-cov==5.*`, `pytest-recording==0.13.*` (VCR for LLM responses).
  - `ruff==0.5.*`, `mypy==1.10.*`.
- **External binary:** `docker compose` v2+; image `datakitchen/dataops-testgen:latest` (tag pin trong tuần 1).
- **Deployment target:** GitHub repo + Docker compose; không PyPI publish ở Phase 1.

## 3. ARCHITECTURE

- **High-level structure:** Demo CLI app — không service, không web UI. Docker compose cho infra dependency (TestGen + Postgres).
- **Directory layout:**

```
vsf-l4-demo/
├── pyproject.toml
├── README.md
├── LICENSE                          # Apache-2.0
├── Dockerfile                       # vsf-l4-demo image
├── docker-compose.yml               # testgen + postgres + demo
├── .github/workflows/ci.yml
├── data/
│   ├── sample.sqlite                # 5-table demo DB, ~1 MB, committed
│   └── sample_seed.sql              # SQL to regenerate sample.sqlite
├── configs/
│   ├── prompts/
│   │   ├── narrate_system.md        # system prompt cho L4
│   │   ├── narrate_user.md.j2       # Jinja2 user prompt template
│   │   └── few_shot/                # 5 few-shot examples (input→narrative)
│   ├── llm.yaml                     # model: claude-opus-4-7, temp=0, max_tok=2000
│   └── eval.yaml                    # 50-finding test suite spec
├── src/
│   └── vsf_l4_demo/
│       ├── __init__.py
│       ├── _version.py
│       ├── cli.py                   # narrate, eval, baseline commands
│       ├── testgen/
│       │   ├── __init__.py
│       │   ├── extractor.py         # Postgres → raw findings list
│       │   └── docker_runner.py     # subprocess for `docker compose up`
│       ├── transformer/
│       │   ├── __init__.py
│       │   └── testgen_to_l3.py     # ~100 LOC adapter (reuse từ M1 nếu có)
│       ├── narrator/
│       │   ├── __init__.py
│       │   ├── prompt_builder.py    # Jinja2 render
│       │   ├── llm_client.py        # Anthropic + cache layer
│       │   └── narrator.py          # narrate(findings) -> str
│       ├── guardrail/
│       │   ├── __init__.py
│       │   ├── tokenizer.py         # regex extract numeric tokens
│       │   ├── validator.py         # validate(output, findings) -> ValidationReport
│       │   └── policy.py            # tolerance, retry policy
│       ├── audit/
│       │   ├── __init__.py
│       │   └── trail.py             # SHA-256 hash + JSONL log
│       └── eval/
│           ├── __init__.py
│           ├── halluc_rate.py       # hallucination rate metric
│           ├── fluency_judge.py     # GPT-4 judge
│           └── report.py
├── tests/
│   ├── conftest.py
│   ├── cassettes/                   # VCR fixtures cho LLM call
│   ├── fixtures/
│   │   ├── testgen_raw_findings.json     # 50 sample finding
│   │   └── expected_l3_findings.json     # 50 transformed L3
│   ├── test_extractor.py
│   ├── test_transformer.py
│   ├── test_guardrail_token_extract.py
│   ├── test_guardrail_validation.py
│   ├── test_narrator_with_cassette.py
│   └── test_end_to_end_demo.py
└── examples/
    ├── 01_run_demo.sh               # docker compose up + narrate
    ├── 02_baseline_vs_guarded.sh    # comparison script
    └── sample_report.md             # committed expected output
```

- **Data flow:**

```
[data/sample.sqlite, 5 tables ~1 MB]
       │
       ▼
[docker compose up testgen]
       │  TestGen scans SQLite, writes results to internal Postgres
       ▼
[vsf_l4_demo.testgen.extractor.extract(pg_conn)] → list[TestGenRawFinding]
       │
       ▼
[vsf_l4_demo.transformer.testgen_to_l3.transform(raw)] → list[Finding] (M1 schema)
       │
       ├── [audit.trail.compute_hash(findings)] → sha256
       │
       ▼
[vsf_l4_demo.narrator.narrator.narrate(findings)]
       │  Loops up to 3 retries:
       │  ┌─ prompt_builder.render(findings, few_shot)
       │  ├─ llm_client.call(prompt) → llm_output_text
       │  ├─ guardrail.validator.validate(llm_output_text, findings) → ValidationReport
       │  └─ if report.failed → regenerate; else return
       │
       ▼
[NL report (Markdown)] + [audit/<run_id>.jsonl with hash, retries, validation results]
```

## 4. FEATURES

### Feature: TestGen Docker integration + extractor

- **Description:** Khởi động TestGen container, point vào `data/sample.sqlite`, đợi scan hoàn thành, kéo findings ra qua Postgres query.
- **Input:** path `data/sample.sqlite`, env `TESTGEN_PG_URL`.
- **Output:** `list[TestGenRawFinding]` — dict raw từ Postgres `test_results` table.
- **Acceptance:**
  - `vsf-demo testgen-scan --db data/sample.sqlite` hoàn thành ≤ 5 phút.
  - Extractor trả về ≥ 10 finding cho sample DB.
  - Mock mode: nếu `TESTGEN_MOCK=1`, đọc `tests/fixtures/testgen_raw_findings.json` (cho CI không cần Docker).
- **Out of scope:** Real-time monitoring; chỉ batch scan.

### Feature: L3 transformer (TestGen → M1 schema)

- **Description:** ~100 LOC adapter convert raw TestGen finding sang `Finding` của M1. Reuse `TestGenAdapter` từ M1 nếu có; M3 wrapper thêm dataset-specific context.
- **Input:** `TestGenRawFinding` dict + context `{dataset_name, sqlite_path}`.
- **Output:** `vsf_l3_schema.Finding` valid theo schema v0.1.
- **Acceptance:**
  - 50 fixture trong `tests/fixtures/testgen_raw_findings.json` transform 100 % thành Finding valid.
  - Mỗi Finding có `finding_id` (SHA-256), `dq_dimensions` populate từ TestGen DAMA scoring, `severity` map từ TestGen tier.
- **Out of scope:** Bi-directional roundtrip (L3 → TestGen).

### Feature: Interpreter-only L4 narrator

- **Description:** LLM nhận chỉ JSON of L3 findings + few-shot examples; instruction nghiêm cấm bịa số/tên. Output Markdown executive summary.
- **Input:** `list[Finding]` (≤ 50 finding per call).
- **Output:** Markdown text `report.md` content.
- **Acceptance:**
  - Temperature = 0, model `claude-opus-4-7` (configurable).
  - Prompt template không bao giờ chứa raw data row — chỉ findings JSON.
  - System prompt khoá narrator: "You must NOT invent numbers, column names, or table names not present in the findings JSON. Cite finding_id for every quantitative claim."
  - Retry tối đa 3 lần nếu guardrail reject.
  - Output ≤ 2000 token và ≥ 200 token (sanity).
  - Cache mode: cùng input hash → cùng output (diskcache).
- **Out of scope:** Multi-turn dialog, streaming output, RAG over external docs.

### Feature: Token-level numerical guardrail

- **Description:** Validator extract mọi numeric token trong LLM output, set-intersect với numeric values trong findings JSON; reject nếu có số "ngoại lai".
- **Input:** `(output_text: str, findings: list[Finding])`.
- **Output:** `ValidationReport {passed: bool, unmatched_numbers: list[str], matched_count: int, rationale: str}`.
- **Numeric token extraction:**
  - Regex: `r"-?\d{1,3}(?:[,_]\d{3})*(?:\.\d+)?(?:[eE][-+]?\d+)?%?"` (số nguyên/decimal/thousand-sep/percent/scientific).
  - Strip thousands separator + percent sign → normalized float.
- **Matching rule:**
  - Build set của tất cả numeric values từ findings: `Finding.measurement.value`, `Finding.constraint.threshold`, `Finding.confidence`, và mọi số trong `short_description`/`long_description` (extract qua cùng regex).
  - Allowed if `any(abs(output_num - allowed_num) <= tolerance)` với tolerance: 0 cho integer, 1e-4 cho decimal, hoặc relative 1e-3 cho |allowed| > 1.
  - Allowed list bonus: số nguyên ∈ {0, 1, 2, 3, 10, 100, 1000} (đếm finding, count thứ tự); ngày/year format `\d{4}` được pass-through nếu match `created_at` years.
- **Acceptance:**
  - Unit tests trên 200 hand-crafted output strings: pass-rate khớp với expected pass/fail tags ≥ 98 %.
  - Trên 50-finding eval suite, full pipeline với guardrail giảm hallucination rate **≥ 90 %** vs baseline không guardrail (KILL CRITERION).
  - Validator chạy < 50 ms / output.
- **Out of scope:** Semantic entailment, NLI-based check (giữ làm fallback nếu kill).

### Feature: Audit trail

- **Description:** Mỗi `narrate` call sinh JSONL log với hash input, prompt hash, retry list, validation reports.
- **Input:** narrate context.
- **Output:** `audit/<run_id>.jsonl` (1 dòng/event).
- **Acceptance:**
  - SHA-256 hash của canonical JSON findings được lưu.
  - Replay từ audit + cassette → bit-identical output.
- **Out of scope:** Encryption at rest, remote log shipping.

### Feature: Evaluation harness

- **Description:** Chạy 50-finding suite ở 2 mode (baseline = no guardrail; guarded = full pipeline). Tính hallucination rate, fluency, faithfulness.
- **Input:** `configs/eval.yaml` với 50 finding spec.
- **Output:** `eval/<run_id>_report.md` + JSON metric.
- **Metrics:**
  - **Hallucination rate** = `|unmatched_numeric_tokens| / |all_numeric_tokens|` trung bình trên 50.
  - **Fluency** (GPT-4 judge): 1-5 Likert, prompt template trong `eval/fluency_judge.py`.
  - **Faithfulness** (GPT-4 judge): 1-5; "does every claim trace to a finding?".
- **Acceptance:**
  - Baseline halluc rate đo được; guarded halluc rate ≤ 10 % của baseline (≥ 90 % reduction — KILL).
  - Fluency mean ≥ 4.0/5.0 (~80 %) trên guarded mode (KILL).
  - Faithfulness mean ≥ 4.0/5.0.
- **Out of scope:** Human eval (chỉ GPT-4 judge).

## 5. DATA MODELS

### `TestGenRawFinding` (intermediate, before L3)

```python
from pydantic import BaseModel
from typing import Any

class TestGenRawFinding(BaseModel):
    table_name: str
    column_name: str | None
    test_type: str               # TestGen internal label
    severity: str                # TestGen tier label
    result_score: float
    threshold: float | None
    dama_dimension: str | None   # TestGen DAMA scoring
    drill_down: dict[str, Any]   # JSON additional context
    detected_at: str             # ISO timestamp
    raw_row: dict[str, Any]      # opaque raw Postgres row
```

### `ValidationReport`

```python
from pydantic import BaseModel, Field

class UnmatchedNumber(BaseModel):
    token: str
    normalized: float
    context_snippet: str = Field(max_length=200)

class ValidationReport(BaseModel):
    passed: bool
    matched_count: int
    total_numeric_tokens: int
    unmatched_numbers: list[UnmatchedNumber]
    retries_used: int
    rationale: str
```

### Audit event

```python
from datetime import datetime
from pydantic import BaseModel

class AuditEvent(BaseModel):
    run_id: str
    timestamp: datetime
    event_type: str   # "narrate_start" | "llm_call" | "guardrail_check" | "retry" | "narrate_complete"
    findings_hash: str                # SHA-256
    prompt_hash: str | None
    llm_model: str | None
    llm_latency_ms: int | None
    validation: ValidationReport | None
    output_hash: str | None
```

### Example L3 finding (post-transformer, from TestGen)

```json
{
  "schema_url": "https://hieu-npt.github.io/vsf-l3-schema/v0.1/finding.schema.json",
  "finding_id": "b1d2e3f4a5...64hex",
  "created_at": "2026-05-29T11:00:00Z",
  "scope": {
    "dataset": "sample_sqlite",
    "table": "customers",
    "column": "email",
    "cross_table": false,
    "cross_table_refs": []
  },
  "issue_type": "MISSING_VALUES",
  "detected_by": "testgen.profile_anomaly.missing_pct",
  "dq_dimensions": ["Completeness"],
  "iso_25012_dimension": "Completeness",
  "measurement": {"value": 7.3, "unit": "percent"},
  "constraint": {"threshold": 5.0, "operator": "<=", "passed": false},
  "severity": "WARN",
  "compound_severity": "WARN",
  "confidence": 0.95,
  "ml_impact": ["training_warning"],
  "short_description": "7.3% missing emails in customers (threshold 5%).",
  "long_description": "TestGen profile anomaly detected 7.3% null rate in customers.email across 12,453 rows. Exceeds default threshold 5% by 2.3 percentage points.",
  "source_tool": "datakitchen-testgen-2.4.1",
  "raw_pointer": "testgen://test_results/id/4821"
}
```

### Example narrative output (truncated)

```markdown
# Data Quality Summary — `sample_sqlite` (run 0193a2f1)

## Headline issues
- **`customers.email` 7.3% missing** (finding b1d2e3f4) — exceeds 5% threshold; tier WARN.
- **`orders.amount` outlier rate 2.1%** (finding c8a9b0d1) — INFO, no action.

## Recommended action
…
```

(Mọi số `7.3`, `5`, `2.1` đều trace được tới finding JSON.)

## 6. API / INTERFACE CONTRACTS

### Public Python API

```python
from vsf_l4_demo import narrate, evaluate

# Main entry
def narrate(
    findings: list[Finding],
    *,
    llm_model: str = "claude-opus-4-7",
    cache_dir: str | None = None,
    max_retries: int = 3,
) -> tuple[str, AuditEvent]: ...

def evaluate(
    findings: list[Finding],
    *,
    mode: Literal["baseline", "guarded"] = "guarded",
    judge_model: str = "gpt-4o",
) -> dict: ...
```

### CLI

```bash
# 1. Boot TestGen + scan
vsf-demo testgen-scan --db data/sample.sqlite

# 2. Run end-to-end demo (extract → transform → narrate)
vsf-demo narrate \
  --db data/sample.sqlite \
  --out outputs/report.md \
  [--mode guarded|baseline] \
  [--model claude-opus-4-7] \
  [--max-retries 3]

# 3. Run evaluation suite
vsf-demo eval \
  --suite configs/eval.yaml \
  --out outputs/eval_report.md

# 4. Inspect audit
vsf-demo audit --run-id <id>
```

### Error cases

| Error | Type | Exit code |
|---|---|---|
| TestGen Postgres unreachable | `TestGenUnavailable` | 2 |
| L3 transformer failed validate(M1) | `M1SchemaError` | 3 |
| LLM API timeout sau 3 retry | `LLMTimeoutError` | 4 |
| Guardrail fail sau `max_retries` | `GuardrailExhaustedError` | 5 (output dùng `<UNVERIFIED_NUMBER>` placeholder) |
| Hallucination rate kill criterion fail | `KillCriterionFailed` | 0 (warning) |

## 7. ENVIRONMENT & CONFIG

- **Env vars:**
  - `ANTHROPIC_API_KEY=sk-ant-...` (required cho narrator).
  - `OPENAI_API_KEY=sk-...` (required cho judge eval).
  - `TESTGEN_PG_URL=postgresql://testgen:testgen@localhost:5432/testgen` (Docker compose default).
  - `VSF_L4_CACHE_DIR=./.cache/llm` (LLM response cache).
  - `VSF_L4_MOCK_LLM=1` (CI: dùng cassette thay vì gọi LLM thật).
  - `TESTGEN_MOCK=1` (CI: dùng fixture JSON thay vì Docker).
  - `VSF_L4_LLM_MODEL=claude-opus-4-7` (override default).
- **External services:**
  - **Anthropic Claude API** — narrator chính.
  - **OpenAI GPT-4o** — judge cho eval.
  - **DataKitchen TestGen** Docker image `datakitchen/dataops-testgen:<pinned-tag>`.
  - **Postgres** (sidecar TestGen).
- **Local dev setup steps:**

  ```bash
  git clone <repo>
  cd vsf-l4-demo
  cp .env.example .env    # edit API keys
  python -m venv .venv && source .venv/bin/activate
  pip install -e ".[dev]"

  # Boot infra (TestGen + Postgres):
  docker compose up -d testgen postgres

  # Wait scan + run demo:
  vsf-demo testgen-scan --db data/sample.sqlite
  vsf-demo narrate --db data/sample.sqlite --out outputs/report.md

  # Eval:
  vsf-demo eval --suite configs/eval.yaml --out outputs/eval_report.md

  # Tests (mock mode):
  TESTGEN_MOCK=1 VSF_L4_MOCK_LLM=1 pytest tests/ -v
  ```

## 8. CONSTRAINTS

**Hard technical constraints:**
- Python 3.10+.
- LLM temperature **must = 0** (deterministic; CI gate).
- LLM cost ≤ 5 USD cho full 50-finding eval (cap qua `max_tokens=2000` + prompt-size budget).
- End-to-end demo wall-clock ≤ 60 s cho ≤ 10 findings; ≤ 10 min cho 50-finding eval.
- Sample SQLite ≤ 5 MB (commit-friendly).
- TestGen image tag được **pin** trong `docker-compose.yml` (không `:latest` ở release).
- M1 schema v0.1 là hard dep — không bypass `validate_finding`.
- Guardrail hallucination reduction **≥ 90 %** vs baseline (PROJECT KILL).
- Fluency mean **≥ 4.0/5.0** trên guarded mode (PROJECT KILL).

**Do NOT do list:**
- ❌ Không bao giờ đưa raw data row vào prompt (chỉ L3 findings JSON).
- ❌ Không cho LLM execute code / SQL (PandasAI anti-pattern).
- ❌ Không streaming token output (sync only — guardrail cần full output trước khi check).
- ❌ Không multi-turn dialog với user — single-shot narrate.
- ❌ Không fine-tune custom model — zero training.
- ❌ Không support non-English narrative (chỉ EN).
- ❌ Không UI / dashboard.
- ❌ Không bypass guardrail cho "edge cases" — nếu guardrail block hợp lệ và regen fail, output `<UNVERIFIED_NUMBER>` placeholder.
- ❌ Không log API key trong audit trail.
- ❌ Không gọi LLM > 3 lần / narrate call (cost cap).

## 9. ACCEPTANCE CRITERIA (PROJECT LEVEL)

- [ ] `TESTGEN_MOCK=1 VSF_L4_MOCK_LLM=1 pytest tests/ -v --cov=src/vsf_l4_demo --cov-fail-under=80` xanh trong CI.
- [ ] `docker compose up -d && vsf-demo narrate --db data/sample.sqlite --out outputs/report.md` chạy thành công ≤ 60 s; `outputs/report.md` tồn tại và ≥ 200 chars.
- [ ] `vsf-demo eval --suite configs/eval.yaml --out outputs/eval_report.md` chạy thành công; eval report chứa:
  - Bảng `{metric, baseline_value, guarded_value, threshold, pass}` với:
    - Hallucination rate giảm **≥ 90 %** so với baseline (e.g. baseline 12 % → guarded ≤ 1.2 %) — `pass`.
    - Fluency mean ≥ 4.0 — `pass`.
    - Faithfulness mean ≥ 4.0 — `pass`.
- [ ] Mỗi `Finding` qua transformer pass `vsf_l3_schema.validate_finding`.
- [ ] Replay từ audit + cassette → bit-identical output (verify trong `tests/test_end_to_end_demo.py::test_replay`).
- [ ] Cost LLM thực tế cho full eval ≤ 5 USD — log usage tokens.
- [ ] Token guardrail unit tests (≥ 200 cases) pass rate ≥ 98 %.
- [ ] `ruff check src/ tests/` không warning; `mypy src/` không error.
- [ ] `examples/01_run_demo.sh` chạy thành công trên máy clean (smoke test).
- [ ] Sample `outputs/report.md` được commit vào repo và match output reproducible (CI diff check).
- [ ] CHANGELOG.md có entry v0.1.0 + GIF demo trong README.

## 10. OPEN QUESTIONS

1. **TestGen output extraction method:** TestGen lưu finding ở Postgres internal. Cần verify:
   - Schema bảng `test_results` (column names, types).
   - Quyền đọc trực tiếp có vi phạm Apache-2.0 ToS không (low risk vì OSS, nhưng confirm).
   - Có CLI export JSON public không, hay chỉ SQL query? [BLOCKING — verify tuần 1; nếu chỉ HTML/UI → KILL → upstream feature request].
2. **LLM model lock-in:** `claude-opus-4-7` là default. Có nên test multi-model (Claude vs GPT-4 vs Llama-3) trong eval? [ASSUMED single-model cho Phase 1; multi-model trong Phase 2].
3. **Few-shot examples curation:** 5 examples trong `configs/prompts/few_shot/` được hand-craft. Quality control: mỗi example phải pass guardrail trên chính nó. Có cần ablation few-shot 0 vs 3 vs 5? Khuyến nghị: có, trong eval report Phase 2.
4. **Tolerance design cho guardrail:** Số nguyên tolerance = 0 quá strict (rounding `99.9` → `100` fail). Có nên relax tới "nearest integer match"? [ASSUMED relative 1e-3 cho |allowed| > 1 — verify trên 200-case test suite].
5. **Year/date pass-through:** Output có thể chứa `2026-05-29` (ngày scan). Hiện regex match `\d{4}` → có thể false-positive với percentage `2026 %`. Cần thêm context check (e.g. "có dấu `-` trước hoặc sau" → date). [Cần refine trong tuần 2].
6. **Cost monitoring:** Anthropic API cost tracking chỉ qua response usage field. Có nên implement budget circuit-breaker (stop khi vượt $5)? Khuyến nghị: có, đơn giản.
7. **Replayable cassettes vs live calls trong CI:** `pytest-recording` cassettes có thể stale khi M1 schema bump. Strategy: cassette versioned theo M1 schema version. [ASSUMED cassette tự refresh khi prompt_hash thay đổi].
8. **Sample SQLite content:** 5 tables, ~1 MB. Cần tạo từ public dataset (Northwind? Sakila?) hay tự synth? [ASSUMED synth nhỏ với 5-table normalized + có dirty data đã inject — generator script `data/sample_seed.sql`].
9. **Hallucination rate baseline:** Cần baseline number nào để đo "90% reduction"? Nếu baseline halluc rate ~10 %, guarded ≤ 1 %. Nếu baseline 50 %, guarded ≤ 5 %. Plan: measure baseline trên 5 dataset trước, lock target relative.
10. **Faithfulness judge prompt:** GPT-4 judge có thể bias theo "verbose = faithful". Cần calibrate prompt với 10 manual gold-label cases trước khi auto-eval.
11. **Reproducibility với LLM:** Ngay cả `temperature=0`, Anthropic không guarantee bit-identical (server-side non-determinism). Document caveat trong audit + CI dùng cassette để bypass. [ASSUMED cassette-based CI; live calls chỉ dev/release].
12. **Issue_type new value:** TestGen có nhiều finding type (drift, profile anomaly, hygiene) không khớp 1-1 với M1 enum. Có cần coordinate với M1 để add value, hay map fuzzy ở transformer? [Map fuzzy cho v0.1; track gap để M1 v0.2 expand enum].
