import json
from pathlib import Path
from ontology.models import AnomalyRecord, ColumnStats, Severity, SEVERITY_ORDER

_TABLE_PATH = Path(__file__).parent.parent.parent / "config" / "calibrator_table.json"


def load_calibrator_table() -> dict:
    with open(_TABLE_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _missingness_severity(p_missing: float, thresholds: list) -> Severity:
    for entry in thresholds:
        if p_missing < entry["max"]:
            return Severity(entry["severity"])
    return Severity.CRITICAL


def calibrate_columns(
    columns: dict,
    table: dict,
    n: int,
) -> list:
    findings = []
    completeness_cfg = table["completeness"]
    constant_cfg = table["constant_column"]
    hc_cfg = table["high_cardinality"]
    imbalance_cfg = table["severe_imbalance"]

    for col_name, stats in columns.items():
        # Completeness
        if stats.p_missing > 0:
            sev = _missingness_severity(stats.p_missing, completeness_cfg["thresholds"])
            # Escalate by 1 tier for non-random missing (MAR/MNAR? are more dangerous than MCAR)
            if stats.missingness_mechanism in ("MAR", "MNAR?"):
                idx = SEVERITY_ORDER.index(sev)
                sev = SEVERITY_ORDER[min(idx + 1, len(SEVERITY_ORDER) - 1)]
            findings.append(AnomalyRecord(
                issue_type="MISSINGNESS",
                description=f"Column '{col_name}' has {stats.p_missing:.1%} missing values",
                severity=sev,
                dq_dimensions=[completeness_cfg["dq_dimension"]],
                affected_count=stats.n_missing,
                affected_percent=stats.p_missing,
                affected_column=col_name,
                top_10_samples=[],
            ))

        # Constant column
        n_distinct = stats.n_distinct if stats.n_distinct is not None else 0
        if n_distinct <= 1:
            findings.append(AnomalyRecord(
                issue_type="CONSTANT_COLUMN",
                description=f"Column '{col_name}' has ≤1 distinct value",
                severity=Severity(constant_cfg["severity"]),
                dq_dimensions=[constant_cfg["dq_dimension"]],
                affected_count=n,
                affected_percent=1.0,
                affected_column=col_name,
                top_10_samples=[],
            ))

        if stats.type == "Categorical":
            # High cardinality: p_distinct = n_distinct / n
            p_distinct = n_distinct / n if n > 0 else 0.0
            if p_distinct > 0.9:
                findings.append(AnomalyRecord(
                    issue_type="HIGH_CARDINALITY",
                    description=f"Column '{col_name}' has high cardinality (p_distinct={p_distinct:.2f})",
                    severity=Severity(hc_cfg["severity"]),
                    dq_dimensions=[hc_cfg["dq_dimension"]],
                    affected_count=n_distinct,
                    affected_percent=p_distinct,
                    affected_column=col_name,
                    top_10_samples=[],
                ))

            # Severe imbalance
            imbalance = stats.additional_metrics.get("imbalance")
            if imbalance is not None and imbalance > 0.95:
                findings.append(AnomalyRecord(
                    issue_type="IMBALANCE",
                    description=f"Column '{col_name}' is severely imbalanced (imbalance={imbalance:.3f})",
                    severity=Severity(imbalance_cfg["severity"]),
                    dq_dimensions=[imbalance_cfg["dq_dimension"]],
                    affected_count=n,
                    affected_percent=imbalance,
                    affected_column=col_name,
                    top_10_samples=[],
                ))

    return findings
