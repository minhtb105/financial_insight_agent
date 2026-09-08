from collections.abc import Callable
from typing import Any

import logging
from shared.constants import COMPANY_TTL_HOURS
from shared.ports.cache_port import CachePort
from shared.ports.company_port import CompanyPort
from shared.base_service import BaseService


class CompanyService(BaseService):
    def __init__(self, cache: CachePort, company_port: CompanyPort) -> None:
        super().__init__("company_service", cache)
        self._company = company_port

    def handle_query(self, tickers: list[str], field: str = "shareholders") -> dict[str, Any]:
        err = self._require_tickers(tickers)
        if err:
            return err
        return self.for_each_ticker(tickers, lambda t: self._fetch_single(t, field))

    def _fetch_single(self, ticker: str, field: str) -> dict[str, Any]:
        getter = _FIELD_GETTERS.get(field, _FIELD_GETTERS["shareholders"])
        return self._cached_fetch("company", ticker, lambda: getter(self._company, ticker), ttl_hours=COMPANY_TTL_HOURS, requested_field=field)


_COMPANY_FIELD_MAP = {
    "shareholders": ["major_shareholders", "top_shareholders", "shareholder_list", "ownership_structure", "shareholder_info"],
    "executives": ["executives", "management_team", "board_of_directors", "leadership", "key_personnel"],
    "subsidiaries": ["subsidiaries", "affiliated_companies", "group_companies", "related_entities", "business_units"],
}


def _get_company_field(port: CompanyPort, ticker: str, field: str, display_name: str) -> dict[str, Any]:
    try:
        company_data = port.get_overview(ticker)
        if company_data is None or getattr(company_data, "empty", False):
            return {"error": "No company data available"}
        result_items = []
        for col in _COMPANY_FIELD_MAP.get(field, []):
            if col in getattr(company_data, "columns", []):
                data = company_data[col].iloc[0] if hasattr(company_data, "iloc") else company_data.get(col)
                if data is not None and str(data) != "nan":
                    result_items.append({"type": col, "data": data})
        if not result_items:
            basic_info = {}
            for col in ["company_name", "company_code", "industry", "sector"]:
                if col in getattr(company_data, "columns", []):
                    basic_info[col] = company_data[col].iloc[0] if hasattr(company_data, "iloc") else company_data.get(col)
            return {"company_info": basic_info, "note": f"Detailed {display_name} information not available"}
        return {display_name: result_items, f"total_{display_name}": len(result_items)}
    except Exception as e:
        return {"error": str(e)}


_FIELD_GETTERS: dict[str, Callable[[CompanyPort, str], dict[str, Any]]] = {
    "executives": lambda p, t: _get_company_field(p, t, "executives", "executives"),
    "subsidiaries": lambda p, t: _get_company_field(p, t, "subsidiaries", "subsidiaries"),
    "shareholders": lambda p, t: _get_company_field(p, t, "shareholders", "shareholders"),
}

# Alias for backward compat with tests
_get_company_field_with_ticker = _get_company_field


def handle_company_query(tickers: list[str], field: str = "shareholders") -> dict[str, Any]:
    from shared.service_registry import get_service
    svc = get_service("company")
    if svc is None:
        raise RuntimeError("Service 'company' not initialized — call init_deps()")
    return svc.handle_query(tickers=tickers, field=field)
