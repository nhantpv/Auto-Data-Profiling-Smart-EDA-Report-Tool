# AI SPEC — M2: OpenML-CC18 Perturbation Benchmark + Modular Severity-Stack

## 1. PROJECT OVERVIEW

- **Project name:** `vsf-severity-bench`
- **One-line description:** Perturbation benchmark trên OpenML-CC18 (72 datasets) + 4 plug-in component (MCAR/MAR/MNAR detector, calibrator, aggregator, compound escalator) — đo realized ML-accuracy drop và validate severity-stack.
- **Problem being solved:** Hiện không có harness chuẩn hoá đo "DQ signals → ML readiness" trên scale OpenML; mỗi paper severity calibration / aggregation chỉ test 1-2 dataset. Cần benchmark public chứng minh aggregator-tuyến tính, calibrator-table-lookup, compound-rule-tier-max dự đoán realized accuracy-drop tốt hơn baseline.
- **Core value proposition:** "Build harness once, reuse for any DQ predictor" — chứng minh empirical aggregator R² ≥ 0.5, escalator Spearman ρ ≥ 0.5, MCAR/MAR/MNAR ≥ 85 % agreement; tất cả output L3 schema (M1) interop được.

## 2. TECH STACK

- **Language:** Python 3.10+ (locked `>=3.10,<3.13`).
- **Runtime:** CPython; chạy local 16 GB RAM / 8-core trong ≤ 24 giờ; không GPU.
- **Key libraries (locked):**
  - `vsf-l3-schema==0.1.0` — schema từ M1 (dependency hard).
  - `numpy==1.26.*`, `pandas==2.2.*` — numerical + tabular.
  - `scikit-learn==1.5.*` — RandomForest, LogisticRegression, GradientBoosting, train/test split, CV, metrics.
  - `openml==0.14.*` — OpenML-CC18 dataset loader (study_id=99).
  - `scipy==1.13.*` — Little's MCAR test, statistical tests.
  - `statsmodels==0.14.*` — logistic regression MAR test, OLS.
  - `cleanlab==2.7.*` — label_purity proxy nếu IBM DQ Toolkit không khả dụng.
  - `missingno==0.5.*` — missingness visualization (chỉ EDA, không trong CI).
  - `pyarrow==16.*` — Parquet output.
  - `click==8.1.*` — CLI.
  - `pytest==8.*`, `pytest-xdist==3.6.*`, `pytest-cov==5.*` — parallel test.
  - `ruff==0.5.*`, `mypy==1.10.*`.
- **Deployment target:** Personal/research GitHub repo + Docker image cho reproducibility. Không PyPI publish ở Phase 1.

## 3. ARCHITECTURE

- **High-level structure:** Monolith Python — CLI-driven batch jobs. 1 entry point `vsf-bench run`. Output Parquet/JSON, không service runtime.
- **Directory layout:**

```
vsf-severity-bench/
├── pyproject.toml
├── README.md
├── LICENSE                          # Apache-2.0
├── Dockerfile
├── docker-compose.yml               # bench job + Parquet output volume
├── .github/workflows/ci.yml
├── configs/
│   ├── benchmark.yaml               # 72 dataset list, 5 perturbation, 3 algo
│   └── splits.json                  # frozen 60/12 train/holdout split
├── src/
│   └── vsf_severity_bench/
│       ├── __init__.py
│       ├── _version.py
│       ├── cli.py                   # click CLI: run, results, report
│       ├── harness/
│       │   ├── __init__.py
│       │   ├── loader.py            # OpenML loader, cache local
│       │   ├── perturbations.py     # 5 perturbation injectors
│       │   ├── trainer.py           # sklearn train + measure drop
│       │   ├── runner.py            # orchestrate: dataset × perturbation × algo × fold
│       │   └── io.py                # Parquet write/read
│       ├── components/
│       │   ├── __init__.py
│       │   ├── base.py              # Component ABC: detect(df) -> list[Finding]
│       │   ├── missingness.py       # Component 1: MCAR/MAR/MNAR
│       │   ├── calibrator.py        # Component 2: severity table-lookup
│       │   ├── aggregator.py        # Component 3: linear verdict
│       │   └── escalator.py         # Component 4: compound rule
│       ├── signals/
│       │   ├── __init__.py
│       │   ├── class_overlap.py     # k-NN based class overlap signal
│       │   ├── label_purity.py      # Cleanlab wrapper
│       │   ├── class_imbalance.py   # ratio min/max class
│       │   └── missingness_signal.py
│       └── eval/
│           ├── __init__.py
│           ├── metrics.py           # R², Spearman ρ, agreement rate
│           └── report.py            # markdown + matplotlib chart
├── data/
│   ├── cache/                       # OpenML cache (gitignored)
│   └── results/                     # Parquet outputs (gitignored)
├── tests/
│   ├── conftest.py
│   ├── test_perturbations.py
│   ├── test_components.py
│   ├── test_signals.py
│   ├── test_end_to_end_one_dataset.py    # 24h MVP test
│   └── test_holdout_metrics.py
└── notebooks/
    ├── 01_explore_results.ipynb
    └── 02_paper_figures.ipynb
```

- **Data flow:**

```
[OpenML CC18 study=99]
       │  72 datasets fetched, cached local Parquet
       ▼
[harness.loader.load(dataset_id)]
       │
       ▼
[harness.perturbations.inject(df, kind, magnitude, seed)]
       │  → perturbed_df, ground_truth_meta
       ▼
[signals.* compute (class_overlap, label_purity, class_imbalance, missingness)]
       │  → dict[str, float] signals
       ▼
[components.missingness.detect(perturbed_df)] → list[Finding]
[components.calibrator.calibrate(Finding)] → Finding (severity tier set)
[components.escalator.escalate(list[Finding])] → list[Finding] (compound_severity set)
       │
       ▼
[harness.trainer.train_measure(perturbed_df, algo)] → baseline_acc, perturbed_acc, drop
       │
       ▼
[components.aggregator.predict(signals)] → verdict, predicted_drop_score
       │
       ▼
[eval.metrics R² (predicted_drop vs realized_drop on holdout 12-dataset)]
[eval.metrics Spearman ρ (compound_tier vs realized_drop rank)]
       │
       ▼
[Parquet: data/results/{run_id}.parquet] + [markdown report + PNG charts]
```

## 4. FEATURES

### Feature: Perturbation harness

- **Description:** Orchestrator chạy `dataset × perturbation × algorithm × fold` matrix với seed-fixed, output 1 row/run vào Parquet.
- **Input:** `configs/benchmark.yaml` (dataset_ids, perturbation grid, algo list, seeds).
- **Output:** `data/results/<run_id>.parquet` columns `[run_id, dataset_id, dataset_name, perturbation, magnitude, algorithm, fold, baseline_acc, perturbed_acc, drop, signals_json, findings_json]`.
- **Acceptance:**
  - Chạy full grid 72 dataset × 5 perturbation × 3 algo × 5-fold ≤ 24 h trên 16 GB / 8-core.
  - Re-run với cùng config + seed → bit-identical drop columns.
  - CLI `vsf-bench run --config configs/benchmark.yaml --datasets 3 --algo rf --perturbation label_noise --magnitude 0.1` chạy 1 row trong ≤ 60 giây.
- **Out of scope:** Multi-class non-binary, regression, custom dataset upload, distributed compute.

### Feature: 5 perturbation injectors

- **Description:** `harness/perturbations.py` cung cấp 5 hàm injector deterministic theo seed.
- **Input:** `(df: pd.DataFrame, y: pd.Series, magnitude: float, seed: int)`.
- **Output:** `(perturbed_df, perturbed_y, meta: dict)`.
- **5 perturbations:**
  1. `label_noise(magnitude ∈ {0.05, 0.10, 0.20})` — flip symmetric với prob `magnitude`.
  2. `feature_shuffle(magnitude=1.0)` — permute 1 column random.
  3. `class_imbalance_subsample(target_ratio ∈ {0.1, 0.2, 0.3})` — subsample minority class.
  4. `missing_injection(mechanism ∈ {MCAR, MAR, MNAR}, rate ∈ {0.10, 0.20})` — inject NaN.
  5. `feature_redundancy(magnitude=1.0)` — duplicate top-correlated column.
- **Acceptance:**
  - Mỗi injector pass property test: cùng seed → identical output; magnitude=0 → identity.
  - `meta` dict chứa `mechanism`, `affected_columns`, `prob` để ground-truth verify.
- **Out of scope:** Adversarial noise, image/text perturbation.

### Feature: Component 1 — MCAR/MAR/MNAR detector

- **Description:** `components/missingness.py` phân loại cơ chế missing trên column-level.
- **Input:** `pd.DataFrame` có NaN.
- **Output:** `list[Finding]` mỗi column NaN-positive 1 finding, `issue_type=MISSING_MECHANISM`, payload `{mechanism: MCAR|MAR|MNAR|unknown}`.
- **Acceptance:**
  - ≥ 85 % mechanism-classification agreement với ground-truth trên ≥ 45 synthetic-injected trial (15 MCAR + 15 MAR + 15 MNAR).
  - Mỗi finding pass `validate_finding` của M1.
  - Little's MCAR test (`scipy.stats.chi2`) cho null hypothesis MCAR; Logistic-Regression MAR test (regress missing-indicator trên các cột khác); MNAR fallback heuristic (self-correlation indicator).
- **Out of scope:** Multi-column joint mechanism, time-varying mechanism.

### Feature: Component 2 — Per-finding calibrator

- **Description:** `components/calibrator.py` map `(issue_type, magnitude_bucket, dq_dimension) → Severity` qua table-lookup học từ training split.
- **Input:** `Finding` chưa có severity hoặc severity coarse.
- **Output:** `Finding` với `severity` set theo bảng.
- **Acceptance:**
  - Default table được fit từ 60 training dataset (drop bucket → severity tier: drop<0.02 = INFO, [0.02,0.05) = WARN, [0.05,0.15) = ERROR, ≥ 0.15 = CRITICAL).
  - ≥ 70 % tier-agreement với downstream-impact ground-truth (RF accuracy-drop bucket) trên 12 holdout dataset.
  - Bảng calibrator export ra `configs/calibrator_table_v0.1.json` để paper appendix.
- **Out of scope:** Online learning / adaptive calibration.

### Feature: Component 3 — Dataset-level aggregator (ML-readiness verdict)

- **Description:** `components/aggregator.py` chạy OLS regression: `realized_drop ~ w₁·class_overlap + w₂·label_purity + w₃·class_imbalance + w₄·missingness_signal + b`. Fit trên training, predict trên holdout.
- **Input:** dict `signals: {class_overlap, label_purity, class_imbalance, missingness_signal}` (4 float ∈ [0,1]).
- **Output:** `Verdict {verdict: READY|WARN|NOT_READY, score ∈ [0,1], blockers: list[str], warnings: list[str], predicted_drop: float}`. Cut-off: predicted_drop ≤ 0.05 = READY; (0.05, 0.15) = WARN; ≥ 0.15 = NOT_READY.
- **Acceptance:**
  - Aggregator predict realized RF test-accuracy drop với **R² ≥ 0.5** trên held-out 12-dataset (PRIMARY KILL CRITERION).
  - Baseline max-only (`predicted_drop = max(signals)`) R² ≤ 0.3 → aggregator phải vượt.
  - Output verdict L3 finding với `issue_type=DATASET_VERDICT` (mới thêm vào enum nếu chưa có, hoặc dùng existing) — pass `validate_finding`.
- **Out of scope:** Conformal interval (đẩy ml-readiness-2 idea, không trong M2), per-family surrogate.

### Feature: Component 4 — Compound escalator

- **Description:** `components/escalator.py` áp dụng rule: `compound_severity = max(individual_tiers) + 1_tier per co-occurring finding > WARN trên cùng column`, bounded at CRITICAL.
- **Input:** `list[Finding]` thuộc cùng dataset.
- **Output:** cùng list với mỗi finding có `compound_severity` field set.
- **Acceptance:**
  - Spearman ρ ≥ 0.5 giữa compound tier và realized accuracy-drop rank, trên ≥ 30/72 datasets (KILL CRITERION).
  - Baseline max-only ρ ≤ 0.35 — escalator phải vượt.
  - Output đáp ứng M1 schema constraint `compound_severity ≥ severity`.
- **Out of scope:** Copula-based aggregation (compound-2), causal DAG (compound-3).

### Feature: Evaluation harness + report

- **Description:** `eval/` tính metric trên Parquet results, sinh markdown + PNG.
- **Input:** Parquet file từ harness run.
- **Output:** `data/results/<run_id>_report.md` + 3 PNG (R² scatter, Spearman ρ heatmap, MCAR confusion matrix).
- **Acceptance:**
  - `vsf-bench report --run-id <id>` exit 0 và sinh đủ 4 artifact.
  - Markdown chứa bảng `{metric, value, kill_threshold, pass/fail}` cho cả 4 component.
- **Out of scope:** Interactive dashboard.

## 5. DATA MODELS

### Run record (Parquet schema)

```python
import pyarrow as pa

RUN_SCHEMA = pa.schema([
    ("run_id",              pa.string()),
    ("dataset_id",          pa.int32()),
    ("dataset_name",        pa.string()),
    ("perturbation",        pa.string()),     # one of 5 names
    ("magnitude",           pa.float64()),
    ("seed",                pa.int32()),
    ("algorithm",           pa.string()),     # rf | logreg | gbm
    ("fold",                pa.int8()),       # 0..4
    ("baseline_acc",        pa.float64()),
    ("perturbed_acc",       pa.float64()),
    ("drop",                pa.float64()),    # baseline - perturbed
    ("signals_json",        pa.string()),     # JSON of dict[str, float]
    ("findings_json",       pa.string()),     # JSON list[Finding]
    ("verdict",             pa.string()),     # READY|WARN|NOT_READY
    ("predicted_drop",      pa.float64()),
    ("compound_tier_max",   pa.string()),     # max compound_severity across findings
    ("created_at",          pa.timestamp("us", tz="UTC")),
])
```

### Verdict model

```python
from pydantic import BaseModel, Field
from typing import Literal

class Verdict(BaseModel):
    verdict: Literal["READY", "WARN", "NOT_READY"]
    score: float = Field(ge=0.0, le=1.0)
    predicted_drop: float = Field(ge=0.0, le=1.0)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    rationale: str = Field(max_length=2000)
```

### Calibrator table (JSON)

```json
{
  "version": "0.1",
  "fit_on": "openml_cc18_train_split_2026-05-29",
  "table": [
    {
      "issue_type": "LABEL_NOISE",
      "dq_dimension": "Validity",
      "magnitude_buckets": [
        {"range": [0.0, 0.02], "severity": "INFO"},
        {"range": [0.02, 0.05], "severity": "WARN"},
        {"range": [0.05, 0.15], "severity": "ERROR"},
        {"range": [0.15, 1.0], "severity": "CRITICAL"}
      ]
    },
    {
      "issue_type": "MISSING_VALUES",
      "dq_dimension": "Completeness",
      "magnitude_buckets": [
        {"range": [0.0, 0.05], "severity": "INFO"},
        {"range": [0.05, 0.20], "severity": "WARN"},
        {"range": [0.20, 0.50], "severity": "ERROR"},
        {"range": [0.50, 1.0], "severity": "CRITICAL"}
      ]
    }
  ]
}
```

### Example run record

```json
{
  "run_id": "0193a2f1-...",
  "dataset_id": 3,
  "dataset_name": "kr-vs-kp",
  "perturbation": "label_noise",
  "magnitude": 0.1,
  "seed": 42,
  "algorithm": "rf",
  "fold": 0,
  "baseline_acc": 0.992,
  "perturbed_acc": 0.871,
  "drop": 0.121,
  "signals_json": "{\"class_overlap\":0.18,\"label_purity\":0.87,\"class_imbalance\":0.48,\"missingness_signal\":0.0}",
  "findings_json": "[{... 1 L3 Finding ...}]",
  "verdict": "WARN",
  "predicted_drop": 0.115,
  "compound_tier_max": "ERROR",
  "created_at": "2026-05-29T10:15:30Z"
}
```

## 6. API / INTERFACE CONTRACTS

### Public Python API

```python
from vsf_severity_bench import (
    load_dataset,           # (dataset_id: int) -> pd.DataFrame, pd.Series
    inject_perturbation,    # (df, y, kind, magnitude, seed) -> (df', y', meta)
    Trainer,                # .fit_measure(df, y, algorithm) -> (baseline_acc, perturbed_acc, drop)
    Verdict,
)

from vsf_severity_bench.components import (
    MissingnessDetector,    # .detect(df) -> list[Finding]
    Calibrator,             # .calibrate(finding) -> Finding
    Aggregator,             # .predict(signals: dict) -> Verdict
    Escalator,              # .escalate(findings: list[Finding]) -> list[Finding]
)

from vsf_severity_bench.signals import (
    class_overlap,          # (df, y) -> float
    label_purity,           # (df, y) -> float
    class_imbalance,        # (y) -> float
    missingness_signal,     # (df) -> float
)
```

### CLI

```bash
vsf-bench run \
  --config configs/benchmark.yaml \
  [--datasets <id-list>] [--algo rf|logreg|gbm|all] \
  [--perturbation <name>|all] [--seed 42] \
  --output data/results/<run_id>.parquet

vsf-bench fit-calibrator \
  --input data/results/<run_id>.parquet \
  --output configs/calibrator_table_v0.1.json

vsf-bench fit-aggregator \
  --input data/results/<run_id>.parquet \
  --output configs/aggregator_weights_v0.1.json

vsf-bench report \
  --input data/results/<run_id>.parquet \
  --output data/results/<run_id>_report.md
```

### Error cases

| Error | Type | Exit code |
|---|---|---|
| Dataset không trong OpenML-CC18 | `DatasetNotInStudyError` | 2 |
| Phối hợp perturbation × dataset không hợp lệ (e.g. MAR mà df không có nullable col) | `PerturbationError` | 3 |
| Aggregator R² < 0.3 trên kill split | `KillCriterionFailed` (cảnh báo, exit 0 vẫn) | 0 (warning) |
| L3 finding output không pass `validate_finding(M1)` | `M1SchemaError` | 4 |

## 7. ENVIRONMENT & CONFIG

- **Env vars:**
  - `VSF_BENCH_CACHE_DIR=/path/to/cache` (default `./data/cache`).
  - `OPENML_API_KEY=<key>` (OpenML cho phép anonymous read; key chỉ cần nếu upload).
  - `VSF_BENCH_SEED=42` (default seed toàn cục).
  - `VSF_BENCH_N_JOBS=-1` (sklearn parallelism).
- **External services:**
  - **OpenML** REST API (`https://www.openml.org/api/v1`) — fetch dataset; cache local Parquet.
  - **M1 package** `vsf-l3-schema==0.1.0` qua PyPI hoặc local wheel.
- **Local dev setup steps:**

  ```bash
  git clone <repo>
  cd vsf-severity-bench
  python -m venv .venv && source .venv/bin/activate
  pip install -e ".[dev]"

  # Cache OpenML-CC18 (≈ 800 MB, 1 lần):
  vsf-bench cache-datasets --study 99

  # 24h MVP test (1 dataset, 1 perturbation, 1 algo):
  vsf-bench run --datasets 3 --algo rf --perturbation label_noise --magnitude 0.1 \
    --output data/results/mvp.parquet

  pytest tests/ -v
  ```

## 8. CONSTRAINTS

**Hard technical constraints:**
- Python 3.10+.
- Compute budget: ≤ 24 h full benchmark trên laptop 16 GB / 8-core; ≤ 10 GB RAM peak.
- Mỗi 1 perturbation injector phải deterministic theo `seed` (CI verify).
- Mọi `Finding` output phải pass `vsf_l3_schema.validate_finding` (M1 v0.1 hard dep).
- Aggregator trên holdout R² ≥ 0.5 (PROJECT-LEVEL kill).
- Escalator Spearman ρ ≥ 0.5 trên ≥ 30/72 datasets (PROJECT-LEVEL kill).
- MCAR/MAR/MNAR detector ≥ 85 % agreement (PROJECT-LEVEL kill).
- Calibrator ≥ 70 % tier-agreement (PROJECT-LEVEL kill).
- Reproducibility: Docker image phải cho cùng metric ± 1e-6.

**Do NOT do list:**
- ❌ Không thêm component thứ 5 (giữ scope 4 component cố định).
- ❌ Không generate L3 finding bằng LLM (deterministic-first; LLM chỉ trong M3).
- ❌ Không dùng dataset ngoài OpenML-CC18 ở Phase 1.
- ❌ Không support distributed (Ray, Dask) — single-machine only.
- ❌ Không train neural network (giữ sklearn-only).
- ❌ Không add web UI / dashboard.
- ❌ Không tự define schema riêng — phải import M1.
- ❌ Không bỏ qua hold-out split để "boost" R² (statistical integrity).

## 9. ACCEPTANCE CRITERIA (PROJECT LEVEL)

- [ ] `pytest tests/ -v --cov=src/vsf_severity_bench --cov-fail-under=85` xanh.
- [ ] `vsf-bench run --config configs/benchmark.yaml --output data/results/full.parquet` hoàn thành trong ≤ 24 h trên laptop reference; output Parquet có ≥ 72×5×3×5 = 5400 rows.
- [ ] `vsf-bench report --input data/results/full.parquet --output report.md` sinh markdown + 3 PNG. Markdown chứa bảng `{component, metric, value, kill_threshold, pass}` với cả 4 component đều `pass`.
- [ ] Aggregator `R² ≥ 0.5` trên 12 holdout dataset — verify trong `tests/test_holdout_metrics.py::test_aggregator_r2`.
- [ ] Escalator `Spearman ρ ≥ 0.5` trên ≥ 30/72 datasets — verify trong `tests/test_holdout_metrics.py::test_escalator_rho`.
- [ ] MCAR/MAR/MNAR detector `≥ 85 % agreement` — verify trong `tests/test_components.py::test_missingness_agreement`.
- [ ] Calibrator `≥ 70 % tier-agreement` — verify trong `tests/test_components.py::test_calibrator_agreement`.
- [ ] Mỗi `Finding` trong `findings_json` của Parquet pass `vsf_l3_schema.validate_finding(json.loads(row.findings_json))`.
- [ ] Re-run với cùng seed/config → bit-identical `drop` column trong Parquet.
- [ ] Docker image `vsf-severity-bench:0.1` build và chạy được `vsf-bench run --datasets 3` trong container.
- [ ] `ruff check src/ tests/` không warning; `mypy src/` không error.

## 10. OPEN QUESTIONS

1. **IBM DQ Toolkit availability:** Per gap doc, IBM DQ Toolkit (Gupta 2021) là target signal-source nhưng chưa rõ Python API public. Nếu không khả dụng, fallback: tự implement `class_overlap` (k-NN per-class distance), `label_purity` (Cleanlab confident-learning score). [ASSUMED fallback Cleanlab + sklearn nếu IBM không phát hành].
2. **OpenML-CC18 dataset stability:** 72 datasets có dataset nào đã deprecated/withdrawn 2026? Cần verify danh sách hợp lệ trong tuần 1; fallback sub-sample 60 dataset nếu một số không tải được.
3. **Holdout split methodology:** Stratify theo `n_features` × `n_classes` đủ chưa, hay cần thêm `n_samples` bin? [ASSUMED 2-dim stratification đủ; điều chỉnh nếu R² unstable].
4. **Algorithm extensibility:** Có cần thêm `XGBoost` (Chen 2016) ở Phase 1 hay giữ 3 sklearn? Khuyến nghị: giữ 3 — XGBoost thêm dependency và rủi ro reproducibility (CUDA, OpenMP).
5. **Calibrator table fit method:** Hiện đang hard-code bucket range. Có nên dùng quantile-based bucket auto-fit thay vì hand-coded? [ASSUMED hand-coded cho v0.1; quantile cho v0.2].
6. **Compound escalator co-occurrence definition:** "Cùng column" vs "cùng table" — đang dùng column-level. Có cần option config? [ASSUMED column-level cho v0.1].
7. **Verdict cut-off thresholds:** `≤ 0.05 = READY, 0.05-0.15 = WARN, ≥ 0.15 = NOT_READY`. Có dữ liệu fit để justify không, hay chọn arbitrary? Cần ablation trong report.
8. **PyPI publish vs private:** Đẩy `vsf-severity-bench` lên PyPI sau Phase 1, hay chỉ GitHub release? [ASSUMED GitHub release ở Phase 1].
9. **Eval seeds:** 1 seed (=42) đủ rigor, hay cần aggregate ≥ 3 seed cho mỗi cell? Khuyến nghị: 3 seeds cho aggregator/escalator final metrics, 1 seed cho MVP.
10. **DATASET_VERDICT issue_type:** M1 enum chưa có. Cần coordinate với M1 để add hoặc reuse existing (e.g. `DISTRIBUTION_DRIFT`). [BLOCKING — chốt với M1 owner trước khi code Component 3].
