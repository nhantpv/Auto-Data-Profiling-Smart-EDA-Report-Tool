# Smart EDA — Công cụ Tự động Phân tích & Báo cáo Chất lượng Dữ liệu

> Công cụ chẩn đoán chất lượng dữ liệu tự động: profiling, phát hiện anomaly, đánh giá mức độ nghiêm trọng và sinh báo cáo EDA toàn diện — có tùy chọn narrative bằng LLM đóng vai "Senior Data Scientist".

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115%2B-green)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Tại sao công cụ này tồn tại?

Trong mọi dự án Data/AI, giai đoạn đầu tiên luôn là **Exploratory Data Analysis (EDA)** — một công việc thủ công, lặp đi lặp lại và phụ thuộc vào kinh nghiệm chuyên gia. Một data engineer thường phải dành hàng giờ để kiểm tra từng dataset mới bằng tay, viết báo cáo không theo chuẩn nào, mỗi người một kiểu.

**Smart EDA tự động hóa bước đầu tiên đó.** Công cụ phát hiện vấn đề chất lượng dữ liệu bằng các thuật toán ML cổ điển, chấm điểm mức độ nghiêm trọng theo chuẩn DAMA-DMBOK, và (tùy chọn) dùng LLM để viết phần nhận xét — với cơ chế guardrail tích hợp ngăn LLM bịa số liệu.

> **Đây là công cụ chẩn đoán, không phải công cụ làm sạch dữ liệu.** Nó chỉ ra *vấn đề gì* và *tại sao ảnh hưởng đến ML* — không tự động clean data.

---

## Bắt đầu nhanh (Quick Start)

**1. Cài đặt môi trường:**

```bash
python3.11 -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
.venv\Scripts\activate

pip install -e ".[dev]"
```

**2. Sao chép file cấu hình:**

```bash
cp .env.example .env
```

**3. Chạy ứng dụng web:**

```bash
uvicorn webapp.app:app --host 127.0.0.1 --port 8000
```

Mở trình duyệt tại `http://127.0.0.1:8000` — các dataset mẫu có sẵn ở panel bên trái.

---

## Cài đặt chi tiết

**Yêu cầu:**
- Python 3.11 trở lên
- pip

```bash
# Clone repository
git clone <repo-url>
cd Auto-Data-Profiling-Smart-EDA-Report-Tool

# Tạo và kích hoạt virtual environment
python3.11 -m venv .venv
source .venv/bin/activate   # hoặc .venv\Scripts\activate trên Windows

# Cài đặt project + dev dependencies
pip install -e ".[dev]"

# Cấu hình môi trường
cp .env.example .env
# Chỉnh sửa .env theo nhu cầu (API key, giới hạn upload, v.v.)
```

---

## Cách sử dụng

### Ứng dụng Web (Khuyến nghị)

```bash
uvicorn webapp.app:app --host 127.0.0.1 --port 8000
```

Upload file dữ liệu qua giao diện trình duyệt. Hệ thống xử lý dưới dạng background job — bạn có thể theo dõi tiến trình theo thời gian thực qua Server-Sent Events.

### Command Line

**Phân tích một bảng:**

```bash
python run_pipeline.py tests/fixtures/outliers_realistic.csv output
```

**Có schema validation (DBML hoặc SQL DDL):**

```bash
python run_pipeline.py tests/fixtures/schema_bad.csv output tests/fixtures/schema_bad.dbml
```

**Đa bảng với schema tường minh:**

```bash
python run_pipeline.py \
  --multi tests/fixtures/multi/users.csv tests/fixtures/multi/orders.csv \
  --schema tests/fixtures/multi/shop.dbml \
  --out output
```

**Đa bảng — tự suy ra schema (không cần DBML):**

```bash
python run_pipeline.py \
  --multi examples/sample_datasets/school_multi_relations/schools.csv \
         examples/sample_datasets/school_multi_relations/classes.csv \
         examples/sample_datasets/school_multi_relations/students.csv \
  --out output
```

### Định dạng đầu vào được hỗ trợ

| Loại | Định dạng |
|------|-----------|
| File dữ liệu | `.csv`, `.xlsx`, `.xls`, `.parquet`, `.json`, `.jsonl`, `.ndjson` |
| File schema | `.dbml`, `.sql` |

---

## File đầu ra

Sau khi chạy pipeline, bạn sẽ thấy các file này trong thư mục output:

| File | Mô tả |
|------|-------|
| `data_quality_findings.json` | Phân tích chất lượng đầy đủ — thống kê từng cột, anomalies, điểm severity |
| `schema_evaluation_findings.json` | Kết quả đối chiếu schema (chỉ có khi dùng schema/multi-table mode) |
| `dataset_verdict.json` | Phán quyết cuối cùng: `READY`, `WARN`, hoặc `NOT_READY` |
| `summary_report.md` | Báo cáo Markdown tổng hợp (không cần LLM) |
| `l4_report.md` | Báo cáo narrative của LLM (khi bật L4 provider) |
| `guardrail_report.json` | Kết quả kiểm tra hallucination từ module guardrail |
| `*__diagnostic_*.png` | Biểu đồ chẩn đoán outlier (khi có) |
| `*__outlier_rows.csv` | Export đầy đủ các dòng outlier |
| `*__duplicate_rows.csv` | Export đầy đủ các dòng trùng lặp |

Trong chế độ đa bảng, `data_quality_findings.json` dùng schema `multi_table_data_quality_v1` — một findings payload cho từng bảng, cộng thêm tổng hợp cross-table.

---

## Cấu hình

Sao chép `.env.example` thành `.env` và điều chỉnh:

| Biến | Mặc định | Mô tả |
|------|----------|-------|
| `SMART_EDA_L4_PROVIDER` | `deterministic` | Chế độ L4: `deterministic` (không LLM) hoặc `openai` |
| `OPENAI_API_KEY` | *(trống)* | Bắt buộc khi `SMART_EDA_L4_PROVIDER=openai` |
| `SMART_EDA_L4_ANALYST_MODEL` | `gpt-4o-mini` | Model LLM cho Analyst agent |
| `SMART_EDA_L4_EDITOR_MODEL` | `gpt-4o` | Model LLM cho Editor agent |
| `SMART_EDA_L4_API_MODE` | `chat_completions` | API mode: `chat_completions` hoặc `responses` |
| `SMART_EDA_MAX_UPLOAD_MB` | `100` | Giới hạn kích thước file upload |
| `SMART_EDA_MAX_MULTI_FILES` | `10` | Số file tối đa trong chế độ đa bảng |
| `SMART_EDA_JOB_WORKERS` | `2` | Số background worker |
| `SMART_EDA_ENABLE_GUARDRAIL` | `true` | Bật/tắt guardrail kiểm tra hallucination |

Ngưỡng và từ đồng nghĩa dùng cho schema inference có thể chỉnh trong `config/schema_inference_policy.json` mà không cần sửa source code.

---

## Dataset mẫu

Các dataset mẫu có sẵn trong `examples/sample_datasets/`:

| Dataset | Mô tả |
|---------|-------|
| `students_csv_dirty` | CSV có lỗi PK, missing value, sai kiểu dữ liệu, cột thừa, outlier |
| `orders_json_dirty` | JSON có bản ghi không hợp lệ và schema drift |
| `school_multi_relations` | Bộ CSV đa bảng có FK mồ côi, thiếu bảng, PK trùng, alias column |
| `school_multi_infer_schema` | Bộ CSV đa bảng không có DBML/DDL — schema và quan hệ được suy ra tự động |

Ngoài ra còn có các ví dụ thực tế (Chinook, Northwind, DVD Rental, Olist) trong các thư mục con của `examples/`.

---

## Chạy kiểm thử

```bash
pytest tests/ -q
```

**Script đánh giá:**

```bash
# Benchmark độ chính xác suy luận quan hệ schema
python scripts/evaluate_schema_relationships.py

# Kiểm tra artifact đầu ra của pipeline
python scripts/evaluate_pipeline_artifacts.py
```

---

## Cấu trúc dự án

```
.
├── run_pipeline.py          # Entry point CLI
├── run_ui.py                # Shortcut chạy web UI
├── pyproject.toml           # Metadata và dependencies
├── config/                  # Ngưỡng và policy có thể tinh chỉnh
│   ├── calibrator_table.json
│   └── schema_inference_policy.json
├── src/                     # Thư viện lõi
│   ├── ingestion/           # Đọc file (CSV, Excel, Parquet, JSON)
│   ├── engines/             # Các engine phân tích (profiling, anomaly, schema, cross-table)
│   ├── severity/            # Severity Stack (calibrator, compound, aggregator)
│   ├── ontology/            # Pydantic data models và finding registry
│   ├── reporting/           # HTML report merger và L4 LLM report
│   ├── guardrail/           # Kiểm tra hallucination
│   ├── evaluation/          # Benchmark và đánh giá
│   ├── config/              # Config loader nội bộ
│   └── webapp/              # FastAPI web application
├── examples/                # Dataset mẫu
├── tests/                   # Pytest test suite
├── scripts/                 # Script đánh giá và tiện ích
├── docs/                    # Tài liệu dự án
└── runtime/                 # Output job lúc chạy (gitignored)
```

---

## Tài liệu

| Tài liệu | Mô tả |
|----------|-------|
| [SETUP.md](docs/SETUP.md) | Hướng dẫn cài đặt môi trường chi tiết |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | Kiến trúc hệ thống và sơ đồ các module |
| [PIPELINE_GUIDE.md](docs/PIPELINE_GUIDE.md) | Chi tiết pipeline và hướng dẫn mở rộng |
| [USER_GUIDE.md](docs/USER_GUIDE.md) | Cách đọc và diễn giải báo cáo EDA |
| [DATA_DICTIONARY.md](docs/DATA_DICTIONARY.md) | Từ điển khái niệm, data model và catalog lỗi |

---

## Giấy phép

MIT
