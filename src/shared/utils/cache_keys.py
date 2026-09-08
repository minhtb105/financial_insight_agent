"""Pure cache key utils — moved from infrastructure.cache.cache_keys to shared for hexagon purity."""

import zlib
from typing import Any


def make_cache_key(
    service: str, ticker: str, start: str | None = None, end: str | None = None, **extra: Any
) -> str:
    segments = [service, ticker]
    if start:
        segments.append(start)
    if end:
        segments.append(end)
    if extra:
        extra_str = ",".join(f"{k}={v}" for k, v in sorted(extra.items()) if v is not None)
        if extra_str:
            segments.append(format(zlib.crc32(extra_str.encode()), "x"))
    return ":".join(segments)


def make_overview_cache_key(service: str, ticker: str, extra: dict[str, Any] | None = None) -> str:
    return make_cache_key(service, ticker, **extra or {})
