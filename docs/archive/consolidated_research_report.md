# Consolidated Research Report — Automated EDA / LLM-Powered Data Science Agents

**Sources:** Claude (C), ChatGPT (G), Perplexity (P — regular + Pro Research, merged under one tag), Grok (X).
**Confidence rule:** 3–4 sources = HIGH, 2 = MEDIUM, 1 = LOW. The two Perplexity files share the P tag — an item in either or both still counts as a single P source.

---

## 1. Executive Summary

- **LIDA (Dibia, ACL 2023) is the single anchor paper all four AIs agree on** — every report cites it as the closest architectural blueprint for "LLM-driven auto-visualization + summarization." [C/G/P/X]
- **ydata-profiling is the consensus classical baseline** for column-level statistical profiling; ~13k stars, all four sources flag it as production-ready but lacking any LLM narrative or DB connectivity. [C/G/P/X]
- **PandasAI is the consensus LLM-data-agent leader** but every source warns it can hallucinate on statistics and is conversational rather than profiling-focused. [C/G/P/X]
- **Vanna's status is the largest factual disagreement in the source set** — Claude, ChatGPT, and Grok call it archived (Mar 2026); Perplexity Pro Research says it is active (updated Feb 2026). Verify before adopting. [C/G/X say archived; P says active]
- **LLM hallucination on numeric statistics is the unsolved risk every report flags** — Claude cites 59–82% factual hallucination rates; Perplexity Pro cites the Akella et al. (2025) and Combo-Eval papers as the most direct mitigations; no open-source tool implements end-to-end grounding. [C/G/P/X]
- **The strongest differentiator across all four reports is the same**: a reliable, auditable LLM "Senior Data Scientist" agent that grounds narrative claims in verified computed statistics, integrated with DB-native profiling and DQ detection in a single pipeline. No open-source tool covers all five layers at production quality. [C/G/P/X]
- **TiInsight (PingCAP) is the closest production-validated system for DB schema understanding via LLMs** — three sources cite it; Hierarchical Data Context (HDC) is an immediately reusable technique. The arXiv ID is a contradiction point (see §6). [G/P/X]
- **Julius AI and Tableau Pulse are the strongest commercial overlaps** — Julius is the only consumer-priced tool that claims the full narrative pipeline; Tableau Pulse leads on enterprise auto-insight delivery but is metric-centric, not profile-centric. [C/G/P/X]

---

## 2. Academic Papers — Consolidated

| Paper | Year | Venue | Relevance to project | Confidence | Sources |
|---|---|---|---|---|---|
| **LIDA: A Tool for Automatic Generation of Grammar-Agnostic Visualizations and Infographics** (V. Dibia) | 2023 | ACL Demo / arXiv:2303.02927 | Closest blueprint for the "chart + narrative summary" layer; the SUMMARIZER → GOAL EXPLORER → VISGENERATOR → INFOGRAPHER pipeline mirrors the Senior Data Scientist design. | HIGH | C/G/P/X |
| **Towards Automated Cross-domain EDA through LLMs (TiInsight)** (Zhu et al.) | 2024/2025 | PVLDB / arXiv:2412.07214 [URL contested — see §6] | Production-validated cross-database EDA system; Hierarchical Data Context (HDC) directly solves the DB-schema-to-LLM problem. ~86–91% accuracy on Spider with GPT-4. | HIGH | G/P/X |
| **Large Language Model-based Data Science Agent: A Survey** (Chen / Wang et al.) | 2025 | arXiv:2508.02744 | Most-cited landscape survey; provides taxonomy of agent roles, execution strategies, and DS workflow stages — essential positioning map. | HIGH | C/G/P |
| **InsightPilot: An LLM-Empowered Automated Data Exploration System** (Ma et al.) | 2023 | EMNLP Demo / arXiv:2304.00477 | Closest architectural ancestor to the "LLM as analyst" intent → IQuery → insight pipeline. | MEDIUM | C/P |
| **InReAcTable: LLM-Powered Interactive Visual Data Story Construction from Tabular Data** (Aodeng et al.) | 2024–2025 | UIST 2025 / arXiv conflict (see §6) | Models the narrative-findings output layer; interaction design for user-guided story construction. | MEDIUM | G/P |
| **A Data-centric AI Framework for Automating EDA and Data Quality Tasks** (IBM team) | 2023 | ACM TODS / DOI:10.1145/3603709 | Validates the productivity case for automated EDA (2× productivity, 30–50% time savings); algorithms for both EDA and DQ. | MEDIUM | P/X |
| **Dead or Alive: Continuous Data Profiling for Interactive Data Science / AutoProfiler** (Epperson et al.) | 2023 | IEEE VIS / arXiv:2308.03964 or 2305.07126 [URL inconsistent across sources] | Notebook-integrated continuous profiling with live-updating visual summaries; user study found 91% of findings discovered. | MEDIUM | G/P |
| Data Interpreter: An LLM Agent For Data Science (Hong et al.) | 2024 | ACL Findings / arXiv:2402.18679 | Hierarchical graph-based DS agent; achieves 94.9% on DABench. | LOW | C |
| InfiAgent-DABench: Evaluating Agents on Data Analysis Tasks (Hu et al.) | 2024 | ICML 2024 / arXiv:2401.05507 | 603 data analysis questions, 124 CSVs; benchmark for evaluating DS agents. | LOW | C |
| DS-1000: A Natural and Reliable Benchmark for Data Science Code Generation (Lai et al.) | 2023 | ICML 2023 / arXiv:2211.11501 | 1,000 DS problems across 7 Python libraries; execution-based evaluation. | LOW | C |
| Chat2VIS: Generating Data Visualisations via NL using ChatGPT, Codex, GPT-3 (Maddigan & Susnjak) | 2023 | IEEE Access / arXiv:2302.02094 | Prompt-engineering approach to NL → Python viz code. | LOW | C |
| MatPlotAgent: LLM-Based Agentic Scientific Data Visualization (Yang et al.) | 2024 | ACL Findings / arXiv:2402.11453 | Multi-modal LLM with visual feedback for chart error correction; MatPlotBench eval set. | LOW | C |
| Data Formulator 2: Iterative Creation of Data Visualizations with AI Data Transformation (Wang et al.) | 2024 | arXiv:2408.16119 | GUI + NL hybrid for iterative viz with "data threads." | LOW | C |
| DAgent: A Relational Database-Driven Data Analysis Report Generation Agent (Xu et al.) | 2025 | arXiv:2503.13269 | End-to-end NL-to-report agent on relational DBs; introduces DA-Dataset benchmark. | LOW | C |
| Spider2-V: How Far Are Multimodal Agents From Automating DS/Engineering Workflows? (Cao et al.) | 2024 | NeurIPS 2024 / arXiv:2407.10956 | 494 enterprise tasks across 20 apps; SOTA agents at 14–30% success. | LOW | C |
| ChartGPT: Leveraging LLMs to Generate Charts from Abstract Natural Language (Tian et al.) | 2023/2024 | IEEE TVCG / arXiv:2311.01920 | Six-step CoT decomposition for chart generation. | LOW | C |
| A Survey of Data Agents: Emerging Paradigm or Overstated Hype? (Zhu et al.) | 2025 (rev. Feb 2026) | arXiv:2510.23587 | Hierarchical L0–L5 autonomy taxonomy. | LOW | C |
| Data Quality Toolkit: Automatic Assessment of DQ for ML Datasets (Gupta et al., IBM) | 2021 | arXiv:2108.05935 | ML-specific DQ assessment + remediation. | LOW | C |
| DA-Code: Agent Data Science Code Generation Benchmark (multiple authors) | 2024 | ACL 2024 / arXiv:2410.07331 | 500 real DS tasks; DA-Agent baseline at 30.5% accuracy. | LOW | C |
| Profiling Relational Data – A Survey (Abedjan et al.) | 2015 | VLDB Journal 24(4):557–581 | Foundational taxonomy of single-column and multi-column profiling tasks. | LOW | G |
| Tasks and Visualizations Used for Data Profiling: A Survey and Interview Study (Ruddle et al.) | 2023 | IEEE TVCG / DOI:10.1109/TVCG.2023.3299452 | Empirical study of 53 analysts' profiling practices. | LOW | G |
| Large language models on tabular data: Prediction, generation, and understanding — a survey (Fang et al.) | 2024 | TMLR | LLM capabilities/limits on tabular tasks. | LOW | G |
| DataPrep.EDA: Task-Centric EDA for Statistical Modeling in Python (Peng et al.) | 2021 | SIGMOD / arXiv:2104.00841 | Declarative Python API for common EDA tasks; Dask-based. | LOW | G |
| QUIS: Question-guided Insights Generation for Automated EDA (Manatkar et al.) | 2024 | EMNLP Industry / arXiv:2410.10270 | QUGen + ISGen two-stage zero-shot pipeline. | LOW | P |
| Quality Assessment of Tabular Data using LLMs and Code Generation (Akella et al.) | 2025 | arXiv:2509.10572 | RAG-aided LLM rule generation + executable validators for DQ. | LOW | P |
| LLM-Based Data Science Agents: A Survey of Capabilities, Challenges, and Future Directions (Rahman et al.) | 2025 | arXiv:2510.04023 | Maps 45 systems on 6 DS lifecycle stages; finds >90% lack trust/safety. | LOW | P |
| A Survey on LLM-based Agents for Statistics and Data Science (Chinese consortium) | 2024 | arXiv:2412.14222 | Planning, reflection, multi-agent collaboration patterns. | LOW | P |
| NL4DV: A Toolkit for Generating Analytic Specifications for Data Visualization from NL (Narechania et al.) | 2020 | IEEE VIS / arXiv:2008.10723 | Pre-LLM rule-based NL → Vega-Lite spec toolkit. | LOW | P |
| Generating Analytic Specifications for Data Visualization from NL using LLMs (Sah et al., NL4DV-LLM) | 2024 | NLVIZ @ IEEE VIS / arXiv:2408.13391 | GPT-4 extension of NL4DV with explainability. | LOW | P |
| Data-centric Artificial Intelligence: A Survey (Zha et al.) | 2023 | arXiv:2303.10158 | Holistic data-centric AI framework. | LOW | P |
| Can LLMs Narrate Tabular Data? (Combo-Eval) (Singh et al., Oracle) | 2025 | arXiv:2510.23854 | Multi-method evaluation framework for LLM-generated NL representations of SQL results. | LOW | P |
| Why Do Open-Source LLMs Struggle with Data Analysis? (Zhu et al.) | 2025 | arXiv:2506.19794 | Finds strategic planning quality is the primary determinant of DA performance. | LOW | P |
| LLM/Agent-as-Data-Analyst: A Survey (Tang et al.) | 2025 | arXiv:2509.23988 | Surveys LLM/agent techniques for heterogeneous data. | LOW | X |
| An LLM-Based Approach for Insight Generation in Data Analysis (Pérez et al.) | 2025 | arXiv:2503.11664 | LLMs producing actionable text insights from multi-table data. | LOW | X |
| InsightLens: Augmenting LLM-Powered Data Analysis with Interactive Insight Management (Weng et al.) | 2024 | arXiv:2404.01644 | Interactive insight management layer. | LOW | X |
| AdaVis: Adaptive and Explainable Visualization Recommendation (Zhang et al.) | 2023 | arXiv:2310.11742 | Logical reasoning-based explainable chart recommendation. | LOW | X |
| DataTales: A Benchmark for Real-World Intelligent Data Narration | 2024 [uncertain] | arXiv [uncertain] | Benchmark for tabular-data narration. **Source self-flagged as unverified.** | LOW | P [uncertain] |

### HIGH-confidence paper summaries

**LIDA (Dibia 2023, ACL Demo, arXiv:2303.02927).** Multi-stage LLM pipeline: SUMMARIZER → GOAL EXPLORER → VISGENERATOR → INFOGRAPHER. Grammar-agnostic because it generates visualization code in any target library (Matplotlib, Seaborn, Altair, D3). Every source identifies this as the closest open-source architectural template; the SUMMARIZER module is the direct analog of "Senior Data Scientist narrative." Code at github.com/microsoft/lida.

**TiInsight (Zhu et al. 2024/2025, PVLDB, arXiv:2412.07214 per P/X; arXiv:2206.12909 per G — see §6).** Production-deployed at PingCAP. Introduces Hierarchical Data Context (HDC) to compress schema semantics for LLM consumption, then chains question clarification → TiSQL text-to-SQL → TiChart visualization. Reports ~86.3% execution accuracy on Spider with GPT-4. The most production-validated end-to-end system in the literature for DB-native LLM EDA.

**Large Language Model-based Data Science Agent: A Survey (Chen / Wang et al. 2025, arXiv:2508.02744).** Dual-perspective survey: agent-design perspective (roles, execution structures, knowledge integration, reflection) crossed with DS-workflow perspective (preprocessing, modeling, evaluation, visualization). The most-cited landscape survey across reports; used as the framing reference for positioning new tools.

---

## 3. GitHub Repositories — Consolidated

### 3.1 Data profiling libraries

| Repo | URL | Stars | Activity | What it does | Confidence | Sources |
|---|---|---|---|---|---|---|
| **ydata-profiling** | github.com/ydataai/ydata-profiling (G links to the fg-data-profiling fork — see §6) | ~13.3k–13.6k | **Active** (Apr 2026 / Jan 2026 per multiple sources) | One-line HTML/JSON EDA reports for pandas/Spark: distributions, correlations, missing values, quality alerts | HIGH | C/G/P/X |
| **Sweetviz** | github.com/fbdesignpro/sweetviz | ~3.1k | **Disputed** — C says stale (v2.3.1, Nov 2023); G/P/X say active (Apr 2026) | High-density target-comparison + train/test diffing HTML | HIGH | C/G/P/X |
| **D-Tale** | github.com/man-group/dtale | ~4.5k–5.1k | **Active** (v3.19.1, Jan/May 2026) | Flask+React interactive grid + chart builder for pandas DataFrames | HIGH | C/G/P/X |
| **DataPrep** | github.com/sfu-db/dataprep | ~2.1k–2.2k | **Disputed** — C/G say stale (Jun 2024 / Apr 2024); P/X say moderately active | Dask-based EDA + Connector + Clean modules; ~10× pandas speed | HIGH | C/G/P/X |
| **AutoViz** | github.com/AutoViML/AutoViz | ~1.6k–1.9k | **Disputed** — G says stale (~2023); C/P say active; includes `FixDQ()` | One-line auto-visualization for any dataset size | HIGH | C/G/P/X |
| **klib** | github.com/akanz1/klib | ~522–~900 | **Disputed** — C says active (v1.4.0 Feb 2026); P says stale (last update 2023) | Lightweight one-line cleaning + viz | MEDIUM | C/P |
| **capitalone/DataProfiler** | github.com/capitalone/DataProfiler | ~1.1k | Active / moderately active | Schema, stats, and PII/sensitive-entity detection via deep learning | MEDIUM | P/X |
| Lux | github.com/lux-org/lux | ~5.4k | **Disputed** — C says stale (2021–2022); G says active (2025) | Auto-viz recommendations as a pandas DataFrame extension; Jupyter-only | MEDIUM | C/G |
| gventuri/pandas-profiling | (legacy fork) | uncertain | Stale | Historic predecessor name; superseded by ydata-profiling | LOW | P [uncertain] |
| smalltech/auto-eda | (URL not given) | uncertain | Stale | Simple auto-EDA report generator | LOW | P [uncertain — possibly hallucinated; verify before trusting] |

### 3.2 LLM-powered data agents

| Repo | URL | Stars | Activity | What it does | Confidence | Sources |
|---|---|---|---|---|---|---|
| **PandasAI** | github.com/sinaptik-ai/pandas-ai | ~16k (P) / ~20k+ (X) / ~23.5k (C) / ~23.6k (G) — **star counts vary** | **Active** (v3.0.0, Oct 2025; YC W24) | NL queries over DataFrames/SQL with LLM + RAG, chart generation, Docker sandbox | HIGH | C/G/P/X |
| **Vanna AI** | github.com/vanna-ai/vanna | ~23.4k–23.5k | **CONTRADICTION** — C/G/X say archived (Mar 2026); P (Pro) says "Active (updated Feb 2026)" | RAG-based text-to-SQL; self-learning from schema + query history; 20+ DB connectors | HIGH | C/G/P/X (status contested) |
| **LIDA** | github.com/microsoft/lida | ~3.2k–4.5k | **Disputed** — C says stale (2023–2024); G/P/X say active or moderately active | LLM-driven grammar-agnostic chart + infographic generation | HIGH | C/G/P/X |
| **Jupyter AI** | github.com/jupyterlab/jupyter-ai | ~3.8k–4.2k | **Active** (v3.0.0rc0; Apr 2026) | JupyterLab extension: chat UI + %%ai magic; multi-LLM support including local | HIGH | C/G/P |
| **Sketch** | github.com/approximatelabs/sketch | ~2.3k–2.6k | **Disputed** — C/P say stale (>18 months / 2023); G says active (Jan 2024) | NL → pandas code; data-context aware via sketching | HIGH | C/G/P |
| OpenInterpreter | github.com/openinterpreter/open-interpreter | ~63.6k | Active | General-purpose NL → local code execution. **Borderline — see appendix.** | LOW | C |
| MetaGPT (with DataInterpreter) | github.com/geekan/MetaGPT | ~40k+ | Active (v0.8.0 Mar 2024) | Multi-agent framework with DataInterpreter for E2E DS | LOW | C |
| LangChain | github.com/langchain-ai/langchain | ~123k+ | Active | General framework with pandas/SQL/CSV agents. **Borderline — see appendix.** | LOW | C |
| Inconvo | github.com/inconvoai/inconvo | ~105 | Active (2026) | Chat-with-data framework with RBAC + safe queries | LOW | G |
| DeepInsight-AI/DeepBI | github.com/DeepInsight-AI/DeepBI | uncertain | Active | AI-native multi-source conversational analytics + dashboards | LOW | P |
| The-Pocket/PocketFlow-Tutorial-Data-Profiler | github.com/The-Pocket/PocketFlow-Tutorial-Data-Profiler | uncertain | Active | LLM-based profiling demo / tutorial | LOW | P [uncertain] |

### 3.3 Auto-visualization / narrative reporting

| Repo | URL | Stars | Activity | What it does | Confidence | Sources |
|---|---|---|---|---|---|---|
| **LIDA** | (see §3.2) | — | — | Listed here by P and X as well — same repo as in 3.2 | HIGH | C/G/P/X |
| NL4DV (Python toolkit) | github.com/arpitomprakash/nl4dv (also PyPI) | ~200 | Maintained | Pre-LLM NL → Vega-Lite spec generator; LLM extension exists in paper form | LOW | P |
| Chat2VIS (Streamlit) | github.com/frog-land/Chat2VIS_Streamlit | research | Research (2023) | NL → viz Streamlit demo | LOW | C |
| lida-project/lida-streamlit | github.com/lida-project/lida-streamlit | uncertain | Active [uncertain] | Streamlit packaging example for LIDA | LOW | P [uncertain] |
| "Related forks/extensions for Streamlit integration" (unspecified) | — | — | — | Generic mention only — no specific repo | LOW | X [vague] |

### 3.4 Data quality / anomaly detection

| Repo | URL | Stars | Activity | What it does | Confidence | Sources |
|---|---|---|---|---|---|---|
| **Great Expectations** | github.com/great-expectations/great_expectations | ~10k–~12k | **Active** (May 2026; Python 3.10–3.14) | Declarative "Expectations" framework; Data Docs HTML reports; CI/CD friendly | HIGH | C/G/P/X (X says "implied in ecosystem") |
| **Evidently** | github.com/evidentlyai/evidently | ~7.5k | Active | Drift detection (20+ tests), model + data monitoring, test suites | HIGH | C/G/P |
| Deequ | github.com/awslabs/deequ | ~3.6k | Active (Mar 2026) | Spark-native data quality checks at scale | MEDIUM | G/P |
| pandera | github.com/unionai-oss/pandera | ~4.3k | Active (v0.31.1, Apr 2026) | Schema validation for pandas/Polars/PySpark/Xarray; pydantic-like | LOW | C |
| whylogs | github.com/whylabs/whylogs | significant | Active (OSS continues post-WhyLabs/Apple) | Privacy-preserving statistical profiles; mergeable; streaming | LOW | C |
| deepchecks | github.com/deepchecks/deepchecks | significant | Active (acquired by Check Point, May 2026) | Tabular/NLP/CV validation suite | LOW | C |
| Soda Core | URL uncertain | uncertain | Active | YAML (SodaCL) data quality checks | LOW | C [uncertain] |
| DataKitchen TestGen | github.com/DataKitchen/dataops-testgen | ~1.5k | Active (2025) | Auto-generates ~60 DQ tests from profiling; anomaly monitoring; scorecards | LOW | P |
| tensorflow/data-validation | github.com/tensorflow/data-validation | uncertain | Active | Statistical validation for ML training/serving data | LOW | P [uncertain] |
| OpenRefine | github.com/OpenRefine/OpenRefine | uncertain | Active | Interactive data cleaning and reconciliation | LOW | P [uncertain] |

### 3.5 Full-stack EDA report generators

| Repo | URL | Stars | Activity | What it does | Confidence | Sources |
|---|---|---|---|---|---|---|
| **D-Tale** | (see §3.1) | — | — | Also listed here by G as full-stack | HIGH | C/G/P/X |
| **AutoViz** | (see §3.1) | — | — | Also listed here by X | HIGH | C/G/P/X |
| Devang-C/AutoEDA | github.com/Devang-C/AutoEDA | ~200 | Stale (2023) | Streamlit EDA app: overview, distributions, correlations | LOW | P |
| exploratoryio/exploratory | github.com/exploratoryio/exploratory | uncertain | Active [uncertain] | Desktop analytics tool: data prep, viz, notes, dashboards | LOW | P [uncertain] |
| pingcap/tiinsight | (claimed URL; not publicly confirmed) | n/a | Production (PingCAP-internal) | TiInsight system (companion to paper) | LOW | P [uncertain — "not publicly listed as of survey date"] |

---

## 4. Commercial Tools — Consolidated

| Vendor | Description | Overlap with project | Pricing | Confidence | Sources |
|---|---|---|---|---|---|
| **Julius AI** | AI data analyst over Excel/CSV/Google Sheets and (per C) DBs like Snowflake, BigQuery, Redshift, Postgres, MySQL; NL queries → charts, models, summaries | Strong narrative + reporting; file-focused per X, DB-capable per C | Free 15 messages/mo; Basic $20/mo; Essential $45/mo (Pro/Business tiers per C) | HIGH | C/G/P/X |
| **Hex** | Collaborative SQL+Python notebook platform with "Hex Magic" / Notebook Agent / Threads | SQL/Python EDA, NL-to-code, AI insights, dashboards; connects to Snowflake/BigQuery/Redshift/Databricks/Postgres | $25/user/mo Starter (P); raised $70M May 2025; enterprise custom | HIGH | C/G/P/X |
| **Tableau Pulse (Salesforce)** | Proactive AI metric insights, NL Q&A, root-cause analysis via Slack/email | Strong narrative & proactive insights; **metric-centric, not profile-centric** (X) | Part of Tableau Cloud; ~$70–$75/user/mo Creator/Standard | HIGH | C/G/P/X |
| **Akkio** | No-code AI for prep + predictive modeling + Chat Explore + Generative Reports | Profiling, predictions, NL exploration; agency-focused | $49/mo Starter (C); reported $349/mo Starter (G); Pro $99/user/mo; Build-On $999/mo; Enterprise custom — **pricing data conflicts across sources** | HIGH | C/G/P/X |
| **Mode Analytics** | SQL/Python/R collaborative analytics; AI Assist for SQL | Reporting/EDA overlap; not autonomous profiling | Contact for pricing (P-Pro: acquired by ThoughtSpot) | HIGH | G/P/X |
| **Athenic AI** | Autonomous always-on NL analytics agent over DBs/warehouses | NL-to-SQL, multi-source insight discovery; query-focused per X; root-cause + anomaly detection per C | Not publicly listed; free trial; $4.3M funding Jan 2025 (per C) | HIGH | C/G/P/X (X is brief mention) |
| **ThoughtSpot** | Agentic analytics with NL search + "Spotter" agent | Auto pattern analysis (SpotIQ); anomaly + DQ monitoring; multi-step NL explanations | Enterprise + consumption-based; custom; AWS Marketplace | MEDIUM | C/P |
| **Microsoft Power BI Copilot / Q&A** | Copilot-assisted BI authoring + NL Q&A | Narrative summaries, generated visuals | Included in some Microsoft plans | MEDIUM | G/P |
| **YData Fabric / Data Catalog** | Data catalog + profiling-focused platform with DB connectivity | Strong profiling + quality + data understanding | Enterprise custom | LOW | P |
| **Sigma Computing** | Spreadsheet-like cloud analytics with AI features | Business-facing exploration + charting | Paid SaaS | LOW | P |
| **Zenlytic** | Self-service BI with AI analyst "Zoë"; auto-onboards + governed semantic layer | Connects Snowflake/BigQuery/Redshift/Databricks/Athena/Synapse/Postgres/MySQL; Zoë generates analyses, memos, PowerPoint | Free trial; $9M Series A (2025) | LOW | C |
| **DataChat** | No-code conversational analytics; **processes data in-database, never sent to LLMs** | Built-in cleaning + outlier analysis; transparent/reproducible | Not publicly listed; AWS Marketplace; acquired by Mews (2025) | LOW | C |
| **DataKitchen (Enterprise)** | Enterprise tier above the open-source TestGen | Full-stack DQ profiling + tests + observability + quality dashboards | Enterprise custom (flat-rate, unlimited tables) | LOW | P |
| Google Looker (Smart Lenses) | BI with NL features | Brief mention only — "Others" line | n/a | LOW | G |
| Grist, Aible | Mentioned in "Others" line, no detail | — | n/a | LOW | G |

---

## 5. Gap Analysis — Merged

### 5.1 Consensus gaps (3+ reports — treat as real)

- **LLM "Senior Data Scientist" narrative grounded in verified statistics.** Every source identifies this as the dominant unfilled gap. Open tools either compute statistics with no narrative, or produce narratives without grounding. Risk citation: Claude reports 59–82% factual hallucination rates on numeric content; Perplexity Pro cites Akella et al. (2025) and Combo-Eval as the most direct mitigations. [C/G/P/X]
- **End-to-end seamless pipeline: DB/CSV connection → automated profiling → DQ detection → visualization → LLM narrative → polished report.** No open-source tool covers all five layers at production quality. The market is bifurcated: classical profilers (ydata-profiling, Sweetviz) provide deep statistics but no LLM or DB layer; LLM agents (PandasAI, Vanna) provide conversation but require pre-loaded data and skip automated profiling. [C/G/P/X]
- **Hallucination of statistics by LLMs.** Cited as the highest-impact unsolved technical risk by every source. Verification frameworks (e.g., Combo-Eval, multi-agent critics) exist in research but are not implemented end-to-end in any production open-source tool. [C/G/P/X]
- **Security of running generated code/queries against live databases.** Risks: prompt injection via column data, data exfiltration, goal hijacking, accidental destructive ops. PandasAI uses Docker sandboxing and DataChat processes in-database, but comprehensive frameworks addressing OWASP LLM Top 10 / Agentic Top 10 are absent. Rahman survey (per P) finds >90% of agents lack explicit trust/safety mechanisms. [C/G/P/X]
- **Scale on large tables.** Most DataFrame-based profilers load the whole table into memory. DataPrep's Dask backend is the exception. LLM context windows make wide tables (1000+ columns) infeasible without aggressive sampling, which introduces statistical bias. [C/G/P/X]

### 5.2 Partial-consensus gaps (2 reports — likely real)

- **Schema drift detection with explanatory narrative.** Evidently and whylogs detect drift, but don't diagnose root causes or assess downstream impact. [C/P]
- **Automated DQ remediation beyond detection.** Tools detect missing values, outliers, duplicates well, but don't auto-fix in context-aware ways. IBM Data Quality Toolkit (2021) was an early attempt. [C/P]
- **Cross-domain generalization.** Generic "Senior Data Scientist" prompts degrade on financial/biomedical/etc. data without domain-adapted prompting (per P, citing Zhu 2025 "Why Open-Source LLMs Struggle"). [P/X]

### 5.3 Single-source gaps (1 report — verify before pursuing)

- **Report portability and versioning (CI/CD data quality gates).** No open-source EDA report generator produces versioned, diffable reports. [P only]
- **Prompt injection via column data.** Adversarially crafted cell values can override system prompts; not defended against by any reviewed tool. [P only]
- **Evaluation/testing of non-deterministic agents.** Traditional testing assumes determinism; most teams resort to "tested manually" or "monitor in production." [C only]
- **Inconsistent NL quality across dataset domains** — strategic planning quality, not raw LLM capability, determines output quality (P citing Zhu 2025 arXiv:2506.19794). [P only]
- **Interactive feedback (refining queries) is limited outside research prototypes.** Continuous-profiling-plus-LLM-summary is not seen in any single product. [G only]

### 5.4 Top 3 differentiators for the project

1. **Reliable LLM "Senior Data Scientist" narrative grounded in verified statistics.** Every source ranks this first or near-first. Achievable because the underlying statistics are deterministic; the engineering challenge is verification, not generation.
2. **End-to-end pipeline: DB connection → profiling → DQ detection → visualization → narrative → report.** Every source notes the market bifurcation; closing it is a unique positioning.
3. **Explicit DQ enforcement with prescriptive recommendations** (not just "47 missing values in X" but "this is likely caused by Y, here are 3 remediations"). Claude calls this out explicitly; Grok phrases it as "publication-ready reports with citations to underlying computations."

---

## 6. Contradictions & Disagreements

- **TiInsight arXiv ID.** G cites arXiv:2206.12909 (a June 2022 ID — inconsistent with "VLDB 2025" claim); P (Pro) and X cite arXiv:2412.07214 (December 2024). The latter matches the production-deployed PingCAP system; G's URL appears to be a likely typo or wrong-paper citation. **For the user:** treat 2412.07214 as the working URL but verify on arXiv directly before citing in writing.
- **InReAcTable arXiv ID.** G cites arXiv:2412.06819 (Dec 2024); P (Pro) cites arXiv:2508.18174 (Aug 2025). These may be separate works or different versions of the same paper. **For the user:** check both IDs on arXiv before treating as the same paper.
- **AutoProfiler / Dead or Alive arXiv ID.** G cites doi.org/10.48550/arXiv.2305.07126; P cites arXiv:2308.03964. Different IDs for what is described as the same Epperson et al. work. **For the user:** verify which is the canonical preprint.
- **Vanna repository status.** C, G, and X say archived (Mar 2026); P (Pro Research) says "Active (updated Feb 2026)." This is the largest factual contradiction in the source set. **For the user:** check the GitHub repo directly before any architectural decision depends on Vanna being maintained.
- **Lux activity.** C says stale (2021–2022); G says active (2025). **For the user:** verify recent commit history.
- **Sweetviz activity.** C says stale (v2.3.1, Nov 2023); G/P/X say active (Apr 2026). **For the user:** the consensus is active, but Claude's "v2.3.1, Nov 2023" specifics are concrete enough to warrant a direct check.
- **LIDA activity.** C says stale (2023–2024); G/P/X say active or moderately active (Mar 2024 / 2026). **For the user:** consensus is active; Claude is the outlier.
- **AutoViz activity.** G says stale (~2023); C/P say active with recent commits. **For the user:** consensus is active; G is the outlier.
- **DataPrep activity.** C/G say stale (Jun 2024 / Apr 2024); P/X say moderately active or "active-ish." **For the user:** split 2–2; lean stale.
- **Sketch activity.** C/P say stale (>18 months / 2023); G says active (Jan 2024). **For the user:** lean stale; G's "active" is the outlier.
- **ydata-profiling canonical URL.** G links to github.com/Data-Centric-AI-Community/fg-data-profiling (a fork); C/P link to github.com/ydataai/ydata-profiling (original); X mentions both ("ydata-profiling … or successor fg-data-profiling"). **For the user:** the canonical original is ydataai/ydata-profiling; fg-data-profiling appears to be a fork — its "successor" status is asserted only by Grok and is **uncorroborated**.
- **Akkio Starter pricing.** C says $49/mo; G says ~$349/mo. **For the user:** check Akkio's current pricing page directly.
- **Star counts.** PandasAI ranges 16k (P) → 23.6k (G). LIDA ranges 3.2k (C/G) → 4.5k (P). D-Tale ranges 4.5k (P) → 5.1k (C/G). These are likely snapshot timing differences rather than disagreements; not actionable but worth noting if precise star counts matter.

---

## 7. Single-Source Findings — Verify Before Trusting

Single-source items are either rare gems (the only source noticed them) or hallucinations (the source invented or misremembered them). Verify before incorporating.

### Claude-only (C)

- **Data Interpreter (Hong et al. 2024, arXiv:2402.18679).** Hierarchical-graph DS agent. *Likely real:* arXiv ID looks correct, ACL Findings is plausible.
- **InfiAgent-DABench (Hu et al. 2024, ICML, arXiv:2401.05507).** 603 questions / 124 CSVs benchmark. *Likely real:* concrete numbers, plausible venue.
- **DS-1000 (Lai et al., ICML 2023, arXiv:2211.11501).** *Likely real:* widely cited Stack-Overflow-sourced DS benchmark.
- **Chat2VIS (Maddigan & Susnjak 2023, IEEE Access).** *Likely real:* arXiv:2302.02094 plausible.
- **MatPlotAgent (Yang et al. 2024, arXiv:2402.11453).** *Likely real.*
- **Data Formulator 2 (Wang et al. 2024, arXiv:2408.16119).** *Likely real:* Microsoft/MSR-Asia work, well-known author.
- **DAgent (Xu et al. 2025, arXiv:2503.13269).** *Likely real:* very on-topic for the project; **strong candidate to investigate.**
- **Spider2-V (Cao et al. NeurIPS 2024, arXiv:2407.10956).** *Likely real:* 494-task benchmark, well-known authors.
- **ChartGPT (Tian et al. 2024, IEEE TVCG, arXiv:2311.01920).** *Likely real.*
- **Survey of Data Agents: Emerging Paradigm or Overstated Hype? (Zhu et al. 2025, arXiv:2510.23587).** L0–L5 taxonomy. *Likely real, recent.*
- **Data Quality Toolkit (Gupta et al. 2021, IBM, arXiv:2108.05935).** *Likely real:* well-known IBM Research work.
- **DA-Code (multiple 2024, ACL, arXiv:2410.07331).** 500 tasks; DA-Agent 30.5%. *Likely real.*
- **OpenInterpreter, MetaGPT, LangChain repos.** Real but **out of scope for the brief** — see appendix.
- **pandera, whylogs, deepchecks, Soda Core (Soda Core URL uncertain).** Real DQ libraries; only Claude included them. Pandera and whylogs especially are credible; Soda Core URL warrants verification.
- **Zenlytic, DataChat (commercial).** Real companies; Claude is the only source — verify current product status.

### ChatGPT-only (G)

- **Profiling Relational Data Survey (Abedjan et al., VLDB Journal 2015).** *Almost certainly real:* widely cited foundational survey. The fact only one AI surfaced it is a content gap in the other reports, not a hallucination risk.
- **Tasks and Visualizations Used for Data Profiling (Ruddle et al., TVCG 2023).** *Likely real:* concrete DOI.
- **LLMs on tabular data survey (Fang et al., TMLR 2024).** *Likely real.*
- **DataPrep.EDA paper (Peng et al., SIGMOD 2021, arXiv:2104.00841).** *Likely real:* matches the DataPrep open-source library.
- **Inconvo (github.com/inconvoai/inconvo, ~105 stars).** Production-grade chat-with-data with RBAC. *Plausible but obscure* — 105 stars suggests a small project; the URL pattern matches a real-looking org. **Verify URL exists.**
- **Power BI Q&A, Looker Smart Lenses, Grist, Aible.** Brief "Others" mentions; real products but no detail given.

### Perplexity-only (P) — Pro Research items

- **QUIS (Manatkar et al., EMNLP 2024, arXiv:2410.10270).** Two-stage zero-shot QUGen + ISGen pipeline. *Likely real and directly relevant.*
- **Quality Assessment of Tabular Data using LLMs and Code Generation (Akella et al. 2025, arXiv:2509.10572).** RAG-aided LLM rule generation. *Likely real and highly relevant to the DQ layer.*
- **LLM-Based DS Agents: A Survey (Rahman et al. 2025, arXiv:2510.04023).** Lifecycle survey of 45 systems; the ">90% lack trust/safety" finding is widely actionable. *Likely real.*
- **A Survey on LLM-based Agents for Statistics and Data Science (arXiv:2412.14222).** Chinese consortium 2024. *Likely real.*
- **NL4DV (Narechania et al. 2020, IEEE VIS) and NL4DV-LLM (Sah et al. 2024, NLVIZ).** *Likely real, well-known toolkit lineage.*
- **Data-centric AI: A Survey (Zha et al. 2023, arXiv:2303.10158).** *Likely real, widely cited.*
- **Combo-Eval / Can LLMs Narrate Tabular Data? (Singh et al., Oracle, 2025, arXiv:2510.23854).** *Likely real and highly relevant for evaluation.*
- **Why Do Open-Source LLMs Struggle with Data Analysis? (Zhu et al. 2025, arXiv:2506.19794).** *Likely real.*
- **klib, DataKitchen TestGen, NL4DV repo, AutoEDA (Devang-C), pingcap/tiinsight (URL uncertain).** Real to varying degrees. **pingcap/tiinsight URL is explicitly flagged uncertain by Perplexity Pro itself** — not publicly listed.

### Perplexity-only (P) — regular report items (mostly [uncertain])

- **DataTales benchmark for data narration.** *Possibly real but unverified by source.* Could be a hallucination — verify on arXiv.
- **"Sketch: Extensible Interactive Data Analysis Using LLMs" as a paper** (distinct from the Sketch repo). *May be a paper-vs-repo confusion;* verify whether a formal paper exists.
- **Generic placeholders** ("Conversational data analysis with LLMs", "Automatic chart recommendation", "Automated EDA", "Automated DQ assessment surveys", "Continuous/live data profiling"). These are research areas, not specific papers — not actionable items.
- **smalltech/auto-eda, gventuri/pandas-profiling, DeepInsight-AI/DeepBI, The-Pocket/PocketFlow-Tutorial-Data-Profiler, exploratoryio/exploratory, tensorflow/data-validation, OpenRefine.** Repo names range from plausible-real (OpenRefine, tensorflow/data-validation are well-known) to questionable (smalltech/auto-eda — verify exists). **Treat the unfamiliar ones as URLs to verify.**
- **YData Fabric / Data Catalog, Sigma Computing (commercial).** Real companies.

### Grok-only (X)

- **LLM/Agent-as-Data-Analyst Survey (Tang et al. 2025, arXiv:2509.23988).** *Likely real, but verify — only Grok surfaced this and Grok ranked it #2 in its reading order. Strong candidate to read if it verifies.*
- **An LLM-Based Approach for Insight Generation in Data Analysis (Pérez et al. 2025, arXiv:2503.11664).** *Likely real, focused on narrative findings.*
- **InsightLens (Weng et al. 2024, arXiv:2404.01644).** Interactive insight management. *Likely real.*
- **AdaVis (Zhang et al. 2023, arXiv:2310.11742).** Explainable chart recommendation. *Likely real.*

---

## 8. Recommended Reading Order

Top 7 items to read first, drawn from the consolidated list, ranked. This synthesizes the reading orders from all four sources, weighted toward HIGH-confidence items.

1. **LIDA (Dibia 2023, arXiv:2303.02927)** — the only paper all four sources include in their reading order; the closest architectural blueprint for the project. The microsoft/lida repo gives you concrete reference code.
2. **LLM-Based Data Science Agent: A Survey (Chen / Wang 2025, arXiv:2508.02744)** — 3-source landscape map; gives the conceptual vocabulary for positioning the project against the field.
3. **TiInsight / Towards Automated Cross-domain EDA via LLMs (Zhu et al. 2024, arXiv:2412.07214)** — most production-validated DB-native LLM EDA system; HDC is directly reusable. *Verify the arXiv ID against §6's contradiction before citing.*
4. **ydata-profiling (github.com/ydataai/ydata-profiling)** — the consensus classical baseline; reading the docs/source defines what a "strong automated profile" includes before adding the LLM layer.
5. **InsightPilot (Ma et al. 2023, EMNLP, arXiv:2304.00477)** — closest architectural ancestor for "intent → IQuery → insight" — read alongside LIDA for the full EDA-agent design space.
6. **Quality Assessment of Tabular Data using LLMs and Code Generation (Akella et al. 2025, arXiv:2509.10572)** *single-source from P, but* the most direct paper on the RAG-aided LLM rule generation + critic-agent pattern, which is the best-known mitigation for the hallucination risk every source flagged.
7. **PandasAI (github.com/sinaptik-ai/pandas-ai)** — the consensus state-of-the-art LLM data agent. Read both the docs and the open issues to internalize the failure modes (hallucination on stats, code-exec security) that the project must avoid.

---

## Appendix — Items Excluded as Outside the Brief

The following items were mentioned in source reports but fall outside the original brief's scope (automated EDA / data profiling / LLM-data-agents / data-quality detection / auto-visualization / commercial EDA tools). They are noted here for completeness:

- **OpenInterpreter** [C] — general-purpose NL → local code execution, not data-specific.
- **LangChain** [C] — general LLM-application framework; the brief is about data tools, not framework choices.
- **Generic Perplexity-regular research-area placeholders** ("Conversational data analysis with LLMs", "Automatic chart recommendation from tables", "Automated EDA", "Automated DQ assessment surveys", "Continuous/live data profiling", "Data wrangling with pandas and NL") — these are topics, not citable items.
- **Athenic mention by Grok** ("Others like Athenic (query-focused) exist in the space") — kept in §4 as it is corroborated elsewhere, but Grok's mention itself is too brief to count as substantive.
