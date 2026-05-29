# Nhận Xét Đề Bài, Các Plan Đã Làm Và Hướng Tiếp Cận Giải Quyết

## 1. Tóm Tắt Đề Bài

Đề bài của nhóm Trần Phan Văn Nhân, Nguyễn Đức Duy, Nguyễn Hữu Tấn Long là xây dựng công cụ **Auto Data-Profiling & Smart EDA Report Tool**. Mục tiêu chính của công cụ là tự động hóa giai đoạn phân tích dữ liệu ban đầu và EDA trong các dự án Data/AI.

Theo mô tả đề bài, hệ thống cần kết nối tới nguồn dữ liệu như **database** hoặc **CSV**, tự động tính toán chỉ số thống kê, phát hiện vấn đề chất lượng dữ liệu như missing values, outliers, dữ liệu trùng lặp hoặc bất thường, sau đó dùng LLM đóng vai trò Senior Data Scientist để tạo báo cáo phân tích kèm biểu đồ.

Bản chất của đề bài không phải là xây dựng công cụ tự động làm sạch dữ liệu hay train model. Đây là một **diagnostic tool**: hệ thống đọc dữ liệu, chỉ ra vấn đề, trực quan hóa bằng biểu đồ, và đề xuất hướng xử lý. Vì vậy, trọng tâm kiến trúc nên nằm ở pipeline phân tích đáng tin cậy, output có cấu trúc, và lớp LLM chỉ diễn giải dựa trên kết quả đã được tính toán.

## 2. Nhận Xét Về Đề Bài

Đề bài có tính thực tế cao vì EDA là bước lặp lại trong hầu hết các dự án Data/AI. Khi nhận dataset mới, Data Engineer hoặc Data Scientist thường phải kiểm tra thủ công số dòng, số cột, kiểu dữ liệu, tỷ lệ thiếu, phân phối, outliers và duplicate rows. Công việc này tốn thời gian, dễ thiếu nhất quán và phụ thuộc nhiều vào kinh nghiệm cá nhân.

Điểm hay của đề bài là kết hợp hai hướng: phân tích deterministic bằng code và diễn giải bằng LLM. Các chỉ số thống kê, biểu đồ và phát hiện lỗi phải được tính bằng Python hoặc thư viện phân tích dữ liệu, không giao cho LLM tự suy đoán. Sau đó, LLM biến các kết quả khô khan thành báo cáo dễ hiểu, có nhận xét và khuyến nghị.

Tuy nhiên, đề bài có rủi ro nếu mở rộng scope quá sớm. Nếu vừa hỗ trợ nhiều loại input, vừa xây anomaly detection nâng cao, vừa phân tích đa bảng, vừa build multi-agent LLM, dự án sẽ dễ bị dàn trải. Với mục tiêu bài nộp, hướng tốt nhất là làm một pipeline end-to-end chạy ổn định trước.

## 3. Nhận Xét Các Plan Đã Làm

Các tài liệu hiện có đã xác định đúng nguyên tắc kiến trúc quan trọng nhất: **Deterministic-First, LLM-Last**. Đây là quyết định phù hợp với bài toán. Hệ thống không nên để LLM đọc raw data và tự tính toán số liệu, vì LLM có thể tạo ra nhận xét sai hoặc bịa số. Thay vào đó, Python pipeline phải tạo ra các kết quả có thể kiểm chứng, còn LLM chỉ đọc structured findings và viết báo cáo.

Plan kiến trúc hiện tại chia hệ thống thành các layer:

- **Layer 0 - Data Ingestion:** đọc dữ liệu từ CSV, Excel, Parquet hoặc schema file.
- **Layer 1 - Deterministic Profiling:** dùng công cụ như `ydata-profiling` để tính thống kê mô tả.
- **Layer 2 - Data Quality / ML Engine:** phát hiện outliers, missing patterns, schema mismatch và các vấn đề chất lượng dữ liệu.
- **Layer 3 - Structured Findings:** gom kết quả thành JSON/YAML chuẩn hóa.
- **Layer 3.5 - Visualization:** tạo biểu đồ tổng quan và biểu đồ chẩn đoán.
- **Layer 4 - LLM Reporting:** dùng LLM để viết báo cáo phân tích.

Cách chia layer này hợp lý vì mỗi phần có trách nhiệm rõ ràng. Data ingestion không phụ thuộc vào LLM, profiling engine không cần biết báo cáo cuối cùng trình bày thế nào, và LLM report layer chỉ nhận output đã chuẩn hóa. Nhờ vậy, dự án dễ test, dễ thay thư viện, và dễ mở rộng.

Điểm mạnh thứ hai là ý tưởng **structured findings ontology**. Thay vì đưa toàn bộ raw output của profiling library cho LLM, hệ thống nên chuẩn hóa thành `findings.json`. File này là source of truth cho report, chứa loại lỗi, cột liên quan, mức độ nghiêm trọng, metric, ngưỡng, bằng chứng và gợi ý xử lý. Đây là nền tảng tốt để giảm rủi ro hallucination và giúp báo cáo có thể audit.

Điểm mạnh thứ ba là plan đã tính tới visualization và fallback. Biểu đồ là yêu cầu quan trọng vì report EDA không chỉ nên có text. Nếu LLM lỗi hoặc API timeout, hệ thống vẫn nên xuất được report cơ bản từ kết quả deterministic.

Tuy nhiên, một số phần đang vượt quá scope MVP. DBML validator, multi-table schema checking, PyOD anomaly detection nâng cao, multi-agent orchestration và LLM-directed visualization đều là hướng hay nhưng không nhất thiết phải có trong bản đầu tiên.

Ngoài ra, câu khẳng định rằng việc không cho LLM chạm raw data sẽ loại bỏ 100% hallucination nên được điều chỉnh. Cách làm này chỉ **giảm mạnh rủi ro hallucination**, không thể loại bỏ tuyệt đối.

## 4. Hướng Tiếp Cận Giải Quyết Đề Xuất

Hướng tiếp cận phù hợp nhất là xây dựng một MVP theo pipeline đơn giản, rõ ràng và có thể demo end-to-end. Pipeline đề xuất:

```text
CSV / Database
    ↓
Data Loader
    ↓
Pandas DataFrame + Metadata
    ↓
Profiling Engine
    ↓
Data Quality Detection Engine
    ↓
findings.json
    ↓
Chart Generator
    ↓
LLM Report Generator
    ↓
Final EDA Report
```

Trong MVP, input nên tập trung vào **CSV** và một dạng database phổ biến, ví dụ SQLite hoặc PostgreSQL thông qua SQLAlchemy. CSV giúp demo dễ, còn DB connection đáp ứng đúng yêu cầu đề bài. Excel, Parquet và DBML có thể để giai đoạn sau.

Data Loader có nhiệm vụ đọc dữ liệu và trả về `DataFrame` kèm metadata như tên nguồn, số dòng, số cột, lỗi parse nếu có, và thông tin sampling nếu dataset lớn. Report cần biết dữ liệu đến từ đâu và pipeline đã xử lý như thế nào.

Profiling Engine nên tính các chỉ số cơ bản:

- Số dòng, số cột.
- Kiểu dữ liệu từng cột.
- Missing count và missing percentage.
- Unique count và cardinality.
- Mean, median, standard deviation, min, max, quartiles cho numeric columns.
- Top values cho categorical columns.
- Duplicate rows.
- Correlation matrix cho các cột numeric.

Data Quality Detection Engine nên bắt đầu bằng các rule/statistical checks dễ giải thích:

- Cột có missing rate cao.
- Dòng trùng lặp.
- Outliers bằng IQR hoặc Z-score.
- Cột constant hoặc gần constant.
- Cột categorical có cardinality quá cao.
- Numeric column bị skew mạnh.
- Type inconsistency đơn giản, ví dụ cột đáng lẽ numeric nhưng có nhiều giá trị không parse được.

Ở MVP, không nên dùng PyOD hoặc Isolation Forest làm logic chính. Các thuật toán này mạnh hơn nhưng cần xử lý encoding, scaling, mixed data type và explainability. Rule thống kê cổ điển sẽ dễ hiểu, dễ test và dễ trình bày hơn.

## 5. Structured Findings Là Trung Tâm Hệ Thống

Thành phần quan trọng nhất nên được thiết kế sớm là `findings.json`. Đây là contract giữa engine phân tích, chart generator và LLM report generator. Một finding nên có cấu trúc tối thiểu:

```json
{
  "finding_id": "F001",
  "type": "missing_values",
  "dimension": "completeness",
  "severity": "high",
  "table": "sales",
  "column": "customer_email",
  "metric_value": 0.32,
  "threshold": 0.2,
  "evidence": "32% values are missing",
  "recommendation_hint": "Review data collection process or define imputation strategy",
  "source_engine": "data_quality_engine"
}
```

LLM chỉ được phép viết báo cáo dựa trên các finding này. Prompt nên yêu cầu LLM không tự tạo số liệu mới, không suy đoán ngoài dữ liệu, và nếu thiếu thông tin thì nói rõ là chưa đủ bằng chứng.

## 6. Visualization Strategy

Visualization trong MVP nên deterministic, không nên để LLM tự yêu cầu chart. Mỗi loại vấn đề có thể map với một loại biểu đồ cố định:

- Missing values: bar chart hoặc missing heatmap.
- Numeric distribution: histogram và boxplot.
- Outliers: boxplot hoặc scatter plot nếu có index/time.
- Categorical distribution: bar chart top categories.
- Correlation: heatmap cho numeric columns.

Chart Generator nên xuất ảnh vào thư mục output của từng lần chạy và lưu metadata trong report context. LLM có thể nhắc đến biểu đồ dựa trên chart metadata, nhưng không nên quyết định logic tính toán chart trong MVP.

## 7. Roadmap Triển Khai

### Phase 1 - Data Loading Và Profiling Cơ Bản

Xây dựng CLI hoặc script chạy được với CSV trước, sau đó thêm DB connection bằng SQLAlchemy. Output đầu tiên là file JSON chứa summary, column profile và duplicate statistics.

### Phase 2 - Data Quality Checks Và Charts

Thêm các rule phát hiện missing, duplicate, outlier, high cardinality, constant column và skewness. Chuẩn hóa vấn đề thành `findings.json`, sau đó tạo chart tương ứng bằng matplotlib, seaborn hoặc plotly.

### Phase 3 - LLM Report Generator

Thiết kế prompt để LLM đóng vai Senior Data Scientist nhưng chỉ được dùng `findings.json` và chart metadata. Output là Markdown report gồm executive summary, dataset overview, data quality issues, chart interpretation và recommendations. Nếu LLM lỗi, fallback sang template report cơ bản.

### Phase 4 - Demo, UI Và Kiểm Thử

Nếu cần giao diện, dùng Streamlit để upload CSV hoặc nhập DB connection string, chạy profiling và xem report. Tạo dataset demo có lỗi rõ ràng và viết test cho các rule quan trọng.

## 8. Kết Luận

Plan hiện tại có nền tảng kiến trúc tốt, đặc biệt ở hướng deterministic-first, structured findings và LLM-last. Tuy nhiên, để phù hợp với đề bài và khả năng triển khai, MVP nên được thu gọn. Mục tiêu đầu tiên là xây một pipeline hoàn chỉnh, đáng tin cậy và demo được.

Hướng giải quyết nên tập trung vào: đọc CSV/DB, tính profiling metrics, phát hiện data quality issues bằng rule/statistical checks, sinh biểu đồ, chuẩn hóa kết quả thành `findings.json`, và dùng LLM viết báo cáo từ findings đó. Sau khi MVP ổn định, dự án có thể mở rộng sang DBML, multi-table validation, PyOD anomaly detection, LLM-directed visualization và multi-agent reporting.
