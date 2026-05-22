import json
import pytest
from fastapi.testclient import TestClient


def _parse_sse_events(response) -> list[dict]:
    """Parse SSE response into a list of {event, data} dicts."""
    events = []
    current_event = None
    current_data = []
    for line in response.text.split("\n"):
        if line.startswith("event: "):
            if current_event:
                events.append({"event": current_event, "data": "\n".join(current_data)})
            current_event = line[7:]
            current_data = []
        elif line.startswith("data: ") and current_event:
            current_data.append(line[6:])
    if current_event:
        events.append({"event": current_event, "data": "\n".join(current_data)})
    return events


class TestApiEndpointsMocked:
    def test_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"

    def test_ping_endpoint(self, client):
        response = client.get("/ping")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

    def test_ask_stream_valid_query_success(self, client):
        response = client.post("/ask-stream", json={"query": "Giá VCB hôm qua"})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        events = _parse_sse_events(response)
        final = next((e for e in events if e["event"] == "final"), None)
        assert final is not None, "Missing final event"
        data = json.loads(final["data"])
        assert "answer" in data
        assert len(data["answer"]) > 0
        assert "request_id" in data
        assert "latency_ms" in data
        assert isinstance(data["latency_ms"], (int, float))

    def test_ask_stream_empty_query_returns_422(self, client):
        response = client.post("/ask-stream", json={"query": ""})
        assert response.status_code == 422

    def test_ask_stream_whitespace_query_returns_422(self, client):
        response = client.post("/ask-stream", json={"query": "   "})
        assert response.status_code == 422

    def test_ask_stream_missing_query_field_returns_422(self, client):
        response = client.post("/ask-stream", json={})
        assert response.status_code == 422

    def test_health_agent_ready_flag(self, client):
        response = client.get("/health")
        data = response.json()
        assert "agent_ready" in data

    def test_ask_stream_has_chunk_and_final_events(self, client):
        response = client.post("/ask-stream", json={"query": "Giá VCB hôm qua"})
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert "event: chunk" in response.text or "event: final" in response.text

    def test_ask_stream_long_query_success(self, client):
        response = client.post("/ask-stream", json={"query": "Cho tôi giá cổ phiếu " + "VCB " * 100})
        assert response.status_code == 200
        events = _parse_sse_events(response)
        final = next((e for e in events if e["event"] == "final"), None)
        assert final is not None
        data = json.loads(final["data"])
        assert "answer" in data

    def test_ask_stream_empty_body_returns_422(self, client):
        response = client.post("/ask-stream", json={})
        assert response.status_code == 422
