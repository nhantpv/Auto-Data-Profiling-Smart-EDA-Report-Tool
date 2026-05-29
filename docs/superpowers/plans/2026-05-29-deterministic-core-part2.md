# Deterministic Core — Part 2: Engines & Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the 3 core analysis engines (Profiling, Anomaly, Schema) and the Findings Builder that merges their outputs into validated JSON.

**Architecture:** Each engine is a thin wrapper around a library (fg-data-profiling, PyOD, pydbml). Findings Builder consumes their raw outputs and produces Pydantic-validated JSON files.

**Tech Stack:** Python 3.13, fg-data-profiling (ydata-profiling), PyOD, pydbml, Pandas, Pytest.

**Prerequisite:** Part 1 must be completed first (Task 1-4).

---

## ⚠️ Pitfalls & Traps

1. **fg-data-profiling `to_json()` returns a STRING, not a dict.** Must do `json.loads(profile.to_json())` to get a dict.
2. **fg-data-profiling JSON structure:** Stats are nested under `profile["variables"]["Age"]["mean"]`, NOT flat. Key `table` holds dataset-level stats, `variables` holds per-column.
3. **PyOD requires ONLY numeric columns.** Must `df.select_dtypes(include='number')` before fitting. If no numeric columns exist, skip anomaly detection entirely.
4. **PyOD crashes on NaN.** Must `dropna()` or impute before fitting. We choose `dropna()` for v1 simplicity.
5. **LOF requires `n_neighbors < n_samples`.** If dataset has < 20 rows (default), LOF will crash. Must set `n_neighbors = min(20, n_samples - 1)`.
6. **ECOD crashes on constant columns** (zero variance → division by zero). Must drop constant columns before fitting.
7. **PyOD `decision_scores_` are NOT normalized** across algorithms. Must normalize to [0,1] before averaging. Use `pyod.utils.utility.standardizer()`.
8. **pydbml API:** Use `parsed = PyDBML(path)`, then `parsed.tables` and `parsed.refs`. Each `ref` has `.col1` (list) and `.col2` (list) attributes.

---

### Task 5: Profiling Engine (Layer 1 Wrapper)

**Files:**
- Create: `src/engines/profiling_engine.py`
- Create: `tests/engines/test_profiling_engine.py`

> ⚠️ **Pitfall:** `ydata_profiling.ProfileReport` is SLOW. For tests, use `minimal=True` to skip heavy computations (correlations, interactions). Test will take ~5s instead of ~30s.

- [ ] **Step 1: Write the failing test**

```python
# tests/engines/test_profiling_engine.py
import pytest
from engines.profiling_engine import run_profiling


class TestRunProfiling:
    def test_returns_dict(self, clean_csv_path):
        from ingestion.csv_reader import load_csv
        df = load_csv(clean_csv_path)
        result = run_profiling(df)
        assert isinstance(result, dict)

    def test_has_table_key(self, clean_csv_path):
        from ingestion.csv_reader import load_csv
        df = load_csv(clean_csv_path)
        result = run_profiling(df)
        assert "table" in result
        assert result["table"]["n"] == 10

    def test_has_variables_key(self, clean_csv_path):
        from ingestion.csv_reader import load_csv
        df = load_csv(clean_csv_path)
        result = run_profiling(df)
        assert "variables" in result
        assert "age" in result["variables"] or "Age" in result["variables"]

    def test_duplicates_detected(self, dirty_csv_path):
        from ingestion.csv_reader import load_csv
        df = load_csv(dirty_csv_path)
        result = run_profiling(df)
        assert result["table"]["n_duplicates"] >= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/engines/test_profiling_engine.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/engines/profiling_engine.py
"""Layer 1: Deterministic profiling via fg-data-profiling (ydata-profiling).

Returns a Python dict containing all statistics. The raw dict is NOT
the final JSON — it must be processed by findings_builder.py (Layer 3).
"""
import json
import logging
import pandas as pd
from ydata_profiling import ProfileReport  # will change to data_profiling when migrated

logger = logging.getLogger(__name__)


def run_profiling(df: pd.DataFrame, minimal: bool = True) -> dict:
    """Run fg-data-profiling on a DataFrame and return raw stats as dict.

    Args:
        df: Input DataFrame (already loaded & sampled).
        minimal: If True, skip heavy computations (correlations, interactions).
                 Set to False for production runs.

    Returns:
        Dict with keys 'table' (dataset-level) and 'variables' (per-column).
    """
    logger.info("Running profiling on DataFrame with %d rows, %d cols.", len(df), len(df.columns))

    profile = ProfileReport(df, minimal=minimal, progress_bar=False)

    # PITFALL: to_json() returns a STRING, not a dict
    raw_json_str = profile.to_json()
    result = json.loads(raw_json_str)

    logger.info("Profiling complete. Found %d variables.", len(result.get("variables", {})))
    return result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/engines/test_profiling_engine.py -v`
Expected: ALL PASS (4 tests). May take 10-20 seconds due to profiling.

- [ ] **Step 5: Commit**

```bash
git add src/engines/profiling_engine.py tests/engines/test_profiling_engine.py
git commit -m "feat: profiling engine wrapping ydata-profiling with minimal mode"
```

---

### Task 6: Anomaly Engine (Layer 2 — PyOD Ensemble)

**Files:**
- Create: `src/engines/anomaly_engine.py`
- Create: `tests/engines/test_anomaly_engine.py`

> ⚠️ **CRITICAL PITFALL:** This is the most trap-heavy module. Read all pitfalls in the header.

- [ ] **Step 1: Write the failing test**

```python
# tests/engines/test_anomaly_engine.py
import pytest
import pandas as pd
import numpy as np
from engines.anomaly_engine import run_anomaly_detection


class TestAnomalyDetection:
    def test_returns_expected_keys(self, dirty_csv_path):
        from ingestion.csv_reader import load_csv
        df = load_csv(dirty_csv_path)
        result = run_anomaly_detection(df)
        assert "outlier_indices" in result
        assert "anomaly_scores" in result
        assert "n_outliers" in result

    def test_detects_outliers_in_dirty_data(self, dirty_csv_path):
        from ingestion.csv_reader import load_csv
        df = load_csv(dirty_csv_path)
        result = run_anomaly_detection(df)
        assert result["n_outliers"] > 0
        assert len(result["outlier_indices"]) == result["n_outliers"]

    def test_clean_data_has_few_outliers(self, clean_csv_path):
        from ingestion.csv_reader import load_csv
        df = load_csv(clean_csv_path)
        result = run_anomaly_detection(df)
        # Clean data should have 0 or very few outliers
        assert result["n_outliers"] <= 2

    def test_no_numeric_columns(self):
        """DataFrame with only text columns should return empty result."""
        df = pd.DataFrame({"name": ["A", "B", "C"], "city": ["X", "Y", "Z"]})
        result = run_anomaly_detection(df)
        assert result["n_outliers"] == 0
        assert result["skipped"] is True

    def test_scores_are_normalized(self, dirty_csv_path):
        from ingestion.csv_reader import load_csv
        df = load_csv(dirty_csv_path)
        result = run_anomaly_detection(df)
        if len(result["anomaly_scores"]) > 0:
            assert all(0 <= s <= 1 for s in result["anomaly_scores"])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/engines/test_anomaly_engine.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/engines/anomaly_engine.py
"""Layer 2: Anomaly detection via PyOD Ensemble (IForest + ECOD + LOF).

Uses Average Score + Threshold combination as recommended by ADBench.
Only runs on numeric columns. Categorical columns are handled by
fg-data-profiling alerts in Layer 1.
"""
import logging
import numpy as np
import pandas as pd
from pyod.models.iforest import IForest
from pyod.models.ecod import ECOD
from pyod.models.lof import LOF

logger = logging.getLogger(__name__)

_CONTAMINATION = 0.05  # assume 5% of data is anomalous


def _normalize_scores(scores: np.ndarray) -> np.ndarray:
    """Normalize scores to [0, 1] range using min-max scaling."""
    s_min, s_max = scores.min(), scores.max()
    if s_max - s_min == 0:
        return np.zeros_like(scores)
    return (scores - s_min) / (s_max - s_min)


def run_anomaly_detection(
    df: pd.DataFrame,
    contamination: float = _CONTAMINATION,
) -> dict:
    """Run PyOD Ensemble on numeric columns of df.

    Args:
        df: Input DataFrame.
        contamination: Expected fraction of outliers (0.0 to 0.5).

    Returns:
        Dict with keys:
        - outlier_indices: list of row indices flagged as outliers
        - anomaly_scores: list of normalized scores for outlier rows only
        - all_scores: list of scores for ALL rows (for diagnostic charts)
        - n_outliers: int count
        - numeric_columns_used: list of column names used
        - skipped: bool (True if no numeric columns found)
    """
    # Select only numeric columns
    numeric_df = df.select_dtypes(include="number")

    if numeric_df.shape[1] == 0:
        logger.warning("No numeric columns found. Skipping anomaly detection.")
        return {
            "outlier_indices": [],
            "anomaly_scores": [],
            "all_scores": [],
            "n_outliers": 0,
            "numeric_columns_used": [],
            "skipped": True,
        }

    # Drop constant columns (ECOD will crash on zero-variance)
    non_constant = numeric_df.loc[:, numeric_df.nunique() > 1]
    if non_constant.shape[1] == 0:
        logger.warning("All numeric columns are constant. Skipping.")
        return {
            "outlier_indices": [], "anomaly_scores": [], "all_scores": [],
            "n_outliers": 0, "numeric_columns_used": [], "skipped": True,
        }

    # Drop rows with NaN (PyOD cannot handle NaN)
    clean_df = non_constant.dropna()
    clean_indices = clean_df.index.tolist()
    X = clean_df.values

    if len(X) < 3:
        logger.warning("Too few rows (%d) for anomaly detection.", len(X))
        return {
            "outlier_indices": [], "anomaly_scores": [], "all_scores": [],
            "n_outliers": 0, "numeric_columns_used": list(non_constant.columns),
            "skipped": True,
        }

    n_samples = len(X)
    # LOF pitfall: n_neighbors must be < n_samples
    lof_neighbors = min(20, n_samples - 1)

    logger.info("Running Ensemble on %d rows x %d numeric cols.", n_samples, X.shape[1])

    # Run 3 detectors
    models = [
        ("IForest", IForest(contamination=contamination, random_state=42)),
        ("ECOD", ECOD(contamination=contamination)),
        ("LOF", LOF(n_neighbors=lof_neighbors, contamination=contamination)),
    ]

    all_scores = []
    for name, model in models:
        try:
            model.fit(X)
            scores = _normalize_scores(model.decision_scores_)
            all_scores.append(scores)
            logger.info("%s completed. Max score: %.3f", name, scores.max())
        except Exception as e:
            logger.warning("%s failed: %s. Skipping this detector.", name, e)

    if len(all_scores) == 0:
        return {
            "outlier_indices": [], "anomaly_scores": [], "all_scores": [],
            "n_outliers": 0, "numeric_columns_used": list(non_constant.columns),
            "skipped": True,
        }

    # Average Score combination (ADBench recommended)
    avg_scores = np.mean(all_scores, axis=0)

    # Threshold: use contamination percentile
    threshold = np.percentile(avg_scores, 100 * (1 - contamination))
    outlier_mask = avg_scores >= threshold

    outlier_positions = np.where(outlier_mask)[0]
    # Map back to original DataFrame indices
    outlier_original_indices = [clean_indices[i] for i in outlier_positions]
    outlier_scores = [round(float(avg_scores[i]), 4) for i in outlier_positions]

    # Sort by score descending
    sorted_pairs = sorted(zip(outlier_original_indices, outlier_scores), key=lambda x: -x[1])
    sorted_indices = [p[0] for p in sorted_pairs]
    sorted_scores = [p[1] for p in sorted_pairs]

    return {
        "outlier_indices": sorted_indices,
        "anomaly_scores": sorted_scores,
        "all_scores": [round(float(s), 4) for s in avg_scores],
        "n_outliers": len(sorted_indices),
        "numeric_columns_used": list(non_constant.columns),
        "skipped": False,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/engines/test_anomaly_engine.py -v`
Expected: ALL PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/engines/anomaly_engine.py tests/engines/test_anomaly_engine.py
git commit -m "feat: PyOD Ensemble anomaly engine with Average Score combination"
```

---

### Task 7: Findings Builder (Layer 3 — Merge L1 + L2 → JSON)

**Files:**
- Create: `src/ontology/findings_builder.py`
- Create: `tests/ontology/test_findings_builder.py`

> ⚠️ **Pitfall:** fg-data-profiling JSON keys vary by column type. Numeric columns have `mean`, `std`, etc. Categorical have `word_counts`, `character_counts`. Must handle both gracefully.

- [ ] **Step 1: Write the failing test**

```python
# tests/ontology/test_findings_builder.py
import pytest
import pandas as pd
from ontology.findings_builder import build_data_quality_findings
from ontology.models import DataQualityFindings


class TestBuildDataQualityFindings:
    def test_end_to_end(self, dirty_csv_path):
        """Full pipeline: load → profile → detect anomalies → build findings."""
        from ingestion.csv_reader import load_csv
        from engines.profiling_engine import run_profiling
        from engines.anomaly_engine import run_anomaly_detection

        df = load_csv(dirty_csv_path)
        profile_result = run_profiling(df)
        anomaly_result = run_anomaly_detection(df)

        findings = build_data_quality_findings(
            file_name="dirty_with_outliers.csv",
            df=df,
            profile_result=profile_result,
            anomaly_result=anomaly_result,
        )

        # Type check
        assert isinstance(findings, DataQualityFindings)

        # Dataset meta
        assert findings.dataset_meta.file_name == "dirty_with_outliers.csv"
        assert findings.dataset_meta.n == 14

        # Columns
        assert len(findings.columns) > 0
        assert "age" in findings.columns or "Age" in findings.columns

        # Must be serializable to JSON
        json_str = findings.model_dump_json(indent=2)
        assert len(json_str) > 100

    def test_clean_data_no_anomalies(self, clean_csv_path):
        from ingestion.csv_reader import load_csv
        from engines.profiling_engine import run_profiling
        from engines.anomaly_engine import run_anomaly_detection

        df = load_csv(clean_csv_path)
        profile_result = run_profiling(df)
        anomaly_result = run_anomaly_detection(df)

        findings = build_data_quality_findings(
            file_name="clean_10rows.csv",
            df=df,
            profile_result=profile_result,
            anomaly_result=anomaly_result,
        )
        # Should have 0 or very few anomaly records
        total_affected = sum(a.affected_count for a in findings.anomalies)
        assert total_affected <= 2
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ontology/test_findings_builder.py -v`
Expected: FAIL with `ModuleNotFoundError`

- [ ] **Step 3: Write minimal implementation**

```python
# src/ontology/findings_builder.py
"""Layer 3: Merges raw outputs from profiling (L1) and anomaly detection (L2)
into validated Pydantic DataQualityFindings objects.
"""
import logging
import pandas as pd
from typing import Dict, Any
from ontology.models import (
    DatasetMeta, ColumnStats, AnomalyRecord, DataQualityFindings,
)

logger = logging.getLogger(__name__)


def _extract_column_stats(variables: Dict[str, Any]) -> Dict[str, ColumnStats]:
    """Convert fg-data-profiling 'variables' dict into ColumnStats map."""
    columns = {}
    for col_name, col_data in variables.items():
        col_type = col_data.get("type", "Unknown")

        # Map fg-data-profiling types to our simplified types
        type_map = {"Numeric": "Numeric", "Categorical": "Categorical",
                     "Boolean": "Boolean", "DateTime": "DateTime",
                     "Unsupported": "Unsupported"}
        simple_type = type_map.get(col_type, "Unknown")

        n_missing = col_data.get("n_missing", 0)
        p_missing = col_data.get("p_missing", 0.0)
        n_distinct = col_data.get("n_distinct", None)

        # Collect extra metrics based on column type
        extra = {}
        if simple_type == "Numeric":
            for key in ["mean", "std", "min", "max", "median", "skewness", "kurtosis"]:
                if key in col_data:
                    extra[key] = round(col_data[key], 4) if isinstance(col_data[key], float) else col_data[key]
        elif simple_type == "Categorical":
            if "imbalance" in col_data:
                extra["imbalance"] = round(col_data["imbalance"], 4)

        columns[col_name] = ColumnStats(
            type=simple_type,
            n_missing=int(n_missing),
            p_missing=float(p_missing),
            n_distinct=int(n_distinct) if n_distinct is not None else None,
            additional_metrics=extra,
        )
    return columns


def build_data_quality_findings(
    file_name: str,
    df: pd.DataFrame,
    profile_result: dict,
    anomaly_result: dict,
) -> DataQualityFindings:
    """Merge profiling + anomaly outputs into a validated DataQualityFindings.

    Args:
        file_name: Original file name.
        df: The loaded DataFrame (for extracting sample rows).
        profile_result: Raw dict from profiling_engine.run_profiling().
        anomaly_result: Raw dict from anomaly_engine.run_anomaly_detection().

    Returns:
        A validated DataQualityFindings Pydantic model.
    """
    table = profile_result.get("table", {})

    # Build dataset meta
    meta = DatasetMeta(
        file_name=file_name,
        n=int(table.get("n", len(df))),
        n_var=int(table.get("n_var", len(df.columns))),
        memory_size=int(table.get("memory_size", 0)),
        p_cells_missing=float(table.get("p_cells_missing", 0.0)),
        n_duplicates=int(table.get("n_duplicates", 0)),
        p_duplicates=float(table.get("p_duplicates", 0.0)),
    )

    # Build column stats
    columns = _extract_column_stats(profile_result.get("variables", {}))

    # Build anomaly records
    anomalies = []
    if not anomaly_result.get("skipped", True) and anomaly_result.get("n_outliers", 0) > 0:
        outlier_indices = anomaly_result["outlier_indices"]
        outlier_scores = anomaly_result["anomaly_scores"]
        n_outliers = anomaly_result["n_outliers"]

        # Top 10 samples
        top_k = min(10, n_outliers)
        top_indices = outlier_indices[:top_k]
        top_scores = outlier_scores[:top_k]

        top_samples = []
        for idx, score in zip(top_indices, top_scores):
            row = df.iloc[idx].to_dict()
            row["_anomaly_score"] = score
            row["_row_index"] = int(idx)
            top_samples.append(row)

        anomalies.append(AnomalyRecord(
            issue_type="OUTLIER_ENSEMBLE",
            description=f"Phát hiện {n_outliers} dòng dị biệt ({n_outliers/meta.n*100:.1f}% data)",
            severity="HIGH" if n_outliers / meta.n > 0.05 else "MEDIUM",
            affected_count=n_outliers,
            affected_percent=round(n_outliers / meta.n, 4),
            top_10_samples=top_samples,
        ))

    # Build duplicate record (from profiling)
    if meta.n_duplicates > 0:
        dup_df = df[df.duplicated(keep=False)]
        dup_samples = dup_df.head(10).to_dict(orient="records")
        anomalies.append(AnomalyRecord(
            issue_type="DUPLICATE",
            description=f"Phát hiện {meta.n_duplicates} dòng trùng lặp hoàn toàn ({meta.p_duplicates*100:.1f}% data)",
            severity="MEDIUM" if meta.p_duplicates < 0.05 else "HIGH",
            affected_count=meta.n_duplicates,
            affected_percent=meta.p_duplicates,
            top_10_samples=dup_samples,
        ))

    return DataQualityFindings(
        dataset_meta=meta,
        columns=columns,
        anomalies=anomalies,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ontology/test_findings_builder.py -v`
Expected: ALL PASS (2 tests). May take 20-30s total due to profiling.

- [ ] **Step 5: Run ALL tests**

Run: `pytest tests/ -v`
Expected: ALL PASS (22 tests total)

- [ ] **Step 6: Commit**

```bash
git add src/ontology/findings_builder.py tests/ontology/test_findings_builder.py
git commit -m "feat: findings builder merging profiling + anomaly into validated JSON"
```

---

### Task 8: Integration Test — Full Pipeline

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write the integration test**

```python
# tests/test_integration.py
"""End-to-end integration test: CSV → Profile → Anomaly → JSON output."""
import pytest
import json
from pathlib import Path
from ingestion.csv_reader import load_csv
from engines.profiling_engine import run_profiling
from engines.anomaly_engine import run_anomaly_detection
from ontology.findings_builder import build_data_quality_findings
from ontology.models import DataQualityFindings


class TestFullPipeline:
    def test_dirty_csv_produces_valid_json(self, dirty_csv_path, tmp_path):
        # Step 1: Ingestion
        df = load_csv(dirty_csv_path)
        assert len(df) == 14

        # Step 2: Layer 1 — Profiling
        profile = run_profiling(df)
        assert "table" in profile

        # Step 3: Layer 2 — Anomaly Detection
        anomalies = run_anomaly_detection(df)
        assert anomalies["n_outliers"] >= 0

        # Step 4: Layer 3 — Build Findings
        findings = build_data_quality_findings(
            file_name="dirty_with_outliers.csv",
            df=df,
            profile_result=profile,
            anomaly_result=anomalies,
        )

        # Step 5: Export to JSON file
        output_path = tmp_path / "data_quality_findings.json"
        output_path.write_text(findings.model_dump_json(indent=2), encoding="utf-8")

        # Step 6: Verify file is valid JSON and re-parseable
        with open(output_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        restored = DataQualityFindings.model_validate(raw)
        assert restored.dataset_meta.n == 14
        assert len(restored.anomalies) >= 1  # at least outliers or duplicates
```

- [ ] **Step 2: Run integration test**

Run: `pytest tests/test_integration.py -v`
Expected: PASS

- [ ] **Step 3: Run FULL test suite**

Run: `pytest tests/ -v --tb=short`
Expected: ALL PASS (23 tests total)

- [ ] **Step 4: Commit & Push**

```bash
git add tests/test_integration.py
git commit -m "test: end-to-end integration test for deterministic core pipeline"
git push
```
