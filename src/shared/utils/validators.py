"""Shared validators — moved from domain for shared layer purity."""

import re

TICKER_PATTERN = re.compile(r"^[A-Z0-9]{2,8}$")


def validate_ticker_list(tickers: list[str]) -> list[str]:
    if not tickers:
        raise ValueError("At least one ticker is required")
    result = []
    for ticker in tickers:
        if not isinstance(ticker, str) or not TICKER_PATTERN.match(ticker.upper()):
            raise ValueError(f"Invalid ticker: {ticker}")
        result.append(ticker.upper())
    return result
