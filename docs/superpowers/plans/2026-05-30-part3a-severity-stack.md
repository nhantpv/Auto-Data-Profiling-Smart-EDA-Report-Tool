# Part 3a — Severity Stack (Calibrator → Compound → Aggregator)

> **Cho Thợ:** Build deterministic Layer 2.5. KHÔNG LLM, KHÔNG network. TDD task-by-task.
> Source of truth là CODE hiện tại (các plan doc cũ đã lệch — đừng tin doc, đọc code).
> Gặp conflict/mơ hồ → DỪNG, Issue Report, không tự quyết.

## Goal
Sinh file JSON thứ 3 — `dataset_verdict.json` — trả lời "data dùng được chưa?" (READY/WARN/NOT_READY)
từ `data_quality_findings.json` (+ schema findings nếu có sau này). Hoàn tất "deterministic core".

## Scope 3a (làm) vs KHÔNG làm
- ✅ Calibrator: sinh **column-level findings** (missingness, constant, cardinality, imbalance) + gán severity theo bảng config.
- ✅ Compound: gộp nhiều finding **cùng một cột** → nâng bậc severity.
- ✅ Aggregator: roll-up → `VerdictSummary` + verdict → `DatasetVerdict`.
- ❌ KHÔNG làm missingness MCAR/MAR/MNAR (đó là 3b, spike riêng — Little's test không có lib chuẩn).
- ❌ KHÔNG làm schema engine (chưa có); aggregator phải chạy được khi **không có** schema findings.

---

## ⚠️ Khái niệm BẮT BUỘC nắm: severity (trục A) ≠ verdict (trục B)

Hai trục KHÁC nhau, tình cờ chung chữ "WARN" — đừng trộn:

- **Trục A — severity tier (mỗi finding):** `INFO < WARN < HIGH < CRITICAL` (đã có enum `Severity` + `SEVERITY_ORDER`).
- **Trục B — verdict (cả dataset):** `READY / WARN / NOT_READY` (đã có enum `Verdict`).

**Quy tắc verdict (theo severity cao nhất của toàn bộ findings sau compound):**
| Severity cao nhất hiện diện | Verdict |
|---|---|
| có ≥1 CRITICAL | **NOT_READY** |
| có ≥1 HIGH (không CRITICAL) | **WARN** |
| chỉ WARN/INFO, hoặc không finding | **READY** |

Lưu ý: WARN-*severity* → READY-*verdict* (lỗi nhỏ không chặn). HIGH-severity → WARN-verdict. Đây là chủ ý.

> Tham khảo tiền lệ trước khi code: đọc `soda_core` (outcome pass/warn/fail) và `deequ`
> (`CheckLevel.Warning/Error`) — cách họ map ngưỡng → tầng → verdict gần đúng cái ta cần.

---

## Config — `config/calibrator_table.json` (bảng ngưỡng tách khỏi code để tune được)

```json
{
  "completeness": {
    "metric": "p_missing",
    "thresholds": [
      {"max": 0.05, "severity": "INFO"},
      {"max": 0.20, "severity": "WARN"},
      {"max": 0.50, "severity": "HIGH"},
      {"max": 1.01, "severity": "CRITICAL"}
    ],
    "dq_dimension": "Completeness"
  },
  "constant_column": {"rule": "n_distinct <= 1", "severity": "HIGH", "dq_dimension": "Uniqueness"},
  "high_cardinality": {"rule": "categorical and p_distinct > 0.9", "severity": "WARN", "dq_dimension": "Uniqueness"},
  "severe_imbalance": {"rule": "categorical and imbalance > 0.95", "severity": "WARN", "dq_dimension": "Consistency"}
}
```

> Vì sao là JSON ngoài, không hardcode: bảng calibration là **data**, để DAMA-ngưỡng chỉnh được mà
> không sửa code (đúng mục đích "calibrator table" của kiến trúc).

---

## Task 3a-1: Calibrator — sinh column-level findings

**Files:** `src/severity/calibrator.py`, `tests/severity/test_calibrator.py`

Đọc `DataQualityFindings.columns` (kiểu `ColumnStats`) + bảng config → trả `List[AnomalyRecord]`
(dùng lại model có sẵn; `issue_type` = "MISSINGNESS"/"CONSTANT_COLUMN"/"HIGH_CARDINALITY"/"IMBALANCE").
KHÔNG đụng anomaly/integrity findings đã có severity từ trước (chỉ thêm column-level mới).

```python
def calibrate_columns(columns: dict[str, ColumnStats], table: dict) -> list[AnomalyRecord]:
    """Sinh finding mức cột từ stats theo bảng ngưỡng. severity lấy từ table."""
```

Quy tắc:
- `p_missing` → tra `completeness.thresholds` (ngưỡng đầu tiên `p_missing < max`). Chỉ tạo finding nếu severity > INFO? → KHÔNG: tạo cả INFO để summary đếm đủ; nhưng nếu p_missing == 0 thì BỎ QUA (không có vấn đề).
- `n_distinct <= 1` → finding CONSTANT_COLUMN (HIGH).
- categorical (`type == "Categorical"`) + `imbalance > 0.95` → IMBALANCE (WARN).
- categorical + `p_distinct > 0.9` (n_distinct/n) → HIGH_CARDINALITY (WARN). (p_distinct = n_distinct/n; n lấy từ dataset_meta — truyền vào.)

**AC:**
- cột p_missing=0.6 → 1 finding severity=CRITICAL, dq_dimensions=["Completeness"].
- cột p_missing=0.0 → KHÔNG finding.
- cột n_distinct=1 → finding CONSTANT_COLUMN severity=HIGH.
- cột Categorical imbalance=0.99 → finding IMBALANCE severity=WARN.

---

## Task 3a-2: CompoundEscalator — nâng bậc khi 1 cột nhiều lỗi

**Files:** `src/severity/compound.py`, `tests/severity/test_compound.py`

```python
def apply_compound(findings: list[AnomalyRecord]) -> list[AnomalyRecord]:
    """Gộp findings theo cột bị ảnh hưởng; nếu 1 cột có >=2 finding,
    set compound_severity = escalate(max_severity, n_extra) cho các finding đó."""
```

- Nhóm theo cột. Cách lấy cột của 1 finding: ưu tiên `affected_column` nếu có; nếu không, suy từ
  `issue_type` + sample (column-level finding của 3a-1 nên mang tên cột — THÊM field `affected_column:
  Optional[str] = None` vào AnomalyRecord nếu chưa có, default None).
- Finding **multivariate** (OUTLIER_ENSEMBLE — không thuộc 1 cột) và DUPLICATE: **đứng riêng**, KHÔNG
  gộp (không ép gán cột). compound_severity = severity gốc.
- Escalate dùng `SEVERITY_ORDER` đã có: `idx = min(order.index(max_sev) + (count-1), len-1)`.

**AC (lấy đúng ví dụ data-flow):**
- cột "age" có 2 finding [outlier→HIGH, missing→WARN] gán cùng affected_column="age"
  → cả hai có compound_severity=CRITICAL (HIGH + 1 bậc).
- finding OUTLIER_ENSEMBLE (multivariate, affected_column=None) → compound_severity == severity (không đổi).
- cột chỉ 1 finding → compound_severity == severity.

> Dùng `SEVERITY_ORDER` từ `ontology.models` — KHÔNG tự định nghĩa lại thứ tự (single source of truth).

---

## Task 3a-3: Aggregator — roll-up → DatasetVerdict

**Files:** `src/severity/aggregator.py`, `tests/severity/test_aggregator.py`

```python
def aggregate(meta: DatasetMeta,
              dq_findings: list[AnomalyRecord],
              integrity_errors: list[IntegrityError] | None = None) -> DatasetVerdict:
    """Đếm theo tier (dùng compound_severity nếu có, else severity) -> VerdictSummary;
    áp quy tắc verdict (bảng trục B ở trên) -> DatasetVerdict."""
```

- `effective_severity(f) = f.compound_severity or f.severity`.
- Đếm vào `VerdictSummary` (critical/high/warn/info, total_issues).
- Verdict: CRITICAL→NOT_READY; elif HIGH→WARN; else READY.
- `verdict_rationale`: chuỗi ngắn nêu lý do (vd "1 CRITICAL completeness ở cột X").
- `integrity_errors` None hoặc rỗng → vẫn chạy bình thường.

**AC:**
- findings có 1 CRITICAL → verdict=NOT_READY.
- max=HIGH, không CRITICAL → WARN.
- chỉ WARN/INFO → READY.
- list rỗng + integrity=None → READY, summary.total_issues=0.
- DatasetVerdict serialize/deserialize round-trip OK.

---

## Task 3a-4: Wire vào pipeline + xuất file thứ 3

**Files:** sửa orchestrator/integration test.

Sau khi có `DataQualityFindings`:
```python
from severity.calibrator import calibrate_columns
from severity.compound import apply_compound
from severity.aggregator import aggregate

col_findings = calibrate_columns(findings.columns, table, n=findings.dataset_meta.n)
all_dq = apply_compound(findings.anomalies + col_findings)
verdict = aggregate(findings.dataset_meta, all_dq)   # integrity=None cho tới khi có schema engine
# dump verdict.model_dump_json() -> output/dataset_verdict.json
```

**AC integration:** chạy full pipeline trên `stroke_classification.csv` → sinh `dataset_verdict.json`
hợp lệ. Sanity (mềm, không hard-assert vì phụ thuộc ngưỡng): với data này (bmi 3.9% missing → INFO,
outlier 3% → WARN, không CRITICAL) verdict kỳ vọng **READY** hoặc **WARN**, KHÔNG NOT_READY.

---

## GATE 3a
`pytest tests/ -v` xanh hết (gồm tests/severity/* mới). Pipeline sinh đủ **2/3** JSON
(`data_quality_findings.json` + `dataset_verdict.json`; `schema_evaluation_findings.json` chờ schema engine).

## Sau 3a (không làm bây giờ)
- **3b spike:** missingness MCAR/MAR/MNAR (statsmodels/Little's test — rủi ro cao, làm riêng).
- Schema engine (pydbml + integrity) → file JSON thứ 3 thật.
- overview_charts (giờ đã khả thi vì minimal=False có correlations).
- L4 LLM + Guardrail.

## Phần cần verify khi chạy (chưa chắc tới khi có code)
- `imbalance`/`p_distinct` key tên đúng trong ColumnStats.additional_metrics — đã thấy `imbalance`
  xuất hiện thật trên file stroke, nhưng `p_distinct` hiện CHƯA được lưu vào ColumnStats → 3a-1 cần
  tính `p_distinct = n_distinct / n` từ `n_distinct` + `dataset_meta.n` (đừng giả định có sẵn).
- Cần thêm `affected_column: Optional[str] = None` vào AnomalyRecord (Task 3a-1/3a-2) — kiểm xem
  model đã có chưa; nếu chưa thì đây là sửa nhỏ ở models.py + 1 test.
