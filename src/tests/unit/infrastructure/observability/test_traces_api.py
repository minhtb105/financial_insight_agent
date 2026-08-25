"""Unit tests for the /traces REST endpoints (isolated FastAPI app)."""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from infrastructure.observability.tracing import SpanKind, Tracer, TraceStore


@pytest.fixture()
def client(tmp_path, monkeypatch):
    store = TraceStore(tmp_path / "api_traces.db")
    tracer = Tracer(store=store, enabled=True)
    with tracer.start_span("agent.run", SpanKind.AGENT) as root:
        root.attributes["marker"] = "api_test"
        with tracer.start_span("reason", SpanKind.NODE):
            pass

    import interfaces.api.routes.traces as traces_module

    monkeypatch.setattr(traces_module, "get_tracer", lambda: tracer)

    app = FastAPI()
    app.include_router(traces_module.router)
    return TestClient(app), store


class TestTracesApi:
    def test_list_returns_trace_summary(self, client):
        http, _store = client
        resp = http.get("/traces")
        assert resp.status_code == 200
        body = resp.json()
        assert body["enabled"] is True
        assert body["count"] == 1
        row = body["traces"][0]
        assert row["root_name"] == "agent.run"
        assert row["num_spans"] == 2
        assert row["status"] == "ok"

    def test_list_filters_by_status(self, client):
        http, _store = client
        resp = http.get("/traces", params={"status": "error"})
        assert resp.status_code == 200
        assert resp.json()["count"] == 0

    def test_detail_contains_span_tree(self, client):
        http, _store = client
        listed = http.get("/traces").json()["traces"][0]
        detail = http.get(f"/traces/{listed['trace_id']}")
        assert detail.status_code == 200
        trace = detail.json()["trace"]
        names = {s["name"] for s in trace["spans"]}
        assert names == {"agent.run", "reason"}

    def test_detail_404_for_unknown(self, client):
        http, _store = client
        assert http.get("/traces/nope").status_code == 404

    def test_disabled_tracer_returns_503_on_detail(self, tmp_path, monkeypatch):
        from infrastructure.observability.tracing import Tracer as _T

        disabled = _T(store=None, enabled=False)
        import interfaces.api.routes.traces as traces_module

        monkeypatch.setattr(traces_module, "get_tracer", lambda: disabled)
        app = FastAPI()
        app.include_router(router := traces_module.router)

        http = TestClient(app)
        resp = http.get("/traces/some-id")
        assert resp.status_code == 503
        listing = http.get("/traces")
        assert listing.json()["enabled"] is False

    def test_limit_validation(self, client):
        http, _store = client
        resp = http.get("/traces", params={"limit": 999})
        assert resp.status_code == 422
