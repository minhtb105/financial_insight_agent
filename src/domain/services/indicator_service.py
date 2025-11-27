from data.indicators import get_sma, get_rsi
from typing import Dict, Any
from infrastructure.api_clients.vn_stock_client import VNStockClient


class IndicatorService:
    """
    Handle indicator_query: SMA, RSI, MACD
    """
    def get_sma(self, query: dict):
        window_sizes = []
        if query.get("indicator_params") and "sma" in query["indicator_params"]:
            window_sizes = query["indicator_params"]["sma"]
        else:
            window_sizes = [9] 

        client = VNStockClient(ticker=query["tickers"][0])
        df, _ = client.fetch_trading_data(
            start=query.get("start"),
            end=query.get("end"),
            interval=query.get("interval") or "1d",
            window_size=max(window_sizes),
        )
        
        result = {}
        for w in window_sizes:
            col = f"SMA"
            if col in df.columns:
                result[f"SMA{w}"] = df[col].iloc[-1]
                
        return result

    def get_rsi(self, query: dict):
        window_sizes = []
        if query.get("indicator_params") and "rsi" in query["indicator_params"]:
            window_sizes = query["indicator_params"]["rsi"]
        else:
            window_sizes = [14] # default

        client = VNStockClient(ticker=query["tickers"][0])
        df, _ = client.fetch_trading_data(
            start=query.get("start"),
            end=query.get("end"),
            interval=query.get("interval") or "1d",
            window_size=max(window_sizes),
        )
        
        result = {}
        for w in window_sizes:
            col = f"RSI_{w}"
            if col in df.columns:
                result[f"RSI{w}"] = df[col].iloc[-1]
                
        return result
    
    def handle(self, parsed: Dict[str, Any]):
        tickers = parsed.get("tickers") or []
        if not tickers:
            return {"error": "Missing ticker"}

        params = parsed.get("indicator_params") or {}
        output = {}

        try:
            if "sma" in params:
                output["sma"] = get_sma(parsed)

            if "rsi" in params:
                output["rsi"] = get_rsi(parsed)

            if not output:
                return {"error": "Does not has any valid indicator"}

            return output

        except Exception as e:
            return {"error": str(e)}
