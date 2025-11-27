import pytest
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from llm_tools.nlp_parser import QueryParser
from models.intent import Intent


parser = QueryParser()

# -----------------------------
# Helper date functions
# -----------------------------
def today():
    return datetime.now().strftime("%Y-%m-%d")

def days_ago(n):
    return (datetime.now() - timedelta(days=n)).strftime("%Y-%m-%d")

def weeks_ago(n):
    return (datetime.now() - timedelta(weeks=n)).strftime("%Y-%m-%d")

def months_ago(n):
    return (datetime.now() - relativedelta(months=n)).strftime("%Y-%m-%d")

def start_of_month(month):
    year = datetime.now().year
    return f"{year}-{month:02d}-01"

@pytest.mark.parametrize("query, expected", [

    # 1 ─ Lấy OHLCV 10 ngày gần nhất
    ("Lấy dữ liệu OHLCV 10 ngày gần nhất HPG?",
     {
         "intent": Intent.historical_prices,
         "tickers": ["HPG"],
         "requested_field": "ohlcv",         
         "start": days_ago(10),
         "end": today()
     }),

    # 2 ─ Giá đóng từ đầu tháng 11
    ("Lấy giá đóng của của mã VCB từ đầu tháng 11 theo khung 1d?",
     {
         "intent": Intent.historical_prices,
         "tickers": ["VCB"],
         "requested_field": "close_price",
         "interval": "1d",
         "start": start_of_month(11),
         "end": today()
     }),

    # 3 ─ Giá mở cửa thấp nhất
    ("Trong các mã BID, TCB và VCB mã nào có giá mở cửa thấp nhất trong 10 ngày qua.",
     {
         "intent": Intent.historical_prices,
         "tickers": ["BID", "TCB", "VCB"],
         "requested_field": "open_price",
         "aggregate": "min",
         "start": days_ago(10),
         "end": today()
     }),

    # 4 ─ Tổng volume 1 tuần
    ("Tổng khối lượng giao dịch (volume) của mã VIC trong vòng 1 tuần gần đây.",
     {
         "intent": Intent.historical_prices,
         "tickers": ["VIC"],
         "requested_field": "volume",
         "start": weeks_ago(1),
         "end": today()
     }),

    # 5 ─ So sánh volume 2 tuần
    ("So sánh khối lượng giao dịch của VIC với HPG trong 2 tuần gần đây.",
     {
         "intent": Intent.historical_prices,
         "tickers": ["VIC"],
         "requested_field": "volume",
         "compare_with": ["HPG"],
         "start": weeks_ago(2),
         "end": today()
     }),

    # 6 ─ Cổ đông lớn
    ("Danh sách cổ đông lớn của VCB",
     {
         "intent": Intent.company_info,
         "tickers": ["VCB"],
         "requested_field": "shareholders",
         "start": None,
         "end": None
     }),

    # 7 ─ Công ty con
    ("Các công ty con thuộc VCB",
     {
         "intent": Intent.company_info,
         "tickers": ["VCB"],
         "requested_field": "subsidiaries",
         "start": None,
         "end": None
     }),

    # 8 ─ Lãnh đạo
    ("Lấy cho tôi toàn bộ tên các lãnh đạo đang làm việc của VCB.",
     {
         "intent": Intent.company_info,
         "tickers": ["VCB"],
         "requested_field": "executives",
         "start": None,
         "end": None
     }),

    # 9 ─ SMA9 trong 2 tuần
    ("Tính cho tôi SMA9 của mã VIC trong 2 tuần với timeframe 1d.",
     {
         "intent": Intent.technical_indicator,
         "tickers": ["VIC"],
         "requested_field": "sma",
         "interval": "1d",
         "start": weeks_ago(2),
         "end": today()
     }),

    # 10 ─ SMA9 và SMA20 trong 2 tháng
    ("Tính cho tôi SMA9 và SMA20 của mã VIC trong 2 tháng với timeframe 1d.",
     {
         "intent": Intent.technical_indicator,
         "tickers": ["VIC"],
         "requested_field": "sma",
         "interval": "1d",
         "start": months_ago(2),
         "end": today(),
     }),

    # 11 ─ RSI14
    ("Tính cho tôi RSI14 của TCB trong 1 tuần với timeframe 1m.",
     {
         "intent": Intent.technical_indicator,
         "tickers": ["TCB"],
         "requested_field": "rsi",
         "interval": "1m",
         "start": weeks_ago(1),
         "end": today()
     }),

    # 12 ─ SMA9 và SMA20 từ đầu tháng 11
    ("Tính SMA9 và SMA20 của mã TCB từ đầu tháng 11 đến nay",
     {
         "intent": Intent.technical_indicator,
         "tickers": ["TCB"],
         "requested_field": "sma",
         "start": start_of_month(11),
         "end": today(),
     }),

])
def test_query_parser_datetime(query, expected):

    parsed_dict = parser.parse(query)

    # CHECK INTENT ------------------------------------------------------
    assert parsed_dict["intent"] == expected["intent"]

    # CHECK TICKERS -----------------------------------------------------
    for tk in expected["tickers"]:
        assert tk in parsed_dict["tickers"]

    # CHECK REQUESTED FIELD ---------------------------------------------
    if "requested_field" in expected:
        assert parsed_dict["requested_field"] == expected["requested_field"]

    # CHECK INTERVAL -----------------------------------------------------
    if "interval" in expected:
        assert parsed_dict["interval"] == expected["interval"]

    # CHECK WINDOW SIZE --------------------------------------------------
    if "window_size" in expected:
        assert parsed_dict["window_size"] == expected["window_size"]

    # CHECK AGGREGATE ----------------------------------------------------
    if "aggregate" in expected:
        assert parsed_dict["aggregate"] == expected["aggregate"]

    # CHECK COMPARE-WITH -------------------------------------------------
    if "compare_with" in expected:
        assert parsed_dict["compare_with"] == expected["compare_with"]

    # CHECK DATE RANGE ---------------------------------------------------
    if expected["start"] is None:
        assert parsed_dict["start"] is None
    else:
        assert parsed_dict["start"] == expected["start"]

    if expected["end"] is None:
        assert parsed_dict["end"] is None
    else:
        assert parsed_dict["end"] == expected["end"]
