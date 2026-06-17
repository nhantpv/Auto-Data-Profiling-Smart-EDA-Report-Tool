"""Issue catalog — pre-defined probable_causes and suggested_fix per issue_type.

Ported and adapted from VSF Data Profiler issue_catalog.py.
Used to enrich AnomalyRecord and IntegrityError with actionable context,
giving the LLM (L4) higher-quality, domain-grounded context to work with.

Usage:
    from ontology.issue_catalog import get_causes, get_fixes

    causes = get_causes("ORPHAN_FOREIGN_KEY")
    fixes  = get_fixes("ORPHAN_FOREIGN_KEY")
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------

_CAUSES: dict[str, list[str]] = {
    # --- Schema / Structural ---
    "ORPHAN_FOREIGN_KEY": [
        "Bảng cha (parent table) có thể đang thiếu một batch dữ liệu.",
        "Bảng con (child) được load trước bảng cha trong pipeline.",
        "Logic biến đổi khóa ngoại không nhất quán giữa các bảng.",
    ],
    "DUPLICATE_PRIMARY_KEY": [
        "Khóa chính không được enforce unique ở tầng upstream.",
        "Nhiều pipeline hoặc nguồn dữ liệu cùng ghi vào một bảng.",
        "Tiến trình upsert bị lỗi, tạo ra dòng trùng thay vì cập nhật.",
    ],
    "PARENT_KEY_DUPLICATE": [
        "Bảng cha đang có khóa không unique — join sẽ nhân dòng con lên.",
        "Bảng cha là dimension nhưng chưa được deduplicate trước khi dùng.",
    ],
    "MISSING_COLUMN": [
        "CSV export không bao gồm cột được khai báo trong DBML schema.",
        "Tên cột bị thay đổi hoặc viết sai ở nguồn dữ liệu.",
    ],
    "EXTRA_COLUMN": [
        "CSV export chứa cột không được khai báo trong DBML schema.",
        "Schema DBML chưa được cập nhật sau khi thêm cột mới vào nguồn.",
    ],
    "TYPE_MISMATCH": [
        "Nguồn dữ liệu gửi giá trị không đúng kiểu được khai báo trong schema.",
        "Logic biến đổi dữ liệu chưa cast đúng kiểu trước khi xuất.",
    ],
    "NON_UNIQUE_PARENT_PK": [
        "Khóa chính của bảng cha không unique — sẽ gây nhân dòng khi JOIN.",
        "Bảng cần được deduplicate trước khi dùng làm dimension.",
    ],

    # --- Data Quality (từ anomaly engine) ---
    "OUTLIER_ENSEMBLE": [
        "Dòng dữ liệu có kết hợp nhiều đặc trưng bất thường (multivariate outlier).",
        "Lỗi nhập liệu hoặc lỗi ETL tạo ra giá trị cực đoan ở nhiều chiều cùng lúc.",
        "Gian lận hoặc sự kiện bất thường thực sự trong dữ liệu (cần xác minh).",
    ],
    "DUPLICATE": [
        "Pipeline ETL bị chạy lại mà không có idempotency check.",
        "Nhiều nguồn dữ liệu cùng ghi vào một bảng mà không dedup.",
        "Logic merge/upsert có bug tạo ra bản ghi trùng.",
    ],
    "HIGH_MISSING_RATE": [
        "Trường dữ liệu không bắt buộc trong hệ thống nguồn → user bỏ qua.",
        "Lỗi ETL làm NULL hóa một cột khi transform.",
        "Dữ liệu historical không có trường này (backfill chưa được thực hiện).",
    ],
    "MNAR_MISSING": [
        "Việc thiếu dữ liệu có tương quan với giá trị của chính cột đó (MNAR).",
        "Người dùng/hệ thống cố tình không nhập trường nhạy cảm (thu nhập, điểm số).",
        "Cảnh báo: Impute bằng mean/median trên MNAR sẽ gây bias nghiêm trọng cho model ML.",
    ],
    "MAR_MISSING": [
        "Việc thiếu dữ liệu phụ thuộc vào giá trị của cột khác (MAR).",
        "Ví dụ: giới tính nữ thường không khai cân nặng → bỏ trống phụ thuộc vào gender.",
    ],

    # --- Cross-table / Relationship ---
    "WEAK_FK_COVERAGE": [
        "Tỷ lệ khớp giữa khóa ngoại và khóa cha thấp — dữ liệu không đồng bộ.",
        "Bảng cha chưa được load đầy đủ hoặc đã bị xóa một phần.",
    ],
    "CARDINALITY_VIOLATION": [
        "Quan hệ được khai báo là 1:1 nhưng dữ liệu thực tế là 1:N.",
        "Bảng child có nhiều dòng cho một khóa cha — vi phạm ràng buộc cardinality.",
    ],
}

_FIXES: dict[str, list[str]] = {
    # --- Schema / Structural ---
    "ORPHAN_FOREIGN_KEY": [
        "Kiểm tra và load đầy đủ bảng cha trước khi load bảng con.",
        "Thêm anti-join validation trong pipeline trước khi publish.",
        "Quarantine các dòng con mà khóa cha không tồn tại.",
    ],
    "DUPLICATE_PRIMARY_KEY": [
        "Deduplicate theo khóa chính hoặc sửa logic sinh khóa ở upstream.",
        "Thêm UNIQUE constraint hoặc upsert đúng cách.",
        "Audit pipeline để tìm bước nào đang tạo ra bản ghi trùng.",
    ],
    "PARENT_KEY_DUPLICATE": [
        "Deduplicate bảng cha trước khi dùng làm dimension.",
        "Xác minh lại thiết kế schema — khóa chính phải unique.",
    ],
    "MISSING_COLUMN": [
        "Cập nhật export query hoặc DBML schema để header khớp nhau.",
        "Kiểm tra xem cột đã bị đổi tên hay xóa ở nguồn.",
    ],
    "EXTRA_COLUMN": [
        "Xác nhận cột thừa có cần thiết không — nếu không thì loại khỏi export.",
        "Cập nhật DBML schema nếu cột mới là hợp lệ.",
    ],
    "TYPE_MISMATCH": [
        "Chuẩn hóa kiểu dữ liệu ở bước transform trước khi export.",
        "Quarantine các dòng không cast được và xử lý riêng.",
    ],
    "NON_UNIQUE_PARENT_PK": [
        "Deduplicate bảng cha trước khi JOIN.",
        "Kiểm tra lại logic sinh khóa chính ở nguồn.",
    ],

    # --- Data Quality ---
    "OUTLIER_ENSEMBLE": [
        "Xuất danh sách các dòng bất thường để xem xét thủ công.",
        "Xác minh xem đây là lỗi dữ liệu hay sự kiện thực sự bất thường.",
        "Nếu là lỗi: loại bỏ hoặc sửa. Nếu là thực: gán nhãn và giữ lại.",
        "Cân nhắc dùng robust scaler hoặc winsorization nếu dùng cho ML.",
    ],
    "DUPLICATE": [
        "Dedup theo khóa tự nhiên trước khi đưa vào phân tích.",
        "Tìm bước trong pipeline gây ra duplicate và thêm idempotency check.",
        "Kiểm tra xem các bản trùng có cùng timestamp không — có thể là re-ingestion.",
    ],
    "HIGH_MISSING_RATE": [
        "Phân loại cơ chế missing (MCAR/MAR/MNAR) trước khi quyết định impute.",
        "Nếu MCAR: impute bằng mean/median/mode là an toàn.",
        "Nếu MAR/MNAR: cần impute có điều kiện hoặc dùng model-based imputation.",
        "Nếu > 50% missing: cân nhắc bỏ cột hoặc thu thập lại dữ liệu.",
    ],
    "MNAR_MISSING": [
        "KHÔNG impute bằng mean/median — sẽ gây bias nghiêm trọng.",
        "Dùng multiple imputation hoặc model-based imputation (MICE, missForest).",
        "Tạo binary indicator column để encode 'is_missing' trước khi impute.",
        "Thu thập lại dữ liệu nếu tỷ lệ MNAR quá cao.",
    ],
    "MAR_MISSING": [
        "Dùng conditional imputation dựa trên cột tương quan.",
        "Impute trong từng nhóm (group-by cột có tương quan).",
        "Kiểm tra lại form nhập liệu để bắt buộc điền trường này trong các trường hợp liên quan.",
    ],

    # --- Cross-table / Relationship ---
    "WEAK_FK_COVERAGE": [
        "Load lại bảng cha với đầy đủ dữ liệu.",
        "Kiểm tra xem dữ liệu cha có bị xóa nhầm không.",
    ],
    "CARDINALITY_VIOLATION": [
        "Dedup cột child theo khóa cha nếu quan hệ phải là 1:1.",
        "Cập nhật lại khai báo cardinality trong DBML nếu 1:N là đúng ý định.",
    ],
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_causes(issue_type: str) -> list[str]:
    """Return probable_causes list for a given issue_type.

    Falls back to a generic cause if issue_type is not in catalog.
    Never raises — safe to call for any issue_type.
    """
    return _CAUSES.get(
        issue_type,
        ["Dữ liệu không đáp ứng yêu cầu chất lượng kỳ vọng — cần điều tra thêm."],
    )


def get_fixes(issue_type: str) -> list[str]:
    """Return suggested_fix list for a given issue_type.

    Falls back to a generic fix if issue_type is not in catalog.
    Never raises — safe to call for any issue_type.
    """
    return _FIXES.get(
        issue_type,
        ["Kiểm tra các dòng mẫu và xác minh với chủ sở hữu dữ liệu."],
    )
