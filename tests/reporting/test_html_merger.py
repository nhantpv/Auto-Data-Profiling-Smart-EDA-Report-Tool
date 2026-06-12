from ontology.models import (
    AnalystOutput,
    DatasetMeta,
    DatasetVerdict,
    EditorOutput,
    MultiAgentResult,
    Verdict,
    VerdictSummary,
)
from reporting.html_merger import merge_to_tabbed_html


def test_merge_to_tabbed_html_renders_ai_and_ydata_tabs():
    verdict = DatasetVerdict(
        dataset_meta=DatasetMeta(
            file_name="data.csv",
            n=12,
            n_var=3,
            memory_size=0,
            p_cells_missing=0.25,
        ),
        verdict=Verdict.WARN,
        verdict_rationale="Needs review",
        summary=VerdictSummary(total_issues=1, warn=1),
    )
    result = MultiAgentResult(
        analyst_outputs=[AnalystOutput(cluster_type="MISSINGNESS", markdown="### `MISSINGNESS`\n\nOK")],
        editor_output=EditorOutput(executive_summary="Dataset has 12 rows."),
        guardrail_report={
            "provider": "openai-multi-agent",
            "agents": [
                {
                    "agent": "analyst",
                    "cluster": "MISSINGNESS",
                    "provider": "openai-analyst",
                    "status": "passed",
                    "used_fallback": False,
                    "retry_count": 0,
                },
                {
                    "agent": "editor",
                    "provider": "openai-editor",
                    "status": "passed",
                    "used_fallback": False,
                    "retry_count": 0,
                },
            ],
        },
        used_fallback=True,
    )

    html = merge_to_tabbed_html(result, verdict, "<h1>YData</h1>", guardrail_status="passed")

    assert "tab-ai" in html
    assert "tab-stats" in html
    assert "Data Science Report" in html
    assert "Data Science Brief" in html
    assert "Immediate Attention" in html
    assert "No ranked issue details were included." in html
    assert "Executive Interpretation" in html
    assert "What the data scientist should notice first" in html
    assert "Evidence Review" in html
    assert "Guardrailed analyst notes" in html
    assert "Statistical Workbench" in html
    assert "Profile Diagnostics" in html
    assert "Completeness" in html
    assert "Severity Distribution" in html
    assert "profile-viewer" in html
    assert "LLM Agent Review" in html
    assert "Guardrailed L4 Comments" in html
    assert "openai-analyst" in html
    assert "openai-editor" in html
    assert "MISSINGNESS" in html
    assert "<code>MISSINGNESS</code>" in html
    assert "insight-list" in html
    assert "&lt;h1&gt;YData&lt;/h1&gt;" in html
