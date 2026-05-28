# Repository Guidelines

## Project Structure & Module Organization

This repository currently contains planning and research materials for an automated data profiling and smart EDA reporting tool. The root contains `README.md`, `.gitignore`, and this guide. Primary project documentation lives in `docs/`, including `project_brief.md`, architecture notes, research reports, and standard EDA process references. Older or superseded materials are kept under `docs/archive/`.

There is no application source tree yet. When implementation begins, keep product code in a clear top-level package such as `src/`, tests in `tests/`, and small non-sensitive examples in `examples/` or `fixtures/`.

## Build, Test, and Development Commands

No build system, package manager, or automated test runner is configured yet. Useful repository commands:

- `rg --files` lists tracked project files quickly.
- `sed -n '1,160p' docs/project_brief.md` previews a documentation section.
- `git status --short` checks local changes before editing or committing.
- `git log --oneline -n 10` reviews recent commit style.

If code is added, document the exact setup, run, lint, and test commands in `README.md` and keep this file in sync.

## Coding Style & Naming Conventions

For Markdown, use ATX headings (`#`, `##`), concise sections, and fenced code blocks with language labels where useful. Prefer descriptive lowercase filenames with underscores for documentation, for example `system_architecture_design.md`.

For future Python code, prefer PEP 8 conventions: 4-space indentation, `snake_case` functions and modules, `PascalCase` classes, and type hints for public interfaces. Keep generated reports and exploratory notebooks separate from reusable library code.

## Testing Guidelines

There are no tests yet. When implementation starts, add focused tests under `tests/` and mirror the source layout, for example `tests/test_quality_metrics.py`. Prefer deterministic fixtures over large real datasets. Cover data quality scoring, schema validation, anomaly detection, and report serialization paths.

## Commit & Pull Request Guidelines

Recent commits use short, direct messages such as `add architecture` and `research papers and tools`. Continue using concise imperative commit subjects; add a body when the change needs rationale.

Pull requests should include a brief summary, affected docs or modules, validation performed, and linked issues when applicable. For report or UI output changes, attach screenshots or sample generated artifacts.

## Security & Configuration Tips

Do not commit client data, credentials, database dumps, or large generated profiling outputs. The current `.gitignore` excludes `demo_ydata`; add new ignored paths for local datasets, model outputs, caches, and environment files before introducing them.
