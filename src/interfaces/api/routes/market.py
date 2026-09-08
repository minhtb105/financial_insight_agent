"""Market data REST endpoints — direct service access for frontend BFF.

These endpoints expose the same logic as MCP tools but via HTTP GET for the
Next.js dashboard. They delegate to ``handle_*_query`` wrappers which use the
service registry (strict DI). No LLM involved.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Query

router = APIRouter(prefix="/market", tags=["market"])


def _parse_tickers(tickers: str) -> list[str]:
    return [t.strip().upper() for t in tickers.split(",") if t.strip()]


@router.get("/prices", summary="Get price data")
async def get_prices(
    tickers: str = Query(..., description="Comma-separated tickers e.g. VCB,FPT"),
    field: Literal["close", "open", "high", "low", "volume", "ohlcv"] = Query("close"),
    days: int | None = Query(None, ge=1),
    weeks: int | None = Query(None, ge=1),
    months: int | None = Query(None, ge=1),
    years: int | None = Query(None, ge=1),
    start_date: str | None = Query(None, description="YYYY-MM-DD"),
    end_date: str | None = Query(None, description="YYYY-MM-DD"),
) -> dict[str, Any]:
    from application.services.market.price_service import handle_price_query

    tick_list = _parse_tickers(tickers)
    return handle_price_query(
        tickers=tick_list, field=field, days=days, weeks=weeks, months=months, years=years, start_date=start_date, end_date=end_date
    )


@router.get("/candles", summary="Get OHLCV candles + indicators for chart")
async def get_candles(
    ticker: str = Query(..., description="Single ticker e.g. VCB"),
    days: int | None = Query(30, ge=1, le=365 * 5),
    weeks: int | None = Query(None, ge=1),
    months: int | None = Query(None, ge=1),
    years: int | None = Query(None, ge=1),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
) -> dict[str, Any]:
    from application.services.market.indicator_service import handle_indicator_query
    from application.services.market.price_service import handle_price_query

    tick_list = [ticker.strip().upper()]
    price_res = handle_price_query(
        tickers=tick_list, field="close", days=days, weeks=weeks, months=months, years=years, start_date=start_date, end_date=end_date
    )
    # Extract raw candles from price result
    ticker_data = price_res.get(ticker, {}) if isinstance(price_res, dict) else {}
    raw_candles = ticker_data.get("data", []) if isinstance(ticker_data, dict) else []

    # Fetch indicators (SMA9 + RSI14) for overlay
    ind_res = handle_indicator_query(tickers=tick_list, indicator="sma", period=9, days=days, weeks=weeks, months=months, start_date=start_date, end_date=end_date)
    rsi_res = handle_indicator_query(tickers=tick_list, indicator="rsi", period=14, days=days, weeks=weeks, months=months, start_date=start_date, end_date=end_date)

    # Merge by date: price candles + sma/rsi
    sma_map: dict[str, float] = {}
    rsi_map: dict[str, float] = {}
    if isinstance(ind_res, dict):
        t_ind = ind_res.get(ticker, {})
        if isinstance(t_ind, dict):
            for entry in t_ind.get("sma_9", []) + t_ind.get("sma_9", []):
                sma_map[entry.get("date", "")] = entry.get("sma", 0)
            # indicator returns keys like sma_9, sma_20 etc
            for k, v in t_ind.items():
                if k.startswith("sma"):
                    for e in v if isinstance(v, list) else []:
                        sma_map[e.get("date", "")] = e.get("sma", e.get("value", 0))
    if isinstance(rsi_res, dict):
        t_rsi = rsi_res.get(ticker, {})
        if isinstance(t_rsi, dict):
            for k, v in t_rsi.items():
                if k.startswith("rsi"):
                    for e in v if isinstance(v, list) else []:
                        rsi_map[e.get("date", "")] = e.get("rsi", e.get("value", 0))

    merged: list[dict[str, Any]] = []
    for c in raw_candles:
        d = c.get("date", "")
        merged.append(
            {
                "date": d,
                "price": c.get("close", 0),
                "open": c.get("open_price", c.get("open")),
                "high": c.get("high"),
                "low": c.get("low"),
                "volume": c.get("volume"),
                "sma9": sma_map.get(d),
                "rsi": rsi_map.get(d),
            }
        )
    return {"ticker": ticker, "candles": merged, "count": len(merged)}


@router.get("/indicators", summary="Get technical indicators")
async def get_indicators(
    tickers: str = Query(..., description="Comma-separated tickers"),
    indicator: Literal["sma", "rsi", "macd"] = Query("sma"),
    period: int | None = Query(None, ge=1),
    days: int | None = Query(None, ge=1),
    weeks: int | None = Query(None, ge=1),
    months: int | None = Query(None, ge=1),
    years: int | None = Query(None, ge=1),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
) -> dict[str, Any]:
    from application.services.market.indicator_service import handle_indicator_query

    tick_list = _parse_tickers(tickers)
    return handle_indicator_query(
        tickers=tick_list, indicator=indicator, period=period, days=days, weeks=weeks, months=months, start_date=start_date, end_date=end_date
    )


@router.get("/sector", summary="Get sector performance")
async def get_sector(
    sector: str = Query(..., description="Sector name e.g. Ngan hang, Cong nghe"),
    metric: Literal["performance", "volume"] = Query("performance"),
    timeframe: Literal["1d", "5d", "1w", "2w", "1m", "3m"] = Query("1w"),
) -> dict[str, Any]:
    from application.services.market.sector_service import handle_sector_query

    return handle_sector_query(sector=sector, metric=metric, timeframe=timeframe)


@router.get("/sectors", summary="Get multiple sectors summary (dashboard)")
async def get_sectors(
    timeframe: Literal["1d", "5d", "1w", "2w", "1m", "3m"] = Query("1w"),
) -> dict[str, Any]:
    from application.services.market.sector_service import handle_sector_query

    sectors = ["Ngân hàng", "Bất động sản", "Công nghệ", "Thép", "Tiêu dùng"]
    results: list[dict[str, Any]] = []
    for s in sectors:
        try:
            data = handle_sector_query(sector=s, metric="performance", timeframe=timeframe)
            ranked = data.get("ranked_tickers", [])
            top = ranked[0] if ranked else {}
            # compute avg performance
            avg_perf = 0.0
            if ranked:
                avg_perf = sum(r.get("performance_pct", 0) for r in ranked[:5]) / min(5, len(ranked))
            results.append(
                {
                    "sector": s,
                    "changePct": round(avg_perf, 2),
                    "topTicker": top.get("ticker", ""),
                    "totalTickers": data.get("total_tickers", 0),
                }
            )
        except Exception:
            results.append({"sector": s, "changePct": 0, "topTicker": "", "totalTickers": 0})
    return {"sectors": results, "timeframe": timeframe}


@router.get("/portfolio", summary="Get portfolio summary")
async def get_portfolio(
    field: str = Query("portfolio_summary", description="portfolio_summary|portfolio_value|portfolio_performance|portfolio_allocation"),
) -> dict[str, Any]:
    from application.services.portfolio.portfolio_service import handle_portfolio_query

    return handle_portfolio_query(field=field)


@router.get("/compare", summary="Compare tickers")
async def compare_tickers(
    tickers: str = Query(..., description="Main tickers comma-separated"),
    compare_with: str = Query(..., description="Compare tickers comma-separated"),
    field: str = Query("close"),
    days: int | None = Query(None, ge=1),
    weeks: int | None = Query(None, ge=1),
    months: int | None = Query(None, ge=1),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
) -> dict[str, Any]:
    from application.services.market.compare_service import handle_compare_query

    return handle_compare_query(
        tickers=_parse_tickers(tickers),
        compare_with=_parse_tickers(compare_with),
        field=field,
        days=days,
        weeks=weeks,
        months=months,
        start_date=start_date,
        end_date=end_date,
    )


@router.get("/ranking", summary="Rank tickers")
async def ranking(
    tickers: str = Query(..., description="Comma-separated tickers"),
    field: str = Query("close"),
    aggregate: Literal["max", "min", "mean", "latest"] = Query("max"),
    days: int | None = Query(None, ge=1),
    weeks: int | None = Query(None, ge=1),
    months: int | None = Query(None, ge=1),
    start_date: str | None = Query(None),
    end_date: str | None = Query(None),
) -> dict[str, Any]:
    from application.services.financial.ranking_service import handle_ranking_query

    return handle_ranking_query(
        tickers=_parse_tickers(tickers), field=field, aggregate=aggregate, days=days, weeks=weeks, months=months, start_date=start_date, end_date=end_date
    )
