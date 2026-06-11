# Part 3b — Missingness Mechanism (MCAR / MAR / MNAR-tentative)

> **Cho Thợ:** Hoàn tất L2.5. Deterministic (seed cố định), KHÔNG LLM/network. TDD task-by-task.
> Phương pháp ĐÃ được spike verify (xem bảng kết quả trong report kèm). Conflict/mơ hồ → DỪNG + Issue Report.

## Goal
Điền `ColumnStats.missingness_mechanism` (đang null) cho các cột có missing, dùng:
1. **Little's MCAR test** (pyampute) — dataset-level: missing có hoàn toàn ngẫu nhiên không?
2. **Logistic MAR heuristic** — per-column: missing của cột này có đoán được từ các cột quan sát khác không?

## ⚠️ Sự thật phải nhúng vào output (đừng hứa quá tay)
- **MNAR KHÔNG thể khẳng định từ data** (phụ thuộc giá trị đã mất — không quan sát được). Tool chỉ gán
  **"MNAR?"** (dấu hỏi) kèm caveat "cần kiểm tra nghiệp vụ", KHÔNG bao giờ khẳng định MNAR chắc chắn.
- Little's test là **chỉ báo**, không phải phán quyết (chính doc pyampute cảnh báo). Bác bỏ H0 ≠ chắc chắn
  không-MCAR.
- Little's test **có thể lỗi số học** (ma trận hiệp phương sai suy biến khi cột cộng tuyến) → phải
  try/except → fallback `None` (hệ thống đã xử null tốt, đừng để crash).

## Decision logic per-column (đã verify bằng spike)
Cho mỗi cột có `p_missing > 0`:
```
mcar_p = little_mcar_pvalue(df_numeric)          # dataset-level, None nếu test lỗi
auc    = mar_auc(df, col)                         # per-column, None nếu không đủ dữ liệu

if mcar_p is None and auc is None:  -> None        # không xác định được
elif auc is not None and auc > 0.65: -> "MAR"      # missing đoán được từ cột quan sát khác
elif mcar_p is not None and mcar_p >= 0.05: -> "MCAR"   # không bác bỏ được ngẫu nhiên
elif mcar_p is not None and mcar_p < 0.05:  -> "MNAR?"  # không-MCAR & không giải thích bởi observed -> nghi MNAR
else: -> None
```
> Ngưỡng `0.65` (AUC) và `0.05` (p) là **heuristic** — ghi rõ trong docstring, để hằng số ở đầu module để tune.

---

## Task 3b-1: Module missingness
**Files:** `src/severity/missingness.py`, `tests/severity/test_missingness.py`
**Deps (pyproject):** thêm `pyampute>=0.0.3`. (scikit-learn đã có sẵn qua pyod.)

```python
_MAR_AUC_GATE = 0.65
_MCAR_ALPHA = 0.05

def little_mcar_pvalue(df_numeric) -> float | None:
    """Wrap pyampute MCARTest(method='little'). try/except -> None nếu lỗi/không đủ cột."""

def mar_auc(df, col: str) -> float | None:
    """Logistic CV-AUC dự đoán is_missing(col) từ các cột numeric KHÁC (fillna median).
    None nếu: <10 missing, y một lớp, không có cột numeric khác, hoặc lỗi."""

def classify_missingness(col_missing: int, mcar_p: float | None, auc: float | None) -> str | None:
    """Trả 'MCAR' | 'MAR' | 'MNAR?' | None theo decision logic ở trên. col_missing==0 -> None."""

def detect_missingness(df) -> dict[str, str]:
    """Chạy 1 lần Little (dataset), rồi per-column auc -> {col: mechanism} cho cột có missing."""
```

**AC (dùng fixture tổng hợp seed cố định):**
- df MCAR thuần → cột missing được gán "MCAR" (p>=0.05, auc≈0.5).
- df MAR (missing cột c phụ thuộc cột a) → c gán "MAR" (auc>0.65).
- cột missing nhưng không có cột numeric khác → None (không crash).
- df 1 cột duy nhất / cột cộng tuyến làm Little lỗi → mcar_p=None, KHÔNG raise.
- col_missing==0 → None.

## Task 3b-2: Wire vào pipeline — điền missingness_mechanism
Sau profiling, trước/trong khi build findings:
```python
from severity.missingness import detect_missingness
mechs = detect_missingness(df)           # {col: "MAR"/"MCAR"/"MNAR?"}
# khi tạo ColumnStats: missingness_mechanism = mechs.get(col_name)
```
(Sửa `_extract_column_stats` / findings_builder để nhận `mechs` và set field. Cột không trong dict → giữ None.)

**AC:** chạy pipeline trên `stroke_classification.csv` → `columns.bmi.missingness_mechanism == "MAR"`
(spike đã xác nhận AUC=0.727). Các cột không missing → null.

## Task 3b-3: Calibrator dùng mechanism để chỉnh severity Completeness (sửa nhỏ 3a)
Trong `calibrator.py`, rule completeness: sau khi tra tier theo `p_missing`, **nâng 1 bậc** (dùng
`SEVERITY_ORDER`, cap CRITICAL) nếu `missingness_mechanism in ("MAR", "MNAR?")` — vì missing không-ngẫu-nhiên
nguy hiểm hơn (impute ngây thơ sẽ gây bias). `MCAR` hoặc `None` → KHÔNG nâng.

> Khớp đúng ý data-flow gốc ("p_missing 5.2% + MAR → HIGH"). Giữ nhỏ: chỉ tác động rule completeness.

**AC:**
- cột p_missing=0.10 (→WARN theo bảng) + mechanism="MAR" → finding severity = HIGH (nâng 1 bậc).
- cùng p_missing + mechanism="MCAR" → giữ WARN.
- cột p_missing=0.10 + mechanism=None → giữ WARN (hành vi 3a cũ không đổi).

## GATE 3b
`pytest tests/ -v` xanh hết (gồm tests/severity/test_missingness.py + calibrator update).
Pipeline trên stroke → `bmi.missingness_mechanism == "MAR"`; verdict vẫn hợp lý (bmi 3.9% missing → WARN sau
nâng bậc do MAR, vẫn không CRITICAL/HIGH đủ để đổi verdict khỏi READY... **kiểm lại**: WARN→ không đổi verdict;
nếu nâng thành HIGH thì verdict thành WARN — xác nhận hành vi và ghi rõ).

> **Lưu ý kiểm GATE:** sau 3b, bmi MAR có thể bị nâng từ INFO/WARN lên 1 bậc → verdict stroke CÓ THỂ
> đổi từ READY sang WARN. Đó là hành vi ĐÚNG (missing không ngẫu nhiên đáng cảnh báo hơn), không phải bug —
> nhưng phải xác nhận con số và cập nhật kỳ vọng test cho khớp.

## Sau 3b (L2.5 hoàn tất hoàn toàn)
- (nợ cũ) compound chạy trên data thật — task nhỏ riêng.
- overview_charts; data-quality per-table (multi mode).
- **L4 LLM + Guardrail** — đề xuất làm Guardrail (deterministic, test được) TRƯỚC, rồi mới cắm LLM.

## Verify khi build
- pyampute API: `from pyampute.exploration.mcar_statistical_tests import MCARTest; MCARTest(method="little").little_mcar_test(df_numeric)` (đã verify chạy được, trả p-value float).
- Little's test cần ≥2 cột numeric và có pattern missing; ít hơn → để trả None.
- Cố định seed cho logistic CV để kết quả reproducible (cross_val_score không random với LogisticRegression mặc định, nhưng set random_state cho chắc).
