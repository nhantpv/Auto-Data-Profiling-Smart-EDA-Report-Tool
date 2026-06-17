# Architecture Decision Record (ADR) — Smart EDA v3.0

**Ngày tạo:** 2026-06-10
**Tác giả:** Team (Tổng hợp từ Problem_need_to_be_solved.md, review_Long_architecture.md, review_Long_architecture_adjusted.md, và các phiên thảo luận kiến trúc)
**Mục đích:** Ghi nhận quyết định kiến trúc cuối cùng cho từng trụ cột. Tài liệu này là **nguồn sự thật duy nhất** cho đội ngũ phát triển.

---

## Mục lục

1. [Trụ cột 1: Xóa bỏ Vision LLM + ArtifactManifest](#trụ-cột-1-xóa-bỏ-vision-llm--artifactmanifest) — ✅ ĐÃ GIẢI QUYẾT
2. [Trụ cột 2: Tự động phát hiện Schema (Auto-Discovery)](#trụ-cột-2-tự-động-phát-hiện-schema-auto-discovery) — 🔄 THIẾT KẾ MỚI
3. [Trụ cột 3: Cross-table Safe Join & Correlation](#trụ-cột-3-cross-table-safe-join--correlation) — ⚠️ THIẾT KẾ XONG, CHƯA CODE
4. [Trụ cột 4: Sampling Metadata](#trụ-cột-4-sampling-metadata) — ✅ ĐÃ GIẢI QUYẾT
5. [Trụ cột 5: Severity Stack & Verdict](#trụ-cột-5-severity-stack--verdict) — ⚠️ CẦN ĐÁNH GIÁ THÊM

---

## Trụ cột 1: Xóa bỏ Vision LLM + ArtifactManifest

### Trạng thái: ✅ ĐÃ GIẢI QUYẾT — Đã code xong, đang hoạt động

### Vấn đề gốc

1. **Vision LLM tốn token gấp 3-4x**, tốc độ chậm 50%, và rất hay hallucinate khi đọc biểu đồ phức tạp.
2. **Rủi ro Path Traversal**: Nếu LLM tự do sinh mã `[CHART_XYZ]`, hacker có thể lừa LLM đọc file hệ thống qua Prompt Injection.

### Quyết định kiến trúc

- **L4 Text-Only**: LLM chỉ nhận JSON evidence (các con số thống kê chính xác do Python tính toán). Tuyệt đối không gửi ảnh.
- **ArtifactManifest Allowlist**: Khi Python vẽ xong biểu đồ PNG, nó ghi ID vào manifest. Report chỉ được tham chiếu artifact có trong manifest.
- **Guardrail kiểm tra**: Narrative report bị quét regex — mọi số liệu và tham chiếu phải tồn tại trong evidence set trước khi file được ghi ra.

### Code đã triển khai

| File | Chức năng |
|:---|:---|
| `src/reporting/l4_report.py` | Sinh report deterministic hoặc gọi OpenAI, luôn kiểm tra guardrail trước khi trả kết quả |
| `src/guardrail/narrative.py` | Xây dựng evidence set từ findings/verdict, quét narrative tìm violation |
| `src/ontology/models.py` | `ArtifactManifest` + `ArtifactRecord` Pydantic models |
| `run_pipeline.py` | `_write_artifact_manifest()` ghi manifest sau khi tất cả artifact được tạo |

### Đánh giá

Hoàn hảo cho MVP. Không overengineer. Chi phí API giảm đáng kể. Rủi ro Path Traversal bị chặn triệt để.

---

## Trụ cột 2: Tự động phát hiện Schema (Auto-Discovery)

### Trạng thái: 🔄 THIẾT KẾ MỚI — Đã có code nền, cần bổ sung Human-in-the-loop

### Vấn đề gốc

Khi user không cung cấp file DBML/SQL DDL, hệ thống phải tự suy luận:
1. Cột nào là Khóa chính (PK) của mỗi bảng?
2. Cột nào ở bảng A trỏ sang Khóa chính ở bảng B? (FK relationship)

Các phương pháp đã được đánh giá và loại bỏ:
- **Jaccard Index**: Sai hoàn toàn với Surrogate Key (ID tự tăng 1,2,3... → bảng nào cũng trùng 100%).
- **LLM chốt FK**: Tốn token, có thể hallucinate quan hệ nghiệp vụ, khó test ổn định.
- **Chỉ dùng thuật toán scoring (deterministic 100%)**: Hệ thống 15 magic numbers quá phức tạp để calibrate, output không được đảm bảo — dù thuật toán đúng 90% thì 10% sai vẫn lan truyền làm hỏng toàn bộ pipeline phía sau.

### Quyết định kiến trúc: Thuật toán gợi ý + Human xác nhận

**Nguyên tắc cốt lõi:** Không thuật toán hay LLM nào có thể đảm bảo 100% chính xác cho bài toán suy luận quan hệ bảng (vì bản chất là bài toán ngữ nghĩa). Do đó, **human là người ra quyết định cuối cùng**. Thuật toán chỉ đóng vai trò "gợi ý thông minh" — tick sẵn các ứng viên để user xác nhận nhanh.

### Luồng xử lý theo số bảng

```text
User upload data
    │
    ├── 1 file duy nhất
    │   → Single-table pipeline
    │   → Trụ cột 2 & 3 KHÔNG CHẠY (không có vấn đề gì)
    │
    └── Nhiều file (N ≥ 2)
        │
        ├── User có cung cấp DBML/SQL DDL?
        │   ├── Có → Dùng schema explicit, bỏ qua bước suy luận
        │   └── Không → Chạy Auto-Discovery ↓
        │
        ├── 🚀 Quick Mode (Tùy chọn — mặc định ở CLI)
        │   │  Thuật toán tự chọn FK dựa trên coverage + scoring
        │   │  KHÔNG chờ user xác nhận
        │   │  Gắn cờ: "schema = inferred, chưa xác nhận"
        │   │  Phù hợp: Demo nhanh, khám phá sơ bộ, batch CLI
        │   └─→ Chuyển sang Trụ cột 3
        │
        └── 🎯 Precise Mode (Mặc định ở Web UI)
            │  Thuật toán lọc ứng viên, tick sẵn gợi ý
            │  Hiển thị UI cho user xem data mẫu + xác nhận
            │  User tick/bỏ tick → Chốt schema chính xác 100%
            └─→ Chuyển sang Trụ cột 3
```

### Vai trò code hiện tại của Long

Code trong `src/engines/schema_engine.py` (~400 dòng) vẫn được giữ nguyên, nhưng thay đổi vai trò:

| Trước (Long thiết kế) | Sau (Quyết định mới) |
|:---|:---|
| Thuật toán là **người ra quyết định** cuối cùng | Thuật toán chỉ **gợi ý** (tick sẵn) |
| Output = schema chốt, chạy tiếp ngay | Output = danh sách ứng viên, chờ user xác nhận |
| Nếu sai → pipeline sai hoàn toàn | Nếu sai → user bỏ tick, sửa lại |

Code hiện có đóng vai trò "AI gợi ý":
- `_infer_primary_key()` → Gợi ý cột nào là PK (tick sẵn)
- `infer_relationships()` → Gợi ý cặp FK nào hợp lý (tick sẵn)
- `_value_coverage()` → Tính % coverage hiển thị cho user tham khảo

Nếu thuật toán đúng → User bấm xác nhận, xong trong 3 giây.
Nếu thuật toán sai → User bỏ tick, sửa lại, vẫn đúng.

### Thiết kế giao diện Human-in-the-loop (Precise Mode)

#### Bước 1: Hiển thị tổng quan các bảng

UI hiển thị **10 dòng đầu** của mỗi bảng để user có bức tranh toàn cảnh về dữ liệu:

```text
┌─────────────────────────────────────────────────────────────────┐
│  📊 TỔNG QUAN DỮ LIỆU ĐÃ TẢI LÊN                             │
│                                                                 │
│  ┌─ students.csv ──────────────────────────────────────────┐    │
│  │ 150 dòng × 5 cột                                       │    │
│  ├────────┬──────────┬──────┬────────┬──────────────────┤    │
│  │ ma_sv  │ ho_ten   │ tuoi │ lop_id │ email            │    │
│  ├────────┼──────────┼──────┼────────┼──────────────────┤    │
│  │ SV001  │ Nguyễn A │ 20   │ L01    │ a@school.edu.vn  │    │
│  │ SV002  │ Trần B   │ 21   │ L01    │ b@school.edu.vn  │    │
│  │ SV003  │ Lê C     │ 19   │ L02    │ c@school.edu.vn  │    │
│  │ ...    │ ...      │ ...  │ ...    │ ...              │    │
│  └────────┴──────────┴──────┴────────┴──────────────────┘    │
│                                                                 │
│  ┌─ classes.csv ───────────────────────────────────────────┐    │
│  │ 5 dòng × 3 cột                                         │    │
│  ├────────┬────────────────┬───────┐                       │    │
│  │ ma_lop │ ten_lop        │ khoa  │                       │    │
│  ├────────┼────────────────┼───────┤                       │    │
│  │ L01    │ CNTT-K18       │ CNTT  │                       │    │
│  │ L02    │ QTKD-K18       │ QTKD  │                       │    │
│  │ ...    │ ...            │ ...   │                       │    │
│  └────────┴────────────────┴───────┘                       │    │
│                                                                 │
│  ┌─ scores.csv ────────────────────────────────────────────┐    │
│  │ 600 dòng × 4 cột                                       │    │
│  ├──────────┬────────┬───────┬──────┐                      │    │
│  │ id_diem  │ ma_sv  │ mon   │ diem │                      │    │
│  ├──────────┼────────┼───────┼──────┤                      │    │
│  │ 1        │ SV001  │ Toán  │ 8.5  │                      │    │
│  │ 2        │ SV001  │ Lý    │ 7.0  │                      │    │
│  │ 3        │ SV002  │ Toán  │ 9.0  │                      │    │
│  │ ...      │ ...    │ ...   │ ...  │                      │    │
│  └──────────┴────────┴───────┴──────┘                      │    │
└─────────────────────────────────────────────────────────────────┘
```

#### Bước 2: Xác nhận Khóa chính (PK)

Thuật toán `_infer_primary_key()` tick sẵn cột mà nó nghĩ là PK. User có thể sửa:

```text
┌─────────────────────────────────────────────────────────────────┐
│  🔑 XÁC NHẬN KHÓA CHÍNH (PRIMARY KEY)                         │
│                                                                 │
│  Hệ thống đã đánh dấu cột mà nó cho là khóa chính.            │
│  Bạn có thể thay đổi nếu không đúng.                          │
│                                                                 │
│  students.csv:                                                  │
│    (•) ma_sv  ← Gợi ý: giá trị không trùng, tên chứa "mã"     │
│    ( ) ho_ten                                                   │
│    ( ) tuoi                                                     │
│    ( ) lop_id                                                   │
│    ( ) email                                                    │
│                                                                 │
│  classes.csv:                                                   │
│    (•) ma_lop  ← Gợi ý: giá trị không trùng, tên chứa "mã"    │
│    ( ) ten_lop                                                  │
│    ( ) khoa                                                     │
│                                                                 │
│  scores.csv:                                                    │
│    (•) id_diem  ← Gợi ý: giá trị không trùng, tên chứa "id"   │
│    ( ) ma_sv                                                    │
│    ( ) mon                                                      │
│    ( ) diem                                                     │
│                                                                 │
│  ℹ️ Nếu bảng không có khóa chính, chọn "Không có".             │
│    [Không có khóa chính cho bảng này]                           │
│                                                                 │
│  [← Quay lại]    [Tiếp tục xác nhận quan hệ →]                │
└─────────────────────────────────────────────────────────────────┘
```

#### Bước 3: Xác nhận Quan hệ FK

Thuật toán `infer_relationships()` tick sẵn các cặp FK. Kèm theo % coverage để user tham khảo:

```text
┌─────────────────────────────────────────────────────────────────┐
│  🔗 XÁC NHẬN QUAN HỆ GIỮA CÁC BẢNG                           │
│                                                                 │
│  Hệ thống phát hiện các mối quan hệ tiềm năng dựa trên        │
│  dữ liệu thực tế. Bạn hãy kiểm tra và điều chỉnh.            │
│                                                                 │
│  ─── Quan hệ được gợi ý ───────────────────────────────────    │
│                                                                 │
│  [✓] students.lop_id  →  classes.ma_lop                        │
│      Coverage: 100% (150/150 giá trị khớp)                     │
│      Confidence: 0.92                                           │
│                                                                 │
│  [✓] scores.ma_sv  →  students.ma_sv                           │
│      Coverage: 100% (600/600 giá trị khớp)                     │
│      Confidence: 0.95                                           │
│                                                                 │
│  ─── Quan hệ nghi ngờ (coverage thấp) ──────────────────────   │
│                                                                 │
│  [ ] scores.diem  →  students.tuoi                              │
│      Coverage: 65% — ⚠️ Có thể là trùng hợp giá trị số        │
│      Confidence: 0.42                                           │
│                                                                 │
│  ─── Thêm quan hệ thủ công ─────────────────────────────────   │
│                                                                 │
│  [+ Thêm quan hệ mới]                                          │
│  Bảng con: [dropdown]  Cột: [dropdown]                          │
│  Bảng cha: [dropdown]  Cột: [dropdown]                          │
│                                                                 │
│  [← Quay lại]    [Xác nhận và chạy phân tích ▶]               │
└─────────────────────────────────────────────────────────────────┘
```

**Các yếu tố UX quan trọng:**

1. **Phân vùng rõ ràng**: Chia thành "Gợi ý tốt" (tick sẵn) và "Nghi ngờ" (không tick) dựa trên confidence.
2. **Coverage hiển thị trực quan**: User thấy "100% giá trị khớp" thì biết ngay là đúng, thấy "65%" thì cảnh giác.
3. **Cho phép thêm thủ công**: User có thể thêm quan hệ mà thuật toán bỏ sót.
4. **Nút "Bỏ qua"**: User có thể bỏ qua bước này hoàn toàn nếu chỉ muốn phân tích từng bảng độc lập.

#### Bước 4: Chọn bảng chính (Fact Table) — Phục vụ Trụ cột 3

Sau khi xác nhận PK/FK, hệ thống hỏi user **bảng nào là bảng chính** (Fact) để làm trục tính tương quan chéo ở Trụ cột 3. Thuật toán gợi ý mặc định dựa trên row_count + out-degree, user có thể thay đổi.

```text
┌─────────────────────────────────────────────────────────────────┐
│  📌 CHỌN BẢNG CHÍNH (FACT TABLE)                                │
│                                                                 │
│  Bảng chính sẽ được dùng làm trục để tính tương quan chéo      │
│  giữa các bảng. Thường là bảng giao dịch / sự kiện / kết quả. │
│                                                                 │
│  (•) scores    ← Gợi ý: 600 dòng, nhiều FK nhất (2 FK)        │
│  ( ) students  (150 dòng, 1 FK)                                 │
│  ( ) classes   (5 dòng, 0 FK)                                   │
│                                                                 │
│  [← Quay lại]    [Xác nhận và chạy phân tích ▶]               │
└─────────────────────────────────────────────────────────────────┘
```

### Tóm tắt quyết định Trụ cột 2

| Quyết định | Chi tiết |
|:---|:---|
| Thuật toán scoring của Long | Giữ nguyên, làm "gợi ý thông minh" |
| LLM chốt FK | Không dùng — human đã là người chốt, LLM thừa |
| Human-in-the-loop | **Bắt buộc** ở Precise Mode (Web UI), tùy chọn ở Quick Mode (CLI) |
| Quick Mode | Thuật toán tự chốt, gắn cờ `inferred`, phù hợp demo/batch |
| Precise Mode | Thuật toán gợi ý, UI hiển thị data mẫu + tick/bỏ tick, user chốt |
| Chọn Fact Table | User chỉ định bảng chính (Precise Mode); thuật toán tự chọn (Quick Mode). Xem Trụ cột 3 Bước 3.1 |
| Single-table | Trụ cột 2 không chạy, không có vấn đề |

---

## Trụ cột 3: Cross-table Correlation Engine

### Trạng thái: 🔄 THIẾT KẾ HOÀN CHỈNH, CHƯA CODE — Cần triển khai

### Vấn đề gốc

Sau khi Trụ cột 2 xác định được schema (quan hệ PK-FK giữa các bảng), hệ thống cần tính tương quan giữa các cột **khác bảng** (Cross-table Correlation). Đây là tính năng cốt lõi tạo ra giá trị khác biệt so với ydata-profiling (vốn chỉ hỗ trợ single-table). Tuy nhiên, việc gộp bảng (JOIN) gặp 3 rủi ro lớn:

1. **Fan-out OOM**: Khi LEFT JOIN, nếu khóa bảng Dimension không Unique, 1 dòng Fact nhân bản thành N dòng → nổ RAM.
2. **Sai lệch thống kê**: Khi JOIN, dữ liệu Dimension bị duplicate theo số dòng Fact → Mean/Median/Distribution bị méo.
3. **Xóa nhầm cột**: Luật "Cardinality > 95% thì xóa" vô tình xóa sạch cột Tiền tệ và Ngày tháng.

### Quyết định kiến trúc: Dual-Pass Profiling + Mini-batch Safe Join + Phik

**Nguyên tắc cốt lõi:**
- **Lượt 1** (Single-table): ydata-profiling chạy riêng từng bảng → Correlation nội bảng chính xác 100%.
- **Lượt 2** (Cross-table): Dùng chiến lược **Mini-batch per Dimension** — chỉ JOIN Fact với **1 bảng Dimension tại một thời điểm** — sau đó tính `phik_matrix()` cho batch đó.
- **Phương pháp tương quan**: Dùng **Phik (φₖ)** cho toàn bộ — xử lý được Numeric, Categorical, và Mixed types mà không cần code riêng từng loại.

---

### Lượt 1: Single-table Profiling — Đã code xong

Mỗi bảng được chạy profiling **hoàn toàn độc lập** bằng ydata-profiling Full Mode. Vì không có JOIN, mọi thông số (Mean, Median, Missing Count, Outliers, Correlation nội bảng) được bảo toàn chính xác 100%.

**Code hiện tại:** `run_pipeline.py` → `run_multi()` → vòng lặp `_profile_data_quality()` cho từng bảng.

**Output của Lượt 1:** Mỗi bảng có 1 ma trận correlation nội bảng riêng (do ydata tính sẵn, lấy từ JSON output `report_dict["correlations"]`).

**ydata hỗ trợ 5 phương pháp correlation:**

| Phương pháp | Áp dụng cho | Cách hoạt động |
|:---|:---|:---|
| Pearson | Numeric ↔ Numeric | Tương quan tuyến tính |
| Spearman | Numeric ↔ Numeric | Tương quan đơn điệu (xếp hạng) |
| Kendall | Numeric / Ordinal | Tương quan thứ bậc |
| Cramér's V | Categorical ↔ Categorical | Liên kết giữa 2 biến phân loại |
| **Phik (φₖ)** | **Mọi kiểu** (Numeric, Categorical, Mixed) | Bắt cả quan hệ phi tuyến, dựa trên chi-squared |

> **Lưu ý về cột Text:** ydata **không tự tính correlation cho cột raw text** (ghi chú tự do, mô tả dài). Tuy nhiên, nếu cột text có giá trị lặp lại (ví dụ: "Đã giao", "Đang xử lý", "Hủy") → ydata nhận diện là **Categorical** → tính được Cramér's V và Phik. Cột text high-cardinality (mỗi dòng khác nhau) bị loại khỏi correlation matrix — đây là hành vi đúng.

---

### Lượt 2: Cross-table Correlation — Chưa code

Mục tiêu duy nhất: Tính hệ số tương quan giữa các cột **khác bảng**.

#### Tại sao chọn Mini-batch thay vì Pairwise hoặc Universal Table?

Có 3 chiến lược JOIN để tính tương quan chéo. Sau khi phân tích, chúng ta chọn **Mini-batch per Dimension** vì nó cân bằng tốt nhất giữa tốc độ, RAM, và khả năng chịu lỗi:

| Chiến lược | Mô tả | Tốc độ | RAM | Chịu lỗi |
|:---|:---|:---:|:---:|:---:|
| **Pairwise (2 cột/lần)** | Mỗi cặp cột ghép riêng → gọi phik riêng | ❌ Chậm (200 lần gọi phik, mỗi lần có overhead khởi tạo binning) | ✅ Rất thấp | ✅ Cặp nào lỗi skip cặp đó |
| **Universal Table** | JOIN tất cả Dim vào Fact → 1 bảng khổng lồ | ✅ Nhanh (1 lần phik_matrix) | ❌ Cao (tất cả Dim cùng lúc) | ❌ 1 Dim lỗi → abort toàn bộ |
| **Mini-batch per Dim** ✅ | JOIN Fact + 1 Dim mỗi lần → phik_matrix() cho batch đó | ✅ Nhanh (N_dims lần phik_matrix, vectorized) | ✅ Thấp (chỉ Fact + 1 Dim) | ✅ Dim nào lỗi skip Dim đó |

**Ví dụ tính toán cụ thể:**

```text
Scenario: Fact (100k dòng, 10 cột measure) + 4 bảng Dim (mỗi bảng 5 cột measure)

Pairwise:   10 × 20 = 200 lần gọi phik riêng lẻ, mỗi lần ~200ms → ~40 giây ❌
Universal:  1 lần JOIN + 1 lần phik_matrix(30 cột) → ~12 giây ✅ nhưng RAM cao ❌
Mini-batch: 4 lần JOIN nhỏ + 4 lần phik_matrix(15 cột) → ~15 giây ✅, RAM thấp ✅
```

Lý do phik nhanh hơn khi gọi matrix thay vì từng cặp: `phik_matrix()` **chia sẻ binning** — binning cho mỗi cột chỉ tính 1 lần rồi tái sử dụng cho tất cả cặp trong matrix. Gọi riêng lẻ 200 lần = tính binning 200 lần.

---

#### Bước 3.1: Xác định bảng Fact

**Bản chất:** Cần một bảng "gốc" (thường là bảng giao dịch/sự kiện) để làm trục gộp dữ liệu từ các bảng vệ tinh.

**Logic dự kiến:** Chọn deterministic dựa trên:
- Bảng có số dòng lớn nhất → Có khả năng là Fact
- Bảng có nhiều FK trỏ ra (out-degree cao) → Đang tham chiếu nhiều bảng khác
- Bảng có cột datetime → Thường lưu lịch sử sự kiện

**Rủi ro Bridge Table:** Bảng nối nhiều-nhiều (ví dụ: `student_courses` với FK→students và FK→courses) có out-degree cao, row_count lớn → dễ bị nhận nhầm là Fact. Nếu bảng có rất ít cột (< 5) nhưng out-degree ≥ 2 → nên đánh dấu là Bridge Table, không chọn làm Fact.

**Giải pháp tối ưu:** Vì Trụ cột 2 đã có Human-in-the-loop, user có thể **trực tiếp chỉ định bảng nào là bảng chính (Fact)** trong bước xác nhận schema. Thuật toán chỉ đóng vai trò **gợi ý mặc định** — nếu user không chọn, dùng heuristic trên; nếu user chọn, dùng lựa chọn của user.

---

#### Bước 3.2: Lọc cột theo Dtype + Confirmed Schema (Dtype-Aware Filter)

**Bản chất:** Không phải cột nào cũng có ích khi tính tương quan. Cột UUID, ghi chú tự do, và đặc biệt cột PK/FK sẽ làm rác kết quả.

**Logic lọc cột:**

| Dtype | Điều kiện | Hành động | Lý do |
|:---|:---:|:---|:---|
| String/Object | Cardinality > 95% | ❌ Loại bỏ | UUID, text tự do — mỗi dòng khác nhau, không có ý nghĩa thống kê |
| String/Object | Cardinality ≤ 95% | ✅ Giữ lại | Categorical có giá trị — "Trạng thái đơn hàng", "Giới tính", etc. Phik tính được. |
| Numeric | Là PK/FK (theo confirmed schema) | ❌ Loại bỏ | Không có ý nghĩa phân tích — chỉ là mã liên kết |
| Numeric | Không phải PK/FK | ✅ Giữ lại | Tiền, tuổi, lương — luôn có giá trị phân tích |
| Datetime | Bất kỳ | ✅ Giữ lại | Có thể trích xuất feature (ngày, tháng, quý) |

**Điểm cải tiến so với phiên bản cũ:** Thay vì dùng heuristic tên cột ("id", "ma", "code") để đoán ID-like Numeric, giờ chúng ta **dùng trực tiếp confirmed_schema từ Trụ cột 2** — user đã tick cột nào là PK/FK → tự động loại khỏi correlation set. Chính xác 100%, không cần đoán.

---

#### Bước 3.3: Safe Join — Exact Dedupe + Unique Check + Fan-out Guard

Đây là phần thiết kế **quan trọng nhất** của Trụ cột 3. Mỗi lượt Mini-batch (Fact + 1 Dim) đều phải chạy qua 3 lớp bảo vệ:

##### Bước 3.3a: `drop_duplicates()` exact rows — Cứu vãn dữ liệu bẩn

**Logic:**
```python
# Chỉ áp dụng trên BẢN SAO của bảng Dimension, không sửa data gốc
dim_clean = df_dim.drop_duplicates()
n_deduped = len(df_dim) - len(dim_clean)
if n_deduped > 0:
    emit("DEDUPED_DIMENSION_ROWS", table=dim_name, removed=n_deduped)
```

**Ví dụ:**
```text
Trước:  [{id:1, name:"An"}, {id:1, name:"An"}, {id:2, name:"Bình"}]
         → id có giá trị 1 xuất hiện 2 lần → NOT Unique

Sau drop_duplicates():
         [{id:1, name:"An"}, {id:2, name:"Bình"}]
         → id Unique ✅ → Có thể JOIN an toàn
```

**Tại sao cần bước này?** Dữ liệu export từ SQL thực tế rất hay bị dính duplicate rows (do lệnh JOIN trong câu query export hoặc user lỡ xuất 2 lần). Bước này "cứu" được ~90% trường hợp mà không làm sai dữ liệu (chỉ xóa dòng giống 100%).

##### Bước 3.3b: Unique Check sau Dedupe

**Logic:**
```python
if not dim_clean[join_key].is_unique:
    emit("NON_UNIQUE_JOIN_KEY", table=dim_name, column=join_key)
    # SKIP bảng Dimension này — các Dim khác vẫn chạy bình thường
    continue
```

**Ví dụ khi vẫn non-unique sau dedupe:**
```text
[{id:1, name:"An", age:20}, {id:1, name:"Bình", age:30}]
→ id = 1 xuất hiện 2 lần nhưng NỘI DUNG KHÁC NHAU
→ Đây là lỗi dữ liệu thật sự → Không thể JOIN an toàn
```

**Tại sao không dùng `groupby().first()` để "sửa"?** Vì nếu có 2 user cùng ID:
- An (nữ, 20 tuổi)
- Bình (nam, 30 tuổi)

`first()` sẽ giữ An, xóa Bình → Mọi đơn hàng của Bình bị gán thông tin của An → **Silent Data Corruption** — sai mà không ai biết, nguy hiểm hơn lỗi hiển thị. Triết lý: **thà mất insight chéo của 1 bảng Dim còn hơn làm sai dữ liệu**.

##### Bước 3.3c: Fan-out Guard — Kiểm tra sau JOIN

**Logic:**
```python
merged = pd.merge(
    fact_df[fact_measure_cols + [fk_col]],
    dim_clean[dim_measure_cols + [pk_col]],
    left_on=fk_col,
    right_on=pk_col,
    how="left"
)

if len(merged) > len(fact_df):
    emit("FAN_OUT_JOIN_RISK", expected=len(fact_df), actual=len(merged))
    continue  # Abort bảng Dim này, chạy tiếp Dim khác
```

**Lý do:** LEFT JOIN đúng cách (Parent key Unique) **không bao giờ** tăng số dòng so với bảng Fact. Nếu tăng → có lỗi logic hoặc dữ liệu → abort bảng Dim đó.

**Lưu ý quan trọng:** Chỉ lấy **các cột cần thiết** (measure cols + join key) vào `pd.merge()`, không merge toàn bộ bảng → giảm RAM đáng kể.

---

#### Bước 3.4: Tính Correlation bằng Phik

##### Tại sao chọn Phik?

| Tiêu chí | Pearson/Spearman | Cramér's V | **Phik (φₖ)** ✅ |
|:---|:---:|:---:|:---:|
| Numeric ↔ Numeric | ✅ | ❌ | ✅ |
| Categorical ↔ Categorical | ❌ | ✅ | ✅ |
| Numeric ↔ Categorical | ❌ | ❌ (cần encode) | ✅ |
| Quan hệ phi tuyến | ❌ | Hạn chế | ✅ |
| Đã là dependency? | Cần import riêng | Cần import riêng | ✅ (ydata-profiling kéo theo phik) |

**Phik xử lý mọi dtype mà không cần code riêng từng loại.** Nó dựa trên chi-squared contingency test — tự binning cho numeric, tự xử lý categorical. Đây là dependency có sẵn (ydata-profiling ≥ 4.0 bắt buộc cài phik).

##### Logic tính correlation cho mỗi Mini-batch

```python
# Sau khi Safe Join thành công → merged là bảng Fact + 1 Dim
# Chỉ giữ lại measure columns (đã loại PK/FK/text-rác ở Bước 3.2)
calc_cols = fact_measure_cols + dim_measure_cols
mini_df = merged[calc_cols]

# phik_matrix() tính tất cả cặp correlation trong 1 lần gọi
# Vectorized, chia sẻ binning → nhanh hơn nhiều so với gọi từng cặp
corr_matrix = mini_df.phik_matrix()

# Trích kết quả CHÉO bảng (Fact_col × Dim_col)
# Bỏ qua kết quả nội bảng (Fact×Fact, Dim×Dim) vì đã có ở Lượt 1
for f_col in fact_measure_cols:
    for d_col in dim_measure_cols:
        cross_results.append({
            "fact_column": f_col,
            "dim_table": dim_name,
            "dim_column": d_col,
            "correlation": round(float(corr_matrix.loc[f_col, d_col]), 4),
            "method": "phik",
            "n_samples": int(mini_df[[f_col, d_col]].dropna().shape[0]),
        })
```

---

#### Bước 3.5: Ghép kết quả Nội bảng + Chéo bảng

Sau khi Lượt 1 (ydata) và Lượt 2 (mini-batch phik) hoàn tất, chúng ta có 2 nguồn dữ liệu:

| Nguồn | Nội dung | Ví dụ |
|:---|:---|:---|
| Lượt 1 (ydata) | Correlation nội bảng students | students.tuoi ↔ students.lop_id = 0.12 |
| Lượt 1 (ydata) | Correlation nội bảng scores | scores.diem ↔ scores.mon = 0.45 |
| Lượt 2 (mini-batch) | Correlation chéo students × scores | students.tuoi ↔ scores.diem = 0.35 |

**Ghép thành 1 ma trận thống nhất:**

```text
Ma trận Tương quan Toàn cục (Phik)

                  students.tuoi  students.lop_id  scores.diem  scores.mon
students.tuoi         1.00           0.12        │   0.35        0.08
students.lop_id       0.12           1.00        │   0.72        0.15
──────────────────────────────────────────────────┤
scores.diem           0.35           0.72        │   1.00        0.45
scores.mon            0.08           0.15        │   0.45        1.00

Trong đó:
  ▪ Góc trên-trái + dưới-phải: Nội bảng — do ydata tính sẵn (Lượt 1)
  ▪ Góc trên-phải + dưới-trái: Chéo bảng — do mini-batch tính (Lượt 2)
```

**Logic ghép:**

```python
def merge_correlation_matrices(
    single_table_corrs: dict[str, pd.DataFrame],   # {"students": matrix, "scores": matrix}
    cross_table_results: list[dict],                 # Output từ mini-batch
) -> pd.DataFrame:
    """Ghép correlation nội bảng + chéo bảng thành 1 matrix thống nhất."""

    # 1. Thu thập tất cả tên cột (prefix bằng tên bảng)
    all_cols = []
    for table_name, corr_df in single_table_corrs.items():
        for col in corr_df.columns:
            all_cols.append(f"{table_name}.{col}")

    # 2. Tạo matrix NaN
    unified = pd.DataFrame(float("nan"), index=all_cols, columns=all_cols)

    # 3. Điền correlation nội bảng (từ ydata)
    for table_name, corr_df in single_table_corrs.items():
        for col_a in corr_df.columns:
            for col_b in corr_df.columns:
                unified.loc[f"{table_name}.{col_a}", f"{table_name}.{col_b}"] = corr_df.loc[col_a, col_b]

    # 4. Điền correlation chéo bảng (từ mini-batch)
    for r in cross_table_results:
        if r.get("correlation") is None:
            continue
        key_fact = f"fact_table.{r['fact_column']}"
        key_dim = f"{r['dim_table']}.{r['dim_column']}"
        if key_fact in unified.index and key_dim in unified.columns:
            unified.loc[key_fact, key_dim] = r["correlation"]
            unified.loc[key_dim, key_fact] = r["correlation"]  # Đối xứng

    return unified
```

---

### Trình bày kết quả — 3 góc nhìn

Học theo cách ydata trình bày (tabs chuyển đổi + heatmap tương tác), nhưng mở rộng cho multi-table:

#### Tab 1: Nội bảng (Intra-table)

```text
┌─────────────────────────────────────────────────────────────────┐
│  📊 TƯƠNG QUAN (CORRELATIONS)                                   │
│                                                                 │
│  [Tab: Nội bảng ▼]  [Tab: Chéo bảng]  [Tab: Toàn cục]         │
│                                                                 │
│  Chọn bảng: [students ▼]                                       │
│  Chọn phương pháp: [Phik ▼] [Pearson] [Spearman] [Cramér's V] │
│                                                                 │
│  ┌──────────────────────────────┐                               │
│  │       tuoi  lop_id  email   │  ← Heatmap do ydata tính sẵn  │
│  │ tuoi  ████   ░░░░   ░░░░   │                                │
│  │ lop_id ░░░░  ████   ░░░░   │  (Hover → hiện giá trị cụ thể)│
│  │ email  ░░░░  ░░░░   ████   │                                │
│  └──────────────────────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

**Nguồn dữ liệu:** 100% từ ydata (Lượt 1). Không cần code thêm — chỉ cần trích `report_dict["correlations"]["phi_k"]` từ JSON output.

#### Tab 2: Chéo bảng (Cross-table) — **Đây là USP của sản phẩm**

```text
┌─────────────────────────────────────────────────────────────────┐
│  [Tab: Nội bảng]  [Tab: Chéo bảng ▼]  [Tab: Toàn cục]         │
│                                                                 │
│  Chỉ hiện correlation giữa các cột KHÁC bảng (Phik).          │
│  Sắp xếp theo giá trị tương quan giảm dần.                    │
│                                                                 │
│  🔴 Tương quan mạnh (> 0.5)                                    │
│  ┌─────────────────────┬──────────────────┬───────┬──────────┐  │
│  │ Cột bảng Fact       │ Cột bảng Dim     │ Phik  │ Samples  │  │
│  ├─────────────────────┼──────────────────┼───────┼──────────┤  │
│  │ orders.total_amount │ users.age        │ 0.72  │ 99,200   │  │
│  │ orders.total_amount │ products.category│ 0.58  │ 98,100   │  │
│  └─────────────────────┴──────────────────┴───────┴──────────┘  │
│                                                                 │
│  🟡 Tương quan trung bình (0.3 — 0.5)                          │
│  ┌─────────────────────┬──────────────────┬───────┬──────────┐  │
│  │ orders.total_amount │ users.gender     │ 0.35  │ 98,500   │  │
│  └─────────────────────┴──────────────────┴───────┴──────────┘  │
│                                                                 │
│  ⚪ Tương quan yếu (< 0.3): 12 cặp — [Hiện tất cả ▸]          │
│                                                                 │
│  ⚠️ Bảng bị bỏ qua:                                           │
│  │ products — NON_UNIQUE_JOIN_KEY (cột product_id)             │
└─────────────────────────────────────────────────────────────────┘
```

**Nguồn dữ liệu:** 100% từ mini-batch (Lượt 2).

#### Tab 3: Toàn cục (Global Matrix)

```text
┌─────────────────────────────────────────────────────────────────┐
│  [Tab: Nội bảng]  [Tab: Chéo bảng]  [Tab: Toàn cục ▼]         │
│                                                                 │
│  Heatmap tổng hợp tất cả cột từ mọi bảng (nội + chéo).       │
│  Viền phân cách giữa các bảng để dễ đọc.                      │
│                                                                 │
│  ┌───────────────────────────────────────────┐                  │
│  │        s.tuoi s.lop  │ sc.diem sc.mon     │                  │
│  │ s.tuoi  ████  ░░░░  │  ▓▓▓▓   ░░░░       │  Nội bảng       │
│  │ s.lop   ░░░░  ████  │  ████   ░░░░       │  (ydata)        │
│  │ ─────────────────────┤                    │                  │
│  │ sc.diem ▓▓▓▓  ████  │  ████   ▓▓▓▓       │  Chéo bảng      │
│  │ sc.mon  ░░░░  ░░░░  │  ▓▓▓▓   ████       │  (mini-batch)   │
│  └───────────────────────────────────────────┘                  │
│                                                                 │
│  Hover → hiện: "students.tuoi ↔ scores.diem = 0.35 (φₖ)"      │
└─────────────────────────────────────────────────────────────────┘
```

**Nguồn dữ liệu:** Ghép từ Lượt 1 + Lượt 2 bằng hàm `merge_correlation_matrices()`.

---

### JSON Output

```json
{
  "cross_table_correlations": {
    "method": "phik",
    "fact_table": "orders",
    "pairs": [
      {"fact_col": "total_amount", "dim_table": "users", "dim_col": "age", "value": 0.72, "n": 99200},
      {"fact_col": "total_amount", "dim_table": "users", "dim_col": "gender", "value": 0.35, "n": 98500},
      {"fact_col": "total_amount", "dim_table": "products", "dim_col": "category", "value": 0.58, "n": 98100}
    ],
    "skipped_dimensions": [
      {"table": "products", "reason": "NON_UNIQUE_JOIN_KEY", "column": "product_id"}
    ]
  }
}
```

LLM L4 đọc JSON này → viết nhận xét narrative: *"Tương quan mạnh nhất giữa các bảng: `total_amount` và `users.age` (φₖ = 0.72) — cho thấy tuổi khách hàng có ảnh hưởng đáng kể đến giá trị đơn hàng."*

---

### Edge Cases & Fail-safe

| Tình huống | Hành vi |
|:---|:---|
| Tất cả bảng Dim đều non-unique key | Báo user rõ ràng: "Không tìm thấy bảng nào có khóa duy nhất sau khi loại bỏ dòng trùng. Tương quan chéo không thể tính." |
| User upload chỉ 1 file | Trụ cột 3 KHÔNG CHẠY — chỉ có correlation nội bảng từ ydata |
| Bảng Dim quá nhỏ (< 30 dòng sau JOIN filter) | Skip cặp đó, ghi log |
| phik_matrix() lỗi (collinear, constant column) | Try/except → skip Dim đó, ghi lỗi vào `skipped_dimensions` |

---

### Tổng kết Trụ cột 3

```text
Lượt 1 (ĐÃ CODE):
  Từng bảng → ydata-profiling Full Mode → correlation nội bảng (Pearson, Spearman, Phik, Cramér's V)

Lượt 2 (CHƯA CODE):
  Duyệt từng bảng Dimension:
    → Dedupe → Unique check → Mini JOIN (Fact + 1 Dim)
    → Fan-out guard
    → phik_matrix() cho batch
    → Trích kết quả chéo bảng
  Ghép nội bảng + chéo bảng → Ma trận toàn cục
  → cross_table_correlations.json
```

**Ưu tiên triển khai:** Tạo file `src/engines/cross_table_engine.py` với các hàm chính:
- `select_fact_table(tables, relationships, user_choice=None) → str`
- `select_measure_columns(df, confirmed_schema) → list[str]`
- `safe_join_single_dim(fact_df, dim_df, fk_col, pk_col) → DataFrame | None`
- `compute_cross_correlations(fact_df, dimensions, confirmed_schema) → list[dict]`
- `merge_correlation_matrices(single_table_corrs, cross_results) → pd.DataFrame`

---

## Trụ cột 4: Sampling Metadata

### Trạng thái: ✅ ĐÃ GIẢI QUYẾT — Đã code xong, đang hoạt động

### Vấn đề gốc

Báo cáo không nói rõ dữ liệu đã bị cắt mẫu (sample) → User lầm tưởng về quy mô dữ liệu → Ảo giác thống kê.

### Quyết định kiến trúc

Bổ sung 5 trường bắt buộc vào `DatasetMeta`:

```python
# src/ontology/models.py
class DatasetMeta(BaseModel):
    ...
    is_sampled: bool = False
    original_n: Optional[int] = None
    sample_n: Optional[int] = None
    sample_method: Optional[str] = None
    sample_seed: Optional[int] = None
```

### Code đã triển khai

| File | Chức năng |
|:---|:---|
| `src/ontology/models.py` L27-31 | Pydantic model với 5 trường sampling |
| `src/reporting/l4_report.py` L80-86 | Report hiển thị sampling info nếu `is_sampled=True` |
| `src/sampling.py` | Logic `sample_if_large()` cắt mẫu khi > 500k dòng |
| `run_pipeline.py` | Truyền sampling metadata vào DatasetMeta |

### Đánh giá

Sạch sẽ, đơn giản, hiệu quả. Random Sampling đủ cho MVP, không overengineer sang Stratified Sampling.

---

## Trụ cột 5: Severity Stack & Verdict

### Trạng thái: ⚠️ CẦN ĐÁNH GIÁ THÊM — Phần lớn đã code, một số điểm cần sửa

### Vấn đề gốc

Trụ cột này gộp 5 vấn đề con từ Problem gốc:

| Mã | Vấn đề | Bản chất |
|:---|:---|:---|
| 6 | `dataset_verdict.json` nhồi nhét 1000 lỗi | Token tràn, LLM bị ngợp |
| 7.3 | Hai file JSON báo cáo lệch nhau | `calibrator.py` tính severity nhưng không ghi lại vào findings |
| 7.4 | Compound cộng dồn INFO thành CRITICAL | Logic escalation sai bản chất |
| 7.5 | Missingness gán chung 1 p-value cho tất cả cột | Đánh đồng cơ chế thiếu dữ liệu |
| 7.6 | 50 lỗi WARN vẫn cho ra READY | Ngưỡng verdict quá lỏng lẻo |

### 5A: Verdict JSON gọn nhẹ (Vấn đề 6)

**Trạng thái: ✅ ĐÃ GIẢI QUYẾT**

**Logic của Long:**

Thay vì nhồi nhét toàn bộ 1000 lỗi vào `dataset_verdict.json`, Long tạo cơ chế `top_issues` + `detail_ref`:

```python
# src/severity/aggregator.py → _top_issues()
# 1. Thu thập tất cả findings (DQ + Schema Integrity)
# 2. Sắp xếp theo effective_severity DESC, affected_count DESC, confidence DESC
# 3. Cắt lấy top 10
# 4. Mỗi issue có detail_ref trỏ về file findings gốc:
#    detail_ref = {
#        "file": "data_quality_findings.json",
#        "collection": "anomalies",
#        "index": 3  ← Dòng thứ 3 trong mảng anomalies
#    }
```

**Kết quả:** `dataset_verdict.json` cực kỳ gọn (~2KB thay vì ~200KB). LLM đọc nhanh, không bị ngợp. Chi tiết lỗi nằm ở file findings riêng, ai cần thì tra cứu theo `detail_ref`.

**Đánh giá:** ✅ Xuất sắc. Đúng pattern Reference Architecture.

### 5B: Compound Severity (Vấn đề 7.4)

**Trạng thái: ✅ ĐÃ SỬA LOGIC, cần kiểm tra thêm**

**Logic hiện tại của Long:**

```python
# src/severity/compound.py

# Quy tắc 1: INFO KHÔNG tham gia compound escalation
def _is_participating(severity):
    return severity != Severity.INFO  # INFO bị loại khỏi phép tính

# Quy tắc 2: Nhóm findings theo affected_column
# Quy tắc 3: Findings multivariate (affected_column = None) luôn đi solo, không compound

# Quy tắc 4: Compound chỉ xảy ra khi:
#   - Có >= 2 findings từ WARN trở lên trên CÙNG CỘT
#   - Nếu có >= 2 HIGH hoặc max là CRITICAL → compound = CRITICAL
#   - Nếu max là HIGH (nhưng < 2 HIGH) → compound = HIGH

# Quy tắc 5: Khi compound xảy ra:
#   - Findings đang participating → compound_severity = mức compound
#   - Findings INFO → compound_severity = giữ nguyên INFO (không bị kéo lên)
```

**Ví dụ minh họa:**

```text
Cột "salary" có 3 findings:
  - MISSINGNESS (severity=WARN)
  - OUTLIER (severity=HIGH)
  - HIGH_CARDINALITY (severity=INFO)

Bước 1: Lọc participating → [WARN, HIGH] (INFO bị loại)
Bước 2: Có 2 findings participating → Compound kích hoạt
Bước 3: max_sev = HIGH, high_or_above = 1 (chỉ có 1 HIGH)
Bước 4: → compound = HIGH

Kết quả:
  - MISSINGNESS: compound_severity = HIGH (leo thang từ WARN)
  - OUTLIER: compound_severity = HIGH (giữ nguyên)
  - HIGH_CARDINALITY: compound_severity = INFO (giữ nguyên, không bị kéo)
```

**Đánh giá:**

> ✅ **Điểm mạnh:**
> - INFO không bị kéo lên → Đúng triết lý "không bắt người cảm cúm đi cấp cứu"
> - Phân tách rõ `severity` (gốc, bất biến) và `compound_severity` (effective, có thể leo thang)
> - Multivariate findings không bị compound theo cột → Tránh false escalation
>
> ⚠️ **Điểm cần kiểm tra:**
> - Dòng 22-24 trong `compound.py` có logic lặp:
>   ```python
>   if max_sev == Severity.HIGH:
>       return Severity.HIGH
>   return Severity.HIGH  # ← Luôn trả HIGH khi participating >= 2
>   ```
>   Hai nhánh `elif` và `else` đều trả `HIGH` — có vẻ là thiếu nhánh xử lý cho trường hợp `max_sev == WARN` (khi 2 findings đều là WARN thì compound nên giữ WARN chứ không lên HIGH). **Cần xác nhận lại intent của Long.**

### 5C: Missingness Classification (Vấn đề 7.5)

**Trạng thái: ⚠️ ĐÃ CÓ GIẢI PHÁP PHẦN NÀO — Cần đánh giá kỹ**

**Logic hiện tại của Long:**

```python
# src/severity/missingness.py

# Bước 1: Little's MCAR test → 1 p-value CHUNG cho toàn dataframe
mcar_p = little_mcar_pvalue(numeric_df)

# Bước 2: MAR heuristic per-column → Logistic Regression CV-AUC
# Với MỖI cột bị thiếu dữ liệu:
#   - Tạo target: is_missing_col = 1 nếu Null, 0 nếu không
#   - Predictors: tất cả cột numeric KHÁC
#   - Chạy Logistic Regression 3-fold CV
#   - Nếu AUC > 0.65 → Cột này bị thiếu PHỤ THUỘC cột khác → "MAR"

# Bước 3: Phân loại theo priority
# 1. Nếu auc > 0.65 → "MAR"      (thiếu có quy luật, phụ thuộc biến khác)
# 2. Nếu mcar_p >= 0.05 → "MCAR"  (thiếu hoàn toàn ngẫu nhiên)
# 3. Nếu mcar_p < 0.05 → "MNAR?"  (thiếu có chủ đích — NHƯNG chỉ là "tentative")
# 4. Khác → None (không đủ data để phân loại)
```

**Vấn đề Problem gốc đề cập:** Little's MCAR test chạy trên toàn dataframe → ra 1 p-value chung → gán cho TẤT CẢ cột bị thiếu. Cột Tuổi thiếu có chủ đích (MNAR) nhưng cột Email thiếu ngẫu nhiên (MCAR) → Cả hai bị gán chung label.

**Long đã giải quyết PHẦN NÀO:** MAR AUC tính PER-COLUMN (đúng). Nhưng Little's test vẫn là GLOBAL — nếu AUC <= 0.65, hệ thống rơi vào nhánh dùng `mcar_p` global → tất cả cột không-MAR đều bị gán chung label (MCAR hoặc MNAR?).

**Đánh giá:**

> ✅ **Điểm mạnh:**
> - MAR detection per-column bằng Logistic Regression là approach đúng và tiên tiến
> - `sample_missingness_frame()` ưu tiên giữ lại dòng có missing → Đảm bảo đủ sample cho ML
> - Ghi rõ `MNAR?` với dấu hỏi → Trung thực rằng MNAR không thể xác nhận 100% từ observed data
>
> ⚠️ **Điểm yếu:**
> - Little's test global vẫn là fallback cho non-MAR columns → Vẫn có khả năng đánh đồng
> - Tuy nhiên, Problem gốc đề xuất "Dummy Variable Correlation" nhưng bản adjusted của Long phản biện rằng code hiện tại (Logistic Regression) **xịn hơn** Dummy Correlation — và đây là nhận xét ĐÚNG. Logistic Regression per-column chính xác hơn đơn thuần tính Pearson correlation với biến dummy.
>
> **Đề xuất:** Giữ nguyên Logistic Regression approach hiện tại. Nếu muốn cải thiện: thay Little's test global bằng per-column chi-squared test — nhưng đây là Phase sau.

### 5D: Verdict Logic & Ngưỡng WARN (Vấn đề 7.6)

**Trạng thái: ❌ CHƯA GIẢI QUYẾT — Cần sửa**

**Logic hiện tại của Long:**

```python
# src/severity/aggregator.py L118-126

if summary.critical > 0:
    verdict = Verdict.NOT_READY
elif summary.high > 0:
    verdict = Verdict.WARN
else:
    verdict = Verdict.READY  # ← Dù có 100 WARN cũng vẫn READY
```

**Vấn đề:** 50 lỗi WARN vẫn cho ra READY. Một dataset bị xước 50 chỗ không thể dán nhãn "Sẵn sàng sử dụng".

**Đánh giá:**

> ❌ **Lỗ hổng nghiêm trọng mà bản adjusted của Long KHÔNG đề cập.** Bản Problem gốc (7.6) nêu rõ vấn đề này. Bản adjusted nhắc đến sửa compound nhưng không thiết lập ngưỡng WARN → Verdict.
>
> **Đề xuất sửa:**
> ```python
> if summary.critical > 0:
>     verdict = Verdict.NOT_READY
>     rationale = f"{summary.critical} CRITICAL finding(s) — data not ready for use"
> elif summary.high > 0:
>     verdict = Verdict.WARN
>     rationale = f"{summary.high} HIGH finding(s) — review before use"
> elif summary.warn > 10 or (meta.n_var > 0 and summary.warn / meta.n_var > 0.2):
>     verdict = Verdict.WARN
>     rationale = f"{summary.warn} WARN finding(s) exceed threshold — review before use"
> else:
>     verdict = Verdict.READY
> ```
>
> Logic: Nếu số WARN > 10 **HOẶC** WARN chiếm > 20% tổng số cột → Verdict = WARN thay vì READY.

### 5E: Risk Score

**Trạng thái: ✅ ĐÃ CÓ — Hoạt động tốt**

**Logic hiện tại:**
```python
# src/severity/aggregator.py → _risk_score()
# Mỗi finding được gán weight theo effective severity:
#   INFO = 0.0, WARN = 1.0, HIGH = 5.0, CRITICAL = 20.0
# risk_score = tổng weight / tổng cells (n × n_var)
```

**Đánh giá:** Hợp lý. Cho phép so sánh mức độ rủi ro giữa các dataset khác nhau.

### Tổng kết Trụ cột 5

| Phần | Trạng thái | Hành động |
|:---|:---:|:---|
| 5A: top_issues + detail_ref | ✅ Xong | Giữ nguyên |
| 5B: Compound rule fix | ✅ Phần lớn xong | Kiểm tra logic dòng 22-24 (WARN × 2 → nên giữ WARN hay lên HIGH?) |
| 5C: Missingness per-column | ✅ Phần lớn xong | Giữ Logistic Regression, cải thiện Little's test ở Phase sau |
| 5D: Ngưỡng WARN → Verdict | ❌ Chưa sửa | **Cần thêm ngưỡng WARN vào aggregator.py** |
| 5E: Risk Score | ✅ Xong | Giữ nguyên |

---

## Roadmap Ưu tiên Triển khai

| Ưu tiên | Công việc | Trụ cột | Độ phức tạp |
|:---:|:---|:---:|:---:|
| 1 | Thêm ngưỡng WARN vào `aggregator.py` | 5 | Thấp (5 dòng) |
| 2 | Kiểm tra logic compound dòng 22-24 | 5 | Thấp |
| 3 | Thiết kế + code UI xác nhận schema (Human-in-the-loop) | 2 | Trung bình |
| 4 | Tạo `cross_table_engine.py` (Safe Join + Correlation) | 3 | Cao |
| 5 | Viết eval test cases cho Schema Inference | 2 | Trung bình |
