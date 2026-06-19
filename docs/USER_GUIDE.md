# Hướng dẫn Sử dụng (User Guide)

Tài liệu này giải thích cách vận hành Smart EDA, các bước phân tích dữ liệu, và cách diễn giải giao diện báo cáo HTML được sinh ra. Báo cáo của Smart EDA tập trung mạnh vào tính trực quan, giúp bạn phát hiện ngoại lệ (outlier) và đánh giá chất lượng dữ liệu ngay lập tức.

---

## 1. Cách chạy hệ thống (Web UI)

Để có trải nghiệm tốt nhất, hãy sử dụng Web UI:

1. Mở Terminal và chạy lệnh: `python run_ui.py` (hoặc `uvicorn src.webapp.app:app --host 127.0.0.1 --port 8000`).
2. Truy cập trình duyệt tại địa chỉ: `http://127.0.0.1:8000`.
3. Giao diện có 2 tab chính ở bên trái:
   - **Single Table:** Phân tích 1 tệp độc lập (Ví dụ: `customers.csv`).
   - **Multi Table:** Phân tích một hệ cơ sở dữ liệu nhiều tệp (Ví dụ: `users.csv`, `orders.csv` và kèm theo file lược đồ `schema.dbml`).
4. Nhấn nút **Run Analysis**. Hệ thống sẽ chạy ngầm qua 4 Layer và cập nhật tiến độ (Progress Bar) liên tục trên màn hình.
5. Khi hoàn tất (100%), nút **View HTML Report** sẽ xuất hiện. Nhấp vào để xem kết quả.

---

## 2. Bố cục của Báo cáo HTML

Báo cáo HTML được chia thành 2 Tabs chính ở góc trên cùng:

- **Tab 1: Smart EDA Report (Báo cáo thông minh):** Nơi chứa phán quyết, đánh giá của AI (LLM), và giao diện phân tích ngoại lệ (Diagnostic 3-Tier Layout). Đây là báo cáo bạn cần đọc kỹ nhất.
- **Tab 2: YData Profiling Report:** Một bản nhúng thống kê mô tả chi tiết của thư viện `ydata-profiling`. Nơi bạn tra cứu số liệu thô (Mean, Max, Histogram) của từng cột.

---

## 3. Đọc hiểu Tab "Smart EDA Report"

Trong Tab này, hệ thống trình bày thông tin theo cấu trúc "Từ trên xuống dưới": Từ tổng quan bảng đến chi tiết từng lỗi.

### Bước 1: Xem Phán quyết Tổng thể (Verdict)

Bạn sẽ thấy ngay một khối thông báo màu sắc (Verdict) cho toàn bộ tập dữ liệu:

- ✅ **READY (Màu Xanh):** Dữ liệu an toàn, không có lỗi nguy hiểm. Có thể nạp vào Model Machine Learning ngay.
- ⚠️ **WARN (Màu Vàng):** Có rủi ro. Dữ liệu dính một số lỗi nặng (Ví dụ: Thiếu dữ liệu dạng MAR, hoặc có Outlier). Cần xử lý cẩn thận.
- ❌ **NOT_READY (Màu Đỏ):** Cấm sử dụng. Hệ thống phát hiện lỗi cấu trúc (Missing PK, Orphan FK). Nếu đưa vào chạy sẽ làm sập pipeline.

### Bước 2: Xem Phân tích Từng Bảng (Table-by-Table Analysis)

Mỗi bảng trong Dataset sẽ được đóng khung rõ ràng.

#### A. Tiêu đề và Tóm tắt Bảng
Nằm trên cùng của mỗi khung là thông tin bảng và đoạn văn giải thích do AI tóm tắt:

> 📦 **Bảng: Invoice**  
> 🌟 *Bảng này chứa thông tin về hóa đơn, bao gồm các trường như mã hóa đơn, địa chỉ thanh toán và ngày hóa đơn.*

#### B. Cụm Phân tích Ngoại lệ (Outlier Diagnostic Section)
Ngay dưới đoạn mô tả bảng là Cụm Phân tích Outlier. Đây là khu vực tập trung hiển thị các dòng dữ liệu dị biệt (được chấm điểm Z-Score bởi PyOD Ensemble).

Cụm này tuân theo **Giao diện 3 Cấp độ (3-Tier Layout)** để bạn có cái nhìn từ tổng quan đến chi tiết:

1. **Biểu đồ Box Plot (Biểu đồ hộp):** Hiển thị phân phối tổng thể. Những điểm nằm chót vót ngoài râu hộp là các Outlier. Bạn sẽ có cái nhìn trực quan xem dữ liệu đang lệch về phía nào.
2. **Biểu đồ Anomaly Score Bar Chart:** Biểu đồ cột ngang hiển thị "Điểm số dị biệt". 
   - Biểu đồ này xếp hạng các dòng dữ liệu bị lỗi nặng nhất.
   - Khi bạn di chuột (Hover) vào các thanh Bar, một **Tooltip** sẽ hiện ra cho biết chính xác điểm Z-Score từ PyOD (Ví dụ: Score = 4.2). Điểm càng cao, dòng đó càng vô lý.
3. **Data Sample Table (Bảng HTML 10 dòng mẫu):** Nằm cuối cụm Outlier. Đây là bảng trích xuất nguyên văn dữ liệu của top 10 dòng bị điểm Outlier cao nhất. Nhìn vào đây, Data Analyst có thể biết ngay tại sao dòng đó bị coi là lỗi (Ví dụ: Tuổi = 150).

#### C. Chi tiết Lỗi Từng Cột (Column-Level Findings)

Bên dưới Cụm Outlier, hệ thống liệt kê các lỗi chi tiết của từng cột (nếu có).

- **[CRITICAL] / [HIGH] / [WARN]:** Mức độ nguy hiểm của lỗi.
- **Vấn đề:** Ví dụ: "Cột Age bị missing 25% dạng MAR".
- **Hệ quả ML (ML Consequence):** AI sẽ giải thích nếu giữ nguyên cột này thì mô hình AI (như Random Forest hay Linear Regression) sẽ bị học sai như thế nào.
- **Gợi ý xử lý (Suggested Fix):** Các phương pháp Imputation hoặc SQL Script gợi ý để làm sạch.

---

## 4. Báo cáo Đa Bảng (Multi-Table & Schema Analysis)

Nếu bạn chạy ở chế độ Multi-Table (kèm file `.dbml`), sẽ xuất hiện thêm các phần:

1. **Schema Relationship Network Graph:** Một sơ đồ mạng lưới với các Nodes (Bảng) và Edges (Đường nối Khóa ngoại). 
   - Đường màu Xanh = Quan hệ FK toàn vẹn.
   - Đường màu Đỏ đứt nét = Có dữ liệu rác mồ côi (Orphan Foreign Keys).
2. **Lỗi Schema (Integrity Errors):** Hệ thống chỉ rõ dòng nào trỏ đến Parent PK không tồn tại.
3. **Cross-Table Correlations:** Bảng xếp hạng tương quan chéo giữa 2 bảng. Cảnh báo rò rỉ dữ liệu (Data Leakage) nếu cột ở bảng này có tương quan bất thường với cột ở bảng kia.

---

## 5. Tích hợp Máy Móc (Đọc file JSON)

Nếu bạn là Data Engineer muốn lấy kết quả tích hợp vào Airflow hoặc MLOps Pipeline, đừng đọc HTML. Hãy truy xuất kết quả tĩnh từ thư mục `output/`:

- **`dataset_verdict.json`:** Chỉ chứa chữ `READY` / `WARN` / `NOT_READY` để bạn làm điều kiện IF/ELSE dừng luồng CI/CD.
- **`data_quality_findings.json`:** Toàn bộ thông số % lỗi, danh sách `finding_id`. Dữ liệu này tuân chuẩn DMBOK.
- **`schema_evaluation_findings.json`:** Chứa danh sách các ràng buộc DBML bị vi phạm.
