"""
Company Service

This module contains the service for handling company-related queries.
It provides functionality to fetch and process company information.
"""

from typing import Dict, Any, List
from infrastructure.api_clients.vn_stock_client import VNStockClient


def handle_company_query(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle company_query: shareholders, executives, subsidiaries
    
    Args:
        parsed: Parsed query dictionary
        
    Returns:
        Dictionary containing company information
    """
    tickers = parsed.get("tickers") or []
    if not tickers:
        return {"error": "Missing ticker"}

    requested_field = parsed.get("requested_field", "shareholders")
    
    try:
        results = {}
        
        for ticker in tickers:
            try:
                client = VNStockClient(ticker=ticker)
                
                if requested_field == "shareholders":
                    shareholders_data = get_shareholders(client)
                    results[ticker] = shareholders_data
                
                elif requested_field == "executives":
                    executives_data = get_executives(client)
                    results[ticker] = executives_data
                
                elif requested_field == "subsidiaries":
                    subsidiaries_data = get_subsidiaries(client)
                    results[ticker] = subsidiaries_data
                
                else:
                    # Default to shareholders
                    shareholders_data = get_shareholders(client)
                    results[ticker] = shareholders_data
            
            except Exception as e:
                results[ticker] = {"error": str(e)}
        
        return results if results else {"error": "No valid data found"}
    
    except Exception as e:
        return {"error": str(e)}


def get_shareholders(client: VNStockClient) -> Dict[str, Any]:
    """
    Get shareholders information for a company.
    
    Args:
        client: VNStockClient instance
        
    Returns:
        Dictionary containing shareholders information
    """
    try:
        # Get company overview which includes major shareholders
        company_data = client.company.overview()
        
        if company_data is None or company_data.empty:
            return {"error": "No company data available"}
        
        # Extract shareholders information
        shareholders = []
        
        # Look for shareholder-related columns in the company data
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
        
        # If no specific shareholder data found, return basic company info
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
    """
    Get executives information for a company.
    
    Args:
        client: VNStockClient instance
        
    Returns:
        Dictionary containing executives information
    """
    try:
        # Get company overview which includes executives information
        company_data = client.company.overview()
        
        if company_data is None or company_data.empty:
            return {"error": "No company data available"}
        
        # Extract executives information
        executives = []
        
        # Look for executive-related columns in the company data
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
        
        # If no specific executive data found, return basic company info
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
    """
    Get subsidiaries information for a company.
    
    Args:
        client: VNStockClient instance
        
    Returns:
        Dictionary containing subsidiaries information
    """
    try:
        # Get company overview which includes subsidiaries information
        company_data = client.company.overview()
        
        if company_data is None or company_data.empty:
            return {"error": "No company data available"}
        
        # Extract subsidiaries information
        subsidiaries = []
        
        # Look for subsidiary-related columns in the company data
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
        
        # If no specific subsidiary data found, return basic company info
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
    """
    Get comprehensive company overview.
    
    Args:
        client: VNStockClient instance
        
    Returns:
        Dictionary containing comprehensive company information
    """
    try:
        company_data = client.company.overview()
        
        if company_data is None or company_data.empty:
            return {"error": "No company data available"}
        
        # Extract all available information
        overview = {}
        
        # Basic company information
        basic_fields = [
            'company_name', 'company_code', 'industry', 'sector',
            'website', 'address', 'phone', 'email', 'founded_date'
        ]
        
        for field in basic_fields:
            if field in company_data.columns:
                overview[field] = company_data[field].iloc[0]
        
        # Financial information
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
        
        # Business information
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
        
        return overview if overview else {"error": "No detailed information available"}
    
    except Exception as e:
        return {"error": str(e)}


def get_company_financials(client: VNStockClient) -> Dict[str, Any]:
    """
    Get company financial statements.
    
    Args:
        client: VNStockClient instance
        
    Returns:
        Dictionary containing financial statements
    """
    try:
        # Get financial statements
        financial_data = client.company.financial_statement()
        
        if financial_data is None or financial_data.empty:
            return {"error": "No financial data available"}
        
        # Process financial data
        financials = {}
        
        # Balance Sheet
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
        
        # Income Statement
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
        
        # Cash Flow Statement
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
        
        return financials if financials else {"error": "No financial statements available"}
    
    except Exception as e:
        return {"error": str(e)}