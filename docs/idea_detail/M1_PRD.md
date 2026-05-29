# AI Product Requirements Document — M1

**Product Name:** L3 Ontology as Published Schema + 3 Reference Adapters
**Codename:** `vsf-l3-schema`
**Version:** 1.0
**Created:** 2026-05-29
**Status:** Draft — chờ phê duyệt sequencing trước M2/M3

**Contacts:**
- Product Manager / Researcher: hieu.npt1710@gmail.com
- Engineering Lead: (chủ dự án thực hiện)
- Design Lead: (n/a — schema-first, không UI)

---

## 1. Executive Summary

**Purpose:** Trình bày tóm tắt sáng kiến M1 và tiêu chí thành công để người không đọc hết tài liệu vẫn nắm được phạm vi.

M1 xây dựng **ontology L3 (findings) chuẩn hoá** dưới dạng **JSON Schema có version + Pydantic model + 3 adapter tham chiếu** (DataKitchen TestGen, Great Expectations, Facebook Kats). Mục tiêu là biến lớp L3 — đầu ra trung gian giữa các engine phát hiện DQ/anomaly (L1+L2) và lớp tường thuật LLM (L4) — thành **substrate liên thông** (interop substrate) mà nhiều công cụ có thể "phát" và "tiêu thụ".

Nguyên cớ: Phân tích hội tụ ý tưởng (`wiki/synthesis/idea-convergence-map-2026-05.md`) cho thấy **F3 (L3 schema) là hot-spot lớn nhất** — 14/21 ý tưởng dự án phụ thuộc vào nó. Đầu tư vào L3 một lần mở khoá phần lớn không gian downstream. M1 cũng là tiền điều kiện cho M2 (perturbation benchmark) và M3 (interpreter-only L4 demo).

**Success criteria:**
- ≥ 80 % **field-presence consistency** khi cùng một narrator L4 đọc finding từ 3 nguồn (TestGen/GE/Kats) đã qua adapter.
- Schema **không cần >3 discriminator branch / conditional field** để chứa toàn bộ variance cross-tool (kill criterion).
- ≥ 95 % finding mẫu (≥ 30 finding/adapter) **round-trip** sạch qua `jsonschema.validate` Python.
- Schema được publish tại **URL ổn định** (pattern OpenLineage `_schemaURL`) trong vòng 3 tuần kể từ khi bắt đầu.

---

## 2. Market Opportunity

**Purpose:** Vì sao thời điểm 2026 là phù hợp để publish chuẩn L3.

**Key Questions trả lời:**
- **Giai đoạn thị trường:** EDA + Data Quality OSS đang ở giai đoạn **mature-and-fragment** — đã có >10 công cụ trưởng thành (Great Expectations 9k★, deequ 3.5k★, ydata-profiling 12k★, Soda Core, TestGen, Pandera, DataKitchen…) nhưng **chưa có ngôn ngữ chung cho "finding"**. Mỗi công cụ phát ra cấu trúc riêng (GE `ExpectationSuiteValidationResult`, TFDV `Anomalies` protobuf, Deequ `VerificationResult`, TestGen DAMA-scoring). Đây chính là cửa sổ cho một schema chuẩn hoá theo mô hình OpenLineage / OpenTelemetry.
- **Growth rate / drivers:** Adoption của data-contract-as-code (dbt + Great Expectations integration) tăng nhanh; cộng đồng OpenLineage + OpenMetadata đang chứng minh giá trị của schema-trung-tâm.
- **TAM:** Không nhằm vào doanh thu trực tiếp — đây là sáng kiến nghiên cứu/OSS-standard. Giá trị nằm ở **adoption rate** (số tool/team tích hợp) và **publishability** (đăng paper hoặc workshop).

**Định lượng cơ hội (per [merged_research §4.2]):** Great Expectations là baseline L3 mạnh nhất nhưng JSON output của họ thiếu **DAMA/ISO 25012 dimension tags**, **compound severity field**, và **ml_impact enums** — chính là 3 đóng góp mà schema M1 thêm vào.

---

## 3. Strategic Alignment

M1 phù hợp với mục tiêu dài hạn của dự án — kiến trúc **deterministic-first** với L4 = strict interpreter trên L3 — vì:
- L3 schema chính là **hợp đồng** đảm bảo L4 chỉ tường thuật trên findings cấu trúc, không bao giờ chạm raw data → trực tiếp hỗ trợ guardrail chống hallucination.
- Là **Element 1 của Framing D** (per `wiki/synthesis/red-team-meta-differentiator-framing.md`) — yếu tố differentiator của dự án so với TestGen, GE, Soda.
- Mở khoá 14/21 ý tưởng phụ thuộc F3 (per convergence map) → leverage cao nhất trên toàn portfolio nghiên cứu.

Mid-term objective được hỗ trợ: tăng số ý tưởng có thể "build once, reuse N×" từ 0 hiện tại lên ≥ 4 trong 6 tháng.

---

## 4. Customer & User Needs

**Phân khúc/persona chính:**

1. **Persona A — Nghiên cứu sinh / kỹ sư dự án VSF-EDA (chính chủ).**
   Jobs-to-be-done: viết paper/báo cáo nội bộ về Layer 3 với artifact có thể tái sử dụng cho M2 & M3. Đau điểm: hiện không có schema để chuẩn hoá finding giữa các thí nghiệm; mỗi nhánh code đẻ ra format riêng.

2. **Persona B — Maintainer của OSS DQ tool** (GE, TestGen, Pandera…).
   Jobs-to-be-done: muốn "phát" output sang format chung để liên thông với LLM-narrator, BI tool, lineage system. Đau điểm: không có schema được community accept; mỗi tool tự định nghĩa.

3. **Persona C — Data engineer dùng nhiều tool DQ song song** trong lakehouse.
   Jobs-to-be-done: hợp nhất finding từ TestGen (batch) + Kats (streaming) + GE (transformation) thành 1 dashboard / 1 narrative. Đau điểm: phải viết adapter ad-hoc.

**Ràng buộc:**
- Schema cần Apache-2.0 compatible (phần lớn tool nguồn).
- Phải có Python reference; nice-to-have: TypeScript types cho frontend.
- Không có ràng buộc địa lý/regulatory.

**Vấn đề ưu tiên:** Persona A là khách hàng chính (chính chủ dự án). Persona B + C là chỉ-báo adoption tiềm năng nhưng KHÔNG nằm trong scope M1.

---

## 5. Value Proposition & Messaging

**Giá trị cốt lõi:**
> "Một schema L3 duy nhất + 3 adapter mẫu cho phép bất kỳ engine DQ nào cũng có thể được narrator LLM tường thuật một cách nhất quán, có thể audit, và không hallucinate số."

**Khác biệt vs GE / OpenLineage / TFDV:**
- vs **GE `ExpectationSuiteValidationResult`**: thêm `dq_dimensions` (DAMA/ISO 25012), `compound_severity`, `ml_impact` enum — các trường GE thiếu.
- vs **OpenLineage**: OpenLineage tập trung lineage events; M1 schema tập trung **finding semantics** (issue_type, severity, measurement vs constraint).
- vs **TFDV Anomalies protobuf**: M1 dùng JSON Schema (human-readable, web-friendly) thay vì protobuf; thêm tag DAMA và liên kết với DQ ontology.

**Messaging (1 câu):**
> "Build once, narrate anywhere — chuẩn finding L3 mở cho mọi engine DQ."

---

## 6. Competitive Advantage

**Defensibility:**
- **Tài sản độc quyền:** synthesis của dự án (`wiki/synthesis/red-team-meta-differentiator-framing.md`, `concepts/structured-finding-schema.md`) đã làm việc cross-reference TFDV + Deequ + DAMA-DMBOK + ISO 25012 — không tool nào trên thị trường đã hợp nhất 4 nguồn này vào một schema.
- **First-mover trong "L3 published standard":** GE, Soda, Pandera đều chưa publish JSON Schema cho output của họ ở dạng standalone, versioned, URL-addressable. M1 chiếm space này trước.
- **Khó copy:** giá trị nằm ở **cross-tool field reconciliation work**, không nằm ở schema syntax. Để copy, đối thủ phải làm lại survey cross-tool — không khó nhưng tốn ≥ 4 tuần.

**Sustainability:** Vì là OSS schema, advantage không phải "khoá kỹ thuật" mà là **brand + community adoption**. Nếu 3 adapter chạy mượt và demo cross-tool L4 narrative thuyết phục, M1 trở thành "schema được tham chiếu" — adoption lock-in.

---

## 7. Product Scope and Use Cases

**Năng lực then chốt:**
1. **JSON Schema v0.1** (~80 dòng): formalize trường từ `concepts/structured-finding-schema.md`.
2. **Pydantic model**: Python class mirror schema, hỗ trợ serialize/validate.
3. **3 reference adapters** (Python module riêng biệt):
   - `vsf_l3_schema.adapters.testgen`: đọc TestGen JSON/DB output → L3 finding.
   - `vsf_l3_schema.adapters.great_expectations`: đọc GE `ExpectationSuiteValidationResult` → L3 finding.
   - `vsf_l3_schema.adapters.kats`: đọc Kats anomaly detector output → L3 finding.
4. **Validation test suite**: ≥ 30 finding mẫu/adapter, chạy `pytest` với `jsonschema.validate`.
5. **Reference doc**: README chứa pattern field, ví dụ end-to-end.

**Out-of-scope (M1 không làm):**
- Không xây narrator L4 (đẩy sang M3).
- Không build benchmark (đẩy sang M2).
- Không support batch+streaming hợp nhất (chỉ batch L3; streaming Kats là batch-of-windows).
- Không phát version v0.2 — M1 chỉ commit v0.1.
- Không build UI/dashboard.

**Outcome đo lường:**
- ≥ 95 % finding/adapter round-trip sạch.
- ≥ 80 % field-presence consistency khi cross-tool.
- ≤ 3 discriminator branch trong schema (đảm bảo "publishing standard" framing).

**High-risk assumption:**
- **A1:** "Schema 80 dòng đủ chứa variance cross-tool" — test bằng 24h MVP với 1 finding/tool.
- **A2:** "TestGen output programmatically extractable" — kill criterion nếu TestGen chỉ phát HTML/DB không có JSON API.
- **A3:** "Kats output stable enough để mapping" — Kats là Meta OSS, có thể bị abandoned (check star/last-commit).

---

## 8. Non-Functional Requirements

### 8.1 General Requirements

- **Performance:** validate 1 finding < 5 ms với `jsonschema` Python; chạy 1000 finding < 10 giây.
- **Scalability:** schema phải scale tới **finding bundle có 10 000 records** (giới hạn 1 file ~50 MB JSON).
- **Reliability:** 100 % reproducible — `pip install vsf-l3-schema==0.1.0` cho cùng output bytes-identical.
- **Security:** schema public, không chứa secret; adapter không log raw data.
- **Versioning:** semver; `schema_url` field embed version để forward-compat.
- **Compatibility:** Python ≥ 3.10; `pydantic` v2; `jsonschema` ≥ 4.0.

### 8.2 AI-Specific Requirements (LLMs)

M1 **không tự gọi LLM**, nhưng schema được thiết kế để **LLM tiêu thụ được**:
- Mỗi finding phải có cả `short_description` (≤ 140 ký tự, ưu tiên cho prompt) và `long_description` (≤ 2000 ký tự).
- Toàn bộ trường số (`measurement.value`, `constraint.threshold`, `confidence`) phải nằm trong scalar/struct rõ ràng để token-level guardrail (M3) chạy regex-extract được.
- `compound_severity` và `severity` tách rời để LLM phân biệt cá nhân vs hệ thống.
- DAMA dimension thuộc enum đóng để LLM không "sáng tạo" tag.

**Đo lường:** trong M3 demo, ≥ 90 % numeric token output của L4 phải match được với số trong L3 finding (gián tiếp validate schema design của M1).

---

## 9. Go-to-Market Approach

**Phase 1 (M1 scope) — Tuần 1-3:**
- **Target:** Persona A (chính chủ dự án).
- **Deliverable:** repo `vsf-l3-schema` v0.1.0 trên Git private/personal; publish JSON Schema tại URL ổn định (GitHub raw / GitHub Pages).
- **Success metric:** 3 adapter pass test suite; M2 + M3 import được package mà không phải fork.
- **Evidence:** badge `pytest` xanh; 90-finding test suite (30/adapter) round-trip sạch.

**Phase 2 (Hậu M1, không thuộc scope tài liệu này) — Tháng 2-3:**
- Sau khi M2 + M3 chứng minh schema dùng được end-to-end, viết short paper / workshop submission (target: VLDB DBQual workshop, DEEM workshop).
- Open-source repo lên GitHub public; mời community add adapter cho Pandera, Soda Core.

**Phase 3 (Tương lai, ngoài tài liệu):**
- v0.2 với streaming-native field, DBML cross-table flag, vector-DQ extension.

---

## Cross-references

- `wiki/synthesis/idea-convergence-map-2026-05.md` §3 Meta-Idea M1
- `wiki/concepts/structured-finding-schema.md` — design seed
- `wiki/layers/l3.md` — layer context
- `wiki/gaps/l1-l4-oss-pipeline-contested.md`, `wiki/gaps/time-series-streaming-coverage.md`
- `wiki/ideas/time-series-streaming-coverage-3-multi-tool-finding-schema-standard.md`
- `wiki/ideas/l1-l4-oss-pipeline-contested-3-l3-schema-diff-vs-testgen.md`
- `wiki/synthesis/red-team-meta-differentiator-framing.md` — Framing D Element 1
- M2_PRD.md, M3_PRD.md — downstream meta-ideas phụ thuộc M1
