# Design Spec: JSON Ontology & Data Ingestion (Sub-project 1)

## 1. Goal
Thiết kế bộ khung (Data Contract) để chuẩn hóa dữ liệu đầu ra từ Layer 1, 2 & 2.5 thành 3 file JSON, đóng vai trò là "Ngôn ngữ giao tiếp" duy nhất giữa hệ thống phân tích Python và đội ngũ LLM Agents. Đồng thời xác định luồng dữ liệu đầu vào (Ingestion).

## 2. Core Architecture Decisions (Các quyết định đã chốt)

1. **Strict Validation (Đổ bê tông cấu trúc):** Sử dụng `Pydantic` để định nghĩa toàn bộ cấu trúc JSON. Nếu Layer 1 & 2 xuất ra sai kiểu dữ liệu, hệ thống sẽ báo lỗi ngay lập tức thay vì đẩy "rác" cho LLM.
2. **Flexible Expansion (Mở rộng linh hoạt):** Các class Pydantic sẽ có một trường `additional_metrics: Dict[str, Any]` để chứa các chỉ số thống kê dị biệt mà không làm gãy cấu trúc lõi.
3. **Anomaly Handling (Xử lý dung lượng dữ liệu rác):** Áp dụng chiến lược "Summarization + Top-K". Thay vì gửi hàng chục ngàn dòng outliers, JSON chỉ chứa: Tổng số lượng lỗi, tỷ lệ %, và **Top 10 dòng rác tồi tệ nhất** (Anomaly Score cao nhất).
4. **L4 text-only:** LLM không nhận chart, không Vision, không sinh lệnh vẽ biểu đồ. Payload L4 chỉ gồm JSON findings và raw top-k samples dạng số/chữ.
5. **Đồ thị (Charts) là artifact phụ trợ:** Overview/Diagnostic charts có thể được Python sinh ra cho end user ở L3.5, nhưng không nằm trong contract bắt buộc của L4 và không được dùng làm nguồn số liệu cho LLM.
6. **Data Export (Bắt trọn dữ liệu):** Bên cạnh báo cáo Markdown, hệ thống tự động xuất (dump) toàn bộ 100% các dòng dữ liệu bị lỗi ra các file riêng biệt (VD: `output/anomalies/outliers_export.csv`) để Data Engineer có thể tải về xử lý.

## 3. Data Contracts (Cấu trúc JSON)

### 3.1. data_quality_findings.json (Gửi cho Data QA Agent)
Đầu ra kết hợp từ `fg-data-profiling` và `PyOD Ensemble (IForest + ECOD + LOF)`.

```json
{
  "dataset_meta": {
    "file_name": "titanic.csv",
    "n": 891,
    "n_var": 12,
    "memory_size": 85632,
    "p_cells_missing": 0.08,
    "n_duplicates": 12,
    "p_duplicates": 0.0135,
    "overview_charts": {
      "correlation_heatmap": "output/charts/heatmap.png",
      "missing_matrix": "output/charts/missing.png"
    }
  },
  "columns": {
    "Age": {
      "type": "Numeric",
      "n_missing": 177,
      "p_missing": 0.19865,
      "n_zeros": 0,
      "missingness_mechanism": "MAR",
      "additional_metrics": {
        "mean": 29.69,
        "std": 14.52,
        "min": 0.42,
        "max": 80.0
      }
    },
    "Sex": {
      "type": "Categorical",
      "n_missing": 0,
      "p_missing": 0.0,
      "n_distinct": 2,
      "additional_metrics": {}
    }
  },
  "anomalies": [
    {
      "issue_type": "OUTLIER_ENSEMBLE",
      "description": "Phát hiện 25 dòng dị biệt (2.8% data)",
      "severity": "HIGH",
      "dq_dimensions": ["Accuracy"],
      "ml_impact": ["training_bias"],
      "compound_severity": "HIGH",
      "confidence": 0.92,
      "top_10_samples": [
        {"PassengerId": 259, "Age": 35, "Fare": 512.3292, "anomaly_score": 0.99},
        {"PassengerId": 738, "Age": 35, "Fare": 512.3292, "anomaly_score": 0.98}
      ],
      "full_anomalies_export_path": "output/anomalies/outliers_export.csv"
    }
  ]
}
```

### 3.2. schema_evaluation_findings.json (Gửi cho Architect Agent)
Đầu ra từ `pydbml`/SQL DDL parser và logic kiểm tra Pandas. File này phải thể hiện được cả quan hệ explicit trong schema và quan hệ inferred khi thiếu FK metadata.

```json
{
  "schema_meta": {
    "schema_file": "ecommerce.dbml",
    "total_tables": 5,
    "total_relationships": 4
  },
  "tables": [
    {
      "name": "orders",
      "columns": ["id", "user_id", "total"]
    }
  ],
  "integrity_errors": [
    {
      "error_type": "ORPHAN_FOREIGN_KEY",
      "description": "Có 15 orders chứa user_id không tồn tại trong bảng Users",
      "severity": "CRITICAL",
      "affected_table": "orders",
      "affected_column": "user_id",
      "top_10_samples": [
        {"order_id": 101, "invalid_user_id": 9999}
      ]
    },
    {
      "error_type": "COLUMN_ALIAS_INFERRED",
      "description": "Column 'id_school' absent but 'trường học' is a likely alias",
      "severity": "WARN",
      "affected_table": "students",
      "affected_column": "id_school",
      "missing_field_context": {
        "expected_column": "id_school",
        "table_context": "Table 'students' expects 2 schema column(s); loaded data has 2 column(s).",
        "inferred_meaning": "school identifier or school attribute",
        "is_intentional_missing": null,
        "intentional_missing_basis": "unknown; source owner confirmation required",
        "candidate_aliases": ["trường học"]
      }
    },
    {
      "error_type": "MISSING_RELATIONSHIP_METADATA",
      "description": "Likely relationship students.id_school -> schools.id is present in data but not declared in schema",
      "severity": "WARN",
      "affected_table": "students",
      "affected_column": "id_school",
      "relationship": {
        "child_table": "students",
        "child_column": "id_school",
        "parent_table": "schools",
        "parent_column": "id",
        "relationship_type": "inferred_fk",
        "status": "missing_from_schema",
        "confidence": 0.91,
        "evidence": ["value_coverage=1.000", "name_score=0.920"]
      }
    }
  ],
  "relationships": [
    {
      "child_table": "orders",
      "child_column": "user_id",
      "parent_table": "users",
      "parent_column": "id",
      "relationship_type": "explicit_fk",
      "status": "declared_in_schema",
      "confidence": 1.0,
      "evidence": ["Declared in schema metadata"]
    }
  ]
}
```

### 3.3. dataset_verdict.json (Phán quyết Tổng thể — từ C2 Aggregator)
Đầu ra từ module `severity/aggregator.py`. Trả lời câu hỏi: "Dữ liệu này dùng được chưa?"

```json
{
  "dataset_meta": {
    "file_name": "titanic.csv",
    "n": 891,
    "n_var": 12
  },
  "verdict": "WARN",
  "verdict_rationale": "2 cột có severity HIGH, 1 lỗi CRITICAL ở ORPHAN_FOREIGN_KEY",
  "summary": {
    "total_issues": 5,
    "critical": 1,
    "high": 2,
    "medium": 1,
    "info": 1
  }
}
```

## 4. Ingestion Layer (Đầu vào)
- **Data Reader:** Sử dụng `pandas` để đọc CSV/Excel/Parquet/JSON/JSONL. Nếu file > 500MB hoặc > 500k rows, tự động trigger hàm `sample(n=500000)`.
- **Schema Parser:** Sử dụng `pydbml` cho DBML và SQL DDL adapter cho `.sql`, trả về cùng một `UnifiedSchemaResult` để phục vụ `schema_engine`.
