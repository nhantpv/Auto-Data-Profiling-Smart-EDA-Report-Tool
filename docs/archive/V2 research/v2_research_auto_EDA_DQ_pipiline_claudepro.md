# Structured Literature-and-Tool Review: Deterministic-First, LLM-Last Automated EDA / DQ Pipeline

## Section 1 — Academic Papers

1. **Profiling Relational Data: A Survey** — Abedjan, Golab, Naumann. *VLDB Journal* 24(4):557–581, 2015. DOI: 10.1007/s00778-015-0389-y. https://link.springer.com/article/10.1007/s00778-015-0389-y
   - Problem: No unified taxonomy of profiling tasks exists across DB research and industry.
   - Approach: Classifies profiling into single-column statistics, multi-column dependencies (UCCs, FDs, INDs), and conditional/approximate variants; surveys algorithms and tools per class.
   - Relevance: **HIGH** — foundational vocabulary for Layer 1 and the boundary between Layer 1 and Layer 2 (dependency-based DQ).
   - [verified]

2. **Data Quality Toolkit: Automatic Assessment of Data Quality and Remediation for ML Datasets** — Gupta, Patel, Saha et al. (IBM Research). arXiv:2108.05935, 2021. https://arxiv.org/abs/2108.05935
   - Problem: General DQ profiling does not catch ML-specific issues (noisy labels, class overlap, label leakage).
   - Approach: Library of ML-oriented DQ metrics with remediation; exposed as IBM API Hub services for tabular classification/regression readiness.
   - Relevance: **HIGH** — direct prior art for Layer 2 ML-readiness / trainability assessment and for the IBM DQ-for-AI framework cited in project context.
   - [verified]

3. **PyOD: A Python Toolbox for Scalable Outlier Detection** — Zhao, Nasrullah, Li. *JMLR* 20(96), 2019. arXiv:1901.01588. https://arxiv.org/abs/1901.01588
   - Problem: Outlier detection algorithms are fragmented across implementations with inconsistent APIs.
   - Approach: Unified scikit-learn-style API for 20+ detectors (IForest, LOF, OCSVM, HBOS, COPOD, ECOD, autoencoder variants).
   - Relevance: **HIGH** — the canonical Layer 2 outlier-detection backbone for the project.
   - [verified]

4. **PyOD 2: A Python Library for Outlier Detection with LLM-powered Model Selection** — Chen et al. arXiv:2412.12154, 2024. https://arxiv.org/abs/2412.12154
   - Problem: PyOD lacks modern deep detectors and automatic model selection.
   - Approach: 12 PyTorch deep OD models plus an LLM-driven detector-recommendation pipeline (ADBench-informed).
   - Relevance: **HIGH** — informs Layer 2 algorithm coverage and shows an *upstream* LLM use that the project explicitly avoids (LLM choosing detectors, not narrating findings).
   - [verified]

5. **Automating Large-Scale Data Quality Verification** — Schelter, Lange, Schmidt, Celikel, Biessmann, Grafberger. *PVLDB* 11(12):1781–1794, 2018 (Deequ). https://www.amazon.science/publications/automating-large-scale-data-quality-verification
   - Problem: Declarative, scalable DQ verification on Spark-scale tables.
   - Approach: Constraint API + metric computation engine + constraint-suggestion module producing structured check results.
   - Relevance: **HIGH** — canonical Layer-2/Layer-3 prior art; Deequ's constraint-result schema is one of the strongest baselines for the project's Layer 3 ontology.
   - [verified]

6. **TensorFlow Data Validation: Data Analysis and Validation in Continuous ML Pipelines** — Caveness, Suganthan G.C., Peng, Polyzotis, Roy, Zinkevich. *SIGMOD* 2020. https://dl.acm.org/doi/10.1145/3318464.3384707
   - Problem: ML pipelines need scalable, schema-driven data analysis with anomaly detection.
   - Approach: Apache Beam-based statistics computation; schema-as-protobuf; anomaly objects with typed reasons; drift/skew checks vs. previous batches.
   - Relevance: **HIGH** — TFDV's `Anomalies` protobuf is a strong reference design for Layer 3 (machine-readable typed findings).
   - [verified]

7. **Data Validation for Machine Learning** — Breck, Polyzotis, Roy, Whang, Zinkevich. *SysML* 2019. https://research.google/pubs/pub47967/
   - Problem: ML data errors must be caught before training/serving.
   - Approach: Schema inference + per-feature constraints + training/serving skew detection deployed at Google.
   - Relevance: **HIGH** — companion paper to TFDV; articulates the data-as-first-class-citizen position the project shares.
   - [verified]

8. **Data-centric Artificial Intelligence: A Survey** — Zha, Bhat, Lai, Yang, Jiang, Zhong, Hu. arXiv:2303.10158, 2023. https://arxiv.org/abs/2303.10158
   - Problem: Survey of methods that improve data instead of models.
   - Approach: Three-axis taxonomy (training data development, inference data development, data maintenance) with benchmarks.
   - Relevance: **HIGH** — frames the broader research narrative the project sits inside (DQ-for-AI).
   - [verified]

9. **A Survey on Data Quality Dimensions and Tools for Machine Learning** — Zhou, Tu, Wang, Chen, et al. arXiv:2406.19614, 2024. https://arxiv.org/abs/2406.19614
   - Problem: ML-oriented DQ tooling landscape is fragmented across dimensions.
   - Approach: Reviews 17 DQ tools from the last 5 years against DQ dimensions/metrics; proposes a roadmap; flags LLM/GenAI applicability.
   - Relevance: **HIGH** — directly aligned with the project's Layer-3 dimensions grounding (DAMA / ISO 25012) and explicitly considers LLMs in DQ.
   - [verified]

10. **Isolation Forest** — Liu, Ting, Zhou. *ICDM* 2008. DOI: 10.1109/ICDM.2008.17. https://ieeexplore.ieee.org/document/4781136/
    - Problem: Most anomaly detectors profile normality; expensive at scale.
    - Approach: Tree-based recursive partitioning that isolates anomalies in few splits; linear time, sub-sampling friendly.
    - Relevance: **HIGH** — workhorse algorithm in Layer 2; foundational.
    - [verified]

11. **Sherlock: A Deep Learning Approach to Semantic Data Type Detection** — Hulsebos, Hu, Bakker, Zgraggen, Satyanarayan, Kraska, Demiralp, Hidalgo. *KDD* 2019. arXiv:1905.10688. https://arxiv.org/abs/1905.10688
    - Problem: Column type detection beyond syntactic (string/int) into 78 semantic types from DBpedia.
    - Approach: Multi-input DNN over 686,765 VizNet columns; F1=0.89.
    - Relevance: **MEDIUM** — directly relevant to Layer 1 type-inference depth and to "semantic anomaly" novelty in Layer 2.
    - [verified]

12. **Sato: Contextual Semantic Type Detection in Tables** — Zhang, Suhara, Li, Hulsebos, Demiralp, Tan. *VLDB* 2020. arXiv:1911.06311. https://arxiv.org/abs/1911.06311
    - Problem: Sherlock ignores intra-table context.
    - Approach: Adds topic-model + structured prediction (CRF) over neighbouring columns; improves on Sherlock.
    - Relevance: **MEDIUM** — direct extension for cross-column / contextual type signals.
    - [verified]

13. **A Survey on Hallucination in Large Language Models: Principles, Taxonomy, Challenges and Open Questions** — Huang, Yu, Ma, et al. arXiv:2311.05232, 2023–2024 (ACM TOIS). https://arxiv.org/abs/2311.05232
    - Problem: Comprehensive taxonomy of LLM hallucinations and mitigations.
    - Approach: Splits factual vs. faithfulness hallucinations; reviews data-, training-, and inference-stage mitigations including grounding.
    - Relevance: **HIGH** — central reference for justifying the deterministic-first, LLM-last architecture (Layer 4 cannot compute or fabricate stats).
    - [verified]

14. **Investigating Table-to-Text Generation Capabilities of LLMs in Real-World Information-Seeking Scenarios** — Zhao et al. *EMNLP* 2023. arXiv:2305.14987. https://arxiv.org/abs/2305.14987
    - Problem: Can LLMs faithfully narrate tables in realistic settings?
    - Approach: Benchmarks GPT-4 / fine-tuned models on table-to-text faithfulness; finds GPT-4 outperforms fine-tuned baselines on faithfulness; CoT can serve as reference-free metric.
    - Relevance: **HIGH** — empirical grounding for Layer 4 (LLM narrative quality over structured tabular findings).
    - [verified]

15. **LIDA: A Tool for Automatic Generation of Grammar-Agnostic Visualizations and Infographics using LLMs** — Dibia (Microsoft Research). *ACL 2023 (System Demo)*. arXiv:2303.02927. https://arxiv.org/abs/2303.02927
    - Problem: Automate goal-driven visualization with LLMs.
    - Approach: 4-module pipeline — `SUMMARIZER` (data → compact NL summary), `GOAL EXPLORER`, `VISGENERATOR`, `INFOGRAPHER`.
    - Relevance: **LOW** (adjacent, landscape contrast cap-counted). The `SUMMARIZER` is the closest published analogue to feeding deterministic profile metadata into an LLM, but LIDA's output is charts, not DQ narrative.
    - [verified]

16. **Towards Data-Centric AI: A Comprehensive Survey of Traditional, RL and Generative Approaches for Tabular Data Transformation** — Wang, Ying et al. arXiv:2501.10555, 2025. https://arxiv.org/abs/2501.10555
    - Problem: Tabular feature engineering / data prep landscape across automation paradigms.
    - Approach: Reviews feature selection / generation for tabular data with emphasis on AutoML/RL/generative methods.
    - Relevance: **MEDIUM** — useful for AutoML-EDA-stage positioning (MEDIUM-priority bucket).
    - [verified]

*Note on conflicting IDs:* The IBM Data Quality Toolkit paper (arXiv:2108.05935) and the secondary IJISA 2022 "Data Quality for AI Tool: EDA on IBM API" (DOI 10.5815/ijisa.2022.01.04) describe the *same* IBM toolkit from different vantage points (research engineers vs. external evaluation); neither contradicts the other.

## Section 2 — GitHub Repositories

### PRIMARY — Classical EDA / Profiling

| Name | URL | Stars (date) | One-line description | Activity | Input formats | Output formats | Strengths vs project | Gaps vs project | Tag |
|---|---|---|---|---|---|---|---|---|---|
| ydata-profiling | https://github.com/ydataai/ydata-profiling | 13.5k (release v4.18.1 page, 2026) | One-line EDA + DQ alerts for pandas/Spark DataFrames | Active (renamed to fg-data-profiling in late 2025) | pandas, Spark, SQL via Fabric | HTML, JSON, dict | Comprehensive JSON profile incl. alerts list (high_correlation, skewness, uniformity, zeros, missing, constant); strongest Layer-1 baseline | No ML-readiness verdict; alerts are flat strings, not severity-graded; no LLM layer | [verified] |
| Sweetviz | github.com/fbdesignpro/sweetviz | ~3.1k | Side-by-side dataset comparison reports | Last release v2.3.1, November 2023 (per PyPI) — effectively stale | pandas | HTML only | Strong train/test comparison view | HTML-only output makes Layer-3 extraction hard; no JSON | [verified] |
| DataPrep | github.com/sfu-db/dataprep | ~2.2k | Dask-accelerated EDA + cleaning | Semi-active | pandas, Dask | HTML report, Python objects | 10× faster than pandas-profiling on wide data | Maintenance has slowed; JSON profile less mature | [verified] |
| AutoViz | github.com/AutoViML/AutoViz | ~1.9k | Auto-visualize any CSV in one line | Active | CSV, pandas | Charts (matplotlib/bokeh), inline | Quick visual EDA, target-aware "supervised" mode | No structured findings JSON; viz-centric | [verified] |
| klib | github.com/akanz1/klib | ~1.5k | Concise functions for data cleaning, missingness, correlations | Active | pandas | Python objects, plots | Good cross-column correlation views and dtype cleaning | No HTML/JSON report; library style only | [verified] |
| D-Tale | github.com/man-group/dtale | ~5.2k | Interactive web GUI over a DataFrame | Active | pandas | Web GUI; export to code | Interactive exploration | GUI-centric, not pipeline-friendly | [verified] |
| Capital One DataProfiler | github.com/capitalone/DataProfiler | ~1.6k | Profiling library focused on schema/sensitive-data detection across CSV/JSON/Avro/Parquet | Active | CSV, JSON, Parquet, Avro, text | JSON profile incl. PII labels | Strong PII/semantic detection; structured JSON | Heavier dep footprint; less mainstream alert taxonomy | [verified] |

### PRIMARY — Deterministic DQ frameworks

| Name | URL | Stars | One-line description | Activity | Input formats | Output formats | Strengths vs project | Gaps vs project | Tag |
|---|---|---|---|---|---|---|---|---|---|
| Great Expectations | github.com/great-expectations/great_expectations | ~10.4k | Declarative "expectations" assertion framework with Data Docs | Active | pandas, Spark, SQL | ValidationResult JSON, HTML Data Docs | Mature ExpectationSuiteValidationResult JSON; well-typed result objects | Expectation-centric (user must declare); profilers exist but assertions still dominate | [verified] |
| Deequ (Scala) / PyDeequ | github.com/awslabs/deequ | ~3.4k | Spark-scale DQ via constraints + metrics | Active | Spark DataFrames | VerificationResult (constraint statuses + computed metrics) | Constraint-suggestion module; clean metric/check separation; PVLDB-grounded | JVM-first; PyDeequ wrapper less ergonomic | [verified] |
| pandera | github.com/unionai-oss/pandera | ~3.9k | Statistical schema validation for DataFrames | Active | pandas, Polars, PySpark | SchemaErrors object (typed) | Pydantic-style typed schemas | Schema-first, not exploratory profiling | [verified] |
| whylogs | github.com/whylabs/whylogs | ~2.6k | Streaming-friendly statistical data logging | Active | pandas, Spark, Java | Mergeable DatasetProfile (protobuf / JSON view) | Sketch-based, mergeable, language-agnostic format; ideal for Layer 1 at scale | DQ constraints API exists but secondary; no ML-readiness verdict | [verified] |
| deepchecks | github.com/deepchecks/deepchecks | ~3.7k | Suite of validation Checks for data & models | Active | pandas, image, NLP | CheckResult JSON / HTML | Rich Check catalog incl. drift, weak segments | HTML-leaning; CheckResult JSON less standardised than GE | [verified] |
| Soda Core | github.com/sodadata/soda-core | ~2.2k | YAML-defined SodaCL checks executed as SQL | Active | SQL warehouses, Spark, pandas | Scan result YAML/JSON | Declarative SodaCL; warehouse-native push-down | Check-first; weak on free EDA profiling | [verified] |
| TFDV | github.com/tensorflow/data-validation | ~774 | Statistics + schema + anomalies for TFX pipelines | Active | tf.Example, CSV, pandas, Beam | DatasetFeatureStatisticsList + Anomalies protobuf | Strong typed anomaly schema; Beam-scalable | Beam/TFX-coupled; integration overhead | [verified] |
| Evidently AI | github.com/evidentlyai/evidently | ~5.9k | DQ, drift and LLM observability reports | Active | pandas, parquet | Report JSON/HTML; LLM-as-judge descriptors | 100+ metrics; presets for DataDrift/DataQuality; ships an LLM-as-judge layer (but evaluating LLM outputs, not narrating tabular DQ) | LLM layer is judge-of-text, not narrator-of-DQ; coupling to Layer 4 must still be built | [verified] |

### PRIMARY — Traditional ML / statistical libraries for DQ

| Name | URL | Stars | One-line description | Activity | Input formats | Output formats | Strengths vs project | Gaps vs project | Tag |
|---|---|---|---|---|---|---|---|---|---|
| PyOD | github.com/yzhao062/pyod | ~9k | 60+ outlier detectors under sklearn-style API (PyOD 3) | Active | numpy / pandas | decision_scores_, labels_, optional ADEngine routing | Industry-standard; covers ECOD/COPOD/IForest/LOF/OCSVM/AE/VAE; ADEngine orchestration | PyOD 3 introduces LLM-driven orchestration the project deliberately rejects | [verified] |
| alibi-detect (Seldon) | github.com/SeldonIO/alibi-detect | ~2.4k | Outlier, adversarial and drift detection across modalities | Active | tabular, text, image, time-series | dict with `is_drift`, `p_val`, `distance` | KS, MMD, ChiSq, classifier drift; both TF and PyTorch backends | Heavyweight deps; not focused on first-pass tabular DQ | [verified] |
| river | github.com/online-ml/river | 5.6k (latest release v0.24.2, April 15 2026, per GitHub) | Online ML incl. ADWIN, Page-Hinkley drift | Active | streams | Detector objects with `drift_detected` flag | Streaming/online drift detection | Streaming framing may not match batch EDA | [verified] |
| NannyML | github.com/NannyML/nannyml | ~2.2k | Post-deployment performance estimation + drift + DQ | Active | pandas tabular | DriftCalculator results, performance-estimation tables | CBPE/DLE performance estimation + PCA-reconstruction multivariate drift; ranker | Targeted at deployed models with reference period, not first-look profiling | [verified] |
| datasketch | github.com/ekzhu/datasketch | ~2.9k | MinHash, LSH (+Forest, Ensemble), HyperLogLog, HNSW | Active | hashable items | sketch objects, similarity query results | Direct backbone for Layer-2 near-duplicate detection | Need to write the duplicate-finding pipeline on top | [verified] |
| scikit-learn outlier modules | github.com/scikit-learn/scikit-learn | 60k+ | IForest, EllipticEnvelope, LOF, OneClassSVM | Active | numpy / pandas | predict/decision_function | Ubiquitous; well-tested | Single-algorithm depth; PyOD is broader | [verified] |

### PRIMARY / RARE — LLM-on-top-of-deterministic-findings

This is the project's novelty surface, and the OSS landscape is **thin**. Three findings:

| Name | URL | Stars | One-line description | Activity | Input formats | Output formats | Strengths vs project | Gaps vs project | Tag |
|---|---|---|---|---|---|---|---|---|---|
| LIDA `SUMMARIZER` (Microsoft) | github.com/microsoft/lida | ~3.0k | LLM pipeline that summarises data → goals → charts | Active | pandas / CSV | NL summary, viz specs, code | The `SUMMARIZER` is the closest published analogue: deterministic column metadata → compact NL summary fed to downstream LLM stages | Output is visualization, not DQ narrative; no severity/finding ontology | [verified] |
| Evidently LLM-as-judge | github.com/evidentlyai/evidently | ~5.9k | Evaluation framework with `LLMEval` descriptor + `BinaryClassificationPromptTemplate` | Active | text columns | descriptor scores merged into Report | Demonstrates structured-prompt LLM evaluation embedded in a metrics framework | Targets LLM-output evaluation, NOT narrative-from-DQ; coupling must be built | [verified] |
| whylogs + LangKit | github.com/whylabs/langkit | ~900 | OSS toolkit extracting deterministic metrics FROM LLM I/O for whylogs | Active | text in/out | whylogs profiles enriched with LLM-signal columns | Pattern-relevant in reverse: deterministic metrics over LLM text | NOT a "DQ findings → LLM narrative" tool; direction is inverted (clarifying earlier project-brief misconception) | [verified] |

**Negative result:** No flagship, first-party plugin was found that takes a `ydata-profiling`/Great Expectations/whylogs JSON profile and emits an LLM-authored narrative under a structured-findings contract. Many blog tutorials wire `profile.to_json()` to `openai.ChatCompletion`, but no maintained, schema-grounded library exists. This is a genuine open space for the project.

### ADJACENT — one representative each (cap = 3)

| Name | URL | Stars | One-line description | Activity | Tag |
|---|---|---|---|---|---|
| PandasAI | github.com/Sinaptik-AI/pandas-ai | ~15k | LLM agent that executes code to chat with DataFrames — explicitly the *opposite* pattern of this project | Active | [verified] |
| LIDA | github.com/microsoft/lida | ~3.0k | Auto-viz; counted in PRIMARY/RARE above for the SUMMARIZER role; also functions as the auto-visualization adjacent representative | Active | [verified] |
| dbt-expectations | github.com/calogica/dbt-expectations | ~1.1k | Port of Great Expectations to dbt test macros — pure data-contract governance | Active | [verified] |

(*Cap of 3 honored; PandasAI + LIDA + dbt-expectations.*)

## Section 3 — Commercial / Closed-Source Tools

| Vendor | Tool | One-line description | Overlap with deterministic-engine + LLM-narrative architecture | LLM narrative? | Pricing tier |
|---|---|---|---|---|---|
| Monte Carlo | Monte Carlo Data + AI Observability (Incident IQ + AI Agents) | ML-driven freshness/volume/schema/distribution monitoring with LLM-powered root-cause agents | **High.** Incident IQ provides deterministic metric/lineage substrate; "AI Agents" narrate and investigate incidents over those deterministic findings. Per Monte Carlo's official LLM Training & Observability documentation: *"We use Amazon Bedrock to empower our agents with the latest foundational models without the need to manage any infrastructure… Monte Carlo does not fine-tune or retrain them. We exclusively use the pre-trained versions provided."* | Yes | Enterprise. Per Vendr's anonymized transaction benchmarks (vendr.com/marketplace/monte-carlo): mid-sized deployments (50–200 tables, 3–5 sources) typically $30K–$80K/yr; enterprise (300+ tables across 6+ sources) typically $120K–$250K+/yr |
| Anomalo | Anomalo + **AIDA** (launched Oct 29, 2025) | Unsupervised-ML DQ monitoring + conversational LLM analyst grounded in Anomalo's "intelligence layer" | **Highest** — most directly aligned. Anomalo's Oct 29, 2025 GlobeNewswire press release states verbatim: *"What makes AIDA unique is that it is powered by Anomalo's intelligence layer – comprising all the context that Anomalo obtains when it monitors data for data quality. This includes Anomalo's unsupervised machine learning… its rich data profiling, as well as the many insights Anomalo regularly obtains through both out of the box and custom data quality checks. Traditionally used for detecting data quality issues, this intelligence layer now enables AIDA to reason about data in a way that no other AI can."* | Yes | Enterprise (custom; no public list price) |
| Bigeye | Bigeye AI Trust Platform | Lineage-aware data observability with "data health summaries" for business users | Partial — health summaries appear LLM-generated but feature documentation is thinner than Monte Carlo/Anomalo | Partial (unverified whether LLM vs templated) | Enterprise (custom) |
| Acceldata | Acceldata Data Observability Cloud | Multi-domain observability with agentic AI architecture (quality, lineage, profiling agents) | High — agent architecture matches the pattern (agents act on deterministic measurements) | Yes (agent-based) | Enterprise (custom) |
| Soda | Soda Core (OSS) + Soda Cloud | YAML-defined SodaCL checks; cloud UI | Low — strong Layer-2/3 result schema (SodaCL YAML), no prominent LLM narrative feature | No (not prominent) | Free OSS + Cloud paid tiers |
| Collibra | Collibra DQ & Observability (formerly OwlDQ) | Predictive ML-generated DQ rules within Collibra DI Cloud | Low/medium — ML auto-rules but no LLM narrative surfaced in product docs | Not documented | Enterprise |
| Telmai | Telmai Data Reliability Agents (~2025) | ML anomaly detection + plain-English query/explanation; MCP exposure | Medium — explicit NL explanations of anomalies and root causes | Yes | Custom |
| Informatica | Data Quality + **CLAIRE GPT / Agentic CLAIRE GPT** | Enterprise DQ + supervisor agent orchestrating Discovery / DQ / Integration agents over Azure OpenAI / Anthropic Claude | High — IDQ produces deterministic profiles, CLAIRE agents narrate and recommend rules | Yes | Enterprise (IPU consumption) |

*BI-assistant cap (≤2):* Julius AI and Hex Magic / Tableau Pulse are noted only for landscape contrast; both are chat-with-data analyst tools (the explicit anti-pattern) and are not expanded.

## Section 4 — Gap Analysis

**1. Layer-1 / Layer-2 coverage.** Layer-1 deterministic profiling is exceptionally well-covered: ydata-profiling, DataPrep, Capital One DataProfiler, whylogs, and TFDV between them handle types, distributions, quantiles, cardinality, correlations, skewness, entropy, null patterns, and value-frequency tables. Layer-2 detection is covered by composition rather than by a single library: PyOD/scikit-learn (IForest, LOF, OCSVM, ECOD, COPOD, autoencoder), alibi-detect (KS, MMD, ChiSq, classifier drift), NannyML (PCA-reconstruction multivariate drift; CBPE/DLE post-deployment), datasketch (MinHash/LSH/HNSW), and TFDV/Deequ (schema/skew). MCAR/MAR/MNAR diagnostics, latent leakage detection and cross-column inconsistency are *not* first-class in any one library; this is real white space.

**2. Layer-3 ontology gap.** Among the surveyed Layer-3 outputs:
- **ydata-profiling JSON** — richest column-level profile; alerts are flat strings without severity.
- **Great Expectations `ExpectationSuiteValidationResult`** — strongly typed result objects but oriented to user-declared expectations, not auto-discovered findings.
- **whylogs `DatasetProfile`** — mergeable, sketch-based, language-agnostic; excellent for distributed/incremental but lean on issue semantics.
- **Deequ `VerificationResult`** — clean separation of metrics and constraint statuses; closest to a DQ-finding object but JVM-first.
- **TFDV `Anomalies` protobuf** — typed reasons and short/long descriptions, schema-grounded; the strongest *issue-typed* schema we found.
- **SodaCL scan result (YAML)** — declarative checks with pass/fail, light on statistical context.
- **Frictionless validation report** — table-shape and constraint focused; weak on statistical findings.
- **OpenLineage DQ facets** — interchange-only, not a finding ontology in their own right.

**Recommendation:** the strongest single baseline to extend is the **TFDV `Anomalies` schema** (typed reason enums + severity-like short descriptions + per-feature scope), grafted onto **whylogs `DatasetProfile`** as the statistical substrate (mergeable, language-agnostic). DAMA-DMBOK 6 dimensions / ISO 25012 should be added as orthogonal tags on each finding.

**3. Layer-4 gap.** In OSS, putting an LLM strictly *over* deterministic findings is essentially unimplemented as a maintained, schema-grounded library: LIDA's `SUMMARIZER` does the closest thing (compact NL summary from deterministic metadata) but feeds visualization, not DQ narrative; Evidently's LLM-as-judge evaluates LLM outputs, not tabular DQ; whylogs+LangKit goes in the inverse direction (metrics from LLM text). In commercial tooling the pattern is rapidly emerging: **Anomalo AIDA** (Oct 2025) is the most explicit deterministic-findings → LLM-reasoning architecture; **Monte Carlo AI Agents** is the most mature; **Informatica Agentic CLAIRE GPT** and **Acceldata** agents follow. None publish their finding ontology or prompt scaffolding.

**4. Combined-pipeline gap.** No single OSS tool covers L1 + L2 + L3 + L4. The closest stacks are: (a) **whylogs (L1) + Evidently (L2) + custom JSON (L3) + custom LLM wrapper (L4)**, or (b) **TFDV (L1+L2+L3) + custom LLM (L4)**. Commercially, **Anomalo + AIDA** is the only end-to-end implementation that mirrors the project's exact layering, but is closed-source.

**5. DQ-dimension grounding.** Almost no surveyed tool grounds severity in DAMA-DMBOK or ISO 25012; thresholds are ad-hoc and per-check. Soda Cloud and Collibra DQ expose dimension *labels* on rules but do not derive severity from them. Treating ISO/IEC 25012 dimensions as first-class fields on every finding would be a clear differentiator.

**6. Strongest differentiator.** Combine three rare elements: (i) a *single*, versioned, machine-readable **Structured Finding Schema** that fuses TFDV-style typed reasons, Deequ-style metric/constraint separation, and DAMA/ISO 25012 dimension tagging; (ii) **deterministic ML-readiness verdict** computed by Layer 2 (IBM Data Quality Toolkit-style noisy-label / class-overlap / leakage signals); (iii) a Layer-4 LLM whose prompt contract *forbids numerical synthesis* — the LLM may only quote, prioritise and interpret values present in Layer-3 findings. None of the surveyed tools combine all three with reproducibility guarantees.

**7. Technical risks unsolved.** Even with structured Layer-3 input, LLMs hallucinate on numerical reasoning under multi-issue compounding (well-documented in the hallucination survey, arXiv:2311.05232); commercial agents (Monte Carlo, Anomalo) do not publish hallucination rates on numerical narrative. **Severity calibration when issues compound** (e.g. high missingness + drift + label leakage) is unaddressed — every tool surveyed scores findings independently. **Wide-table profiling (>1000 columns)** stresses ydata-profiling and DataPrep; whylogs and TFDV scale better via sketches and Beam. **Semi-structured columns** (JSON-in-text, free text) are largely ignored outside Capital One DataProfiler and whylogs. **Mapping a finding to a concrete Data/AI-readiness verdict** is only attempted by IBM DQ Toolkit. **Reproducibility of the LLM narrative across runs** is a known weakness of all LLM-narrative commercial features; no vendor advertises deterministic narrative seeds or content-addressed prompt logs.

## Section 5 — Suggested Reading Order

1. **Abedjan, Golab, Naumann — Profiling Relational Data: A Survey (VLDB Journal 2015)** — foundational vocabulary you will use in every layer.
2. **Schelter et al. — Automating Large-Scale Data Quality Verification / Deequ (PVLDB 2018)** — the cleanest published architecture for constraint + metric + structured result that maps onto Layer 2 and Layer 3.
3. **Caveness et al. — TFDV: Data Analysis and Validation in Continuous ML Pipelines (SIGMOD 2020)** plus Breck et al. *Data Validation for ML* (SysML 2019) — the strongest reference for a typed Anomalies schema, which is the Layer-3 baseline to extend.
4. **Zhou et al. — A Survey on Data Quality Dimensions and Tools for ML (arXiv 2406.19614, 2024)** — anchors your DAMA/ISO 25012 dimensions story and surveys 17 tools you'll need to reference.
5. **Gupta et al. — IBM Data Quality Toolkit (arXiv 2108.05935, 2021)** — direct prior art for ML-readiness assessment, which is the Layer-2 novelty closest to your differentiator.

LLM-narrative / hallucination references (Huang 2311.05232; Zhao 2305.14987; Dibia LIDA 2303.02927) come *after* you have solidified Layers 1–3.