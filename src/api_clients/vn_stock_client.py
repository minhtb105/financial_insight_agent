from vnstock import Company, Quote
import pandas as pd


class VNStockClient: 
    def __init__(self, ticker: str = "VCB", source: str = "TCBS"):
        self.ticker = ticker
        self.company = Company(symbol=ticker, source=source)
        self.quote = Quote(symbol=ticker, source=source)
        
    def company_info(self):
        return self.company.overview()
        
    def fetch_trading_data(
        self, 
        start: str = None, 
        end: str = None, 
        interval: str = "1m",
        window_size: int = 2
    ) -> pd.DataFrame:
        """
        Lấy dữ liệu giá lịch sử cho mã chứng khoán.
        - Hỗ trợ: khoảng thời gian cụ thể (start-end) hoặc số tháng gần nhất (months)
        - Trả về DataFrame chuẩn hóa cột và thống kê cơ bản
        """
         # --- 1. Chuẩn hóa start/end thành datetime ---
        if isinstance(start, str):
            start = pd.to_datetime(start)

        if isinstance(end, str):
            end = pd.to_datetime(end)

        # --- 2. Kiểm tra trường hợp thiếu ---
        if start is None or end is None:
            raise ValueError("start và end không được để None trong chế độ fetch theo khoảng thời gian.")

        # --- 3. Chuyển về đúng định dạng API yêu cầu ---
        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        # --- 4. Fetch dữ liệu từ vnstock ---
        df = self.quote.history(start=start_str, end=end_str, interval=interval)
        df = df.rename(columns={"time": "date"})
        df = df[(df["date"] >= start_str) & (df["date"] <= end_str)]
        
        df["date"] = pd.to_datetime(df["date"], errors="coerce").dt.strftime("%Y-%m-%d")
        
        if df.empty:
            return df, {}
        
        # --- 5. Stats ---
        stats = {
            "symbol": self.ticker,
            "start": str(start),
            "end": str(end),
            "close_mean": round(df["close"].mean(), 2),
            "close_min": round(df["close"].min(), 2),
            "close_max": round(df["close"].max(), 2),
            "volume_avg": int(df["volume"].mean()),
        }
        
        # --- 6. SMA ---
        df["SMA"] = df["close"].rolling(window=window_size, min_periods=1).mean().round(2)

        # --- 7. RSI ---
        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        
        avg_gain = gain.rolling(window=window_size, min_periods=1).mean()
        avg_loss = loss.rolling(window=window_size, min_periods=1).mean()

        rs = avg_gain / avg_loss
        df[f"RSI_{window_size}"] = 100 - (100 / (1 + rs))

        df[f"RSI_{window_size}"] = df[f"RSI_{window_size}"].round(2)

        return df, stats
        
        
if __name__ == "__main__":
    client = VNStockClient(ticker="VND", source="TCBS")
    df, stats = client.fetch_trading_data(start='2025-11-01', end='2025-11-15',
                                        window_size=14, interval="1d")
    print(df)
       