"""End-to-end integration test: CSV → Profile → Anomaly → JSON output."""
# pyrefly: ignore [missing-import]
import pytest
import json
from pathlib import Path
from ingestion.csv_reader import load_csv
from engines.profiling_engine import run_profiling
from engines.anomaly_engine import run_anomaly_detection
from engines.visualizer import attach_diagnostic_charts
from engines.schema_engine import build_schema_findings, validate_schema_multi
from ontology.findings_builder import build_data_quality_findings
from ontology.models import DataQualityFindings, DatasetVerdict, SchemaEvaluationFindings, Verdict
from severity.calibrator import calibrate_columns, load_calibrator_table
from severity.compound import apply_compound
from severity.aggregator import aggregate

FIXTURES = Path(__file__).parent / "fixtures"


class TestFullPipeline:
    def test_dirty_csv_produces_valid_json(self, realistic_outliers_path, tmp_path):
        # Step 1: Ingestion
        df = load_csv(realistic_outliers_path)
        assert len(df) == 32

        # Step 2: Layer 1 — Profiling
        profile = run_profiling(df)
        assert "table" in profile

        # Step 3: Layer 2 — Anomaly Detection
        anomalies = run_anomaly_detection(df)
        assert anomalies["n_outliers"] >= 0

        # Step 4: Layer 3 — Build Findings
        findings = build_data_quality_findings(
            file_name="outliers_realistic.csv",
            df=df,
            profile_result=profile,
            anomaly_result=anomalies,
        )

        # Step 5: Layer 3.5 — Attach diagnostic charts (PATCH 5c)
        findings = attach_diagnostic_charts(
            findings, df, anomalies, out_dir=str(tmp_path / "charts")
        )
        # If outliers detected, every OUTLIER_ENSEMBLE record must have diagnostic_chart set
        outlier_recs = [a for a in findings.anomalies if a.issue_type == "OUTLIER_ENSEMBLE"]
        for r in outlier_recs:
            assert r.diagnostic_chart is not None
            assert Path(r.diagnostic_chart).exists()

        # Step 6: Export to JSON
        output_path = tmp_path / "data_quality_findings.json"
        output_path.write_text(findings.model_dump_json(indent=2), encoding="utf-8")

        # Step 7: Verify round-trip
        with open(output_path, "r", encoding="utf-8") as f:
            raw = json.load(f)

        restored = DataQualityFindings.model_validate(raw)
        assert restored.dataset_meta.n == 32
        assert len(restored.anomalies) >= 1  # at least outliers or duplicates

    def test_severity_pipeline_produces_verdict_json(self, realistic_outliers_path, tmp_path):
        df = load_csv(realistic_outliers_path)
        profile = run_profiling(df)
        anomalies = run_anomaly_detection(df)
        findings = build_data_quality_findings(
            file_name="outliers_realistic.csv",
            df=df,
            profile_result=profile,
            anomaly_result=anomalies,
        )

        # Layer 2.5 — severity stack
        table = load_calibrator_table()
        col_findings = calibrate_columns(findings.columns, table, n=findings.dataset_meta.n)
        all_dq = apply_compound(findings.anomalies + col_findings)
        verdict = aggregate(findings.dataset_meta, all_dq)

        # Emit both output files
        dq_path = tmp_path / "data_quality_findings.json"
        verdict_path = tmp_path / "dataset_verdict.json"
        dq_path.write_text(findings.model_dump_json(indent=2), encoding="utf-8")
        verdict_path.write_text(verdict.model_dump_json(indent=2), encoding="utf-8")

        # Both files exist and are valid JSON
        assert dq_path.exists()
        assert verdict_path.exists()

        restored = DatasetVerdict.model_validate_json(verdict_path.read_text())
        assert restored.verdict in (Verdict.READY, Verdict.WARN, Verdict.NOT_READY)
        assert restored.summary.total_issues >= 0
        # Sanity: realistic fixture has no catastrophic missing → expect READY or WARN
        # (3b note: MAR escalation on small-missing cols yields WARN tier → verdict stays READY)
        assert restored.verdict != Verdict.NOT_READY


class TestSchemaIntegration:
    def test_schema_bad_produces_not_ready_and_three_files(self, tmp_path):
        csv_path = str(FIXTURES / "schema_bad.csv")
        schema_path = str(FIXTURES / "schema_bad.dbml")
        df = load_csv(csv_path)

        schema = build_schema_findings(df, csv_path, schema_path)
        error_types = {e.error_type for e in schema.integrity_errors}
        assert "PK_DUPLICATE" in error_types
        assert "TYPE_MISMATCH" in error_types
        assert "UNIQUE_VIOLATION" in error_types
        assert "MISSING_COLUMN" in error_types
        assert "EXTRA_COLUMN" in error_types

        # Verdict must be NOT_READY (has CRITICAL from PK_DUPLICATE + MISSING_COLUMN)
        profile = run_profiling(df)
        anomaly_result = run_anomaly_detection(df)
        findings = build_data_quality_findings(
            file_name="schema_bad.csv", df=df,
            profile_result=profile, anomaly_result=anomaly_result,
        )
        table = load_calibrator_table()
        col_findings = calibrate_columns(findings.columns, table, n=findings.dataset_meta.n)
        all_dq = apply_compound(findings.anomalies + col_findings)
        verdict = aggregate(findings.dataset_meta, all_dq, integrity_errors=schema.integrity_errors)

        assert verdict.verdict == Verdict.NOT_READY
        assert verdict.summary.critical >= 1

        # Three files
        for name, obj in [
            ("data_quality_findings.json", findings),
            ("schema_evaluation_findings.json", schema),
            ("dataset_verdict.json", verdict),
        ]:
            p = tmp_path / name
            p.write_text(obj.model_dump_json(indent=2), encoding="utf-8")
            assert p.exists()

    def test_schema_ok_produces_ready(self, tmp_path):
        csv_path = str(FIXTURES / "schema_ok.csv")
        schema_path = str(FIXTURES / "schema_ok.dbml")
        df = load_csv(csv_path)

        schema = build_schema_findings(df, csv_path, schema_path)
        # No blocking errors on a clean fixture
        critical = [e for e in schema.integrity_errors if e.severity.value == "CRITICAL"]
        assert critical == []

        profile = run_profiling(df)
        anomaly_result = run_anomaly_detection(df)
        findings = build_data_quality_findings(
            file_name="schema_ok.csv", df=df,
            profile_result=profile, anomaly_result=anomaly_result,
        )
        table = load_calibrator_table()
        col_findings = calibrate_columns(findings.columns, table, n=findings.dataset_meta.n)
        all_dq = apply_compound(findings.anomalies + col_findings)
        verdict = aggregate(findings.dataset_meta, all_dq, integrity_errors=schema.integrity_errors)
        assert verdict.verdict == Verdict.READY

    def test_no_schema_produces_two_files_unchanged(self, realistic_outliers_path, tmp_path):
        """Without schema the pipeline must still produce exactly 2 files and not crash."""
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        import importlib
        # pyrefly: ignore [missing-import]
        import run_pipeline
        importlib.reload(run_pipeline)

        result = run_pipeline.run(realistic_outliers_path, str(tmp_path), schema_path=None)
        assert Path(result["dq_path"]).exists()
        assert Path(result["verdict_path"]).exists()
        assert "schema_path" not in result


class TestMultiTableIntegration:
    MULTI = FIXTURES / "multi"

    def test_orphan_fk_detected_not_ready(self):
        schema = str(self.MULTI / "shop.dbml")
        csvs = [str(self.MULTI / "users.csv"), str(self.MULTI / "orders.csv")]
        findings = validate_schema_multi(csvs, schema)

        error_types = {e.error_type for e in findings.integrity_errors}
        assert "ORPHAN_FOREIGN_KEY" in error_types

        orphan = next(e for e in findings.integrity_errors if e.error_type == "ORPHAN_FOREIGN_KEY")
        assert orphan.affected_count == 1
        assert orphan.affected_column == "user_id"
        assert any(s.get("user_id") == 9999 for s in orphan.top_10_samples)

        # Verdict must be NOT_READY
        from severity.aggregator import aggregate
        from ontology.models import DatasetMeta
        meta = DatasetMeta(file_name="shop", n=7, n_var=5, memory_size=0, p_cells_missing=0.0)
        verdict = aggregate(meta, [], integrity_errors=findings.integrity_errors)
        assert verdict.verdict == Verdict.NOT_READY

    def test_null_fk_not_counted_as_orphan(self):
        schema = str(self.MULTI / "shop.dbml")
        csvs = [str(self.MULTI / "users.csv"), str(self.MULTI / "orders.csv")]
        findings = validate_schema_multi(csvs, schema)
        orphans = [e for e in findings.integrity_errors if e.error_type == "ORPHAN_FOREIGN_KEY"]
        # orders row 104 (user_id=null) must NOT be counted
        assert orphans[0].affected_count == 1

    def test_clean_orders_no_orphan(self):
        schema = str(self.MULTI / "shop.dbml")
        csvs = [str(self.MULTI / "users.csv"), str(self.MULTI / "orders_clean.csv")]
        findings = validate_schema_multi(csvs, schema)
        orphans = [e for e in findings.integrity_errors if e.error_type == "ORPHAN_FOREIGN_KEY"]
        assert orphans == []

    def test_schema_meta_covers_all_tables(self):
        schema = str(self.MULTI / "shop.dbml")
        csvs = [str(self.MULTI / "users.csv"), str(self.MULTI / "orders.csv")]
        findings = validate_schema_multi(csvs, schema)
        assert findings.schema_meta.total_tables == 2
        assert findings.schema_meta.total_relationships == 1
        table_names = {t.name for t in findings.tables}
        assert "users" in table_names
        assert "orders" in table_names

    def test_pipeline_multi_csv_produces_three_files(self, tmp_path):
        import sys
        sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
        import importlib
        # pyrefly: ignore [missing-import]
        import run_pipeline
        importlib.reload(run_pipeline)

        csvs = [str(self.MULTI / "users.csv"), str(self.MULTI / "orders.csv")]
        schema = str(self.MULTI / "shop.dbml")
        result = run_pipeline.run_multi(csvs, str(tmp_path), schema)

        assert Path(result["schema_path"]).exists()
        assert Path(result["verdict_path"]).exists()

        import json
        v = json.loads(Path(result["verdict_path"]).read_text())
        assert v["verdict"] == "NOT_READY"
