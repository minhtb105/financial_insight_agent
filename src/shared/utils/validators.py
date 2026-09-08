"""Ticker validators — re-export from domain (single source of truth).

Shared layer re-exports domain validators so application code can import from
``shared.utils.validators`` without creating a second implementation.
Domain remains canonical and does not import shared (hexagon rule).
"""

from domain.entities.time_range import TICKER_PATTERN, validate_ticker_list

__all__ = ["TICKER_PATTERN", "validate_ticker_list"]
