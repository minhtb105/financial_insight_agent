from collections.abc import Callable
from typing import Any

from shared.constants import COMPANY_TTL_HOURS
from infrastructure.api_clients.vn_stock_client import VNStockClient
from shared.base_service import BaseService


class CompanyService(BaseService):
    def __init__(self) -> None:
        """Khởi tạo CompanyService."""
        super().__init__("company_service")

    def handle_query(
        self,
        tickers: list[str],
        field: str = "shareholders",
    ) -> dict[str, Any]:
        """Truy vấn thông tin công ty cho danh sách mã chứng khoán.

        Args:
            tickers: Danh sách mã chứng khoán.
            field: Loại thông tin (shareholders, executives, subsidiaries).

        Returns:
            Dict chứa thông tin công ty cho từng mã.
        """
        err = self._require_tickers(tickers)
        if err:
            return err

        return self.for_each_ticker(tickers, lambda t: self._fetch_single(t, field))

    def _fetch_single(self, ticker: str, field: str) -> dict[str, Any]:
        client = VNStockClient(ticker=ticker)
        getter = _FIELD_GETTERS.get(field, _FIELD_GETTERS["shareholders"])
        return self._cached_fetch("company", ticker, lambda: getter(client), ttl_hours=COMPANY_TTL_HOURS, requested_field=field)


_company_service = CompanyService()


def handle_company_query(
    tickers: list[str],
    field: str = "shareholders",
) -> dict[str, Any]:
    return _company_service.handle_query(tickers=tickers, field=field)


_COMPANY_FIELD_MAP = {
    "shareholders": [
        "major_shareholders",
        "top_shareholders",
        "shareholder_list",
        "ownership_structure",
        "shareholder_info",
    ],
    "executives": [
        "executives",
        "management_team",
        "board_of_directors",
        "leadership",
        "key_personnel",
    ],
    "subsidiaries": [
        "subsidiaries",
        "affiliated_companies",
        "group_companies",
        "related_entities",
        "business_units",
    ],
}


def _get_company_field(client: VNStockClient, field: str, display_name: str) -> dict[str, Any]:
    try:
        company_data = client.company.overview()
        if company_data is None or company_data.empty:
            return {"error": "No company data available"}

        result_items = []
        for col in _COMPANY_FIELD_MAP.get(field, []):
            if col in company_data.columns:
                data = company_data[col].iloc[0]
                if data:
                    result_items.append({"type": col, "data": data})

        if not result_items:
            basic_info = {}
            for col in ["company_name", "company_code", "industry", "sector"]:
                if col in company_data.columns:
                    basic_info[col] = company_data[col].iloc[0]
            return {
                "company_info": basic_info,
                "note": f"Detailed {display_name} information not available in current data source",
            }

        return {display_name: result_items, f"total_{display_name}": len(result_items)}
    except Exception as e:
        return {"error": str(e)}


_FIELD_GETTERS: dict[str, Callable[[VNStockClient], dict[str, Any]]] = {
    "executives": lambda c: _get_company_field(c, "executives", "executives"),
    "subsidiaries": lambda c: _get_company_field(c, "subsidiaries", "subsidiaries"),
    "shareholders": lambda c: _get_company_field(c, "shareholders", "shareholders"),
}
