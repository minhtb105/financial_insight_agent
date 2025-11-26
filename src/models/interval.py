from enum import Enum


class Interval(str, Enum):
    _1m = "1m"
    _5m = "5m"
    _15m = "15m"
    _30m = "30m"
    _1h = "1H"
    _1d = "1D"
    _1w = "1W"
    _1M = "1M"
