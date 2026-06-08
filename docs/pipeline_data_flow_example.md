# Ví dụ Minh họa Dòng chảy Dữ liệu (Data Flow Walkthrough)

Tài liệu này dùng dữ liệu giả lập để minh chứng cho bạn thấy chính xác dữ liệu đã "biến hình" như thế nào khi đi qua các Layer của hệ thống (L0 → L1 → L2 → L2.5 → L3 → L3.5 → L4 + Guardrail). Chúng ta sẽ theo dõi hành trình của một file `sales.csv`.

---

## 1. Layer 0: Khởi đầu (Input)
Người dùng nạp vào hệ thống một file `sales.csv` gồm 1,000 dòng.
**Dữ liệu thô (Input):**
```csv
id, customer_age, ticket_price
1,  25,           100
2,  30,           150
...
899, 150,         0      <-- (Dữ liệu rác)
```

---

## 2. Layer 1: Khám tổng quát (ydata-profiling)
- **Input:** Pandas DataFrame của `sales.csv`.
- **Hành động:** Thư viện `ydata-profiling` quét các cột để tìm phân phối, tính trung bình, đếm dòng trống.
- **Output:** Trả về một Dictionary khổng lồ chứa thống kê bề mặt.
```python
# Output của Layer 1 (Minh họa)
{
    "table": {"n": 1000, "n_var": 3},
    "variables": {
        "customer_age": {"type": "Numeric", "mean": 35.5, "max": 150}
    }
}
```

---

## 3. Layer 2: Khám chuyên sâu (PyOD - Anomaly Detection)
- **Input:** Pandas DataFrame của `sales.csv`.
- **Hành động:** Ensemble (Isolation Forest + ECOD + LOF) soi từng dòng để tìm xem dòng nào kỳ lạ nhất so với đám đông.
- **Output:** Mảng (Array) chứa tọa độ các dòng rác và điểm dị biệt (Anomaly Score).
```python
# Output của Layer 2 (Minh họa)
outliers_indices = [899] # Phát hiện dòng số 899 là rác
anomaly_scores = [0.99]
```

---

## 4. Layer 2.5: Đánh giá mức độ (Severity Stack)
- **Input:** Dictionary từ Layer 1 + Array từ Layer 2.
- **Hành động:** 4 module Python chạy tuần tự:
  1. **MCAR/MAR/MNAR Detector:** Cột `customer_age` có missing data? Nếu có, phân loại lý do (ngẫu nhiên hay có hệ thống?).
  2. **Calibrator:** Tra bảng `calibrator_table.json` → "`p_missing` 5.2% với `missingness=MAR` → severity = HIGH".
  3. **CompoundEscalator:** Cột `customer_age` dính 2 lỗi (outlier + missing) → nâng `compound_severity` lên CRITICAL.
  4. **Aggregator:** Gộp toàn dataset → phán quyết: **WARN** (“Dữ liệu cần xử lý trước khi dùng”).
- **Output:** Severity đã được gán cho từng lỗi + `dataset_verdict.json`.
```python
# Output của Layer 2.5 (Minh họa)
{
    "verdict": "WARN",
    "enriched_anomalies": [
        {"issue_type": "OUTLIER_ENSEMBLE", "severity": "HIGH", "dq_dimensions": ["Accuracy"], "compound_severity": "CRITICAL"}
    ]
}
```

---

## 5. Layer 3: Đóng gói (JSON Ontology với C1 Fields)
- **Input:** Dictionary từ Layer 1 + Array từ Layer 2 + Severity từ Layer 2.5.
- **Hành động:** Code Pydantic của chúng ta sẽ "nhào nặn" tất cả thành JSON chuẩn mực với các trường DAMA (dq_dimensions, ml_impact, compound_severity, confidence).
- **Output:** 3 file JSON: `data_quality_findings.json`, `schema_evaluation_findings.json`, `dataset_verdict.json`.
```json
{
  "dataset_meta": { "n": 1000 },
  "columns": {
    "customer_age": {
      "mean": 35.5, "max": 150,
      "missingness_mechanism": "MAR"
    }
  },
  "anomalies": [
    {
      "issue_type": "OUTLIER_ENSEMBLE",
      "severity": "HIGH",
      "dq_dimensions": ["Accuracy"],
      "ml_impact": ["training_bias"],
      "compound_severity": "CRITICAL",
      "confidence": 0.99,
      "top_10_samples": [ {"row_index": 899, "customer_age": 150, "ticket_price": 0} ]
    }
  ]
}
```

---

## 6. Layer 3.5: Visualization phụ trợ cho end user
- **Input:** `data_quality_findings.json` + DataFrame gốc.
- **Hành động:** Python có thể vẽ biểu đồ chẩn đoán nếu sản phẩm cần minh họa cho người dùng. Quyết định vẽ chart thuộc code deterministic, không thuộc L4.
- **Output:** Một file ảnh được lưu tại `output/charts/scatter_age_price.png`.
- **Ghi chú:** Chart không được gửi vào L4 và không được dùng làm nguồn số liệu cho LLM.

---

## 7. Layer 4 (Vòng 1): Text-only Mini Agent
- **Input:** File `data_quality_findings.json`, `dataset_verdict.json`, và raw top-k samples dạng số/chữ. Không có chart, không Vision, không lệnh vẽ biểu đồ.
- **Hành động:** LLM đọc JSON, phát hiện ra *"Có khách hàng tuổi = 150 mà giá vé = 0, vô lý quá!"*. Nó chỉ được diễn giải dữ liệu đã có.
- **Output của LLM:** Một đoạn nhận xét text/JSON có trace về finding gốc:
```json
{
  "nhan_xet": "Cột customer_age có dữ liệu rác nghiêm trọng (tuổi = 150).",
  "source_finding": "OUTLIER_ENSEMBLE.customer_age"
}
```

---

## 8. Layer 4 (Vòng 1.5): 🛑 Guardrail kiểm tra số liệu
- **Input:** Toàn bộ văn bản mà Mini Agent vừa viết.
- **Hành động:** Hàm Python `validate_output()` chạy 2 bước:
  1. **Allowed-Set Check:** Regex quét mọi con số trong văn bản LLM (“150”, “0đ”, “35.5”...) → đối chiếu với danh sách số hợp lệ từ JSON gốc. Nếu số nào không khớp (ví dụ LLM bịa “200 tuổi”) → đánh dấu Hallucination.
  2. **Column-Name Check:** Quét tên cột — nếu LLM nhắc đến cột `"revenue"` nhưng JSON không có cột này → Hallucination.
- **Kết quả:** PASS ✔️ (không có số bịa). Nếu FAIL → Retry tối đa 3 lần.

---

## 9. Layer 4 (Vòng 2): Chốt hạ Báo cáo (Master Agent)
- **Input:** 
  1. Toàn bộ nhận xét của Mini Agent (đã qua Guardrail ✔️).
  2. Phán quyết từ `dataset_verdict.json` (WARN).
  3. Schema/relationship metadata nếu có.
- **Hành động:** Master Agent (GPT-4o) ráp nhận xét thành Markdown text-only. **Sau đó Guardrail chạy lần 2** để kiểm tra đầu ra Master.
- **Output (Final):** Báo cáo `report.md` gửi cho người dùng.

```markdown
# Báo cáo Chất lượng Dữ liệu Sales

## Phán quyết: ⚠️ WARN — Dữ liệu cần xử lý trước khi dùng

## 1. Tình trạng chung
Hệ thống phát hiện dữ liệu dị biệt nghiêm trọng cần xử lý ngay.

## 2. Phân tích Chuyên sâu (Cột Tuổi & Giá vé)
- **Loại lỗi:** Accuracy (chuẩn DAMA-DMBOK)
- **Mức độ:** CRITICAL (cột dính nhiều lỗi, được CompoundEscalator nâng bậc)
- **Ảnh hưởng ML:** training_bias — nếu train AI trên data này, model sẽ sai lệch.

**Khuyến nghị:** Cần lọc bỏ các dòng có tuổi > 100 trước khi đem train AI.
```

*(Nếu sản phẩm có sinh chart ở Layer 3.5, chart được đính kèm như artifact phụ trợ riêng cho end user. L4 không nhìn hoặc tạo chart.)*
