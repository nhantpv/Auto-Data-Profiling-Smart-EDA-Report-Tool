# Phase 0 — Research Sprint: Kết quả Nghiên cứu Trực tiếp

## Ngày: 2026-05-26

---

## 1. fg-data-profiling (tên mới của ydata-profiling)

### Phát hiện quan trọng
- **Đã đổi tên:** Package chính thức giờ là `fg-data-profiling` (trước là `ydata-profiling`). Import mới: `from data_profiling import ProfileReport`.
- **13.6k stars**, MIT license, 1585 commits. Active.

### Tính năng chính (phủ Layer 2, 4, 6)
1. **Type Inference:** Tự động phát hiện kiểu dữ liệu (Categorical, Numerical, Date, Text, URL, Image...).
2. **Warnings/Alerts:** Tự động sinh cảnh báo: high correlation, skewness, uniformity, zeros, missing values, constant values.
3. **Univariate Analysis:** Mean, median, mode, distributions, histograms.
4. **Multivariate Analysis:** Correlations, missing data patterns, duplicate rows, pairwise interactions.
5. **Time-Series:** Auto-correlation, seasonality, ACF/PACF plots.
6. **Text Analysis:** Uppercase/lowercase, scripts, blocks.
7. **Compare datasets:** So sánh 2 dataset (train vs test).
8. **Sensitive data detection:** Phát hiện PII.

### Output format
- **HTML report** (rich, interactive).
- **JSON** (via `profile.to_json()` hoặc `profile.to_file("report.json")`).
- **Jupyter widgets** (via `profile.to_widgets()`).

### Giới hạn
- DataFrame-based: load toàn bộ vào RAM (có thể dùng PySpark cho big data).
- Không có LLM narrative.
- Không có business rule validation.

### Quyết định: **INTEGRATE** — dùng thẳng `pip install fg-data-profiling`, gọi API lấy JSON output.

---

## 2. LIDA (Microsoft)

### Phát hiện quan trọng
- **3.3k stars**, MIT license, 160 commits. Đang ổn định (không phát triển mạnh).
- Python chỉ chiếm 11.2% code — phần lớn là Jupyter Notebook (31.4%), JavaScript (30%), HTML (27.4%).

### Kiến trúc Pipeline (phủ Layer 10)
1. **Summarizer:** `lida.summarize("data.csv")` → tạo summary nhỏ gọn về dataset.
2. **Goal Explorer:** `lida.goals(summary, n=5, persona="ceo")` → LLM tự đặt câu hỏi phân tích.
3. **VisGenerator:** `lida.visualize(summary, goal, library="matplotlib")` → sinh code tạo biểu đồ.
4. **Editing:** `lida.edit(code, summary, instructions)` → sửa biểu đồ bằng NL.
5. **Explanation:** `lida.explain(code, summary)` → giải thích biểu đồ.
6. **Evaluation & Repair:** `lida.evaluate(code, goal)` → tự đánh giá và sửa lỗi biểu đồ.
7. **Recommendation:** `lida.recommend(code, summary, n=2)` → gợi ý biểu đồ mới.
8. **Infographics (Beta):** Tạo infographic từ visualization.

### Đặc điểm kỹ thuật
- **Grammar-agnostic:** Sinh code cho bất kỳ thư viện viz nào (matplotlib, seaborn, altair, d3).
- **Multi-LLM:** OpenAI, Azure OpenAI, PaLM, Cohere, HuggingFace (local).
- **Bundled UI:** `lida ui --port=8080` — có sẵn web UI.
- **Error rate:** < 3.5% trên 2200+ visualizations.

### Giới hạn QUAN TRỌNG
- **Chỉ hoạt động tốt với <= 10 cột** do context window LLM bị giới hạn.
- Không có profiling/DQ — chỉ tập trung vào visualization + narrative.
- Sinh và thực thi code → **cần môi trường sandbox an toàn**.

### Quyết định: **INSPIRE** — học kiến trúc pipeline (đặc biệt Summarizer + Goals + VisGenerator), tự viết code phù hợp. Có thể tích hợp trực tiếp LIDA nếu scope cho phép.

---

## 3. Great Expectations (GX Core)

### Phát hiện quan trọng
- **11.5k stars**, Apache-2.0 license, 13,643 commits, v1.17.2 (May 2026). Rất active.
- Python 99.4%.

### Kiến trúc Core (phủ Layer 3)
- **Expectations:** Unit test cho dữ liệu. Ví dụ:
  - `expect_column_values_to_be_between(column="age", min_value=0, max_value=120)`
  - `expect_column_values_to_not_be_null(column="id")`
  - `expect_column_values_to_match_regex(column="email", regex="^[a-zA-Z0-9+_.-]+@[a-zA-Z0-9.-]+$")`
- **Data Docs:** Tự động sinh tài liệu HTML từ kết quả validation.
- **Data Context:** Lưu trữ cấu hình, kết quả validation, lịch sử.
- Có **hàng chục built-in Expectations** sẵn, cho phép viết custom.

### ⚠️ PHÁT HIỆN QUAN TRỌNG: Tích hợp ydata-profiling + GE đã bị NGỪNG HỖ TRỢ
- Docs chính thức của ydata-profiling ghi rõ:
  > "Great expectations integration is no longer supported. You can recreate the integration with the following packages versions: ydata-profiling==2.1.0, great-expectations==0.13.4"
- Các phiên bản hiện tại (fg-data-profiling mới + GE v1.17.x) **KHÔNG còn tương thích trực tiếp**.
- Hàm `profile.to_expectation_suite()` không còn hoạt động với bản mới nhất.

### Ảnh hưởng đến kiến trúc
- **KHÔNG thể dùng pattern "profiling → auto-generate Expectations"** như cũ.
- Phải chọn 1 trong 2 hướng:
  1. Dùng GE v1.17+ **độc lập**, tự viết Expectations thay vì auto-generate từ profiling.
  2. Dùng version cũ (ydata-profiling==2.1.0 + GE==0.13.4) để giữ integration — nhưng bản cũ thiếu rất nhiều tính năng mới.
  3. Tự viết bridge layer kết nối output JSON từ fg-data-profiling → sinh Expectations cho GE mới.

### Quyết định: **INTEGRATE nhưng cần tự viết bridge layer**. Dùng GE v1.17+ cho validation, tự parse JSON output từ fg-data-profiling để auto-generate Expectations.

---

## 4. Tổng hợp Bài học & Quyết định

### Ma trận Layer → Công cụ (Cập nhật sau Research)

| Layer | Công cụ | Cách kế thừa | Ghi chú |
|---|---|---|---|
| 1 (Business Understanding) | Tự viết + LLM | — | Cấu hình Target, Constraints, Domain |
| 2 (Ingestion & Schema) | **fg-data-profiling** | **Integrate** | Type inference, schema detection |
| 3 (DQ Validation) | **Great Expectations** | **Integrate + Bridge** | Tự viết layer sinh Expectations từ profiling JSON |
| 4 (Profiling & Missing) | **fg-data-profiling** | **Integrate** | Missing pattern, cardinality, alerts |
| 5 (Cleaning) | Tự viết (pandas) | — | Fuzzy match, imputation, outlier treatment |
| 6 (Exploratory Stats) | **fg-data-profiling** | **Integrate** | Correlations, distributions, stats |
| 7 (Transformation) | scikit-learn | **Integrate** | Scaling, Encoding, Power transforms |
| 8 (Leakage Detection) | Tự viết | — | Target leakage, multicollinearity |
| 9 (Post-validation) | Tự viết | — | Distribution shift check |
| 10 (Reporting) | **LIDA** (kiến trúc) | **Inspire** | Pipeline: Summary → Goals → Vis → Report |

### Rủi ro phát hiện mới
1. **ydata-profiling + GE integration bị ngưng:** Cần budget dev để viết bridge layer.
2. **LIDA giới hạn <= 10 cột:** Cần preprocessing (sampling/selecting top columns) trước khi đưa vào LLM.
3. **fg-data-profiling đổi tên/import:** Cần chắc chắn team dùng đúng package mới (`fg-data-profiling`, không phải `ydata-profiling`).
