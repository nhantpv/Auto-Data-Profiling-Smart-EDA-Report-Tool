# Quyết Định Kiến Trúc (ADR): Hợp Nhất Các Ý Tưởng M1/M2/M3

**Ngày quyết định:** 2026-05-29
**Trạng thái:** Đã chốt (Chỉ đạo trực tiếp từ Product Owner)
**Ngữ cảnh:** Sau khi xem xét bản đề xuất hợp nhất tại [`integration_proposal.md`](./integration_proposal.md), chúng tôi đã tiến hành đánh giá chi tiết tính khả thi, giá trị mang lại và rủi ro Overengineer của 3 ý tưởng C1, C2, C3.

Dưới đây là các quyết định chính thức về việc định hình kiến trúc cho dự án `Auto-Data-Profiling-Smart-EDA-Report-Tool`.

---

## 1. QUYẾT ĐỊNH 1: Chấp nhận C1 (Làm giàu L3 Schema)
**Quyết định:** Tích hợp C1 vào Phase 1 (Task 2 & 3).
- **Mô tả:** Mở rộng các Pydantic Models (File JSON Layer 3) bằng cách bổ sung các trường thông tin chuẩn quốc tế: `dq_dimensions` (theo chuẩn DAMA), `ml_impact`, và `compound_severity`.
- **Lý do chấp nhận:** 
  - Đem lại giá trị cực cao: Giúp Báo cáo chẩn đoán (Diagnostic Report) trở nên chuyên nghiệp, có tính cấu trúc và đạt chuẩn quốc tế ngành Data Quality.
  - Chi phí cực thấp (Low effort): Chỉ cần thêm vài dòng định nghĩa biến vào Pydantic Model.
  - Không phá vỡ kiến trúc cốt lõi đã đề ra.

---

## 2. QUYẾT ĐỊNH 2: BÁC BỎ C2 (Severity Stack bằng Machine Learning)
**Quyết định:** Loại bỏ hoàn toàn C2 khỏi lộ trình phát triển Sản phẩm.
- **Mô tả ban đầu của C2:** Xây dựng một Layer 2.5 khổng lồ, tải 72 bộ OpenML datasets, chạy giả lập lỗi và huấn luyện các mô hình Machine Learning để tìm ra công thức chấm điểm độ nghiêm trọng (Severity).
- **Lý do bác bỏ (Chống Overengineer):**
  - **Sai mục đích:** Dự án của chúng ta là xây dựng một **Công cụ (Tool)** thực dụng cho người dùng cuối upload CSV lên để khám phá dữ liệu. Việc xây dựng cả một hệ thống Benchmark khổng lồ chỉ để phân loại lỗi "Nặng/Nhẹ" là hành động đi quá xa (Overengineered), phù hợp để làm Research Paper hơn là làm Product.
- **Giải pháp thay thế (Thực dụng):** 
  - Sử dụng **Kinh nghiệm chuyên gia (Heuristics / Hard Thresholds)**.
  - Trực tiếp dùng các rule đơn giản (Ví dụ: `if missing_rate > 20% then HIGH`). Nhanh, gọn, đáp ứng hoàn hảo 99% nhu cầu EDA của người dùng bình thường.

---

## 3. QUYẾT ĐỊNH 3: Chấp nhận & Nâng cấp C3 (Guardrail Chống Trảm Phong)
**Quyết định:** Tích hợp C3 vào Phase 4 (LLM Reporting) — với cơ chế **Trích dẫn bắt buộc**.
- **Mô tả:** Xây dựng một "Cảnh vệ" (Guardrail) bằng Python thuần túy đứng giữa LLM và File JSON để chặn đứng tình trạng AI bịa số liệu (Hallucination).
- **Nâng cấp cốt lõi (Citation-based Guardrail):** Thay vì dùng Regex bóc tách *toàn bộ* con số trong câu văn (dễ gây bắt nhầm số thứ tự, số năm), chúng ta áp dụng cơ chế:
  1. **Ép buộc trích dẫn (Prompt):** Bắt LLM mỗi khi nêu một số liệu thống kê thì PHẢI gắn tên biến JSON trong ngoặc vuông bên cạnh (VD: *Tỷ lệ lỗi là 5% [p_outliers]*).
  2. **Regex nhắm mục tiêu:** Cảnh vệ Python chỉ dùng Regex quét và bắt các con số đi kèm ngoặc vuông `[ ]`.
  3. **Đối chiếu chéo:** Python tự động tra tên biến trong ngoặc vuông vào file JSON gốc. Nếu con số của LLM sinh ra không khớp với JSON gốc → Đánh dấu Hallucination và ép LLM viết lại (Retry).
- **Lý do chấp nhận:**
  - Giải quyết triệt để "nỗi đau" lớn nhất của việc áp dụng LLM vào DataOps (Sự thiếu tin cậy về số liệu).
  - Kiến trúc vô cùng thanh lịch: Chỉ tốn 1 lần gọi API LLM duy nhất, sử dụng Python thuần (Deterministic) để kiểm tra, đảm bảo báo cáo đầu ra chính xác 100% về mặt số liệu thống kê.

---

## TỔNG KẾT HÀNH ĐỘNG (NEXT STEPS)
Với các quyết định trên, Blueprint kiến trúc hiện tại đã được chốt hạ và bảo vệ hoàn toàn khỏi rủi ro đi chệch hướng nghiên cứu học thuật.

- **Bỏ qua việc viết thêm 3 file COMBINED_SPEC**.
- **Tiến hành Code ngay lập tức cho Part 1 (Phase 1):** Bắt đầu xây dựng bộ khung thư mục và định nghĩa các hợp đồng dữ liệu (Pydantic Data Contracts) có bao gồm các field của C1.
