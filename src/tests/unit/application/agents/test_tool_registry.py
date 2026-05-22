"""Unit tests for tool_registry — all 12 tool functions and utilities."""

import json
from unittest.mock import patch

import pytest

from application.agents.tool_registry import (
    _wrap,
    _safe_json,
    _categorize_error,
    TOOL_ERR_PREFIX,
    ALL_TOOLS,
    get_stock_price,
    calculate_technical_indicator,
    compare_stocks,
    rank_stocks,
    aggregate_prices,
    get_financial_ratios,
    get_company_info,
    get_news_and_sentiment,
    manage_portfolio,
    check_price_alert,
    forecast_stock_price,
    analyze_sector,
)

# -- helpers to access the raw function inside StructuredTool ---------------


def _fn(tool):
    return tool.func


# ---------------------------------------------------------------------------
# _categorize_error
# ---------------------------------------------------------------------------


def test_categorize_error_timeout():
    result = _categorize_error(TimeoutError("request timed out"))
    assert result.startswith(f"{TOOL_ERR_PREFIX}TIMEOUT")


def test_categorize_error_validation():
    result = _categorize_error(ValueError("invalid ticker"))
    assert result.startswith(f"{TOOL_ERR_PREFIX}VALIDATION")


def test_categorize_error_keyerror():
    result = _categorize_error(KeyError("missing field"))
    assert result.startswith(f"{TOOL_ERR_PREFIX}NOT_FOUND")


def test_categorize_error_generic():
    result = _categorize_error(RuntimeError("something broke"))
    assert result.startswith(f"{TOOL_ERR_PREFIX}UNKNOWN")


# ---------------------------------------------------------------------------
# _wrap / _safe_json
# ---------------------------------------------------------------------------


def test_wrap_none_returns_not_err():
    result = _wrap("test_fn", None)
    assert TOOL_ERR_PREFIX not in result
    parsed = json.loads(result)
    assert parsed["data"] is None
    assert "note" in parsed


def test_wrap_error_dict_only():
    result = _wrap("test_fn", {"error": "something broke"})
    assert result.startswith(f"{TOOL_ERR_PREFIX}SERVICE")
    assert "something broke" in result


def test_wrap_dict_with_data_and_error_is_not_err():
    result = _wrap("test_fn", {"data": [1, 2], "error": "partial failure"})
    assert TOOL_ERR_PREFIX not in result
    parsed = json.loads(result)
    assert parsed["data"] == [1, 2]
    assert "_warning" in parsed
    assert "partial failure" in parsed["_warning"]


def test_wrap_valid_list():
    result = _wrap("test_fn", [1, 2, 3])
    parsed = json.loads(result)
    assert parsed == [1, 2, 3]


def test_safe_json_handles_non_serializable():
    class Unserializable:
        pass

    result = _safe_json(Unserializable())
    assert isinstance(result, str)

    d = {}
    d["self"] = d
    result = _safe_json(d)
    assert isinstance(result, str)


def test_safe_json_with_none():
    result = _safe_json(None)
    assert result == "null"


# ---------------------------------------------------------------------------
# ALL_TOOLS registration
# ---------------------------------------------------------------------------


def test_all_tools_contains_12_tools():
    assert len(ALL_TOOLS) == 12


def test_all_tools_have_func_and_name():
    for tool_fn in ALL_TOOLS:
        assert hasattr(tool_fn, "func")
        assert callable(tool_fn.func)
        assert hasattr(tool_fn, "name")


# ---------------------------------------------------------------------------
# Per-tool happy-path & exception tests (via .func)
# ---------------------------------------------------------------------------

TOOL_HANDLER_MAP = {
    "get_stock_price": ("handle_price_query", ["VCB"]),
    "calculate_technical_indicator": ("handle_indicator_query", ["VCB"]),
    "compare_stocks": ("handle_compare_query", ["VCB"]),
    "rank_stocks": ("handle_ranking_query", ["VCB", "VNM"]),
    "aggregate_prices": ("handle_aggregate_query", ["VCB"]),
    "get_financial_ratios": ("handle_financial_ratio_query", ["VCB"]),
    "get_company_info": ("handle_company_query", ["VCB"]),
    "get_news_and_sentiment": ("handle_news_sentiment_query", ["VCB"]),
    "manage_portfolio": ("handle_portfolio_query", None),
    "check_price_alert": ("handle_alert_query", ["VCB"]),
    "forecast_stock_price": ("handle_forecast_query", ["VCB"]),
    "analyze_sector": ("handle_sector_query", None),
}


def _tool_kwargs(name):
    if name == "compare_stocks":
        return {"tickers": ["VCB"], "compare_with": ["VNM"]}
    if name == "manage_portfolio":
        return {"field": "portfolio_summary"}
    if name == "analyze_sector":
        return {"sector": "banking"}
    if name == "check_price_alert":
        return {"tickers": ["VCB"], "threshold": 100.0}
    return {"tickers": ["VCB"]}


@pytest.mark.parametrize("tool_name", list(TOOL_HANDLER_MAP.keys()))
def test_tool_happy_path(tool_name):
    handler_name, _ = TOOL_HANDLER_MAP[tool_name]
    handler_path = f"application.agents.tool_registry.{handler_name}"
    tool_fn = globals()[tool_name]
    kwargs = _tool_kwargs(tool_name)

    with patch(handler_path, return_value={"result": "ok"}) as mock_h:
        result = tool_fn.func(**kwargs)

    mock_h.assert_called_once()
    assert isinstance(result, str)


@pytest.mark.parametrize("tool_name", list(TOOL_HANDLER_MAP.keys()))
def test_tool_handler_exception(tool_name):
    handler_name, _ = TOOL_HANDLER_MAP[tool_name]
    handler_path = f"application.agents.tool_registry.{handler_name}"
    tool_fn = globals()[tool_name]
    kwargs = _tool_kwargs(tool_name)

    with patch(handler_path, side_effect=ValueError("conn failed")):
        result = tool_fn.func(**kwargs)

    assert result.startswith(f"{TOOL_ERR_PREFIX}VALIDATION")
    assert "conn failed" in result


# ---------------------------------------------------------------------------
# Per-tool param verification
# ---------------------------------------------------------------------------


@patch("application.agents.tool_registry.handle_price_query")
def test_get_stock_price_default_field(m):
    m.return_value = {"data": "ok"}
    get_stock_price.func(tickers=["VCB"])
    m.assert_called_once_with(
        tickers=["VCB"], field="close", days=None, weeks=None,
        months=None, start_date=None, end_date=None,
    )


@patch("application.agents.tool_registry.handle_price_query")
def test_get_stock_price_with_timeframe(m):
    m.return_value = {"data": "ok"}
    get_stock_price.func(tickers=["VCB"], days=10, field="open")
    m.assert_called_once_with(
        tickers=["VCB"], field="open", days=10, weeks=None,
        months=None, start_date=None, end_date=None,
    )


@patch("application.agents.tool_registry.handle_indicator_query")
def test_calculate_technical_indicator_params(m):
    m.return_value = {"data": "ok"}
    calculate_technical_indicator.func(
        tickers=["VCB"], indicator="rsi", period=14,
    )
    m.assert_called_once_with(
        tickers=["VCB"], indicator="rsi", period=14,
        fast_period=None, slow_period=None, days=None,
        weeks=None, months=None, start_date=None, end_date=None,
    )


@patch("application.agents.tool_registry.handle_compare_query")
def test_compare_stocks_params(m):
    m.return_value = {"data": "ok"}
    compare_stocks.func(
        tickers=["VCB"], compare_with=["VNM", "HPG"], field="volume",
    )
    m.assert_called_once_with(
        tickers=["VCB"], compare_with=["VNM", "HPG"], field="volume",
        days=None, weeks=None, months=None, start_date=None, end_date=None,
    )


@patch("application.agents.tool_registry.handle_ranking_query")
def test_rank_stocks_params(m):
    m.return_value = {"data": "ok"}
    rank_stocks.func(tickers=["VCB", "VNM"], field="high", aggregate="mean")
    m.assert_called_once_with(
        tickers=["VCB", "VNM"], field="high", aggregate="mean",
        days=None, weeks=None, months=None, start_date=None, end_date=None,
    )


@patch("application.agents.tool_registry.handle_aggregate_query")
def test_aggregate_prices_params(m):
    m.return_value = {"data": "ok"}
    aggregate_prices.func(
        tickers=["VCB", "HPG"], field="volume", aggregate_fn="sum",
    )
    m.assert_called_once_with(
        tickers=["VCB", "HPG"], field="volume", aggregate_fn="sum",
        days=None, weeks=None, months=None, start_date=None, end_date=None,
    )


@patch("application.agents.tool_registry.handle_financial_ratio_query")
def test_get_financial_ratios_params(m):
    m.return_value = {"data": "ok"}
    get_financial_ratios.func(tickers=["VCB"], field="roe")
    m.assert_called_once_with(tickers=["VCB"], field="roe")


@patch("application.agents.tool_registry.handle_company_query")
def test_get_company_info_params(m):
    m.return_value = {"data": "ok"}
    get_company_info.func(tickers=["VCB"], field="executives")
    m.assert_called_once_with(tickers=["VCB"], field="executives")


@patch("application.agents.tool_registry.handle_news_sentiment_query")
def test_get_news_and_sentiment_params(m):
    m.return_value = {"data": "ok"}
    get_news_and_sentiment.func(
        tickers=["VCB"], field="sentiment", compare_with=["VNM"], days=7,
    )
    m.assert_called_once_with(
        tickers=["VCB"], field="sentiment", compare_with=["VNM"],
        days=7, weeks=None, months=None,
    )


@patch("application.agents.tool_registry.handle_portfolio_query")
def test_manage_portfolio_params(m):
    m.return_value = {"data": "ok"}
    manage_portfolio.func(field="portfolio_value", portfolio={"VCB": 10})
    m.assert_called_once_with(
        field="portfolio_value", portfolio={"VCB": 10}, tickers=None,
    )


@patch("application.agents.tool_registry.handle_alert_query")
def test_check_price_alert_params(m):
    m.return_value = {"data": "ok"}
    check_price_alert.func(
        tickers=["VCB"], threshold=105.0, condition="below", timeframe="1w",
    )
    m.assert_called_once_with(
        tickers=["VCB"], threshold=105.0, condition="below", timeframe="1w",
    )


@patch("application.agents.tool_registry.handle_forecast_query")
def test_forecast_stock_price_params(m):
    m.return_value = {"data": "ok"}
    forecast_stock_price.func(tickers=["HPG"], timeframe="1m")
    m.assert_called_once_with(tickers=["HPG"], timeframe="1m")


@patch("application.agents.tool_registry.handle_sector_query")
def test_analyze_sector_params(m):
    m.return_value = {"data": "ok"}
    analyze_sector.func(sector="technology", metric="volume", timeframe="1m")
    m.assert_called_once_with(sector="technology", metric="volume", timeframe="1m")


# ---------------------------------------------------------------------------
# Empty / edge-case tool calls
# ---------------------------------------------------------------------------


@patch("application.agents.tool_registry.handle_price_query", return_value={"error": "Missing ticker"})
def test_get_stock_price_empty_tickers(m):
    result = get_stock_price.func(tickers=[])
    assert TOOL_ERR_PREFIX in result


@patch("application.agents.tool_registry.handle_indicator_query", return_value={"error": "Missing ticker"})
def test_calculate_technical_indicator_empty_tickers(m):
    result = calculate_technical_indicator.func(tickers=[])
    assert TOOL_ERR_PREFIX in result


@patch("application.agents.tool_registry.handle_compare_query", return_value={"error": "Missing ticker"})
def test_compare_stocks_empty_tickers(m):
    result = compare_stocks.func(tickers=[], compare_with=["VNM"])
    assert TOOL_ERR_PREFIX in result


@patch("application.agents.tool_registry.handle_compare_query", return_value={"error": "Missing compare_with"})
def test_compare_stocks_empty_compare_with(m):
    result = compare_stocks.func(tickers=["VCB"], compare_with=[])
    assert TOOL_ERR_PREFIX in result


@patch("application.agents.tool_registry.handle_forecast_query", return_value={"error": "Missing ticker"})
def test_forecast_empty_tickers(m):
    result = forecast_stock_price.func(tickers=[])
    assert TOOL_ERR_PREFIX in result
