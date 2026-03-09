"""
Price Service

This module contains the service for handling price-related queries.
It provides functionality to fetch and process price data for stocks.
"""

from typing import Dict, Any
from datetime import datetime
import pandas as pd
from infrastructure.api_clients.vn_stock_client import VNStockClient
from domain.services.base.time_processor import TimeProcessor


def handle_price_query(parsed: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle price_query: open, close, volume, ohlcv
    
    Args:
        parsed: Parsed query dictionary
        
    Returns:
        Dictionary containing price data
    """
    tickers = parsed.get("tickers") or []
    if not tickers:
        return {"error": "Missing ticker"}

    # Extract requested field
    requested_field = parsed.get("requested_field", "close")
    
    try:
        results = {}
        
        for ticker in tickers:
            try:
                client = VNStockClient(ticker=ticker)
                
                # Process time parameters using TimeProcessor
                time_processor = TimeProcessor()
                time_params = time_processor.process_time_params(parsed)
                start_date = time_params["start_date"]
                end_date = time_params["end_date"]
                
                # Fetch data
                data = client.fetch_trading_data(
                    start=start_date,
                    end=end_date,
                    interval="1d"
                )
                
                if data is None or data.empty:
                    results[ticker] = {"error": "No data available"}
                    continue
                
                # Process data based on requested field
                if requested_field == "ohlcv":
                    # Return all OHLCV data
                    ticker_data = []
                    for _, row in data.iterrows():
                        ticker_data.append({
                            "date": row["time"].strftime("%Y-%m-%d"),
                            "open": float(row["open"]),
                            "high": float(row["high"]),
                            "low": float(row["low"]),
                            "close": float(row["close"]),
                            "volume": int(row["volume"])
                        })
                    results[ticker] = ticker_data
                
                elif requested_field == "open":
                    # Return open prices
                    ticker_data = []
                    for _, row in data.iterrows():
                        ticker_data.append({
                            "date": row["time"].strftime("%Y-%m-%d"),
                            "open": float(row["open"])
                        })
                    results[ticker] = ticker_data
                
                elif requested_field == "close":
                    # Return close prices
                    ticker_data = []
                    for _, row in data.iterrows():
                        ticker_data.append({
                            "date": row["time"].strftime("%Y-%m-%d"),
                            "close": float(row["close"])
                        })
                    results[ticker] = ticker_data
                
                elif requested_field == "volume":
                    # Return volumes
                    ticker_data = []
                    for _, row in data.iterrows():
                        ticker_data.append({
                            "date": row["time"].strftime("%Y-%m-%d"),
                            "volume": int(row["volume"])
                        })
                    results[ticker] = ticker_data
                
                else:
                    # Default to close price
                    ticker_data = []
                    for _, row in data.iterrows():
                        ticker_data.append({
                            "date": row["time"].strftime("%Y-%m-%d"),
                            "close": float(row["close"])
                        })
                    results[ticker] = ticker_data
            
            except Exception as e:
                results[ticker] = {"error": str(e)}
        
        return results if results else {"error": "No valid data found"}
    
    except Exception as e:
        return {"error": str(e)}


def get_latest_price(ticker: str, field: str = "close") -> Dict[str, Any]:
    """
    Get the latest price for a specific ticker.
    
    Args:
        ticker: Stock ticker symbol
        field: Price field to retrieve (open, close, high, low, volume)
        
    Returns:
        Dictionary containing the latest price
    """
    try:
        client = VNStockClient(ticker=ticker)
        today = datetime.now().strftime("%Y-%m-%d")
        
        data = client.fetch_trading_data(
            start=today,
            end=today,
            interval="1d"
        )
        
        if data is None or data.empty:
            return {"error": "No data available"}
        
        latest_row = data.iloc[-1]
        
        if field == "open":
            return {"ticker": ticker, "date": today, "open": float(latest_row["open"])}
        elif field == "close":
            return {"ticker": ticker, "date": today, "close": float(latest_row["close"])}
        elif field == "high":
            return {"ticker": ticker, "date": today, "high": float(latest_row["high"])}
        elif field == "low":
            return {"ticker": ticker, "date": today, "low": float(latest_row["low"])}
        elif field == "volume":
            return {"ticker": ticker, "date": today, "volume": int(latest_row["volume"])}
        else:
            return {"ticker": ticker, "date": today, "close": float(latest_row["close"])}
    
    except Exception as e:
        return {"error": str(e)}


def get_price_history(ticker: str, days: int = 30, field: str = "close") -> Dict[str, Any]:
    """
    Get price history for a specific ticker.
    
    Args:
        ticker: Stock ticker symbol
        days: Number of days to retrieve
        field: Price field to retrieve
        
    Returns:
        Dictionary containing price history
    """
    try:
        client = VNStockClient(ticker=ticker)
        end_date = datetime.now()
        start_date = end_date.replace(day=end_date.day - days)
        
        data = client.fetch_trading_data(
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            interval="1d"
        )
        
        if data is None or data.empty:
            return {"error": "No data available"}
        
        history = []
        for _, row in data.iterrows():
            if field == "open":
                value = float(row["open"])
            elif field == "close":
                value = float(row["close"])
            elif field == "high":
                value = float(row["high"])
            elif field == "low":
                value = float(row["low"])
            elif field == "volume":
                value = int(row["volume"])
            else:
                value = float(row["close"])
            
            history.append({
                "date": row["time"].strftime("%Y-%m-%d"),
                field: value
            })
        
        return {
            "ticker": ticker,
            "field": field,
            "days": days,
            "history": history
        }
    
    except Exception as e:
        return {"error": str(e)}