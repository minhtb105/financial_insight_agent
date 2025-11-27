from api_clients.vn_stock_client import VNStockClient


def get_ohlcv(query: dict):
    client = VNStockClient(ticker=query["tickers"][0])
    df, _ = client.fetch_trading_data(
        start=query.get("start"),
        end=query.get("end"),
        interval=query.get("interval") or "1d",
    )
    
    return df.tail(5).to_dict(orient="records")

def get_price_field(query: dict):
    """
    Return one of price field following requested_field:
    - close_price → close
    - open_price → open
    - high_price → high
    - low_price → low
    - volume → volume

    Output: DataFrame gồm 2 cột: date + value_field
    """

    client = VNStockClient(ticker=query["tickers"][0])
    df, _ = client.fetch_trading_data(
        start=query.get("start"),
        end=query.get("end"),
        interval=query.get("interval") or "1d",
    )

    if df is None or df.empty:
        return None

    mapping = {
        "close_price": "close",
        "open_price": "open",
        "high_price": "high",
        "low_price": "low",
        "volume": "volume",
    }

    requested = query.get("requested_field")

    if requested not in mapping:
        return None

    col = mapping[requested]

    if col not in df.columns:
        return None

    return df[["date", col]].to_dict(orient="records")

def get_price_stat(query: dict, stat: str):
    client = VNStockClient(ticker=query["tickers"][0])
    df, _ = client.fetch_trading_data(
        start=query.get("start"),
        end=query.get("end"),
        interval=query.get("interval") or "1d",
    )
    if stat == "min":
        return df[query["requested_field"].replace("_price", "")].min()
    elif stat == "max":
        return df[query["requested_field"].replace("_price", "")].max()
    elif stat == "mean":
        return df[query["requested_field"].replace("_price", "")].mean()
    else:
        return None

def get_min_open_across_tickers(query: dict):
    """
    Find the smallest open price over N days ago.
    
    tickers = ["BID", "TCB", "VCB"]
    requested_field = "open_price"
    aggregate = "min"
    """

    tickers = query["tickers"]
    start = query.get("start")
    end = query.get("end")
    interval = query.get("interval") or "1d"

    results = {}

    for ticker in tickers:
        client = VNStockClient(ticker=ticker)
        df, _ = client.fetch_trading_data(start=start, end=end, interval=interval)

        if df is None or df.empty:
            continue

        min_open = df["open"].min()
        results[ticker] = min_open

    if not results:
        return None

    lowest_ticker = min(results, key=results.get)

    return {
        "ticker": lowest_ticker,
        "min_open": results[lowest_ticker],
        "details": results
    }

def get_aggregate_volume(query: dict):
    client = VNStockClient(ticker=query["tickers"][0])
    df, _ = client.fetch_trading_data(
        start=query.get("start"),
        end=query.get("end"),
        interval=query.get("interval") or "1d",
    )
    
    return df["volume"].sum()

def compare_volume(query: dict):
    results = {}
    for ticker in [query["tickers"][0]] + (query.get("compare_with") or []):
        client = VNStockClient(ticker=ticker)
        df, _ = client.fetch_trading_data(
            start=query.get("start"),
            end=query.get("end"),
            interval=query.get("interval") or "1d",
        )
        results[ticker] = df["volume"].sum()
        
    return results

def get_sma(query: dict):
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

def get_rsi(query: dict):
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

def get_company_info(query: dict):
    client = VNStockClient(ticker=query["tickers"][0])
    df = client.company

    field = query.get("requested_field")
    if field == "shareholders":
        return df.shareholders().to_dict(orient="records")
    elif field == "subsidiaries":
        return df.subsidiaries().to_dict(orient="records")
    elif field == "executives":
        return df.officers(filter_by='all').to_dict(orient="records")
    else:
        return df.overview().to_dict(orient="records")
    