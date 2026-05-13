import hashlib
from typing import Any, Dict, Optional


def make_cache_key(
    service: str,
    ticker: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    **extra: Any
) -> str:
    segments = [service, ticker]
    if start:
        segments.append(start)
    if end:
        segments.append(end)

    if extra:
        extra_str = ",".join(f"{k}={v}" for k, v in sorted(extra.items()) if v is not None)
        if extra_str:
            segments.append(hashlib.md5(extra_str.encode()).hexdigest()[:8])

    return ":".join(segments)


def make_overview_cache_key(service: str, ticker: str, extra: Optional[Dict[str, Any]] = None) -> str:
    return make_cache_key(service, ticker, **extra or {})