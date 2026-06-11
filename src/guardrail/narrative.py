from __future__ import annotations

import re
from typing import Any, Iterable

from pydantic import BaseModel, Field

from ontology.models import DataQualityFindings, DatasetVerdict, SchemaEvaluationFindings


_NUMERIC_TOKEN = re.compile(r"(?<![A-Za-z0-9_])-?\d+(?:\.\d+)?%?(?![A-Za-z0-9_])")
_BACKTICK_TOKEN = re.compile(r"`([^`]+)`")
_CAUSATION_LANGUAGE = re.compile(
    r"\b(causes?|caused by|causing|leads? to|result(?:s|ed)? in|due to)\b",
    re.IGNORECASE,
)


class GuardrailViolation(BaseModel):
    check: str
    value: str
    detail: str


class GuardrailReport(BaseModel):
    status: str
    provider: str
    used_fallback: bool = False
    checked_numbers: list[str] = Field(default_factory=list)
    checked_references: list[str] = Field(default_factory=list)
    violations: list[GuardrailViolation] = Field(default_factory=list)
    allowed_numbers_count: int = 0
    allowed_references_count: int = 0


class NarrativeEvidence(BaseModel):
    numbers: set[str] = Field(default_factory=set)
    references: set[str] = Field(default_factory=set)


def _norm_number(value: int | float | None) -> str | None:
    if value is None:
        return None
    as_float = float(value)
    if as_float.is_integer():
        return str(int(as_float))
    return f"{as_float:.4f}".rstrip("0").rstrip(".")


def _norm_percent(value: float | None) -> str | None:
    if value is None:
        return None
    return f"{float(value) * 100:.1f}%"


def _add_numbers(target: set[str], values: Iterable[int | float | None]) -> None:
    for value in values:
        norm = _norm_number(value)
        if norm is not None:
            target.add(norm)


def _add_percents(target: set[str], values: Iterable[float | None]) -> None:
    for value in values:
        norm = _norm_percent(value)
        if norm is not None:
            target.add(norm)


def _normalize_numeric_token(token: str) -> str:
    if token.endswith("%"):
        try:
            return f"{float(token[:-1]):.1f}%"
        except ValueError:
            return token
    try:
        return _norm_number(float(token)) or token
    except ValueError:
        return token


def _collect_evidence_values(value: Any, numbers: set[str], references: set[str]) -> None:
    """Collect primitive values from JSON-like evidence for agent-level checks."""
    if value is None:
        return
    if isinstance(value, bool):
        references.add(str(value))
        return
    if isinstance(value, (int, float)):
        norm = _norm_number(value)
        if norm is not None:
            numbers.add(norm)
        if isinstance(value, float) and 0.0 <= value <= 1.0:
            percent = _norm_percent(value)
            if percent is not None:
                numbers.add(percent)
        return
    if isinstance(value, str):
        references.add(value)
        for token in _NUMERIC_TOKEN.findall(value):
            numbers.add(_normalize_numeric_token(token))
        return
    if isinstance(value, dict):
        for key, item in value.items():
            references.add(str(key))
            _collect_evidence_values(item, numbers, references)
        return
    if isinstance(value, (list, tuple, set)):
        for item in value:
            _collect_evidence_values(item, numbers, references)


def _report_for_text(
    text: str,
    numbers: set[str],
    references: set[str],
    provider: str,
    used_fallback: bool = False,
) -> GuardrailReport:
    checked_numbers = [_normalize_numeric_token(token) for token in _NUMERIC_TOKEN.findall(text)]
    checked_references = [
        token for token in _BACKTICK_TOKEN.findall(text)
        if _normalize_numeric_token(token) not in numbers
    ]

    violations: list[GuardrailViolation] = []
    for token in checked_numbers:
        if token not in numbers:
            violations.append(GuardrailViolation(
                check="number_allowed_set",
                value=token,
                detail="Number is not present in the evidence allowed set.",
            ))

    for reference in checked_references:
        if reference not in references:
            violations.append(GuardrailViolation(
                check="reference_allowed_set",
                value=reference,
                detail="Backticked reference is not present in the evidence allowed set.",
            ))

    for match in _CAUSATION_LANGUAGE.finditer(text):
        violations.append(GuardrailViolation(
            check="causation_language_ban",
            value=match.group(0),
            detail="Narrative must not turn correlation or association into causal language.",
        ))

    return GuardrailReport(
        status="passed" if not violations else "failed",
        provider=provider,
        used_fallback=used_fallback,
        checked_numbers=checked_numbers,
        checked_references=checked_references,
        violations=violations,
        allowed_numbers_count=len(numbers),
        allowed_references_count=len(references),
    )


def verify_analyst_output(
    markdown: str,
    evidence: dict[str, Any],
    provider: str = "analyst",
    used_fallback: bool = False,
) -> GuardrailReport:
    """Validate one Analyst section against only its assigned JSON slice."""
    numbers: set[str] = {"0", "10", "100", "0.0%"}
    references: set[str] = {"INFO", "WARN", "HIGH", "CRITICAL", "READY", "NOT_READY"}
    _collect_evidence_values(evidence, numbers, references)
    return _report_for_text(markdown, numbers, references, provider, used_fallback)


def verify_editor_output(
    editor_json: dict[str, Any],
    analyst_markdowns: list[str],
    verdict: DatasetVerdict,
    provider: str = "editor",
    used_fallback: bool = False,
) -> GuardrailReport:
    """Validate Editor output against verdict evidence plus approved Analyst text."""
    numbers: set[str] = {"0", "10", "100", "0.0%"}
    references: set[str] = {"INFO", "WARN", "HIGH", "CRITICAL", "READY", "NOT_READY"}
    _collect_evidence_values(verdict.model_dump(mode="json"), numbers, references)
    for markdown in analyst_markdowns:
        for token in _NUMERIC_TOKEN.findall(markdown):
            numbers.add(_normalize_numeric_token(token))
        for token in _BACKTICK_TOKEN.findall(markdown):
            references.add(token)
    text = "\n".join(str(value) for value in editor_json.values() if value is not None)
    return _report_for_text(text, numbers, references, provider, used_fallback)


def build_narrative_evidence(
    findings: DataQualityFindings | None,
    verdict: DatasetVerdict,
    schema: SchemaEvaluationFindings | None = None,
) -> NarrativeEvidence:
    numbers: set[str] = {"0", "10", "100", "0.0%"}
    references: set[str] = {
        verdict.verdict.value,
        verdict.dataset_meta.file_name,
        "READY",
        "WARN",
        "NOT_READY",
        "INFO",
        "HIGH",
        "CRITICAL",
        "none",
    }

    meta = verdict.dataset_meta
    _add_numbers(
        numbers,
        [
            meta.n,
            meta.n_var,
            meta.memory_size,
            meta.n_duplicates,
            meta.original_n,
            meta.sample_n,
            meta.sample_seed,
            verdict.summary.total_issues,
            verdict.summary.critical,
            verdict.summary.high,
            verdict.summary.warn,
            verdict.summary.info,
            verdict.risk_score,
        ],
    )
    _add_percents(numbers, [meta.p_cells_missing, meta.p_duplicates])
    if meta.sample_method:
        references.add(meta.sample_method)

    for issue in verdict.top_issues:
        references.add(issue.source)
        references.add(issue.issue_type)
        references.add(issue.effective_severity.value)
        references.add(issue.severity.value)
        if issue.affected_table:
            references.add(issue.affected_table)
        if issue.affected_column:
            references.add(issue.affected_column)
        _add_numbers(numbers, [issue.affected_count, issue.confidence])
        if issue.detail_ref:
            references.add(issue.detail_ref.file)
            references.add(issue.detail_ref.collection)
            _add_numbers(numbers, [issue.detail_ref.index])

    if findings is not None:
        references.add(findings.dataset_meta.file_name)
        references.update(findings.columns.keys())
        for name, stats in findings.columns.items():
            references.add(name)
            _add_numbers(numbers, [stats.n_missing, stats.n_zeros, stats.n_distinct])
            _add_percents(numbers, [stats.p_missing])
            _add_numbers(numbers, stats.additional_metrics.values())

        for issue in findings.anomalies:
            references.add(issue.issue_type)
            if issue.affected_column:
                references.add(issue.affected_column)
            _add_numbers(numbers, [issue.affected_count, issue.confidence])
            _add_percents(numbers, [issue.affected_percent])

    if schema is not None:
        references.add(schema.schema_meta.schema_file)
        _add_numbers(numbers, [schema.schema_meta.total_tables, schema.schema_meta.total_relationships])
        for table in schema.tables:
            references.add(table.name)
            references.update(table.columns)
            for column in table.columns:
                references.add(f"{table.name}.{column}")

        for issue in schema.integrity_errors:
            references.add(issue.error_type)
            references.add(issue.affected_table)
            if issue.affected_column:
                references.add(issue.affected_column)
                references.add(f"{issue.affected_table}.{issue.affected_column}")
            _add_numbers(numbers, [issue.affected_count, issue.confidence])

        for rel in schema.relationships:
            rel_ref = f"{rel.child_table}.{rel.child_column} -> {rel.parent_table}.{rel.parent_column}"
            references.add(rel_ref)
            references.add(rel.status)
            references.add(rel.relationship_type)
            references.add(rel.decision)
            references.add(rel.confidence_bucket)
            references.update(rel.decision_reasons)
            references.update(rel.blocked_reasons)
            references.add(rel.child_table)
            references.add(rel.parent_table)
            references.add(rel.child_column)
            references.add(rel.parent_column)
            references.add(f"{rel.child_table}.{rel.child_column}")
            references.add(f"{rel.parent_table}.{rel.parent_column}")
            _add_numbers(numbers, [rel.confidence])
            for metric in rel.evidence_metrics.values():
                if isinstance(metric, (int, float, bool)):
                    _add_numbers(numbers, [int(metric) if isinstance(metric, bool) else metric])

    return NarrativeEvidence(numbers=numbers, references=references)


def validate_narrative(
    text: str,
    findings: DataQualityFindings | None,
    verdict: DatasetVerdict,
    schema: SchemaEvaluationFindings | None = None,
    provider: str = "deterministic",
    used_fallback: bool = False,
) -> GuardrailReport:
    evidence = build_narrative_evidence(findings, verdict, schema)
    checked_numbers = [_normalize_numeric_token(token) for token in _NUMERIC_TOKEN.findall(text)]
    checked_references = [
        token for token in _BACKTICK_TOKEN.findall(text)
        if _normalize_numeric_token(token) not in evidence.numbers
    ]

    violations: list[GuardrailViolation] = []
    for token in checked_numbers:
        if token not in evidence.numbers:
            violations.append(GuardrailViolation(
                check="number_allowed_set",
                value=token,
                detail="Number is not present in the deterministic findings/verdict evidence set.",
            ))

    for reference in checked_references:
        if reference not in evidence.references:
            violations.append(GuardrailViolation(
                check="reference_allowed_set",
                value=reference,
                detail="Backticked field/table/issue reference is not present in the evidence set.",
            ))

    for match in _CAUSATION_LANGUAGE.finditer(text):
        violations.append(GuardrailViolation(
            check="causation_language_ban",
            value=match.group(0),
            detail="Narrative must not turn correlation or association into causal language.",
        ))

    return GuardrailReport(
        status="passed" if not violations else "failed",
        provider=provider,
        used_fallback=used_fallback,
        checked_numbers=checked_numbers,
        checked_references=checked_references,
        violations=violations,
        allowed_numbers_count=len(evidence.numbers),
        allowed_references_count=len(evidence.references),
    )
