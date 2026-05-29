# Architecture Review v2: Đối chiếu Đề bài Gốc

> **Đề bài gốc (từ hình ảnh):**
> *"Công cụ kết nối DB/CSV, tự động tính các chỉ số thống kê, phát hiện lỗi chất lượng dữ liệu (outliers, missing values) và dùng LLM đóng vai Senior Data Scientist để xuất báo cáo nhận xét chi tiết kèm biểu đồ trực quan."*

---

## Verdict: ⭐⭐⭐⭐ (4/5) — Kiến trúc vượt kỳ vọng đề bài, nhưng có 5 khe hổng kỹ thuật

---

## I. ĐỐI CHIẾU ĐỀ BÀI GỐC vs KIẾN TRÚC

| Yêu cầu đề bài | Đáp ứng? | Layer phụ trách |
|:---|:---:|:---|
| Kết nối DB/CSV | ✅ | L0 Ingestion (CSV Reader, mở rộng DB sau) |
| Tự động tính chỉ số thống kê | ✅ | L1 ydata-profiling |
| Phát hiện outliers | ✅ | L2 PyOD Ensemble |
| Phát hiện missing values | ✅ | L1 ydata-profiling (đếm + cảnh báo) |
| LLM đóng vai Senior Data Scientist | ✅ | L4 Multi-Agent |
| Xuất báo cáo nhận xét chi tiết | ✅ | L4 Master Agent → Markdown |
| Kèm biểu đồ trực quan | ✅ | L3.5 Dual Visualization |

> **Kết luận:** Kiến trúc hiện tại đáp ứng 100% đề bài gốc và vượt kỳ vọng (thêm DBML multi-table, Data Export CSV, Pydantic Contract).

---

## II. 5 KHE HỔNG KỸ THUẬT

### Khe hổng 1: `ydata-profiling` đã DEPRECATED 🔴
- **Vấn đề:** Đã đổi tên thành `fg-data-profiling`. Code demo hiện tại đã hiện DeprecationWarning.
- **Insight từ Research (dòng 561, 570):** Claude Pro xác nhận rename vào cuối 2025. API giữ nguyên.
- **Đề xuất:** Đổi tên trong docs & code → `fg-data-profiling` / `from data_profiling import ProfileReport`.
- **🟢 Không cần quyết định từ bạn** — Chỉ là đổi tên, không ảnh hưởng kiến trúc.

---

### Khe hổng 2: PyOD không xử lý Categorical Data 🟡
- **Vấn đề:** PyOD chỉ nhận dữ liệu số. Cột chữ (Giới tính, Thành phố) sẽ bị bỏ qua.
- **Insight từ Research (dòng 594):** PyOD yêu cầu Numpy arrays / Pandas DF dạng số. Research không đề cập giải pháp cho mixed-type.
- **Insight bổ sung từ web:** `alibi-detect` (dòng 595) có `TabularDrift` hỗ trợ mixed categorical/numerical, nhưng nó là drift detection, không phải outlier detection.

> [!IMPORTANT]
> **🔶 CẦN QUYẾT ĐỊNH TỪ BẠN — Chọn 1 trong 2 phương án:**

| | Phương án A: Chỉ chạy PyOD trên cột số | Phương án B: Thêm Preprocessing Pipeline |
|:--|:---|:---|
| **Mô tả** | Tách cột số → PyOD. Cột chữ → dựa vào cảnh báo của ydata (Imbalance, High Cardinality) | Encode cột chữ (Label/Target Encoding) → ghép vào ma trận số → PyOD quét toàn bộ |
| **Ưu điểm** | Đơn giản, nhanh triển khai, ít bug | Phát hiện rác đa biến giữa cột số VÀ cột chữ |
| **Nhược điểm** | Bỏ lọt rác liên quan đến cột chữ | Encoding có thể tạo ra kết quả sai lệch (LOF nhạy cảm với One-Hot). Phải chọn đúng kỹ thuật Encoding cho từng loại cột |
| **Khuyến nghị** | ✅ **Nên chọn cho v1** | Phù hợp cho v2 khi đã ổn định |

---

### Khe hổng 3: Logic Ensemble "cả 3 kết án" quá bảo thủ 🟡
- **Vấn đề:** Kiến trúc ghi *"Chỉ dòng nào bị cả 3 cùng kết án mới là rác"* → dễ bỏ sót rác thật.
- **Insight từ Research (dòng 893):** Paper ADBench (NeurIPS 2022) khuyến nghị dùng **Average Score** thay vì hard voting. PyOD có sẵn `pyod.models.combination` hỗ trợ việc này.

> [!IMPORTANT]
> **🔶 CẦN QUYẾT ĐỊNH TỪ BẠN — Chọn 1 trong 3 phương án:**

| | A: Cả 3 kết án (hiện tại) | B: Majority Vote (2/3) | C: Average Score + Threshold |
|:--|:---|:---|:---|
| **Mô tả** | Dòng phải bị cả IForest, ECOD, LOF cùng đánh dấu | Chỉ cần 2/3 thuật toán đánh dấu | Lấy trung bình điểm của 3 thuật toán, dòng nào vượt ngưỡng = rác |
| **Ưu điểm** | Rất ít báo nhầm (High Precision) | Cân bằng giữa bắt sót và báo nhầm | Linh hoạt nhất, được ADBench khuyến nghị |
| **Nhược điểm** | Bỏ sót rác thật (Low Recall) | Vẫn có thể bỏ sót nếu 1 thuật toán quá yếu | Phải tinh chỉnh ngưỡng (threshold) cho từng loại data |
| **Khuyến nghị** | Không nên | Tốt cho v1 | ✅ **Tối ưu nhất** — dùng `pyod.models.combination.average()` |

---

### Khe hổng 4: Thiếu Duplicate Detection trong Architecture 🟡
- **Vấn đề:** Đề bài gốc không nói rõ Duplicates, nhưng đây là lỗi chất lượng dữ liệu cơ bản nhất.
- **Insight từ Research (dòng 561):** `ydata-profiling` đã tính sẵn `n_duplicates` trong output JSON. Research (dòng 598) cũng đề cập `datasketch` cho near-duplicate detection.
- **Đề xuất:** Tận dụng luôn `n_duplicates` từ ydata, nhét vào JSON Spec. Không cần thêm thư viện mới.
- **🟢 Không cần quyết định từ bạn** — Chỉ cần thêm 1 trường vào Pydantic model.

---

### Khe hổng 5: TDD Plan chỉ cover 2/7 modules 🟢
- **Vấn đề:** Plan hiện tại chỉ có Pydantic Models + CSV Reader. Thiếu profiling_engine, anomaly_engine, schema_engine, findings_builder, visualizer.
- **Đề xuất:** Bổ sung sau khi Phase 1 xong. Không ảnh hưởng kiến trúc.
- **🟢 Không cần quyết định từ bạn** — Sẽ tạo thêm Plan files theo tiến độ.

---

## III. TỔNG HỢP HÀNH ĐỘNG

| # | Hành động | Ưu tiên | Cần quyết định? |
|:--|:---|:---:|:---:|
| 1 | Đổi `ydata-profiling` → `fg-data-profiling` trong docs & code | 🔴 Cao | Không |
| 2 | Chọn cách xử lý Categorical Data (Phương án A hoặc B) | 🟡 TB | **Có** |
| 3 | Chọn logic Ensemble (A, B hoặc C) | 🟡 TB | **Có** |
| 4 | Thêm `n_duplicates` vào JSON Spec từ output ydata | 🟡 TB | Không |
| 5 | Bổ sung TDD Plan cho các module còn lại | 🟢 Thấp | Không |
