from .tickers import VIETNAMESE_TICKERS


class GuardrailConfig:
    rate_limit_requests: int = 20
    rate_limit_window_seconds: int = 60
    rate_limit_burst: int = 5
    rate_limit_hourly_per_ip: int = 100

    max_query_length: int = 1000
    max_ticker_count: int = 10

    max_special_char_ratio: float = 0.3
    max_uppercase_ratio: float = 0.6

    ticker_pattern: str = r"\b[A-Z]{2,4}\b"

    vietnamese_tickers: frozenset = VIETNAMESE_TICKERS
