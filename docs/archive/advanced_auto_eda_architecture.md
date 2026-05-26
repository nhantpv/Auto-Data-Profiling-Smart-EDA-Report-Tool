# Kiến trúc Quy trình EDA Tự động cấp độ Production (Advanced Architecture)
**Mục tiêu:** Định hướng cho team kỹ thuật xây dựng công cụ `Auto-Data-Profiling-Smart-EDA-Report-Tool`. Tài liệu này giải thích chi tiết kiến trúc 10 lớp, lý do tồn tại của từng lớp và cách nó ánh xạ (map) vào quy trình EDA cơ bản.

---

## Sự khác biệt giữa EDA Cơ bản và EDA Tự động (Production-grade)

Ở quy trình 5 bước cơ bản, con người dùng mắt và kinh nghiệm cá nhân để xử lý dữ liệu. Tuy nhiên, khi **chế tạo một cỗ máy tự động hóa**, chúng ta không thể "trông cậy vào mắt người". 

Máy móc cần những quy tắc (rules) chặt chẽ, khả năng phát hiện rủi ro (risk alerts) tự động, và sự xác thực (validation) ở mức độ cực kỳ sâu sắc để tránh việc tự ý biến đổi làm hỏng dữ liệu của người dùng.

Đó là lý do quy trình 5 bước cơ bản được phân rã và mở rộng thành **Kiến trúc 10 Lớp (10-Layer Architecture)** khắt khe sau đây:

---

## Chi tiết Kiến trúc 10 Lớp (10-Layer Architecture)

### Nhóm 1: Thấu hiểu & Nạp dữ liệu (Tương đương Bước 1 cơ bản)

#### Layer 1: Thấu hiểu Nghiệp vụ (Business & Problem Understanding)
*   **Đây là gì?** Lớp cấu hình ban đầu, nơi người dùng (hoặc LLM) định nghĩa bối cảnh của dữ liệu cho hệ thống.
*   **Tại sao cần thiết?** Máy móc không biết cột "Doanh thu" quan trọng hơn cột "Mã số thuế". Hệ thống cần được cho biết **Biến mục tiêu (Target variable)** là gì để tập trung phân tích, và các **Ràng buộc nghiệp vụ (Constraints)** (Ví dụ: giá nhà không thể âm, tuổi không thể quá 150) để biết đâu là lỗi thật sự, đâu là dữ liệu hiếm.

#### Layer 2: Thu thập & Kiểm tra Cấu trúc Tự động (Data Ingestion & Schema Inspection)
*   **Đây là gì?** Bước hệ thống đọc file và tự động nhận diện kiểu dữ liệu của từng cột.
*   **Tại sao cần thiết?** Trong thực tế, dữ liệu thường rất lộn xộn. Hệ thống phải có khả năng tự động nhận diện (Type Inference) cột nào là kiểu Số, cột nào là Ngày tháng, cột nào là Text tự do. Đặc biệt, nó phải phát hiện được các cột bị trộn lẫn (Mixed type - ví dụ một cột vừa chứa chữ "N/A" vừa chứa số "100") để xử lý kịp thời.

### Nhóm 2: Đánh giá Chất lượng Dữ liệu (Tương đương Bước 2 cơ bản)

#### Layer 3: Xác thực Chất lượng Dữ liệu Chuyên sâu (Deep Data Quality Validation)
*   **Đây là gì?** Bước kiểm tra lỗi logic và định dạng, vượt xa khỏi việc chỉ đếm ô trống (missing).
*   **Tại sao cần thiết?** Dữ liệu có thể không bị trống nhưng lại bị sai logic. Layer này dùng Regex và Logic để kiểm tra các lỗi như: Số điện thoại sai định dạng, ngày kết thúc diễn ra trước ngày bắt đầu, hoặc dữ liệu vi phạm tính toàn vẹn (ví dụ: Cột ID khách hàng chứa một mã không hề tồn tại trong cơ sở dữ liệu gốc).

#### Layer 4: Phân tích Cấu trúc Phân loại & Mất mát (Initial Profiling & Missing Pattern)
*   **Đây là gì?** Đánh giá mức độ "dùng được" của dữ liệu và phân tích nguyên nhân dữ liệu bị mất.
*   **Tại sao cần thiết?** Thay vì tự động xóa mù quáng các ô trống, hệ thống cần tìm ra quy luật (Pattern): dữ liệu bị mất ngẫu nhiên hay có chủ đích? Ngoài ra, hệ thống phải đếm số lượng giá trị duy nhất (Cardinality) để cảnh báo nếu một cột (như ID hoặc Email) có quá nhiều giá trị khác biệt. Nếu mang các cột này đi mã hóa (One-hot Encoding), hệ thống sẽ bị quá tải (Explosion) và sập nguồn.

#### Layer 5: Làm sạch & Đồng nhất (Cleaning & Standardization)
*   **Đây là gì?** Hệ thống tự động sửa lỗi dựa trên những gì tìm thấy ở Layer 3 và 4.
*   **Tại sao cần thiết?** Máy tính sẽ dùng các thuật toán (như Fuzzy matching) để tự động gom nhóm các từ viết sai chính tả (vd: "Nam", "Namm", "M" -> "Male"), tự động chọn thuật toán điền khuyết (Imputation) phù hợp dựa trên phân phối dữ liệu, và xử lý các giá trị ngoại lệ (cắt bỏ hoặc thay thế) tùy theo mức độ ảnh hưởng.

### Nhóm 3: Phân tích & Tối ưu Đặc trưng (Tương đương Bước 3 & 4 cơ bản)

#### Layer 6: Phân tích Thống kê Khám phá Tự động (Exploratory Statistical Analysis)
*   **Đây là gì?** Máy móc tự động chạy hàng loạt các bài test thống kê (ANOVA, Chi-square, Mutual Information) đan chéo giữa tất cả các cột.
*   **Tại sao cần thiết?** Nhờ tốc độ tính toán, máy móc có thể tìm ra các "cột rác" (cột mà 99.9% giá trị giống hệt nhau - Near-zero variance) để loại bỏ ngay lập tức. Nó cũng giúp khám phá những mối quan hệ phi tuyến tính ẩn giấu với Biến mục tiêu mà mắt thường hay các biểu đồ cơ bản dễ bỏ sót.

#### Layer 7: Kỹ thuật Đặc trưng & Chuyển đổi (Feature Engineering & Transformation)
*   **Đây là gì?** Các phép biến đổi toán học để làm "phẳng" dữ liệu hoặc tạo ra các tính năng (Features) mới có ý nghĩa hơn.
*   **Tại sao cần thiết?** Nếu dữ liệu phân phối quá xiên (skewed), hệ thống tự động áp dụng hàm Logarit để nắn thẳng lại. Nếu có cột Thời gian, hệ thống tự tách ra thành các cột "Ngày trong tuần", "Tháng", "Mùa" để các thuật toán máy học có thêm manh mối dự đoán.

#### Layer 8: Lựa chọn Đặc trưng & Cảnh báo Rò rỉ (Feature Selection & Leakage Detection) - [Cực kỳ Quan trọng]
*   **Đây là gì?** Lớp rà soát an ninh cuối cùng trước khi xuất dữ liệu, chuyên loại bỏ các cột gây nguy hiểm.
*   **Tại sao cần thiết?** Đây là tính năng "ăn tiền" định hình một hệ thống chuyên nghiệp. Nó phát hiện **Rò rỉ dữ liệu (Target Leakage)** (Ví dụ: Dùng cột "Lý do hủy đơn" để dự đoán xem "Khách có hủy đơn không" - Điều này khiến AI đạt độ chính xác 100% một cách giả tạo) và **Đa cộng tuyến (Multicollinearity)** (xóa bớt các cột chứa thông tin lặp lại nhau y hệt để làm nhẹ mô hình).

### Nhóm 4: Xác thực & Báo cáo (Tương đương Bước 5 cơ bản)

#### Layer 9: Xác thực Hậu chuyển đổi (Post-Transformation Validation)
*   **Đây là gì?** Bước "khám lại bệnh" sau khi đã xào nấu dữ liệu.
*   **Tại sao cần thiết?** Ở các quy trình thủ công cơ bản, người ta biến đổi xong là đem dùng luôn. Ở hệ thống tự động, ta phải bắt buộc kiểm tra lại xem việc điền khuyết hay chuẩn hóa (scaling) có vô tình làm hỏng phân phối gốc ban đầu, hay tự dưng sinh ra các lỗi NaN mới hay không.

#### Layer 10: Trực quan hóa & Đánh giá Sức khỏe (Reporting & Health Scoring)
*   **Đây là gì?** Đóng gói toàn bộ hàng vạn phép tính toán trên thành một báo cáo và điểm số dễ hiểu.
*   **Tại sao cần thiết?** Thay vì quăng cho người dùng 50 cái biểu đồ rời rạc rắc rối, hệ thống tổng hợp lại thành một con số **Điểm Sức khỏe Dữ liệu (Dataset Health Score)** (ví dụ: Dữ liệu đạt 75/100 điểm). Đồng thời, hệ thống biểu diễn các cảnh báo rủi ro (Risk warnings) một cách trực quan, và kết hợp với LLM để đưa ra các đề xuất hành động (Actionable Insights) bằng ngôn ngữ tự nhiên.
