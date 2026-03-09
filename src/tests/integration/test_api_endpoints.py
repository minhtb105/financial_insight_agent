import pytest
from fastapi.testclient import TestClient
from interfaces.http.app import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_api_price_query(client):
    response = client.get("/ask", params={"question": "Lấy giá mở cửa của VCB hôm qua"})
    assert response.status_code == 200
    json = response.json()
    assert json["status"] == "ok"
    assert isinstance(json["data"], list)


def test_api_indicator(client):
    response = client.get("/ask", params={"question": "Tính SMA9 của HPG 10 ngày gần nhất"})
    assert response.status_code == 200
    json = response.json()
    assert json["status"] == "ok"
    assert "sma" in json["data"]


def test_api_company(client):
    response = client.get("/ask", params={"question": "Danh sách lãnh đạo của GAS"})
    assert response.status_code == 200
    json = response.json()
    assert json["status"] == "ok"
    assert isinstance(json["data"], list)


def test_api_comparison(client):
    response = client.get("/ask", params={"question": "So sánh volume của FPT và MWG trong 1 tuần"})
    assert response.status_code == 200
    json = response.json()
    assert json["status"] == "ok"
    assert isinstance(json["data"], dict)


def test_api_ranking(client):
    response = client.get("/ask", params={"question": "Trong các mã VCB, BID, CTG mã nào có giá đóng thấp nhất 5 ngày qua"})
    assert response.status_code == 200
    json = response.json()
    assert json["status"] == "ok"
    assert "winner" in json["data"]


def test_api_aggregate(client):
    response = client.get("/ask", params={"question": "Tổng volume của HPG tuần này"})
    assert response.status_code == 200
    json = response.json()
    assert json["status"] == "ok"
    assert isinstance(json["data"], (int, float))
