from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from engines.schema_engine import validate_schema_multi


class RelationshipKey(BaseModel):
    child_table: str
    child_column: str
    parent_table: str
    parent_column: str

    def as_tuple(self) -> tuple[str, str, str, str]:
        return (
            self.child_table,
            self.child_column,
            self.parent_table,
            self.parent_column,
        )


class RelationshipEvalCase(BaseModel):
    id: str
    data_files: list[str]
    schema_file: str | None = None
    expected_relationships: list[RelationshipKey] = Field(default_factory=list)


class RelationshipEvalResult(BaseModel):
    id: str
    expected_count: int
    predicted_count: int
    true_positive: int
    false_positive: int
    false_negative: int
    precision: float
    recall: float
    f1: float
    predicted_relationships: list[RelationshipKey]
    missing_relationships: list[RelationshipKey]
    extra_relationships: list[RelationshipKey]


def _resolve(root: Path, value: str | None) -> str | None:
    if value is None:
        return None
    path = Path(value)
    return str(path if path.is_absolute() else root / path)


def _score(tp: int, fp: int, fn: int) -> tuple[float, float, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if precision + recall else 0.0
    return round(precision, 4), round(recall, 4), round(f1, 4)


def evaluate_relationship_case(case: RelationshipEvalCase, project_root: str | Path = ".") -> RelationshipEvalResult:
    root = Path(project_root)
    data_paths = [_resolve(root, path) for path in case.data_files]
    schema_path = _resolve(root, case.schema_file)
    findings = validate_schema_multi(data_paths, schema_path)

    predicted = [
        RelationshipKey(
            child_table=rel.child_table,
            child_column=rel.child_column,
            parent_table=rel.parent_table,
            parent_column=rel.parent_column,
        )
        for rel in findings.relationships
    ]
    expected_set = {rel.as_tuple() for rel in case.expected_relationships}
    predicted_set = {rel.as_tuple() for rel in predicted}
    true_positive = len(expected_set & predicted_set)
    false_positive = len(predicted_set - expected_set)
    false_negative = len(expected_set - predicted_set)
    precision, recall, f1 = _score(true_positive, false_positive, false_negative)

    return RelationshipEvalResult(
        id=case.id,
        expected_count=len(expected_set),
        predicted_count=len(predicted_set),
        true_positive=true_positive,
        false_positive=false_positive,
        false_negative=false_negative,
        precision=precision,
        recall=recall,
        f1=f1,
        predicted_relationships=predicted,
        missing_relationships=[
            rel for rel in case.expected_relationships if rel.as_tuple() not in predicted_set
        ],
        extra_relationships=[
            rel for rel in predicted if rel.as_tuple() not in expected_set
        ],
    )


def evaluate_relationship_cases(spec: dict[str, Any], project_root: str | Path = ".") -> dict[str, Any]:
    cases = [RelationshipEvalCase.model_validate(raw) for raw in spec.get("cases", [])]
    results = [evaluate_relationship_case(case, project_root) for case in cases]
    totals = {
        "cases": len(results),
        "expected_count": sum(result.expected_count for result in results),
        "predicted_count": sum(result.predicted_count for result in results),
        "true_positive": sum(result.true_positive for result in results),
        "false_positive": sum(result.false_positive for result in results),
        "false_negative": sum(result.false_negative for result in results),
    }
    precision, recall, f1 = _score(totals["true_positive"], totals["false_positive"], totals["false_negative"])
    totals.update({"precision": precision, "recall": recall, "f1": f1})
    return {
        "schema_version": "schema_relationship_eval_result_v1",
        "summary": totals,
        "results": [result.model_dump(mode="json") for result in results],
    }
