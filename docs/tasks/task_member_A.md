# Task: Member A — Backend Core (Severity + Registry + Graph)

## Bạn là ai
Bạn là AI coding assistant đang implement phần **Backend Core** cho dự án Smart EDA. Bạn **CHỈ SỬA các file được liệt kê bên dưới**. Không sửa file nào khác.

## Context dự án
- **SSOT**: Đọc `docs/ARCHITECT (8).md` — đây là tài liệu kiến trúc duy nhất
- **Pipeline hiện tại**: `run_pipeline.py` gọi L0→L1→L2→L2.5→L3→L4 tuần tự
- **Models đã được cập nhật**: `src/ontology/models.py` đã có sẵn `Provenance`, `GraphEdge`, `GraphResult`, `ThresholdEntry` — bạn import trực tiếp, KHÔNG tạo lại

## Files bạn SỞ HỮU (chỉ sửa các file này)

### File cần MODIFY:
1. `src/severity/missingness.py` — sửa H5 (missingness per-column)
2. `src/severity/calibrator.py` — sửa H5 (chỉ giữ MAR, bỏ "MNAR?")
3. `src/severity/aggregator.py` — sửa M1 (verdict density rule)
4. `src/ontology/findings_builder.py` — update dùng FindingRegistry + ThresholdRegistry

### File cần IMPLEMENT (stub đã tạo sẵn, thay `raise NotImplementedError`):
5. `src/config/threshold_registry.py` — implement `_load()`, `get()`, `maturity()`
6. `src/ontology/finding_registry.py` — implement `register_anomaly()`, `register_integrity_error()`
7. `src/engines/graph_engine.py` — implement `reconstruct_graph()`, `classify_cardinality()`, `check_pk_uniqueness()`

### File KHÔNG ĐƯỢC SỬA:
- `src/ontology/models.py` (đã hoàn chỉnh, locked)
- `src/reporting/*` (của Member B)
- `src/webapp/*` (của Member C)
- `run_pipeline.py` (của Member B)

## Yêu cầu chi tiết

### Task A1: H5 — Missingness per-column
**File**: `src/severity/missingness.py`
**Vấn đề hiện tại**: `detect_missingness()` tính AUC ở dataset-level → gán cùng 1 mechanism cho tất cả cột
**Cần sửa**: Tính AUC **per-column** (logistic regression mỗi cột target vs tất cả cột khác)
**Logic** (ARCHITECT §5.4 L2.5):
```
Với mỗi cột có missing > 0:
  - X = các cột khác (numeric)
  - y = cột_target.isna()
  - Fit LogisticRegression, tính AUC
  - AUC > 0.7 → MAR; AUC <= 0.7 → MCAR_CONSISTENT
  - KHÔNG dùng nhãn MNAR (đã deprecated, xem QĐ-6a)
```
**Backward compat**: Hàm `detect_missingness(df)` vẫn trả `dict[str, str]` nhưng giờ per-column thay vì 1 giá trị chung

### Task A2: H5 — Calibrator chỉ-MAR
**File**: `src/severity/calibrator.py`
**Vấn đề**: Có logic emit "MNAR?" hoặc xử lý MNAR
**Cần sửa**: Bỏ mọi reference tới "MNAR?". Chỉ giữ MAR / MCAR_CONSISTENT / INDETERMINATE
**Tham chiếu**: ARCHITECT §Mục 10 — QĐ-6a đã đóng: nghỉ hưu "MNAR?"

### Task A3: M1 — Verdict density rule
**File**: `src/severity/aggregator.py`
**Vấn đề**: Không có luật mật độ — dataset có nhiều WARN nhỏ vẫn pass
**Cần thêm** (ARCHITECT §5.6 L2.5):
```python
# Sau khi tính severity cho mọi finding:
warn_plus = [f for f in findings if effective_sev(f) >= WARN]
n_cols_affected = len(set(f.affected_column for f in warn_plus if f.affected_column))
share = len(warn_plus) / total_findings if total_findings else 0

if share > 0.20 and n_cols_affected >= 2:
    # Verdict ít nhất WARN, bất kể từng finding riêng lẻ
    verdict = max(verdict, Verdict.WARN)
```

### Task A4: ThresholdRegistry — implement
**File**: `src/config/threshold_registry.py` (stub đã tạo)
**Logic**:
- `_load()`: parse `config/calibrator_table.json`, với mỗi entry tạo `ThresholdEntry`
- `get(key)`: trả `entry.value`, raise KeyError nếu không có (trừ khi có default)
- `maturity(key)`: trả `entry.maturity` string
- Mọi ngưỡng hiện hardcode trong code (z=3.0, null_overlap=0.70, etc.) → chuyển qua registry

### Task A5: FindingRegistry — implement
**File**: `src/ontology/finding_registry.py` (stub đã tạo)
**Logic**:
- `register_anomaly(record)`: gán `finding_id` = sha256 hash của (issue_type + affected_column), dedup theo finding_id
- `register_integrity_error(error)`: tương tự
- Dedup: nếu cùng finding_id → giữ record có severity cao hơn

### Task A6: Graph Reconstruction — implement
**File**: `src/engines/graph_engine.py` (stub đã tạo)
**Logic** (ARCHITECT §5.5 L2c):
```
def reconstruct_graph(tables, schema):
    1. Lấy relationships từ schema.relationships
    2. Với mỗi relationship:
       a. classify_cardinality(child_df, child_col, parent_df, parent_col)
       b. check_pk_uniqueness(parent_df, parent_col)
       c. Tạo GraphEdge
    3. Nếu PK không unique → thêm vào non_unique_pk_tables + warning
    Return GraphResult

def classify_cardinality(child, child_col, parent, parent_col):
    parent_unique = parent[parent_col].is_unique
    child_unique = child[child_col].is_unique
    if parent_unique and child_unique: return "1:1"
    if parent_unique and not child_unique: return "1:N"
    return "N:N"
```

### Task A7: Update findings_builder
**File**: `src/ontology/findings_builder.py`
**Cần sửa**: Dùng `FindingRegistry` để register mọi anomaly trước khi trả về. Gán `threshold_ref` cho những anomaly dùng ngưỡng từ `ThresholdRegistry`.

## Test
Sau khi code xong, chạy:
```bash
python run_pipeline.py examples/sample_datasets/titanic/train.csv output_test
```
Verify:
- Pipeline không lỗi
- `dataset_verdict.json` có verdict hợp lý
- `data_quality_findings.json` có `finding_id` cho mỗi anomaly
- `missingness_mechanism` per-column (không phải 1 giá trị chung)

## Lưu ý quan trọng
- **KHÔNG import từ `reporting/`** — đó là của Member B
- **KHÔNG sửa `models.py`** — đã locked
- Tất cả field mới trong models đều có default → code cũ không cần sửa
- Viết docstring + type hints cho mọi hàm public
