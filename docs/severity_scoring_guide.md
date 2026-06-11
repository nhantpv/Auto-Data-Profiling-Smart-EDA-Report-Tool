# Hướng dẫn Chi tiết Quy trình Đánh giá & Chấm điểm Chất lượng Dữ liệu

Tài liệu này được viết để giải thích toàn bộ logic hoạt động của bộ máy **Đánh giá mức độ nghiêm trọng (Severity Stack - `src/severity`)**. Nội dung được trình bày bằng ngôn ngữ nghiệp vụ thực tế, không sử dụng mã nguồn (code) để bất kỳ ai cũng có thể hiểu được cách hệ thống "khám sức khỏe" và cấp chứng nhận cho một tệp dữ liệu.

---

## Lời mở đầu: "Bệnh án" của dữ liệu là gì?
Khi bạn nạp một tệp dữ liệu vào hệ thống, các công cụ dò quét sẽ tìm ra rất nhiều điểm bất thường (ví dụ: ô trống, dữ liệu bị trùng, dữ liệu lệch chuẩn). Tuy nhiên, không phải lỗi nào cũng nguy hiểm như nhau. 

Bộ máy `src/severity` đóng vai trò như một **Hội đồng y khoa**. Nhiệm vụ của nó không phải là tìm ra lỗi, mà là **đánh giá xem các lỗi đó nặng hay nhẹ, ảnh hưởng thế nào đến việc sử dụng dữ liệu, và cuối cùng ra phán quyết tệp dữ liệu đó đạt hay hỏng.**

---

## PHẦN 1: Bốn mức độ nghiêm trọng của lỗi

Hệ thống phân chia mọi lỗi tìm thấy thành 4 cấp độ từ nhẹ đến nặng:

1.  **Cấp 1 - THÔNG TIN (`INFO`):** Mức nhẹ nhất. Chỉ mang tính chất thông báo cho bạn biết rằng dữ liệu có sự sai lệch nhỏ nhưng không ảnh hưởng gì đến phân tích (Ví dụ: cột bị thừa so với thiết kế ban đầu).
2.  **Cấp 2 - CẢNH BÁO (`WARN`):** Mức nhẹ nhì. Dữ liệu bắt đầu xuất hiện vấn đề đáng lưu ý. Bạn vẫn dùng được dữ liệu nhưng nên cẩn thận (Ví dụ: cột bị trống từ 5% đến 20%).
3.  **Cấp 3 - CAO (`HIGH`):** Mức độ nguy hiểm cao. Dữ liệu đã bị lỗi nặng, nếu đưa vào các mô hình AI/Machine Learning phân tích sẽ rất dễ cho ra kết quả sai lệch (Ví dụ: cột bị rỗng trên 20%, hoặc dính quá nhiều dòng dữ liệu rác/dị biệt).
4.  **Cấp 4 - NGUY KỊCH (`CRITICAL`):** Mức độ cao nhất. Lỗi vi phạm nghiêm trọng tính logic của hệ thống dữ liệu (Ví dụ: cột Khóa chính dùng để định danh khách hàng lại bị bỏ trống hoặc bị trùng lặp).

---

## PHẦN 2: Bảng tra cứu chi tiết các loại lỗi và cách chấm điểm phạt

Dưới đây là danh sách đầy đủ toàn bộ lỗi mà hệ thống có thể phát hiện, đi kèm điều kiện kích hoạt và mức độ phạt ban đầu được thiết lập trong cấu hình hệ thống:

### Nhóm A: Lỗi Chất lượng Dữ liệu (Dò quét trực tiếp từ file CSV/Excel)

| Tên lỗi | Mô tả nghiệp vụ | Điều kiện kích hoạt | Mức phạt ban đầu |
| :--- | :--- | :--- | :--- |
| **`MISSINGNESS`** | Khuyết dữ liệu (ô bị trống/rỗng) | Tỷ lệ ô trống trong cột > 0% | • Dưới 5%: `INFO`<br>• Từ 5% đến dưới 20%: `WARN`<br>• Từ 20% đến dưới 50%: `HIGH`<br>• Từ 50% trở lên: `CRITICAL` |
| **`OUTLIER_ENSEMBLE`** | Dòng dữ liệu dị biệt (bất thường) | Chạy 3 thuật toán AI để tìm ra các dòng có hành vi khác lạ vượt ngưỡng 3.0 độ lệch chuẩn. | • Dưới 5% số dòng bị dị biệt: `WARN`<br>• Từ 5% số dòng bị dị biệt trở lên: `HIGH` |
| **`DUPLICATE`** | Dòng dữ liệu trùng lặp | Tìm các dòng giống hệt nhau về nội dung (bỏ qua cột ID tự tăng) | • Dưới 5% số dòng bị trùng: `WARN`<br>• Từ 5% số dòng bị trùng trở lên: `HIGH` |
| **`CONSTANT_COLUMN`** | Cột hằng số (vô giá trị) | Cột chỉ chứa đúng 1 giá trị duy nhất cho mọi dòng (ví dụ: cả cột đều ghi là "Việt Nam") | • Cố định: `HIGH` |
| **`HIGH_CARDINALITY`** | Cột phân loại quá nhiều nhóm | Cột văn bản (như Tên đường, Địa chỉ) nhưng số nhóm phân biệt chiếm tới hơn 90% số dòng. | • Cố định: `WARN` |
| **`IMBALANCE`** | Mất cân bằng dữ liệu cực đoan | Cột phân loại có một nhóm chiếm ưu thế tuyệt đối trên 95% số dòng (ví dụ: cột giới tính có 99% Nam, 1% Nữ) | • Cố định: `WARN` |

---

### Nhóm B: Lỗi Cấu trúc Thiết kế (So khớp dữ liệu với bản vẽ DBML/SQL)

Các lỗi này mang tính chất "Đúng hoặc Sai" tuyệt đối nên mức phạt được **gán cứng trực tiếp** chứ không cần chạy theo tỷ lệ %:

| Tên lỗi | Mô tả nghiệp vụ | Mức phạt cố định |
| :--- | :--- | :--- |
| **`MISSING_COLUMN`** | File dữ liệu bị thiếu hẳn cột mà bản vẽ yêu cầu bắt buộc phải có. | **`CRITICAL`** (Nguy kịch) |
| **`PK_NULL`** | Cột Khóa chính (định danh duy nhất, ví dụ: Mã khách hàng) bị để rỗng. | **`CRITICAL`** (Nguy kịch) |
| **`PK_DUPLICATE`** | Cột Khóa chính có các giá trị trùng nhau (2 khách hàng chung 1 mã số). | **`CRITICAL`** (Nguy kịch) |
| **`ORPHAN_FOREIGN_KEY`** | Khóa ngoại mồ côi (Ví dụ: Đơn hàng ghi mã khách hàng là 99, nhưng bảng khách hàng không tồn tại ai có ID là 99). | **`CRITICAL`** (Nguy kịch) |
| **`TYPE_MISMATCH`** | Sai kiểu dữ liệu (Ví dụ: Bản vẽ yêu cầu cột tuổi là Số, nhưng thực tế chứa chữ "Hai mươi"). | **`HIGH`** (Cao) |
| **`NOT_NULL_VIOLATION`** | Cột bắt buộc phải điền (`NOT NULL`) lại bị bỏ trống. | **`HIGH`** (Cao) |
| **`UNIQUE_VIOLATION`** | Cột yêu cầu không được trùng (`UNIQUE`, ví dụ: Số điện thoại) lại bị trùng dữ liệu. | **`HIGH`** (Cao) |
| **`FK_UNCHECKED`** | Không thể kiểm tra liên kết khóa ngoại vì bạn quên không nạp bảng liên quan. | **`WARN`** (Cảnh báo) |
| **`EXTRA_COLUMN`** | File dữ liệu có thêm cột lạ mà bản vẽ không khai báo (thừa cột). | **`INFO`** (Thông tin) |

---

## PHẦN 3: Quy trình 3 bước xử lý lỗi và leo thang hình phạt

Đối với các lỗi chất lượng dữ liệu ở **Nhóm A**, sau khi xác định được mức phạt ban đầu ở bảng trên, hệ thống sẽ thực hiện tiếp 3 bước chẩn đoán nâng cao:

### Bước 1: Điều tra nguyên nhân khuyết dữ liệu (`missingness.py`)
Khi phát hiện lỗi khuyết dữ liệu (`MISSINGNESS`), hệ thống sẽ phân loại nguyên nhân rỗng thành 3 loại:
1.  **Thiếu ngẫu nhiên hoàn toàn (MCAR):** Do sự cố kỹ thuật tình cờ (mất mạng, gõ sót). Lỗi này nhẹ nhất vì không làm lệch bản chất phân phối của dữ liệu.
2.  **Thiếu ngẫu nhiên có điều kiện (MAR):** Lỗi rỗng có quy luật và giải thích được bằng các cột khác (ví dụ: Khách hàng Nữ thường bỏ trống cột Cân nặng).
3.  **Thiếu không ngẫu nhiên (MNAR?):** Nguy hiểm nhất. Dữ liệu bị rỗng do chính giá trị ẩn bên trong của nó quyết định (ví dụ: Người siêu giàu cố tình giấu thu nhập).

### Bước 2: Leo thang hình phạt dựa trên nguyên nhân (`calibrator.py`)
*   **Logic:** Nếu cột bị khuyết dữ liệu rơi vào dạng **Thiếu có điều kiện (MAR)** hoặc **Thiếu không ngẫu nhiên (MNAR?)**, mức độ nghiêm trọng ban đầu của cột đó sẽ tự động bị **nâng lên 1 bậc** (Ví dụ: từ `WARN` nâng lên thành `HIGH`). 
*   *Lý do:* Vì khuyết dữ liệu có chủ đích hoặc có quy luật ẩn sẽ gây sai lệch phân phối dữ liệu nghiêm trọng nếu chúng ta cố tình dùng các phương pháp điền giá trị trung bình đơn giản.

### Bước 3: Cộng dồn hình phạt khi cột bị "đa bệnh" (`compound.py`)
Một cột dính nhiều lỗi khác nhau cùng lúc sẽ cực kỳ không an toàn cho việc phân tích.
*   **Logic phạt lũy tiến:** Nếu một cột dính từ 2 lỗi trở lên, hệ thống sẽ lấy mức phạt của lỗi nặng nhất trong cột đó làm mốc, sau đó **tăng thêm bậc phạt tương ứng với số lỗi cộng thêm**.
    *   *Ví dụ thực tế:* Cột `Lương` dính 2 lỗi: Khuyết dữ liệu (đang phạt ở mức `HIGH`) và Mất cân bằng dữ liệu (đang phạt ở mức `WARN`). 
    *   Vì cột này dính 2 lỗi, hệ thống lấy mốc cao nhất là `HIGH`, cộng thêm 1 bậc phạt lũy tiến ➔ Kết quả cuối cùng là cột `Lương` bị quy về lỗi **`CRITICAL`**.

---

## PHẦN 4: Sơ đồ luồng đi của lỗi và Phán quyết chung cuộc

Dưới đây là sơ đồ trực quan cách hệ thống gom tất cả các nguồn lỗi để đưa ra quyết định sinh tử cho tệp dữ liệu của bạn:

```
[Dữ liệu CSV] ➔ Dò lỗi chất lượng ➔ Chấm điểm & Leo thang (calibrator) ➔ Cộng dồn (compound) ┐
                                                                                           ├➔ Bộ tổng hợp (aggregator) ➔ [Phán quyết]
[Bản vẽ Schema] ➔ Đối chiếu lỗi cấu trúc ➔ Gán cứng mức phạt ───────────────────────────────┘
```

Dựa trên danh sách lỗi tổng hợp cuối cùng, **`aggregator.py`** đưa ra phán quyết:

*   **SẴN SÀNG (`READY`):** Nếu **không có bất kỳ lỗi nào** ở mức `HIGH` hoặc `CRITICAL`. Dữ liệu an toàn tuyệt đối.
*   **CẢNH BÁO (`WARN`):** Nếu không bị lỗi nguy kịch nào, nhưng dính **ít nhất 1 lỗi nặng (`HIGH`)** (ví dụ: có cột bị khuyết dữ liệu trên 20%, hoặc có trên 5% dòng dữ liệu dị biệt). Bạn nên làm sạch dữ liệu trước khi sử dụng.
*   **HỎNG - CẤM DÙNG (`NOT_READY`):** Chỉ cần dính **ít nhất 1 lỗi nguy kịch (`CRITICAL`)** (ví dụ: cột khóa chính bị rỗng, khóa ngoại bị mồ côi, hoặc có cột dính nhiều lỗi cộng dồn thành CRITICAL). Dữ liệu này không thể sử dụng vì chắc chắn sẽ làm sai lệch hoàn toàn kết quả báo cáo và mô hình AI.
