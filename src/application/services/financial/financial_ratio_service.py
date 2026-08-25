from copy import deepcopy
from typing import Any
from shared.constants import RATIO_TTL_HOURS
from shared.utils.time_processor import TimeProcessor
from infrastructure.api_clients.vn_stock_client import VNStockClient
from infrastructure.cache import get_cache_manager
from infrastructure.cache.cache_keys import make_cache_key
from shared.base_service import BaseService


def _ensure_float(v, default: float = 0.0) -> float:
    if v is None:
        return default
    try:
        f = float(v)
        return f if f == f else default
    except (ValueError, TypeError):
        return default


class FinancialRatioService(BaseService):
    def __init__(self) -> None:
        """Khởi tạo FinancialRatioService."""
        super().__init__("financial_ratio_service")

    def handle_query(
        self,
        tickers: list[str],
        field: str = "pe",
    ) -> dict[str, Any]:
        """Truy vấn chỉ số tài chính cho danh sách mã chứng khoán.

        Args:
            tickers: Danh sách mã chứng khoán.
            field: Loại chỉ số cần lấy.

        Returns:
            Dict chứa chỉ số tài chính cho từng mã.
        """
        err = self._require_tickers(tickers)
        if err:
            return err

        results = {}
        for ticker in tickers:
            try:
                client = VNStockClient(ticker=ticker)
                _ = client.ticker
                results[ticker] = get_financial_ratios(client, field, {"requested_field": field})
            except Exception as e:
                self.logger.error(f"Failed to init VNStockClient for {ticker}: {e}")
                results[ticker] = {"error": str(e)}
        return results


_financial_ratio_service = FinancialRatioService()


def handle_financial_ratio_query(
    tickers: list[str],
    field: str = "pe",
) -> dict[str, Any]:
    return _financial_ratio_service.handle_query(tickers=tickers, field=field)


def get_pe_interpretation(pe_ratio: float) -> str:
    if pe_ratio < 10:
        return "Low P/E - Potentially undervalued or company has issues"
    elif pe_ratio < 20:
        return "Moderate P/E - Reasonable valuation"
    elif pe_ratio < 30:
        return "High P/E - Potentially overvalued or high growth expectations"
    else:
        return "Very high P/E - Significant overvaluation risk"


def get_pb_interpretation(pb_ratio: float) -> str:
    if pb_ratio < 1:
        return "Low P/B - Potentially undervalued"
    elif pb_ratio < 3:
        return "Moderate P/B - Reasonable valuation"
    else:
        return "High P/B - Potentially overvalued"


def get_roe_interpretation(roe: float) -> str:
    if roe < 5:
        return "Low ROE - Poor profitability"
    elif roe < 15:
        return "Moderate ROE - Acceptable profitability"
    elif roe < 25:
        return "Good ROE - Strong profitability"
    else:
        return "Excellent ROE - Exceptional profitability"


def get_eps_interpretation(eps: float) -> str:
    if eps < 0:
        return "Negative EPS - Company is losing money"
    elif eps < 1:
        return "Low EPS - Modest profitability"
    elif eps < 5:
        return "Moderate EPS - Good profitability"
    else:
        return "High EPS - Strong profitability"


def get_current_ratio_interpretation(current_ratio: float) -> str:
    if current_ratio < 1:
        return "Poor liquidity - Potential solvency issues"
    elif current_ratio < 1.5:
        return "Adequate liquidity - Acceptable short-term health"
    elif current_ratio < 3:
        return "Good liquidity - Strong short-term financial health"
    else:
        return "Very high liquidity - May indicate inefficient asset use"


def get_debt_to_equity_interpretation(debt_to_equity: float) -> str:
    if debt_to_equity < 0.5:
        return "Low leverage - Conservative capital structure"
    elif debt_to_equity < 1.5:
        return "Moderate leverage - Balanced capital structure"
    elif debt_to_equity < 2.5:
        return "High leverage - Aggressive capital structure"
    else:
        return "Very high leverage - High financial risk"


def get_profit_margin_interpretation(profit_margin: float) -> str:
    if profit_margin < 0:
        return "Negative margin - Company is losing money"
    elif profit_margin < 5:
        return "Low margin - Thin profitability"
    elif profit_margin < 15:
        return "Moderate margin - Reasonable profitability"
    elif profit_margin < 25:
        return "Good margin - Strong profitability"
    else:
        return "Excellent margin - Exceptional profitability"


def get_quick_ratio_interpretation(quick_ratio: float) -> str:
    if quick_ratio < 1:
        return "Poor liquidity - May struggle with immediate obligations"
    elif quick_ratio < 1.5:
        return "Adequate liquidity - Can meet short-term obligations"
    else:
        return "Strong liquidity - Excellent short-term financial health"


def get_asset_turnover_interpretation(asset_turnover: float) -> str:
    if asset_turnover < 0.5:
        return "Low efficiency - Poor asset utilization"
    elif asset_turnover < 1.5:
        return "Moderate efficiency - Acceptable asset utilization"
    elif asset_turnover < 3:
        return "Good efficiency - Strong asset utilization"
    else:
        return "Excellent efficiency - Outstanding asset utilization"


def get_dividend_yield_interpretation(dividend_yield: float) -> str:
    if dividend_yield < 1:
        return "Low yield - Minimal income generation"
    elif dividend_yield < 3:
        return "Moderate yield - Reasonable income generation"
    elif dividend_yield < 5:
        return "Good yield - Strong income generation"
    else:
        return "High yield - Very strong income generation (may be unsustainable)"


_RATIO_ENTRIES: dict[str, dict[str, Any]] = {
    "pe": {
        "key": "pe_ratio",
        "extract": lambda row, market: {
            "eps": _ensure_float(row.get("eps")),
            "current_price": market.get("current_price", 0),
        },
        "guard": lambda vals: vals["eps"] != 0 and vals["current_price"],
        "compute": lambda vals: vals["current_price"] / vals["eps"],
        "interpret": get_pe_interpretation,
    },
    "pb": {
        "key": "pb_ratio",
        "extract": lambda row, market: {
            "book_value_per_share": _ensure_float(row.get("book_value_per_share")),
            "current_price": market.get("current_price", 0),
        },
        "guard": lambda vals: vals["book_value_per_share"] != 0 and vals["current_price"],
        "compute": lambda vals: vals["current_price"] / vals["book_value_per_share"],
        "interpret": get_pb_interpretation,
    },
    "roe": {
        "key": "roe",
        "extract": lambda row, market: {
            "net_profit": _ensure_float(row.get("net_profit")),
            "total_equity": _ensure_float(row.get("equity")),
        },
        "guard": lambda vals: vals["total_equity"] != 0,
        "compute": lambda vals: (vals["net_profit"] / vals["total_equity"]) * 100,
        "interpret": get_roe_interpretation,
    },
    "eps": {
        "key": "eps",
        "extract": lambda row, market: {
            "net_profit": _ensure_float(row.get("net_profit")),
            "shares_outstanding": _ensure_float(row.get("shares_outstanding")),
        },
        "guard": lambda vals: vals["shares_outstanding"] != 0,
        "compute": lambda vals: vals["net_profit"] / vals["shares_outstanding"],
        "interpret": get_eps_interpretation,
    },
    "current_ratio": {
        "key": "current_ratio",
        "extract": lambda row, market: {
            "current_assets": _ensure_float(row.get("current_assets")),
            "current_liabilities": _ensure_float(row.get("current_liabilities")),
        },
        "guard": lambda vals: vals["current_liabilities"] != 0,
        "compute": lambda vals: vals["current_assets"] / vals["current_liabilities"],
        "interpret": get_current_ratio_interpretation,
    },
    "debt_to_equity": {
        "key": "debt_to_equity",
        "extract": lambda row, market: {
            "total_liabilities": _ensure_float(row.get("total_liabilities")),
            "total_equity": _ensure_float(row.get("equity")),
        },
        "guard": lambda vals: vals["total_equity"] != 0,
        "compute": lambda vals: vals["total_liabilities"] / vals["total_equity"],
        "interpret": get_debt_to_equity_interpretation,
    },
    "profit_margin": {
        "key": "profit_margin",
        "extract": lambda row, market: {
            "net_profit": _ensure_float(row.get("net_profit")),
            "revenue": _ensure_float(row.get("revenue")),
        },
        "guard": lambda vals: vals["revenue"] != 0,
        "compute": lambda vals: (vals["net_profit"] / vals["revenue"]) * 100,
        "interpret": get_profit_margin_interpretation,
    },
    "quick_ratio": {
        "key": "quick_ratio",
        "extract": lambda row, market: {
            "quick_assets": _ensure_float(row.get("cash_and_equivalents")) + _ensure_float(row.get("marketable_securities")),
            "current_liabilities": _ensure_float(row.get("current_liabilities")),
        },
        "guard": lambda vals: vals["current_liabilities"] != 0,
        "compute": lambda vals: vals["quick_assets"] / vals["current_liabilities"],
        "interpret": get_quick_ratio_interpretation,
    },
    "asset_turnover": {
        "key": "asset_turnover",
        "extract": lambda row, market: {
            "revenue": _ensure_float(row.get("revenue")),
            "total_assets": _ensure_float(row.get("total_assets")),
        },
        "guard": lambda vals: vals["total_assets"] != 0,
        "compute": lambda vals: vals["revenue"] / vals["total_assets"],
        "interpret": get_asset_turnover_interpretation,
    },
    "dividend_yield": {
        "key": "dividend_yield",
        "extract": lambda row, market: {
            "dividend_per_share": _ensure_float(row.get("dividend_per_share")),
            "current_price": market.get("current_price", 0),
        },
        "guard": lambda vals: vals["current_price"] != 0,
        "compute": lambda vals: (vals["dividend_per_share"] / vals["current_price"]) * 100,
        "interpret": get_dividend_yield_interpretation,
    },
}


def get_financial_ratios(
    client: VNStockClient, ratio_type: str | None = None, parsed: dict[str, Any] | None = None
) -> dict[str, Any]:
    """Lấy các chỉ số tài chính cho một mã chứng khoán.

    Args:
        client: Đối tượng VNStockClient đã khởi tạo.
        ratio_type: Loại chỉ số cần lấy (pe, pb, roe, ...).
        parsed: Dict chứa tham số thời gian.

    Returns:
        Dict chứa các chỉ số tài chính hoặc lỗi.
    """
    try:
        ticker = client.ticker
        cache = get_cache_manager()
        rt = ratio_type or "all"
        cache_key = make_cache_key("financial_ratio", ticker, ratio_type=rt)
        cached = cache.get(cache_key) if cache else None
        if cached is not None:
            if parsed:
                result = deepcopy(cached)
                tp = TimeProcessor()
                tp_result = tp.process_time_params(parsed)
                for val in result.values():
                    if isinstance(val, dict):
                        val["time_range"] = tp_result.get("time_description", "Latest")
                return result
            return cached

        financial_data = client.company.financial_statement()

        if financial_data is None or financial_data.empty:
            return {"error": "No financial data available"}

        market_data = client.company.market_data()

        ratios = {}

        row = financial_data.iloc[0].to_dict() if not financial_data.empty else {}

        time_processor = TimeProcessor()
        time_params = (
            time_processor.process_time_params(parsed)
            if parsed
            else time_processor.get_default_time_range()
        )
        time_range = time_params.get("time_description", "Latest")

        for rt_name, cfg in _RATIO_ENTRIES.items():
            if ratio_type is None or ratio_type == rt_name:
                vals = cfg["extract"](row, market_data)
                if cfg["guard"](vals):
                    result = cfg["compute"](vals)
                    ratios[cfg["key"]] = {
                        "value": result,
                        **vals,
                        "interpretation": cfg["interpret"](result),
                        "time_range": time_range,
                    }

        result = ratios if ratios else {"error": "No ratios calculated"}
        if cache and "error" not in result:
            cache.set(cache_key, result, ttl_hours=RATIO_TTL_HOURS)
        return result

    except Exception as e:
        return {"error": str(e)}
