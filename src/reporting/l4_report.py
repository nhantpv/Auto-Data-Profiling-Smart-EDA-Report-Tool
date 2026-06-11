from __future__ import annotations

import asyncio
import html
import json
import os
import urllib.error
import urllib.request
from typing import Any

from guardrail import (
    GuardrailReport,
    validate_narrative,
    verify_analyst_output,
    verify_editor_output,
)
from ontology.models import (
    AnalystOutput,
    CrossTableAnalysis,
    DataQualityFindings,
    DatasetVerdict,
    DispatchResult,
    EditorOutput,
    IssueCluster,
    MultiAgentResult,
    SchemaEvaluationFindings,
    Severity,
    SEVERITY_ORDER,
)
from reporting.dispatcher import dispatch

_MAX_AGENT_RETRIES = 3  # ARCHITECT §5.9(f): per-agent guardrail retry ≤ 3


def _severity_rank(severity: Severity) -> int:
    return SEVERITY_ORDER.index(severity)


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


def _call_openai(prompt: str, instructions: str, model_env: str, default_model: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    model = os.getenv(model_env, default_model)
    request_body = {
        "model": model,
        "instructions": instructions,
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


def _llm_enabled() -> bool:
    return os.getenv("SMART_EDA_L4_PROVIDER", "deterministic").strip().lower() == "openai"


async def _call_openai_async(
    prompt: str,
    instructions: str,
    model_env: str,
    default_model: str,
) -> str:
    return await asyncio.to_thread(_call_openai, prompt, instructions, model_env, default_model)


def _render_cluster_markdown(cluster: IssueCluster) -> str:
    lines = [
        f"### `{cluster.issue_type}`",
        "",
        f"Effective severity: `{cluster.max_severity}`.",
    ]
    if cluster.affected_columns:
        lines.append("Affected scope: " + ", ".join(f"`{column}`" for column in cluster.affected_columns) + ".")
    lines.extend([
        "",
        "| Severity | Scope | Affected |",
        "| --- | --- | --- |",
    ])
    for issue in cluster.issues[:10]:
        severity = issue.get("compound_severity") or issue.get("severity") or cluster.max_severity
        scope = issue.get("affected_column") or issue.get("affected_table") or "dataset"
        affected_count = issue.get("affected_count", 0)
        affected_percent = issue.get("affected_percent")
        if affected_percent is None:
            affected_text = f"`{affected_count}`"
        else:
            affected_text = f"`{affected_count}` (`{_pct(float(affected_percent))}`)"
        lines.append(f"| `{severity}` | {_issue_scope(scope if scope != 'dataset' else None)} | {affected_text} |")
    lines.append("")
    return "\n".join(lines)


def _agent_detail(
    agent: str,
    report: GuardrailReport,
    retry_count: int,
    cluster: str | None = None,
) -> dict[str, Any]:
    detail: dict[str, Any] = {
        "agent": agent,
        "status": report.status,
        "provider": report.provider,
        "used_fallback": report.used_fallback,
        "retry_count": retry_count,
        "violations": [violation.model_dump(mode="json") for violation in report.violations],
    }
    if cluster is not None:
        detail["cluster"] = cluster
    return detail


async def _run_analyst(cluster: IssueCluster) -> tuple[AnalystOutput, dict[str, Any]]:
    fallback_markdown = _render_cluster_markdown(cluster)

    if _llm_enabled():
        prompt = (
            "Write one concise Markdown section for this issue cluster. "
            "Use only this JSON slice. Put every numeric value and every field/table/issue reference in backticks.\n\n"
            f"{json.dumps(cluster.json_slice, ensure_ascii=False, indent=2)}"
        )
        retries = 0
        for _attempt in range(_MAX_AGENT_RETRIES):
            try:
                markdown = await _call_openai_async(
                    prompt,
                    (
                        "You are an EDA Analyst agent. Explain only the assigned issue cluster. "
                        "Do not invent numbers, thresholds, columns, tables, or recommendations."
                    ),
                    "SMART_EDA_L4_ANALYST_MODEL",
                    "gpt-4o-mini",
                )
            except Exception:
                retries += 1
                continue
            report = verify_analyst_output(
                markdown,
                cluster.json_slice,
                provider="openai-analyst",
            )
            if report.status == "passed":
                output = AnalystOutput(
                    cluster_type=cluster.issue_type,
                    markdown=markdown,
                    guardrail_passed=True,
                    retry_count=retries,
                )
                return output, _agent_detail("analyst", report, retries, cluster.issue_type)
            retries += 1

        # All retries exhausted → deterministic section (graceful degradation).
        report = verify_analyst_output(
            fallback_markdown,
            cluster.json_slice,
            provider="deterministic-analyst",
            used_fallback=True,
        )
        output = AnalystOutput(
            cluster_type=cluster.issue_type,
            markdown=fallback_markdown,
            guardrail_passed=report.status == "passed",
            retry_count=retries,
        )
        return output, _agent_detail("analyst", report, retries, cluster.issue_type)

    report = verify_analyst_output(
        fallback_markdown,
        cluster.json_slice,
        provider="deterministic-analyst",
    )
    output = AnalystOutput(
        cluster_type=cluster.issue_type,
        markdown=fallback_markdown,
        guardrail_passed=report.status == "passed",
        retry_count=0,
    )
    return output, _agent_detail("analyst", report, 0, cluster.issue_type)


def _cross_table_summary(cross_table_analysis: CrossTableAnalysis | None) -> str | None:
    if cross_table_analysis is None:
        return None
    if cross_table_analysis.status != "completed":
        return f"Cross-table analysis status is {cross_table_analysis.status}."
    if cross_table_analysis.planned_correlations:
        top = cross_table_analysis.planned_correlations[0]
        return (
            f"L3b validated planned cross-table pair {top.left_feature} vs {top.right_feature}. "
            "The narrative treats it as association, not causation."
        )
    if cross_table_analysis.correlations:
        top = cross_table_analysis.correlations[0]
        return (
            f"Cross-table analysis used fact table {cross_table_analysis.fact_table} "
            f"and found strongest Pearson pair {top.left_feature} vs {top.right_feature}."
        )
    return f"Cross-table analysis used fact table {cross_table_analysis.fact_table}."


def _strip_json_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        first_break = stripped.find("\n")
        stripped = stripped[first_break + 1:] if first_break != -1 else ""
        if stripped.rstrip().endswith("```"):
            stripped = stripped.rstrip()[:-3]
    return stripped.strip()


async def _run_editor(
    verdict: DatasetVerdict,
    analyst_outputs: list[AnalystOutput],
    cross_table_analysis: CrossTableAnalysis | None,
) -> tuple[EditorOutput, dict[str, Any]]:
    meta = verdict.dataset_meta
    fallback = EditorOutput(
        executive_summary=(
            f"Dataset {meta.file_name} has {meta.n} rows and {meta.n_var} columns. "
            f"The deterministic verdict is {verdict.verdict.value} with {verdict.summary.total_issues} total issues."
        ),
        verdict_explanation=verdict.verdict_rationale,
        cross_table_evaluation=_cross_table_summary(cross_table_analysis),
        priority_ranking=", ".join(output.cluster_type for output in analyst_outputs),
    )
    analyst_markdowns = [output.markdown for output in analyst_outputs]

    if _llm_enabled():
        payload = {
            "verdict": verdict.model_dump(mode="json"),
            "analyst_sections": analyst_markdowns,
            "cross_table_analysis": cross_table_analysis.model_dump(mode="json") if cross_table_analysis else None,
        }
        prompt = (
            "Write JSON with keys executive_summary, verdict_explanation, cross_table_evaluation, priority_ranking. "
            "Use only the provided evidence.\n\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )
        retries = 0
        for _attempt in range(_MAX_AGENT_RETRIES):
            try:
                text = await _call_openai_async(
                    prompt,
                    (
                        "You are an EDA Editor agent. Return valid compact JSON only. "
                        "Do not invent numbers, columns, tables, relationships, or thresholds."
                    ),
                    "SMART_EDA_L4_EDITOR_MODEL",
                    "gpt-4o",
                )
                editor = EditorOutput.model_validate_json(_strip_json_fences(text))
            except Exception:
                retries += 1
                continue
            report = verify_editor_output(
                editor.model_dump(mode="json"),
                analyst_markdowns,
                verdict,
                provider="openai-editor",
            )
            if report.status == "passed":
                editor.guardrail_passed = True
                editor.retry_count = retries
                return editor, _agent_detail("editor", report, retries)
            retries += 1

        report = verify_editor_output(
            fallback.model_dump(mode="json"),
            analyst_markdowns,
            verdict,
            provider="deterministic-editor",
            used_fallback=True,
        )
        fallback.guardrail_passed = report.status == "passed"
        fallback.retry_count = retries
        return fallback, _agent_detail("editor", report, retries)

    report = verify_editor_output(
        fallback.model_dump(mode="json"),
        analyst_markdowns,
        verdict,
        provider="deterministic-editor",
    )
    fallback.guardrail_passed = report.status == "passed"
    return fallback, _agent_detail("editor", report, 0)


def _render_appendix_html(
    dispatch_result: DispatchResult,
    findings: DataQualityFindings | None,
    schema: SchemaEvaluationFindings | None,
) -> str:
    """Python-rendered table of every finding not narrated by a Top-5 cluster.

    ARCHITECT §5.9(d): Top-5 clusters get narrative; everything else (lower
    ranked types + all INFO findings) must still appear in the report.
    """
    covered_types = {cluster.issue_type for cluster in dispatch_result.top_clusters}
    warn_rank = _severity_rank(Severity.WARN)
    rows: list[tuple[int, str, str, str, int]] = []

    for record in (findings.anomalies if findings is not None else []):
        effective = record.compound_severity or record.severity
        if record.issue_type in covered_types and _severity_rank(effective) >= warn_rank:
            continue  # already narrated by an Analyst cluster
        rows.append((
            _severity_rank(effective),
            effective.value,
            record.issue_type,
            record.affected_column or "dataset",
            record.affected_count,
        ))
    for error in (schema.integrity_errors if schema is not None else []):
        effective = error.compound_severity or error.severity
        if error.error_type in covered_types and _severity_rank(effective) >= warn_rank:
            continue
        rows.append((
            _severity_rank(effective),
            effective.value,
            error.error_type,
            error.affected_column or error.affected_table,
            error.affected_count,
        ))

    if not rows:
        return ""
    rows.sort(key=lambda row: (-row[0], row[2], row[3]))
    body = "".join(
        f"<tr><td>{html.escape(severity)}</td><td>{html.escape(issue_type)}</td>"
        f"<td>{html.escape(scope)}</td><td>{affected}</td></tr>"
        for _rank, severity, issue_type, scope, affected in rows
    )
    return (
        "<section class=\"appendix\">"
        "<h2>Appendix — Remaining Findings</h2>"
        "<table>"
        "<thead><tr><th>Severity</th><th>Type</th><th>Scope</th><th>Affected</th></tr></thead>"
        f"<tbody>{body}</tbody>"
        "</table>"
        "</section>"
    )


def render_multi_agent_markdown(result: MultiAgentResult, verdict: DatasetVerdict) -> str:
    meta = verdict.dataset_meta
    editor = result.editor_output or EditorOutput()
    lines = [
        "# L4 Guarded EDA Report",
        "",
        "## Executive Summary",
        "",
        editor.executive_summary or (
            f"Dataset {meta.file_name} has {meta.n} rows and {meta.n_var} columns."
        ),
        "",
        "## Decision Rationale",
        "",
        editor.verdict_explanation or verdict.verdict_rationale,
        "",
        "## Data Quality Analysis",
        "",
    ]
    if result.analyst_outputs:
        for output in result.analyst_outputs:
            lines.extend([output.markdown, ""])
    else:
        lines.extend(["No WARN, HIGH, or CRITICAL issues were dispatched to Analyst sections.", ""])

    if editor.cross_table_evaluation:
        lines.extend([
            "## Cross-table Evaluation",
            "",
            editor.cross_table_evaluation,
            "",
        ])

    if editor.priority_ranking:
        lines.extend([
            "## Priority Ranking",
            "",
            editor.priority_ranking,
            "",
        ])

    lines.extend([
        "## Guardrail Statement",
        "",
        "This report is generated only from deterministic JSON evidence. Numeric values and backticked fields are checked against the evidence set before the file is written.",
        "",
    ])
    return "\n".join(lines)


async def run_multi_agent_l4(
    findings: DataQualityFindings | None,
    verdict: DatasetVerdict,
    schema: SchemaEvaluationFindings | None = None,
    cross_table_analysis: CrossTableAnalysis | None = None,
) -> tuple[str, GuardrailReport, MultiAgentResult]:
    dispatch_result = dispatch(
        findings.anomalies if findings is not None else [],
        schema.integrity_errors if schema is not None else [],
    )
    analyst_results = await asyncio.gather(*[
        _run_analyst(cluster)
        for cluster in dispatch_result.top_clusters
    ])
    analyst_outputs = [output for output, _detail in analyst_results]
    agent_details = [detail for _output, detail in analyst_results]
    editor_output, editor_detail = await _run_editor(verdict, analyst_outputs, cross_table_analysis)
    agent_details.append(editor_detail)
    result = MultiAgentResult(
        analyst_outputs=analyst_outputs,
        editor_output=editor_output,
        appendix_html=_render_appendix_html(dispatch_result, findings, schema),
        guardrail_report={},
        used_fallback=not _llm_enabled(),
    )
    text = render_multi_agent_markdown(result, verdict)
    report = validate_narrative(
        text,
        findings,
        verdict,
        schema,
        provider="openai-multi-agent" if _llm_enabled() else "deterministic-multi-agent",
        used_fallback=result.used_fallback,
    )
    if report.status != "passed":
        text = render_deterministic_l4_report(findings, verdict, schema)
        report = validate_narrative(
            text,
            findings,
            verdict,
            schema,
            provider="deterministic-fallback",
            used_fallback=True,
        )
        result.used_fallback = True
    report.agents = agent_details
    result.guardrail_report = report.model_dump(mode="json")
    return text, report, result


def _run_multi_agent_sync(
    findings: DataQualityFindings | None,
    verdict: DatasetVerdict,
    schema: SchemaEvaluationFindings | None,
    cross_table_analysis: CrossTableAnalysis | None = None,
) -> tuple[str, GuardrailReport, MultiAgentResult]:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(run_multi_agent_l4(findings, verdict, schema, cross_table_analysis))

    # FastAPI currently calls the pipeline synchronously. If a caller is already
    # in an event loop, avoid nested asyncio.run() and use deterministic fallback.
    text = render_deterministic_l4_report(findings, verdict, schema)
    report = validate_narrative(
        text,
        findings,
        verdict,
        schema,
        provider="deterministic-fallback",
        used_fallback=True,
    )
    result = MultiAgentResult(
        editor_output=EditorOutput(
            executive_summary=f"Dataset {verdict.dataset_meta.file_name} has {verdict.dataset_meta.n} rows.",
            verdict_explanation=verdict.verdict_rationale,
        ),
        guardrail_report=report.model_dump(mode="json"),
        used_fallback=True,
    )
    return text, report, result


def generate_multi_agent_report(
    findings: DataQualityFindings | None,
    verdict: DatasetVerdict,
    schema: SchemaEvaluationFindings | None = None,
    cross_table_analysis: CrossTableAnalysis | None = None,
) -> tuple[str, GuardrailReport, MultiAgentResult]:
    return _run_multi_agent_sync(findings, verdict, schema, cross_table_analysis)


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
                "| Status | Decision | Bucket | Relationship |",
                "| --- | --- | --- | --- |",
            ])
            for rel in schema.relationships[:10]:
                relationship = f"{rel.child_table}.{rel.child_column} -> {rel.parent_table}.{rel.parent_column}"
                lines.append(
                    f"| `{rel.status}` | `{rel.decision}` | `{rel.confidence_bucket}` | `{relationship}` |"
                )
            lines.append("")

    lines.extend([
        "## Guardrail Statement",
        "",
        "This report is generated only from deterministic JSON evidence. Numeric values and backticked fields are checked against the evidence set before the file is written.",
        "",
    ])
    return "\n".join(lines)


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
    text, report, _result = generate_multi_agent_report(findings, verdict, schema)
    return text, report
