# Tuyên ngôn Kiến trúc & Quản trị Rủi ro Smart EDA v3.0 (Architecture Directives)

Tài liệu này đóng vai trò như một **Bản Hiến pháp Kỹ thuật**, được trích xuất từ các cuộc phản biện khốc liệt giữa các AI Agents (Chuyên gia Dữ liệu, Kiến trúc sư Hệ thống, và Product Owner). Nhằm giải quyết tình trạng mỗi kỹ sư làm việc trên một nhánh (branch) riêng lẻ khó nắm bắt tổng thể, toàn bộ các vấn đề kiến trúc đã được chúng tôi phân rã thành **Hệ tiêu chuẩn 3 Cấp độ**:

1. **Architecture Flaws:** Những sai lầm trong thiết kế gốc mà mọi nhánh phải từ bỏ.
2. **MVP Boundaries:** Ranh giới giới hạn tính năng, cấm "vẽ rắn thêm chân" (Overengineer).
3. **Mandatory Guardrails:** Các chốt chặn an toàn bắt buộc mọi đoạn code phải triển khai.

---

## PHẦN 1: ARCHITECTURE FLAWS (CÁC SAI LẦM THIẾT KẾ GỐC CẦN TRÁNH)

Đây là những tư duy thiết kế lý thuyết đã được chứng minh là sai lầm thông qua các vòng Audit. Mọi Developer tuyệt đối không được tiếp cận bài toán theo các hướng dưới đây.

### 1.1. Nút thắt Cổ chai Vision LLM (Trụ cột 1)
*   **Tình trạng thiết kế cũ:** Kiến trúc Layer 4 dự kiến gửi ảnh biểu đồ cho LLM đọc và viết báo cáo.
*   **Bản chất sai lầm:**
    *   **Agent (Cost-Optimizer):** Việc gửi ảnh base64 qua API LLM (như GPT-4o) cực kỳ tốn kém token (giá gấp 3-4 lần text), tốc độ phản hồi chậm đi 50%.
    *   **Agent (Data Architect):** LLM rất hay "ảo giác" (hallucinate) khi đọc biểu đồ phức tạp (ví dụ: đọc sai các tọa độ outlier trên scatter plot). Nguyên tắc cốt lõi của chúng ta là "Deterministic-First". Toàn bộ thông số chính xác 100% đã nằm trong tệp JSON.
*   **Chỉ thị Kiến trúc:** **Tuyệt đối loại bỏ Vision LLM.** LLM chỉ nhận Input là file JSON (Text). Python (Layer 3.5) sẽ đọc báo cáo của LLM, tự động sinh ra biểu đồ bằng Matplotlib, và chèn trực tiếp đường dẫn ảnh thay thế vào vị trí mã lệnh đó.

### 1.2. Ảo tưởng "Jaccard Index và LLM chốt hạ Schema" (Trụ cột 2)
*   **Tình trạng thiết kế cũ:** Dùng Jaccard Index (Độ giao thoa tập hợp) để lọc thô các cặp cột, sau đó ném toàn bộ danh sách cho LLM để nó "chốt hạ" xem đâu là Khóa ngoại (Foreign Key).
*   **Bản chất sai lầm:** Jaccard Index sẽ báo cáo tỷ lệ trùng lặp 100% nếu bảng `Users` có ID từ 1-100 và bảng `Products` cũng có ID từ 1-100 (đây là Surrogate Keys tự tăng, hoàn toàn không liên quan đến nhau). Việc giao quyền chốt hạ cho LLM sẽ tạo ra một bài toán tổ hợp khổng lồ, gây nghẽn cổ chai hiệu năng và sinh ra ảo giác trầm trọng.
*   **Chỉ thị Kiến trúc:** Cấm dùng Jaccard Index làm Metric quyết định. Bắt buộc chuyển sang dùng **Value Coverage (Độ phủ giá trị)**. Hệ thống phải quyết định liên kết bảng bằng code Toán học (Deterministic) hoàn toàn, LLM chỉ đóng vai trò Verification phụ trợ.

### 1.3. Thảm họa gộp chung Data thành Universal Table để Profiling (Trụ cột 3)
*   **Tình trạng thiết kế cũ:** Nhằm phân tích tương quan chéo, hệ thống gộp toàn bộ CSDL lại thành một bảng khổng lồ (Universal Table) để ném vào thư viện `ydata-profiling`.
*   **Bản chất sai lầm (Tối kỵ Data Engineering):**
    1.  **Thảm họa nổ RAM (OOM):** Khâu nặng nhất của Profiling là tính Tương quan (Correlation Matrix) với độ phức tạp O(N²). Gộp 5 bảng tạo ra một bảng 200 cột, số cặp cần so sánh là 200 × 200 = 40,000 cặp. Máy chủ 16GB RAM chắc chắn sẽ treo.
    2.  **Sai lệch Phân phối Thống kê (Statistical Skew):** Khi JOIN bảng Giao dịch (Fact) với bảng Khách hàng (Dimension), dữ liệu Khách hàng bị nhân bản lên tương ứng với số hóa đơn (1 người mua 100 đơn thì xuất hiện 100 lần). Việc tính Độ tuổi trung bình (Mean) trên bảng gộp sẽ ra kết quả hoàn toàn sai lệch so với phân phối gốc.
*   **Chỉ thị Kiến trúc:** Bắt buộc sử dụng kiến trúc **Dual-Pass Profiling (Đánh giá Đa bảng 2 lượt)**: Lượt 1 chạy trên từng bảng đơn để đảm bảo độ chính xác của từng thông số; Lượt 2 chỉ tạo 1 bảng phụ rút gọn để tính tương quan chéo.

### 1.4. Lấy mẫu âm thầm (Silent Sampling) và Phá vỡ Khóa ngoại (Trụ cột 4)
*   **Tình trạng thiết kế cũ:** Báo cáo ghi `n = 500,000` nhưng không nói rõ đây là dữ liệu đã cắt mẫu. Hơn nữa, mọi bảng bị lấy mẫu ngẫu nhiên *trước khi* đem đi kiểm tra đa bảng.
*   **Bản chất sai lầm:**
    *   **Agent (System Architect):** Nếu anh lấy mẫu ngẫu nhiên trước khi check Khóa, dòng `Parent` có thể bị loại trong khi dòng `Child` được giữ. Hệ thống sẽ báo lỗi `Orphan-FK` giả mạo, phá nát báo cáo Schema.
    *   **Agent (Data Scientist):** Lấy mẫu mà không báo là hành vi "nói dối" thống kê. Khách hàng thấy "Missing 10%" sẽ nghĩ thiếu 50.000 dòng, trong khi gốc là 10 triệu dòng.
*   **Chỉ thị Kiến trúc:** Bắt buộc áp dụng **Two-phase Loading** (Tải dữ liệu 2 pha). Luồng Integrity Check phải nạp 100% dòng (nhưng chỉ tải các cột ID). Cập nhật schema `DatasetMeta` lưu rõ `is_sampled`, `original_n`, `sample_n` và prompt cho LLM luôn nhắc nhở nội suy này.

### 1.5. Đánh đồng Missingness và Thiếu insight trong file Verdict (Trụ cột 5)
*   **Tình trạng thiết kế cũ:** Module `missingness.py` chạy test Little's MCAR trên toàn dataframe, ra 1 cái p-value chung, rồi gán nhãn đó cho TẤT CẢ các cột. Sau đó, nó đếm số lượng lỗi (ví dụ: 2 CRITICAL) và ghi tóm tắt vào file `dataset_verdict.json`, vứt bỏ toàn bộ chi tiết MNAR ra ngoài. Lại có ý kiến muốn nhét toàn bộ 1000 lỗi chi tiết vào Verdict để LLM dễ đọc.
*   **Bản chất sai lầm:**
    *   **Missingness Sai Lệch:** Cột Tuổi có thể thiếu có chủ đích (MNAR), nhưng cột Email thiếu ngẫu nhiên (MCAR). Áp chung 1 p-value là sai hoàn toàn về mặt Toán học.
    *   **JSON Phình To:** Việc dồn toàn bộ lỗi vào Verdict JSON làm ngộp LLM Context Window và đẩy chi phí Token lên cao. Đồng thời, lỗi giữa file Findings và Verdict không đồng bộ nhau.
*   **Chỉ thị Kiến trúc:**
    *   Tính Missingness riêng biệt cho từng cột.
    *   File `dataset_verdict.json` chỉ chứa mảng `top_issues` tóm tắt mỏng nhẹ. Đối với mỗi lỗi lớn, lưu đường dẫn `detail_ref` trỏ ngược lại file `data_quality_findings.json` chứa chi tiết. Biến file findings này thành Single Source of Truth.

---

## PHẦN 2: MVP BOUNDARIES (GIỚI HẠN TÍNH NĂNG - KHÔNG OVERENGINEER)

Đây là ranh giới "Đừng cố làm quá tốt". Các kỹ sư phải từ bỏ các ý tưởng dưới đây để đảm bảo dự án kịp tiến độ ra mắt (MVP).

### 2.1. Cấm xây dựng Biểu đồ Tương tác JSON Plotly (Trụ cột 1)
*   **Ý tưởng bị bác bỏ:** Việc chê ảnh PNG tĩnh là "kém sang" và cố gắng cấu trúc hệ thống xuất Plotly JSON để UI/Frontend render biểu đồ có thể Zoom/Hover được.
*   **MVP Boundary:** Cấm code thêm luồng Render Plotly Frontend. Cứ lưu ảnh `.png` tĩnh vào ổ cứng và nhúng đường dẫn vào file Markdown. Nó giải quyết được 90% nhu cầu trực quan hóa của khách hàng mà không tốn 1 tuần code của Team UI.

### 2.2. Cấm đẻ thêm file `auto_schema.py` mới (Trụ cột 2)
*   **Ý tưởng bị bác bỏ:** Viết hẳn một module AI Agent mới toanh chỉ để làm nhiệm vụ Auto-Discovery.
*   **MVP Boundary:** Tuyệt đối không sinh thêm cấu trúc module mới. Tận dụng 100% logic đã có sẵn trong file `src/engines/schema_engine.py` (từ nhánh code `tanlong`). Chỉ cần refactor lại module này thành các class có locality tốt hơn.

### 2.3. Cấm "Chữa bệnh dữ liệu" bằng `groupby().first()` (Trụ cột 3)
*   **Ý tưởng bị bác bỏ:** Khi thao tác LEFT JOIN báo lỗi vì Khóa ngoại chứa dữ liệu trùng lặp (không Unique), hệ thống tỏ ra "thông minh" bằng cách tự chạy lệnh gom nhóm `.first()` hoặc `.mean()` để ép dữ liệu về dạng 1-1 cho bằng được nhằm duy trì quá trình ghép bảng.
*   **MVP Boundary:** Cấm hành vi lấp liếm lỗi thiết kế CSDL của khách hàng. Ở phiên bản MVP, phương châm là **Fail-Fast (Chết nhanh còn hơn lừa dối)**. Nếu dữ liệu không đạt chuẩn để ghép, từ chối ghép và để nó cảnh báo cho khách hàng tự sửa dữ liệu của họ.

### 2.4. Cấm triển khai Lấy mẫu Phân tầng - Stratified Sampling (Trụ cột 4)
*   **Ý tưởng bị bác bỏ:** Đòi hỏi quét qua toàn bộ dữ liệu (kể cả các cột Low-cardinality) để tính toán tỷ lệ, sau đó tiến hành bốc mẫu phân tầng nhằm không làm mất dữ liệu hiếm.
*   **MVP Boundary:** Quá trình tính toán phân tầng tốn cực nhiều thao tác I/O. Ở mức MVP, **chỉ dùng Random Sampling** (Lấy mẫu ngẫu nhiên mặc định) khi tệp quá lớn. 

### 2.5. Từ chối phán quyết READY nếu ngập tràn WARN (Trụ cột 5)
*   **Ý tưởng bị bác bỏ:** Chấp nhận một file Dataset là **READY** ngay cả khi nó chứa 50 lỗi WARN (Cảnh báo).
*   **MVP Boundary:** Áp dụng **Ngưỡng quy đổi (Threshold Rule)**. Ví dụ: Nếu số lượng WARN > 10 HOẶC vượt quá 20% tổng số cột, tự động leo thang Phán quyết chung thành **WARN** (Review before use). Không thể dán mác Ready cho một dataset thủng lỗ chỗ.

---

## PHẦN 3: MANDATORY GUARDRAILS (CHỐT CHẶN AN TOÀN BẮT BUỘC)

Đây là luật sinh tồn. Các Kỹ sư viết code xử lý dữ liệu và AI phải coi các Guardrail này như những dòng `assert` bắt buộc trong mã nguồn. Thiếu chúng, Server sẽ sập hoặc hệ thống sẽ bị hack.

### 3.1. Chốt chặn bảo mật chống Path Traversal (Trụ cột 1)
*   **Tình huống vỡ trận:** Hacker lợi dụng Prompt của người dùng để lừa LLM in ra mã `[CHART_../../../etc/passwd]`. Code Python ngây thơ đọc mã này và render thẳng file hệ thống lên UI.
*   **Guardrail Bắt Buộc:** LLM không có quyền tự do sinh ra mã định danh cho biểu đồ. Báo cáo (L4) chỉ được phép trỏ tới các `artifact_id` ĐÃ TỒN TẠI TRƯỚC ĐÓ trong danh sách Whitelist (ArtifactManifest). Bất kỳ ID lạ nào cũng bị regex chặn và vứt bỏ.

### 3.2. Chốt chặn Chọn nhầm Fact Table bằng Thuật toán Lai (Trụ cột 3)
*   **Tình huống vỡ trận:** Trong Lượt 2 của Dual-Pass Profiling, nếu hệ thống chọn nhầm bảng Log/Audit làm Bảng chính (Fact), toàn bộ phân tích tương quan chéo sau đó sẽ bị rác. Đặc biệt Toán học đồ thị rất dễ bị lừa bởi Bridge table (Bảng nối Nhiều-Nhiều) vì bảng này có Out-degree cực cao.
*   **Guardrail Bắt Buộc:** Áp dụng **The Fact Score Algorithm** với 3 vòng lọc:
    1.  Trọng số Heuristic: Cộng điểm mạnh cho bảng nhiều dòng nhất và chứa cột thời gian (`created_at`).
    2.  Trọng số Đồ thị: Cộng điểm bảng In-degree thấp, Out-degree cao.
    3.  Lọc Semantic: Lấy Top 3 bảng điểm cao nhất gửi cho LLM đọc tên để nó dùng Semantic (Ngữ nghĩa kinh doanh) loại bỏ các Bridge table rác. Bảng chiến thắng cuối cùng mới được làm mốc gộp dữ liệu.

### 3.3. Chốt chặn Nổ RAM do Fan-out LEFT JOIN (Trụ cột 3)
*   **Tình huống vỡ trận:** Khi tạo bảng phụ theo cơ chế Targeted Denormalization (LEFT JOIN), đáng lẽ Khóa Dimension phải Unique, nhưng khách hàng cấu hình sai khiến 1 dòng Dimension lặp lại 100 lần. Lệnh `pd.merge()` sẽ làm 1 dòng Fact (Ví dụ 1 triệu dòng hóa đơn) nhân bản thành 100 triệu dòng hóa đơn ảo. Server sẽ bốc cháy và tiền tệ bị sai lệch nhân lên trăm lần.
*   **Guardrail Bắt Buộc (Safe Join Rule):** Trước bất kỳ lệnh `pd.merge()` nào, bắt buộc phải có lệnh kiểm tra `assert df_dim[key].is_unique`. Nếu trả về False, lập tức kích hoạt Exception `NON_UNIQUE_JOIN_KEY` và HỦY BO JOIN. Thà mất insight chéo còn hơn làm sập máy chủ.

### 3.4. Chốt chặn Loại bỏ Nhầm Cột Số Học (Trụ cột 3)
*   **Tình huống vỡ trận:** Dùng luật "Lọc cột phân tích dựa trên Cardinality > 95% thì ném bỏ vì đó là UUID". Vô tình, cột `So_Tien_Giao_Dich` tính tới từng đồng lẻ cũng có Cardinality 99%. Hệ thống ngây ngô tự động xóa sạch cột quan trọng nhất của khách hàng trước khi tính tương quan.
*   **Guardrail Bắt Buộc:** Luật Cardinality > 95% PHẢI ĐƯỢC BỌC LẠI bởi bộ kiểm tra Kiểu dữ liệu (Dtype checker). Nếu Dtype là `TEXT/STRING/OBJECT` $\rightarrow$ Áp dụng luật (Xóa). Nếu Dtype là `NUMERIC` hoặc `DATETIME` $\rightarrow$ Bỏ qua luật, giữ lại phân tích bằng mọi giá.

### 3.5. Chốt chặn OOM bằng Streaming Scanner (Trụ cột 4)
*   **Tình huống vỡ trận:** Dùng lệnh `pd.read_csv("5_ty_dong.csv")` để lấy danh sách Khóa Chính phục vụ việc Integrity Check. RAM 16GB bị tràn ngay lập tức.
*   **Guardrail Bắt Buộc:** Đối với tệp dữ liệu khổng lồ, luồng check Khóa bắt buộc phải dùng `KeyColumnScanner` đọc theo cơ chế Streaming (`chunksize=100000`). Chỉ lưu các giá trị ID vào cấu trúc dữ liệu Hash set để đối chiếu, tuyệt đối không nạp nguyên cái DataFrame lên RAM.

### 3.6. Chốt chặn Leo thang Lỗi sai lệch (Compound Escalation) (Trụ cột 5)
*   **Tình huống vỡ trận:** Một cột bị 1 lỗi INFO (VD: Text dài) và 1 lỗi HIGH (VD: Lệch kiểu dữ liệu). Module `compound.py` tự động cộng dồn gán nhãn lại cả 2 lỗi này thành CỰC KỲ NGHIÊM TRỌNG (Critical). LLM đọc vào tưởng cột này bị 2 lỗi Critical, hoảng loạn viết báo cáo cảnh báo khẩn cấp sai sự thật.
*   **Guardrail Bắt Buộc:** Tách bạch 2 khái niệm: `Finding Severity` (Mức độ tĩnh của từng bệnh) và `Column Effective Severity` (Mức độ nguy kịch tổng quát của bệnh nhân). Khi in ra báo cáo cho LLM, LLM chỉ được phép phân tích dựa trên `Finding Severity` gốc để đánh giá đúng bản chất của từng loại lỗi.
