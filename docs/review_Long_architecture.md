# Review Kiến trúc: Phản biện Kế hoạch của Long (Smart EDA v3.0)

**Tài liệu tham chiếu:**
- `Problem_need_to_be_solved.md` (Các vấn đề gốc cần giải quyết)
- `Long_fix_architecture_plan (1).md` (Bản đề xuất giải pháp của Long)

Tài liệu này không chỉ diễn giải cặn kẽ bản chất kỹ thuật trong các đề xuất của Long, mà còn đưa ra các **phản biện và góp ý điều chỉnh cốt lõi từ góc nhìn Product / Thực chiến**. Mục tiêu là tránh việc hệ thống trở nên quá "khó tính", dỗi khách hàng, hoặc tự lừa dối bằng những rào cản kỹ thuật cứng nhắc.

---

## DIỄN GIẢI CHI TIẾT & GÓP Ý ĐIỀU CHỈNH 5 TRỤ CỘT KIẾN TRÚC

Bản đề xuất của Long bám rất sát triết lý **"Deterministic-first, LLM-last, Fail-safe"** nhằm tối ưu máy chủ và tiết kiệm chi phí. Tuy nhiên, nếu áp dụng nguyên xi, hệ thống sẽ bị thiên kiến "an toàn thái quá cho máy móc" mà bỏ quên Trải nghiệm Khách hàng (UX). Dưới đây là phân tích kỹ thuật và phản biện cho từng vấn đề gốc:

### 1. Vấn đề 1: Lỗ hổng Path Traversal và Nút thắt LLM Vision
*   **Bản chất kỹ thuật (Lỗi cũ):**
    1.  Để LLM "nhìn" ảnh biểu đồ qua API Vision tốn token gấp nhiều lần text. Hơn nữa, thuật toán Vision của LLM rất kém trong việc đọc tọa độ trục X/Y trên biểu đồ Scatter Plot, dẫn đến việc LLM "bịa" ra số liệu không có thật (Hallucination).
    2.  Nếu thiết kế hệ thống cho phép LLM tự động sinh ra chuỗi biến `[CHART_OUTLIER_AGE]` vào chuỗi văn bản báo cáo để Frontend parse (dịch) và load ảnh từ server, hacker có thể dùng kỹ thuật Prompt Injection ép LLM in ra chuỗi `[CHART_../../../etc/passwd]`. Frontend sẽ đọc nhầm file hệ thống của máy chủ và hiển thị lên UI.
*   **Giải pháp MVP của Long:**
    *   **Text-Only L4:** Chuyển luồng L4 thành báo cáo thuần văn bản. Cung cấp cho LLM tệp JSON chứa các con số thống kê chính xác tuyệt đối (do Python tính toán) để LLM viết báo cáo. Tuyệt đối không gửi ảnh. Bỏ qua yêu cầu vẽ Plotly/ECharts tương tác để tiết kiệm thời gian Frontend.
    *   **ArtifactManifest:** Tạo ra một Danh sách trắng. Khi Python vẽ xong biểu đồ tĩnh PNG nào, nó sẽ ghi ID của biểu đồ đó vào Manifest. Báo cáo của LLM bị khóa cứng, chỉ được phép gọi các ID biểu đồ ĐÃ TỒN TẠI trong Manifest. Các biến lạ do LLM bịa ra đều bị Regex xóa bỏ.

### 2. Vấn đề 2: Thuật toán dò Khóa ngoại Jaccard Index bị sai số
*   **Bản chất kỹ thuật (Lỗi cũ):** Dùng Jaccard Index (tính tỷ lệ số phần tử chung chia cho tổng số phần tử của 2 cột) để đoán xem 2 cột có phải là Khóa chính - Khóa ngoại (PK-FK) không.
    *   *Ví dụ lỗi:* Bảng `Users` có cột `id` kiểu số nguyên tự tăng từ 1 đến 100. Bảng `Products` cũng có cột `id` từ 1 đến 100. Công thức Jaccard sẽ trả về tỷ lệ giao thoa là 100%. Hệ thống sẽ tự động liên kết bảng Users và Products với nhau một cách vô lý.
*   **Giải pháp MVP của Long:**
    *   **Bác bỏ Jaccard.** Áp dụng công thức **Value Coverage** (Độ phủ giá trị tập con). Thuật toán sẽ quét xem các giá trị trong cột `user_id` của bảng `Orders` có NẰM GỌN trong tập hợp các giá trị của cột `id` bảng `Users` hay không.
    *   **Gạt bỏ LLM.** Nếu thuật toán tính ra Value Coverage > 95% kết hợp với Name Score (tên cột trùng chữ `user`) > 0.8 thì code Python tự chốt hạ liên kết. Không đưa cho LLM chốt để tránh độ trễ API và ảo giác.
*   **Góp ý Phản biện (Từ góc nhìn Thực chiến): Lỗ hổng của `Value Coverage` và Bắt buộc phải có `Human-in-the-loop`**
    *   **Điểm yếu trong giải pháp của Long:** Long bác bỏ Jaccard và tin tưởng hoàn toàn vào `Value Coverage` (Tỷ lệ tập hợp con). Tuy nhiên, Toán học hoàn toàn bất lực trước Khóa tự tăng (Surrogate Keys). Ví dụ: Bảng `Orders` có `user_id` từ 1-50, bảng `Products` có `id` từ 1-100. Tập 1-50 nằm trọn 100% trong tập 1-100. Thuật toán `Value Coverage` sẽ lập tức nhận diện mù quáng đây là Khóa ngoại.
    *   **Giải pháp Kỹ thuật Điều chỉnh:**
        1.  **Lọc tinh bằng Semantic (LLM):** Mặc dù Long muốn gạt bỏ LLM để tiết kiệm, nhưng ở đây BẮT BUỘC phải đưa danh sách lọc thô (Toán học) cho LLM để nó dùng Ngữ nghĩa chốt hạ (Ví dụ: LLM sẽ hiểu `user_id` không thể nối với `product_id`).
        2.  **Chốt hạ bằng Human-in-the-loop:** Trước khi chạy Profiling Lượt 2, giao diện hệ thống bắt buộc phải in ra Sơ đồ Database dự đoán để Khách hàng bấm nút **"Xác nhận sơ đồ / Sửa lại kết nối"**. Không thể để Toán học hay AI tự quyết định ngầm rồi chạy tuốt luốt, dẫn đến báo cáo sai lệch hoàn toàn.

### 3. Vấn đề 3: Fan-out OOM khi JOIN bảng và Lỗi hàm lọc Cardinality
*   **Bản chất kỹ thuật (Lỗi cũ):**
    1.  Khi chạy lệnh `pd.merge()` (LEFT JOIN) bảng `Orders` (1 triệu dòng) với bảng `Users` (Dimension), bắt buộc cột khóa của bảng `Users` phải là Unique. Nếu CSDL khách hàng bị lỗi (ví dụ có 2 user cùng ID), 1 dòng Order khi JOIN sẽ nhân bản thành 2. Tệp 1 triệu dòng có thể phình thành chục triệu dòng gây tràn bộ nhớ (Out of Memory - OOM). Code cũ định dùng `groupby().first()` bốc đại 1 dòng để chữa cháy.
    2.  Luật dọn rác quy định: Cột nào có Cardinality (Tỷ lệ giá trị khác biệt) > 95% thì xóa bỏ. Áp dụng máy móc, hệ thống sẽ xóa luôn cột `Order_Amount` (Doanh thu) vì số tiền giao dịch thường lẻ đến từng đồng, dòng nào cũng khác dòng nào (100% Cardinality).
*   **Giải pháp MVP của Long:**
    *   **Safe Join Rule:** Trước khi chạy `pd.merge()`, sử dụng cờ `is_unique` của thư viện Pandas để check Khóa bảng Dimension. Nếu `False`, lập tức hủy lệnh JOIN (Fail-safe). Thà không phân tích chéo còn hơn tự ý dùng `groupby().first()` làm sai lệch số liệu tính tổng doanh thu sau này.
    *   **Dtype-Aware Filter:** Bọc hàm check Cardinality bằng một hàm check Kiểu dữ liệu. Chỉ xóa cột khi `dtype == string/object` (vd: chuỗi UUID, đoạn text ghi chú tự do). Bảo lưu tuyệt đối các cột có `dtype == numeric/datetime`.
*   **Góp ý Phản biện (Từ góc nhìn Thực chiến): Chống "Fail-Fast" cực đoan bằng `Deduplicate` toàn phần**
    *   **Điểm yếu trong giải pháp của Long:** Long quy định `Safe Join Rule`: Chỉ cần Khóa không Unique là hệ thống từ chối JOIN và văng lỗi. Trong thực tế, dữ liệu xuất từ các hệ thống ERP cũ cực kỳ bẩn. Nếu hệ thống cứ hơi một tí là dỗi (Fail-Fast) và từ chối phân tích chéo, thì 90% tệp dữ liệu khách hàng đưa lên sẽ bị chối bỏ. Khách hàng mua tool "Smart EDA" để tìm insight đa bảng, chứ không phải để nhận thông báo "Tệp của anh bẩn quá, tôi từ chối phân tích".
    *   **Giải pháp Kỹ thuật Điều chỉnh (The Silver Bullet):**
        *   **Thêm bước Tiền xử lý (Pre-processing):** Trước khi chạy lệnh kiểm tra Unique cho bảng Dimension, ta chèn thêm lệnh **`df_dim = df_dim.drop_duplicates()`** (Xóa các dòng bị nhân bản giống hệt nhau 100% về nội dung - một lỗi cực kỳ phổ biến khi trích xuất SQL).
        *   Nếu sau khi chạy `drop_duplicates()`, Khóa Dimension trở nên Unique $\rightarrow$ Quá tuyệt, tiến hành JOIN bình thường! Khách hàng vẫn có insight chéo. Nếu Khóa vẫn trùng (ID giống nhưng Tên/Tuổi khác $\rightarrow$ CSDL hỏng thật), lúc này mới dùng đến lệnh Fail-Fast.
        *   **Về rủi ro Tràn RAM (OOM):** Việc dữ liệu lớn đến mức gây tràn RAM khi JOIN không phải là rủi ro cần khóa tính năng ở bản MVP. Đó là bài toán Scale hạ tầng ở Phase sau. Đối với MVP, thà giới hạn cứng dung lượng tệp tải lên (Ví dụ: Max file 500MB) còn hơn là bóp nghẹt tính năng cốt lõi.

### 4. Vấn đề 4: Ảo giác thống kê do "Lấy mẫu ngầm"
*   **Bản chất kỹ thuật (Lỗi cũ):** Do không load nổi tệp CSV khổng lồ, hệ thống tự động chạy hàm `df.sample()` để cắt tệp xuống còn 500k dòng đem đi chạy Profiling. Tuy nhiên, JSON xuất ra không chứa thông số nào ghi nhận việc này. LLM đọc JSON thấy `missing_count = 100`, liền viết báo cáo: "Tệp dữ liệu cực kỳ sạch, chỉ thiếu 100 dòng". Thực tế, 100 dòng lỗi đó nằm trong mẫu 5%, khách hàng bị lừa dối về mặt thống kê.
*   **Giải pháp MVP của Long:**
    *   Chấp nhận việc build module Streaming Load (đọc tệp từng chunk nhỏ) cho mọi định dạng là quá sức cho bản MVP hiện tại. Vẫn giữ cơ chế Random Sampling.
    *   **Bổ sung Metadata Constraint:** Cập nhật schema Pydantic thêm các trường bắt buộc `is_sampled: bool`, `original_n: int`, `sample_n: int`. Truyền thẳng khối JSON này vào LLM Prompt, ép LLM khi sinh Text bắt buộc phải in ra dòng cảnh báo để minh bạch với người dùng.

### 5. Vấn đề 5: JSON phình to (Context Window Limit) và Logic Compound sai lệch
*   **Bản chất kỹ thuật (Lỗi cũ):**
    1.  Đẩy mảng `AnomalyRecord` chứa chi tiết 1000 lỗi của từng dòng dữ liệu vào chung một file `dataset_verdict.json`. Điều này tạo ra một cục JSON khổng lồ, khi đưa qua API OpenAI sẽ làm tràn Context Window (Giới hạn ngữ cảnh), khiến LLM mất khả năng ghi nhớ và suy luận logic.
    2.  Module `compound.py` sử dụng phép toán cộng dồn vô lý: Cột A có lỗi Type (INFO) + lỗi Missing (WARN) $\rightarrow$ đẩy `severity` lên CRITICAL. LLM đọc JSON thấy nhãn CRITICAL thì hoảng loạn, đánh giá sai bản chất kỹ thuật của lỗi.
*   **Giải pháp MVP của Long:**
    *   **Phân mảnh Payload (Reference Architecture):** Cấu trúc lại `dataset_ver định.json` cực kỳ mỏng. Chỉ chứa mảng `top_issues` lược trích các lỗi nghiêm trọng nhất. Các chi tiết lỗi giữ lại ở file `data_quality_findings.json`. Verdict chỉ chứa một key `detail_ref` trỏ URL về file Findings. LLM nạp JSON mỏng sẽ chạy cực nhanh.
    *   **Tách biến độc lập:** Tạo biến `effective_severity` (mức độ cộng dồn) chỉ dùng để Front-end sắp xếp thứ tự ưu tiên hiển thị. Tạo biến `severity` (mức độ tĩnh nguyên bản của lỗi). LLM chỉ đọc `severity` gốc để hiểu đúng bản chất kỹ thuật. Giữ nguyên công thức Logistic Regression thay vì đổi sang Dummy Correlation.
*   **Góp ý Phản biện (Từ góc nhìn Thực chiến): Đập bỏ và thiết kế lại Thuật toán `Compound`**
    *   **Điểm yếu trong giải pháp của Long:** Logic cộng dồn lỗi trong `compound.py` đang rất vô lý. Việc Long đề xuất "Tách biến" (Variable Separation) chỉ là giải pháp lấp liếm. Nếu phép toán cộng dồn đã sai bản chất, thì việc giấu nó vào biến `effective_severity` để Frontend đem đi xếp hạng cũng làm UI hiển thị một cách ngu ngốc (Lỗi rất bé lại bị gán cờ Critical đỏ chót đẩy lên Top đầu).
    *   **Giải pháp Kỹ thuật Điều chỉnh:**
        *   Không thể dùng mẹo che giấu. Bắt buộc phải **đập bỏ và thiết kế lại logic tính toán trong `compound.py`**.
        *   **Quy tắc mới:** Các lỗi cấp `INFO` tuyệt đối không được tham gia vào phép tính cộng dồn. Chỉ cho phép leo thang lên `CRITICAL` nếu cột đó dính **từ 2 lỗi HIGH trở lên**. Nếu ở MVP chưa kịp code lại logic chuẩn xác này, thà vô hiệu hóa luôn module Compound còn hơn để nó làm nhiễu loạn báo cáo.
