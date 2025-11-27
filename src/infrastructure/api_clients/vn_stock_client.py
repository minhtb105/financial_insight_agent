from vnstock import Company, Quote
import pandas as pd


class VNStockClient: 
    def __init__(self, ticker: str = "VCB", source: str = "TCBS"):
        self.ticker = ticker
        self.company = Company(symbol=ticker, source=source)
        self.quote = Quote(symbol=ticker, source=source)
        
    def company_info(self):
        """Return static company overview"""
        return self.company.overview()
        
    def fetch_trading_data(
        self, 
        start: str = None, 
        end: str = None, 
        interval: str = "1m",
        window_size: int = 2
    ) -> pd.DataFrame:
        """
        Fetch OHLCV trading data from vnstock (raw data only).

        - start, end: yyyy-mm-dd
        - interval: 1d, 1m, 5m, 15m, 1W, 1M

        Returns:
            DataFrame with columns standardized:
            date, open, high, low, close, volume
        """
        # --- 1. Validate ---
        if start is None or end is None:
            raise ValueError("start and end must not be None.")
        
        if isinstance(start, str):
            start = pd.to_datetime(start)

        if isinstance(end, str):
            end = pd.to_datetime(end)

        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        # --- 2. Fetch raw data ---
        df = self.quote.history(start=start_str, end=end_str, interval=interval)
        
        if df is None or df.empty:
            return pd.DataFrame()
        
         # --- 3. Normalize column names ---
        df = df.rename(columns={"time": "date"})
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        
        # Ensure sort ascending
        df = df.sort_values(by="date")

        # Filter exact time window
        df = df[(df["date"] >= start_str) & (df["date"] <= end_str)]
        
        return df
        
        
if __name__ == "__main__":
    client = VNStockClient(ticker="VND", source="TCBS")
    df= client.fetch_trading_data(start='2025-11-01', end='2025-11-15',
                                        window_size=14, interval="1d")
    print(df)
       