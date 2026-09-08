"""Safety layer per TT 135/2025 — prevents specific buy/sell advice from unlicensed agent."""

from __future__ import annotations

import re

from infrastructure.observability import get_logger

logger = get_logger("rag.safety")

# Patterns that indicate specific investment recommendation
BLOCK_PATTERNS = [
    r"mua\s+ngay\b",
    r"bán\s+ngay\b",
    r"khuyến\s+nghị\s+(mua|bán)\b",
    r"nên\s+mua\b.*\b(cổ phiếu|mã)\b",
    r"all[-\s]*in\b",
    r"đòn\s+bẩy\s+cao\b.*khuyến nghị",
]

COMPILED = [re.compile(p, re.IGNORECASE) for p in BLOCK_PATTERNS]

DISCLAIMER = "\n\n> Lưu ý: Thông tin trên chỉ mang tính giáo dục và tham khảo, không phải lời khuyên đầu tư. Quyết định mua/bán cần dựa trên khẩu vị rủi ro cá nhân và tham khảo tư vấn được cấp phép (TT 135/2025/TT-BTC)."


def check_and_sanitize(response: str) -> tuple[str, bool]:
    """Returns (sanitized_response, was_blocked)."""
    blocked = any(p.search(response) for p in COMPILED)
    if blocked:
        logger.warning("Safety layer triggered — sanitizing")
        # replace blocked phrases with generic wording
        sanitized = response
        for p in COMPILED:
            sanitized = p.sub("[đã lọc khuyến nghị cụ thể]", sanitized)
        sanitized = sanitized.rstrip() + DISCLAIMER
        return sanitized, True
    # always append disclaimer if response contains financial knowledge
    if len(response) > 200:
        return response + DISCLAIMER, False
    return response, False
