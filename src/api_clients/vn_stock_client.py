from vnstock import Company, Quote
import pandas as pd
from datetime import datetime
from dateutil.relativedelta import relativedelta


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
        months: int = None,
        interval: str = "1m",
        window_size: int = 5
    ) -> pd.DataFrame:
        """
        Lấy dữ liệu giá lịch sử cho mã chứng khoán.
        - Hỗ trợ: khoảng thời gian cụ thể (start-end) hoặc số tháng gần nhất (months)
        - Trả về DataFrame chuẩn hóa cột và thống kê cơ bản
        """
        today = datetime.today().date()
        if months is not None:
            end = today 
            start = end - relativedelta(months=months)
        elif start is None and end is None:
            # mặc định 3 tháng gần nhất
            end = today
            start = today - relativedelta(months=3)
        else:
            start = pd.to_datetime(start)
            end = pd.to_datetime(end)

        start_str = start.strftime("%Y-%m-%d")
        end_str = end.strftime("%Y-%m-%d")

        df = self.quote.history(start=start_str, end=end_str, interval=interval)
        df = df.rename(columns={"time": "date"})
        df['SMA'] = df['close'].rolling(window=window_size).mean().round(2)


        delta = df['close'].diff()
        gain = delta.clip(lower=0)
        loss = -delta.clip(upper=0)
        
        avg_gain = gain.ewm(alpha=1/window_size, min_periods=window_size).mean()
        avg_loss = loss.ewm(alpha=1/window_size, min_periods=window_size).mean()

        rs = avg_gain / avg_loss
        df[f"RSI_{window_size}"] = 100 - (100 / (1 + rs))

        df = df.dropna().reset_index(drop=True)
        df[f"RSI_{window_size}"] = df[f"RSI_{window_size}"].round(2)


        stats = {
            "symbol": self.ticker,
            "start": str(start),
            "end": str(end),
            "close_mean": round(df["close"].mean(), 2),
            "close_min": round(df["close"].min(), 2),
            "close_max": round(df["close"].max(), 2),
            "volume_avg": int(df["volume"].mean()),
        }

        return df, stats
        
        
if __name__ == "__main__":
    client = VNStockClient(ticker="VND", source="TCBS")
    df, stats = client.fetch_trading_data(start='2020-01-01', end='2024-05-25',
                                        months=3, window_size=14, interval="30m")
    print(df)
    print(stats)
       