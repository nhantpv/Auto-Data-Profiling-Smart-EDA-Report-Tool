# Hướng dẫn Kỹ thuật Pipeline (Pipeline Guide)

Tài liệu này giải phẫu chi tiết cách dòng chảy dữ liệu (Data Flow) di chuyển qua các Layer trong Smart EDA Pipeline. Dành cho các kỹ sư muốn hiểu sâu cách hoạt động hoặc muốn đóng góp mã nguồn (thêm Engine, Chart hoặc Rule mới).

---

## Tổng quan Luồng Dữ liệu (Data Flow)

Ví dụ mô phỏng quá trình xử lý một tập dữ liệu đầu vào: `users.csv` (10.000 dòng, 5 cột).

```text
users.csv (10.000 dòng)
      │
      ▼
[Layer 0] csv_reader.py + sampling.py
      → DataFrame chuẩn hóa. Nếu file > Max RAM, áp dụng Reservoir Sampling.
      │
      ▼
[Layer 1] profiling_engine.py
      → Thu được profile: {'age': {'mean': 32, 'max': 200, 'n_missing': 100}}
      │
      ▼
[Layer 2a] anomaly_engine.py (PyOD: IForest + ECOD + LOF)
      → Tính Z-Score. Điểm dị thường: outlier_indices = [999], score = 3.5
      │
      ▼
[Layer 2b] schema_engine.py & graph_engine.py (Nếu có schema)
      → Kiểm tra PK/FK. Sinh sơ đồ quan hệ Relationship Graph.
      │
      ▼
[Layer 2.5] severity/ (Hội đồng Y khoa)
      → missingness.py: Cơ chế cột age là 'MAR'.
      → calibrator.py: Điểm 3.5 Z-score mức độ 'HIGH'.
      → compound.py: Cộng gộp lỗi (Missing + Outlier) → 'CRITICAL'.
      → aggregator.py: Tổng thể file bị dính CRITICAL → Verdict = 'NOT_READY'.
      │
      ▼
[Layer 3] ontology/
      → Đúc kết thành `data_quality_findings.json` chuẩn DMBOK.
      │
      ├─────────────────────────────────┐
      ▼                                 ▼
[Layer 3.5] visualizer.py         [Layer 4] l4_report.py (LLM Orchestrator)
      → Vẽ diagnostic charts            → Phân luồng cho Nx Analyst Agent.
        (Boxplot, Scatter, Bar)         → Đánh giá bởi Editor Agent.
                                        → Xác thực bởi narrative.py (Guardrail).
      │                                 │
      └─────────────┬───────────────────┘
                    ▼
[Layer 5] html_merger.py
      → Dựng report.html 3-tier giao diện, nhúng JSON và PNG.
```

---

## Phẫu thuật từng Bước Pipeline

### Bước 1: Layer 0 — Ingestion & Cấu trúc Dữ liệu

**File:** `src/ingestion/csv_reader.py`, `registry.py`, `sampling.py`

Hệ thống dùng mô hình Registry. Bạn không bao giờ đọc DataFrame thủ công.
```python
# Gọi csv_reader (wrapper của CSVReader trong readers.py)
df = load_csv("data.csv")
```
Quá trình `load_csv()` đã tự động đính kèm `DatasetMeta` (Metadata như `original_n`, `sample_n`) vào để đảm bảo các Engine sau biết dữ liệu này đang chạy thật hay chạy trên tập Sample.

### Bước 2: Layer 1 — Statistical Profiling

**File:** `src/engines/profiling_engine.py`

Khởi chạy thuật toán `ydata-profiling` ở mode config thấp nhất (disable biểu đồ phức tạp để tăng tốc). Lấy ra bộ số tĩnh (Univariate Stats). Output của bước này là bộ số `ColumnStats`.

### Bước 3: Layer 2 — Phân tích Cấu trúc (Multivariate)

Đây là nơi thực thi các logic hạng nặng:

**1. `anomaly_engine.py` (Outlier Detection):**
Bọc một Ensemble Model gồm:
- **IForest:** Isolation Forest, dùng cấu trúc dạng cây cách ly điểm dữ liệu.
- **ECOD:** Empirical Cumulative Distribution, tốt với dữ liệu bị lệch chuẩn xa.
- **LOF:** Local Outlier Factor, phát hiện ngoại lệ mật độ cục bộ.
Tính ra Max Z-score để chọn những điểm bất thường nhất. Mặc định `Z >= 3.0` là bị cắm cờ.

**2. `schema_engine.py` (Validation):**
Nếu user nạp kèm DBML, thực thi các phép kiểm Type, Nullability, Primary Key Unique, Foreign Key Orphan.

**3. `graph_engine.py` (Network Graph):**
Đọc cấu trúc DBML, dùng thư viện networkx giải quyết Graph Topology. Render ra sơ đồ mạng lưới thể hiện mũi tên khóa ngoại (1:N) hoặc các liên kết. Tách bạch khỏi module đồ họa thông thường để chạy tính toán Graph Logic.

### Bước 4: Layer 2.5 — Thang điểm Severity

**File:** `src/severity/`

Thay vì hard-code `if...else`, mọi mức độ lỗi chạy qua Stack 4 bước để ra phán quyết:
1. `missingness.py` kiểm tra bản chất rỗng (Little's Test) để cảnh báo MCAR hay MNAR.
2. `calibrator.py` lấy ngưỡng từ cấu hình để chấm severity cơ sở (VD: `WARN`).
3. `compound.py` kiểm tra xem một đối tượng có bị nhiều lỗi cấu thành không. Càng nhiều lỗi, bậc Severity tự đội lên `HIGH` hoặc `CRITICAL`.
4. `aggregator.py` quét toàn cục, tính Risk Score (thang 100) và hạ phán quyết `Verdict`.

### Bước 5: Layer 3 & 3.5 — Đóng gói Vật liệu (Artifacts)

- Tầng 3 (`src/ontology/`): Thu gom mọi Dataframe và Exception biến thành Pydantic Class. Export ra các file JSON như `data_quality_findings.json`.
- Tầng 3.5 (`src/engines/visualizer.py`): Nhận JSON để vẽ biểu đồ chẩn đoán Diagnostic Layout 3-Tier (Boxplot Outlier, Scatter Grid, Bar chart Top Score). Toàn bộ chart được dump ra thư mục `output/` định dạng PNG.

### Bước 6: Layer 4 — Văn bản (Multi-Agent Reporting)

**File:** `src/reporting/l4_report.py`, `src/guardrail/narrative.py`

Đây là nơi duy nhất LLM được triệu gọi:
1. Lọc bớt chỉ lấy những dòng bị lỗi `WARN` trở lên gửi cho AI.
2. `dispatcher.py` chia Batch các cột theo nhóm chức năng.
3. Kích hoạt song song `Analyst Agent` để giải thích thuật ngữ chuyên môn.
4. Tổng hợp bằng `Editor Agent`.
5. **Guardrail Check:** Module `narrative.py` lấy nguyên văn báo cáo LLM đâm vào Regex Regexes extract mảng Số Lượng. So khớp Số Lượng đó với `Allowed-Set` (tập số được quy định trong JSON của L3). Nếu bắt được LLM điền khống số liệu (Ảo giác), Pipeline bắt bỏ văn bản và viết lại (Retry).

### Bước 7: Layer 5 — Lắp ráp HTML

**File:** `src/reporting/html_merger.py`

Nhập tĩnh các `templates/*.html`. Script này dùng vòng lặp để chèn: văn bản Markdown đã dịch, link trỏ đến hình PNG, và chèn raw JSON vào một cục HTML siêu nhẹ. Cuối cùng trả về tay người dùng.

---

## Hướng dẫn Mở rộng (How to Extend)

### 1. Cách tạo Engine Kiểm tra mới

Ví dụ: Viết Engine kiểm tra email hợp lệ (`email_engine.py`)

1. Tạo file `src/engines/email_engine.py`.
2. Tạo hàm phân tích, nhận vào `df`, trả về List `AnomalyRecord` (import từ `ontology.models`).
3. Đăng ký loại lỗi mới vào `src/ontology/issue_catalog.py` (Thêm `INVALID_EMAIL_FORMAT`).
4. Bổ sung `INVALID_EMAIL_FORMAT` vào cấu hình ngưỡng `config/calibrator_table.json`.
5. Gọi `email_engine` vào luồng `run_pipeline.py`. (Không cần cấu hình LLM, hệ thống sẽ tự đọc JSON mới để sinh giải thích!).

### 2. Cách thiết lập Job Runtime (Background Pipeline)

Nếu gọi qua Web (FastAPI):
- Pipeline sẽ được `src/webapp/runtime.py` đưa vào Background Thread Pool.
- Quá trình chạy (Task ID, Process %) được đẩy về Browser thông qua cơ chế Server-Sent Events tại `src/webapp/progress_bus.py`.
