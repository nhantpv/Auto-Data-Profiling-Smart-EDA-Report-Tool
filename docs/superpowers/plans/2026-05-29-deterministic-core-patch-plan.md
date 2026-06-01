# Deterministic Core — Patch Set & Plan (vá Part 1 + Part 2)

> **Cho Thợ thi công:** Đây là bản vá + plan bổ sung cho `2026-05-29-deterministic-core-part1.md`
> và `part2.md`. Áp dụng theo đúng thứ tự TIP ở cuối. Mỗi patch là **thay thế chính xác** (full
> replacement) hoặc **thêm mới**, không "cải thiện" code lân cận. Mọi acceptance criteria phải pass
> trước khi commit.

## 0. Các quyết định đã chốt (recap)

- **Severity (trục A — mức độ 1 finding):** enum `INFO / WARN / HIGH / CRITICAL`. Thứ tự tăng dần.
  Dùng chung cho **mọi** finding (`AnomalyRecord`, `IntegrityError`), `compound_severity`, và các
  bucket trong `summary`. **Không** có `LOW / MEDIUM / ERROR`.
- **Verdict (trục B — phán quyết toàn dataset):** enum `READY / WARN / NOT_READY`. Là **field khác**
  trục A, chỉ tình cờ trùng chữ `WARN`. Không trộn hai trục.
- **Diagnostic chart:** vẽ bằng **matplotlib (Python deterministic)**, KHÔNG để LLM ra lệnh vẽ.
  → `diagnostic_chart` được điền ở **L3.5 (visualizer)**, ngay sau L3, **trước** khi gọi LLM.
- **Ingestion:** theo **Plugin Architecture** (nguyên tắc kiến trúc số 1), MVP phải đọc **CSV +
  Excel + Parquet**.

---

## Patch 1 — `src/ontology/models.py` (vá Part 1, Task 2 & 3)

Bốn thay đổi, đều bám theo quyết định đã chốt. `Severity` enum **giữ nguyên** (đã đúng INFO/WARN/HIGH/CRITICAL).

### 1a. Thêm thứ tự severity (single source of truth cho CompoundEscalator ở Part 3)

Thêm **ngay dưới** `class Severity`:

```python
# Thứ tự tăng dần của severity tier. compound.py (Part 3) dùng đúng tuple này
# để thực thi rule "max(tier) + 1 bậc / lỗi co-occurring, cap CRITICAL".
SEVERITY_ORDER: tuple[Severity, ...] = (
    Severity.INFO, Severity.WARN, Severity.HIGH, Severity.CRITICAL,
)
```

> **Vì sao:** rule compound (`max + 1 bậc`) chỉ chạy được nếu tier có thứ tự xác định. Đặt thứ tự ở
> đây = một nguồn duy nhất, tránh Part 3 tự suy lại lệch.

### 1b. `ColumnStats` — re-add `n_zeros`

Đúng theo pitfall của chính Part 1 ("Numeric có `n_zeros`, Categorical thì không"). Thay thế class:

```python
class ColumnStats(BaseModel):
    """Per-column statistics from fg-data-profiling (Layer 1)."""
    type: str
    n_missing: int
    p_missing: float
    n_zeros: Optional[int] = None                 # <-- re-add: numeric mới có, categorical = None
    n_distinct: Optional[int] = None
    missingness_mechanism: Optional[str] = None
    additional_metrics: Dict[str, Any] = Field(default_factory=dict)
```

### 1c. `IntegrityError` — dùng chung `Severity` + bổ sung C1 fields (parity với AnomalyRecord)

Theo Quyết định 2 ("**mọi lỗi** đều gán DAMA + ml_impact + compound_severity"). Thay thế class:

```python
class IntegrityError(BaseModel):
    """A referential / schema integrity violation found by schema_engine."""
    error_type: str                                # "ORPHAN_FOREIGN_KEY" | "TYPE_MISMATCH" | ...
    description: str
    severity: Severity                             # <-- đổi từ `str`; dùng chung enum trục A
    affected_table: str
    affected_count: int = 0
    dq_dimensions: List[str] = Field(default_factory=list)   # C1 (parity)
    ml_impact: List[str] = Field(default_factory=list)        # C1
    compound_severity: Optional[Severity] = None              # C1 (điền ở Part 3)
    confidence: Optional[float] = None                        # C1
    top_10_samples: List[Dict[str, Any]] = Field(default_factory=list)
```

> Test cũ `test_valid_schema_findings` truyền `severity="CRITICAL"` (string) vẫn pass — Pydantic v2
> tự coerce string → `Severity.CRITICAL`. Không vỡ test hiện có.
>
> **Đã cân nhắc & cố tình KHÔNG làm:** gộp 4 field C1 vào một `BaseFinding` chung cho cả
> `AnomalyRecord` lẫn `IntegrityError`. Sẽ phải sửa `AnomalyRecord` (đã viết & test) → vi phạm
> nguyên tắc surgical. Để lại như một cleanup tùy chọn về sau.

### 1d. Thêm `Verdict` + `DatasetVerdict` (file JSON thứ 3, hiện chưa có model)

Thêm vào cuối file:

```python
class Verdict(str, Enum):
    """Trục B — phán quyết go/no-go toàn dataset (KHÁC severity tier)."""
    READY = "READY"
    WARN = "WARN"
    NOT_READY = "NOT_READY"


class VerdictSummary(BaseModel):
    """Histogram đếm finding theo từng severity tier (đúng trục A)."""
    total_issues: int = 0
    critical: int = 0
    high: int = 0
    warn: int = 0          # <-- thay 'medium' của schema-design draft bằng đúng tier
    info: int = 0


class DatasetVerdict(BaseModel):
    """Root model cho dataset_verdict.json — output từ severity/aggregator.py (Part 3)."""
    dataset_meta: DatasetMeta
    verdict: Verdict
    verdict_rationale: str
    summary: VerdictSummary
```

### 1e. Bổ sung test (thêm vào `tests/ontology/test_models.py`)

```python
from ontology.models import (
    Severity, SEVERITY_ORDER, Verdict, VerdictSummary, DatasetVerdict, DatasetMeta,
)

class TestSeverityOrder:
    def test_order_is_ascending(self):
        assert SEVERITY_ORDER == (Severity.INFO, Severity.WARN, Severity.HIGH, Severity.CRITICAL)

class TestDatasetVerdict:
    def test_roundtrip(self):
        dv = DatasetVerdict(
            dataset_meta=DatasetMeta(file_name="x.csv", n=10, n_var=2,
                                     memory_size=1, p_cells_missing=0.0),
            verdict=Verdict.WARN,
            verdict_rationale="1 CRITICAL orphan FK",
            summary=VerdictSummary(total_issues=3, critical=1, high=1, warn=1),
        )
        restored = DatasetVerdict.model_validate_json(dv.model_dump_json())
        assert restored.verdict == Verdict.WARN
        assert restored.summary.critical == 1

class TestColumnZeros:
    def test_n_zeros_optional(self):
        from ontology.models import ColumnStats
        assert ColumnStats(type="Categorical", n_missing=0, p_missing=0.0).n_zeros is None
        assert ColumnStats(type="Numeric", n_missing=0, p_missing=0.0, n_zeros=5).n_zeros == 5
```

**AC Patch 1:** `pytest tests/ontology/ -v` → all pass (các test cũ + 3 test mới).

---

## Patch 2 — `src/ontology/findings_builder.py` (vá Part 2, Task 7)

### 2a. Sửa `NameError` — thêm `Severity` vào import

```python
from ontology.models import (
    DatasetMeta, ColumnStats, AnomalyRecord, DataQualityFindings, Severity,   # <-- thêm Severity
)
```

> Không có dòng này, `Severity.HIGH` / `Severity.WARN` trong thân hàm crash ngay → Task 7 & Task 8
> **không thể pass** dù plan gốc ghi "ALL PASS". Đây là điều kiện tiên quyết.

### 2b. Điền `n_zeros` trong `_extract_column_stats`

Trong vòng lặp, thêm trước khi tạo `ColumnStats(...)`:

```python
        n_zeros = col_data.get("n_zeros", None)   # ydata cung cấp cho numeric; categorical = None
```

và truyền vào constructor:

```python
        columns[col_name] = ColumnStats(
            type=simple_type,
            n_missing=int(n_missing),
            p_missing=float(p_missing),
            n_zeros=int(n_zeros) if n_zeros is not None else None,   # <-- thêm
            n_distinct=int(n_distinct) if n_distinct is not None else None,
            additional_metrics=extra,
        )
```

**AC Patch 2:** `pytest tests/ontology/test_findings_builder.py tests/test_integration.py -v` → all pass.

---

## Patch 3 — `src/engines/anomaly_engine.py` (vá Part 2, Task 6) — sửa "bịa outlier trên data sạch"

**Gốc rễ (digestion):** code hiện dùng **min-max** normalize. Min-max LUÔN map điểm cao nhất → 1.0,
kể cả data sạch — nên cổng tuyệt đối trên min-max là vô nghĩa. Pitfall #7 của chính Part 2 đã yêu cầu
dùng **z-score (standardizer)**; phần code lại làm min-max → mâu thuẫn nội bộ. Patch này đưa code về
đúng pitfall #7 và thêm **cổng z tuyệt đối**: data sạch (mọi điểm gần trung bình) → không điểm nào
vượt cổng → 0 outlier (đúng intent).

### 3a. Thay `_normalize_scores` bằng `_zscore`

```python
def _zscore(scores: np.ndarray) -> np.ndarray:
    """Standardize to z-scores. Constant input → zeros (tránh chia 0)."""
    std = scores.std()
    if std == 0:
        return np.zeros_like(scores, dtype=float)
    return (scores - scores.mean()) / std
```

### 3b. Thay block tính điểm + threshold (từ chỗ chạy 3 detector tới hết hàm)

```python
    n_samples = len(X)
    lof_neighbors = min(20, n_samples - 1)

    models = [
        ("IForest", IForest(contamination=contamination, random_state=42)),
        ("ECOD", ECOD(contamination=contamination)),
        ("LOF", LOF(n_neighbors=lof_neighbors, contamination=contamination)),
    ]

    # Thu raw decision_scores_ (cao = bất thường hơn — quy ước PyOD)
    raw_scores = []
    for name, model in models:
        try:
            model.fit(X)
            raw_scores.append(model.decision_scores_)
        except Exception as e:
            logger.warning("%s failed: %s. Skipping this detector.", name, e)

    if len(raw_scores) == 0:
        return {
            "outlier_indices": [], "anomaly_scores": [], "all_scores": [],
            "n_outliers": 0, "numeric_columns_used": list(non_constant.columns),
            "skipped": True,
        }

    # Maximization combiner: robust to LOF sign-inversion on small n
    # Lý do dùng max: LOF đảo dấu trên n nhỏ → np.mean mất signal; Maximization robust hơn.
    ensemble_z = np.max([_zscore(s) for s in raw_scores], axis=0)

    # QUYẾT ĐỊNH outlier = cổng z tuyệt đối (KHÔNG dùng percentile → data sạch không bị bịa).
    # z_gate là parameter (default _DEFAULT_Z_GATE=4.0 production; test inject 1.5).
    outlier_mask = ensemble_z >= z_gate

    # Điểm hiển thị [0,1] cho chart/JSON (logistic squash; chỉ để hiển thị, không quyết định)
    display = 1.0 / (1.0 + np.exp(-ensemble_z))

    outlier_positions = np.where(outlier_mask)[0]
    outlier_original_indices = [clean_indices[i] for i in outlier_positions]
    outlier_scores = [round(float(display[i]), 4) for i in outlier_positions]

    sorted_pairs = sorted(zip(outlier_original_indices, outlier_scores), key=lambda x: -x[1])
    sorted_indices = [p[0] for p in sorted_pairs]
    sorted_scores = [p[1] for p in sorted_pairs]

    return {
        "outlier_indices": sorted_indices,
        "anomaly_scores": sorted_scores,
        "all_scores": [round(float(s), 4) for s in display],   # [0,1] cho mọi dòng
        "n_outliers": len(sorted_indices),
        "numeric_columns_used": list(non_constant.columns),
        "skipped": False,
    }
```

Và thêm hằng số + parameter cạnh `_CONTAMINATION`:

```python
_DEFAULT_Z_GATE = 4.0  # production ~4σ; calibrate on real data

def run_anomaly_detection(
    df: pd.DataFrame,
    contamination: float = _CONTAMINATION,
    z_gate: float = _DEFAULT_Z_GATE,
) -> dict:
```

> **Ghi chú trung thực (CLAUDE.md #1):** `_Z_GATE = 3.0` là phỏng đoán hợp lý, **chưa benchmark**.
> Với n nhỏ, masking effect có thể bỏ sót outlier thứ 2 (2 outlier làm phồng std). Chấp nhận cho v1;
> nêu rõ giới hạn này trong report. `contamination` vẫn truyền vào từng detector (chúng cần), nhưng
> quyết định ensemble giờ do z-gate.

### 3c. Sửa test theo INTENT, không chỉ behavior (CLAUDE.md #9)

Thêm vào `tests/engines/test_anomaly_engine.py`:

```python
    def test_clean_data_yields_no_outliers(self, clean_csv_path):
        """Data sạch KHÔNG được sinh outlier nào (intent, không chỉ 'few')."""
        from ingestion.csv_reader import load_csv
        df = load_csv(clean_csv_path)
        result = run_anomaly_detection(df)
        assert result["n_outliers"] == 0
```

Và trong `tests/ontology/test_findings_builder.py`, siết `test_clean_data_no_anomalies`:

```python
        # Data sạch KHÔNG được gán finding mức HIGH/CRITICAL
        assert all(a.severity in (Severity.INFO, Severity.WARN) for a in findings.anomalies)
```
(nhớ `from ontology.models import Severity` ở đầu file test).

**AC Patch 3:** `pytest tests/engines/test_anomaly_engine.py tests/ontology/test_findings_builder.py -v`
→ all pass; test mới `test_clean_data_yields_no_outliers` **fail với code cũ, pass sau patch**.

---

## Patch 4 — Ingestion Plugin (vá Part 1, Task 4) — NHIỆM VỤ MỚI

Lý do: `project_brief` đặt **nguyên tắc kiến trúc số 1 = Plugin Architecture** và MVP yêu cầu
**CSV + Excel + Parquet**. Task 4 gốc chỉ có 1 hàm `load_csv` lẻ → vi phạm ngay từ module đầu.
Thiết kế: reader chỉ **đọc thuần** → DataFrame; sampling tách riêng (sửa luôn lỗi "sample trước
anomaly có thể vứt mất outlier" — giờ là 1 bước rõ ràng, dễ tắt sau này).

### 4a. `pyproject.toml` — thêm dependency

```toml
    "openpyxl>=3.1",     # đọc .xlsx
    "pyarrow>=14.0",     # đọc .parquet
```

### 4b. `src/ingestion/sampling.py` (mới)

```python
"""Tách sampling khỏi reader để dùng chung & dễ tắt cho anomaly detection."""
import logging
import pandas as pd

logger = logging.getLogger(__name__)


def sample_if_large(df: pd.DataFrame, threshold: int = 500_000, seed: int = 42) -> pd.DataFrame:
    if len(df) > threshold:
        logger.info("Dataset %d rows > %d. Sampling down.", len(df), threshold)
        return df.sample(n=threshold, random_state=seed).reset_index(drop=True)
    return df
```

### 4c. `src/ingestion/base.py` (mới)

```python
from typing import Protocol
import pandas as pd


class DataReader(Protocol):
    """Mọi reader implement interface này. Thêm format mới = thêm 1 class, KHÔNG sửa pipeline."""
    suffixes: tuple[str, ...]
    def read(self, path: str) -> pd.DataFrame: ...
```

### 4d. `src/ingestion/readers.py` (mới)

```python
"""Readers thuần: file -> DataFrame. KHÔNG sampling ở đây."""
import pandas as pd
from pathlib import Path

_ENCODINGS = ["utf-8", "utf-8-sig", "latin-1"]


class CSVReader:
    suffixes = (".csv",)
    def read(self, path: str) -> pd.DataFrame:
        for enc in _ENCODINGS:
            try:
                return pd.read_csv(path, encoding=enc)
            except UnicodeDecodeError:
                continue
        raise ValueError(f"Cannot read {path} with encodings {_ENCODINGS}")


class ExcelReader:
    suffixes = (".xlsx", ".xls")
    def read(self, path: str) -> pd.DataFrame:
        return pd.read_excel(path)            # sheet đầu tiên; multi-sheet để v2


class ParquetReader:
    suffixes = (".parquet",)
    def read(self, path: str) -> pd.DataFrame:
        return pd.read_parquet(path)          # Parquet có sẵn dtype → không cần encoding fallback
```

### 4e. `src/ingestion/registry.py` (mới)

```python
"""Entry point chung của Ingestion Layer. Pipeline chỉ gọi load_any()."""
from pathlib import Path
from typing import List
import pandas as pd
from ingestion.base import DataReader
from ingestion.readers import CSVReader, ExcelReader, ParquetReader
from ingestion.sampling import sample_if_large

_READERS: List[DataReader] = [CSVReader(), ExcelReader(), ParquetReader()]


def _pick_reader(path: str) -> DataReader:
    suffix = Path(path).suffix.lower()
    for r in _READERS:
        if suffix in r.suffixes:
            return r
    supported = sorted({s for r in _READERS for s in r.suffixes})
    raise ValueError(f"Unsupported format '{suffix}'. Supported: {supported}")


def load_any(path: str, sample_threshold: int = 500_000, seed: int = 42) -> pd.DataFrame:
    if not Path(path).exists():
        raise FileNotFoundError(f"File not found: {path}")
    df = _pick_reader(path).read(path)
    return sample_if_large(df, sample_threshold, seed)
```

### 4f. `src/ingestion/csv_reader.py` — biến `load_csv` thành wrapper (giữ test cũ xanh)

```python
"""Backward-compat wrapper. Code mới nên dùng ingestion.registry.load_any()."""
from pathlib import Path
from ingestion.readers import CSVReader
from ingestion.sampling import sample_if_large
import pandas as pd


def load_csv(file_path: str, sample_threshold: int = 500_000, random_seed: int = 42) -> pd.DataFrame:
    if not Path(file_path).exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    return sample_if_large(CSVReader().read(file_path), sample_threshold, random_seed)
```

### 4g. Test mới `tests/ingestion/test_registry.py`

```python
import pytest
import pandas as pd
from ingestion.registry import load_any


class TestLoadAny:
    def test_csv(self, clean_csv_path):
        assert len(load_any(clean_csv_path)) == 10

    def test_parquet(self, clean_csv_path, tmp_path):
        df = pd.read_csv(clean_csv_path)
        p = tmp_path / "x.parquet"; df.to_parquet(p)
        assert len(load_any(str(p))) == 10

    def test_excel(self, clean_csv_path, tmp_path):
        df = pd.read_csv(clean_csv_path)
        p = tmp_path / "x.xlsx"; df.to_excel(p, index=False)
        assert len(load_any(str(p))) == 10

    def test_unsupported(self, tmp_path):
        p = tmp_path / "x.txt"; p.write_text("hi")
        with pytest.raises(ValueError):
            load_any(str(p))

    def test_missing(self):
        with pytest.raises(FileNotFoundError):
            load_any("nope.csv")
```

**AC Patch 4:** `pytest tests/ingestion/ -v` → all pass (6 test cũ csv_reader + 5 test mới registry).

---

## Patch 5 — Visualizer L3.5 (giải quyết NEW-1) — NHIỆM VỤ MỚI

Diagnostic chart = matplotlib deterministic, vẽ **100% điểm rác đè lên dữ liệu thường** (Quyết định 5),
điền `diagnostic_chart` **trước** khi gọi LLM.

### 5a. `src/engines/visualizer.py` (mới)

```python
"""L3.5: vẽ diagnostic chart bằng matplotlib (deterministic). KHÔNG dùng LLM."""
import logging
from pathlib import Path
from typing import Optional, List
import matplotlib
matplotlib.use("Agg")                     # headless: chạy được trong test/CI
import matplotlib.pyplot as plt
import pandas as pd

logger = logging.getLogger(__name__)


def draw_diagnostic_scatter(
    df: pd.DataFrame, anomaly_result: dict, out_dir: str
) -> Optional[str]:
    """Scatter 2 cột numeric có phương sai lớn nhất; tô đỏ TẤT CẢ outlier. Trả path .png hoặc None."""
    if anomaly_result.get("skipped", True) or anomaly_result.get("n_outliers", 0) == 0:
        return None

    numeric = df.select_dtypes(include="number")
    cols = anomaly_result.get("numeric_columns_used") or list(numeric.columns)
    cols = [c for c in cols if c in numeric.columns]
    if len(cols) < 2:
        return None
    x_col, y_col = numeric[cols].var().sort_values(ascending=False).index[:2]

    outlier_idx = set(anomaly_result["outlier_indices"])
    is_out = df.index.isin(outlier_idx)

    Path(out_dir).mkdir(parents=True, exist_ok=True)
    out_path = str(Path(out_dir) / f"diagnostic_{x_col}_{y_col}.png")

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.scatter(df.loc[~is_out, x_col], df.loc[~is_out, y_col], c="#9aa0a6", s=18, label="normal")
    ax.scatter(df.loc[is_out, x_col], df.loc[is_out, y_col], c="#d93025", s=42, label="outlier")
    ax.set_xlabel(x_col); ax.set_ylabel(y_col)
    ax.set_title(f"Diagnostic: {x_col} vs {y_col} ({len(outlier_idx)} outliers)")
    ax.legend()
    fig.savefig(out_path, dpi=100, bbox_inches="tight")
    plt.close(fig)
    logger.info("Diagnostic chart saved: %s", out_path)
    return out_path


def attach_diagnostic_charts(findings, df: pd.DataFrame, anomaly_result: dict, out_dir: str):
    """Điền diagnostic_chart cho các AnomalyRecord OUTLIER_ENSEMBLE. Mutate findings tại chỗ."""
    chart = draw_diagnostic_scatter(df, anomaly_result, out_dir)
    if chart is None:
        return findings
    for rec in findings.anomalies:
        if rec.issue_type == "OUTLIER_ENSEMBLE":
            rec.diagnostic_chart = chart
    return findings
```

### 5b. Test `tests/engines/test_visualizer.py`

```python
import pytest
from pathlib import Path
from ingestion.csv_reader import load_csv
from engines.anomaly_engine import run_anomaly_detection
from engines.visualizer import draw_diagnostic_scatter


class TestVisualizer:
    def test_chart_created_for_dirty(self, dirty_csv_path, tmp_path):
        df = load_csv(dirty_csv_path)
        res = run_anomaly_detection(df)
        path = draw_diagnostic_scatter(df, res, str(tmp_path))
        if res["n_outliers"] > 0:
            assert path is not None and Path(path).exists()

    def test_no_chart_when_skipped(self, tmp_path):
        res = {"skipped": True, "n_outliers": 0}
        assert draw_diagnostic_scatter(None, res, str(tmp_path)) is None
```

### 5c. Cập nhật integration test (Part 2, Task 8) — wire L3.5 vào pipeline

Thêm sau bước build findings, trước khi dump JSON:

```python
        from engines.visualizer import attach_diagnostic_charts
        findings = attach_diagnostic_charts(
            findings, df, anomalies, out_dir=str(tmp_path / "charts")
        )
        # nếu có outlier thì record outlier phải có diagnostic_chart
        outlier_recs = [a for a in findings.anomalies if a.issue_type == "OUTLIER_ENSEMBLE"]
        for r in outlier_recs:
            assert r.diagnostic_chart is not None
```

**AC Patch 5:** `pytest tests/engines/test_visualizer.py tests/test_integration.py -v` → all pass.

> **Sequencing (NEW-1 đã đóng):** L3 (builder) → L3.5 (visualizer điền path) → L4 (LLM nhận JSON đã
> có path + ảnh). LLM **không** ra lệnh vẽ diagnostic chart nữa. `overview_charts` (heatmap, missing
> matrix) vẫn theo Quyết định 5 = **trích xuất từ ydata-profiling**, là task riêng — KHÔNG nằm trong
> patch này (đánh dấu để khỏi nhầm là đã xong).

---

## Task Graph (thứ tự cho Thợ)

```
TIP-P1 (models.py)  ──►  TIP-P2 (findings_builder import + n_zeros)
        │
        ├──►  TIP-P3 (anomaly z-gate + tests)
        │
        └──►  TIP-P4 (ingestion plugin)  ──►  TIP-P5 (visualizer + wire integration)
```

| TIP | Patch | Depends | Acceptance (Gherkin) |
|-----|-------|---------|----------------------|
| P1 | Patch 1 | — | Given models updated, When `pytest tests/ontology/`, Then all pass incl. 3 new tests |
| P2 | Patch 2 | P1 | Given `Severity` imported + n_zeros wired, When `pytest tests/ontology/test_findings_builder.py tests/test_integration.py`, Then no NameError & all pass |
| P3 | Patch 3 | P1 | Given z-gate, When clean fixture profiled, Then `n_outliers == 0` AND no HIGH/CRITICAL finding; When dirty fixture, Then `n_outliers > 0` |
| P4 | Patch 4 | — | Given plugin readers, When load CSV/Excel/Parquet, Then each returns 10-row DataFrame; unsupported suffix → ValueError |
| P5 | Patch 5 | P4 | Given dirty data with outliers, When pipeline runs, Then `.png` exists AND every OUTLIER_ENSEMBLE record has `diagnostic_chart` set |

Cuối cùng: `pytest tests/ -v` → toàn bộ xanh, rồi commit theo từng TIP với message tương ứng.

---

## Phần KHÔNG đụng tới / cần bạn quyết riêng (CLAUDE.md #3, #16)

- **`overview_charts` (heatmap/missing matrix):** vẫn theo Quyết định 5 = trích từ ydata-profiling,
  **chưa** có task. Cần 1 TIP riêng nếu muốn L4 nhìn được overview. *Lưu ý:* builder đang gọi
  `run_profiling(minimal=True)` → ydata **bỏ qua correlation** → không có sẵn heatmap. Muốn overview
  heatmap phải chạy `minimal=False` (chậm hơn). Đây là trade-off bạn cần chốt.
- **`full_anomalies_export_path` (dump 100% dòng lỗi ra CSV — Quyết định 6):** chưa có task. Đơn giản
  (1 hàm `to_csv`), nhưng vẫn là feature-đã-quyết-thiếu-task → nêu để bạn xếp lịch.
- **Doc fix (không phải code):** JSON ví dụ trong `project_brief` Output 1 dùng `summary.{rows,columns}`
  và `row_index` (không gạch dưới), lệch contract thật (`dataset_meta.n`, `_row_index`/`_anomaly_score`).
  Vì JSON này sẽ thành ví dụ trong prompt LLM, nên sửa ví dụ về đúng schema kẻo LLM học sai tên field.

## Độ tin & phần CHƯA verify (chưa chạy code thật)

- **Chắc chắn:** Patch 1, 2, 4, 5 (đối chiếu trực tiếp giữa các file chốt + Pydantic/pandas API ổn định).
- **Đúng cơ chế, cần calibrate:** Patch 3 — `_Z_GATE=3.0` là heuristic; logic z-score/sigmoid đúng về
  bản chất nhưng ngưỡng nên tinh chỉnh trên vài dataset thật.
- **Chưa verify (phải test bằng code):** (a) ydata-profiling `to_json()` có key `n_zeros` đúng tên ở
  version cài đặt — nếu khác tên, sửa `_extract_column_stats`; (b) `ExcelReader`/`ParquetReader` cần
  `openpyxl`/`pyarrow` cài thành công; (c) matplotlib Agg backend đã set sẵn nên test headless OK,
  nhưng cần xác nhận môi trường Thợ có matplotlib.
