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


class DatasetMeta(BaseModel):
    file_name: str
    n: int
    n_var: int
    memory_size: int
    p_cells_missing: float
    n_duplicates: int = 0
    p_duplicates: float = 0.0
    overview_charts: Dict[str, str] = Field(default_factory=dict)


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


class DatasetVerdict(BaseModel):
    dataset_meta: DatasetMeta
    verdict: Verdict
    verdict_rationale: str
    summary: VerdictSummary


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
    top_10_samples: List[Dict[str, Any]] = Field(default_factory=list)
    missing_field_context: Optional[MissingFieldContext] = None
    relationship: Optional[RelationshipInfo] = None


class SchemaEvaluationFindings(BaseModel):
    schema_meta: SchemaMeta
    tables: List[TableInfo]
    integrity_errors: List[IntegrityError] = Field(default_factory=list)
    relationships: List[RelationshipInfo] = Field(default_factory=list)
