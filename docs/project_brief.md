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
- Đánh giá dữ liệu theo các metrics chuẩn.
- Dùng LLM đóng vai Senior Data Scientist để đưa ra nhận xét và gợi ý hướng cải thiện.

> **Bản chất sản phẩm:** Đây là công cụ **chẩn đoán** (diagnostic tool) — chỉ ra vấn đề và gợi ý hướng xử lý, **KHÔNG** tự động xử lý/clean dữ liệu.

---

## Pipeline tổng quan

```
┌──────────────────────┐
│       INPUT          │
│  CSV, DBML, Schema   │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│    ML ENGINE         │
│  (Thuật toán ML      │
│   truyền thống)      │
│                      │
│  • Phát hiện điểm    │
│    nhiễm data        │
│  • Đánh giá data     │
│    theo metrics      │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│   OUTPUT CHÍNH       │
│  File có cấu trúc    │
│  (JSON / YAML)       │
└──────────┬───────────┘
           ▼
┌──────────────────────┐
│      LLM LAYER       │
│  Đọc JSON kết quả    │
│  → Suggest hướng     │
│    cải thiện data     │
│  → Kèm biểu đồ      │
│    trực quan          │
└──────────────────────┘
```

---

## Input (Đầu vào)

### Bắt buộc

| Input | Mô tả | Ví dụ |
|-------|--------|-------|
| **File CSV** | Dữ liệu thô cần đánh giá. Có thể là 1 hoặc nhiều file. | `sales_2024.csv`, `customers.csv` |

### Tùy chọn (Optional)

| Input | Mô tả | Ví dụ |
|-------|--------|-------|
| **File DBML** | Bản thiết kế cấu trúc database (bảng, cột, kiểu dữ liệu, quan hệ). Dùng để đối chiếu data thực tế với schema thiết kế. | `schema.dbml` |
| **DB Schema** | Cấu trúc schema thực tế từ database (CREATE TABLE statements hoặc metadata). | Kết nối trực tiếp DB |

> **DBML là gì?** Database Markup Language — một ngôn ngữ mô tả cấu trúc database dưới dạng text, thường dùng với [dbdiagram.io](https://dbdiagram.io). Ví dụ:
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
| Phát hiện outliers | Isolation Forest, LOF, Z-score, IQR |
| Đánh giá phân phối dữ liệu | Statistical tests (Shapiro-Wilk, K-S test) |
| Phát hiện missing pattern | Pattern mining, MCAR/MAR/MNAR classification |
| Phát hiện data bất thường | DBSCAN clustering, One-class SVM |
| Đánh giá chất lượng tổng thể | Composite quality score dựa trên nhiều metrics |

### Đánh giá theo Metrics

Tool tính toán và báo cáo các chỉ số chất lượng dữ liệu chuẩn:

- **Completeness:** Tỷ lệ dữ liệu không bị missing (%).
- **Uniqueness:** Tỷ lệ giá trị duy nhất / tổng số dòng.
- **Consistency:** Dữ liệu có format nhất quán không (ví dụ: "VN" vs "Vietnam" vs "vn").
- **Validity:** Dữ liệu có nằm trong miền giá trị hợp lệ không (ví dụ: tuổi < 0?).
- **Accuracy:** Dữ liệu có khớp với schema thiết kế không (nếu có DBML).
- **Timeliness:** Dữ liệu có cập nhật/tươi không (nếu có timestamp).

### Đối chiếu Schema (khi có DBML)

Nếu người dùng cung cấp file DBML, tool sẽ đối chiếu thêm:
- Data type thực tế vs thiết kế (cột `age` thiết kế là INTEGER nhưng data chứa chuỗi?).
- Constraint violations (cột `email` thiết kế là UNIQUE nhưng data có 12 giá trị trùng?).
- Quan hệ giữa bảng (foreign key có integrity không?).

---

## Output (Đầu ra)

### Output 1 — File có cấu trúc (Core output)

File JSON hoặc YAML chứa toàn bộ kết quả phân tích. Đây là output **chính** của tool, được thiết kế để:
- Hệ thống khác có thể đọc và xử lý tiếp (machine-readable).
- Làm input cho LLM ở bước tiếp theo.

```json
{
  "dataset": "sales_2024.csv",
  "summary": {
    "rows": 10000,
    "columns": 15,
    "overall_quality_score": 72.5
  },
  "columns": {
    "age": {
      "type": "numeric",
      "missing_pct": 5.2,
      "outliers_count": 23,
      "outlier_method": "IQR",
      "distribution": "right-skewed",
      "quality_flags": ["HAS_OUTLIERS", "MODERATE_MISSING"]
    }
  },
  "contamination_points": [
    {
      "column": "age",
      "issue": "OUTLIER",
      "severity": "HIGH",
      "detail": "23 values > 120, likely data entry errors",
      "affected_rows": [102, 455, 789]
    }
  ]
}
```

### Output 2 — LLM Narrative Report

LLM đọc file JSON ở trên và viết nhận xét bằng ngôn ngữ tự nhiên, đóng vai Senior Data Scientist:

> *"Dataset `sales_2024.csv` có chất lượng ở mức trung bình (72.5/100). Vấn đề nghiêm trọng nhất là cột `age` có 23 giá trị > 120, rất có thể là lỗi nhập liệu — nên kiểm tra lại nguồn dữ liệu hoặc xử lý bằng cách cap tại percentile 99. Cột `income` bị missing 23%, phân bố missing không ngẫu nhiên (MAR) — nên xem xét impute bằng median theo nhóm `job_category`..."*

### Output 3 — Biểu đồ trực quan (Bổ trợ)

Các chart minh họa cho các vấn đề phát hiện được:
- Missing value heatmap
- Distribution plots (histogram, boxplot)
- Outlier visualization
- Correlation matrix

---

## Scope

### ✅ Trong scope (MVP)

1. Nhận file CSV làm input (1 hoặc nhiều file).
2. Nhận file DBML / DB Schema để đối chiếu data thực tế vs thiết kế.
3. Tự động profiling (thống kê mô tả, phát hiện kiểu dữ liệu).
4. Phát hiện các điểm nhiễm data (missing, outliers, duplicates, inconsistencies).
5. Đối chiếu data vs schema (type mismatch, constraint violations, referential integrity).
6. Multi-table analysis (đánh giá quan hệ giữa nhiều bảng theo DBML).
7. Đánh giá chất lượng data theo metrics chuẩn (completeness, validity...).
8. Xuất kết quả dạng JSON/YAML.
9. LLM đọc JSON → viết nhận xét + gợi ý cải thiện.
10. Kèm biểu đồ trực quan minh họa.

### 🔜 Mở rộng sau (v2+)

- Kết nối trực tiếp database (PostgreSQL, MySQL...).
- Lưu lịch sử đánh giá để so sánh chất lượng data theo thời gian.

### ❌ Ngoài scope

- Tự động clean/xử lý data (tool chỉ chẩn đoán, không chữa).
- Feature engineering / transformation.
- Train model ML.
- Real-time data streaming.

---

## Thông tin dự án

| Hạng mục | Chi tiết |
|----------|----------|
| **Tên dự án** | Auto Data-Profiling & Smart EDA Report Tool |
| **Số thành viên** | 3 người |
| **Phòng ban** | Phát triển Nền tảng (Platform Development) |
| **Mục tiêu** | Tự động hóa giai đoạn EDA ban đầu cho các dự án Data/AI |

---
