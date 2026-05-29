# AI SPEC — M1: L3 Ontology as Published Schema + 3 Reference Adapters

## 1. PROJECT OVERVIEW

- **Project name:** `vsf-l3-schema`
- **One-line description:** Versioned JSON Schema + Pydantic model cho Layer-3 findings của pipeline EDA/DQ, kèm 3 adapter tham chiếu (DataKitchen TestGen, Great Expectations, Facebook Kats).
- **Problem being solved:** Mỗi công cụ DQ/anomaly OSS phát ra finding theo cấu trúc riêng, khiến downstream layer (LLM narrator, BI, lineage) không liên thông được. Dự án cần một schema chuẩn để L4 narrator đọc đầu ra từ nhiều engine khác nhau mà không cần code tool-specific.
- **Core value proposition:** "Build once, narrate anywhere" — chuẩn finding L3 mở cho mọi engine DQ; là tiền điều kiện kỹ thuật cho M2 (benchmark) và M3 (interpreter-only L4 demo).

## 2. TECH STACK

- **Language:** Python 3.10+ (locked: `>=3.10,<3.13`).
- **Runtime:** CPython; không cần GPU; chạy local hoặc CI Linux/macOS.
- **Key libraries (locked):**
  - `pydantic==2.7.*` — model definition + JSON serialization.
  - `jsonschema==4.22.*` — schema validation runtime.
  - `openml==0.14.*` [ASSUMED] — chỉ cần ở test cho TestGen adapter (sample DB fetch).
  - `great-expectations==0.18.*` — adapter source format.
  - `kats==0.2.*` [ASSUMED, verify khả dụng PyPI; fallback `pip install git+https://github.com/facebookresearch/Kats`] — adapter source format.
  - `pytest==8.*`, `pytest-cov==5.*` — test runner.
  - `ruff==0.5.*`, `mypy==1.10.*` — lint + type check.
  - `hatchling==1.25.*` — build backend.
- **DataKitchen TestGen** truy cập qua Docker (image `datakitchen/dataops-testgen:latest`), không phải PyPI dep.
- **Deployment target:** PyPI package `vsf-l3-schema` (private cho M1 tuần 1-3); JSON Schema host trên GitHub Pages tại URL ổn định `https://hieu-npt.github.io/vsf-l3-schema/v0.1/finding.schema.json` [ASSUMED — chốt host sau].

## 3. ARCHITECTURE

- **High-level structure:** Monolith Python package — schema-first, không service.
- **Directory layout (full file tree):**

```
vsf-l3-schema/
├── pyproject.toml
├── README.md
├── LICENSE                          # Apache-2.0
├── .gitignore
├── .github/
│   └── workflows/
│       └── ci.yml                   # pytest + ruff + mypy + schema-publish
├── schemas/
│   ├── v0.1/
│   │   └── finding.schema.json     # JSON Schema Draft 2020-12, ~80 lines
│   └── CHANGELOG.md
├── src/
│   └── vsf_l3_schema/
│       ├── __init__.py             # exposes __version__, Finding, validate_finding
│       ├── _version.py              # __version__ = "0.1.0"
│       ├── models.py                # Pydantic Finding, Scope, Measurement, Constraint enums
│       ├── validator.py             # jsonschema-backed validate_finding(d: dict) -> None
│       ├── enums.py                 # DqDimension, Severity, MlImpact, IssueType enum
│       └── adapters/
│           ├── __init__.py
│           ├── testgen.py           # TestGenAdapter
│           ├── great_expectations.py# GreatExpectationsAdapter
│           └── kats.py              # KatsAdapter
├── tests/
│   ├── conftest.py                  # fixtures: sample raw outputs từ 3 tool
│   ├── fixtures/
│   │   ├── testgen/                 # 30 raw JSON findings extracted từ TestGen
│   │   ├── ge/                      # 30 ExpectationSuiteValidationResult
│   │   └── kats/                    # 30 anomaly outputs từ Kats
│   ├── test_schema_self_validates.py
│   ├── test_models_roundtrip.py
│   ├── test_adapter_testgen.py
│   ├── test_adapter_great_expectations.py
│   ├── test_adapter_kats.py
│   └── test_cross_tool_consistency.py  # field-presence consistency ≥ 80%
└── examples/
    ├── 01_minimal_finding.py
    ├── 02_adapter_demo.py
    └── 03_publish_schema_url.md
```

- **Data flow description:**

```
[L1/L2 engine output: TestGen JSON | GE ExpectationSuiteValidationResult | Kats anomaly dict]
                              │
                              ▼
              [vsf_l3_schema.adapters.<tool>.to_l3()]
                              │
                              ▼
              [Pydantic Finding(...) — typed, validated]
                              │
                ┌─────────────┴──────────────┐
                ▼                            ▼
       [finding.model_dump_json()]   [validate_finding(dict)]
                │                            │
                ▼                            ▼
         {finding JSON}              raises ValidationError | None
                │
                ▼
        [downstream: M2 component, M3 narrator, audit log]
```

## 4. FEATURES

### Feature: JSON Schema v0.1

- **Description:** File `schemas/v0.1/finding.schema.json` (Draft 2020-12), URL-addressable, host trên GitHub Pages. Định nghĩa shape của 1 finding L3.
- **Input:** không có — đây là artifact static.
- **Output:** file JSON Schema ~80 dòng có `$id`, `$schema`, `title`, `type: object`, đầy đủ trường (xem §5).
- **Acceptance:**
  - `jsonschema.Draft202012Validator.check_schema(schema)` không raise.
  - Schema phải khai báo `additionalProperties: false` ở root.
  - Sample fixture mỗi adapter (≥ 30) round-trip 100 % qua `validate(instance, schema)`.
- **Out of scope:** Không định nghĩa cho streaming-native event, cross-table DBML flag (đẩy v0.2).

### Feature: Pydantic `Finding` model

- **Description:** Python class trong `src/vsf_l3_schema/models.py` mirror schema, hỗ trợ tạo finding programmatic + validate.
- **Input:** Python dict hoặc keyword args.
- **Output:** instance `Finding`; `.model_dump()` → dict; `.model_dump_json()` → JSON str.
- **Acceptance:**
  - Round-trip `Finding.model_validate(Finding(...).model_dump())` == identity trên 30 fixture/adapter.
  - `Finding.model_json_schema()` tương đương `schemas/v0.1/finding.schema.json` (kiểm `pytest -k test_schema_match`).
- **Out of scope:** Không tự generate `finding_id` content-addressed hash trong M1 — yêu cầu caller cung cấp (Pydantic validator chỉ check format SHA-256).

### Feature: `TestGenAdapter.to_l3(raw: dict) -> Finding`

- **Description:** Map TestGen output (extracted từ TestGen Postgres DB hoặc CSV export) sang `Finding`.
- **Input:** dict raw từ TestGen `test_results` row (schema TestGen-internal; verify trong tuần 1).
- **Output:** `Finding` instance valid.
- **Acceptance:**
  - 30 fixture trong `tests/fixtures/testgen/` đều convert thành `Finding` valid.
  - Field mapping coverage: `dq_dimensions` lấy từ TestGen DAMA category column; `severity` map từ TestGen `severity` cột; `measurement.value` lấy từ `result_score` cột.
  - Nếu raw thiếu field bắt buộc → raise `AdapterError` với message rõ field nào thiếu.
- **Out of scope:** Không poll TestGen DB live; caller phải pre-extract.

### Feature: `GreatExpectationsAdapter.to_l3(raw: dict) -> Finding`

- **Description:** Map GE `ExpectationSuiteValidationResult` element (1 expectation result) sang `Finding`.
- **Input:** dict GE result với keys `expectation_config`, `result`, `success`, `meta`.
- **Output:** `Finding` instance valid.
- **Acceptance:**
  - 30 fixture trong `tests/fixtures/ge/` đều convert valid.
  - GE-specific mapping: `expectation_config.expectation_type` → `issue_type` enum (table lookup); `result.observed_value` → `measurement.value`; `success` → `constraint.passed`.
  - `dq_dimensions` infer từ expectation_type table (ví dụ `expect_column_values_to_not_be_null` → `[Completeness]`).
- **Out of scope:** Không hỗ trợ custom expectation; chỉ GE core expectations.

### Feature: `KatsAdapter.to_l3(raw: dict, *, context: dict) -> Finding`

- **Description:** Map Kats anomaly detector output (e.g., `CUSUMDetector`, `BOCPDDetector`) sang `Finding`.
- **Input:** dict với `detected_time_window`, `anomaly_score`, `detector_name`; `context` chứa `column_name`, `dataset_name`.
- **Output:** `Finding` instance valid.
- **Acceptance:**
  - 30 fixture trong `tests/fixtures/kats/` đều convert valid.
  - Kats mapping: `anomaly_score` → `measurement.value`; `detector_name` → `detected_by`; `dq_dimensions` = `[Timeliness]` default.
  - Test xác nhận `scope.column` populated từ `context["column_name"]`.
- **Out of scope:** Không cover Kats forecasting output (chỉ anomaly).

### Feature: Cross-tool consistency test

- **Description:** Test suite `tests/test_cross_tool_consistency.py` đo field-presence consistency.
- **Input:** 30+30+30 = 90 finding sau khi đi qua 3 adapter.
- **Output:** report metric.
- **Acceptance:**
  - ≥ 80 % field-presence consistency: với mỗi field optional, % adapter có ≥ 1 finding populate phải ≥ 80 % (kill criterion).
  - Schema phải pass mà không cần > 3 conditional/`if-then-else` branches (kill criterion).
- **Out of scope:** Không đo semantic equivalence, chỉ presence.

## 5. DATA MODELS

### Core entity: `Finding`

Pydantic v2 model + enum:

```python
from __future__ import annotations
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict


SCHEMA_URL = "https://hieu-npt.github.io/vsf-l3-schema/v0.1/finding.schema.json"


class DqDimension(str, Enum):
    completeness = "Completeness"
    consistency = "Consistency"
    integrity = "Integrity"
    timeliness = "Timeliness"
    validity = "Validity"
    uniqueness = "Uniqueness"


class Severity(str, Enum):
    info = "INFO"
    warn = "WARN"
    error = "ERROR"
    critical = "CRITICAL"


class MlImpact(str, Enum):
    training_blocker = "training_blocker"
    training_warning = "training_warning"
    leakage_risk = "leakage_risk"
    distribution_shift = "distribution_shift"
    no_impact = "no_impact"


class IssueType(str, Enum):
    MISSING_VALUES = "MISSING_VALUES"
    MISSING_MECHANISM = "MISSING_MECHANISM"
    DUPLICATE_ROWS = "DUPLICATE_ROWS"
    SCHEMA_DRIFT = "SCHEMA_DRIFT"
    INTEGRITY_FK_VIOLATION = "INTEGRITY_FK_VIOLATION"
    DISTRIBUTION_DRIFT = "DISTRIBUTION_DRIFT"
    OUTLIER = "OUTLIER"
    LABEL_NOISE = "LABEL_NOISE"
    CLASS_IMBALANCE = "CLASS_IMBALANCE"
    LEAKAGE = "LEAKAGE"
    TIMESTAMP_ANOMALY = "TIMESTAMP_ANOMALY"
    SEMANTIC_TYPE_MISMATCH = "SEMANTIC_TYPE_MISMATCH"


class Scope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset: str
    table: str | None = None
    column: str | None = None
    cross_table: bool = False
    cross_table_refs: list[str] = Field(default_factory=list)


class Measurement(BaseModel):
    model_config = ConfigDict(extra="forbid")
    value: float | int | str
    unit: str | None = None       # e.g. "percent", "count", "ratio"


class Constraint(BaseModel):
    model_config = ConfigDict(extra="forbid")
    threshold: float | int | str | None = None
    operator: str | None = None    # e.g. "<=", ">", "=="
    passed: bool


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)
    schema_url: str = SCHEMA_URL
    finding_id: str = Field(pattern=r"^[a-f0-9]{64}$")   # SHA-256 hex
    created_at: datetime
    scope: Scope
    issue_type: IssueType
    detected_by: str                                      # algorithm name
    dq_dimensions: list[DqDimension] = Field(min_length=1)
    iso_25012_dimension: str | None = None
    measurement: Measurement
    constraint: Constraint | None = None
    severity: Severity
    compound_severity: Severity | None = None
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    ml_impact: list[MlImpact] = Field(default_factory=list)
    short_description: str = Field(max_length=140)
    long_description: str = Field(max_length=2000)
    source_tool: str                                      # e.g. "testgen-2.4.1"
    raw_pointer: str | None = None                        # opaque ref back to raw output
```

**Relationships & constraints:**
- `finding_id` = SHA-256 hex của `f"{scope.dataset}|{scope.table}|{scope.column}|{issue_type}|{measurement.value}|{created_at.isoformat()}"` (caller phải tính trước; validator chỉ check format).
- `compound_severity ≥ severity` (Pydantic field validator).
- `dq_dimensions` ít nhất 1 phần tử; `ml_impact` có thể rỗng nếu không xác định.

**Example record:**

```json
{
  "schema_url": "https://hieu-npt.github.io/vsf-l3-schema/v0.1/finding.schema.json",
  "finding_id": "a3f9c1d2e4b5...64hex",
  "created_at": "2026-05-29T10:15:30Z",
  "scope": {
    "dataset": "openml_cc18_3_kr_vs_kp",
    "table": "main",
    "column": "feature_07",
    "cross_table": false,
    "cross_table_refs": []
  },
  "issue_type": "MISSING_VALUES",
  "detected_by": "ge.expect_column_values_to_not_be_null",
  "dq_dimensions": ["Completeness"],
  "iso_25012_dimension": "Completeness",
  "measurement": {"value": 12.4, "unit": "percent"},
  "constraint": {"threshold": 5.0, "operator": "<=", "passed": false},
  "severity": "ERROR",
  "compound_severity": "ERROR",
  "confidence": 0.99,
  "ml_impact": ["training_warning"],
  "short_description": "12.4% missing in feature_07 exceeds 5% threshold.",
  "long_description": "Column feature_07 has 12.4% null values across 3196 rows. GE expectation 'expect_column_values_to_not_be_null' failed with threshold 5%.",
  "source_tool": "great_expectations-0.18.12",
  "raw_pointer": "ge://suite/kr_vs_kp/expectation/3"
}
```

## 6. API / INTERFACE CONTRACTS

### Python public API

```python
# vsf_l3_schema/__init__.py
__version__: str = "0.1.0"

from .models import Finding, Scope, Measurement, Constraint
from .enums import DqDimension, Severity, MlImpact, IssueType
from .validator import validate_finding, ValidationError

# validator.py
def validate_finding(payload: dict) -> None:
    """Raises jsonschema.ValidationError if payload doesn't match v0.1 schema."""

# adapters/testgen.py
class TestGenAdapter:
    @staticmethod
    def to_l3(raw: dict, *, dataset_name: str) -> Finding: ...

# adapters/great_expectations.py
class GreatExpectationsAdapter:
    @staticmethod
    def to_l3(raw: dict, *, dataset_name: str) -> Finding: ...

# adapters/kats.py
class KatsAdapter:
    @staticmethod
    def to_l3(raw: dict, *, dataset_name: str, column_name: str) -> Finding: ...
```

### CLI (optional, tuần 3 nếu kịp)

```bash
vsf-l3-schema validate <path-to-finding.json>
# exit 0 if valid; exit 1 + JSON error report if invalid.
```

### Error cases

| Error | Cause | Type | Exit code |
|---|---|---|---|
| `ValidationError` | finding không match schema v0.1 | `jsonschema.ValidationError` | 1 |
| `AdapterError` | raw input thiếu field bắt buộc cho adapter | `vsf_l3_schema.adapters.AdapterError` | 2 |
| `VersionMismatchError` | `schema_url` trong finding khác `SCHEMA_URL` constant | `vsf_l3_schema.VersionMismatchError` | 3 |

## 7. ENVIRONMENT & CONFIG

- **Env vars:**
  - `VSF_L3_SCHEMA_URL` (optional, default = constant trong code) — override URL schema để chạy offline / staging.
  - `TESTGEN_DB_URL=postgresql://testgen:testgen@localhost:5432/testgen` (chỉ test integration, không cần ở runtime).
- **External services:**
  - **TestGen** chạy qua Docker compose tại `tests/docker-compose.yml`. Image `datakitchen/dataops-testgen:latest`. Cần Docker desktop 4.x+.
  - **GitHub Pages** host schema URL (static; setup 1 lần).
- **Local dev setup steps:**

  ```bash
  git clone <repo>
  cd vsf-l3-schema
  python -m venv .venv && source .venv/bin/activate
  pip install -e ".[dev]"
  pre-commit install     # nếu dùng
  pytest tests/ -v
  # Integration test với TestGen (optional):
  docker compose -f tests/docker-compose.yml up -d
  pytest tests/ -v -m integration
  ```

## 8. CONSTRAINTS

**Hard technical constraints:**
- Python 3.10+ (sử dụng `match-case` và `X | None` syntax).
- JSON Schema **Draft 2020-12** (không 2019-09; jsonschema 4.22+).
- Schema file ≤ 200 dòng (target ~80; max 200 trước khi refactor).
- `additionalProperties: false` ở root + mọi nested object.
- Cross-tool consistency ≥ 80 % field presence (kill nếu < 80 %).
- ≤ 3 conditional/`oneOf`/`if-then-else` branches trong schema (kill nếu > 3).
- Schema response time `validate()` < 5 ms / finding trên CPU laptop standard.

**Do NOT do list:**
- ❌ Không thêm trường mới khi không có ≥ 2 trong 3 adapter cần đến (tránh schema bloat).
- ❌ Không hỗ trợ streaming-event fields (e.g. watermark, event_time) — đẩy v0.2.
- ❌ Không tự tính `finding_id` trong validator (caller responsibility).
- ❌ Không phụ thuộc package nặng (pandas, numpy) trong core; chỉ phép trong adapters layer.
- ❌ Không support backward-incompat changes mà không bump major version.
- ❌ Không sinh schema từ Pydantic ở runtime (schema file là source of truth; Pydantic regenerate offline).

## 9. ACCEPTANCE CRITERIA (PROJECT LEVEL)

- [ ] `pytest tests/ -v` xanh 100 %, coverage ≥ 90 % cho `src/vsf_l3_schema/`.
- [ ] `python -c "import jsonschema; import json; jsonschema.Draft202012Validator.check_schema(json.load(open('schemas/v0.1/finding.schema.json')))"` chạy thành công.
- [ ] 30 finding fixture cho mỗi adapter (TestGen, GE, Kats) round-trip valid: `python tests/run_roundtrip.py --tool all` exit 0.
- [ ] `pytest tests/test_cross_tool_consistency.py -v` xanh với field-presence consistency ≥ 80 %.
- [ ] Schema được publish tại URL `https://hieu-npt.github.io/vsf-l3-schema/v0.1/finding.schema.json` và `curl -fsSL <URL>` trả về 200.
- [ ] `pip install vsf-l3-schema==0.1.0` trong môi trường mới import được `Finding`, `validate_finding`, 3 adapter class.
- [ ] `ruff check src/ tests/` không warning; `mypy src/` không error.
- [ ] CHANGELOG.md có entry v0.1.0 với date.
- [ ] CI workflow `.github/workflows/ci.yml` chạy `pytest + ruff + mypy` xanh trên push.

## 10. OPEN QUESTIONS

1. **Schema host URL:** Dùng GitHub Pages (`hieu-npt.github.io/...`) hay domain riêng (`vsf-l3-schema.org`)? [ASSUMED GitHub Pages cho M1; cần xác nhận từ user].
2. **Kats license/maintenance:** Kats có vẻ chậm cập nhật (last commit ?). Nếu dead, fallback dùng `prophet` hoặc `darts`? Cần check `pip install kats` còn work.
3. **TestGen output access:** TestGen lưu finding ở Postgres internal. Có programmatic API hay phải SQL query trực tiếp? Cần xác nhận trong tuần 1 — nếu không có API, adapter input sẽ là SQL-extracted JSON.
4. **Finding ID hashing:** Spec mong caller pre-compute SHA-256. Có nên cung cấp helper `compute_finding_id(scope, issue_type, measurement, created_at)` trong package? (Khuyến nghị có — giảm friction).
5. **`raw_pointer` semantics:** Là URL, opaque string, hay JSON pointer? [ASSUMED opaque string cho M1; có thể chuẩn hoá v0.2].
6. **Multi-language support:** `short_description` / `long_description` có cần i18n field? [ASSUMED không cho v0.1, English only].
7. **Versioning policy khi M2/M3 phát sinh field mới:** Bump patch (v0.1.1) hay minor (v0.2.0)? Khuyến nghị: minor cho thêm field optional, major cho breaking.
8. **PyPI publishing:** Có push lên PyPI public ngay ở v0.1 không, hay giữ private GitHub release? [ASSUMED private đến hết Phase 1 PRD].
