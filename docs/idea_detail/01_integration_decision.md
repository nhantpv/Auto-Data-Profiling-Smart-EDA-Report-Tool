# Quyết Định Kiến Trúc (ADR): Hợp Nhất Các Ý Tưởng M1/M2/M3

**Ngày quyết định:** 2026-05-29  
**Trạng thái:** Đã chốt  
**Ngữ cảnh:** Bản đề xuất gốc tại [`integration_proposal.md`](./integration_proposal.md) đưa ra 3 ý tưởng hợp nhất (C1, C2, C3) giữa các tài liệu M1/M2/M3 và bản thiết kế hệ thống (`system_architecture_design.md`). Tài liệu này ghi lại các quyết định chính thức sau quá trình đánh giá chi tiết.

---

## 1. QUYẾT ĐỊNH 1: Chấp nhận C1 — Làm giàu L3 Schema

**Quyết định:** ✅ Tích hợp C1 vào Phase 1 (Task 2 & 3).

**C1 là gì?** Mở rộng các Pydantic Models (File JSON Layer 3) bằng cách bổ sung thêm các trường thông tin theo chuẩn quốc tế:
- `dq_dimensions` — Gắn nhãn loại lỗi theo chuẩn DAMA (6 chiều: Completeness, Validity, Consistency, Timeliness, Uniqueness, Accuracy).
- `ml_impact` — Đánh dấu lỗi này có ảnh hưởng đến việc huấn luyện AI không (VD: `training_blocker`, `leakage_risk`).
- `compound_severity` — Mức độ nghiêm trọng tổng hợp khi 1 cột bị dính nhiều lỗi cùng lúc.
- `confidence` — Độ tin cậy của phát hiện.

**Lý do chấp nhận:**
- Chi phí thấp: Chỉ cần thêm vài dòng định nghĩa biến vào Pydantic Model.
- Giá trị cao: Báo cáo đầu ra sẽ chuyên nghiệp hơn rất nhiều, đạt chuẩn quốc tế ngành Data Quality.
- Không phá vỡ kiến trúc cốt lõi đã đề ra.

**Lưu ý:** Các trường `compound_severity` và `ml_impact` sẽ được điền bởi các module thuộc C2 (xem Quyết Định 2). Đây là lý do C1 và C2 phải đi cùng nhau — nếu chỉ làm C1 mà bỏ C2, các trường này sẽ luôn rỗng.

---

## 2. QUYẾT ĐỊNH 2: Chấp nhận C2 — Layer 2.5 Severity Stack (Toàn bộ 4 Module)

**Quyết định:** ✅ Chấp nhận toàn bộ 4 module.

### Tại sao ban đầu lo ngại C2 bị overengineer?

Đề xuất gốc mô tả C2 bao gồm việc "tải 72 bộ dữ liệu OpenML, chạy huấn luyện hàng loạt mô hình ML". Điều này nghe rất nặng nề. Tuy nhiên, sau khi phân tích kỹ, C2 thực chất gồm **4 module hoàn toàn tách rời nhau**, và phần "nặng" chỉ là 1 bước tùy chọn (optional), không bắt buộc:

### Chi tiết từng Module

#### Module (d): CompoundEscalator — "Cột bị nhiều lỗi → Nâng mức độ"
- **Bản chất:** Nếu 1 cột dính 3 lỗi nhẹ cùng lúc (thiếu dữ liệu + outlier + phân phối lệch), hệ thống tự động nâng mức nghiêm trọng lên. Ví dụ: Mỗi lỗi riêng lẻ là MEDIUM, nhưng 3 cái chồng lên nhau → nâng lên HIGH.
- **Logic:** `compound_severity = max(các lỗi riêng lẻ) + 1 bậc cho mỗi lỗi thêm`. Giới hạn tối đa là CRITICAL.
- **Nỗ lực:** ~15-20 dòng Python. Không cần thêm dependency.
- **Overengineer?** Không. Đây là một phép tính đơn giản.
- **Giá trị:** Cao. Giúp LLM nhận ra và cảnh báo những cột "bệnh nặng tổng hợp" thay vì liệt kê từng lỗi rời rạc.

#### Module (c): Aggregator — "Ra phán quyết: READY / WARN / NOT_READY"
- **Bản chất:** Sau khi phân tích xong tất cả các cột, hệ thống đưa ra 1 câu kết luận cho toàn bộ bộ dữ liệu: "Dữ liệu này dùng được chưa?". Đây là câu hỏi tự nhiên nhất mà mọi User đều muốn được trả lời.
- **Logic v0.1 (Rule đơn giản):** Đếm số lỗi HIGH/CRITICAL. Ví dụ: Có ≥ 1 lỗi CRITICAL → NOT_READY; Chỉ có MEDIUM → WARN; Không có lỗi đáng kể → READY.
- **Nỗ lực:** ~30-50 dòng Python.
- **Overengineer?** Không. Logic rule-based cực kỳ đơn giản.
- **Giá trị:** Rất cao. Thay vì User phải tự đọc 20 lỗi rồi tự kết luận, tool đưa ra verdict rõ ràng.

#### Module (a): MCAR/MAR/MNAR Detector — "Tại sao dữ liệu bị thiếu?"
- **Bản chất:** Khi phát hiện cột bị thiếu dữ liệu, module này phân tích lý do:
  - **MCAR (Missing Completely At Random):** Thiếu ngẫu nhiên, không liên quan gì. VD: Sensor hỏng ngẫu nhiên.
  - **MAR (Missing At Random):** Thiếu có hệ thống, liên quan đến cột khác. VD: Người > 50 tuổi thường bỏ trống cột Email.
  - **MNAR (Missing Not At Random):** Thiếu vì chính giá trị đó. VD: Người thu nhập cao từ chối khai báo Lương.
- **Logic:** Sử dụng Little's MCAR test (~20 dòng, `scipy.stats.chi2`), Logistic Regression cho MAR (~20 dòng), và heuristic cho MNAR (~10 dòng).
- **Nỗ lực:** ~50-60 dòng Python. Dependency `statsmodels` đã có sẵn (kéo theo bởi `ydata-profiling`).
- **Overengineer?** Không. Nỗ lực thấp, có thể wrap trong try/except để xử lý edge case (dataset nhỏ, toàn cột Categorical).
- **Giá trị:** Cao. Giúp LLM viết được nhận xét sâu hơn rất nhiều. Thay vì chỉ nói *"Cột Lương thiếu 20%"*, báo cáo có thể nói *"Cột Lương thiếu 20%, và đây là thiếu có hệ thống (MAR) — những người có Tuổi > 50 có xu hướng bỏ trống cột này"*.

#### Module (b): Calibrator — "Bảng phân loại mức độ nghiêm trọng"
- **Bản chất:** Thay vì viết luật cứng rải rác trong code (`if missing > 20%: severity = HIGH`), ta tập trung toàn bộ ngưỡng vào 1 file JSON duy nhất (`calibrator_table.json`). Code Python chỉ việc tra bảng.
- **Tại sao đây KHÔNG phải overengineer?** Cần phân biệt rõ 2 phần:
  1. **Phần Runtime (nhẹ, ship ngay):** Code Python mở file `calibrator_table.json`, tra bảng theo loại lỗi + tỷ lệ → ra severity. Cực kỳ nhẹ, chỉ ~20 dòng code.
  2. **Phần Benchmark (nặng, TÙY CHỌN, làm sau):** Một script offline chạy 72 dataset OpenML để sinh ra file `calibrator_table.json` với các ngưỡng đã được chứng minh khoa học. Phần này chỉ cần khi muốn viết Paper hoặc muốn nâng cấp chất lượng.
- **Cơ chế Fallback (Điểm then chốt):** Cấu trúc file JSON là GIỐNG NHAU dù được tạo bằng tay hay bằng benchmark:
  ```json
  // Bảng đặt tay (v0.1 - ship ngay):
  { "MISSING_VALUES": { "0-5%": "INFO", "5-20%": "WARN", "20%+": "HIGH" } }

  // Bảng từ benchmark (v0.2 - nâng cấp sau):
  { "MISSING_VALUES": { "0-3.2%": "INFO", "3.2-18.7%": "WARN", "18.7%+": "HIGH" } }
  ```
  Code Python đọc bảng **không cần thay đổi bất kỳ dòng nào** khi chuyển từ bảng đặt tay sang bảng benchmark. Chỉ thay file JSON config.
- **Nỗ lực v0.1:** ~20 dòng code tra bảng + 1 file JSON đặt tay. Không cần ML, không cần download dataset.
- **Overengineer?** Không. Đây là thiết kế mở rộng thông minh (Extensible Design), không phải overengineer.
- **Giá trị:** Tập trung hóa toàn bộ ngưỡng vào 1 nơi duy nhất, dễ bảo trì và nâng cấp.

### Tóm tắt Quyết Định C2

| Module | Nỗ lực | Overengineer? | Giá trị cho User |
|:--|:--|:--|:--|
| (d) CompoundEscalator | ~15 dòng | Không | Cao |
| (c) Aggregator (Verdict) | ~30-50 dòng | Không | Rất cao |
| (a) MCAR/MAR/MNAR | ~50-60 dòng | Không | Cao |
| (b) Calibrator (tra bảng) | ~20 dòng + 1 JSON | Không | Trung bình (nhưng mở đường upgrade) |

**Tổng nỗ lực Runtime:** ~120-150 dòng Python. Hoàn toàn không overengineer.

**Phần Benchmark OpenML (offline):** Hoãn. Sẽ làm khi cần viết Paper hoặc muốn nâng cấp chất lượng ngưỡng. Kiến trúc đã sẵn sàng tiếp nhận mà không cần refactor.

---

## 3. QUYẾT ĐỊNH 3: Chấp nhận C3 — Guardrail chống AI bịa số liệu

**Quyết định:** ✅ Tích hợp C3 vào Phase LLM Reporting — sử dụng cơ chế **Allowed-Set + Tolerance + Column-Name Check**.

### C3 là gì?

Xây dựng một "Cảnh vệ" (Guardrail) bằng Python thuần túy đứng giữa LLM và File JSON, để chặn đứng tình trạng AI bịa số liệu (Hallucination).

### Cơ chế hoạt động: Allowed-Set + Tolerance

Dựa trên thiết kế gốc từ M3_SPEC, đã được kiểm chứng qua eval suite 200+ test case. Cơ chế này **không phụ thuộc vào sự tuân thủ của LLM** — nó chủ động quét và đối chiếu mọi con số.

**Cách hoạt động (3 bước):**

**Bước 1 — Xây dựng Allowed-Set (Tập hợp các số hợp lệ):**
Trước khi kiểm tra, code Python đọc file JSON và thu thập TẤT CẢ các con số có trong đó thành một danh sách "Số được phép" (Allowed-Set). Ví dụ từ JSON:
- `n_duplicates = 15` → Allowed: `15`
- `p_missing = 0.25` → Allowed: `0.25`
- `mean = 29.69` → Allowed: `29.69`
- Ngoài ra, thêm **Whitelist cố định:** `{0, 1, 2, 3, 10, 100, 1000}` — đây là các số đếm thông dụng mà LLM hay dùng trong câu văn (VD: "có 3 vấn đề chính").
- Year pass-through: Số có format `\d{4}` khớp với năm trong `created_at` của JSON → cho phép.

**Bước 2 — Regex quét MỌI số trong văn bản LLM:**
Sau khi LLM sinh ra đoạn văn, code Python dùng Regex quét toàn bộ các con số (integer, decimal, phần trăm, scientific notation). Mỗi số tìm được sẽ được đối chiếu với Allowed-Set.

**Quy tắc đối chiếu (Tolerance):**
- Số nguyên: Khớp chính xác (`15` phải đúng `15`).
- Số thập phân: Cho phép sai số ±0.0001 (`29.69` ≈ `29.6900`).
- Số lớn (|giá trị| > 1): Cho phép sai số tương đối ±0.1% (`29.69` → `30` khớp vì sai 1%, vượt ngưỡng → vẫn bắt. Nhưng `29.69` → `29.7` chỉ sai 0.03% → cho phép).
- Phần trăm: `25%` tự động quy đổi thành `0.25` trước khi đối chiếu.

**Bước 3 — Xử lý vi phạm:**
- Nếu LLM sinh ra số `999` mà Allowed-Set không hề có số nào gần `999` → **Hallucination!**
- Python gọi lại API bắt LLM sửa. Tối đa 3 lần retry.
- Nếu vẫn sai → Thay bằng `<SỐ LIỆU CHƯA XÁC MINH>`.

**Ví dụ minh họa:**

LLM viết: *"Dữ liệu có 15 dòng trùng lặp, tỷ lệ thiếu khoảng 25%. Tôi thấy có 3 vấn đề chính cần lưu ý ở năm 2026."*

| Số tìm được | Đối chiếu | Kết quả |
|:--|:--|:--|
| `15` | JSON có `n_duplicates = 15` | ✅ Khớp |
| `25` | JSON có `p_missing = 0.25`, quy đổi 0.25 × 100 = 25 | ✅ Khớp |
| `3` | Nằm trong Whitelist `{0, 1, 2, 3, ...}` | ✅ Cho phép |
| `2026` | Khớp year trong `created_at` | ✅ Cho phép |

→ Tất cả đều hợp lệ. Guardrail cho qua. **Không có bắt nhầm (False Positive).**

### Bổ sung: Column-Name Check (Chống bịa tên cột)

Ngoài việc kiểm tra số, Guardrail cũng quét toàn bộ văn bản tìm **tên cột** mà LLM đề cập. Nếu LLM nhắc đến một cột không hề tồn tại trong JSON (VD: LLM viết "cột Revenue" nhưng JSON chỉ có "Age", "Salary") → đánh dấu Hallucination.

Cơ chế này đơn giản (so sánh chuỗi ký tự) và không gây bắt nhầm.

### Bổ sung: Citation `[tên_biến]` (Bonus, không bắt buộc)

Trong Prompt, ta **khuyến khích** (không ép buộc) LLM gắn tên biến JSON trong ngoặc vuông bên cạnh số liệu (VD: *"Thiếu 25% [p_missing]"*). Đây là bonus giúp tăng tính **truy vết (Audit Trail)** cho báo cáo — người đọc có thể click vào trích dẫn để tra ngược nguồn dữ liệu. Tuy nhiên, **Guardrail không dựa vào Citation làm cơ chế bảo vệ chính** — nó dùng Allowed-Set ở trên.

### Guardrail áp vào đâu trong hệ thống Multi-Agent?

Guardrail là một **hàm Python** (không phải một Agent), được đặt ngay sau đầu ra của MỖI Agent:

- **Sau mỗi Mini-Agent (gpt-4o-mini):** Kiểm tra đoạn phân tích của từng cột. Nếu Mini-Agent nào bịa số → chỉ gọi lại API rẻ của con đó, không ảnh hưởng các Agent khác.
- **Sau Master Agent (gpt-4o):** Kiểm tra lần cuối bài tổng hợp trước khi xuất ra báo cáo. Đảm bảo Master không "phóng đại" khi tổng hợp.

Kiến trúc Multi-Agent hiện tại **không bị thay đổi**. Guardrail chỉ là lớp bảo vệ được chèn thêm vào sau mỗi lần gọi LLM.

### Lưu ý quan trọng

- **Không phải "1 lần gọi API duy nhất":** Hệ thống Multi-Agent có nhiều lần gọi (N Mini + 1 Master + retry nếu có). Guardrail không giảm số lần gọi — nó chỉ đảm bảo chất lượng đầu ra sau mỗi lần gọi.
- **Không phải "chính xác 100% tuyệt đối":** Guardrail phủ được **mọi con số** và **tên cột**. Tuy nhiên, những nhận xét văn xuôi không chứa số (VD: LLM bịa *"Dữ liệu có xu hướng tăng mạnh"* trong khi thực tế không hề), hoặc claim dựa trên nhìn ảnh/chart, thì Guardrail không bắt được. Phát biểu chính xác: *"Phủ hallucination cho mọi số liệu và tên cột; kill criterion nếu hallucination rate > 2% trên eval suite 50-finding"*.

---

## TỔNG KẾT

| Ý tưởng | Quyết định | Tóm tắt lý do |
|:--|:--|:--|
| **C1** (Làm giàu L3) | ✅ Chấp nhận | Chi phí thấp, giá trị cao, đạt chuẩn DAMA |
| **C2** (Severity Stack) | ✅ Chấp nhận toàn bộ 4 module | Không overengineer (~150 dòng runtime). Phần benchmark nặng là tùy chọn, có cơ chế fallback về bảng đặt tay |
| **C3** (Guardrail) | ✅ Chấp nhận (Allowed-Set + Tolerance + Column-Name Check) | Quét chủ động mọi số và tên cột bằng Python thuần, không phụ thuộc sự tuân thủ của LLM, không phá kiến trúc Multi-Agent |

