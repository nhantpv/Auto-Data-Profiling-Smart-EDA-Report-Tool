# Bản chỉnh plan sau review `review_Long_architecture.md`

Ngày cập nhật: 2026-06-09  
Mục tiêu: giữ lại các nhận xét đúng trong `review_Long_architecture.md`, phản biện các điểm chưa phù hợp, và chốt lại hướng MVP không overengineer.

## 1. Kết luận ngắn

`review_Long_architecture.md` có nhiều nhận xét thực chiến đúng, đặc biệt ở các điểm:

- Không dùng Vision LLM.
- Cần artifact allowlist/manifest.
- Jaccard không đủ tin cậy cho FK inference.
- `Value Coverage` vẫn có false-positive với surrogate keys.
- Cross-table join phải có safe join rule.
- Cardinality filter phải xét dtype.
- Sampling phải minh bạch qua metadata.
- `dataset_verdict.json` không nên nhồi toàn bộ findings.
- Compound severity hiện cần sửa logic.

Tuy nhiên, một số đề xuất trong file review **quá nặng cho MVP** hoặc đi ngược nguyên tắc deterministic-first:

- Không nên bắt buộc LLM chốt FK.
- Không nên bắt buộc human confirmation trước mọi cross-table run.
- Không nên coi OOM là vấn đề phase sau rồi bỏ guardrail.
- Không nên auto sửa dimension bằng `groupby().first()`.
- Không nên "đập bỏ" toàn bộ severity stack; chỉ sửa đúng logic compound và verdict.

Hướng MVP sau khi chỉnh:

```text
1. Giữ L4 text-only.
2. Thêm ArtifactManifest.
3. Làm giàu DatasetVerdict bằng top_issues + detail_ref.
4. Mở rộng eval cho schema inference false-positive.
5. Thêm CrossTable MVP an toàn: safe join + dtype filter + caveat.
6. Thêm sampling metadata.
```

## 2. Phần chuẩn nên giữ

### 2.1. L4 text-only, không Vision

Nhận xét trong review là đúng.

Lý do:

- Vision LLM tốn token và không đáng tin khi đọc chart.
- Số liệu gốc đã nằm trong JSON deterministic.
- Chart là artifact phụ trợ cho end user, không phải input cho L4.

Plan MVP:

- L4 chỉ nhận JSON + raw top-k samples dạng số/chữ.
- Không gửi image/chart vào LLM.
- Không cho LLM sinh chart command.
- `l4_report.md` phải pass guardrail trước khi ghi ra output.

### 2.2. ArtifactManifest là cần thiết

Nhận xét trong review là đúng.

Rủi ro cần chặn:

- LLM hoặc report text nhắc tới đường dẫn không tồn tại.
- UI render file ngoài output folder.
- Sau này nếu có interactive chart, artifact path càng cần allowlist.

Plan MVP:

Tạo `artifact_manifest.json`:

```json
{
  "schema_version": "artifact_manifest_v1",
  "artifacts": [
    {
      "artifact_id": "diagnostic_outlier_salary_age",
      "kind": "png",
      "path": "outliers_realistic__diagnostic_salary_age.png",
      "source": "l3_5_visualization",
      "description": "Outlier diagnostic scatter plot."
    }
  ]
}
```

UI/report chỉ được tham chiếu artifact có trong manifest.

### 2.3. Jaccard không phù hợp làm metric FK chính

Nhận xét trong review là đúng.

Jaccard dễ sai với surrogate keys:

- `users.id`: 1..100
- `products.id`: 1..100
- Jaccard = 100%, nhưng không có quan hệ nghiệp vụ.

Plan MVP:

- Không dùng Jaccard làm metric chính.
- Giữ hướng hiện tại: `value_coverage + name_score + parent_uniqueness`.
- Thêm eval false-positive để khóa behavior.

### 2.4. Value Coverage vẫn có false-positive

Nhận xét trong review là đúng một phần.

Ví dụ:

- `orders.user_id`: 1..50
- `products.id`: 1..100
- Value coverage có thể = 100%, nhưng name/table semantics không khớp.

Plan MVP:

- Không tin coverage một mình.
- Relationship candidate phải qua nhiều cổng:
  - parent key unique.
  - value coverage đủ cao.
  - name/table score đủ cao.
  - generic `id` phải bị phạt nếu table concept không khớp.
  - relationship evidence phải ghi rõ.

### 2.5. Safe Join Rule là bắt buộc

Nhận xét trong review là đúng.

Nếu dimension key không unique, LEFT JOIN có thể gây fan-out:

```text
1 fact row x 5 dimension matches = 5 output rows
```

Plan MVP:

- Trước merge, assert parent join key unique.
- Nếu không unique:
  - emit `NON_UNIQUE_JOIN_KEY`.
  - không join mặc định.
  - không tính cross-table correlation.

### 2.6. Dtype-aware cardinality filter là bắt buộc

Nhận xét trong review là đúng.

Không được loại numeric/datetime chỉ vì cardinality cao.

Plan MVP:

| Dtype | Rule |
| --- | --- |
| String/categorical high-cardinality | Drop khỏi association/correlation |
| Numeric continuous | Keep |
| Datetime | Keep hoặc derive time features |
| ID-like numeric | Drop khỏi measure set nếu name/evidence cho thấy là key |

### 2.7. Sampling metadata là bắt buộc

Nhận xét trong review là đúng.

Hiện code có `sample_if_large`, nhưng `DatasetMeta` chưa ghi rõ sample state.

Plan MVP:

Thêm vào `DatasetMeta`:

- `is_sampled`
- `original_n`
- `sample_n`
- `sample_method`
- `sample_seed`

Report phải nói rõ nếu kết quả được tính trên sample.

### 2.8. `top_issues + detail_ref` là hướng đúng

Nhận xét trong review là đúng.

Không nên đưa toàn bộ findings vào `dataset_verdict.json`.

Plan MVP:

- `dataset_verdict.json` giữ compact.
- Thêm `top_issues`.
- Mỗi issue có `detail_ref` trỏ về file detail.
- L4 dùng `top_issues` để viết report, còn detail nằm ở findings JSON.

## 3. Phần chưa chuẩn cần phản biện

### 3.1. Không đồng ý: "Bắt buộc dùng LLM chốt FK"

Review đề xuất đưa candidates qua LLM để chốt FK semantic.

Phản biện:

- MVP cần deterministic-first.
- FK inference là phần có thể đo bằng eval precision/recall.
- LLM có thể hallucinate quan hệ nghiệp vụ.
- LLM làm pipeline chậm, tốn chi phí, khó test ổn định.
- Nếu LLM quyết định FK, guardrail phải phức tạp hơn nhiều.

Hướng chỉnh:

- Không dùng LLM làm source of truth.
- Thêm eval false-positive.
- Output confidence/evidence rõ.
- Cho phép user override schema ở UI hoặc bằng DBML/SQL DDL sau này.

MVP rule:

```text
Deterministic candidate -> confidence/evidence -> report as inferred_fk
User/Schema override -> explicit_fk
LLM -> không tham gia MVP
```

### 3.2. Không đồng ý: "Bắt buộc human confirmation trước Profiling lượt 2"

Review đề xuất UI bắt khách hàng xác nhận sơ đồ trước khi chạy cross-table.

Phản biện:

- Đúng với enterprise workflow, nhưng nặng cho MVP localhost.
- Làm demo chậm và thêm UI state phức tạp.
- Hiện user có thể cung cấp DBML/SQL DDL nếu muốn explicit schema.

Hướng chỉnh:

- MVP không block pipeline để chờ confirm.
- JSON phải ghi rõ relationship là `inferred_fk`, confidence, evidence.
- UI có thể hiển thị "Inferred relationships" và cho override ở phase sau.

### 3.3. Chỉnh lại: `drop_duplicates()` trước join là hợp lý, nhưng không được âm thầm

Review đề xuất `df_dim.drop_duplicates()` trước khi check unique.

Đồng ý một phần:

- Nếu duplicate rows giống hệt 100%, dedupe là hợp lý.
- Đây là lỗi export phổ biến.
- Dedupe exact rows giúp không fail quá sớm.

Không đồng ý nếu làm âm thầm:

- User phải biết dữ liệu đã bị dedupe để join.
- Dedupe không được áp dụng cho rows có cùng key nhưng khác nội dung.

MVP rule:

```text
1. Drop exact duplicate rows in dimension copy only.
2. Record warning DEDUPED_DIMENSION_ROWS with count.
3. Check parent key unique after exact dedupe.
4. If still non-unique -> NON_UNIQUE_JOIN_KEY and skip join.
```

Không dùng `groupby().first()` trong MVP.

### 3.4. Không đồng ý: "OOM là phase sau, không cần khóa tính năng"

Review cho rằng OOM là scale hạ tầng phase sau.

Phản biện:

- Localhost MVP vẫn không được treo máy user.
- Cross-table join là nơi dễ fan-out nhất.
- Web app hiện đã có upload limit, nhưng join vẫn cần row cap.

Hướng chỉnh:

- Giữ upload limit.
- Cross-table MVP phải có:
  - `max_join_rows`.
  - `base_row_count`.
  - `joined_row_count`.
  - abort nếu joined rows tăng bất thường.

MVP rule:

```text
if joined_row_count > base_row_count:
    emit FAN_OUT_JOIN_RISK
    abort association for that join
```

### 3.5. Chỉnh lại: Compound không cần "đập bỏ", nhưng phải sửa rule

Review nói phải đập bỏ toàn bộ `compound.py`.

Đồng ý phần vấn đề:

- Logic hiện tại leo thang theo số finding cùng cột.
- INFO/WARN có thể bị kéo lên quá cao nếu cùng nhóm với lỗi khác.
- Aggregator đang dùng `compound_severity` để đếm verdict, nên lỗi compound có thể ảnh hưởng verdict.

Không cần đập bỏ toàn bộ:

- Có thể sửa rule nhỏ, ít rủi ro hơn.
- Giữ interface hiện tại để tránh phá nhiều code.

MVP rule đề xuất:

```text
Finding severity: giữ nguyên.
Effective severity: dùng để ưu tiên, nhưng tính theo rule thận trọng.

Compound escalation chỉ xảy ra khi:
- có >= 2 findings từ WARN trở lên trên cùng cột, hoặc
- có >= 2 HIGH trên cùng cột thì có thể lên CRITICAL.

INFO không tham gia escalation.
Multivariate findings như OUTLIER/DUPLICATE không bị compound theo cột.
```

Nếu chưa kịp sửa đúng:

- Disable compound escalation khỏi verdict.
- Vẫn hiển thị finding severity gốc.

## 4. Plan MVP đã chỉnh

### Phase 1 - Verdict và report contract

Tasks:

- Thêm `IssueSummary`.
- Thêm `top_issues` vào `DatasetVerdict`.
- Mỗi `top_issue` có `detail_ref`.
- L4 deterministic report dùng `top_issues`.
- Guardrail evidence đọc thêm `top_issues`.

Không làm:

- Không nhét full `issues_breakdown`.

### Phase 2 - ArtifactManifest

Tasks:

- Tạo `artifact_manifest.json`.
- Đăng ký JSON/MD/CSV/PNG artifacts.
- Web app list file từ manifest nếu có.
- Report chỉ được tham chiếu artifact id hợp lệ.

Không làm:

- Không Plotly/ECharts ở MVP.
- Không placeholder chart do LLM sinh.

### Phase 3 - Schema inference hardening

Tasks:

- Thêm eval false-positive:
  - `users.id` vs `products.id`.
  - `orders.user_id` vs `products.id`.
  - `buyer_id`, `seller_id` -> `users.id`.
  - bridge table.
  - parent dimension lớn, child sample nhỏ.
- Tune policy nếu eval fail.

Không làm:

- Không LLM chốt FK.
- Không bắt human confirmation.

### Phase 4 - Cross-table MVP safe join

Tasks:

- Tạo `cross_table_findings.json`.
- Chọn fact candidates deterministic.
- Build join plan từ explicit/inferred relationships.
- Drop exact duplicate dimension rows trong copy, ghi warning.
- Check parent key unique sau exact dedupe.
- Abort join nếu non-unique.
- Abort/warn nếu fan-out làm tăng row count.
- Dtype-aware column filter.
- Join-null ratio filter.
- Correlation MVP chỉ numeric-numeric.

Không làm:

- Không universal table.
- Không auto `groupby().first()`.
- Không mixed/categorical correlation nếu chưa có method tốt.

### Phase 5 - Sampling metadata

Tasks:

- Thêm `is_sampled`, `original_n`, `sample_n`, `sample_method`, `sample_seed`.
- Report ghi rõ khi dataset đã sample.

Không làm:

- Không streaming mọi format trong MVP.
- Không stratified sampling nếu chưa có target/categorical rõ.

### Phase 6 - Compound rule fix

Tasks:

- INFO không tham gia compound escalation.
- Chỉ escalate khi có nhiều WARN/HIGH có ý nghĩa cùng cột.
- Tách rõ `severity` và `effective_severity` trong report/verdict summary.
- Nếu chưa chắc rule, không dùng compound severity để quyết định verdict.

Không làm:

- Không gán đỏ CRITICAL cho lỗi nhẹ chỉ vì cùng cột với lỗi khác.

## 5. Roadmap ưu tiên

Nên làm theo thứ tự:

1. `top_issues + detail_ref`.
2. `ArtifactManifest`.
3. Schema eval false-positive.
4. Compound rule fix.
5. Cross-table MVP safe join.
6. Sampling metadata.

Lý do đổi thứ tự:

- `top_issues` và manifest giúp report/UI rõ hơn ngay.
- Schema eval giúp giảm rủi ro trước khi cross-table join.
- Compound fix tránh verdict bị nhiễu.
- Cross-table làm sau khi relationship inference và severity đã đáng tin hơn.

## 6. Kết luận

`review_Long_architecture.md` có nhiều phản biện đúng và nên giữ, nhất là góc nhìn "tool không nên từ chối quá nhiều dữ liệu bẩn của khách hàng". Nhưng với MVP, cần chỉnh lại:

- Không đưa LLM vào chốt FK.
- Không bắt human confirmation trong luồng chính.
- Không bỏ OOM guardrail.
- Không auto aggregate bằng `first()`.
- Không đập bỏ toàn bộ severity stack.

Plan tối ưu là làm MVP theo hướng deterministic, minh bạch, fail-safe vừa đủ, và có warning rõ khi hệ thống không đủ evidence để phân tích chéo.
