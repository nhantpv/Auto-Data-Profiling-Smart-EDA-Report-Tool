# Member B Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining gaps between the current Member-B code and `docs/ARCHITECT (8).md` + `docs/tasks/task_member_B.md`: L3b Phase-2 aggregate-before-join, L4 per-agent retry, real Appendix rendering, guardrail numeric tolerance, ydata handoff to Member C, and a safe `--multi` CLI parser.

**Architecture:** All changes stay inside the six files Member B owns (`src/reporting/dispatcher.py`, `src/reporting/html_merger.py`, `src/reporting/l4_report.py`, `src/guardrail/narrative.py`, `src/engines/cross_table_engine.py`, `run_pipeline.py`) plus their tests. The SSOT rule applies: where existing code deviates from ARCHITECT v5.4 (row-aligned Pearson in L3b Phase 2), the code is changed to match the doc, and the test that froze the deviation is updated.

**Tech Stack:** Python 3.12, pandas, pydantic v2, pytest. No new dependencies (spearman via `pandas.DataFrame.corr`, no phik).

---

### Context for a zero-context engineer

- Run tests with `.venv/bin/python -m pytest -q` from the repo root. `pythonpath = ["src"]` is set in `pyproject.toml`, so tests import `engines.…`, `reporting.…` directly.
- `src/ontology/models.py` is **locked** — never edit it. `CrossTableCorrelation` has fields `left_feature, right_feature, left_table, right_table, method, coefficient, abs_coefficient, n` only.
- LLM calls are gated by env vars and default OFF (`SMART_EDA_L4_PROVIDER` / `SMART_EDA_L3B_PROVIDER` must equal `"openai"`). All tests run in deterministic mode.
- ARCHITECT §5.7 Phase 2 (normative): aggregate child column to parent grain via the FK, JOIN on the relationship key, correlate on the aggregated frame, `N` = parent rows, skip `N < 30` (TOO_FEW_UNITS) and skip when both-null overlap > 0.70 (P4).
- ARCHITECT §5.9(f): per-agent guardrail retry ≤ 3, then deterministic fallback. §5.9(d): Appendix = Python-rendered table of all findings outside the Top-5 clusters plus all INFO findings, so 100% of findings appear in the report.
- ARCHITECT §10 L4 Guardrail Tolerance: integer = exact, decimal = ±0.0001, relative (percent) = ±0.1%, year 1900–2100 = pass-through.

### Task 0: Sync venv with pyproject (env only, no code)

**Files:** none (environment).

- [ ] **Step 0.1:** `.venv/bin/pip install simple-ddl-parser fastapi httpx "python-multipart>=0.0.9" "uvicorn[standard]"` (all already declared in `pyproject.toml`).
- [ ] **Step 0.2:** `.venv/bin/python -m pytest -q tests/ingestion/test_schema_reader.py tests/webapp -q` → previously-erroring collections now run.

### Task 1: L3b Phase 2 — aggregate-before-join (ARCHITECT §5.7)

**Files:**
- Modify: `src/engines/cross_table_engine.py` (`compute_planned_correlations`, its call in `run_cross_table_analysis`, `_call_openai_plan` temperature, planner prompt sample rows)
- Test: `tests/engines/test_cross_table_llm_plan.py`

- [ ] **Step 1.1: Replace the row-aligned test with aggregate-before-join tests (RED).** The old test froze the row-aligned deviation; rewrite `test_compute_planned_correlations_returns_numeric_pairs` so users has 40 rows (`id` 1..40, `age` = id), orders has 80 rows (2 per user, `amount` = 2×user_id ± 0), pair = `users.age` ↔ `mean(orders.amount)`, expect one record with `method == "spearman_agg_mean"`, `coefficient == 1.0`, `n == 40`. Add `test_compute_planned_correlations_skips_too_few_units` (10 parent rows → no records) and `test_compute_planned_correlations_skips_high_null_overlap` (≥80% of parent rows have both sides null → no records).
- [ ] **Step 1.2:** Run `.venv/bin/python -m pytest tests/engines/test_cross_table_llm_plan.py -q` → new tests FAIL against the old implementation.
- [ ] **Step 1.3: Implement.** New signature `compute_planned_correlations(tables, plan, relationships, limit=25)`:
  1. find `rel` where `rel.parent_table == pair.parent_table and rel.child_table == pair.child_table` (validation already guarantees existence);
  2. `child_agg = child.groupby(rel.child_column)[pair.child_column].agg(pair.aggregate_method)` with numeric coercion;
  3. join onto `parent` via `rel.parent_column`;
  4. drop rows where either side is null; skip when both-null overlap > 0.70 of parent rows; skip when N < 30;
  5. `coefficient = frame.corr(method="spearman")`, `method=f"spearman_agg_{pair.aggregate_method}"`, `n = len(frame)`.
  Update the call inside `run_cross_table_analysis` to pass `schema relationships`.
- [ ] **Step 1.4:** Add `"temperature": 0` to `_call_openai_plan` request body; include up to 10 sample rows per table in the planner prompt when `tables_meta` values are DataFrames (`df.head(10).to_dict("records")`).
- [ ] **Step 1.5:** `.venv/bin/python -m pytest tests/engines -q` → PASS.
- [ ] **Step 1.6:** Commit `fix(L3b): aggregate-before-join for planned correlations per ARCHITECT §5.7`.

### Task 2: Guardrail tolerance + per-agent report field (ARCHITECT §10, Task B3)

**Files:**
- Modify: `src/guardrail/narrative.py`
- Test: `tests/guardrail/test_narrative.py`

- [ ] **Step 2.1: Failing tests.** (a) year pass-through: narrative containing `2024` with empty evidence passes the number check; (b) decimal tolerance: evidence `0.1234`, narrative `0.1234` exact passes and `0.1230` fails, while `0.12341` (±0.0001) passes; (c) percent tolerance: evidence `12.3%`, narrative `12.3%` passes (existing) and `12.31%` fails beyond ±0.1% relative — narrative `12.29%` passes.
- [ ] **Step 2.2:** Run → FAIL.
- [ ] **Step 2.3: Implement `_number_token_allowed(token, numbers) -> bool`** used by both `_report_for_text` and `validate_narrative`: exact normalized match → True; integer in [1900, 2100] → True (year pass-through); percent token → relative compare against evidence percents (strip `%`, pass if `abs(a-b)/max(b,eps) <= 0.001`); decimal token → pass if any evidence number within ±0.0001. Integers (non-year) remain exact-only. Add optional `agents: list[dict]` field (default `[]`) to `GuardrailReport` for per-agent details.
- [ ] **Step 2.4:** Run `tests/guardrail -q` → PASS.
- [ ] **Step 2.5:** Commit `feat(guardrail): numeric tolerance per ARCHITECT §10 + per-agent report field`.

### Task 3: L4 retry ≤3 + real Appendix (ARCHITECT §5.9(d)(f), Task B2)

**Files:**
- Modify: `src/reporting/l4_report.py`
- Test: `tests/reporting/test_l4_multi_agent.py`

- [ ] **Step 3.1: Failing tests.** (a) `test_appendix_lists_findings_outside_top_clusters`: 6 distinct WARN issue_types + 1 INFO finding → `result.appendix_html` contains the 6th type name and the INFO type name (top_n=5 default); (b) `test_analyst_retries_up_to_three_times_then_falls_back` (monkeypatch `_call_openai_async` to always return a hallucinated number with provider env set to openai): final `AnalystOutput.guardrail_passed` is True (deterministic fallback), `retry_count == 3`, and the patched function was called exactly 3 times; (c) `test_guardrail_report_contains_per_agent_details`: final `GuardrailReport.agents` has one entry per analyst + one for editor.
- [ ] **Step 3.2:** Run → FAIL.
- [ ] **Step 3.3: Implement.**
  - `_run_analyst`: when LLM enabled, loop `for attempt in range(3)`: call LLM, verify with `verify_analyst_output`; break on pass; after 3 failures use deterministic fallback (`retry_count=3`). Deterministic mode unchanged (`retry_count=0`).
  - `_run_editor`: same 3-attempt loop around the LLM call + `verify_editor_output`; strip Markdown code fences from the LLM text before `EditorOutput.model_validate_json`.
  - `_render_appendix_html(dispatch_result, findings, schema)`: build the set of issue types covered by `dispatch_result.top_clusters`; render an HTML `<table>` with one row per finding not covered (all INFO findings + findings of types beyond top-5): columns Severity | Type | Scope | Affected. Always include the section when there is at least one leftover finding.
  - `run_multi_agent_l4`: collect per-agent reports into `result.guardrail_report["agents"]` and set `report.agents` before returning.
- [ ] **Step 3.4:** Run `tests/reporting -q` → PASS.
- [ ] **Step 3.5:** Commit `feat(L4): per-agent retry loop and full appendix rendering`.

### Task 4: Pipeline polish — ydata handoff + `_parse_multi_args` (Task B6)

**Files:**
- Modify: `run_pipeline.py`
- Test: `tests/test_run_pipeline.py` (rewrite the stale untracked file to the current `--schema` CLI)

- [ ] **Step 4.1: Rewrite `tests/test_run_pipeline.py`.** The untracked file tests a retired `--dbml`-required CLI that contradicts ARCHITECT L2b.5 (schema optional, Quick Mode infers). Keep its intent (no IndexError on dangling flags, no silently-dropped tokens) but target the real interface: `_parse_multi_args(args) -> (data_paths, out_dir, schema, confirmed_schema, fact_table)` — cases: basic two CSVs no flags; `--schema`/`--out`/`--confirmed-schema`/`--fact-table` in any position; dangling flag → ValueError; fewer than 2 data paths → ValueError; unknown `--flag` → ValueError. Plus `test_run_multi_schema_optional`: `inspect.signature(run_pipeline.run_multi).parameters["schema_path"].default is None`.
- [ ] **Step 4.2:** Run → FAIL (`_parse_multi_args` undefined).
- [ ] **Step 4.3: Implement `_parse_multi_args`** in `run_pipeline.py` replacing the inline `__main__` parsing: walk tokens left→right; known flags consume one value (ValueError if absent); tokens starting with `--` otherwise → ValueError; everything else is a data path; require ≥2 data paths. `__main__` calls it.
- [ ] **Step 4.4: ydata handoff.** `_safe_ydata_html` first tries `from engines.profiling_engine import run_profiling_html` and returns `run_profiling_html(df, minimal=minimal)`; on `ImportError/AttributeError` falls back to current direct `ProfileReport` call; keep the existing exception-to-HTML fallback.
- [ ] **Step 4.5:** Run `tests/test_run_pipeline.py -q` → PASS.
- [ ] **Step 4.6:** Commit `feat(pipeline): safe --multi arg parser + run_profiling_html handoff`.

### Task 5: End-to-end verification (verification-before-completion)

- [ ] **Step 5.1:** `.venv/bin/python -m pytest -q` → full suite green (webapp + schema_reader now collect after Task 0).
- [ ] **Step 5.2:** Single-table run: `.venv/bin/python run_pipeline.py tests/fixtures/dirty_with_outliers.csv output_test_b` → verify `smart_eda_report.html` exists, contains `tab-ai` and `tab-stats`, `l4_report.md` non-empty, `guardrail_report.json` has `"status": "passed"` and non-empty `agents`.
- [ ] **Step 5.3:** Multi-table run: `.venv/bin/python run_pipeline.py --multi tests/fixtures/multi/users.csv tests/fixtures/multi/orders.csv --schema tests/fixtures/multi/shop.dbml --out output_test_b_multi` → verify `cross_table_analysis.json`, `schema_gate.json`, `relationship_graph.json`, `smart_eda_report.html` exist; `dataset_verdict.json` verdict is one of READY/WARN/NOT_READY.
- [ ] **Step 5.4:** Commit any remaining changes `feat(member-B): complete L4 + L3b integration per task_member_B`.

### Self-review notes

- Spec coverage: B1 dispatcher (done previously, tests pass), B2 (Task 3), B3 (Task 2), B4 (Task 1), B5 merger (done previously, tests pass), B6 (Task 4 + Task 5 e2e). Locked files untouched. A/C files untouched.
- The only contract change: `compute_planned_correlations` gains a required `relationships` argument — its single call site (`run_cross_table_analysis`) and single test are updated in the same task.
- `GuardrailReport.agents` defaults to `[]` → backward compatible with `artifact_contract.py` (reads only `status`).
