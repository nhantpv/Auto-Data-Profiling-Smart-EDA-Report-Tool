import json
from pathlib import Path

from evaluation.schema_relationships import evaluate_relationship_cases


def test_schema_relationship_eval_spec_scores_inferred_school_links():
    project_root = Path(__file__).parents[2]
    spec = json.loads(
        (project_root / "examples/evaluation/schema_relationship_eval.json").read_text(encoding="utf-8")
    )

    result = evaluate_relationship_cases(spec, project_root=project_root)

    assert result["summary"]["cases"] == 1
    assert result["summary"]["precision"] == 1.0
    assert result["summary"]["recall"] == 1.0
    assert result["summary"]["f1"] == 1.0
