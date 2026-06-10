# Kế hoạch Nâng cấp Kiến trúc: Smart EDA v3.0 (Master Plan)

Tài liệu này phân tích các vấn đề chiến lược do đội ngũ đưa ra, trình bày qua màn phản biện giữa các AI Agents (Chuyên gia Dữ liệu, Kiến trúc sư Hệ thống, và Product Owner) để đi đến giải pháp tối ưu nhất. Nhằm mang lại góc nhìn hệ thống và mạch lạc nhất, 7 vấn đề rời rạc trước đây đã được chúng tôi tái cấu trúc và cô đọng thành **5 Trụ cột Chiến lược**.

Phiên bản này đi sâu giải phẫu cặn kẽ bản chất, gốc rễ của kiến trúc **Dual-Pass Profiling (Đánh giá Đa bảng)** nhằm làm tài liệu chuẩn mực cho đội ngũ phát triển.

---

## Trụ cột 1: Xóa bỏ Nút thắt Cổ chai Vision LLM (Nguyên bản: Vấn đề 1)

*Tình trạng hiện tại:* Kiến trúc Layer 4 dự kiến gửi ảnh biểu đồ cho LLM đọc và viết báo cáo.
*   **Agent (Cost-Optimizer):** Việc gửi ảnh base64 qua API LLM (như GPT-4o) cực kỳ tốn kém token (giá gấp 3-4 lần text), tốc độ phản hồi chậm đi 50%. Quan trọng hơn, LLM rất hay "ảo giác" (hallucinate) khi đọc biểu đồ phức tạp (ví dụ: đọc sai các điểm outlier trên scatter plot).
*   **Agent (Data Architect):** Nguyên tắc cốt lõi của chúng ta là "Deterministic-First". Toàn bộ thông số chính xác 100% đã nằm trong tệp JSON. LLM không cần phải nhìn ảnh để biết cột A có outlier.
*   **Kết luận tối ưu:** **Tuyệt đối loại bỏ Vision LLM.** 
    *   LLM chỉ nhận Input là file JSON (Text). LLM sẽ viết báo cáo phân tích dựa trên các con số trong JSON. Khi viết xong, LLM sẽ xuất ra một mã lệnh định sẵn (ví dụ: `[CHART_OUTLIER_AGE_SALARY]`). 
    *   Một đoạn code Python (Layer 3.5) sẽ đọc báo cáo của LLM, tự động sinh ra biểu đồ bằng Matplotlib/Plotly, và chèn trực tiếp đường dẫn ảnh thay thế vào vị trí mã lệnh đó.

> 🚨 **CẢNH BÁO TỪ KIỂM TOÁN (AUDIT & GUARDRAILS)**
> *   **Lỗi nghiêm trọng (Critical):** Rủi ro Path Traversal. Nếu LLM tự do sinh mã `[CHART_XYZ]`, hacker có thể lừa LLM đọc file hệ thống.
> *   **Giải pháp MVP:** Cấm LLM sinh mã yêu cầu tạo Chart mới. Báo cáo L4 chỉ được tham chiếu các `artifact_id` ĐÃ TỒN TẠI trong `ArtifactManifest`.
> *   **Overengineer cần tránh:** Cố gắng chuyển ảnh tĩnh (PNG) thành dạng JSON Plotly tương tác. Mất thời gian code Frontend, không cần thiết cho MVP. Cứ dùng ảnh tĩnh PNG.

---

## Trụ cột 2: Tự động phát hiện Schema (Auto-Discovery) với Phễu lọc 2 tầng (Nguyên bản: Vấn đề 2 & 3)

*Tình trạng hiện tại:* Hệ thống không có khả năng tự suy luận liên kết đa bảng nếu người dùng không cung cấp file thiết kế CSDL (DBML/DDL).
*Mục tiêu:* Thiết kế một cơ chế quét tự động để ghép nối các bảng dựa trên độ trùng lặp dữ liệu và ngữ nghĩa tên cột. Tuy nhiên, việc đẩy toàn bộ các cặp cột qua LLM để kiểm tra chéo sẽ tạo ra một bài toán tổ hợp khổng lồ, gây nghẽn cổ chai hiệu năng và bùng nổ chi phí API.

*Giải pháp kiến trúc: Xây dựng module `src/engines/auto_schema.py` theo quy trình phễu lọc 2 tầng (Rule-first, LLM-second):*
1.  **Bước 1: Lọc thô bằng Toán học (Rule-based Jaccard Index)**
    Thay vì dùng LLM ngay từ đầu, code Python sẽ tự động tính toán **Độ giao thoa tập hợp (Jaccard Index)** trên tập giá trị của các cột có cùng kiểu dữ liệu giữa 2 bảng.
    *Ví dụ:* Lấy tập hợp các giá trị unique của `table1.id` giao với `table2.id_school`. Nếu tỷ lệ trùng lặp giá trị $> 50\%$, cặp này được đánh dấu lọt vào danh sách "Ứng viên Khóa ngoại". Bằng cách này, ta loại bỏ được 95% các cặp cột không liên quan bằng toán học với tốc độ siêu nhanh (miễn phí).
2.  **Bước 2: Chốt hạ ngữ nghĩa bằng LLM (Semantic Verification)**
    Hệ thống chỉ gửi danh sách "Ứng viên Khóa ngoại" đã được rút gọn ở Bước 1 (kèm theo tên cột và 5 dòng dữ liệu mẫu) cho LLM (GPT-4o-mini).
    *Prompt mẫu:* "Dựa vào ngữ nghĩa nghiệp vụ, `id` của bảng student và `id_school` của bảng class có mối liên hệ Khóa chính - Khóa ngoại không?"
3.  **Bước 3: Khởi tạo Schema Ảo (Virtual Schema)**
    Từ kết quả của LLM, hệ thống tự động sinh ra một cây cấu trúc Schema ảo (tương đương với một file DBML) và lưu vào bộ nhớ RAM. Cấu trúc này sẽ được chuyển trực tiếp cho `schema_engine.py` và `auto_join.py` để thực hiện các nghiệp vụ đánh giá đa bảng như bình thường.

> 🚨 **CẢNH BÁO TỪ KIỂM TOÁN (AUDIT & GUARDRAILS)**
> *   **Lỗi nghiêm trọng (Critical):** Dùng Jaccard Index làm chỉ số chính sẽ sai hoàn toàn với Khóa tự tăng (Surrogate Keys). Ví dụ ID 1-100 của Users trùng 100% với ID 1-100 của Products.
> *   **Giải pháp MVP:** Bỏ Jaccard. Chuyển sang dùng **Value Coverage (Độ phủ giá trị)**. Nhánh code hiện tại ĐÃ CÓ sẵn các hàm này ở `schema_engine.py`, KHÔNG CẦN đẻ thêm file `auto_schema.py` mới, chỉ cần refactor chia nhỏ file.
> *   **Overengineer cần tránh:** Dùng LLM để "chốt hạ" schema. Việc này gây ảo giác (hallucination) và tốn kém API. Mọi logic Khóa ngoại phải chạy bằng code toán học 100% (Deterministic).

---

## Trụ cột 3: Nâng cấp Đánh giá đa bảng (Giải phẫu kiến trúc Dual-Pass Profiling) (Nguyên bản: Vấn đề 4)

#### 3.1. Bản chất vấn đề: Tại sao không gộp chung (JOIN) tất cả rồi tính một lần?
Gộp toàn bộ CSDL lại thành một bảng khổng lồ (Universal Table) để chạy ydata-profiling là một **tối kỵ trong Data Engineering**, vì 2 lý do:
1.  **Thảm họa nổ RAM (OOM):** Khâu nặng nhất của Profiling là tính Tương quan (Correlation Matrix) với độ phức tạp $O(N^2)$. Nếu gộp 5 bảng tạo ra một bảng 200 cột, số cặp cần so sánh là $200 \times 200 = 40,000$ cặp. Máy chủ 16GB RAM chắc chắn sẽ treo.
2.  **Sai lệch Phân phối Thống kê (Statistical Skew):** Khi JOIN bảng Giao dịch (Fact) với bảng Khách hàng (Dimension), dữ liệu Khách hàng sẽ bị **nhân bản (duplicate)** lên tương ứng với số giao dịch. Một người mua 100 đơn hàng sẽ khiến độ tuổi của họ xuất hiện 100 lần. Nếu để hệ thống tính lại Độ tuổi trung bình (Mean) trên bảng gộp này, kết quả sẽ hoàn toàn sai lệch so với phân phối độ tuổi gốc.

#### 3.2. Giải pháp cốt lõi: Quy trình 2 lượt (Dual-Pass Profiling)
Dựa trên trực giác sắc bén của Product Owner, chúng ta sẽ tách biệt việc tính toán thông số cơ bản và tính tương quan chéo thành 2 quy trình song song:

**LƯỢT 1: SINGLE-TABLE PASS (Đảm bảo độ chuẩn xác 100% của từng thông số)**
Hệ thống giữ nguyên việc chạy `ydata-profiling` ở chế độ Full Mode độc lập cho từng bảng. Vì không có sự can thiệp của JOIN, mọi thông số như Mean, Median, Missing Count, Histograms, Outliers của từng cột được bảo toàn chính xác tuyệt đối.

**LƯỢT 2: CROSS-TABLE CORRELATION PASS (Thiết lập bảng phụ tập trung)**
Ở lượt này, mục tiêu duy nhất là tính hệ số tương quan chéo. Quy trình diễn ra qua 4 bước khắt khe:

**Bước 2.1. Tìm kiếm Bảng Fact Trung tâm (The Fact Score Algorithm)**
*Bản chất:* Ta cần một cái trục (Bảng giao dịch chính) để đính kèm dữ liệu từ các bảng vệ tinh vào.
Hệ thống sử dụng **Thuật toán Lai (Hybrid Scoring)** để tự động tìm ra bảng này nhằm hạn chế sai sót:
*   **Trọng số Heuristic:** Bảng có số lượng dòng lớn nhất được cộng điểm (+40 điểm). Bảng có chứa các cột thời gian (`created_at`) được cộng điểm (+10) vì Fact thường lưu lịch sử giao dịch.
*   **Trọng số Đồ thị (Graph Theory):** Quy CSDL về đồ thị DAG. Bảng nào trỏ ra nhiều bảng khác (Out-degree cao) được cộng điểm (+30). Bảng bị nhiều bảng trỏ tới (In-degree cao) bị trừ điểm (-20) do đó là bảng Dimension.
*   *Lỗ hổng của Toán học:* Toán học dễ bị đánh lừa bởi **Bridge table** (bảng nối nhiều-nhiều) vì bảng này có Out-degree cực cao nhưng không có ý nghĩa phân tích.
*   **Chốt hạ bằng LLM Semantic:** Hệ thống lấy Top 3 bảng điểm cao nhất, gửi cho LLM đọc tên. Dựa vào kiến thức kinh doanh, LLM sẽ nhận ra bảng `Orders` mang ý nghĩa phân tích cốt lõi hơn bảng `User_Role_Mapping` (Bridge table). Bảng chiến thắng sẽ làm mốc gộp dữ liệu.

**Bước 2.2. Lọc cột phân tích dựa trên Cardinality (Độ phân tán)**
*Bản chất:* Không phải cột nào mang sang bảng phụ cũng có ích. Cột ID rác hoặc Text tự do dài dòng sẽ làm nát thuật toán Phik Correlation.
*Quy tắc lọc:* Chúng ta **KHÔNG lọc theo độ dài chuỗi Text**, mà lọc theo **Cardinality (Tính độc nhất)**.
*   Tính tỷ lệ: `Cardinality Ratio = Số giá trị phân biệt / Tổng số dòng`.
*   Nếu `Ratio > 95%`: (Ví dụ cột UUID, cột Ghi chú khách hàng tự gõ). Dòng nào cũng khác dòng nào. Lập tức gạt bỏ khỏi danh sách ghép. Đưa chúng vào tính tương quan chỉ sinh rác và tốn RAM.
*   Nếu `Ratio < 95%`: (Ví dụ cột "Mô tả trạng thái", Text tuy dài nhưng lặp lại tạo thành nhóm). GIỮ LẠI. Nó rất có giá trị thống kê phân loại (Categorical).

**Bước 2.3. Tạo bảng phụ theo cơ chế Targeted Denormalization (LEFT JOIN)**
*Bản chất:* Tạo duy nhất MỘT bảng phụ siêu gọn nhẹ.
*   Hệ thống lấy Bảng Fact lõi làm gốc.
*   Sử dụng lệnh **`LEFT JOIN`** kéo các cột đã vượt qua vòng lọc Cardinality từ các bảng Dimension đính kèm trực tiếp vào bảng Fact.
*   *Tại sao phải là LEFT JOIN?* Tránh làm mất dữ liệu. Nếu dùng `INNER JOIN`, các Hóa đơn không có thông tin Khách hàng (Khóa ngoại mồ côi) sẽ bị xóa mất, làm sai lệch phân phối hóa đơn. `LEFT JOIN` bảo toàn 100% dòng của bảng Fact, thiếu thông tin thì để Null.

**Bước 2.4. Tính toán Tương quan chéo**
Đưa duy nhất cái "Bảng phụ siêu gọn nhẹ" này vào thư viện để tính Ma trận Tương quan (Correlation Matrix). Kết quả xuất ra sẽ chỉ đích danh mối liên hệ giữa các cột chéo bảng một cách hoàn hảo và đính kèm vào báo cáo JSON Lượt 1.

> 🚨 **CẢNH BÁO TỪ KIỂM TOÁN (AUDIT & GUARDRAILS)**
> *   **Lỗi nghiêm trọng 1 (Nổ RAM):** Khi LEFT JOIN, nếu Khóa Dimension không Unique, 1 dòng Fact sẽ tự nhân bản làm nổ tung Server (Fan-out).
> *   **Lỗi nghiêm trọng 2 (Xóa nhầm cột):** Áp dụng luật "Cardinality > 95% thì xóa" sẽ vô tình xóa sạch mọi cột Tiền tệ và Ngày tháng.
> *   **Giải pháp MVP:** 
>     - **Safe Join Rule:** Trước khi JOIN, kiểm tra Khóa. Nếu KHÔNG Unique -> Hủy JOIN ngay lập tức và báo lỗi `NON_UNIQUE_JOIN_KEY`. Thà mất insight chéo còn hơn làm sai dữ liệu và chết server.
>     - **Lọc theo Dtype:** Chỉ áp dụng luật Cardinality > 95% cho kiểu TEXT. Kiểu số (Numeric) và Ngày tháng (Datetime) phải giữ lại vô điều kiện.
> *   **Overengineer cần tránh:** Tự động sửa lỗi JOIN bằng lệnh gom nhóm `groupby().first()`. Việc này che giấu lỗi DB của khách hàng. Thà từ chối phân tích chéo (Fail-fast) còn hơn phân tích sai.

---

## Trụ cột 4: Chiến lược Profiling & Quản trị Lấy mẫu (Sampling) An Toàn (Gộp Vấn đề 5, 7.1, 7.2)

*Tổng quan:* Để khai thác sức mạnh của Profiling, chúng ta cần chạy Full Mode. Nhưng để hệ thống không sập khi xử lý dữ liệu khổng lồ (>500k dòng), ta cần cơ chế bốc mẫu (Sampling). Tuy nhiên, việc cắt mẫu bừa bãi sẽ sinh ra những "hạt sạn" chết người về Khóa ngoại và Metadata. 

Dưới đây là màn phản biện để đi đến luồng xử lý "Tải dữ liệu 2 pha" (Two-Phase Loading) nhằm giải quyết triệt để sự xung đột này.

### Phần A: Chế độ Minimal vs Full của ydata-profiling (Vấn đề 5)
*Tình trạng hiện tại:* Đang chạy Minimal mode khiến mất đi các thông số tương quan quan trọng (Phik, Spearman, Text analysis).
*   **Product Owner:** Không được hi sinh chất lượng lấy tốc độ. Các thông số này cần thiết cho nhiều lĩnh vực. Dữ liệu 60.000 dòng vẫn chạy rất ổn. Máy tính hiện đại không bị giới hạn 16GB RAM.
*   **Kết luận tối ưu:** 
    *   **Bật Full Mode (`minimal=False`) mặc định** cho toàn bộ pipeline ở Lượt 1 để khai thác tối đa sức mạnh phân tích, cung cấp dữ liệu sâu nhất cho LLM viết báo cáo.
    *   **Chốt chặn an toàn (Smart Sampling):** Vẫn giữ cơ chế bốc mẫu ngẫu nhiên (chỉ kích hoạt nếu file vượt ngưỡng siêu khổng lồ, ví dụ > 500,000 dòng). Bằng cách này, ta vừa giữ được báo cáo đỉnh cao, vừa không lo cháy máy.

### Phần B: Hạt sạn Lấy mẫu phá kiểm tra khoá ngoại (Fake Orphan-FK) (Vấn đề 7.1)
*   **Vấn đề:** Mọi bảng >500k dòng bị lấy mẫu *trước khi* kiểm tra đa bảng.
*   **Agent (Data Engineer):** Nếu không lấy mẫu, máy chủ 16GB sẽ sập khi xử lý bảng 10 triệu dòng. Bắt buộc phải sample ở Layer 0.
*   **Agent (System Architect):** Nhưng anh lấy mẫu ngẫu nhiên! Nếu dòng `Parent` bị loại mà dòng `Child` được giữ, hệ thống sẽ báo lỗi `Orphan-FK` giả mạo. Điều này phá nát độ tin cậy của báo cáo Schema.
*   **Kết luận tối ưu:** **Tách biệt 2 luồng nạp dữ liệu (Two-phase Loading).**
    *   **Luồng Integrity Check:** Tải *toàn bộ* dữ liệu nhưng **CHỈ tải các cột Khóa (ID)** để check Schema và FK (rất nhẹ RAM). Không bao giờ lấy mẫu khi check Integrity.
    *   **Luồng Profiling:** Lấy mẫu ngẫu nhiên (Sample) trên toàn bộ cột để tính toán thống kê (Mean, Median, Outlier).

### Phần C: Hạt sạn Lấy mẫu âm thầm (Silent Sampling) (Vấn đề 7.2)
*   **Vấn đề:** Báo cáo ghi `n = 500,000` nhưng không nói rõ đây là dữ liệu đã cắt mẫu. User lầm tưởng tổng dữ liệu chỉ có vậy.
*   **Agent (Data Scientist):** Đây là một hành vi "nói dối" về mặt thống kê. Khách hàng thấy "Missing 10%" sẽ nghĩ là thiếu 50.000 dòng, trong khi gốc là 10 triệu dòng (tức thiếu 1 triệu dòng).
*   **Kết luận tối ưu:** Cập nhật schema `DatasetMeta` trong `models.py`. Phải lưu đủ 3 biến: `is_sampled` (Boolean), `original_n` (Số dòng gốc), và `sample_n` (Số dòng đã lấy mẫu). LLM phải được prompt để luôn nhắc nhở user: *"Kết quả thống kê được nội suy từ tập mẫu 500k dòng."*

> 🚨 **CẢNH BÁO TỪ KIỂM TOÁN (AUDIT & GUARDRAILS)**
> *   **Lỗi nghiêm trọng (Critical):** Dùng lệnh `pd.read_csv()` để tải toàn bộ các cột ID lên RAM để check Integrity sẽ làm sập Server nếu file nặng vài tỷ dòng.
> *   **Giải pháp MVP:** Đưa vào cơ chế `KeyColumnScanner`, quét dữ liệu dạng luồng (Streaming) theo từng khối (`chunksize`).
> *   **Overengineer cần tránh:** Chuyển sang dùng Lấy mẫu phân tầng (Stratified Sampling). Nó đòi hỏi quét file tính toán tỷ lệ rất tốn I/O. Cứ dùng Random Sampling và gắn cờ `is_sampled=True` là đủ cho MVP.

---

## Trụ cột 5: Đại tu Tầng Severity Stack & Hợp nhất Báo cáo JSON (Gộp Vấn đề 6, 7.3, 7.4, 7.5, 7.6)

*Tổng quan:* Tầng L2.5 (Severity Stack) với các module `calibrator.py`, `missingness.py`, `compound.py` thực hiện rất nhiều logic đánh giá cực kỳ đắt giá. Tuy nhiên, luồng đi của dữ liệu đang có những lỗ hổng toán học, logic cộng dồn sai lệch, và cuối cùng là vứt bỏ mọi Insight ra khỏi file `dataset_verdict.json` cũng như `data_quality_findings.json`.

Dưới đây là các đợt "đại phẫu" để biến tầng L2.5 thành một cỗ máy lâm sàng hoàn chỉnh và hợp nhất 2 file JSON thành Nguồn Sự Thật Duy Nhất (Single Source of Truth).

### Phần A: Thiếu insight trong file `dataset_verdict.json` (Vấn đề 6)
*Lỗ hổng kiến trúc:* Khi đến module `aggregator.py`, tất cả insight tuyệt vời (Cơ chế MNAR, Lỗi kép...) bị gạt bỏ. Hệ thống chỉ đếm số lượng lỗi (Ví dụ: 2 CRITICAL) để ghi vào `dataset_verdict.json`. Hậu quả là LLM ở L4 khi đọc file verdict chỉ thấy "Dữ liệu NOT_READY vì có 2 lỗi CRITICAL" mà không biết đó là lỗi gì, ở cột nào, có cơ chế MNAR hay không. Nó không có đủ nguyên liệu để viết một báo cáo sâu sắc.
*Định hướng Chỉnh sửa Kiến trúc:*
Ta sẽ viết lại schema `DatasetVerdict` trong `src/ontology/models.py` và luồng xử lý trong `src/severity/aggregator.py`. Thay vì chỉ giữ lại các con số đếm (summary), ta sẽ thêm một trường `issues_breakdown` (Phân rã lỗi) trực tiếp vào trong `DatasetVerdict`. Trường này sẽ là một bộ lọc (Dictionary), nhóm tất cả các `AnomalyRecord` và `IntegrityError` theo mức độ nghiêm trọng (CRITICAL, HIGH, WARN). Nhờ vậy, `dataset_verdict.json` trở thành một **Báo cáo Chẩn đoán Lâm sàng** hoàn chỉnh, đủ mọi insight để LLM viết báo cáo cuối mà không cần tra cứu ngược.

### Phần B: Hạt sạn Hai file JSON báo cáo lệch nhau (Vấn đề 7.3)
*   **Vấn đề:** Tầng `calibrator.py` tính ra Severity rất hay cho từng cột. Nhưng nó chỉ dùng để "đếm" trong `dataset_verdict.json`. File `data_quality_findings.json` (nơi lưu chi tiết cột) lại không hề chứa Severity này.
*   **Agent (System Architect):** Lỗi kiến trúc phân mảnh! Code L2.5 sinh ra insight nhưng không map ngược lại vào object `ColumnStats` của L1. LLM đọc file DQ Findings sẽ bị "mù" mức độ nghiêm trọng.
*   **Kết luận tối ưu:** Biến `data_quality_findings.json` thành **Single Source of Truth**. Khi `calibrator.py` tính xong mức độ nghiêm trọng của cột A, nó phải ghi trực tiếp object `Severity` vào lại thông tin của cột A trong `data_quality_findings.json`.

### Phần C: Hạt sạn Lỗi kép bị thổi phồng + Dán nhãn sai (Compound Escalation Bug) (Vấn đề 7.4)
*   **Vấn đề:** Khi một cột có nhiều lỗi, `compound.py` nâng mức **TẤT CẢ** các lỗi trong cột đó lên mức cao nhất (Ví dụ: Cột có 1 lỗi HIGH và 1 lỗi INFO, cả 2 sẽ bị biến thành CRITICAL). Lỗi INFO bị đếm phồng.
*   **Agent (Data Scientist):** Sai lầm logic! Anh không thể bắt một người bị "Cảm cúm" (INFO) đi cấp cứu chỉ vì họ vô tình ở chung phòng với người bị "Đột quỵ" (CRITICAL).
*   **Kết luận tối ưu:** Phân tách khái niệm **`Finding Severity`** (Mức độ của lỗi đơn lẻ - giữ nguyên không đổi) và **`Column Effective Severity`** (Mức độ tổng quát của cả cột - được phép leo thang). `compound.py` chỉ được cập nhật `Column Effective Severity`.

### Phần D: Phân loại "Kiểu thiếu dữ liệu" (Missingness) đánh đồng mọi cột (Vấn đề 7.5)
*   **Vấn đề:** Module `missingness.py` chạy test Little's MCAR trên toàn dataframe, ra 1 cái p-value chung, rồi gán nhãn đó cho... TẤT CẢ các cột bị thiếu dữ liệu.
*   **Agent (Data Scientist):** Khủng khiếp! Cột `Tuổi` có thể bị thiếu có chủ đích (MNAR), nhưng cột `Email` thiếu ngẫu nhiên (MCAR). Áp chung 1 p-value là sai hoàn toàn về mặt Toán học.
*   **Kết luận tối ưu:** Thay đổi thuật toán `missingness.py`.
    *   **Bỏ Little's MCAR tổng.**
    *   **Dùng Dummy Variable Correlation:** Tạo cột `is_missing_A` (1 nếu A Null, 0 nếu không). Tính tương quan của cột này với các cột khác. Nếu `is_missing_A` có tương quan mạnh với cột `Salary`, thì cột A bị thiếu theo cơ chế MAR (Missing at Random - phụ thuộc biến khác). Nếu không tương quan ai: MCAR. Tính riêng cho từng cột!

### Phần E: Hạt sạn Phán quyết bỏ qua mức WARN (Vấn đề 7.6)
*   **Vấn đề:** 50 lỗi WARN (Cảnh báo) vẫn cho ra phán quyết Dataset là **READY**.
*   **Agent (Product Owner):** Quá lỏng lẻo. Một chiếc xe xước 1 vết thì còn chạy được, chứ xước 50 vết, lốp xì hơi 50 chỗ thì không thể dán mác READY được.
*   **Kết luận tối ưu:** Thiết lập **Ngưỡng quy đổi (Threshold Rule)** trong `aggregator.py`. Ví dụ: `Nếu số lượng WARN > 10` HOẶC `WARN > 20% tổng số cột` $\rightarrow$ Tự động leo thang Phán quyết chung (Dataset Verdict) thành **WARN** (Review before use).

*Mẫu Output (Sample JSON) mới của `dataset_verdict.json`:*
```json
{
  "dataset_meta": {
    "dataset_name": "Ecommerce_Data",
    "total_rows": 100000,
    "total_columns": 15
  },
  "verdict": "NOT_READY",
  "verdict_rationale": "2 CRITICAL finding(s) — data not ready for use. 1 HIGH finding(s).",
  "summary": {
    "total_issues": 3,
    "critical": 2,
    "high": 1,
    "warn": 0,
    "info": 0
  },
  "issues_breakdown": {
    "CRITICAL": [
      {
        "issue_type": "MISSINGNESS_ESCALATED",
        "affected_table": "transactions",
        "affected_column": "customer_age",
        "severity": "HIGH",
        "compound_severity": "CRITICAL",
        "missingness_mechanism": "MNAR",
        "description": "Cột customer_age thiếu 65% dữ liệu. Cơ chế MNAR (Thiếu có chủ đích). Đã bị leo thang lên mức CRITICAL do cột này đồng thời chứa 30% giá trị Zeros.",
        "disposition": "Reject Column",
        "dq_dimensions": ["Completeness", "Accuracy"]
      },
      {
        "issue_type": "PK_DUPLICATE",
        "affected_table": "users",
        "affected_column": "user_id",
        "severity": "CRITICAL",
        "compound_severity": null,
        "missingness_mechanism": null,
        "description": "Khóa chính user_id chứa 150 giá trị trùng lặp. Vi phạm tính toàn vẹn dữ liệu nghiêm trọng.",
        "disposition": "Cleanse Rows",
        "dq_dimensions": ["Uniqueness"]
      }
    ],
    "HIGH": [
      {
        "issue_type": "OUTLIER_ENSEMBLE",
        "affected_table": "transactions",
        "affected_column": "total_amount",
        "severity": "HIGH",
        "compound_severity": null,
        "missingness_mechanism": null,
        "description": "Phát hiện 205 dòng ngoại lai (Outliers) dựa trên thuật toán Ensemble (IForest+ECOD+LOF) với Z-score > 3.0.",
        "disposition": "Review Required",
        "dq_dimensions": ["Validity"]
      }
    ],
    "WARN": [],
    "INFO": []
  }
}
```

> 🚨 **CẢNH BÁO TỪ KIỂM TOÁN (AUDIT & GUARDRAILS)**
> *   **Lỗi nghiêm trọng (Critical):** Việc nhồi nhét toàn bộ chi tiết 1000 lỗi vào `dataset_verdict.json` (`issues_breakdown`) sẽ làm file phình to, lãng phí Token và làm LLM bị ngợp.
> *   **Giải pháp MVP:** Cấu trúc lại file `dataset_verdict.json` cho cực kỳ gọn nhẹ. Chỉ tạo một mảng `top_issues` chứa tóm tắt các lỗi nghiêm trọng nhất, đính kèm đường link (`detail_ref`) trỏ về file Finding gốc chứa chi tiết. Dùng **Mật độ lỗi (Issue Density)** kết hợp với các Hard-blockers (như Trùng khóa chính) để định đoạt phán quyết.
> *   **Overengineer cần tránh:** Thay thế thuật toán Logistic Regression hiện có bằng Dummy Correlation để tìm Missingness. Code nhánh hiện tại đang đúng và xịn hơn, KHÔNG đổi thuật toán.

---

## Đề xuất Kế hoạch Triển khai (Implementation Steps)

1.  **Bước 1: Nâng cấp Profiling Engine & Tách luồng Sampling (Trụ cột 4)**
    - Tắt cờ `minimal=True`, chuyển sang Full Mode.
    - Cập nhật Data Loader để chỉ lấy mẫu lúc Profiling. Check Schema/Integrity trên Data gốc (hoặc tải riêng các cột Khóa). Thêm `is_sampled` vào `DatasetMeta`.
2.  **Bước 2: Sửa luồng JSON & Hợp nhất Severity (Trụ cột 5)**
    - Viết lại `aggregator.py` và `compound.py` để nhúng `issues_breakdown`.
    - Phân tách `Finding Severity` và `Column Effective Severity`. Đưa Severity vào chung file Findings.
3.  **Bước 3: Đại tu Missingness & Threshold (Trụ cột 5)**
    - Thay thế thuật toán MCAR tổng bằng thuật toán Dummy Correlation trên từng cột.
    - Setup ngưỡng quy đổi WARN -> Dataset Verdict trong `aggregator.py`.
4.  **Bước 4: Xây dựng Auto-Discovery Engine (Trụ cột 2)**
    - Viết logic Rule-based Jaccard Index và tích hợp Mini-LLM chốt hạ.
5.  **Bước 5: Xây dựng Auto-Join & Cross-table Engine (Trụ cột 3)**
    - Triển khai thuật toán **Fact Score**, thực hiện **LEFT JOIN** và tính Correlation.
6.  **Bước 6: Thiết kế lại luồng LLM (Trụ cột 1)**
    - Gỡ bỏ LLM Vision, thay bằng cơ chế chèn ảnh qua Placeholder trong báo cáo cuối.

> 🚨 **ĐIỀU CHỈNH KẾ HOẠCH TRIỂN KHAI (CẬP NHẬT TỪ BẢN REVIEW CỦA TEAM)**
> Kế hoạch 6 bước trên là bản nháp đầu tiên. Sau khi Audit, chúng ta **không áp dụng** nó mà chuyển sang Lộ trình MVP cực kỳ thực dụng sau đây:
> 1. **Làm giàu Verdict:** Cấu trúc lại `dataset_verdict.json` với `top_issues` và `detail_ref` thay vì nhồi nhét.
> 2. **Refactor Schema Engine:** Không đẻ thêm `auto_schema.py`. Cấu trúc lại `schema_engine.py` thành các class có locality tốt hơn. Đổi sang thuật toán Value Coverage.
> 3. **Thêm Cross-Table Deterministic:** Code `auto_join.py` với luật `Safe Join Rule` (Chặn JOIN rác), bắt buộc giữ lại cột Số (Numeric).
> 4. **Quản trị rủi ro OOM:** Thêm `KeyColumnScanner` đọc theo `chunksize` cho file khổng lồ.
> 5. **Hoàn thiện Guardrail L4:** Báo cáo 100% Text-only, cấm LLM sinh chart mới.
