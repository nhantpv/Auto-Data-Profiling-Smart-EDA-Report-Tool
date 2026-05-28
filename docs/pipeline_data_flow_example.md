# Ví dụ Minh họa Dòng chảy Dữ liệu (Data Flow Walkthrough)

Tài liệu này dùng dữ liệu giả lập để minh chứng cho bạn thấy chính xác dữ liệu đã "biến hình" như thế nào khi đi qua 4 Layer của hệ thống. Chúng ta sẽ theo dõi hành trình của một file `sales.csv`.

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
- **Hành động:** Thuật toán Isolation Forest soi từng dòng để tìm xem dòng nào kỳ lạ nhất so với đám đông.
- **Output:** Mảng (Array) chứa tọa độ các dòng rác và điểm dị biệt (Anomaly Score).
```python
# Output của Layer 2 (Minh họa)
outliers_indices = [899] # Phát hiện dòng số 899 là rác
anomaly_scores = [0.99]
```

---

## 4. Layer 3: Đóng gói (JSON Ontology)
- **Input:** Dictionary từ Layer 1 + Array từ Layer 2.
- **Hành động:** Code Pydantic của chúng ta sẽ "nhào nặn" 2 cục data này thành một file JSON chuẩn mực.
- **Output:** File `data_quality_findings.json`.
```json
{
  "dataset_meta": { "n": 1000 },
  "columns": {
    "customer_age": { "mean": 35.5, "max": 150 }
  },
  "anomalies": [
    {
      "issue_type": "OUTLIER",
      "top_samples": [ {"row_index": 899, "customer_age": 150, "ticket_price": 0} ]
    }
  ]
}
```

---

## 5. Layer 4 (Vòng 1): Khám bệnh & Yêu cầu vẽ biểu đồ
- **Input:** File `data_quality_findings.json` ở trên được gửi cho **Mini Agent (GPT-4o-mini)**.
- **Hành động:** LLM đọc JSON, phát hiện ra *"Ô kìa, có khách hàng tuổi = 150 mà giá vé = 0, vô lý quá!"*. Nó quyết định phải có biểu đồ để sếp nhìn thấy sự vô lý này.
- **Output của LLM:** LLM không trả về một câu nói bình thường. Chúng ta đã prompt ép LLM phải trả về một chuỗi JSON (Function Calling) chứa Lệnh Vẽ:
```json
{
  "nhan_xet": "Cột customer_age có dữ liệu rác nghiêm trọng (tuổi = 150).",
  "lenh_ve_bieu_do": {
    "chart_type": "scatter",
    "x_axis": "customer_age",
    "y_axis": "ticket_price",
    "title": "Phân tán Tuổi và Giá vé để bóc trần rác"
  }
}
```

---

## 6. Layer 3.5: Thực thi lệnh vẽ biểu đồ (Visualization Engine)
- **Input:** Cái cục `"lenh_ve_bieu_do"` mà con LLM vừa nhả ra.
- **Hành động:** Code Python của chúng ta (file `visualizer.py`) nhận lệnh. Nó tự động gọi `seaborn.scatterplot(x='customer_age', y='ticket_price')` và lưu thành file ảnh `.png`.
- **Output:** Một file ảnh được lưu tại `output/charts/scatter_age_price.png`.
- **Ghi chú:** (Optional) Ta sẽ ném luôn cái file ảnh này ngược lại cho Agent nếu muốn nó viết nhận xét dựa trên tầm nhìn đa phương thức (Vision).

---

## 7. Layer 4 (Vòng 2): Chốt hạ Báo cáo (Master Agent)
- **Input:** 
  1. Toàn bộ nhận xét của Mini Agent ("Cột customer_age có dữ liệu rác...").
  2. Đường link (địa chỉ) của cái ảnh vừa được vẽ ở bước trên (`output/charts/scatter_age_price.png`).
- **Hành động:** Master Agent (GPT-4o) làm nhiệm vụ của Tổng biên tập. Nó sẽ ráp chữ và link ảnh lại với nhau bằng cú pháp Markdown.
- **Output (Final):** Báo cáo `report.md` gửi cho người dùng.

```markdown
# Báo cáo Chất lượng Dữ liệu Sales

## 1. Tình trạng chung
Hệ thống phát hiện một số dữ liệu dị biệt nghiêm trọng cần xử lý ngay.

## 2. Phân tích Chuyên sâu (Cột Tuổi & Giá vé)
Có hiện tượng lỗi nhập liệu ở cột tuổi. Một số khách hàng được ghi nhận là 150 tuổi và mua vé với giá 0đ. Điều này làm sai lệch toàn bộ mô hình doanh thu.

**Bằng chứng:**
![Biểu đồ rác dữ liệu Tuổi - Giá vé](output/charts/scatter_age_price.png)

**Khuyến nghị:** Cần lọc bỏ các dòng có tuổi > 100 trước khi đem train AI.
```

*(Lúc người dùng mở báo cáo này lên, phần `![Biểu đồ...]` sẽ tự động load tấm ảnh mà Python vừa vẽ ở bước 6 ra màn hình, tạo thành một báo cáo cực kỳ trực quan và thuyết phục).*
