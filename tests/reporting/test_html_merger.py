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


def test_merge_to_tabbed_html_renders_overview_tab():
    """Tab Tổng quan phải xuất hiện, chart từ overview_charts phải được nhúng vào."""
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

    # Tab layout mới — Tổng quan là tab đầu tiên
    assert "tab-overview" in html
    assert "tab-button-overview" in html
    assert "Tổng Quan" in html

    # Các chart từ overview_charts phải xuất hiện trong HTML (trong tab bảng)
    assert "data__overview_missingness_bar.png" in html
    assert "data__overview_correlation_heatmap.png" in html

    # Profile link xuất hiện trong tab bảng (không còn ở Tổng Quan)
    assert "statistical_profile.html" in html

    # Không dùng srcdoc embed
    assert "srcdoc=" not in html

    # Science brief vẫn ở tab Tổng quan
    assert "Data Science Brief" in html
    # _visual_overview đã bỏ khỏi Tổng Quan, chỉ còn trong _agent_content (legacy)

    # Guardrail status chip
    assert "guardrail-passed" in html

    # Provider info
    assert "openai-multi-agent" in html

    # Analyst outputs vẫn render được (legacy analyst_outputs path)
    assert "MISSINGNESS" in html


def test_merge_to_tabbed_html_per_table_tabs():
    """Khi có analyst_table_results, phải tạo tab riêng cho từng bảng."""
    from ontology.models import AnalystTableResult, ColumnIssue

    verdict = DatasetVerdict(
        dataset_meta=DatasetMeta(
            file_name="customers.csv",
            n=100,
            n_var=5,
            memory_size=0,
            p_cells_missing=0.1,
        ),
        verdict=Verdict.NOT_READY,
        verdict_rationale="Critical issues found",
        summary=VerdictSummary(total_issues=2, critical=1, high=1),
    )
    table_result = AnalystTableResult(
        table_name="customers",
        table_overview="Bảng khách hàng có vấn đề nghiêm trọng.",
        column_issues=[
            ColumnIssue(
                column_name="email",
                severity="CRITICAL",
                problem="50% giá trị null.",
                ml_consequence="Ảnh hưởng mọi mô hình dùng email.",
                suggested_action="Điền hoặc loại cột.",
            )
        ],
    )
    result = MultiAgentResult(
        analyst_table_results=[table_result],
        guardrail_report={},
        used_fallback=True,
    )

    html = merge_to_tabbed_html(result, verdict, "", guardrail_status="passed")

    # Tab cho bảng customers phải xuất hiện
    assert "tab-customers" in html
    assert "tab-button-customers" in html
    assert "customers" in html

    # Tab Tổng quan vẫn có
    assert "tab-overview" in html

    # Nội dung của table analyst
    assert "email" in html
    assert "CRITICAL" in html
    assert "50% giá trị null" in html

    # Verdict headline tiếng Việt, không còn "Do not use"
    assert "Do not use" not in html
    assert "cần xử lý" in html.lower() or "nghiêm trọng" in html.lower()


def test_merge_to_tabbed_html_verdict_headline_vietnamese():
    """Verdict headline phải là tiếng Việt, không giả định use-case."""
    verdict = DatasetVerdict(
        dataset_meta=DatasetMeta(
            file_name="data.csv",
            n=10,
            n_var=2,
            memory_size=0,
            p_cells_missing=0.0,
        ),
        verdict=Verdict.NOT_READY,
        verdict_rationale="Critical issues",
        summary=VerdictSummary(total_issues=3, critical=2, high=1),
    )
    result = MultiAgentResult(used_fallback=True)

    html = merge_to_tabbed_html(result, verdict, "", guardrail_status="failed")

    # Không còn hardcode tiếng Anh
    assert "Do not use this dataset for downstream analysis" not in html
    assert "Usable only after analyst review" not in html
    assert "No blocking data-quality issues detected" not in html


def test_merge_to_tabbed_html_feature_usability_has_table_col():
    """Bảng Feature Usability phải có cột Bảng khi table_name được điền."""
    from ontology.models import (
        AnalystTableResult, ColumnIssue,
        EditorStructuredOutput, FeatureUsabilityItem,
    )

    verdict = DatasetVerdict(
        dataset_meta=DatasetMeta(
            file_name="data.csv",
            n=10,
            n_var=2,
            memory_size=0,
            p_cells_missing=0.0,
        ),
        verdict=Verdict.WARN,
        verdict_rationale="Needs review",
        summary=VerdictSummary(total_issues=1, warn=1),
    )
    editor = EditorStructuredOutput(
        executive_summary="Dataset ổn.",
        feature_usability=[
            FeatureUsabilityItem(
                column="age",
                table_name="customers",
                status="needs_work",
                reason="Có 5% null.",
            )
        ],
        fix_priority=["customers.age"],
        verdict_explanation="Cần kiểm tra thêm.",
    )
    result = MultiAgentResult(
        editor_structured=editor,
        guardrail_report={},
        used_fallback=True,
    )

    html = merge_to_tabbed_html(result, verdict, "", guardrail_status="passed")

    # Cột Bảng phải xuất hiện trong header bảng
    assert "<th>Bảng</th>" in html
    # table_name hiển thị
    assert "customers" in html
    # Status badge với text mức độ (không còn prescriptive label)
    assert "Có vấn đề" in html
    assert "status-needs-work" in html
