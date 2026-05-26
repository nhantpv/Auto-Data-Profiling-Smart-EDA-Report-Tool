# SECTION 1 — Academic Papers

### 1. LIDA: A Tool for Automatic Generation of Grammar-Agnostic Visualizations and Infographics using Large Language Models

**Authors:** Victor Dibia  
**Year & Venue:** 2023, ACL (61st Annual Meeting of the Association for Computational Linguistics) - System Demonstrations  
**Problem:** Automatic visualization creation requires addressing multiple subtasks including understanding data semantics, enumerating visualization goals, and generating visualization specifications.  
**Approach:** Four modules: (1) SUMMARIZER converts data into compact natural language summaries, (2) GOAL EXPLORER enumerates visualization goals, (3) VISGENERATOR generates, refines, executes and filters visualization code, (4) INFOGRAPHER yields data-faithful stylized graphics using image generation models. Uses GPT-3.5/GPT-4 for orchestration.  
**Relevance:** Directly addresses automated EDA through goal-driven visualization generation and data summarization, demonstrating how LLMs can automate the entire visualization creation pipeline.  
**Link:** https://arxiv.org/abs/2303.02927  
**Tag:** [verified]

---

### 2. Data Interpreter: An LLM Agent For Data Science

**Authors:** Shaoqing Hong, Yilin Lin, Bang Liu, Bangzheng Wu, Deyu Li, Jiaqi Chen, Jian Zhang, Jiangjie Chen, Lan Wu, Manchen Zhu, Xiang Li, Yifei Li, Yankai Lin, Zhangsheng Wang, Zongmin Li  
**Year & Venue:** 2024, ACL 2024/2025 Findings  
**Problem:** LLM agents struggle with non-linear relationships, recursive dependencies, implicit data-dependent reasoning, and extensive context management in data science tasks.  
**Approach:** Uses hierarchical graph-based modeling to represent task complexity and a progressive strategy for step-by-step verification and refinement. Features dynamic planning with hierarchical graph structures, dynamic tool integration, and logical inconsistency identification through feedback. Decomposes projects into tasks like data exploration, correlation analysis, outlier detection, feature engineering, and visualization.  
**Relevance:** Comprehensive data science agent covering entire workflow including exploratory analysis, demonstrating autonomous handling of complex data profiling and analysis tasks.  
**Link:** https://arxiv.org/abs/2402.18679  
**Tag:** [verified]

---

### 3. InfiAgent-DABench: Evaluating Agents on Data Analysis Tasks

**Authors:** Xueyu Hu, Ziyu Zhao, Shuang Wei, Ziwei Chai, Qianli Ma, Guoyin Wang, Xuwu Wang, Jing Su, Jingjing Xu, Ming Zhu, Yao Cheng, Jiwei Li, Kun Kuang, Yang Yang, Hongxia Yang, Fei Wu  
**Year & Venue:** 2024, ICML 2024 (Proceedings of Machine Learning Research Vol. 235)  
**Problem:** Lack of comprehensive benchmark for evaluating LLM-based agents on data analysis tasks that require end-to-end problem solving through code generation and execution.  
**Approach:** Introduces DABench with 603 data analysis questions derived from 124 CSV files. Uses format-prompting technique to convert open-ended questions into closed-form format for automatic evaluation. Develops DAAgent, a specialized agent that surpasses GPT-3.5 by 3.9% on the benchmark.  
**Relevance:** Provides evaluation framework crucial for assessing automated data analysis systems, includes tasks directly related to data profiling and exploratory analysis.  
**Link:** https://arxiv.org/abs/2401.05507  
**Tag:** [verified]

---

### 4. DS-1000: A Natural and Reliable Benchmark for Data Science Code Generation

**Authors:** Yuhang Lai, Chengxi Li, Yiming Wang, Tianyi Zhang, Ruiqi Zhong, Luke Zettlemoyer, Scott Wen-tau Yih, Daniel Fried, Sida Wang, Tao Yu  
**Year & Venue:** 2022/2023, ICML 2023  
**Problem:** Lack of benchmark with naturalistic, diverse data science problems and reliable execution-based evaluation metrics for code generation models.  
**Approach:** 1,000 data science problems spanning seven Python libraries (NumPy, Pandas, TensorFlow, PyTorch, SciPy, Scikit-learn, Matplotlib) collected from StackOverflow. Uses multi-criteria metrics checking both functional correctness through test cases and surface-form constraints, with problem perturbations to defend against memorization.  
**Relevance:** Foundational benchmark for evaluating code generation capabilities essential for automated data analysis and EDA tasks, covering data manipulation and visualization libraries.  
**Link:** https://arxiv.org/abs/2211.11501  
**Tag:** [verified]

---

### 5. Chat2VIS: Generating Data Visualisations via Natural Language using ChatGPT, Codex and GPT-3 Large Language Models

**Authors:** Paula Maddigan, Teo Susnjak  
**Year & Venue:** 2023, IEEE Access, Vol. 11, pp. 45181-45193  
**Problem:** Natural language interfaces for visualization face challenges due to inherent ambiguity and poorly written user queries, making language understanding difficult.  
**Approach:** Uses effective prompt engineering with LLMs (GPT-3, Codex, ChatGPT) to convert free-form natural language directly into Python code for visualizations, demonstrating that proper prompting solves language understanding more efficiently than traditional NLP approaches using hand-crafted grammar rules.  
**Relevance:** Shows practical application of LLMs for automated visualization generation from natural language, relevant for building conversational interfaces to data profiling tools.  
**Link:** https://arxiv.org/abs/2302.02094  
**Tag:** [verified]

---

### 6. InsightPilot: An LLM-Empowered Automated Data Exploration System

**Authors:** Pingchuan Ma, Rui Ding, Shuai Wang, Shi Han, Dongmei Zhang  
**Year & Venue:** 2023, EMNLP 2023 System Demonstrations  
**Problem:** Effective data exploration requires in-depth dataset knowledge and expertise in data analysis techniques, creating time-consuming obstacles for analysts.  
**Approach:** LLM-based system that automatically selects analysis actions (understanding, summarizing, explaining) and issues intentional queries (IQueries) to create coherent exploration sequences. Collaborates with insight engine to iteratively explore data and generate insights using carefully designed analysis actions that mimic data analyst approaches.  
**Relevance:** Direct application to automated EDA through intelligent orchestration of data exploration actions, demonstrating how LLMs can guide systematic data profiling.  
**Link:** https://arxiv.org/abs/2304.00477  
**Tag:** [verified]

---

### 7. MatPlotAgent: Method and Evaluation for LLM-Based Agentic Scientific Data Visualization

**Authors:** Zhiyu Yang, Zihan Zhou, Shuo Wang, Xin Cong, Xu Han, Yukun Yan, Zhenghao Liu, Zhixing Tan, Pengyuan Liu, Dong Yu, Zhiyuan Liu, Xiaodong Shi, Maosong Sun  
**Year & Venue:** 2024, ACL 2024 Findings  
**Problem:** Scientific data visualization automation with LLMs remains unexplored, and generating precise visualizations requires accurate parameter specification and error correction.  
**Approach:** Model-agnostic framework with three modules: (1) query understanding, (2) code generation with iterative debugging, (3) visual feedback mechanism using multi-modal LLMs for error correction. Introduces MatPlotBench with 100 human-verified test cases and GPT-4V-based automatic evaluation.  
**Relevance:** Addresses automated scientific visualization generation, a key component of data profiling and EDA, with emphasis on iterative refinement and error correction.  
**Link:** https://arxiv.org/abs/2402.11453  
**Tag:** [verified]

---

### 8. Data Formulator 2: Iterative Creation of Data Visualizations, with AI Transforming Data Along the Way

**Authors:** Chenglong Wang, Bongshin Lee, Steven M. Drucker, Donghao Ren, Jianfeng Gao  
**Year & Venue:** 2024, arXiv preprint  
**Problem:** Existing AI-powered visualization systems require analysts to provide complete specifications in a single turn, which doesn't support the iterative nature of data exploration.  
**Approach:** Blends graphical user interfaces and natural language inputs with AI-powered data transformation. Includes "data threads" that let users navigate iteration history and reuse previous designs. Uses LLMs to transform data flexibly (reshaping, filtering, aggregation, window functions, column derivation) while maintaining context across iterations.  
**Relevance:** Addresses iterative data exploration workflow essential for EDA, showing how LLMs can manage complex data transformations throughout the analysis process.  
**Link:** https://arxiv.org/abs/2408.16119  
**Tag:** [verified]

---

### 9. DAgent: A Relational Database-Driven Data Analysis Report Generation Agent

**Authors:** Wenyi Xu, Yuren Mao, Xiaolu Zhang, Xuemei Dong, Mengfei Zhang, Yunjun Gao, Chao Zhang  
**Year & Venue:** 2025, arXiv preprint  
**Problem:** Manual data analysis report generation from relational databases is labor-intensive and requires multi-step reasoning, cross-table associations, and synthesizing insights into reports.  
**Approach:** LLM agent system integrating planning, tools, and memory modules to decompose natural language questions into logically independent sub-queries, retrieve information from relational databases, and generate analytical reports. Constructs DA-Dataset benchmark for evaluation.  
**Relevance:** Demonstrates end-to-end data profiling and analysis from relational data sources, directly applicable to automated data quality reporting and insight generation.  
**Link:** https://arxiv.org/abs/2503.13269  
**Tag:** [verified]

---

### 10. Spider2-V: How Far Are Multimodal Agents From Automating Data Science and Engineering Workflows?

**Authors:** Ruisheng Cao, Fangyu Lei, Haoyuan Wu, Jixuan Chen, Yeqiao Fu, Hongcheng Gao, Xinzhuang Xiong, Hanchong Zhang, Yuchen Mao, Wenjing Hu, Tianbao Xie, Hongshen Xu, Danyang Zhang, Sida Wang, Ruoxi Sun, Pengcheng Yin, Caiming Xiong, Ansong Ni, Qian Liu, Victor Zhong, Lu Chen, Kai Yu, Tao Yu  
**Year & Venue:** 2024, NeurIPS 2024  
**Problem:** Evaluating multimodal agents on professional data science workflows requires realistic tasks in authentic environments with enterprise-level applications.  
**Approach:** Introduces first multimodal agent benchmark with 494 real-world tasks in authentic computer environments, incorporating 20 enterprise-level professional applications. Tasks evaluate ability to perform data-related tasks by writing code and managing GUI in enterprise data software.  
**Relevance:** Benchmark for evaluating automated data engineering and analysis capabilities across diverse enterprise data tools, relevant for understanding practical deployment of data profiling agents.  
**Link:** https://arxiv.org/abs/2407.10956  
**Tag:** [verified]

---

### 11. ChartGPT: Leveraging LLMs to Generate Charts from Abstract Natural Language

**Authors:** Yuan Tian, Weiwei Cui, Dazhen Deng, Xinjing Yi, Yurun Yang, Haidong Zhang, Yingcai Wu  
**Year & Venue:** 2023/2024, IEEE Transactions on Visualization and Computer Graphics (TVCG) 2024  
**Problem:** Accurately capturing user intents from abstract natural language inputs for chart generation is challenging as inputs are often ambiguous or under-specified.  
**Approach:** Decomposes chart generation into six sequential steps using chain-of-thought reasoning (column selection, filtering, chart type selection, visual encoding). Fine-tunes open-source LLM on constructed dataset of abstract utterances with corresponding charts rather than relying solely on prompt engineering.  
**Relevance:** Demonstrates step-by-step decomposition for visualization generation from natural language, applicable to automated chart recommendation in data profiling tools.  
**Link:** https://arxiv.org/abs/2311.01920  
**Tag:** [verified]

---

### 12. Large Language Model-based Data Science Agent: A Survey

**Authors:** Ke Chen, Chengquan Guo, Hao Liu, Shiyang Huang, Junru Lu, Xin Li, Tingxiang Fan, Xin Luna Dong  
**Year & Venue:** 2025, arXiv preprint  
**Problem:** LLM-based data science agents are scattered across different designs and capabilities, making it difficult to understand their design principles and application patterns systematically.  
**Approach:** Dual-perspective survey framework examining: (1) Agent design covering agent roles, execution structures (static vs. dynamic), knowledge integration, and reflection mechanisms; (2) Data science applications covering data preprocessing, modeling, evaluation, and visualization workflows. Synthesizes insights to identify research opportunities.  
**Relevance:** Comprehensive survey providing structured understanding of how LLM agents are designed for data science tasks, essential reading for building LLM-powered data profiling systems.  
**Link:** https://arxiv.org/abs/2508.02744  
**Tag:** [verified]

---

### 13. A Survey of Data Agents: Emerging Paradigm or Overstated Hype?

**Authors:** Yizhang Zhu, Liangwei Wang, Chenyu Yang, Xiaotian Lin, Boyan Li, Wei Zhou, Xinyu Liu, Zhangyang Peng, Tianqi Luo, Yu Li, Chengliang Chai, Chong Chen, Shimin Di, Ju Fan, Guoliang Li, Nan Tang, Yuyu Luo, Guanzhen Li, Jinyang Gao, Xiaoyong Du (24+ authors)  
**Year & Venue:** 2025, arXiv preprint (revised February 2026)  
**Problem:** Terminological ambiguity around "data agents" conflates simple query responders with sophisticated autonomous architectures, creating mismatched expectations and adoption barriers.  
**Approach:** Introduces first systematic hierarchical taxonomy (L0–L5) defining agent autonomy levels from simple responders to proactive systems. Reviews agents by autonomy progression across data management, preparation, and analysis. Analyzes L2-to-L3 transition where agents evolve from procedural execution to autonomous orchestration.  
**Relevance:** Most comprehensive and recent survey providing taxonomy and roadmap for data agent development, essential for understanding where automated data profiling fits in the broader data agent ecosystem.  
**Link:** https://arxiv.org/abs/2510.23587  
**Tag:** [verified]

---

### 14. Data Quality Toolkit: Automatic Assessment of Data Quality and Remediation for Machine Learning Datasets

**Authors:** Nitin Gupta, Hima Patel, Shazia Afzal, Naveen Panwar, Ruhi Sharma Mittal, Shanmukha Guttula, Abhinav Jain, Lokesh Nagalapatti, Sameep Mehta, Sandeep Hans, Pranay Lohia, Aniya Aggarwal, Diptikalyan Saha  
**Year & Venue:** 2021, IBM Research, arXiv preprint  
**Problem:** General data quality tools assess data with profiling checks but cannot detect ML-specific issues like noisy labels, overlapping classes, or context-dependent quality problems.  
**Approach:** Automated toolkit that assesses data quality across ML-specific metrics and develops transformation operations to address quality gaps. Reduces data preparation time by automatically identifying issues that affect ML model performance rather than just general data quality.  
**Relevance:** Foundational work on automated data quality assessment specifically designed for ML workflows, directly applicable to intelligent data profiling for model building.  
**Link:** https://arxiv.org/abs/2108.05935  
**Tag:** [verified]

---

### 15. DA-Code: Agent Data Science Code Generation Benchmark for Large Language Models

**Authors:** Multiple  
**Year & Venue:** 2024, ACL 2024  
**Problem:** Existing benchmarks do not adequately capture the complexity of real-world data analysis tasks requiring data wrangling, machine learning, and exploratory data analysis.  
**Approach:** 500 complex task examples from real data analysis covering data wrangling (DW), machine learning (ML), and exploratory data analysis (EDA). Uses real and diverse data, requires complex data science programming (Python, SQL, Bash). Includes DA-Agent baseline achieving 30.5% accuracy showing substantial room for improvement.  
**Relevance:** Benchmark specifically designed to evaluate data analysis agents on realistic EDA tasks, provides metrics for assessing automated profiling system capabilities.  
**Link:** https://arxiv.org/abs/2410.07331  
**Tag:** [verified]

---

# SECTION 2 — GitHub Repositories

## Data Profiling / AutoEDA Libraries

| Repository | GitHub URL | Stars (May 2026) | Description | Activity Status | What it Does Well | What it Lacks vs Target | Tag |
|------------|-----------|------------------|-------------|-----------------|-------------------|------------------------|-----|
| ydata-profiling | https://github.com/ydataai/ydata-profiling | ~13,600 | One-line EDA tool generating comprehensive HTML/JSON reports for Pandas and Spark DataFrames with statistics, visualizations, correlations, and data quality checks | Active (v4.19.1, Apr 2026) | Comprehensive statistical profiling, time-series and text analysis, minimal code, multiple export formats | No database connectivity (requires pre-loaded dataframes), no LLM narrative insights, no automated issue detection beyond statistics | [verified] |
| D-Tale | https://github.com/man-group/dtale | ~5,100 | Flask/React visualizer for Pandas with interactive grid, charts, and analysis tools | Active (v3.19.1, Jan 2026) | Interactive web UI, extensive chart builder, column transformations, code export, Jupyter integration | Limited database connectivity, no LLM narrative generation, memory-based data storage, no automated quality scoring | [verified] |
| Sweetviz | https://github.com/fbdesignpro/sweetviz | ~3,100 | High-density visualization EDA tool for comparing datasets and analyzing target features | Stale (v2.3.1, Nov 2023) | Beautiful high-density visualizations in HTML, dataset comparison, target value analysis, mixed-type associations | No database connectivity, no LLM insights, works only with in-memory DataFrames, no automated quality detection | [verified] |
| DataPrep | https://github.com/sfu-db/dataprep | ~2,200+ | Low-code data preparation library with Connector, EDA, and Clean APIs | Stale (last update Jun 2024) | 10X faster than Pandas tools (Dask-based), database connectivity via ConnectorX (Postgres, MySQL, SQLServer), interactive visualizations | No LLM narrative generation, no comprehensive data quality issue detection | [verified] |
| AutoViz | https://github.com/AutoViML/AutoViz | ~1,800-1,900 | Automatically visualizes datasets of any size with one line of code | Active (recent commits) | Works with any size dataset, automatic data cleaning recommendations, supervised visualizations, interactive Bokeh charts | No database connectivity (CSV/DataFrame input only), no LLM insights, no automated quality testing framework | [verified] |
| klib | https://github.com/akanz1/klib | ~522 | Python library for importing, cleaning, analyzing and preprocessing data | Active (v1.4.0, Feb 2026) | Data cleaning functions, customized visualizations (correlation, missing values, distributions), interactive Plotly plots | No database connectivity, no comprehensive profiling reports, no LLM narrative insights, more cleaning-focused than profiling | [verified] |

## LLM-Powered Data Analysis Agents

| Repository | GitHub URL | Stars (May 2026) | Description | Activity Status | What it Does Well | What it Lacks vs Target | Tag |
|------------|-----------|------------------|-------------|-----------------|-------------------|------------------------|-----|
| PandasAI | https://github.com/sinaptik-ai/pandas-ai | ~23,500 | Conversational data analysis library making pandas DataFrames conversational using LLMs and RAG | Active (v3.0.0, Oct 2025) | Natural language queries on DataFrames, supports multiple data sources (SQL, CSV, parquet), multi-dataframe queries, chart generation, Docker sandbox execution, managed service platform | Limited automated data quality detection, no comprehensive narrative "Senior Data Scientist" analysis, no full automated EDA report generation, focus on interactive queries vs automated profiling | [verified] |
| OpenInterpreter | https://github.com/openinterpreter/open-interpreter | ~63,600 | Natural language interface for computers to run code (Python, JavaScript, Shell) locally | Active (3,120+ commits, May 2026) | General-purpose code execution across languages, interactive terminal interface, full system access, works with various LLM providers, voice interface available | General-purpose not data-specific, no automated data profiling, no data quality detection, no structured report generation, requires user to guide analysis | [verified] |
| MetaGPT (DataInterpreter) | https://github.com/geekan/MetaGPT | ~40,000+ | Multi-agent framework including DataInterpreter for end-to-end data science | Active (v0.8.0, Mar 2024) | End-to-end data science workflows, dynamic planning with hierarchical graphs, tool integration, experience recording, ML automation | Part of larger multi-agent framework, complex setup vs single-purpose tools, not specifically focused on data quality detection, limited pre-built narrative generation | [verified] |
| Vanna | https://github.com/vanna-ai/vanna | ~23,400 | RAG-powered text-to-SQL agent for chatting with databases | **ARCHIVED** (Mar 2026) | Accurate text-to-SQL via agentic retrieval, user-aware permissions, streaming responses with rich UI, supports multiple databases | SQL-focused not general data analysis, no descriptive statistics computation, no data quality detection, no visual report generation, **project archived** | [verified] |
| LIDA (Microsoft) | https://github.com/microsoft/lida | ~3,200 | Grammar-agnostic visualization and infographics generation using LLMs | Stale (2023-2024) | Automatic visualization goal generation, grammar-agnostic support (matplotlib, seaborn, altair, d3), data summarization, visualization editing via NL, evaluation and repair | Visualization-focused not full analysis, no automated data quality detection, no descriptive statistics computation, limited database connectivity, stale development | [verified] |
| Jupyter AI | https://github.com/jupyterlab/jupyter-ai | ~3,800 | Extension connecting AI agents to computational notebooks in JupyterLab | Active (v3.0.0rc0) | Native chat UI in JupyterLab, multiple frontier agents (Claude, Codex, GitHub Copilot, Gemini), real-time collaboration, MCP server integration, permission system | Integration platform not analysis tool itself, no automated data profiling, no data quality detection, depends on connected agents for capabilities, no built-in report generation | [verified] |
| LangChain | https://github.com/langchain-ai/langchain | ~123,000+ | Framework with built-in pandas/SQL agents for data analysis | Active (continuously) | Integration with broader ecosystem, SQL agent with query generation and error recovery, pandas DataFrame agent, CSV agent, extensible with custom tools | Framework component not standalone tool, requires custom implementation, no automated data profiling, no pre-built data quality detection, no automatic report generation | [verified] |
| Sketch | https://github.com/approximatelabs/sketch | Not prominently listed | AI code-writing assistant for pandas understanding data context via sketches | Stale (>18 months) | Data-context aware code suggestions, efficient data summarization via sketching algorithms, works as pandas extension, no IDE plugin required | Code suggestion tool not full analysis agent, no automated EDA, no data quality detection, no report generation, limited recent development | [verified] |

## Auto-Visualization & Narrative Reporting

| Repository | GitHub URL | Stars (May 2026) | Description | Activity Status | What it Does Well | What it Lacks vs Target | Tag |
|------------|-----------|------------------|-------------|-----------------|-------------------|------------------------|-----|
| Lux | https://github.com/lux-org/lux | ~5,400 | Automatic visualization recommendations for pandas DataFrames | Stale (2021-2022) | Zero-code visualization recommendations, interactive widget in Jupyter, intent-based exploration (Enhance, Filter, Generalize), export to multiple formats, fast pattern discovery | **No LLM integration** - rule-based not AI-powered, no natural language interface, no automated data quality detection, no narrative generation, Jupyter-only, development discontinued | [verified] |
| Chat2VIS | https://github.com/frog-land/Chat2VIS_Streamlit | Research implementation | Natural language to visualization using GPT-3, Codex, and ChatGPT | Research project (2023) | Free-form natural language to visualization, Streamlit-based interface, prompt engineering for visualization | Research implementation not production tool, visualization-only focus, no data quality detection, no automated profiling, no comprehensive reports | [verified] |

## Data Quality & Validation Libraries

| Repository | GitHub URL | Stars (May 2026) | Description | Activity Status | What it Does Well | What it Lacks vs Target | Tag |
|------------|-----------|------------------|-------------|-----------------|-------------------|------------------------|-----|
| Great Expectations | https://github.com/great-expectations/great_expectations | ~10,000+ | Leading data validation, testing, documentation, and profiling tool with "Expectations" | Active (Python 3.10-3.14) | Comprehensive data validation framework, generates documentation automatically, integration with many data sources, production-ready validation system, expectations as code, data profiling | No LLM narrative generation, complex setup compared to lightweight tools, steeper learning curve, not focused on visual EDA reports | [verified] |
| pandera | https://github.com/unionai-oss/pandera | ~4,300 | Light-weight statistical data testing library for validating dataframes | Active (v0.31.1, Apr 2026) | Schema validation for multiple dataframe libraries (Pandas, Polars, PySpark, Xarray), statistical data testing, Pythonic API (like pydantic for data), type hints and IDE integration, low overhead | No visual reports or dashboards, no database connectivity, no LLM narrative generation, not designed for exploratory profiling, focused on validation not discovery | [verified] |
| Evidently | https://github.com/evidentlyai/evidently | Verified significant | ML and LLM observability framework for evaluating, testing, and monitoring data quality, model performance, and drift | Active (continuous development) | Data drift detection (20+ statistical tests), model performance monitoring, interactive HTML reports, test suites with pass/fail conditions, monitoring UI (self-hosted or cloud), supports tabular data and LLMs | Limited database connectivity (primarily DataFrame-based), no LLM-generated narratives (focuses on metrics/tests), primarily monitoring-focused not exploratory profiling, no CSV auto-import interface | [verified] |
| whylogs | https://github.com/whylabs/whylogs | Verified significant | Open-source data logging library for creating statistical profiles of datasets with privacy-preserving features | Active (Note: WhyLabs acquired by Apple, platform discontinued but OSS continues) | Privacy-preserving data profiling, lightweight and efficient profiles, mergeable profiles for distributed systems, streaming data support, profile visualizer | No automated narrative generation, WhyLabs hosted platform discontinued, requires self-hosting for UI features, not focused on visual EDA reports, limited database connectivity | [verified] |
| deepchecks | https://github.com/deepchecks/deepchecks | Verified | Holistic solution for ML validation supporting tabular, NLP, and CV data | Active (acquired by Check Point May 2026) | Comprehensive test suite (data integrity, drift, model performance), supports tabular/NLP/CV data, minimal configuration, visual test results, CI/CD pipeline integration | No database connectivity, no LLM narrative generation, focused on validation/testing not exploratory profiling, no automated CSV import interface | [verified] |
| Soda Core | Reference found, URL uncertain | Uncertain | Open-source data quality testing framework using SodaCL (checks as YAML) | Active (based on references) | YAML-based data quality checks, CLI and programmatic interfaces, multiple database connector support, part of larger Soda platform | No visual EDA reports, no LLM narrative insights, SodaCL requires YAML knowledge, advanced features require Soda Cloud (paid) | [uncertain] |

---

# SECTION 3 — Commercial / Closed-Source Tools

| Vendor | Description | Overlapping Capabilities | Pricing Tier |
|--------|-------------|-------------------------|--------------|
| **Julius AI** | AI-powered data analyst that performs analysis, visualization, and predictive modeling through natural language queries | ✅ All five capabilities: connects to databases/CSVs (Snowflake, BigQuery, Redshift, PostgreSQL, MySQL), computes descriptive statistics and profiles, detects data quality issues with automated cleaning, uses LLM to generate polished memos and narrative findings, produces charts/graphs/GIFs with export to CSV/Excel | Free tier: 15 messages/month; Paid tiers: Pro and Business (team collaboration, scheduled runs, custom agents, governance controls) |
| **Hex** | AI analytics platform combining notebooks, conversational self-serve analytics, and data apps with AI agents | ✅ Connects to Snowflake/BigQuery/Redshift/Databricks/Postgres, computes statistics through Notebook Agent, partial data quality checks via AI code generation, "Threads" feature for LLM-generated insights in natural language, creates interactive dashboards and AI-generated visualizations | Not publicly disclosed; multiple tiers, requires sales contact; free trial available |
| **Athenic AI** | LLM-enabled self-serve analytics platform that monitors business metrics and provides proactive root-cause analysis | ✅ Pulls data from ERP/CRMs/data warehouses, automated data analysis and metric monitoring, automated anomaly detection and quality monitoring, provides plain-language insights with context and AI explanations, generates tables/graphs/reports | Not publicly disclosed; serves startups to Fortune 50 companies ($4.3M funding Jan 2025) |
| **Zenlytic** | Self-service BI platform with AI data analyst "Zoë" that auto-onboards, generates governed semantic layer, and produces complete analyses | ✅ Connects to Snowflake/BigQuery/Redshift/Databricks/Athena/Azure Synapse/Postgres/MySQL, automated data analysis and exploration, partial quality monitoring through semantic layer governance, Zoë generates written analyses/memos/explanations and PowerPoint presentations, produces dashboards/charts/Excel models/PowerPoint decks | Not publicly disclosed; free trial available ("Try Zoë Free"); $9M Series A (2025) |
| **Tableau Pulse** | AI-powered metrics experience that delivers personalized insights and automated analytics directly into workflows | ✅ Connects to cloud data warehouses and Tableau-supported data sources, automated insights detection and statistical analysis via SpotIQ, anomaly detection and change analysis, AI-generated insight summaries in natural language (Tableau AI with Einstein Trust Layer), creates visualizations paired with natural language explanations | Included with all Tableau Cloud editions; enhanced Q&A features with Tableau+ premium tier only |
| **ThoughtSpot** | Agentic analytics platform with natural language search and AI agent "Spotter" for self-service analytics | ✅ Connects to Snowflake/Databricks/BigQuery/Redshift/Azure Synapse, automated analytics through SpotIQ (AI-powered pattern analysis), automated anomaly detection and data quality monitoring, "Spotter" AI agent provides multi-step analysis with natural language explanations, Liveboards (interactive dashboards) with real-time data | Enterprise Edition and consumption-based pricing; subscription-based with tiered options; custom pricing (contact for quotes); available on AWS Marketplace |
| **Akkio** | No-code AI platform for predictive modeling, data analysis, and workflow automation aimed at business teams | ✅ Connects to CSV/XLSX/Google Sheets/Salesforce/HubSpot/Snowflake/BigQuery/Postgres, "Chat Explore" for analysis and automated data profiling, automated data cleaning and outlier detection, "Generative Reports" feature automatically generates AI-powered reports with actionable insights, dashboards and visualizations with white-labeling | Plans start at $49/month; month-to-month subscription; multiple tiers; free trial (no credit card required) |
| **DataChat** | No-code conversational analytics platform enabling natural language data queries with transparent, reproducible results | ✅ Connects to BigQuery/Databricks/Snowflake/CSV files (processes data in-database), automated data exploration/trend analysis/statistical functions, built-in data cleaning and outlier analysis, conversational AI translates queries and provides insights in plain English, data visualization and automated reporting | Not publicly disclosed; available on AWS Marketplace; acquired by Mews (2025); all processing happens within customer's database (data never sent to LLMs) |

**Note on source quality:** Most information derived from official vendor marketing materials rather than detailed technical documentation. Pricing and specific capability details should be verified directly with vendors for accuracy.

---

# SECTION 4 — Gap Analysis

## (1) Which capabilities are well-covered by existing tools?

**Classical data profiling and statistics computation** is thoroughly solved by traditional libraries. Tools like ydata-profiling, Sweetviz, D-Tale, and DataPrep excel at generating comprehensive statistical summaries, distribution analyses, correlation matrices, missing value reports, and duplicate detection. These tools can produce production-quality HTML reports in seconds and handle large datasets efficiently (especially Dask-based tools like DataPrep). The statistical foundations are mature and reliable.

**Basic visualization generation** is well-covered both by traditional rule-based systems (Lux, AutoViz) and newer LLM-powered tools (LIDA, Chat2VIS, ChartGPT). Grammar-agnostic visualization generation from natural language is now feasible through proper prompt engineering, with systems like LIDA demonstrating reliable chart creation across multiple libraries (matplotlib, seaborn, altair, d3).

**Data validation and testing frameworks** are production-ready. Great Expectations, pandera, and Evidently provide robust "expectations as code" or schema validation for production pipelines. These tools integrate well with CI/CD systems and can enforce data quality contracts at scale.

**Text-to-SQL capabilities** are increasingly reliable for structured queries. Systems like Vanna (though now archived) and commercial tools like ThoughtSpot and Athenic AI demonstrate that converting natural language to SQL queries is a solved problem for many common use cases, especially with RAG-based approaches.

**Interactive conversational query interfaces** work well for targeted questions. PandasAI, Julius AI, and Hex demonstrate that users can successfully query dataframes and databases using natural language for specific analytical questions, with code execution in sandboxed environments.

## (2) Which capabilities are weakly covered or missing?

**LLM-generated narrative insights acting as "Senior Data Scientist"** remains the most underserved capability. While commercial tools like Julius AI, Zenlytic, and Athenic AI claim this capability, open-source implementations are rare. Most tools either generate code/visualizations OR produce pre-templated statistical text, but few synthesize holistic interpretive narratives that explain what the data means, identify business implications, or recommend next analytical steps with domain expertise. The gap between "here's a correlation coefficient" and "this correlation suggests customer churn is driven by X, and you should investigate Y" is largely unfilled.

**End-to-end automated EDA workflows** show surprisingly poor performance. Spider2-V benchmark reveals that state-of-the-art multimodal agents achieve only 14-30% success rates on complete data science workflows despite strong performance on isolated subtasks. The orchestration of profiling → quality detection → visualization → narrative synthesis remains fragile.

**Hallucination and factual grounding** is a critical unresolved problem. Research shows 59-82% factual hallucination rates in LLM outputs, with particularly poor performance on numeric information. The risk that an LLM will confidently state incorrect statistics, misinterpret distributions, or generate plausible-sounding but false insights about data quality is very high. Current systems lack robust verification mechanisms to ensure narrative claims are grounded in actual computed statistics rather than confabulated from the model's training distribution.

**Schema drift detection at production scale** is weakly covered. While Evidently and whylogs offer basic drift detection, automated adaptation strategies are limited. Systems can flag that a schema changed or data distribution shifted, but few automatically diagnose root causes, assess impact on downstream analyses, or recommend remediation strategies. The gap between "we detected drift" and "here's why it happened and what to do" is substantial.

**Automated data quality remediation** is under-developed. Tools excel at detecting issues (missing values, outliers, type inconsistencies, duplicates) but provide minimal automated remediation beyond basic imputation. IBM's Data Quality Toolkit (2021) represents early work on ML-aware quality assessment, but systematic automated fixing of quality issues—especially context-dependent ones like "this outlier is valid in domain X but suspicious in domain Y"—remains unsolved.

**Security for code-generating agents in production** is immature. Running LLM-generated code against real databases creates attack surfaces (prompt injection, data exfiltration, goal hijacking). While PandasAI implements Docker sandboxing and DataChat processes in-database without sending data to LLMs, comprehensive security frameworks addressing the OWASP LLM Top 10 (2025) and Agentic Top 10 (2026) risks are not standard. Most academic systems ignore production security entirely.

**Evaluation and testing of non-deterministic agents** lacks mature frameworks. Traditional software testing assumes determinism; LLM-based systems are inherently stochastic. As noted in ZenML's research, most teams resort to "tested manually," "demo went well," or "monitor in production"—none constituting rigorous quality gates. Systematic offline evaluation frameworks for multi-step data analysis workflows remain rare.

**Handling of large-scale data** reveals scaling challenges. Most LLM-powered tools work well on small-to-medium datasets (under 10GB, under 10M rows) but struggle with big data. Context window limitations, inference costs that balloon with concurrent requests, and inability to reason about data that doesn't fit in memory are persistent problems. Spark-based profiling (ydata-profiling, DataPrep) exists but LLM integration with distributed computing is minimal.

## (3) What is the strongest differentiator the project could pursue?

**Reliable narrative grounding with verification** represents the highest-value differentiator. A system that generates "Senior Data Scientist" narratives but with explicit grounding to actual computed statistics, uncertainty quantification on claims, and automated fact-checking of LLM outputs would fill a critical gap. This means: 
- Every narrative claim (e.g., "the data shows strong correlation between X and Y") is hyperlinked to the specific computed statistic
- Numeric assertions are verified against actual calculations before presentation
- Uncertainty is explicitly communicated when data is ambiguous
- A separate verification module checks LLM outputs for hallucinations before user presentation

This differentiator is achievable because:
- The profiling statistics are computed deterministically (traditional tooling is mature)
- The grounding problem is constrained (unlike general-purpose LLMs, the output must reference specific computed values)
- Verification can be rule-based for many cases (e.g., "does the claimed mean match the computed mean?")

**Integrated workflow from connection to report** is a strong secondary differentiator. The market is bifurcated: traditional profiling tools (ydata-profiling) provide comprehensive analysis but no LLM insights or database connectivity; LLM agents (PandasAI) provide conversational interfaces but require pre-loaded data and lack automated profiling. A tool that truly integrates `database connection → automated profiling → quality detection → visualization → LLM narrative → polished report` in a single workflow would be unique. No existing open-source tool covers all five capabilities at production quality.

**Explicit data quality enforcement with prescriptive recommendations** could differentiate from purely descriptive tools. Rather than "here are 47 missing values in column X" (descriptive), provide "column X has 47 missing values (8.2%); this is likely due to Y; recommended actions: (1) investigate upstream ETL job Z, (2) implement validation rule W, (3) consider imputation strategy V for downstream modeling." Combining Great Expectations-style enforcement with LLM-powered diagnosis creates a more actionable tool than either alone.

## (4) Known technical risks existing tools have NOT solved

**LLM hallucination on statistics** is demonstrably unsolved. DefAn benchmark shows 59-82% factual hallucination rates, with performance deteriorating significantly on numeric information. When asked to interpret data, LLMs frequently generate plausible-sounding statistical claims not grounded in actual calculations. Example risks: claiming correlation values that weren't computed, misidentifying distribution types, inventing trends in time series, stating incorrect percentiles. No existing tool implements robust verification that narrative claims match computed statistics.

**Security of running generated code against real databases** remains a critical vulnerability. Risks include:
- Prompt injection attacks where malicious data in the database (e.g., column names, cell values) manipulate the LLM into running destructive queries
- Data exfiltration where generated code sends sensitive data to external endpoints
- Goal hijacking where autonomous agents are redirected to malicious objectives
- Unintended destructive operations (UPDATE/DELETE instead of SELECT)

While PandasAI uses Docker sandboxing and DataChat processes in-database, comprehensive security frameworks are absent. The OWASP LLM Top 10 (2025) and Agentic Top 10 (2026) enumerate attack vectors, but systematic defenses aren't standard in data analysis agents.

**Scale limits on big tables** constrain practical applicability. Challenges include:
- Context window limitations (GPT-4 has ~128K token limit; a table with 1000 columns exceeds this for schema alone)
- Inference costs that grow linearly with data size (analyzing 100M rows requires either expensive embeddings or sampling strategies that may miss rare anomalies)
- Inability to reason about data that doesn't fit in memory (LLMs can't "scan" a 10TB table to find schema drift)
- Poor performance on truly wide tables (1000+ columns overwhelm both context windows and LLM reasoning)

Current solutions rely on aggressive summarization (LIDA's SUMMARIZER module) or sampling, but these introduce risks of missing critical data quality issues in un-sampled regions.

**Schema drift detection at production scale** lacks automated diagnosis and remediation. While Evidently and whylogs detect when schemas change or distributions shift, they don't automatically:
- Diagnose root causes (was this a deliberate schema migration? a bug in upstream ETL? changing business logic?)
- Assess downstream impact (which dashboards/models/reports will break?)
- Recommend remediation (which transformations are needed to maintain compatibility?)
- Distinguish malicious schema changes from benign evolution

Production data pipelines evolve constantly; automated profiling tools that can't distinguish signal from noise in schema changes generate alert fatigue.

**Narrative grounding to actual computed numbers rather than plausible-sounding text** is the meta-risk underlying many others. Without explicit verification that LLM outputs correspond to computed statistics, users cannot trust automated insights. Current tools either:
- Generate narratives without grounding (hallucination risk)
- Generate only templated text from statistics (no insight synthesis)
- Rely on human review of every claim (not scalable)

The challenge is designing a system where narrative richness and factual reliability coexist. This requires:
- Formal grounding: every narrative claim maps to a computed statistic
- Automated verification: a separate module checks LLM outputs for consistency
- Explicit uncertainty: communicates confidence levels and limitations
- Audit trails: users can trace any claim back to raw data and computation

No existing tool, open-source or commercial, fully solves this. It represents both the highest-value opportunity and the hardest technical challenge for LLM-powered data profiling.

---

# SECTION 5 — Suggested Reading Order

**1. "Large Language Model-based Data Science Agent: A Survey" (Chen et al., 2025)**  
**Reason:** Start here for comprehensive taxonomy of LLM agent design patterns (roles, execution structures, knowledge integration, reflection) and applications across the data science workflow. Provides the conceptual framework for understanding how all other systems fit together and identifies current research gaps.

**2. "A Survey of Data Agents: Emerging Paradigm or Overstated Hype?" (Zhu et al., 2025, revised Feb 2026)**  
**Reason:** Most recent and comprehensive survey providing hierarchical taxonomy (L0-L5 autonomy levels) distinguishing simple query responders from sophisticated autonomous systems. Essential for positioning your tool's capabilities accurately and understanding the L2-to-L3 transition from procedural execution to autonomous orchestration. Updated through February 2026 so captures latest developments.

**3. LIDA: A Tool for Automatic Generation of Grammar-Agnostic Visualizations (Dibia, 2023)**  
**Reason:** Closest academic analog to your system architecture. Demonstrates proven multi-stage pipeline (SUMMARIZER → GOAL EXPLORER → VISGENERATOR → INFOGRAPHER) that successfully integrates data understanding, goal generation, code generation, and visualization. Open-source implementation available at microsoft/lida provides concrete reference architecture you can adapt.

**4. InfiAgent-DABench: Evaluating Agents on Data Analysis Tasks (Hu et al., 2024)**  
**Reason:** Provides concrete benchmark (603 questions, 124 CSV files) you can use to evaluate your system's data analysis capabilities. Format-prompting technique for converting open-ended questions to closed-form evaluation is directly applicable. Understanding current baselines (DAAgent surpasses GPT-3.5 by 3.9%) helps calibrate performance expectations.

**5. Data Interpreter: An LLM Agent For Data Science (Hong et al., 2024)**  
**Reason:** State-of-the-art system demonstrating hierarchical graph modeling for complex data science workflows. Achieves 25% boost on DABench (75.9% to 94.9%) and strong results on open-ended tasks (60% to 97%). Provides concrete technical approaches for handling non-linear relationships, recursive dependencies, and extensive context management—all critical for production-ready data profiling agents.