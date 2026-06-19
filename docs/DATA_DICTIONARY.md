# Từ điển Dữ liệu (Data Dictionary)

Tài liệu này định nghĩa tất cả các khái niệm, thuật ngữ, cấu trúc dữ liệu (data models), và phân loại lỗi (issue catalog) được sử dụng xuyên suốt trong mã nguồn Smart EDA. Đây là kim chỉ nam (Single Source of Truth) để các kỹ sư hiểu cấu trúc thông tin di chuyển qua pipeline.

---

## Phần 1: Khái niệm Cốt lõi

### Pipeline Layer

| Layer | Tên | Mô tả |
|-------|-----|-------|
| **Layer 0** | Ingestion | Đọc đa dạng định dạng dữ liệu thô (CSV, DBML) chuyển thành chuẩn pandas DataFrame. Có cơ chế Sampling thông minh nén kích thước file khổng lồ. |
| **Layer 1** | Profiling | Đo đạc thống kê mô tả độc lập trên từng cột (Univariate). Tính toán mean, std, zero_count, missing_count, kiểu phân phối. |
| **Layer 2a** | Anomaly | Truy tìm bất thường đa biến với PyOD Ensemble (IForest, ECOD, LOF). Tính toán Outlier Z-Score. |
| **Layer 2b** | Schema | Đối chiếu cấu trúc. Xác thực tính toàn vẹn (Integrity) Type, PK, FK, Unique constraints. |
| **Layer 2c** | Cross-table | Tìm rò rỉ dữ liệu (Data Leakage) hoặc đa cộng tuyến (Multicollinearity) qua hệ số tương quan chéo. |
| **Layer 2d** | Graph | Sinh sơ đồ mạng lưới Schema (Schema Relationship Network Graph) từ DBML. |
| **Layer 2.5** | Severity Stack | 4 bước chấm điểm mức độ: Missingness MCAR → Tra ngưỡng → Cộng gộp lỗi (Escalation) → Ra Phán quyết. |
| **Layer 3** | Ontology | Đóng gói Pydantic thành các cấu trúc JSON tĩnh để tái sử dụng. |
| **Layer 3.5** | Visualizer | Sinh biểu đồ PNG trực quan (Diagnostic 3-Tier Layout: Boxplot, Scatter Grid, Data Sample). |
| **Layer 4** | Reporting | Điều phối hệ thống Agent AI. Multi-Agent LLM viết giải thích báo cáo dưới dự giám sát của Text/JSON Guardrail. |

---

### Mức độ nghiêm trọng (Severity)

Được định nghĩa bởi Class `Severity`. Ưu tiên: `INFO` < `WARN` < `HIGH` < `CRITICAL`

| Giá trị | Mã số | Ý nghĩa |
|---------|-------|---------|
| `INFO` | 0 | Thông tin lưu ý, dữ liệu hoàn toàn an toàn. |
| `WARN` | 1 | Rủi ro nhẹ, có thể train model nhưng cần tiền xử lý cẩn thận. |
| `HIGH` | 2 | Vấn đề nghiêm trọng ảnh hưởng trực tiếp độ chính xác của model, bắt buộc phải lọc bỏ hoặc impute phức tạp. |
| `CRITICAL`| 3 | Lỗi cấu trúc nghiêm trọng (Thiếu khóa, Orphan FK). Nguy cơ vỡ pipeline/crash ứng dụng. |

---

### Phán quyết tổng thể (Verdict)

Được tính bởi `src/severity/aggregator.py` dựa trên tổng Severity của dataset.

| Phán quyết | Quy tắc tính | Hành động |
|------------|--------------|-----------|
| `READY` | Hoàn toàn sạch, 0 lỗi `HIGH`, 0 lỗi `CRITICAL`. | Có thể deploy để train ngay. |
| `WARN` | Tồn tại `HIGH` nhưng không dính `CRITICAL`. | Dùng với sự cẩn trọng, khuyến nghị Imputation. |
| `NOT_READY`| Chỉ cần có 1 lỗi `CRITICAL`. | Chặn quy trình CI/CD. Đẩy lại cho Data Engineer. |

---

### Nguồn gốc (Provenance)

Được định nghĩa bởi Class `Provenance`. Xác định con số được tính bằng cách nào.

| Giá trị | Mô tả |
|---------|-------|
| `OBSERVED` | Tính trực tiếp từ Data (ví dụ đếm số Null = 500). |
| `INFERRED` | Máy tự suy luận (ví dụ Compound Escalator tự nâng mức Severity). |
| `LLM_GUIDED` | Bị ảnh hưởng bởi LLM (dùng trong Layer 4 Narrative). |

---

### Cơ chế Missingness (Cơ sở khoa học về rỗng dữ liệu)

Trích xuất từ `src/severity/missingness.py`

| Thuật ngữ | Tên đầy đủ | Giải thích ngắn | Rủi ro |
|---|---|---|---|
| `MCAR` | Missing Completely At Random | Lỗi kỹ thuật ngẫu nhiên, không liên quan bản chất dữ liệu. | Rất thấp. Có thể điền (Impute) bằng Mean/Mode. |
| `MAR` | Missing At Random | Bị rỗng do ảnh hưởng từ 1 cột khác (VD: "Nam" thì cột "Bệnh Nữ giới" rỗng). | Trung bình. Cần dùng Logistic/Tree Imputation. |
| `MNAR` | Missing Not At Random | Rỗng có tính hệ thống liên quan trực tiếp biến ẩn (VD: Người giàu hay giấu lương). | Rất nguy hiểm. Không thể Impute thường. |

---

### Chuẩn DAMA-DMBOK Dimensions

Ánh xạ từ chuẩn Data Management Body of Knowledge toàn cầu để phân rã chất lượng:
1. `Accuracy`: Dữ liệu chính xác với thực tế (Ví dụ: Tránh Outlier tuổi = 150).
2. `Completeness`: Mức độ đầy đủ của dữ liệu (Ví dụ: Bị null).
3. `Uniqueness`: Không trùng lặp (Ví dụ: PK_DUPLICATE).
4. `Consistency`: Tính nhất quán định dạng (Ví dụ: Mixed Data Type).
5. `Validity`: Trong giới hạn miền (Ví dụ: Tuổi < 0 là vô lý).

---

## Phần 2: Cấu trúc Data Models (Pydantic SSOT)

Nằm tại `src/ontology/models.py`.

### 1. `DatasetMeta` — Metadata toàn cục của Bảng

Lưu giữ trạng thái gốc và trạng thái sau khi thu gọn của file dữ liệu.

```python
class DatasetMeta(BaseModel):
    file_name: str
    n: int
    n_var: int
    memory_size: int
    p_cells_missing: float
    n_duplicates: int = 0
    p_duplicates: float = 0.0
    overview_charts: Dict[str, str]       # Map các chart tổng quan (missing heatmap...)
    is_sampled: bool = False              # Đã bị thu gọn chưa
    original_n: Optional[int] = None      # Số lượng dòng gốc
    sample_n: Optional[int] = None        # Kích thước sample
    sample_method: Optional[str] = None   # Ví dụ: "reservoir_sampling"
    sample_seed: Optional[int] = None     # Random seed
```

### 2. `ColumnStats` — Hồ sơ năng lực 1 Cột

```python
class ColumnStats(BaseModel):
    type: str                             # 'Numeric', 'Categorical', 'DateTime', 'Boolean'
    n_missing: int
    p_missing: float
    n_zeros: Optional[int] = None
    n_distinct: Optional[int] = None
    missingness_mechanism: Optional[str]  # 'MCAR', 'MAR', 'MNAR'
    additional_metrics: Dict[str, Any]    # Lưu mean, std, min, max, skewness
```

### 3. `AnomalyRecord` — Biên bản 1 Lỗi Đơn lẻ

```python
class AnomalyRecord(BaseModel):
    issue_type: str                       # Tên lỗi theo Catalog
    description: str                      # Ghi chú
    severity: Severity                    # Mức gốc
    compound_severity: Optional[Severity] # Mức sau khi Escalation (Cộng gộp)
    dq_dimensions: List[str]              # List DAMA dimension
    ml_impact: List[str]                  # Tác động model
    confidence: Optional[float]           # Z-score confidence của PyOD
    provenance: Provenance
    finding_id: Optional[str]             # ID dùng riêng cho Guardrail check
    threshold_ref: Optional[str]
    affected_count: int
    affected_percent: float
    affected_column: Optional[str]
    top_10_samples: List[Dict[str, Any]]  # Preview 10 rows
    diagnostic_chart: Optional[str]       # Đường dẫn ảnh PNG Box/Scatter
    full_anomalies_export_path: Optional[str] # File CSV đầy đủ lỗi
    probable_causes: List[str]            # List giải thích
    suggested_fix: List[str]              # List gợi ý
```

### 4. `DataQualityFindings` — Output chính phân tích tĩnh

```python
class DataQualityFindings(BaseModel):
    dataset_meta: DatasetMeta
    columns: Dict[str, ColumnStats]
    anomalies: List[AnomalyRecord]        # Mảng biên bản lỗi
```

### 5. `SchemaEvaluationFindings` — Output kiểm tra lược đồ SQL

```python
class SchemaEvaluationFindings(BaseModel):
    schema_meta: SchemaMeta               # Tên dbml, số tables
    tables: List[TableInfo]               # Tên các bảng
    integrity_errors: List[IntegrityError]# Mảng lỗi (TypeMismatch, PK_NULL)
    relationships: List[RelationshipInfo] # Danh sách sơ đồ FK mapping
```

### 6. `CrossTableAnalysis` — Output Đa Cộng Tuyến

```python
class CrossTableAnalysis(BaseModel):
    status: str
    fact_table: Optional[str]
    join_steps: List[SafeJoinStep]        # Tiến trình JOIN an toàn các bảng
    correlations: List[CrossTableCorrelation] # Các cặp cột có Tương quan cao
    anomalies: List[CrossTableAnomaly]    # Lỗi rò rỉ hoặc cộng tuyến liên bảng
```

### 7. `ArtifactManifest` — Định tuyến tập tin đầu ra

Được dùng bởi Evaluator để audit tự động.

```python
class ArtifactManifest(BaseModel):
    schema_version: str = "artifact_manifest_v1"
    artifacts: List[ArtifactRecord]       # List path tới từng HTML, JSON, PNG
```

---

## Phần 3: Catalog Cấp độ Lỗi (Issue Type Catalog)

Các mã lỗi mặc định được định nghĩa tại `src/ontology/issue_catalog.py`. Được phân giải qua File config `config/calibrator_table.json`.

### Lỗi Dữ liệu Cột (Column-level)

| Mã lỗi | DQ Dimension | Ngưỡng cấu hình mặc định (INFO/WARN/HIGH/CRITICAL) |
|--------|-------------|--------------------------------------------------|
| `MISSINGNESS` | Completeness | Phụ thuộc vào % Missing và Cơ chế (MCAR vs MNAR) |
| `OUTLIER_ENSEMBLE` | Accuracy | > 3.0 Z-score (PyOD) kích hoạt cảnh báo |
| `DUPLICATE` | Uniqueness | Bất kỳ trùng lặp toàn dòng nào |
| `CONSTANT_COLUMN` | Validity | Nếu 100% data chung 1 giá trị → Phế phẩm tính năng |
| `HIGH_CARDINALITY` | Consistency | > 90% dòng khác nhau (không tốt cho Grouping) |
| `IMBALANCE` | Accuracy | Một lớp vượt ngưỡng 95% áp đảo lớp còn lại |

### Lỗi Toàn vẹn Lược đồ (Schema Integrity)

| Mã lỗi | Mức nghiêm trọng tĩnh | Giải thích lỗi |
|--------|----------------------|----------------|
| `MISSING_COLUMN` | **CRITICAL** | Cột bắt buộc (theo DBML) không tồn tại |
| `PK_NULL` | **CRITICAL** | Khóa chính bị để trống (Gây sập Indexing) |
| `PK_DUPLICATE` | **CRITICAL** | Khóa chính trùng lặp (Gây hỏng định danh) |
| `ORPHAN_FOREIGN_KEY` | **CRITICAL** | Khóa ngoại dẫn tới bảng không tồn tại (Join sẽ thất bại) |
| `TYPE_MISMATCH` | **HIGH** | File CSV dùng dạng Text nhưng DBML bảo Integer |
| `UNIQUE_VIOLATION` | **HIGH** | Cột Unique bị trùng lặp |

---

## Phần 4: Narrative Guardrail & Allowed Set

Cơ chế phòng thủ (Defensive mechanism) áp dụng ở Layer 4 (`narrative.py`) để chống LLM bóp méo số liệu.

- **Allowed-Set (Tập giá trị an toàn):** Hệ thống tạo ra một mảng Set bằng cách lướt qua mọi số (Float/Int), mọi phần tử Text và ID (`finding_id`) từ JSON SSOT ban đầu.
- **Dung sai (Tolerance):** Số của LLM được coi là vượt rào nếu sai lệch > 1% so với Allowed-Set. (Ví dụ 99.8% trong Allowed-Set được phép làm tròn thành 100%).
- **Cơ chế Retry:** Báo cáo bị Fail Guardrail sẽ được trả về Agent với thông báo lỗi, bắt làm lại.

---

## Phần 5: Tính chất Escalation (Cộng gộp Bệnh lý)

`src/severity/compound.py` sẽ thực hiện một phương trình rủi ro: Nếu 1 cột dính > 1 lỗi.
*Công thức:* `Severity = Lỗi Nặng Nhất + Phụ Cấp số lượng lỗi phụ`.

Ví dụ: Cột `Income` có Outlier (`WARN`) nhưng lại bị Missing theo chuẩn MNAR (`HIGH`).
Hệ thống lấy mức cao nhất là `HIGH`, và cộng 1 bậc phụ cấp rủi ro thành `CRITICAL` và trả về `compound_severity`.
