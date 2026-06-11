# Thảo luận đa chiều: LLM-Guided Cross-table Correlation

## Đề xuất của User

> Dùng LLM quyết định cặp cột nào có thể tính tương quan chéo chính xác, rồi mới tính. LLM Layer 4 đánh giá thêm độ tin cậy từng kết quả. Hiển thị đầy đủ nhưng kết luận LLM giúp user nắm bắt nhanh.

---

## 🧠 AI Engineer — Đánh giá tính khả thi kỹ thuật

### Đề xuất này khai thác đúng thế mạnh của LLM

Bài toán "cặp cột nào tính tương quan được" cần **domain knowledge** — điều mà rule-based KHÔNG THỂ có:

```text
Rule-based chỉ biết:
  ✓ Dtype (numeric, categorical)
  ✓ Cardinality (unique count)
  ✓ Tên cột (heuristic)

LLM hiểu thêm:
  ✓ "customer_age" là thuộc tính CỐ ĐỊNH của customer → không nên aggregate
  ✓ "order_amount" là metric BIẾN ĐỔI → nên aggregate (sum/mean) trước khi join
  ✓ "Tuổi ↔ Giới tính" cùng bảng parent → tính trên bảng parent, KHÔNG tính sau JOIN
  ✓ "Lương trung bình ↔ Khu vực" → cần GROUP BY trước → LLM đề xuất cách aggregate
```

### LLM KHÔNG tính toán — chỉ QUYẾT ĐỊNH

Đây là điểm thiết kế cốt lõi:

```text
┌──────────────────────────────────────────────────────┐
│  LLM Phase 1: QUYẾT ĐỊNH                            │
│  Input: Schema + 10 dòng mẫu + tên cột + dtype      │
│  Output: JSON — danh sách cặp cột cần tính          │
│          + cách aggregate cho từng cặp               │
└──────────────┬───────────────────────────────────────┘
               │ Structured JSON
               ▼
┌──────────────────────────────────────────────────────┐
│  DETERMINISTIC COMPUTE                                │
│  Aggregate theo chỉ dẫn LLM → phik/spearman          │
│  Kết quả: correlation values + sample sizes           │
└──────────────┬───────────────────────────────────────┘
               │ Numbers
               ▼
┌──────────────────────────────────────────────────────┐
│  LLM Phase 2: ĐÁNH GIÁ                              │
│  Input: Kết quả correlation + schema context          │
│  Output: Narrative — cặp nào đáng tin, cặp nào nghi  │
│          ngờ, insight nào actionable                   │
└──────────────────────────────────────────────────────┘
```

**Nguyên tắc "Deterministic-first"** vẫn được tôn trọng: LLM không tính correlation (phần có thể sai) — máy tính tính. LLM chỉ chọn cặp (phần cần domain knowledge) và nhận xét (phần cần ngữ cảnh).

### ✅ Kết luận AI Engineer: Khả thi và đúng hướng

LLM mạnh ở semantic reasoning, yếu ở tính toán. Thiết kế này khai thác đúng thế mạnh, tránh điểm yếu.

---

## 🏗️ Software Architect — Đánh giá kiến trúc

### Thiết kế này tạo ra kiến trúc 3 tầng rõ ràng

```text
TẦNG 1: Schema + Data → LLM → Correlation Plan (JSON)
TẦNG 2: Correlation Plan → Pandas/Phik → Results (Numbers)  
TẦNG 3: Results + Context → LLM → Report (Narrative)
```

Tầng 2 **hoàn toàn deterministic** — cùng input luôn cho cùng output. Tầng 1 và 3 dùng LLM nhưng output được structure hóa và validate.

### Prompt cho LLM Phase 1 — Thiết kế cụ thể

```text
SYSTEM PROMPT (LLM Phase 1):
Bạn là chuyên gia phân tích dữ liệu. Nhiệm vụ: xác định cặp cột nào từ 
2 bảng KHÁC NHAU có thể tính tương quan một cách chính xác.

QUY TẮC BẮT BUỘC:
1. Chỉ chọn cặp cột có Ý NGHĨA phân tích (không ghép ID với tên).
2. Nếu 1 cột thuộc bảng parent và bảng child có quan hệ 1-nhiều:
   → PHẢI chỉ định cách aggregate cột child (mean, sum, count, max, min)
   → Đơn vị phân tích SAU aggregate phải là cấp PARENT (mỗi parent = 1 dòng)
3. KHÔNG chọn cặp mà CẢ HAI cột đều thuộc cùng 1 bảng → đã có ydata tính.
4. KHÔNG chọn cột PK/FK (chỉ là mã liên kết, không có ý nghĩa phân tích).
5. Nếu không có cặp nào hợp lệ → trả về mảng rỗng.

SCHEMA:
{schema_json}

DỮ LIỆU MẪU (10 dòng đầu mỗi bảng):
{sample_data}

TRẢ VỀ JSON:
```

```json
{
  "correlation_pairs": [
    {
      "parent_table": "customers",
      "parent_column": "age",
      "child_table": "orders",
      "child_column": "amount",
      "aggregate_method": "mean",
      "reasoning": "Tuổi khách hàng có thể ảnh hưởng đến giá trị đơn hàng trung bình",
      "confidence": "high"
    },
    {
      "parent_table": "customers",
      "parent_column": "gender",
      "child_table": "orders",
      "child_column": "amount",
      "aggregate_method": "sum",
      "reasoning": "Giới tính có thể liên quan đến tổng chi tiêu",
      "confidence": "medium"
    }
  ],
  "skipped_pairs": [
    {
      "columns": ["customers.name", "orders.product_id"],
      "reason": "Tên khách hàng và mã sản phẩm không có mối liên hệ phân tích"
    }
  ]
}
```

### Validation Layer sau LLM Phase 1

LLM có thể hallucinate (đề xuất cặp cột không tồn tại). Cần validate:

```python
def validate_llm_correlation_plan(plan, tables, schema):
    validated = []
    for pair in plan["correlation_pairs"]:
        # Check 1: Bảng có tồn tại không?
        if pair["parent_table"] not in tables:
            continue
        if pair["child_table"] not in tables:
            continue
        
        # Check 2: Cột có tồn tại không?
        if pair["parent_column"] not in tables[pair["parent_table"]].columns:
            continue
        if pair["child_column"] not in tables[pair["child_table"]].columns:
            continue
        
        # Check 3: Aggregate method hợp lệ?
        if pair["aggregate_method"] not in ["mean", "sum", "count", "min", "max", "median"]:
            pair["aggregate_method"] = "mean"  # fallback
        
        # Check 4: Quan hệ PK-FK tồn tại giữa 2 bảng?
        if not schema.has_relationship(pair["parent_table"], pair["child_table"]):
            continue
        
        validated.append(pair)
    
    return validated
```

### ⚠️ Rủi ro kiến trúc

| Rủi ro | Mức | Giải pháp |
|:---|:---:|:---|
| LLM hallucinate cột không tồn tại | Trung bình | Validation layer (code trên) loại 100% |
| LLM chọn aggregate method sai | Thấp | Có thể chạy nhiều method rồi so sánh |
| Khác kết quả mỗi lần chạy | Thấp | Dùng temperature=0, seed cố định |
| Chi phí API call | Thấp | Chỉ gọi LLM 1 lần cho Phase 1 (schema nhỏ, ~200 tokens) |

### ✅ Kết luận Architect: Kiến trúc hợp lý, có validation layer chống hallucination

---

## 🔧 Data Engineer — Đánh giá quy trình dữ liệu

### Quy trình Aggregate Before Compute — Với LLM chỉ đạo

```python
def execute_correlation_plan(tables, schema, llm_plan):
    results = []
    
    for pair in llm_plan["correlation_pairs"]:
        parent_df = tables[pair["parent_table"]]
        child_df = tables[pair["child_table"]]
        
        # Lấy FK relationship
        rel = schema.get_relationship(pair["parent_table"], pair["child_table"])
        
        # AGGREGATE TRƯỚC (theo chỉ dẫn LLM)
        agg_func = pair["aggregate_method"]  # "mean", "sum", etc.
        child_agg = child_df.groupby(rel.child_column).agg(
            **{f"{pair['child_column']}_{agg_func}": (pair["child_column"], agg_func)}
        )
        
        # JOIN SAU — mỗi parent = 1 dòng, không lặp → i.i.d. ✅
        analysis_df = parent_df.merge(
            child_agg, 
            left_on=rel.parent_column, 
            right_index=True, 
            how="inner"
        )
        
        # TÍNH CORRELATION — trên data đã aggregate, chính xác
        p_col = pair["parent_column"]
        c_col = f"{pair['child_column']}_{agg_func}"
        
        if len(analysis_df) < 10:
            results.append({**pair, "status": "SKIP_TOO_FEW", "n": len(analysis_df)})
            continue
        
        corr_val = analysis_df[[p_col, c_col]].phik_matrix().iloc[0, 1]
        
        results.append({
            **pair,
            "correlation": round(float(corr_val), 4),
            "n_samples": len(analysis_df),
            "status": "OK",
        })
    
    return results
```

### Điểm mạnh của quy trình này

1. **Aggregate trước** → mỗi parent = 1 dòng → không vi phạm i.i.d.
2. **LLM chọn aggregate method** → mean cho metric liên tục, count cho tần suất, sum cho tổng
3. **JOIN sau aggregate** → bảng nhỏ (= số parent rows) → nhanh, ít RAM
4. **Sample size = số parent rows** (không phải số child rows) → p-value đúng

### ⚠️ Vấn đề Data Engineer lo ngại

**Edge case: Parent có quá ít dòng**

```text
classes (3 dòng):
| id  | name    |
| C01 | Toán    |
| C02 | Lý      |
| C03 | Hóa     |

Sau aggregate: avg_grade per class → 3 data points
→ Correlation trên 3 điểm → VÔ NGHĨA thống kê
```

**Giải pháp:** Ngưỡng tối thiểu. Nếu sau aggregate < 30 dòng → skip + cảnh báo "Quá ít đơn vị phân tích."

### ✅ Kết luận Data Engineer: Quy trình đúng về mặt dữ liệu. Cần ngưỡng minimum samples.

---

## 🔍 Model QA Specialist — Phản biện

### Rủi ro 1: LLM có thực sự hiểu statistical validity không?

**Phản biện:** LLM không phải nhà thống kê. Nó có thể:
- Đề xuất cặp "Tuổi ↔ Số đơn hàng" với aggregate "mean" → nhưng mean(count) = count/1 = count → OK
- Đề xuất cặp vô nghĩa mà nghe có vẻ hợp lý: "Mã bưu điện ↔ Doanh thu" → spurious correlation
- Bỏ sót cặp quan trọng mà tên cột không rõ nghĩa

**Đánh giá:** Rủi ro này có NHƯNG **thấp hơn nhiều** so với rule-based:

| Tình huống | Rule-based | LLM-guided |
|:---|:---|:---|
| Cột "tuoi" vs "age" | Không hiểu | ✅ Hiểu cả 2 |
| Cột "so_tien" → aggregate sum hay mean? | Không biết | ✅ Hiểu ngữ cảnh |
| Cột không liên quan (zip_code ↔ amount) | Tính hết → rác | ✅ Biết loại |
| Hallucinate cột không tồn tại | Không xảy ra | ⚠️ Xảy ra → nhưng validation layer bắt 100% |

### Rủi ro 2: Determinism — Chạy 2 lần ra 2 kết quả khác?

**Phản biện:** LLM Phase 1 có thể chọn khác mỗi lần chạy.

**Giải pháp:**
- `temperature=0` + `seed` cố định → output gần như deterministic
- Cache kết quả LLM Phase 1 → cùng schema = cùng plan
- Nếu user chạy lại → hỏi: "Dùng plan cũ hay tạo plan mới?"

### Rủi ro 3: LLM bỏ sót cặp quan trọng

**Phản biện:** Nếu LLM không đề xuất cặp "amount ↔ age", user sẽ không biết mình đang thiếu insight.

**Giải pháp:** Trong report, liệt kê **cả** cặp đã tính VÀ cặp bị bỏ qua (với lý do). User có thể yêu cầu tính thêm cặp bất kỳ.

### ✅ Kết luận QA: Rủi ro kiểm soát được. Validation layer + transparency (hiện cặp bị skip) giải quyết hầu hết lo ngại.

---

## 📊 Product Manager — Đánh giá giá trị sản phẩm

### So sánh 5 hướng

| Hướng | Chính xác | Phức tạp code | USP | Phù hợp MVP |
|:---|:---:|:---:|:---:|:---:|
| A: JOIN trực tiếp + cảnh báo | ❌ Sai bias | ✅ Đơn giản | ⚠️ Có nhưng sai | ❌ |
| B: Aggregate rule-based | ⚠️ Không biết aggregate gì | ❌ Rất phức tạp | ✅ Nếu đúng | ❌ |
| C: Không tính, chỉ LLM narrative | ✅ Không sai | ✅ Đơn giản | ❌ Mất USP | ⚠️ |
| D: Aggregate cơ bản + LLM | ⚠️ Mean/sum có thể sai | ⚠️ Trung bình | ⚠️ | ⚠️ |
| **E: LLM-guided (đề xuất user)** | **✅ LLM chọn đúng cách aggregate** | **⚠️ Cần prompt engineering** | **✅ Mạnh** | **✅** |

### USP của Hướng E so với thị trường

```text
ydata-profiling:     Chỉ single-table correlation, tính hết, không biết cái nào đúng
pandas-profiling:    Tương tự ydata
sweetviz:            Single-table, comparison mode nhưng không cross-table
dataprep:            Single-table, có report nhưng không cross-table
D-Tale:              UI tốt nhưng correlation chỉ single-table

→ KHÔNG CÓ TOOL NÀO tính cross-table correlation VỚI aggregate đúng cách
→ Sản phẩm chúng ta sẽ là ĐẦU TIÊN có LLM-guided cross-table analysis
```

### Giá trị cho User

```text
User nhận được:
1. Correlation nội bảng (ydata) → đầy đủ, chi tiết
2. Correlation chéo bảng (LLM-guided) → CÓ CHỌN LỌC, có lý do
3. Nhận xét LLM → "Tuổi khách hàng tương quan mạnh (0.72) với 
   giá trị đơn hàng trung bình. Kết quả tính trên 200 khách hàng."
4. Cảnh báo rõ ràng → "Dựa trên lựa chọn của AI. Xem chi tiết."

So với ydata:
- ydata: Ma trận 50×50 → user không biết xem cái nào
- Chúng ta: 5-10 cặp quan trọng + giải thích → user nắm ngay
```

### ✅ Kết luận PM: Hướng E tạo ra USP mạnh nhất, phù hợp MVP.

---

## 🤝 Đồng thuận chung

### 5/5 Agent đồng ý: Hướng E (LLM-Guided) là tốt nhất cho bài toán này

**Lý do cốt lõi:** Bài toán "cặp cột nào tính tương quan được" CẦN domain knowledge. Rule-based không thể cung cấp domain knowledge cho mọi loại data. LLM là công cụ duy nhất hiện tại có khả năng này.

### Kiến trúc cuối cùng — Trụ cột 3 v2

```text
INPUT: Confirmed Schema (Trụ cột 2) + Data mẫu + Dtype info

PHASE 1 — LLM Correlation Planner (1 lần gọi API)
  ┌─────────────────────────────────────────────────┐
  │ LLM nhận: Schema + 10 dòng mẫu/bảng + PK/FK   │
  │ LLM trả: JSON — danh sách cặp cột + cách agg   │
  │ Validation: Kiểm tra cột/bảng tồn tại          │
  └─────────────────┬───────────────────────────────┘
                    │
PHASE 2 — Deterministic Compute (Pandas + Phik)
  ┌─────────────────┴───────────────────────────────┐
  │ Duyệt từng cặp LLM đề xuất:                    │
  │   1. Aggregate child → cấp parent               │
  │   2. JOIN aggregated → parent table              │
  │   3. phik/spearman trên bảng đã aggregate       │
  │   4. Ghi kết quả + sample size                  │
  └─────────────────┬───────────────────────────────┘
                    │
PHASE 3 — LLM Evaluator (tích hợp vào L4 Report)
  ┌─────────────────┴───────────────────────────────┐
  │ LLM đọc kết quả correlation + schema context    │
  │ → Đánh giá độ tin cậy từng cặp                  │
  │ → Viết insight narrative súc tích               │
  │ → Cảnh báo cặp nào nghi ngờ spurious           │
  └─────────────────────────────────────────────────┘

OUTPUT:
  - cross_table_correlations.json (đầy đủ số liệu)
  - LLM narrative (kết luận nhanh cho user)
  - Cảnh báo: "Dựa trên lựa chọn của AI"
```

### Điểm mấu chốt cần làm kỹ

1. **Prompt Phase 1** — Thiết kế rất kỹ, test nhiều schema khác nhau
2. **Validation Layer** — Bắt 100% hallucination (cột/bảng không tồn tại)
3. **Minimum samples** — Skip nếu sau aggregate < 30 dòng
4. **Transparency** — Hiện cả cặp bị LLM bỏ qua (với lý do) để user biết
5. **Override** — User có thể yêu cầu tính thêm cặp LLM bỏ sót
