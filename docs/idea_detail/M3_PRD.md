# AI Product Requirements Document — M3

**Product Name:** Interpreter-Only L4 + TestGen-Plugin End-to-End Demo
**Codename:** `vsf-l4-demo`
**Version:** 1.0
**Created:** 2026-05-29
**Status:** Draft — depends on M1 (L3 schema v0.1)

**Contacts:**
- Product Manager / Researcher: hieu.npt1710@gmail.com
- Engineering Lead: (chủ dự án thực hiện)
- Design Lead: (n/a — chỉ CLI + JSON output, không UI)

---

## 1. Executive Summary

M3 xây dựng demo **end-to-end** chứng minh kiến trúc Framing D Element 3 của dự án (**LLM = strict interpreter trên findings, không bao giờ trên raw data**) là **khả thi kỹ thuật** lẫn **giao được trong ≤ 1 tháng** mà không cần tự build lại L1+L2.

Pipeline demo:

```
SQLite sample DB → TestGen (L1+L2) → L3 transformer (M1 schema) → Interpreter-only L4 narrator → NL report
```

Hai đóng góp chính:
- **L3 transformer**: adapter TestGen → L3 schema M1 (~100 LOC).
- **Interpreter-only L4 narrator**: LLM được khoá bởi **token-level numerical guardrail** — mọi số trong output PHẢI khớp số trong L3 findings JSON, validator reject/regen nếu không.

Nguyên cớ chiến lược: TestGen của DataKitchen có overlap đáng kể với scope ban đầu của dự án (L1+L2 OSS). M3 hoán đổi: **bỏ greenfield L1+L2, plug TestGen vào**, dự án tập trung **L3 schema + interpreter L4** — phần TestGen KHÔNG có. Đây là Framing D defensible.

**Success criteria:**
- **≥ 90 % giảm rate numerical-hallucination** vs LLM baseline không guardrail (đo trên 50-finding suite).
- **≥ 80 % fluency rating** (GPT-4-as-judge).
- **≥ 60 % feature-parity** với pitch greenfield gốc (deliverable ≤ 1 tháng vs ≥ 3 tháng greenfield).
- Demo end-to-end chạy được từ CLI duy nhất trên 1 SQLite sample DB.

---

## 2. Market Opportunity

**Giai đoạn thị trường:** "LLM cho data documentation/profiling" đang **bùng nổ** (PandasAI, Sketch, LIDA, ydata-profiling LLM extension) nhưng **chưa ai publish OSS demo với hallucination guarantee**. TestGen 2024 OSS thậm chí **inverted direction** — LLM **generate test** từ NL, không phải narrate finding.

**Drivers:**
- Hallucination là rào cản #1 của adoption LLM-in-dataops (Huang 2023 hallucination survey, OWASP LLM Top-10).
- Faithfulness review framework (Malin 2024) đang nổi nhưng chỉ ở paper level — chưa có OSS demo.
- DataKitchen TestGen Apache-2.0 OSS phát hành ~2024, có L1+L2 chất lượng cao nhưng L4 yếu — gap thị trường rõ ràng.

**Per [merged_research §3]:** Không tool OSS nào cung cấp LLM-narrator với guarantee determinism. Vendor (Acceldata, Monte Carlo) có narrator nhưng **closed-source** và **không công bố guardrail mechanism**.

**TAM / strategic value:** Đây là **proof-of-concept differentiator** — không kỳ vọng doanh thu trực tiếp; giá trị nằm ở blog post / paper / talk chứng minh "guardrail interpreter L4" là pattern triển khai được.

---

## 3. Strategic Alignment

M3 phù hợp **trực tiếp** với hướng dài hạn của dự án vì đây chính là **mục tiêu cuối cùng của kiến trúc 4-layer**:
- L1 + L2 = TestGen (đã có).
- L3 = M1 schema (đã có).
- L4 = M3 narrator (sản phẩm này).

Validate empirically rằng:
- Schema L3 (M1) đủ giàu để narrator tường thuật tự nhiên.
- Token-level guardrail tinh đủ giảm hallucination > 90 %.
- Framing D differentiator (vs TestGen) là defensible: dự án sở hữu L3 spec + L4 interpreter constraint, không cố replicate L1+L2.

Mid-term objective: tạo **1 artifact OSS** chứng minh end-to-end pipeline; mở đường cho paper/workshop submission.

---

## 4. Customer & User Needs

**Phân khúc/persona chính:**

1. **Persona A — Chính chủ dự án + advisor.**
   Jobs-to-be-done: thesis/paper demo cho hội đồng. Đau điểm: paper Framing-D-only không thuyết phục bằng OSS demo chạy được.

2. **Persona B — Reviewer / data engineer skeptical về LLM.**
   Jobs-to-be-done: kiểm chứng "LLM trong dataops có an toàn không?". Đau điểm: hiện chỉ có vendor demo, không có OSS verify được.

3. **Persona C — DataKitchen TestGen user**.
   Jobs-to-be-done: muốn thêm NL summary cho dashboard TestGen. Đau điểm: TestGen UI tốt nhưng chỉ là charts/tables; cần executive-summary text.

**Ràng buộc:**
- LLM cost: ≤ 5 USD cho toàn bộ benchmark 50 finding (tránh phụ thuộc fund infra).
- Offline reproducible mode (cache LLM response cho CI).
- TestGen License Apache-2.0 cho phép embed vào demo.
- Không cần local GPU — tất cả LLM call qua API.

**Vấn đề ưu tiên:** Persona A. Persona B/C là tín hiệu adoption tiềm năng.

---

## 5. Value Proposition & Messaging

**Giá trị cốt lõi:**
> "LLM narrator với 0 hallucination số — vì mọi số phải khớp finding JSON. Không vibe, chỉ interpreter."

**Khác biệt vs PandasAI / LIDA / ydata-profiling LLM mode:**
- **vs PandasAI:** PandasAI cho phép LLM **execute code trên raw data** → hallucination/code-injection risk. M3: LLM chỉ thấy L3 findings JSON, không thấy data.
- **vs LIDA:** LIDA generate visualization spec từ NL; M3 generate NL từ structured findings — orthogonal.
- **vs ydata-profiling LLM extension:** ydata-profiling LLM mode đẩy raw column stats vào prompt; không có guardrail. M3: guardrail mức token.
- **vs DataKitchen TestGen LLM feature:** TestGen LLM **generate test code** từ NL; M3 inverted — **narrate finding** từ structured input.

**Messaging (1 câu):**
> "Mọi số trong NL summary đều trace ngược về 1 finding ID. Auditable LLM cho dataops."

---

## 6. Competitive Advantage

**Defensibility:**
- **Tài sản:** Framing D synthesis + L3 schema M1 + interpreter-only constraint design.
- **Token-level guardrail mechanism:** copy được nhưng cần effort + cross-tool L3 schema từ M1.
- **Demo end-to-end working** beat **pitch greenfield không demo** — strategic moat trong 6-12 tháng.

**Sustainability:**
- Vì OSS, defensibility = **brand + demo reproducibility**. Một blog post + GIF demo đủ chiếm "term" trong community.
- Risk: nếu DataKitchen tự build narrator with guardrail, M3 mất differentiator. Mitigation: ship trong 4 tuần và publish trước.

---

## 7. Product Scope and Use Cases

**Năng lực then chốt:**
1. **TestGen integration:**
   - Docker compose chạy TestGen OSS.
   - Sample SQLite DB (hoặc CSV-loaded) trong repo.
   - Programmatic extraction TestGen findings (JSON/DB query).
2. **L3 transformer** (~100 LOC Python):
   - Map TestGen output → M1 L3 schema.
   - DAMA scoring → `dq_dimensions`, severity label → tier, drill-down → `long_description`.
3. **Interpreter-only L4 narrator** (~250 LOC tổng):
   - LLM call Anthropic Claude API hoặc OpenAI API (configurable).
   - Prompt template: chỉ chứa L3 findings JSON + instruction "narrate only what's in this JSON".
   - Temperature = 0.
4. **Token-level guardrail validator** (~150 LOC):
   - Regex extract mọi numeric token trong LLM output.
   - Set-intersect với numeric values trong L3 findings JSON.
   - Tolerance: exact match cho integer/percent; floating tolerance 1e-4 cho decimal.
   - Nếu có số không match → reject → regenerate (max 3 retry) → nếu vẫn fail, mark finding `<UNVERIFIED_NUMBER>` placeholder.
5. **Audit trail:**
   - SHA-256 hash của L3 findings input lưu cùng output.
   - Log mọi regen + lý do reject.
6. **Evaluation harness:**
   - 50-finding test suite, 2 chế độ: baseline (no guardrail) vs guarded.
   - Hallucination rate = % numeric tokens output không match input.
   - Fluency: GPT-4 judge với 5-point Likert.

**Out-of-scope (M3 không làm):**
- Không tự build L1 hay L2 (TestGen làm).
- Không support non-SQL data source trong demo (CSV → SQLite trước nếu cần).
- Không UI/dashboard (CLI + JSON output là đủ).
- Không multi-language (chỉ English narrator).
- Không streaming/realtime (batch only).
- Không train custom LLM (zero fine-tuning).
- Không "auto-explain code"; chỉ narrate findings.

**Outcome đo lường:** xem §1 success criteria.

**High-risk assumption:**
- **A1:** "TestGen output extractable programmatically." Kill nếu chỉ HTML/UI-only — pivot sang upstream feature request hoặc greenfield.
- **A2:** "Token-level guardrail giảm hallucination ≥ 30 %." Kill nếu < 30 % → pivot semantic NLI-entailment.
- **A3:** "Fluency không drop quá nhiều khi regen-loop." Kill nếu fluency < 50 % → accept lower fluency hoặc redesign prompt.

---

## 8. Non-Functional Requirements

### 8.1 General Requirements

- **Performance:** end-to-end demo ≤ 60 giây cho 1 SQLite DB (10 findings); ≤ 10 phút cho 50-finding eval.
- **Scalability:** không phải concern — M3 là demo, không production. Tuy nhiên L3 transformer scale với #findings linearly.
- **Reliability:** deterministic ở phía guardrail (regex + numeric set); LLM call có cache mode (replay).
- **Security:** API key qua env var `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`; không log prompt/response chứa secret.
- **Cost:** ≤ 5 USD cho full 50-finding eval (kiểm soát bằng prompt-size cap + sampling).

### 8.2 AI-Specific Requirements (LLMs)

Đây là phần cốt lõi của M3.

- **Architectural choice:** strict interpreter-only — LLM nhận **chỉ** L3 findings JSON + few-shot examples; không bao giờ thấy raw data row/col values trừ khi chúng đã trong finding.
- **Accuracy:**
  - Numerical-hallucination rate ≤ 10 % của baseline (i.e. giảm ≥ 90 %).
  - Field-presence consistency: nếu 1 finding có `compound_severity`, narrative phải đề cập (audit).
- **Ethical/safety:**
  - Không bịa số → giảm risk decision-maker hiểu sai.
  - Audit trail SHA-256 + retry log cho replay.
- **Measurement:**
  - Auto-eval: hallucination rate = `|numeric_tokens_in_output - numeric_set(L3)| / |numeric_tokens_in_output|`.
  - GPT-4 judge: fluency 1-5, faithfulness 1-5, actionability 1-5.
- **Maintenance:**
  - Khi M1 schema bump version, M3 transformer + validator phải update.
  - Cache LLM response key bởi `(prompt_hash, model_version)` để reproducibility.

---

## 9. Go-to-Market Approach

**Phase 1 (M3 scope) — Tuần 1-4 (sau khi M1 v0.1 done):**
- **Target:** Persona A.
- **Deliverable:** repo `vsf-l4-demo` với:
  - Docker compose chạy TestGen + sample SQLite.
  - CLI `narrate --db <sqlite-path> --out report.md`.
  - Test suite + benchmark numbers.
- **Success metric:** 3 acceptance criteria pass (xem §1).
- **Evidence:** GIF demo 60 giây; table so sánh baseline vs guarded hallucination rate; sample report.md generated.

**Phase 2 (Tuần 5-6) — Write-up:**
- Blog post / tech report giải thích interpreter-only constraint.
- Optional: submit short paper VLDB DBQual hoặc DEEM workshop.

**Phase 3 (Tháng 3+, ngoài scope):**
- Mở rộng adapter cho Great Expectations (reuse M1 GE adapter) và Kats — chứng minh portability.
- Multi-LLM benchmark (Claude vs GPT-4 vs Llama).

---

## Cross-references

- `wiki/synthesis/idea-convergence-map-2026-05.md` §3 Meta-Idea M3 + Chain β
- `wiki/synthesis/red-team-meta-differentiator-framing.md` — Framing D Element 3
- `wiki/gaps/l1-l4-oss-pipeline-contested.md`, `wiki/gaps/llm-on-findings-novelty-contested.md`
- `wiki/ideas/l1-l4-oss-pipeline-contested-1-interpreter-only-l4-prototype.md`
- `wiki/ideas/l1-l4-oss-pipeline-contested-2-testgen-compatible-plugin.md`
- `wiki/ideas/l1-l4-oss-pipeline-contested-3-l3-schema-diff-vs-testgen.md`
- `wiki/layers/l4.md` — layer context
- M1_PRD.md — prerequisite (L3 schema v0.1)
- M2_PRD.md — sibling meta-idea, có thể chạy song song
