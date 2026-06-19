# Giới thiệu Dự án: Auto Data-Profiling & Smart EDA Report Tool

## Mô tả Bài toán

### Bối cảnh

Trong bất kỳ dự án Data/AI nào, bước đầu tiên và tốn kém nhất luôn là **Exploratory Data Analysis (EDA)** — khám phá và đánh giá chất lượng dữ liệu thô. 

Tuy nhiên, quy trình EDA truyền thống đang gặp phải các vấn đề nghiêm trọng:
1. **Lặp lại và tốn thời gian:** Mỗi khi nhận một dataset mới (CSV, Excel, DB Dump), Data Engineer/Scientist phải viết code lặp đi lặp lại để kiểm tra: có bao nhiêu giá trị rỗng (missing), có dữ liệu dị biệt (outlier) không, kiểu dữ liệu có đồng nhất không.
2. **Thiếu chuẩn mực:** Mỗi chuyên gia đánh giá một kiểu, dựa trên kinh nghiệm cá nhân. Báo cáo tạo ra không có một thước đo chuẩn mực nào (Ví dụ: Dựa vào đâu để kết luận lỗi này là Nặng hay Nhẹ?).
3. **Kém trực quan cho Business User:** Các báo cáo thống kê với một rừng số liệu (Mean, Std, Skewness) rất khó hiểu với PM hoặc Business Analyst. Họ không biết "Tóm lại dữ liệu này đã dùng được chưa?".

### Giải pháp của Smart EDA

**Smart EDA** là công cụ **Tự động hóa toàn diện quy trình kiểm tra sức khỏe dữ liệu**. Nó đóng vai trò như một "Hội đồng Y khoa", tự động dò quét, chẩn đoán bệnh lý của dữ liệu và xuất ra một bệnh án trực quan, dễ hiểu.

> **Sứ mệnh sản phẩm:** Giải phóng 90% thời gian làm EDA thủ công. Chuyển đổi hàng vạn con số thống kê khô khan thành văn bản phân tích dễ hiểu (thông qua AI) nhưng phải đảm bảo tính chính xác tuyệt đối của số liệu.

---

## Các Điểm nổi bật Cốt lõi (Key Value Propositions)

### 1. Triết lý "Deterministic-First, LLM-Last"
Không giống các công cụ "Chat-with-Data" thông thường hay mắc lỗi ảo giác (Hallucination) do AI tự bịa số liệu. Smart EDA tách biệt quy trình:
- **Tính toán (Deterministic):** Do mã nguồn Python chạy bằng các thuật toán ML chuẩn xác (PyOD Ensemble, ydata-profiling, Isolation Forest).
- **Diễn giải (LLM):** LLM Multi-Agent chỉ làm nhiệm vụ viết văn bản giải thích.
- **Lưới bảo vệ (Guardrail):** Trước khi báo cáo đến tay người dùng, công cụ `narrative.py` sẽ chặn đứng mọi văn bản có chứa các con số do LLM tự bịa ra. Đảm bảo an toàn 100% cho số liệu.

### 2. Thang điểm Mức độ Nghiêm trọng (Severity Stack)
Thay vì chỉ liệt kê lỗi, hệ thống có khả năng tự động phân loại mức độ rủi ro (INFO, WARN, HIGH, CRITICAL).
Hệ thống thậm chí biết **Cộng dồn rủi ro (Escalation)**: Nếu một cột dính lỗi ngoại lệ (Outlier) đồng thời bị Khuyết dữ liệu có chủ đích (MNAR/MAR), hệ thống sẽ nâng mức cảnh báo của cột đó lên CRITICAL, chặn người dùng mang đi huấn luyện mô hình.

### 3. Giao diện Chẩn đoán 3 Tầng (3-Tier Diagnostic Layout)
Báo cáo HTML sinh ra không chỉ có text, mà cung cấp một giao diện chẩn đoán ngoại lệ (Outlier) chuyên nghiệp:
- **Tầng 1 (Box Plot):** Biểu đồ hộp chỉ ra phân phối chung.
- **Tầng 2 (Anomaly Score Bar):** Biểu đồ cột ngang trích xuất "Top các dòng bị điểm lỗi cao nhất" (Z-Score) có Tooltip giải thích.
- **Tầng 3 (Data Sample):** Bảng HTML bóc tách nguyên văn dữ liệu của các dòng bị nghi ngờ là Outlier, giúp Data Scientist đối chiếu chéo ngay trên web.

### 4. Phân tích Quan hệ Đa bảng (Multi-Table & Graph Engine)
Hỗ trợ nạp cấu trúc Database (DBML/SQL DDL). Hệ thống tự động phân tích:
- Ràng buộc Khóa Chính / Khóa Ngoại (PK/FK Integrity).
- Rò rỉ dữ liệu / Đa cộng tuyến (Data Leakage & Multicollinearity).
- Vẽ Sơ đồ Mạng lưới Bảng (Schema Relationship Graph).

---

## Kiến trúc Tổng quan (High-Level Architecture)

```text
┌─────────────────────────────────┐
│           ĐẦU VÀO               │
│  CSV / XLSX / Parquet / JSON    │
│  + DBML / SQL DDL (Tùy chọn)    │
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│     ĐỘNG CƠ TÍNH TOÁN (L1-L2)   │
│  (Không dùng AI, tính bằng code)│
│  - Thống kê Profiling           │
│  - Dò quét Ngoại lệ (PyOD)      │
│  - Đối chiếu Lược đồ Schema     │
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│     HỘI ĐỒNG Y KHOA (L2.5)      │
│  - Phân tích cơ chế Khuyết rỗng │
│  - Áp dụng Thang điểm phạt      │
│  - Ra Phán quyết (READY/WARN)   │
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│       MÔ HÌNH CHUẨN HÓA (L3)    │
│  Đóng gói Data Models Pydantic  │
│  Xuất ra JSON chuẩn DAMA-DMBOK  │
└────────────────┬────────────────┘
                 ▼
┌─────────────────────────────────┐
│       BÁO CÁO LLM & UI (L4)     │
│  - Multi-Agent AI viết báo cáo  │
│  - Dựng Báo cáo HTML trực quan  │
│  - Lưới chặn Ảo giác Guardrail  │
└─────────────────────────────────┘
```

---

## Hệ thống Đầu vào & Đầu ra

### 1. Đầu vào (Inputs)
- **Tệp dữ liệu:** `.csv`, `.xlsx`, `.parquet`, `.json`.
- **Tệp lược đồ (Tùy chọn):** `.dbml`, `.sql`.

### 2. Đầu ra (Outputs)
Nằm toàn bộ trong thư mục `output/`:
- **`report.html`**: Giao diện trình duyệt tương tác. Nơi chứa nhận xét AI, phán quyết tổng quan (READY/NOT_READY), và các biểu đồ chẩn đoán.
- **`data_quality_findings.json`**: Tập tin JSON tĩnh đóng gói mọi số liệu theo tiêu chuẩn quản trị dữ liệu (Data Governance), sẵn sàng để máy móc ở hệ thống khác đọc hiểu tự động.
- **Thư mục ảnh PNG**: Hình ảnh biểu đồ phân phối, biểu đồ Scatter Plot của Outlier, và Sơ đồ lưới dữ liệu (Graph).
