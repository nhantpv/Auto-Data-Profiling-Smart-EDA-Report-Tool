# Báo cáo Nghiên cứu Tổng hợp — Automated EDA / Các Data Science Agent được hỗ trợ bởi LLM

**Nguồn:** Claude (C), ChatGPT (G), Perplexity (P — regular + Pro Research, được gộp chung dưới một thẻ), Grok (X).
**Quy tắc về độ tin cậy (Confidence rule):** 3–4 nguồn = HIGH, 2 = MEDIUM, 1 = LOW. Hai tệp Perplexity dùng chung thẻ P — một mục có trong một hoặc cả hai vẫn chỉ được tính là một nguồn P duy nhất.

---

## 1. Tóm tắt Thực thi (Executive Summary)

- **LIDA (Dibia, ACL 2023) là bài báo nền tảng duy nhất mà cả bốn AI đều đồng tình** — mọi báo cáo đều trích dẫn nó như là bản thiết kế kiến trúc (architectural blueprint) gần gũi nhất cho "auto-visualization + summarization (tự động trực quan hóa + tóm tắt) được điều khiển bởi LLM." [C/G/P/X]
- **ydata-profiling là cơ sở (baseline) cổ điển được đồng thuận** cho việc lập hồ sơ thống kê cấp độ cột (column-level statistical profiling); ~13k sao, cả bốn nguồn đều đánh giá nó ở mức production-ready (sẵn sàng cho môi trường sản xuất) nhưng thiếu bất kỳ narrative (bài tường thuật/diễn giải) LLM nào hoặc khả năng kết nối DB (cơ sở dữ liệu). [C/G/P/X]
- **PandasAI được đồng thuận là người dẫn đầu về LLM-data-agent** nhưng mọi nguồn đều cảnh báo rằng nó có thể hallucinate (ảo giác) về các số liệu thống kê và mang tính chất đàm thoại (conversational) hơn là tập trung vào profiling (lập hồ sơ). [C/G/P/X]
- **Trạng thái của Vanna là sự bất đồng thực tế lớn nhất trong tập các nguồn** — Claude, ChatGPT, và Grok gọi nó là đã lưu trữ (archived - Tháng 3 năm 2026); Perplexity Pro Research nói rằng nó đang hoạt động (active - cập nhật Tháng 2 năm 2026). Hãy xác minh trước khi áp dụng. [C/G/X nói archived; P nói active]
- **LLM hallucination (ảo giác của LLM) về thống kê số liệu là rủi ro chưa được giải quyết mà mọi báo cáo đều gắn cờ** — Claude trích dẫn tỷ lệ hallucination thực tế là 59–82%; Perplexity Pro trích dẫn các bài báo của Akella và cộng sự (2025) và Combo-Eval như là các biện pháp giảm thiểu (mitigations) trực tiếp nhất; không có công cụ open-source (mã nguồn mở) nào triển khai grounding (nền tảng/xác minh) end-to-end (từ đầu đến cuối). [C/G/P/X]
- **Điểm khác biệt mạnh mẽ nhất qua cả bốn báo cáo là giống nhau**: một "Senior Data Scientist" agent LLM đáng tin cậy, có thể kiểm toán được (auditable) giúp đối chiếu các khẳng định mang tính narrative (tường thuật) vào các số liệu thống kê đã được tính toán và xác minh, tích hợp với DB-native profiling (lập hồ sơ trực tiếp trên cơ sở dữ liệu) và DQ detection (phát hiện chất lượng dữ liệu) trong một pipeline duy nhất. Không có công cụ open-source nào bao phủ toàn bộ năm lớp (layers) ở chất lượng production. [C/G/P/X]
- **TiInsight (PingCAP) là hệ thống được xác nhận ở mức production (production-validated system) gần gũi nhất cho việc thấu hiểu DB schema thông qua các LLM** — ba nguồn trích dẫn nó; Hierarchical Data Context (HDC - Ngữ cảnh Dữ liệu Phân cấp) là một kỹ thuật có thể tái sử dụng ngay lập tức. Mã arXiv ID là một điểm mâu thuẫn (xem §6). [G/P/X]
- **Julius AI và Tableau Pulse là những giao thoa thương mại (commercial overlaps) mạnh mẽ nhất** — Julius là công cụ duy nhất ở mức giá tiêu dùng (consumer-priced) tuyên bố có toàn bộ narrative pipeline; Tableau Pulse dẫn đầu về cung cấp auto-insight (phân tích tự động) cho doanh nghiệp nhưng theo hướng metric-centric (lấy số liệu làm trung tâm), chứ không phải profile-centric (lấy hồ sơ dữ liệu làm trung tâm). [C/G/P/X]

---

## 2. Bài báo Học thuật (Academic Papers) — Đã tổng hợp

| Bài báo (Paper) | Năm (Year) | Nơi xuất bản (Venue) | Mức độ liên quan đến dự án (Relevance to project) | Độ tin cậy (Confidence) | Nguồn (Sources) |
|---|---|---|---|---|---|
| **LIDA: A Tool for Automatic Generation of Grammar-Agnostic Visualizations and Infographics** (V. Dibia) | 2023 | ACL Demo / arXiv:2303.02927 | Bản thiết kế (blueprint) gần gũi nhất cho lớp "chart + narrative summary"; pipeline SUMMARIZER → GOAL EXPLORER → VISGENERATOR → INFOGRAPHER phản chiếu thiết kế Senior Data Scientist. | HIGH | C/G/P/X |
| **Towards Automated Cross-domain EDA through LLMs (TiInsight)** (Zhu và cộng sự) | 2024/2025 | PVLDB / arXiv:2412.07214 [URL bị tranh cãi — xem §6] | Hệ thống EDA đa cơ sở dữ liệu (cross-database EDA system) được xác nhận ở mức production; Hierarchical Data Context (HDC) trực tiếp giải quyết vấn đề DB-schema-to-LLM. Độ chính xác ~86–91% trên tập Spider với GPT-4. | HIGH | G/P/X |
| **Large Language Model-based Data Science Agent: A Survey** (Chen / Wang và cộng sự) | 2025 | arXiv:2508.02744 | Khảo sát tổng quan (landscape survey) được trích dẫn nhiều nhất; cung cấp taxonomy (hệ thống phân loại) về các vai trò agent, chiến lược thực thi (execution strategies), và các giai đoạn quy trình làm việc DS — bản đồ định vị thiết yếu. | HIGH | C/G/P |
| **InsightPilot: An LLM-Empowered Automated Data Exploration System** (Ma và cộng sự) | 2023 | EMNLP Demo / arXiv:2304.00477 | Tiền bối về mặt kiến trúc gần gũi nhất cho mục đích "LLM as analyst" (LLM đóng vai trò nhà phân tích) → IQuery → insight pipeline. | MEDIUM | C/P |
| **InReAcTable: LLM-Powered Interactive Visual Data Story Construction from Tabular Data** (Aodeng và cộng sự) | 2024–2025 | UIST 2025 / mâu thuẫn arXiv (xem §6) | Mô hình hóa lớp đầu ra narrative-findings (các phát hiện mang tính tường thuật); thiết kế tương tác cho việc xây dựng câu chuyện do người dùng hướng dẫn (user-guided story construction). | MEDIUM | G/P |
| **A Data-centric AI Framework for Automating EDA and Data Quality Tasks** (Nhóm IBM) | 2023 | ACM TODS / DOI:10.1145/3603709 | Xác nhận bài toán năng suất (productivity case) cho automated EDA (năng suất gấp đôi, tiết kiệm 30–50% thời gian); các thuật toán cho cả EDA và DQ. | MEDIUM | P/X |
| **Dead or Alive: Continuous Data Profiling for Interactive Data Science / AutoProfiler** (Epperson và cộng sự) | 2023 | IEEE VIS / arXiv:2308.03964 hoặc 2305.07126 [URL không nhất quán giữa các nguồn] | Continuous profiling (lập hồ sơ liên tục) được tích hợp trong Notebook với visual summaries (tóm tắt trực quan) cập nhật trực tiếp; nghiên cứu người dùng cho thấy 91% các phát hiện (findings) đã được khám phá. | MEDIUM | G/P |
| Data Interpreter: An LLM Agent For Data Science (Hong và cộng sự) | 2024 | ACL Findings / arXiv:2402.18679 | DS agent dựa trên đồ thị phân cấp (Hierarchical graph-based); đạt 94.9% trên DABench. | LOW | C |
| InfiAgent-DABench: Evaluating Agents on Data Analysis Tasks (Hu và cộng sự) | 2024 | ICML 2024 / arXiv:2401.05507 | 603 câu hỏi phân tích dữ liệu, 124 CSV; benchmark để đánh giá các DS agents. | LOW | C |
| DS-1000: A Natural and Reliable Benchmark for Data Science Code Generation (Lai và cộng sự) | 2023 | ICML 2023 / arXiv:2211.11501 | 1.000 bài toán DS qua 7 thư viện Python; đánh giá dựa trên việc thực thi (execution-based evaluation). | LOW | C |
| Chat2VIS: Generating Data Visualisations via NL using ChatGPT, Codex, GPT-3 (Maddigan & Susnjak) | 2023 | IEEE Access / arXiv:2302.02094 | Phương pháp tiếp cận prompt-engineering (kỹ thuật gợi ý) cho NL (ngôn ngữ tự nhiên) → mã code trực quan hóa Python. | LOW | C |
| MatPlotAgent: LLM-Based Agentic Scientific Data Visualization (Yang và cộng sự) | 2024 | ACL Findings / arXiv:2402.11453 | LLM đa phương thức (Multi-modal) với phản hồi trực quan để sửa lỗi biểu đồ; tập đánh giá MatPlotBench. | LOW | C |
| Data Formulator 2: Iterative Creation of Data Visualizations with AI Data Transformation (Wang và cộng sự) | 2024 | arXiv:2408.16119 | Kết hợp giữa GUI + NL cho việc trực quan hóa lặp lại (iterative viz) với "các luồng dữ liệu" (data threads). | LOW | C |
| DAgent: A Relational Database-Driven Data Analysis Report Generation Agent (Xu và cộng sự) | 2025 | arXiv:2503.13269 | Agent NL-to-report (từ ngôn ngữ tự nhiên ra báo cáo) end-to-end trên các DB quan hệ (relational DBs); giới thiệu DA-Dataset benchmark. | LOW | C |
| Spider2-V: How Far Are Multimodal Agents From Automating DS/Engineering Workflows? (Cao và cộng sự) | 2024 | NeurIPS 2024 / arXiv:2407.10956 | 494 tác vụ doanh nghiệp qua 20 ứng dụng; SOTA agents đạt tỷ lệ thành công 14–30%. | LOW | C |
| ChartGPT: Leveraging LLMs to Generate Charts from Abstract Natural Language (Tian và cộng sự) | 2023/2024 | IEEE TVCG / arXiv:2311.01920 | Phân rã CoT (Chain-of-Thought) 6 bước cho việc tạo biểu đồ. | LOW | C |
| A Survey of Data Agents: Emerging Paradigm or Overstated Hype? (Zhu và cộng sự) | 2025 (sửa đổi Tháng 2 năm 2026) | arXiv:2510.23587 | Taxonomy quyền tự trị phân cấp L0-L5. | LOW | C |
| Data Quality Toolkit: Automatic Assessment of DQ for ML Datasets (Gupta và cộng sự, IBM) | 2021 | arXiv:2108.05935 | Đánh giá DQ chuyên biệt cho ML + remediation (biện pháp khắc phục). | LOW | C |
| DA-Code: Agent Data Science Code Generation Benchmark (nhiều tác giả) | 2024 | ACL 2024 / arXiv:2410.07331 | 500 tác vụ DS thực tế; DA-Agent baseline đạt độ chính xác 30.5%. | LOW | C |
| Profiling Relational Data – A Survey (Abedjan và cộng sự) | 2015 | VLDB Journal 24(4):557–581 | Taxonomy nền tảng của các tác vụ profiling đơn cột (single-column) và đa cột (multi-column). | LOW | G |
| Tasks and Visualizations Used for Data Profiling: A Survey and Interview Study (Ruddle và cộng sự) | 2023 | IEEE TVCG / DOI:10.1109/TVCG.2023.3299452 | Nghiên cứu thực nghiệm về các thực tiễn profiling của 53 nhà phân tích. | LOW | G |
| Large language models on tabular data: Prediction, generation, and understanding — a survey (Fang và cộng sự) | 2024 | TMLR | Các khả năng/giới hạn của LLM trên các tác vụ tabular (dữ liệu dạng bảng). | LOW | G |
| DataPrep.EDA: Task-Centric EDA for Statistical Modeling in Python (Peng và cộng sự) | 2021 | SIGMOD / arXiv:2104.00841 | API Python dạng khai báo (Declarative Python API) cho các tác vụ EDA phổ biến; dựa trên Dask. | LOW | G |
| QUIS: Question-guided Insights Generation for Automated EDA (Manatkar và cộng sự) | 2024 | EMNLP Industry / arXiv:2410.10270 | Pipeline zero-shot 2 giai đoạn QUGen + ISGen. | LOW | P |
| Quality Assessment of Tabular Data using LLMs and Code Generation (Akella và cộng sự) | 2025 | arXiv:2509.10572 | Việc tạo luật (rule generation) LLM được hỗ trợ bởi RAG + các validators (trình xác thực) có thể thực thi cho DQ. | LOW | P |
| LLM-Based Data Science Agents: A Survey of Capabilities, Challenges, and Future Directions (Rahman và cộng sự) | 2025 | arXiv:2510.04023 | Lập bản đồ 45 hệ thống trên 6 giai đoạn vòng đời DS; phát hiện >90% thiếu trust/safety (sự tin cậy/an toàn). | LOW | P |
| A Survey on LLM-based Agents for Statistics and Data Science (Hiệp hội Trung Quốc) | 2024 | arXiv:2412.14222 | Các pattern (mẫu) về planning (lập kế hoạch), reflection (suy ngẫm), multi-agent collaboration (cộng tác đa agent). | LOW | P |
| NL4DV: A Toolkit for Generating Analytic Specifications for Data Visualization from NL (Narechania và cộng sự) | 2020 | IEEE VIS / arXiv:2008.10723 | Bộ công cụ rule-based NL (ngôn ngữ tự nhiên dựa trên luật) trước thời đại LLM → Vega-Lite spec. | LOW | P |
| Generating Analytic Specifications for Data Visualization from NL using LLMs (Sah và cộng sự, NL4DV-LLM) | 2024 | NLVIZ @ IEEE VIS / arXiv:2408.13391 | Bản mở rộng GPT-4 của NL4DV với khả năng explainability (có thể giải thích). | LOW | P |
| Data-centric Artificial Intelligence: A Survey (Zha và cộng sự) | 2023 | arXiv:2303.10158 | Framework AI data-centric (lấy dữ liệu làm trung tâm) toàn diện. | LOW | P |
| Can LLMs Narrate Tabular Data? (Combo-Eval) (Singh và cộng sự, Oracle) | 2025 | arXiv:2510.23854 | Framework đánh giá đa phương pháp (Multi-method) cho các biểu diễn NL được tạo bởi LLM của kết quả SQL. | LOW | P |
| Why Do Open-Source LLMs Struggle with Data Analysis? (Zhu và cộng sự) | 2025 | arXiv:2506.19794 | Phát hiện ra rằng chất lượng strategic planning (lập kế hoạch chiến lược) là yếu tố quyết định chính đến hiệu suất DA (Phân tích Dữ liệu). | LOW | P |
| LLM/Agent-as-Data-Analyst: A Survey (Tang và cộng sự) | 2025 | arXiv:2509.23988 | Khảo sát các kỹ thuật LLM/agent cho dữ liệu không đồng nhất (heterogeneous data). | LOW | X |
| An LLM-Based Approach for Insight Generation in Data Analysis (Pérez và cộng sự) | 2025 | arXiv:2503.11664 | Các LLM tạo ra các text insights (phân tích dưới dạng văn bản) có thể hành động được từ dữ liệu đa bảng (multi-table data). | LOW | X |
| InsightLens: Augmenting LLM-Powered Data Analysis with Interactive Insight Management (Weng và cộng sự) | 2024 | arXiv:2404.01644 | Lớp quản lý insight tương tác (Interactive insight management). | LOW | X |
| AdaVis: Adaptive and Explainable Visualization Recommendation (Zhang và cộng sự) | 2023 | arXiv:2310.11742 | Đề xuất biểu đồ có thể giải thích dựa trên suy luận logic (Logical reasoning-based). | LOW | X |
| DataTales: A Benchmark for Real-World Intelligent Data Narration | 2024 [không chắc chắn] | arXiv [không chắc chắn] | Benchmark cho tường thuật dữ liệu dạng bảng (tabular-data narration). **Nguồn tự gắn cờ là chưa được xác minh (unverified).** | LOW | P [không chắc chắn] |

### Tóm tắt các bài báo có độ tin cậy CAO (HIGH-confidence)

**LIDA (Dibia 2023, ACL Demo, arXiv:2303.02927).** Pipeline LLM đa giai đoạn: SUMMARIZER → GOAL EXPLORER → VISGENERATOR → INFOGRAPHER. Nó là Grammar-agnostic (không phụ thuộc vào cú pháp) bởi vì nó tạo ra mã nguồn trực quan hóa trong bất kỳ thư viện đích nào (Matplotlib, Seaborn, Altair, D3). Mọi nguồn đều xác định đây là open-source architectural template (mẫu kiến trúc mã nguồn mở) gần gũi nhất; mô-đun SUMMARIZER là điểm tương đồng trực tiếp của "Senior Data Scientist narrative". Mã nguồn tại github.com/microsoft/lida.

**TiInsight (Zhu và cộng sự 2024/2025, PVLDB, arXiv:2412.07214 theo P/X; arXiv:2206.12909 theo G — xem §6).** Được triển khai production tại PingCAP. Giới thiệu Hierarchical Data Context (HDC - Ngữ cảnh Dữ liệu Phân cấp) để nén ngữ nghĩa của schema (lược đồ) cho LLM xử lý, sau đó tạo chuỗi question clarification (làm rõ câu hỏi) → TiSQL text-to-SQL → TiChart visualization (trực quan hóa bằng TiChart). Báo cáo đạt ~86.3% execution accuracy (độ chính xác khi thực thi) trên tập dữ liệu Spider với GPT-4. Đây là end-to-end system (hệ thống từ đầu đến cuối) được xác nhận production (production-validated) nhiều nhất trong các tài liệu dành cho DB-native LLM EDA.

**Large Language Model-based Data Science Agent: A Survey (Chen / Wang và cộng sự 2025, arXiv:2508.02744).** Khảo sát góc nhìn kép (Dual-perspective): agent-design perspective (góc nhìn thiết kế agent - các vai trò, cấu trúc thực thi, tích hợp kiến thức, sự suy ngẫm/reflection) giao thoa với DS-workflow perspective (góc nhìn quy trình làm việc DS - tiền xử lý, mô hình hóa, đánh giá, trực quan hóa). Khảo sát tổng quan (landscape survey) được trích dẫn nhiều nhất qua các báo cáo; được sử dụng như là tài liệu tham khảo định hình (framing reference) cho việc định vị các công cụ mới.

---

## 3. Các Kho lưu trữ (Repositories) GitHub — Đã tổng hợp

### 3.1 Các thư viện data profiling

| Kho lưu trữ (Repo) | URL | Số sao (Stars) | Hoạt động (Activity) | Chức năng (What it does) | Độ tin cậy (Confidence) | Nguồn (Sources) |
|---|---|---|---|---|---|---|
| **ydata-profiling** | github.com/ydataai/ydata-profiling (G liên kết đến fork fg-data-profiling — xem §6) | ~13.3k–13.6k | **Đang hoạt động (Active)** (Tháng 4 năm 2026 / Tháng 1 năm 2026 theo nhiều nguồn) | Các báo cáo EDA HTML/JSON bằng một dòng lệnh (one-line) cho pandas/Spark: phân phối (distributions), tương quan (correlations), giá trị thiếu (missing values), các cảnh báo chất lượng (quality alerts) | HIGH | C/G/P/X |
| **Sweetviz** | github.com/fbdesignpro/sweetviz | ~3.1k | **Tranh cãi (Disputed)** — C nói cũ (stale - v2.3.1, Tháng 11 năm 2023); G/P/X nói đang hoạt động (Tháng 4 năm 2026) | HTML so sánh mục tiêu mật độ cao (High-density target-comparison) + so sánh sự khác biệt (diffing) giữa train/test | HIGH | C/G/P/X |
| **D-Tale** | github.com/man-group/dtale | ~4.5k–5.1k | **Đang hoạt động (Active)** (v3.19.1, Tháng 1/Tháng 5 năm 2026) | Lưới tương tác (interactive grid) Flask+React + trình xây dựng biểu đồ (chart builder) cho pandas DataFrames | HIGH | C/G/P/X |
| **DataPrep** | github.com/sfu-db/dataprep | ~2.1k–2.2k | **Tranh cãi (Disputed)** — C/G nói cũ (Tháng 6 năm 2024 / Tháng 4 năm 2024); P/X nói hoạt động vừa phải (moderately active) | Các mô-đun EDA + Connector (kết nối) + Clean (làm sạch) dựa trên Dask; tốc độ ~10× pandas | HIGH | C/G/P/X |
| **AutoViz** | github.com/AutoViML/AutoViz | ~1.6k–1.9k | **Tranh cãi (Disputed)** — G nói cũ (~2023); C/P nói đang hoạt động; bao gồm `FixDQ()` | Auto-visualization bằng một dòng lệnh cho mọi kích thước tập dữ liệu | HIGH | C/G/P/X |
| **klib** | github.com/akanz1/klib | ~522–~900 | **Tranh cãi (Disputed)** — C nói đang hoạt động (v1.4.0 Tháng 2 năm 2026); P nói cũ (lần cập nhật cuối 2023) | Làm sạch nhẹ nhàng bằng một dòng (Lightweight one-line cleaning) + trực quan hóa (viz) | MEDIUM | C/P |
| **capitalone/DataProfiler** | github.com/capitalone/DataProfiler | ~1.1k | Đang hoạt động / hoạt động vừa phải | Phát hiện lược đồ (Schema), số liệu thống kê (stats), và PII/các thực thể nhạy cảm (sensitive-entity) qua học sâu (deep learning) | MEDIUM | P/X |
| Lux | github.com/lux-org/lux | ~5.4k | **Tranh cãi (Disputed)** — C nói cũ (2021–2022); G nói đang hoạt động (2025) | Các khuyến nghị auto-viz (tự động trực quan hóa) dưới dạng extension (tiện ích mở rộng) của pandas DataFrame; chỉ dành cho Jupyter | MEDIUM | C/G |
| gventuri/pandas-profiling | (fork cũ) | không chắc chắn | Cũ (Stale) | Tên tiền nhiệm mang tính lịch sử; được thay thế (superseded) bởi ydata-profiling | LOW | P [không chắc chắn] |
| smalltech/auto-eda | (Không cung cấp URL) | không chắc chắn | Cũ (Stale) | Trình tạo báo cáo auto-EDA đơn giản | LOW | P [không chắc chắn — có thể là hallucinated (ảo giác); hãy xác minh trước khi tin cậy] |

### 3.2 Các data agents được hỗ trợ bởi LLM

| Kho lưu trữ (Repo) | URL | Số sao (Stars) | Hoạt động (Activity) | Chức năng (What it does) | Độ tin cậy (Confidence) | Nguồn (Sources) |
|---|---|---|---|---|---|---|
| **PandasAI** | github.com/sinaptik-ai/pandas-ai | ~16k (P) / ~20k+ (X) / ~23.5k (C) / ~23.6k (G) — **số sao thay đổi (star counts vary)** | **Đang hoạt động** (v3.0.0, Tháng 10 năm 2025; YC W24) | Các truy vấn NL (ngôn ngữ tự nhiên) trên DataFrames/SQL bằng LLM + RAG, tạo biểu đồ (chart generation), sandbox Docker | HIGH | C/G/P/X |
| **Vanna AI** | github.com/vanna-ai/vanna | ~23.4k–23.5k | **MÂU THUẪN (CONTRADICTION)** — C/G/X nói đã lưu trữ (archived - Tháng 3 năm 2026); P (Pro) nói "Đang hoạt động (cập nhật Tháng 2 năm 2026)" | Text-to-SQL dựa trên RAG; self-learning (tự học) từ schema + lịch sử truy vấn; 20+ trình kết nối DB (DB connectors) | HIGH | C/G/P/X (trạng thái đang tranh cãi) |
| **LIDA** | github.com/microsoft/lida | ~3.2k–4.5k | **Tranh cãi (Disputed)** — C nói cũ (2023–2024); G/P/X nói đang hoạt động hoặc hoạt động vừa phải | Tạo biểu đồ + infographic grammar-agnostic (không phụ thuộc cú pháp) được điều khiển bởi LLM | HIGH | C/G/P/X |
| **Jupyter AI** | github.com/jupyterlab/jupyter-ai | ~3.8k–4.2k | **Đang hoạt động** (v3.0.0rc0; Tháng 4 năm 2026) | Extension của JupyterLab: giao diện trò chuyện (chat UI) + lệnh %%ai magic; hỗ trợ đa LLM (multi-LLM support) bao gồm local LLMs (LLMs chạy cục bộ) | HIGH | C/G/P |
| **Sketch** | github.com/approximatelabs/sketch | ~2.3k–2.6k | **Tranh cãi (Disputed)** — C/P nói cũ (>18 tháng / 2023); G nói đang hoạt động (Tháng 1 năm 2024) | NL → mã code pandas; nhận biết ngữ cảnh dữ liệu (data-context aware) thông qua việc phác thảo (sketching) | HIGH | C/G/P |
| OpenInterpreter | github.com/openinterpreter/open-interpreter | ~63.6k | Đang hoạt động | NL đa mục đích (General-purpose NL) → thực thi mã code cục bộ (local code execution). **Mấp mé ranh giới (Borderline) — xem phụ lục.** | LOW | C |
| MetaGPT (with DataInterpreter) | github.com/geekan/MetaGPT | ~40k+ | Đang hoạt động (v0.8.0 Tháng 3 năm 2024) | Framework đa agent (Multi-agent framework) với DataInterpreter cho quy trình E2E DS (Data Science từ đầu đến cuối) | LOW | C |
| LangChain | github.com/langchain-ai/langchain | ~123k+ | Đang hoạt động | Framework chung (General framework) với các pandas/SQL/CSV agents. **Mấp mé ranh giới — xem phụ lục.** | LOW | C |
| Inconvo | github.com/inconvoai/inconvo | ~105 | Đang hoạt động (2026) | Framework trò chuyện với dữ liệu (Chat-with-data) tích hợp RBAC + safe queries (truy vấn an toàn) | LOW | G |
| DeepInsight-AI/DeepBI | github.com/DeepInsight-AI/DeepBI | không chắc chắn | Đang hoạt động | Phân tích đàm thoại (conversational analytics) AI-native đa nguồn + các dashboards (bảng điều khiển) | LOW | P |
| The-Pocket/PocketFlow-Tutorial-Data-Profiler | github.com/The-Pocket/PocketFlow-Tutorial-Data-Profiler | không chắc chắn | Đang hoạt động | Bản demo / hướng dẫn (tutorial) profiling dựa trên LLM | LOW | P [không chắc chắn] |

### 3.3 Auto-visualization (Tự động trực quan hóa) / narrative reporting (báo cáo tường thuật)

| Kho lưu trữ (Repo) | URL | Số sao (Stars) | Hoạt động (Activity) | Chức năng (What it does) | Độ tin cậy (Confidence) | Nguồn (Sources) |
|---|---|---|---|---|---|---|
| **LIDA** | (xem §3.2) | — | — | Cũng được liệt kê ở đây bởi P và X — cùng một repo như trong 3.2 | HIGH | C/G/P/X |
| NL4DV (Python toolkit) | github.com/arpitomprakash/nl4dv (và PyPI) | ~200 | Được bảo trì (Maintained) | Trình tạo (generator) NL → Vega-Lite spec từ trước thời LLM (Pre-LLM); bản mở rộng bằng LLM (LLM extension) tồn tại dưới dạng bài báo | LOW | P |
| Chat2VIS (Streamlit) | github.com/frog-land/Chat2VIS_Streamlit | dành cho nghiên cứu | Dành cho nghiên cứu (Research) (2023) | Bản demo NL → viz (trực quan hóa) bằng Streamlit | LOW | C |
| lida-project/lida-streamlit | github.com/lida-project/lida-streamlit | không chắc chắn | Đang hoạt động [không chắc chắn] | Ví dụ đóng gói bằng Streamlit (Streamlit packaging) cho LIDA | LOW | P [không chắc chắn] |
| "Các forks/extensions liên quan cho việc tích hợp Streamlit" (không chỉ định rõ) | — | — | — | Chỉ đề cập chung chung (Generic mention only) — không có repo cụ thể nào | LOW | X [mơ hồ (vague)] |

### 3.4 Chất lượng dữ liệu (Data quality) / phát hiện bất thường (anomaly detection)

| Kho lưu trữ (Repo) | URL | Số sao (Stars) | Hoạt động (Activity) | Chức năng (What it does) | Độ tin cậy (Confidence) | Nguồn (Sources) |
|---|---|---|---|---|---|---|
| **Great Expectations** | github.com/great-expectations/great_expectations | ~10k–~12k | **Đang hoạt động** (Tháng 5 năm 2026; Python 3.10–3.14) | Framework "Expectations" (kỳ vọng) dạng khai báo (Declarative); các báo cáo Data Docs HTML; thân thiện với CI/CD | HIGH | C/G/P/X (X nói "được ngụ ý trong hệ sinh thái (implied in ecosystem)") |
| **Evidently** | github.com/evidentlyai/evidently | ~7.5k | Đang hoạt động | Phát hiện sự trôi lệch (Drift detection) (20+ bài kiểm tra), giám sát dữ liệu + mô hình (model + data monitoring), các bộ thử nghiệm (test suites) | HIGH | C/G/P |
| Deequ | github.com/awslabs/deequ | ~3.6k | Đang hoạt động (Tháng 3 năm 2026) | Kiểm tra chất lượng dữ liệu Spark-native (nguyên bản trên Spark) ở quy mô lớn (at scale) | MEDIUM | G/P |
| pandera | github.com/unionai-oss/pandera | ~4.3k | Đang hoạt động (v0.31.1, Tháng 4 năm 2026) | Xác thực lược đồ (Schema validation) cho pandas/Polars/PySpark/Xarray; giống với pydantic | LOW | C |
| whylogs | github.com/whylabs/whylogs | đáng kể | Đang hoạt động (OSS (mã nguồn mở) vẫn tiếp tục sau sự kiện WhyLabs/Apple) | Các hồ sơ thống kê bảo vệ quyền riêng tư (Privacy-preserving statistical profiles); có thể hợp nhất (mergeable); truyền phát (streaming) | LOW | C |
| deepchecks | github.com/deepchecks/deepchecks | đáng kể | Đang hoạt động (được Check Point mua lại, Tháng 5 năm 2026) | Bộ xác thực (validation suite) Tabular/NLP/CV | LOW | C |
| Soda Core | URL không chắc chắn | không chắc chắn | Đang hoạt động | Kiểm tra chất lượng dữ liệu bằng YAML (SodaCL) | LOW | C [không chắc chắn] |
| DataKitchen TestGen | github.com/DataKitchen/dataops-testgen | ~1.5k | Đang hoạt động (2025) | Tự động tạo ra (Auto-generates) ~60 bài kiểm tra DQ (Chất lượng Dữ liệu) từ profiling; giám sát bất thường (anomaly monitoring); thẻ điểm (scorecards) | LOW | P |
| tensorflow/data-validation | github.com/tensorflow/data-validation | không chắc chắn | Đang hoạt động | Xác thực thống kê (Statistical validation) cho dữ liệu huấn luyện/phục vụ ML (ML training/serving data) | LOW | P [không chắc chắn] |
| OpenRefine | github.com/OpenRefine/OpenRefine | không chắc chắn | Đang hoạt động | Làm sạch dữ liệu tương tác (Interactive data cleaning) và đối chiếu (reconciliation) | LOW | P [không chắc chắn] |

### 3.5 Trình tạo báo cáo EDA full-stack (toàn diện)

| Kho lưu trữ (Repo) | URL | Số sao (Stars) | Hoạt động (Activity) | Chức năng (What it does) | Độ tin cậy (Confidence) | Nguồn (Sources) |
|---|---|---|---|---|---|---|
| **D-Tale** | (xem §3.1) | — | — | Cũng được G liệt kê ở đây dưới dạng full-stack | HIGH | C/G/P/X |
| **AutoViz** | (xem §3.1) | — | — | Cũng được X liệt kê ở đây | HIGH | C/G/P/X |
| Devang-C/AutoEDA | github.com/Devang-C/AutoEDA | ~200 | Cũ (2023) | Ứng dụng Streamlit EDA: tổng quan (overview), phân phối (distributions), tương quan (correlations) | LOW | P |
| exploratoryio/exploratory | github.com/exploratoryio/exploratory | không chắc chắn | Đang hoạt động [không chắc chắn] | Công cụ phân tích Desktop: chuẩn bị dữ liệu (data prep), viz (trực quan hóa), ghi chú, dashboards | LOW | P [không chắc chắn] |
| pingcap/tiinsight | (URL được tuyên bố; chưa xác nhận công khai) | n/a | Production (Nội bộ PingCAP) | Hệ thống TiInsight (đi kèm với bài báo) | LOW | P [không chắc chắn — "chưa được niêm yết công khai (not publicly listed) tính đến ngày khảo sát"] |

---

## 4. Các Công cụ Thương mại (Commercial Tools) — Đã tổng hợp

| Nhà cung cấp (Vendor) | Mô tả (Description) | Điểm giao thoa với dự án (Overlap with project) | Định giá (Pricing) | Độ tin cậy (Confidence) | Nguồn (Sources) |
|---|---|---|---|---|---|
| **Julius AI** | Nhà phân tích dữ liệu AI (AI data analyst) trên Excel/CSV/Google Sheets và (theo C) các DB như Snowflake, BigQuery, Redshift, Postgres, MySQL; truy vấn NL → biểu đồ, mô hình, tóm tắt | Khả năng tường thuật (narrative) + báo cáo mạnh mẽ; tập trung vào tệp (file-focused) theo X, có khả năng xử lý DB (DB-capable) theo C | Miễn phí 15 tin nhắn/tháng; Basic $20/tháng; Essential $45/tháng (Các cấp Pro/Business theo C) | HIGH | C/G/P/X |
| **Hex** | Nền tảng notebook SQL+Python cộng tác với "Hex Magic" / Notebook Agent / Threads | EDA bằng SQL/Python, NL-to-code (NL thành code), các insights AI, dashboards; kết nối tới Snowflake/BigQuery/Redshift/Databricks/Postgres | Gói Starter $25/người dùng/tháng (P); gọi vốn được 70 triệu đô la vào Tháng 5 năm 2025; tùy chỉnh cho doanh nghiệp (enterprise custom) | HIGH | C/G/P/X |
| **Tableau Pulse (Salesforce)** | Chủ động (Proactive) đưa ra các thông tin chi tiết về số liệu AI (AI metric insights), Hỏi đáp NL (NL Q&A), phân tích nguyên nhân gốc rễ (root-cause analysis) qua Slack/email | Mạnh về tường thuật (narrative) & chủ động đưa ra các insight; **metric-centric (lấy số liệu làm trung tâm), không phải profile-centric (lấy hồ sơ làm trung tâm)** (X) | Là một phần của Tableau Cloud; ~$70–$75/người dùng/tháng cho Creator/Standard | HIGH | C/G/P/X |
| **Akkio** | AI No-code (không cần viết code) cho khâu chuẩn bị (prep) + mô hình hóa dự đoán (predictive modeling) + Chat Explore + Generative Reports (Báo cáo sinh bằng AI) | Profiling, dự đoán, khám phá bằng NL; tập trung vào các agency (đại lý/tổ chức) | Starter $49/tháng (C); được báo cáo là Starter $349/tháng (G); Pro $99/người dùng/tháng; Build-On $999/tháng; Tùy chỉnh Enterprise — **dữ liệu định giá mâu thuẫn giữa các nguồn** | HIGH | C/G/P/X |
| **Mode Analytics** | Phân tích cộng tác SQL/Python/R; AI Assist (Hỗ trợ AI) cho SQL | Giao thoa ở mảng Báo cáo/EDA; không phải profiling tự trị (autonomous profiling) | Liên hệ để có giá (P-Pro: được ThoughtSpot mua lại) | HIGH | G/P/X |
| **Athenic AI** | NL analytics agent tự trị, luôn bật (always-on) trên các DB/warehouses (kho dữ liệu) | NL-to-SQL, khám phá insight đa nguồn (multi-source insight discovery); tập trung vào truy vấn (query-focused) theo X; root-cause (nguyên nhân gốc rễ) + anomaly detection theo C | Không niêm yết công khai; có bản dùng thử miễn phí; gọi vốn 4.3 triệu đô la vào Tháng 1 năm 2025 (theo C) | HIGH | C/G/P/X (X chỉ đề cập ngắn gọn) |
| **ThoughtSpot** | Phân tích agentic với NL search (tìm kiếm bằng NL) + agent "Spotter" | Phân tích mẫu tự động (Auto pattern analysis) (SpotIQ); giám sát bất thường + DQ; các giải thích NL đa bước (multi-step NL explanations) | Enterprise + dựa trên mức độ tiêu thụ (consumption-based); tùy chỉnh; AWS Marketplace | MEDIUM | C/P |
| **Microsoft Power BI Copilot / Q&A** | Soạn thảo BI (BI authoring) do Copilot hỗ trợ + NL Q&A | Tóm tắt tường thuật (Narrative summaries), các visuals được tạo ra | Bao gồm trong một số gói (plans) của Microsoft | MEDIUM | G/P |
| **YData Fabric / Data Catalog** | Data catalog (Danh mục dữ liệu) + nền tảng tập trung vào profiling với khả năng kết nối DB | Mạnh về profiling + quality + thấu hiểu dữ liệu (data understanding) | Tùy chỉnh Enterprise | LOW | P |
| **Sigma Computing** | Phân tích đám mây giống-Spreadsheet (bảng tính) với các tính năng AI | Khám phá hướng tới kinh doanh (Business-facing exploration) + vẽ biểu đồ (charting) | SaaS trả phí (Paid SaaS) | LOW | P |
| **Zenlytic** | BI tự phục vụ (Self-service BI) với chuyên gia phân tích AI "Zoë"; tự động giới thiệu (auto-onboards) + governed semantic layer (lớp ngữ nghĩa được quản lý) | Kết nối Snowflake/BigQuery/Redshift/Databricks/Athena/Synapse/Postgres/MySQL; Zoë tạo ra các bản phân tích, memos (bản ghi nhớ), PowerPoint | Dùng thử miễn phí; 9 triệu đô la Series A (2025) | LOW | C |
| **DataChat** | Phân tích đàm thoại No-code; **xử lý dữ liệu in-database (trong cơ sở dữ liệu), không bao giờ gửi tới các LLM** | Làm sạch tích hợp sẵn (Built-in cleaning) + phân tích giá trị ngoại lệ (outlier analysis); minh bạch/có thể tái tạo (transparent/reproducible) | Không niêm yết công khai; AWS Marketplace; được Mews mua lại (2025) | LOW | C |
| **DataKitchen (Enterprise)** | Bậc Enterprise xếp trên mã nguồn mở TestGen | DQ profiling full-stack + tests + observability (khả năng quan sát) + bảng điều khiển chất lượng (quality dashboards) | Tùy chỉnh Enterprise (mức phí cố định (flat-rate), không giới hạn bảng) | LOW | P |
| Google Looker (Smart Lenses) | BI với các tính năng NL | Chỉ được đề cập ngắn gọn — dòng "Những công cụ khác (Others)" | n/a | LOW | G |
| Grist, Aible | Được đề cập trong dòng "Những công cụ khác", không có chi tiết | — | n/a | LOW | G |

---

## 5. Phân tích Khoảng trống (Gap Analysis) — Đã gộp

### 5.1 Các khoảng trống được đồng thuận (3+ báo cáo — coi như là thực tế)

- **Bài tường thuật (narrative) của "Senior Data Scientist" LLM được đối chiếu (grounded) trên các số liệu thống kê đã được xác minh.** Mọi nguồn đều xác định đây là khoảng trống chính chưa được lấp đầy. Các công cụ mở (Open tools) hoặc là tính toán số liệu thống kê mà không có tường thuật, hoặc là tạo ra các bài tường thuật mà không đối chiếu (without grounding). Trích dẫn rủi ro (Risk citation): Claude báo cáo tỷ lệ hallucination thực tế 59–82% trên nội dung số (numeric content); Perplexity Pro trích dẫn Akella và cộng sự (2025) cùng Combo-Eval như là các biện pháp giảm thiểu (mitigations) trực tiếp nhất. [C/G/P/X]
- **Pipeline liền mạch từ đầu đến cuối (End-to-end seamless pipeline): Kết nối DB/CSV → automated profiling → DQ detection → visualization → LLM narrative → báo cáo được chau chuốt (polished report).** Không có công cụ mã nguồn mở nào bao phủ cả năm lớp ở chất lượng production. Thị trường đang bị phân đôi (bifurcated): các trình lập hồ sơ cổ điển (classical profilers) (ydata-profiling, Sweetviz) cung cấp các số liệu thống kê chuyên sâu nhưng không có lớp LLM hoặc DB; Các LLM agents (PandasAI, Vanna) cung cấp khả năng đàm thoại nhưng yêu cầu dữ liệu phải được tải sẵn (pre-loaded) và bỏ qua quá trình automated profiling. [C/G/P/X]
- **Hallucination về thống kê số liệu của LLM.** Được mọi nguồn trích dẫn là rủi ro kỹ thuật chưa có lời giải có tác động cao nhất. Các framework xác minh (ví dụ: Combo-Eval, multi-agent critics - hệ thống đánh giá đa tác nhân) tồn tại trong nghiên cứu nhưng không được triển khai end-to-end trong bất kỳ công cụ open-source production nào. [C/G/P/X]
- **Bảo mật của việc chạy các truy vấn/mã code được tạo ra (generated code/queries) đối với các cơ sở dữ liệu trực tiếp (live databases).** Các rủi ro: prompt injection (tiêm nhiễm chỉ thị) thông qua dữ liệu cột, data exfiltration (đánh cắp dữ liệu), goal hijacking (chiếm đoạt mục tiêu), accidental destructive ops (vô tình thực hiện các hoạt động phá hoại). PandasAI sử dụng Docker sandboxing và DataChat xử lý in-database, nhưng các framework toàn diện giải quyết vấn đề OWASP LLM Top 10 / Agentic Top 10 đều vắng bóng. Khảo sát của Rahman (theo P) phát hiện ra rằng >90% các agents thiếu cơ chế trust/safety rõ ràng. [C/G/P/X]
- **Khả năng mở rộng (Scale) trên các bảng lớn.** Hầu hết các profilers dựa trên DataFrame đều tải toàn bộ bảng vào bộ nhớ (memory). Backend Dask của DataPrep là một ngoại lệ. Các cửa sổ ngữ cảnh (context windows) của LLM khiến việc xử lý các bảng rộng (hơn 1000 cột) trở nên bất khả thi nếu không thực hiện aggressive sampling (lấy mẫu theo cách mạnh tay), điều này gây ra độ lệch thống kê (statistical bias). [C/G/P/X]

### 5.2 Các khoảng trống được đồng thuận một phần (2 báo cáo — có khả năng là thực tế)

- **Phát hiện Schema drift (trôi lệch lược đồ) kèm theo bài tường thuật giải thích (explanatory narrative).** Evidently và whylogs phát hiện được sự trôi lệch, nhưng không chẩn đoán được các nguyên nhân gốc rễ (root causes) hoặc đánh giá các tác động lên luồng dữ liệu sau đó (downstream impact). [C/P]
- **Khắc phục (remediation) DQ tự động vượt ra ngoài việc chỉ phát hiện.** Các công cụ phát hiện tốt các missing values (giá trị thiếu), outliers (giá trị ngoại lệ), duplicates (bản sao), nhưng không tự động sửa (auto-fix) theo những cách nhận biết ngữ cảnh (context-aware ways). IBM Data Quality Toolkit (2021) là một nỗ lực đầu tiên (early attempt). [C/P]
- **Khả năng khái quát hóa đa miền (Cross-domain generalization).** Các prompts (câu lệnh) "Senior Data Scientist" chung chung (Generic) sẽ bị suy giảm hiệu quả trên dữ liệu tài chính/y sinh/v.v. nếu không có domain-adapted prompting (prompting được điều chỉnh cho phù hợp với từng miền cụ thể) (theo P, trích dẫn bài "Why Open-Source LLMs Struggle" của Zhu năm 2025). [P/X]

### 5.3 Các khoảng trống chỉ từ một nguồn (1 báo cáo — hãy xác minh trước khi theo đuổi)

- **Tính di động của báo cáo (Report portability) và versioning (quản lý phiên bản) (Các cổng chất lượng dữ liệu CI/CD - CI/CD data quality gates).** Không có trình tạo báo cáo EDA open-source nào sản xuất ra các báo cáo có phiên bản (versioned), có thể diff (so sánh sự khác biệt) được. [Chỉ P]
- **Prompt injection thông qua dữ liệu cột.** Các giá trị ô được tạo ra với ý đồ xấu (Adversarially crafted cell values) có thể ghi đè (override) các system prompts; chưa được chống lại bởi bất kỳ công cụ nào đã được đánh giá. [Chỉ P]
- **Đánh giá/kiểm tra các agents không tất định (non-deterministic agents).** Kiểm thử truyền thống giả định tính tất định (determinism); hầu hết các nhóm đành phải dùng cách "được kiểm thử thủ công (tested manually)" hoặc "giám sát trong production (monitor in production)." [Chỉ C]
- **Chất lượng NL không nhất quán qua các miền tập dữ liệu (dataset domains)** — chất lượng strategic planning (lập kế hoạch chiến lược), chứ không phải năng lực LLM thô, mới là thứ quyết định chất lượng đầu ra (theo P trích dẫn Zhu 2025 arXiv:2506.19794). [Chỉ P]
- **Phản hồi tương tác (Interactive feedback) (tinh chỉnh truy vấn - refining queries) bị hạn chế bên ngoài các nguyên mẫu nghiên cứu (research prototypes).** continuous-profiling-plus-LLM-summary (profiling liên tục kết hợp với tóm tắt của LLM) không được thấy trong bất kỳ sản phẩm đơn lẻ nào. [Chỉ G]

### 5.4 Top 3 điểm khác biệt (differentiators) cho dự án

1. **Bài tường thuật (narrative) của "Senior Data Scientist" LLM đáng tin cậy được đối chiếu (grounded) trên các số liệu thống kê đã được xác minh.** Mọi nguồn đều xếp hạng điều này ở vị trí đầu tiên hoặc gần đầu. Có thể đạt được (Achievable) bởi vì các số liệu thống kê cơ bản là tất định (deterministic); thách thức kỹ thuật (engineering challenge) nằm ở việc xác minh (verification), chứ không phải tạo ra (generation).
2. **Pipeline từ đầu đến cuối (End-to-end pipeline): Kết nối DB → profiling → DQ detection → visualization → narrative → report.** Mọi nguồn đều lưu ý về sự phân đôi thị trường (market bifurcation); lấp đầy được nó là một định vị (positioning) độc nhất.
3. **Thực thi DQ (DQ enforcement) một cách rõ ràng cùng với các prescriptive recommendations (các khuyến nghị mang tính chỉ dẫn)** (không chỉ là "có 47 missing values ở cột X" mà phải là "điều này nhiều khả năng gây ra bởi Y, sau đây là 3 biện pháp khắc phục (remediations)"). Claude chỉ ra điều này một cách rõ ràng; Grok diễn đạt nó là "các báo cáo sẵn sàng cho xuất bản (publication-ready reports) với các trích dẫn (citations) đến các tính toán cơ bản."

---

## 6. Các Mâu thuẫn & Bất đồng (Contradictions & Disagreements)

- **Mã TiInsight arXiv ID.** G trích dẫn arXiv:2206.12909 (một ID của tháng 6 năm 2022 — không nhất quán với tuyên bố "VLDB 2025"); P (Pro) và X trích dẫn arXiv:2412.07214 (Tháng 12 năm 2024). Mã sau khớp với hệ thống PingCAP được triển khai production; URL của G dường như là một lỗi đánh máy (typo) hoặc trích dẫn nhầm bài báo. **Dành cho người dùng:** hãy coi 2412.07214 là URL hoạt động (working URL) nhưng hãy xác minh trực tiếp trên arXiv trước khi trích dẫn trong văn bản.
- **Mã InReAcTable arXiv ID.** G trích dẫn arXiv:2412.06819 (Tháng 12 năm 2024); P (Pro) trích dẫn arXiv:2508.18174 (Tháng 8 năm 2025). Những bài báo này có thể là các tác phẩm riêng biệt hoặc các phiên bản khác nhau của cùng một bài. **Dành cho người dùng:** hãy kiểm tra cả hai ID trên arXiv trước khi coi chúng là cùng một bài báo.
- **Mã AutoProfiler / Dead or Alive arXiv ID.** G trích dẫn doi.org/10.48550/arXiv.2305.07126; P trích dẫn arXiv:2308.03964. Các ID khác nhau cho cùng một tác phẩm của Epperson và cộng sự theo như mô tả. **Dành cho người dùng:** hãy xác minh đâu là bản in trước (preprint) chính thức (canonical).
- **Trạng thái của Vanna repository.** C, G, và X nói đã lưu trữ (archived - Tháng 3 năm 2026); P (Pro Research) nói "Đang hoạt động (cập nhật Tháng 2 năm 2026)." Đây là mâu thuẫn thực tế lớn nhất trong tập các nguồn. **Dành cho người dùng:** hãy kiểm tra trực tiếp repo GitHub trước khi bất kỳ quyết định kiến trúc nào phụ thuộc vào việc Vanna đang được bảo trì.
- **Hoạt động của Lux.** C nói cũ (2021–2022); G nói đang hoạt động (2025). **Dành cho người dùng:** hãy xác minh lịch sử commit gần đây.
- **Hoạt động của Sweetviz.** C nói cũ (v2.3.1, Tháng 11 năm 2023); G/P/X nói đang hoạt động (Tháng 4 năm 2026). **Dành cho người dùng:** sự đồng thuận (consensus) là đang hoạt động, nhưng các chi tiết cụ thể "v2.3.1, Tháng 11 năm 2023" của Claude là đủ cụ thể (concrete) để đảm bảo (warrant) phải kiểm tra trực tiếp.
- **Hoạt động của LIDA.** C nói cũ (2023–2024); G/P/X nói đang hoạt động hoặc hoạt động vừa phải (Tháng 3 năm 2024 / 2026). **Dành cho người dùng:** sự đồng thuận là đang hoạt động; Claude là ngoại lệ (outlier).
- **Hoạt động của AutoViz.** G nói cũ (~2023); C/P nói đang hoạt động với các commit gần đây. **Dành cho người dùng:** sự đồng thuận là đang hoạt động; G là ngoại lệ.
- **Hoạt động của DataPrep.** C/G nói cũ (Tháng 6 năm 2024 / Tháng 4 năm 2024); P/X nói hoạt động vừa phải hoặc "hơi có vẻ đang hoạt động (active-ish)." **Dành cho người dùng:** tỷ lệ 2-2; nghiêng về (lean) cũ (stale).
- **Hoạt động của Sketch.** C/P nói cũ (>18 tháng / 2023); G nói đang hoạt động (Tháng 1 năm 2024). **Dành cho người dùng:** nghiêng về cũ (stale); trạng thái "đang hoạt động" của G là ngoại lệ.
- **URL chính thức (canonical URL) của ydata-profiling.** G liên kết đến github.com/Data-Centric-AI-Community/fg-data-profiling (một fork); C/P liên kết đến github.com/ydataai/ydata-profiling (nguyên bản - original); X đề cập đến cả hai ("ydata-profiling … hoặc phiên bản kế nhiệm (successor) fg-data-profiling"). **Dành cho người dùng:** bản gốc chính thức (canonical original) là ydataai/ydata-profiling; fg-data-profiling dường như là một fork — trạng thái "kế nhiệm" của nó chỉ được khẳng định (asserted) bởi Grok và **chưa được chứng thực (uncorroborated)**.
- **Định giá Akkio Starter.** C nói $49/tháng; G nói ~$349/tháng. **Dành cho người dùng:** hãy kiểm tra trực tiếp trang giá hiện tại của Akkio.
- **Số lượng sao (Star counts).** PandasAI dao động từ 16k (P) → 23.6k (G). LIDA dao động từ 3.2k (C/G) → 4.5k (P). D-Tale dao động từ 4.5k (P) → 5.1k (C/G). Đây có thể là những khác biệt về thời điểm chụp dữ liệu (snapshot timing differences) chứ không phải là những sự bất đồng; không có khả năng hành động (not actionable) nhưng đáng chú ý nếu số lượng sao chính xác quan trọng.

---

## 7. Các Phát hiện từ Nguồn Đơn lẻ (Single-Source Findings) — Hãy Xác minh Trước khi Tin cậy

Các mục (items) một nguồn này có thể là những viên ngọc hiếm (rare gems) (nguồn duy nhất nhận thấy chúng) hoặc là những ảo giác (hallucinations) (nguồn đã bịa ra hoặc nhớ nhầm). Hãy xác minh trước khi kết hợp (incorporating) vào.

### Chỉ từ Claude (C)

- **Data Interpreter (Hong và cộng sự 2024, arXiv:2402.18679).** DS agent dùng đồ thị phân cấp (Hierarchical-graph). *Có khả năng là thật (Likely real):* Mã arXiv ID có vẻ đúng, ACL Findings là hợp lý (plausible).
- **InfiAgent-DABench (Hu và cộng sự 2024, ICML, arXiv:2401.05507).** Benchmark gồm 603 câu hỏi / 124 CSVs. *Có khả năng là thật:* các con số cụ thể, nơi xuất bản hợp lý.
- **DS-1000 (Lai và cộng sự, ICML 2023, arXiv:2211.11501).** *Có khả năng là thật:* benchmark DS có nguồn từ Stack-Overflow được trích dẫn rộng rãi.
- **Chat2VIS (Maddigan & Susnjak 2023, IEEE Access).** *Có khả năng là thật:* arXiv:2302.02094 hợp lý.
- **MatPlotAgent (Yang và cộng sự 2024, arXiv:2402.11453).** *Có khả năng là thật.*
- **Data Formulator 2 (Wang và cộng sự 2024, arXiv:2408.16119).** *Có khả năng là thật:* Nghiên cứu của Microsoft/MSR-Asia, tác giả nổi tiếng.
- **DAgent (Xu và cộng sự 2025, arXiv:2503.13269).** *Có khả năng là thật:* rất đúng chủ đề (on-topic) với dự án; **là một ứng viên mạnh (strong candidate) để điều tra.**
- **Spider2-V (Cao và cộng sự NeurIPS 2024, arXiv:2407.10956).** *Có khả năng là thật:* benchmark 494-task (tác vụ), tác giả nổi tiếng.
- **ChartGPT (Tian và cộng sự 2024, IEEE TVCG, arXiv:2311.01920).** *Có khả năng là thật.*
- **Survey of Data Agents: Emerging Paradigm or Overstated Hype? (Zhu và cộng sự 2025, arXiv:2510.23587).** Taxonomy L0–L5. *Có khả năng là thật, gần đây.*
- **Data Quality Toolkit (Gupta và cộng sự 2021, IBM, arXiv:2108.05935).** *Có khả năng là thật:* tác phẩm nghiên cứu nổi tiếng của IBM Research.
- **DA-Code (nhiều tác giả 2024, ACL, arXiv:2410.07331).** 500 tasks; DA-Agent 30.5%. *Có khả năng là thật.*
- **Các repos OpenInterpreter, MetaGPT, LangChain.** Có thật nhưng **nằm ngoài phạm vi (out of scope) của bản tóm tắt (brief)** — xem phụ lục.
- **pandera, whylogs, deepchecks, Soda Core (URL của Soda Core không chắc chắn).** Các thư viện DQ (Chất lượng Dữ liệu) có thật; chỉ có Claude bao gồm chúng. Pandera và whylogs đặc biệt đáng tin cậy (credible); URL của Soda Core cần phải xác minh (warrants verification).
- **Zenlytic, DataChat (thương mại - commercial).** Các công ty có thật; Claude là nguồn duy nhất — hãy xác minh trạng thái sản phẩm hiện tại.

### Chỉ từ ChatGPT (G)

- **Profiling Relational Data Survey (Abedjan và cộng sự, VLDB Journal 2015).** *Gần như chắc chắn là thật (Almost certainly real):* khảo sát nền tảng (foundational survey) được trích dẫn rộng rãi. Việc chỉ có một AI phát hiện ra nó là một lỗ hổng nội dung (content gap) trong các báo cáo khác, không phải là một rủi ro về hallucination.
- **Tasks and Visualizations Used for Data Profiling (Ruddle và cộng sự, TVCG 2023).** *Có khả năng là thật:* số DOI cụ thể.
- **LLMs on tabular data survey (Fang và cộng sự, TMLR 2024).** *Có khả năng là thật.*
- **Bài báo DataPrep.EDA (Peng và cộng sự, SIGMOD 2021, arXiv:2104.00841).** *Có khả năng là thật:* khớp với thư viện open-source DataPrep.
- **Inconvo (github.com/inconvoai/inconvo, ~105 sao).** Chat-with-data ở cấp độ production (Production-grade) với RBAC. *Hợp lý nhưng ít người biết (Plausible but obscure)* — 105 sao gợi ý một dự án nhỏ; kiểu mẫu URL (URL pattern) khớp với một tổ chức có vẻ là thật. **Hãy xác minh xem URL có tồn tại không.**
- **Power BI Q&A, Looker Smart Lenses, Grist, Aible.** Những đề cập ngắn gọn trong phần "Những công cụ khác (Others)"; các sản phẩm có thật nhưng không có chi tiết được đưa ra.

### Chỉ từ Perplexity (P) — Các mục Pro Research

- **QUIS (Manatkar và cộng sự, EMNLP 2024, arXiv:2410.10270).** Pipeline zero-shot 2 giai đoạn QUGen + ISGen. *Có khả năng là thật và liên quan trực tiếp.*
- **Quality Assessment of Tabular Data using LLMs and Code Generation (Akella và cộng sự 2025, arXiv:2509.10572).** Việc tạo luật (rule generation) LLM được hỗ trợ bởi RAG. *Có khả năng là thật và liên quan mật thiết (highly relevant) đến lớp DQ.*
- **LLM-Based DS Agents: A Survey (Rahman và cộng sự 2025, arXiv:2510.04023).** Khảo sát vòng đời (Lifecycle survey) của 45 hệ thống; phát hiện ">90% thiếu trust/safety" là có thể hành động được một cách rộng rãi (widely actionable). *Có khả năng là thật.*
- **A Survey on LLM-based Agents for Statistics and Data Science (arXiv:2412.14222).** Hiệp hội Trung Quốc (Chinese consortium) năm 2024. *Có khả năng là thật.*
- **NL4DV (Narechania và cộng sự 2020, IEEE VIS) và NL4DV-LLM (Sah và cộng sự 2024, NLVIZ).** *Có khả năng là thật, dòng (lineage) bộ công cụ nổi tiếng.*
- **Data-centric AI: A Survey (Zha và cộng sự 2023, arXiv:2303.10158).** *Có khả năng là thật, được trích dẫn rộng rãi.*
- **Combo-Eval / Can LLMs Narrate Tabular Data? (Singh và cộng sự, Oracle, 2025, arXiv:2510.23854).** *Có khả năng là thật và rất liên quan cho việc đánh giá (evaluation).*
- **Why Do Open-Source LLMs Struggle with Data Analysis? (Zhu và cộng sự 2025, arXiv:2506.19794).** *Có khả năng là thật.*
- **klib, DataKitchen TestGen, repo NL4DV, AutoEDA (Devang-C), pingcap/tiinsight (URL không chắc chắn).** Có thật ở các mức độ khác nhau (varying degrees). **URL pingcap/tiinsight được tự bản thân Perplexity Pro gắn cờ là không chắc chắn một cách rõ ràng (explicitly flagged uncertain)** — không được niêm yết công khai.

### Chỉ từ Perplexity (P) — Các mục báo cáo thông thường (hầu hết [không chắc chắn])

- **DataTales benchmark cho tường thuật dữ liệu (data narration).** *Có thể là thật (Possibly real) nhưng chưa được xác minh bởi nguồn.* Có thể là một ảo giác (hallucination) — hãy xác minh trên arXiv.
- **"Sketch: Extensible Interactive Data Analysis Using LLMs" với tư cách là một bài báo** (khác biệt so với repo Sketch). *Có thể là sự nhầm lẫn giữa paper-vs-repo;* hãy xác minh xem liệu có một bài báo chính thức nào tồn tại hay không.
- **Các placeholders chung chung (Generic placeholders)** ("Conversational data analysis with LLMs", "Automatic chart recommendation", "Automated EDA", "Automated DQ assessment surveys", "Continuous/live data profiling"). Đây là các lĩnh vực nghiên cứu (research areas), không phải các bài báo cụ thể — không phải các mục có thể hành động được (not actionable items).
- **smalltech/auto-eda, gventuri/pandas-profiling, DeepInsight-AI/DeepBI, The-Pocket/PocketFlow-Tutorial-Data-Profiler, exploratoryio/exploratory, tensorflow/data-validation, OpenRefine.** Tên các repo trải dài từ hợp lý-có-thật (plausible-real) (OpenRefine, tensorflow/data-validation đều nổi tiếng) cho đến đáng ngờ (questionable) (smalltech/auto-eda — hãy xác minh là có tồn tại). **Hãy coi những cái lạ lẫm như là các URL cần phải xác minh.**
- **YData Fabric / Data Catalog, Sigma Computing (thương mại).** Các công ty có thật.

### Chỉ từ Grok (X)

- **Khảo sát LLM/Agent-as-Data-Analyst (Tang và cộng sự 2025, arXiv:2509.23988).** *Có khả năng là thật, nhưng hãy xác minh — chỉ có Grok làm lộ diện nó và Grok xếp nó ở vị trí số 2 trong thứ tự nên đọc (reading order). Đây là ứng viên mạnh đáng đọc nếu được xác minh là đúng.*
- **An LLM-Based Approach for Insight Generation in Data Analysis (Pérez và cộng sự 2025, arXiv:2503.11664).** *Có khả năng là thật, tập trung vào các narrative findings.*
- **InsightLens (Weng và cộng sự 2024, arXiv:2404.01644).** Quản lý insight tương tác. *Có khả năng là thật.*
- **AdaVis (Zhang và cộng sự 2023, arXiv:2310.11742).** Đề xuất biểu đồ có thể giải thích (Explainable chart recommendation). *Có khả năng là thật.*

---

## 8. Thứ tự Khuyên Đọc (Recommended Reading Order)

Top 7 mục nên đọc trước tiên, được rút ra từ danh sách tổng hợp, đã được xếp hạng. Phần này tổng hợp (synthesizes) các thứ tự đọc từ cả bốn nguồn, với trọng số nghiêng về (weighted toward) các mục có độ tin cậy CAO.

1. **LIDA (Dibia 2023, arXiv:2303.02927)** — bài báo duy nhất mà cả bốn nguồn đều đưa vào thứ tự đọc của họ; là architectural blueprint (bản thiết kế kiến trúc) gần gũi nhất cho dự án. Kho repo microsoft/lida cung cấp cho bạn mã nguồn tham khảo cụ thể (concrete reference code).
2. **LLM-Based Data Science Agent: A Survey (Chen / Wang 2025, arXiv:2508.02744)** — Bản đồ tổng quan (landscape map) từ 3 nguồn; cung cấp vốn từ vựng khái niệm (conceptual vocabulary) để định vị dự án so với lĩnh vực nói chung.
3. **TiInsight / Towards Automated Cross-domain EDA via LLMs (Zhu và cộng sự 2024, arXiv:2412.07214)** — Hệ thống DB-native LLM EDA được xác nhận production nhiều nhất; kỹ thuật HDC có thể tái sử dụng trực tiếp. *Hãy xác minh mã arXiv ID với các mâu thuẫn ở phần §6 trước khi trích dẫn.*
4. **ydata-profiling (github.com/ydataai/ydata-profiling)** — baseline cổ điển được đồng thuận; việc đọc tài liệu hướng dẫn/mã nguồn sẽ giúp định nghĩa xem một "strong automated profile (hồ sơ tự động mạnh mẽ)" là bao gồm những gì trước khi thêm vào lớp LLM.
5. **InsightPilot (Ma và cộng sự 2023, EMNLP, arXiv:2304.00477)** — Tiền bối kiến trúc (architectural ancestor) gần gũi nhất cho đường ống "intent → IQuery → insight" (ý định → Truy vấn → insight) — nên đọc cùng với LIDA để thấy được toàn bộ không gian thiết kế EDA-agent.
6. **Quality Assessment of Tabular Data using LLMs and Code Generation (Akella và cộng sự 2025, arXiv:2509.10572)** *chỉ có từ nguồn P, nhưng* lại là bài báo trực tiếp nhất về pattern "RAG-aided LLM rule generation + critic-agent" (Tạo luật LLM được hỗ trợ bởi RAG + tác nhân phản biện), đây là biện pháp giảm thiểu được biết đến nhiều nhất cho rủi ro hallucination mà mọi nguồn đều gắn cờ.
7. **PandasAI (github.com/sinaptik-ai/pandas-ai)** — LLM data agent hiện đại (state-of-the-art) được đồng thuận. Hãy đọc cả tài liệu hướng dẫn và các vấn đề đang mở (open issues) để thấu hiểu (internalize) được các failure modes (chế độ lỗi - ảo giác về số liệu thống kê, bảo mật khi thực thi code) mà dự án phải tránh.

---

## Phụ lục (Appendix) — Các Mục Bị Loại trừ vì Nằm ngoài Bản tóm tắt (Outside the Brief)

Các mục sau đây đã được đề cập trong các báo cáo nguồn nhưng nằm ngoài phạm vi của bản tóm tắt (brief's scope) ban đầu (automated EDA / data profiling / LLM-data-agents / phát hiện data-quality / auto-visualization / công cụ EDA thương mại). Chúng được ghi nhận ở đây để đảm bảo tính đầy đủ (completeness):

- **OpenInterpreter** [C] — NL đa mục đích (general-purpose) → thực thi mã code cục bộ, không chuyên biệt cho dữ liệu (not data-specific).
- **LangChain** [C] — framework chung cho ứng dụng LLM; bản tóm tắt này nói về các công cụ dữ liệu, chứ không phải các lựa chọn framework.
- **Các placeholders chung chung về lĩnh vực nghiên cứu từ bản Perplexity-regular** ("Conversational data analysis with LLMs", "Automatic chart recommendation from tables", "Automated EDA", "Automated DQ assessment surveys", "Continuous/live data profiling", "Data wrangling with pandas and NL") — đây là các chủ đề (topics), không phải là các mục có thể trích dẫn được (citable items).
- **Sự đề cập đến Athenic của Grok** ("Những cái khác như Athenic (tập trung vào truy vấn) đang tồn tại trong không gian này") — được giữ lại trong phần §4 vì nó đã được chứng thực (corroborated) ở nơi khác, nhưng việc Grok đề cập thì lại quá ngắn gọn để được tính là có giá trị thực chất (substantive).
