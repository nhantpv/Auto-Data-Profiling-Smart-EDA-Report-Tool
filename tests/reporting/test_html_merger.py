from ontology.models import (
    AnalystOutput,
    DatasetMeta,
    DatasetVerdict,
    EditorOutput,
    IssueSummary,
    MultiAgentResult,
    Severity,
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
            n_duplicates=1,
            p_duplicates=0.0833,
            overview_charts={
                "missingness_bar": "data__overview_missingness_bar.png",
                "correlation_heatmap": "data__overview_correlation_heatmap.png",
            },
        ),
        verdict=Verdict.WARN,
        verdict_rationale="Needs review",
        summary=VerdictSummary(total_issues=1, warn=1),
        top_issues=[
            IssueSummary(
                source="data_quality",
                issue_type="MISSINGNESS",
                effective_severity=Severity.HIGH,
                severity=Severity.HIGH,
                affected_column="age",
                affected_count=2,
                rationale="Column age has missing values",
            )
        ],
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

    profile_fragment = (
        "<!-- smart-eda-profile-fragment -->"
        "<section class=\"profile-viewer profile-export-panel\">"
        "<div class=\"profile-export-grid\">"
        "<article class=\"profile-export-card\"><strong>statistical_profile.html</strong>"
        "<a href=\"statistical_profile.html\">Open profile</a></article>"
        "</div></section>"
    )
    html = merge_to_tabbed_html(result, verdict, profile_fragment, guardrail_status="passed")

    assert "tab-ai" in html
    assert "tab-stats" in html
    assert "Data Science Report" in html
    assert "Data Science Brief" in html
    assert "Visual Data Science Overview" in html
    assert "Charts to inspect immediately" in html
    assert "Generated Data Charts" in html
    assert "Missingness Bar" in html
    assert "Correlation Heatmap" in html
    assert "data__overview_missingness_bar.png" in html
    assert "data__overview_correlation_heatmap.png" in html
    assert "Immediate Attention" in html
    assert "Issues that should drive the next action" in html
    assert "Executive Interpretation" in html
    assert "What the data scientist should notice first" in html
    assert "Evidence Review" in html
    assert "Guardrailed analyst notes" in html
    assert "Statistical Workbench" in html
    assert "Profile Diagnostics" in html
    assert "Completeness" in html
    assert "Severity Distribution" in html
    assert "profile-viewer" in html
    assert "profile-export-grid" in html
    assert "statistical_profile.html" in html
    assert "Open profile" in html
    assert "srcdoc=" not in html
    assert "LLM Agent Review" in html
    assert "Guardrailed L4 Comments" in html
    assert "openai-analyst" in html
    assert "openai-editor" in html
    assert "MISSINGNESS" in html
    assert "<code>MISSINGNESS</code>" in html
    assert "cluster-summary-card" in html
    assert "Completeness risk" in html
    assert "Affected rows" in html
    assert "Column age has missing values" in html
    assert "View full analyst notes" in html
    assert "openai-analyst · llm · retries 0" in html
    assert "openai-analyst · guardrail passed · llm" not in html
    assert "insight-list" in html


def test_merge_to_tabbed_html_keeps_legacy_ydata_collapsed():
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
    result = MultiAgentResult(editor_output=EditorOutput(executive_summary="Dataset has 12 rows."))

    html = merge_to_tabbed_html(result, verdict, "<h1>YData</h1>", guardrail_status="passed")

    assert "View legacy embedded profile" in html
    assert "&lt;h1&gt;YData&lt;/h1&gt;" in html
