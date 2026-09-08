import os
import logging
from typing import TypeVar

T = TypeVar("T", int, float, str)

logger = logging.getLogger(__name__)


def parse_int_env(name: str, default: int) -> int:
    """Deprecated — use shared.config._get_int instead for consistency."""
    raw = os.getenv(name, str(default))
    try:
        return int(raw.strip())
    except (ValueError, TypeError, AttributeError):
        logger.warning("Invalid %s=%r, using default %d", name, raw, default)
        return default
