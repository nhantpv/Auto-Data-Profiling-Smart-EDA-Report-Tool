# Task: Member C — Frontend + UI + Output Template

## Bạn là ai
Bạn là AI coding assistant đang implement phần **Frontend + Output** cho dự án Smart EDA. Bạn **CHỈ SỬA các file được liệt kê bên dưới**. Không sửa file nào khác.

## Context dự án
- **SSOT**: Đọc `docs/ARCHITECT (8).md` — tài liệu kiến trúc duy nhất
- **Webapp hiện tại**: FastAPI backend (`src/webapp/app.py`) + SPA frontend (`src/webapp/static/`)
- **Pipeline**: `run_pipeline.py` chạy pipeline → sinh output vào `output/` folder
- **Template stubs đã tạo**: `src/reporting/templates/` có `report_template.html`, `styles.css`, `tab.js` — bạn thiết kế lại hoàn toàn
- **Models đã cập nhật**: `src/ontology/models.py` có `MultiAgentResult`, `DatasetVerdict` etc.

## Files bạn SỞ HỮU (chỉ sửa các file này)

### File cần REDESIGN (stub đã tạo, bạn redesign hoàn toàn):
1. `src/reporting/templates/report_template.html` — HTML template cho smart_eda_report
2. `src/reporting/templates/styles.css` — CSS design system
3. `src/reporting/templates/tab.js` — Tab switching + interactions

### File cần MODIFY:
4. `src/engines/profiling_engine.py` — thêm hàm `run_profiling_html()`
5. `src/webapp/app.py` — thêm endpoints mới
6. `src/webapp/static/app.js` — UI nâng cấp
7. `src/webapp/static/styles.css` — webapp styles
8. `src/webapp/static/index.html` — webapp layout

### File KHÔNG ĐƯỢC SỬA:
- `src/ontology/models.py` (locked)
- `src/severity/*` (của Member A)
- `src/ontology/*` (của Member A)
- `src/reporting/dispatcher.py` (của Member B)
- `src/reporting/l4_report.py` (của Member B)
- `src/reporting/html_merger.py` (của Member B)
- `src/guardrail/*` (của Member B)
- `src/engines/cross_table_engine.py` (của Member B)
- `run_pipeline.py` (của Member B)

## Yêu cầu chi tiết

### Task C1: HTML Template — Thiết kế UI/UX đẹp
**File**: `src/reporting/templates/report_template.html`

Template này là output cuối cùng user sẽ thấy. Phải **đẹp, chuyên nghiệp, dễ đọc**.

**Cấu trúc bắt buộc** (ARCHITECT §5.8):
```
┌────────────────────────────────────────────────────────┐
│  HEADER: Verdict Banner                                │
│  ┌──────────────────────────────────────────────────┐  │
│  │ ✅/⚠️/❌ READY / WARN / NOT_READY               │  │
│  │ Rationale text                                   │  │
│  │ file.csv · 1000 rows · 12 cols · Missing: 5.2%  │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  TAB BAR: [🤖 AI Analysis]  [📊 Statistical Details]  │
│  ─────────────────────────────────────────────────────  │
│                                                        │
│  TAB 1 — AI Analysis:                                  │
│  ┌──────────────────────────────────────────────────┐  │
│  │ Executive Summary (từ Editor Agent)              │  │
│  │ ────────────────────────────────                 │  │
│  │ Verdict Explanation                              │  │
│  │ ────────────────────────────────                 │  │
│  │ Issue Group 1: Missing Values (từ Analyst #1)    │  │
│  │ Issue Group 2: Outliers (từ Analyst #2)          │  │
│  │ ...                                              │  │
│  │ Cross-table Insights (nếu multi-table)           │  │
│  │ ────────────────────────────────                 │  │
│  │ Priority Ranking                                 │  │
│  │ ────────────────────────────────                 │  │
│  │ Appendix (bảng findings còn lại)                 │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  TAB 2 — Statistical Details:                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │ <iframe srcdoc="ydata HTML">                     │  │
│  │   ydata interactive charts                       │  │
│  │   per-column stats                               │  │
│  │   correlation matrix                             │  │
│  └──────────────────────────────────────────────────┘  │
│                                                        │
│  FOOTER: Guardrail status · Model info · Timestamp     │
└────────────────────────────────────────────────────────┘
```

**Placeholders bắt buộc** (Member B sẽ fill khi merge):
```
{verdict_class}        → READY | WARN | NOT_READY (dùng cho CSS class)
{verdict_value}        → READY | WARN | NOT_READY
{verdict_icon}         → ✅ | ⚠️ | ❌
{verdict_rationale}    → string mô tả
{file_name}            → tên file
{n}                    → số dòng
{n_var}                → số cột
{p_cells_missing}      → "5.2%"
{ai_analysis_content}  → HTML string (Editor + Analysts + Appendix)
{ydata_escaped}        → HTML-escaped ydata string (cho iframe srcdoc)
{guardrail_status}     → "passed" | "partial" | "failed"
{provider}             → "multi-agent" | "deterministic"
{model_info}           → "Analyst: gpt-4o-mini, Editor: gpt-4o"
{timestamp}            → ISO datetime
{css_content}          → nội dung styles.css (inline)
{js_content}           → nội dung tab.js (inline)
```

**YÊU CẦU THIẾT KẾ:**
- Font: Google Fonts (Inter hoặc Outfit) — nhúng qua `<link>` hoặc base64
- Responsive: mobile-friendly
- Dark mode: `@media (prefers-color-scheme: dark)`
- Verdict banner: gradient background theo severity
- Tab switching: smooth, không reload
- Sections: có spacing, border, heading rõ ràng
- Severity badges: color-coded (CRITICAL=đỏ, HIGH=cam, WARN=vàng, INFO=xanh)
- File này phải là **self-contained** (CSS inline, JS inline) vì sẽ gửi file .html đơn lẻ

### Task C2: CSS Design System
**File**: `src/reporting/templates/styles.css`

Thiết kế CSS hoàn chỉnh cho report. Bao gồm:
- **Color palette**: Harmonious, không dùng màu gốc (plain red/blue)
- **Typography**: Inter/Outfit font, proper heading hierarchy
- **Verdict banner**: Gradient backgrounds
  - READY: xanh lá (#10b981 → #059669)
  - WARN: vàng/cam (#f59e0b → #d97706)
  - NOT_READY: đỏ (#ef4444 → #dc2626)
- **Tab system**: Active state, hover, transition
- **Severity badges**: Inline badges màu
- **Tables**: Striped, border, responsive
- **Code blocks**: Syntax highlighting feel
- **Dark mode**: Full dark mode support
- **Print**: `@media print` styles cho in ấn

### Task C3: Tab JS
**File**: `src/reporting/templates/tab.js`
- Tab switching không reload page
- Active state management
- Keyboard navigation (← → arrows)
- URL hash sync (#ai, #stats) để bookmark được
- Smooth scroll to top khi switch tab

### Task C4: ydata HTML generation
**File**: `src/engines/profiling_engine.py`

Hiện tại file này có hàm `run_profiling()` trả về dict. Cần thêm:

```python
def run_profiling_html(df: pd.DataFrame, minimal: bool = False) -> str:
    """
    Chạy ydata-profiling và trả về HTML string nguyên bản.
    
    Output này sẽ được nhúng vào smart_eda_report.html qua <iframe srcdoc>.
    
    Args:
        df: DataFrame cần profile
        minimal: True = chạy nhanh (ít chart), False = đầy đủ
    
    Returns:
        HTML string từ ProfileReport.to_html()
    """
    from ydata_profiling import ProfileReport
    profile = ProfileReport(df, minimal=minimal, title="Statistical Details")
    return profile.to_html()
```

### Task C5: Webapp — Hiển thị smart_eda_report.html
**File**: `src/webapp/app.py`

Thêm endpoint mới:
```python
@app.get("/api/jobs/{job_id}/report")
def get_smart_eda_report(job_id: str) -> HTMLResponse:
    """Serve smart_eda_report.html cho viewer."""
    job_id = _validate_job_id(job_id)
    report_path = JOBS_DIR / job_id / "smart_eda_report.html"
    if not report_path.exists():
        raise HTTPException(status_code=404, detail="Report not yet generated")
    return HTMLResponse(report_path.read_text(encoding="utf-8"))
```

Cập nhật `KNOWN_OUTPUTS`:
```python
KNOWN_OUTPUTS = {
    "data_quality_findings.json",
    "schema_evaluation_findings.json",
    "cross_table_analysis.json",
    "dataset_verdict.json",
    "summary_report.md",
    "l4_report.md",
    "smart_eda_report.html",   # ← THÊM
    "guardrail_report.json",
    "artifact_manifest.json",
}
```

### Task C6: Webapp — Job viewer UI nâng cấp
**File**: `src/webapp/static/app.js`, `src/webapp/static/styles.css`

Khi job hoàn thành, thay vì chỉ hiển thị markdown report, hiển thị:
1. **"View Full Report" button** → mở smart_eda_report.html trong tab mới hoặc iframe
2. **Verdict banner** ngay trên job result (lấy từ `dataset_verdict.json`)
3. **Progress bar** cải thiện — hiện tại đã có `progress` field, nhưng UI cần animation
4. **Download button** cho smart_eda_report.html

UI mock:
```
┌──────────────────────────────────────────────┐
│  Job: abc123def456                           │
│  Status: ✅ Completed                         │
│                                              │
│  ┌────────────────────────────────────────┐  │
│  │ ⚠️ WARN — Dataset có 3 vấn đề         │  │
│  │ titanic.csv · 891 rows · 12 cols       │  │
│  └────────────────────────────────────────┘  │
│                                              │
│  [📊 View Full Report]  [⬇ Download HTML]   │
│                                              │
│  Files:                                      │
│  📄 smart_eda_report.html                    │
│  📄 data_quality_findings.json               │
│  📄 dataset_verdict.json                     │
│  📄 guardrail_report.json                    │
│  ...                                         │
└──────────────────────────────────────────────┘
```

### Task C7: L2b.5 Human-in-the-loop UI
**File**: `src/webapp/app.py` + `src/webapp/static/app.js`

**Quick Mode** (MVP — ARCHITECT §5.4.5):
Khi pipeline detect multi-table + schema, hiển thị schema confirmation step:

**API endpoints cần tạo:**
```python
@app.get("/api/jobs/{job_id}/schema-suggestions")
def get_schema_suggestions(job_id: str) -> JSONResponse:
    """Trả schema suggestions (PKs, FKs) cho user confirm."""
    # Đọc từ schema_evaluation_findings.json
    # Trả: {"tables": [...], "relationships": [...], "suggested_pks": {...}}

@app.post("/api/jobs/{job_id}/schema-confirm")
def confirm_schema(job_id: str, body: dict) -> JSONResponse:
    """
    User confirm/reject schema suggestions.
    Body: {"confirmed_pks": {...}, "confirmed_fks": [...], "mode": "quick"}
    Lưu vào: JOBS_DIR / job_id / "confirmed_schema.json"
    """
```

**UI flow:**
```
Upload files → Pipeline bắt đầu → Detect multi-table
                                        ↓
                              ┌─ Schema Confirmation ──────────┐
                              │                                │
                              │ Confirm Primary Keys:          │
                              │ ☑ customers.customer_id (0.92) │
                              │ ☑ orders.order_id (0.88)       │
                              │                                │
                              │ Confirm Relationships:         │
                              │ ☑ orders.customer_id → ...     │
                              │                                │
                              │ [Skip All] [Confirm & Continue]│
                              └────────────────────────────────┘
                                        ↓
                              Pipeline tiếp tục với confirmed schema
```

**Quick Mode fallback**: Nếu user click "Skip All" → pipeline dùng inferred schema (auto-fallback).

### Task C8: Responsive + Dark Mode
**File**: `src/reporting/templates/styles.css`, `src/webapp/static/styles.css`
- Report template: responsive breakpoints (mobile, tablet, desktop)
- Webapp: dark mode toggle hoặc auto-detect
- Print styles cho report

## Test

### Test 1: Template độc lập
Mở `report_template.html` trực tiếp trong browser với hardcoded values:
```bash
# Tạo test file thay placeholders bằng giá trị thật
python -c "
template = open('src/reporting/templates/report_template.html').read()
css = open('src/reporting/templates/styles.css').read()
js = open('src/reporting/templates/tab.js').read()
html = template.format(
    verdict_class='WARN',
    verdict_value='WARN',
    verdict_icon='⚠️',
    verdict_rationale='Dataset có 3 vấn đề cần xem xét',
    file_name='titanic.csv',
    n=891,
    n_var=12,
    p_cells_missing='5.2%%',
    ai_analysis_content='<h2>Executive Summary</h2><p>Test content</p>',
    ydata_escaped='<h1>ydata test</h1>',
    guardrail_status='passed',
    provider='multi-agent',
    model_info='Analyst: gpt-4o-mini, Editor: gpt-4o',
    timestamp='2026-06-11T12:00:00',
    css_content=css,
    js_content=js,
)
open('test_report.html', 'w', encoding='utf-8').write(html)
print('Created test_report.html — open in browser')
"
```

### Test 2: Webapp
```bash
# Chạy webapp
uvicorn src.webapp.app:app --reload --port 8000

# Mở browser → http://localhost:8000
# Upload file → verify progress → verify report viewer
```

### Test 3: ydata HTML
```bash
python -c "
import sys; sys.path.insert(0, 'src')
import pandas as pd
from engines.profiling_engine import run_profiling_html
df = pd.read_csv('examples/sample_datasets/titanic/train.csv')
html = run_profiling_html(df, minimal=True)
print(f'ydata HTML: {len(html)} chars')
open('test_ydata.html', 'w', encoding='utf-8').write(html)
"
```

## Lưu ý quan trọng
- **Template placeholders PHẢI khớp** danh sách `TEMPLATE_PLACEHOLDERS` trong `src/reporting/html_merger.py`
- **Dùng `{` và `}` cẩn thận** trong template — escape bằng `{{` `}}` nếu là CSS/JS literal
- **KHÔNG sửa `models.py`** — đã locked
- **KHÔNG sửa `run_pipeline.py`** — của Member B
- File report template phải **self-contained** (no external CDN dependencies ngoại trừ Google Fonts)
- Dùng `{css_content}` và `{js_content}` placeholders thay vì link external files
