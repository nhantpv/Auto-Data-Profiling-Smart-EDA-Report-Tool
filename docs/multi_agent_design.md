# Thiết kế Multi-Agent L4 — Phân tích & Đề xuất

---

## 1. Hệ thống Multi-Agent HIỆN TẠI (As-Is)

### Luồng hoạt động

```
                    ┌──────────────────────────────────┐
                    │  L3 Output (findings, schema,    │
                    │  verdict, cross_table_analysis)   │
                    └───────────────┬──────────────────┘
                                    ↓
                    ┌──────────────────────────────────┐
                    │  DISPATCHER (Python thuần)       │
                    │  Gom anomalies → top 5 clusters  │
                    │  (theo issue_type)                │
                    └───────────────┬──────────────────┘
                                    ↓ fan-out
             ┌──────────┬──────────┼──────────┬──────────┐
             ↓          ↓          ↓          ↓          ↓
       ┌──────────┐ ┌──────────┐ ┌──────────┐      (max 5)
       │ ANALYST  │ │ ANALYST  │ │ ANALYST  │
       │ Agent #1 │ │ Agent #2 │ │ Agent #3 │ ...
       │(gpt-4o-  │ │(gpt-4o-  │ │(gpt-4o-  │
       │  mini)   │ │  mini)   │ │  mini)   │
       └────┬─────┘ └────┬─────┘ └────┬─────┘
            │            │            │
            ↓ collect    ↓            ↓
       ┌──────────────────────────────────────┐
       │  EDITOR Agent (gpt-4o)               │
       │  Nhận: verdict + analyst Markdown[]  │
       │  Trả: JSON {executive_summary,       │
       │        verdict_explanation,           │
       │        cross_table_evaluation,        │
       │        priority_ranking}              │
       └───────────────┬──────────────────────┘
                       ↓
       ┌──────────────────────────────────────┐
       │  GUARDRAIL (Python thuần)            │
       │  Check: số liệu có match evidence?  │
       │  Nếu FAIL → fallback deterministic  │
       └───────────────┬──────────────────────┘
                       ↓
       ┌──────────────────────────────────────┐
       │  HTML Merger → Final Report          │
       └──────────────────────────────────────┘
```

### Số lần gọi LLM hiện tại

| Agent | Model | Số call tối đa | Ghi chú |
|---|---|---|---|
| Analyst ×5 | gpt-4o-mini | 5 × 3 retry = **15 calls** | Song song (`asyncio.gather`) |
| Editor ×1 | gpt-4o | 1 × 3 retry = **3 calls** | Tuần tự sau khi Analyst xong |
| **Tổng tối đa** | | **18 calls** | Worst case (tất cả retry 3 lần) |
| **Tổng happy path** | | **6 calls** | 5 Analyst + 1 Editor, không retry |

### Vấn đề hiện tại

| # | Vấn đề | Hậu quả |
|---|---|---|
| 1 | Analyst gom theo `issue_type` → mỗi Analyst viết về 1 loại lỗi (VD: MISSINGNESS) | Output là danh sách lỗi rời rạc, KHÔNG theo cấu trúc Table→Column |
| 2 | 5 Analyst chạy **độc lập**, không biết nhau | Agent #1 viết "Missing 40% ở email" nhưng Agent #3 viết "Orphan Keys ở customer_id" → không ai tổng hợp BẢNG `Customers` có bao nhiêu vấn đề |
| 3 | Editor chỉ nhận Markdown text → không có column stats | Editor viết executive summary chung chung, không có Feature Usability Summary |
| 4 | Không có cơ chế đảm bảo **thống nhất văn phong** | Analyst #1 có thể viết tiếng Anh formal, Analyst #3 viết casual |

---

## 2. Đề xuất Thiết kế Mới — 2 Phương án

### Phương án A: Giữ kiến trúc cũ, đổi chiến lược gom (Sửa ít nhất)

**Ý tưởng:** Giữ nguyên luồng Dispatcher → Analyst[] → Editor, nhưng đổi đơn vị gom từ `issue_type` sang `table`.

```
DISPATCHER (gom theo TABLE thay vì issue_type)
    ↓ fan-out theo bảng
┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│  ANALYST    │  │  ANALYST    │  │  ANALYST    │
│ Table:      │  │ Table:      │  │ Table:      │
│ "Orders"    │  │ "Customers" │  │ "Products"  │
│ (tất cả     │  │ (tất cả     │  │ (tất cả     │
│ issues +    │  │ issues +    │  │ issues +    │
│ col stats)  │  │ col stats)  │  │ col stats)  │
└──────┬──────┘  └──────┬──────┘  └──────┬──────┘
       ↓                ↓                ↓
                  EDITOR (tổng hợp)
```

**Số call LLM:**

| Agent | Số call | Ghi chú |
|---|---|---|
| Analyst × (số bảng, max 5) | 1-5 calls | Song song, mỗi bảng 1 call |
| Editor × 1 | 1 call | Nhận tất cả analyst outputs |
| **Tổng happy path** | **2-6 calls** | Ít hơn hoặc bằng hiện tại |
| **Tổng worst case (retry)** | **18 calls** | Giống hiện tại |

**Ưu điểm:**
- Sửa ít code nhất (chỉ đổi logic gom trong `dispatcher.py`)
- Mỗi Analyst đã tự nhiên viết theo cấu trúc Table→Column
- Editor nhận output đã gom theo bảng → dễ tổng hợp Feature Usability

**Nhược điểm:**
- 5 Analyst vẫn độc lập → vẫn có thể không thống nhất văn phong
- Nếu 1 bảng quá nhiều lỗi → 1 Analyst call quá nặng token

---

### Phương án B: 2-pass — Analyst theo bảng + Editor tổng hợp toàn bộ (Sửa nhiều hơn, chất lượng cao hơn)

**Ý tưởng:** Bỏ fan-out nhiều Analyst. Thay bằng 1 call LLM lớn chứa TẤT CẢ evidence, trả về Phần 2 (Table-by-Table). Sau đó Editor tổng hợp Phần 1 + 3.

```
┌──────────────────────────────────────────────────────┐
│  Pass 1: TABLE ANALYST (1 call LLM duy nhất)         │
│  Model: gpt-4o                                       │
│  Input: ALL issues + ALL column stats + ALL schema   │
│  Output: Structured JSON — Phần 2 hoàn chỉnh         │
│          {tables: [{name, overview, columns: [        │
│            {name, severity, problem, ml_consequence,  │
│             suggested_action, evidence_ref}]}]}       │
└───────────────────────┬──────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│  Pass 2: EDITOR (1 call LLM duy nhất)                │
│  Model: gpt-4o                                       │
│  Input: Pass 1 output + verdict + cross_table        │
│  Output: JSON — Phần 1 (Dashboard) + Phần 3 (Cross)  │
│          {executive_summary,                          │
│           feature_usability_summary: [{col, status}], │
│           fix_priority: [...],                        │
│           cross_table_evaluation,                     │
│           schema_evaluation}                          │
└───────────────────────┬──────────────────────────────┘
                        ↓
┌──────────────────────────────────────────────────────┐
│  GUARDRAIL (Python thuần)                             │
│  1. Check evidence_ref → finding_id                   │
│  2. Check số liệu match                              │
│  3. Nếu FAIL → fallback deterministic                 │
└──────────────────────────────────────────────────────┘
```

**Số call LLM:**

| Agent | Model | Số call | Ghi chú |
|---|---|---|---|
| Table Analyst | gpt-4o | 1 × 3 retry = max 3 | 1 call chứa mọi thứ |
| Editor | gpt-4o | 1 × 3 retry = max 3 | Nhận structured output từ Pass 1 |
| **Tổng happy path** | | **2 calls** | Ít nhất có thể |
| **Tổng worst case** | | **6 calls** | Rất ít so với 18 hiện tại |

**Ưu điểm:**
- **Thống nhất tuyệt đối:** 1 LLM call = 1 văn phong, 1 giọng điệu, 1 cấu trúc
- **LLM thấy toàn cảnh:** Khi viết về `Orders.customer_id`, nó biết `Customers` có lỗi gì → nhận xét liên bảng tự nhiên
- **Ít call hơn = rẻ hơn + nhanh hơn + ít lỗi hơn**
- Editor nhận structured JSON (không phải Markdown text) → dễ tổng hợp chính xác

**Nhược điểm:**
- Nếu dataset có quá nhiều bảng/cột → 1 call LLM có thể vượt context window
- Cần viết lại nhiều code hơn (bỏ fan-out pattern, đổi output model)
- Mất khả năng song song (nhưng 2 call tuần tự vẫn nhanh hơn 6 call song song)

---

## 3. So sánh 2 phương án

| Tiêu chí | Phương án A (Giữ fan-out) | Phương án B (2-pass) |
|---|---|---|
| Số call LLM (happy) | 2-6 | **2** |
| Số call LLM (worst) | 18 | **6** |
| Thống nhất văn phong | ⚠️ Trung bình | ✅ Tuyệt đối |
| LLM thấy toàn cảnh | ❌ Mỗi Analyst chỉ thấy 1 bảng | ✅ Thấy tất cả |
| Xử lý dataset lớn (10+ bảng) | ✅ Tốt (fan-out) | ⚠️ Có thể vượt context |
| Lượng code cần sửa | Ít (dispatcher + prompts) | Nhiều (restructure flow) |
| Giữ được Deterministic Fallback | ✅ Tái sử dụng dễ | ✅ Cần viết lại fallback |

---

## 4. Cơ chế đảm bảo Thống nhất (cho cả 2 phương án)

Dù chọn phương án nào, cần 3 cơ chế:

### 4a. System Prompt Template cố định
Tất cả Analyst dùng **cùng 1 System Prompt** với format yêu cầu cụ thể:
```
Output Format cho MỖI cột bị lỗi:
1. [SEVERITY] Vấn đề: (mô tả + số liệu chính xác)
2. ML Consequence: (theo nhóm: Tuyến tính / Tree / NN / Clustering)
3. Gợi ý tham khảo: (advisory tone)
```

### 4b. Structured JSON Output (không phải Markdown tự do)
Hiện tại Analyst trả **Markdown tự do** → mỗi agent viết khác nhau.
Đổi thành trả **JSON schema cố định** → Python render ra Markdown/HTML → **100% đồng nhất format.**

### 4c. Guardrail Post-validation (đã thiết kế)
Python kiểm tra `evidence_ref` → reject LLM hallucination.

---

## 5. Đề xuất của tôi

> [!IMPORTANT]
> **Tôi đề xuất Phương án A (Giữ fan-out, đổi gom theo Table)** với lý do:
> 1. Sửa ít code nhất → giảm rủi ro phá vỡ hệ thống đang chạy
> 2. Dataset thực tế có thể có 5-10 bảng → fan-out vẫn phù hợp
> 3. Bổ sung **Structured JSON Output** (4b) là đủ để giải quyết vấn đề thống nhất
> 4. Phương án B có thể triển khai sau nếu cần upgrade
>
> **Bạn nghĩ sao? Chọn A hay B?**
