# Auto Data-Profiling & Smart EDA Report Tool

## Mô tả bài toán

### Bối cảnh

Trong các dự án Data/AI, giai đoạn đầu tiên luôn là **Exploratory Data Analysis (EDA)** — khám phá và đánh giá chất lượng dữ liệu thô. Đây là công việc lặp đi lặp lại ở mọi dự án:

1. Nhận dữ liệu thô (CSV, dump DB) từ khách hàng hoặc bộ phận nghiệp vụ.
2. Một Data Engineer/Scientist ngồi check thủ công: bao nhiêu cột, kiểu dữ liệu gì, missing bao nhiêu %, có outlier không, format có nhất quán không...
3. Viết báo cáo đánh giá (thường bằng tay, mỗi người viết một kiểu, không có chuẩn).
4. Gửi cho PM/khách hàng.

**Vấn đề:**
- **Tốn thời gian:** Mỗi dataset mới phải check lại từ đầu, công việc lặp lại.
- **Không nhất quán:** Mỗi người đánh giá theo tiêu chí riêng, không có metrics chuẩn.
- **Phụ thuộc chuyên gia:** Chỉ Senior Data Scientist mới có đủ kinh nghiệm để đưa ra nhận xét chất lượng dữ liệu tốt. Junior/PM nhìn số liệu thống kê nhưng không biết đánh giá thế nào.

### Giải pháp

Xây dựng một **công cụ tự động hóa** giai đoạn EDA ban đầu, giúp:
- Tự động phân tích và phát hiện các vấn đề chất lượng dữ liệu (data contamination).
- Đánh giá dữ liệu theo metrics chuẩn DAMA-DMBOK (Completeness, Validity, Accuracy,…).
- Dùng LLM đóng vai Senior Data Scientist để đưa ra nhận xét và gợi ý hướng cải thiện, **kèm Guardrail chống bịa số liệu**.

> **Bản chất sản phẩm:** Đây là công cụ **chẩn đoán** (diagnostic tool) — chỉ ra vấn đề và gợi ý hướng xử lý, **KHÔNG** tự động xử lý/clean dữ liệu.

---

## Pipeline tổng quan

```
┌──────────────────────┐
│       INPUT          │
│  CSV/XLSX/Parquet/   │
│  JSON + DBML/SQL DDL │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  DETERMINISTIC       │
│  ENGINES (L1 & L2)   │
│  • fg-data-profiling  │
│  • PyOD Ensemble      │
│  • Schema/Relation    │
│    Validator          │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│  SEVERITY STACK      │
│  (Layer 2.5)         │
│  • MCAR/MAR/MNAR      │
│  • Calibrator         │
│  • CompoundEscalator  │
│  • Aggregator         │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│   OUTPUT CHÍNH       │
│  3 file JSON chuẩn   │
│  (Pydantic + DAMA)   │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│      LLM LAYER       │
│  Multi-Agent          │
│  + Guardrail đối     │
│    chiếu số liệu     │
│  → Báo cáo Markdown  │
│  (text/JSON only)    │
└──────────────────────┘
```

---

## Input (Đầu vào)

### Data Files (file dữ liệu)

| Input | Mô tả | Ví dụ |
|-------|--------|-------|
| **CSV** | Text thuần, phân cách dấu phẩy. Format phổ biến nhất. | `sales_2024.csv` |
| **Excel (.xlsx)** | Bảng tính, có thể nhiều sheet. Rất phổ biến từ business users. | `report_q4.xlsx` |
| **Parquet** | Columnar binary format, có sẵn type info. Chuẩn data engineering. | `transactions.parquet` |
| **JSON/JSONL/NDJSON** | Object/list records hoặc JSON Lines; nested fields được flatten cơ bản. | `events.jsonl` |

> Tất cả data files đều được chuyển thành **pandas DataFrame** trước khi vào pipeline xử lý → engine phân tích không cần biết file gốc là CSV hay Parquet.

### Schema Files (file mô tả cấu trúc — tùy chọn)

| Input | Mô tả | Ví dụ |
|-------|--------|-------|
| **DBML** | Bản thiết kế cấu trúc database (bảng, cột, kiểu dữ liệu, quan hệ). | `schema.dbml` |
| **SQL DDL** | File `CREATE TABLE`, `PRIMARY KEY`, `FOREIGN KEY` phổ biến từ database. | `schema.sql` |

Khi có schema file, tool sẽ **đối chiếu** data thực tế với thiết kế: type mismatch, constraint violations, referential integrity. Nếu schema thiếu FK hoặc tên cột khác nhau nhưng cùng nghĩa, tool phải ghi rõ alias/relationship inference trong JSON để người dùng và LLM hiểu được.

> **DBML là gì?** Database Markup Language — ngôn ngữ mô tả cấu trúc database dưới dạng text, thường dùng với [dbdiagram.io](https://dbdiagram.io). Ví dụ:
> ```dbml
> Table users {
>   id integer [pk]
>   name varchar
>   email varchar [unique]
> }
> Table orders {
>   id integer [pk]
>   user_id integer [ref: > users.id]
>   total_amount decimal
> }
> ```
> Đọc file DBML, ta biết ngay database có bảng gì, cột nào, kiểu gì, quan hệ ra sao.

---

## Processing (Xử lý)

### ML Engine — Thuật toán ML truyền thống

Tool sử dụng các thuật toán Machine Learning cổ điển (không phải LLM) để phân tích data. Lý do dùng ML thay vì chỉ thống kê đơn giản: ML phát hiện được **anomaly phức tạp** mà thống kê cơ bản bỏ lỡ.

| Nhiệm vụ | Kỹ thuật ML có thể dùng |
|-----------|--------------------------|
| Phát hiện outliers | PyOD Ensemble: Isolation Forest + ECOD + LOF |
| Đánh giá phân phối dữ liệu | Statistical tests (Shapiro-Wilk, K-S test) |
| Phát hiện missing pattern | MCAR/MAR/MNAR classification (Little's test + Logistic Regression) |
| Phát hiện data bất thường | PyOD ensemble + normalized score threshold |
| Đánh giá mức độ nghiêm trọng | Severity Stack (Calibrator + CompoundEscalator + Aggregator) |
| Đánh giá chất lượng tổng thể | Dataset Verdict: READY / WARN / NOT_READY |

### Đánh giá theo Metrics

Tool tính toán và báo cáo các chỉ số chất lượng dữ liệu chuẩn:

- **Completeness:** Tỷ lệ dữ liệu không bị missing (%).
- **Uniqueness:** Tỷ lệ giá trị duy nhất / tổng số dòng.
- **Consistency:** Dữ liệu có format nhất quán không (ví dụ: "VN" vs "Vietnam" vs "vn").
- **Validity:** Dữ liệu có nằm trong miền giá trị hợp lệ không (ví dụ: tuổi < 0?).
- **Accuracy:** Dữ liệu có khớp với schema thiết kế không (nếu có DBML).
- **Timeliness:** Dữ liệu có cập nhật/tươi không (nếu có timestamp).

### Đối chiếu Schema (khi có DBML/SQL DDL)

Nếu người dùng cung cấp file schema, tool sẽ đối chiếu thêm:
- Data type thực tế vs thiết kế (cột `age` thiết kế là INTEGER nhưng data chứa chuỗi?).
- Constraint violations (cột `email` thiết kế là UNIQUE nhưng data có 12 giá trị trùng?).
- Quan hệ giữa bảng (foreign key có integrity không?).
- Missing table/column: bảng/cột nào được khai báo nhưng data không có.
- Alias/inference: cột `id_school` và `trường học` có thể được ghi là `COLUMN_ALIAS_INFERRED` nếu đủ bằng chứng.
- Missing FK metadata: quan hệ bảng có trong dữ liệu nhưng chưa khai báo trong schema được ghi là `inferred_fk` với confidence/evidence.

---

## Output (Đầu ra)

### Output 1 — File có cấu trúc (Core output)

File JSON chứa toàn bộ kết quả phân tích, được validate bởi Pydantic và tuân thủ chuẩn DAMA-DMBOK. Hệ thống xuất 3 file:
- `data_quality_findings.json` — báo cáo chất lượng dữ liệu
- `schema_evaluation_findings.json` — báo cáo đối chiếu schema
- `dataset_verdict.json` — phán quyết tổng thể (READY/WARN/NOT_READY)
- `summary_report.md` — báo cáo Markdown deterministic cho end user khi L4 chưa chạy hoặc làm fallback

Đây là output **chính** của tool, được thiết kế để:
- Hệ thống khác có thể đọc và xử lý tiếp (machine-readable).
- Làm input cho LLM ở bước tiếp theo.

```json
{
  "dataset": "sales_2024.csv",
  "summary": {
    "rows": 10000,
    "columns": 15
  },
  "columns": {
    "age": {
      "type": "Numeric",
      "n_missing": 520,
      "p_missing": 0.052,
      "missingness_mechanism": "MAR",
      "additional_metrics": {
        "mean": 35.5,
        "std": 12.3,
        "min": -5,
        "max": 150
      }
    }
  },
  "anomalies": [
    {
      "issue_type": "OUTLIER_ENSEMBLE",
      "severity": "HIGH",
      "dq_dimensions": ["Accuracy"],
      "ml_impact": ["training_bias"],
      "compound_severity": "CRITICAL",
      "confidence": 0.95,
      "affected_count": 23,
      "affected_percent": 0.0023,
      "top_10_samples": [
        {"row_index": 102, "age": 150, "_anomaly_score": 0.99}
      ],
      "full_anomalies_export_path": null
    }
  ]
}
```

Ví dụ phần schema JSON khi thiếu field hoặc thiếu FK metadata:

```json
{
  "integrity_errors": [
    {
      "error_type": "COLUMN_ALIAS_INFERRED",
      "affected_table": "students",
      "affected_column": "id_school",
      "missing_field_context": {
        "expected_column": "id_school",
        "candidate_aliases": ["trường học"],
        "is_intentional_missing": null,
        "intentional_missing_basis": "unknown; source owner confirmation required"
      }
    },
    {
      "error_type": "MISSING_RELATIONSHIP_METADATA",
      "relationship": {
        "child_table": "students",
        "child_column": "id_school",
        "parent_table": "schools",
        "parent_column": "id",
        "relationship_type": "inferred_fk",
        "status": "missing_from_schema",
        "confidence": 0.91
      }
    }
  ]
}
```

### Output 2 — LLM Narrative Report (với Guardrail chống Hallucination)

LLM đọc file JSON và raw top-k samples dạng số/chữ, sau đó viết nhận xét bằng ngôn ngữ tự nhiên. L4 **không nhận chart, không Vision, không sinh lệnh vẽ biểu đồ**. Mọi con số và tên cột trong báo cáo đều được **Guardrail (Allowed-Set + Tolerance)** kiểm tra đối chiếu với JSON gốc trước khi gửi cho người dùng:

> *"Dataset `sales_2024.csv` có chất lượng ở mức trung bình (72.5/100). Vấn đề nghiêm trọng nhất là cột `age` có 23 giá trị > 120, rất có thể là lỗi nhập liệu — nên kiểm tra lại nguồn dữ liệu hoặc xử lý bằng cách cap tại percentile 99. Cột `income` bị missing 23%, phân bố missing không ngẫu nhiên (MAR) — nên xem xét impute bằng median theo nhóm `job_category`..."*

### Output 3 — Biểu đồ trực quan (Bổ trợ, không thuộc L4)

Các chart minh họa cho các vấn đề phát hiện được:
- Missing value heatmap
- Distribution plots (histogram, boxplot)
- Outlier visualization
- Correlation matrix

Chart là artifact phụ trợ cho end user. Chart không được dùng làm nguồn số liệu cho LLM.

---

## Scope

### ✅ Trong scope (MVP)

**Input:**
1. Nhận file dữ liệu: CSV, Excel (.xlsx/.xls), Parquet, JSON/JSONL/NDJSON.
2. Nhận file DBML hoặc SQL DDL để đối chiếu data thực tế vs thiết kế.

**Processing:**
3. Tự động profiling (thống kê mô tả, phát hiện kiểu dữ liệu).
4. Phát hiện các điểm nhiễm data (missing, outliers, duplicates, inconsistencies).
5. Đối chiếu data vs schema (type mismatch, constraint violations, referential integrity).
6. Multi-table analysis (đánh giá quan hệ giữa nhiều bảng theo schema explicit hoặc inferred).
7. Đánh giá chất lượng data theo metrics chuẩn (completeness, validity...).
8. Ghi rõ các ngưỡng severity là heuristic v0 nếu chưa có benchmark calibration.

**Output:**
9. Xuất kết quả dạng JSON/YAML và `summary_report.md`.
10. LLM đọc JSON + raw samples dạng số/chữ → viết nhận xét + gợi ý cải thiện.
11. Biểu đồ trực quan chỉ là artifact bổ trợ, không phải input/output của L4.

### 🔜 Mở rộng sau

**v2 — Mở rộng ingestion/schema nâng cao:**
- JSON nested phức tạp hơn, cần flatten config rõ ràng.
- Nhiều sheet Excel trong một lần chạy.
- Lưu lịch sử đánh giá để so sánh chất lượng data theo thời gian.

**v3 — Kết nối trực tiếp:**
- DB Connection (PostgreSQL, MySQL, SQL Server...) — cần xử lý credentials, bảo mật, pagination.

### ❌ Ngoài scope

- Tự động clean/xử lý data (tool chỉ chẩn đoán, không chữa).
- Feature engineering / transformation.
- Train model ML.
- Real-time data streaming.

---

## Nguyên tắc kiến trúc

> **Nguyên tắc số 1: Thiết kế modular, tối ưu cho scale.**
> Toàn bộ project phải được thiết kế dạng module. Mỗi lớp (ingestion, analysis, reporting) hoạt động độc lập qua interface rõ ràng. Khi thêm format mới (JSON, DB connection...) ở v2/v3, chỉ cần thêm 1 module mới mà **không sửa pipeline hiện có**.

### Ví dụ: Ingestion Layer dạng Plugin

```
Ingestion Layer (Plugin Architecture)
├── CSVReader      →  pd.read_csv()      →  DataFrame
├── ExcelReader    →  pd.read_excel()    →  DataFrame
├── ParquetReader  →  pd.read_parquet()  →  DataFrame
├── [v2] JSONReader    →  flatten + parse  →  DataFrame
└── [v3] DBConnector   →  pd.read_sql()    →  DataFrame
         ↓
    Tất cả đều output DataFrame
         ↓
    Pipeline xử lý (chung cho mọi format)
```

Khi cần thêm format mới:
- Viết 1 class `NewFormatReader` implement interface `DataReader`.
- Đăng ký vào registry.
- **Không sửa bất kỳ code nào** trong pipeline phân tích, LLM, hay reporting.

Nguyên tắc này áp dụng cho **tất cả các lớp**, không chỉ ingestion:
- **Schema Parser:** DBML parser, SQL DDL parser (v2) — cùng interface.
- **Analysis Engine:** Mỗi loại phân tích (outlier, missing, distribution) là 1 module riêng.
- **Output Formatter:** JSON, YAML, PDF — mỗi format 1 module.

---

## Thông tin dự án

| Hạng mục | Chi tiết |
|----------|----------|
| **Tên dự án** | Auto Data-Profiling & Smart EDA Report Tool |
| **Số thành viên** | 3 người |
| **Phòng ban** | Phát triển Nền tảng (Platform Development) |
| **Mục tiêu** | Tự động hóa giai đoạn EDA ban đầu cho các dự án Data/AI |

---
