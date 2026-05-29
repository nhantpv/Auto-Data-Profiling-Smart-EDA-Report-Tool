# Deterministic Core — Part 1: Foundation & Ingestion

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build project skeleton, Pydantic data contracts, and smart data ingestion layer.

**Architecture:** Strict Pydantic models define the API contract between Python engines and LLM agents. Ingestion module uses pandas to read CSV/Excel with auto-sampling at 500k rows.

**Tech Stack:** Python 3.13, Pydantic 2.x, Pandas, Pytest.

---

## ⚠️ Pitfalls & Traps (Đọc trước khi code)

1. **Import path trap:** Project uses `src/` layout. Pytest won't find `src.ontology.models` unless `conftest.py` adds `src/` to `sys.path`, OR we use `pyproject.toml` with `[tool.pytest.ini_options] pythonpath = ["src"]`.
2. **Pydantic v2 syntax:** Dùng `model_validate(dict)` thay vì `MyModel(**dict)` khi parse từ JSON. Cả 2 đều hoạt động nhưng `model_validate` là chuẩn v2.
3. **`__init__.py` bắt buộc:** Mỗi thư mục `src/`, `src/ontology/`, `src/ingestion/`, `tests/`, v.v. đều PHẢI có file `__init__.py` trống. Thiếu 1 file = pytest crash.
4. **Pandas `sample()` với seed:** Luôn dùng `random_state=42` để kết quả reproducible khi test.
5. **CSV encoding trap:** File CSV tiếng Việt có thể dùng `utf-8-sig` (có BOM). Code cần try `utf-8` trước, fallback `utf-8-sig`.

---

### Task 1: Project Skeleton & Pytest Configuration

**Files:**
- Create: `pyproject.toml`
- Create: `src/__init__.py`
- Create: `src/ontology/__init__.py`
- Create: `src/ingestion/__init__.py`
- Create: `src/engines/__init__.py`
- Create: `src/severity/__init__.py`
- Create: `src/guardrail/__init__.py`
- Create: `tests/__init__.py`
- Create: `tests/ontology/__init__.py`
- Create: `tests/ingestion/__init__.py`
- Create: `tests/engines/__init__.py`
- Create: `tests/severity/__init__.py`
- Create: `tests/guardrail/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/fixtures/clean_10rows.csv`
- Create: `tests/fixtures/dirty_with_outliers.csv`

- [ ] **Step 1: Create `pyproject.toml`**

```toml
# pyproject.toml
[project]
name = "smart-eda"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "pandas>=2.0",
    "pydantic>=2.0",
    "ydata-profiling>=4.0",
    "pyod>=1.0",
    "pydbml>=1.0",
    "matplotlib>=3.0",
    "seaborn>=0.12",
]

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]

[project.optional-dependencies]
dev = ["pytest>=7.0"]
```

> ⚠️ **Pitfall:** Chúng ta vẫn dùng `ydata-profiling` trong dependencies vì `fg-data-profiling` mới rename và API giống hệt. Khi nào `fg-data-profiling` stable trên PyPI thì đổi 1 dòng. Import trong code vẫn dùng `from ydata_profiling import ProfileReport` cho đến khi migrate.

- [ ] **Step 2: Create all `__init__.py` files (empty)**

Tạo các file rỗng:
```
src/__init__.py
src/ontology/__init__.py
src/ingestion/__init__.py
src/engines/__init__.py
src/severity/__init__.py
src/guardrail/__init__.py
tests/__init__.py
tests/ontology/__init__.py
tests/ingestion/__init__.py
tests/engines/__init__.py
tests/severity/__init__.py
tests/guardrail/__init__.py
```

- [ ] **Step 3: Create test fixtures**

```csv
# tests/fixtures/clean_10rows.csv
id,name,age,salary
1,Alice,25,50000
2,Bob,30,60000
3,Charlie,35,55000
4,Diana,28,52000
5,Eve,32,58000
6,Frank,40,70000
7,Grace,27,51000
8,Hank,33,62000
9,Iris,29,53000
10,Jack,31,59000
```

```csv
# tests/fixtures/dirty_with_outliers.csv
id,name,age,salary
1,Alice,25,50000
2,Bob,30,60000
3,Charlie,35,55000
4,Diana,28,52000
5,Eve,32,58000
6,Frank,40,70000
7,Grace,27,51000
8,Hank,33,62000
9,Iris,29,53000
10,Jack,31,59000
11,Outlier1,150,999999
12,Outlier2,-5,0
13,Alice,25,50000
14,Alice,25,50000
```

> Row 11-12: outliers (tuổi 150, tuổi -5). Row 13-14: exact duplicates of row 1.

- [ ] **Step 4: Create `tests/conftest.py`**

```python
# tests/conftest.py
import pytest
from pathlib import Path

FIXTURES_DIR = Path(__file__).parent / "fixtures"

@pytest.fixture
def clean_csv_path():
    return str(FIXTURES_DIR / "clean_10rows.csv")

@pytest.fixture
def dirty_csv_path():
    return str(FIXTURES_DIR / "dirty_with_outliers.csv")
```

- [ ] **Step 5: Verify pytest discovers correctly**

Run: `pytest --collect-only`
Expected: "no tests ran" (0 items collected) — nhưng KHÔNG có lỗi import.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "chore: initialize project skeleton with pytest config and test fixtures"
```

---

### Task 2: Pydantic Models — DataQualityFindings

**Files:**
- Create: `src/ontology/models.py`
- Create: `tests/ontology/test_models.py`

> ⚠️ **Pitfall:** `ColumnStats` phải xử lý cả cột Numeric (có `n_zeros`) lẫn Categorical (có `n_distinct` nhưng KHÔNG có `n_zeros`). Dùng `Optional` cho các field không phải lúc nào cũng có.

- [ ] **Step 1: Write the failing test**

```python
# tests/ontology/test_models.py
import pytest
from ontology.models import DatasetMeta, ColumnStats, AnomalyRecord, DataQualityFindings


class TestDatasetMeta:
    def test_valid_meta(self):
        meta = DatasetMeta(
            file_name="test.csv",
            n=1000,
            n_var=5,
            memory_size=1024,
            p_cells_missing=0.05,
            n_duplicates=10,
            p_duplicates=0.01,
            overview_charts={"heatmap": "path/to/img.png"},
        )
        assert meta.n == 1000
        assert meta.n_duplicates == 10

    def test_meta_defaults(self):
        """overview_charts and duplicates should default to empty/zero."""
        meta = DatasetMeta(
            file_name="x.csv", n=1, n_var=1, memory_size=0, p_cells_missing=0.0
        )
        assert meta.overview_charts == {}
        assert meta.n_duplicates == 0


class TestColumnStats:
    def test_numeric_column(self):
        col = ColumnStats(
            type="Numeric",
            n_missing=10,
            p_missing=0.1,
            additional_metrics={"mean": 25.5, "std": 3.2},
        )
        assert col.additional_metrics["mean"] == 25.5

    def test_categorical_column(self):
        col = ColumnStats(
            type="Categorical",
            n_missing=0,
            p_missing=0.0,
            n_distinct=5,
            additional_metrics={},
        )
        assert col.n_distinct == 5


class TestAnomalyRecord:
    def test_valid_anomaly(self):
        rec = AnomalyRecord(
            issue_type="OUTLIER_ENSEMBLE",
            description="Found 10 outliers",
            severity="HIGH",
            dq_dimensions=["Accuracy"],
            ml_impact=["training_bias"],
            compound_severity="HIGH",
            confidence=0.92,
            affected_count=10,
            affected_percent=0.01,
            top_10_samples=[{"id": 1, "score": 0.99}],
            diagnostic_chart="path/to/chart.png",
            full_anomalies_export_path="path/to/export.csv",
        )
        assert rec.severity == "HIGH"
        assert rec.dq_dimensions == ["Accuracy"]
        assert rec.compound_severity == "HIGH"
        assert len(rec.top_10_samples) == 1

    def test_anomaly_optional_fields(self):
        """diagnostic_chart and export_path are optional."""
        rec = AnomalyRecord(
            issue_type="DUPLICATE",
            description="Found duplicates",
            severity="MEDIUM",
            affected_count=5,
            affected_percent=0.005,
            top_10_samples=[],
        )
        assert rec.diagnostic_chart is None


class TestDataQualityFindings:
    def test_full_roundtrip(self):
        """Build a full findings object, serialize to JSON, deserialize back."""
        findings = DataQualityFindings(
            dataset_meta=DatasetMeta(
                file_name="test.csv", n=100, n_var=3,
                memory_size=500, p_cells_missing=0.02,
            ),
            columns={
                "age": ColumnStats(
                    type="Numeric", n_missing=2, p_missing=0.02,
                    additional_metrics={"mean": 30},
                ),
            },
            anomalies=[],
        )
        json_str = findings.model_dump_json()
        restored = DataQualityFindings.model_validate_json(json_str)
        assert restored.dataset_meta.file_name == "test.csv"
        assert restored.columns["age"].additional_metrics["mean"] == 30
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ontology/test_models.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ontology'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ontology/models.py
"""Pydantic data contracts for the Smart EDA pipeline.

These models define the strict JSON schema (Layer 3) that bridges
deterministic Python engines (L1/L2/L2.5) and LLM agents (L4).
Includes C1 fields: dq_dimensions, ml_impact, compound_severity, confidence.
"""
from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional


class Severity(str, Enum):
    """Standardized severity levels for all findings."""
    INFO = "INFO"
    WARN = "WARN"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class DatasetMeta(BaseModel):
    """Top-level metadata about the profiled dataset."""
    file_name: str
    n: int                          # total rows
    n_var: int                      # total columns
    memory_size: int                # bytes
    p_cells_missing: float          # 0.0 ~ 1.0
    n_duplicates: int = 0
    p_duplicates: float = 0.0
    overview_charts: Dict[str, str] = Field(default_factory=dict)


class ColumnStats(BaseModel):
    """Per-column statistics from fg-data-profiling (Layer 1)."""
    type: str                       # "Numeric" | "Categorical" | "Boolean" | ...
    n_missing: int
    p_missing: float
    n_distinct: Optional[int] = None
    missingness_mechanism: Optional[str] = None  # "MCAR" | "MAR" | "MNAR" (from C2 module a)
    additional_metrics: Dict[str, Any] = Field(default_factory=dict)


class AnomalyRecord(BaseModel):
    """A single data quality finding (outlier cluster, duplicate batch, etc.)."""
    issue_type: str                 # "OUTLIER_ENSEMBLE" | "DUPLICATE" | ...
    description: str
    severity: Severity              # C1: Enum instead of free string
    dq_dimensions: List[str] = Field(default_factory=list)  # C1: DAMA dimensions
    ml_impact: List[str] = Field(default_factory=list)       # C1: e.g. ["training_bias"]
    compound_severity: Optional[Severity] = None             # C1: from CompoundEscalator (C2d)
    confidence: Optional[float] = None                       # C1: 0.0 ~ 1.0
    affected_count: int             # how many rows affected
    affected_percent: float         # 0.0 ~ 1.0
    top_10_samples: List[Dict[str, Any]]
    diagnostic_chart: Optional[str] = None
    full_anomalies_export_path: Optional[str] = None


class DataQualityFindings(BaseModel):
    """Root model for data_quality_findings.json — sent to Data QA Agent."""
    dataset_meta: DatasetMeta
    columns: Dict[str, ColumnStats]
    anomalies: List[AnomalyRecord] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ontology/test_models.py -v`
Expected: ALL PASS (6 tests)

- [ ] **Step 5: Commit**

```bash
git add src/ontology/models.py tests/ontology/test_models.py
git commit -m "feat: pydantic data contracts for DataQualityFindings"
```

---

### Task 3: Pydantic Models — SchemaEvaluationFindings

**Files:**
- Modify: `src/ontology/models.py` (append new classes)
- Create: `tests/ontology/test_schema_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/ontology/test_schema_models.py
import pytest
from ontology.models import SchemaMeta, TableInfo, IntegrityError, SchemaEvaluationFindings


class TestSchemaEvaluationFindings:
    def test_valid_schema_findings(self):
        findings = SchemaEvaluationFindings(
            schema_meta=SchemaMeta(
                dbml_file="ecommerce.dbml",
                total_tables=3,
                total_relationships=2,
            ),
            tables=[
                TableInfo(name="orders", columns=["id", "user_id", "total"]),
                TableInfo(name="users", columns=["id", "name"]),
            ],
            integrity_errors=[
                IntegrityError(
                    error_type="ORPHAN_FOREIGN_KEY",
                    description="15 orders have invalid user_id",
                    severity="CRITICAL",
                    affected_table="orders",
                    affected_count=15,
                    top_10_samples=[{"order_id": 101, "invalid_user_id": 9999}],
                )
            ],
        )
        assert findings.schema_meta.total_tables == 3
        assert len(findings.integrity_errors) == 1
        assert findings.integrity_errors[0].severity == "CRITICAL"

    def test_empty_errors(self):
        findings = SchemaEvaluationFindings(
            schema_meta=SchemaMeta(
                dbml_file="clean.dbml", total_tables=2, total_relationships=1
            ),
            tables=[TableInfo(name="t1", columns=["id"])],
            integrity_errors=[],
        )
        assert len(findings.integrity_errors) == 0

    def test_roundtrip_json(self):
        findings = SchemaEvaluationFindings(
            schema_meta=SchemaMeta(
                dbml_file="x.dbml", total_tables=1, total_relationships=0
            ),
            tables=[],
            integrity_errors=[],
        )
        json_str = findings.model_dump_json()
        restored = SchemaEvaluationFindings.model_validate_json(json_str)
        assert restored.schema_meta.dbml_file == "x.dbml"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ontology/test_schema_models.py -v`
Expected: FAIL with `ImportError: cannot import name 'SchemaMeta'`

- [ ] **Step 3: Append to `src/ontology/models.py`**

Add these classes at the end of the existing file:

```python
# --- Schema Evaluation Models (for schema_evaluation_findings.json) ---

class SchemaMeta(BaseModel):
    """Metadata about the DBML schema being evaluated."""
    dbml_file: str
    total_tables: int
    total_relationships: int


class TableInfo(BaseModel):
    """Basic info about a table found in the DBML schema."""
    name: str
    columns: List[str]


class IntegrityError(BaseModel):
    """A referential integrity violation found by schema_engine."""
    error_type: str              # "ORPHAN_FOREIGN_KEY" | "TYPE_MISMATCH" | ...
    description: str
    severity: str                # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"
    affected_table: str
    affected_count: int = 0
    top_10_samples: List[Dict[str, Any]] = Field(default_factory=list)


class SchemaEvaluationFindings(BaseModel):
    """Root model for schema_evaluation_findings.json — sent to Architect Agent."""
    schema_meta: SchemaMeta
    tables: List[TableInfo]
    integrity_errors: List[IntegrityError] = Field(default_factory=list)
```

- [ ] **Step 4: Run ALL ontology tests**

Run: `pytest tests/ontology/ -v`
Expected: ALL PASS (9 tests total)

- [ ] **Step 5: Commit**

```bash
git add src/ontology/models.py tests/ontology/test_schema_models.py
git commit -m "feat: pydantic data contracts for SchemaEvaluationFindings"
```

---

### Task 4: CSV Reader with Smart Sampling

**Files:**
- Create: `src/ingestion/csv_reader.py`
- Create: `tests/ingestion/test_csv_reader.py`

> ⚠️ **Pitfall 1:** `pd.read_csv()` mặc định dùng `utf-8`. File CSV tiếng Việt từ Excel có thể là `utf-8-sig` (BOM). Code phải try/except.
> ⚠️ **Pitfall 2:** `df.sample(n=X)` sẽ crash nếu `X > len(df)`. Phải check `len(df) > threshold` trước.
> ⚠️ **Pitfall 3:** Fixture file `dirty_with_outliers.csv` có 14 rows. Test sampling threshold phải < 14.

- [ ] **Step 1: Write the failing test**

```python
# tests/ingestion/test_csv_reader.py
import pytest
import pandas as pd
from ingestion.csv_reader import load_csv


class TestLoadCsv:
    def test_load_clean_csv(self, clean_csv_path):
        df = load_csv(clean_csv_path)
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 10
        assert list(df.columns) == ["id", "name", "age", "salary"]

    def test_load_dirty_csv(self, dirty_csv_path):
        df = load_csv(dirty_csv_path)
        assert len(df) == 14

    def test_sampling_triggers(self, dirty_csv_path):
        """With threshold=10, 14-row file should be sampled down to 10."""
        df = load_csv(dirty_csv_path, sample_threshold=10)
        assert len(df) == 10

    def test_sampling_not_needed(self, clean_csv_path):
        """With threshold=100, 10-row file should NOT be sampled."""
        df = load_csv(clean_csv_path, sample_threshold=100)
        assert len(df) == 10

    def test_file_not_found(self):
        with pytest.raises(FileNotFoundError):
            load_csv("nonexistent.csv")

    def test_sampling_is_reproducible(self, dirty_csv_path):
        """Same seed → same sample every time."""
        df1 = load_csv(dirty_csv_path, sample_threshold=10)
        df2 = load_csv(dirty_csv_path, sample_threshold=10)
        pd.testing.assert_frame_equal(df1, df2)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ingestion/test_csv_reader.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'ingestion'`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ingestion/csv_reader.py
"""CSV data ingestion with smart sampling to prevent OOM.

Usage:
    df = load_csv("data.csv")                    # full load
    df = load_csv("data.csv", sample_threshold=500000)  # auto-sample if > 500k rows
"""
import logging
import pandas as pd
from pathlib import Path

logger = logging.getLogger(__name__)

_ENCODINGS = ["utf-8", "utf-8-sig", "latin-1"]


def load_csv(
    file_path: str,
    sample_threshold: int = 500_000,
    random_seed: int = 42,
) -> pd.DataFrame:
    """Load a CSV file into a DataFrame, sampling if too large.

    Args:
        file_path: Path to the CSV file.
        sample_threshold: Max rows before sampling kicks in.
        random_seed: Seed for reproducible sampling.

    Returns:
        A pandas DataFrame.

    Raises:
        FileNotFoundError: If file_path does not exist.
        ValueError: If file cannot be parsed with any supported encoding.
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    # Try multiple encodings (Vietnamese CSV from Excel may use utf-8-sig)
    df = None
    for enc in _ENCODINGS:
        try:
            df = pd.read_csv(path, encoding=enc)
            break
        except UnicodeDecodeError:
            continue

    if df is None:
        raise ValueError(
            f"Cannot read {file_path} with encodings {_ENCODINGS}"
        )

    # Smart sampling
    if len(df) > sample_threshold:
        logger.info(
            "Dataset has %d rows (> %d threshold). Sampling down to %d rows.",
            len(df), sample_threshold, sample_threshold,
        )
        df = df.sample(n=sample_threshold, random_state=random_seed)
        df = df.reset_index(drop=True)

    return df
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ingestion/test_csv_reader.py -v`
Expected: ALL PASS (6 tests)

- [ ] **Step 5: Run ALL tests to confirm nothing broke**

Run: `pytest tests/ -v`
Expected: ALL PASS (15 tests total)

- [ ] **Step 6: Commit**

```bash
git add src/ingestion/csv_reader.py tests/ingestion/test_csv_reader.py
git commit -m "feat: CSV reader with smart sampling and encoding fallback"
```
