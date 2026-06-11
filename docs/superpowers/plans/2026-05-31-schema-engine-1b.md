# Schema Engine — Nhịp 1b (Multi-table + Orphan Foreign Key)

> **Cho Thợ:** Mở rộng 1a sang nhiều bảng để kiểm referential integrity. Deterministic, KHÔNG LLM/network.
> TDD task-by-task. Source of truth = CODE. Conflict/mơ hồ → DỪNG + Issue Report.
> Đã verify pydbml: `ref.type` ∈ {'>','<','-'}; với '>' thì `table1.col1`=FK(con), `table2.col2`=PK(cha).
> Tham khảo `frictionless_py` cách check FK/PK integrity (đọc để học, KHÔNG copy).

## Goal
Nạp **nhiều CSV cùng lúc** (mỗi file ↔ 1 bảng DBML), chạy lại 7 check single-table của 1a **cho từng bảng**,
và thêm **ORPHAN_FOREIGN_KEY** chéo bảng. Sinh một `schema_evaluation_findings.json` bao trùm mọi bảng,
verdict tính cả lỗi FK. Hoàn tất referential integrity.

## Scope 1b (LÀM) vs KHÔNG
- ✅ Multi-table ingestion: list/dir CSV + 1 DBML, khớp file ↔ bảng theo **tên file (stem)**.
- ✅ Chạy 7 validator 1a cho **mỗi** bảng (loop).
- ✅ ORPHAN_FOREIGN_KEY: giá trị FK ở bảng con không tồn tại trong PK bảng cha.
- ✅ FK_UNCHECKED (transparent): khi bảng cha không được nạp → KHÔNG im lặng bỏ qua.
- ✅ Wire vào aggregator → verdict.
- ❌ KHÔNG làm: composite FK (>1 cột) → bỏ qua + note; ref một-một `'-'` → bỏ qua + note.
- ❌ KHÔNG làm data-quality (profiling/anomaly) **per-table** ở chế độ multi — đó là việc riêng sau.
- ❌ KHÔNG đụng compound (integrity vẫn đi thẳng vào aggregator như 1a — nợ "compound chạy thật" vẫn để mở).

---

## Input model (mới)
Chế độ multi-table **tách biệt** với chế độ single-CSV hiện có (đừng phá luồng cũ):
```python
def load_tables(csv_paths: list[str], dbml_path: str) -> dict[str, "pd.DataFrame"]:
    """Khớp mỗi CSV với 1 bảng DBML theo filename stem (users.csv -> 'users').
    Dùng lại registry.load_any cho từng file. Trả {table_name: df} cho các file khớp được.
    File không khớp bảng nào -> log cảnh báo, bỏ qua (không raise)."""
```
- Bảng DBML không có CSV tương ứng → vẫn parse schema, nhưng FK chạm tới nó → FK_UNCHECKED.

## ⚠️ Cạm bẫy FK matching (dtype)
FK con và PK cha có thể khác dtype (int64 vs float64 do null, hoặc int vs str) → `isin` so sai → orphan giả.
Quy tắc: nếu **cùng family numeric** → so trực tiếp (pandas tự coerce int/float). Nếu **family khác nhau**
(vd numeric vs string) → KHÔNG đoán, emit **FK_UNCHECKED (WARN)** kèm mô tả lệch kiểu, đừng tạo orphan giả.

---

## Severity policy bổ sung (tiếp bảng 1a)
| issue_type | severity | dq_dimension |
|---|---|---|
| ORPHAN_FOREIGN_KEY | CRITICAL | Consistency |
| FK_UNCHECKED | WARN | Consistency |

---

## Task 1b-1: Ref normalizer (xác định hướng FK)
**Files:** mở rộng `src/engines/schema_engine.py`, `tests/engines/test_schema_engine.py`

```python
def normalize_refs(db) -> list[dict]:
    """Trả [{child_table, fk_col, parent_table, pk_col}] cho FK đơn cột.
    '>': child=table1.col1, parent=table2.col2
    '<': child=table2.col2, parent=table1.col1
    '-': bỏ qua (one-to-one, ambiguous) + log
    Composite (len(col1)>1): bỏ qua + log."""
```
**AC:** `[ref: > users.id]` trên orders.user_id → {child:orders, fk:user_id, parent:users, pk:id};
ref `'<'` đảo hướng đúng; composite/`'-'` bị loại + không crash.

## Task 1b-2: Orphan FK check
```python
def check_foreign_keys(tables: dict, refs: list[dict]) -> list[IntegrityError]:
```
Cho mỗi ref:
- bảng con/cha chưa nạp, hoặc cột FK/PK vắng → **FK_UNCHECKED** (WARN), continue.
- family lệch (xem cạm bẫy) → **FK_UNCHECKED** (WARN), continue.
- `parent_keys = set(parent_df[pk_col].dropna())`
- `orphan = child_df[fk_col].notna() & ~child_df[fk_col].isin(parent_keys)`  (FK null = "không tham chiếu", KHÔNG phải orphan)
- `n = orphan.sum()`; nếu n>0 → **ORPHAN_FOREIGN_KEY** (CRITICAL): affected_table=child, affected_column=fk_col,
  affected_count=n, top_10_samples = vài dòng orphan `{fk_col: value}`.

**AC (dùng fixture 1b-4):**
- orders có user_id=9999 không có trong users → ORPHAN_FOREIGN_KEY, affected_count đúng, sample chứa 9999.
- FK null → KHÔNG tính orphan.
- mọi FK hợp lệ → KHÔNG có finding.
- users (cha) không nạp → FK_UNCHECKED (WARN), không crash.

## Task 1b-3: validate_all (multi-table) + wire pipeline
```python
def validate_schema_multi(csv_paths: list[str], dbml_path: str) -> SchemaEvaluationFindings:
    tables = load_tables(csv_paths, dbml_path)
    parsed = parse_dbml(dbml_path)
    errs = []
    for tname, df in tables.items():
        errs += validate_table(df, tname, parsed)        # 7 check 1a/bảng
    errs += check_foreign_keys(tables, normalize_refs(PyDBML(...)))
    # schema_meta: dbml_file, total_tables=len(parsed), total_relationships=len(refs)
    # tables: [{name, columns:[...]}]
    return SchemaEvaluationFindings(...)
```
Pipeline (`run_pipeline.py`): thêm nhánh multi-table — khi nhận **nhiều CSV + 1 DBML**:
- dump `schema_evaluation_findings.json` (đa bảng)
- `aggregate(meta, dq_findings=[], integrity_errors=findings.integrity_errors)` → `dataset_verdict.json`
  (chế độ multi-table 1b: dq_findings rỗng — data-quality per-table là việc sau; verdict dựa trên integrity).
- `meta` cho verdict: dùng tổng hợp (vd n = tổng số dòng các bảng, hoặc meta của bảng "chính"); ghi rõ trong code chọn cách nào.

Luồng single-CSV cũ (1 file) GIỮ NGUYÊN, không đổi.

**AC:** fixture orphan → schema_evaluation_findings.json có ORPHAN_FOREIGN_KEY + verdict NOT_READY.

## Task 1b-4: Fixtures tự chứa (data thật user đưa sau)
`tests/fixtures/multi/shop.dbml`:
```dbml
Table users { id integer [pk] email varchar [unique] }
Table orders { id integer [pk] user_id integer [ref: > users.id] total decimal }
```
`tests/fixtures/multi/users.csv`:
```csv
id,email
1,a@x.com
2,b@x.com
3,c@x.com
```
`tests/fixtures/multi/orders.csv` (cố ý có orphan user_id=9999 và 1 FK null):
```csv
id,user_id,total
101,1,50.0
102,2,75.0
103,9999,20.0
104,,30.0
```
→ kỳ vọng: 1 ORPHAN_FOREIGN_KEY (affected_count=1, user_id=9999), dòng 104 (null) KHÔNG tính orphan.
Verdict → NOT_READY (CRITICAL).

Thêm biến thể clean (orders.user_id toàn ∈ {1,2,3}) → 0 orphan → verdict không vì FK mà fail.

## GATE 1b
`pytest tests/ -v` xanh hết (gồm test orphan FK + integration multi-table).
Chạy pipeline trên `tests/fixtures/multi/` → `schema_evaluation_findings.json` đa bảng có ORPHAN_FOREIGN_KEY,
`dataset_verdict.json` = NOT_READY. Luồng single-CSV cũ chạy không đổi.

## Sau 1b (không làm bây giờ)
- **3b spike:** missingness MCAR/MAR/MNAR (statsmodels/Little's test — rủi ro cao).
- data-quality per-table ở chế độ multi (profiling/anomaly cho từng bảng).
- compound chạy trên data thật (nợ cũ — task nhỏ riêng).
- L4 LLM + Guardrail.

## Verify khi build
- `normalize_refs` cần object db (PyDBML) — cân nhắc cho `parse_dbml` trả luôn cả refs để khỏi parse 2 lần.
- pydbml ref đôi khi định nghĩa ngoài bảng (`Ref: orders.user_id > users.id`) — fixture nên test cả 2 cách viết nếu dễ.
- `isin` với tập rỗng (bảng cha 0 dòng) → mọi FK non-null thành orphan; cân nhắc emit FK_UNCHECKED nếu parent rỗng.
