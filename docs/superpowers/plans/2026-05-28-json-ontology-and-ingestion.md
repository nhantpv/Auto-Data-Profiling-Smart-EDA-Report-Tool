# JSON Ontology & Data Ingestion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the strict Pydantic JSON schemas (Layer 3) and the smart CSV data ingestion module with auto-sampling (Layer 1).

**Architecture:** We use strict Pydantic models with `extra="allow"` mechanisms to define the API contract between Python engines and LLM agents. The ingestion module will use `pandas` to read data, automatically sampling down to 500k rows if the dataset exceeds memory constraints to prevent OOM errors.

**Tech Stack:** Python 3, Pydantic, Pandas, Pytest.

---

### Task 1: Initialize Project Structure & Base Ontology Models

**Files:**
- Create: `src/ontology/models.py`
- Create: `tests/ontology/test_models.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/ontology/test_models.py
import pytest
from src.ontology.models import ColumnStats, DatasetMeta, DataQualityFindings

def test_data_quality_findings_validation():
    # Test strict validation and flexible additional_metrics
    payload = {
        "dataset_meta": {
            "file_name": "test.csv",
            "n": 1000,
            "n_var": 5,
            "memory_size": 1024,
            "p_cells_missing": 0.05,
            "overview_charts": {"heatmap": "path/to/img.png"}
        },
        "columns": {
            "age": {
                "type": "Numeric",
                "n_missing": 0,
                "p_missing": 0.0,
                "n_zeros": 0,
                "additional_metrics": {"mean": 25.5, "max": 80}
            }
        },
        "anomalies": []
    }
    
    findings = DataQualityFindings(**payload)
    assert findings.dataset_meta.n == 1000
    assert findings.columns["age"].additional_metrics["mean"] == 25.5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ontology/test_models.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src'"

- [ ] **Step 3: Write minimal implementation**

```python
# src/ontology/models.py
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional

class DatasetMeta(BaseModel):
    file_name: str
    n: int
    n_var: int
    memory_size: int
    p_cells_missing: float
    overview_charts: Dict[str, str] = Field(default_factory=dict)

class ColumnStats(BaseModel):
    type: str
    n_missing: int
    p_missing: float
    n_zeros: int
    additional_metrics: Dict[str, Any] = Field(default_factory=dict)

class AnomalyRecord(BaseModel):
    issue_type: str
    description: str
    severity: str
    top_10_samples: List[Dict[str, Any]]
    diagnostic_chart: Optional[str] = None
    full_anomalies_export_path: Optional[str] = None

class DataQualityFindings(BaseModel):
    dataset_meta: DatasetMeta
    columns: Dict[str, ColumnStats]
    anomalies: List[AnomalyRecord] = Field(default_factory=list)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ontology/test_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/ontology/test_models.py src/ontology/models.py
git commit -m "feat: implement pydantic ontology for data quality findings"
```

---

### Task 2: Implement CSV Reader with Smart Sampling

**Files:**
- Create: `src/ingestion/csv_reader.py`
- Create: `tests/ingestion/test_csv_reader.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/ingestion/test_csv_reader.py
import pytest
import pandas as pd
import numpy as np
import os
from src.ingestion.csv_reader import load_and_sample_csv

def test_load_and_sample_csv(tmp_path):
    # Create a dummy CSV with 100 rows
    df = pd.DataFrame({'id': range(100), 'val': np.random.randn(100)})
    csv_path = tmp_path / "test_data.csv"
    df.to_csv(csv_path, index=False)
    
    # Test reading without sampling (threshold = 200)
    loaded_df = load_and_sample_csv(str(csv_path), sample_threshold=200)
    assert len(loaded_df) == 100
    
    # Test reading with sampling (threshold = 50)
    sampled_df = load_and_sample_csv(str(csv_path), sample_threshold=50)
    assert len(sampled_df) == 50
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/ingestion/test_csv_reader.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'src.ingestion'"

- [ ] **Step 3: Write minimal implementation**

```python
# src/ingestion/csv_reader.py
import pandas as pd
import os

def load_and_sample_csv(file_path: str, sample_threshold: int = 500000) -> pd.DataFrame:
    """
    Loads a CSV file. If it has more rows than sample_threshold, 
    it randomly samples down to the threshold to prevent OOM.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
        
    df = pd.read_csv(file_path)
    
    if len(df) > sample_threshold:
        print(f"Dataset too large ({len(df)} rows). Sampling down to {sample_threshold} rows.")
        df = df.sample(n=sample_threshold, random_state=42).reset_index(drop=True)
        
    return df
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/ingestion/test_csv_reader.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/ingestion/test_csv_reader.py src/ingestion/csv_reader.py
git commit -m "feat: implement csv reader with smart sampling strategy"
```
