# Superpowers Audit: Toàn cảnh Kiến trúc Smart EDA v3.0 (Master Audit)

Tài liệu này ghi lại vòng kiểm toán chuyên sâu (Superpowers Audit) trên toàn bộ **5 Trụ cột Kiến trúc**, thực hiện bởi 5 AI Agents.

Mục tiêu của vòng Audit này là phân tách rõ ràng giữa những **Lỗi Nghiêm Trọng (Critical)** bắt buộc phải xử lý để cứu hệ thống, và những ý tưởng **Vẽ rắn thêm chân (Overengineer)** cần loại bỏ để tập trung tốc độ phát triển cho phiên bản MVP.

---

## PHẦN A: NHÓM LỖI NGHIÊM TRỌNG (CRITICAL - BẮT BUỘC SỬA CHO MVP)

### 1. Trụ cột 3: Bom Fan-out nổ RAM khi JOIN Khóa không Unique
*   **Tình trạng:** Khi LEFT JOIN bảng phụ (Dimension) vào bảng chính (Fact) để tìm insight chéo, nếu Khóa của bảng phụ chứa dữ liệu trùng lặp, 1 dòng Fact sẽ tự nhân bản thành nhiều dòng. Server sẽ hết RAM ngay lập tức.
*   **Guardrail (Bắt buộc):** Chốt chặn `Safe Join Rule`. Trước khi `pd.merge()`, phải chạy lệnh `assert Dimension[Key].is_unique`. Nếu không unique, văng cảnh báo `NON_UNIQUE_JOIN_KEY` và **HỦY BO JOIN luôn**.

*(Giải đáp: Nếu hủy JOIN thì mất insight tương quan chéo bảng? Đúng. Nhưng thà mất insight của một bảng phụ bị thiết kế lỗi, còn hơn là làm nổ Server hoặc sinh ra báo cáo với các con số tiền tệ bị nhân đôi vô lý. Ở MVP, ta từ chối phục vụ data bẩn thay vì cố gắng phân tích nó).*

### 2. Trụ cột 3: Xóa nhầm Biến số liên tục (Tiền tệ, Tuổi)
*   **Tình trạng:** Áp dụng luật "Nếu Cardinality > 95% -> Xóa cột" một cách mù quáng sẽ vô tình xóa sạch các cột Số (ví dụ: Tổng tiền lẻ tới từng xu) hoặc Ngày tháng (tới từng mili-giây).
*   **Guardrail (Bắt buộc):** Phải xét thêm `Data Type`. Luật loại bỏ Cardinality > 95% CHỈ ÁP DỤNG cho kiểu chuỗi (TEXT/STRING). Kiểu số (NUMERIC) và ngày tháng (DATETIME) phải giữ lại vô điều kiện.

### 3. Trụ cột 4: Quá tải bộ nhớ (OOM) khi đọc file tỷ dòng
*   **Tình trạng:** Khâu kiểm tra toàn vẹn Khóa (Integrity Check) bắt tải toàn bộ các cột ID. Nếu dùng `pd.read_csv()` để nạp 1 file khổng lồ lên RAM, Server sẽ chết.
*   **Guardrail (Bắt buộc):** Chuyển sang cơ chế streaming bằng `KeyColumnScanner`. Đọc file theo từng khối (`chunksize=100000`). Quét đến đâu đối chiếu bằng Hash set đến đó.

### 4. Trụ cột 2: Jaccard Index đo lường sai Khóa Ngoại
*   **Tình trạng:** Thuật toán Jaccard (Độ giao thoa) cực kỳ yếu kém với Surrogate Keys. Bảng Users (ID từ 1-100) và bảng Products (ID từ 1-100) sẽ bị toán học gán nhầm là Khóa Ngoại vì Jaccard = 100%.
*   **Guardrail (Bắt buộc):** Cấm dùng Jaccard làm metric chính. Chuyển sang dùng **Value Coverage (Độ phủ giá trị)** kết hợp với khoảng cách tên cột (Name Score).

### 5. Trụ cột 1: Lỗ hổng Prompt Injection từ Placeholder
*   **Tình trạng:** Nếu cho phép LLM tự do sinh mã `[CHART_XYZ]`, hacker có thể lừa LLM sinh ra đường dẫn đọc lén file hệ thống (Path Traversal).
*   **Guardrail (Bắt buộc):** Cấm LLM tự ý gọi lệnh vẽ biểu đồ. Báo cáo L4 Text-only 100%. Nếu chèn ảnh, chỉ được phép tham chiếu các biểu đồ đã được sinh sẵn một cách thụ động từ các bước trước.

---

## PHẦN B: NHÓM OVERENGINEER (VẼ RẮN THÊM CHÂN - ĐÃ LOẠI BỎ KHỎI MVP)

*Lưu ý: Các ý tưởng dưới đây nghe rất "sang trọng" về mặt lý thuyết, nhưng tốn quá nhiều tài nguyên phát triển và không đem lại giá trị sinh tồn thiết thực. Chúng ta thống nhất **BỎ QUA** ở phiên bản MVP.*

### 1. Đòi dùng Biểu đồ tương tác Plotly JSON (Trụ cột 1)
*   **Ý tưởng Overengineer:** Chê ảnh PNG là tĩnh và "kém sang", đòi Python xuất cấu trúc Plotly JSON để UI ở Frontend tự render thành biểu đồ có thể Zoom/Hover được.
*   **Quyết định MVP:** **BỎ QUA.** Ảnh tĩnh `.png` là hoàn toàn đủ dùng để chứng minh giá trị phân tích của hệ thống. Việc xử lý ảnh tĩnh lưu vào thư mục `artifacts/` nhanh, nhẹ, và cực kỳ dễ code.

### 2. Đòi lấy mẫu phân tầng - Stratified Sampling (Trụ cột 4)
*   **Ý tưởng Overengineer:** Chê Random Sampling (Lấy mẫu ngẫu nhiên) làm mất các dòng dữ liệu hiếm. Đòi hệ thống phải quét toàn bộ file để tính toán tỷ lệ và lấy mẫu phân tầng phức tạp.
*   **Quyết định MVP:** **BỎ QUA.** Việc tính toán phân tầng tốn cực nhiều thao tác đọc ghi (I/O) và làm code phức tạp hóa lên nhiều lần. Chốt sử dụng **Random Sampling**. Chỉ cần thêm một dòng cảnh báo `is_sampled=True` trong Metadata báo cáo cho người dùng biết dữ liệu đã bị lấy mẫu là đủ chuẩn mực đạo đức.

### 3. Bắt hệ thống tự động sửa lỗi JOIN bằng `groupby().first()` (Trụ cột 3)
*   **Ý tưởng Overengineer:** Khi hệ thống LEFT JOIN gặp lỗi ngược hướng (do Khóa Dimension không Unique), thay vì báo lỗi, hệ thống sẽ "tỏ ra thông minh" bằng cách tự động chạy hàm `groupby().first()` để ép bảng phụ về dạng 1-1 cho bằng được.
*   **Quyết định MVP:** **BỎ QUA.** Việc tự động gom nhóm bằng `.first()` là hành vi lấp liếm lỗi thiết kế CSDL của khách hàng. Kết quả Insight chéo sinh ra sẽ mang tính "hên xui" tùy vào dòng dữ liệu nào lọt vào `.first()`. 
*   **Kết luận:** MVP chọn giải pháp **Fail-Fast (Chết nhanh còn hơn lừa dối)**. Cứ thấy Khóa không Unique là thẳng tay Hủy JOIN. Chúng ta thà báo cáo thiếu phần tương quan chéo của bảng đó, còn hơn là bịa ra số liệu.
