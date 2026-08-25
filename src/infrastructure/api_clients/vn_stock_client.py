import logging
import pandas as pd
from vnstock import Company, Quote

logger = logging.getLogger(__name__)

_EXPECTED_COLUMNS = {"time", "open", "high", "low", "close", "volume"}


class VNStockClient:
    """vnstock wrapper.

    vnstock 3.5 restricts ``Company`` to source 'VCI'/'KBS' and its VCI
    company endpoint is unstable, while ``Quote`` works reliably on VCI.
    Defaults therefore differ per underlying class; pass ``source`` to
    force the same provider for both.
    """

    def __init__(self, ticker: str = "VCB", source: str | None = None):
        self.ticker = ticker
        quote_source = source or "VCI"
        company_source = source or "KBS"
        self.company = Company(symbol=ticker, source=company_source)
        self.quote = Quote(symbol=ticker, source=quote_source)

    def company_info(self):
        """Return static company overview"""
        return self.company.overview()

    def fetch_trading_data(
        self,
        start: str | None = None,
        end: str | None = None,
        interval: str = "1m",
    ) -> "pd.DataFrame":
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
        try:
            df = self.quote.history(start=start_str, end=end_str, interval=interval)
        except (ValueError, TypeError) as e:
            logger.error("Invalid parameters for %s: %s", self.ticker, e)
            return pd.DataFrame()
        except ConnectionError as e:
            logger.error("Network error fetching %s: %s", self.ticker, e)
            return pd.DataFrame()
        except Exception:
            logger.exception("Unexpected error fetching %s", self.ticker)
            return pd.DataFrame()

        if df is None or df.empty:
            return pd.DataFrame()

        # --- 3. Validate required columns ---
        missing = _EXPECTED_COLUMNS - set(df.columns)
        if missing:
            logger.error("Missing columns %s in vnstock response for %s", missing, self.ticker)
            return pd.DataFrame()

        # --- 4. Normalize column names ---
        df = df.rename(columns={"time": "date"})
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        df = df.dropna(subset=["date"])
        df["date"] = df["date"].dt.strftime("%Y-%m-%d")

        # Ensure sort ascending
        df = df.sort_values(by="date")

        # Filter exact time window
        df = df[(df["date"] >= start_str) & (df["date"] <= end_str)]

        return df
