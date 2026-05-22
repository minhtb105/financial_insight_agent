"""
Tool registry for the true tool-calling agent.

Each tool has explicit typed parameters so the LLM can autonomously decide
which tool to call and with what arguments — no pre-parsing pipeline needed.
"""

import json
import logging
from collections.abc import Callable
from typing import Any

from langchain.tools import tool

from application.services.financial.aggregate_service import handle_aggregate_query
from application.services.company.company_service import handle_company_query
from application.services.market.compare_service import handle_compare_query
from application.services.market.indicator_service import handle_indicator_query
from application.services.market.price_service import handle_price_query
from application.services.financial.ranking_service import handle_ranking_query
from application.services.financial.financial_ratio_service import handle_financial_ratio_query
from application.services.portfolio.news_sentiment_service import handle_news_sentiment_query
from application.services.portfolio.portfolio_service import handle_portfolio_query
from application.services.market.alert_service import handle_alert_query
from application.services.market.forecast_service import handle_forecast_query
from application.services.market.sector_service import handle_sector_query

logger = logging.getLogger(__name__)
TOOL_ERR_PREFIX = "TOOL_ERR#"


def _categorize_error(e: Exception) -> str:
    if isinstance(e, TimeoutError):
        return f"{TOOL_ERR_PREFIX}TIMEOUT {e}"
    if isinstance(e, ValueError):
        return f"{TOOL_ERR_PREFIX}VALIDATION {e}"
    if isinstance(e, KeyError):
        return f"{TOOL_ERR_PREFIX}NOT_FOUND {e}"
    if isinstance(e, PermissionError):
        return f"{TOOL_ERR_PREFIX}AUTH {e}"
    return f"{TOOL_ERR_PREFIX}UNKNOWN {e}"


def _safe_json(obj: Any) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    except (TypeError, ValueError):
        return str(obj)


def _wrap(fn_name: str, result: Any) -> str:
    if result is None:
        return _safe_json({"data": None, "note": f"No data returned for {fn_name}"})
    if isinstance(result, dict) and "error" in result:
        result = dict(result)
        error_keys = {k for k in result if k != "error"}
        if not error_keys:
            return _safe_json({"data": None, "note": f"Service error for {fn_name}: {result['error']}"})
        result["_partial_error"] = True
        result["_error"] = result.pop("error")
    return _safe_json(result)


def _call_service(name: str, fn: Callable[..., Any], /, *args, **kwargs) -> str:
    """Wrap a service call with standard try/except + _wrap.

    Called inside each tool function so that ``@tool`` sees the real
    typed signature and generates a correct schema for the LLM.
    """
    try:
        result = fn(*args, **kwargs)
    except Exception as e:
        logger.exception("%s failed", name)
        return _categorize_error(e)
    return _wrap(name, result)


# ---------------------------------------------------------------------------
# Tools — typed signatures enable genuine LLM tool-calling
# ---------------------------------------------------------------------------


@tool(description="""
Fetch OHLCV price data for one or more tickers.
Use when asked about price, open/close/high/low prices, or trading volume.
field: open | close | high | low | volume | ohlcv (default: close)
Do NOT use for technical indicators, ranking, comparison, aggregation, financial ratios.
""")
def get_stock_price(
    tickers: list[str],
    field: str = "close",
    days: int | None = None,
    weeks: int | None = None,
    months: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    return _call_service(
        "get_stock_price", handle_price_query,
        tickers=tickers, field=field, days=days, weeks=weeks,
        months=months, start_date=start_date, end_date=end_date,
    )


@tool(description="""
Compute technical indicators (SMA/RSI/MACD) for one or more tickers.
indicator: sma | rsi | macd (default: sma)
period: lookback period for SMA/RSI (default SMA=20, RSI=14)
fast_period / slow_period: used only for MACD (default 12/26)
Do NOT use for raw OHLCV prices (use get_stock_price), ranking, comparison.
""")
def calculate_technical_indicator(
    tickers: list[str],
    indicator: str = "sma",
    period: int | None = None,
    fast_period: int | None = None,
    slow_period: int | None = None,
    days: int | None = None,
    weeks: int | None = None,
    months: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    return _call_service(
        "calculate_technical_indicator", handle_indicator_query,
        tickers=tickers, indicator=indicator, period=period,
        fast_period=fast_period, slow_period=slow_period,
        days=days, weeks=weeks, months=months,
        start_date=start_date, end_date=end_date,
    )


@tool(description="""
Compare price data between a main group (tickers) and a reference group (compare_with).
field: close | open | high | low | volume (default: close)
Do NOT use for a single group of tickers (use get_stock_price) or aggregation (use aggregate_prices).
""")
def compare_stocks(
    tickers: list[str],
    compare_with: list[str],
    field: str = "close",
    days: int | None = None,
    weeks: int | None = None,
    months: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    return _call_service(
        "compare_stocks", handle_compare_query,
        tickers=tickers, compare_with=compare_with, field=field,
        days=days, weeks=weeks, months=months,
        start_date=start_date, end_date=end_date,
    )


@tool(description="""
Rank 2+ tickers by a price field.
field: close | open | high | low | volume (default: close)
aggregate: max | min | mean | latest — aggregation method for ranking (default: max)
Requires at least 2 tickers. Do NOT use for two-group comparison (use compare_stocks).
""")
def rank_stocks(
    tickers: list[str],
    field: str = "close",
    aggregate: str = "max",
    days: int | None = None,
    weeks: int | None = None,
    months: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    return _call_service(
        "rank_stocks", handle_ranking_query,
        tickers=tickers, field=field, aggregate=aggregate,
        days=days, weeks=weeks, months=months,
        start_date=start_date, end_date=end_date,
    )


@tool(description="""
Compute statistical aggregation (mean/sum/median/std/min/max) over 1+ tickers.
field: close | open | high | low | volume (default: close)
aggregate_fn: mean | sum | median | std | min | max (default: mean)
Do NOT use for per-ticker ranking (use rank_stocks) or comparison (use compare_stocks).
""")
def aggregate_prices(
    tickers: list[str],
    field: str = "close",
    aggregate_fn: str = "mean",
    days: int | None = None,
    weeks: int | None = None,
    months: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> Any:
    return _call_service(
        "aggregate_prices", handle_aggregate_query,
        tickers=tickers, field=field, aggregate_fn=aggregate_fn,
        days=days, weeks=weeks, months=months,
        start_date=start_date, end_date=end_date,
    )


@tool(description="""
Fetch financial ratios (PE, PB, ROE, EPS, debt_to_equity, etc.) for tickers.
field: pe | pb | roe | eps | current_ratio | debt_to_equity | profit_margin |
       quick_ratio | asset_turnover | dividend_yield (default: pe)
Do NOT use for stock prices, technical indicators, or company info.
""")
def get_financial_ratios(
    tickers: list[str],
    field: str = "pe",
) -> Any:
    return _call_service("get_financial_ratios", handle_financial_ratio_query, tickers=tickers, field=field)


@tool(description="""
Fetch company info: shareholders, executives, subsidiaries.
field: shareholders | executives | subsidiaries (default: shareholders)
Do NOT use for stock prices, technical indicators, or financial ratios.
""")
def get_company_info(
    tickers: list[str],
    field: str = "shareholders",
) -> Any:
    return _call_service("get_company_info", handle_company_query, tickers=tickers, field=field)


@tool(description="""
Fetch news, market sentiment, and social volume for tickers.
field: news | sentiment | social_volume | all (default: all)
compare_with: optional list of reference tickers for sentiment comparison
Do NOT use for stock prices, technical indicators, or financial ratios.
""")
def get_news_and_sentiment(
    tickers: list[str],
    field: str = "all",
    compare_with: list[str] | None = None,
    days: int | None = None,
    weeks: int | None = None,
    months: int | None = None,
) -> Any:
    return _call_service(
        "get_news_and_sentiment", handle_news_sentiment_query,
        tickers=tickers, field=field, compare_with=compare_with,
        days=days, weeks=weeks, months=months,
    )


@tool(description="""
Manage and analyze investment portfolios.
field: portfolio_value | portfolio_performance | portfolio_allocation | portfolio_summary (default: portfolio_summary)
portfolio: dict {ticker: share_count} to update the portfolio (optional)
Do NOT use for single-ticker analysis, company info, or news.
""")
def manage_portfolio(
    field: str = "portfolio_summary",
    portfolio: dict[str, int] | None = None,
) -> Any:
    return _call_service("manage_portfolio", handle_portfolio_query, field=field, portfolio=portfolio)


@tool(description="""
Set a price alert when a ticker crosses above or below a threshold.
condition: above | below (default: above)
timeframe: check interval, e.g. 1d (default: 1d)
Do NOT use for forecasting, sector analysis, or ranking.
""")
def check_price_alert(
    tickers: list[str],
    threshold: float,
    condition: str = "above",
    timeframe: str = "1d",
) -> Any:
    return _call_service(
        "check_price_alert", handle_alert_query,
        tickers=tickers, threshold=threshold, condition=condition, timeframe=timeframe,
    )


@tool(description="""
Forecast stock prices based on historical data (SMA + recent trend).
timeframe: forecast horizon, e.g. 1d | 1w | 1m (default: 1w)
Do NOT use for technical indicators, price alerts, or sector analysis.
""")
def forecast_stock_price(
    tickers: list[str],
    timeframe: str = "1w",
) -> Any:
    return _call_service("forecast_stock_price", handle_forecast_query, tickers=tickers, timeframe=timeframe)


@tool(description="""
Analyze stock performance by sector/industry.
sector: sector name, e.g. banking | real_estate | technology | energy
metric: performance | volume (default: performance)
timeframe: lookback period, e.g. 1w | 1m (default: 1w)
Do NOT use for single-ticker analysis or technical indicators.
""")
def analyze_sector(
    sector: str,
    metric: str = "performance",
    timeframe: str = "1w",
) -> Any:
    return _call_service(
        "analyze_sector", handle_sector_query,
        sector=sector, metric=metric, timeframe=timeframe,
    )


# ---------------------------------------------------------------------------
# Public exports
# ---------------------------------------------------------------------------

ALL_TOOLS: list = [
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
]

__all__ = ["ALL_TOOLS", "TOOL_ERR_PREFIX"]
