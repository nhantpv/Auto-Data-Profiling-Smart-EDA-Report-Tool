# Kiến trúc Hệ thống (System Architecture)

Tài liệu này mô tả chi tiết toàn bộ kiến trúc của Smart EDA — từ sơ đồ pipeline tổng quan đến chức năng cụ thể của từng thư mục, module và file trong source code. Tài liệu phản ánh chính xác cấu trúc thư mục `src/` hiện hành.

---

## Triết lý thiết kế: "Deterministic-First, LLM-Last"

Nguyên tắc cốt lõi xuyên suốt toàn bộ hệ thống:

> **Mọi kết quả tính toán, số liệu và phán quyết logic phải đến từ code Python (Deterministic).** Mô hình ngôn ngữ lớn (LLM) chỉ được sử dụng ở bước cuối cùng để *diễn giải* kết quả thành văn bản thân thiện với con người, không được phép *tạo ra* hay *thay đổi* kết quả.

Điều này đảm bảo:
- **Tính nhất quán:** Cùng một dataset luôn cho ra cùng một kết quả ở bất kỳ thời điểm nào.
- **Tính kiểm toán (Auditability):** Mọi con số trong báo cáo Markdown/HTML đều truy xuất ngược được về file JSON thô ban đầu.
- **Chống ảo giác (Anti-Hallucination):** Tích hợp Guardrail kiểm tra đối chiếu từng con số LLM viết ra với tập hợp dữ liệu gốc.

---

## Sơ đồ Pipeline Tổng quan

```text
┌─────────────────────────────────┐
│           ĐẦU VÀO               │
│  CSV / XLSX / Parquet / JSON    │
│  + DBML / SQL DDL (tùy chọn)    │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│    LAYER 0 — Ingestion          │
│  Đọc file → pandas DataFrame    │
│  csv_reader, base, registry...  │
│  src/ingestion/                 │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│    LAYER 1 — Profiling          │
│  ydata-profiling: thống kê      │
│  mô tả từng cột (univariate)    │
│  src/engines/profiling_engine.py│
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│    LAYER 2 — Phân tích sâu      │
│  • anomaly_engine: PyOD Ensemble│
│  • schema_engine: Type, FK, PK  │
│  • cross_table_engine           │
│  • graph_engine: Sơ đồ Schema   │
│  src/engines/                   │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│    LAYER 2.5 — Severity Stack   │
│  1. Missingness Detector (MCAR) │
│  2. Calibrator (Tra bảng điểm)  │
│  3. Compound Escalator          │
│  4. Aggregator → Verdict        │
│  src/severity/                  │
└────────────────┬────────────────┘
                 │
                 ▼
┌─────────────────────────────────┐
│    LAYER 3 — JSON Ontology      │
│  Đóng gói Pydantic + DMBOK      │
│  → JSON chuẩn (findings, schema)│
│  src/ontology/                  │
└────────────────┬────────────────┘
                 │
           ┌─────┴─────┐
           │           │
           ▼           ▼
┌──────────────┐  ┌─────────────────────────┐
│  LAYER 3.5   │  │    LAYER 4 — LLM        │
│  Visualizer  │  │  Multi-Agent + Guardrail│
│  Charts PNG  │  │  → l4_report.md         │
│  src/engines │  │  src/reporting &        │
│              │  │  src/guardrail/         │
└──────────────┘  └─────────────────────────┘
           │           │
           ▼           ▼
┌─────────────────────────────────┐
│    HTML Report Merger           │
│  Ghép báo cáo HTML (templates)  │
│  src/reporting/html_merger.py   │
└─────────────────────────────────┘
```

---

## Cấu trúc Thư mục Source (`src/`)

```text
src/
├── ingestion/          # Layer 0 — Đọc file dữ liệu đầu vào thành DataFrame
├── engines/            # Layer 1, 2, 3.5 — Các engine tính toán và vẽ biểu đồ
├── severity/           # Layer 2.5 — Chấm điểm nghiêm trọng (Severity Stack)
├── ontology/           # Layer 3 — Data models (Pydantic), lưu cấu trúc JSON
├── reporting/          # Layer 4 — Multi-Agent LLM & HTML rendering (HTML merger)
├── guardrail/          # Layer 4 — Xác thực LLM chống ảo giác (Narrative Guardrail)
├── evaluation/         # Công cụ tự đánh giá, kiểm chứng output pipeline
├── config/             # Cấu hình ngưỡng điểm, schema policy
└── webapp/             # Web API (FastAPI) để chạy qua giao diện trình duyệt
```

---

## Chi tiết Kiến trúc từng Module

### 1. `src/ingestion/` — Layer 0: Đọc dữ liệu

**Nhiệm vụ:** Trừu tượng hóa quá trình nạp dữ liệu. Nhận bất kỳ định dạng dữ liệu thô nào được hỗ trợ và trả về một đối tượng `pandas.DataFrame` cùng metadata đính kèm.

**Các file chính:**
- `base.py`: Định nghĩa Interface cốt lõi `DataReader`.
- `readers.py`: Cung cấp lớp cơ sở để đọc các định dạng (CSVReader, JSONReader, v.v.).
- `csv_reader.py`: Chuyên trách đọc định dạng CSV, cung cấp hàm wrapper `load_csv()` đóng gói metadata (nếu dùng sampling).
- `registry.py`: Map đuôi file (e.g. `.csv`, `.parquet`) tới reader class tương ứng.
- `sampling.py`: Quản lý lấy mẫu ngẫu nhiên (Reservoir sampling) đối với dataset lớn nhằm tối ưu bộ nhớ.
- `schema_reader.py`: Đọc cấu trúc quan hệ từ các file `.dbml` hoặc `.sql` (Data Definition Language).

---

### 2. `src/engines/` — Layer 1, 2 và 3.5: Các Engine Tính toán

Nơi thực thi mọi phép toán phân tích dữ liệu chuyên sâu.

- **`profiling_engine.py` (Layer 1):** Bọc thư viện `ydata-profiling` để tính toán thông số cơ bản từng cột (missing, distinct, min, max, mean, distribution).
- **`anomaly_engine.py` (Layer 2a):** Phát hiện dữ liệu ngoại lệ đa biến (Multivariate Outlier Detection) bằng **PyOD Ensemble** (tích hợp Isolation Forest, ECOD, LOF) rồi lấy Max Z-score để đưa ra cảnh báo độ lệch chuẩn.
- **`schema_engine.py` (Layer 2b):** Đối chiếu dữ liệu thực tế với schema. Kiểm tra ràng buộc Type (Data Type), Primary Key (PK), Foreign Key (FK) Integrity và Unique constraints.
- **`schema_gate.py`:** Phân tích quy mô dataset để ra quyết định dùng chế độ `quick_mode` (suy luận tự động) hay `precise_mode` khi phân tích schema đa bảng.
- **`cross_table_engine.py` (Layer 2c):** Phân tích liên bảng, phát hiện tương quan rò rỉ dữ liệu (Data Leakage) hoặc đa cộng tuyến (Multicollinearity).
- **`graph_engine.py` (Layer 2d):** Xử lý đồ thị quan hệ. Parse các file DBML/SQL để sinh ra Sơ đồ cấu trúc mạng lưới (Schema Relationship Network Graph), định tuyến các Node (bảng) và Edge (quan hệ khóa).
- **`visualizer.py` (Layer 3.5):** Engine sinh file ảnh PNG bổ trợ. Không chỉ vẽ histogram/missing heatmap, mà còn vẽ phân tích bất thường sâu (Diagnostic Chart), gồm:
  - Mini Box-Plot phân phối ngoại lệ.
  - Scatter Plot: Tọa độ ngoại lệ (Anomaly Scores).
  - Outlier Score Bar Chart: Top dòng có điểm số bất thường cao nhất.

---

### 3. `src/severity/` — Layer 2.5: Severity Stack (Chấm điểm mức độ)

Cơ chế 4 bước hoạt động tuần tự như một hội đồng thẩm định chất lượng để chấm điểm lỗi:

- **`missingness.py` (Bác sĩ 1):** Chẩn đoán lý do thiếu dữ liệu (Missingness Mechanism). Phân loại Missing Completely At Random (MCAR), Missing At Random (MAR), hoặc Missing Not At Random (MNAR) thông qua Logistic Regression.
- **`calibrator.py` (Bác sĩ 2):** Tra bảng ngưỡng từ file cấu hình. Ví dụ: Lỗi outlier với điểm số > 0.95 sẽ được ánh xạ thành mức `HIGH` hoặc `CRITICAL`.
- **`compound.py` (Bác sĩ 3):** Cộng gộp bệnh lý (Escalation). Nếu một cột vừa dính Outlier (`HIGH`) lại vừa bị rỗng dữ liệu `MNAR` (`HIGH`), nó sẽ bị đẩy mức độ nguy hiểm lên `CRITICAL`.
- **`aggregator.py` (Bác sĩ 4):** Phán quyết cuối cùng (Verdict). Quét toàn bộ hệ thống để kết luận tổng thể: `READY` (Dùng được), `WARN` (Chú ý rủi ro), hoặc `NOT_READY` (Không thể dùng).

---

### 4. `src/ontology/` — Layer 3: Data Models (Đóng gói JSON)

**Nhiệm vụ:** Biến toàn bộ kết quả thành JSON chuẩn hóa theo DAMA-DMBOK. Đóng vai trò là Single Source of Truth (SSOT).

- **`models.py`:** Chứa định nghĩa các class Pydantic (e.g., `DataQualityFindings`, `DatasetVerdict`, `SchemaEvaluationFindings`).
- **`findings_builder.py`:** Thu thập kết quả rải rác từ các engine và severity stack, sau đó đúc khuôn vào các class model.
- **`finding_registry.py`:** Sinh và theo dõi ID nội bộ (finding_id) cho từng lỗi, đảm bảo lỗi xuyên suốt pipeline.
- **`issue_catalog.py`:** Từ điển định nghĩa trước các loại lỗi (VD: `OUTLIER_ENSEMBLE`, `PK_DUPLICATE`), ánh xạ kèm `dq_dimensions` (Ví dụ: Accuracy, Completeness) và `ml_impact` (Hậu quả đối với Machine Learning).

---

### 5. `src/reporting/` — Layer 4: Xây dựng báo cáo

**Nhiệm vụ:** Sinh văn bản LLM, hoặc văn bản tĩnh, rồi nhúng tất cả vào báo cáo HTML.

- **`l4_report.py`:** Gọi Multi-Agent pipeline (nếu OpenAI được kích hoạt). Orchestrator này chạy luồng Analyst Agent đánh giá từng cột, và Editor Agent tổng hợp toàn bộ. Kết quả ra file `l4_report.md`.
- **`dispatcher.py`:** Điều phối và chia nhỏ tập hợp finding JSON thành từng batch công việc cho các LLM Agent xử lý.
- **`html_merger.py`:** Script cốt lõi dựng giao diện HTML. Đọc báo cáo Markdown, parse dữ liệu JSON từ ontology và file PNG từ visualizer. Nó nhúng CSS trực tiếp và dựng giao diện 3-Tier Diagnostic (Boxplot, Grid chart, Sample table) cho báo cáo.
- **`templates/` (Thư mục):** Chứa các file giao diện HTML thô (Skeleton) để `html_merger.py` điền dữ liệu vào.
- **`summary_renderer.py`:** Sinh báo cáo tĩnh nhanh (Summary Report) bằng Markdown cơ bản nếu không dùng LLM.
- **`sql_fix_generator.py`:** Gợi ý code SQL để xử lý dọn dẹp các lỗi Schema hoặc Missing data dựa trên ontology.

---

### 6. `src/guardrail/` — Lưới bảo vệ (Anti-Hallucination)

- **`narrative.py`:** Đảm nhận trọng trách cực kỳ quan trọng:
  1. **Text Guardrail (Kiểm tra văn bản):** Trích xuất mọi con số (number) và mọi Backtick Reference (text trong dấu nháy `) từ báo cáo LLM. Đối chiếu với tập `Allowed Set` tạo ra từ JSON gốc. Nếu LLM bịa số (ví dụ: JSON có 5 outlier nhưng LLM chém thành 50), lập tức đánh dấu lỗi (FAIL) và yêu cầu sinh lại.
  2. **Structured JSON Guardrail:** Khi Analyst Agent trả về một cấu trúc JSON chi tiết chứa trường `evidence_ref`, `narrative.py` sẽ đối soát trường này với `finding_id` ở L3. Nếu mã ID bịa đặt, thông tin đó sẽ bị loại bỏ khỏi báo cáo.

---

### 7. `src/evaluation/` — Đánh giá Benchmark

Bộ công cụ tự kiểm toán pipeline:

- **`artifact_contract.py`:** Kịch bản kiểm tra chuẩn tự động (Evaluator Contract). Kiểm chứng mọi file cấu trúc cần thiết (`data_quality_findings.json`, `l4_report.md`, charts) có được pipeline sinh ra đầy đủ hay không. Nếu pipeline thiếu file, Contract sẽ bị fail.
- **`schema_relationships.py`:** Script đánh giá và xác thực tính chính xác của các thuật toán nhận diện DB Relationship (Inference Schema).

---

### 8. `src/webapp/` — Web API

Giao diện để chạy Smart EDA qua trình duyệt web:

- **`app.py`:** Khởi tạo FastAPI Server. Cung cấp các endpoint REST API (upload, check status).
- **`runtime.py`:** Quản lý Background Task (Job Queue). Đảm bảo pipeline chạy ngầm mà không làm treo web server, hỗ trợ Worker Pool.
- **`progress_bus.py`:** Cơ chế Server-Sent Events (SSE). Bắn thông báo cập nhật thanh tiến trình chạy pipeline real-time về cho trình duyệt.
- **`static/` (Thư mục):** File tĩnh (CSS, JS) phục vụ riêng cho trang giao diện Upload Web.

---

## Nguyên tắc Kiến trúc Quan trọng

### 1. Plugin Architecture (Cắm và Chạy)
Mọi component đều tuân theo interface.
- Thêm định dạng dữ liệu mới? Tạo reader kế thừa `DataReader`, không cần sửa ingestion cốt lõi.
- Thêm biểu đồ mới? Viết hàm vào `visualizer.py` và cắm ID vào `html_merger.py`.

### 2. Tách biệt Metric và Constraint (Deequ Principle)
- **Metric:** Là số liệu khách quan (Ví dụ: "Tuổi cao nhất là 150"). Nằm trong `DataQualityFindings.columns`.
- **Constraint Violation:** Phán quyết lỗi dựa trên luật (Ví dụ: "Tuổi > 100 là ngoại lệ"). Nằm trong `DataQualityFindings.anomalies`.

### 3. Ưu tiên Machine-Readable JSON
Báo cáo HTML có thể thay đổi giao diện, nhưng bộ 3 file JSON (`data_quality_findings.json`, `schema_evaluation_findings.json`, `dataset_verdict.json`) là không thể phá vỡ, giữ nguyên vai trò SSOT cho bất kỳ hệ thống phân tích tích hợp nào khác (MLOps pipeline, Airflow, v.v.).
