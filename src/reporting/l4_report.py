from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

from guardrail import GuardrailReport, validate_narrative
from ontology.models import DataQualityFindings, DatasetVerdict, SchemaEvaluationFindings


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _issue_scope(affected_column: str | None) -> str:
    return f"`{affected_column}`" if affected_column else "dataset"


def _compact_payload(
    findings: DataQualityFindings | None,
    verdict: DatasetVerdict,
    schema: SchemaEvaluationFindings | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "dataset": verdict.dataset_meta.model_dump(),
        "verdict": verdict.verdict.value,
        "verdict_rationale": verdict.verdict_rationale,
        "summary": verdict.summary.model_dump(),
        "top_issues": [issue.model_dump(exclude_none=True) for issue in verdict.top_issues],
        "risk_score": verdict.risk_score,
        "calibration_status": verdict.calibration_status,
        "data_quality_issues": [],
        "schema_issues": [],
        "relationships": [],
    }
    if findings is not None:
        payload["columns"] = {
            name: stats.model_dump(exclude_none=True)
            for name, stats in findings.columns.items()
        }
        payload["data_quality_issues"] = [
            issue.model_dump(exclude_none=True, exclude={"top_10_samples"})
            for issue in findings.anomalies[:10]
        ]
    if schema is not None:
        payload["schema"] = {
            "meta": schema.schema_meta.model_dump(),
            "tables": [table.model_dump() for table in schema.tables],
        }
        payload["schema_issues"] = [
            issue.model_dump(exclude_none=True, exclude={"top_10_samples"})
            for issue in schema.integrity_errors[:10]
        ]
        payload["relationships"] = [rel.model_dump() for rel in schema.relationships[:10]]
    return payload


def render_deterministic_l4_report(
    findings: DataQualityFindings | None,
    verdict: DatasetVerdict,
    schema: SchemaEvaluationFindings | None = None,
) -> str:
    meta = verdict.dataset_meta
    lines = [
        "# L4 Guarded EDA Report",
        "",
        "## Executive Summary",
        "",
        f"Dataset `{meta.file_name}` has `{meta.n}` rows and `{meta.n_var}` columns.",
        f"The deterministic verdict is `{verdict.verdict.value}` with `{verdict.summary.total_issues}` total issues.",
        f"Missing cells account for `{_pct(meta.p_cells_missing)}` and duplicate rows account for `{_pct(meta.p_duplicates)}`.",
        "",
        "## Decision Rationale",
        "",
        verdict.verdict_rationale,
        "",
    ]
    if meta.is_sampled:
        lines.extend([
            "## Sampling",
            "",
            f"The input had `{meta.original_n}` original rows. Profiling used `{meta.sample_n}` rows with `{meta.sample_method}` sampling and seed `{meta.sample_seed}`.",
            "",
        ])

    if verdict.top_issues:
        lines.extend([
            "## Top Issues Driving The Verdict",
            "",
            "| Effective Severity | Type | Scope | Affected Rows |",
            "| --- | --- | --- | --- |",
        ])
        for issue in verdict.top_issues[:10]:
            scope = issue.affected_column or issue.affected_table or "dataset"
            lines.append(
                f"| `{issue.effective_severity.value}` | `{issue.issue_type}` | {_issue_scope(scope if scope != 'dataset' else None)} | `{issue.affected_count}` |"
            )
        lines.append("")

    if findings is not None:
        lines.extend([
            "## Data Quality Issues",
            "",
            "| Severity | Type | Scope | Affected |",
            "| --- | --- | --- | --- |",
        ])
        if findings.anomalies:
            for issue in findings.anomalies[:10]:
                lines.append(
                    f"| `{issue.severity.value}` | `{issue.issue_type}` | {_issue_scope(issue.affected_column)} | "
                    f"`{issue.affected_count}` (`{_pct(issue.affected_percent)}`) |"
                )
        else:
            lines.append("| `INFO` | none | dataset | `0` (`0.0%`) |")
        lines.append("")

    if schema is not None:
        lines.extend([
            "## Schema And Relationship Issues",
            "",
            f"Schema source `{schema.schema_meta.schema_file}` covers `{schema.schema_meta.total_tables}` tables "
            f"and `{schema.schema_meta.total_relationships}` relationships.",
            "",
            "| Severity | Type | Scope | Affected Rows |",
            "| --- | --- | --- | --- |",
        ])
        if schema.integrity_errors:
            for issue in schema.integrity_errors[:10]:
                scope = issue.affected_column or issue.affected_table
                lines.append(
                    f"| `{issue.severity.value}` | `{issue.error_type}` | `{scope}` | `{issue.affected_count}` |"
                )
        else:
            lines.append("| `INFO` | none | schema | `0` |")
        lines.append("")

        if schema.relationships:
            lines.extend([
                "## Inferred Or Explicit Relationships",
                "",
                "| Status | Relationship | Confidence |",
                "| --- | --- | --- |",
            ])
            for rel in schema.relationships[:10]:
                relationship = f"{rel.child_table}.{rel.child_column} -> {rel.parent_table}.{rel.parent_column}"
                lines.append(f"| `{rel.status}` | `{relationship}` | `{rel.confidence:.3f}` |")
            lines.append("")

    lines.extend([
        "## Guardrail Statement",
        "",
        "This report is generated only from deterministic JSON evidence. Numeric values and backticked fields are checked against the evidence set before the file is written.",
        "",
    ])
    return "\n".join(lines)


def _extract_openai_text(payload: dict[str, Any]) -> str:
    if isinstance(payload.get("output_text"), str):
        return payload["output_text"]
    parts: list[str] = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            text = content.get("text")
            if isinstance(text, str):
                parts.append(text)
    return "\n".join(parts).strip()


def _call_openai(prompt: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    model = os.getenv("SMART_EDA_L4_MODEL", "gpt-5")
    request_body = {
        "model": model,
        "instructions": (
            "Write a concise end-user EDA report in Markdown. "
            "Use only facts from the provided JSON evidence. "
            "Do not invent numbers, columns, tables, relationships, thresholds, charts, or recommendations. "
            "Put every numeric value and every field/table/issue reference inside backticks."
        ),
        "input": prompt,
        "max_output_tokens": 1200,
    }
    request = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(request_body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            response_payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"OpenAI L4 request failed: HTTP {exc.code} {body}") from exc

    text = _extract_openai_text(response_payload)
    if not text:
        raise RuntimeError("OpenAI L4 response did not include text")
    return text


def _llm_prompt(
    findings: DataQualityFindings | None,
    verdict: DatasetVerdict,
    schema: SchemaEvaluationFindings | None,
) -> str:
    payload = _compact_payload(findings, verdict, schema)
    return (
        "Generate L4 narrative from this deterministic evidence only.\n\n"
        f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
    )


def generate_l4_report(
    findings: DataQualityFindings | None,
    verdict: DatasetVerdict,
    schema: SchemaEvaluationFindings | None = None,
) -> tuple[str, GuardrailReport]:
    provider = os.getenv("SMART_EDA_L4_PROVIDER", "deterministic").strip().lower() or "deterministic"
    used_fallback = False
    text: str | None = None

    if provider == "openai":
        try:
            text = _call_openai(_llm_prompt(findings, verdict, schema))
            report = validate_narrative(text, findings, verdict, schema, provider=provider)
            if report.status == "passed":
                return text, report
            used_fallback = True
        except Exception:
            used_fallback = True
    else:
        provider = "deterministic"

    text = render_deterministic_l4_report(findings, verdict, schema)
    report = validate_narrative(
        text,
        findings,
        verdict,
        schema,
        provider=provider,
        used_fallback=used_fallback,
    )
    return text, report
