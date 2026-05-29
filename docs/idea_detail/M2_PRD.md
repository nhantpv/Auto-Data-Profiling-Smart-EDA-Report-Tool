# AI Product Requirements Document — M2

**Product Name:** OpenML-CC18 Perturbation Benchmark + Modular Severity-Stack
**Codename:** `vsf-severity-bench`
**Version:** 1.0
**Created:** 2026-05-29
**Status:** Draft — depends on M1 (L3 schema v0.1)

**Contacts:**
- Product Manager / Researcher: hieu.npt1710@gmail.com
- Engineering Lead: (chủ dự án thực hiện)
- Design Lead: (n/a)

---

## 1. Executive Summary

**Purpose:** Tóm tắt M2 cho người không đọc hết tài liệu.

M2 xây dựng một **perturbation benchmark harness** trên **OpenML-CC18** (72 binary-classification datasets, Bischl 2017) cùng **4 component module** dạng plug-in — tất cả đều tiêu thụ/phát finding theo schema L3 (M1):

1. **MCAR/MAR/MNAR detector** (giải gap l2-semantic-anomaly-coverage).
2. **Per-finding calibrator** (giải gap dama-iso-calibrated-severity).
3. **Dataset-level aggregator** (giải gap ml-readiness-verdict).
4. **Compound escalator** (giải gap compound-severity-aggregation).

Mỗi component có thể publish riêng (research paper standalone); cả 4 chained end-to-end tạo thành **severity-aware ML-readiness pipeline**.

Nguyên cớ: Phân tích hội tụ chỉ ra "Chain α — Severity stack" là chuỗi sâu nhất (5 ý tưởng) và F1 (OpenML harness) + F2 (IBM DQ Toolkit signals) là **2 foundation được 9 ý tưởng dùng chung**. Build harness 1 lần → reuse 4×.

**Success criteria:**
- Aggregator dự đoán **realized RF test-accuracy drop với R² ≥ 0.5** trên held-out 12-dataset split, đánh bại baseline max-only (R² kỳ vọng ≤ 0.3).
- Compound escalator đạt **Spearman ρ ≥ 0.5** giữa compound tier và realized accuracy-drop rank, vượt max-only baseline (ρ ≤ 0.35) trên ≥ 30/72 datasets.
- MCAR/MAR/MNAR detector đạt **≥ 85 % mechanism-classification agreement** với ground-truth trên ≥ 45 synthetic-injected trials.
- Calibrator đạt **≥ 70 % tier-agreement** với downstream-impact ground-truth (RF accuracy-drop bucket).
- Cả 4 component round-trip L3 schema (M1) sạch, không lossy.

---

## 2. Market Opportunity

**Giai đoạn thị trường:** Benchmark cho ML data-quality đang ở giai đoạn **early growth** — đã có ADBench (Han 2022) cho anomaly detection, OpenML-CC18 (Bischl 2017) là tiêu chuẩn cho ML eval, nhưng **chưa có benchmark chuẩn cho "DQ → ML-readiness prediction"**.

**Drivers:**
- Cộng đồng ML đang chuyển từ "model-centric" sang "data-centric AI" (Ng 2021).
- IBM DQ Toolkit (Gupta 2021) đưa ra 4 signal định lượng — nhưng chưa ai chạy regression trên scale OpenML để fit weight.
- Cleanlab + Confident Learning (Northcutt 2021) chứng minh data-quality predictors hữu ích nhưng chưa được chuẩn hoá thành readiness verdict.

**TAM / market value:** Nghiên cứu — target venue: NeurIPS Datasets & Benchmarks track, VLDB DBQual workshop, DEEM. Không doanh thu trực tiếp.

**Per [merged_research §4.4]:** Hiện không có công cụ OSS nào phát ra "READY / WARN / NOT_READY verdict" với confidence interval đã calibrated — Schwabe 2024 METRIC framework dừng ở khung lý thuyết, không có implementation.

---

## 3. Strategic Alignment

M2 phù hợp với mục tiêu dài hạn dự án vì:
- **Cung cấp evidence empirical** cho lớp L3 → L4 verdict (Framing D Element 2).
- Mỗi component **standalone publishable**, hỗ trợ chiến lược "khoá kiến thức + đăng paper" cho nghiên cứu sinh.
- Mid-term objective: tăng số research artifact của dự án từ 0 hiện tại lên ≥ 4 component-level publications trong 6 tháng.
- Validate empirically rằng L3 schema (M1) đủ giàu để chứa toàn bộ severity-stack — feedback loop về M1.

---

## 4. Customer & User Needs

**Phân khúc/persona chính:**

1. **Persona A — Chính chủ dự án + advisor học thuật.**
   Jobs-to-be-done: viết paper hoặc thesis chapter với benchmark có defensible methodology. Đau điểm: không có harness sẵn để chạy 72-dataset experiment trong 1 tuần.

2. **Persona B — Reviewer NeurIPS / VLDB.**
   Jobs-to-be-done: kiểm tra reproducibility, scale, statistical rigor. Đau điểm: nhiều DQ paper baselines yếu, datasets nhỏ; cần benchmark trên scale OpenML.

3. **Persona C — Data scientist enterprise** muốn biết "data này sẵn sàng train chưa?".
   Jobs-to-be-done: verdict đáng tin cậy hơn linh cảm. Đau điểm: hiện chỉ có deequ/GE pass/fail, không có ML-readiness verdict.

**Ràng buộc:**
- Tất cả dataset phải có license cho phép redistribute (OpenML CC0/CC-BY).
- Reproducible: seed-fixed, environment lock (`requirements.txt` + Python version).
- Compute budget: chạy được trên 1 máy laptop 16 GB RAM hoặc 1 colab notebook trong < 24 giờ tổng.

**Vấn đề ưu tiên:** Persona A (research). Persona B/C là indicator validity của design choices, không phải khách trực tiếp.

---

## 5. Value Proposition & Messaging

**Giá trị cốt lõi:**
> "Một harness duy nhất, 4 component modular, 72 dataset — chứng minh empirical rằng aggregator + calibrator + escalator của bạn dự đoán realized ML accuracy-drop tốt hơn baseline."

**Khác biệt vs ADBench / OpenML-CC18:**
- **vs ADBench (Han 2022):** ADBench evaluate anomaly detectors trên anomaly recall; M2 evaluate **predictor of downstream ML impact** — orthogonal contribution.
- **vs OpenML-CC18 (Bischl 2017):** OpenML-CC18 là tập dataset, không phải benchmark cho DQ. M2 dùng OpenML-CC18 làm input, thêm perturbation injection layer.
- **vs IBM DQ Toolkit (Gupta 2021):** IBM Toolkit cung cấp signals; M2 cung cấp **regression-fitted weights + verdict + held-out validation**.

**Messaging (1 câu):**
> "Build harness once, reuse for any DQ predictor — biết chính xác signal nào dự đoán model failure."

---

## 6. Competitive Advantage

**Defensibility:**
- **Tài sản:** synthesis của dự án + L3 schema từ M1 (severity-aware finding format).
- **Chain α tích hợp 4 ý tưởng** — đối thủ phải re-implement cả 4 component để compete.
- **Held-out methodology** (12 dataset hold-out, stratified): defensible vs reviewer.
- **Reproducibility lock-in:** packaged harness + Docker image; reviewer chạy lại không sai.

**Sustainability:**
- Vì là benchmark public, defensibility = community usage. Nếu paper được accept và cited, M2 trở thành "the OpenML-CC18 DQ extension" — terminology lock-in.
- Risk: nếu Cleanlab hoặc Snorkel publish trước, M2 mất first-mover. Mitigation: ship trong 4 tuần kể từ M1 hoàn thành.

---

## 7. Product Scope and Use Cases

**Năng lực then chốt:**
1. **Perturbation harness** (~600 LOC Python):
   - Loader OpenML-CC18 (72 datasets) via `openml-python`.
   - 5 perturbation type: label noise (5/10/20 %), feature shuffle, class imbalance subsample, missing injection (MCAR/MAR/MNAR), feature redundancy (duplicate top-corr column).
   - 3 ML algorithm: RandomForest, LogisticRegression, GradientBoosting (sklearn defaults).
   - Train/test split stratified by n_features × n_classes; 60 train / 12 hold-out; 5-fold CV trên train.
   - Output: CSV/Parquet `(dataset_id, perturbation, magnitude, baseline_acc, perturbed_acc, drop)`.
2. **Component 1 — MCAR/MAR/MNAR detector:**
   - Wrap `missingno` + Little's MCAR test + logistic-regression MAR test + MNAR heuristic.
   - Output L3 finding `{issue_type: MISSING_MECHANISM, mechanism: MCAR|MAR|MNAR, confidence}`.
3. **Component 2 — Per-finding calibrator:**
   - Table-lookup `(finding_type, magnitude_bucket, dq_dimension) → severity_tier`.
   - Default table empirically fit từ harness output.
4. **Component 3 — Aggregator (ML-readiness verdict):**
   - Least-squares regression: realized drop ~ class_overlap + label_purity + class_imbalance + missingness_signal.
   - Output: `{verdict: READY|WARN|NOT_READY, score: float ∈ [0,1], blockers: [], warnings: []}`.
5. **Component 4 — Compound escalator:**
   - Rule: `compound_severity = max(individual_tiers) + 1_per_co_occurring_finding_above_WARN_on_same_column`.
   - Bounded at CRITICAL.
6. **End-to-end chain test:** L1 stub → L2 detector → L3 aggregator → L4 print, round-trip không lossy.

**Out-of-scope (M2 không làm):**
- Không build narrator L4 (đẩy M3).
- Không streaming / time-series (Kats là phạm vi M1 + future).
- Không real production deployment.
- Không multi-class / regression task (chỉ binary classification per OpenML-CC18 default).
- Không component 5+ (giữ 4 component cố định).
- Không UI hay dashboard.

**Outcome đo lường:** xem §1 success criteria.

**High-risk assumption:**
- **A1:** "IBM DQ Toolkit signals có Python API hoặc dễ reimplement" — verify trong tuần 1; fallback dùng Cleanlab + sklearn proxy.
- **A2:** "Linear weighted aggregator đạt R² ≥ 0.5" — kill criterion: nếu R² < 0.3 trên 24h MVP, signals không predictive → pivot sang per-family surrogate (ml-readiness-3).
- **A3:** "Compound rule đơn giản đủ tốt" — kill nếu Spearman ρ < 0.3 → thử copula-based (compound-2) hoặc causal DAG (compound-3).

---

## 8. Non-Functional Requirements

### 8.1 General Requirements

- **Performance:** chạy full benchmark (72 dataset × 5 perturbation × 3 algorithm × 5-fold) trong ≤ 24 giờ trên laptop 16 GB / 8-core.
- **Scalability:** harness phải accept ≥ 100 dataset OpenML-CC18 mở rộng mà không cần refactor.
- **Reliability:** seed-fixed (`numpy.random.seed`, `sklearn.utils.check_random_state`); reproducible bit-identical metric.
- **Security:** không secret; data tải qua OpenML API public.
- **Reproducibility:** Docker image + `requirements.txt` lock; CI test chạy 1 dataset slice end-to-end.

### 8.2 AI-Specific Requirements (LLMs)

M2 **không gọi LLM trực tiếp** — đây là deterministic harness. Tuy nhiên:
- Tất cả 4 component đều **emit L3 finding** (M1 schema) sao cho M3 narrator có thể tường thuật được.
- Calibrator severity tier + Aggregator verdict text phải có **rationale string** human-readable để M3 reuse trong prompt.
- Không component nào được "auto-generate explanation bằng LLM" — quy tắc deterministic-first.

**Validation cho M3 readiness:** sau khi M2 xong, ≥ 95 % finding output của component pass `jsonschema.validate` của M1.

---

## 9. Go-to-Market Approach

**Phase 1 (M2 scope) — Tuần 1-3 (sau khi M1 v0.1 done):**
- **Target:** Persona A (research output).
- **Deliverable:** repo `vsf-severity-bench` với CLI `run-bench.py`; tabulated results trên 72 dataset; 4 component module riêng biệt.
- **Success metric:** 4 kill criteria pass (xem §1).
- **Evidence:** CSV/JSON results table; 1 confusion-matrix figure cho MCAR/MAR/MNAR; 1 R² scatter plot cho aggregator.

**Phase 2 (Tuần 4-6) — Paper draft:**
- Short paper (workshop format, 4-6 trang).
- Bench results + ablation: per-component vs full chain.

**Phase 3 (Tháng 3+, ngoài scope tài liệu):**
- Submit NeurIPS Datasets & Benchmarks track hoặc DEEM workshop.
- Extend với conformal wrapper (ml-readiness-2) và per-family surrogate (ml-readiness-3).

---

## Cross-references

- `wiki/synthesis/idea-convergence-map-2026-05.md` §3 Meta-Idea M2 + Chain α
- `wiki/gaps/ml-readiness-verdict.md`, `wiki/gaps/dama-iso-calibrated-severity.md`, `wiki/gaps/compound-severity-aggregation.md`, `wiki/gaps/l2-semantic-anomaly-coverage.md`
- `wiki/ideas/ml-readiness-verdict-1-empirical-aggregation-benchmark.md`
- `wiki/ideas/dama-iso-calibrated-severity-3-standalone-calibrator-package.md`
- `wiki/ideas/compound-severity-aggregation-1-max-tier-multiplicative-escalation.md`
- `wiki/ideas/l2-semantic-anomaly-coverage-1-mcar-mar-mnar-plugin-wrapper.md`
- M1_PRD.md — prerequisite (L3 schema v0.1)
