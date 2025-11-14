from api_clients.vn_stock_client import VNStockClient

def get_ohlcv(query: dict):
    client = VNStockClient(ticker=query["tickers"][0])
    df, _ = client.fetch_trading_data(
        start=query.get("start"),
        end=query.get("end"),
        interval=query.get("interval", "1d"),
    )
    
    return df

def get_price_stat(query: dict, stat: str):
    client = VNStockClient(ticker=query["tickers"][0])
    df, _ = client.fetch_trading_data(
        start=query.get("start"),
        end=query.get("end"),
        interval=query.get("interval", "1d"),
    )
    if stat == "min":
        return df[query["requested_field"].replace("_price", "")].min()
    elif stat == "max":
        return df[query["requested_field"].replace("_price", "")].max()
    elif stat == "mean":
        return df[query["requested_field"].replace("_price", "")].mean()
    else:
        return None

def get_aggregate_volume(query: dict):
    client = VNStockClient(ticker=query["tickers"][0])
    df, _ = client.fetch_trading_data(
        start=query.get("start"),
        end=query.get("end"),
        interval=query.get("interval", "1d"),
    )
    
    return df["volume"].sum()

def compare_volume(query: dict):
    results = {}
    for ticker in [query["tickers"][0]] + (query.get("compare_with") or []):
        client = VNStockClient(ticker=ticker)
        df, _ = client.fetch_trading_data(
            start=query.get("start"),
            end=query.get("end"),
            interval=query.get("interval", "1d"),
        )
        results[ticker] = df["volume"].sum()
        
    return results

def get_sma(query: dict):
    window_sizes = []
    if query.get("indicator_params") and "sma" in query["indicator_params"]:
        window_sizes = query["indicator_params"]["sma"]
    elif query.get("window_size"):
        window_sizes = [query["window_size"]]
    else:
        window_sizes = [9]  # default

    client = VNStockClient(ticker=query["tickers"][0])
    df, _ = client.fetch_trading_data(
        start=query.get("start"),
        end=query.get("end"),
        interval=query.get("interval", "1d"),
        window_size=max(window_sizes),
    )
    result = {}
    for w in window_sizes:
        col = f"SMA"
        if col in df.columns:
            result[f"SMA{w}"] = df[col].iloc[-1]
            
    return result

def get_rsi(query: dict):
    window_sizes = []
    if query.get("indicator_params") and "rsi" in query["indicator_params"]:
        window_sizes = query["indicator_params"]["rsi"]
    elif query.get("window_size"):
        window_sizes = [query["window_size"]]
    else:
        window_sizes = [14]  # default

    client = VNStockClient(ticker=query["tickers"][0])
    df, _ = client.fetch_trading_data(
        start=query.get("start"),
        end=query.get("end"),
        interval=query.get("interval", "1d"),
        window_size=max(window_sizes),
    )
    result = {}
    for w in window_sizes:
        col = f"RSI_{w}"
        if col in df.columns:
            result[f"RSI{w}"] = df[col].iloc[-1]
            
    return result

def get_company_info(query: dict):
    client = VNStockClient(ticker=query["tickers"][0])
    info = client.company_info()
    if query["requested_field"] == "shareholders":
        return info.get("shareholders")
    elif query["requested_field"] == "subsidiaries":
        return info.get("subsidiaries")
    elif query["requested_field"] == "executives":
        return info.get("executives")
    else:
        return info
    