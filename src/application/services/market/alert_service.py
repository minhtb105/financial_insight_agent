from typing import Dict, Any, Optional
from infrastructure.api_clients.vn_stock_client import VNStockClient
from infrastructure.observability import get_logger

logger = get_logger(__name__)


def handle_alert_query(parsed: Dict[str, Any]) -> Dict[str, Any]:
    tickers = parsed.get("tickers") or []
    threshold = parsed.get("threshold", 0.0)
    condition = parsed.get("condition", "above")
    timeframe = parsed.get("timeframe", "1d")

    if not tickers or threshold == 0.0:
        return {"error": "Missing tickers or threshold parameter"}

    try:
        results = []
        for ticker in tickers:
            try:
                client = VNStockClient(ticker=ticker)
                data = client.fetch_trading_data(end=None, interval="1d")

                if data is None or data.empty:
                    results.append({
                        "ticker": ticker,
                        "error": "No price data available",
                    })
                    continue

                current_price = float(data.iloc[-1]["close"])
                triggered = (
                    (condition == "above" and current_price >= threshold)
                    or (condition == "below" and current_price <= threshold)
                )

                results.append({
                    "ticker": ticker,
                    "current_price": current_price,
                    "threshold": threshold,
                    "condition": condition,
                    "triggered": triggered,
                })

            except Exception as e:
                logger.error(f"Alert check failed for {ticker}: {e}")
                results.append({"ticker": ticker, "error": str(e)})

        if not results:
            return {"error": "Alert monitoring requires price data"}

        return {
            "alerts": results,
            "timeframe": timeframe,
            "summary": {
                "total": len(results),
                "triggered": sum(1 for r in results if r.get("triggered")),
            },
        }

    except Exception as e:
        logger.error(f"Alert query failed: {e}")
        return {"error": f"Alert monitoring requires price data: {e}"}