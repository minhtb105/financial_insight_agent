import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

TEMPLATES: Dict[str, str] = {
    "price_query": (
        "Kết quả truy vấn giá:\n{output}\n"
    ),
    "company_query": (
        "Thông tin công ty:\n{output}\n"
    ),
    "financial_ratio_query": (
        "Kết quả chỉ số tài chính:\n{output}\n"
    ),
    "comparison_query": (
        "Kết quả so sánh:\n{output}\n"
    ),
    "aggregate_query": (
        "Kết quả tổng hợp:\n{output}\n"
    ),
    "indicator_query": (
        "Kết quả chỉ báo kỹ thuật:\n{output}\n"
    ),
    "ranking_query": (
        "Kết quả xếp hạng:\n{output}\n"
    ),
}

CONFIDENCE_PREFIXES: Dict[str, str] = {
    "high": "",
    "medium": (
        "[Lưu ý] Thông tin dưới đây có độ tin cậy trung bình, "
        "vui lòng kiểm tra lại nếu cần.\n"
    ),
    "low": (
        "[Cảnh báo] Thông tin dưới đây có độ tin cậy thấp, "
        "khuyến nghị xác nhận lại từ nguồn khác.\n"
    ),
}

FALLBACK_TEMPLATE = "Kết quả:\n{output}\n"


class ResponseFormatter:
    def format(
        self,
        query_type: str,
        original_query: str,
        raw_output: str,
        confidence: float,
    ) -> str:
        if not raw_output or raw_output.startswith("Error") or raw_output.startswith("Missing") or raw_output.startswith("No data"):
            return self._format_error(raw_output, confidence)

        template = TEMPLATES.get(query_type, FALLBACK_TEMPLATE)
        prefix = self._confidence_prefix(confidence)
        body = template.format(output=raw_output.strip())
        return prefix + body

    def _format_error(self, raw_output: str, confidence: float) -> str:
        prefix = self._confidence_prefix(confidence)
        return f"{prefix}[Lỗi] Không thể lấy dữ liệu cho truy vấn của bạn. Chi tiết: {raw_output}"

    def _confidence_prefix(self, confidence: float) -> str:
        if confidence >= 0.8:
            return CONFIDENCE_PREFIXES["high"]
        elif confidence >= 0.5:
            return CONFIDENCE_PREFIXES["medium"]
        return CONFIDENCE_PREFIXES["low"]