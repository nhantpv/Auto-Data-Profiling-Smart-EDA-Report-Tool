from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field
from typing import Dict, List, Any, Optional


class Severity(str, Enum):
    INFO = "INFO"
    WARN = "WARN"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


SEVERITY_ORDER: tuple = (
    Severity.INFO, Severity.WARN, Severity.HIGH, Severity.CRITICAL,
)


class Provenance(str, Enum):
    """Nguồn gốc của finding — trục thứ 3 (ARCHITECT v5.4 §3)."""
    OBSERVED = "OBSERVED"       # Đo trực tiếp từ dữ liệu
    INFERRED = "INFERRED"       # Máy suy luận (calibrator, compound, etc.)
    LLM_GUIDED = "LLM_GUIDED"  # LLM chọn/đánh giá (L3b Phase 1, L4)


class DatasetMeta(BaseModel):
    file_name: str
    n: int
    n_var: int
    memory_size: int
    p_cells_missing: float
    n_duplicates: int = 0
    p_duplicates: float = 0.0
    overview_charts: Dict[str, str] = Field(default_factory=dict)
    is_sampled: bool = False
    original_n: Optional[int] = None
    sample_n: Optional[int] = None
    sample_method: Optional[str] = None
    sample_seed: Optional[int] = None


class ColumnStats(BaseModel):
    type: str
    n_missing: int
    p_missing: float
    n_zeros: Optional[int] = None
    n_distinct: Optional[int] = None
    missingness_mechanism: Optional[str] = None
    additional_metrics: Dict[str, Any] = Field(default_factory=dict)


class AnomalyRecord(BaseModel):
    issue_type: str
    description: str
    severity: Severity
    dq_dimensions: List[str] = Field(default_factory=list)
    ml_impact: List[str] = Field(default_factory=list)
    compound_severity: Optional[Severity] = None
    confidence: Optional[float] = None
    provenance: Provenance = Provenance.OBSERVED
    finding_id: Optional[str] = None
    threshold_ref: Optional[str] = None
    affected_count: int
    affected_percent: float
    affected_column: Optional[str] = None
    top_10_samples: List[Dict[str, Any]]
    diagnostic_chart: Optional[str] = None
    full_anomalies_export_path: Optional[str] = None


class DataQualityFindings(BaseModel):
    dataset_meta: DatasetMeta
    columns: Dict[str, ColumnStats]
    anomalies: List[AnomalyRecord] = Field(default_factory=list)


class Verdict(str, Enum):
    READY = "READY"
    WARN = "WARN"
    NOT_READY = "NOT_READY"


class VerdictSummary(BaseModel):
    total_issues: int = 0
    critical: int = 0
    high: int = 0
    warn: int = 0
    info: int = 0


class IssueDetailRef(BaseModel):
    file: str
    collection: str
    index: int


class IssueSummary(BaseModel):
    source: str
    issue_type: str
    effective_severity: Severity
    severity: Severity
    affected_table: Optional[str] = None
    affected_column: Optional[str] = None
    affected_count: int = 0
    confidence: Optional[float] = None
    rationale: str
    detail_ref: Optional[IssueDetailRef] = None


class DatasetVerdict(BaseModel):
    dataset_meta: DatasetMeta
    verdict: Verdict
    verdict_rationale: str
    summary: VerdictSummary
    top_issues: List[IssueSummary] = Field(default_factory=list)
    risk_score: Optional[float] = None
    calibration_status: str = "heuristic_v0_not_benchmark_calibrated"


class ArtifactRecord(BaseModel):
    artifact_id: str
    kind: str
    path: str
    source_layer: str
    description: Optional[str] = None


class ArtifactManifest(BaseModel):
    schema_version: str = "artifact_manifest_v1"
    artifacts: List[ArtifactRecord] = Field(default_factory=list)


class SchemaMeta(BaseModel):
    schema_file: str
    total_tables: int
    total_relationships: int


class TableInfo(BaseModel):
    name: str
    columns: List[str]


class MissingFieldContext(BaseModel):
    expected_column: str
    table_context: Optional[str] = None
    inferred_meaning: Optional[str] = None
    is_intentional_missing: Optional[bool] = None
    intentional_missing_basis: str = "unknown"
    candidate_aliases: List[str] = Field(default_factory=list)


class RelationshipInfo(BaseModel):
    child_table: str
    child_column: str
    parent_table: str
    parent_column: str
    relationship_type: str
    status: str
    confidence: float
    evidence: List[str] = Field(default_factory=list)
    decision: str = "accepted_for_safe_join"
    confidence_bucket: str = "HIGH_CONFIDENCE"
    decision_reasons: List[str] = Field(default_factory=list)
    blocked_reasons: List[str] = Field(default_factory=list)
    evidence_metrics: Dict[str, Any] = Field(default_factory=dict)
    cardinality: Optional[str] = None
    role: Optional[str] = None


class IntegrityError(BaseModel):
    error_type: str
    description: str
    severity: Severity
    affected_table: str
    affected_count: int = 0
    affected_column: Optional[str] = None
    dq_dimensions: List[str] = Field(default_factory=list)
    ml_impact: List[str] = Field(default_factory=list)
    compound_severity: Optional[Severity] = None
    confidence: Optional[float] = None
    provenance: Provenance = Provenance.OBSERVED
    finding_id: Optional[str] = None
    threshold_ref: Optional[str] = None
    top_10_samples: List[Dict[str, Any]] = Field(default_factory=list)
    missing_field_context: Optional[MissingFieldContext] = None
    relationship: Optional[RelationshipInfo] = None


class SchemaEvaluationFindings(BaseModel):
    schema_meta: SchemaMeta
    tables: List[TableInfo]
    integrity_errors: List[IntegrityError] = Field(default_factory=list)
    relationships: List[RelationshipInfo] = Field(default_factory=list)


class SchemaGateResult(BaseModel):
    """Output L2b.5 Human-in-the-loop gate."""
    schema_version: str = "schema_gate_v1"
    mode: str = "quick"
    schema_status: str = "inferred"
    fact_table: Optional[str] = None
    relationships: List[RelationshipInfo] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    source: str = "auto"


class SafeJoinStep(BaseModel):
    child_table: str
    child_column: str
    parent_table: str
    parent_column: str
    status: str
    before_rows: int
    after_rows: int
    parent_rows: int
    parent_rows_after_dedupe: int
    parent_key_unique: bool
    matched_rows: int
    match_rate: float
    added_columns: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class CrossTableCorrelation(BaseModel):
    left_feature: str
    right_feature: str
    left_table: str
    right_table: str
    method: str
    coefficient: float
    abs_coefficient: float
    n: int


class CrossTableAnalysis(BaseModel):
    schema_version: str = "cross_table_analysis_v1"
    status: str
    fact_table: Optional[str] = None
    llm_plan: Optional["LlmCorrelationPlan"] = None
    denormalized_rows: int = 0
    denormalized_columns: int = 0
    analysis_rows: int = 0
    exact_duplicate_rows_removed: int = 0
    join_steps: List[SafeJoinStep] = Field(default_factory=list)
    correlations: List[CrossTableCorrelation] = Field(default_factory=list)
    planned_correlations: List[CrossTableCorrelation] = Field(default_factory=list)
    excluded_columns: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    preview_csv_path: Optional[str] = None


# ============================================================
# L4 Multi-Agent models (ARCHITECT v5.4 §5.9)
# ============================================================

class IssueCluster(BaseModel):
    """1 nhóm lỗi cùng loại — Dispatcher tạo, Analyst nhận."""
    issue_type: str
    issues: List[Dict[str, Any]]     # AnomalyRecord.model_dump() list
    affected_columns: List[str]
    max_severity: str                # Severity.value
    json_slice: Dict[str, Any] = Field(default_factory=dict)


class DispatchResult(BaseModel):
    """Output Dispatcher → input cho Analyst fan-out."""
    top_clusters: List[IssueCluster] = Field(default_factory=list)
    remainder_count: int = 0


class AnalystOutput(BaseModel):
    """Output 1 Analyst agent (mini model)."""
    cluster_type: str
    markdown: str
    guardrail_passed: bool = True
    retry_count: int = 0


class EditorOutput(BaseModel):
    """Output Editor agent (strong model)."""
    executive_summary: str = ""
    verdict_explanation: str = ""
    cross_table_evaluation: Optional[str] = None
    priority_ranking: str = ""
    guardrail_passed: bool = True
    retry_count: int = 0


class MultiAgentResult(BaseModel):
    """Kết quả tổng hợp L4 multi-agent pipeline."""
    analyst_outputs: List[AnalystOutput] = Field(default_factory=list)
    editor_output: Optional[EditorOutput] = None
    appendix_html: str = ""
    guardrail_report: Dict[str, Any] = Field(default_factory=dict)
    used_fallback: bool = False


# ============================================================
# Graph Reconstruction models (ARCHITECT v5.4 §5.5 L2c)
# ============================================================

class GraphEdge(BaseModel):
    """1 edge trong relationship graph — có cardinality."""
    child_table: str
    child_column: str
    parent_table: str
    parent_column: str
    cardinality: str = "UNKNOWN"   # "1:1" | "1:N" | "N:N" | "UNKNOWN"
    role: str = "unknown"
    pk_runtime_unique: bool = True
    confidence: float = 1.0


class GraphResult(BaseModel):
    """Output của reconstruct_graph()."""
    edges: List[GraphEdge] = Field(default_factory=list)
    integrity_errors: List[IntegrityError] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    non_unique_pk_tables: List[str] = Field(default_factory=list)


# ============================================================
# Threshold Registry models (ARCHITECT v5.4 §Mục 10)
# ============================================================

class ThresholdEntry(BaseModel):
    """1 entry trong Threshold Registry."""
    key: str
    value: float
    maturity: str = "Heuristic"   # "Heuristic"|"Benchmark-Validated"|"Production-Validated"
    policy_version: str = "v5.4"
    description: str = ""


# ============================================================
# LLM Correlation Plan models (ARCHITECT v5.4 §5.7 L3b)
# ============================================================

class CorrelationPairPlan(BaseModel):
    """1 cặp LLM chọn trong Phase 1."""
    parent_table: str
    parent_column: str
    child_table: str
    child_column: str
    parent_value_column: Optional[str] = None
    child_value_column: Optional[str] = None
    aggregate_method: str     # mean|sum|count|min|max|median
    reasoning: str = ""
    confidence: str = "medium"  # high|medium|low


class LlmCorrelationPlan(BaseModel):
    """Output Phase 1 (LLM Planner) sau validation."""
    correlation_pairs: List[CorrelationPairPlan] = Field(default_factory=list)
    skipped_pairs: List[Dict[str, Any]] = Field(default_factory=list)
    model: str = ""
    temperature: float = 0.0
    seed: int = 42
