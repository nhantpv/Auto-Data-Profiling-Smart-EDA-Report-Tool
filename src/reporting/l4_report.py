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
    AnalystTableResult,
    ColumnIssue,
    CrossTableAnalysis,
    DataQualityFindings,
    DatasetVerdict,
    DispatchResult,
    EditorOutput,
    EditorStructuredOutput,
    FeatureUsabilityItem,
    IntegrityError,
    IssueCluster,
    MultiAgentResult,
    SEVERITY_ORDER,
    SchemaEvaluationFindings,
    SchemaGateResult,
    Severity,
    TableCluster,
)
from reporting.dispatcher import dispatch, dispatch_by_table


def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _issue_scope(affected_column: str | None) -> str:
    return f"`{affected_column}`" if affected_column else "dataset"


def _severity_rank(severity: Severity) -> int:
    return SEVERITY_ORDER.index(severity)


def _effective_severity(record: Any) -> Severity:
    return record.compound_severity if record.compound_severity is not None else record.severity


def _agent_detail(
    agent: str,
    report: GuardrailReport,
    retry_count: int,
    cluster: str | None = None,
    detail: str | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "agent": agent,
        "status": report.status,
        "provider": report.provider,
        "used_fallback": report.used_fallback,
        "retry_count": retry_count,
        "violations": [
            violation.model_dump(mode="json")
            for violation in report.violations
        ],
    }
    if cluster is not None:
        payload["cluster"] = cluster
    if detail is not None:
        payload["detail"] = detail
    return payload


def _strip_json_fences(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    first_break = stripped.find("\n")
    if first_break == -1:
        return ""
    stripped = stripped[first_break + 1:].strip()
    if stripped.endswith("```"):
        stripped = stripped[:-3].strip()
    return stripped


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


def _extract_chat_completion_text(payload: dict[str, Any]) -> str:
    choices = payload.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message", {})
    content = message.get("content")
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and isinstance(item.get("text"), str):
                parts.append(item["text"])
        return "\n".join(parts).strip()
    return ""


def _call_openai(prompt: str, instructions: str, model_env: str, default_model: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")

    model = os.getenv(model_env, default_model)
    max_tokens = int(os.getenv("SMART_EDA_L4_MAX_TOKENS", "2200"))
    api_mode = os.getenv("SMART_EDA_L4_API_MODE", "chat_completions").strip().lower().replace("-", "_")
    if api_mode in {"chat", "chat_completions"}:
        endpoint = "https://api.openai.com/v1/chat/completions"
        request_body = {
            "model": model,
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0,
            "max_tokens": max_tokens,
        }
        extractor = _extract_chat_completion_text
    elif api_mode == "responses":
        endpoint = "https://api.openai.com/v1/responses"
        request_body = {
            "model": model,
            "instructions": instructions,
            "input": prompt,
            "max_output_tokens": max_tokens,
        }
        extractor = _extract_openai_text
    else:
        raise RuntimeError(f"Unsupported SMART_EDA_L4_API_MODE: {api_mode}")

    request = urllib.request.Request(
        endpoint,
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
        raise RuntimeError(f"OpenAI L4 request failed on {api_mode}: HTTP {exc.code} {body}") from exc

    text = extractor(response_payload)
    if not text:
        raise RuntimeError(f"OpenAI L4 {api_mode} response did not include text")
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
    affected_counts = [
        int(issue.get("affected_count", 0) or 0)
        for issue in cluster.issues
    ]
    largest_affected = max(affected_counts) if affected_counts else 0
    dimensions = sorted({
        str(dimension)
        for issue in cluster.issues
        for dimension in issue.get("dq_dimensions", [])
        if dimension
    })
    impacts = sorted({
        str(impact)
        for issue in cluster.issues
        for impact in issue.get("ml_impact", [])
        if impact
    })
    lines = [
        f"### `{cluster.issue_type}`",
        "",
        "#### Evidence Snapshot",
        "",
        f"- Cluster finding count: `{len(cluster.issues)}`.",
        f"- Maximum effective severity: `{cluster.max_severity}`.",
        f"- Largest affected-row count in a single finding: `{largest_affected}`.",
    ]
    if cluster.affected_columns:
        lines.append("- Affected scope: " + ", ".join(f"`{column}`" for column in cluster.affected_columns) + ".")
    if dimensions:
        lines.append("- Data-quality dimensions recorded in evidence: " + ", ".join(f"`{dimension}`" for dimension in dimensions) + ".")
    if impacts:
        lines.append("- Machine-learning impact labels recorded in evidence: " + ", ".join(f"`{impact}`" for impact in impacts) + ".")
    lines.extend([
        "",
        "#### Interpretation",
        "",
        f"- The cluster groups deterministic evidence for `{cluster.issue_type}` with maximum effective severity `{cluster.max_severity}`.",
        "- Review the scoped columns or tables before using this dataset for modeling, reporting, joins, or downstream business analysis.",
        "- Treat this section as a triage summary from observed evidence, not as a causal explanation.",
        "",
        "#### Evidence Table",
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
    lines.extend([
        "",
        "#### Suggested Follow-up",
        "",
        "- Confirm whether the affected records should be corrected, filtered, or documented before downstream use.",
        "- Re-run the report after remediation so the verdict and issue counts can be compared against this evidence snapshot.",
        "",
    ])
    return "\n".join(lines)


async def _run_analyst(
    cluster: IssueCluster,
    llm_errors: list[str] | None = None,
) -> tuple[AnalystOutput, dict[str, Any]]:
    fallback_markdown = _render_cluster_markdown(cluster)
    llm_enabled = _llm_enabled()

    if llm_enabled:
        prompt = (
            "Write one detailed Markdown section for this issue cluster. "
            "Use only this JSON slice. Put every numeric value and every field/table/issue reference in backticks. "
            "Do not use numbered lists, ordinal numbers, or extra counts that are not present in the JSON slice.\n\n"
            "Required structure:\n"
            "- Heading with the issue type.\n"
            "- Evidence Snapshot: severity, finding count, scope, affected-row counts, dimensions or impact labels if present.\n"
            "- Interpretation: explain what the data scientist should inspect and why this matters for analysis.\n"
            "- Evidence Table: include severity, scope, affected count, and affected percent when present.\n"
            "- Suggested Follow-up: concrete analyst checks that do not invent new thresholds or facts.\n\n"
            f"{json.dumps(cluster.json_slice, ensure_ascii=False, indent=2)}"
        )
        for attempt in range(1, 4):
            try:
                markdown = await _call_openai_async(
                    prompt,
                    (
                        "You are an EDA Analyst agent. Explain only the assigned issue cluster in a detailed but grounded way. "
                        "Do not invent numbers, thresholds, columns, tables, or recommendations. "
                        "Write a heading plus structured sections and bullets; bullets must not start with numbers. "
                        "Use table.column references only when that exact relationship exists in evidence. "
                        "Do not use causal language such as causes, caused by, causing, leads to, "
                        "results in, or due to."
                    ),
                    "SMART_EDA_L4_ANALYST_MODEL",
                    "gpt-4o-mini",
                )
            except Exception as exc:
                if llm_errors is not None:
                    llm_errors.append(
                        f"analyst:{cluster.issue_type}:attempt_{attempt}: {exc}"
                    )
                continue
            report = verify_analyst_output(
                markdown,
                cluster.json_slice,
                provider="openai-analyst",
                used_fallback=False,
            )
            if report.status == "passed":
                output = AnalystOutput(
                    cluster_type=cluster.issue_type,
                    markdown=markdown,
                    guardrail_passed=True,
                    retry_count=attempt - 1,
                )
                return output, _agent_detail(
                    "analyst",
                    report,
                    attempt - 1,
                    cluster=cluster.issue_type,
                )
            if llm_errors is not None:
                violation_checks = ",".join(violation.check for violation in report.violations)
                llm_errors.append(
                    f"analyst:{cluster.issue_type}:attempt_{attempt}: guardrail_failed:{violation_checks}"
                )

    report = verify_analyst_output(
        fallback_markdown,
        cluster.json_slice,
        provider="deterministic-analyst",
        used_fallback=llm_enabled,
    )

    output = AnalystOutput(
        cluster_type=cluster.issue_type,
        markdown=fallback_markdown,
        guardrail_passed=report.status == "passed",
        retry_count=3 if llm_enabled else 0,
    )
    return output, _agent_detail(
        "analyst",
        report,
        output.retry_count,
        cluster=cluster.issue_type,
    )


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


async def _run_editor(
    verdict: DatasetVerdict,
    analyst_outputs: list[AnalystOutput],
    cross_table_analysis: CrossTableAnalysis | None,
    llm_errors: list[str] | None = None,
) -> tuple[EditorOutput, dict[str, Any]]:
    meta = verdict.dataset_meta
    fallback = EditorOutput(
        executive_summary=(
            f"Dataset `{meta.file_name}` has `{meta.n}` rows and `{meta.n_var}` columns. "
            f"The deterministic verdict is `{verdict.verdict.value}` with `{verdict.summary.total_issues}` total issues. "
            "Read this report as an evidence-backed triage note: start with the verdict, then inspect the ranked issue clusters and any schema or cross-table notes."
        ),
        verdict_explanation=verdict.verdict_rationale,
        cross_table_evaluation=_cross_table_summary(cross_table_analysis),
        priority_ranking=(
            "Priority issue clusters: "
            + ", ".join(f"`{output.cluster_type}`" for output in analyst_outputs)
            if analyst_outputs
            else "No WARN, HIGH, or CRITICAL issue cluster was dispatched to Analyst review."
        ),
    )
    llm_enabled = _llm_enabled()
    editor = fallback

    if llm_enabled:
        payload = {
            "verdict": verdict.model_dump(mode="json"),
            "analyst_sections": [output.markdown for output in analyst_outputs],
            "cross_table_analysis": cross_table_analysis.model_dump(mode="json") if cross_table_analysis else None,
        }
        prompt = (
            "Write JSON with keys executive_summary, verdict_explanation, cross_table_evaluation, priority_ranking. "
            "Every value must be a detailed string, not an object and not an array. "
            "Use only the provided evidence. The executive_summary should be several sentences. "
            "The verdict_explanation should explain the decision signal and the most important evidence. "
            "The priority_ranking should name the issue clusters in practical review order. "
            "For cross_table_evaluation, write a comprehensive narrative explaining the cross-table correlations and their business meaning if they exist. "
            "If no cross-table analysis is available, return a brief statement.\n\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )
        for attempt in range(1, 4):
            try:
                text = await _call_openai_async(
                    prompt,
                    (
                        "You are an EDA Editor agent. Return valid compact JSON only. "
                        "The JSON values must be strings. Do not return nested objects or arrays. "
                        "Do not invent numbers, columns, tables, relationships, or thresholds. "
                        "Write enough detail for a data scientist to understand what to inspect first. "
                        "Do not use causal language such as causes, caused by, causing, leads to, "
                        "results in, or due to."
                    ),
                    "SMART_EDA_L4_EDITOR_MODEL",
                    "gpt-4o",
                )
                candidate = EditorOutput.model_validate_json(_strip_json_fences(text))
            except Exception as exc:
                if llm_errors is not None:
                    llm_errors.append(f"editor:attempt_{attempt}: {exc}")
                continue
            report = verify_editor_output(
                candidate.model_dump(mode="json"),
                [output.markdown for output in analyst_outputs],
                verdict,
                cross_table_analysis=cross_table_analysis,
                provider="openai-editor",
                used_fallback=False,
            )
            if report.status == "passed":
                candidate.guardrail_passed = True
                candidate.retry_count = attempt - 1
                return candidate, _agent_detail("editor", report, attempt - 1)
            if llm_errors is not None:
                violation_checks = ",".join(violation.check for violation in report.violations)
                llm_errors.append(f"editor:attempt_{attempt}: guardrail_failed:{violation_checks}")

    report = verify_editor_output(
        fallback.model_dump(mode="json"),
        [output.markdown for output in analyst_outputs],
        verdict,
        cross_table_analysis=cross_table_analysis,
        provider="deterministic-editor",
        used_fallback=llm_enabled,
    )
    fallback.guardrail_passed = report.status == "passed"
    fallback.retry_count = 3 if llm_enabled else 0
    return fallback, _agent_detail("editor", report, fallback.retry_count)


def _appendix_scope(record: Any) -> str:
    if record.affected_column:
        if isinstance(record, IntegrityError):
            return f"{record.affected_table}.{record.affected_column}"
        return record.affected_column
    if isinstance(record, IntegrityError):
        return record.affected_table
    return "dataset"


def _appendix_type(record: Any) -> str:
    return record.error_type if isinstance(record, IntegrityError) else record.issue_type


def _render_appendix_html(
    dispatch_result: DispatchResult,
    findings: DataQualityFindings | None,
    schema: SchemaEvaluationFindings | None,
) -> str:
    covered_types = {cluster.issue_type for cluster in dispatch_result.top_clusters}
    warn_rank = _severity_rank(Severity.WARN)
    rows: list[tuple[int, str, str, str, int, str]] = []

    records = [
        *(findings.anomalies if findings is not None else []),
        *(schema.integrity_errors if schema is not None else []),
    ]
    for record in records:
        issue_type = _appendix_type(record)
        severity = _effective_severity(record)
        if _severity_rank(severity) < warn_rank:
            continue
        if issue_type in covered_types:
            continue
        source = "schema" if isinstance(record, IntegrityError) else "data_quality"
        rows.append((
            _severity_rank(severity),
            severity.value,
            issue_type,
            _appendix_scope(record),
            int(record.affected_count),
            source,
        ))

    if not rows:
        return ""

    rows.sort(key=lambda row: (-row[0], row[2], row[3]))
    body = "".join(
        "<tr>"
        f"<td>{html.escape(severity)}</td>"
        f"<td>{html.escape(issue_type)}</td>"
        f"<td>{html.escape(scope)}</td>"
        f"<td>{affected_count}</td>"
        f"<td>{html.escape(source)}</td>"
        "</tr>"
        for _rank, severity, issue_type, scope, affected_count, source in rows
    )
    return (
        "<section class=\"appendix\">"
        "<h2>Appendix</h2>"
        "<p>Lower-ranked findings not expanded by Analyst agents.</p>"
        "<table>"
        "<thead><tr>"
        "<th>Severity</th><th>Type</th><th>Scope</th><th>Affected</th><th>Source</th>"
        "</tr></thead>"
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
    llm_errors: list[str] = []
    analyst_results = await asyncio.gather(*[
        _run_analyst(cluster, llm_errors)
        for cluster in dispatch_result.top_clusters
    ])
    analyst_outputs = [output for output, _detail in analyst_results]
    agent_details = [detail for _output, detail in analyst_results]
    editor_output, editor_detail = await _run_editor(
        verdict,
        list(analyst_outputs),
        cross_table_analysis,
        llm_errors,
    )
    agent_details.append(editor_detail)
    llm_enabled = _llm_enabled()
    used_fallback = (
        not llm_enabled
        or any(output.retry_count >= 3 for output in analyst_outputs)
        or editor_output.retry_count >= 3
    )
    result = MultiAgentResult(
        analyst_outputs=list(analyst_outputs),
        editor_output=editor_output,
        appendix_html=_render_appendix_html(dispatch_result, findings, schema),
        guardrail_report={},
        used_fallback=used_fallback,
    )
    text = render_multi_agent_markdown(result, verdict)
    report = validate_narrative(
        text,
        findings,
        verdict,
        schema,
        cross_table_analysis,
        provider="multi-agent",
        used_fallback=any(a.get("used_fallback", False) for a in agent_details),
    )
    report.llm_errors = llm_errors
    report.agents = agent_details
    
    # If the combined narrative still fails the guardrail, do a full fallback
    if report.status != "passed":
        text = render_deterministic_l4_report(findings, verdict, schema)
        report = validate_narrative(
            text,
            findings,
            verdict,
            schema,
            cross_table_analysis,
            provider="deterministic-fallback",
            used_fallback=True,
        )
        report.llm_errors = llm_errors
        report.agents = agent_details
        result.used_fallback = True
    else:
        result.used_fallback = any(a.get("used_fallback", False) for a in agent_details)
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
        cross_table_analysis,
        provider="deterministic-fallback",
        used_fallback=True,
    )
    report.llm_errors = [
        "L4 was called from an active event loop; deterministic fallback was used."
    ]
    report.agents = [
        _agent_detail(
            "runtime",
            report,
            retry_count=0,
            detail="active_event_loop_deterministic_fallback",
        )
    ]
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


# ============================================================
# NEW: Structured JSON Multi-Agent Pipeline (Table-based)
# ============================================================

_TABLE_ANALYST_SYSTEM_PROMPT = (
    "You are a Senior Data Scientist performing EDA on a dataset. "
    "Analyze the assigned table and return valid JSON only. "
    "The JSON must have keys: table_name (string), table_overview (string), "
    "column_issues (array of objects with keys: column_name, severity, problem, "
    "ml_consequence, suggested_action, evidence_ref). "
    "For problem: describe the issue with exact numbers from the evidence. "
    "For ml_consequence: explain how this affects model families "
    "(Linear/Logistic, Tree-based, Neural Networks, Clustering). "
    "For suggested_action: use advisory tone — suggest, do not command. "
    "For evidence_ref: use the finding_id from the evidence JSON if available, otherwise null. "
    "Do not invent numbers, columns, or tables not in the evidence. "
    "Do not use causal language such as causes, caused by, leads to, results in, or due to."
)

_TABLE_ANALYST_USER_PROMPT_TEMPLATE = (
    "Analyze this table and return structured JSON. "
    "Include only columns with issues at WARN severity or above. "
    "Use only the evidence provided below.\n\n"
    "{json_slice}"
)

_EDITOR_STRUCTURED_SYSTEM_PROMPT = (
    "You are a Senior Data Scientist writing an executive summary of a data quality report. "
    "Return valid JSON only with these keys: "
    "executive_summary (string — several sentences), "
    "feature_usability (array of objects with keys: column, status, reason "
    "where status is 'ready' or 'needs_work' or 'drop'), "
    "fix_priority (array of strings — column names in priority order), "
    "cross_table_evaluation (string or null), "
    "verdict_explanation (string). "
    "Do not invent numbers or columns not in the evidence. "
    "Use advisory tone throughout."
)


def _build_deterministic_table_result(table_cluster: TableCluster) -> AnalystTableResult:
    """Deterministic fallback: tạo AnalystTableResult từ TableCluster không cần LLM."""
    column_issues: list[ColumnIssue] = []
    # Gom issues theo cột
    col_issues_map: dict[str, list[dict]] = {}
    for issue in table_cluster.issues:
        col = issue.get("affected_column") or issue.get("affected_table") or "dataset"
        col_issues_map.setdefault(col, []).append(issue)

    for col_name, issues in col_issues_map.items():
        for issue in issues:
            severity = issue.get("compound_severity") or issue.get("severity", "WARN")
            issue_type = issue.get("issue_type") or issue.get("error_type", "UNKNOWN")
            affected_count = issue.get("affected_count", 0)
            affected_percent = issue.get("affected_percent")
            pct_str = f" ({affected_percent:.1%})" if affected_percent is not None else ""

            column_issues.append(ColumnIssue(
                column_name=col_name,
                severity=severity,
                problem=(
                    f"{issue_type}: {issue.get('description', 'Issue detected')}. "
                    f"Affected: {affected_count} rows{pct_str}."
                ),
                ml_consequence="Review this column before using in modeling.",
                suggested_action="Inspect the affected rows and decide on remediation.",
                evidence_ref=issue.get("finding_id"),
            ))

    return AnalystTableResult(
        table_name=table_cluster.table_name,
        table_overview=(
            f"Table '{table_cluster.table_name}' has {len(table_cluster.issues)} issues "
            f"(max severity: {table_cluster.max_severity}) "
            f"across {len(table_cluster.affected_columns)} columns."
        ),
        column_issues=column_issues,
        guardrail_passed=True,
        retry_count=0,
    )


async def _run_table_analyst(
    table_cluster: TableCluster,
    llm_errors: list[str] | None = None,
) -> tuple[AnalystTableResult, dict[str, Any]]:
    """Analyst agent per TABLE — trả AnalystTableResult (structured JSON)."""
    fallback = _build_deterministic_table_result(table_cluster)
    llm_enabled = _llm_enabled()

    if llm_enabled:
        prompt = _TABLE_ANALYST_USER_PROMPT_TEMPLATE.format(
            json_slice=json.dumps(table_cluster.json_slice, ensure_ascii=False, indent=2),
        )
        for attempt in range(1, 4):
            try:
                text = await _call_openai_async(
                    prompt,
                    _TABLE_ANALYST_SYSTEM_PROMPT,
                    "SMART_EDA_L4_ANALYST_MODEL",
                    "gpt-4o-mini",
                )
                candidate = AnalystTableResult.model_validate_json(
                    _strip_json_fences(text)
                )
                candidate.guardrail_passed = True
                candidate.retry_count = attempt - 1
                # Basic validation: table_name should match
                if candidate.table_name != table_cluster.table_name:
                    candidate.table_name = table_cluster.table_name
                return candidate, {
                    "agent": "table_analyst",
                    "status": "passed",
                    "provider": "openai-table-analyst",
                    "used_fallback": False,
                    "retry_count": attempt - 1,
                    "table": table_cluster.table_name,
                }
            except Exception as exc:
                if llm_errors is not None:
                    llm_errors.append(
                        f"table_analyst:{table_cluster.table_name}:attempt_{attempt}: {exc}"
                    )
                continue

    return fallback, {
        "agent": "table_analyst",
        "status": "fallback",
        "provider": "deterministic-table-analyst",
        "used_fallback": llm_enabled,
        "retry_count": 3 if llm_enabled else 0,
        "table": table_cluster.table_name,
    }


async def _run_structured_editor(
    verdict: DatasetVerdict,
    analyst_results: list[AnalystTableResult],
    cross_table_analysis: CrossTableAnalysis | None,
    findings: DataQualityFindings | None = None,
    schema: SchemaEvaluationFindings | None = None,
    schema_gate: SchemaGateResult | None = None,
    llm_errors: list[str] | None = None,
) -> tuple[EditorStructuredOutput, dict[str, Any]]:
    """Editor agent — nhận structured JSON từ Analyst, trả EditorStructuredOutput."""
    # Build deterministic fallback
    all_columns_ok: list[FeatureUsabilityItem] = []
    all_columns_issues: list[FeatureUsabilityItem] = []
    fix_priority: list[str] = []

    for result in analyst_results:
        for issue in result.column_issues:
            status = "drop" if issue.severity == "CRITICAL" else "needs_work"
            all_columns_issues.append(FeatureUsabilityItem(
                column=issue.column_name,
                status=status,
                reason=f"[{issue.severity}] {issue.problem[:80]}",
            ))
            fix_priority.append(f"{result.table_name}.{issue.column_name}")

    meta = verdict.dataset_meta
    fallback = EditorStructuredOutput(
        executive_summary=(
            f"Dataset '{meta.file_name}' has {meta.n} rows and {meta.n_var} columns. "
            f"Verdict: {verdict.verdict.value} with {verdict.summary.total_issues} total issues."
        ),
        feature_usability=all_columns_issues,
        fix_priority=fix_priority,
        cross_table_evaluation=_cross_table_summary(cross_table_analysis),
        verdict_explanation=verdict.verdict_rationale,
    )

    llm_enabled = _llm_enabled()
    if llm_enabled:
        payload = {
            "verdict": verdict.model_dump(mode="json"),
            "analyst_results": [r.model_dump(mode="json") for r in analyst_results],
            "cross_table_analysis": (
                cross_table_analysis.model_dump(mode="json")
                if cross_table_analysis else None
            ),
        }
        # Inject extra context
        if findings:
            payload["columns"] = {
                name: stats.model_dump(exclude_none=True)
                for name, stats in findings.columns.items()
            }
        if schema_gate:
            payload["schema_mode"] = schema_gate.mode
        if schema and schema.relationships:
            payload["relationship_cardinalities"] = [
                f"{r.child_table}.{r.child_column} -> {r.parent_table}.{r.parent_column}: {r.cardinality}"
                for r in schema.relationships if r.cardinality
            ]

        prompt = (
            "Write a structured JSON executive summary for this data quality report. "
            "Include feature_usability for ALL columns mentioned in analyst_results. "
            "Order fix_priority by severity (CRITICAL first).\n\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
        )
        for attempt in range(1, 4):
            try:
                text = await _call_openai_async(
                    prompt,
                    _EDITOR_STRUCTURED_SYSTEM_PROMPT,
                    "SMART_EDA_L4_EDITOR_MODEL",
                    "gpt-4o",
                )
                candidate = EditorStructuredOutput.model_validate_json(
                    _strip_json_fences(text)
                )
                candidate.guardrail_passed = True
                candidate.retry_count = attempt - 1
                return candidate, {
                    "agent": "structured_editor",
                    "status": "passed",
                    "provider": "openai-structured-editor",
                    "used_fallback": False,
                    "retry_count": attempt - 1,
                }
            except Exception as exc:
                if llm_errors is not None:
                    llm_errors.append(f"structured_editor:attempt_{attempt}: {exc}")
                continue

    return fallback, {
        "agent": "structured_editor",
        "status": "fallback",
        "provider": "deterministic-structured-editor",
        "used_fallback": llm_enabled,
        "retry_count": 3 if llm_enabled else 0,
    }


def render_table_result_html(result: AnalystTableResult) -> str:
    """Python Renderer: chuyển AnalystTableResult JSON → HTML đẹp.

    LLM chỉ cung cấp nội dung (problem, ml_consequence, suggested_action).
    Hình thức (icon, heading, format) do code Python quyết định → 100% đồng nhất.
    """
    parts: list[str] = []
    table_icon = "📦"
    parts.append(f'<div class="table-health-section">')
    parts.append(f'<h3>{table_icon} Bảng: <code>{html.escape(result.table_name)}</code></h3>')
    parts.append(f'<p class="table-overview">🌟 {html.escape(result.table_overview)}</p>')

    if not result.column_issues:
        parts.append('<p class="no-issues">✅ Không phát hiện vấn đề nào từ mức WARN trở lên.</p>')
    else:
        for issue in result.column_issues:
            sev_class = issue.severity.lower()
            sev_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "WARN": "🟡"}.get(issue.severity, "⚪")
            parts.append(f'<div class="column-issue severity-{sev_class}">')
            parts.append(f'<h4>🔸 Cột: <code>{html.escape(issue.column_name)}</code></h4>')
            parts.append(
                f'<p class="issue-problem">{sev_icon} '
                f'<strong>[{html.escape(issue.severity)}]</strong> '
                f'{html.escape(issue.problem)}</p>'
            )
            parts.append(
                f'<p class="issue-ml"><strong>ML Consequence:</strong> '
                f'{html.escape(issue.ml_consequence)}</p>'
            )
            parts.append(
                f'<p class="issue-action"><strong>Gợi ý tham khảo:</strong> '
                f'{html.escape(issue.suggested_action)}</p>'
            )
            if issue.evidence_ref:
                parts.append(
                    f'<p class="evidence-ref"><small>Evidence: '
                    f'<code>{html.escape(issue.evidence_ref)}</code></small></p>'
                )
            parts.append('</div>')

    parts.append('</div>')
    return "\n".join(parts)


def render_editor_structured_html(editor: EditorStructuredOutput) -> str:
    """Python Renderer: chuyển EditorStructuredOutput → HTML cho Phần 1."""
    parts: list[str] = []

    # Executive Summary
    parts.append(f'<div class="executive-summary">')
    parts.append(f'<p>{html.escape(editor.executive_summary)}</p>')
    parts.append('</div>')

    # Feature Usability Summary
    if editor.feature_usability:
        status_icons = {"ready": "✅", "needs_work": "⚠️", "drop": "❌"}
        parts.append('<div class="feature-usability">')
        parts.append('<h3>Feature Usability Summary</h3>')
        parts.append('<table><thead><tr>')
        parts.append('<th>Trạng thái</th><th>Cột</th><th>Lý do</th>')
        parts.append('</tr></thead><tbody>')
        for item in editor.feature_usability:
            icon = status_icons.get(item.status, "❓")
            parts.append(
                f'<tr><td>{icon}</td>'
                f'<td><code>{html.escape(item.column)}</code></td>'
                f'<td>{html.escape(item.reason)}</td></tr>'
            )
        parts.append('</tbody></table>')
        parts.append('</div>')

    # Fix Priority
    if editor.fix_priority:
        parts.append('<div class="fix-priority">')
        parts.append('<h3>Fix Priority</h3>')
        parts.append('<ol>')
        for col in editor.fix_priority:
            parts.append(f'<li><code>{html.escape(col)}</code></li>')
        parts.append('</ol>')
        parts.append('</div>')

    # Verdict Explanation
    if editor.verdict_explanation:
        parts.append(f'<div class="verdict-explanation">')
        parts.append(f'<h3>Decision Rationale</h3>')
        parts.append(f'<p>{html.escape(editor.verdict_explanation)}</p>')
        parts.append('</div>')

    # Cross-table Evaluation
    if editor.cross_table_evaluation:
        parts.append(f'<div class="cross-table-eval">')
        parts.append(f'<h3>Cross-Table Evaluation</h3>')
        parts.append(f'<p>{html.escape(editor.cross_table_evaluation)}</p>')
        parts.append('</div>')

    return "\n".join(parts)


async def run_structured_multi_agent_l4(
    findings: DataQualityFindings | None,
    verdict: DatasetVerdict,
    schema: SchemaEvaluationFindings | None = None,
    cross_table_analysis: CrossTableAnalysis | None = None,
    schema_gate: SchemaGateResult | None = None,
) -> tuple[str, MultiAgentResult]:
    """Luồng multi-agent MỚI: gom theo Table, output JSON, Python render HTML."""
    # Step 1: Dispatch theo table
    dispatch_result = dispatch_by_table(
        findings.anomalies if findings else [],
        schema.integrity_errors if schema else [],
        columns=findings.columns if findings else None,
    )

    llm_errors: list[str] = []

    # Step 2: Fan-out Analyst per table (song song)
    analyst_tasks = [
        _run_table_analyst(tc, llm_errors)
        for tc in dispatch_result.table_clusters
    ]
    analyst_results_raw = await asyncio.gather(*analyst_tasks)
    analyst_table_results = [result for result, _detail in analyst_results_raw]
    agent_details = [detail for _result, detail in analyst_results_raw]

    # Step 3: Editor tổng hợp
    editor_structured, editor_detail = await _run_structured_editor(
        verdict,
        analyst_table_results,
        cross_table_analysis,
        findings=findings,
        schema=schema,
        schema_gate=schema_gate,
        llm_errors=llm_errors,
    )
    agent_details.append(editor_detail)

    # Step 4: Python render JSON → HTML
    html_parts: list[str] = []

    # Phần 1: Executive Dashboard
    html_parts.append(render_editor_structured_html(editor_structured))

    # Phần 2: Table-by-Table Health Check
    html_parts.append('<div class="table-health-checks">')
    html_parts.append('<h2>Table-by-Table Health Check</h2>')
    for result in analyst_table_results:
        html_parts.append(render_table_result_html(result))
    html_parts.append('</div>')

    rendered_html = "\n".join(html_parts)

    # Build MultiAgentResult
    used_fallback = any(
        detail.get("used_fallback", False) for detail in agent_details
    )
    multi_result = MultiAgentResult(
        analyst_table_results=analyst_table_results,
        editor_structured=editor_structured,
        appendix_html=_render_appendix_html(dispatch_result, findings, schema),
        guardrail_report={"agents": agent_details, "llm_errors": llm_errors},
        used_fallback=used_fallback,
    )

    return rendered_html, multi_result


def generate_structured_report(
    findings: DataQualityFindings | None,
    verdict: DatasetVerdict,
    schema: SchemaEvaluationFindings | None = None,
    cross_table_analysis: CrossTableAnalysis | None = None,
    schema_gate: SchemaGateResult | None = None,
) -> tuple[str, MultiAgentResult]:
    """Sync wrapper cho luồng structured mới."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            run_structured_multi_agent_l4(
                findings, verdict, schema, cross_table_analysis, schema_gate
            )
        )
    # Fallback nếu đang trong event loop
    html_parts = []
    if findings:
        dispatch_result = dispatch_by_table(
            findings.anomalies, 
            schema.integrity_errors if schema else [],
            columns=findings.columns,
        )
        for tc in dispatch_result.table_clusters:
            fallback = _build_deterministic_table_result(tc)
            html_parts.append(render_table_result_html(fallback))

    return "\n".join(html_parts), MultiAgentResult(used_fallback=True)
