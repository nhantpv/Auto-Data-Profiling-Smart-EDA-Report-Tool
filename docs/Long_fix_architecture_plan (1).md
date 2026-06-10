# Architecture Review & Revised Fix Plan: Smart EDA v3.0

Ngày cập nhật: 2026-06-09  
Phạm vi: đối chiếu `fix_architecture_plan.md` do Claude đề xuất với code hiện tại trên branch `tanlong`.

## Kết luận ngắn

Code hiện tại đã phù hợp với hướng sản phẩm chính: **Deterministic-first, LLM-last, L4 text-only, chart là artifact phụ trợ cho end user**. Không nên implement nguyên xi plan cũ của Claude vì plan đó đang mô tả sai một số trạng thái đã có trong repo và đề xuất thêm module mới dễ trùng trách nhiệm.

Nên tiếp tục theo hướng:

```text
Web/CLI adapters
  -> JobRuntime
  -> PipelineRunner
  -> Ingestion / Profiling / Anomaly / SchemaAnalyzer / Severity
  -> FindingBundle v1
  -> ArtifactWriter / Reporters / Guardrail / EvalHarness
```

Điểm cần sửa kiến trúc không phải là thêm thật nhiều engine mới, mà là **làm sâu các module hiện có**, giảm logic dồn vào `run_pipeline.py` và `src/engines/schema_engine.py`.

## Trạng thái code hiện tại

| Layer | Trạng thái | Code hiện có | Nhận xét |
| --- | --- | --- | --- |
| L0 Ingestion | Built | `src/ingestion/registry.py`, `readers.py`, `schema_reader.py`, `sampling.py` | Đọc CSV, Excel, Parquet, JSON/JSONL/NDJSON; parse DBML/SQL DDL. |
| L1 Profiling | Built | `src/engines/profiling_engine.py` | `run_profiling(df, minimal=False)` mặc định full. Web/UI cho phép quick/minimal. Multi-table hiện ép minimal để giữ runtime. |
| L2 Anomaly | Built | `src/engines/anomaly_engine.py` | PyOD numeric-only, có outlier score/index/position. Full anomaly rows đã export CSV qua `findings_builder.py`. |
| L2 Schema | Built, cần tách module | `src/engines/schema_engine.py`, `config/schema_inference_policy.json` | Đã validate DBML/SQL, alias column, inferred PK, inferred relationship, orphan FK. Module đang quá lớn. |
| L2.5 Severity | Built, cần làm giàu verdict | `src/severity/calibrator.py`, `missingness.py`, `compound.py`, `aggregator.py` | Missingness đã có sampling 10k. Aggregator hiện chỉ trả summary, thiếu top issue context trong `dataset_verdict.json`. |
| L3 Ontology | Built | `src/ontology/models.py`, `findings_builder.py` | JSON Pydantic đã có `data_quality_findings`, `schema_evaluation_findings`, `dataset_verdict`. Multi-table bundle đã có. |
| L3.5 Charts | Built cho diagnostic, partial cho overview | `src/engines/visualizer.py` | Đã sinh `*__diagnostic_*.png`, gắn vào `diagnostic_chart`, web download được PNG. Chưa có overview chart set. |
| L4 Reporting | Partial nhưng đúng hướng | `src/reporting/l4_report.py`, `src/guardrail/narrative.py` | Có deterministic guarded report và optional OpenAI single-call fallback. Chưa phải multi-agent L4 đầy đủ. |
| Eval Process | Built nền tảng, cần mở rộng | `src/evaluation/*`, `scripts/evaluate_schema_relationships.py`, `scripts/evaluate_pipeline_artifacts.py` | Đã có eval relationship và artifact contract. Chưa có eval severity calibration, cross-table correlation, L4 hallucination suite lớn. |
| Web App | Built local production basic | `src/webapp/app.py`, `src/webapp/runtime.py` | Đã có background `ThreadPoolExecutor`, job status/progress, upload limit, file download, retry/cancel cơ bản. Chưa có queue bền vững, worker process riêng, kill running job an toàn. |

## Target + Input/Output contract qua từng Layer

Mentor yêu cầu phần này là đúng. `docs/system_architecture_design.md` đã có bảng input/output tổng quát, nhưng bản architecture fix cần ghi rõ hơn: **target của layer là gì, layer nhận gì, trả gì, và hiện code đã đáp ứng đến đâu**.

| Layer | Target | Input | Output | Hiện trạng |
| --- | --- | --- | --- | --- |
| L0 Ingestion | Chuẩn hóa mọi format dữ liệu và schema về object nội bộ thống nhất để engine phía sau không biết file gốc là gì. | Data files: `.csv`, `.xlsx/.xls`, `.parquet`, `.json/.jsonl/.ndjson`; schema optional: `.dbml`, `.sql`. | Single-table: `pandas.DataFrame`. Multi-table: `dict[table_name, DataFrame]`. Schema: parsed dict gồm `tables`, `refs`, `meta`. | Đã có qua `load_any(...)`, readers, `parse_schema(...)`. Sampling file lớn đã có module riêng nhưng chưa thành `RunMetadata` first-class. |
| L1 Profiling | Tạo thống kê nền tảng cho từng bảng gốc, không join, không làm sai phân phối. | `DataFrame` từng bảng + `ProfilingPolicy` (`full`, `minimal`, hoặc sau này `auto`). | `profile_result` dict: table stats, variables stats, missing, duplicate, numeric/categorical metrics. | Đã có `run_profiling(df, minimal=False)`. Cần policy auto rõ hơn thay vì web/multi-table tự truyền boolean. |
| L2 Anomaly | Phát hiện dòng dị biệt bằng ML truyền thống, chỉ dùng data numeric đủ điều kiện, không thay đổi dữ liệu gốc. | `DataFrame` + profile summary optional. | `anomaly_result`: `outlier_indices`, `outlier_positions`, `anomaly_scores`, `n_outliers`, `numeric_columns_used`, `skipped`. | Đã có PyOD ensemble. Đã fix index/position và export full rows ở L3 builder. Categorical anomaly vẫn là future work. |
| L2 Schema | Đối chiếu schema explicit hoặc infer schema/relationship khi thiếu DBML/DDL; ghi evidence rõ cho alias/FK. | Single-table: `DataFrame + data_path + schema_path`. Multi-table: `list[data_path] + schema_path optional`. | `SchemaEvaluationFindings`: `tables`, `integrity_errors`, `relationships[]` với `explicit_fk`/`inferred_fk`, confidence, evidence. | Đã có trong `schema_engine.py`. Cần refactor thành `SchemaAnalyzer` để giảm module quá lớn. |
| L2.5 Severity | Chuyển findings thô thành mức độ ưu tiên có ý nghĩa cho quyết định READY/WARN/NOT_READY. | `DataQualityFindings.columns`, `anomalies`, `IntegrityError[]`, calibrator policy, missingness result. | Severity per finding, `compound_severity`, `DatasetVerdict.summary`, rationale. Target tiếp theo: `top_issues` compact. | Đã có calibrator, missingness sampling 10k, compound, aggregator. Thiếu `top_issues` trong verdict. |
| L3 Ontology | Đóng gói output máy đọc ổn định, versionable, làm nguồn sự thật cho report/eval/guardrail. | L1 profile, L2 anomaly/schema, L2.5 severity, dataset metadata. | `data_quality_findings.json`, `schema_evaluation_findings.json`, `dataset_verdict.json`; multi-table bundle; CSV artifact paths. | Đã có Pydantic models và JSON writer trong pipeline. Cần `FindingBundle v1` + `ArtifactManifest` để caller không scan file rải rác. |
| L3.5 Visualization | Sinh chart deterministic cho end user, không làm nguồn số liệu cho LLM. | `DataFrame` + `anomaly_result` + L3 findings + artifact output dir. | PNG artifacts, currently `*__diagnostic_*.png`, linked via `diagnostic_chart`. Future: overview chart set in `dataset_meta.overview_charts`. | Diagnostic charts đã built và web download được. Overview charts còn partial/not built. |
| L4 Reporting | Viết narrative report dễ hiểu từ evidence text-only, không bịa số liệu, không đọc/gọi chart. | Chỉ JSON findings/verdict/schema + raw top-k samples dạng số/chữ + report context compact. | `l4_report.md`, `guardrail_report.json`; fallback deterministic nếu LLM fail/không cấu hình. | Đã có deterministic guarded report + optional OpenAI single-call. Chưa có multi-agent routing, retry, substitution, tolerance đầy đủ. |
| Eval Harness | Đo được chất lượng inference/artifact/report thay vì chỉ smoke test. | Eval specs JSON + fixtures + pipeline outputs. | Eval result JSON: pass/fail, precision/recall/F1, artifact counts, guardrail status. | Đã có relationship eval và artifact eval. Cần severity eval, cross-table eval, L4 hallucination eval. |
| Web/Runtime | Chạy localhost theo job model thay vì block request lâu. | Upload files, schema optional, example specs, runtime config. | Job JSON: status/progress/error/files/report/links; downloadable artifacts. | Đã có background `JobRuntime`, upload limit, retry/cancel cơ bản. Cần worker process/timeout/cancel running job/cleanup policy. |

### Contract nguyên tắc cần giữ

- **L4 không nhận chart/image**. Chart chỉ đi tới end user qua artifact path.
- **L1 stats luôn tính trên bảng gốc**. Cross-table join không được dùng để tính lại mean/missing/duplicate của dimension tables.
- **Schema inference phải có evidence**. Không ghi FK/alias chỉ vì LLM nói đúng.
- **Verdict phải compact**. `dataset_verdict.json` nên chứa `summary` và `top_issues`, không duplicate toàn bộ detail JSON.
- **Eval output phải parseable JSON** để dùng được trong CI.

## Những đoạn đã có trong code

### Pipeline chính

- `run_pipeline.run(...)`: single-table pipeline.
- `run_pipeline.run_multi(...)`: multi-table pipeline, có schema validation/inference và profiling từng bảng.
- `_profile_data_quality(...)`: gom profiling, anomaly, missingness, findings, chart, severity cho từng bảng.
- `_multi_data_quality_bundle(...)`: đóng gói output multi-table vào `data_quality_findings.json`.

### Schema auto-discovery đã có

Không đúng khi nói hệ thống "chưa có khả năng tự suy luận liên kết nếu không có DBML/DDL". Code hiện đã có:

- `infer_parsed_schema(tables)`: suy luận schema nội bộ từ data.
- `_infer_primary_key(...)`: chấm điểm PK theo tên cột, concept table, uniqueness.
- `infer_relationships(...)`: suy luận quan hệ bằng value coverage, name score, unique parent bonus.
- `validate_schema_multi(data_paths, schema_path=None)`: khi không có schema file, tự load tables, infer schema, infer relationships.
- `RelationshipInfo`: lưu `explicit_fk` hoặc `inferred_fk`, `status`, `confidence`, `evidence`.
- `MISSING_RELATIONSHIP_METADATA`: ghi quan hệ có trong data nhưng thiếu trong schema.

Vì vậy không nên tạo thêm `src/engines/auto_schema.py` như một module song song. Nên tách `schema_engine.py` thành các module sâu hơn.

### L3.5 charts đã có

- `draw_diagnostic_scatter(...)`: sinh scatter diagnostic cho outlier.
- `attach_diagnostic_charts(...)`: gắn path PNG vào `AnomalyRecord.diagnostic_chart`.
- Web app đã list/download `.png` và trả `image/png`.
- `scripts/evaluate_pipeline_artifacts.py`: kiểm tra output có chart/export/guardrail.

### Guardrail/L4 đã có một phần

- `validate_narrative(...)`: kiểm tra số và backticked references có nằm trong evidence set không.
- `generate_l4_report(...)`: nếu `SMART_EDA_L4_PROVIDER=openai` thì gọi OpenAI, nếu fail hoặc guardrail fail thì fallback deterministic.
- `l4_report.md` và `guardrail_report.json` đã được pipeline xuất ra.

Chưa có:

- Multi-agent routing.
- Retry 3 lần theo từng agent.
- Tolerance matcher đầy đủ theo relative tolerance.
- Substitution kiểu `<SỐ LIỆU CHƯA XÁC MINH>`.
- Raw top-k samples batching mạnh cho LLM.

## Phản biện plan cũ của Claude

### 1. L4 chart placeholder là sai hướng

Plan cũ nói LLM sẽ viết placeholder như `[CHART_OUTLIER_AGE_SALARY]`, rồi Python đọc report của LLM để chèn chart.

Không nên làm vậy.

Lý do:

- Architecture đã chốt: **L4 không có Chart Architect, không Vision, không lệnh vẽ biểu đồ**.
- Chart là artifact phụ trợ ở L3.5, không phải input/output contract của L4.
- Nếu LLM được phép yêu cầu chart, LLM có thể yêu cầu chart không có evidence hoặc chart không tồn tại trong JSON.

Hướng đúng:

- Python sinh chart từ deterministic findings.
- JSON chứa `diagnostic_chart` hoặc `overview_charts`.
- Report chỉ có thể tham chiếu chart path đã có trong artifact manifest, không tự đặt lệnh mới.

### 2. `auto_schema.py` mới là module nông, trùng trách nhiệm

Plan cũ đề xuất tạo `src/engines/auto_schema.py`.

Không nên tạo ngay.

Lý do:

- `schema_engine.py` đã chứa auto-discovery, alias matching, PK inference, relationship inference.
- Thêm `auto_schema.py` song song sẽ tạo 2 nguồn sự thật cho relationship inference.
- Vấn đề thật là `schema_engine.py` đang quá lớn, không phải thiếu file.

Hướng đúng:

```text
src/engines/schema/
  analyzer.py              # public module interface
  policy.py                # load schema_inference_policy.json
  name_normalizer.py       # accents, tokens, synonyms, similarity
  key_inference.py         # PK/unique candidate scoring
  relationship_inference.py# FK candidate scoring and evidence
  validators.py            # type/null/unique/FK checks
```

External interface vẫn nên nhỏ:

```text
validate_schema_multi(data_paths, schema_path=None) -> SchemaEvaluationFindings
build_schema_findings(df, data_path, schema_path) -> SchemaEvaluationFindings
```

Đây là refactor để tăng locality, không đổi behavior.

### 3. Jaccard không phải metric chính cho FK

Plan cũ đề xuất Jaccard Index.

Với FK, metric đúng hơn là **containment/value coverage**:

```text
coverage = child_non_null_values_found_in_parent / child_non_null_values
```

Jaccard dễ sai vì parent dimension thường có nhiều key chưa được child table dùng. Ví dụ bảng `schools` có 1,000 trường nhưng `students` sample chỉ thuộc 20 trường; Jaccard thấp không có nghĩa là không có FK.

Code hiện đã dùng coverage, đây là hướng đúng. Có thể bổ sung Jaccard như evidence phụ, không nên thay coverage.

### 4. LLM semantic verification cho FK/fact table phải optional

Plan cũ đưa LLM vào "chốt hạ" FK và chọn fact table.

Không nên để LLM là source of truth ở L2.

Hướng đúng:

- Deterministic engine sinh candidate + confidence + evidence.
- Eval harness đo precision/recall.
- LLM chỉ được dùng ở chế độ optional để diễn giải hoặc gắn cờ "needs human confirmation".
- Nếu LLM xác nhận relationship, output phải ghi rõ `relationship_type="llm_assisted_inferred_fk"` hoặc evidence có trường riêng, không lẫn với deterministic confidence.

### 5. Dual-pass profiling là đúng, nhưng không được gọi là "hoàn hảo"

Plan cũ đúng khi phản đối join toàn bộ DB thành universal table. Single-table stats phải được tính trên từng bảng gốc.

Nhưng cross-table pass sau LEFT JOIN chỉ cho ra **transaction-weighted association** hoặc **fact-grain association**, không phải phân phối gốc của dimension. Ví dụ tuổi khách hàng sau join vào orders sẽ bị weighted theo số đơn hàng.

Output cross-table phải ghi rõ:

- `fact_table`
- `join_grain`
- `join_type`
- `base_row_count`
- `joined_row_count`
- `dropped_or_unmatched_count`
- `relationship_evidence`
- `interpretation_caveat`

Không được viết "hoàn hảo" trong report.

### 6. Full ydata mặc định cho mọi multi-table không phù hợp production

Plan cũ đề xuất tắt `minimal=True`, chạy full mode mặc định toàn bộ.

Code hiện:

- Single-table mặc định `profiling_minimal=False`.
- Web cho phép bật quick/minimal.
- Multi-table đang ép `profiling_minimal=True` cho từng bảng để tránh treo.

Hướng đúng là `ProfilingPolicy`, không hard-code một mode:

```text
mode = full | minimal | auto
auto rule:
  - small table: full
  - wide/large table: minimal plus selected extra metrics
  - over threshold: sample with explicit sample metadata
```

### 7. `issues_breakdown` đúng nhu cầu nhưng không nên duplicate full JSON

Plan cũ muốn nhúng toàn bộ `AnomalyRecord` và `IntegrityError` vào `dataset_verdict.json`.

Vấn đề:

- Trùng dữ liệu với `data_quality_findings.json` và `schema_evaluation_findings.json`.
- Làm `dataset_verdict.json` phình to, trái lý do ban đầu là tách 3 JSON để LLM không bị ngợp.
- Dễ tạo inconsistency nếu issue ở file detail khác issue ở verdict.

Hướng đúng:

- Thêm `top_issues` hoặc `blocking_issues` dạng compact.
- Mỗi item là `IssueSummary`, có reference tới source issue.
- Full detail vẫn ở file chuyên trách.

Ví dụ:

```json
{
  "verdict": "NOT_READY",
  "summary": {
    "total_issues": 3,
    "critical": 2,
    "high": 1,
    "warn": 0,
    "info": 0
  },
  "top_issues": [
    {
      "source": "data_quality_findings",
      "issue_type": "OUTLIER_ENSEMBLE",
      "effective_severity": "HIGH",
      "affected_table": null,
      "affected_column": null,
      "affected_count": 205,
      "rationale": "Phát hiện 205 dòng dị biệt.",
      "detail_ref": {
        "file": "data_quality_findings.json",
        "issue_index": 0
      }
    }
  ]
}
```

## Đối chiếu Superpowers Audit

Audit mới có giá trị ở phần red-team rủi ro, đặc biệt là cross-table, sampling, fan-out, và severity. Tuy nhiên không nên copy nguyên văn vì có phần giả định sai với architecture hiện tại. Bảng dưới đây là quyết định chính thức cho từng guardrail.

| Audit finding | Quyết định | Lý do | Hành động cần đưa vào plan |
| --- | --- | --- | --- |
| LLM sinh placeholder chart có rủi ro path traversal/prompt injection | Reject cơ chế placeholder, accept rủi ro path traversal nếu sau này có chart references | Architecture đã chốt L4 không sinh chart command. Không có placeholder thì không có `[CHART_../../../...]`. Rủi ro còn lại là report/UI không được render arbitrary path ngoài artifact manifest. | Giữ L4 text-only. Thêm `ArtifactManifest` và chỉ cho report tham chiếu artifact id đã tồn tại. |
| Chuyển PNG sang Plotly/ECharts JSON để hover/zoom | Worth exploring, không phải blocker | Interactive chart tốt cho UI, nhưng không thay đổi source-of-truth. PNG diagnostic hiện đã đủ cho L3.5 MVP. | Future: thêm `chart_spec.json` hoặc `*.plotly.json` song song PNG, render ở frontend từ allowlisted artifact id. |
| Jaccard dễ sai với surrogate keys | Accept, đã xử lý một phần | Code hiện không dùng Jaccard làm metric chính; đã dùng value coverage + name score + parent uniqueness. | Thêm eval false-positive: `users.id` vs `products.id` cùng range nhưng khác domain. |
| Cần phân biệt nhiều FK cùng trỏ một parent như `buyer_id`, `seller_id` -> `users.id` | Accept | Relationship inference phải cho phép nhiều child columns trỏ cùng parent key, không ép một alias duy nhất. | Thêm fixture/eval cho multi-role FK. Relationship evidence cần giữ role theo child column. |
| Fact score dễ chọn nhầm log table | Accept | Row count + timestamp + out-degree có thể chọn `api_request_logs` thay vì business fact. | Trong `CrossTableAnalyzer`, thêm log-table penalty, measure-column density, text/id ratio, table-name deny/soft patterns (`log`, `event`, `audit`). |
| Multi-fact schema không nên ép đúng một fact table | Accept | Retail có thể có `sales` và `inventory`; chọn một fact làm mất insight. | Cross-table output nên hỗ trợ `fact_candidates[]` và chạy top-k fact views có cap, không chỉ một universal fact. |
| Cardinality > 95% không được loại numeric/datetime continuous variables | Accept | Với numeric continuous, high cardinality là bình thường và thường là measure quan trọng. | Column filter phải xét dtype: high-cardinality string loại; numeric giữ; datetime giữ hoặc transform thành derived features nếu cần. |
| LEFT JOIN có fan-out/cartesian explosion nếu dimension key không unique | Accept, critical guardrail | Đây là rủi ro lớn nhất của cross-table analysis. | `SafeJoinPlan` phải assert parent key unique trước merge. Nếu không unique: không auto `first()` mặc định; ghi warning hoặc aggregate bằng policy explicit. |
| Auto-aggregation bằng `groupby().first()` để ép dimension 1-1 | Modify | `first()` có thể giấu lỗi dữ liệu và tạo kết quả ngẫu nhiên theo order. | Default không join khi parent key non-unique. Cho phép aggregation chỉ khi policy khai báo deterministic aggregation per column. |
| Correlation giả do NULL overlap sau LEFT JOIN | Accept | Nếu 90% join miss, correlation có thể phản ánh cùng missingness chứ không phải quan hệ thật. | Trước correlation, filter cột có join-null ratio > threshold, ví dụ 70%, và ghi `insufficient_join_coverage` warning. |
| Random sampling có thể bỏ sót minority/fraud class | Accept, nhưng cần đúng scope | Random sample 500k hiện có thể bỏ minority. Nhưng nếu không có label/category rõ, stratification chỉ là heuristic. | Thêm `SamplingPolicy`: random/stratified/none. Stratify theo low-cardinality categorical columns hoặc target column nếu user chỉ định. Ghi sample metadata. |
| Integrity check không được load full key columns vào RAM với file cực lớn | Accept, future production hardening | Hiện `pd.read_csv()` load full file trước rồi mới sample, không streaming thật. Với file rất lớn sẽ OOM. | Thêm `KeyColumnScanner` streaming cho CSV trước; dùng chunksize và set/hash sketch. Parquet có thể đọc selected columns. Excel/JSON streaming để sau. |
| Missingness không nên dùng dummy correlation; dùng Little's test + Logistic Regression | Already aligned | Code hiện đã dùng Little's MCAR test và Logistic Regression CV-AUC, không dùng dummy Pearson correlation. | Giữ hướng hiện tại; mở rộng eval missingness thay vì đổi thuật toán. |
| Dùng issue density thay vì số WARN tuyệt đối | Modify | Issue density tốt để scale theo dataset size, nhưng không được thay hard blockers. Một PK duplicate critical vẫn có thể NOT_READY dù density nhỏ. | Aggregator nên hybrid: hard blocker rules + issue density/risk score + top issues. |

### Guardrails cần đưa vào `CrossTableAnalyzer`

`CrossTableAnalyzer` chưa tồn tại trong code hiện tại. Khi build P3, các guardrail dưới đây là bắt buộc:

1. **Fact candidate scoring không chọn mù theo row count**
   - Tín hiệu cộng điểm: measure-column density, business-name concept, valid outgoing FK count, timestamp presence.
   - Tín hiệu trừ điểm: log/audit/event naming, quá nhiều text/id columns, append-only system events, bridge-table pattern.
   - Output phải lưu `fact_candidates[]`, không chỉ `selected_fact`.

2. **Multi-fact support**
   - Cho phép top-k fact views với cap.
   - Mỗi fact view có join plan và caveat riêng.
   - Không tạo universal table toàn DB.

3. **Type-aware column filter**
   - String/categorical high cardinality: loại khỏi association nếu `p_distinct` quá cao.
   - Numeric continuous: giữ.
   - Datetime: giữ nếu correlation method hỗ trợ hoặc derive `year/month/day/hour`.
   - ID-like numeric: loại khỏi measure set nếu name/type/evidence cho thấy là key.

4. **Safe join rule**
   - Parent side key phải unique.
   - Nếu parent key non-unique: emit `NON_UNIQUE_JOIN_KEY`, không join mặc định.
   - Aggregation chỉ chạy khi có policy rõ: `sum`, `mean`, `max`, `first_by_timestamp`, v.v.
   - Ghi `base_row_count`, `joined_row_count`; nếu row count tăng bất thường thì abort.

5. **Join coverage / null-overlap filter**
   - Ghi `match_rate` cho từng relationship.
   - Cột dimension có null ratio do join miss > 70% không được đưa vào correlation.
   - Emit warning `INSUFFICIENT_JOIN_COVERAGE`.

6. **Correlation result phải có caveat**
   - Ghi method: Pearson/Spearman/Cramer's V/Phik nếu có.
   - Ghi sample size thực tế sau khi drop/null handling.
   - Không diễn giải causal.
   - Không dùng kết quả cross-table để sửa L1 stats gốc.

### Guardrails cần đưa vào Ingestion/Sampling

Code hiện có `sample_if_large(df, threshold=500_000)` nhưng sampling xảy ra **sau khi đã load full DataFrame**. Điều này đủ cho demo/local file vừa, nhưng chưa đủ production với file cực lớn.

Plan mới:

- Tạo `SamplingPolicy` có mode `none`, `random`, `stratified`, `auto`.
- Ghi `sample_metadata` vào `RunMetadata` hoặc `DatasetMeta`: original rows nếu biết, sampled rows, seed, method, stratify columns.
- Stratified sampling chỉ áp dụng khi có low-cardinality categorical column hoặc user-provided target column.
- Tạo streaming reader cho CSV key scans:
  - đọc `chunksize`.
  - chỉ đọc key columns khi kiểm tra FK/PK.
  - dùng set khi vừa RAM, dùng hash/sketch/temp sqlite khi lớn.
- Không claim "RAM không bao giờ vượt 1GB" nếu chưa có measurement; dùng target ngân sách RAM và test benchmark.

### Guardrails cần đưa vào Severity

Code hiện đã đúng hơn audit ở missingness: đang dùng Little's test + Logistic Regression, không dùng dummy correlation. Gap thật nằm ở aggregator.

Plan mới:

- `DatasetVerdict` thêm `top_issues` compact.
- Aggregator thêm `risk_score` hoặc `issue_density` nhưng không thay thế hard blockers.
- Hard blocker examples:
  - PK null/duplicate.
  - orphan FK critical.
  - severe missingness trên critical/user-marked columns.
- Density examples:
  - weighted issue points / cells hoặc / columns.
  - severity weights: INFO=0.1, WARN=1, HIGH=5, CRITICAL=20.
- Output phải ghi rõ `calibration_status="heuristic_v0_not_benchmark_calibrated"` cho đến khi có eval calibration.

## Architecture đề xuất sau khi sửa

### Module sâu cần có

#### 1. `PipelineRunner`

Mục tiêu: gom luồng pipeline vào một module có interface nhỏ để CLI/Web không gọi trực tiếp nhiều hàm engine.

Leverage:

- Web app, CLI, eval script dùng chung một interface.
- Dễ thêm progress hooks, timeout, artifact manifest.
- Dễ test end-to-end qua một seam.

#### 2. `FindingBundle v1`

Mục tiêu: chuẩn hóa output trung gian trước khi write file.

Nên chứa:

- `data_quality_findings`
- `schema_evaluation_findings`
- `dataset_verdict`
- `artifact_manifest`
- `run_metadata`

Leverage:

- Reporters, guardrail, eval không phải tự tìm file rải rác.
- Dễ version contract.
- Dễ migrate JSON schema.

#### 3. `SchemaAnalyzer`

Mục tiêu: tách `schema_engine.py` thành các module có locality.

Các module nội bộ:

- `SchemaSource`: parse DBML/SQL hoặc inferred schema.
- `NameNormalizer`: accents, Vietnamese/English synonyms, token similarity.
- `KeyInferencePolicy`: PK/unique candidate scoring.
- `RelationshipInferencer`: FK candidates, confidence, evidence.
- `SchemaValidator`: missing columns, aliases, type mismatch, PK/FK checks.

External interface vẫn giữ nhỏ để không làm caller phức tạp.

#### 4. `CrossTableAnalyzer`

Mục tiêu: thêm dual-pass cross-table insight mà không làm sai single-table profiling.

Output riêng:

```text
cross_table_findings.json
```

Nội dung:

- fact table selection evidence
- join plan
- denormalized sample metadata
- cross-table associations
- caveats

Không nhét cross-table correlation trực tiếp vào `data_quality_findings.json` nếu chưa có schema rõ, vì đây là insight phân tích, không hẳn là data quality issue.

#### 5. `ReportContextBuilder`

Mục tiêu: thay vì L4 tự đọc 3 JSON lớn, Python build compact evidence payload cho L4.

Nên chứa:

- top issues
- verdict rationale
- relationship summaries
- artifact refs đã tồn tại
- raw top-k samples dạng số/chữ

Guardrail dùng cùng payload này để build allowed-set.

## Revised implementation plan

### P0 - Không làm các việc này

- Không cho LLM tạo chart placeholder.
- Không gửi chart/image vào L4.
- Không render chart/report từ arbitrary file path; chỉ dùng artifact id/path trong `ArtifactManifest`.
- Không tạo `auto_schema.py` song song với `schema_engine.py`.
- Không thay coverage bằng Jaccard cho FK inference.
- Không ép full ydata cho toàn bộ multi-table mặc định.
- Không để LLM là source of truth cho FK hoặc fact table.
- Không auto `groupby().first()` để sửa non-unique dimension key nếu không có aggregation policy rõ.

### P1 - Làm giàu `dataset_verdict.json`

Mục tiêu: end user và L4 hiểu verdict vì sao mà không phải đọc ngược toàn bộ detail.

Tasks:

- Thêm model `IssueSummary`.
- Thêm field `top_issues` hoặc `blocking_issues` vào `DatasetVerdict`.
- `aggregator.aggregate(...)` nhận `dq_findings` và `integrity_errors`, sort theo effective severity, affected count, confidence.
- Thêm `risk_score` hoặc `issue_density` dạng heuristic, nhưng giữ hard blocker rules cho lỗi nghiêm trọng.
- Giữ full issue detail ở `data_quality_findings.json` và `schema_evaluation_findings.json`.
- Update guardrail evidence builder để đọc số/reference từ `top_issues`.
- Ghi rõ calibration status từ `calibrator_table.json`.
- Update tests cho verdict JSON.

Definition of done:

- `dataset_verdict.json` vẫn nhỏ.
- Không duplicate `top_10_samples`.
- Critical integrity blockers vẫn có thể đưa verdict về `NOT_READY` dù issue density thấp.
- L4 deterministic report dùng được `top_issues`.
- Full tests pass.

### P2 - Refactor `schema_engine.py` thành `SchemaAnalyzer`

Mục tiêu: tăng locality, giảm rủi ro khi thêm relationship logic.

Tasks:

- Move policy loading sang `schema/policy.py`.
- Move name normalization/synonym sang `schema/name_normalizer.py`.
- Move PK scoring sang `schema/key_inference.py`.
- Move relationship scoring sang `schema/relationship_inference.py`.
- Move validators sang `schema/validators.py`.
- Giữ compatibility wrapper ở `src/engines/schema_engine.py`.
- Không đổi JSON output trong phase này.

Definition of done:

- `scripts/evaluate_schema_relationships.py` cho cùng kết quả hoặc tốt hơn.
- Tests schema hiện tại pass.
- Public functions cũ vẫn hoạt động.

### P3 - Thêm cross-table analysis deterministic

Mục tiêu: có insight chéo bảng nhưng không phá single-table statistics.

Tasks:

- Tạo `src/engines/cross_table.py`.
- Chọn fact candidates deterministic bằng score:
  - row count
  - timestamp columns
  - out-degree/in-degree
  - bridge-table penalty
  - log/audit/event table penalty
  - measure-column density
  - text/id column ratio
  - table-name concept score
- Hỗ trợ top-k fact views thay vì ép một fact table duy nhất.
- Tạo join plan từ `SchemaEvaluationFindings.relationships`.
- LEFT JOIN theo relationship đã explicit/inferred đủ confidence.
- Safe join rule:
  - parent join key phải unique.
  - nếu non-unique thì emit warning và không join mặc định.
  - chỉ aggregate khi có policy rõ cho từng cột.
- Lọc cột theo cardinality, dtype, uniqueness, max columns:
  - high-cardinality string/categorical: drop.
  - numeric continuous: keep.
  - datetime: keep hoặc derive time features.
  - ID-like numeric: drop khỏi measure set.
- Filter cột dimension có join-null ratio quá cao, ví dụ > 70%.
- Tính association/correlation trên temp table có cap.
- Ghi `cross_table_findings.json`.

Definition of done:

- Output có caveat rõ về fact grain.
- Output có `fact_candidates`, `join_plan`, `match_rate`, `base_row_count`, `joined_row_count`.
- Fan-out làm tăng row count phải bị abort hoặc warning rõ, không âm thầm chạy tiếp.
- Không dùng joined table để tính lại mean/missing của bảng gốc.
- Có fixture multi-table e-commerce nhỏ và expected output.

### P4 - Mở rộng eval process

Mục tiêu: architecture mới phải đo được, không chỉ chạy được.

Tasks:

- Mở rộng `examples/evaluation/schema_relationship_eval.json`.
- Thêm false-positive cases:
  - same IDs nhưng khác domain.
  - surrogate key cùng range như `users.id` và `products.id`.
  - multi-role FK như `buyer_id` và `seller_id` cùng trỏ về `users.id`.
  - bridge table.
  - parent dimension lớn, child sample nhỏ.
  - string/numeric ID mismatch.
- Thêm `cross_table_eval.json`.
- Thêm eval fan-out join, log-table fact selection, multi-fact schema, high-null join.
- Thêm `severity_eval.json` hoặc benchmark calibration fixture.
- Thêm L4 hallucination eval:
  - allowed number.
  - disallowed number.
  - unknown column.
  - percent rounding.

Definition of done:

- Eval script trả JSON parseable.
- Có precision/recall/F1 cho relationship.
- CI có thể fail nếu artifact contract hoặc relationship eval tụt dưới threshold.

### P5 - L4 real LLM + guardrail hoàn chỉnh

Mục tiêu: từ deterministic guarded report lên guarded LLM report thật.

Tasks:

- Tạo `ReportContextBuilder`.
- Batching theo issue groups.
- Optional OpenAI provider qua adapter riêng.
- Guardrail:
  - number allowed-set.
  - column/table/reference allowed-set.
  - tolerance config.
  - retry policy.
  - fallback/substitution.
- Không cho LLM yêu cầu chart mới.

Definition of done:

- Không có `OPENAI_API_KEY` vẫn chạy deterministic.
- Có `OPENAI_API_KEY` thì LLM report pass guardrail hoặc fallback.
- Guardrail report ghi rõ provider, retry count, violations.

### P6 - Production hardening cho localhost app

Hiện đã có `JobRuntime`, background jobs, progress đơn giản, upload limit. Cần tiếp:

- Queue bền vững hơn nếu process restart.
- Worker process riêng cho job nặng.
- Timeout per job.
- Cancel running job an toàn.
- Job cleanup policy.
- Structured error code cho UI.
- Artifact manifest thay vì scan output folder thủ công.
- `SamplingPolicy` và `RunMetadata` cho file lớn.
- Streaming key scan cho CSV integrity checks bằng `chunksize`.
- Memory-budget benchmark cho ingestion/schema validation.

## Roadmap đề xuất

Thứ tự nên làm:

1. `IssueSummary` + `top_issues` trong verdict.
2. Refactor `schema_engine.py` thành `SchemaAnalyzer` mà không đổi behavior.
3. Mở rộng relationship eval set.
4. Thêm `cross_table_findings.json`.
5. Thêm `ReportContextBuilder`.
6. Hoàn thiện L4 provider/guardrail.
7. Hardening web runtime.

## Kết luận

Repo hiện tại đã đạt tốt cho deterministic MVP và đã có nhiều phần mà plan cũ tưởng là chưa có: schema inference, multi-table profiling từng bảng, chart artifact, web background jobs, guardrail narrative, eval artifact.

Plan đúng ở nhu cầu phát triển tiếp: verdict cần sâu hơn, cross-table cần dual-pass, L4 cần guardrail thật hơn. Nhưng implementation phải đi qua refactor module hiện có và eval contract, không nên thêm module song song hoặc để LLM quyết định thay deterministic engine.
