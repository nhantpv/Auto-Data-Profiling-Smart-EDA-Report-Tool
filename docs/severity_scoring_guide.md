# Hướng dẫn Chi tiết Quy trình Đánh giá & Chấm điểm Chất lượng Dữ liệu

Tài liệu này giải thích logic hoạt động của bộ máy **Đánh giá mức độ nghiêm trọng (Severity Stack - `src/severity`)**. Nội dung được bám sát 100% theo các thuật toán và logic đang chạy trong codebase (`calibrator.py`, `compound.py`, `aggregator.py`).

---

## Lời mở đầu: "Bệnh án" của dữ liệu là gì?

Khi bạn nạp một tệp dữ liệu vào hệ thống, các engine dò quét (`anomaly_engine`, `profiling_engine`) sẽ tìm ra rất nhiều điểm bất thường (ví dụ: ô trống, dữ liệu bị trùng, dữ liệu lệch chuẩn). 

Tuy nhiên, không phải lỗi nào cũng nguy hiểm như nhau. Bộ máy `src/severity` đóng vai trò như một **Hội đồng y khoa**. Nhiệm vụ của nó không phải là tìm ra lỗi, mà là **đánh giá xem các lỗi đó nặng hay nhẹ, ảnh hưởng thế nào đến việc sử dụng dữ liệu, và cuối cùng ra phán quyết tệp dữ liệu đó đạt hay hỏng.**

---

## PHẦN 1: Bốn mức độ nghiêm trọng của lỗi

Hệ thống phân chia mọi lỗi tìm thấy thành 4 cấp độ từ nhẹ đến nặng:

1. **Cấp 1 - THÔNG TIN (`INFO`):** Trọng số rủi ro = 0. Mức nhẹ nhất. Chỉ mang tính chất thông báo (Ví dụ: cột bị thừa so với thiết kế ban đầu).
2. **Cấp 2 - CẢNH BÁO (`WARN`):** Trọng số rủi ro = 1. Có vấn đề, nhưng vẫn dùng được nếu cẩn thận.
3. **Cấp 3 - CAO (`HIGH`):** Trọng số rủi ro = 5. Lỗi nặng, bắt buộc phải lọc bỏ hoặc impute phức tạp nếu không muốn mô hình Machine Learning học sai phân phối.
4. **Cấp 4 - NGUY KỊCH (`CRITICAL`):** Trọng số rủi ro = 20. Lỗi vi phạm logic cơ bản (Ví dụ: PK rỗng). Dữ liệu hoàn toàn không thể đưa vào sử dụng.

---

## PHẦN 2: Bảng tra cứu mức phạt ban đầu (Calibrator)

`src/severity/calibrator.py` chịu trách nhiệm chấm điểm sơ cấp (Base Severity) dựa vào file cấu hình `config/calibrator_table.json`.

### Nhóm A: Lỗi Chất lượng Dữ liệu (Dò quét trực tiếp từ file)

| Tên lỗi | Mô tả | Mức phạt ban đầu mặc định |
| :--- | :--- | :--- |
| **`MISSINGNESS`** | Khuyết dữ liệu (ô bị rỗng) | • Dưới 5%: `INFO`<br>• Từ 5% đến 20%: `WARN`<br>• Từ 20% đến 50%: `HIGH`<br>• > 50%: `CRITICAL` |
| **`OUTLIER_ENSEMBLE`** | Dòng dữ liệu dị biệt đa biến (PyOD Z-Score > 3.0) | • Dưới 5% dòng bị dị biệt: `WARN`<br>• Từ 5% trở lên: `HIGH` |
| **`DUPLICATE`** | Dòng dữ liệu trùng lặp | • Dưới 5% dòng trùng: `WARN`<br>• Từ 5% trở lên: `HIGH` |
| **`CONSTANT_COLUMN`** | Cột hằng số (Chỉ chứa đúng 1 giá trị duy nhất) | • Cố định: `HIGH` |
| **`HIGH_CARDINALITY`** | Cột quá nhiều nhóm phân biệt (> 90%) | • Cố định: `WARN` |
| **`IMBALANCE`** | Mất cân bằng cực đoan (1 nhóm chiếm > 95%) | • Cố định: `WARN` |

### Nhóm B: Lỗi Toàn vẹn Lược đồ (Schema Integrity)

Các lỗi Schema không dựa vào tỷ lệ %, mà được **gán cứng trực tiếp** vì nó mang tính chất Đúng/Sai tuyệt đối:

| Tên lỗi | Mô tả | Mức phạt cố định |
| :--- | :--- | :--- |
| **`MISSING_COLUMN`** | Thiếu cột bắt buộc theo Schema. | **`CRITICAL`** |
| **`PK_NULL`** | Cột Khóa chính bị rỗng. | **`CRITICAL`** |
| **`PK_DUPLICATE`** | Cột Khóa chính bị trùng lặp. | **`CRITICAL`** |
| **`ORPHAN_FOREIGN_KEY`** | Khóa ngoại dẫn tới dữ liệu không tồn tại. | **`CRITICAL`** |
| **`TYPE_MISMATCH`** | Sai kiểu dữ liệu (Ví dụ String thay vì Integer). | **`HIGH`** |
| **`NOT_NULL_VIOLATION`** | Cột `NOT NULL` bị để trống. | **`HIGH`** |
| **`UNIQUE_VIOLATION`** | Cột `UNIQUE` bị trùng. | **`HIGH`** |
| **`FK_UNCHECKED`** | Không có bảng gốc để kiểm tra FK. | **`WARN`** |
| **`EXTRA_COLUMN`** | Có thêm cột không nằm trong Schema. | **`INFO`** |

---

## PHẦN 3: Xử lý leo thang hình phạt (Escalation)

Mức phạt ban đầu chưa phải là kết quả cuối. Hệ thống chạy qua 2 bước chẩn đoán sâu:

### Bước 1: Leo thang do tính chất rỗng (`calibrator.py`)

Khi phát hiện cột khuyết dữ liệu (`MISSINGNESS`), hệ thống phân loại cơ chế rỗng và tự động tăng/giảm phạt:
- **`MCAR` (Thiếu ngẫu nhiên):** Giữ nguyên mức phạt ban đầu.
- **`MAR` (Thiếu có điều kiện):** Rỗng phụ thuộc vào quy luật của cột khác. **Tăng 1 bậc hình phạt** (Ví dụ `WARN` → `HIGH`). Lý do: Dữ liệu bị rỗng có chủ đích sẽ gây lệch phân phối rất nguy hiểm. (Ghi chú: Khái niệm `MNAR` đã được retired khỏi pipeline).
- **`STRUCTURAL_ABSENT` (Thiếu do cấu trúc):** Nghĩa là NULL đại diện cho "không áp dụng" (Ví dụ: cột "Tên công ty" của khách hàng cá nhân). **Giảm 1 bậc hình phạt** vì đây không thực sự là lỗi thiếu dữ liệu.

### Bước 2: Cộng dồn hình phạt (`compound.py`)

Nếu một cột mắc nhiều "bệnh" cùng lúc, `compound.py` sẽ thực thi thuật toán cộng dồn rủi ro (`compound_severity`):
Chỉ xét các lỗi có mức `WARN` trở lên (gọi là lỗi tham gia). Nếu cột dính từ 2 lỗi tham gia trở lên:
- Nếu bản thân cột đó đã dính một lỗi `CRITICAL` hoặc có **ít nhất 2 lỗi `HIGH` trở lên**: Kết quả phạt bị đẩy kịch trần lên **`CRITICAL`**.
- Các trường hợp còn lại dính nhiều lỗi: Bị nâng lên **`HIGH`**.

*Ví dụ:* Một cột dính 1 lỗi Khuyết Dữ Liệu `HIGH` và 1 lỗi Ngoại Lệ `WARN` → Phạt lên `CRITICAL`.

---

## PHẦN 4: Phán quyết chung cuộc (Aggregator)

Sau khi xử lý `compound_severity` cho toàn bộ các cột, `src/severity/aggregator.py` sẽ ra phán quyết (`Verdict`) cho cả tập dữ liệu:

1. **HỎNG - CẤM DÙNG (`NOT_READY`):** Chỉ cần tồn tại **ít nhất 1 lỗi `CRITICAL`**.
2. **CẢNH BÁO (`WARN`):** Nếu không bị lỗi nguy kịch nào, nhưng dính **ít nhất 1 lỗi `HIGH`**.
3. **SẴN SÀNG (`READY`):** Không có lỗi nào ở mức `HIGH` hoặc `CRITICAL`.

### M1 Density Rule (Luật Mật độ)
Dù dữ liệu không dính lỗi `HIGH/CRITICAL` nào, nhưng nếu nó mắc "quá nhiều bệnh vặt" rải rác ở khắp các cột (Số cột dính `WARN` vượt quá tỷ lệ % `density_share_gate` và tổng số cột `density_min_cols` quy định trong threshold), phán quyết sẽ tự động bị giáng cấp từ `READY` xuống `WARN`.

### Risk Score (Điểm Rủi ro)
Tính bằng cách cộng dồn toàn bộ trọng số (INFO=0, WARN=1, HIGH=5, CRITICAL=20) chia cho tổng số ô dữ liệu `(N_Rows * N_Cols)`. Thước đo này giúp so sánh chất lượng giữa 2 dataset khác nhau một cách khách quan.
