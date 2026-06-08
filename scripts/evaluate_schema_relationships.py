from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC = PROJECT_ROOT / "src"
sys.path.insert(0, str(SRC))

from evaluation.schema_relationships import evaluate_relationship_cases


def main() -> int:
    parser = argparse.ArgumentParser(description="Evaluate schema relationship inference precision/recall.")
    parser.add_argument(
        "--spec",
        default="examples/evaluation/schema_relationship_eval.json",
        help="Evaluation spec JSON path.",
    )
    parser.add_argument("--out", default=None, help="Optional output JSON path.")
    args = parser.parse_args()

    spec_path = Path(args.spec)
    if not spec_path.is_absolute():
        spec_path = PROJECT_ROOT / spec_path
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    result = evaluate_relationship_cases(spec, project_root=PROJECT_ROOT)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        out_path = Path(args.out)
        if not out_path.is_absolute():
            out_path = PROJECT_ROOT / out_path
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
