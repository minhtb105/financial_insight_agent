from enum import Enum

class QueryType(str, Enum):
    price_query = "price_query"            # Get price, OHLCV, volume, etc.
    indicator_query = "indicator_query"    # SMA, RSI, MACD
    company_query = "company_query"        # Shareholders, executives, subsidiaries
    ranking_query = "ranking_query"        # "Which ticker is the lowest/highest?"
    comparison_query = "comparison_query"  # "Compare A with B, C"
    aggregate_query = "aggregate_query"    # sum / average / min / max
