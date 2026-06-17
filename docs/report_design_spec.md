# Kim chỉ nam Thiết kế Báo cáo L4 (Design Spec — KHÔNG GHI ĐÈ)

> **File này là tài liệu đối chiếu DUY NHẤT trong quá trình code.**
> Mọi thay đổi code phải bám sát thiết kế trong file này.

---

## 1. Đề bài gốc (Nguyên văn — KHÔNG tự thêm thắt)

- **Mục tiêu:** "Tự động hóa giai đoạn phân tích và thăm dò dữ liệu thô ban đầu (EDA) cho các dự án Data/AI."
- **Tính năng:** "Công cụ kết nối DB/CSV, tự động tính các chỉ số thống kê, phát hiện lỗi chất lượng dữ liệu (outliers, missing values) và dùng LLM đóng vai Senior Data Scientist để xuất báo cáo nhận xét chi tiết kèm biểu đồ trực quan."
- **LLM đóng vai:** Senior Data Scientist (theo đề bài).
- **Đề bài KHÔNG chỉ định** người dùng cụ thể là ai. Công cụ phục vụ bất kỳ ai cần EDA cho dự án Data/AI.

---

## 2. Thiết kế Giao diện HTML — 2 Tab (Giữ nguyên thiết kế gốc)

- **Tab 1 (Báo cáo LLM):** Chứa toàn bộ Phần 1 đến Phần 4.
- **Tab 2 (Chi tiết YData):** Nhúng nguyên khối báo cáo `ydata-profiling` HTML. Không thay đổi.
- **TUYỆT ĐỐI KHÔNG dồn tất cả vào 1 trang kéo dài.**

---

## 3. Cấu trúc Nội dung Tab 1 — 5 Phần (Từ Tổng quan → Chi tiết)

Tuân thủ tuyệt đối cấu trúc phân cấp **Table → Column**.

### Phần 1: Executive Dashboard (Bảng điều khiển Tổng quan)

- **Phán quyết (Verdict) & Điểm số (Risk Score).**
- **Feature Usability Summary (Bảng tóm tắt cột):** DS mở báo cáo ra là biết ngay cột nào dùng được, cột nào cần xử lý, cột nào nên bỏ.

    | Trạng thái | Ý nghĩa | Ví dụ |
    |---|---|---|
    | ✅ Dùng ngay | Cột sạch, không lỗi | `age`, `product_id` |
    | ⚠️ Cần xử lý | Có lỗi nhưng cứu được | `income` (Outlier, skewness=12.4) |
    | ❌ Nên bỏ | Quá rác, không nên đưa vào model | `email` (Missing 40%, không impute được) |

- **Fix Priority (Ưu tiên xử lý):** Xếp hạng Bảng/Cột cần sửa đầu tiên dựa trên công thức `Severity × Số lượng downstream tables bị ảnh hưởng` (VD: Bảng gốc bị lỗi sẽ ảnh hưởng hàng loạt bảng con nối vào nó).
- 📊 **Visual Chart:** Biểu đồ Stacked Bar Chart hiển thị số lượng lỗi (theo mức độ CRITICAL/HIGH/WARN) phân bổ theo từng bảng *(Cần code mới)*.

---

### Phần 2: Table-by-Table Health Check (Khám sức khỏe từng bảng)

Đây là **trái tim** của báo cáo, gom nhóm mọi lỗi theo bảng và cột. LLM chỉ liệt kê các cột có lỗi từ mức WARN trở lên.

#### 📦 BẢNG: `Orders` (Dữ liệu Giao dịch)
**🌟 Đánh giá tổng quan bảng:** Bảng dữ liệu có cấu trúc khá tốt nhưng gặp rủi ro cực kỳ nghiêm trọng về tính toàn vẹn khóa ngoại (Orphan Keys), có nguy cơ làm đứt gãy toàn bộ pipeline tính toán nếu không được xử lý.

**🔸 Cột: `customer_id`**
- **[CRITICAL] Vấn đề:** Phát hiện 1,240 dòng (15%) chứa mã khách hàng không tồn tại trong bảng tham chiếu `Customers` (Lỗi Orphan Keys).
- **ML Consequence (Theo nhóm thuật toán):** Khi Join để tạo tập dữ liệu huấn luyện, 15% mẫu này sẽ bị rớt. Các mô hình Tuyến tính (Linear/Logistic) sẽ mất mát lượng lớn thông tin, gây Underfitting. Các mô hình Tree-based (Random Forest, XGBoost) cũng bị ảnh hưởng tương tự vì giảm số mẫu huấn luyện.
    > *Quy tắc: LLM phân tích rủi ro theo **nhóm thuật toán** (Tuyến tính / Tree-based / Neural Networks / Clustering) thay vì liệt kê cụ thể từng model, vì ở giai đoạn EDA DS chưa chọn thuật toán.*
- **Gợi ý tham khảo:** Bạn có thể cân nhắc áp dụng Left Join và tạo thêm đặc trưng (feature) `is_missing_customer=1` để model học được pattern mồ côi này, hoặc loại bỏ trước khi train.
- 📊 **Visual Chart (Cơ chế Inline):** Mỗi cột bị lỗi sẽ được đính kèm một biểu đồ thu nhỏ (mini-chart) của **RIÊNG** cột đó nằm ngay bên cạnh text. VD: Tại mục này sẽ là 1 mini-missingness bar.

**🔸 Cột: `total_amount`**
- **[HIGH] Vấn đề:** Phát hiện 5 giá trị âm (Min = -500) và 10 giá trị lớn bất thường (Outliers > 3 độ lệch chuẩn).
- **ML Consequence:** Giá trị âm làm sai logic. Outliers lớn sẽ làm hỏng các hàm mất mát (loss function) nếu dùng cột này để train mô hình Tuyến tính hay Neural Networks. Nhóm Tree-based ít bị ảnh hưởng hơn.
- **Gợi ý tham khảo:** Bạn có thể cân nhắc loại bỏ (drop) các dòng `< 0`. Với Outliers, có thể áp dụng kỹ thuật Capping (giới hạn đuôi) hoặc dùng Robust Scaler trước khi train model.
- 📊 **Inline Chart:** 1 mini-histogram + 1 mini-boxplot riêng của cột `total_amount`.

**🔸 Cột: `birth_date`**
- **[HIGH] Vấn đề (Format Consistency):** Phát hiện trộn lẫn định dạng (dd/mm/yyyy và mm/dd/yyyy) và cả Text ('Unknown').
- **ML Consequence:** Thư viện Pandas sẽ parse nhầm thành Object thay vì Datetime. Các thuật toán Tree-based không thể xử lý chuỗi ký tự hỗn hợp này, dẫn đến lỗi runtime khi fit model.

#### 👤 BẢNG: `Customers` (Dữ liệu Khách hàng)
**🌟 Đánh giá tổng quan bảng:** Dữ liệu có dấu hiệu bị thu thập thiếu đồng bộ, dẫn đến tỷ lệ rỗng (Null) rải rác ở các cột định danh quan trọng. Cần chú ý kỹ thuật điền khuyết (Imputation) trước khi phân tích.

**🔸 Cột: `email`**
- **[WARN] Vấn đề:** Thiếu (Missing values) lên tới 40%.
- **ML Consequence:** Làm suy giảm chất lượng định danh khách hàng. Thuật toán phân cụm (Clustering) sẽ gặp khó khăn vì bị khuyết quá nhiều đặc trưng.
- **Gợi ý tham khảo:** Không nên dùng Mean/Mode imputation cho cột này. Bạn có thể cân nhắc tạo thêm một cột cờ (flag) `has_email` (1/0) thay vì cố gắng điền khuyết.
- 📊 **Inline Chart:** 1 mini-missingness bar riêng của cột `email`.

---

### Phần 3: Cross-Table Analysis (Phân tích Đa bảng)

Chia làm 2 tiểu mục:

#### 3a. Schema Evaluation (Đánh giá Cấu trúc)
- Phân tích các đứt gãy quan hệ (Integrity errors, Orphan FK).
- **📝 Mockup Text từ LLM:** *"Phát hiện rủi ro khi JOIN: Đường nối từ `Orders` trỏ về `Customers` có 1,240 dòng Orphan Keys [CRITICAL]. Trong khi đó, đường nối từ `Products` về `Categories` đạt mức toàn vẹn 100% [OK]."*
- 📊 **Visual Chart:** Relationship Network Graph. Node = Bảng, Edge = Khóa ngoại (FK), màu sắc Edge cảnh báo trạng thái Integrity *(Cần code mới với thư viện networkx)*. Đính kèm Orphan FK Detail Table.

#### 3b. Cross Correlation (Tương quan chéo)
- Phân tích sự tương quan giữa các cột khác bảng.
- **ML Consequence:** Cảnh báo Đa cộng tuyến (Multicollinearity) hoặc Rò rỉ dữ liệu (Data Leakage).
- 📊 **Visual Chart:** Biểu đồ Horizontal Bar Top 10 Correlations *(Cần code mới)*.

---

### Phần 4: Data Dictionary (Từ điển dữ liệu) — Should-have

- Sử dụng LLM để sinh chú giải tự động cho từng bảng/cột dựa vào tên và phân phối dữ liệu.
- **Lý do nâng cấp từ Nice-to-have lên Should-have:** Hiểu sai ý nghĩa cột (VD: `status=2` là "Hoàn thành" hay "Đã hủy"?) là nguyên nhân hàng đầu khiến DS encode sai → model học ngược. Một Senior DS thực thụ luôn giải thích nghĩa data cho team — đây là phần tự nhiên của vai trò.

---

## 4. Quy tắc Văn phong (Tone Rules)

- **Advisory tone TUYỆT ĐỐI:** "Bạn có thể cân nhắc...", "Gợi ý tham khảo..." — KHÔNG BAO GIỜ ra lệnh.
- **ML Consequence theo nhóm thuật toán:** Tuyến tính / Tree-based / Neural Networks / Clustering — KHÔNG liệt kê cụ thể từng model (vì DS chưa chọn).
- **Mỗi issue phải có đủ 3 thành phần:** [Severity] Vấn đề → ML Consequence → Gợi ý tham khảo.
- **Đầu mỗi bảng phải có nhận xét tổng quan** rồi mới breakdown ra từng cột.

---

## 5. Phạm vi (Scope)

### ✅ Làm:
- Format Consistency (date nhiều format, numeric lẫn text, categorical sai case) — universal, ảnh hưởng đến parse và modeling.
- Stacked Bar Chart, Network Graph, Horizontal Bar Correlations — 3 chart mới.
- Inject column stats (mean, std, skewness, kurtosis, min, max) vào payload cho LLM.
- Bỏ exclude `top_10_samples` (hoặc đổi thành top 5 để tiết kiệm token).
- Truyền `cardinality` (1:N, 1:1) và `schema_mode` (quick/precise) vào Editor prompt.

### ❌ KHÔNG làm:
- Business Rules hardcode — domain-specific, không bao quát hết case. Để LLM gợi ý nếu muốn.
- PII detection — không phải việc của DS.
- Timeliness check — không phải việc của DS.
- Thay đổi thiết kế 2 Tab hiện tại.

---

## 6. Guardrail — Cơ chế kỹ thuật (Python Post-validation)

LLM không phải database engine, có thể viết sai ID. Cơ chế kiểm tra PHẢI nằm ở phía code Python:

1. LLM trả về JSON chứa `evidence_ref` cho mỗi Suggested Action.
2. Code Python kiểm tra: `evidence_ref` có tồn tại trong danh sách `finding_ids` của L3 không?
3. Nếu không tồn tại → xóa dòng Action đó khỏi báo cáo (Reject). Nếu tồn tại → giữ lại (Accept).

---

## 7. Payload Wiring — Dữ liệu L3 cần truyền cho L4

> **Gốc rễ vấn đề:** LLM hiện tại nói chung chung vì chúng ta không gửi Column Stats cho nó.

| Dữ liệu cần truyền | Nguồn | Đích | Trạng thái hiện tại |
|---|---|---|---|
| `columns` dict (mean, std, skewness, kurtosis, min, max, n_zeros, n_distinct, missingness_mechanism, imbalance) | `DataQualityFindings.columns` | Analyst Agent (qua dispatcher) + Editor Agent | ❌ Chưa truyền ở luồng multi-agent |
| `top_10_samples` (hoặc top 5) | `AnomalyRecord.top_10_samples` | Analyst Agent | ❌ Đang bị `exclude` |
| `cardinality` (1:1, 1:N, N:N) + `pk_runtime_unique` | `relationship_graph.json.edges[]` | Editor Agent | ❌ Chưa truyền |
| `schema_mode` (quick / precise) | `schema_gate.json.mode` | Editor Agent | ❌ Chưa truyền |

### Những gì ĐÃ ĐÚNG (Không cần sửa):
| Khoản mục | Trạng thái |
|---|---|
| `DataQualityFindings.dataset_meta` | ✅ Đã vào editor prompt |
| `DatasetVerdict.verdict, summary, risk_score, top_issues` | ✅ Đã vào editor prompt |
| `SchemaEvaluationFindings.integrity_errors` | ✅ Đã vào dispatcher → analyst |
| `SchemaEvaluationFindings.relationships` | ✅ Đã vào editor prompt |
| `CrossTableAnalysis.correlations, join_steps` | ✅ Đã vào editor prompt |
| ydata-profiling HTML Tab 2 | ✅ Giữ nguyên |
| Overview PNG charts gallery | ✅ Giữ nguyên |
