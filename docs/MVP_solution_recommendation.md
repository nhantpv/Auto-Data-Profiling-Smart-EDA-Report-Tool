# Báo cáo đề xuất hướng giải quyết MVP cho Smart EDA v3.0

Ngày cập nhật: 2026-06-09  
Mục tiêu: tổng hợp các vấn đề trong `Problem_need_to_be_solved.md`, đối chiếu với code hiện tại, và đề xuất hướng giải quyết tối ưu cho MVP, tránh overengineering.

## 1. Kết luận ngắn

Code hiện tại đã có nền tảng tốt cho MVP:

- Đọc được CSV, Excel, Parquet, JSON/JSONL/NDJSON.
- Có pipeline single-table và multi-table.
- Có schema validation và relationship inference khi không có DBML/SQL DDL.
- Có data quality findings, schema findings, dataset verdict.
- Có L3.5 diagnostic chart PNG.
- Có L4 deterministic report và guardrail cơ bản.
- Có web app localhost chạy theo background job.
- Có eval harness nền tảng cho schema relationship và artifact output.

Vì vậy không nên viết lại toàn bộ. Hướng tối ưu là **làm sâu các module hiện có**, bổ sung contract còn thiếu, và chỉ thêm cross-table analysis ở mức MVP an toàn.

Khuyến nghị chọn hướng:

```text
Option B - MVP có cross-table an toàn

1. Làm giàu verdict/report contract.
2. Thêm ArtifactManifest.
3. Mở rộng schema eval để giảm false-positive.
4. Thêm cross_table_findings.json bản nhỏ, deterministic, fail-safe.
5. Giữ L4 text-only, không Vision, không placeholder chart.
```

## 2. Những điểm không nên làm trong MVP

Các ý dưới đây có vẻ hấp dẫn nhưng nên loại khỏi MVP vì rủi ro cao hoặc chưa cần thiết:

| Không làm | Lý do |
| --- | --- |
| LLM sinh placeholder chart như `[CHART_OUTLIER]` | Trái contract L4 text-only, có rủi ro prompt injection/path traversal, không cần vì chart đã sinh deterministic ở L3.5. |
| Gửi ảnh/chart vào LLM Vision | Tốn token, chậm, dễ hallucinate số liệu từ ảnh. |
| Chuyển toàn bộ chart sang Plotly/ECharts interactive | Tốt cho UI sau này nhưng chưa cần cho MVP; PNG diagnostic hiện đủ. |
| Tạo `auto_schema.py` mới song song với `schema_engine.py` | Code hiện đã có schema inference. Tạo module mới sẽ có 2 nguồn sự thật. |
| Dùng Jaccard làm metric chính cho FK inference | Sai với surrogate keys như `users.id` và `products.id` cùng range. |
| Dùng LLM để chốt FK/fact table | LLM không nên là source of truth ở L2. FK/fact phải deterministic và có evidence. |
| Auto `groupby().first()` khi join key không unique | Che giấu lỗi dữ liệu, kết quả phụ thuộc thứ tự dòng. MVP nên fail-safe. |
| Nhét toàn bộ `issues_breakdown` vào `dataset_verdict.json` | Làm verdict phình to, trùng dữ liệu với findings JSON, tốn context cho LLM. |
| Đổi missingness từ Logistic Regression sang dummy correlation | Code hiện dùng hướng tốt hơn; dummy correlation yếu hơn về mặt thống kê. |
| Build streaming framework cho mọi file format | Quá lớn cho MVP. Nếu cần, ưu tiên CSV key-column scan trước. |

## 3. Mapping vấn đề sang hướng giải quyết MVP

| Vấn đề | Hiện trạng code | Hướng MVP đề xuất | Kết quả mong muốn |
| --- | --- | --- | --- |
| L4/Chart | Đã có `l4_report.md`, `guardrail_report.json`, diagnostic PNG | Giữ L4 text-only; thêm `ArtifactManifest` để report/UI chỉ tham chiếu artifact hợp lệ | Không Vision, không placeholder, không path traversal |
| Auto schema | Đã có inferred PK/FK trong `schema_engine.py` bằng value coverage + name score | Không tạo `auto_schema.py`; refactor nhẹ sau, trước mắt thêm eval false-positive | Relationship inference đáng tin hơn |
| Jaccard/surrogate key false-positive | Code hiện không dùng Jaccard chính | Thêm eval case `users.id` vs `products.id` cùng range | Giảm nhầm quan hệ FK |
| Multi-role FK | Chưa có eval riêng | Thêm fixture `buyer_id`, `seller_id` cùng trỏ `users.id` | Không ép một parent chỉ có một child FK |
| Verdict thiếu insight | `dataset_verdict.json` hiện chỉ summary count | Thêm `top_issues` compact + `detail_ref` | End user/LLM hiểu vì sao NOT_READY/WARN |
| Compound severity dễ gây hiểu nhầm | `compound_severity` đang gắn lên từng finding | Report phân biệt `severity` gốc và `effective_severity` dùng để xếp hạng | Không phóng đại lỗi INFO thành lỗi blocker |
| WARN nhiều nhưng verdict READY | Aggregator chỉ NOT_READY nếu CRITICAL, WARN nếu HIGH | Thêm rule nhẹ: issue density/risk score, nhưng giữ hard blockers | Verdict scale tốt hơn theo kích thước dataset |
| Cross-table insight | Multi-table hiện profile từng bảng + relationship/schema validation, chưa có cross-table correlation | Thêm `cross_table_findings.json` bản nhỏ: safe join plan + fact candidates + caveat | Có insight chéo bảng nhưng không làm sai stats gốc |
| Fan-out join | Chưa có cross-table engine | Safe join rule: parent key phải unique, nếu không thì skip join + warning | Không nổ RAM, không nhân bản fact rows |
| Cardinality filter | Chưa có cross-table filter | Dtype-aware: high-cardinality string drop, numeric/datetime keep, ID-like numeric drop | Không xóa nhầm cột tiền/ngày |
| Correlation giả do NULL overlap | Chưa có cross-table engine | Filter cột có join-null ratio cao, ví dụ >70% | Không báo tương quan giả |
| Sampling file lớn | Có `sample_if_large`, nhưng sample sau khi load full DataFrame | MVP: thêm metadata `is_sampled`, `original_n`, `sample_n`; streaming key scan để phase sau | Không gây hiểu nhầm số dòng trong report |

## 4. Hướng triển khai khuyến nghị

### Phase 1 - Contract và report rõ ràng hơn

Mục tiêu: cải thiện chất lượng output ngay, ít rủi ro nhất.

Tasks:

- Thêm model `IssueSummary`.
- Thêm `top_issues` vào `DatasetVerdict`.
- `top_issues` chỉ chứa tóm tắt lỗi quan trọng, không chứa `top_10_samples`.
- Mỗi item có `detail_ref` trỏ về file gốc:
  - `data_quality_findings.json`
  - `schema_evaluation_findings.json`
- Thêm `effective_severity` để xếp hạng nhưng giữ `severity` gốc.
- Update L4 deterministic report để dùng `top_issues`.
- Update guardrail evidence builder để đọc số/reference từ `top_issues`.

Output mong muốn:

```json
{
  "verdict": "NOT_READY",
  "summary": {
    "total_issues": 3,
    "critical": 1,
    "high": 1,
    "warn": 1,
    "info": 0
  },
  "top_issues": [
    {
      "source": "schema_evaluation_findings",
      "issue_type": "PK_DUPLICATE",
      "effective_severity": "CRITICAL",
      "affected_table": "users",
      "affected_column": "user_id",
      "affected_count": 150,
      "rationale": "Primary key user_id contains duplicate values.",
      "detail_ref": {
        "file": "schema_evaluation_findings.json",
        "issue_index": 0
      }
    }
  ]
}
```

Definition of done:

- `dataset_verdict.json` nhỏ, dễ đọc.
- Không duplicate full findings.
- L4 report giải thích được vì sao verdict là WARN/NOT_READY.
- Full test pass.

### Phase 2 - ArtifactManifest để khóa đường dẫn artifact

Mục tiêu: UI/report chỉ render artifact hợp lệ, không dùng path do LLM bịa.

Tasks:

- Tạo `artifact_manifest.json`.
- Mỗi artifact có:
  - `artifact_id`
  - `kind`: `json`, `markdown`, `csv`, `png`
  - `path`
  - `source`
  - `description`
- Web app list file từ manifest nếu có, fallback scan folder nếu chưa có.
- Report chỉ tham chiếu artifact id đã tồn tại.

Definition of done:

- Không có arbitrary file path trong report/UI.
- Diagnostic chart vẫn là PNG.
- Không cần Plotly/ECharts trong MVP.

### Phase 3 - Schema inference eval hardening

Mục tiêu: tăng độ tin cậy schema inference hiện có, không viết engine mới.

Tasks:

- Mở rộng `examples/evaluation/schema_relationship_eval.json`.
- Thêm false-positive cases:
  - `users.id` và `products.id` cùng range nhưng không liên quan.
  - `buyer_id`, `seller_id` cùng trỏ về `users.id`.
  - bridge table.
  - parent dimension lớn, child sample nhỏ.
  - string/numeric ID mismatch.
- Chạy `scripts/evaluate_schema_relationships.py`.
- Chỉ chỉnh policy/threshold khi eval chứng minh cần.

Definition of done:

- Eval JSON có precision/recall/F1.
- Relationship inference không tụt trên sample hiện có.
- Không dùng LLM để xác nhận FK.

### Phase 4 - Cross-table MVP an toàn

Mục tiêu: có insight chéo bảng nhưng không làm sai single-table stats.

Output mới:

```text
cross_table_findings.json
```

Nội dung tối thiểu:

- `fact_candidates`
- `selected_fact_view`
- `join_plan`
- `join_warnings`
- `column_selection`
- `cross_table_associations`
- `interpretation_caveats`

Guardrails bắt buộc:

- Không tạo universal table.
- Không dùng joined table để tính lại mean/missing/duplicate của bảng gốc.
- Parent join key phải unique.
- Nếu parent key non-unique: skip join và ghi `NON_UNIQUE_JOIN_KEY`.
- Nếu join làm tăng row count bất thường: abort hoặc warning rõ.
- String high-cardinality: drop.
- Numeric/datetime continuous: keep.
- ID-like numeric: drop khỏi measure set.
- Join-null ratio >70%: không tính correlation cho cột đó.
- Output luôn ghi caveat: association không phải causation.

MVP correlation nên đơn giản:

- Numeric-numeric: Pearson/Spearman.
- Categorical-categorical: để phase sau nếu không có library ổn.
- Mixed type: để phase sau.

Definition of done:

- Không crash với multi-table sample.
- Có warning khi không đủ điều kiện join.
- Có 1-3 association đáng đọc nếu dữ liệu đủ điều kiện.
- Không report insight khi evidence yếu.

### Phase 5 - Sampling metadata, chưa cần full streaming

Mục tiêu: không làm user hiểu nhầm dataset đã bị sample.

Tasks:

- Thêm vào `DatasetMeta`:
  - `is_sampled`
  - `original_n`
  - `sample_n`
  - `sample_method`
  - `sample_seed`
- `load_any(...)` trả thêm metadata hoặc chuyển sang `LoadedTable`.
- Report ghi rõ khi dataset đã sample.

Post-MVP:

- `KeyColumnScanner` streaming cho CSV integrity check.
- Stratified sampling nếu có target/categorical column rõ.
- Memory benchmark.

## 5. Roadmap đề xuất theo mức ưu tiên

### Nên làm ngay cho MVP

1. `DatasetVerdict.top_issues`.
2. `ArtifactManifest`.
3. Schema relationship eval hardening.
4. Cross-table MVP safe join.
5. Sampling metadata.

### Làm sau MVP

1. Refactor sâu `schema_engine.py` thành `SchemaAnalyzer`.
2. Streaming key scan cho CSV lớn.
3. Stratified sampling.
4. Interactive chart Plotly/ECharts.
5. Multi-agent L4 đầy đủ.
6. Severity calibration bằng benchmark.

### Không nên làm

1. LLM chart placeholder.
2. LLM chốt FK/fact table.
3. Jaccard làm FK metric chính.
4. Auto aggregation `groupby().first()` để sửa join.
5. Nhồi full `issues_breakdown` vào verdict.
6. Đổi missingness sang dummy correlation.

## 6. Quyết định cần chọn

Có 3 lựa chọn:

| Option | Nội dung | Đánh giá |
| --- | --- | --- |
| A | Chỉ làm contract/report: `top_issues`, `ArtifactManifest`, schema eval | An toàn nhất, ít code nhất, nhưng chưa có cross-table insight mới |
| B | Option A + cross-table MVP safe join | Cân bằng tốt nhất cho MVP; có thêm giá trị multi-table rõ ràng |
| C | Full architecture: streaming, interactive chart, multi-agent, calibration | Quá lớn, dễ overengineer |

Khuyến nghị: **chọn Option B**.

Lý do:

- Vừa xử lý các vấn đề mentor/team quan tâm nhất: input-output layer, multi-table, FK inference, end-user report.
- Không viết lại toàn bộ hệ thống.
- Không đưa LLM vào chỗ cần deterministic.
- Có thể demo được bằng localhost và sample data hiện có.

## 7. Kết luận

MVP không cần "bulletproof enterprise architecture". MVP cần:

- Output rõ.
- Không bịa số liệu.
- Không join sai làm lệch thống kê.
- Không crash trên sample vừa.
- Có cảnh báo trung thực khi evidence không đủ.

Do đó hướng tối ưu là **tăng chất lượng contract và guardrail quanh pipeline hiện tại**, sau đó thêm cross-table analysis ở mức nhỏ, deterministic, fail-safe.
