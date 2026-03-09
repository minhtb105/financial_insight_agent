"""
Ranking Service

This module contains the service for handling ranking queries.
It provides functionality to rank financial data across multiple tickers.
"""

from typing import Dict, Any, List
import pandas as pd
from infrastructure.api_clients.vn_stock_client import VNStockClient
from domain.services.base.time_processor import TimeProcessor


def handle_ranking_query(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle ranking_query: min/max/mean across multiple tickers
    
    Args:
        parsed: Parsed query dictionary
        
    Returns:
        Dictionary containing ranking results
    """
    tickers = parsed.get("tickers") or []
    if not tickers or len(tickers) < 2:
        return {"error": "Need at least 2 tickers for ranking"}

    # Extract requested field and aggregate function
    requested_field = parsed.get("requested_field", "close")
    aggregate = parsed.get("aggregate", "max")
    
    try:
        results = {}
        
        # Process time parameters using TimeProcessor
        time_processor = TimeProcessor()
        time_params = time_processor.process_time_params(parsed)
        start_date = time_params["start_date"]
        end_date = time_params["end_date"]
        
        # Get data for all tickers
        all_data = {}
        for ticker in tickers:
            try:
                data = get_price_data(ticker, start_date, end_date)
                if data:
                    all_data[ticker] = data
            except Exception as e:
                all_data[ticker] = {"error": str(e)}
        
        # Perform ranking
        ranking_results = perform_ranking(all_data, requested_field, aggregate)
        
        results["ranking"] = ranking_results
        results["tickers"] = tickers
        results["requested_field"] = requested_field
        results["aggregate"] = aggregate
        results["time_range"] = {
            "start_date": start_date,
            "end_date": end_date
        }
        
        return results
    
    except Exception as e:
        return {"error": str(e)}


def get_price_data(
    ticker: str, 
    start_date: str = None, 
    end_date: str = None
) -> Dict[str, Any]:
    """
    Get price data for a ticker.
    
    Args:
        ticker: Stock ticker symbol
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        Dictionary containing price data
    """
    try:
        client = VNStockClient(ticker=ticker)
        
        # Fetch data
        data = client.fetch_trading_data(
            start=start_date,
            end=end_date,
            interval="1d"
        )
        
        if data is None or data.empty:
            return {"error": "No data available"}
        
        # Convert to list format
        price_data = []
        for _, row in data.iterrows():
            price_data.append({
                "date": row["time"].strftime("%Y-%m-%d"),
                "open": float(row["open"]),
                "high": float(row["high"]),
                "low": float(row["low"]),
                "close": float(row["close"]),
                "volume": int(row["volume"])
            })
        
        return {
            "ticker": ticker,
            "data": price_data,
            "start_date": start_date,
            "end_date": end_date
        }
    
    except Exception as e:
        return {"error": str(e)}


def perform_ranking(
    all_data: Dict[str, Any], 
    field: str, 
    aggregate: str
) -> Dict[str, Any]:
    """
    Perform ranking across multiple tickers.
    
    Args:
        all_data: Dictionary of ticker data
        field: Field to rank (open, close, high, low, volume)
        aggregate: Aggregation function (max, min, mean, latest)
        
    Returns:
        Dictionary containing ranking results
    """
    ranking = {}
    
    # Calculate statistics for each ticker
    ticker_stats = {}
    for ticker, data in all_data.items():
        if "error" in data:
            ticker_stats[ticker] = {"error": data["error"]}
            continue
        
        values = [item[field] for item in data["data"] if field in item]
        if values:
            if aggregate == "max":
                stat_value = max(values)
            elif aggregate == "min":
                stat_value = min(values)
            elif aggregate == "mean":
                stat_value = sum(values) / len(values)
            elif aggregate == "latest":
                stat_value = values[-1]
            else:
                stat_value = max(values)  # Default to max
            
            ticker_stats[ticker] = {
                "value": stat_value,
                "count": len(values),
                "data_points": values
            }
    
    # Filter out tickers with errors
    valid_stats = {k: v for k, v in ticker_stats.items() if "error" not in v}
    
    if not valid_stats:
        return {"error": "No valid data for ranking"}
    
    # Sort by value
    sorted_tickers = sorted(
        valid_stats.items(), 
        key=lambda x: x[1]["value"], 
        reverse=(aggregate != "min")
    )
    
    # Create ranking list
    ranking_list = []
    for i, (ticker, stats) in enumerate(sorted_tickers, 1):
        ranking_list.append({
            "rank": i,
            "ticker": ticker,
            "value": stats["value"],
            "data_points": stats["count"]
        })
    
    # Get top and bottom performers
    top_performer = ranking_list[0] if ranking_list else None
    bottom_performer = ranking_list[-1] if ranking_list else None
    
    # Calculate statistics
    values = [stats["value"] for stats in valid_stats.values()]
    stats_summary = {
        "mean": sum(values) / len(values) if values else 0,
        "median": sorted(values)[len(values) // 2] if values else 0,
        "std_dev": calculate_std_dev(values) if values else 0,
        "range": (max(values) - min(values)) if values else 0
    }
    
    ranking = {
        "ranking_list": ranking_list,
        "top_performer": top_performer,
        "bottom_performer": bottom_performer,
        "total_tickers": len(valid_stats),
        "valid_tickers": list(valid_stats.keys()),
        "statistics": stats_summary,
        "field": field,
        "aggregate": aggregate
    }
    
    return ranking


def calculate_std_dev(values: List[float]) -> float:
    """
    Calculate standard deviation of a list of values.
    
    Args:
        values: List of numeric values
        
    Returns:
        Standard deviation
    """
    if len(values) < 2:
        return 0.0
    
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return variance ** 0.5


def rank_performance(tickers: List[str], days: int = 30, metric: str = "performance") -> Dict[str, Any]:
    """
    Rank tickers by performance over a specified period.
    
    Args:
        tickers: List of tickers to rank
        days: Number of days to analyze
        metric: Metric to rank by (performance, volatility, volume)
        
    Returns:
        Dictionary containing performance ranking
    """
    try:
        # Get data for all tickers
        all_data = {}
        for ticker in tickers:
            data = get_price_data(ticker, days=days)
            if data and "error" not in data:
                all_data[ticker] = data
        
        # Calculate performance metrics
        performance_data = {}
        for ticker, ticker_data in all_data.items():
            if "data" not in ticker_data or not ticker_data["data"]:
                continue
            
            price_data = ticker_data["data"]
            if len(price_data) < 2:
                continue
            
            if metric == "performance":
                # Calculate price performance
                first_price = price_data[0]["close"]
                last_price = price_data[-1]["close"]
                performance = ((last_price - first_price) / first_price) * 100
                performance_data[ticker] = performance
            
            elif metric == "volatility":
                # Calculate volatility
                volatility = calculate_volatility(price_data)
                performance_data[ticker] = volatility
            
            elif metric == "volume":
                # Calculate average volume
                volumes = [item["volume"] for item in price_data]
                avg_volume = sum(volumes) / len(volumes) if volumes else 0
                performance_data[ticker] = avg_volume
        
        # Sort by metric value
        if metric == "performance":
            # Higher performance is better
            sorted_tickers = sorted(
                performance_data.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
        elif metric == "volatility":
            # Lower volatility might be better (less risk)
            sorted_tickers = sorted(
                performance_data.items(), 
                key=lambda x: x[1], 
                reverse=False
            )
        else:
            # Higher volume is generally better
            sorted_tickers = sorted(
                performance_data.items(), 
                key=lambda x: x[1], 
                reverse=True
            )
        
        # Create ranking list
        ranking_list = []
        for i, (ticker, value) in enumerate(sorted_tickers, 1):
            ranking_list.append({
                "rank": i,
                "ticker": ticker,
                "value": value,
                "metric": metric
            })
        
        return {
            "ranking": ranking_list,
            "metric": metric,
            "analysis_period": f"{days} days",
            "total_tickers": len(ranking_list),
            "top_performer": ranking_list[0] if ranking_list else None,
            "bottom_performer": ranking_list[-1] if ranking_list else None
        }
    
    except Exception as e:
        return {"error": str(e)}


def calculate_volatility(price_data: List[Dict[str, Any]]) -> float:
    """
    Calculate volatility for a ticker.
    
    Args:
        price_data: List of price data points
        
    Returns:
        Volatility percentage
    """
    if len(price_data) < 2:
        return 0.0
    
    returns = []
    for i in range(1, len(price_data)):
        prev_price = price_data[i-1]["close"]
        curr_price = price_data[i]["close"]
        if prev_price != 0:
            return_pct = (curr_price - prev_price) / prev_price
            returns.append(return_pct)
    
    if not returns:
        return 0.0
    
    # Calculate standard deviation of returns
    mean_return = sum(returns) / len(returns)
    variance = sum((r - mean_return) ** 2 for r in returns) / len(returns)
    volatility = (variance ** 0.5) * (252 ** 0.5)  # Annualized volatility
    
    return volatility * 100  # Convert to percentage


def rank_by_indicator(
    tickers: List[str], 
    indicator: str, 
    period: int = 14,
    days: int = 30
) -> Dict[str, Any]:
    """
    Rank tickers by a specific technical indicator.
    
    Args:
        tickers: List of tickers to rank
        indicator: Indicator to rank by (rsi, macd, etc.)
        period: Indicator period
        days: Number of days to analyze
        
    Returns:
        Dictionary containing indicator ranking
    """
    try:
        # Get data for all tickers
        all_data = {}
        for ticker in tickers:
            data = get_price_data(ticker, days=days)
            if data and "error" not in data:
                all_data[ticker] = data
        
        # Calculate indicator for each ticker
        indicator_data = {}
        for ticker, ticker_data in all_data.items():
            if "data" not in ticker_data or not ticker_data["data"]:
                continue
            
            price_data = ticker_data["data"]
            if len(price_data) < period:
                continue
            
            # Convert to DataFrame for indicator calculation
            df = pd.DataFrame(price_data)
            df['close'] = df['close'].astype(float)
            
            if indicator == "rsi":
                rsi_value = calculate_rsi_value(df, period)
                if rsi_value is not None:
                    indicator_data[ticker] = rsi_value
            
            elif indicator == "macd":
                macd_value = calculate_macd_value(df)
                if macd_value is not None:
                    indicator_data[ticker] = macd_value
        
        # Sort by indicator value
        sorted_tickers = sorted(
            indicator_data.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        # Create ranking list
        ranking_list = []
        for i, (ticker, value) in enumerate(sorted_tickers, 1):
            ranking_list.append({
                "rank": i,
                "ticker": ticker,
                "value": value,
                "indicator": indicator,
                "period": period
            })
        
        return {
            "ranking": ranking_list,
            "indicator": indicator,
            "period": period,
            "analysis_period": f"{days} days",
            "total_tickers": len(ranking_list),
            "top_performer": ranking_list[0] if ranking_list else None,
            "bottom_performer": ranking_list[-1] if ranking_list else None
        }
    
    except Exception as e:
        return {"error": str(e)}


def calculate_rsi_value(data: pd.DataFrame, period: int = 14) -> float:
    """
    Calculate RSI value for the latest data point.
    
    Args:
        data: Price data DataFrame
        period: RSI period
        
    Returns:
        Latest RSI value
    """
    if len(data) < period + 1:
        return None
    
    close_prices = data['close'].astype(float)
    
    # Calculate price changes
    delta = close_prices.diff()
    
    # Get gains and losses
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    # Calculate RS and RSI
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else None


def calculate_macd_value(data: pd.DataFrame) -> float:
    """
    Calculate MACD value for the latest data point.
    
    Args:
        data: Price data DataFrame
        
    Returns:
        Latest MACD value
    """
    if len(data) < 26:
        return None
    
    close_prices = data['close'].astype(float)
    
    # Calculate EMAs
    ema_fast = close_prices.ewm(span=12).mean()
    ema_slow = close_prices.ewm(span=26).mean()
    
    # Calculate MACD line
    macd_line = ema_fast - ema_slow
    
    return float(macd_line.iloc[-1]) if pd.notna(macd_line.iloc[-1]) else None


def rank_by_volume(tickers: List[str], days: int = 30) -> Dict[str, Any]:
    """
    Rank tickers by trading volume.
    
    Args:
        tickers: List of tickers to rank
        days: Number of days to analyze
        
    Returns:
        Dictionary containing volume ranking
    """
    return rank_performance(tickers, days, "volume")


def rank_by_volatility(tickers: List[str], days: int = 30) -> Dict[str, Any]:
    """
    Rank tickers by volatility (risk).
    
    Args:
        tickers: List of tickers to rank
        days: Number of days to analyze
        
    Returns:
        Dictionary containing volatility ranking
    """
    return rank_performance(tickers, days, "volatility")