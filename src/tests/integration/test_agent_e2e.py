import pytest
from application.agent.agent import StockAgent
from infrastructure.llm.nlp_parser import QueryParser


@pytest.fixture(scope="module")
def agent():
    """
    Agent thật: parser thật + router thật + services thật.
    """
    parser = QueryParser(test_mode=True)  # test_mode để không gọi LLM thật
    return StockAgent(parser=parser)


def test_price_query_ohlcv(agent):
    query = "Lấy dữ liệu OHLCV 5 ngày gần nhất của HPG"
    result = agent.run(query)
    assert result["status"] == "ok"
    assert isinstance(result["data"], list)
    assert "date" in result["data"][0]
    assert "open" in result["data"][0]


def test_indicator_sma(agent):
    query = "Tính SMA9 của VCB trong 10 ngày gần đây"
    result = agent.run(query)
    assert result["status"] == "ok"
    assert "sma" in result["data"]
    assert "SMA9" in result["data"]["sma"]


def test_company_info(agent):
    query = "Danh sách cổ đông lớn của VCB"
    result = agent.run(query)
    assert result["status"] == "ok"
    assert isinstance(result["data"], list)
    assert len(result["data"]) > 0


def test_comparison(agent):
    query = "So sánh khối lượng giao dịch của VIC với HPG trong 1 tuần"
    result = agent.run(query)
    assert result["status"] == "ok"
    assert isinstance(result["data"], dict)
    assert "VIC" in result["data"]
    assert "HPG" in result["data"]


def test_aggregate(agent):
    query = "Tổng volume của VCB trong 5 ngày gần nhất"
    result = agent.run(query)
    assert result["status"] == "ok"
    assert isinstance(result["data"], (int, float))


def test_ranking(agent):
    query = "Trong các mã VCB, BID, CTG mã nào có giá mở cửa thấp nhất trong 5 ngày gần đây"
    result = agent.run(query)
    assert result["status"] == "ok"
    assert "winner" in result["data"]
    assert "details" in result["data"]
