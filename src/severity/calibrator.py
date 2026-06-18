"""Column-level calibrator — threshold-driven findings from profiling stats.

Generates AnomalyRecords for: missingness, constant columns, high cardinality,
and severe imbalance.  All records include provenance, threshold_ref, and
finding_id metadata (ARCHITECT v5.4 §L3).

QĐ-6a: "MNAR?" retired.  Only MAR escalates missingness severity.
"""
import json
from pathlib import Path
from config.threshold_registry import ThresholdRegistry
from ontology.models import AnomalyRecord, ColumnStats, Provenance, Severity, SEVERITY_ORDER
from ontology.finding_registry import FindingRegistry

_TABLE_PATH = Path(__file__).parent.parent.parent / "config" / "calibrator_table.json"
_THRESHOLDS = ThresholdRegistry()


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
    df: "pd.DataFrame | None" = None,
) -> list[AnomalyRecord]:
    """Generate threshold-driven findings from column stats.

    All findings are registered in a FindingRegistry for dedup and ID assignment.

    Args:
        columns: Dict of column_name -> ColumnStats
        table: Calibrator config (from calibrator_table.json)
        n: Total row count
        df: Optional DataFrame for format consistency checks (needs actual data)

    Returns:
        List of AnomalyRecords with finding_id, provenance, and threshold_ref.
    """
    registry = FindingRegistry()
    completeness_cfg = table["completeness"]
    constant_cfg = table["constant_column"]
    hc_cfg = table["high_cardinality"]
    imbalance_cfg = table["severe_imbalance"]

    for col_name, stats in columns.items():
        # Completeness
        if stats.p_missing > 0:
            sev = _missingness_severity(stats.p_missing, completeness_cfg["thresholds"])
            mech = stats.missingness_mechanism
            # MAR: escalate by 1 tier (predictable missing is more dangerous than MCAR).
            # QĐ-6a: "MNAR?" retired — only MAR escalates.
            # STRUCTURAL_ABSENT: de-escalate by 1 tier — NULL means "not applicable"
            #   for optional fields (e.g. Fax, Company); not a real data quality problem.
            if mech == "MAR":
                idx = SEVERITY_ORDER.index(sev)
                sev = SEVERITY_ORDER[min(idx + 1, len(SEVERITY_ORDER) - 1)]
            elif mech == "STRUCTURAL_ABSENT":
                idx = SEVERITY_ORDER.index(sev)
                sev = SEVERITY_ORDER[max(idx - 1, 0)]
            registry.register_anomaly(AnomalyRecord(
                issue_type="MISSINGNESS",
                description=f"Column '{col_name}' has {stats.p_missing:.1%} missing values",
                severity=sev,
                dq_dimensions=[completeness_cfg["dq_dimension"]],
                provenance=Provenance.OBSERVED,
                threshold_ref="completeness",
                affected_count=stats.n_missing,
                affected_percent=stats.p_missing,
                affected_column=col_name,
                top_10_samples=[],
            ))

        # Constant column
        n_distinct = stats.n_distinct if stats.n_distinct is not None else 0
        if n_distinct <= 1:
            registry.register_anomaly(AnomalyRecord(
                issue_type="CONSTANT_COLUMN",
                description=f"Column '{col_name}' has \u22641 distinct value",
                severity=Severity(constant_cfg["severity"]),
                dq_dimensions=[constant_cfg["dq_dimension"]],
                provenance=Provenance.OBSERVED,
                threshold_ref="constant_column",
                affected_count=n,
                affected_percent=1.0,
                affected_column=col_name,
                top_10_samples=[],
            ))

        if stats.type == "Categorical":
            # High cardinality: p_distinct = n_distinct / n
            p_distinct = n_distinct / n if n > 0 else 0.0
            if p_distinct > _THRESHOLDS.get("high_cardinality_gate"):
                registry.register_anomaly(AnomalyRecord(
                    issue_type="HIGH_CARDINALITY",
                    description=f"Column '{col_name}' has high cardinality (p_distinct={p_distinct:.2f})",
                    severity=Severity(hc_cfg["severity"]),
                    dq_dimensions=[hc_cfg["dq_dimension"]],
                    provenance=Provenance.OBSERVED,
                    threshold_ref="high_cardinality",
                    affected_count=n_distinct,
                    affected_percent=p_distinct,
                    affected_column=col_name,
                    top_10_samples=[],
                ))

            # Severe imbalance
            imbalance = stats.additional_metrics.get("imbalance")
            if imbalance is not None and imbalance > _THRESHOLDS.get("imbalance_gate"):
                registry.register_anomaly(AnomalyRecord(
                    issue_type="IMBALANCE",
                    description=f"Column '{col_name}' is severely imbalanced (imbalance={imbalance:.3f})",
                    severity=Severity(imbalance_cfg["severity"]),
                    dq_dimensions=[imbalance_cfg["dq_dimension"]],
                    provenance=Provenance.OBSERVED,
                    threshold_ref="severe_imbalance",
                    affected_count=n,
                    affected_percent=imbalance,
                    affected_column=col_name,
                    top_10_samples=[],
                ))

    # Format Consistency checks (requires actual DataFrame)
    if df is not None:
        format_anomalies = _detect_format_inconsistency(df, columns, n)
        for anomaly in format_anomalies:
            registry.register_anomaly(anomaly)

    return registry.get_all_anomalies()


def _detect_format_inconsistency(
    df: "pd.DataFrame",
    columns: dict,
    n: int,
) -> list[AnomalyRecord]:
    """Detect format inconsistencies across 3 categories.

    1. Date columns: mixed date formats (e.g., dd/mm/yyyy vs mm/dd/yyyy)
    2. Numeric columns: text values mixed with numbers (e.g., "N/A", "unknown")
    3. Categorical columns: case inconsistency (e.g., "Male" vs "male" vs "MALE")
    """
    import re
    anomalies: list[AnomalyRecord] = []

    for col_name, stats in columns.items():
        if col_name not in df.columns:
            continue
        series = df[col_name].dropna()
        if series.empty:
            continue

        # 1. Date format mixing: check object columns that look date-like
        if stats.type in ("DateTime", "Date") or (
            series.dtype == "object"
            and series.head(100).str.match(r"^\d{1,4}[/\-.]").any()
        ):
            date_patterns = set()
            sample = series.head(200).astype(str)
            for val in sample:
                if re.match(r"^\d{4}[/\-.]", val):
                    date_patterns.add("YYYY-first")
                elif re.match(r"^\d{1,2}[/\-.]", val):
                    date_patterns.add("DD-or-MM-first")
            if len(date_patterns) > 1:
                affected_count = len(series)
                anomalies.append(AnomalyRecord(
                    issue_type="INCONSISTENT_FORMAT",
                    description=(
                        f"Column '{col_name}' has mixed date formats "
                        f"({', '.join(sorted(date_patterns))}). "
                        f"Pandas may parse ambiguous dates incorrectly."
                    ),
                    severity=Severity.HIGH,
                    dq_dimensions=["Consistency"],
                    provenance=Provenance.OBSERVED,
                    threshold_ref="format_consistency",
                    affected_count=affected_count,
                    affected_percent=affected_count / n if n > 0 else 0,
                    affected_column=col_name,
                    top_10_samples=sample[
                        sample.str.match(r"^\d{1,2}[/\-.]")
                    ].head(5).tolist(),
                ))

        # 2. Numeric columns with text values (e.g., "N/A", "unknown", "-")
        if stats.type == "Numeric" and series.dtype == "object":
            text_mask = ~series.astype(str).str.match(
                r"^-?\d+\.?\d*(e[+\-]?\d+)?$", na=False
            )
            text_values = series[text_mask]
            if len(text_values) > 0:
                pct = len(text_values) / n if n > 0 else 0
                anomalies.append(AnomalyRecord(
                    issue_type="INCONSISTENT_FORMAT",
                    description=(
                        f"Column '{col_name}' is expected to be Numeric but contains "
                        f"{len(text_values)} text values. "
                        f"Samples: {text_values.unique()[:5].tolist()}"
                    ),
                    severity=Severity.HIGH,
                    dq_dimensions=["Consistency"],
                    provenance=Provenance.OBSERVED,
                    threshold_ref="format_consistency",
                    affected_count=len(text_values),
                    affected_percent=pct,
                    affected_column=col_name,
                    top_10_samples=text_values.head(5).tolist(),
                ))

        # 3. Categorical case inconsistency (e.g., "Male" vs "male" vs "MALE")
        if stats.type == "Categorical" and series.dtype == "object":
            unique_vals = series.unique()
            if len(unique_vals) > 500:
                # Too many unique values — skip expensive case check
                continue
            lower_map: dict[str, set[str]] = {}
            for val in unique_vals:
                key = str(val).strip().lower()
                lower_map.setdefault(key, set()).add(str(val))
            inconsistent_groups = {
                k: v for k, v in lower_map.items() if len(v) > 1
            }
            if inconsistent_groups:
                examples = [
                    f"{sorted(variants)}"
                    for _, variants in list(inconsistent_groups.items())[:3]
                ]
                affected_count = sum(
                    series.isin(variants).sum()
                    for variants in inconsistent_groups.values()
                )
                anomalies.append(AnomalyRecord(
                    issue_type="INCONSISTENT_FORMAT",
                    description=(
                        f"Column '{col_name}' has {len(inconsistent_groups)} "
                        f"case-inconsistent value groups: {'; '.join(examples)}."
                    ),
                    severity=Severity.WARN,
                    dq_dimensions=["Consistency"],
                    provenance=Provenance.OBSERVED,
                    threshold_ref="format_consistency",
                    affected_count=int(affected_count),
                    affected_percent=affected_count / n if n > 0 else 0,
                    affected_column=col_name,
                    top_10_samples=[
                        str(v) for group in list(inconsistent_groups.values())[:3]
                        for v in sorted(group)
                    ][:10],
                ))

    return anomalies

