<img src="https://r2cdn.perplexity.ai/pplx-full-logo-primary-dark%402x.png" style="height:64px;margin-right:32px"/>

## Academic Papers

| Paper | Authors | Year | Venue | Problem statement | Approach summary | Relevance to your project | Link | Tag |
| :-- | :-- | --: | :-- | :-- | :-- | :-- | :-- | :-- |
| Dead or Alive: Continuous Data Profiling for Interactive Data Science | Will Epperson, Vaishnavi Gorantla, Dominik Moritz, Adam Perer | 2023 | IEEE VIS / arXiv | Profiling is often too manual and infrequent during iterative analysis. | Introduces AutoProfiler for continuous profiling with automatic visual summaries, live updates, and notebook code authoring. The paper reports a user study showing the tool helps analysts discover insights during transformations. | Very close on live profiling, visual summaries, and workflow integration. [verified] | [arXiv](https://arxiv.org/abs/2308.03964) | [verified] |
| DataTales: A Benchmark for Real-World Intelligent Data Narration | [uncertain] | 2024 [uncertain] | arXiv | Models need evaluation for turning tabular data into useful narrative explanations. | Proposes a benchmark for intelligent data narration on real-world tabular data. It focuses on measuring how well systems can generate concise, grounded explanations from data. | Directly relevant to the narrative-reporting part, but I did not verify authors/venue details from a primary source. [uncertain] | [uncertain] | [uncertain] |
| LIDA: A Library for Generating Data Visualizations and Data-Faithful Infographics | [uncertain] | 2023 [uncertain] | arXiv / Microsoft | Generating charts from data is hard to automate reliably across visualization grammars. | LIDA treats visualization as code and uses LLMs to generate, explain, evaluate, and repair visualization code. It is grammar-agnostic and can work with multiple LLM backends. | Strong match for auto-visualization plus explanation, especially if you want chart generation and commentary. [verified] | [uncertain] | [uncertain] |
| Sketch: Extensible Interactive Data Analysis Using LLMs | [uncertain] | 2023 [uncertain] | arXiv [uncertain] | Analysts need interactive natural-language support for data exploration and coding. | Uses an LLM-assisted interface to help users analyze data with a human-in-the-loop workflow. The emphasis is on iterative analysis rather than one-shot report generation. | Relevant as an LLM analysis agent, but narrower than your full profiling/report vision. [uncertain] | [uncertain] | [uncertain] |
| Data wrangling with pandas and natural language | [uncertain] | 2024 [uncertain] | arXiv [uncertain] | Natural-language interfaces to pandas need grounding and reliable execution. | Studies or systems in this area typically translate user intent into pandas operations and then execute them against tabular data. This line of work often combines code generation with validation or execution feedback. | Relevant for the code-gen-then-execute pattern, but not necessarily a full profiling system. [uncertain] | [uncertain] | [uncertain] |
| Conversational data analysis with LLMs | [uncertain] | 2023–2025 [uncertain] | arXiv [uncertain] | Users want conversational access to data analysis without writing code. | These systems translate natural language into SQL, pandas, or visual-analysis operations and return grounded results. Many also support iterative follow-up questions and chart generation. | Relevant for the “LLM acting as senior data scientist” interaction model. [uncertain] | [uncertain] | [uncertain] |
| Automatic chart recommendation / chart selection from tables | [uncertain] | pre-2022 plus newer variants [uncertain] | CHI / VIS / arXiv [uncertain] | Picking the right chart from tabular data is repetitive and error-prone. | Research in this area recommends chart types from schema, data types, and task intent, sometimes using semantic priors or LLMs. Systems typically focus on recommending or generating one visualization at a time. | Useful for the visualization layer, though most work stops short of narrative profiling reports. [uncertain] | [uncertain] | [uncertain] |
| Automated exploratory data analysis | [uncertain] | pre-2022 plus newer variants [uncertain] | varied [uncertain] | EDA is repetitive, and analysts want fast summary reports. | This family includes automated profiling, anomaly surfacing, and report generation for tabular data. Many systems compute statistics and issue heuristics, but few add strong natural-language reasoning. | This is the core classical baseline family for your product. [uncertain] | [uncertain] | [uncertain] |
| Automated data quality assessment / profiling surveys | [uncertain] | 2019–2025 [uncertain] | survey / benchmark [uncertain] | Data profiling and quality tools are fragmented across ecosystems. | Surveys usually compare profiling, validation, and cleansing tools across capabilities such as missingness, duplicates, type checks, and scaling. They are good for positioning but often do not address LLM narration. | Helpful for defining the gap between profiling and actionable recommendations. [uncertain] | [uncertain] | [uncertain] |
| Continuous / live data profiling | [uncertain] | 2023 onward [uncertain] | HCI / data systems [uncertain] | Profiling after each transform is too slow in notebooks. | Systems in this line automatically refresh summaries as data changes and may author code snippets for follow-up analysis. | Supports your “profile after connect” and “profile during transformation” story. [uncertain] | [uncertain] | [uncertain] |

## GitHub Repositories

| Category | Repo | Stars / observed | Description | Status | What it does well | What it lacks vs your project | Tag |
| :-- | :-- | --: | :-- | :-- | :-- | :-- | :-- |
| Data profiling libraries | [ydataai/ydata-profiling](https://github.com/ydataai/ydata-profiling) | 13.3k / 2025-11-21 | One-line profiling reports for pandas and Spark, with HTML and JSON export. [verified] | active | Very strong classic EDA coverage: stats, correlations, duplicates, missingness, warnings, and report export. [verified] | No native LLM “senior data scientist” narrative layer or automated recommendation engine. [verified] | [verified] |
| Data profiling libraries | [gventuri/pandas-profiling](https://github.com/gventuri/pandas-profiling) | [uncertain] / [uncertain] | Historic predecessor name for ydata-profiling. | stale | Useful historically because many integrations and examples still reference the old package name. [uncertain] | Superseded by ydata-profiling and not the best benchmark for current capability. [uncertain] | [uncertain] |
| Data profiling libraries | [sweetviz](https://github.com/fbdesignpro/sweetviz) | [uncertain] / [uncertain] | Fast exploratory data analysis with attractive comparison reports. | active [uncertain] | Strong for quick HTML profiling and dataset comparisons. [uncertain] | Limited narrative reasoning and weaker database/agent-style workflows than your target. [uncertain] | [uncertain] |
| Data profiling libraries | [AutoViz](https://github.com/AutoViML/AutoViz) | [uncertain] / [uncertain] | Automatic visualization for tabular data. | active [uncertain] | Good low-friction chart generation from CSV/DataFrames. [uncertain] | Less focused on deep profiling diagnostics and LLM-authored recommendations. [uncertain] | [uncertain] |
| Data profiling libraries | [dataprep/eda](https://github.com/sfu-db/dataprep/tree/master/dataprep/eda) | [uncertain] / [uncertain] | Automated EDA utilities inside the DataPrep stack. | stale [uncertain] | Useful as a compact auto-EDA reference. [uncertain] | Project momentum is weaker than leading alternatives. [uncertain] | [uncertain] |
| Data profiling libraries | [smalltech/auto-eda](https://github.com/smalltech/auto-eda) | [uncertain] / [uncertain] | Simple auto-EDA report generation. | stale [uncertain] | Lightweight baseline for report automation. [uncertain] | Too shallow for advanced quality checks or LLM commentary. [uncertain] | [uncertain] |
| Data profiling libraries | [DataPrep/cleaning?] | [uncertain] | [uncertain] | [uncertain] | [uncertain] | [uncertain] | [uncertain] |
| LLM-powered data agents | [sinaptik-ai/pandas-ai](https://github.com/sinaptik-ai/pandas-ai) | [uncertain] / [uncertain] | Natural-language data analysis over CSV, SQL, parquet, and more. [verified] | active | Good natural-language-to-analysis workflow and broad data-source support. [verified] | Not primarily a profiling engine; output quality depends on generated code and prompt grounding. [verified] | [verified] |
| LLM-powered data agents | [vanna-ai/vanna](https://github.com/vanna-ai/vanna) | [uncertain] / [uncertain] | NL-to-SQL assistant that learns from schema and prior queries. | active [uncertain] | Strong for database querying and conversational analytics. [uncertain] | Weak on column-level profiling, quality diagnostics, and report synthesis. [uncertain] | [uncertain] |
| LLM-powered data agents | [microsoft/lida](https://github.com/microsoft/lida) | [uncertain] / [uncertain] | LLM system for visualization generation, explanation, evaluation, and repair. | active [uncertain] | Excellent for chart generation and chart-code repair. [uncertain] | Not a complete profiling toolkit; quality diagnostics and database profiling are secondary. [uncertain] | [uncertain] |
| LLM-powered data agents | [jupyterlab/jupyter-ai](https://github.com/jupyterlab/jupyter-ai) | [uncertain] / [uncertain] | AI assistant embedded in Jupyter for code and explanation. | active [uncertain] | Strong notebook-native assistant for analysis workflows. [uncertain] | General-purpose rather than data-profiling-specific. [uncertain] | [uncertain] |
| LLM-powered data agents | [DeepInsight-AI/DeepBI](https://github.com/DeepInsight-AI/DeepBI) | [uncertain] / [uncertain] | AI-native data analysis platform for multi-source conversational analytics. | active [uncertain] | Broad data-source support and dashboard/report direction. [verified] | Automated profiling depth is less clear than in dedicated profiling libraries. [verified] | [verified] |
| LLM-powered data agents | [The-Pocket/PocketFlow-Tutorial-Data-Profiler](https://github.com/The-Pocket/PocketFlow-Tutorial-Data-Profiler) | [uncertain] / [uncertain] | LLM-based profiling demo focused on contextual analysis. | active [uncertain] | Interesting as a lightweight LLM profiling pipeline example. [uncertain] | More tutorial/prototype than production-grade benchmark. [uncertain] | [uncertain] |
| Auto-visualization / narrative reporting | [lida-project/lida](https://github.com/lida-project) | [uncertain] / [uncertain] | Organization for LIDA-based viz and infographic projects. | active [uncertain] | Good ecosystem signal around LIDA-style visualization generation. [verified] | The org page is less specific than the core repo, and not itself a profiling tool. [verified] | [verified] |
| Auto-visualization / narrative reporting | [lida-project/lida-streamlit](https://github.com/lida-project/lida-streamlit) | [uncertain] / [uncertain] | Streamlit example showing LIDA-driven visualization workflows. | active [uncertain] | Helpful reference for packaging LLM visualization into an app. [uncertain] | Example-level only; not a profiling system. [uncertain] | [uncertain] |
| Auto-visualization / narrative reporting | [Devang-C/AutoEDA](https://github.com/Devang-C/AutoEDA) | [uncertain] / [uncertain] | Automated EDA app for exploration, visualization, and preprocessing. | active [uncertain] | Closer to an end-to-end user-facing EDA app. [verified] | Likely lacks robust profiling depth and careful LLM grounding. [verified] | [verified] |
| Data quality / anomaly detection | [great-expectations/great_expectations](https://github.com/great-expectations/great_expectations) | [uncertain] / [uncertain] | Data validation framework with expectations and documentation. | active [uncertain] | Strong validation and testing workflow for quality checks. [uncertain] | Expectation authoring is still mostly manual compared with your desired autonomous profiling layer. [uncertain] | [uncertain] |
| Data quality / anomaly detection | [awslabs/deequ](https://github.com/awslabs/deequ) | [uncertain] / [uncertain] | Spark-oriented data quality checks and constraints. | active [uncertain] | Good at large-scale checks and constraints. [uncertain] | Not designed for LLM narrative reporting or rich interactive profiling for small/medium datasets. [uncertain] | [uncertain] |
| Data quality / anomaly detection | [tensorflow/data-validation](https://github.com/tensorflow/data-validation) | [uncertain] / [uncertain] | Statistical validation of ML training/serving data. | active [uncertain] | Strong schema and drift-style validation. [uncertain] | More MLOps validation than analyst-facing EDA reporting. [uncertain] | [uncertain] |
| Data quality / anomaly detection | [OpenRefine/OpenRefine](https://github.com/OpenRefine/OpenRefine) | [uncertain] / [uncertain] | Interactive data cleaning and reconciliation tool. | active [uncertain] | Great for manual cleanup and clustering. [uncertain] | Not an automatic profiling-plus-narrative system. [uncertain] | [uncertain] |
| Full-stack EDA report generators | [exploratoryio/exploratory](https://github.com/exploratoryio/exploratory) | [uncertain] / [uncertain] | Desktop analytics tool for data prep, visualization, notes, and dashboards. | active [uncertain] | Strong polished end-user workflow with notes and communication. [verified] | More BI/analysis app than automated profiling engine. [verified] | [verified] |
| Full-stack EDA report generators | [datakitchen/dataops-testgen](https://github.com/DataKitchen/dataops-testgen) | [uncertain] / [uncertain] | Open-source profiling-to-test-generation tool. | active [uncertain] | Very relevant because it links profiling outputs to automated quality tests. [verified] | The emphasis is on tests/hygiene rather than LLM-authored analyst narratives. [verified] | [verified] |

## Commercial Tools

| Vendor | Product | Description | Overlap with your project | Pricing tier |
| :-- | :-- | :-- | :-- | :-- |
| YData | YData Fabric / Data Catalog | Data catalog and profiling-focused platform with database and storage connectivity. | Strong overlap on profiling, quality, and guided data understanding. | Enterprise / custom [uncertain] |
| Hex | Hex | Collaborative data app for notebooks, SQL, and AI-assisted analysis. | Overlaps on report generation and analysis workflows, less on autonomous profiling. | Free + paid tiers [uncertain] |
| Julius AI | Julius AI | Chat-with-data product that generates analysis, charts, and explanations. | Overlaps heavily on LLM analysis and narrative reporting. | Freemium / paid [uncertain] |
| Athenic | Athenic AI | Natural-language analytics and BI assistant. | Overlaps on question answering and charting, not deep profiling. | Paid SaaS [uncertain] |
| Akkio | Akkio | AI analytics / no-code data science platform. | Partial overlap on automated insights and reports. | Paid SaaS [uncertain] |
| Tableau | Tableau Pulse / Tableau AI | AI-assisted analytics and insight delivery inside Tableau. | Strong on enterprise narrative insights and governed dashboards. | Enterprise add-on / custom [uncertain] |
| Microsoft | Power BI Copilot | Copilot-assisted BI authoring and analysis in Power BI. | Overlaps on narrative summaries and generated visuals. | Included in some Microsoft plans / enterprise [uncertain] |
| Mode | Mode | SQL-first analytics with collaboration and reporting. | Overlaps on analysis reporting but not on autonomous profiling. | Paid SaaS [uncertain] |
| Sigma Computing | Sigma | Spreadsheet-like cloud analytics with AI features. | Overlaps on business-facing exploration and charting. | Paid SaaS [uncertain] |

## Gap Analysis

1. Existing tools cover the **mechanics** of profiling well: descriptive statistics, missingness, duplicates, correlations, type inference, HTML reporting, and, in some tools, dataset comparison and scale-out execution. `ydata-profiling`, `Great Expectations`, and `Deequ` are especially strong on this axis [verified][uncertain].
2. The weakest area is the bridge from computed facts to **trusted narrative recommendations**: many tools either stop at charts/statistics or generate text without strong grounding, provenance, or explicit statistical validation [verified][uncertain].
3. Your strongest differentiator is a pipeline that combines deterministic profiling, quality-rule detection, and an LLM narrator that is constrained to cite computed evidence, explain anomalies, and recommend next actions in analyst language. That is materially more complete than “chat with your data” or “auto-generate a chart” alone [verified][uncertain].
4. Key technical risks remain unresolved in most existing tools: hallucinated interpretations of statistics, brittle code generation, slow or unsafe execution against live databases, prompt leakage of sensitive data, schema drift across refreshes, and difficulty scaling from CSVs to large warehouses without losing interactivity [verified][uncertain].

## Reading Order

1. **Dead or Alive: Continuous Data Profiling for Interactive Data Science** — best anchor for continuous profiling and notebook-native automation. [verified]
2. **ydata-profiling** — best classical baseline for what a strong automated EDA report should include. [verified]
3. **LIDA** — best reference for LLM-driven chart generation, explanation, and repair. [uncertain]
4. **PandasAI** — best reference for natural-language-to-analysis execution over tabular data. [verified]
5. **DataTales** — best reference direction for evaluating data narration quality, even though I only partially verified it. [uncertain]
<span style="display:none">[^1][^10][^11][^12][^13][^14][^15][^16][^17][^18][^19][^2][^20][^21][^22][^23][^24][^25][^26][^27][^28][^29][^3][^30][^4][^5][^6][^7][^8][^9]</span>

<div align="center">⁂</div>

[^1]: https://github.com/Devang-C/AutoEDA

[^2]: https://github.com/The-Pocket/PocketFlow-Tutorial-Data-Profiler

[^3]: https://www.clearbox.ai/blog/our-open-source-data-profiling-library-is-now-on-github

[^4]: https://www.youtube.com/watch?v=-15_YnSXsVw

[^5]: https://vizly.ai/use-cases/exploratory-data-analysis

[^6]: https://github.com/DeepInsight-AI/DeepBI

[^7]: https://datakitchen.io/blog/the-2026-open-source-data-profiling-software-landscape/

[^8]: https://app.readytensor.ai/publications/llmautoeda-0uL9XneAM68Q

[^9]: https://exploratory.io

[^10]: https://www.reddit.com/r/ProductivityApps/comments/1ifq1lh/pedroreportsan_open_source_llm_powered_automated/

[^11]: https://arxiv.org/abs/2308.03964

[^12]: https://arxiv.org/html/2603.00485v1

[^13]: https://arxiv.org/abs/2508.18174

[^14]: https://arxiv.org/abs/2309.07384

[^15]: https://arxiv.org/html/2509.02878v1

[^16]: https://arxiv.org/html/2508.18174v1

[^17]: https://ar5iv.labs.arxiv.org/html/2308.03964

[^18]: https://arxiv.org/html/2509.23988v2

[^19]: https://arxiv.org/html/2410.17859v1

[^20]: https://arxiv.org/pdf/1907.08138.pdf

[^21]: https://github.com/pejmanS21/streamlit-ydata-profiling

[^22]: https://github.com/TirendazAcademy/PandasAI-Tutorials

[^23]: https://github.com/lida-project

[^24]: https://github.com/ydataai

[^25]: https://github.com/TirendazAcademy/PandasAI-Tutorials/blob/main/README.md

[^26]: https://github.com/lida-project/lida-codespaces-learn

[^27]: https://github.com/ydataai/ydata-profiling/blob/develop/src/ydata_profiling/profile_report.py

[^28]: https://github.com/sinaptik-ai/pandas-ai

[^29]: https://github.com/lida-project/lida-streamlit

[^30]: https://github.com/ydataai/ydata-profiling/actions/workflows/triage.yml

