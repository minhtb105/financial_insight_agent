"""
Financial Ratio Service

This module contains the service for handling financial ratio queries.
It provides functionality to calculate and analyze financial ratios for companies.
"""

from typing import Dict, Any, List
from infrastructure.api_clients.vn_stock_client import VNStockClient
from ..base.time_processor import TimeProcessor


def handle_financial_ratio_query(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle financial_ratio_query: pe, pb, roe, eps, etc.
    
    Args:
        parsed: Parsed query dictionary
        
    Returns:
        Dictionary containing financial ratio data
    """
    tickers = parsed.get("tickers") or []
    if not tickers:
        return {"error": "Missing ticker"}

    requested_field = parsed.get("requested_field", "pe")
    
    try:
        results = {}
        
        for ticker in tickers:
            try:
                client = VNStockClient(ticker=ticker)
                
                # Get financial ratios
                ratios_data = get_financial_ratios(client, requested_field, parsed)
                results[ticker] = ratios_data
            
            except Exception as e:
                results[ticker] = {"error": str(e)}
        
        return results if results else {"error": "No valid data found"}
    
    except Exception as e:
        return {"error": str(e)}


def get_financial_ratios(client: VNStockClient, ratio_type: str = None, parsed: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Get financial ratios for a company.
    
    Args:
        client: VNStockClient instance
        ratio_type: Specific ratio type to retrieve
        parsed: Parsed query dictionary
        
    Returns:
        Dictionary containing financial ratios
    """
    try:
        # Get financial statements
        financial_data = client.company.financial_statement()
        
        if financial_data is None or financial_data.empty:
            return {"error": "No financial data available"}
        
        # Get market data for ratios that need market price
        market_data = client.company.market_data()
        
        ratios = {}
        
        # Extract financial data
        revenue = financial_data.get('revenue', 0)
        net_profit = financial_data.get('net_profit', 0)
        total_assets = financial_data.get('total_assets', 0)
        total_equity = financial_data.get('equity', 0)
        total_liabilities = financial_data.get('total_liabilities', 0)
        
        # Calculate ratios using TimeProcessor for time-based calculations
        time_processor = TimeProcessor()
        time_params = time_processor.process_time_params(parsed) if 'parsed' in locals() else {}
        
        if ratio_type is None or ratio_type == "pe":
            # Price to Earnings Ratio
            eps = financial_data.get('eps', 0)
            if eps != 0 and market_data.get('current_price'):
                pe_ratio = market_data['current_price'] / eps
                ratios['pe_ratio'] = {
                    "value": pe_ratio,
                    "eps": eps,
                    "current_price": market_data['current_price'],
                    "interpretation": get_pe_interpretation(pe_ratio),
                    "time_range": time_params.get("time_description", "Latest")
                }
        
        if ratio_type is None or ratio_type == "pb":
            # Price to Book Ratio
            book_value_per_share = financial_data.get('book_value_per_share', 0)
            if book_value_per_share != 0 and market_data.get('current_price'):
                pb_ratio = market_data['current_price'] / book_value_per_share
                ratios['pb_ratio'] = {
                    "value": pb_ratio,
                    "book_value_per_share": book_value_per_share,
                    "current_price": market_data['current_price'],
                    "interpretation": get_pb_interpretation(pb_ratio),
                    "time_range": time_params.get("time_description", "Latest")
                }
        
        if ratio_type is None or ratio_type == "roe":
            # Return on Equity
            if total_equity != 0:
                roe = (net_profit / total_equity) * 100
                ratios['roe'] = {
                    "value": roe,
                    "net_profit": net_profit,
                    "total_equity": total_equity,
                    "interpretation": get_roe_interpretation(roe),
                    "time_range": time_params.get("time_description", "Latest")
                }
        
        if ratio_type is None or ratio_type == "eps":
            # Earnings Per Share
            shares_outstanding = financial_data.get('shares_outstanding', 0)
            if shares_outstanding != 0:
                eps = net_profit / shares_outstanding
                ratios['eps'] = {
                    "value": eps,
                    "net_profit": net_profit,
                    "shares_outstanding": shares_outstanding,
                    "interpretation": get_eps_interpretation(eps),
                    "time_range": time_params.get("time_description", "Latest")
                }
        
        if ratio_type is None or ratio_type == "current_ratio":
            # Current Ratio
            current_assets = financial_data.get('current_assets', 0)
            current_liabilities = financial_data.get('current_liabilities', 0)
            if current_liabilities != 0:
                current_ratio = current_assets / current_liabilities
                ratios['current_ratio'] = {
                    "value": current_ratio,
                    "current_assets": current_assets,
                    "current_liabilities": current_liabilities,
                    "interpretation": get_current_ratio_interpretation(current_ratio),
                    "time_range": time_params.get("time_description", "Latest")
                }
        
        if ratio_type is None or ratio_type == "debt_to_equity":
            # Debt to Equity Ratio
            if total_equity != 0:
                debt_to_equity = total_liabilities / total_equity
                ratios['debt_to_equity'] = {
                    "value": debt_to_equity,
                    "total_liabilities": total_liabilities,
                    "total_equity": total_equity,
                    "interpretation": get_debt_to_equity_interpretation(debt_to_equity),
                    "time_range": time_params.get("time_description", "Latest")
                }
        
        if ratio_type is None or ratio_type == "profit_margin":
            # Profit Margin
            if revenue != 0:
                profit_margin = (net_profit / revenue) * 100
                ratios['profit_margin'] = {
                    "value": profit_margin,
                    "net_profit": net_profit,
                    "revenue": revenue,
                    "interpretation": get_profit_margin_interpretation(profit_margin),
                    "time_range": time_params.get("time_description", "Latest")
                }
        
        if ratio_type is None or ratio_type == "quick_ratio":
            # Quick Ratio (Acid-test Ratio)
            cash_and_equivalents = financial_data.get('cash_and_equivalents', 0)
            marketable_securities = financial_data.get('marketable_securities', 0)
            current_liabilities = financial_data.get('current_liabilities', 0)
            
            if current_liabilities != 0:
                quick_assets = cash_and_equivalents + marketable_securities
                quick_ratio = quick_assets / current_liabilities
                ratios['quick_ratio'] = {
                    "value": quick_ratio,
                    "quick_assets": quick_assets,
                    "current_liabilities": current_liabilities,
                    "interpretation": get_quick_ratio_interpretation(quick_ratio),
                    "time_range": time_params.get("time_description", "Latest")
                }
        
        if ratio_type is None or ratio_type == "asset_turnover":
            # Asset Turnover Ratio
            if total_assets != 0:
                asset_turnover = revenue / total_assets
                ratios['asset_turnover'] = {
                    "value": asset_turnover,
                    "revenue": revenue,
                    "total_assets": total_assets,
                    "interpretation": get_asset_turnover_interpretation(asset_turnover),
                    "time_range": time_params.get("time_description", "Latest")
                }
        
        if ratio_type is None or ratio_type == "dividend_yield":
            # Dividend Yield
            dividend_per_share = financial_data.get('dividend_per_share', 0)
            if market_data.get('current_price') and market_data['current_price'] != 0:
                dividend_yield = (dividend_per_share / market_data['current_price']) * 100
                ratios['dividend_yield'] = {
                    "value": dividend_yield,
                    "dividend_per_share": dividend_per_share,
                    "current_price": market_data['current_price'],
                    "interpretation": get_dividend_yield_interpretation(dividend_yield),
                    "time_range": time_params.get("time_description", "Latest")
                }
        
        return ratios if ratios else {"error": "No ratios calculated"}
    
    except Exception as e:
        return {"error": str(e)}


def get_pe_interpretation(pe_ratio: float) -> str:
    """Get interpretation for P/E ratio."""
    if pe_ratio < 10:
        return "Low P/E - Potentially undervalued or company has issues"
    elif pe_ratio < 20:
        return "Moderate P/E - Reasonable valuation"
    elif pe_ratio < 30:
        return "High P/E - Potentially overvalued or high growth expectations"
    else:
        return "Very high P/E - Significant overvaluation risk"


def get_pb_interpretation(pb_ratio: float) -> str:
    """Get interpretation for P/B ratio."""
    if pb_ratio < 1:
        return "Low P/B - Potentially undervalued"
    elif pb_ratio < 3:
        return "Moderate P/B - Reasonable valuation"
    else:
        return "High P/B - Potentially overvalued"


def get_roe_interpretation(roe: float) -> str:
    """Get interpretation for ROE."""
    if roe < 5:
        return "Low ROE - Poor profitability"
    elif roe < 15:
        return "Moderate ROE - Acceptable profitability"
    elif roe < 25:
        return "Good ROE - Strong profitability"
    else:
        return "Excellent ROE - Exceptional profitability"


def get_eps_interpretation(eps: float) -> str:
    """Get interpretation for EPS."""
    if eps < 0:
        return "Negative EPS - Company is losing money"
    elif eps < 1:
        return "Low EPS - Modest profitability"
    elif eps < 5:
        return "Moderate EPS - Good profitability"
    else:
        return "High EPS - Strong profitability"


def get_current_ratio_interpretation(current_ratio: float) -> str:
    """Get interpretation for Current Ratio."""
    if current_ratio < 1:
        return "Poor liquidity - Potential solvency issues"
    elif current_ratio < 1.5:
        return "Adequate liquidity - Acceptable short-term health"
    elif current_ratio < 3:
        return "Good liquidity - Strong short-term financial health"
    else:
        return "Very high liquidity - May indicate inefficient asset use"


def get_debt_to_equity_interpretation(debt_to_equity: float) -> str:
    """Get interpretation for Debt to Equity Ratio."""
    if debt_to_equity < 0.5:
        return "Low leverage - Conservative capital structure"
    elif debt_to_equity < 1.5:
        return "Moderate leverage - Balanced capital structure"
    elif debt_to_equity < 2.5:
        return "High leverage - Aggressive capital structure"
    else:
        return "Very high leverage - High financial risk"


def get_profit_margin_interpretation(profit_margin: float) -> str:
    """Get interpretation for Profit Margin."""
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
    """Get interpretation for Quick Ratio."""
    if quick_ratio < 1:
        return "Poor liquidity - May struggle with immediate obligations"
    elif quick_ratio < 1.5:
        return "Adequate liquidity - Can meet short-term obligations"
    else:
        return "Strong liquidity - Excellent short-term financial health"


def get_asset_turnover_interpretation(asset_turnover: float) -> str:
    """Get interpretation for Asset Turnover Ratio."""
    if asset_turnover < 0.5:
        return "Low efficiency - Poor asset utilization"
    elif asset_turnover < 1.5:
        return "Moderate efficiency - Acceptable asset utilization"
    elif asset_turnover < 3:
        return "Good efficiency - Strong asset utilization"
    else:
        return "Excellent efficiency - Outstanding asset utilization"


def get_dividend_yield_interpretation(dividend_yield: float) -> str:
    """Get interpretation for Dividend Yield."""
    if dividend_yield < 1:
        return "Low yield - Minimal income generation"
    elif dividend_yield < 3:
        return "Moderate yield - Reasonable income generation"
    elif dividend_yield < 5:
        return "Good yield - Strong income generation"
    else:
        return "High yield - Very strong income generation (may be unsustainable)"


def compare_financial_ratios(tickers: List[str], ratio_type: str) -> Dict[str, Any]:
    """
    Compare financial ratios across multiple tickers.
    
    Args:
        tickers: List of tickers to compare
        ratio_type: Type of ratio to compare
        
    Returns:
        Dictionary containing comparison results
    """
    try:
        comparison_results = {}
        
        for ticker in tickers:
            try:
                client = VNStockClient(ticker=ticker)
                ratios = get_financial_ratios(client, ratio_type)
                
                if ratio_type in ratios:
                    comparison_results[ticker] = ratios[ratio_type]
                else:
                    comparison_results[ticker] = {"error": f"No {ratio_type} data available"}
            
            except Exception as e:
                comparison_results[ticker] = {"error": str(e)}
        
        # Calculate comparison statistics
        valid_values = []
        for ticker, data in comparison_results.items():
            if "error" not in data and "value" in data:
                valid_values.append((ticker, data["value"]))
        
        if valid_values:
            # Sort by value
            sorted_values = sorted(valid_values, key=lambda x: x[1], reverse=True)
            
            comparison_results["comparison"] = {
                "sorted_by_value": sorted_values,
                "highest": sorted_values[0],
                "lowest": sorted_values[-1],
                "mean": sum(v[1] for v in valid_values) / len(valid_values),
                "count": len(valid_values)
            }
        
        return comparison_results
    
    except Exception as e:
        return {"error": str(e)}


def calculate_financial_health_score(ticker: str) -> Dict[str, Any]:
    """
    Calculate overall financial health score for a company.
    
    Args:
        ticker: Stock ticker symbol
        
    Returns:
        Dictionary containing financial health score
    """
    try:
        client = VNStockClient(ticker=ticker)
        ratios = get_financial_ratios(client)
        
        score_components = {}
        total_score = 0
        max_score = 0
        
        # P/E Ratio Score (lower is better, but not too low)
        if "pe_ratio" in ratios:
            pe_value = ratios["pe_ratio"]["value"]
            if pe_value < 10:
                pe_score = 6  # Too low might indicate problems
            elif pe_value < 20:
                pe_score = 10  # Ideal range
            elif pe_value < 30:
                pe_score = 7  # Acceptable but high
            else:
                pe_score = 3  # Too high
            score_components["pe_ratio"] = pe_score
            total_score += pe_score
            max_score += 10
        
        # ROE Score (higher is better)
        if "roe" in ratios:
            roe_value = ratios["roe"]["value"]
            if roe_value < 5:
                roe_score = 2
            elif roe_value < 15:
                roe_score = 6
            elif roe_value < 25:
                roe_score = 9
            else:
                roe_score = 10
            score_components["roe"] = roe_score
            total_score += roe_score
            max_score += 10
        
        # Current Ratio Score (moderate is better)
        if "current_ratio" in ratios:
            cr_value = ratios["current_ratio"]["value"]
            if cr_value < 1:
                cr_score = 2  # Poor liquidity
            elif cr_value < 1.5:
                cr_score = 7  # Adequate
            elif cr_value < 3:
                cr_score = 10  # Ideal
            else:
                cr_score = 6  # Too high
            score_components["current_ratio"] = cr_score
            total_score += cr_score
            max_score += 10
        
        # Debt to Equity Score (lower is better)
        if "debt_to_equity" in ratios:
            dte_value = ratios["debt_to_equity"]["value"]
            if dte_value < 0.5:
                dte_score = 10  # Low risk
            elif dte_value < 1.5:
                dte_score = 7  # Moderate risk
            elif dte_value < 2.5:
                dte_score = 4  # High risk
            else:
                dte_score = 1  # Very high risk
            score_components["debt_to_equity"] = dte_score
            total_score += dte_score
            max_score += 10
        
        # Profit Margin Score (higher is better)
        if "profit_margin" in ratios:
            pm_value = ratios["profit_margin"]["value"]
            if pm_value < 0:
                pm_score = 1  # Losing money
            elif pm_value < 5:
                pm_score = 4  # Low margins
            elif pm_value < 15:
                pm_score = 7  # Good margins
            elif pm_value < 25:
                pm_score = 9  # Strong margins
            else:
                pm_score = 10  # Excellent margins
            score_components["profit_margin"] = pm_score
            total_score += pm_score
            max_score += 10
        
        # Calculate overall score
        if max_score > 0:
            overall_score = (total_score / max_score) * 100
        else:
            overall_score = 0
        
        return {
            "ticker": ticker,
            "score_components": score_components,
            "total_score": total_score,
            "max_score": max_score,
            "overall_score": overall_score,
            "health_level": get_health_level(overall_score),
            "interpretation": get_health_interpretation(overall_score, score_components)
        }
    
    except Exception as e:
        return {"error": str(e)}


def get_health_level(score: float) -> str:
    """Get health level based on score."""
    if score < 40:
        return "Poor"
    elif score < 60:
        return "Fair"
    elif score < 80:
        return "Good"
    else:
        return "Excellent"


def get_health_interpretation(score: float, components: Dict[str, int]) -> str:
    """Get detailed interpretation of financial health."""
    if score < 40:
        return "Company has significant financial issues. High risk investment."
    elif score < 60:
        return "Company has moderate financial concerns. Proceed with caution."
    elif score < 80:
        return "Company has generally good financial health. Moderate risk."
    else:
        return "Company has excellent financial health. Low risk investment."