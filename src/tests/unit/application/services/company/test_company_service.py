"""Unit tests for company_service — CompanyService and helpers (strict DI)."""

from unittest.mock import MagicMock
import pandas as pd
from shared.service_registry import set_service, clear
from shared.ports.cache_port import CachePort
from shared.ports.company_port import CompanyPort

class FakeCache(CachePort):
    def get(self, key): return None
    def set(self, key, value, ttl_hours=1.0): pass
    def delete(self, key): pass

class FakeCompanyPort(CompanyPort):
    def __init__(self, df):
        self._df = df
    def get_overview(self, ticker): return self._df
    def list_companies(self): return self._df

# -- module-level handle_company_query ------------------------------------

def test_company_empty_tickers_returns_error():
    from application.services.company.company_service import CompanyService
    svc = CompanyService(cache=FakeCache(), company_port=FakeCompanyPort(pd.DataFrame()))
    set_service("company", svc)
    from application.services.company.company_service import handle_company_query
    result = handle_company_query(tickers=[])
    assert "error" in result
    clear()

def test_company_valid_ticker():
    df = pd.DataFrame({"major_shareholders": ["State Bank"], "company_name": ["VCB"]})
    from application.services.company.company_service import CompanyService
    svc = CompanyService(cache=FakeCache(), company_port=FakeCompanyPort(df))
    set_service("company", svc)
    from application.services.company.company_service import handle_company_query
    result = handle_company_query(tickers=["VCB"], field="shareholders")
    assert "error" not in result, f"Unexpected error: {result}"
    assert "VCB" in result
    assert result["VCB"]["shareholders"][0]["data"] == "State Bank"
    clear()

# -- CompanyService.handle_query ------------------------------------------

def test_service_empty_tickers():
    from application.services.company.company_service import CompanyService
    svc = CompanyService(cache=FakeCache(), company_port=FakeCompanyPort(pd.DataFrame()))
    result = svc.handle_query(tickers=[])
    assert "error" in result

def test_service_cache_hit():
    class CacheWithHit(FakeCache):
        def get(self, key): return {"cached": "data"}
    from application.services.company.company_service import CompanyService
    df = pd.DataFrame({"major_shareholders": ["State Bank"], "company_name": ["VCB"]})
    svc = CompanyService(cache=CacheWithHit(), company_port=FakeCompanyPort(df))
    set_service("company", svc)
    from application.services.company.company_service import handle_company_query
    result = handle_company_query(tickers=["VCB"], field="shareholders")
    assert result == {"VCB": {"cached": "data"}}
    clear()

# -- _get_company_field (pure) --------------------------------------------

def test_get_company_field_matching_columns():
    from application.services.company.company_service import _get_company_field_with_ticker
    df = pd.DataFrame({"major_shareholders": ["State Bank"], "company_name": ["VCB"]})
    port = FakeCompanyPort(df)
    result = _get_company_field_with_ticker(port, "VCB", "shareholders", "shareholders")
    assert result["shareholders"][0]["type"] == "major_shareholders"
    assert result["shareholders"][0]["data"] == "State Bank"
    assert result["total_shareholders"] == 1

def test_get_company_field_no_matching_columns():
    from application.services.company.company_service import _get_company_field_with_ticker
    df = pd.DataFrame({"company_name": ["VCB"], "company_code": ["VCB"]})
    port = FakeCompanyPort(df)
    result = _get_company_field_with_ticker(port, "VCB", "shareholders", "shareholders")
    assert result["company_info"]["company_name"] == "VCB"
    assert "shareholders" in result["note"]

def test_get_company_field_empty_data():
    from application.services.company.company_service import _get_company_field_with_ticker
    port = FakeCompanyPort(pd.DataFrame())
    result = _get_company_field_with_ticker(port, "VCB", "shareholders", "shareholders")
    assert "error" in result

def test_get_company_field_none_data():
    from application.services.company.company_service import _get_company_field_with_ticker
    port = FakeCompanyPort(None)
    result = _get_company_field_with_ticker(port, "VCB", "shareholders", "shareholders")
    assert "error" in result

# -- _FIELD_GETTERS registry -------------------------------------------------

def test_field_getters_shareholders():
    from application.services.company.company_service import _FIELD_GETTERS
    df = pd.DataFrame({"major_shareholders": ["State"], "company_name": ["VCB"]})
    port = FakeCompanyPort(df)
    result = _FIELD_GETTERS["shareholders"](port, "VCB")
    assert result["shareholders"][0]["data"] == "State"
    assert result["total_shareholders"] == 1

def test_field_getters_executives():
    from application.services.company.company_service import _FIELD_GETTERS
    df = pd.DataFrame({"executives": [{"name": "CEO"}], "company_name": ["VCB"]})
    port = FakeCompanyPort(df)
    result = _FIELD_GETTERS["executives"](port, "VCB")
    assert result["executives"][0]["data"] == {"name": "CEO"}
    assert result["total_executives"] == 1

def test_field_getters_subsidiaries():
    from application.services.company.company_service import _FIELD_GETTERS
    df = pd.DataFrame({"subsidiaries": [{"name": "Sub"}], "company_name": ["VCB"]})
    port = FakeCompanyPort(df)
    result = _FIELD_GETTERS["subsidiaries"](port, "VCB")
    assert result["subsidiaries"][0]["data"] == {"name": "Sub"}
    assert result["total_subsidiaries"] == 1
