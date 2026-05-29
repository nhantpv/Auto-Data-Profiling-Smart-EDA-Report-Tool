# Kết quả Nghiên cứu Công nghệ — Scope: Data Assessment Tool

> File gốc đầy đủ (bao gồm cả phần ngoài scope): `docs/archive/phase0_research_findings.md`

---

## 1. fg-data-profiling — Profiling Engine chính

**Vai trò:** Core engine tính toán thống kê + phát hiện lỗi chất lượng dữ liệu.
**Cách dùng:** `pip install fg-data-profiling` → gọi API, lấy JSON output.

### Tính năng liên quan trực tiếp đến tool

| Tính năng | Phục vụ mục nào trong MVP |
|-----------|---------------------------|
| Type inference (tự phát hiện kiểu dữ liệu) | Profiling (#3) |
| Warnings/Alerts (missing, skewness, correlation, constant values) | Phát hiện điểm nhiễm (#4) |
| Univariate stats (mean, median, mode, distributions) | Profiling (#3) |
| Multivariate analysis (correlations, missing patterns, duplicates) | Phát hiện điểm nhiễm (#4) |
| Output JSON (`profile.to_json()`) | Xuất JSON (#8) |

### Giới hạn cần lưu ý
- Không hỗ trợ DBML → phần đối chiếu schema (#5, #6) phải tự viết.
- Không có ML-based anomaly detection → cần bổ sung (Isolation Forest, Z-score...).
- Không có LLM → phần nhận xét (#9) phải tự viết.

### Kết luận
**INTEGRATE** — dùng làm profiling backbone, bổ sung thêm: DBML parser + ML anomaly detection + LLM layer.

---

## 2. LIDA (Microsoft) — Inspiration cho LLM Reporting

**Vai trò:** Học kiến trúc pipeline sinh báo cáo bằng LLM.
**Cách dùng:** Học pattern, tự viết code phù hợp.

### Pattern hữu ích cho tool

```
lida.summarize(data)     →  Tương đương: fg-data-profiling output JSON
lida.goals(summary)      →  Tương đương: LLM đọc JSON, xác định vấn đề chính
lida.visualize(goal)     →  Tương đương: Sinh biểu đồ minh họa vấn đề
lida.explain(code)       →  Tương đương: LLM viết nhận xét bằng ngôn ngữ tự nhiên
```

### Bài học quan trọng
- **Grounding:** LLM chỉ đọc dữ liệu đã được tính toán trước (JSON), KHÔNG truy cập data thô → tránh hallucination.
- **Error rate < 3.5%:** Đạt được nhờ pre/post-processing logic tốt.
- **Giới hạn ≤ 10 cột:** Cần preprocessing (chọn cột quan trọng) trước khi đưa context cho LLM.

### Kết luận
**INSPIRE** — học pipeline pattern (Summary → Goals → Visualization → Explanation), tự implement.

---

## 3. Great Expectations — Tham khảo (không tích hợp trực tiếp)

**Vai trò ban đầu:** Dự kiến tích hợp cho DQ validation.
**Thực tế:** Giảm ưu tiên trong scope mới.

### Lý do giảm ưu tiên
- GE thiết kế cho **pipeline validation** (kiểm tra data liên tục trong production) — tool của chúng ta là **one-shot assessment** (đánh giá 1 lần).
- Integration giữa ydata-profiling và GE đã **bị ngừng hỗ trợ** ở phiên bản mới.
- Concept "Expectations" vẫn hữu ích về mặt tư duy (đặt kỳ vọng → so sánh thực tế) nhưng không cần cài GE dependency.

### Kết luận
**THAM KHẢO** — học concept "Expectations" để thiết kế metrics, nhưng tự viết code thay vì integrate.
