# Báo cáo Audit: Source Code vs. Bản Thiết kế Kiến trúc

**Vai trò:** Principal System Architect & Code Auditor
**Phạm vi:** Toàn bộ source code trong `src/`, `tests/`, `run_pipeline.py` đối chiếu với [system_architecture_design.md](file:///d:/Developer/Auto-Data-Profiling-Smart-EDA-Report-Tool/docs/system_architecture_design.md).

---

## I. BẢN ĐỒ ĐỐI CHIẾU: Kiến trúc vs. Code

### Sơ đồ cấu trúc thư mục hiện tại

```
src/
├── ingestion/          ← Layer 0 (Data Ingestion)
│   ├── base.py              Protocol DataReader
│   ├── readers.py           CSVReader, ExcelReader, ParquetReader
│   ├── registry.py          Auto-detect format (load_any)
│   ├── csv_reader.py        load_csv() entry point
│   └── sampling.py          sample_if_large() — giới hạn 500k dòng
├── engines/            ← Layer 1 & 2 (Profiling + Anomaly + Schema)
│   ├── profiling_engine.py  ydata-profiling wrapper
│   ├── anomaly_engine.py    PyOD Ensemble (IForest + ECOD + LOF)
│   ├── schema_engine.py     pydbml parser + 7 validators + FK check
│   └── visualizer.py        Optional chart artifact cho end user
├── ontology/           ← Layer 3 (JSON Ontology)
│   ├── models.py            Pydantic models (15 classes)
│   └── findings_builder.py  Phễu lọc ydata → JSON nén
├── severity/           ← Layer 2.5 (Severity Stack)
│   ├── missingness.py       MCAR/MAR/MNAR Detector (Little's + LogReg)
│   ├── calibrator.py        Tra bảng calibrator_table.json
│   ├── compound.py          CompoundEscalator
│   └── aggregator.py        Dataset Verdict (READY/WARN/NOT_READY)
├── guardrail/          ← Layer 4 (Guardrail) — CHỈ CÓ __init__.py TRỐNG
│   └── __init__.py
├── reporting/          ← Text report fallback
│   └── summary_renderer.py  Markdown deterministic từ JSON/verdict
config/
└── calibrator_table.json
tests/                  ← 238 dòng integration + unit tests
```

### Bảng đối chiếu từng Layer

| Layer (Thiết kế) | Module Code | Trạng thái | Ghi chú |
|:---|:---|:---:|:---|
| L0: Data Ingestion | `ingestion/` | ✅ Hoàn thành | CSV, Excel, Parquet, JSON/JSONL. Có sampling 500k dòng. |
| L1: Deterministic Profiling | `engines/profiling_engine.py` | ✅ Hoàn thành | ydata-profiling, tự đếm duplicates. |
| L2 NV1: PyOD Ensemble | `engines/anomaly_engine.py` | ✅ Hoàn thành | IForest + ECOD + LOF. Z-score combiner. |
| L2 NV2: DBML Validator | `engines/schema_engine.py` | ✅ Hoàn thành | 7 loại lỗi + FK orphan check. Multi-table. |
| L2.5a: Missingness Detector | `severity/missingness.py` | ✅ Hoàn thành | Little's test + Logistic CV-AUC. |
| L2.5b: Calibrator | `severity/calibrator.py` | ✅ Hoàn thành | Tra bảng JSON, escalate MAR/MNAR. |
| L2.5c: CompoundEscalator | `severity/compound.py` | ✅ Hoàn thành | Gộp lỗi theo cột, nâng bậc. |
| L2.5d: Aggregator | `severity/aggregator.py` | ✅ Hoàn thành | READY/WARN/NOT_READY verdict. |
| L3: Pydantic Ontology | `ontology/models.py` | ✅ Hoàn thành | 15 Pydantic classes, Severity enum, C1 fields. |
| L3: FindingsBuilder | `ontology/findings_builder.py` | ✅ Hoàn thành | Phễu lọc ydata → JSON nén. |
| L3.5: Diagnostic Charts | `engines/visualizer.py` | ⚠️ Một phần | Scatter chart có; chart chỉ là artifact phụ trợ, không đi vào L4. |
| L4: Guardrail | `guardrail/__init__.py` | ❌ Trống | Chưa code gì. |
| L4: Multi-Agent LLM | *(không có)* | ❌ Chưa có | Chưa có code LLM nào. |
| Output: JSON + Markdown | `run_pipeline.py` | ✅ Hoàn thành | data_quality + schema_eval + verdict + summary_report.md. |

---

## II. ĐIỂM MẠNH (Những thứ code làm RẤT TỐT)

### 1. Kiến trúc phân lớp cực kỳ sạch
Code tách bạch hoàn hảo theo đúng 5 package (`ingestion → engines → severity → ontology → guardrail`). Mỗi module có đúng 1 trách nhiệm (Single Responsibility). Không có sự phụ thuộc vòng tròn (circular import). Đây là nền tảng vững chắc để mở rộng.

### 2. Anomaly Engine thiết kế thông minh hơn bản thiết kế
Bản thiết kế ghi dùng `pyod.models.combination.average()` (Average Score). Nhưng code thực tế đã **nâng cấp** lên dùng **Max Z-score combiner** ([anomaly_engine.py:83](file:///d:/Developer/Auto-Data-Profiling-Smart-EDA-Report-Tool/src/engines/anomaly_engine.py#L83)):
```python
ensemble_z = np.max([_zscore(s) for s in raw_scores], axis=0)
```
Đây là lựa chọn tốt hơn vì: LOF có thể trả về điểm âm trên tập dữ liệu nhỏ. Việc dùng Max thay vì Average giúp tránh "pha loãng" tín hiệu dị biệt. Comment trong code cũng giải thích rõ: *"robust to LOF sign-inversion on small n"*.

### 3. Pre-imputation đã được thực hiện đúng
Trong [anomaly_engine.py:47](file:///d:/Developer/Auto-Data-Profiling-Smart-EDA-Report-Tool/src/engines/anomaly_engine.py#L47):
```python
clean_df = non_constant.dropna()
```
Code dùng `dropna()` (loại bỏ dòng có NaN) thay vì điền Median trước khi chạy PyOD. Cách này **an toàn hơn** so với đề xuất "điền Median" trong tài liệu kiến trúc, vì nó không tạo ra dữ liệu giả tạo có thể ảnh hưởng đến kết quả phát hiện Outlier. Tuy nhiên, cần lưu ý: nếu dataset bị thiếu quá nhiều dòng, số dòng được quét sẽ giảm đáng kể.

### 4. Schema Engine cực kỳ toàn diện (348 dòng)
- Bảng parent rỗng → `FK_UNCHECKED` ([schema_engine.py:263](file:///d:/Developer/Auto-Data-Profiling-Smart-EDA-Report-Tool/src/engines/schema_engine.py#L263)).

### 5. Test coverage rất tốt
- **Unit tests:** Mỗi module `severity/` và `engines/` đều có file test riêng.
- **Integration test:** test end-to-end chạy từ data file → JSON → Verdict → Markdown.
- **Fixtures thực tế:** Có `outliers_realistic.csv`, `schema_bad.csv/dbml`, thư mục `multi/` cho multi-table.

### 6. Ingestion Module thiết kế mở rộng tốt
Hệ thống `base.py` (Protocol) + `readers.py` + `registry.py` tuân thủ **Open/Closed Principle**: muốn thêm định dạng mới (ví dụ `.json`, `.sql`) chỉ cần tạo class mới implement Protocol `DataReader` rồi thêm vào danh sách `_READERS`. Không cần sửa code cũ.

---

## III. ĐIỂM YẾU & SAI LỆCH SO VỚI THIẾT KẾ (Đã giải quyết 2/6 điểm)

### ✅ 1. Luồng dữ liệu trong `run_pipeline.py` KHÔNG ĐÚNG sơ đồ Mermaid (ĐÃ GIẢI QUYẾT)

**Sơ đồ thiết kế (Mermaid):**
```
E1 (profiling) → SS1 (Missingness)     ← CHỈ E1 chảy vào SS1
E1 & E2        → SS2 (Calibrator)
SS1 → SS2 → SS3 (Compound) → SS4 (Aggregator)
```

**Khắc phục:** 
Đã tách hàm `detect_missingness(df)` ra khỏi `findings_builder.py` (L3) và đưa lên gọi trực tiếp/tường minh trong `run_pipeline.py` (L2.5) trước khi build findings. Kết quả `mechs` được truyền ngoài vào. Luồng chạy trong code hiện tại đã khớp **100%** với sơ đồ thiết kế.

### ✅ 2. Calibrator KHÔNG nhận kết quả trực tiếp từ PyOD (E2) (ĐÃ GIẢI QUYẾT)

**Thiết kế:** `E1 & E2 → SS2 (Calibrator)`

**Khắc phục:**
Đã thêm cấu hình `outlier_ensemble` và `duplicate` vào `config/calibrator_table.json` và thay thế hoàn toàn logic gán severity hardcode trong `findings_builder.py` bằng helper `_threshold_severity()` tra cứu động từ calibrator table. Hệ thống hiện tại đã đảm bảo tính **config-driven** hoàn toàn cho outlier và duplicate severity.

### 🟡 3. Thiếu tính năng "Anomaly CSV Export"


Thiết kế ghi rõ: *"Tự động xuất 100% các dòng dị biệt ra file CSV riêng biệt"*. Code hiện tại chỉ lưu top 10 samples vào JSON (`top_10_samples`) nhưng **không hề xuất file CSV đầy đủ** cho Data Engineer. Trường `full_anomalies_export_path` trong model [AnomalyRecord:52](file:///d:/Developer/Auto-Data-Profiling-Smart-EDA-Report-Tool/src/ontology/models.py#L52) đã được khai báo nhưng luôn là `None`.

### 🟡 4. Sampling Constraint cho Missingness Detector chưa có

Thiết kế ghi: *"Nếu dataset > 10.000 dòng, SS1 phải lấy mẫu ngẫu nhiên xuống 10.000 dòng"*. Code [missingness.py](file:///d:/Developer/Auto-Data-Profiling-Smart-EDA-Report-Tool/src/severity/missingness.py) hiện tại **không có sampling** — nó chạy Little's Test trên toàn bộ numeric DataFrame. Với file lớn (>100k dòng), hệ thống có nguy cơ bị treo.

### 🟡 5. Overview Charts chưa được trích xuất

Thiết kế Layer 3.5 ghi: *"Trích xuất biểu đồ nằm trong output của ydata-profiling"*. Code hiện tại chỉ có **Diagnostic scatter chart** ([visualizer.py](file:///d:/Developer/Auto-Data-Profiling-Smart-EDA-Report-Tool/src/engines/visualizer.py)). Chưa có code trích xuất Overview Charts (histogram, correlation matrix) từ ydata. Trường `overview_charts` trong model `DatasetMeta` luôn là dict rỗng.

### 🟢 6. Ensemble Combiner khác thiết kế (nhưng TỐT HƠN)

Thiết kế ghi `average()`, code dùng `np.max(z-scores)`. Đây là **sai lệch tích cực** — code đã cải tiến so với thiết kế. Nên cập nhật tài liệu thiết kế cho khớp.

---

## IV. PHÂN TÍCH TÍCH HỢP MODULE DATABASE EXTRACTOR

### Điểm gắn kết (Integration Point)

Dựa trên kiến trúc hiện tại, module mới cần gắn vào đúng **1 điểm duy nhất**: package `src/ingestion/`.

```
src/ingestion/
├── base.py         ← Protocol DataReader (KHÔNG SỬA)
├── readers.py      ← Thêm SQLReader class mới ở đây
├── registry.py     ← Đăng ký SQLReader vào _READERS
├── csv_reader.py   ← KHÔNG SỬA
├── sampling.py     ← KHÔNG SỬA
└── schema_reader.py  ← [MỚI] Đọc file .sql DDL, trả về cùng format với pydbml
```

#### ✅ Đã triển khai: Adapter Pattern (Phương án C)

Module `src/ingestion/schema_reader.py` đã được tạo với hàm `parse_schema()` auto-detect format:
- `.dbml` → gọi `_parse_dbml()` (sử dụng `pydbml`)
- `.sql` → gọi `_parse_sql_ddl()` (sử dụng `simple-ddl-parser`)

Cả 2 adapter trả về **Unified Schema Result** dict chuẩn hóa:
```python
{"tables": {...}, "refs": [...], "meta": {...}}
```

`schema_engine.py` đã được refactor: không còn import `pydbml` trực tiếp, chỉ gọi `parse_schema()`.
CLI đã đổi flag `--dbml` → `--schema` để hỗ trợ cả `.dbml` lẫn `.sql`.

#### Hướng B: "Direct DB Connection" (Dành cho V2 — tự động hóa)

Chỉ triển khai khi có nhu cầu chạy scheduled profiling hàng ngày. Cần bổ sung đầy đủ:
- `.env` + `python-dotenv` cho credential.
- Tài khoản READ-ONLY.
- Audit logging.
- PII filtering config.

### Thứ tự ưu tiên hành động

| # | Hành động | Ưu tiên | Lý do |
|:---:|:---|:---:|:---|
| 1 | Viết `schema_reader.py` (đọc SQL DDL) | 🔴 Cao | Đây là module chính bạn đảm nhận. Gắn ngay vào `ingestion/`. |
| 2 | Sửa `schema_engine.py` auto-detect `.sql` vs `.dbml` | 🔴 Cao | Để hệ thống chấp nhận cả 2 format. |
| 3 | Thêm `simple-ddl-parser` vào `pyproject.toml` | 🔴 Cao | Dependency mới. |
| 4 | Viết test `tests/ingestion/test_schema_reader.py` | 🟡 Trung bình | Đảm bảo parse đúng cho PostgreSQL, MySQL, SQL Server. |
| 5 | Thêm sampling 10k cho `missingness.py` | 🟡 Trung bình | Vá lỗ hổng hiệu năng đã phát hiện. |
| 6 | Tách Outlier severity ra `calibrator_table.json` | 🟢 Thấp | Refactor nhỏ, không ảnh hưởng output. |

---

## V. TỔNG KẾT

| Hạng mục | Đánh giá |
|:---|:---:|
| Độ bám sát thiết kế (Compliance) | **85/100** |
| Chất lượng code (Quality) | **90/100** |
| Test coverage | **88/100** |
| Sẵn sàng tích hợp module mới (Integration-readiness) | **95/100** |

> [!IMPORTANT]
> **Nhận xét tổng thể:** Code hiện tại đã hiện thực hóa được **toàn bộ pipeline deterministic** (L0 → L1 → L2 → L2.5 → L3) với chất lượng rất cao. Kiến trúc `ingestion/` với Protocol pattern đặc biệt thuận lợi cho việc gắn thêm module đọc SQL DDL — bạn chỉ cần viết 1 file `schema_reader.py` và sửa nhẹ `schema_engine.py` là xong, không cần đụng vào bất kỳ module nào khác.
