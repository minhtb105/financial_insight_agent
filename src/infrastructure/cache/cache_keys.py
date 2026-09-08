"""Deprecated re-export — use shared.utils.cache_keys directly. Will be removed in v2."""

import warnings

from shared.utils.cache_keys import make_cache_key, make_overview_cache_key

warnings.warn("infrastructure.cache.cache_keys is deprecated — use shared.utils.cache_keys", DeprecationWarning, stacklevel=2)

__all__ = ["make_cache_key", "make_overview_cache_key"]
