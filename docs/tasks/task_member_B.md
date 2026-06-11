# Task: Member B — LLM + Integration (Cross-table + Multi-Agent + Pipeline)

## Bạn là ai
Bạn là AI coding assistant đang implement phần **LLM Integration** cho dự án Smart EDA. Bạn **CHỈ SỬA các file được liệt kê bên dưới**. Không sửa file nào khác.

## Context dự án
- **SSOT**: Đọc `docs/ARCHITECT (8).md` — tài liệu kiến trúc duy nhất
- **Pipeline hiện tại**: `run_pipeline.py` chạy L0→L1→L2→L2.5→L3→L4 tuần tự
- **Models đã cập nhật**: `src/ontology/models.py` đã có sẵn `IssueCluster`, `DispatchResult`, `AnalystOutput`, `EditorOutput`, `MultiAgentResult`, `CorrelationPairPlan`, `LlmCorrelationPlan` — import trực tiếp, KHÔNG tạo lại
- **Stub files đã tạo**: `reporting/dispatcher.py`, `reporting/html_merger.py` — bạn implement logic vào đây

## Files bạn SỞ HỮU (chỉ sửa các file này)

### File cần IMPLEMENT (stub đã tạo, thay `raise NotImplementedError`):
1. `src/reporting/dispatcher.py` — L4 Dispatcher (Python, 0 LLM)
2. `src/reporting/html_merger.py` — merge multi-agent + ydata → Tabbed HTML

### File cần REWRITE:
3. `src/reporting/l4_report.py` — thay single-call LLM bằng multi-agent pipeline

### File cần EXTEND:
4. `src/guardrail/narrative.py` — thêm per-agent guardrail logic

### File cần REFACTOR:
5. `src/engines/cross_table_engine.py` — thêm LLM-guided Phase 1+2 (giữ nguyên hàm `run_cross_table_analysis` hiện tại, thêm hàm mới)

### File cần UPDATE (integration cuối cùng):
6. `run_pipeline.py` — gọi multi-agent pipeline, sinh smart_eda_report.html

### File KHÔNG ĐƯỢC SỬA:
- `src/ontology/models.py` (locked)
- `src/severity/*` (của Member A)
- `src/ontology/*` (của Member A, trừ import)
- `src/config/*` (của Member A)
- `src/engines/graph_engine.py` (của Member A)
- `src/webapp/*` (của Member C)
- `src/reporting/templates/*` (của Member C)
- `src/engines/profiling_engine.py` (của Member C)

## Yêu cầu chi tiết

### Task B1: Dispatcher — implement
**File**: `src/reporting/dispatcher.py` (stub đã tạo)
**Logic** (ARCHITECT §5.9(a)):
```python
def dispatch(anomalies, integrity_errors=None, top_n=5):
    # 1. Gom tất cả findings vào 1 list
    all_issues = []
    for a in anomalies:
        effective = a.compound_severity or a.severity
        all_issues.append({"record": a, "effective_severity": effective, "source": "dq"})
    if integrity_errors:
        for e in integrity_errors:
            effective = e.compound_severity or e.severity
            all_issues.append({"record": e, "effective_severity": effective, "source": "schema"})
    
    # 2. Lọc >= WARN (bỏ INFO)
    filtered = [i for i in all_issues if sev_rank(i["effective_severity"]) >= sev_rank(Severity.WARN)]
    
    # 3. Group by issue_type
    groups = defaultdict(list)
    for item in filtered:
        groups[item["record"].issue_type].append(item)
    
    # 4. Tạo IssueCluster cho mỗi group
    clusters = []
    for issue_type, items in groups.items():
        records = [i["record"] for i in items]
        affected_cols = list(set(
            r.affected_column for r in records 
            if hasattr(r, 'affected_column') and r.affected_column
        ))
        max_sev = max(items, key=lambda x: sev_rank(x["effective_severity"]))["effective_severity"]
        
        # json_slice: compact cho Analyst (~500 tokens)
        json_slice = {
            "issue_type": issue_type,
            "count": len(records),
            "max_severity": str(max_sev),
            "affected_columns": affected_cols[:10],
            "samples": [r.model_dump(include={"description","severity","affected_column","affected_count","affected_percent"}) for r in records[:5]],
        }
        clusters.append(IssueCluster(
            issue_type=issue_type,
            issues=[r.model_dump() for r in records],
            affected_columns=affected_cols,
            max_severity=str(max_sev),
            json_slice=json_slice,
        ))
    
    # 5. Rank: CRITICAL > HIGH > WARN, phụ = len(affected_columns)
    clusters.sort(key=lambda c: (sev_rank_str(c.max_severity), len(c.affected_columns)), reverse=True)
    
    remainder = sum(len(c.issues) for c in clusters[top_n:])
    return DispatchResult(top_clusters=clusters[:top_n], remainder_count=remainder)
```

### Task B2: L4 Multi-Agent — rewrite l4_report.py
**File**: `src/reporting/l4_report.py`
**Kiến trúc** (ARCHITECT §5.9):

```
Dispatcher (Python) → N×Analyst (gpt-4o-mini, parallel) → Editor (gpt-4o)
```

**Pseudocode chính**:
```python
import asyncio
import os
from openai import AsyncOpenAI

ANALYST_MODEL = os.getenv("SMART_EDA_ANALYST_MODEL", "gpt-4o-mini")
EDITOR_MODEL = os.getenv("SMART_EDA_EDITOR_MODEL", "gpt-4o")

async def run_multi_agent_l4(
    findings: DataQualityFindings,
    verdict: DatasetVerdict,
    schema: SchemaEvaluationFindings | None = None,
    cross_table: CrossTableAnalysis | None = None,
) -> tuple[MultiAgentResult, GuardrailReport]:
    """
    Main entry point cho L4 multi-agent pipeline.
    
    1. Dispatch (Python, 0 LLM)
    2. Fan-out: N×Analyst (parallel, mini model)
    3. Fan-in: Editor (sequential, strong model)
    4. Appendix (Python render)
    5. Return MultiAgentResult
    """
    # 1. Dispatch
    dispatch_result = dispatch(findings.anomalies, 
                               schema.integrity_errors if schema else None)
    
    # 2. Analyst fan-out (parallel)
    analyst_tasks = [
        _call_analyst(cluster, findings, verdict)
        for cluster in dispatch_result.top_clusters
    ]
    analyst_results = await asyncio.gather(*analyst_tasks, return_exceptions=True)
    
    # 3. Handle analyst failures (graceful degradation)
    valid_analysts = []
    for i, result in enumerate(analyst_results):
        if isinstance(result, Exception):
            # Fallback: render deterministic table cho cluster này
            cluster = dispatch_result.top_clusters[i]
            valid_analysts.append(AnalystOutput(
                cluster_type=cluster.issue_type,
                markdown=_render_deterministic_section(cluster),
                guardrail_passed=False,
            ))
        else:
            valid_analysts.append(result)
    
    # 4. Editor (sequential, strong model)
    editor_output = await _call_editor(
        valid_analysts, verdict, cross_table
    )
    
    # 5. Appendix (Python render, 0 LLM)
    appendix_html = _render_appendix(dispatch_result.remainder_count, findings)
    
    return MultiAgentResult(
        analyst_outputs=valid_analysts,
        editor_output=editor_output,
        appendix_html=appendix_html,
        used_fallback=any(not a.guardrail_passed for a in valid_analysts),
    )

async def _call_analyst(cluster: IssueCluster, findings, verdict) -> AnalystOutput:
    """
    Gọi 1 Analyst agent (mini model).
    System prompt:
    - Vai trò: Data Quality Analyst chuyên {issue_type}
    - Input: json_slice (compact)
    - Output: Markdown ~200-400 tokens
    - Quy tắc: CHỈ dùng số từ evidence, KHÔNG bịa, KHÔNG nói "causes"
    
    Guardrail per-agent: verify numbers ⊆ evidence
    Retry tối đa 3 lần.
    """
    # TODO: implement

async def _call_editor(analysts, verdict, cross_table) -> EditorOutput:
    """
    Gọi Editor agent (strong model).
    System prompt:
    - Vai trò: Senior Data Analyst tổng hợp
    - Input: analyst markdowns + verdict + cross_table (nếu có)
    - Output: EditorOutput (executive_summary + verdict_explanation + 
              cross_table_evaluation + priority_ranking)
    - Quy tắc: tổng hợp, không lặp lại analyst, xếp hạng ưu tiên
    
    Guardrail: verify final output
    Retry tối đa 3 lần.
    Fallback: nếu Editor fail → render deterministic tất cả.
    """
    # TODO: implement

def _render_deterministic_section(cluster: IssueCluster) -> str:
    """Fallback: render 1 cluster thành Markdown table khi Analyst fail."""
    # TODO: implement

def _render_appendix(remainder_count: int, findings) -> str:
    """Python render HTML table cho findings ngoài top 5."""
    # TODO: implement
```

**Quan trọng — System Prompts:**

Analyst system prompt phải có:
```
Bạn là Data Quality Analyst chuyên phân tích lỗi loại "{issue_type}".
Phân tích DỰA TRÊN evidence sau (JSON). KHÔNG BỊA SỐ.
Chỉ dùng số xuất hiện trong evidence. Nếu không có số, nói "không đủ dữ liệu".
KHÔNG dùng từ "causes", "drives", "leads to" — chỉ dùng "associated with", "correlated with".
Viết Markdown ~200-400 tokens, có: Tóm tắt → Severity → Cột bị ảnh hưởng → Khuyến nghị.
```

Editor system prompt phải có:
```
Bạn là Senior Data Analyst tổng hợp báo cáo chất lượng dữ liệu.
Input: N phân tích từ các analyst + verdict + cross-table (nếu có).
Output JSON:
{
  "executive_summary": "Tóm tắt 3-5 câu, bao quát toàn bộ",
  "verdict_explanation": "Giải thích tại sao {verdict}",
  "cross_table_evaluation": "Đánh giá tương quan chéo (null nếu single-table)",
  "priority_ranking": "Xếp hạng nhóm lỗi cần xử lý trước"
}
KHÔNG lặp lại nội dung analyst. KHÔNG BỊA SỐ.
```

### Task B3: Guardrail per-agent — extend
**File**: `src/guardrail/narrative.py`
**Cần thêm**: Hàm verify cho Analyst output và Editor output riêng (hiện tại chỉ có 1 hàm chung)
```python
def verify_analyst_output(markdown: str, evidence: dict) -> tuple[bool, list[str]]:
    """Verify 1 analyst output: numbers ⊆ evidence.numbers."""

def verify_editor_output(editor_json: dict, analyst_markdowns: list[str], verdict: dict) -> tuple[bool, list[str]]:
    """Verify editor output: numbers consistent, verdict match."""
```
**Tolerance** (ARCHITECT §Mục 10): integer=exact, decimal=±0.0001, relative=±0.1%

### Task B4: Cross-table LLM-guided — thêm Phase 1
**File**: `src/engines/cross_table_engine.py`
**QUAN TRỌNG**: Giữ nguyên hàm `run_cross_table_analysis()` hiện tại. Thêm hàm MỚI:
```python
async def llm_plan_correlations(tables_meta, relationships) -> LlmCorrelationPlan:
    """
    Phase 1: LLM chọn cặp cột cần tính correlation + aggregate method.
    Input: schema + 10 dòng mẫu (KHÔNG gửi data thô)
    Output: LlmCorrelationPlan (validated)
    Validation: table_exists, column_exists, agg_valid, relationship_exists
    Fallback: LLM lỗi → return empty plan
    """

def validate_llm_plan(plan: dict, tables_meta: dict, relationships: list) -> LlmCorrelationPlan:
    """100% deterministic validation. Loại cặp không hợp lệ."""

def compute_planned_correlations(tables, plan: LlmCorrelationPlan) -> list[CrossTableCorrelation]:
    """Phase 2: Deterministic compute dựa trên plan đã validate."""
```

### Task B5: HTML Merger — implement
**File**: `src/reporting/html_merger.py` (stub đã tạo)
**Logic**:
```python
def merge_to_tabbed_html(multi_agent_result, verdict, ydata_html, ...):
    template = _load_template()  # Load C's template
    css = _load_css()
    js = _load_js()
    
    # Build AI analysis content from multi-agent results
    ai_content = ""
    if multi_agent_result.editor_output:
        ai_content += markdown_to_html(multi_agent_result.editor_output.executive_summary)
        # ... verdict_explanation, priority_ranking, cross_table_evaluation
    for analyst in multi_agent_result.analyst_outputs:
        ai_content += f"<section class='analyst-section'><h3>{analyst.cluster_type}</h3>"
        ai_content += markdown_to_html(analyst.markdown)
        ai_content += "</section>"
    ai_content += multi_agent_result.appendix_html
    
    # Escape ydata HTML cho iframe srcdoc
    ydata_escaped = html.escape(ydata_html)
    
    # Verdict info
    verdict_icons = {"READY": "✅", "WARN": "⚠️", "NOT_READY": "❌"}
    
    return template.format(
        verdict_class=verdict.verdict.value,
        verdict_value=verdict.verdict.value,
        verdict_icon=verdict_icons.get(verdict.verdict.value, "❓"),
        verdict_rationale=verdict.verdict_rationale,
        file_name=verdict.dataset_meta.file_name,
        n=verdict.dataset_meta.n,
        n_var=verdict.dataset_meta.n_var,
        p_cells_missing=f"{verdict.dataset_meta.p_cells_missing:.1%}",
        ai_analysis_content=ai_content,
        ydata_escaped=ydata_escaped,
        guardrail_status=guardrail_status,
        provider="multi-agent" if not multi_agent_result.used_fallback else "deterministic",
        model_info=model_info,
        timestamp=timestamp or datetime.now().isoformat(),
        css_content=css,
        js_content=js,
    )
```

**Markdown to HTML**: Dùng thư viện `markdown` (`pip install markdown`) hoặc tự viết regex đơn giản cho heading/bold/list.

### Task B6: Pipeline integration — update run_pipeline.py
**File**: `run_pipeline.py`
**Cần sửa ở hàm `run()` (single-table):**
```python
# Sau khi có verdict, thay thế:
#   l4_report, guardrail_report = generate_l4_report(findings, verdict, schema)
# Bằng:
import asyncio
from reporting.l4_report import run_multi_agent_l4
from reporting.html_merger import merge_to_tabbed_html
from engines.profiling_engine import run_profiling_html

# L4: Multi-Agent
multi_agent_result, guardrail_report = asyncio.run(
    run_multi_agent_l4(findings, verdict, schema)
)

# ydata HTML
ydata_html = run_profiling_html(df)  # C sẽ implement hàm này

# Merge → Tabbed HTML
smart_eda_html = merge_to_tabbed_html(multi_agent_result, verdict, ydata_html)
smart_eda_path = out / "smart_eda_report.html"
smart_eda_path.write_text(smart_eda_html, encoding="utf-8")

# Giữ l4_report.md cho backward compat
l4_report_md = multi_agent_result.editor_output.executive_summary if multi_agent_result.editor_output else ""
l4_report_path = out / "l4_report.md"
l4_report_path.write_text(l4_report_md, encoding="utf-8")
```

**Tương tự cho `run_multi()`** — thêm cross_table vào multi-agent call.

**LƯU Ý**: Nếu `run_profiling_html()` chưa tồn tại (C chưa code xong), dùng fallback:
```python
def _safe_ydata_html(df):
    try:
        from engines.profiling_engine import run_profiling_html
        return run_profiling_html(df)
    except (ImportError, AttributeError):
        return "<p>ydata profiling report not available</p>"
```

## Dependencies ngoài cần cài
```bash
pip install markdown openai
```
- `openai` cho async LLM calls (`AsyncOpenAI`)
- `markdown` cho Markdown→HTML conversion trong html_merger

## Test
Sau khi code xong:
```bash
# Set API key
set OPENAI_API_KEY=sk-...

# Test single
python run_pipeline.py examples/sample_datasets/titanic/train.csv output_test

# Verify
# - output_test/smart_eda_report.html tồn tại và mở được trong browser
# - HTML có 2 tab, tab AI Analysis có nội dung
# - l4_report.md vẫn sinh ra (backward compat)
# - guardrail_report.json có per-agent details
```

## Test KHÔNG CÓ API key (fallback):
```bash
set SMART_EDA_L4_PROVIDER=deterministic
python run_pipeline.py examples/sample_datasets/titanic/train.csv output_test
```
→ smart_eda_report.html vẫn sinh ra, nhưng dùng deterministic fallback.

## Lưu ý quan trọng
- **GIỮ NGUYÊN `generate_l4_report()` function signature** — webapp đang gọi nó. Wrap multi-agent bên trong.
- **KHÔNG sửa `models.py`** — đã locked
- **KHÔNG sửa `src/severity/*`, `src/ontology/*`, `src/webapp/*`**
- Mọi LLM call phải có fallback deterministic
- `html_merger.py` đã có `_load_template()` với fallback — nếu C chưa tạo template thì dùng fallback
- Template placeholders PHẢI khớp danh sách `TEMPLATE_PLACEHOLDERS` trong `html_merger.py`
