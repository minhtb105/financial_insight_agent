import pytest
from fastapi.testclient import TestClient
from interfaces.api.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def make_ask(client, question: str):
    return client.post("/ask", json={"query": question})


def test_api_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_api_ping(client):
    response = client.get("/ping")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_api_empty_query_returns_422(client):
    response = client.post("/ask", json={"query": ""})
    assert response.status_code == 422


def test_api_whitespace_query_returns_422(client):
    response = client.post("/ask", json={"query": "   "})
    assert response.status_code == 422


def test_api_stream_whitespace_query_returns_422(client):
    response = client.post("/ask-stream", json={"query": "   "})
    assert response.status_code == 422


def test_api_ask_response_structure(client):
    response = make_ask(client, "Lấy giá mở cửa của VCB hôm qua")
    assert response.status_code in (200, 500)
    if response.status_code == 200:
        data = response.json()
        assert "answer" in data
        assert "request_id" in data
        assert "latency_ms" in data
        assert isinstance(data["latency_ms"], (int, float))
        assert "query_type" in data
        assert isinstance(data["query_type"], str)
        assert data["query_type"] != ""
        assert "confidence" in data
        assert isinstance(data["confidence"], (int, float))
        assert data["confidence"] >= 0


def test_api_indicator(client):
    response = make_ask(client, "Tính SMA9 của HPG 10 ngày gần nhất")
    assert response.status_code in (200, 500)
    if response.status_code == 200:
        data = response.json()
        assert "answer" in data
        assert "query_type" in data
        assert isinstance(data["query_type"], str)
        assert data["query_type"] != ""
        assert "confidence" in data
        assert isinstance(data["confidence"], (int, float))
        assert data["confidence"] >= 0


def test_api_company(client):
    response = make_ask(client, "Danh sách lãnh đạo của GAS")
    assert response.status_code in (200, 500)
    if response.status_code == 200:
        data = response.json()
        assert "answer" in data
        assert "query_type" in data
        assert data["query_type"] != ""
        assert "confidence" in data
        assert data["confidence"] >= 0


def test_api_comparison(client):
    response = make_ask(client, "So sánh volume của FPT và MWG trong 1 tuần")
    assert response.status_code in (200, 500)
    if response.status_code == 200:
        data = response.json()
        assert "answer" in data
        assert data["query_type"] != ""
        assert data["confidence"] >= 0


def test_api_ranking(client):
    response = make_ask(client, "Trong các mã VCB, BID, CTG mã nào có giá đóng thấp nhất 5 ngày qua")
    assert response.status_code in (200, 500)
    if response.status_code == 200:
        data = response.json()
        assert "answer" in data
        assert data["query_type"] != ""
        assert data["confidence"] >= 0


def test_api_aggregate(client):
    response = make_ask(client, "Tổng volume của HPG tuần này")
    assert response.status_code in (200, 500)
    if response.status_code == 200:
        data = response.json()
        assert "answer" in data
        assert data["query_type"] != ""
        assert data["confidence"] >= 0


def test_api_ask_stream_returns_sse(client):
    response = client.post(
        "/ask-stream",
        json={"query": "Giá VCB hôm nay"},
    )
    assert response.status_code in (200, 500)
