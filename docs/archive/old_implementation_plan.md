# Implementation Plan — Advanced Auto-EDA Architecture

## Mục tiêu dự án
Xây dựng công cụ **Auto Data-Profiling & Smart EDA Report Tool**: Kết nối DB/CSV, tự động tính chỉ số thống kê, phát hiện lỗi chất lượng dữ liệu (outliers, missing values) và dùng LLM đóng vai Senior Data Scientist để xuất báo cáo nhận xét chi tiết kèm biểu đồ trực quan.

## Nguyên tắc
- **Đứng trên vai người khổng lồ:** Những gì đã tốt, không làm lại. Dùng thẳng code/thư viện của họ.
- **Phân biệt rõ 2 loại kế thừa:**
  - **Integrate:** Cài thư viện làm dependency, gọi API.
  - **Inspire:** Học kiến trúc/thiết kế, tự viết code phù hợp.
- **Mỗi Layer phải giải thích:** Mục đích → Cơ chế → Kế thừa từ đâu → Bài học tránh lỗi.

## Dự án tham chiếu

| Dự án | Vai trò | Cách kế thừa | Phủ Layer nào |
|---|---|---|---|
| **ydata-profiling** | Engine tính toán thống kê + phát hiện DQ cơ bản | **Integrate** (pip install, gọi API lấy JSON) | 2, 4, 6 |
| **Great Expectations** | Validation nghiệp vụ nâng cao (business rules, constraints) | **Integrate** (pip install, dùng Expectations API) | 3 |
| **LIDA (Microsoft)** | Kiến trúc pipeline LLM sinh biểu đồ + tường thuật | **Inspire** (học pipeline 4 bước, tự viết) | 10 |
| **PandasAI** (lướt nhanh Issues) | Học từ lỗi sai: hallucination, security | **Bài học phản diện** | 6, 8 |

---

## Phase 0: Nghiên cứu Trực tiếp (Research Sprint) — `[ĐANG THỰC HIỆN]`

> Phase này phải hoàn thành TRƯỚC khi viết kiến trúc. Mục tiêu: thu thập kiến thức thực tế từ source code/docs.

### 0.1 — ydata-profiling
- [ ] Đọc README, docs chính thức.
- [ ] Xem output mẫu (HTML report / JSON).
- [ ] Trả lời: Tính những thống kê gì? Output format? Có API lấy JSON/Dict không? Có custom rules không?

### 0.2 — Great Expectations
- [ ] Đọc README, docs về Expectations API.
- [ ] Trả lời: Mô hình "Expectation" hoạt động thế nào? Tự động sinh rules được không? Output validation dạng gì?

### 0.3 — LIDA (Microsoft)
- [ ] Đọc README, cấu trúc thư mục, luồng dữ liệu pipeline.
- [ ] Trả lời: Summarizer nhận/trả gì? Dữ liệu truyền giữa module dạng nào? Có grounding không?

### 0.4 — PandasAI (lướt nhanh)
- [ ] Đọc lướt GitHub Issues (top issues về hallucination, security).
- [ ] Ghi lại các failure patterns cần tránh.

### 0.5 — Tổng hợp
- [ ] Ghi bài học rút ra vào file scratch.
- [ ] Xác nhận Integrate/Inspire cho từng Layer.
- [ ] Cập nhật plan nếu cần.

---

## Phase 1: Viết Kiến trúc Nhóm 1 & 2 (Đầu vào & Chất lượng Dữ liệu)

- [ ] Layer 1: Business Understanding (Inspire từ TiInsight HDC)
- [ ] Layer 2: Ingestion & Schema Inspection (Integrate ydata-profiling)
- [ ] Layer 3: Deep DQ Validation (Integrate Great Expectations)
- [ ] Layer 4: Initial Profiling & Missing Pattern (Integrate ydata-profiling)
- [ ] Layer 5: Cleaning & Standardization (Tự viết)
- [ ] **Checkpoint:** Dừng lại nhận phản hồi từ user.

## Phase 2: Viết Kiến trúc Nhóm 3 (Phân tích & Lọc Đặc trưng)

- [ ] Layer 6: Exploratory Statistical Analysis (Integrate ydata-profiling + Grounding)
- [ ] Layer 7: Feature Transformation (scikit-learn preprocessors)
- [ ] Layer 8: Feature Selection & Leakage Detection (Tự viết + bài học PandasAI)
- [ ] **Checkpoint:** Dừng lại nhận phản hồi từ user.

## Phase 3: Viết Kiến trúc Nhóm 4 (Xác thực & Báo cáo)

- [ ] Layer 9: Post-Transformation Validation (Tự viết)
- [ ] Layer 10: Reporting Engine (Inspire từ LIDA pipeline)
- [ ] **Checkpoint:** Dừng lại nhận phản hồi từ user.
- [ ] Rà soát toàn bộ file `advanced_auto_eda_architecture.md`.
