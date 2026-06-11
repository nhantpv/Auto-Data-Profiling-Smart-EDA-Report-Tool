# Schema Engine — Nhịp 1a (Single-table validation)

> **Cho Thợ:** Engine deterministic mới (mức L1/L2), KHÔNG LLM/network. TDD task-by-task.
> Source of truth = CODE hiện tại. Conflict/mơ hồ → DỪNG + Issue Report.
> `pydbml` đã verify parse được: tables, columns, `.type`, `.pk`, `.unique`, `.not_null`, `db.refs` (FK).

## Goal
Khi có file `.dbml`, đối chiếu **1 CSV vs 1 bảng DBML tương ứng**, sinh `schema_evaluation_findings.json`,
và đẩy `integrity_errors` vào aggregator để verdict phản ánh cả lỗi schema. Hoàn tất 3/3 JSON.

## Scope 1a (LÀM) vs KHÔNG
- ✅ TYPE_MISMATCH (so theo **họ kiểu**, không so dtype thô — xem cạm bẫy bên dưới)
- ✅ PK_DUPLICATE, PK_NULL, NOT_NULL_VIOLATION, UNIQUE_VIOLATION
- ✅ MISSING_COLUMN (DBML khai mà CSV thiếu), EXTRA_COLUMN (CSV thừa)
- ✅ Wire: pipeline xuất `schema_evaluation_findings.json` + verdict tính cả integrity
- ❌ KHÔNG làm ORPHAN_FOREIGN_KEY / multi-table / referential integrity → đó là **nhịp 1b** (cần input nhiều CSV)
- ❌ KHÔNG compound integrity errors (đẩy thẳng vào aggregator; cross-type compound để sau)

---

## ⚠️ Cạm bẫy BẮT BUỘC xử: int + null = float trong pandas
CSV có cột khai `integer` nhưng chứa **dù 1 ô trống** → pandas đọc thành `float64`. So dtype chính xác
(`int64 == integer`) sẽ báo TYPE_MISMATCH **giả** cho mọi cột integer có null. → So theo **HỌ KIỂU**:

```python
DBML_FAMILY = {  # DBML type -> family
    "integer":"numeric","int":"numeric","bigint":"numeric","smallint":"numeric",
    "decimal":"numeric","numeric":"numeric","float":"numeric","double":"numeric","real":"numeric",
    "varchar":"string","char":"string","text":"string","string":"string",
    "boolean":"boolean","bool":"boolean",
    "date":"datetime","datetime":"datetime","timestamp":"datetime",
}
def pandas_family(dtype) -> str:
    import pandas.api.types as t
    if t.is_bool_dtype(dtype): return "boolean"        # check bool TRƯỚC numeric (bool là subtype của int)
    if t.is_numeric_dtype(dtype): return "numeric"
    if t.is_datetime64_any_dtype(dtype): return "datetime"
    return "string"
# MISMATCH chỉ khi family khác nhau. DBML type lạ (không trong map) -> bỏ qua check type cột đó (đừng đoán).
```

---

## Severity policy cho integrity (engine tự gán; IntegrityError đã có field severity)
| issue_type | severity | dq_dimension |
|---|---|---|
| MISSING_COLUMN | CRITICAL | Consistency |
| PK_DUPLICATE | CRITICAL | Uniqueness |
| PK_NULL | CRITICAL | Completeness |
| TYPE_MISMATCH | HIGH | Validity |
| UNIQUE_VIOLATION | HIGH | Uniqueness |
| NOT_NULL_VIOLATION | HIGH | Completeness |
| EXTRA_COLUMN | INFO | Consistency |

---

## Task 1a-0: Tiền đề — model & matcher
- Kiểm `src/ontology/models.py` đã có root model `SchemaEvaluationFindings` chưa
  (`schema_meta: dict`, `tables: list`, `integrity_errors: list[IntegrityError]`). Chưa thì thêm + test roundtrip.
- `IntegrityError` cần `affected_column: Optional[str] = None` — thêm nếu chưa có.

## Task 1a-1: DBML parser + table matcher
**Files:** `src/engines/schema_engine.py`, `tests/engines/test_schema_engine.py`

```python
def parse_dbml(dbml_path: str) -> dict:
    """pydbml -> {table_name: {columns:{name:{type,pk,unique,not_null}}}}"""

def match_table(df, parsed: dict, csv_path: str) -> str:
    """Khớp CSV với 1 bảng DBML: (1) nếu DBML chỉ 1 bảng -> dùng nó;
    (2) else khớp tên file (stem) == tên bảng; (3) else raise ValueError rõ ràng."""
```
**AC:** parse sample.dbml ra đúng users/orders + cờ pk/unique; match `users.csv` -> "users";
DBML 1 bảng -> auto match; không khớp được -> ValueError.

## Task 1a-2: Single-table validators
```python
def validate_table(df, table_name: str, parsed: dict) -> list[IntegrityError]:
```
Chạy lần lượt, gom IntegrityError (mỗi lỗi 1 record, kèm `top_10_samples` + `affected_count`):
- cột DBML thiếu trong df → MISSING_COLUMN
- cột df không trong DBML → EXTRA_COLUMN
- với cột có ở cả hai: family khác → TYPE_MISMATCH (sample vài giá trị sai)
- cột pk: trùng → PK_DUPLICATE; có null → PK_NULL
- cột not_null (không pk): có null → NOT_NULL_VIOLATION
- cột unique (không pk): trùng → UNIQUE_VIOLATION

**AC (dùng fixture 1a-4):**
- cột integer có null KHÔNG bị TYPE_MISMATCH (cạm bẫy đã xử)
- cột khai integer chứa chữ → TYPE_MISMATCH (HIGH)
- pk có giá trị lặp → PK_DUPLICATE (CRITICAL)
- DBML khai cột "phone" mà CSV không có → MISSING_COLUMN (CRITICAL)
- CSV có cột "notes" không khai → EXTRA_COLUMN (INFO)

## Task 1a-3: build SchemaEvaluationFindings + wire pipeline
```python
def build_schema_findings(df, csv_path, dbml_path) -> SchemaEvaluationFindings: ...
```
Pipeline (`run_pipeline.py`): nếu `dbml_path` được cung cấp →
1. `schema = build_schema_findings(...)` → dump `output/schema_evaluation_findings.json`
2. truyền `schema.integrity_errors` vào `aggregate(meta, all_dq, integrity_errors=schema.integrity_errors)`
   → verdict tính cả lỗi schema.
Nếu KHÔNG có dbml → bỏ qua, `integrity_errors=None` (hành vi cũ giữ nguyên).

**AC:** aggregator đếm integrity vào summary đúng tier; có 1 CRITICAL integrity → verdict NOT_READY.

## Task 1a-4: Fixtures tự chứa (data thật user đưa sau)
Tạo trong `tests/fixtures/`:

`schema_ok.dbml` + `schema_ok.csv` — khớp hoàn toàn (chỉ có thể vài INFO). Verdict kỳ vọng READY.

`schema_bad.dbml`:
```dbml
Table customers {
  id integer [pk]
  email varchar [unique]
  age integer
  phone varchar
}
```
`schema_bad.csv` (cố ý lỗi):
```csv
id,email,age,notes
1,a@x.com,25,hello
1,b@x.com,thirty,world
2,a@x.com,40,foo
```
→ kỳ vọng: PK_DUPLICATE(id=1 lặp, CRITICAL) + TYPE_MISMATCH(age chứa "thirty", HIGH) +
UNIQUE_VIOLATION(email a@x.com lặp, HIGH) + MISSING_COLUMN(phone, CRITICAL) + EXTRA_COLUMN(notes, INFO).
Verdict → NOT_READY.

## GATE 1a
`pytest tests/ -v` xanh hết (gồm tests/engines/test_schema_engine.py + integration).
Pipeline chạy với cặp CSV+DBML → sinh **ĐỦ 3 file JSON**; verdict bad-pair = NOT_READY, ok-pair = READY.
Pipeline chạy KHÔNG có DBML → vẫn ra 2 file như cũ, không vỡ.

## Sau 1a (không làm bây giờ)
- **Nhịp 1b:** ORPHAN_FOREIGN_KEY + multi-table (cần input model nhiều CSV; đọc `frictionless_py`).
- 3b missingness; overview_charts; L4 LLM + Guardrail.
- (nợ) compound chưa chạy trên data thật — không thuộc schema engine.

## Verify khi build (chưa chắc tới khi chạy)
- `pydbml`: `column.type` có thể là object (đã thấy str hóa OK) — dùng `str(c.type).lower()` khi map family.
- DBML có thể khai type kèm size (`varchar(255)`) → strip phần `(...)` trước khi tra map.
