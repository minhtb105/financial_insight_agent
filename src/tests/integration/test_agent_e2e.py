import pytest
from application.agents.agent import StockAgent


@pytest.fixture(scope="module")
def agent():
    return StockAgent()


def test_agent_initialization(agent):
    assert agent is not None
    assert agent.tools is not None
    assert len(agent.tools) > 0


def test_agent_returns_string(agent):
    query = "Lấy giá đóng cửa của VCB hôm qua."
    result = agent.run(query)
    assert isinstance(result, str)
    assert len(result) > 0


def test_agent_handles_indicator_query(agent):
    query = "Tính SMA9 cho VCB trong 10 ngày gần đây"
    result = agent.run(query)
    assert isinstance(result, str)
    assert len(result) > 0


def test_agent_handles_empty_query(agent):
    result = agent.run("")
    assert isinstance(result, str)


def test_agent_handles_special_characters(agent):
    query = "!@#$%"
    result = agent.run(query)
    assert isinstance(result, str)