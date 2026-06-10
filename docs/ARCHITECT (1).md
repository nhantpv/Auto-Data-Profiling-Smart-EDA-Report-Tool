# ARCHITECT.md — Kiến trúc hệ thống Smart EDA

> **Tài liệu này viết cho người MỚI TINH.** Bạn **không** cần biết lập trình, không cần biết thống kê. Mỗi khái niệm đều được giải thích bằng lời thường và có **ví dụ cụ thể**. Cứ đọc tuần tự từ trên xuống.
>
> Quy ước nhãn trạng thái dùng xuyên suốt tài liệu:
> - ✅ **ĐÃ XONG** — đã viết code, chạy được.
> - 📋 **KẾ HOẠCH v3.0** — đã có bản thiết kế, chưa code.
> - 💡 **ĐỀ XUẤT** — ý tưởng để bàn, chưa chốt.

---

## Mục lục

1. [Đọc trong 30 giây: hệ thống này làm gì?](#1-đọc-trong-30-giây-hệ-thống-này-làm-gì)
2. [Vấn đề thực tế nó giải quyết](#2-vấn-đề-thực-tế-nó-giải-quyết)
3. [Triết lý cốt lõi: "Máy đo số, AI viết lời"](#3-triết-lý-cốt-lõi-máy-đo-số-ai-viết-lời)
4. [Bức tranh tổng thể](#4-bức-tranh-tổng-thể)
5. [Đi qua từng tầng — kèm ví dụ xuyên suốt](#5-đi-qua-từng-tầng--kèm-ví-dụ-xuyên-suốt)
6. [Khi có NHIỀU bảng (multi-table)](#6-khi-có-nhiều-bảng-multi-table)
7. [Nâng cấp v3.0 — những quyết định mới](#7-nâng-cấp-v30--những-quyết-định-mới)
8. [Làm sao để tool không "nói dối"? (Guardrail & Provenance)](#8-làm-sao-để-tool-không-nói-dối-guardrail--provenance)
9. [Trạng thái: cái gì xong, cái gì chưa](#9-trạng-thái-cái-gì-xong-cái-gì-chưa)
10. [Bản đồ file mã nguồn](#10-bản-đồ-file-mã-nguồn)
11. [Từ điển thuật ngữ](#11-từ-điển-thuật-ngữ)

---

## 1. Đọc trong 30 giây: hệ thống này làm gì?

Hãy tưởng tượng bạn sắp **mua một chiếc xe cũ**. Trước khi mua, bạn đưa xe đi **kiểm định**: thợ kiểm tra máy móc, phanh, lốp… rồi đưa cho bạn **một tờ giấy chẩn đoán**: "Xe ổn / Xe có vấn đề ở chỗ này / Đừng mua xe này".

Hệ thống Smart EDA làm **đúng việc đó, nhưng cho FILE DỮ LIỆU**.

- **Đầu vào (Input):** một file dữ liệu (ví dụ file Excel/CSV danh sách nhân viên, đơn hàng, học sinh…).
- **Đầu ra (Output):** một bản **chẩn đoán** trả lời các câu hỏi: Dữ liệu này sạch hay bẩn? Lỗi nằm ở đâu? Nghiêm trọng cỡ nào? **Có nên đem ra dùng không?**

> ⚠️ **Điều quan trọng nhất cần nhớ:** Tool này **CHỈ CHẨN ĐOÁN, KHÔNG TỰ SỬA** dữ liệu. Giống như thợ kiểm định chỉ ra "phanh mòn" chứ không tự thay phanh. Việc sửa do con người quyết định.

**EDA** là viết tắt của *Exploratory Data Analysis* — "phân tích khám phá dữ liệu". Nói nôm na: bước **soi dữ liệu lần đầu** để hiểu nó trông như thế nào trước khi làm gì tiếp.

---

## 2. Vấn đề thực tế nó giải quyết

Trong thực tế, mỗi khi ai đó nhận một file dữ liệu mới, họ phải ngồi **soi bằng tay**: mở file lên, đếm xem cột nào thiếu nhiều ô trống, có giá trị nào vô lý (lương âm, tuổi 999), có dòng nào bị trùng… Việc này:

- **Tốn thời gian** (vài giờ cho mỗi file).
- **Dễ sót** (người mệt sẽ bỏ qua lỗi).
- **Không nhất quán** (mỗi người soi một kiểu).

Smart EDA **tự động hoá bước soi này**, làm trong vài giây, theo một quy trình cố định nên không sót và không phụ thuộc tâm trạng người soi.

---

## 3. Triết lý cốt lõi: "Máy đo số, AI viết lời"

Đây là **nguyên tắc xương sống** của toàn bộ hệ thống. Tên kỹ thuật là **"Deterministic-First, LLM-Last"**. Nghe đáng sợ nhưng ý rất đơn giản.

Có hai loại "công cụ" trong hệ thống:

**1. Công cụ tính toán (deterministic).** "Deterministic" nghĩa là: **đưa cùng một đầu vào thì luôn ra cùng một kết quả**, không bao giờ sai khác. Giống **máy tính bỏ túi**: bấm `2 + 2` thì luôn ra `4`, không bao giờ ra `5`. Các phép như "đếm số ô trống", "tính lương trung bình" là loại này — **chính xác 100%**.

**2. AI viết văn (LLM).** **LLM** = *Large Language Model* = mô hình ngôn ngữ lớn, ví dụ như ChatGPT. Nó **viết văn rất hay, rất tự nhiên**, nhưng có một tật nguy hiểm: nó có thể **"ảo giác" (hallucinate)** — tức **bịa ra con số hoặc sự việc nghe có vẻ đúng nhưng sai**. Ví dụ bạn hỏi "cột lương thiếu bao nhiêu %", nó có thể tự tin trả lời "khoảng 12%" trong khi thực tế là 40% — vì nó *đoán* chứ không *đếm*.

**Nguyên tắc của hệ thống:**

> Để **máy tính** lo phần **con số** (vì nó không bao giờ bịa). Để **AI** lo phần **viết lời giải thích** — nhưng AI **chỉ được dùng những con số máy đã tính sẵn**, tuyệt đối không được tự nghĩ ra số.

**Ví dụ đời thường:** Máy đo huyết áp cho ra con số `140/90` (chính xác, đó là máy). Bác sĩ nhìn con số đó rồi viết kết luận "huyết áp hơi cao, nên giảm muối" (đó là lời, là người). **Bác sĩ không tự bịa ra con số huyết áp.** Hệ thống này hoạt động y hệt: máy đo trước, AI viết sau.

Vì sao "LLM-Last" (AI đứng cuối)? Vì nếu để AI làm sớm, sai số của nó sẽ lan ra toàn bộ. Để nó ở cuối, sau khi mọi con số đã chốt, thì nó chỉ còn việc diễn đạt.

---

## 4. Bức tranh tổng thể

Hệ thống giống một **dây chuyền nhà máy**: dữ liệu đi vào một đầu, đi qua nhiều **trạm** (gọi là **Layer** = **tầng**), mỗi trạm làm một việc, rồi ra thành phẩm ở đầu kia.

```
   FILE DỮ LIỆU (vd: nhanvien.csv)
            │
            ▼
   ┌──────────────────────────────┐
   │ L0  Đọc file vào bộ nhớ      │  → biến file thành "bảng" máy hiểu được
   ├──────────────────────────────┤
   │ L1  Mô tả dữ liệu            │  → đếm, tính trung bình, đếm ô trống…
   ├──────────────────────────────┤
   │ L2a Tìm điểm bất thường      │  → phát hiện giá trị "lạc loài" (outlier)
   │ L2b Kiểm tra quan hệ bảng    │  → kiểm tra khoá chính/khoá ngoại
   ├──────────────────────────────┤
   │ L2.5 Chấm mức nghiêm trọng   │  → mỗi lỗi đáng lo cỡ nào? (INFO→CRITICAL)
   ├──────────────────────────────┤
   │ L3  Đóng gói thành 3 file    │  → kết quả ở dạng máy đọc được (JSON)
   ├──────────────────────────────┤
   │ L3.5 Vẽ biểu đồ              │  → hình ảnh minh hoạ
   ├──────────────────────────────┤
   │ L4  AI viết báo cáo + chặn   │  → văn bản cho người đọc, có "chốt chặn"
   │     bịa số (Guardrail)       │     chống AI bịa số
   └──────────────────────────────┘
            │
            ▼
   BÁO CÁO CUỐI cho người dùng
```

Từ đây trở đi ta đi qua **từng tầng một**, mỗi tầng kèm ví dụ.

---

## 5. Đi qua từng tầng — kèm ví dụ xuyên suốt

Để dễ hiểu, ta dùng **một ví dụ chung** cho mọi tầng. Giả sử có file `nhanvien.csv` như sau (cố tình để vài lỗi):

```
id,ho_ten,tuoi,luong,phong_ban,ngay_vao
1,Nguyen Van A,28,15000000,Kỹ thuật,2020-01-15
2,Tran Thi B,,18000000,Kinh doanh,2019-03-01      ← thiếu TUỔI
3,Le Van C,35,20000000,Kỹ thuật,                   ← thiếu NGÀY VÀO
1,Pham Thi D,42,950000000,Nhân sự,2021-06-10        ← id=1 bị TRÙNG + lương 950 triệu (bất thường)
5,Hoang Van E,31,,Kỹ thuật,2022-08-22              ← thiếu LƯƠNG
```

Mắt người nhìn cũng thấy 4 vấn đề: thiếu tuổi, thiếu ngày vào, thiếu lương, `id` bị trùng, và lương 950 triệu trông "lạc loài". Bây giờ xem hệ thống phát hiện chúng ra sao.

---

### Tầng L0 — Đọc file vào bộ nhớ (Ingestion)   ✅ ĐÃ XONG

**"Ingestion"** = "nạp/nuốt dữ liệu vào". Đây là cửa vào.

**Việc của tầng này:** mở file và biến nó thành một **"bảng" trong bộ nhớ** mà máy xử lý được. Bảng đó gọi là **DataFrame** — bạn cứ hình dung như **một sheet Excel** gồm các hàng và cột.

> ⚠️ **Đính chính (Red Team):** trong code tôi đọc (`registry.py`), tầng này mới đọc **`.csv`, `.xlsx`, `.parquet`** — **chưa có JSON reader**. Một số bản đánh giá nói repo thật đã thêm JSON/JSONL/NDJSON; đây là **[chưa xác minh]** với code đang soi. Đừng tin "đọc được mọi định dạng".

**Hai việc khéo léo tầng này lo sẵn:**

1. **Đọc được vài loại file** (CSV/Excel/Parquet) mà không bắt đổi định dạng.
2. **Lấy mẫu nếu file quá lớn (sampling).** Nếu file có hơn **500.000 dòng**, máy sẽ **bốc ngẫu nhiên** 500.000 dòng để xử lý cho nhanh, tránh treo máy. (Giống nồi canh quá to thì nếm một muỗng thay vì uống cả nồi.)

**Đầu vào:** file trên ổ đĩa. **Đầu ra:** một bảng (DataFrame) gồm 5 hàng, 6 cột như ví dụ trên.

> 🔴 **Hạt sạn đã xác nhận (Red Team):** Việc lấy mẫu hiện chạy **vô điều kiện** cho mọi bảng >500k dòng (`registry.py`). Với dữ liệu **nhiều bảng**, mẫu làm "bảng cha" thiếu dòng → kiểm tra khoá ngoại báo **"mồ côi" giả hàng loạt**. Ngoài ra mẫu **không được ghi lại** trong kết quả (xem Mục 9). Cách sửa: tầng kiểm cấu trúc/khoá phải chạy trên **toàn bộ** dữ liệu; chỉ profiling mới được lấy mẫu, và phải ghi rõ đã lấy mẫu.

---

### Tầng L1 — Mô tả dữ liệu (Profiling)   ✅ ĐÃ XONG (code đang để Full — xem đính chính)

**"Profiling"** = "lập hồ sơ" cho dữ liệu. Giống lập **lý lịch** cho từng cột.

**Việc của tầng này:** với mỗi cột, tính ra các con số mô tả. Ví dụ với cột `luong` trong file trên, nó tính: có bao nhiêu ô, bao nhiêu ô trống, giá trị nhỏ nhất, lớn nhất, trung bình…

Áp vào ví dụ, tầng L1 cho ra (đại khái):

| Cột | Kiểu | Số ô trống | Ghi chú |
|---|---|---|---|
| `id` | số | 0 | có giá trị trùng |
| `ho_ten` | chữ | 0 | |
| `tuoi` | số | 1 (dòng 2) | trung bình ≈ 34 |
| `luong` | số | 1 (dòng 5) | có 1 giá trị rất lớn (950 triệu) |
| `phong_ban` | chữ | 0 | 3 nhóm: Kỹ thuật, Kinh doanh, Nhân sự |
| `ngay_vao` | ngày | 1 (dòng 3) | |

Tầng này dùng một thư viện có sẵn tên là **ydata-profiling** (một công cụ chuyên đi "soi" dữ liệu).

> ⚠️ **Đính chính (Red Team):** trong code tôi đọc, `run_profiling` để **mặc định `minimal=False` (chế độ Full)** (`profiling_engine.py:30`) — tức **đang chạy Full chứ không phải tiết kiệm**. Một số bản đánh giá lại nói "đang minimal". Hai nguồn **mâu thuẫn** → cần xác minh trạng thái repo thật. (Lưu ý: nếu ai đó bật `minimal=True`, một số chỉ số như "imbalance" sẽ **lặng lẽ biến mất** và tầng chấm điểm phía sau bỏ sót lỗi tương ứng.)

---

### Tầng L2a — Tìm điểm bất thường (Anomaly / Outlier)   ✅ ĐÃ XONG (cần kiểm chứng thêm)

**Khái niệm "outlier" (điểm ngoại lai / lạc loài):** là một giá trị **khác hẳn phần còn lại**. Trong ví dụ, cột `luong` có các giá trị 15tr, 18tr, 20tr… rồi đột nhiên **950 triệu**. Con số 950 triệu là **outlier** — nó "lạc loài".

> **Ví dụ đời thường:** trong một lớp ai cũng cao 1m5–1m7, đột nhiên có một bạn cao 2m3. Bạn đó là "outlier" về chiều cao. Không hẳn là **sai**, nhưng **đáng để soi lại** (có thể nhập nhầm, có thể thật).

**Việc của tầng này:** tự động tìm các dòng "lạc loài" trong các cột **số**. Nó không dùng một thước đo duy nhất mà dùng **3 thuật toán cùng lúc** rồi "bỏ phiếu" — gọi là **ensemble** (hội đồng). Ba thuật toán tên là *Isolation Forest*, *ECOD*, *LOF* (bạn không cần nhớ tên, chỉ cần biết: dùng nhiều "giám khảo" cho chắc).

**Đầu ra:** danh sách các dòng bị nghi là bất thường, kèm "điểm số bất thường". Với ví dụ, nó chỉ ra **dòng 4 (lương 950 triệu)**.

> ⚠️ **Lưu ý trung thực:** Ngưỡng quyết định "thế nào là đủ lạc loài để báo" hiện được chỉnh cho khớp với vài bộ dữ liệu thử nhỏ, nên **chưa được kiểm chứng trên dữ liệu thật quy mô lớn**. Đây là một điểm cần làm chặt hơn (xem Mục 9).

---

### Tầng L2b — Kiểm tra cấu trúc & quan hệ bảng (Schema)   ✅ ĐÃ XONG

**"Schema"** = "bản thiết kế cấu trúc" của dữ liệu — quy định bảng có những cột gì, cột nào là "chìa khoá".

Cần hai khái niệm:

- **Khoá chính (Primary Key, PK):** cột dùng để **phân biệt từng dòng**, **không được trùng và không được trống**. Trong `nhanvien.csv`, `id` lẽ ra phải là khoá chính — mỗi nhân viên một `id` riêng.
- **Khoá ngoại (Foreign Key, FK):** cột trong bảng này **trỏ tới** khoá chính của bảng khác. (Sẽ rõ hơn ở Mục 6 khi có nhiều bảng.)

**Việc của tầng này:** kiểm tra các quy tắc cấu trúc, ví dụ:
- Khoá chính có bị **trùng** hay **trống** không?
- Một khoá ngoại có trỏ tới giá trị **không tồn tại** không? (gọi là *orphan* — "mồ côi")
- Kiểu dữ liệu có đúng không (cột tuổi mà chứa chữ)?

Áp vào ví dụ: tầng này phát hiện **`id=1` bị trùng** (dòng 1 và dòng 4 cùng `id=1`) → đây là lỗi **khoá chính trùng (PK duplicate)**, mức nghiêm trọng cao vì làm hỏng tính phân biệt dữ liệu.

Để biết cột nào là khoá chính/ngoại, tầng này đọc một file mô tả cấu trúc gọi là **DBML** (nếu người dùng cung cấp). Nếu **không có** DBML thì sao? → Hệ thống **tự đoán** (xem Mục 6).

---

### Tầng L2.5 — Chấm mức nghiêm trọng (Severity Stack)   ✅ ĐÃ XONG (cách chấm còn theo "kinh nghiệm")

Đây là tầng **"thông minh" nhất** của phần máy tính. Tìm ra lỗi là một chuyện; **lỗi đó đáng lo cỡ nào** lại là chuyện khác. Cột thiếu 2% dữ liệu thì kệ; thiếu 60% thì báo động đỏ. Tầng này lo việc **chấm điểm mức độ**.

**"Stack"** = "chồng" — vì nó gồm **nhiều bước xếp chồng lên nhau**:

#### Bước A — Phân loại kiểu "thiếu dữ liệu" (Missingness)

Khi một cột thiếu ô, **lý do thiếu** quan trọng hơn **số lượng thiếu**. Có 3 kiểu (tên hơi học thuật nhưng ví dụ rất dễ):

- **MCAR** — *thiếu hoàn toàn ngẫu nhiên*. Ví dụ: máy nhập liệu thỉnh thoảng treo, làm rớt ô ngẫu nhiên. Không theo quy luật nào. → **Ít đáng lo**, có thể tạm điền (impute).
- **MAR** — *thiếu phụ thuộc cột khác mà ta thấy được*. Ví dụ: nhân viên **trẻ** thường bỏ trống ô "số năm kinh nghiệm" (vì họ mới đi làm). Việc thiếu liên quan tới **tuổi** — mà tuổi thì ta thấy. → **Đáng lo vừa**.
- **MNAR** — *thiếu phụ thuộc chính cái giá trị bị giấu*. Ví dụ: người **lương rất cao** cố tình **không điền lương**. Lý do thiếu nằm ngay trong cái bị thiếu. → **Đáng lo nhất**.

> 🔑 **Điểm cực kỳ quan trọng (và rất trung thực của hệ thống):** **Không ai có thể chắc chắn 100% là MNAR chỉ bằng cách nhìn dữ liệu** — vì ta **không nhìn thấy** cái đã bị thiếu! Đây là một giới hạn toán học. Vì vậy hệ thống ghi nhãn là **"MNAR?"** (có dấu hỏi) chứ không khẳng định. Hãy nhớ điều này, ở Mục 8 ta sẽ thấy vì sao nó quan trọng để tool không "nói dối".

#### Bước B — Chấm điểm từng lỗi (Calibrator)

Hệ thống có một **bảng tra** (như bảng điểm chấm thi) để quy lỗi thành 4 mức:

| Mức | Ý nghĩa | Ví dụ |
|---|---|---|
| **INFO** | Chỉ để biết, không sao | Cột thiếu < 5% |
| **WARN** | Cảnh báo, nên xem | Cột thiếu 5–20% |
| **HIGH** | Nghiêm trọng | Cột thiếu 20–50%, hoặc cột chỉ có 1 giá trị |
| **CRITICAL** | Báo động đỏ | Cột thiếu > 50% |

#### Bước C — Lỗi kép thì leo thang (Compound)

Nếu **một cột dính nhiều lỗi cùng lúc**, mức độ được **nâng lên**. Ví dụ: cột `luong` vừa thiếu nhiều, **lại vừa** chứa nhiều số 0 vô lý → hai lỗi cộng hưởng → nâng từ HIGH lên **CRITICAL**.

> ⚠️ **Trung thực:** cách "2 cái WARN thì thành 1 cái HIGH" hiện là **quy ước theo kinh nghiệm**, chưa dựa trên căn cứ khoa học đo lường. Đây là điểm cần làm chặt (Mục 9).

#### Bước D — Tổng kết (Aggregator → Verdict)

Cuối cùng, hệ thống gom mọi lỗi lại và ra một **"phán quyết" (verdict)** cho cả bộ dữ liệu, gồm 3 mức:

- **READY** — dùng được.
- **WARN** — dùng được nhưng cẩn thận.
- **NOT_READY** — chưa nên dùng, phải xử lý lỗi trước.

Với `nhanvien.csv` (có khoá chính trùng + thiếu dữ liệu nhiều cột), kết quả sẽ là **NOT_READY**.

---

### Tầng L3 — Đóng gói thành 3 file JSON (Ontology)   ✅ ĐÃ XONG

**JSON** là một **định dạng văn bản mà cả máy lẫn người đều đọc được** — gồm các cặp "tên: giá trị". Đây là **"hợp đồng" (contract)** giữa phần máy tính và phần AI: máy ghi mọi kết quả ra JSON, AI chỉ được đọc từ JSON này.

Hệ thống xuất **3 file**:

1. **`data_quality_findings`** — mọi lỗi chất lượng dữ liệu trong từng cột.
2. **`schema_evaluation_findings`** — mọi lỗi về cấu trúc/quan hệ bảng.
3. **`dataset_verdict`** — phán quyết tổng + tóm tắt.

Một mẩu JSON ví dụ (rút gọn) cho file `dataset_verdict`:

```json
{
  "dataset_name": "nhanvien",
  "verdict": "NOT_READY",
  "verdict_rationale": "1 lỗi CRITICAL — chưa sẵn sàng dùng.",
  "summary": { "total_issues": 4, "critical": 1, "high": 1, "warn": 2, "info": 0 }
}
```

> 💡 Bạn đọc dòng `"verdict": "NOT_READY"` là hiểu ngay — đó là cái hay của JSON: máy ghi, người vẫn đọc được.

---

### Tầng L3.5 — Vẽ biểu đồ (Charts)   ✅ một phần

**Việc của tầng này:** vẽ hình minh hoạ, ví dụ một **biểu đồ chấm** trong đó các điểm bất thường (như lương 950 triệu) được **tô đỏ** để mắt người thấy ngay.

> 📋 **KẾ HOẠCH v3.0:** vị trí của tầng này sẽ **đổi** — xem Mục 7, mục "Bỏ việc cho AI nhìn ảnh".

---

### Tầng L4 — AI viết báo cáo + Guardrail chống bịa số   ❌ CHƯA XÂY DỰNG

Đây là tầng cuối, và **chưa được làm**. Theo thiết kế:

- AI (LLM) **đọc 3 file JSON** ở trên và **viết một báo cáo bằng lời** dễ hiểu cho người dùng. Ví dụ: *"Dữ liệu chưa sẵn sàng dùng. Vấn đề nghiêm trọng nhất là mã nhân viên bị trùng. Ngoài ra cột lương thiếu 20% và có một giá trị nghi nhập sai (950 triệu)."*
- **Guardrail** ("rào chắn") là một **bộ kiểm tra tự động** đứng giữa, **soi từng con số trong bài viết của AI** và đối chiếu với JSON. Nếu AI viết "thiếu 12%" mà JSON ghi 20% → Guardrail **chặn lại**. Đây chính là cơ chế **chống bịa** đã nói ở Mục 3.

Hiện tại hệ thống mới có một bản báo cáo **tạm thời do máy ghép cứng** (không phải AI viết), và thư mục Guardrail **còn trống**. Đây là **việc lớn còn lại** (Mục 9).

---

## 6. Khi có NHIỀU bảng (multi-table)

Thực tế dữ liệu thường **không nằm trong một bảng** mà nhiều bảng liên kết nhau. Ví dụ hệ thống trường học có 3 bảng:

```
schools (trường)              classes (lớp)                 students (học sinh)
─────────────────             ─────────────────             ────────────────────
id_school   ten_truong        class_id  school_id  ten_lop  student_id  class_id  truong_hoc  ho_ten
   1        THPT A               10         1       10A1        101         10         1       An
   2        THPT B               11         1       10A2        102         11         2       Bình
```

**Quan hệ giữa chúng:**
- `classes.school_id` trỏ tới `schools.id_school` → "lớp này thuộc trường nào".
- `students.class_id` trỏ tới `classes.class_id` → "học sinh này học lớp nào".
- `students.truong_hoc` cũng trỏ tới `schools.id_school` → "học sinh này thuộc trường nào".

Mỗi mũi tên đó là một **khoá ngoại (FK)**. Tầng L2b sẽ kiểm tra: ví dụ có học sinh nào ghi `truong_hoc = 9` mà trường số 9 **không tồn tại** không? Nếu có → lỗi **"mồ côi" (orphan FK)**.

**Hai vấn đề khó mà hệ thống xử lý được:**

**(a) Không có file mô tả cấu trúc (DBML)?** Hệ thống **tự đoán** quan hệ bằng cách so các cột giữa các bảng xem cột nào "khớp" với cột nào. ✅ Phần này đã chạy được.

**(b) Hai cột cùng nghĩa nhưng KHÁC TÊN?** Để ý: trường được gọi là `id_school` ở bảng `schools` nhưng lại là `truong_hoc` ở bảng `students`. Tên khác nhau hoàn toàn! Người mới nhìn cũng dễ tưởng không liên quan. Hệ thống vẫn **ghép đúng** được `students.truong_hoc → schools.id_school`. Đây gọi là **khớp ngữ nghĩa (semantic / alias matching)**.

> ⚠️ **Trung thực:** cách đoán hiện tại dùng các quy tắc **gài cứng trong code** (ví dụ danh sách từ đồng nghĩa cố định). Với lĩnh vực mới (y tế, tài chính…) các quy tắc này sẽ không đủ → cần nâng cấp (Mục 7).

---

## 7. Nâng cấp v3.0 — những quyết định mới   📋 KẾ HOẠCH

Sau khi nhận góp ý, đội đã ra một bản kế hoạch nâng cấp lớn. Dưới đây là các quyết định, giải thích đơn giản:

**1) Bỏ việc cho AI "nhìn ảnh".** Ý tưởng cũ là gửi *ảnh biểu đồ* cho AI để nó "nhìn" rồi viết. Nhưng AI nhìn ảnh thì **đắt tiền, chậm, và hay đọc sai** (đọc nhầm điểm trên biểu đồ). Quyết định mới: **AI chỉ đọc số (text), không nhìn ảnh.** Khi muốn có biểu đồ, AI **viết một "mã chỗ trống"** như `[CHART_LUONG_OUTLIER]` vào báo cáo; sau đó **một đoạn code Python tự vẽ biểu đồ thật và dán vào đúng chỗ đó**. → Vì vậy tầng L3.5 (vẽ) sẽ chạy **SAU** tầng L4 (AI viết), khác với sơ đồ ban đầu.

**2) Tự khám phá quan hệ bảng theo "phễu 2 tầng".** Để giải bài "không có DBML" một cách tốt hơn:
   - **Tầng lọc thô (toán học, miễn phí):** dùng **Jaccard Index** — chỉ là **tỷ lệ trùng nhau giữa hai tập giá trị**. Ví dụ tập `id` của bảng A và tập `id_school` của bảng B trùng nhau > 50% → nghi là một cặp khoá chính–ngoại. Cách này loại nhanh 95% các cặp không liên quan.
   - **Tầng chốt (AI ngữ nghĩa):** chỉ những cặp "lọt phễu" mới gửi cho AI hỏi "hai cột này có thật sự liên quan không?". → Vừa nhanh, vừa rẻ, vừa chính xác.

**3) Phân tích đa bảng "2 lượt" (Dual-Pass).** Có thể bạn nghĩ "cứ gộp hết các bảng làm một rồi tính". **Sai lầm lớn!** Vì:
   - Gộp xong bảng quá rộng → máy **hết RAM, treo**.
   - Gộp bảng giao dịch với bảng khách hàng → thông tin khách hàng bị **nhân bản**. Ví dụ một khách mua 100 đơn → tuổi của họ xuất hiện **100 lần** → tính "tuổi trung bình" sẽ **sai bét**.
   - Giải pháp: **Lượt 1** tính các con số cơ bản cho **từng bảng riêng** (chính xác tuyệt đối). **Lượt 2** mới khéo léo ghép một bảng phụ gọn nhẹ chỉ để tính **tương quan chéo bảng**.

   > **"Tương quan" (correlation) là gì?** Là mức độ **hai thứ đi cùng nhau**. Ví dụ: tuổi càng cao thì lương càng cao → tương quan dương. Càng gần ±1 thì quan hệ càng chặt.

**4) Bật chế độ "Full" cho Profiling** (đã nói ở L1) để có thêm các con số sâu như tương quan, nhưng vẫn giữ "lấy mẫu" nếu file quá khổng lồ.

**5) Làm phán quyết "giàu thông tin" hơn.** Hiện file phán quyết chỉ ghi "2 lỗi CRITICAL" mà **không nói lỗi gì, ở cột nào**. Nâng cấp: thêm phần **`issues_breakdown`** (phân rã lỗi) liệt kê chi tiết từng lỗi kèm cột, mức độ, cơ chế thiếu… để AI có đủ "nguyên liệu" viết báo cáo sâu.

---

## 8. Làm sao để tool không "nói dối"? (Guardrail & Provenance)

Đây là phần **tinh tế nhất** nhưng rất đáng hiểu, vì nó là điều khiến hệ thống **đáng tin**.

### 8.1. Guardrail — "rào chắn" kiểm số

Như đã nói: AI viết báo cáo, nhưng trước khi báo cáo tới tay người dùng, **Guardrail** soi lại. 💡 Hình dung như **biên tập viên khó tính**: đọc bài của phóng viên (AI), gặp con số nào cũng tra lại nguồn (JSON); sai một con số là **trả bài**.

Guardrail dự kiến có **2 tầng** kiểm:
- **Tầng 1 — kiểm số & tên:** mọi con số trong bài phải khớp số trong JSON (cho phép sai số nhỏ); mọi tên cột/bảng phải có thật.
- **Tầng 2 — kiểm "giọng văn":** bắt những câu **đúng số nhưng nói quá chắc** (sẽ rõ ở phần Provenance ngay dưới).

### 8.2. Provenance — "nguồn gốc độ tin cậy" của mỗi kết luận   💡 ĐỀ XUẤT

Nhớ lại chuyện **MNAR?** ở Mục 5: hệ thống *không thể* chắc chắn một cột thiếu là do "giấu có chủ đích". Vấn đề: nếu AI cứ thế viết **"Cột lương thiếu do nhân viên cố tình giấu"** — nghe **chắc nịch** — thì đó là **nói dối**, vì sự thật là "ta chỉ **nghi**".

Để chặn việc này, mỗi kết luận sẽ được gắn một **nhãn nguồn gốc (provenance)** thuộc 1 trong 3 mức:

| Nhãn | Nghĩa | Ví dụ | Hệ quả |
|---|---|---|---|
| **OBSERVED** (đo trực tiếp) | Chắc chắn, đếm được | "Cột tuổi thiếu 1 ô" | Được nói chắc, mức nào cũng được |
| **INFERRED** (suy luận) | Máy/AI đoán | "`truong_hoc` trỏ tới `id_school`" (đoán bằng Jaccard) | Được báo, nhưng **phải ghi rõ là suy luận** |
| **INDETERMINATE** (không xác định được) | Về lý thuyết không thể chắc | "Nghi MNAR" | **Tối đa mức WARN** + **bắt buộc nói kiểu dè dặt** ("nghi…, chưa xác nhận được") |

> 🔑 **Câu thần chú:** *Không gì được trình bày chắc chắn hơn bản chất thật của nó.* Tool vẫn báo mọi thứ, nhưng một điều "chỉ là nghi" thì phải được nói ra **như một điều nghi**, không phải như sự thật. Đây chính là việc **Tầng 2 của Guardrail** làm.

---

## 9. Trạng thái: cái gì xong, cái gì chưa

| Phần | Trạng thái | Ghi chú |
|---|---|---|
| L0 Đọc file (CSV/Excel/Parquet) | ✅ Xong | **JSON reader chưa có** trong code đang soi [chưa xác minh với repo mới nhất] |
| L1 Profiling | ✅ Xong | code để mặc định **Full** (review nói minimal — **mâu thuẫn, cần xác minh**) |
| L2a Tìm outlier | ✅ Xong | ngưỡng **chưa kiểm chứng** trên dữ liệu lớn |
| L2b Kiểm tra schema + đoán quan hệ + khớp tên khác | ✅ Xong | cách đoán còn **gài cứng**; v3.0 thay bằng Jaccard + AI |
| L2.5 Chấm mức nghiêm trọng | ✅ Xong | cách chấm theo **kinh nghiệm**, chưa có căn cứ khoa học |
| L3 Ba file JSON | ✅ Xong | v3.0 sẽ thêm `issues_breakdown` |
| L3.5 Vẽ biểu đồ | ✅ một phần | mới có biểu đồ chẩn đoán |
| L4 AI viết báo cáo + Guardrail | ❌ **Chưa làm** | **việc lớn nhất còn lại** |
| Phân tích đa bảng đầy đủ (Dual-Pass) | 📋 Kế hoạch v3.0 | hiện mới kiểm cấu trúc, chưa phân tích chất lượng từng bảng |
| Trục Provenance + Guardrail 2 tầng | 💡 Đề xuất | chống "nói dối" |
| Web app | ✅ chạy demo | chưa "chịu tải" thật (chạy file lớn dễ treo) |

**Vài việc nhỏ còn ngỏ:** xuất ra file CSV chứa **toàn bộ** các dòng bất thường (hiện chỉ đưa 10 dòng mẫu); lấy mẫu 10.000 dòng riêng cho bước phân loại missingness; làm web app "chịu tải" tốt hơn.

---

## 9b. Hạt sạn đã biết (Red Team) — đọc trước khi tin kết quả

Đây là các lỗi **có thật trong code đã đọc** (không phải đồn). Liệt kê để người mới không hiểu nhầm rằng mọi con số đều đáng tin tuyệt đối.

- 🔴 **Lấy mẫu phá kiểm tra khoá ngoại (đa bảng).** Mọi bảng >500k dòng bị lấy mẫu *trước khi* kiểm tra → khoá ngoại báo "mồ côi" giả. Cách sửa: kiểm cấu trúc/khoá chạy trên **toàn bộ** dữ liệu. (`registry.py`, `schema_engine.py`)
- 🔴 **Lấy mẫu âm thầm.** `n` trong báo cáo là **cỡ mẫu**, nhưng không có cờ "đã lấy mẫu / số dòng gốc". → "thiếu 40%" thật ra là "40% của một mẫu". Cách sửa: ghi `sampled / original_n / sample_n` vào phần meta. (`models.py`)
- 🟠 **Hai file JSON báo cáo lệch nhau.** Mức nghiêm trọng của *từng cột* được tính rồi chỉ dùng để **đếm trong verdict**, **không** ghi vào `data_quality_findings.json` (file này chỉ có outlier + trùng lặp). → người/LLM đọc file dq không thấy "cột nào nặng vì sao". Cách sửa: một danh sách findings **duy nhất**, hai file là hai "view" của nó. (`calibrator.py`, `models.py`, `run_pipeline.py`)
- 🟠 **Lỗi kép bị thổi phồng + dán nhãn sai.** Khi một cột có nhiều lỗi, **mọi** lỗi của cột bị nâng lên cùng một mức cao nhất → một lỗi INFO có thể bị báo thành CRITICAL, và số lỗi bị đếm phồng. Cách sửa: chỉ nâng *mức tổng của cột*, giữ nguyên mức gốc từng lỗi. (`compound.py`)
- 🟠 **Phân loại "kiểu thiếu" dùng một con số chung cho mọi cột.** Một p-value tính trên các cột số được áp cho **tất cả** cột (kể cả cột chữ) → dễ gán "MNAR?" oan. Cách sửa: tính theo từng cột, hoặc để nhãn dè dặt rõ ràng. (`missingness.py`)
- 🟡 **Phán quyết bỏ qua mức WARN.** Chỉ lỗi HIGH/CRITICAL mới đổi được phán quyết; 50 lỗi WARN vẫn ra **READY**. Cách sửa: chốt một luật rõ (WARN-finding → dataset ≥ WARN). (`aggregator.py`)
- 🟡 **Ngưỡng & cách chấm điểm theo kinh nghiệm**, chưa hiệu chỉnh khoa học (đã nói ở L2.5/L2a). Nên ghi nhãn "heuristic v0.1" thay vì trình bày như đã kiểm chứng.

> 🔑 Tinh thần: tool này **đáng tin ở phần đo trực tiếp** (đếm ô trống, trùng khoá chính), nhưng các phần **suy luận/chấm điểm** thì còn hạt sạn — hãy đọc kèm cảnh báo ở trên.

---

## 10. Bản đồ file mã nguồn

Để người mới biết "file nào lo việc gì":

- **Đọc file:** `readers.py`, `registry.py`, `sampling.py`, `csv_reader.py`, `db_extractor.py`
- **Profiling:** `profiling_engine.py`
- **Tìm outlier:** `anomaly_engine.py`
- **Schema & quan hệ bảng:** `schema_engine.py`
- **Chấm mức nghiêm trọng:** `missingness.py`, `calibrator.py` (+ `calibrator_table.json`), `compound.py`, `disposition.py`, `aggregator.py`
- **Đóng gói JSON:** `models.py` (định nghĩa "khuôn" dữ liệu), `findings_builder.py`
- **Vẽ:** `visualizer.py`
- **Chạy cả dây chuyền:** `run_pipeline.py`
- **Kiểm thử/đánh giá:** `harness.py`, `chaos.py` (cố tình tạo lỗi để thử), `build_datasets.py`
- **AI + Guardrail:** *(chưa có — sẽ nằm trong `guardrail/` và phần agents)*

> 📋 **KẾ HOẠCH v3.0** thêm: `auto_schema.py` (phễu Jaccard + AI) và `auto_join.py` (ghép bảng phụ cho Dual-Pass).

---

## 11. Từ điển thuật ngữ

- **EDA** — soi dữ liệu lần đầu để hiểu nó.
- **DataFrame** — "bảng" trong bộ nhớ, như một sheet Excel.
- **Deterministic** — cùng đầu vào luôn ra cùng kết quả (như máy tính bỏ túi).
- **LLM** — AI ngôn ngữ (như ChatGPT); viết hay nhưng có thể bịa.
- **Hallucinate (ảo giác)** — AI bịa ra thông tin nghe đúng nhưng sai.
- **Outlier** — giá trị lạc loài, khác hẳn phần còn lại.
- **Schema** — bản thiết kế cấu trúc dữ liệu.
- **Primary Key (PK / khoá chính)** — cột phân biệt từng dòng, không trùng không trống.
- **Foreign Key (FK / khoá ngoại)** — cột trỏ tới khoá chính của bảng khác.
- **Orphan (mồ côi)** — khoá ngoại trỏ tới thứ không tồn tại.
- **Missingness** — kiểu/lý do thiếu dữ liệu (MCAR / MAR / MNAR).
- **Severity** — mức nghiêm trọng (INFO / WARN / HIGH / CRITICAL).
- **Verdict** — phán quyết tổng (READY / WARN / NOT_READY).
- **JSON** — định dạng văn bản máy & người cùng đọc được.
- **Jaccard Index** — tỷ lệ trùng nhau giữa hai tập giá trị.
- **Correlation (tương quan)** — mức độ hai thứ đi cùng nhau.
- **Guardrail (rào chắn)** — bộ kiểm tự động chống AI bịa số.
- **Provenance (nguồn gốc)** — nhãn độ tin cậy của một kết luận (OBSERVED / INFERRED / INDETERMINATE).

---

> **Một lời cuối, trung thực:** Phần "máy đo số" (L0–L3) đã chạy tốt và là phần chắc chắn nhất. Phần "AI viết lời + chống bịa" (L4, Guardrail, Provenance) **chưa được xây dựng** — đó vừa là việc còn lại lớn nhất, vừa là phần thú vị nhất, vì nó quyết định người dùng có **tin** được bản báo cáo cuối hay không.
