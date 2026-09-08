import os
import json
import threading
from collections.abc import Callable
from typing import Any
from datetime import datetime, timezone
from pathlib import Path
import logging
from shared.constants import PORTFOLIO_TTL_HOURS
from shared.ports.cache_port import CachePort
from shared.ports.market_data_port import MarketDataPort
from shared.ports.company_port import CompanyPort
from shared.utils.cache_keys import make_cache_key
from shared.base_service import BaseService

_PORTFOLIO_SECTOR_CACHE_HOURS = 4


class PortfolioManager:
    _file_lock: threading.Lock = threading.Lock()

    def __init__(self, portfolio_file: str | None = None, user_id: str = "default"):
        self.user_id = user_id
        self.portfolio_file = (
            portfolio_file or os.getenv("PORTFOLIO_FILE") or f"user_portfolio_{user_id}.json"
        )
        self.portfolio = self.load_portfolio()

    def load_portfolio(self) -> dict[str, Any]:
        with self._file_lock:
            if Path(self.portfolio_file).exists():
                try:
                    with Path(self.portfolio_file).open() as f:
                        return json.load(f)
                except (OSError, json.JSONDecodeError):
                    return {"holdings": {}, "transactions": []}
            return {"holdings": {}, "transactions": []}

    def save_portfolio(self):
        with self._file_lock:
            path = Path(self.portfolio_file)
            tmp = path.with_suffix(".tmp")
            with tmp.open("w") as f:
                json.dump(self.portfolio, f, indent=2, default=str)
            tmp.replace(path)

    def add_holding(self, ticker: str, quantity: int, price: float):
        if ticker not in self.portfolio["holdings"]:
            self.portfolio["holdings"][ticker] = 0
        self.portfolio["holdings"][ticker] += quantity

        self.portfolio["transactions"].append(
            {
                "ticker": ticker,
                "quantity": quantity,
                "price": price,
                "date": datetime.now(timezone.utc).isoformat(),
                "type": "buy",
            }
        )

        self.save_portfolio()

    def remove_holding(self, ticker: str, quantity: int, price: float):
        if ticker in self.portfolio["holdings"]:
            self.portfolio["holdings"][ticker] = max(
                0, self.portfolio["holdings"][ticker] - quantity
            )

            buy_txns = [
                t
                for t in self.portfolio["transactions"]
                if t["ticker"] == ticker and t["type"] == "buy"
            ]
            total_cost = sum(t["quantity"] * t["price"] for t in buy_txns)
            total_qty = sum(t["quantity"] for t in buy_txns)
            avg_cost = total_cost / total_qty if total_qty > 0 else 0.0
            realized_pnl = (price - avg_cost) * quantity

            self.portfolio["transactions"].append(
                {
                    "ticker": ticker,
                    "quantity": quantity,
                    "price": price,
                    "realized_pnl": round(realized_pnl, 2),
                    "date": datetime.now(timezone.utc).isoformat(),
                    "type": "sell",
                }
            )

            self.save_portfolio()

    def get_holdings(self) -> dict[str, int]:
        return dict(self.portfolio["holdings"])

    def get_transactions(self) -> list[dict]:
        return self.portfolio["transactions"]


_PORTFOLIO_FIELD_HANDLERS: dict[str, Callable[["PortfolioService"], dict[str, Any]]] = {
    "portfolio_value": lambda self: self.get_portfolio_value({}),
    "portfolio_performance": lambda self: self.get_portfolio_performance({}),
}


class PortfolioService(BaseService):
    def __init__(self, cache: CachePort, market_data: MarketDataPort, company_port: CompanyPort) -> None:
        """Khởi tạo PortfolioService — strict DI."""
        super().__init__("PortfolioService", cache, market_data)
        self._company = company_port

    def _fetch_price(self, ticker: str, quantity: int, today_str: str) -> dict[str, Any]:
        cache = self._cache
        try:
            cache_key = make_cache_key(
                "portfolio_price", ticker, today_str, today_str, interval="1d"
            )
            cached_price = cache.get(cache_key) if cache else None
            if cached_price is not None:
                price = cached_price
            else:
                result = self._market_data.get_price_data(ticker, today_str, today_str)
                if result is None or "error" in result or not result.get("data"):
                    return {"error": f"No price data for {ticker}"}
                price = float(result["data"][-1]["close"])
                if cache:
                    cache.set(cache_key, price, ttl_hours=PORTFOLIO_TTL_HOURS)

            value = price * quantity
            return {"ticker": ticker, "quantity": quantity, "current_price": price, "value": value}
        except Exception as e:
            self.logger.error(f"Error fetching price for {ticker}: {e}")
            return {"error": str(e)}

    def _fetch_sector_and_price(self, ticker: str, quantity: int, today_str: str) -> dict[str, Any]:
        cache = self._cache
        try:
            sector_cache_key = make_cache_key("portfolio_sector", ticker)
            cached_sector = cache.get(sector_cache_key) if cache else None
            sector = cached_sector if cached_sector else "Unknown"

            price_cache_key = make_cache_key(
                "portfolio_price", ticker, today_str, today_str, interval="1d"
            )
            cached_price = cache.get(price_cache_key) if cache else None
            if cached_price is not None:
                price = cached_price
            else:
                result = self._market_data.get_price_data(ticker, today_str, today_str)
                if result is None or "error" in result or not result.get("data"):
                    return {"error": f"No price data for {ticker}"}
                price = float(result["data"][-1]["close"])
                if cache:
                    cache.set(sector_cache_key, sector, ttl_hours=_PORTFOLIO_SECTOR_CACHE_HOURS)
                    cache.set(price_cache_key, price, ttl_hours=PORTFOLIO_TTL_HOURS)

            value = price * quantity
            return {"ticker": ticker, "sector": sector, "value": value}
        except Exception as e:
            self.logger.error(f"Error getting allocation for {ticker}: {e}")
            return {"error": str(e)}

    def get_portfolio_value(self, _query: dict) -> dict[str, Any]:
        portfolio_manager = PortfolioManager()
        holdings = portfolio_manager.get_holdings()

        if not holdings:
            return {"portfolio_value": 0, "holdings": {}}

        try:
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            def fetch_price(ticker: str) -> dict[str, Any]:
                return self._fetch_price(ticker, holdings[ticker], today_str)

            results = self.for_each_ticker(list(holdings.keys()), fetch_price)
            total_value = 0
            holding_values = {}

            for ticker, result in results.items():
                if ticker == "error":
                    continue
                if isinstance(result, dict) and "error" not in result and result.get("ticker"):
                    total_value += result["value"]
                    holding_values[ticker] = {
                        "quantity": result["quantity"],
                        "current_price": result["current_price"],
                        "value": result["value"],
                    }

            return {"portfolio_value": total_value, "holdings": holding_values}

        except Exception as e:
            self.logger.error(f"Error calculating portfolio value: {e}")
            return {"error": str(e)}

    def get_portfolio_performance(self, query: dict) -> dict[str, Any]:
        portfolio_manager = PortfolioManager()
        transactions = portfolio_manager.get_transactions()

        if not transactions:
            return {"performance": {}, "total_return": 0}

        try:
            total_cost = 0.0
            total_proceeds = 0.0

            for transaction in transactions:
                if transaction["type"] == "buy":
                    total_cost += transaction["quantity"] * transaction["price"]
                elif transaction["type"] == "sell":
                    total_proceeds += transaction["quantity"] * transaction["price"]

            portfolio_value = self.get_portfolio_value(query)
            total_current_value = portfolio_value.get("portfolio_value", 0)

            total_return = total_current_value + total_proceeds - total_cost
            return_rate = (total_return / total_cost * 100) if total_cost > 0 else 0.0

            return {
                "total_cost": total_cost,
                "total_proceeds": total_proceeds,
                "current_value": total_current_value,
                "total_return": total_return,
                "return_rate": return_rate,
            }

        except Exception as e:
            self.logger.error(f"Error calculating portfolio performance: {e}")
            return {"error": str(e)}

    def get_portfolio_allocation(self, _query: dict) -> dict[str, Any]:
        portfolio_manager = PortfolioManager()
        holdings = portfolio_manager.get_holdings()

        if not holdings:
            return {"allocation": {}, "diversification_score": 0}

        try:
            today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

            def fetch_sector_and_price(ticker: str) -> dict[str, Any]:
                return self._fetch_sector_and_price(ticker, holdings[ticker], today_str)

            results = self.for_each_ticker(list(holdings.keys()), fetch_sector_and_price)
            allocation = {}
            total_value = 0

            for ticker, result in results.items():
                if ticker == "error":
                    continue
                if isinstance(result, dict) and "error" not in result and result.get("ticker"):
                    sector = result["sector"]
                    value = result["value"]
                    total_value += value
                    if sector not in allocation:
                        allocation[sector] = 0
                    allocation[sector] += value

            if total_value > 0:
                for sector, val in list(allocation.items()):
                    allocation[sector] = {
                        "value": val,
                        "percentage": (val / total_value) * 100,
                    }

            num_sectors = len(allocation)
            if num_sectors == 0:
                diversification_score = 0
            elif num_sectors == 1:
                diversification_score = 20
            elif num_sectors == 2:
                diversification_score = 50
            elif num_sectors == 3:
                diversification_score = 70
            elif num_sectors == 4:
                diversification_score = 85
            else:
                diversification_score = 100

            return {
                "allocation": allocation,
                "diversification_score": diversification_score,
                "total_value": total_value,
            }

        except Exception as e:
            self.logger.error(f"Error calculating portfolio allocation: {e}")
            return {"error": str(e)}

    def _update_portfolio_data(self, portfolio_data: dict[str, int]) -> None:
        portfolio_manager = PortfolioManager()
        for ticker, quantity in portfolio_data.items():
            if quantity <= 0:
                continue
            portfolio_manager.add_holding(ticker=ticker, quantity=quantity, price=0.0)

    def handle_query(
        self,
        requested_field: str,
        portfolio: dict[str, int] | None = None,
    ) -> dict[str, Any]:
        if portfolio:
            self._update_portfolio_data(portfolio)

        try:
            handler = _PORTFOLIO_FIELD_HANDLERS.get(requested_field)
            if handler is not None:
                return handler(self)
            if requested_field in ("portfolio_summary", "portfolio_allocation"):
                result: dict[str, Any] = {}
                portfolio_value = self.get_portfolio_value({})
                if portfolio_value and "error" not in portfolio_value:
                    result["portfolio_value"] = portfolio_value

                portfolio_performance = self.get_portfolio_performance({})
                if portfolio_performance and "error" not in portfolio_performance:
                    result["portfolio_performance"] = portfolio_performance

                portfolio_allocation = self.get_portfolio_allocation({})
                if portfolio_allocation and "error" not in portfolio_allocation:
                    result["portfolio_allocation"] = portfolio_allocation

                return result if result else {"error": "No portfolio data found"}

            return {"error": f"Unknown requested_field: {requested_field}"}

        except Exception as e:
            return {"error": str(e)}

def handle_portfolio_query(field: str = "portfolio_summary",
    portfolio: dict[str, int] | None = None,) -> dict[str, Any]:
    from shared.service_registry import get_service
    svc = get_service("portfolio")
    if svc is None:
        raise RuntimeError("Service 'portfolio' not initialized — call init_deps()")
    return svc.handle_query(field=field, portfolio=portfolio)

