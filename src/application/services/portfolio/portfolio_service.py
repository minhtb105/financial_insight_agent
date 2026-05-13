from typing import Dict, Any, List, Optional
from datetime import datetime
import json
import os
from infrastructure.cache import get_cache_manager
from infrastructure.cache.cache_keys import make_cache_key

_PORTFOLIO_TTL_HOURS = 0.25
_SECTOR_TTL_HOURS = 4


def _cache() -> Optional[Any]:
    return get_cache_manager()


class PortfolioManager:
    def __init__(self, portfolio_file: str = "user_portfolio.json"):
        self.portfolio_file = portfolio_file
        self.portfolio = self.load_portfolio()

    def load_portfolio(self) -> Dict[str, Any]:
        if os.path.exists(self.portfolio_file):
            try:
                with open(self.portfolio_file, 'r') as f:
                    return json.load(f)
            except:
                return {"holdings": {}, "transactions": []}
        return {"holdings": {}, "transactions": []}

    def save_portfolio(self):
        try:
            with open(self.portfolio_file, 'w') as f:
                json.dump(self.portfolio, f, indent=2)
        except Exception as e:
            print(f"Error saving portfolio: {e}")

    def add_holding(self, ticker: str, quantity: int, price: float):
        if ticker not in self.portfolio["holdings"]:
            self.portfolio["holdings"][ticker] = 0
        self.portfolio["holdings"][ticker] += quantity

        self.portfolio["transactions"].append({
            "ticker": ticker,
            "quantity": quantity,
            "price": price,
            "date": datetime.now().isoformat(),
            "type": "buy"
        })

        self.save_portfolio()

    def remove_holding(self, ticker: str, quantity: int, price: float):
        if ticker in self.portfolio["holdings"]:
            self.portfolio["holdings"][ticker] = max(0, self.portfolio["holdings"][ticker] - quantity)

            self.portfolio["transactions"].append({
                "ticker": ticker,
                "quantity": quantity,
                "price": price,
                "date": datetime.now().isoformat(),
                "type": "sell"
            })

            self.save_portfolio()

    def get_holdings(self) -> Dict[str, int]:
        return self.portfolio["holdings"]

    def get_transactions(self) -> List[Dict]:
        return self.portfolio["transactions"]


def get_portfolio_value(query: dict) -> Dict[str, Any]:
    portfolio_manager = PortfolioManager()
    holdings = portfolio_manager.get_holdings()

    if not holdings:
        return {"portfolio_value": 0, "holdings": {}}

    try:
        cache = _cache()
        from infrastructure.api_clients.vn_stock_client import VNStockClient
        total_value = 0
        holding_values = {}

        today_str = datetime.now().strftime("%Y-%m-%d")

        for ticker, quantity in holdings.items():
            if quantity > 0:
                try:
                    cache_key = make_cache_key("portfolio_price", ticker, today_str, today_str, interval="1d")
                    cached_price = cache.get(cache_key) if cache else None
                    if cached_price is not None:
                        price = cached_price
                    else:
                        client = VNStockClient(ticker=ticker)
                        current_price = client.fetch_trading_data(
                            start=today_str,
                            end=today_str,
                            interval="1d"
                        )

                        if current_price is None or current_price.empty:
                            continue
                        price = float(current_price["close"].iloc[-1])
                        if cache:
                            cache.set(cache_key, price, ttl_hours=_PORTFOLIO_TTL_HOURS)

                    value = price * quantity
                    total_value += value
                    holding_values[ticker] = {
                        "quantity": quantity,
                        "current_price": price,
                        "value": value
                    }
                except Exception as e:
                    print(f"Error getting price for {ticker}: {e}")

        return {
            "portfolio_value": total_value,
            "holdings": holding_values
        }

    except Exception as e:
        print(f"Error calculating portfolio value: {e}")
        return {"error": str(e)}


def get_portfolio_performance(query: dict) -> Dict[str, Any]:
    portfolio_manager = PortfolioManager()
    transactions = portfolio_manager.get_transactions()

    if not transactions:
        return {"performance": {}, "total_return": 0}

    try:
        total_invested = 0
        total_current_value = 0

        for transaction in transactions:
            if transaction["type"] == "buy":
                total_invested += transaction["quantity"] * transaction["price"]

        portfolio_value = get_portfolio_value(query)
        if "portfolio_value" in portfolio_value:
            total_current_value = portfolio_value["portfolio_value"]

        total_return = total_current_value - total_invested
        return_rate = (total_return / total_invested * 100) if total_invested > 0 else 0

        return {
            "total_invested": total_invested,
            "current_value": total_current_value,
            "total_return": total_return,
            "return_rate": return_rate
        }

    except Exception as e:
        print(f"Error calculating portfolio performance: {e}")
        return {"error": str(e)}


def get_portfolio_allocation(query: dict) -> Dict[str, Any]:
    portfolio_manager = PortfolioManager()
    holdings = portfolio_manager.get_holdings()

    if not holdings:
        return {"allocation": {}, "diversification_score": 0}

    try:
        cache = _cache()
        from infrastructure.api_clients.vn_stock_client import VNStockClient
        allocation = {}
        total_value = 0
        today_str = datetime.now().strftime("%Y-%m-%d")

        for ticker, quantity in holdings.items():
            if quantity > 0:
                try:
                    sector_cache_key = make_cache_key("portfolio_sector", ticker)
                    cached_sector = cache.get(sector_cache_key) if cache else None
                    if cached_sector is not None:
                        sector = cached_sector
                    else:
                        client = VNStockClient(ticker=ticker)
                        company_info = client.company.overview()
                        sector = "Unknown"
                        if company_info is not None and not company_info.empty:
                            sector = company_info.get("sector", "Unknown")
                        if cache:
                            cache.set(sector_cache_key, sector, ttl_hours=_SECTOR_TTL_HOURS)

                    price_cache_key = make_cache_key("portfolio_allocation_price", ticker, today_str, today_str, interval="1d")
                    cached_price = cache.get(price_cache_key) if cache else None
                    if cached_price is not None:
                        price = cached_price
                    else:
                        client = VNStockClient(ticker=ticker)
                        current_price = client.fetch_trading_data(
                            start=today_str,
                            end=today_str,
                            interval="1d"
                        )
                        if current_price is None or current_price.empty:
                            continue
                        price = float(current_price["close"].iloc[-1])
                        if cache:
                            cache.set(price_cache_key, price, ttl_hours=_PORTFOLIO_TTL_HOURS)

                    value = price * quantity
                    total_value += value

                    if sector not in allocation:
                        allocation[sector] = 0
                    allocation[sector] += value

                except Exception as e:
                    print(f"Error getting allocation for {ticker}: {e}")

        if total_value > 0:
            for sector in allocation:
                allocation[sector] = {
                    "value": allocation[sector],
                    "percentage": (allocation[sector] / total_value) * 100
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
            "total_value": total_value
        }

    except Exception as e:
        print(f"Error calculating portfolio allocation: {e}")
        return {"error": str(e)}


def handle_portfolio_query(parsed: Dict[str, Any]):
    requested_field = parsed.get("requested_field")
    portfolio_data = parsed.get("portfolio")

    try:
        if portfolio_data:
            portfolio_manager = PortfolioManager()
            current_holdings = portfolio_manager.get_holdings()

            for ticker, quantity in portfolio_data.items():
                if ticker not in current_holdings:
                    current_holdings[ticker] = 0
                current_holdings[ticker] += quantity

            portfolio_manager.portfolio["holdings"] = current_holdings

        if requested_field == "portfolio_value":
            return get_portfolio_value(parsed)
        elif requested_field == "portfolio_performance":
            return get_portfolio_performance(parsed)
        elif requested_field == "portfolio_allocation":
            return get_portfolio_allocation(parsed)
        else:
            result = {}

            portfolio_value = get_portfolio_value(parsed)
            if portfolio_value:
                result["portfolio_value"] = portfolio_value

            portfolio_performance = get_portfolio_performance(parsed)
            if portfolio_performance:
                result["portfolio_performance"] = portfolio_performance

            portfolio_allocation = get_portfolio_allocation(parsed)
            if portfolio_allocation:
                result["portfolio_allocation"] = portfolio_allocation

            return result if result else {"error": "No portfolio data found"}

    except Exception as e:
        return {"error": str(e)}