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
    """Nguồn gốc của finding — trục thứ 3 (ARCHITECT v5.4 §3, §9.6)."""
    OBSERVED = "OBSERVED"                       # Đo trực tiếp từ dữ liệu
    INFERRED = "INFERRED"                       # Máy suy luận (MAR, FK suy luận, …)
    INDETERMINATE = "INDETERMINATE"             # Lý thuyết không xác định được
    DERIVED_CROSS_TABLE = "DERIVED_CROSS_TABLE"  # Kết quả L3b aggregate-before-join


class Disposition(str, Enum):
    """Hành động đề xuất cho một finding (ARCHITECT v5.4 §5.5d)."""
    BLOCK = "BLOCK"             # Chặn sử dụng dữ liệu
    PREPROCESS = "PREPROCESS"   # Sửa được bằng tiền xử lý
    REVIEW = "REVIEW"           # Cần người xem xét
    SIGNAL = "SIGNAL"           # Tín hiệu thống kê, không phải lỗi


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
    effective_severity: Optional[Severity] = None   # roll-up cấp-cột (§9.2, compound reform)
    confidence: Optional[float] = None              # độ chắc của mechanism label (§9.2)


class AnomalyRecord(BaseModel):
    issue_type: str
    description: str
    severity: Severity
    dq_dimensions: List[str] = Field(default_factory=list)
    ml_impact: List[str] = Field(default_factory=list)
    compound_severity: Optional[Severity] = None
    confidence: Optional[float] = None
    provenance: Provenance = Provenance.OBSERVED
    disposition: Optional[Disposition] = None
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
    table: Optional[str] = None   # khoá bảng cho bundle đa-bảng (§9.5, P3-nhỏ)


class IssueSummary(BaseModel):
    source: str
    issue_type: str
    effective_severity: Severity
    severity: Severity
    affected_table: Optional[str] = None
    affected_column: Optional[str] = None
    affected_count: int = 0
    confidence: Optional[float] = None
    disposition: Optional[Disposition] = None
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
    cardinality: Optional[str] = None   # từ L2c: "1:1" | "1:N" | "N:N" (§9.7)
    role: Optional[str] = None          # từ L2c: "<child_role>-><parent_role>" (§9.7)


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
    disposition: Optional[Disposition] = None
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
    """1 edge trong relationship graph — có cardinality + fan-out (§5.4 L2c)."""
    child_table: str
    child_column: str
    parent_table: str
    parent_column: str
    cardinality: str = "UNKNOWN"   # "1:1" | "1:N" | "N:N" | "UNKNOWN"
    pk_runtime_unique: bool = True
    confidence: float = 1.0
    role: str = ""                          # "<child_role>-><parent_role>"
    fan_out: bool = False                   # P1: cạnh N:N
    join_amplification_ratio: float = 1.0   # expected joined rows / child rows
    base_row_count: int = 0                 # số dòng child trước join
    joined_row_count: int = 0               # số dòng dự kiến sau join


class GraphResult(BaseModel):
    """Output của reconstruct_graph()."""
    edges: List[GraphEdge] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    non_unique_pk_tables: List[str] = Field(default_factory=list)
    table_roles: Dict[str, str] = Field(default_factory=dict)  # fact|dimension|bridge|standalone


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
    timestamp: str = ""   # ISO timestamp lúc plan được tạo (§9.6)


# ============================================================
# Cross-table correlations artifact (ARCHITECT v5.4 §9.6)
# ============================================================

class CrossTablePair(BaseModel):
    """1 cặp trong cross_table_correlations.json (§9.6)."""
    parent_table: str
    parent_column: str
    child_table: str
    child_column: str
    aggregate_method: str
    llm_reasoning: str = ""
    llm_confidence: str = "medium"       # high|medium|low
    correlation: Optional[float] = None
    method: str = "spearman"
    n_independent: Optional[int] = None  # N = parent rows sau aggregate-before-join
    join_cardinality: Optional[str] = None
    unit_of_analysis: str = "parent"
    provenance: str = Provenance.DERIVED_CROSS_TABLE.value
    status: str = "OK"                   # OK|TOO_FEW_UNITS|NULL_OVERLAP|VALIDATION_FAILED
    skip_reason: Optional[str] = None    # chi tiết khi status != OK (mở rộng có ghi chú)


class CrossTableCorrelationsArtifact(BaseModel):
    """Hợp đồng §9.6 — cross_table_correlations.json."""
    schema_version: str = "cross_table_correlations_v1"
    llm_plan: Dict[str, Any] = Field(default_factory=dict)  # {model, temperature, seed, timestamp}
    pairs: List[CrossTablePair] = Field(default_factory=list)
    skipped_by_llm: List[Dict[str, Any]] = Field(default_factory=list)
    skipped_by_validation: List[Dict[str, Any]] = Field(default_factory=list)
