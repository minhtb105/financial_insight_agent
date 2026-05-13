from typing import Dict, Any, Optional
from infrastructure.api_clients.vn_stock_client import VNStockClient
from infrastructure.cache import get_cache_manager
from infrastructure.cache.cache_keys import make_cache_key

_COMPANY_TTL_HOURS = 4


def _cache() -> Optional[Any]:
    return get_cache_manager()


def handle_company_query(parsed: Dict[str, Any]) -> Dict[str, Any]:
    tickers = parsed.get("tickers") or []
    if not tickers:
        return {"error": "Missing ticker"}

    requested_field = parsed.get("requested_field", "shareholders")

    try:
        cache = _cache()
        results = {}

        for ticker in tickers:
            try:
                cache_key = make_cache_key("company", ticker, requested_field=requested_field)
                cached = cache.get(cache_key) if cache else None
                if cached is not None:
                    results[ticker] = cached
                    continue

                client = VNStockClient(ticker=ticker)

                if requested_field == "shareholders":
                    data = get_shareholders(client)
                elif requested_field == "executives":
                    data = get_executives(client)
                elif requested_field == "subsidiaries":
                    data = get_subsidiaries(client)
                else:
                    data = get_shareholders(client)

                results[ticker] = data
                if cache and "error" not in data:
                    cache.set(cache_key, data, ttl_hours=_COMPANY_TTL_HOURS)

            except Exception as e:
                results[ticker] = {"error": str(e)}

        return results if results else {"error": "No valid data found"}

    except Exception as e:
        return {"error": str(e)}


def get_shareholders(client: VNStockClient) -> Dict[str, Any]:
    try:
        company_data = client.company.overview()

        if company_data is None or company_data.empty:
            return {"error": "No company data available"}

        shareholders = []

        shareholder_columns = [
            'major_shareholders', 'top_shareholders', 'shareholder_list',
            'ownership_structure', 'shareholder_info'
        ]

        for col in shareholder_columns:
            if col in company_data.columns:
                shareholders_data = company_data[col].iloc[0]
                if shareholders_data:
                    shareholders.append({
                        "type": col,
                        "data": shareholders_data
                    })

        if not shareholders:
            basic_info = {}
            for col in company_data.columns:
                if col in ['company_name', 'company_code', 'industry', 'sector']:
                    basic_info[col] = company_data[col].iloc[0]

            return {
                "company_info": basic_info,
                "note": "Detailed shareholder information not available in current data source"
            }

        return {
            "shareholders": shareholders,
            "total_shareholders": len(shareholders)
        }

    except Exception as e:
        return {"error": str(e)}


def get_executives(client: VNStockClient) -> Dict[str, Any]:
    try:
        company_data = client.company.overview()

        if company_data is None or company_data.empty:
            return {"error": "No company data available"}

        executives = []

        executive_columns = [
            'executives', 'management_team', 'board_of_directors',
            'leadership', 'key_personnel'
        ]

        for col in executive_columns:
            if col in company_data.columns:
                executives_data = company_data[col].iloc[0]
                if executives_data:
                    executives.append({
                        "type": col,
                        "data": executives_data
                    })

        if not executives:
            basic_info = {}
            for col in company_data.columns:
                if col in ['company_name', 'company_code', 'industry', 'sector']:
                    basic_info[col] = company_data[col].iloc[0]

            return {
                "company_info": basic_info,
                "note": "Detailed executives information not available in current data source"
            }

        return {
            "executives": executives,
            "total_executives": len(executives)
        }

    except Exception as e:
        return {"error": str(e)}


def get_subsidiaries(client: VNStockClient) -> Dict[str, Any]:
    try:
        company_data = client.company.overview()

        if company_data is None or company_data.empty:
            return {"error": "No company data available"}

        subsidiaries = []

        subsidiary_columns = [
            'subsidiaries', 'affiliated_companies', 'group_companies',
            'related_entities', 'business_units'
        ]

        for col in subsidiary_columns:
            if col in company_data.columns:
                subsidiaries_data = company_data[col].iloc[0]
                if subsidiaries_data:
                    subsidiaries.append({
                        "type": col,
                        "data": subsidiaries_data
                    })

        if not subsidiaries:
            basic_info = {}
            for col in company_data.columns:
                if col in ['company_name', 'company_code', 'industry', 'sector']:
                    basic_info[col] = company_data[col].iloc[0]

            return {
                "company_info": basic_info,
                "note": "Detailed subsidiaries information not available in current data source"
            }

        return {
            "subsidiaries": subsidiaries,
            "total_subsidiaries": len(subsidiaries)
        }

    except Exception as e:
        return {"error": str(e)}


def get_company_overview(client: VNStockClient) -> Dict[str, Any]:
    try:
        cache = _cache()
        cache_key = make_cache_key("company_overview", client.ticker)
        cached = cache.get(cache_key) if cache else None
        if cached is not None:
            return cached

        company_data = client.company.overview()

        if company_data is None or company_data.empty:
            return {"error": "No company data available"}

        overview = {}

        basic_fields = [
            'company_name', 'company_code', 'industry', 'sector',
            'website', 'address', 'phone', 'email', 'founded_date'
        ]

        for field in basic_fields:
            if field in company_data.columns:
                overview[field] = company_data[field].iloc[0]

        financial_fields = [
            'market_cap', 'pe_ratio', 'pb_ratio', 'roe', 'eps',
            'dividend_yield', 'revenue', 'net_profit'
        ]

        financial_info = {}
        for field in financial_fields:
            if field in company_data.columns:
                financial_info[field] = company_data[field].iloc[0]

        if financial_info:
            overview['financial_info'] = financial_info

        business_fields = [
            'business_description', 'main_products', 'market_position',
            'competitive_advantages', 'growth_strategy'
        ]

        business_info = {}
        for field in business_fields:
            if field in company_data.columns:
                business_info[field] = company_data[field].iloc[0]

        if business_info:
            overview['business_info'] = business_info

        result = overview if overview else {"error": "No detailed information available"}
        if cache and "error" not in result:
            cache.set(cache_key, result, ttl_hours=_COMPANY_TTL_HOURS)
        return result

    except Exception as e:
        return {"error": str(e)}


def get_company_financials(client: VNStockClient) -> Dict[str, Any]:
    try:
        cache = _cache()
        cache_key = make_cache_key("company_financials", client.ticker)
        cached = cache.get(cache_key) if cache else None
        if cached is not None:
            return cached

        financial_data = client.company.financial_statement()

        if financial_data is None or financial_data.empty:
            return {"error": "No financial data available"}

        financials = {}

        balance_sheet_fields = [
            'total_assets', 'total_liabilities', 'equity',
            'current_assets', 'current_liabilities'
        ]

        balance_sheet = {}
        for field in balance_sheet_fields:
            if field in financial_data.columns:
                balance_sheet[field] = financial_data[field].iloc[0]

        if balance_sheet:
            financials['balance_sheet'] = balance_sheet

        income_statement_fields = [
            'revenue', 'cost_of_goods_sold', 'gross_profit',
            'operating_expense', 'net_profit'
        ]

        income_statement = {}
        for field in income_statement_fields:
            if field in financial_data.columns:
                income_statement[field] = financial_data[field].iloc[0]

        if income_statement:
            financials['income_statement'] = income_statement

        cash_flow_fields = [
            'operating_cash_flow', 'investing_cash_flow',
            'financing_cash_flow', 'net_cash_flow'
        ]

        cash_flow = {}
        for field in cash_flow_fields:
            if field in financial_data.columns:
                cash_flow[field] = financial_data[field].iloc[0]

        if cash_flow:
            financials['cash_flow'] = cash_flow

        result = financials if financials else {"error": "No financial statements available"}
        if cache and "error" not in result:
            cache.set(cache_key, result, ttl_hours=_COMPANY_TTL_HOURS)
        return result

    except Exception as e:
        return {"error": str(e)}