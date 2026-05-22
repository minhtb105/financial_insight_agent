import json
import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def client():
    from interfaces.api.app import app

    with TestClient(app) as c:
        yield c


_API_KEY_MISSING = not os.getenv("OPENAI_API_KEY")
_SKIP_REASON = "OPENAI_API_KEY not set — requires real LLM"


def _parse_sse_final(response) -> dict:
    """Parse SSE response and return the JSON data from the final event."""
    current_event = None
    for line in response.text.split("\n"):
        if line.startswith("event: "):
            current_event = line[7:]
        elif line.startswith("data: ") and current_event == "final":
            return json.loads(line[6:])
    raise AssertionError("No final event found in SSE response")


def make_ask_stream(client, question: str):
    return client.post("/ask-stream", json={"query": question})


def test_api_health_agent_ready(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "agent_ready" in data


def _check_response_structure(data: dict):
    assert "answer" in data
    assert len(data["answer"]) > 0
    assert "request_id" in data
    assert len(data["request_id"]) > 0
    assert "latency_ms" in data
    assert isinstance(data["latency_ms"], (int, float))
    assert data["latency_ms"] >= 0
    assert "query_type" in data
    assert isinstance(data["query_type"], str)
    assert "confidence" in data
    assert isinstance(data["confidence"], (int, float))


@pytest.mark.skipif(_API_KEY_MISSING, reason=_SKIP_REASON)
def test_api_ask_stream_response_structure(client):
    response = make_ask_stream(client, "Lấy giá mở cửa của VCB hôm qua")
    assert response.status_code == 200
    data = _parse_sse_final(response)
    _check_response_structure(data)
    assert "VCB" in data["answer"]


@pytest.mark.skipif(_API_KEY_MISSING, reason=_SKIP_REASON)
def test_api_indicator(client):
    response = make_ask_stream(client, "Tính SMA9 của HPG 10 ngày gần nhất")
    assert response.status_code == 200
    data = _parse_sse_final(response)
    _check_response_structure(data)
    assert "HPG" in data["answer"]


@pytest.mark.skipif(_API_KEY_MISSING, reason=_SKIP_REASON)
def test_api_company(client):
    response = make_ask_stream(client, "Danh sách lãnh đạo của GAS")
    assert response.status_code == 200
    data = _parse_sse_final(response)
    _check_response_structure(data)
    assert "GAS" in data["answer"]


@pytest.mark.skipif(_API_KEY_MISSING, reason=_SKIP_REASON)
def test_api_comparison(client):
    response = make_ask_stream(client, "So sánh volume của FPT và MWG trong 1 tuần")
    assert response.status_code == 200
    data = _parse_sse_final(response)
    _check_response_structure(data)
    assert "FPT" in data["answer"]
    assert "MWG" in data["answer"]


@pytest.mark.skipif(_API_KEY_MISSING, reason=_SKIP_REASON)
def test_api_ranking(client):
    response = make_ask_stream(
        client, "Trong các mã VCB, BID, CTG mã nào có giá đóng thấp nhất 5 ngày qua"
    )
    assert response.status_code == 200
    data = _parse_sse_final(response)
    _check_response_structure(data)


@pytest.mark.skipif(_API_KEY_MISSING, reason=_SKIP_REASON)
def test_api_aggregate(client):
    response = make_ask_stream(client, "Tổng volume của HPG tuần này")
    assert response.status_code == 200
    data = _parse_sse_final(response)
    _check_response_structure(data)


@pytest.mark.skipif(_API_KEY_MISSING, reason=_SKIP_REASON)
def test_api_ask_stream_returns_sse(client):
    response = client.post(
        "/ask-stream",
        json={"query": "Giá VCB hôm nay"},
    )
    assert response.status_code == 200
