# Đề xuất Hợp nhất: Engineering Blueprint & Các Ý tưởng M1/M2/M3

Đã đọc xong 2 nguồn. Đây là engineering blueprint thực sự của dự án (`system_architecture_design.md` = bản thiết kế tổng thể + `superpowers/` = plan thực thi TDD đã chi tiết tới mức code-ready). Dưới đây là phân tích so sánh với M1/M2/M3 và đề xuất hợp nhất.

---

## 1. Tóm tắt 2 nguồn kiến trúc hiện tại

### A. `system_architecture_design.md` — Bản thiết kế product chính thức

| Layer | Tech chốt | Quyết định khác biệt |
| :--- | :--- | :--- |
| **L0 Ingestion** | pandas CSV/Excel + pydbml | Multi-table DBML là "vũ khí bí mật" |
| **L1 Profiling** | `fg-data-profiling` (ydata-profiling rebranded) | Không tự code, extract từ ydata |
| **L2 Anomaly** | PyOD Ensemble = IForest + ECOD + LOF, average score (ADBench-recommended) | Chỉ chạy trên numeric cols, contamination=0.05 |
| **L2 Schema** | pydbml + Pandas FK-check | Tự code (chưa ai làm OSS) |
| **L3 Ontology** | TÁCH 2 file JSON chuẩn hoá DAMA: `data_quality_findings.json` + `schema_evaluation_findings.json` | Tránh ngợp context LLM |
| **L3.5 Charts** | Optional chart artifacts cho end user | Chart không đi vào L4 |
| **L4 Reporting** | Multi-agent OpenAI: Mini (gpt-4o-mini, 2.5M tok/day) + Master (gpt-4o/o1, 250k tok/day) | Mỗi mini agent đọc 1 mảnh JSON + raw samples dạng số/chữ, không chart |
| **NFR** | Sampling 500k/500MB; retry 3× + graceful degradation | Pydantic strict cho contract |

### B. `superpowers/` — Plan TDD đã code-ready

- **`specs/...json-schema-design.md`**: Pydantic contract cụ thể với `top_10_samples` + `full_anomalies_export_path`.
- **`plans/...part1.md` (Task 1-4)**: Skeleton + Pydantic `DatasetMeta` / `ColumnStats` / `AnomalyRecord` / `SchemaEvaluationFindings` + CSV reader có sampling + encoding fallback. Pitfall list cụ thể (15+ traps).
- **`plans/...part2.md` (Task 5-8)**: `profiling_engine` wrap ydata, `anomaly_engine` PyOD ensemble normalized scores, `findings_builder` merge L1+L2, integration test.

**→ Kết luận:** Phase 1+2 (L1, L2, L3 deterministic core) đã có blueprint hoàn chỉnh TDD. Không đụng L3.5 charts và L4 LLM trong superpowers hiện tại.

---

## 2. So sánh với M1/M2/M3 (Những điểm va chạm)

| Chiều | M1/M2/M3 giả định | System arch thực tế | Tension (Mâu thuẫn) |
| :--- | :--- | :--- | :--- |
| **L1+L2 backend** | TestGen plugin (M3) hoặc neutral | Tự build = ydata + PyOD Ensemble | M3 plugin pattern không hợp |
| **L3 schema** | 1 file, version + adapter cho 3 tool ngoài | 2 file tách (data_quality / schema_eval), project-internal | M1 cần redesign — split 2 file + drop 3 adapters |
| **Severity logic** | Adaptive calibrator + compound rule + verdict (M2) | Hard threshold `if n/N>0.05` HIGH else MEDIUM | M2 components là natural extension chưa có |
| **DAMA/ISO tags** | Có (`dq_dimensions`, `compound_severity`, `ml_impact`) | Roadmap nhắc DAMA-DMBOK nhưng Pydantic model hiện chưa có field | M1 differentiator vẫn còn nguyên giá trị |
| **L4 narrator** | Single-agent interpreter + token guardrail (M3) | Multi-agent (Mini × N + Master) + retry/fallback (không có guardrail) | M3 guardrail mechanism vẫn còn cần — chỉ áp vào multi-agent |
| **MCAR/MAR/MNAR** | Component M2 | Không có | Gap còn nguyên |

**→ Kết luận:** M1/M2/M3 **không "thay thế"** system arch; hoàn toàn **hợp nhất lại được** — vì M1/M2/M3 tấn công trực tiếp vào chính những điểm yếu/khoảng trống của bản thiết kế hiện tại.

---

## 3. Đề xuất 3 Ý tưởng Hợp nhất (C1, C2, C3)

### C1 — Extended L3 contract: 2 file + DAMA/ML-impact/compound fields
*Hợp nhất M1 + system arch L3.* Thay vì M1 ship "1 schema URL + 3 adapter ngoài", chúng ta ship:

- **2 Pydantic model** y nguyên system arch split (`DataQualityFindings`, `SchemaEvaluationFindings`).
- Thêm field M1 differentiator vào `AnomalyRecord` và `IntegrityError`:
  - `dq_dimensions: list[DqDimension]` (DAMA 6 chiều)
  - `iso_25012_dimension: str | None`
  - `compound_severity: Severity | None` (set bởi C2 escalator)
  - `ml_impact: list[MlImpact]` (training_blocker, leakage_risk, …)
  - `confidence: float | None`
- Schema published cho cộng đồng vẫn được — chỉ là 2 schema URL thay vì 1.
- **Drop 3 adapter** (TestGen/GE/Kats) khỏi v0.1. Đưa vào "roadmap v0.2 nếu cộng đồng quan tâm".

> **Effort:** +3 ngày trên `superpowers part1` Task 2-3 (thêm field + test). Không phá plan TDD hiện có.

### C2 — Layer 2.5: Severity-stack 4 module + offline OpenML calibration
*Hợp nhất M2 + system arch L2/L3.* Chèn 4 component M2 giữa raw L2 output và L3 `findings_builder`:

```text
L2 PyOD Ensemble (raw scores)
        │
        ▼
[Layer 2.5 — Severity Stack]   ← M2 đóng góp vào product
        │
        ├── (a) MissingnessMechanism detector (MCAR/MAR/MNAR)  ← gap system arch chưa có
        ├── (b) Calibrator       ← thay hard `if n/N>0.05` thành table-lookup
        ├── (c) Aggregator       ← sinh dataset-level Verdict (3rd JSON: dataset_verdict_findings.json)
        └── (d) CompoundEscalator ← set compound_severity (C1 field)
        │
        ▼
L3 findings_builder (merge + validate)
```

**Lưu ý:** OpenML-CC18 benchmark KHÔNG biến mất — vai trò thay đổi từ "research artifact standalone" thành **bộ calibration offline** sinh ra config shipping cùng product.

> **Effort:** Sau khi `superpowers part2` (Task 5-8) xong, thêm 1 thư mục `engines/severity_stack/` với 4 module. ~2-3 tuần kèm bench.

### C3 — Multi-agent L4 + token-level numerical guardrail per agent
*Hợp nhất M3 + system arch L4.* Bỏ "TestGen plugin" angle của M3 — giữ cốt lõi guardrail mechanism và áp vào mỗi agent:

```text
[L3 JSON 2 files]
       │
       ▼
[LLM Router]
       │
       ├─► Mini Agent A (gpt-4o-mini, đọc 1 column slice)
       │       └─► token guardrail (số trong output ∈ số trong slice JSON)
       │       └─► nếu fail → regen ≤ 3 lần → fallback "<UNVERIFIED>"
       │
       ├─► Mini Agent B (Architect)
       │       └─► token guardrail (đối với schema_evaluation JSON)
       │
       └─► Master Agent (gpt-4o/o1)
               └─► faithfulness judge (mọi claim trace tới ≥ 1 mini output)
               └─► token guardrail final pass trên Markdown đầu ra
```

Thay vì system arch hiện tại chỉ có "retry 3× + graceful degradation = ẩn LLM phần", C3 thêm safety net chính xác hơn: guardrail không reject vì lỗi network mà vì bịa số/tên column. Đây là giá trị **deterministic-first thực sự**.

> **Effort:** ~150 LOC validator + 5 prompt template + 50-finding eval suite. Build sau khi Phase 3 multi-agent skeleton xong.

---

## 4. Lộ trình Triển khai Đề xuất (Cập nhật)

| Phase | Nội dung | Nguồn |
| :--- | :--- | :--- |
| **Phase 1** (đang chạy) | Skeleton + Pydantic models + CSV reader | superpowers part1 |
| **Phase 2** (đang chạy) | profiling + anomaly + findings_builder | superpowers part2 |
| **Phase 3 — C2** *(NEW)* | Layer 2.5 (4 module) + OpenML-CC18 calibration offline | M2 ∩ sys arch |
| **Phase 4** | Dual visualization (overview extract + diagnostic LLM-directed) | sys arch only |
| **Phase 5 — C3** | Multi-agent L4 build kèm token-level guardrail từ đầu | M3 ∩ sys arch |
| **Phase 6** *(Publish)* | Paper: "Layer 3 schema + Severity-stack calibration" + Blog: "Multi-agent + guardrail" | M1+M2+M3 outcome |

---

## 5. File PRD/SPEC cần cập nhật

3 file SPEC cũ (`M1_SPEC.md`, `M2_SPEC.md`, `M3_SPEC.md`) hiện đang giả định greenfield và external tooling — không khớp với bản thiết kế thực tế.

**Đề xuất:** Không xoá file cũ, mà tạo thêm 3 file mới:
- `idea_detail/COMBINED_C1_SPEC.md` — C1 ngắn gọn dạng "diff" so với superpowers part1 Task 2-3.
- `idea_detail/COMBINED_C2_SPEC.md` — C2 = Layer 2.5 spec chèn sau Task 8.
- `idea_detail/COMBINED_C3_SPEC.md` — C3 = guardrail spec cho L4 multi-agent (sẽ trở thành superpowers part3 plan).
