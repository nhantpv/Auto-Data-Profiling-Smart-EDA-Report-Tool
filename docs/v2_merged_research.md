# Automated EDA + Data Quality Detection with LLM-Assisted Reporting: Consolidated Literature & Tool Review

> **Synthesized from 5 research sources**: Consensus.app, ChatGPT (OpenAI), Perplexity, Perplexity Pro, Claude Pro
>
> **Topic scope**: Academic papers, open-source repositories, commercial tools, gap analysis, and reading order for a deterministic-first, LLM-last automated EDA / Data Quality (DQ) pipeline architecture (Layer 1 = profiling → Layer 2 = DQ/anomaly detection → Layer 3 = structured findings ontology → Layer 4 = LLM-as-interpreter narrative reporting).

---

## Table of Contents

1. [Academic Papers](#1-academic-papers)
   - 1.1. [Foundational Profiling & DQ Surveys](#11-foundational-profiling--dq-surveys)
   - 1.2. [Data Quality Frameworks & Tools Surveys](#12-data-quality-frameworks--tools-surveys)
   - 1.3. [Outlier / Anomaly Detection Algorithms](#13-outlier--anomaly-detection-algorithms)
   - 1.4. [Drift Detection](#14-drift-detection)
   - 1.5. [Semantic Type Detection](#15-semantic-type-detection)
   - 1.6. [ML-Specific Data Quality Tools](#16-ml-specific-data-quality-tools)
   - 1.7. [LLM-Assisted Data Quality / Validation](#17-llm-assisted-data-quality--validation)
   - 1.8. [Continuous / Interactive Data Profiling](#18-continuous--interactive-data-profiling)
   - 1.9. [Hallucination, Faithfulness & LLM Narrative](#19-hallucination-faithfulness--llm-narrative)
   - 1.10. [Data-Centric AI & Auto-Preparation Surveys](#110-data-centric-ai--auto-preparation-surveys)
   - 1.11. [LLM/Agent-as-Data-Analyst Landscape](#111-llmagent-as-data-analyst-landscape)
   - 1.12. [Declarative Data Contracts](#112-declarative-data-contracts)
   - 1.13. [Clinical / Domain Use Cases of LLM Reporting](#113-clinical--domain-use-cases-of-llm-reporting)
   - 1.14. [Standards & Frameworks (Non-arXiv)](#114-standards--frameworks-non-arxiv)
2. [GitHub Repositories](#2-github-repositories)
   - 2.1. [PRIMARY — Classical EDA / Profiling Libraries](#21-primary--classical-eda--profiling-libraries)
   - 2.2. [PRIMARY — Deterministic DQ / Validation Frameworks](#22-primary--deterministic-dq--validation-frameworks)
   - 2.3. [PRIMARY — Traditional ML / Statistical Libraries for DQ](#23-primary--traditional-ml--statistical-libraries-for-dq)
   - 2.4. [PRIMARY / RARE — LLM-on-Top-of-Deterministic-Findings](#24-primary--rare--llm-on-top-of-deterministic-findings)
   - 2.5. [ADJACENT — Landscape Contrast](#25-adjacent--landscape-contrast)
3. [Commercial / Closed-Source Tools](#3-commercial--closed-source-tools)
4. [Gap Analysis](#4-gap-analysis)
   - 4.1. [Layer-1 & Layer-2 Coverage](#41-layer-1--layer-2-coverage)
   - 4.2. [Layer-3 Ontology Gap & Baseline Comparison](#42-layer-3-ontology-gap--baseline-comparison)
   - 4.3. [Layer-4 Gap — LLM as Interpreter](#43-layer-4-gap--llm-as-interpreter)
   - 4.4. [Combined-Pipeline Coverage](#44-combined-pipeline-coverage)
   - 4.5. [DQ-Dimensions Grounding](#45-dq-dimensions-grounding)
   - 4.6. [Strongest Differentiator](#46-strongest-differentiator)
   - 4.7. [Unsolved Technical Risks](#47-unsolved-technical-risks)
5. [Suggested Reading Order](#5-suggested-reading-order)
6. [Appendix A: Source Conflicts](#appendix-a-source-conflicts)
7. [Appendix B: Unique Information by Source](#appendix-b-unique-information-by-source)
8. [References / Sources](#references--sources)

---

## 1. Academic Papers

### 1.1. Foundational Profiling & DQ Surveys

#### 1.1.1. Profiling Relational Data: A Survey
- **Authors**: Ziawasch Abedjan, Lukasz Golab, Felix Naumann
- **Year/Venue**: 2015, *The VLDB Journal* 24(4): 557–581
- **DOI**: https://doi.org/10.1007/s00778-015-0389-y
- **Link (Springer)**: https://link.springer.com/article/10.1007/s00778-015-0389-y
- **Problem statement**: How can metadata (statistics, dependencies, uniqueness, data types) be systematically extracted from relational datasets without requiring user-specified queries? No unified taxonomy of profiling tasks exists across DB research and industry.
- **Approach**: Defines the full taxonomy of data profiling tasks — single-column analysis (distributions, data types, cardinality, null counts), two-column analysis (correlations, functional dependencies), and multi-column analysis (inclusion dependencies, unique column combinations) — and surveys algorithms for each. Proposes a unified profiling language (DPQL) and cost models for profiling at scale. Classifies profiling into single-column statistics, multi-column dependencies (UCCs, FDs, INDs), and conditional/approximate variants.
- **Relevance**: **HIGH** — Canonical/foundational reference for Layer-1 design; the taxonomy of single/multi-column profiling directly maps to what the project's deterministic profiling engine must compute. Anchors the profiling side of the project and helps define what belongs in the structured findings file. Also defines the boundary between Layer 1 and Layer 2 (dependency-based DQ).
- **Tag**: [verified]
- **Notes**: The paper is consistently cited as DOI 10.1007/s00778-015-0389-y across multiple independent sources. No conflicting arXiv ID was found; the paper predates arXiv-first norms for database venues and was published directly in the VLDB Journal. Waterloo page (https://uwaterloo.ca/data-systems-group/publications/profiling-relational-data-survey) is the canonical bibliographic source.

#### 1.1.2. A Data-centric AI Framework for Automating Exploratory Data Analysis and Data Quality Tasks
- **Authors**: Hima Patel, Shanmukha C. Guttula, Nitin Gupta, Sandeep Hans, Ruhi Sharma Mittal, L. N (IBM Research - India, IIT Bombay)
- **Year/Venue**: 2023, ACM Journal of Data and Information Quality, Vol. 15, pp. 1–26
- **DOI**: https://doi.org/10.1145/3603709
- **Problem**: Existing EDA and DQ tools focus on basic checks but lack ML-readiness metrics and actionable remediation guidance.
- **Approach**: Proposes a framework with novel algorithms for EDA and DQ tailored to ML needs, validated via user studies showing productivity gains and improved model performance.
- **Relevance**: **HIGH**
- **Tag**: [verified]

#### 1.1.3. Data Quality Awareness: A Journey from Traditional Data Management to Data Science Systems
- **Authors**: Sijie Dong, Soror Sahri, Themis Palpanas
- **Year/Venue**: 2024, arXiv:2411.03007 [cs.DB]
- **Link**: https://arxiv.org/abs/2411.03007
- **Problem statement**: How has data quality awareness evolved from classical database management to modern ML/big data systems, and what new DQ challenges have emerged?
- **Approach**: Reviews DQ techniques across traditional DBMS, big data systems, and ML pipelines using a cause-effect model linking big data quality challenges to emerging ML DQ issues. Covers DQ dimensions, anomaly detection, schema management, and data profiling in each era. Claimed to be the first cross-era DQ survey.
- **Relevance**: **HIGH** — Provides historical grounding for Layer-1 and Layer-3 design and clarifies which classical DQ techniques (constraint checking, functional dependency discovery) remain relevant for ML-readiness assessment.
- **Tag**: [verified]

#### 1.1.4. Understanding Data Quality in a Data-Driven Industry Context
- **Source**: 2024, *Data & Knowledge Engineering* / ScienceDirect snippet
- **Link**: https://www.sciencedirect.com/science/article/pii/S2452414X24001729
- **Problem/Approach**: A review that frames data quality around deliberate design and operational enforcement in industry settings.
- **Relevance**: **MEDIUM** — Useful for positioning work in the broader DQ management landscape rather than the algorithmic core. Good positioning paper, but not a core technical reference.
- **Tag**: [uncertain]

### 1.2. Data Quality Frameworks & Tools Surveys

#### 1.2.1. A Survey of Data Quality Measurement and Monitoring Tools
- **Authors**: L. Ehrlinger, E. Rusz, W. Wöß
- **Year/Venue**: 2019/2022, *Frontiers in Big Data*, Vol. 5
- **DOI**: https://doi.org/10.3389/fdata.2022.850611
- **Problem**: Overview of existing data quality measurement and monitoring tools.
- **Approach**: Comparative survey of tools, both open-source and commercial, on DQ measurement features (validation, profiling, monitoring), highlighting functional gaps.
- **Coverage**: Evaluation of tools against criteria (flexibility, automation, scalability). Provides a feature comparison table of popular tools such as Great Expectations, Deequ, Sodadata, etc.
- **Relevance**: **MEDIUM** — Comprehensive overview of existing DQ frameworks (Layer 2).
- **Tag**: [uncertain] (per ChatGPT; some access issues noted)

#### 1.2.2. Big Data Quality Framework: A Holistic Approach to Continuous Quality Management
- **Authors**: Ikbal Taleb, Mohamed Adel Serhani, Chafik Bouhaddioui, Rachida Dssouli
- **Year/Venue**: 2021, *Journal of Big Data*, Vol. 8
- **DOI**: https://doi.org/10.1186/s40537-021-00468-0
- **Problem**: Ensuring end-to-end quality in big data lifecycles is costly and fragmented.
- **Approach**: Introduces a BDQ Management Framework leveraging quality profiles/rules across lifecycle stages; supports both quantitative and qualitative evaluation.
- **Relevance**: **MEDIUM**
- **Tag**: [verified]

#### 1.2.3. A Comparison of Data Quality Frameworks: A Review
- **Authors**: Russell Miller, S. Chan, H. Whelan, J. Gregório
- **Year/Venue**: 2025, *Big Data Cognition & Computation*, Vol. 9, p. 93
- **DOI**: https://doi.org/10.3390/bdcc9040093
- **Problem**: Regulatory-compliant DQ frameworks vary in scope/dimensions; emerging needs not fully addressed.
- **Approach**: Maps major frameworks (TDQM, ISO 8000/25012, DAMA-DMBOK) to common vocabulary; highlights gaps in semantics/quantity dimensions relevant to modern AI systems.
- **Relevance**: **HIGH**
- **Tag**: [verified]

#### 1.2.4. AI-Driven Frameworks for Enhancing Data Quality in Big Data Ecosystems: Error Detection, Correction, and Metadata Integration
- **Authors**: Widad Elouataoui
- **Year/Venue**: 2024, arXiv:2405.03870
- **DOI**: https://doi.org/10.48550/arxiv.2405.03870
- **Problem**: Existing DQ approaches are context-specific and lack comprehensive coverage across quality dimensions in big data settings.
- **Approach**: Proposes interconnected frameworks for metric-based assessment, anomaly detection/correction using AI models; addresses metadata integration; tested on diverse datasets.
- **Relevance**: **HIGH**
- **Tag**: [verified]

#### 1.2.5. Quality Anomaly Detection Using Predictive Techniques: An Extensive Big Data Quality Framework for Reliable Data Analysis
- **Authors**: Widad Elouataoui, Saida E., Yassine Gahi
- **Year/Venue**: 2023, *IEEE Access*, Vol. 11, pp. 103306–103318
- **DOI**: https://doi.org/10.1109/access.2023.3317354
- **Relevance**: Referenced in Consensus gap analysis as a key source on big data quality framework and severity calibration.
- **Tag**: [verified]

#### 1.2.6. A Survey on Data Quality Dimensions and Tools for Machine Learning
- **Authors**: Yuhan Zhou, Fengjiao Tu, Kewei Sha, Junhua Ding, Haihua Chen (variant author list: Zhou, Tu, Wang, Chen, et al.)
- **Year/Venue**: 2024, arXiv:2406.19614 [cs.DB]
- **Link**: https://arxiv.org/abs/2406.19614
- **Problem statement**: Which DQ dimensions and metrics are most relevant for ML, and how well do the 17 major DQ tools cover them? ML-oriented DQ tooling landscape is fragmented across dimensions.
- **Approach**: Defines four DQ dimensions (intrinsic, contextual, representational, accessibility) with associated ML-oriented metrics, then systematically audits 17 tools (including GE, Deequ, whylogs, TFDV, deepchecks) against these dimensions. Finds that most tools emphasize intrinsic/representational dimensions with weak contextual (ML-readiness) coverage. Proposes a roadmap; flags LLM/GenAI applicability.
- **Relevance**: **HIGH** — Directly informs Layer-3 ontology design: the dimension taxonomy is a candidate schema for categorizing DQ findings. The coverage gap for ML-contextual dimensions is the project's primary differentiator. Directly aligned with the project's Layer-3 dimensions grounding (DAMA / ISO 25012) and explicitly considers LLMs in DQ.
- **Tag**: [verified]

#### 1.2.7. A Systematic Review of Tools for AI-Augmented Data Quality Management in Data Warehouses
- **Authors**: Heidi Carolina Tamm (Martinsaari), Anastasija Nikiforova
- **Year/Venue**: 2024, *Business Informatics Research Conference (BIR 2025)*; arXiv:2406.10940 [cs.DB]
- **Link**: https://arxiv.org/abs/2406.10940
- **Problem statement**: To what extent do existing DQ tools support AI-augmented automation of rule detection and anomaly identification in data warehouses?
- **Approach**: Systematic review of 151 DQ tools using multi-phase screening (functionality, trialability, GDPR, architecture); only 10 tools met the full criteria for AI-augmented DQM. Finds that most tools focus on data cleansing for AI rather than using AI to improve DQ management itself; explainability features are scarce.
- **Relevance**: **HIGH** — Empirical confirmation of the Layer-4 gap: almost no tools currently implement AI-as-interpreter over deterministic findings. Provides tool comparison matrix useful for positioning.
- **Tag**: [verified]

#### 1.2.8. What About the Data? A Mapping Study on Data Engineering for AI Systems
- **Authors**: Heck et al.
- **Year/Venue**: 2024, *Empirical Software Engineering*
- **Link**: EMSE 2024
- **Problem**: Survey of technical state related to **data engineering** in AI system development.
- **Approach**: Collects 25 papers (2019–2023) related to data engineering for AI, classified by data lifecycle (collection, processing, storage, etc.), technical solutions, lessons learned, and recommendations for practice.
- **Relevance**: **LOW** — Overview of DataOps/AI engineering lifecycle, less focused directly on DQ/EDA but useful for context-setting.
- **Tag**: [verified]

### 1.3. Outlier / Anomaly Detection Algorithms

#### 1.3.1. Isolation Forest
- **Authors**: Fei Tony Liu, Kai Ming Ting, Zhi-Hua Zhou
- **Year/Venue**: 2008, *ICDM*
- **DOI**: 10.1109/ICDM.2008.17
- **Link**: https://ieeexplore.ieee.org/document/4781136/
- **Problem**: Most anomaly detectors profile normality; expensive at scale.
- **Approach**: Tree-based recursive partitioning that isolates anomalies in few splits; linear time, sub-sampling friendly.
- **Relevance**: **HIGH** — Workhorse algorithm in Layer 2; foundational.
- **Tag**: [verified]

#### 1.3.2. COPOD: Copula-Based Outlier Detection
- **Authors**: Zheng Li et al.
- **Year/Venue**: 2020, *ICDM*
- **Link (arXiv)**: https://arxiv.org/abs/2009.09463
- **Problem**: Proposes an outlier detection method for tabular data, overcoming the performance and explainability limitations of existing methods.
- **Approach**: Builds an empirical *copula* from data, uses the marginal distribution of the copula to compute tail probability for each point. COPOD is parameter-free, high-performance, and explainable.
- **Coverage**: COPOD is evaluated on 30 datasets, demonstrating accuracy and speed improvements. Example of traditional Layer-2 outlier detection.
- **Relevance**: **HIGH** — Specific outlier detection algorithm for DQ.
- **Tag**: [verified]

#### 1.3.3. ECOD: Unsupervised Outlier Detection Using Empirical Cumulative Distribution Functions
- **Authors**: Zheng Li, Yue Zhao, Xiyang Hu, Nicola Botta, Cezar Ionescu, George H. Chen
- **Year/Venue**: 2022, *IEEE Transactions on Knowledge and Data Engineering (TKDE)*
- **Link**: https://arxiv.org/abs/2201.00382
- **Problem statement**: Existing unsupervised outlier detection methods suffer from high computational cost, hyperparameter tuning complexity, and limited interpretability for high-dimensional tabular data.
- **Approach**: ECOD estimates the underlying data distribution non-parametrically using empirical cumulative distribution functions per dimension, then aggregates tail-probability estimates to produce an outlier score. It is parameter-free and provides feature-level interpretability (which dimension drove the score). Outperforms 11 baselines across 30 datasets in accuracy, efficiency, and scalability. Implemented in PyOD.
- **Relevance**: **HIGH** — Directly implements one of the project's named Layer-2 algorithms; its parameter-free design and interpretable per-dimension score are ideal for populating Layer-3 statistical_basis fields.
- **Tag**: [verified]

#### 1.3.4. PyOD: A Python Toolbox for Scalable Outlier Detection
- **Authors**: Yue Zhao, Zain Nasrullah, Zheng Li
- **Year/Venue**: 2019, *JMLR* 20(96) (also *JMLR ML Open Source*)
- **arXiv**: 1901.01588
- **Link**: https://arxiv.org/abs/1901.01588
- **Problem**: Outlier detection algorithms are fragmented across implementations with inconsistent APIs. Python library aggregating >30 algorithms for multivariate outlier detection.
- **Approach**: Unified scikit-learn-style API for 20+ detectors (IForest, LOF, OCSVM, HBOS, COPOD, ECOD, autoencoder variants), plus testing tools and performance optimization modes (JIT, distributed). Provides full lifecycle solution (model creation, evaluation), with features such as ADEngine (automatic algorithm selection and comparison).
- **Relevance**: **HIGH** — The canonical Layer-2 outlier-detection backbone for the project; comprehensive traditional Layer-3 library for DQ (outlier detection).
- **Tag**: [verified]

#### 1.3.5. PyOD 2: A Python Library for Outlier Detection with LLM-powered Model Selection
- **Authors**: Sihan Chen, Zhuangzhuang Qian, Wingchun Siu et al. (USC)
- **Year/Venue**: 2024, arXiv:2412.12154 [cs.LG]
- **Link**: https://arxiv.org/abs/2412.12154
- **Problem statement**: The original PyOD library lacked modern deep learning models, had fragmented PyTorch/TF implementations, and provided no automated model selection, creating barriers for non-expert users.
- **Approach**: PyOD 2 integrates 12 state-of-the-art deep learning OD models into a unified PyTorch framework and adds an LLM-based pipeline (ADEngine) for automated model selection from the 45-algorithm library, guided by ADBench benchmark results.
- **Relevance**: **HIGH** — The definitive paper for PyOD (primary Layer-2 library); the LLM-for-model-selection pattern (LLM picks algorithm, does not compute statistics) is a close analogue to the project's Layer-4 "interpreter not analyst" principle. Informs Layer 2 algorithm coverage and shows an *upstream* LLM use that the project explicitly avoids (LLM choosing detectors, not narrating findings).
- **Tag**: [verified]

#### 1.3.6. ADBench: Anomaly Detection Benchmark
- **Authors**: Songqiao Han, Xiyang Hu, Hailiang Huang, Minqi Jiang, Yue Zhao
- **Year/Venue**: 2022, *NeurIPS 2022 Datasets and Benchmarks Track*
- **Link**: https://arxiv.org/abs/2206.09426
- **Problem statement**: How do 30 existing tabular anomaly detection algorithms compare across levels of supervision, anomaly type, and data corruption?
- **Approach**: Runs 98,436 experiments across 57 tabular benchmark datasets using 30 algorithms spanning unsupervised, semi-supervised, and supervised paradigms; open-sources both datasets and a plug-and-play testbed. Reveals that supervision level dominates performance differences more than algorithm choice for most tabular tasks.
- **Relevance**: **HIGH** — The de-facto benchmark for selecting and justifying Layer-2 outlier detection algorithm choices (IsolationForest, LOF, ECOD, COPOD), directly cited by PyOD documentation.
- **Tag**: [verified]

#### 1.3.7. Anomaly Detection of Tabular Data Using LLMs
- **Authors**: Aodong Li, Yue Zhao, Chen Qiu, Marius Kloft, Padhraic Smyth, Maja Rudolph, Stephan Mandt
- **Year/Venue**: 2024, *ArXiv* abs/2406.16308
- **DOI**: https://doi.org/10.48550/arxiv.2406.16308
- **Problem**: Detecting anomalies in tabular data is challenging without domain-specific models or labeled data.
- **Approach**: Demonstrates that pre-trained LLMs can perform zero-shot batch-level anomaly detection; proposes fine-tuning strategies to align LLMs for this task; benchmarks against SOTA methods on ODDS datasets.
- **Relevance**: **HIGH** (novelty in LLM-based anomaly detection)
- **Tag**: [verified]

### 1.4. Drift Detection

#### 1.4.1. Open-Source Drift Detection Tools in Action: Insights from Two Use Cases
- **Authors**: Müller et al.
- **Year/Venue**: 2024, *arXiv*:2404.18673
- **Problem**: Evaluating open-source distribution/concept drift detection tools.
- **Approach**: Introduces the D3Bench benchmark suite and evaluates three main libraries (Evidently, NannyML, Alibi-Detect) on two real-world scenarios. Analyzed on both functional criteria (drift detection accuracy) and non-functional criteria (time, documentation).
- **Findings**: Results show Evidently excels at general drift detection, NannyML is best at detecting precise change-point timing, and Alibi is strong in handling spurious cases. Highlights pros and cons of each tool.
- **Relevance**: **MEDIUM** — Recent research on drift detection (Layer-2) and available tools.
- **Tag**: [verified]

### 1.5. Semantic Type Detection

#### 1.5.1. Sherlock: A Deep Learning Approach to Semantic Data Type Detection
- **Authors**: Madelon Hulsebos, Kevin Hu, Michiel Bakker, Emanuel Zgraggen, Arvind Satyanarayan, Tim Kraska, Çağatay Demiralp, César Hidalgo
- **Year/Venue**: 2019, *KDD*; arXiv:1905.10688
- **Link**: https://arxiv.org/abs/1905.10688
- **Problem**: Column type detection beyond syntactic (string/int) into 78 semantic types from DBpedia.
- **Approach**: Multi-input DNN over 686,765 VizNet columns; F1=0.89.
- **Relevance**: **MEDIUM** — Directly relevant to Layer 1 type-inference depth and to "semantic anomaly" novelty in Layer 2.
- **Tag**: [verified]

#### 1.5.2. Sato: Contextual Semantic Type Detection in Tables
- **Authors**: Dan Zhang, Yoshihiko Suhara, Jinfeng Li, Madelon Hulsebos, Çağatay Demiralp, Wang-Chiew Tan
- **Year/Venue**: 2020, *VLDB*; arXiv:1911.06311
- **Link**: https://arxiv.org/abs/1911.06311
- **Problem**: Sherlock ignores intra-table context.
- **Approach**: Adds topic-model + structured prediction (CRF) over neighbouring columns; improves on Sherlock.
- **Relevance**: **MEDIUM** — Direct extension for cross-column / contextual type signals.
- **Tag**: [verified]

### 1.6. ML-Specific Data Quality Tools

#### 1.6.1. Data Quality Toolkit: Automatic Assessment of Data Quality and Remediation for Machine Learning Datasets
- **Authors**: Nitin Gupta, Hima Patel, Shazia Afzal et al. / Gupta, Patel, Saha et al. (IBM Research)
- **Year/Venue**: 2021, arXiv:2108.05935 [cs.LG]
- **Link**: https://arxiv.org/abs/2108.05935
- **Problem statement**: Standard data cleaning tools do not detect ML-specific data quality issues like class overlap, feature leakage, or noisy labels. General DQ profiling does not catch ML-specific issues (noisy labels, class overlap, label leakage).
- **Approach**: Introduces the IBM Data Quality for AI Toolkit as a library of DQ metrics (completeness, consistency, accuracy, uniqueness, label purity, class overlap) plus remediation functions. Each metric is assessed independently, and results are output via structured APIs. Library of ML-oriented DQ metrics with remediation; exposed as IBM API Hub services for tabular classification/regression readiness. Provides tutorials via IBM Learning Path and public API Hub.
- **Relevance**: **HIGH** — Closest existing work to the project's Layer 2 + Layer 3 concept: structured, ML-readiness-oriented DQ metrics with an API-accessible result schema. Also defines the "DQ for ML" problem space the project targets. Direct prior art for Layer 2 ML-readiness / trainability assessment and for the IBM DQ-for-AI framework cited in project context.
- **Tag**: [verified]
- **Note**: The IBM Data Quality Toolkit paper (arXiv:2108.05935) and the secondary IJISA 2022 "Data Quality for AI Tool: EDA on IBM API" (DOI 10.5815/ijisa.2022.01.04) describe the *same* IBM toolkit from different vantage points (research engineers vs. external evaluation); neither contradicts the other.

#### 1.6.2. ydata-profiling: Accelerating Data-Centric AI with High-Quality Data
- **Authors**: F. Clemente, G. Ribeiro, A. Quemy, M. Santos, R. Pereira, A. Barros
- **Year/Venue**: 2023, *Neurocomputing* Vol. 554, p. 126585
- **DOI**: https://doi.org/10.1016/j.neucom.2023.126585
- **Problem**: Manual EDA is slow and error-prone; automated profiling must surface complex DQ issues for ML pipelines. Need an automated EDA library to generate high-quality profiling reports supporting data-centric AI.
- **Approach**: Open-source Python package (originally Pandas Profiling) automates profiling with detection of missingness, imbalance, drift, duplicates, cardinality issues; outputs standardized reports for downstream use. Automatically detects complex characteristics (high missingness, constant values, skew, high correlation, fit goodness, duplicates, etc.).
- **Coverage**: Focused on detecting potential data issues and providing a visual interface for fast understanding.
- **Relevance**: **HIGH** — Practical example of Layer-1 profiling tool with JSON results.
- **Tag**: [verified]

#### 1.6.3. Quality Assessment of Tabular Data Using Large Language Models and Code Generation
- **Authors**: Ashlesha Akella, Akshar Kaul, Krishnasuri Narayanam, Sameep Mehta (IBM Research)
- **Year/Venue**: 2025; arXiv:2509.10572 (per Consensus citation: pp. 2713-2748)
- **DOI**: https://doi.org/10.48550/arxiv.2509.10572
- **Link (arXiv PDF)**: https://www.arxiv.org/pdf/2509.10572v1.pdf
- **Problem statement**: Rule-based validation is inefficient for large tabular datasets; semantic errors are hard to detect.
- **Approach**: Combines statistical profiling with LLM-driven rule/code generation using RAG and guardrails for robust DQ assessment; outputs granular reports by dimension. Proposes a three-stage framework combining large-scale statistical inlier detection, LLM-based semantically valid rule generation, and code synthesis for executable validators.
- **Relevance**: **HIGH** — State-of-the-art hybrid deterministic+LLM approach directly relevant to project novelty. This is very close to the "ML/statistics first, LLM advisor second" pattern, though it is still more LLM-generative than the project's intended design. Useful as the nearest known LLM-assisted validator-synthesis precedent.
- **Tag**: [verified]

### 1.7. LLM-Assisted Data Quality / Validation

#### 1.7.1. Test-Driven Evaluation of Linked Data Quality
- **Year/Venue**: 2014, ACM Digital Library
- **Link**: https://dl.acm.org/doi/10.1145/2566486.2568002
- **Problem/Approach**: Formalizes "bad smells" and quality problems as testable conditions for linked data quality assessment. Treats quality checking as test generation rather than narrative analysis, which maps well to a structured validation engine.
- **Relevance**: **MEDIUM** — Conceptual precursor to declarative, test-driven DQ contracts.
- **Tag**: [verified]

#### 1.7.2. Automating Large-Scale Data Quality Verification (Deequ)
- **Authors**: Sebastian Schelter, Dustin Lange, Philipp Schmidt, Meltem Celikel, Felix Biessmann, Andreas Grafberger
- **Year/Venue**: 2018, *PVLDB* 11(12): 1781–1794
- **Link**: https://www.amazon.science/publications/automating-large-scale-data-quality-verification
- **Problem**: Declarative, scalable DQ verification on Spark-scale tables.
- **Approach**: Constraint API + metric computation engine + constraint-suggestion module producing structured check results.
- **Relevance**: **HIGH** — Canonical Layer-2/Layer-3 prior art; Deequ's constraint-result schema is one of the strongest baselines for the project's Layer 3 ontology.
- **Tag**: [verified]

#### 1.7.3. TensorFlow Data Validation: Data Analysis and Validation in Continuous ML Pipelines
- **Authors**: Caveness, Suganthan G.C., Peng, Polyzotis, Roy, Zinkevich
- **Year/Venue**: 2020, *SIGMOD*
- **Link**: https://dl.acm.org/doi/10.1145/3318464.3384707
- **Problem**: ML pipelines need scalable, schema-driven data analysis with anomaly detection.
- **Approach**: Apache Beam-based statistics computation; schema-as-protobuf; anomaly objects with typed reasons; drift/skew checks vs. previous batches.
- **Relevance**: **HIGH** — TFDV's `Anomalies` protobuf is a strong reference design for Layer 3 (machine-readable typed findings).
- **Tag**: [verified]

#### 1.7.4. Data Validation for Machine Learning
- **Authors**: Eric Breck, Neoklis Polyzotis, Sudip Roy, Steven Whang, Martin Zinkevich
- **Year/Venue**: 2019, *SysML*
- **Link**: https://research.google/pubs/pub47967/
- **Problem**: ML data errors must be caught before training/serving.
- **Approach**: Schema inference + per-feature constraints + training/serving skew detection deployed at Google.
- **Relevance**: **HIGH** — Companion paper to TFDV; articulates the data-as-first-class-citizen position the project shares.
- **Tag**: [verified]

#### 1.7.5. AD-LLM: Benchmarking Large Language Models for Anomaly Detection
- **Authors**: Tiankai Yang, Yi Nian, Shawn Li et al. (USC/Northwestern/Adobe)
- **Year/Venue**: 2024, arXiv:2412.11142; accepted Findings of ACL 2025
- **Link**: https://arxiv.org/abs/2412.11142
- **Problem statement**: How effectively can LLMs assist with anomaly detection tasks — zero-shot detection, data augmentation, and model selection — compared to traditional approaches?
- **Approach**: Introduces the AD-LLM benchmark evaluating GPT-4 and Llama 3.1 on NLP AD tasks across three modalities. Finds LLMs are effective at zero-shot AD and data augmentation but that explaining model selection for specific datasets remains challenging. Proposes six future research directions.
- **Relevance**: **MEDIUM** — Illuminates the boundary between what LLMs can usefully contribute (model selection guidance, natural language reasoning about anomalies) versus what they cannot reliably do autonomously. Informs the rationale for the Layer-4 "interpreter not detector" architecture.
- **Tag**: [verified]

### 1.8. Continuous / Interactive Data Profiling

#### 1.8.1. Dead or Alive: Continuous Data Profiling for Interactive Data Science
- **Authors**: Will Epperson, V. Gorantla, D. Moritz, A. Perer
- **Year/Venue**: 2023, *IEEE Transactions on Visualization and Computer Graphics*, Vol. 30, pp. 197–207
- **DOI**: https://doi.org/10.1109/tvcg.2023.3327367
- **Problem**: Manual profiling after each transformation is tedious — errors may go undetected.
- **Approach**: Presents AutoProfiler notebook extension for live/on-demand visual summaries/statistics throughout analysis loop; user study shows increased insight discovery.
- **Relevance**: **HIGH**
- **Tag**: [verified]

#### 1.8.2. Profiler: Integrated Statistical Analysis and Visualization for Data Quality Assessment
- **Authors**: Sean Kandel et al. (Stanford/Berkeley)
- **Year/Venue**: 2012
- **Problem**: Manual identification/fixing of missing/extreme/duplicate values is time-consuming/context-dependent.
- **Approach**: Profiler tool applies automated mining/anomaly detection with coordinated summary visualizations at scale.
- **Relevance**: **MEDIUM**
- **Tag**: [uncertain]

### 1.9. Hallucination, Faithfulness & LLM Narrative

#### 1.9.1. LLMs for Explainable AI: A Comprehensive Survey
- **Authors**: Ahsan Bilal, David Ebert, Beiyu Lin
- **Year/Venue**: 2025, arXiv:2504.00125 [cs.AI]
- **Link**: https://arxiv.org/abs/2504.00125
- **Problem statement**: How can LLMs transform complex ML model outputs (feature importances, SHAP values, counterfactuals) into accessible natural-language explanations for non-expert users?
- **Approach**: Surveys the landscape of LLM-for-XAI approaches covering template-to-LLM evolution, evaluation metrics for explanations (faithfulness, coherence, user satisfaction), and real-world applications across healthcare, finance, and operations. Reviews hallucination risks in explanation generation.
- **Relevance**: **MEDIUM** — The XAI-to-narrative pattern is the closest academic analogue to the project's Layer-4 pattern (deterministic signal → LLM narrative). Specifically covers faithfulness metrics that should constrain Layer-4 outputs.
- **Tag**: [verified]

#### 1.9.2. A Review of Faithfulness Metrics for Hallucination Assessment in LLMs
- **Authors**: Ben Malin, Tatiana Kalganova, Nikolaos Boulgouris
- **Year/Venue**: 2024 (published 2025), arXiv:2501.00269 [cs.CL]
- **Link**: https://arxiv.org/abs/2501.00269
- **Problem statement**: How should faithfulness (factual consistency with a grounding source) be evaluated in LLM-generated text, and which mitigation strategies are most effective?
- **Approach**: Reviews faithfulness evaluation metrics across summarization, QA, and MT tasks; identifies RAG-based and structured prompting frameworks as the most effective mitigation strategies for hallucination. Discusses why LLM-as-evaluator correlates best with human judgment over automated metrics.
- **Relevance**: **HIGH** — Directly applicable to Layer-4 design: the review identifies that structured input with explicit factual anchors (Layer-3 findings) reduces hallucination, which is the architectural bet of the project.
- **Tag**: [verified]

#### 1.9.3. A Survey on Hallucination in Large Language Models: Principles, Taxonomy, Challenges and Open Questions
- **Authors**: Huang, Yu, Ma, et al.
- **Year/Venue**: 2023–2024 (ACM TOIS), arXiv:2311.05232
- **Link**: https://arxiv.org/abs/2311.05232
- **Problem**: Comprehensive taxonomy of LLM hallucinations and mitigations.
- **Approach**: Splits factual vs. faithfulness hallucinations; reviews data-, training-, and inference-stage mitigations including grounding.
- **Relevance**: **HIGH** — Central reference for justifying the deterministic-first, LLM-last architecture (Layer 4 cannot compute or fabricate stats).
- **Tag**: [verified]

#### 1.9.4. Investigating Table-to-Text Generation Capabilities of LLMs in Real-World Information-Seeking Scenarios
- **Authors**: Zhao et al.
- **Year/Venue**: 2023, *EMNLP*; arXiv:2305.14987
- **Link**: https://arxiv.org/abs/2305.14987
- **Problem**: Can LLMs faithfully narrate tables in realistic settings?
- **Approach**: Benchmarks GPT-4 / fine-tuned models on table-to-text faithfulness; finds GPT-4 outperforms fine-tuned baselines on faithfulness; CoT can serve as reference-free metric.
- **Relevance**: **HIGH** — Empirical grounding for Layer 4 (LLM narrative quality over structured tabular findings).
- **Tag**: [verified]

#### 1.9.5. LIDA: A Tool for Automatic Generation of Grammar-Agnostic Visualizations and Infographics using LLMs
- **Authors**: Victor Dibia (Microsoft Research)
- **Year/Venue**: 2023, *ACL 2023 (System Demo)*; arXiv:2303.02927
- **Link**: https://arxiv.org/abs/2303.02927
- **Problem**: Automate goal-driven visualization with LLMs.
- **Approach**: 4-module pipeline — `SUMMARIZER` (data → compact NL summary), `GOAL EXPLORER`, `VISGENERATOR`, `INFOGRAPHER`.
- **Relevance**: **LOW** (adjacent, landscape contrast cap-counted). The `SUMMARIZER` is the closest published analogue to feeding deterministic profile metadata into an LLM, but LIDA's output is charts, not DQ narrative.
- **Tag**: [verified]

#### 1.9.6. METRIC-Framework for Assessing Data Quality for Trustworthy AI in Medicine: A Systematic Review
- **Authors**: D. Schwabe, K. Becker, M. Seyferth, A. Klaß, T. Schäffter
- **Year/Venue**: 2024, *NPJ Digital Medicine*, Vol. 7
- **DOI**: https://doi.org/10.1038/s41746-024-01196-4
- **Relevance**: Referenced in Consensus gap analysis on severity calibration tied to business impact/regulatory standards.
- **Tag**: [verified]

#### 1.9.7. Evaluating Large Language Models on Medical Evidence Summarization
- **Authors**: L. Tang, Z. Sun, B. Idnay, J. Nestor, A. Soroush, P. Elias, Z. Xu, Y. Ding, G. Durrett, J. Rousseau, C. Weng, Y. Peng
- **Year/Venue**: 2023, *NPJ Digital Medicine*, Vol. 6
- **DOI**: https://doi.org/10.1101/2023.04.22.23288967
- **Relevance**: Referenced in Consensus gap analysis on LLM hallucination risks.
- **Tag**: [verified]

### 1.10. Data-Centric AI & Auto-Preparation Surveys

#### 1.10.1. Data-Centric Artificial Intelligence: A Survey
- **Authors**: Daochen Zha, Zaid Pervaiz Bhat, Kwei-Herng Lai, Fan Yang, Zhimeng Jiang, Shaochen Zhong, Xia Hu
- **Year/Venue**: 2023, arXiv:2303.10158 [cs.AI]
- **Link**: https://arxiv.org/abs/2303.10158
- **Problem statement**: How does one systematically understand and organize the rapidly growing body of methods and tools for improving data quality and quantity across the full ML data lifecycle? Survey of methods that improve data instead of models.
- **Approach**: Proposes a taxonomy of data-centric AI tasks under three goals — training data development, inference data development, and data maintenance — covering data collection, labeling, preparation, augmentation, quality evaluation, drift monitoring, and more. Surveys representative methods in each category and benchmarks. Three-axis taxonomy with benchmarks.
- **Relevance**: **HIGH** — Positions the project within the emerging data-centric AI movement; the "data maintenance" pillar directly maps to Layers 1–3. Establishes the intellectual context for why deterministic DQ is now a first-class ML concern. Frames the broader research narrative the project sits inside (DQ-for-AI).
- **Tag**: [verified]

#### 1.10.2. Systematic Review of Data-Centric Approaches in Artificial Intelligence and Machine Learning
- **Author**: Prerna Singh
- **Year/Venue**: 2023, *Data Science and Management*
- **Problem**: Lack of documentation/guidelines for data-centric AI practices impedes systematic improvement of ML pipelines.
- **Approach**: Surveys six major aspects including big data quality assessment/preprocessing/MLOps; discusses technical debt from poor DQ practices.
- **Relevance**: **MEDIUM**
- **Tag**: [verified]

#### 1.10.3. Automated Data Preparation for Machine Learning: A Survey
- **Authors**: Sasa Mladenovic, Marius Lindauer, Carola Doerr (variant attribution: Mladenović et al. 2026, DMLR)
- **Year/Venue**: 2025/2026, *AutoML Workshop* / DMLR; available on HAL / OpenReview
- **Link**: https://openreview.net/forum?id=Euti6LHIOs
- **arXiv ID (per ChatGPT)**: 2602.12345
- **Problem statement**: Data preparation — the most time-consuming stage of the ML pipeline — is largely overlooked by AutoML systems, which assume data is already clean and formatted.
- **Approach**: Claimed to be the first survey focusing explicitly on automated data preparation as a component of AutoML. Covers transformation sequencing, imputation automation, type inference, encoding, and integration with end-to-end AutoML frameworks. Identifies the gap between data-centric AI and AutoML. Emphasizes that AutoML currently focuses on models, has not paid enough attention to DataPrep. Classifies pre-processing automation solutions (missing value handling, transformations, data sequence) and pipelines combined with AutoML. Authors map solutions (end-to-end and standalone) for automated pre-processing, evaluate current limitations, and propose recommendations for the future (e.g., deeper integration into Data-centric AI).
- **Relevance**: **MEDIUM** — Positions the project in the AutoML/AutoDS landscape; demonstrates that Layers 1–2 solve a currently under-automated part of the ML pipeline.
- **Tag**: [verified]

#### 1.10.4. Towards Data-Centric AI: A Comprehensive Survey of Traditional, RL and Generative Approaches for Tabular Data Transformation
- **Authors**: Wang, Ying et al.
- **Year/Venue**: 2025, arXiv:2501.10555
- **Link**: https://arxiv.org/abs/2501.10555
- **Problem**: Tabular feature engineering / data prep landscape across automation paradigms.
- **Approach**: Reviews feature selection / generation for tabular data with emphasis on AutoML/RL/generative methods.
- **Relevance**: **MEDIUM** — Useful for AutoML-EDA-stage positioning (MEDIUM-priority bucket).
- **Tag**: [verified]

### 1.11. LLM/Agent-as-Data-Analyst Landscape

#### 1.11.1. LLM × DATA: A Survey of the Integration between Language Models and Data Systems
- **Authors**: Zhou et al.
- **Year/Venue**: 2025, *arXiv*:2505.18458
- **Problem**: Comprehensive survey of the convergence between LLMs and data management systems.
- **Approach**: Bidirectional analysis: **Data → LLM** (large-scale data processing for LLM training) and **LLM → Data** (using LLMs for data management/mining tasks). Specifically, surveys data ingestion pipelines for LLMs (filtering, browsing, security) and LLM applications (cleaning, integration, querying, system optimization).
- **Coverage**: Broad overview of the LLM–data intersections, from preprocessing data for LLMs to applying LLMs for data tasks.
- **Relevance**: **MEDIUM** — Provides context for combining LLM with data pipelines (useful for hybrid LLM architectures).
- **Tag**: [verified]

#### 1.11.2. LLM/Agent-as-Data-Analyst: A Survey
- **Authors**: Tang et al. (or "Multiple")
- **Year/Venue**: 2025, arXiv:2509.23988 [cs.DB] (September 2025)
- **Link**: https://arxiv.org/abs/2509.23988
- **Problem statement**: How have LLMs and agent frameworks transformed data analysis tasks across structured, semi-structured, unstructured, and heterogeneous data?
- **Approach**: Surveys NL2SQL, ModelQA, table QA, chart understanding, and agentic pipeline orchestration; distils four design goals for intelligent data analysis agents. Compares traditional approaches (rule-based, SKs) with LLM-agent architectures. Examines scenarios by data type (structured, semi-structured, unstructured, hybrid) and summarizes design goals (semantic-aware, autonomous, tool-integrated). Presents examples: NL-to-SQL, QA over JSON/XML, chart-querying, report analysis, etc. Sets out design principles for LLM-as-DS systems (e.g., ability to self-set analysis goals, multi-tool).
- **Relevance**: **LOW / MEDIUM** — Canonical reference for the landscape the project explicitly distinguishes itself from (LLM-as-analyst vs. LLM-as-interpreter). Useful for the "what we are NOT" positioning section. New survey on LLM/agent as analyst (relevant but not focused on DQ).
- **Tag**: [verified]

### 1.12. Declarative Data Contracts

#### 1.12.1. Using Data Contracts to Improve Data Quality
- **Source**: IBM documentation, 2024–2026
- **Link**: https://www.ibm.com/docs/en/ws-and-kc?topic=quality-ensuring-data-data-contracts
- **Description**: Not a paper, but one of the clearest public references for declarative data-contract-driven DQ validation. Shows a YAML/JSON contract stored in Git, executed as validation tests, and retrieved as results through an API, which is very close to a contract-first architecture.
- **Relevance**: **HIGH** — Strong precedent for contract-as-input plus machine-readable test results.
- **Tag**: [verified]

#### 1.12.2. ExpectationSuiteValidationResult — Great Expectations Documentation
- **Source**: 2022, Great Expectations documentation
- **Link**: https://docs.greatexpectations.io/docs/reference/api/core/ExpectationSuiteValidationResult_class
- **Description**: Documentation rather than a paper, but important prior art for structured JSON-like validation results. The object exposes per-check results, success flags, statistics, metadata, and JSON serialization, which is directly relevant to output schema design.
- **Relevance**: **HIGH** — A strong structured-report reference.
- **Tag**: [verified]

#### 1.12.3. Expectation Suite — Great Expectations Documentation
- **Source**: Great Expectations documentation
- **Link**: https://docs.greatexpectations.io/docs/0.18/reference/learn/terms/expectation_suite
- **Description**: An Expectation Suite is a collection of verifiable assertions about data, stored as JSON in the project. One of the clearest examples of declarative validation contracts in the data quality ecosystem.
- **Relevance**: **HIGH** — Close analog to DBML-like contract-driven validation, though not schema-native.
- **Tag**: [verified]

#### 1.12.4. Validating Data — Frictionless Framework Docs
- **Source**: 2022, Frictionless Framework documentation
- **Link**: https://framework.frictionlessdata.io/docs/guides/validating-data.html
- **Description**: Frictionless explicitly frames schema validation as a reusable class of tabular-data checks using Table Schema / Frictionless specs. Especially relevant because the contract and validation artifacts are lightweight and machine-readable.
- **Relevance**: **HIGH** — Very close to a declarative-contract approach.
- **Tag**: [verified]

#### 1.12.5. Frictionless-py Repository (DEVT Framework)
- **Source**: 2014–present
- **Link**: https://github.com/frictionlessdata/frictionless-py
- **Description**: Data management framework for Python that provides functionality to describe, extract, validate, and transform tabular data using Frictionless standards. Not a paper, but a core implementation reference for schema-driven validation.
- **Relevance**: **HIGH** — Important ecosystem anchor.
- **Tag**: [verified]

#### 1.12.6. dbt-expectations
- **Source**: Package docs/repo, 2020
- **Link**: https://github.com/calogica/dbt-expectations
- **Description**: A dbt extension inspired by Great Expectations that ports expectations into dbt tests. Relevant because dbt model contracts and test results are one of the nearest industrial patterns to the "declarative contract + structured findings" idea.
- **Relevance**: **HIGH** — Strong analogous ecosystem, though not DBML-based.
- **Tag**: [verified]

#### 1.12.7. Great Expectations Core Repository
- **Source**: 2025 repo index
- **Link**: https://github.com/orgs/great-expectations/repositories
- **Description**: The project's main repository remains a central example of expectation-driven DQ validation with CI support and structured results.
- **Relevance**: **HIGH** — Essential prior art for contract suites and validation artifacts.
- **Tag**: [verified]

### 1.13. Clinical / Domain Use Cases of LLM Reporting

#### 1.13.1. Automated Structured Data Extraction from Intraoperative Echocardiography Reports Using Large Language Models
- **Authors**: Emily J. Mackay et al.
- **Year/Venue**: 2025, *British Journal of Anaesthesia* (University of Pennsylvania)
- **Problem**: Extracting structured data from unstructured clinical text is labor-intensive and error-prone.
- **Approach**: Uses LLM ensembles with voting strategies to extract key parameters from reports; compares accuracy/yield/error rates across ensemble methods vs human experts.
- **Relevance**: **MEDIUM** (shows LLMs as post-deterministic reporters)
- **Tag**: [verified]

#### 1.13.2. Automated Generation of Discharge Summaries: Leveraging Large Language Models with Clinical Data
- **Authors**: M. Ganzinger et al. (Heidelberg University)
- **Year/Venue**: 2025, *Scientific Reports*
- **Problem**: Generating accurate discharge summaries from structured clinical data remains labor-intensive.
- **Approach**: Uses open-source LLaMA3 model on structured EHR extracts; evaluates output correctness/completeness vs physician-written summaries.
- **Relevance**: **MEDIUM**
- **Tag**: [verified]

### 1.14. Standards & Frameworks (Non-arXiv)

> **Note**: These are standards bodies, not arXiv papers, and are therefore not listed as primary academic references but are critical for grounding Layer-3 ontology.

- **DAMA-DMBOK** — Data Management Body of Knowledge; defines six DQ dimensions: Completeness, Consistency, Integrity, Timeliness, Validity, Uniqueness. Referenced across the surveyed tools and gap analysis.
- **DAMA NL Whitepaper** — "Dimensions of Data Quality (DDQ)", v1.2, September 2020. Verified as a freely accessible PDF at https://www.dama-nl.org/wp-content/uploads/2020/09/DDQ-Dimensions-of-Data-Quality-Research-Paper-version-1.2-d.d.-3-Sept-2020.pdf
- **ISO 8000** — Data Quality standard
- **ISO/IEC 25012** — Data Quality model for software product quality

---

## 2. GitHub Repositories

### 2.1. PRIMARY — Classical EDA / Profiling Libraries

| Name | URL | Stars (date) | One-line description | Activity | Input formats | Output formats | Strengths vs project | Gaps / Limitations |
|------|-----|--------------|----------------------|----------|---------------|----------------|---------------------|---------------------|
| **ydata-profiling** (formerly pandas-profiling) | https://github.com/ydataai/ydata-profiling | ~13k (07/24); 13.5k (release v4.18.1 page, 2026); ~13.6k (2026-05); ~13,000 (May 2026) | One-line EDA + DQ alerts for pandas/Spark DataFrames; Automated EDA/profiling with JSON schema output | Active (YData maintains actively; renamed to fg-data-profiling in late 2025 per Claude Pro) | CSV, Pandas DF, Parquet, Spark DF, SQL via Fabric | HTML, JSON, dict, Jupyter widget | Comprehensive JSON profile incl. alerts list (high_correlation, skewness, uniformity, zeros, missing, constant); strongest Layer-1 baseline; Rich JSON export (`to_json()`) containing per-column distribution stats, correlations, missing values, duplicates — excellent Layer-1 baseline; Spark support for scale; supports diverse statistics (basic stats, distribution, missing, duplicates); exports detailed JSON profile | No ML-readiness verdict; alerts are flat strings, not severity-graded; no LLM layer; JSON export not standardized ontology; lacks complex analysis (cross-column, drift); report-centric, not contract-centric; verbose but parseable; no issue_type taxonomy |
| **Sweetviz** | https://github.com/fbdesignpro/sweetviz | ~4k (Consensus); ~3,000 (May 2026); ~3.1k (2026-05); Last release v2.3.1, November 2023 (per PyPI) — effectively stale per Claude Pro | Visual EDA report generator; Side-by-side dataset comparison reports; Beautiful comparative EDA reports (train vs. test) in two lines | Maintained / Moderately active / stale per Claude Pro | CSV, Pandas DF | HTML (self-contained), Python object | Strong train/test comparison view, useful for detecting dataset shift at EDA time; baked-in dataset comparison (target vs all) | HTML-only output makes Layer-3 extraction hard; no JSON; weak structured output; lacks complex detection |
| **pandas-profiling** (legacy) | https://github.com/pandas-profiling/pandas-profiling | ~12k | Predecessor to ydata-profiling | Legacy | CSV/DataFrame | HTML+JS | Predecessor; historical reference | Superseded by ydata-profiling |
| **DataPrep** | https://github.com/sfu-db/dataprep | ~2k; ~2,000 (May 2026); ~2.2k (2026-05) | Low-code EDA + cleaning + connector library from SFU; Dask-accelerated EDA + cleaning; report profiling, missing handling, visualization | Active / Semi-active (commits 2023/2024) | CSV, Pandas, Dask DF, Parquet | HTML interactive report, Python objects, JSON | Dask-backed, ~10× faster than ydata-profiling on large DataFrames; missing value imputation; DataPrep.clean for standardization; interactive display, schema suggestions | Maintenance has slowed; JSON profile less mature; limited JSON output; not focused on multi-dimensional DQ |
| **AutoViz** | https://github.com/AutoViML/AutoViz | ~1,500 (May 2026); ~1.9k (2026-05) | Automatic chart generation for any dataset; Auto-visualize any CSV in one line for Pandas dataframe | Active / Moderately active (many 2024 commits) | CSV, Pandas DF | Interactive charts (Bokeh/Matplotlib/inline), HTML | Rapid visual EDA; quickly explore relationships (cluster plots, scatter, distribution); target-aware "supervised" mode | Does not provide structured JSON report; primarily visualization-oriented; viz-centric |
| **klib** | https://github.com/akanz1/klib (some sources also cite konstantinstadler/klib) | ~1,000 (May 2026); ~1.5k per Claude Pro; ~522 per ChatGPT (2026-05) | Lightweight data cleaning, profiling, and preprocessing helpers for Pandas; visualization helpers (charts, missing, correlation heatmap) | Active / Moderately active (commit 2024) | Pandas DF | Python outputs, PNG, Matplotlib figures, cleaned DF | Useful utility library; simple, composable cleaning functions; supports fast basic statistical plots, presents DQ characteristics (missing); good cross-column correlation views and dtype cleaning | Not a contract validator; feature limited, no long reports, limited JSON output; no HTML/JSON report; library style only |
| **D-Tale** | https://github.com/man-group/dtale | ~4,500; ~5.2k per Claude Pro | Flask/React interactive UI for exploring Pandas DataFrames; Interactive web GUI over a DataFrame | Active | Pandas DF, Xarray, Dask | Interactive HTML UI, Python/JSON API, export to code | Interactive column-level analysis; can export statistics as JSON via API | GUI-centric, not pipeline-friendly |
| **Capital One DataProfiler** | https://github.com/capitalone/DataProfiler | ~1,400; ~1.6k (2026-05) | Profile + PII/sensitive-data detection with a built-in deep learning labeler; auto-recognizes format, detects PII/NPI | Active (commit 2024) | CSV, Parquet, JSON, AVRO, Text, Pandas DF | JSON report (`profile.report()`), HTML, PDF, CSV, dict | Unique: built-in PII entity detection via NER model; JSON report schema includes `global_stats` + per-column `data_stats` dictionaries — directly usable as Layer-1 output; very relevant for column typing and profiling metrics | Focused on sensitive info; lacks LLM integration; UI limited; heavier dep footprint; less mainstream alert taxonomy |

> ⚠️ **Note on naming**: ChatGPT lists a repo "fg-data-profiling" at `[github.com/fond-data/profiling](https://github.com/fond-data/profiling)`. Claude Pro notes this is the rename of ydata-profiling in late 2025. The mainstream URL remains `github.com/ydataai/ydata-profiling`.

### 2.2. PRIMARY — Deterministic DQ / Validation Frameworks

| Name | URL | Stars | Description | Activity | Inputs | Outputs | Strengths | Gaps / Limitations |
|------|-----|-------|-------------|----------|--------|---------|-----------|---------------------|
| **Great Expectations** | https://github.com/great-expectations/great_expectations | ~9k (Consensus); ~11,400 (Perplexity Pro May 2026); ~11.5k (2026-05 per ChatGPT); ~10.4k per Claude Pro; ~11k-ish Sep 2025 per Perplexity | Deterministic DQ validation framework w/result objects; "Unit tests for data" — define Expectations, validate, get JSON results; Declarative "expectations" assertion framework with Data Docs | Active | CSV, Parquet, SQL DB, Spark, Pandas | JSON (ExpectationValidationResult, ExpectationSuiteValidationResult), HTML (Data Docs), Python dict, YAML | Schema conformance verification, data testing, robust API. Mature ExpectationSuiteValidationResult JSON; well-typed result objects; exports validation result as JSON/YAML | Requires scripting Expectations; JSON output needs careful parsing; no standard DQ mapping; Expectation-centric (user must declare); profilers exist but assertions still dominate |
| **Deequ (Scala)** / PyDeequ | https://github.com/awslabs/deequ | ~2k (Consensus); ~3,300 (May 2026); ~3.6k (2026-05); ~3.4k per Claude Pro | Scala/Spark library for large-scale DQ checks; defining constraints ("unit-test") for big tables; Spark-scale DQ via constraints + metrics | Active / Maintained (cập nhật 2023) | Spark DataFrames (via pydeequ for Python) | Spark DataFrames (constraint check results), Scala case classes, JSON via conversion, VerificationResult (constraint statuses + computed metrics) | Deep Spark integration; constraint suggestion module; clean metric/check separation; PVLDB-grounded; constraint definitions for distributions, missing, JSON output | Spark only; JSON output is test-like, less diverse than profiling; less LLM-oriented; JVM-first; PyDeequ wrapper less ergonomic |
| **pandera** | https://github.com/pandera-dev/pandera / https://github.com/unionai-oss/pandera | ~2k (Consensus); ~4.4k (2026-05 per ChatGPT); ~3.8k per Perplexity Pro; ~3.9k per Claude Pro | Statistical type/schema validation for pandas DataFrame; Pythonic schema validation for Pandas/Polars/Spark DataFrames using type annotations | Active (commit 2024) | Pandas, Polars, Modin, Dask, PySpark DF | Python SchemaError exceptions / check result objects, SchemaErrors object (typed) | Helps with type definitions and correctness checks, pandas-friendly style; Good row/column validation; Pydantic-style typed schemas | Does not create exported file reports; only raises exceptions; doesn't automatically discover errors; not a full profiling/anomaly engine; schema-first, not exploratory profiling |
| **whylogs** | https://github.com/whylabs/whylogs | ~1k (Consensus); ~2,700 (May 2026); ~2.6k per Claude Pro | Logging/profiling library w/statistical summaries; Streaming-friendly statistical data logging | Active (WhyLabs-maintained) | Any tabular, Pandas DF, PySpark, Java, images, text | JSON/YAML, Binary protobuf profile (mergeable), Parquet export, Mergeable DatasetProfile (protobuf / JSON view) | Sketch-based, mergeable, language-agnostic format; ideal for Layer 1 at scale; profile schema storage (protobuf JSON) | DQ constraints API exists but secondary; no ML-readiness verdict; not a finding schema, just statistics summary; lean on issue semantics |
| **deepchecks** | https://github.com/deepchecks/deepchecks | ~2k (Consensus); ~3,800 (May 2026); ~3.7k per Claude Pro | Suite for testing ML/data integrity incl drift/outlier tests; ML model + data validation suite covering integrity, train/test drift, and model evaluation; Suite of validation Checks for data & models | Active | Tabular/model inputs, Pandas DF + model, image, NLP | HTML+JSON, HTML report, JSON result objects, Python CheckResult, CheckResult JSON / HTML | Rich Check catalog incl. drift, weak segments | HTML-leaning; CheckResult JSON less standardised than GE |
| **Soda Core** | https://github.com/sodadata/soda-core | ~1k (Consensus); ~2,400 (May 2026); ~2.4k (2026-05 per ChatGPT); ~2.2k per Claude Pro | Open-source DQ monitoring w/SodaCL config/output; engine to define and check **data contracts** in YAML; YAML-defined SodaCL checks executed as SQL | Maintained / Active (cập nhật 2024) | SQL/tabular, CSV, DB, Parquet, SQL warehouses, Spark, pandas | YAML+JSON, HTML, JSON, YAML scan result object, Soda Cloud dashboard | Strong operational checks; allows writing DQ rules (null check, distribution, naming) in YAML; exports log results JSON/YAML; declarative SodaCL; warehouse-native push-down | CLI/YAML dependent; output mostly logs, no context explanation; less expressive contract modeling; Check-first; weak on free EDA profiling; commercial tool (Cloud) separate |
| **TensorFlow Data Validation (TFDV)** | https://github.com/tensorflow/data-validation | ~2k (Consensus); ~800 (Perplexity Pro May 2026); ~779 (2026-05 per ChatGPT); ~774 per Claude Pro | TensorFlow's statistical profiling/DQ tool; Schema and anomaly detection for ML data pipelines; Statistics + schema + anomalies for TFX pipelines | Maintained / Active (Google-maintained; update 2023) | TFRecords, CSV, Pandas DF, tf.Example, Beam | ProtoBuf, ProtoBuf+JSON, Protocol Buffer (DatasetFeatureStatisticsList, Anomalies), gRPC (Facets UI), JSON (via BigQuery integration), DatasetFeatureStatisticsList + Anomalies protobuf | Large-scale (MapReduce/GCP); auto-generates ML schema; Facets (viz) integration; drift/anomaly detection; Strong on schema drift; Strong typed anomaly schema; Beam-scalable | TF ecosystem only; output in specialized proto/JSON formats; need to learn a separate system; not contract-file agnostic; Beam/TFX-coupled; integration overhead |
| **Evidently AI** | https://github.com/evidentlyai/evidently | ~7k (Consensus); ~6,500 (Perplexity Pro May 2026); ~7.5k (2026-05 per ChatGPT); ~5.9k per Claude Pro | Data drift/dq monitoring w/report objects; Open-source ML and LLM observability framework; DQ, drift and LLM observability reports | Active (Evidently-maintained, commit 2024) | CSV/DataFrame, parquet, Spark (via API), model outputs | HTML+JSON, Report JSON/HTML, JSON metrics, Python dict, Evidently Cloud; LLM-as-judge descriptors | Flexible drift/anomaly reporting; diverse reports (drift test, distribution, statistics); dashboard UI; basic LLM support (Evidently Cloud AI?); 100+ metrics; presets for DataDrift/DataQuality; ships an LLM-as-judge layer | Limited deterministic expectation support; goal is "monitoring"; LLM narrative not integrated; output JSON custom, no standard ontology; LLM layer is judge-of-text, not narrator-of-DQ; coupling to Layer 4 must still be built |
| **Frictionless-py** | https://github.com/frictionlessdata/frictionless-py | ~1,800 per Claude Pro; ~820 per ChatGPT | DEVT framework for describing, extracting, validating, and transforming tabular data using Frictionless standards; general data management framework (metadata/schema, validate, transform) | Active | Frictionless descriptors, Table Schema, CSV/Excel/JSON tabular sources | Validation reports, Python objects, package artifacts, table-shape and constraint focused JSON | Very close to contract-driven validation and structured results; lightweight and machine-readable; strong metadata standards | Lacks ML anomaly layer; not focused on automatic DQ; weak on statistical findings; table-shape and constraint focused |
| **dbt-expectations** | https://github.com/calogica/dbt-expectations | ~1,100 per Claude Pro | Great Expectations-style tests for dbt; port of Great Expectations to dbt test macros — pure data-contract governance | Active | dbt YAML / SQL models / tests | dbt test results / artifacts | Strong declarative validation pattern, but dbt-native, not DBML-native | Limited beyond rule-based checks; dbt ecosystem specific |
| **dbt-core** | https://github.com/dbt-labs/dbt-core | Stars not observed per Perplexity | dbt transformation framework and test ecosystem | Active | SQL models, YAML schema tests | SQL test artifacts, run results | Important contract-adjacent ecosystem; contracts are strong | Not generalized DQ |
| **dbt-adapters** | https://github.com/dbt-labs/dbt-adapters | Stars not observed | dbt adapter layer for warehouses | Active | Warehouse connections | Adapter execution artifacts | Useful for contract enforcement in live DBs | Not DQ-specific |
| **DBML ecosystem** | holistics/dbml | Stars not observed | DBML parser/model ecosystem for the DBML schema language | Active (uncertain) | DBML text | DBML AST / tooling artifacts | Strong schema-spec foundation | No clear DQ engine or LLM advisor (per Perplexity) |

### 2.3. PRIMARY — Traditional ML / Statistical Libraries for DQ

| Name | URL | Stars | Description | Activity | Inputs | Outputs | Strengths | Gaps / Limitations |
|------|-----|-------|-------------|----------|--------|---------|-----------|---------------------|
| **PyOD** | https://github.com/yzhao062/pyod | ~7k (Consensus); ~8,500+ (Perplexity Pro May 2026); ~9.9k (2026-05 per ChatGPT); ~9k per Claude Pro | The most widely used Python library for tabular outlier/anomaly detection (45+ algorithms; 60+ in PyOD 3) | Active (USC team, commit 2024) | Numpy arrays, Pandas DF, array | Per-sample outlier scores + binary labels (numpy arrays); Scores (npy), JSON logs; decision_scores_, labels_, optional ADEngine routing | Wide range of detectors incl IsolationForest, ECOD, COPOD, LOF, DBSCAN, One-Class SVM, autoencoders; PyOD 2 adds LLM-guided model selection (ADEngine); benchmark-aligned via ADBench; agentic workflows; LLM support via od-expert module | No reporting schema; complex to integrate into EDA pipeline; ML-focused; PyOD 3 introduces LLM-driven orchestration the project deliberately rejects |
| **alibi-detect** (Seldon) | https://github.com/SeldonIO/alibi-detect | ~2k (Consensus); ~2,200 (Perplexity Pro May 2026); ~2.5k (2026-05 per ChatGPT); ~2.4k per Claude Pro | Drift/outlier/adversarial detector library; Outlier, adversarial, and concept drift detection with TensorFlow + PyTorch backends; Outlier, adversarial and drift detection across modalities | Active / Maintained (commit 2024) | Tabular/images, Numpy arrays, Pandas DF, TFRecords, tabular, text, image, time-series | Advanced drift/anomaly detectors; Python DetectorResponse dicts with `is_outlier`, `instance_score`, `feature_score`; JSON-serializable detector configs; dict with `is_drift`, `p_val`, `distance` | Covers KS/Chisq/MMD/Wasserstein/LSDD drift tests; TabularDrift for mixed categorical/numerical columns; detector configs are saveable/loadable; supports many tests and ML models for drift/outlier (MMD, autoencoder, statistical) | No reporting schema; raw output (scores); needs wrapping; no LLM integration; heavyweight deps; not focused on first-pass tabular DQ |
| **river** | https://github.com/online-ml/river | ~4k (Consensus); ~1,600 (Perplexity Pro May 2026); ~5,200 per Perplexity Pro elsewhere; ~5.8k (2026-05 per ChatGPT); 5.6k (latest release v0.24.2, April 15 2026, per GitHub per Claude Pro) | Online ML/drift/anomaly detection; Online ML library for data streams including ADWIN, Page-Hinkley drift detectors | Active (commit 2024) | Streams, Python iterables / streaming, pandas-like streams | Python obj, Python DriftDetector objects (drift flag + statistics), Python objects (model, metrics) | Real-time streaming support; ADWIN and Page-Hinkley online concept drift; designed for streaming/incremental DQ signals; suitable for big data streaming | Not focused on batch DQ reporting; streaming framing may not match batch EDA; personalized results, not aggregated JSON export |
| **NannyML** | https://github.com/NannyML/nannyml | ~1k (Consensus); ~1,600 per Perplexity Pro (may be conflated with river); ~2.2k per Claude Pro | Post-deployment drift/performance monitoring; Post-deployment model performance estimation and data drift detection without ground truth labels; Post-deployment performance estimation + drift + DQ | Maintained / Active | Tabular, Pandas obj | Unsupervised concept drift detection; Python result objects (`.data` as DataFrame), interactive Plotly charts; DriftCalculator results, performance-estimation tables | Novel CBPE/DLE algorithms for performance estimation without labels; PCA-based multivariate drift detection links drift alerts back to performance impact; ranker | No deterministic DQ reporting verified; targeted at deployed models with reference period, not first-look profiling |
| **datasketch** | https://github.com/ekzhu/datasketch | ~2k (Consensus); ~2,400 (Perplexity Pro May 2026); ~2.9k (2026-05 per ChatGPT); ~2.9k per Claude Pro | MinHash & LSH duplicate/near-duplicate detector; MinHash, LSH (+Forest, Ensemble), HyperLogLog, HNSW for similarity and near-dup detection | Active / Maintained (commit 2023) | Sets/tabular, strings, streams, sets, hashable items, text/binary | Python obj, Sketches, similarity estimates, sketch objects, similarity query results, Numpy arrays | Efficient duplicate similarity search; MinHashLSH for sub-linear near-duplicate detection; MinHashLSHEnsemble for containment threshold queries; Redis/Cassandra storage backends for scale; direct backbone for Layer-2 near-duplicate detection | No DQ report schema; result is sketch, no visual interpretation; need to write the duplicate-finding pipeline on top |
| **scikit-learn outlier modules** | https://github.com/scikit-learn/scikit-learn | 60k+ per Claude Pro / huge per Perplexity Pro | IForest, EllipticEnvelope, LOF, OneClassSVM; General ML library including outlier and clustering methods | Active | numpy / pandas / Arrays/DataFrames | predict/decision_function / Numpy arrays (decision scores, binary predictions); Estimators, predictions | Ubiquitous; well-tested; industry standard, high performance; IsolationForest, LOF, DBSCAN implementations directly applicable to Layer 2 | Single-algorithm depth; PyOD is broader |

### 2.4. PRIMARY / RARE — LLM-on-Top-of-Deterministic-Findings

This is the project's novelty surface, and the OSS landscape is **thin**. Several partial analogues were identified but no full implementation:

⚠️ **Explicit negative result**: As of May 2026, no open-source repository was found that fully implements the four-layer deterministic-engine → structured-findings → LLM-narrative pipeline the project proposes. Multiple sources confirm this gap (Consensus, Perplexity Pro, Claude Pro, ChatGPT, Perplexity).

Per Consensus: "No open-source repo found matching strict Layer3→Layer4 pattern" [uncertain]

Per ChatGPT: "No official library found that clearly implements the 'first deterministic compute, then LLM presents' pipeline. (Most **LLM data agent** solutions like PandasAI/Vanna allow natural language queries directly to DataFrame, not via predefined deterministic results)." [uncertain]

Per Claude Pro: "**Negative result:** No flagship, first-party plugin was found that takes a `ydata-profiling`/Great Expectations/whylogs JSON profile and emits an LLM-authored narrative under a structured-findings contract. Many blog tutorials wire `profile.to_json()` to `openai.ChatCompletion`, but no maintained, schema-grounded library exists. This is a genuine open space for the project."

The closest partial analogues found:

| Name | URL | Stars | Description | How close to the pattern | Tag |
|------|-----|-------|-------------|---------------------------|-----|
| **whylabs/langkit** | https://github.com/whylabs/langkit | ~600 (Perplexity Pro); ~900 (Claude Pro) | Text metrics toolkit layered on whylogs for LLM monitoring; OSS toolkit extracting deterministic metrics FROM LLM I/O for whylogs | Whylogs produces deterministic profiles of LLM I/O text; LangKit adds NLP metrics; WhyLabs platform visualizes. **The LLM being monitored is the subject, not the reporter** — this is monitoring OF LLMs, not LLM reporting ON data findings; Pattern-relevant in reverse: deterministic metrics over LLM text; NOT a "DQ findings → LLM narrative" tool; direction is inverted (clarifying earlier project-brief misconception) | [verified] |
| **Acceldata Galileo** (closed-source component) | https://github.com/acceldata-io (no public repo for Galileo) | N/A | Acceldata's "Galileo" LLM engine uses GenAI agents (Text-to-Rules, natural-language observability summaries) layered on deterministic profiling and anomaly detection | Closest commercial implementation of the pattern: deterministic DQ engine (profiling + anomaly detection) → structured findings → LLM narrative/recommendations. However, the LLM can also generate SQL and rules autonomously, making it mixed-mode rather than pure interpreter | [verified — commercial] |
| **Evidently + custom LLM wrapper** | https://github.com/evidentlyai/evidently | ~6,500 / ~5.9k | Evidently produces JSON report snapshots; users can wrap these in an LLM call. No built-in LLM narrative layer | The JSON output is suitable as Layer-3 input, but no built-in Layer-4 exists in the open-source package. Community examples exist but no maintained repo was found implementing the full pipeline | [verified — gap confirmed] |
| **LIDA `SUMMARIZER`** (Microsoft) | https://github.com/microsoft/lida | ~3.0k | LLM pipeline that summarises data → goals → charts | The `SUMMARIZER` is the closest published analogue: deterministic column metadata → compact NL summary fed to downstream LLM stages. Output is visualization, not DQ narrative; no severity/finding ontology | [verified] |
| **Evidently LLM-as-judge** | https://github.com/evidentlyai/evidently | ~5.9k | Evaluation framework with `LLMEval` descriptor + `BinaryClassificationPromptTemplate` | Demonstrates structured-prompt LLM evaluation embedded in a metrics framework; Targets LLM-output evaluation, NOT narrative-from-DQ; coupling must be built | [verified] |

**Summary**: The deterministic-engine + LLM-narrative architecture as an end-to-end OSS project does not currently exist. The project would occupy a genuine gap.

Per Perplexity, an additional example noted as a Medium tutorial (informal, not maintained):
- A Medium example illustrating "Prompt-based rule generation from samples" with JSON rules / SQL text output — "Illustrates the pattern, but not a robust implementation." [uncertain]

### 2.5. ADJACENT — Landscape Contrast

| Category | Name | URL | Stars | Description | Note |
|----------|------|-----|-------|-------------|------|
| LLM data agent | **PandasAI** | https://github.com/gventuri/pandas-ai / https://github.com/Sinaptik-AI/pandas-ai / https://github.com/sinaptik-ai/pandas-ai | ~8k (Consensus); ~3.0k per ChatGPT; ~15k per Claude Pro; ~21,000 per Perplexity Pro | Chat-with-data agent / Conversational data analysis via LLM code-generation over DataFrames / "chat" with DataFrame via LLM (openAI) | Natural language interface; Not deterministic-first; Active. Representative of what the project explicitly is NOT: LLM explores raw data directly. **Active** [verified]; ⚠️ star count varies dramatically across sources |
| Chat-to-SQL | **Vanna** | https://github.com/vanna-ai/vanna | ~1k (Consensus) | Chat-to-SQL agent | NL→SQL pipeline. Not deterministic-first [verified] |
| Auto-visualization | **LIDA** | https://github.com/cmudig/lida / https://github.com/microsoft/lida / https://github.com/Prajwal-Narayan/LIDA---Automatic-Generation-of-Visualizations-and-Infographics-with-LLMs | ~500 (Consensus); ~3,300 per ChatGPT; ~4,000 per Perplexity Pro; ~3.0k per Claude Pro | Auto-viz recommender / Grammar-agnostic visualization + infographics generation using LLMs / LLM-based data visualization assistant | LLM generates and executes visualization code; visualization recommendation; not focused on DQ or reporting; useful contrast for LLM-EDA approach. [verified] |
| Interactive UI | **D-Tale** | (already covered in Section 2.1) | (already covered) | Interactive dataframe exploration UI | Useful contrast for EDA/UI, not contract-driven DQ. [uncertain] |
| Auto-visualization (additional) | **AutoViML/sweetviz** | (already covered in 2.1) | (already covered) | Fast EDA comparison/profiling tool | (already covered) |
| Declarative contracts | **frictionless-py** | https://github.com/frictionlessdata/frictionless-py | ~820 per ChatGPT; ~1,800 per Claude Pro | DEVT framework for describing, extracting, validating, and transforming tabular data (already covered in Section 1.12.5 / Section 2.2) | Frictionless validation report is a candidate baseline for Layer-3 schema design [verified] |

> ⚠️ **Cap of 3 honored per source**: Some sources note an adjacency cap. Claude Pro lists: PandasAI + LIDA + dbt-expectations.

---

## 3. Commercial / Closed-Source Tools

| Vendor | Tool | Description | Overlap with deterministic-engine + LLM-narrative architecture | LLM narrative? | Pricing |
|--------|------|-------------|------------------------------------------------------------------|----------------|---------|
| **Monte Carlo** | Monte Carlo Observability / Data + AI Observability (Incident IQ + AI Agents) | End-to-end pipeline observability & DQ monitoring platform / ML-driven freshness/volume/schema/distribution monitoring with LLM-powered root-cause agents / Comprehensive data quality monitoring across pipelines with automatic detection of MISSING/TIMING/DRIFT | **High overlap (Consensus, Perplexity, ChatGPT)** Layer 1&2 + alert/report modules. **Highest per Claude Pro**: Incident IQ provides deterministic metric/lineage substrate; "AI Agents" narrate and investigate incidents over those deterministic findings. Per Monte Carlo's official LLM Training & Observability documentation: *"We use Amazon Bedrock to empower our agents with the latest foundational models without the need to manage any infrastructure… Monte Carlo does not fine-tune or retrain them. We exclusively use the pre-trained versions provided."* | ⚠️ **Conflict across sources**: Consensus/ChatGPT/Perplexity Pro indicate **No** (only dashboards/alerts); Claude Pro indicates **Yes** (incident summaries with NL explanations; closest to Layer-3 + Layer-4); Perplexity Pro also notes "Yes — incident summaries with NL explanations" with 2025 "Graph-AI RCA" module generating natural-language root-cause summaries | Public / Enterprise subscription. Per Vendr's anonymized transaction benchmarks (vendr.com/marketplace/monte-carlo) — Claude Pro: mid-sized deployments (50–200 tables, 3–5 sources) typically $30K–$80K/yr; enterprise (300+ tables across 6+ sources) typically $120K–$250K+/yr; Enterprise SaaS; usage-based |
| **Soda** | Soda Cloud / Soda Core | Open-source DQ rules engine + commercial cloud platform / Cloud extension of Soda Core with AI-assisted check generation and DQ dashboards / Cloud platform for DQ monitoring by policy, extending Soda Core | High overlap Layer 1&2 + YAML result schemas. **Low per Claude Pro** — strong Layer-2/3 result schema (SodaCL YAML), no prominent LLM narrative feature | ⚠️ **Conflict**: Consensus/Claude Pro indicate **No** (rule-based, dashboards / not prominent); Perplexity Pro indicates AI-assisted check generation (not post-hoc narrative); ChatGPT also **No** | Public / Free OSS core + paid cloud tiers (SaaS, monthly fee per ChatGPT) |
| **Anomalo** | Anomalo + **AIDA** (launched Oct 29, 2025 per Claude Pro) | Automated DQ monitoring & root cause analysis / ML-native automated data quality monitoring for warehouses / Detect anomalies in pipelines (batch/stream) using statistical tests / Unsupervised-ML DQ monitoring + conversational LLM analyst grounded in Anomalo's "intelligence layer" | High overlap Layer 1&2 + alert/report modules. **Highest per Claude Pro** — most directly aligned. Anomalo's Oct 29, 2025 GlobeNewswire press release states verbatim: *"What makes AIDA unique is that it is powered by Anomalo's intelligence layer – comprising all the context that Anomalo obtains when it monitors data for data quality. This includes Anomalo's unsupervised machine learning… its rich data profiling, as well as the many insights Anomalo regularly obtains through both out of the box and custom data quality checks. Traditionally used for detecting data quality issues, this intelligence layer now enables AIDA to reason about data in a way that no other AI can."* / Unsupervised ML anomaly detection on warehouse tables; root-cause analysis; no deterministic rule definition required (Perplexity Pro) | ⚠️ **Conflict**: Consensus indicates **No**. ChatGPT indicates **Yes** (uses ML to reduce false alarms) but "not LLM". Perplexity Pro indicates **Partial** — AI-generated anomaly context summaries [uncertain detail]. Claude Pro confirms **Yes** with AIDA launch | Public / Enterprise SaaS (custom; no public list price) |
| **Bigeye** | Bigeye AI Trust Platform (formerly Centrepoint) | Pipeline DQ monitoring & metric tracking / Automated DQ with adaptive thresholds and SLA management / Lineage-aware data observability with "data health summaries" for business users / Auto DQ, measuring PSI/Wasserstein for detecting drift/corruption | High overlap Layer 1&2 + alert/report modules. **Partial per Claude Pro** — health summaries appear LLM-generated but feature documentation is thinner than Monte Carlo/Anomalo. ML-based adaptive threshold anomaly detection; FlexCheck (YAML/UI rules); 2025 "AI-driven data quality" includes auto-generated check suggestions | ⚠️ **Conflict**: Consensus/ChatGPT indicate **No**; Claude Pro indicates **Partial (unverified whether LLM vs templated)**; Perplexity Pro indicates **Limited** — AI assists in check generation; limited narrative reporting | Public / Enterprise / Cloud (contact required per ChatGPT) |
| **Accurics/Splunk** | Accurics/Splunk Observability | Automated DQ/security compliance monitoring platform | Medium overlap Layer 1&2 | No | Public |
| **Acceldata** | Acceldata (Platform) / Acceldata Torch + Galileo / Acceldata Data Observability Cloud | Data observability and pipeline monitoring platform; monitoring big data, performance, data reliability for Enterprise Data Lake/stream / Agentic data management platform with AI-driven profiling, DQ, and observability / Multi-domain observability with agentic AI architecture (quality, lineage, profiling agents) | Strong on observability; can fit structured findings but not a DBML-first contract model. **High per Perplexity Pro & Claude Pro** — Galileo LLM engine sits atop deterministic profiling + anomaly detection; "Text-to-Rules" and NL observability summaries; closest to project's architecture conceptually; agent architecture matches the pattern (agents act on deterministic measurements) | ⚠️ **Conflict**: ChatGPT indicates **No**; Perplexity Pro indicates **Yes** — NL descriptions, DQ summaries, anomaly explanations, Text-to-Rules; includes guardrails and hallucination QA; Claude Pro confirms **Yes (agent-based)** | Enterprise (licensing); Enterprise; contact for pricing |
| **Telmai** | Telmai (Automated AI DQ) / Telmai Data Reliability Agents (~2025) | Data quality and observability, especially for pipelines / Real-time AI-powered data quality for data lakes and lakehouses / DQ platform using AI: validates individual data points by ML, monitors entire data system / ML anomaly detection + plain-English query/explanation; MCP exposure | Overlaps with profiling and anomaly alerts, not a declarative schema contract core. **Medium per Claude Pro** — explicit NL explanations of anomalies and root causes. "Incident Diagnosis Agent" analyzes anomalies and explains root causes; "Data Insight Agent" generates charts and summaries from raw DQ findings; integrates with open table formats | ⚠️ **Conflict**: ChatGPT indicates "Self-claims to use AI, seems ML (unclear if LLM)". Perplexity Pro indicates **Yes** — NL explanations of anomalies and DQ incidents; MCP interface for agents to query validated data context. Claude Pro confirms **Yes** | Enterprise SaaS / Custom |
| **Collibra** | Collibra Data Quality (formerly OwlDQ) / Collibra DQ & Observability | Governance-oriented DQ / Governance solution including DQ module: profiling, cleansing, quality tracking / Predictive ML-generated DQ rules within Collibra DI Cloud / Enterprise DQ platform with behavioral rules, anomaly detection, and data catalog integration | Good governance integration; contract-specific public evidence limited. **Low/medium per Claude Pro** — ML auto-rules but no LLM narrative surfaced in product docs. Behavioral rules learn from historical data patterns; structured DQ scores per dimension; NL explanation features in enterprise tier | ⚠️ **Conflict**: ChatGPT/Claude Pro indicate **No / Not documented**; Perplexity Pro indicates **Partial** — some NL summaries in 2025 Collibra Intelligence Studio integration [uncertain] | Enterprise pricing / licensing |
| **Tableau** | Tableau Prep Builder / Tableau Pulse | BI tool w/data prep/profiling features / BI assistant/narrative layer | Low overlap — focuses on viz not DQ reporting; Very distant from the architecture; helpful only as contrast | No | Commercial / Included in Tableau licensing |
| **PowerBI** | Power Query/Dataflows | BI tool w/data prep/profiling features | Low overlap — focuses on viz not DQ reporting | No | Commercial |
| **DataKitchen** | DataKitchen Enterprise | DataOps and testing platform | Closest commercial angle for pipeline test automation and operational checks | Not specified | Enterprise pricing [uncertain] |
| **Hex** | Hex / Hex Magic | Analyst workspace and AI assistant; BI assistant | Adjacent only; useful contrast for analyst-assistant positioning, not DQ core | (Implied yes) | Freemium/enterprise [uncertain] |
| **Lightup** | Lightup | Automated data quality and observability | Good for anomaly detection and alerting; less visible contract-spec alignment | Not specified | Enterprise pricing [uncertain] |
| **IBM** | IBM InfoSphere QualityStage | Enterprise data quality and matching/standardization suite | Strong rule-based quality workflows; IBM also exposes data contracts in docs | Not specified | Enterprise licensing |
| **Informatica** | Data Quality + **CLAIRE GPT / Agentic CLAIRE GPT** | Enterprise DQ + supervisor agent orchestrating Discovery / DQ / Integration agents over Azure OpenAI / Anthropic Claude | High — IDQ produces deterministic profiles, CLAIRE agents narrate and recommend rules | Yes | Enterprise (IPU consumption) |
| **Julius AI** | Julius (BI Narrative) | LLM-first data analysis and visualization agent; LLM-based feature for automatic report generation in BI (answers queries, describes visualizations) | Mostly Layer-4 (narrative); Layer-1/2 via input dashboards / LLM explores raw data directly; antithesis of the project's architecture | Yes – generates story/visual explanations based on data (LLM GPT-4) / Yes — but LLM reasons over raw data, not structured findings | BI SaaS (included in Julius package) / SaaS, freemium |

> *Note (ChatGPT)*: "LLM data agents (PandasAI, Athenic) or other BIs are not listed; only Julius is cited to illustrate LLM narrative. The 'LLM narrative?' column indicates whether the tool has natural language report/explanation features."

> *BI-assistant cap (≤2) per Claude Pro*: Julius AI and Hex Magic / Tableau Pulse are noted only for landscape contrast; both are chat-with-data analyst tools (the explicit anti-pattern) and are not expanded.

---

## 4. Gap Analysis

### 4.1. Layer-1 & Layer-2 Coverage

**Layer-1 (Profiling) — Well-covered:**

Per Consensus: Most open-source tools provide strong coverage for deterministic profiling (Layer 1) — type inference/distributions/nulls/cardinality/skewness — and basic statistical anomaly/outlier/drift detection (Layer 2), e.g., ydata-profiling (Clemente et al., 2023), Great Expectations (Clemente et al., 2023), PyOD (Clemente et al., 2023; Li et al., 2024), Evidently AI (Clemente et al., 2023). However, deep semantic anomaly detection (cross-column inconsistency/leakage signals), MCAR/MAR/MNAR missingness patterns or advanced leakage diagnostics remain limited.

Per Perplexity Pro: The combination of ydata-profiling, DataPrep, and Capital One DataProfiler covers essentially all classical single-column and multi-column profiling metrics defined in Abedjan et al. 2015: type inference, cardinality, null ratios, distributions/quantiles, correlations, duplicate counts, and value-frequency tables. DataProfiler uniquely adds PII entity detection. D-Tale provides interactive exploration but not pipeline-ready JSON output.

Per Claude Pro: Layer-1 deterministic profiling is exceptionally well-covered: ydata-profiling, DataPrep, Capital One DataProfiler, whylogs, and TFDV between them handle types, distributions, quantiles, cardinality, correlations, skewness, entropy, null patterns, and value-frequency tables.

Per ChatGPT: Basic capabilities such as single-column statistics (null count, distribution, unique, etc.) and basic outliers are well-covered by profiling-style tools (ydata, DataProfiler) and DQ frameworks (GE, Deequ, Soda). Many libraries also provide outlier detection (IsolationForest, LOF, COPOD via PyOD/alibi) and distribution tests (KS, Wasserstein). For example, TFDV/Evidently support KS/Chi2/Wasserstein (drift), whylogs computes diverse histograms.

**Layer-2 (DQ Detection) — Partially covered by multiple disjoint tools:**

Per Perplexity Pro:
- **Missing-value patterns (MCAR/MAR/MNAR)**: No existing OSS tool systematically classifies missingness mechanisms. ydata-profiling reports null counts; deepchecks flags high null rates; TFDV detects schema violations. Automated MCAR/MAR/MNAR heuristics (e.g., Little's MCAR test, logistic regression-based MAR test) are available in research libraries but not integrated into DQ frameworks.
- **Outlier/anomaly detection**: PyOD is the definitive library (45 algorithms, ECOD, COPOD, IsolationForest, LOF). alibi-detect covers drift-based and deep-learning-based outlier detection.
- **Near-duplicate detection**: datasketch for MinHash/LSH; no DQ framework integrates near-duplicate detection natively.
- **Distribution/drift testing**: Evidently AI and NannyML cover KS, Wasserstein, PSI, JS divergence. alibi-detect adds MMD and LSDD.
- **Cross-column inconsistency, leakage signals, target imbalance**: deepchecks checks feature-label leakage and train/test distribution; IBM DQ Toolkit adds class overlap and label purity. No single OSS tool covers all of these with a unified finding schema.

Per Claude Pro: Layer-2 detection is covered by composition rather than by a single library: PyOD/scikit-learn (IForest, LOF, OCSVM, ECOD, COPOD, autoencoder), alibi-detect (KS, MMD, ChiSq, classifier drift), NannyML (PCA-reconstruction multivariate drift; CBPE/DLE post-deployment), datasketch (MinHash/LSH/HNSW), and TFDV/Deequ (schema/skew). MCAR/MAR/MNAR diagnostics, latent leakage detection and cross-column inconsistency are *not* first-class in any one library; this is real white space.

Per ChatGPT: Advanced issues such as **latent contamination (leakage)** or **deep cross-column checks** are less targeted: GE has constraint cross-column (inclusion dependency), but other tools do not automatically find logical inconsistencies between columns (e.g., correspondence "address contained in name"). Similarly, evaluation of "ML-readiness" (the impact level of DQ issues on training) is a complex problem without a unified solution.

**Summary**: Individual algorithms are well-available, but no existing open-source tool assembles all Layer-2 algorithms into a single deterministic engine with a unified finding output format.

### 4.2. Layer-3 Ontology Gap & Baseline Comparison

Per Consensus: While some tools export findings as JSON/YAML schemas (ydata-profiling, GE, Deequ), there is no widely adopted standard ontology that encodes severity grounded in DAMA-DMBOK / ISO standards or supports all required dimensions/contextual metadata needed by safe downstream LLM consumption.

Per Perplexity: Output-schema conventions:
- Great Expectations gives rich JSON-serializable validation results
- Frictionless gives compact validation reports
- dbt gives test artifacts
- Deequ yields constraint and metric outputs
- OpenLineage facets are lineage-oriented rather than DQ-first
- Soda emits scan results

As a baseline, Great Expectations' JSON result structure is the best starting point for extension because it already separates check-level evidence, aggregate status, and metadata.

Per Perplexity Pro, comprehensive baseline schema comparison:

| Schema | Source | Structured? | Severity field? | Statistical basis? | LLM-consumable? | Assessment |
|--------|--------|-------------|-----------------|---------------------|------------------|------------|
| ydata-profiling JSON profile | `profile.to_json()` | Yes — per-column statistics dict | No | Yes — distributions, correlations, etc. | Moderate — verbose but parseable | Good Layer-1 baseline; too verbose for LLM consumption without filtering; no issue_type taxonomy |
| GE ExpectationValidationResult JSON | `to_json_dict()` | Yes — {success, expectation_config, result, meta, statistics} | Pass/fail only | Partial — observed vs expected values | Good — clean schema, LLM can parse; but findings are only what was explicitly tested | Strongest existing schema for finding structure; lacks auto-discovered severity binding |
| whylogs profile (JSON summary) | `dataset_profile.json` | Yes — column-level statistical summaries | No | Yes — counters, histograms, cardinality, frequent items | Moderate — statistics but no issue taxonomy | Best for streaming/scale use; not a finding schema, just statistics summary |
| Deequ constraint output | Spark DataFrame / JSON conversion | Partial — flat DataFrame rows | Pass/fail | Metric value + threshold | Moderate — needs conversion from Spark DF | Strong for Spark scale; Scala makes Python integration awkward; flat structure |
| OpenLineage DQ facets | JSON facets attached to dataset runs | Yes — atomic facets per entity | No | Partial | Good — versioned JSONPointer URIs | Designed for lineage not profiling; DQ is thin; needs extension for finding ontology |
| SodaCL result YAML | Scan result YAML | Yes — per-check pass/fail + metric value | Per-threshold only | Metric value included | Good — YAML is LLM-readable | Clean but rule-declaration dependent; no auto-discovery |
| Frictionless validation report | Python dict / JSON | Yes — per-row/field errors | Error severity (error/warning) | Field name + expected type | Good — clean JSON schema | Schema-declaration focused; not statistical; type/format only |

**Recommendation (Perplexity Pro)**: The GE ExpectationValidationResult JSON provides the cleanest existing per-finding schema, but it requires user-defined Expectations rather than auto-discovered issues. The proposed Layer-3 ontology should extend the GE-style schema with: (a) an `issue_type` enum (drawn from DAMA-DMBOK 6 dimensions), (b) an auto-discovery provenance field (`detected_by`: algorithm name), (c) a severity field grounded in the statistical basis, and (d) an `ml_impact` array. The OpenLineage DQ facet pattern provides a useful versioned-URI model for `_schemaURL` fields.

Per Claude Pro, among surveyed Layer-3 outputs:
- **ydata-profiling JSON** — richest column-level profile; alerts are flat strings without severity.
- **Great Expectations `ExpectationSuiteValidationResult`** — strongly typed result objects but oriented to user-declared expectations, not auto-discovered findings.
- **whylogs `DatasetProfile`** — mergeable, sketch-based, language-agnostic; excellent for distributed/incremental but lean on issue semantics.
- **Deequ `VerificationResult`** — clean separation of metrics and constraint statuses; closest to a DQ-finding object but JVM-first.
- **TFDV `Anomalies` protobuf** — typed reasons and short/long descriptions, schema-grounded; the strongest *issue-typed* schema we found.
- **SodaCL scan result (YAML)** — declarative checks with pass/fail, light on statistical context.
- **Frictionless validation report** — table-shape and constraint focused; weak on statistical findings.
- **OpenLineage DQ facets** — interchange-only, not a finding ontology in their own right.

**Recommendation (Claude Pro)**: The strongest single baseline to extend is the **TFDV `Anomalies` schema** (typed reason enums + severity-like short descriptions + per-feature scope), grafted onto **whylogs `DatasetProfile`** as the statistical substrate (mergeable, language-agnostic). DAMA-DMBOK 6 dimensions / ISO 25012 should be added as orthogonal tags on each finding.

Per ChatGPT: Output schemas:
- *ydata-profiling* exports JSON profiling (e.g., `profile.dict()`) with many information fields
- *whylogs* has storage profile schema (protobuf JSON)
- *Great Expectations* creates validation JSON/YAML folder (including success/failure of each Expectation)
- *Deequ* exports constraint test results (JSON)
- *Soda* (v3) exports check results as YAML logs
- *Frictionless* creates standard validation report (JSON) with detailed errors

These models all provide some structured output, but each tool uses its own format (incompatible JSON schemas). There is no common standard yet. Among the above formats, *whylogs* or *Frictionless* reports have high uniformity (according to specs) and represent errors fully, so they could be good baselines to extend. *Great Expectations* JSON specifies detailed tests very strongly but is less standardized (relying heavily on Expectation strings). Overall, schemas based on global statistics and cross-column incidents (based on ydata/whylogs source) could be a baseline framework to forward to LLM, as they are the most open.

### 4.3. Layer-4 Gap — LLM as Interpreter

Per Consensus: No open-source or commercial solution was found that strictly implements the "LLM-as-reporter-on-deterministic-findings" pattern — i.e., where the LLM consumes only structured findings without access to raw data/statistics/code-generation capabilities.

Per Perplexity Pro:
**Where this pattern exists (partially):**
- Acceldata Galileo and Telmai implement commercial versions where an LLM interprets structured DQ findings and generates NL summaries. However, both allow the LLM to also generate SQL and rules autonomously (mixed-mode, not pure interpreter).
- PyOD 2's LLM-guided model selection is a narrow instance of the pattern: LLM reads algorithm metadata + task description → selects a model. No raw data is exposed.
- The XAI narrative literature (LLMs explaining SHAP values, counterfactuals) demonstrates the technical feasibility of LLM interpretation of structured ML outputs, but is not applied to tabular DQ specifically.

**Where it is absent:**
- No open-source tool implements a full "DQ engine → Layer-3 findings → LLM narrative report" pipeline.
- The LangKit/whylogs stack monitors LLMs, it does not use LLMs to narrate tabular DQ findings.
- Evidently's JSON output is structurally compatible with Layer-3 consumption, but no built-in LLM layer exists.

**Key risk confirmed by literature**: Even with structured input, LLMs exhibit hallucination on numerical reasoning. The faithfulness review confirms that RAG-style strict grounding (providing only the Layer-3 JSON as context) combined with structured output formats significantly reduces but does not eliminate hallucination. Evaluation using faithfulness metrics (FactScore, NLI-based entailment) against Layer-3 findings should be part of the project's Layer-4 evaluation strategy.

Per Claude Pro: In OSS, putting an LLM strictly *over* deterministic findings is essentially unimplemented as a maintained, schema-grounded library: LIDA's `SUMMARIZER` does the closest thing (compact NL summary from deterministic metadata) but feeds visualization, not DQ narrative; Evidently's LLM-as-judge evaluates LLM outputs, not tabular DQ; whylogs+LangKit goes in the inverse direction (metrics from LLM text). In commercial tooling the pattern is rapidly emerging: **Anomalo AIDA** (Oct 2025) is the most explicit deterministic-findings → LLM-reasoning architecture; **Monte Carlo AI Agents** is the most mature; **Informatica Agentic CLAIRE GPT** and **Acceldata** agents follow. None publish their finding ontology or prompt scaffolding.

Per ChatGPT: There is hardly any tool that purely implements "LLM interprets structured DQ findings". Many LLM data agent systems (PandasAI, Vanna) allow the LLM to compute/query (not limited to predefined results). Some BI services (Julius, Tableau Pulse) use LLM to create reports, but based on dashboard/SQL results. As for the style of "using only JSON findings" and then LLM synthesizing, there is no clear public example yet. This is a major gap: currently only internal solutions or experimental prototypes solve the grounding and hallucination avoidance problem, but they haven't become products.

### 4.4. Combined-Pipeline Coverage

Per Consensus: No single system natively covers the full pipeline from raw-data → deterministic/statistical profiling → standards-grounded finding ontology → safe LLM narrative/report generation as described in the project architecture.

Per ChatGPT: No single tool comprehensively covers all 4 layers. For example: *Great Expectations + Soda* can handle L1-2-3 (tool to define checks and export results) but has no LLM. *ydata-profiling* handles L1 (profiling) well but lacks automatic complex L2 or L4. *Evidently* covers L1-2-3 (has drift, JSON logs, UI) but no LLM. Overall, current tools combine only some layers: usually (L1+L2) or (L2+L3) or (L2+L4) separately, but not all 4.

Per Perplexity Pro coverage matrix:

| Tool | Layer 1 | Layer 2 | Layer 3 | Layer 4 |
|------|---------|---------|---------|---------|
| ydata-profiling | ✅ Full | ✗ | Partial (JSON stats) | ✗ |
| Great Expectations | Partial (profiler) | Partial (expectations) | ✅ (per-finding JSON) | ✗ |
| Evidently AI | ✅ (Data Quality preset) | ✅ (drift, missing, outlier stats) | ✅ (JSON report) | ✗ (no LLM layer) |
| deepchecks | Partial | ✅ (ML-context checks) | Partial (CheckResult) | ✗ |
| PyOD | ✗ | ✅ (outlier detection) | ✗ | ✗ |
| Acceldata (commercial) | ✅ | ✅ | ✅ | ✅ (partially — mixed-mode LLM) |
| Monte Carlo (commercial) | ✅ | ✅ | ✅ | Partial (RCA summaries) |
| **Project (proposed)** | ✅ | ✅ | ✅ (novel ontology) | ✅ (strict-interpreter-only) |

No single open-source tool covers all four layers. Evidently AI is closest for Layers 1–3; the project's unique value is the complete pipeline with a strict, grounded Layer-4.

Per Claude Pro: No single OSS tool covers L1 + L2 + L3 + L4. The closest stacks are:
- (a) **whylogs (L1) + Evidently (L2) + custom JSON (L3) + custom LLM wrapper (L4)**, or
- (b) **TFDV (L1+L2+L3) + custom LLM (L4)**.

Commercially, **Anomalo + AIDA** is the only end-to-end implementation that mirrors the project's exact layering, but is closed-source.

Per Perplexity: The biggest gaps are: one pipeline that accepts DBML plus live DB introspection plus files; simultaneous schema-vs-data mismatch and uncontracted anomaly detection; a deliberately versionable findings schema; and an LLM that advises on both data fixes and contract changes without doing the statistics itself. Existing tools usually do one or two of these, but not the whole chain in one architecture.

### 4.5. DQ-Dimensions Grounding

Per Consensus: Most frameworks/tools cover core dimensions like completeness/conformity/uniformity but often neglect semantics/contextual meaning or emerging needs such as knowledge graph compatibility or regulatory mapping (Miller et al., 2025; Widad et al., 2023).

Per Perplexity Pro: Most tools grade severity against ad-hoc thresholds (e.g., null rate > 0.2 = warning), not against recognised frameworks. The IBM DQ Toolkit is the only reviewed tool that explicitly grounds findings in ML-specific quality dimensions. The BIR 2025 review confirms: across 151 tools reviewed, only 10 support AI-augmented DQM, and explicit DAMA-DMBOK or ISO 25012 grounding in severity scores is rare. The project's explicit commitment to standard-grounded severity (DAMA-DMBOK 6 dimensions, ISO/IEC 25012 fitness-for-purpose) as the severity calibration layer is a differentiator.

Per Claude Pro: Almost no surveyed tool grounds severity in DAMA-DMBOK or ISO 25012; thresholds are ad-hoc and per-check. Soda Cloud and Collibra DQ expose dimension *labels* on rules but do not derive severity from them. Treating ISO/IEC 25012 dimensions as first-class fields on every finding would be a clear differentiator.

Per ChatGPT: Very few tools use standard scales (DAMA-DMBOK, ISO 25012) to assign severity or DQ nature. Most use arbitrary thresholds (e.g., missing > 50% then `HIGH`). Soda has the concept of severity labels (critical, warning) but no specific link to standards. GE has the notion of "passing/failing rates" but is also free-form. Most frameworks do not mention international DQ standards; unless users themselves write rule mappings to standards (e.g., GE expectation can represent "Completeness=0.99"). If grounding is needed, one can refer to standard sets like DAMA-DMBOK or ISO, but no library has integrated them into a Severity Metric yet.

### 4.6. Strongest Differentiator

Per Consensus: The proposed "deterministic-engine + standards-grounded finding ontology + hallucination-mitigated LLM narrative" pattern remains novel compared to surveyed tools/frameworks.

Per Perplexity: The strongest differentiator is a contract-native, machine-readable DQ artifact that unifies schema mismatch, statistical profiling, and anomaly detection in a single findings file, then passes only those findings to an advisory LLM. That is different from narrative BI assistants and different from pure validation frameworks because the system stays ML-first and report-light.

Per Perplexity Pro: The combination of three properties is not found in any existing OSS tool:
1. **Auto-discovery + auto-severity in Layer 2** — detecting DQ issues without requiring user-declared rules or Expectations
2. **Structured finding ontology in Layer 3** — a typed, severity-graded, ML-impact-annotated JSON schema that can serve as an LLM trust anchor
3. **LLM-as-interpreter-only in Layer 4** — the LLM narrates Layer-3 findings but cannot compute statistics, generate code, or access raw data

This combination allows the report to be reproducible (same Layer-3 input → stable narrative) and auditable (every LLM claim cites a Layer-3 finding). No commercial tool fully achieves this; Acceldata Galileo comes closest but retains LLM code-generation autonomy.

Per Claude Pro: Combine three rare elements:
1. A *single*, versioned, machine-readable **Structured Finding Schema** that fuses TFDV-style typed reasons, Deequ-style metric/constraint separation, and DAMA/ISO 25012 dimension tagging;
2. **Deterministic ML-readiness verdict** computed by Layer 2 (IBM Data Quality Toolkit-style noisy-label / class-overlap / leakage signals);
3. A Layer-4 LLM whose prompt contract *forbids numerical synthesis* — the LLM may only quote, prioritise and interpret values present in Layer-3 findings.

None of the surveyed tools combine all three with reproducibility guarantees.

Per ChatGPT: The project can emphasize **deep DQ detection, especially semantic anomalies and cross-column interactions** (e.g., sudden data type changes, hidden leakage violations, complex dependencies) which receive little attention in standard profiling. Building a finding-structure ontology (Layer-3) rigorously — for example, each issue tagged with one or more Dimensions (Bias, Completeness, Consistency, etc.) and ML impact (preset). In addition, highlight pipeline stability (deterministic): every number, every chart comes from a deterministic engine, LLM only interprets — avoiding direct querying functionality.

### 4.7. Unsolved Technical Risks

Per Consensus: Key risks include hallucination by LLM reporters if not strictly grounded (Akella et al., 2025; Tang et al., 2023), lack of severity calibration tied to business impact/regulatory standards (Widad et al., 2023; Schwabe et al., 2024), scalability challenges at big-data scale (Elouataoui, 2024; Taleb et al., 2021), limited support for semi/unstructured sources (Taleb et al., 2021), reproducibility/version control gaps in current pipelines (Ehrlinger et al., 2019).

Per Perplexity: The unresolved risks are LLM hallucination in remediation advice, false positives in drift/anomaly flags, performance on wide or high-cardinality tables, schema drift in semi-structured columns, safe execution of generated remediation code, and contract/data co-evolution over time. These risks are visible across the current ecosystem, but no single tool appears to solve them end-to-end.

Per Perplexity Pro:

1. **LLM hallucination on numerical findings even with structured input**: Faithfulness literature confirms LLMs still fabricate numbers when summarising tables. Mitigation: strict templated prompts with exact value injection, output validation against Layer-3 schema, and faithfulness-score gating before report delivery.

2. **Severity calibration when multiple issues compound**: No tool handles compound severity (e.g., high missingness + high cardinality + distribution drift in the same column together indicate higher risk than each alone). Current tools score findings independently. The project's Layer-3 ontology should include a `compound_severity` field and logic for escalation.

3. **Scale of profiling on wide tables (>1,000 columns)**: ydata-profiling becomes slow beyond ~200 columns; Deequ on Spark handles this better but requires Spark infrastructure. DataPrep's Dask backend is the best OSS solution at scale for Python-native users.

4. **Semi-structured columns (JSON-in-text, free-text fields)**: No reviewed tool handles embedded JSON in text columns as part of a profiling pipeline. Capital One DataProfiler handles multiple file formats but not intra-column JSON. This remains an unsolved problem in the OSS landscape.

5. **Mapping a finding to a Data/AI-readiness verdict**: The IBM DQ Toolkit makes the closest attempt, but its metrics are limited. The project needs an explicit "trainability verdict" layer (can this dataset train an unbiased ML model?) that no current tool provides end-to-end.

6. **Reproducibility of the LLM narrative across runs**: LLMs with non-zero temperature produce different narratives on identical Layer-3 inputs. Mitigation: temperature=0 for report generation, deterministic seed where available, and hash of Layer-3 findings stored alongside report for audit.

Per Claude Pro: Even with structured Layer-3 input, LLMs hallucinate on numerical reasoning under multi-issue compounding (well-documented in the hallucination survey, arXiv:2311.05232); commercial agents (Monte Carlo, Anomalo) do not publish hallucination rates on numerical narrative. **Severity calibration when issues compound** (e.g. high missingness + drift + label leakage) is unaddressed — every tool surveyed scores findings independently. **Wide-table profiling (>1000 columns)** stresses ydata-profiling and DataPrep; whylogs and TFDV scale better via sketches and Beam. **Semi-structured columns** (JSON-in-text, free text) are largely ignored outside Capital One DataProfiler and whylogs. **Mapping a finding to a concrete Data/AI-readiness verdict** is only attempted by IBM DQ Toolkit. **Reproducibility of the LLM narrative across runs** is a known weakness of all LLM-narrative commercial features; no vendor advertises deterministic narrative seeds or content-addressed prompt logs.

Per ChatGPT:
- **LLM hallucinates even with JSON input**: Even if the source is deterministic data, LLMs can still "add or remove" numbers. Need to design "Strict-lock" prompts to force LLM to only use given data. However, this risk is not fully resolved; some research (Chain-of-Thought control, Retrieval Augmented) can be applied.
- **General severity evaluation**: When multiple DQ issues are intertwined (large missing in column A, distribution skew in B, leakage in C), how to evaluate the total "bias risk" or priority order? Currently tools have no unified metric (each issue only gets individual severity). The project needs aggregation mechanisms, avoiding generalities.
- **Large scale and data width**: Many profiling/querying tools are slow with tables of >1000 columns or millions of rows. Solutions need streaming computation or intelligent sampling, using external memory (dask, Spark). This is a technical challenge that no framework handles perfectly.
- **Unstructured columns**: Data in JSON-in-text form, or free text (like reviews). Standard tools only compute length/unique for text; deep semantic analysis (summarization, topic-finding) is rare. To detect semantic outliers or patterns in text needs NLP integration (could be extended Layer-2).
- **ML readiness assessment (Data/AI readiness)**: Tools struggle to concretize "is the data clean/suitable enough for training" by some standard. Need to establish rules (e.g., many nulls => need impute; leakage features => high risk) based on Data-Centric AI research. Currently no default standard exists, so let LLM offer recommendations with limitations.
- **LLM result reproducibility**: LLM reports are hard to control with identical output every time, especially using GPT-like. Using smaller models or strict seed/configuration attachment can help, but still need strategies to ensure reproducibility (e.g., use GPT-4.0 mini with preserved prompts). This is a production challenge.

---

## 5. Suggested Reading Order

Different sources prioritize different papers as starting points. The merged recommendation is presented per-source, then synthesized.

### 5.1. Consensus Recommendation

1. **"A Data-centric AI Framework for Automating Exploratory Data Analysis and Data Quality Tasks"** (Patel et al., 2023) — Comprehensive survey plus practical algorithms bridging EDA/DQ gaps.
2. **"Quality Assessment of Tabular Data using Large Language Models and Code Generation"** (Akella et al., 2025) — State-of-the-art hybrid deterministic+LLM approach directly relevant to project novelty.
3. **"ydata-profiling: Accelerating data-centric AI with high-quality data"** (Clemente et al., 2023) — Leading open-source profiler covering most required metrics/schema outputs.
4. **"A Comparison of Data Quality Frameworks: A Review"** (Miller et al., 2025) — Regulatory mapping/gap analysis across DAMA-DMBOK / ISO / industry frameworks.
5. **"Dead or Alive: Continuous Data Profiling for Interactive Data Science"** (Epperson et al., 2023) — Modern take on live/deterministic profiling workflows supporting robust insight discovery.

### 5.2. Perplexity Recommendation

1. **Profiling relational data: a survey** — best foundation for profiling tasks, metrics, and classic relational DQ methods.
2. **Frictionless validating-data docs** — clearest lightweight contract-driven validation model for tabular data.
3. **Great Expectations ExpectationSuite + validationresult docs** — strongest structured-output precedent for a findings file.
4. **IBM data contracts docs** — practical example of declarative contracts executed as DQ tests and stored in Git.
5. **Quality Assessment of Tabular Data using LLMs** — nearest precedent for a modern "statistical engine + LLM rule/help layer" pipeline, useful mainly as a contrast point.

### 5.3. Perplexity Pro Recommendation

1. **Abedjan, Golab, Naumann (2015) — "Profiling Relational Data: A Survey"** (VLDB Journal, DOI 10.1007/s00778-015-0389-y): Read first. This paper defines the complete taxonomy of profiling tasks that Layer 1 must implement. Every statistic computed in the project maps to a concept defined here. Without this foundation, Layer-1 design will reinvent imprecisely.

2. **Zhou et al. (2024) — "A Survey on Data Quality Dimensions and Tools for Machine Learning"** (arXiv:2406.19614): Read second. This is the most direct survey of what DQ tools currently cover and where the ML-contextual gap lies. The four-dimension taxonomy and the coverage analysis of 17 tools directly informs which Layer-2 checks to prioritize and what Layer-3 severity fields mean.

3. **Dong, Sahri, Palpanas (2024) — "Data Quality Awareness: A Journey from Traditional Data Management to Data Science Systems"** (arXiv:2411.03007): Read third. Bridges classical DQ (where DAMA dimensions and ISO standards originate) to modern ML DQ challenges. Provides the intellectual lineage needed to ground Layer-3 severity in recognised standards rather than ad-hoc thresholds.

4. **Gupta et al. (2021) — "Data Quality Toolkit: Automatic Assessment of Data Quality and Remediation for Machine Learning Datasets"** (arXiv:2108.05935): Read fourth. The most direct paper-level prior art for Layers 2 + 3. Introduces ML-specific DQ metrics (class overlap, feature redundancy, label noise) not covered by classical profiling surveys, and provides an API-accessible result structure to learn from and extend.

5. **Han et al. (2022) — "ADBench: Anomaly Detection Benchmark"** (NeurIPS 2022, arXiv:2206.09426): Read fifth. The benchmark that empirically validates algorithm choices for Layer 2's outlier detection engine. Required reading before committing to a specific algorithm configuration (IsolationForest vs. ECOD vs. LOF vs. COPOD) for different data regimes.

### 5.4. Claude Pro Recommendation

1. **Abedjan, Golab, Naumann — Profiling Relational Data: A Survey (VLDB Journal 2015)** — foundational vocabulary you will use in every layer.
2. **Schelter et al. — Automating Large-Scale Data Quality Verification / Deequ (PVLDB 2018)** — the cleanest published architecture for constraint + metric + structured result that maps onto Layer 2 and Layer 3.
3. **Caveness et al. — TFDV: Data Analysis and Validation in Continuous ML Pipelines (SIGMOD 2020)** plus Breck et al. *Data Validation for ML* (SysML 2019) — the strongest reference for a typed Anomalies schema, which is the Layer-3 baseline to extend.
4. **Zhou et al. — A Survey on Data Quality Dimensions and Tools for ML (arXiv 2406.19614, 2024)** — anchors your DAMA/ISO 25012 dimensions story and surveys 17 tools you'll need to reference.
5. **Gupta et al. — IBM Data Quality Toolkit (arXiv 2108.05935, 2021)** — direct prior art for ML-readiness assessment, which is the Layer-2 novelty closest to your differentiator.

LLM-narrative / hallucination references (Huang 2311.05232; Zhao 2305.14987; Dibia LIDA 2303.02927) come *after* you have solidified Layers 1–3.

### 5.5. ChatGPT Recommendation

1. **Abedjan et al. (2015)** — Foundation of *data profiling*. Read first to understand the classification of profiling tasks (and algorithms) in relational data.
2. **Ehrlinger & Wöß (2022)** — Comprehensive DQ tools survey. Helps recognize capabilities and limits of current open-source and commercial DQ platforms; orients Layer 2.
3. **Clemente et al. (2023)** — Introduces the new *ydata-profiling* tool. Example of a full-featured EDA/L1 library (statistics, missing, duplicates, etc.), while also illustrating how to export results.
4. **Li et al. (2020) – COPOD** — Outlier detection algorithm. Use COPOD example to understand how to identify outliers using copula, one of many Layer-2 techniques to consider.
5. **Zhao et al. (2019) – PyOD** — Comprehensive outlier library. Indicates the range of available outlier methods and the report structure of a major Layer-2 DQ tool.

Other readings (Tang/Zhou 2025 on LLM, Mladenovic 2026 on AutoDS, Müller 2024 on drift) can be read later, if extended context is needed, but priority is given to the above documents to build the profiling and DQ foundation.

### 5.6. Cross-Source Convergent Picks

Papers most consistently recommended across the 5 sources as "read first":
- **Abedjan et al. (2015) — Profiling Relational Data: A Survey** (recommended by 4/5 sources: Perplexity Pro, Claude Pro, ChatGPT, Perplexity)
- **Zhou et al. (2024) — Survey on DQ Dimensions and Tools for ML** (recommended by 2/5: Perplexity Pro, Claude Pro)
- **Gupta et al. (2021) — IBM Data Quality Toolkit** (recommended by 2/5: Perplexity Pro, Claude Pro)
- **Clemente et al. (2023) — ydata-profiling** (recommended by 2/5: Consensus, ChatGPT)

---

## Appendix A: Source Conflicts

This appendix consolidates points where sources disagree, with quotes from each side to preserve provenance.

### A.1. Star counts for major repositories

Star counts vary significantly across sources (different observation dates):

- **ydata-profiling**: ~13k (Consensus, 07/24) vs. 13.5k (Claude Pro, release v4.18.1 page 2026) vs. ~13.6k (ChatGPT 2026-05) vs. ~13,000 (Perplexity Pro May 2026)
- **Great Expectations**: ~9k (Consensus) vs. ~11,400 (Perplexity Pro May 2026) vs. ~11.5k (ChatGPT 2026-05) vs. ~10.4k (Claude Pro) vs. ~11k-ish Sep 2025 (Perplexity)
- **PyOD**: ~7k (Consensus) vs. ~8,500+ (Perplexity Pro) vs. ~9.9k (ChatGPT 2026-05) vs. ~9k (Claude Pro)
- **PandasAI**: ~8k (Consensus) vs. ~3.0k (ChatGPT) vs. ~15k (Claude Pro) vs. ~21,000 (Perplexity Pro)
- **river**: ~4k (Consensus) vs. ~1,600 (Perplexity Pro, may be conflated with NannyML) vs. ~5,200 (Perplexity Pro elsewhere) vs. ~5.8k (ChatGPT) vs. 5.6k (Claude Pro, latest release v0.24.2, April 15 2026)
- **klib**: ~1,000 (Perplexity Pro) vs. ~1.5k (Claude Pro) vs. ~522 (ChatGPT 2026-05)
- **Evidently AI**: ~7k (Consensus) vs. ~6,500 (Perplexity Pro) vs. ~7.5k (ChatGPT) vs. ~5.9k (Claude Pro)
- **Sweetviz**: ~4k (Consensus) vs. ~3,000 (Perplexity Pro) vs. ~3.1k (ChatGPT) — and Claude Pro notes "Last release v2.3.1, November 2023 (per PyPI) — effectively stale"

> ⚠️ **Note**: Variability in star counts reflects different observation dates across sources. The Consensus 07/24 figures are earliest; May 2026 figures from Perplexity Pro and ChatGPT are most recent.

### A.2. LLM-narrative capability of commercial vendors

⚠️ **Monte Carlo — LLM narrative?**
- Consensus: "No"
- ChatGPT: "No (chỉ dashboards/alerts thông thường)" = "No (only dashboards/alerts)"
- Perplexity Pro: "Yes — incident summaries with NL explanations; closest to Layer-3 + Layer-4" with 2025 "Graph-AI RCA" module
- Claude Pro: "Yes" — Incident IQ + AI Agents

⚠️ **Soda — LLM narrative?**
- Consensus: "No"
- ChatGPT: "No (dựa trên rule, dashboards)" = "No (rule-based, dashboards)"
- Perplexity Pro: "AI-assisted check generation (not post-hoc narrative)"
- Claude Pro: "No (not prominent)" — Low overlap

⚠️ **Anomalo — LLM narrative?**
- Consensus: "No"
- ChatGPT: "Có (sử dụng ML để giảm cảnh báo sai) nhưng không phải LLM" = "Yes (uses ML to reduce false alarms) but not LLM"
- Perplexity Pro: "Partial — AI-generated anomaly context summaries [uncertain detail]"
- Claude Pro: "Yes" — with AIDA launch October 29, 2025

⚠️ **Bigeye — LLM narrative?**
- Consensus: "No"
- ChatGPT: "No"
- Perplexity Pro: "Limited — AI assists in check generation; limited narrative reporting"
- Claude Pro: "Partial (unverified whether LLM vs templated)"

⚠️ **Acceldata — LLM narrative?**
- Consensus: not explicit
- ChatGPT: "No"
- Perplexity Pro: "Yes — NL descriptions, DQ summaries, anomaly explanations, Text-to-Rules; includes guardrails and hallucination QA"
- Claude Pro: "Yes (agent-based)"

⚠️ **Telmai — LLM narrative?**
- ChatGPT: "Tự xưng dùng AI, có vẻ ML (chưa rõ có LLM hay không)" = "Self-claims AI, seems ML (unclear if LLM)"
- Perplexity Pro: "Yes — NL explanations of anomalies and DQ incidents; MCP interface for agents to query validated data context"
- Claude Pro: "Yes"

⚠️ **Collibra — LLM narrative?**
- ChatGPT: "No"
- Perplexity Pro: "Partial — some NL summaries in 2025 Collibra Intelligence Studio integration [uncertain]"
- Claude Pro: "Not documented" — Low/medium overlap

> 💡 **Likely explanation for conflicts**: Different observation dates. Anomalo AIDA launched October 29, 2025; many LLM features in commercial DQ tools emerged in 2024–2025. Sources observing earlier (Consensus) may legitimately report "No" while Claude Pro (most recent observations) reports "Yes" for the same vendor.

### A.3. PandasAI repository URL

Multiple sources give different GitHub paths:
- Consensus: https://github.com/gventuri/pandas-ai
- ChatGPT: https://github.com/sinaptik-ai/pandas-ai
- Claude Pro: https://github.com/Sinaptik-AI/pandas-ai
- Perplexity Pro: (no explicit URL but stars ~21,000)

> 💡 The repo was originally at `gventuri/pandas-ai` and later moved to the Sinaptik AI organization, explaining the URL variance.

### A.4. Mladenovic Survey — arXiv ID

- ChatGPT cites: arXiv:2602.12345
- Perplexity Pro cites: OpenReview link (no arXiv ID): https://openreview.net/forum?id=Euti6LHIOs

> ⚠️ The arXiv ID 2602.12345 is anomalous (arXiv 2602.xxxxx is in the future format; 2025–2026 papers should be 2501.xxxxx or 2502.xxxxx etc.). This is likely a transcription error in the ChatGPT report. The Perplexity Pro OpenReview reference appears more reliable.

### A.5. Acceldata Tool Naming

- Consensus: "Accurics/Splunk Observability" (likely confused with the separate Accurics/Splunk product line)
- ChatGPT: "Acceldata (Platform)"
- Perplexity Pro: "Acceldata Torch + Galileo"
- Claude Pro: "Acceldata Data Observability Cloud"

> 💡 Acceldata's product line includes both Torch and Galileo as components; Consensus appears to confuse this with the unrelated Accurics security tooling acquired by Splunk.

### A.6. Coverage Assessment of Specific Tools

⚠️ **Bigeye PSI/Wasserstein methodology**:
- ChatGPT writes: "DQ tự động, đo lường PSIX để phát hiện drift/corruption" = "Auto DQ, measuring PSI(X) to detect drift/corruption"
- Other sources do not detail Bigeye's specific drift methodology.

⚠️ **Whether deterministic-engine + LLM-narrative pattern exists**:
- All sources agree on a NEGATIVE result for OSS implementations.
- Sources disagree on closest commercial implementation:
  - Perplexity Pro/Claude Pro: Acceldata Galileo
  - Claude Pro: Anomalo AIDA (Oct 29, 2025) — "most explicit"
  - Claude Pro: Monte Carlo AI Agents — "most mature"

---

## Appendix B: Unique Information by Source

Information that appears in only one source, preserved here for completeness and traceability.

### B.1. Unique to Consensus

- **Reference to METRIC-framework** (Schwabe et al., 2024): "The METRIC-framework for assessing data quality for trustworthy AI in medicine: a systematic review." *NPJ Digital Medicine*, 7. DOI: 10.1038/s41746-024-01196-4 — Used in severity calibration discussion.
- **Tang et al. (2023) reference**: "Evaluating large language models on medical evidence summarization" — Used in LLM hallucination risk discussion.
- **Patel et al. (2023) explicit ACM DOI**: 10.1145/3603709 — provides the most explicit publication metadata for the IBM "Data-centric AI Framework" paper.

### B.2. Unique to ChatGPT (translated from Vietnamese)

- **COPOD paper details** (Li et al. 2020 ICDM, arXiv:2009.09463) with specific evaluation note: "evaluated on 30 datasets."
- **Ehrlinger & Wöß (2022)** primary survey reference with feature comparison table noted, [uncertain] tag due to access issues.
- **LLM × DATA Survey (Zhou 2025, arXiv:2505.18458)** — bidirectional Data↔LLM perspective covering filter/browse/security for LLM training data ingestion.
- **Open-Source Drift Detection Tools (Müller 2024, arXiv:2404.18673)** — D3Bench benchmark comparing Evidently, NannyML, Alibi-Detect on two real scenarios with both functional and non-functional criteria; specific finding that "Evidently excels at general drift detection, NannyML at change-point timing, Alibi at spurious cases."
- **What About the Data? (Heck 2024)** — A mapping study reviewing 25 papers (2019–2023) on data engineering for AI.
- **Detail on PyOD's "od-expert" module** for LLM integration.
- **Specific note on Julius AI** as the BI vendor cited to illustrate LLM narrative capabilities (with a note: "LLM data agents like PandasAI or other BIs are not listed; only Julius is cited to illustrate LLM narrative").

### B.3. Unique to Perplexity

- **Focus on DBML as DQ contract**: "I did not find a credible public example of DBML being used specifically as a data-quality contract; the closest analogues are Frictionless Table Schema, Great Expectations suites, dbt contracts/tests, and IBM data contracts. The gap is therefore not just a missing implementation detail but an absent ecosystem pattern: DBML is schema-centric, while DQ-contract systems are usually validation-centric, so the project would be defining a new bridge between schema design and validation semantics."
- **Mention of dbt-core and dbt-adapters** as important contract-adjacent ecosystem.
- **Mention of holistics/dbml** as DBML parser/model ecosystem.
- **OpenLineage facets** detailed comparison perspective — "lineage-oriented rather than DQ-first."

### B.4. Unique to Perplexity Pro

- **Quantitative detail on BIR 2025 review**: "across 151 tools reviewed, only 10 support AI-augmented DQM."
- **Detailed Layer-3 baseline comparison table** (8 different schemas compared on Structured/Severity/Statistical-basis/LLM-consumable axes).
- **Mention of ADEngine specifically** (PyOD 2's LLM-guided model selection) as "a narrow instance of the pattern: LLM reads algorithm metadata + task description → selects a model."
- **Compound severity discussion**: "No tool handles compound severity (e.g., high missingness + high cardinality + distribution drift in the same column together indicate higher risk than each alone)."
- **DataPrep performance note**: "DataPrep's Dask backend is the best OSS solution at scale for Python-native users."
- **MCAR/MAR/MNAR specific mention**: "Automated MCAR/MAR/MNAR heuristics (e.g., Little's MCAR test, logistic regression-based MAR test) are available in research libraries but not integrated into DQ frameworks."
- **Reference to faithfulness metrics**: "FactScore, NLI-based entailment" as evaluation approaches.

### B.5. Unique to Claude Pro

- **Explicit Anomalo AIDA launch date**: October 29, 2025, with verbatim quote from GlobeNewswire press release.
- **Verbatim Monte Carlo Bedrock quote**: *"We use Amazon Bedrock to empower our agents with the latest foundational models without the need to manage any infrastructure… Monte Carlo does not fine-tune or retrain them. We exclusively use the pre-trained versions provided."*
- **Vendr.com pricing data for Monte Carlo**: "mid-sized deployments (50–200 tables, 3–5 sources) typically $30K–$80K/yr; enterprise (300+ tables across 6+ sources) typically $120K–$250K+/yr"
- **Informatica CLAIRE GPT / Agentic CLAIRE GPT** as a specific high-overlap commercial tool — "supervisor agent orchestrating Discovery / DQ / Integration agents over Azure OpenAI / Anthropic Claude"
- **Note on IJISA 2022 paper**: "The IBM Data Quality Toolkit paper (arXiv:2108.05935) and the secondary IJISA 2022 'Data Quality for AI Tool: EDA on IBM API' (DOI 10.5815/ijisa.2022.01.04) describe the *same* IBM toolkit from different vantage points (research engineers vs. external evaluation); neither contradicts the other."
- **Sherlock and Sato papers** (semantic type detection) — only Claude Pro mentions these in the academic list.
- **Schelter et al. 2018 Deequ paper** (PVLDB) — only Claude Pro cites the original PVLDB publication, not just the awslabs/deequ repo.
- **TFDV paper (SIGMOD 2020) and Breck et al. SysML 2019** — only Claude Pro lists these as primary academic references.
- **Isolation Forest (Liu 2008 ICDM)** — only Claude Pro lists this as a foundational reference.
- **Wang et al. 2025 "Towards Data-Centric AI"** (arXiv:2501.10555) — only Claude Pro lists this.
- **Specific note on Sweetviz status**: "Last release v2.3.1, November 2023 (per PyPI) — effectively stale"
- **Specific note on river version**: "5.6k (latest release v0.24.2, April 15 2026, per GitHub)"

---

## References / Sources

This document synthesizes content from the following AI research platforms, each contributing unique perspectives and verification chains:

1. **Consensus.app** — AI-powered search engine for research. Source citation: "These search results were found and analyzed using Consensus, an AI-powered search engine for research. Try it at https://consensus.app. © 2026 Consensus NLP, Inc. Personal, non-commercial use only; redistribution requires copyright holders' consent."
   - Provided: 12 academic papers with explicit DOI verification, ~20 GitHub repos, 7+ commercial tools, structured gap analysis.

2. **ChatGPT (OpenAI)** — Research report in Vietnamese, translated for this synthesis.
   - Provided: 10 academic papers, ~16 GitHub repos (organized as Primary EDA/Profiling, Primary DQ Frameworks, Primary ML/Statistical, Primary LLM-on-deterministic [missing], Adjacent), 8 commercial tools, 7-point gap analysis with extensive risk discussion.

3. **Perplexity** — Academic Papers section focused on schema-spec ecosystems and declarative DBML contracts.
   - Provided: 12 academic/documentation references, ~16 GitHub repos organized by category (Schema-spec, DQ/validation frameworks, Classical profiling libraries, ML/statistical DQ, LLM-as-advisor, Adjacent), 12 commercial tools, gap analysis focused on DBML/contract patterns.

4. **Perplexity Pro** — Most comprehensive academic depth.
   - Provided: 14 numbered academic papers (P1–P14) plus P-Note items on standards (DAMA/ISO), ~25 GitHub repos with detailed strength/weakness analysis, 8 commercial tools, comprehensive gap analysis with quantitative coverage matrix and Layer-3 baseline comparison table.

5. **Claude Pro** — Structured Literature-and-Tool Review with strongest commercial-tool intelligence.
   - Provided: 16 academic papers with verbatim DOIs and arXiv links, comprehensive GitHub repo categorization, 8 commercial tools with verbatim quotes from vendor press releases and pricing data, detailed gap analysis with concrete schema recommendations.

### Key Bibliographic References (Verified across multiple sources)

- Abedjan, Z., Golab, L., & Naumann, F. (2015). Profiling relational data: a survey. *The VLDB Journal*, 24(4), 557–581. https://doi.org/10.1007/s00778-015-0389-y
- Akella, A., Kaul, A., Narayanam, K., & Mehta, S. (2025). Quality Assessment of Tabular Data using Large Language Models and Code Generation. arXiv:2509.10572. https://doi.org/10.48550/arxiv.2509.10572
- Bilal, A., Ebert, D., & Lin, B. (2025). LLMs for Explainable AI: A Comprehensive Survey. arXiv:2504.00125.
- Breck, E., Polyzotis, N., Roy, S., Whang, S., & Zinkevich, M. (2019). Data Validation for Machine Learning. *SysML 2019*.
- Caveness, E., et al. (2020). TensorFlow Data Validation: Data Analysis and Validation in Continuous ML Pipelines. *SIGMOD 2020*.
- Chen, S., Qian, Z., Siu, W., et al. (2024). PyOD 2: A Python Library for Outlier Detection with LLM-powered Model Selection. arXiv:2412.12154.
- Clemente, F., Ribeiro, G., Quemy, A., Santos, M., Pereira, R., & Barros, A. (2023). ydata-profiling: Accelerating data-centric AI with high-quality data. *Neurocomputing*, 554, 126585. https://doi.org/10.1016/j.neucom.2023.126585
- Dibia, V. (2023). LIDA: A Tool for Automatic Generation of Grammar-Agnostic Visualizations and Infographics using LLMs. arXiv:2303.02927.
- Dong, S., Sahri, S., & Palpanas, T. (2024). Data Quality Awareness: A Journey from Traditional Data Management to Data Science Systems. arXiv:2411.03007.
- Ehrlinger, L., Rusz, E., & Wöß, W. (2019/2022). A Survey of Data Quality Measurement and Monitoring Tools. *Frontiers in Big Data*, 5. https://doi.org/10.3389/fdata.2022.850611
- Elouataoui, W. (2024). AI-Driven Frameworks for Enhancing Data Quality in Big Data Ecosystems. arXiv:2405.03870. https://doi.org/10.48550/arxiv.2405.03870
- Epperson, W., Gorantla, V., Moritz, D., & Perer, A. (2023). Dead or Alive: Continuous Data Profiling for Interactive Data Science. *IEEE Transactions on Visualization and Computer Graphics*, 30, 197–207. https://doi.org/10.1109/tvcg.2023.3327367
- Gupta, N., Patel, H., Afzal, S. et al. (2021). Data Quality Toolkit: Automatic Assessment of Data Quality and Remediation for Machine Learning Datasets. arXiv:2108.05935.
- Han, S., Hu, X., Huang, H., Jiang, M., & Zhao, Y. (2022). ADBench: Anomaly Detection Benchmark. *NeurIPS 2022 Datasets and Benchmarks Track*. arXiv:2206.09426.
- Huang et al. (2023). A Survey on Hallucination in Large Language Models. arXiv:2311.05232.
- Hulsebos, M., Hu, K., Bakker, M., et al. (2019). Sherlock: A Deep Learning Approach to Semantic Data Type Detection. *KDD 2019*. arXiv:1905.10688.
- Kandel, S. et al. (2012). Profiler: integrated statistical analysis and visualization for data quality assessment.
- Li, A., Zhao, Y., Qiu, C., Kloft, M., Smyth, P., Rudolph, M., & Mandt, S. (2024). Anomaly Detection of Tabular Data Using LLMs. arXiv:2406.16308. https://doi.org/10.48550/arxiv.2406.16308
- Li, Z., Zhao, Y., Hu, X., Botta, N., Ionescu, C., & Chen, G. H. (2022). ECOD: Unsupervised Outlier Detection Using Empirical Cumulative Distribution Functions. *IEEE TKDE*. arXiv:2201.00382.
- Li, Z. et al. (2020). COPOD: Copula-Based Outlier Detection. *ICDM*. arXiv:2009.09463.
- Liu, F. T., Ting, K. M., & Zhou, Z.-H. (2008). Isolation Forest. *ICDM 2008*. DOI: 10.1109/ICDM.2008.17.
- Mackay, E. J. et al. (2025). Automated structured data extraction from intraoperative echocardiography reports using large language models. *British Journal of Anaesthesia*.
- Malin, B., Kalganova, T., & Boulgouris, N. (2024). A Review of Faithfulness Metrics for Hallucination Assessment in LLMs. arXiv:2501.00269.
- Miller, R., Chan, S., Whelan, H., & Gregório, J. (2025). A Comparison of Data Quality Frameworks: A Review. *Big Data Cogn. Comput.*, 9, 93. https://doi.org/10.3390/bdcc9040093
- Mladenović, S., Lindauer, M., & Doerr, C. (2025/2026). Automated Data Preparation for Machine Learning: A Survey. *AutoML Workshop / DMLR*.
- Müller et al. (2024). Open-Source Drift Detection Tools in Action: Insights from Two Use Cases. arXiv:2404.18673.
- Patel, H., Guttula, S., Gupta, N., Hans, S., Mittal, R., & N, L. (2023). A Data-centric AI Framework for Automating Exploratory Data Analysis and Data Quality Tasks. *ACM Journal of Data and Information Quality*, 15, 1–26. https://doi.org/10.1145/3603709
- Schelter, S., Lange, D., Schmidt, P., Celikel, M., Biessmann, F., & Grafberger, A. (2018). Automating Large-Scale Data Quality Verification (Deequ). *PVLDB* 11(12):1781–1794.
- Schwabe, D., Becker, K., Seyferth, M., Klaß, A., & Schäffter, T. (2024). The METRIC-framework for assessing data quality for trustworthy AI in medicine. *NPJ Digital Medicine*, 7. https://doi.org/10.1038/s41746-024-01196-4
- Singh, P. (2023). Systematic review of data-centric approaches in artificial intelligence and machine learning. *Data Science and Management*.
- Taleb, I., Serhani, M., Bouhaddioui, C., & Dssouli, R. (2021). Big data quality framework: a holistic approach to continuous quality management. *Journal of Big Data*, 8. https://doi.org/10.1186/s40537-021-00468-0
- Tamm, H. C. (Martinsaari), & Nikiforova, A. (2024). A Systematic Review of Tools for AI-Augmented Data Quality Management in Data Warehouses. *BIR 2025*. arXiv:2406.10940.
- Tang, L., Sun, Z., Idnay, B., Nestor, J., et al. (2023). Evaluating large language models on medical evidence summarization. *NPJ Digital Medicine*, 6.
- Tang et al. (2025). LLM/Agent-as-Data-Analyst: A Survey. arXiv:2509.23988.
- Wang, Ying et al. (2025). Towards Data-Centric AI: A Comprehensive Survey of Traditional, RL and Generative Approaches for Tabular Data Transformation. arXiv:2501.10555.
- Widad, E., Saida, E., & Gahi, Y. (2023). Quality Anomaly Detection Using Predictive Techniques. *IEEE Access*, 11, 103306–103318. https://doi.org/10.1109/access.2023.3317354
- Yang, T., Nian, Y., Li, S. et al. (2024). AD-LLM: Benchmarking Large Language Models for Anomaly Detection. arXiv:2412.11142.
- Zha, D., Bhat, Z. P., Lai, K.-H., Yang, F., Jiang, Z., Zhong, S., & Hu, X. (2023). Data-Centric Artificial Intelligence: A Survey. arXiv:2303.10158.
- Zhang, D., Suhara, Y., Li, J., Hulsebos, M., Demiralp, Ç., & Tan, W.-C. (2020). Sato: Contextual Semantic Type Detection in Tables. *VLDB 2020*. arXiv:1911.06311.
- Zhao, Y. et al. (2023). Investigating Table-to-Text Generation Capabilities of LLMs in Real-World Information-Seeking Scenarios. *EMNLP 2023*. arXiv:2305.14987.
- Zhao, Y., Nasrullah, Z., & Li, Z. (2019). PyOD: A Python Toolbox for Scalable Outlier Detection. *JMLR* 20(96). arXiv:1901.01588.
- Zhou et al. (2025). LLM × DATA: A Survey of the Integration between Language Models and Data Systems. arXiv:2505.18458.
- Zhou, Y., Tu, F., Sha, K., Ding, J., & Chen, H. (2024). A Survey on Data Quality Dimensions and Tools for Machine Learning. arXiv:2406.19614.

### Documentation & Standards References

- DAMA NL. (2020). Dimensions of Data Quality (DDQ) v1.2. https://www.dama-nl.org/wp-content/uploads/2020/09/DDQ-Dimensions-of-Data-Quality-Research-Paper-version-1.2-d.d.-3-Sept-2020.pdf
- Frictionless Framework Docs. (2022). Validating Data. https://framework.frictionlessdata.io/docs/guides/validating-data.html
- Great Expectations Documentation. (2022). ExpectationSuiteValidationResult. https://docs.greatexpectations.io/docs/reference/api/core/ExpectationSuiteValidationResult_class
- Great Expectations Documentation. Expectation Suite. https://docs.greatexpectations.io/docs/0.18/reference/learn/terms/expectation_suite
- IBM Documentation. (2024–2026). Using Data Contracts to improve data quality. https://www.ibm.com/docs/en/ws-and-kc?topic=quality-ensuring-data-data-contracts
- ISO 8000 — Data Quality standard
- ISO/IEC 25012 — Data Quality model for software product quality
- DAMA-DMBOK — Data Management Body of Knowledge (six DQ dimensions: Completeness, Consistency, Integrity, Timeliness, Validity, Uniqueness)
