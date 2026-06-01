# Giải Thích Chi Tiết Kiến Trúc Hệ Thống (Deep Dive)

Tài liệu này tổng hợp lại các giải thích chi tiết, phi kỹ thuật (non-technical) và trực quan nhất về cách thức hoạt động bên dưới nắp ca-pô của 4 Layer trong hệ thống Auto Data-Profiling & Smart EDA (Exploratory Data Analysis - Khám phá Dữ liệu) Report. 

Bằng cách sử dụng các phép ẩn dụ thực tế, tài liệu này giúp giải đáp các thắc mắc chuyên sâu về logic vận hành của các thuật toán và nguyên lý thiết kế, đặc biệt là lý do tại sao chúng ta tuân thủ nghiêm ngặt nguyên tắc **"Deterministic-First, LLM-Last"** (Ưu tiên tính xác định bằng Toán học/Code trước, sử dụng Large Language Model - Mô hình Ngôn ngữ Lớn sau cùng).

---

## 1. Layer 2: Khám chuyên sâu (Anomaly Detection & Multi-table)

### 1.1 Tại sao lại cần Layer 2 trong khi đã có Layer 1?
Layer 1 (`ydata-profiling`) rất giỏi trong việc phân tích **từng cột một (Univariate)**. Ví dụ: nó có thể phát hiện một người cao 2.5m (rất bất thường ở cột Chiều Cao) hoặc một người nặng 10kg (rất bất thường ở cột Cân Nặng). 

Nhưng nếu có một người cao 1.6m và nặng 150kg thì sao? Nhìn riêng lẻ, 1.6m là bình thường và 150kg cũng có thể tồn tại. Nhưng **kết hợp cả 2 yếu tố lại**, tỷ lệ cơ thể đó là một sự dị biệt nghiêm trọng. Layer 1 không nhìn ra được điều này vì nó hiếm khi phân tích chéo nhiều cột. Đó là lúc ta cần **Layer 2 — Khám chuyên sâu Đa biến (Multivariate Anomaly Detection)**.

### 1.2 Nhiệm vụ 1: Phát hiện Dị biệt Đa biến (PyOD Ensemble)
Hãy coi tập dữ liệu (Dataset) như một đám đông người và nhiệm vụ của Layer 2 là tìm ra những **kẻ dị biệt (Outliers)** — những người có hành vi hoặc đặc điểm hoàn toàn lạc lõng so với phần lớn đám đông còn lại.

Để đảm bảo kết quả chính xác và không bị "báo động giả", Layer 2 không chỉ dùng 1 thuật toán, mà sử dụng cơ chế **Ensemble (Hội đồng Bầu chọn)** gồm 3 thuật toán xuất sắc nhất của thư viện PyOD (Python Outlier Detection - Thư viện Phát hiện Dị biệt) hợp lực lại:

1. **Isolation Forest (iForest - Rừng cô lập):** 
   - *Nguyên lý:* Nếu một người bình thường chìm trong đám đông, bạn phải dùng rất nhiều câu hỏi (nhát cắt) mới tách được người đó ra. Nhưng nếu một người đội mũ màu hồng chói lọi đứng giữa đám đông mặc đồ đen, bạn chỉ cần 1 câu hỏi là tách được họ. 
   - *Kết luận:* Điểm nào càng dễ bị "cô lập" nhanh chóng, điểm đó càng có nguy cơ cao là Outlier.
2. **LOF (Local Outlier Factor - Hệ số dị biệt cục bộ):** 
   - *Nguyên lý:* Nếu bạn sống ở thành phố (vùng dữ liệu bình thường), hàng xóm của bạn sẽ ở san sát nhau. Nếu bạn sống ở sa mạc (Outlier), khoảng cách từ bạn đến hàng xóm gần nhất sẽ rất xa. 
   - *Kết luận:* Những điểm nằm ở vùng có "mật độ cục bộ" cực thấp so với hàng xóm của nó sẽ bị đánh dấu là dị biệt.
3. **ECOD (Empirical Cumulative Distribution-based Outlier Detection - Phát hiện dị biệt dựa trên phân phối tích lũy thực nghiệm):** 
   - *Nguyên lý:* Thuật toán ước lượng phân phối thống kê ở vùng "đuôi" (tail distribution). Bất cứ dòng dữ liệu nào có quá nhiều thông số rơi vào "vùng đuôi hiếm gặp" của nhiều cột cùng lúc sẽ bị nghi ngờ.

**Cách hoạt động:** Cả 3 thuật toán cùng quét qua dữ liệu và chấm cho từng dòng một số điểm gọi là **Anomaly Score** (Điểm dị biệt). Điểm của 3 thuật toán được cộng lại và chia trung bình (Average Score). Hệ thống sẽ thiết lập một ngưỡng (ví dụ: Top 5% điểm cao nhất) để ném các dòng này sang cho Layer 3 đóng gói vào JSON.

**Lưu ý quan trọng (Pre-imputation):** Thuật toán PyOD rất "dị ứng" với các ô trống (NaN). Trước khi đưa cho PyOD khám bệnh, hệ thống phải tự động nhân bản dữ liệu, điền tạm Median (Trung vị) vào các lỗ hổng để PyOD không bị "chết đứng". Sau khi khám xong, bản copy này sẽ bị vứt đi, và file gốc vẫn giữ lại các lỗ hổng để báo cáo.

### 1.3 Nhiệm vụ 2: Kiểm tra chéo toàn vẹn tham chiếu (Multi-table DBML)
Nếu PyOD soi mói sự vô lý về mặt Toán học/Thống kê, thì Nhiệm vụ 2 soi mói sự vô lý về mặt **Cấu trúc Quan hệ**. 

*Tình huống thực tế:* Tưởng tượng bạn có 2 danh sách. Bảng 1 (Học sinh) chứa ID Học sinh và ID Lớp học. Bảng 2 (Lớp học) chứa ID Lớp học và Tên Giáo viên. Chuyện gì xảy ra nếu một học sinh ở Bảng 1 ghi `ID Lớp học = 99`, nhưng khi tra sang Bảng 2 thì **không hề tồn tại** lớp nào có ID là 99? 

Đây gọi là **Lỗi toàn vẹn tham chiếu (Referential Integrity Error)** — hay nôm na là dữ liệu bị "mồ côi". Các thuật toán ML (Machine Learning - Học máy) thông thường hoàn toàn "mù" trước loại lỗi này vì nó đòi hỏi phải đối chiếu logic giữa nhiều file với nhau.

**Giải pháp:** Hệ thống sử dụng công cụ **DBML (Database Markup Language)** và thư viện `pydbml`:
- **Bước 1 (Đọc bản đồ):** Thư viện đọc file thiết kế `.dbml` để hiểu quy định: *Cột ID Lớp học ở bảng Học Sinh phải có mặt trong bảng Lớp Học*.
- **Bước 2 (Đi tuần tra):** Code Python (`Pandas`) đóng vai "Cảnh sát khu vực", cầm danh sách lớp học đi kiểm tra từng học sinh. Nếu phát hiện học sinh nào đang ở một Lớp Học "ma", lập tức bắt giữ (ghi log lại).
- **Bước 3 (Xuất báo cáo):** Lỗi này được xuất ra một file riêng biệt có tên là `schema_evaluation_findings.json`.

Nhờ 2 gọng kìm (Toán học của Nhiệm vụ 1 + Logic cấu trúc của Nhiệm vụ 2), Layer 2 tạo ra một chốt chặn cực kỳ mạnh mẽ trước khi nộp kết quả.

---

## 2. Layer 2.5: Tháp Đánh giá Mức độ (Severity Stack)

Sau khi Layer 1 (chỉ ra các bệnh cơ bản) và Layer 2 (chỉ ra các bệnh ung thư/dị biệt) hoàn thành nhiệm vụ, chúng ta có một đống "bệnh án" thô. Nếu chỉ đưa đống bệnh án này cho LLM, nó sẽ bối rối vì không biết bệnh nào nặng, bệnh nào nhẹ (Một cột thiếu 5% có nghiêm trọng bằng thiếu 50% không?).

Layer 2.5 ra đời đóng vai trò như một **Hội đồng Chẩn đoán Y khoa**. Hội đồng này nhận bệnh án thô, đo lường mức độ nguy hiểm, gán nhãn, và đưa ra phán quyết cuối cùng. Hội đồng bao gồm 4 "Bác sĩ chuyên khoa" (4 module Python) hoạt động nối tiếp nhau:

### 2.1 Bác sĩ 1: MCAR/MAR/MNAR Detector (Chuyên gia Phân tích Khuyết thiếu)
Khi có cột bị trống (missing), Bác sĩ 1 sẽ hỏi: **Vì sao nó trống?** Có 3 loại:
- **MCAR (Missing Completely At Random - Khuyết thiếu hoàn toàn ngẫu nhiên):** Máy chủ lưu lỗi mất 20% dữ liệu ngẫu nhiên. Bệnh nhẹ.
- **MAR (Missing At Random - Khuyết thiếu ngẫu nhiên cục bộ):** Dữ liệu trống phụ thuộc vào cột khác (Ví dụ: Nữ giới thường không khai báo cân nặng).
- **MNAR (Missing Not At Random - Khuyết thiếu không ngẫu nhiên / Rất nguy hiểm):** Việc trống liên quan trực tiếp đến giá trị của cột đó (Ví dụ: Người trốn thuế cố tình bỏ trống cột Thu nhập). Nếu tự ý điền trung bình vào đây, ta sẽ phá hỏng mô hình ML. Bác sĩ 1 dùng thuật toán thống kê hạng nặng (Little's test / Logistic Regression) để bắt mạch. *Đặc biệt:* Để tránh việc bác sĩ 1 bị "quá tải" đến mức treo máy khi gặp file 1 triệu dòng do độ phức tạp của thuật toán, bác sĩ này được cấp quyền chỉ bốc ngẫu nhiên (Sampling) 10.000 dòng để xét nghiệm là đủ kết luận cho toàn bộ dữ liệu.

### 2.2 Bác sĩ 2: Calibrator (Chuyên gia Tra bảng Phân loại)
Vị bác sĩ này cầm cuốn "Sổ tay Tiêu chuẩn Y khoa" (`calibrator_table.json`). Bác sĩ so chiếu kết quả để gán mức độ: INFO, WARN, HIGH, CRITICAL. Ví dụ: Cột A thiếu 3% (MCAR) ➡️ **INFO**. Cột B thiếu 20% (MNAR) ➡️ **CRITICAL**. Nhờ vậy, hệ thống luôn đánh giá theo một tiêu chuẩn thống nhất, tránh cảm tính.

### 2.3 Bác sĩ 3: CompoundEscalator (Chuyên gia Cộng gộp Bệnh lý)
Chuyện gì xảy ra nếu một cột dính nhiều bệnh cùng lúc? (Vừa bị Outlier, vừa bị thiếu dữ liệu). 
Bác sĩ 3 sẽ nói: *"Một bệnh thì nhẹ, nhưng hai bệnh tụ lại ở cùng một chỗ thì cơ thể rất yếu"*. Bác sĩ 3 sẽ cộng gộp các mức độ đơn lẻ lại và nâng mức độ chung (Compound Severity) của cột đó lên (Ví dụ lên thành **HIGH** hoặc **CRITICAL**). Đây là cơ chế thông minh giúp phát hiện ra các "ổ bệnh" dữ liệu.

### 2.4 Bác sĩ 4: Aggregator (Viện trưởng — Đưa ra Phán quyết)
Bác sĩ 4 nhìn bao quát toàn bộ dataset để đưa ra 1 trong 3 Phán quyết (Dataset Verdict):
- **READY:** Sạch sẽ, mang đi train AI ngay!
- **WARN:** Có vài lỗi HIGH, cần làm sạch trước khi dùng.
- **NOT_READY:** Dữ liệu có quá nhiều lỗi CRITICAL, phải vứt đi hoặc thu thập lại.

### 🛑 TẠI SAO BƯỚC NÀY KHÔNG GIAO CHO LLM?
Nếu ném dữ liệu cho LLM và hỏi *"Theo mày tập dữ liệu này tốt hay xấu?"*, chúng ta sẽ đối mặt với sự bất định (Non-deterministic). Sáng thứ Hai LLM đang "vui", nó bảo READY. Chiều thứ Ba nó "khó tính", nó bảo NOT_READY. 
**Triết lý Deterministic-First:** Quyền quyết định sinh tử (Tốt hay Xấu) bắt buộc phải thuộc về Toán học / Rule-based (Python). Phán quyết được Code Python khóa cứng vào file `dataset_verdict.json`. Quyền ăn nói (Trình bày lý do tại sao xấu) mới thuộc về LLM. Lúc này LLM bị ép vào thế đã rồi, chỉ được phép diễn giải kết quả từ Python.

---

## 3. Layer 3: Triết lý Thiết kế File JSON (Structured Findings Ontology)

Trong bản thiết kế có nhắc đến: *"Một schema JSON có version, hợp nhất kiểu lỗi (TFDV) + tách metric/constraint (Deequ) + gán chuẩn DAMA-DMBOK / ISO 25012 trên từng finding."* 
Đây là sự chắt lọc tinh hoa từ các ông lớn công nghệ để tạo ra cấu trúc file JSON chuẩn mực nhất ở Layer 3:

### 3.1 "Một schema JSON có version"
Giống như các phần mềm có bản cập nhật v1.0, v2.0... Nếu sau này hệ thống phát triển thêm tính năng, file JSON sẽ thay đổi hình dáng. Việc gắn Version (`{"schema_version": "1.0", ...}`) giúp các hệ thống đọc file JSON cũ không bị lỗi crash khi nhận file mới.

### 3.2 "Hợp nhất kiểu lỗi (TFDV)"
**TFDV** (TensorFlow Data Validation của Google) không bao giờ báo cáo lỗi bằng text tự do (kiểu *"Cột tuổi bị sai"*). Họ đúc mọi lỗi thành **mã lỗi chuẩn hóa (Anomaly Types)**.
Chúng ta học theo Google: Thay vì viết mô tả dài dòng, ta gom mọi lỗi thành các mã cố định (Ví dụ: `OUTLIER_ENSEMBLE`, `DUPLICATE`). Việc này giúp tự động hóa dễ dàng (Ví dụ: Code cứ thấy mã `DUPLICATE` thì tự động gọi lệnh xóa dòng trùng lặp).

### 3.3 "Tách metric/constraint (Deequ)"
**Deequ** (Công cụ Big Data của Amazon) tách bạch hoàn toàn 2 khái niệm:
- **Metric (Đo lường):** Sự thật khách quan (Ví dụ: *"Giá trị max là 150"*).
- **Constraint (Ràng buộc):** Luật lệ con người đặt ra (Ví dụ: *"Tuổi không vượt quá 100"*).
Lỗi sinh ra khi: Metric vi phạm Constraint. File JSON của chúng ta tách bạch rất rõ: Phần `columns` chỉ chứa Metrics, phần `anomalies` chỉ chứa lỗi khi bị vi phạm. Cấu trúc nhờ thế mà cực kỳ mạch lạc.

### 3.4 "Gán chuẩn DAMA-DMBOK / ISO 25012"
**DAMA-DMBOK** (Data Management Body of Knowledge - Cẩm nang Kiến thức Quản trị Dữ liệu) và **ISO 25012** (Tiêu chuẩn quốc tế về chất lượng dữ liệu phần mềm) là những "Kinh thánh" quốc tế quy định các tiêu chuẩn về Quản trị Chất lượng Dữ liệu. Khi bạn nói dữ liệu "tồi", bạn phải chỉ rõ nó tồi ở Chiều (Dimension) nào trong 6 chiều chuẩn mực:
- **Accuracy (Độ chính xác):** Có đúng thực tế không? (VD: Tuổi 200 là sai).
- **Completeness (Độ đầy đủ):** Có bị thiếu không?
- **Consistency (Độ nhất quán):** Có đồng nhất format không?
- **Uniqueness (Độ duy nhất):** Có bị trùng không?
- **Validity (Độ hợp lệ):** Format có chuẩn không?
- **Timeliness (Độ kịp thời):** Dữ liệu có cũ không?

Với mỗi lỗi sinh ra ở Layer 3, chúng ta ép thêm 1 nhãn (Tag). Ví dụ: Lỗi outlier tuổi 150 sẽ được gán nhãn `"dq_dimensions": ["Accuracy"]`. Nhờ vậy, báo cáo của LLM đạt chuẩn chuyên môn kiểm toán.

---

## 4. Layer 4: Đội Ngũ AI & Thanh Bảo Vệ (Multi-Agent & Guardrail)

### 4.1 Cơ chế "Thái nhỏ" dữ liệu (Smart Routing & Batching)
Nếu ném nguyên cuốn "bệnh án" dày cộp cho 1 con AI đọc, nó sẽ viết báo cáo rất ẩu và tốn tiền. Thay vào đó, hệ thống thuê một đội gồm hàng chục "Mini Agent".
- **Lọc bệnh (Severity Filtering):** Bỏ qua những cột khỏe mạnh, chỉ giao cho Agent xử lý những cột có bệnh (WARN trở lên).
- **Gộp nhóm (Batching):** Gom 5 bệnh nhân bị chung bệnh (ví dụ: Khuyết thiếu) giao cho 1 Agent chuyên khoa viết báo cáo.
- **Cắt ngọn (Top N Limiter):** Dù bệnh viện có 1000 bệnh nhân, AI cũng chỉ tập trung phân tích sâu 5 ca bệnh nặng nhất (Top 5). Các ca nhẹ hơn sẽ được hệ thống máy tính tự động in thành dạng Bảng (Table) đính kèm ở cuối báo cáo để chống quá tải (Rate Limit) cho đội ngũ AI.

### 4.2 Guardrail Chống Hallucination (Thanh bảo vệ chống Ảo giác AI)

Để hiểu về Guardrail, hãy hình dung LLM (AI) giống như một anh chàng Trợ lý cực kỳ giỏi ăn nói, văn phong lưu loát nhưng lại mắc bệnh **"hay chém gió quá đà" (Hallucination - Ảo giác AI)**. Nếu dữ liệu thật thiếu 5%, anh ta có thể cao hứng viết thành *"thiếu trầm trọng lên tới 50%!"*.

Hệ thống sinh ra một anh **"Giám thị" (Guardrail)**. Giám thị là một đoạn code Python vô cùng máy móc, không biết chém gió, chuyên làm nhiệm vụ kiểm duyệt:

### Bước 1: Thu thập "Bằng chứng gốc" (Allowed-Set)
Giám thị đọc file JSON gốc và nhặt tất cả các con số, tên cột có trong đó gom vào một **"Rổ số liệu hợp lệ" (Allowed-Set)**.
Luật thép: *Bất cứ con số nào AI viết ra trong báo cáo, bắt buộc phải có mặt trong cái Rổ này.*

### Bước 2: AI viết báo cáo
Trợ lý AI viết: *"Cột Tuổi bị trống 5%. Trung bình là 35.5. Cá biệt có trường hợp lên tới 200 tuổi, tạo ra mức độ CRITICAL."*

### Bước 3: Giám thị quét báo cáo (Guardrail Check)
Báo cáo chưa được gửi đi! Giám thị dùng "Kính lúp" (Regex) để dò từng con số:
- Dò số "5", "35.5" ➡️ Có trong Rổ. Duyệt!
- Dò số **"200"** ➡️ 🚨 BÁO ĐỘNG! Số này không có trong JSON. AI bịa đặt!

### Bước 4: Xử lý vi phạm (Retry Mechanism)
Giám thị ném trả bản báo cáo lại cho AI kèm thông báo: *"Mày lấy số 200 ở đâu ra? Trong dữ liệu lớn nhất chỉ là 150. Sửa ngay!"*. 
AI sẽ phải viết lại thành: *"Cá biệt có trường hợp lên tới 150 tuổi"*. Lúc này Giám thị kiểm tra thấy "150" có trong Rổ, mới cho **PASS**.

### Vấn đề làm tròn số (Tolerance)
Để AI có thể hành văn tự nhiên, Giám thị được trang bị thêm **Độ khoan dung (Tolerance)**. Nếu số gốc trong JSON là `35.51234`, nhưng AI viết là `"gần 36"`, Giám thị sẽ tính toán sai số. Nếu sai số dưới 1%, Giám thị vẫn gật đầu cho qua để tránh bắt lỗi oan việc làm tròn số bình thường.

### Kết luận
Nhờ vòng lặp **"AI viết ➡️ Guardrail dò số ➡️ Trả lại bắt viết lại nếu sai"**, hệ thống đạt được sự kết hợp hoàn hảo: **Văn phong mềm mại, thông minh của AI** + **Độ chính xác toán học tuyệt đối 100% của Code Python**.
