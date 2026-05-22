"""Unit tests for query_validator — QuerySizeLimit, TickerValidator, PatternGuard."""

from infrastructure.guardrails.query_validator import (
    QuerySizeLimit,
    TickerValidator,
    PatternGuard,
)
from infrastructure.guardrails.config import GuardrailConfig

# -- QuerySizeLimit -------------------------------------------------------


def test_query_size_limit_passes():
    cfg = GuardrailConfig()
    cfg.max_query_length = 100
    v = QuerySizeLimit(cfg)
    result = v.validate("short query", "127.0.0.1")
    assert result.passed is True


def test_query_size_limit_exceeds():
    cfg = GuardrailConfig()
    cfg.max_query_length = 5
    v = QuerySizeLimit(cfg)
    result = v.validate("too long query", "127.0.0.1")
    assert result.passed is False


def test_query_size_limit_boundary():
    cfg = GuardrailConfig()
    cfg.max_query_length = 5
    v = QuerySizeLimit(cfg)
    assert v.validate("12345", "127.0.0.1").passed is True
    assert v.validate("123456", "127.0.0.1").passed is False


# -- TickerValidator ------------------------------------------------------


def test_ticker_validator_known_ticker_passes():
    cfg = GuardrailConfig()
    cfg.vietnamese_tickers = {"VCB", "HPG", "VNM"}
    cfg.ticker_pattern = r"\b[A-Z]{2,8}\b"
    v = TickerValidator(cfg)
    result = v.validate("VCB", "127.0.0.1")
    assert result.passed is True


def test_ticker_validator_unknown_ticker_fails():
    cfg = GuardrailConfig()
    cfg.vietnamese_tickers = {"VCB"}
    cfg.ticker_pattern = r"\b[A-Z]{2,8}\b"
    v = TickerValidator(cfg)
    result = v.validate("XXXX", "127.0.0.1")
    assert result.passed is False


def test_ticker_validator_english_word_not_flagged():
    cfg = GuardrailConfig()
    cfg.vietnamese_tickers = set()
    cfg.ticker_pattern = r"\b[A-Z]{2,8}\b"
    v = TickerValidator(cfg)
    result = v.validate("TOP", "127.0.0.1")
    assert result.passed is True


def test_ticker_validator_mixed_known_and_unknown():
    cfg = GuardrailConfig()
    cfg.vietnamese_tickers = {"VCB"}
    cfg.ticker_pattern = r"\b[A-Z]{2,8}\b"
    v = TickerValidator(cfg)
    result = v.validate("VCB and XXXX", "127.0.0.1")
    assert result.passed is False


def test_ticker_validator_no_tickers_passes():
    cfg = GuardrailConfig()
    v = TickerValidator(cfg)
    result = v.validate("hello world", "127.0.0.1")
    assert result.passed is True


# -- PatternGuard ---------------------------------------------------------


def test_pattern_guard_normal_passes():
    v = PatternGuard()
    result = v.validate("What is the price of VCB?", "127.0.0.1")
    assert result.passed is True


def test_pattern_guard_sql_injection():
    v = PatternGuard()
    result = v.validate("DROP TABLE users", "127.0.0.1")
    assert result.passed is False


def test_pattern_guard_shell_injection():
    v = PatternGuard()
    result = v.validate("import os; os.system('ls')", "127.0.0.1")
    assert result.passed is False


def test_pattern_guard_path_traversal():
    v = PatternGuard()
    result = v.validate("../../../etc/passwd", "127.0.0.1")
    assert result.passed is False


def test_pattern_guard_sql_union():
    v = PatternGuard()
    result = v.validate("1 UNION SELECT * FROM users", "127.0.0.1")
    assert result.passed is False


def test_pattern_guard_url_encoded_traversal():
    v = PatternGuard()
    result = v.validate("%2e%2e%2fetc/passwd", "127.0.0.1")
    assert result.passed is False
