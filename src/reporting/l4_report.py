"""L4 Multi-Agent Report — Luồng duy nhất: Structured JSON Table-based.

Kiến trúc:
  dispatch_by_table() → _run_table_analyst() × N (song song) → _run_structured_editor()
  → Python Renderer (JSON → HTML)

LLM output là tiếng Việt. JSON chỉ là ngôn ngữ nội bộ giữa các agent;
người dùng chỉ thấy HTML đã được render.

Xem ARCHITECT v5.4 §5.9 và implementation_plan.md.
"""
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
)
from ontology.models import (
    AnalystTableResult,
    ColumnIssue,
    CrossTableAnalysis,
    DataQualityFindings,
    DatasetVerdict,
    DispatchResult,
    EditorStructuredOutput,
    FeatureUsabilityItem,
    IntegrityError,
    MultiAgentResult,
    SEVERITY_ORDER,
    SchemaEvaluationFindings,
    SchemaGateResult,
    Severity,
    TableCluster,
)
from reporting.dispatcher import dispatch_by_table


# ============================================================
# Shared Utilities
# ============================================================

def _pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def _severity_rank(severity: Severity) -> int:
    return SEVERITY_ORDER.index(severity)


def _effective_severity(record: Any) -> Severity:
    return record.compound_severity if record.compound_severity is not None else record.severity


def _strip_json_fences(text: str) -> str:
    """Loại bỏ markdown code fences (```json ... ```) nếu có."""
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


def _llm_enabled() -> bool:
    return os.getenv("SMART_EDA_L4_PROVIDER", "deterministic").strip().lower() == "openai"


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
        raise RuntimeError("OPENAI_API_KEY chưa được thiết lập")

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
        raise RuntimeError(f"SMART_EDA_L4_API_MODE không hợp lệ: {api_mode}")

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
        raise RuntimeError(f"OpenAI L4 request thất bại ({api_mode}): HTTP {exc.code} {body}") from exc

    text = extractor(response_payload)
    if not text:
        raise RuntimeError(f"OpenAI L4 {api_mode} response không chứa text")
    return text


async def _call_openai_async(
    prompt: str,
    instructions: str,
    model_env: str,
    default_model: str,
) -> str:
    return await asyncio.to_thread(_call_openai, prompt, instructions, model_env, default_model)


def _cross_table_summary(cross_table_analysis: CrossTableAnalysis | None) -> str | None:
    if cross_table_analysis is None:
        return None
    if cross_table_analysis.status != "completed":
        return f"Phân tích cross-table có trạng thái: {cross_table_analysis.status}."
    if cross_table_analysis.planned_correlations:
        top = cross_table_analysis.planned_correlations[0]
        return (
            f"L3b đã xác nhận cặp cross-table theo kế hoạch: {top.left_feature} và {top.right_feature}. "
            "Mối quan hệ được xem là tương quan, không phải nhân quả."
        )
    if cross_table_analysis.correlations:
        top = cross_table_analysis.correlations[0]
        return (
            f"Phân tích cross-table dùng fact table {cross_table_analysis.fact_table}. "
            f"Cặp Pearson mạnh nhất: {top.left_feature} và {top.right_feature}."
        )
    return f"Phân tích cross-table dùng fact table {cross_table_analysis.fact_table}."


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
    """Phụ lục: các findings mức WARN+ chưa được Analyst expand."""
    covered_tables = {tc.table_name for tc in dispatch_result.table_clusters}
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
        "<h2>Phụ lục — Các Vấn Đề Chưa Được Phân Tích Sâu</h2>"
        "<p>Các findings mức WARN trở lên chưa được Analyst agent phân tích chi tiết.</p>"
        "<table>"
        "<thead><tr>"
        "<th>Mức độ</th><th>Loại</th><th>Phạm vi</th><th>Số dòng ảnh hưởng</th><th>Nguồn</th>"
        "</tr></thead>"
        f"<tbody>{body}</tbody>"
        "</table>"
        "</section>"
    )


# ============================================================
# LLM Prompts — Tiếng Việt
# ============================================================

_TABLE_ANALYST_SYSTEM_PROMPT = (
    "Bạn là một Senior Data Scientist đang thực hiện EDA (Phân tích Dữ liệu Khám phá) trên một dataset. "
    "Hãy phân tích bảng được giao và trả về JSON hợp lệ DUY NHẤT, không thêm bất kỳ text nào khác. "
    "JSON phải có các khóa sau: "
    "table_name (string — tên bảng), "
    "table_overview (string — nhận xét tổng quan về bảng bằng tiếng Việt), "
    "column_issues (mảng các object với các khóa: column_name, severity, problem, ml_consequence, suggested_action, evidence_ref). "
    "Yêu cầu cụ thể: "
    "- problem: mô tả vấn đề bằng tiếng Việt với con số chính xác từ evidence. "
    "- ml_consequence: giải thích ảnh hưởng đến các nhóm thuật toán ML bằng tiếng Việt "
    "(Linear/Logistic Regression, Tree-based, Neural Networks, Clustering). "
    "- suggested_action: viết dưới góc độ Data Scientist tư vấn trực tiếp. Phải bao gồm: "
    "(1) kỹ thuật xử lý cụ thể phù hợp với loại vấn đề (ví dụ: mean/median/KNN/MICE imputation, "
    "log-transform, IQR clipping, deduplication theo key, target encoding, cast kiểu dữ liệu); "
    "(2) điều kiện hoặc trade-off cần lưu ý trước khi áp dụng; "
    "(3) thứ tự ưu tiên nếu có nhiều lựa chọn. Dùng giọng đề xuất, không ra lệnh. "
    "Tham chiếu issue_type trong evidence để chọn hướng xử lý phù hợp: "
    "MISSINGNESS→imputation strategy; PK_DUPLICATE→dedup; ORPHAN_FOREIGN_KEY→kiểm tra join; "
    "OUTLIER_RATE_HIGH→clip/transform; SKEWNESS_HIGH→log/box-cox; DUPLICATE_ROWS→dedup; "
    "HIGH_CARDINALITY→encoding strategy; TYPE_MISMATCH→cast với error handling; CONSTANT_COLUMN→loại khỏi feature set. "
    "- evidence_ref: dùng finding_id từ JSON evidence nếu có, ngược lại để null. "
    "- severity: chỉ dùng một trong ba giá trị: CRITICAL, HIGH, WARN. "
    "NGHIÊM CẤM: bịa đặt con số, tên cột, tên bảng không có trong evidence. "
    "NGHIÊM CẤM: dùng ngôn ngữ nhân quả như 'gây ra', 'dẫn đến', 'do', 'vì'."
)

_TABLE_ANALYST_USER_PROMPT_TEMPLATE = (
    "Hãy phân tích bảng sau và trả về JSON có cấu trúc. "
    "Chỉ đưa vào column_issues những cột có vấn đề từ mức WARN trở lên. "
    "Viết tất cả nhận xét bằng tiếng Việt. "
    "Chỉ sử dụng thông tin trong evidence dưới đây:\n\n"
    "{json_slice}"
)

_EDITOR_STRUCTURED_SYSTEM_PROMPT = (
    "Bạn là một Senior Data Scientist đang tư vấn trực tiếp cho engineering team về chất lượng dữ liệu. "
    "Trả về JSON hợp lệ DUY NHẤT, không thêm bất kỳ text nào khác. "
    "JSON phải có các khóa sau: "
    "executive_summary (string bằng tiếng Việt, TỐI THIỂU 12 câu), "
    "feature_usability (mảng object với các khóa: column, table_name, status, reason — "
    "trong đó status chỉ là một trong ba giá trị: 'ready', 'needs_work', 'drop', "
    "table_name là tên bảng chứa cột, reason viết bằng tiếng Việt), "
    "fix_priority (mảng string — tên cột theo thứ tự ưu tiên xử lý), "
    "cross_table_evaluation (string bằng tiếng Việt, TỐI THIỂU 4 câu — hoặc null nếu không có dữ liệu liên bảng), "
    "verdict_explanation (string — giải thích verdict bằng tiếng Việt). "
    "YÊU CẦU executive_summary phải có ĐẦY ĐỦ CÁC PHẦN SAU: "
    "(1) Tổng quan dataset: số bảng, tổng số cột, tổng số dòng, verdict và lý do cụ thể với con số. "
    "(2) Các vấn đề nghiêm trọng nhất (CRITICAL/HIGH) — đề cập ĐÍch danh tên bảng và tên cột bị ảnh hưởng, "
    "kèm số dòng/tỷ lệ cụ thể từ top_issues. "
    "(3) Tỷ lệ thiếu dữ liệu và trùng lặp nếu > 1%. "
    "(4) Hệ quả cụ thể nếu dùng dataset này cho ML: ít nhất 2 hệ quả kỹ thuật "
    "(ví dụ: Linear Regression bị bias do missing MAR, FK violation khiến JOIN trả thiếu rows, "
    "duplicate làm overfit trong train set...). "
    "(5) Phần cuối BẮT BUỘC là 'Khuyến nghị ưu tiên:' — liệt kê 3-5 hành động cụ thể theo thứ tự tác động "
    "(cao → thấp), viết dưới góc độ chuyên gia đang tư vấn trực tiếp, KHÔNG mô tả lại vấn đề. "
    "Dùng giọng: 'Chúng tôi khuyến nghị...', 'Ưu tiên xử lý...', 'Có thể bỏ qua... nếu...'. "
    "Mỗi khuyến nghị phải chỉ rõ kỹ thuật cụ thể (ví dụ: MICE imputation, dedup theo surrogate key, "
    "cast kiểu với pd.to_numeric(errors='coerce'), log1p transform trước khi train). "
    "NGHIÊM CẤM: bịa đặt con số hoặc tên cột không có trong evidence. "
    "Dùng giọng tư vấn, tránh ngôn ngữ nhân quả."
)


# ============================================================
# Deterministic Fallback (0 LLM call)
# ============================================================

# Per-issue-type action suggestions for deterministic fallback (Issue 6)
_DETERMINISTIC_SUGGESTIONS: dict[str, str] = {
    "PK_DUPLICATE": (
        "Thực hiện deduplication: giữ bản ghi mới nhất (theo timestamp) hoặc bản ghi có nhiều dữ liệu nhất. "
        "Kiểm tra upstream ETL pipeline để ngăn tái phát. Cân nhắc thêm UNIQUE constraint ở database layer. "
        "Ưu tiên fix trước vì PK duplicate phá vỡ tính toàn vẹn của mọi phép JOIN."
    ),
    "COMPOSITE_PK_DUPLICATE": (
        "Tìm các tuple (key1, key2) bị trùng và quyết định giữ bản ghi nào (mới nhất hoặc merge). "
        "Kiểm tra xem có đúng là composite PK hay cần thêm cột thứ ba vào key. "
        "Thêm UNIQUE(col1, col2) constraint sau khi đã dedup."
    ),
    "PK_NULL": (
        "Điều tra tại sao PK có NULL — có thể do lỗi ETL hoặc optional entity. "
        "Nếu cần giữ: gán surrogate key (UUID hoặc sequence) cho các row bị NULL. "
        "Nếu không cần: xóa các row không có identity. Đây là blocker cho mọi JOIN."
    ),
    "ORPHAN_FOREIGN_KEY": (
        "Không JOIN trực tiếp khi còn FK violation. Trước tiên: LEFT JOIN để đếm orphan rows. "
        "Quyết định hướng xử lý: (1) SET NULL nếu FK là optional, "
        "(2) xóa orphan rows nếu business logic cho phép, "
        "(3) fix upstream để đảm bảo parent records tồn tại trước khi insert child. "
        "Ưu tiên cao vì sẽ gây mất dữ liệu âm thầm trong aggregation."
    ),
    "NON_UNIQUE_PARENT_PK": (
        "Bảng cha có PK không unique sẽ nhân rows khi JOIN — cần dedup bảng cha trước. "
        "Dùng ROW_NUMBER() OVER (PARTITION BY pk ORDER BY ...) để chọn bản ghi đại diện. "
        "Sau dedup, thêm UNIQUE constraint để prevent tái phát."
    ),
    "MISSINGNESS": (
        "Xem cơ chế thiếu (MAR/MCAR/MNAR) trong bảng Missingness Diagnostic. "
        "Nếu MAR: dùng KNN imputation hoặc MICE thay vì mean/median blind — pattern thiếu có thể dự đoán. "
        "Nếu MCAR: mean/median/mode an toàn, listwise deletion ít gây bias. "
        "Nếu > 60% missing: cân nhắc drop cột hoặc thu thập lại dữ liệu nguồn."
    ),
    "HIGH_MISSING_RATE": (
        "Nếu > 60%: cân nhắc drop cột. "
        "Nếu 30-60% với MAR pattern: dùng MICE hoặc model-based imputation (IterativeImputer trong sklearn). "
        "Nếu 5-30%: KNN imputation thường đủ tốt. "
        "Không dùng mean/median khi có pattern thiếu (MAR)."
    ),
    "DUPLICATE_ROWS": (
        "Dùng df.drop_duplicates(subset=[key_cols]) nếu chỉ muốn dedup theo key columns. "
        "Nếu dedup toàn row: df.drop_duplicates(keep='last'). "
        "Audit upstream ETL để tìm nguyên nhân gốc. "
        "Tách train/test TRƯỚC khi dedup để tránh data leakage."
    ),
    "OUTLIER_RATE_HIGH": (
        "Kiểm tra bằng box-plot và IQR. Nếu right-skewed: log1p transform. "
        "Nếu muốn giữ outlier: clip tại [Q1-1.5*IQR, Q3+1.5*IQR] thay vì xóa. "
        "Không xóa outlier trước khi verify với domain expert — có thể là tín hiệu quan trọng. "
        "Dùng robust scalers (RobustScaler) thay vì StandardScaler cho ML."
    ),
    "SKEWNESS_HIGH": (
        "Thử log1p transform (nếu right-skewed và giá trị >= 0), "
        "square-root (nếu count data), hoặc Box-Cox (nếu tất cả giá trị dương). "
        "Kiểm tra lại skewness/kurtosis sau transform. "
        "Tree-based models (XGBoost, Random Forest) không cần transform — chỉ Linear/NN cần."
    ),
    "TYPE_MISMATCH": (
        "Ép kiểu với error handling: pd.to_numeric(col, errors='coerce') hoặc pd.to_datetime(col, errors='coerce'). "
        "Log các row bị coerce thành NaN và kiểm tra pattern (thường là chuỗi lạ hoặc null marker). "
        "Xem xét thêm data contract validation ở ingestion layer để bắt lỗi sớm."
    ),
    "CONSTANT_COLUMN": (
        "Loại bỏ cột khỏi feature set ML — zero variance không mang thông tin. "
        "Trước khi xóa: kiểm tra xem đây có phải placeholder ('N/A', 0) hay lỗi ETL không. "
        "Dùng VarianceThreshold(threshold=0) trong sklearn để tự động filter."
    ),
    "HIGH_CARDINALITY": (
        "Nếu là ID column: loại khỏi feature set. "
        "Nếu là categorical thực: dùng target encoding (cho supervised) hoặc frequency encoding. "
        "Tránh one-hot encoding khi cardinality > 50 — sẽ tạo sparse matrix rất lớn. "
        "Cân nhắc embeddings cho NLP features hoặc khi cardinality > 1000."
    ),
    "FK_INTEGRITY_VIOLATION": (
        "Không JOIN trực tiếp khi có FK violation — INNER JOIN sẽ mất rows, LEFT JOIN tạo NULL. "
        "Quyết định: (1) fix upstream source, (2) dùng surrogate key, "
        "(3) chấp nhận mất dữ liệu và document rõ ràng. "
        "Báo cáo số lượng orphan rows cụ thể cho business stakeholders."
    ),
    "NOT_NULL_VIOLATION": (
        "Cột được khai báo NOT NULL nhưng có null — cần điều tra nguồn gốc. "
        "Impute bằng giá trị mặc định hợp lý (0, 'Unknown', median) hoặc xóa các row bị null. "
        "Thêm NOT NULL constraint enforcement ở ingestion layer."
    ),
    "UNIQUE_VIOLATION": (
        "Tìm các giá trị bị trùng và quyết định giữ bản ghi nào. "
        "Nếu cột phải unique theo business logic: dedup ngay. "
        "Nếu không: bỏ UNIQUE constraint và document lý do."
    ),
    "INCONSISTENT_FORMAT": (
        "Normalize format: chuẩn hóa date về ISO 8601, phone về E.164, email về lowercase. "
        "Dùng regex để validate và flag các giá trị không match pattern. "
        "Tạo data cleaning pipeline có thể tái sử dụng thay vì fix one-off."
    ),
}

_DETERMINISTIC_SUGGESTION_DEFAULT = (
    "Kiểm tra các dòng bị ảnh hưởng. Tham khảo tab Hướng dẫn để biết các kỹ thuật xử lý phù hợp với loại vấn đề này."
)


def _get_deterministic_suggestion(issue_type: str) -> str:
    """Trả về gợi ý xử lý cụ thể theo issue_type cho deterministic fallback."""
    return _DETERMINISTIC_SUGGESTIONS.get(
        issue_type.upper() if issue_type else "",
        _DETERMINISTIC_SUGGESTION_DEFAULT,
    )


def _build_deterministic_table_result(table_cluster: TableCluster) -> AnalystTableResult:
    """Fallback deterministc: tạo AnalystTableResult từ TableCluster, không cần LLM."""
    column_issues: list[ColumnIssue] = []
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

            # ML consequence per issue type
            ml_consequence_map = {
                "PK_DUPLICATE": "JOIN sẽ nhân rows, aggregation bị sai, model train trên dữ liệu bị lặp.",
                "ORPHAN_FOREIGN_KEY": "LEFT JOIN tạo NULL rows, INNER JOIN mất dữ liệu âm thầm.",
                "MISSINGNESS": "Cần imputation phù hợp trước khi train. Nếu MAR: tránh mean/median blind.",
                "HIGH_MISSING_RATE": "Feature này không đáng tin cậy cho ML, cần quyết định giữ hay drop.",
                "DUPLICATE_ROWS": "Data leakage nếu duplicate span qua train/test split, model overfit.",
                "OUTLIER_RATE_HIGH": "Kéo lệch mean/std, ảnh hưởng Linear Regression và K-Means nghiêm trọng.",
                "SKEWNESS_HIGH": "Linear models và Neural Networks bị ảnh hưởng — cần transform trước.",
                "TYPE_MISMATCH": "Parse fail âm thầm trong production, feature bị coerce thành NaN.",
                "CONSTANT_COLUMN": "Zero variance — feature này không có thông tin, nên loại khỏi feature set.",
                "HIGH_CARDINALITY": "One-hot encoding tạo sparse matrix khổng lồ, tree models xử lý tốt hơn.",
            }
            ml_consequence = ml_consequence_map.get(
                issue_type.upper() if issue_type else "",
                "Cần kiểm tra cột này trước khi đưa vào mô hình.",
            )

            column_issues.append(ColumnIssue(
                column_name=col_name,
                severity=severity,
                issue_type=issue_type,
                problem=(
                    f"{issue_type}: {issue.get('description', 'Phát hiện vấn đề')}. "
                    f"Ảnh hưởng: {affected_count} dòng{pct_str}."
                ),
                ml_consequence=ml_consequence,
                suggested_action=_get_deterministic_suggestion(issue_type),
                evidence_ref=issue.get("finding_id"),
            ))

    return AnalystTableResult(
        table_name=table_cluster.table_name,
        table_overview=(
            f"Bảng '{table_cluster.table_name}' có {len(table_cluster.issues)} vấn đề "
            f"(mức độ cao nhất: {table_cluster.max_severity}) "
            f"trên {len(table_cluster.affected_columns)} cột."
        ),
        column_issues=column_issues,
        guardrail_passed=True,
        retry_count=0,
    )


# ============================================================
# Agent: Table Analyst
# ============================================================

async def _run_table_analyst(
    table_cluster: TableCluster,
    llm_errors: list[str] | None = None,
) -> tuple[AnalystTableResult, dict[str, Any]]:
    """Analyst agent per TABLE — trả AnalystTableResult (structured JSON tiếng Việt)."""
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


# ============================================================
# Agent: Structured Editor
# ============================================================

async def _run_structured_editor(
    verdict: DatasetVerdict,
    analyst_results: list[AnalystTableResult],
    cross_table_analysis: CrossTableAnalysis | None,
    findings: DataQualityFindings | None = None,
    schema: SchemaEvaluationFindings | None = None,
    schema_gate: SchemaGateResult | None = None,
    llm_errors: list[str] | None = None,
) -> tuple[EditorStructuredOutput, dict[str, Any]]:
    """Editor agent — nhận JSON từ Analyst, trả EditorStructuredOutput tiếng Việt."""
    # Deterministic fallback
    all_columns_issues: list[FeatureUsabilityItem] = []
    fix_priority: list[str] = []

    for result in analyst_results:
        for issue in result.column_issues:
            status = "drop" if issue.severity == "CRITICAL" else "needs_work"
            all_columns_issues.append(FeatureUsabilityItem(
                column=issue.column_name,
                table_name=result.table_name,
                status=status,
                reason=f"[{issue.severity}] {issue.problem[:80]}",
            ))
            fix_priority.append(f"{result.table_name}.{issue.column_name}")

    meta = verdict.dataset_meta
    summary = verdict.summary
    # Build a more informative deterministic summary
    critical_count = summary.critical
    high_count = summary.high
    warn_count = summary.warn
    missing_pct = meta.p_cells_missing * 100
    dup_pct = meta.p_duplicates * 100

    severity_line = ""
    if critical_count:
        severity_line += f"{critical_count} vấn đề CRITICAL"
    if high_count:
        severity_line += (", " if severity_line else "") + f"{high_count} HIGH"
    if warn_count:
        severity_line += (", " if severity_line else "") + f"{warn_count} WARN"
    if not severity_line:
        severity_line = "không có vấn đề nghiêm trọng"

    missing_note = (
        f"Tỷ lệ thiếu dữ liệu {missing_pct:.1f}% — cần xem xét chiến lược imputation trước khi huấn luyện mô hình."
        if missing_pct > 5 else
        f"Tỷ lệ thiếu dữ liệu thấp ({missing_pct:.1f}%)."
    )
    dup_note = (
        f"Tỷ lệ trùng lặp {dup_pct:.1f}% — nên dedup trước khi phân tích."
        if dup_pct > 1 else ""
    )

    fallback = EditorStructuredOutput(
        executive_summary=(
            f"Dataset '{meta.file_name}' có {meta.n:,} dòng × {meta.n_var} cột. "
            f"Kết luận tổng thể: {verdict.verdict.value}. "
            f"Phát hiện {severity_line} trên tổng {summary.total_issues} vấn đề. "
            f"{missing_note} "
            f"{dup_note}"
        ).strip(),
        feature_usability=all_columns_issues,
        fix_priority=fix_priority,
        cross_table_evaluation=_cross_table_summary(cross_table_analysis),
        verdict_explanation=verdict.verdict_rationale,
    )

    llm_enabled = _llm_enabled()
    if llm_enabled:
        payload: dict[str, Any] = {
            "verdict": verdict.model_dump(mode="json"),
            "analyst_results": [r.model_dump(mode="json") for r in analyst_results],
            "cross_table_analysis": (
                cross_table_analysis.model_dump(mode="json")
                if cross_table_analysis else None
            ),
        }
        if findings:
            payload["columns"] = {
                name: stats.model_dump(exclude_none=True)
                for name, stats in findings.columns.items()
            }
            # Extract per-column missingness analysis for LLM (C3)
            _miss_analysis = [
                {
                    "column": name,
                    "p_missing": round(stats.p_missing, 4),
                    "mechanism": stats.missingness_mechanism,
                    "predictability": "high" if stats.missingness_mechanism == "MAR" else "random",
                }
                for name, stats in findings.columns.items()
                if stats.p_missing and stats.p_missing > 0.01
                and stats.missingness_mechanism is not None
            ][:20]
            if _miss_analysis:
                payload["missingness_analysis"] = _miss_analysis
        if schema_gate:
            payload["schema_mode"] = schema_gate.mode
        if schema and schema.relationships:
            payload["relationship_cardinalities"] = [
                f"{r.child_table}.{r.child_column} -> {r.parent_table}.{r.parent_column}: {r.cardinality}"
                for r in schema.relationships if r.cardinality
            ]

        # Build per-table summary for richer context
        table_summaries = []
        for r in analyst_results:
            t_issues = [f"{i.severity}: {i.column_name} — {i.problem[:60]}" for i in r.column_issues]
            table_summaries.append({
                "table": r.table_name,
                "overview": r.table_overview,
                "issue_count": len(r.column_issues),
                "issues": t_issues[:6],
            })

        top_issues_summary = [
            {
                "issue_type": iss.issue_type,
                "severity": iss.effective_severity.value,
                "affected_column": iss.affected_column,
                "affected_count": iss.affected_count,
                "rationale": iss.rationale,
            }
            for iss in (verdict.top_issues or [])[:15]
        ]

        _miss_instruction = ""
        if payload.get("missingness_analysis"):
            _miss_instruction = (
                "\n\n# Yêu cầu phân tích Missingness (Layer 2.5a):\n"
                "Với mỗi cột có mechanism='MAR' trong missingness_analysis: "
                "(1) Lý giải tại sao MAR gợi ý data collection bias hoặc selection effect "
                "(predictability=high nghĩa là pattern thiếu có thể dự đoán từ cột khác). "
                "(2) Phỏng đoán business logic cụ thể — tại sao nhóm người dùng hoặc điều kiện nào "
                "khiến cột này hay bị bỏ trống. "
                "(3) Khuyến nghị imputation strategy phù hợp: KHÔNG dùng mean/median blind — "
                "cần conditional impute theo nhóm hoặc model-based imputation. "
                "Với cột MCAR_CONSISTENT: xác nhận impute mean/median là an toàn. "
                "Với cột INDETERMINATE: ghi nhận không đủ dữ liệu để xác định cơ chế."
            )
        prompt = (
            "Hãy viết báo cáo chất lượng dữ liệu đầy đủ dưới dạng JSON có cấu trúc. "
            "executive_summary phải tối thiểu 8 câu, bao gồm: tổng quan dataset, các vấn đề nghiêm trọng "
            "kèm số liệu cụ thể, ảnh hưởng phân tích, và hướng giải quyết được gợi ý. "
            "feature_usability phải bao gồm tất cả các cột trong analyst_results, kèm table_name của từng cột. "
            "cross_table_evaluation (nếu có dữ liệu relationship): nêu chi tiết mối quan hệ, cardinality, vấn đề khóa. "
            "Viết tất cả nhận xét bằng tiếng Việt.\n\n"
            f"{json.dumps(payload, ensure_ascii=False, indent=2)}"
            f"\n\n# Tóm tắt per-table (context bổ sung):\n"
            f"{json.dumps(table_summaries, ensure_ascii=False, indent=2)}"
            f"\n\n# Top issues (context bổ sung):\n"
            f"{json.dumps(top_issues_summary, ensure_ascii=False, indent=2)}"
            f"{_miss_instruction}"
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
                # Backfill table_name on feature_usability items if LLM didn't include it
                if candidate.feature_usability:
                    # Build a lookup: column_name -> table_name from analyst_results
                    col_to_table: dict[str, str] = {}
                    for r in analyst_results:
                        for ci in r.column_issues:
                            col_to_table[ci.column_name] = r.table_name
                    for item in candidate.feature_usability:
                        if not getattr(item, "table_name", ""):
                            item.table_name = col_to_table.get(item.column, "")
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


# ============================================================
# Python Renderer: JSON → HTML
# ============================================================

def render_table_result_html(
    result: AnalystTableResult,
    chart_paths: dict[str, str] | None = None,
    col_stats: dict | None = None,
) -> str:
    """Python Renderer: chuyển AnalystTableResult JSON → HTML đẹp.

    Nhúng chart bảng ngay sau overview, và chart cột ngay sau mỗi issue.
    LLM chỉ cung cấp nội dung văn bản — hình thức do Python quyết định.

    Args:
        result: AnalystTableResult từ LLM/deterministic agent
        chart_paths: dict {chart_key → path} cho bảng này (đã bỏ prefix bảng)
        col_stats: dict {col_name → ColumnStats} thống kê inline cho bảng này
    """
    chart_paths = chart_paths or {}
    col_stats = col_stats or {}

    # Chart keys thuộc cấp bảng (không phải cột)
    _TABLE_LEVEL_CHARTS = {
        "missingness_bar", "dtype_distribution", "numeric_boxplot",
        "correlation_heatmap", "stacked_bar_issues",
    }
    # Chart keys thuộc cấp cột (prefix là tên cột)
    _COLUMN_LEVEL_CHARTS = {"numeric_distributions", "categorical_top_values"}

    def _chart_img(src: str, alt: str, caption: str = "") -> str:
        cap = f'<figcaption class="chart-caption">{html.escape(caption)}</figcaption>' if caption else ""
        return (
            f'<figure class="inline-chart">'
            f'<img src="{html.escape(src, quote=True)}" alt="{html.escape(alt)}" loading="lazy">'
            f'{cap}</figure>'
        )

    def _col_stats_row(col_name: str) -> str:
        # Try exact match first; then try prefixed key (single-table mode)
        stats = col_stats.get(col_name)
        if stats is None:
            for k, v in col_stats.items():
                if "." in k and k.split(".", 1)[1] == col_name:
                    stats = v
                    break
        if not stats:
            return ""
        items = []
        dtype = getattr(stats, "type", None)
        if dtype:
            items.append(f"<span class='cstat-pill'>Kiểu: {html.escape(str(dtype))}</span>")
        p_miss = getattr(stats, "p_missing", None)
        if p_miss is not None:
            items.append(f"<span class='cstat-pill cstat-miss'>Thiếu: {p_miss*100:.1f}%</span>")
        n_dist = getattr(stats, "n_distinct", None)
        if n_dist is not None:
            items.append(f"<span class='cstat-pill'>Distinct: {n_dist}</span>")
        n_zeros = getattr(stats, "n_zeros", None)
        if n_zeros is not None:
            items.append(f"<span class='cstat-pill'>Zeros: {n_zeros}</span>")
        # Missingness mechanism badge (MAR / MCAR / INDETERMINATE)
        mechanism = getattr(stats, "missingness_mechanism", None)
        p_miss_val = getattr(stats, "p_missing", None)
        if mechanism and p_miss_val and p_miss_val > 0:
            _MECH_CLASSES = {
                "MAR": ("cstat-mar", "MAR ⚠️"),
                "MCAR_CONSISTENT": ("cstat-mcar", "MCAR ✅"),
                "INDETERMINATE": ("cstat-indet", "INDET. ?"),
            }
            css_cls, label = _MECH_CLASSES.get(mechanism, ("cstat-indet", mechanism))
            items.append(f"<span class='cstat-pill {css_cls}'>{html.escape(label)}</span>")
        if not items:
            return ""
        return f'<div class="col-stats-row">{" ".join(items)}</div>'

    parts: list[str] = []
    parts.append('<div class="table-health-section">')
    parts.append(
        f'<h3 class="table-section-title">'
        f'📦 Bảng: <code>{html.escape(result.table_name)}</code></h3>'
    )
    parts.append(f'<p class="table-overview">🌟 {html.escape(result.table_overview)}</p>')

    # Nhúng chart cấp bảng ngay sau overview
    table_chart_html = []
    for ckey in _TABLE_LEVEL_CHARTS:
        path = chart_paths.get(ckey)
        if path:
            label, desc = _CHART_LABEL.get(ckey, (ckey, ""))
            table_chart_html.append(_chart_img(path, label, desc))
    if table_chart_html:
        parts.append('<div class="table-chart-row">' + "".join(table_chart_html) + '</div>')

    def _display_col(col_name: str) -> str:
        """Strip table prefix for display: 'table.col' -> 'col'."""
        return col_name.split(".", 1)[1] if "." in col_name else col_name

    if not result.column_issues:
        parts.append('<p class="no-issues">✅ Không phát hiện vấn đề nào từ mức WARN trở lên.</p>')
    else:
        for issue in result.column_issues:
            sev_class = issue.severity.lower()
            sev_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "WARN": "🟡"}.get(issue.severity, "⚪")
            parts.append(f'<div class="column-issue severity-{sev_class}">')
            parts.append(
                f'<h4 class="col-issue-title">🔸 Cột: '
                f'<code>{html.escape(_display_col(issue.column_name))}</code></h4>'
            )
            # Inline stats cho cột này
            stats_row = _col_stats_row(issue.column_name)
            if stats_row:
                parts.append(stats_row)
            parts.append(
                f'<p class="issue-problem">{sev_icon} '
                f'<strong>[{html.escape(issue.severity)}]</strong> '
                f'{html.escape(issue.problem)}</p>'
            )
            parts.append(
                f'<p class="issue-ml"><strong>Ảnh hưởng ML:</strong> '
                f'{html.escape(issue.ml_consequence)}</p>'
            )
            parts.append(
                f'<p class="issue-action"><strong>Gợi ý tham khảo:</strong> '
                f'{html.escape(issue.suggested_action)}</p>'
            )
            # Nhúng chart cấp cột nếu có
            col_chart_found = False
            # Try both prefixed and plain column name for chart key lookup
            display_col = _display_col(issue.column_name)
            for ckey in _COLUMN_LEVEL_CHARTS:
                for possible_key in (
                    f"{issue.column_name}.{ckey}",
                    f"{display_col}.{ckey}",
                    ckey if len(result.column_issues) == 1 else None,
                ):
                    if possible_key and possible_key in chart_paths:
                        label, desc = _CHART_LABEL.get(ckey, (ckey, ""))
                        parts.append(_chart_img(chart_paths[possible_key], label, desc))
                        col_chart_found = True
                        break
            if issue.evidence_ref:
                parts.append(
                    f'<p class="evidence-ref"><small>Evidence: '
                    f'<code>{html.escape(issue.evidence_ref)}</code></small></p>'
                )
            # SQL diagnostic snippet — 3-tier issue_type resolution
            _KNOWN_TYPES = {
                "PK_DUPLICATE", "COMPOSITE_PK_DUPLICATE", "PK_NULL", "DUPLICATE",
                "ORPHAN_FOREIGN_KEY", "NON_UNIQUE_PARENT_PK", "MISSINGNESS",
                "NOT_NULL_VIOLATION", "UNIQUE_VIOLATION", "HIGH_CARDINALITY",
                "CONSTANT_COLUMN", "TYPE_MISMATCH", "INCONSISTENT_FORMAT",
            }
            # Tier 1: explicit issue_type field (deterministic builder)
            _raw_issue_type = getattr(issue, "issue_type", None) or "UNKNOWN"
            if _raw_issue_type.upper() not in _KNOWN_TYPES:
                _raw_issue_type = "UNKNOWN"
            else:
                _raw_issue_type = _raw_issue_type.upper()

            # Tier 2: parse "ISSUE_TYPE: description" prefix if still unknown
            if _raw_issue_type == "UNKNOWN" and ":" in issue.problem:
                _candidate = issue.problem.split(":", 1)[0].strip().upper()
                if _candidate in _KNOWN_TYPES:
                    _raw_issue_type = _candidate

            # Tier 3: keyword heuristic from problem text (for LLM-generated Vietnamese text)
            if _raw_issue_type == "UNKNOWN":
                _prob_lower = issue.problem.lower()
                # Check duplicate/trùng first since those texts also contain "%"
                if any(k in _prob_lower for k in ["trùng", "duplicate", "lặp", "dòng đặc biệt", "dòng dùng bẫy"]):
                    _raw_issue_type = "DUPLICATE"
                elif any(k in _prob_lower for k in ["unique", "duy nhất", "uniform"]):
                    _raw_issue_type = "UNIQUE_VIOLATION"
                elif any(k in _prob_lower for k in ["giá trị null", "giá trị thiếu", "missing", "null", "thiếu"]):
                    _raw_issue_type = "MISSINGNESS"
                elif any(k in _prob_lower for k in ["cardinality", "distinct", "đa dạng"]):
                    _raw_issue_type = "HIGH_CARDINALITY"
                elif any(k in _prob_lower for k in ["kiểu dữ liệu", "type mismatch", "định dạng sai", "type"]):
                    _raw_issue_type = "TYPE_MISMATCH"

            if _raw_issue_type != "UNKNOWN":
                try:
                    from reporting.sql_fix_generator import generate_sql_for_issue
                    _sql = generate_sql_for_issue(
                        issue_type=_raw_issue_type,
                        table_name=result.table_name,
                        column_name=_display_col(issue.column_name),
                        prefer_llm=False,  # template fallback for speed; LLM can opt-in separately
                    )
                    parts.append(
                        '<details class="sql-snippet-details">'
                        '<summary>🔍 SQL chẩn đoán</summary>'
                        '<div class="sql-snippet-body">'
                        f'<pre><code>{html.escape(_sql)}</code></pre>'
                        '</div></details>'
                    )
                except Exception:
                    pass  # SQL generation is non-critical
            parts.append('</div>')



    parts.append('</div>')
    return "\n".join(parts)


# Mapping chart_key → (label ngắn, mô tả) dùng cho caption inline
_CHART_LABEL: dict[str, tuple[str, str]] = {
    "missingness_bar": ("Mức độ đầy đủ dữ liệu", "% giá trị thiếu theo từng cột"),
    "dtype_distribution": ("Phân bổ kiểu dữ liệu", "Tỷ lệ các kiểu dữ liệu trong bảng"),
    "numeric_distributions": ("Phân phối biến số", "Histogram các cột numeric"),
    "numeric_boxplot": ("Box Plot", "Phân tán và ngoại lệ của biến số"),
    "correlation_heatmap": ("Tương quan", "Mức độ tương quan từng cặp biến"),
    "categorical_top_values": ("Giá trị phổ biến nhất", "Top values trong cột phân loại"),
    "stacked_bar_issues": ("Phân bổ vấn đề", "Vấn đề theo bảng và mức độ nghiêm trọng"),
}


def render_editor_structured_html(editor: EditorStructuredOutput) -> str:
    """Python Renderer: chuyển EditorStructuredOutput → HTML cho Executive Dashboard."""
    parts: list[str] = []

    # Tóm tắt điều hành
    parts.append('<div class="executive-summary">')
    parts.append(f'<p>{html.escape(editor.executive_summary)}</p>')
    parts.append('</div>')

    # Bảng Khả Năng Sử Dụng Từng Cột
    if editor.feature_usability:
        # Mức độ dựa trên severity thực tế, không gợi ý dùng hay loại bỏ
        status_config = {
            "ready":      ("✅", "Không vấn đề", "status-ready"),
            "needs_work": ("⚠️", "Có vấn đề",   "status-needs-work"),
            "drop":       ("🔴", "Nghiêm trọng", "status-critical"),
        }
        has_table_col = any(getattr(item, "table_name", "") for item in editor.feature_usability)
        parts.append('<div class="feature-usability">')
        parts.append('<h3>Chất Lượng Từng Cột</h3>')
        parts.append('<p class="feature-usability-note">Đánh giá dựa trên chất lượng dữ liệu quan sát được — không phụ thuộc vào mục đích sử dụng cụ thể.</p>')
        parts.append('<table class="feature-usability-table"><thead><tr>')
        if has_table_col:
            parts.append('<th>Bảng</th>')
        parts.append('<th>Cột</th><th>Mức độ</th><th>Nhận xét</th>')
        parts.append('</tr></thead><tbody>')
        for item in editor.feature_usability:
            icon, label, css_cls = status_config.get(item.status, ("❓", item.status, ""))
            table_cell = ""
            if has_table_col:
                tname = getattr(item, "table_name", "") or "—"
                table_cell = f'<td class="col-table-name"><code>{html.escape(tname)}</code></td>'
            parts.append(
                f'<tr class="{css_cls}">'
                f'{table_cell}'
                f'<td class="col-name-cell"><code>{html.escape(item.column)}</code></td>'
                f'<td class="status-cell"><span class="status-badge {css_cls}">{icon} {label}</span></td>'
                f'<td class="reason-cell">{html.escape(item.reason)}</td></tr>'
            )
        parts.append('</tbody></table>')
        parts.append('</div>')

    # Giải thích verdict — đặt sau để người đọc đã có context
    if editor.verdict_explanation:
        parts.append('<div class="verdict-explanation">')
        parts.append('<h3>Cơ Sở Đánh Giá</h3>')
        parts.append(f'<p>{html.escape(editor.verdict_explanation)}</p>')
        parts.append('</div>')

    # Cross-table Evaluation — nếu có, hiển thị ở đây như text tóm tắt
    # (Chart network và visual sẽ được hiển thị riêng ở section Cross-table)
    if editor.cross_table_evaluation:
        parts.append('<div class="cross-table-eval-summary">')
        parts.append('<h3>Đánh Giá Mối Quan Hệ Liên Bảng</h3>')
        parts.append(f'<p>{html.escape(editor.cross_table_evaluation)}</p>')
        parts.append('</div>')

    return "\n".join(parts)


# ============================================================
# Orchestrator
# ============================================================

async def run_structured_multi_agent_l4(
    findings: DataQualityFindings | None,
    verdict: DatasetVerdict,
    schema: SchemaEvaluationFindings | None = None,
    cross_table_analysis: CrossTableAnalysis | None = None,
    schema_gate: SchemaGateResult | None = None,
) -> tuple[str, MultiAgentResult]:
    """Orchestrator chính: gom theo Table → Analyst JSON → Editor JSON → Python render HTML."""
    # Bước 1: Dispatch theo table
    dispatch_result = dispatch_by_table(
        findings.anomalies if findings else [],
        schema.integrity_errors if schema else [],
        columns=findings.columns if findings else None,
    )

    llm_errors: list[str] = []

    # Bước 2: Fan-out Analyst per table (chạy song song)
    analyst_tasks = [
        _run_table_analyst(tc, llm_errors)
        for tc in dispatch_result.table_clusters
    ]
    analyst_results_raw = await asyncio.gather(*analyst_tasks)
    analyst_table_results = [result for result, _detail in analyst_results_raw]
    agent_details = [detail for _result, detail in analyst_results_raw]

    # Bước 3: Editor tổng hợp
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

    # Bước 4: Python render JSON → HTML
    html_parts: list[str] = []

    # Phần 1: Executive Dashboard
    html_parts.append(render_editor_structured_html(editor_structured))

    # Phần 2: Kiểm tra sức khỏe từng bảng
    html_parts.append('<div class="table-health-checks">')
    html_parts.append('<h2>Kiểm Tra Sức Khỏe Từng Bảng</h2>')
    for result in analyst_table_results:
        html_parts.append(render_table_result_html(result))
    html_parts.append('</div>')

    rendered_html = "\n".join(html_parts)

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
    """Sync wrapper cho orchestrator chính."""
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(
            run_structured_multi_agent_l4(
                findings, verdict, schema, cross_table_analysis, schema_gate
            )
        )
    # Fallback nếu đang trong event loop (ví dụ: test async)
    html_parts = []
    if findings:
        dr = dispatch_by_table(
            findings.anomalies,
            schema.integrity_errors if schema else [],
            columns=findings.columns,
        )
        for tc in dr.table_clusters:
            fb = _build_deterministic_table_result(tc)
            html_parts.append(render_table_result_html(fb))

    return "\n".join(html_parts), MultiAgentResult(used_fallback=True)


# ============================================================
# Backward-compatible wrappers
# ============================================================

def generate_multi_agent_report(
    findings: DataQualityFindings | None,
    verdict: DatasetVerdict,
    schema: SchemaEvaluationFindings | None = None,
    cross_table_analysis: CrossTableAnalysis | None = None,
    schema_gate: SchemaGateResult | None = None,
) -> tuple[str, GuardrailReport, MultiAgentResult]:
    """Backward-compat wrapper — gọi luồng structured mới.

    Trả (html_text, guardrail_report, multi_result) để giữ interface cũ.
    """
    html_text, multi_result = generate_structured_report(
        findings, verdict, schema, cross_table_analysis, schema_gate
    )
    # Build a minimal GuardrailReport from multi_result metadata
    guardrail = validate_narrative(
        html_text, findings, verdict, schema, cross_table_analysis,
        provider="structured-pipeline",
        used_fallback=multi_result.used_fallback,
    )
    return html_text, guardrail, multi_result


def generate_l4_report(
    findings: DataQualityFindings | None,
    verdict: DatasetVerdict,
    schema: SchemaEvaluationFindings | None = None,
) -> tuple[str, GuardrailReport]:
    """Backward-compat wrapper — gọi luồng structured mới.

    Trả (html_text, guardrail_report) để giữ interface cũ.
    """
    text, report, _result = generate_multi_agent_report(findings, verdict, schema)
    return text, report
