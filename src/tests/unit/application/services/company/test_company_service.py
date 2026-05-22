"""Unit tests for company_service — CompanyService and helpers."""

from unittest.mock import patch, MagicMock
import pandas as pd

# -- module-level handle_company_query ------------------------------------


def test_company_empty_tickers_returns_error():
    from application.services.company.company_service import handle_company_query

    result = handle_company_query(tickers=[])
    assert "error" in result


@patch("shared.base_service.get_cache_manager")
@patch("application.services.company.company_service.VNStockClient")
def test_company_valid_ticker(mock_client, mock_cache):
    mock_cache.return_value = None
    mock_instance = MagicMock()
    mock_instance.company.overview.return_value = pd.DataFrame(
        {
            "major_shareholders": ["State Bank"],
            "company_name": ["VCB"],
        }
    )
    mock_client.return_value = mock_instance

    from application.services.company.company_service import handle_company_query

    result = handle_company_query(tickers=["VCB"], field="shareholders")
    assert "error" not in result, f"Unexpected error: {result}"
    assert "VCB" in result
    assert result["VCB"]["shareholders"][0]["data"] == "State Bank"


# -- CompanyService.handle_query ------------------------------------------


def test_service_empty_tickers():
    from application.services.company.company_service import CompanyService

    svc = CompanyService()
    result = svc.handle_query(tickers=[])
    assert "error" in result


@patch("shared.base_service.get_cache_manager")
@patch("application.services.company.company_service.VNStockClient")
def test_service_cache_hit(mock_client, mock_cache):
    mock_cache.return_value = MagicMock()
    mock_cache.return_value.get.return_value = {"cached": "data"}

    from application.services.company.company_service import handle_company_query

    result = handle_company_query(tickers=["VCB"], field="shareholders")
    assert result == {"VCB": {"cached": "data"}}


# -- _get_company_field (pure) --------------------------------------------


def test_get_company_field_matching_columns():
    from application.services.company.company_service import _get_company_field

    client = MagicMock()
    client.company.overview.return_value = pd.DataFrame(
        {
            "major_shareholders": ["State Bank"],
            "company_name": ["VCB"],
        }
    )
    result = _get_company_field(client, "shareholders", "shareholders")
    assert result["shareholders"][0]["type"] == "major_shareholders"
    assert result["shareholders"][0]["data"] == "State Bank"
    assert result["total_shareholders"] == 1


def test_get_company_field_no_matching_columns():
    from application.services.company.company_service import _get_company_field

    client = MagicMock()
    client.company.overview.return_value = pd.DataFrame(
        {
            "company_name": ["VCB"],
            "company_code": ["VCB"],
        }
    )
    result = _get_company_field(client, "shareholders", "shareholders")
    assert result["company_info"]["company_name"] == "VCB"
    assert "shareholders" in result["note"]


def test_get_company_field_empty_data():
    from application.services.company.company_service import _get_company_field

    client = MagicMock()
    client.company.overview.return_value = pd.DataFrame()
    result = _get_company_field(client, "shareholders", "shareholders")
    assert "error" in result


def test_get_company_field_none_data():
    from application.services.company.company_service import _get_company_field

    client = MagicMock()
    client.company.overview.return_value = None
    result = _get_company_field(client, "shareholders", "shareholders")
    assert "error" in result


# -- _FIELD_GETTERS registry -------------------------------------------------


def test_field_getters_shareholders():
    from application.services.company.company_service import _FIELD_GETTERS

    client = MagicMock()
    client.company.overview.return_value = pd.DataFrame(
        {
            "major_shareholders": ["State"],
            "company_name": ["VCB"],
        }
    )
    result = _FIELD_GETTERS["shareholders"](client)
    assert result["shareholders"][0]["data"] == "State"
    assert result["total_shareholders"] == 1


def test_field_getters_executives():
    from application.services.company.company_service import _FIELD_GETTERS

    client = MagicMock()
    client.company.overview.return_value = pd.DataFrame(
        {
            "executives": [{"name": "CEO"}],
            "company_name": ["VCB"],
        }
    )
    result = _FIELD_GETTERS["executives"](client)
    assert result["executives"][0]["data"] == {"name": "CEO"}
    assert result["total_executives"] == 1


def test_field_getters_subsidiaries():
    from application.services.company.company_service import _FIELD_GETTERS

    client = MagicMock()
    client.company.overview.return_value = pd.DataFrame(
        {
            "subsidiaries": [{"name": "Sub"}],
            "company_name": ["VCB"],
        }
    )
    result = _FIELD_GETTERS["subsidiaries"](client)
    assert result["subsidiaries"][0]["data"] == {"name": "Sub"}
    assert result["total_subsidiaries"] == 1
