"""Unit tests for dashboard follow-up context (P4) — no LLM calls."""

from unittest.mock import patch

from langchain_core.messages import HumanMessage, SystemMessage

from application.agents.agent import StockAgent, _summarize_chart_spec
from application.agents.agent import LLMUnavailableError


def _make_agent():
    with (
        patch("application.agents.agent.LLMProvider") as mock_provider_cls,
        patch("infrastructure.mcp.loader.load_mcp_tools_sync", return_value=[]),
        patch("application.agents.agent.CustomToolNode"),
        patch("application.agents.agent.ResponseSynthesizer"),
        patch("application.agents.agent.HybridQuerySplitter"),
    ):
        mock_provider_cls.side_effect = LLMUnavailableError("No LLM")
        return StockAgent()


def _spec(**overrides):
    base = {
        "chart_type": "candlestick",
        "title": "VNM — Giá 6 tháng",
        "x_field": "time",
        "y_field": "close",
        "series": [{"name": "VNM", "type": "candlestick", "data_ref": "rows"}],
        "data_source": "vnstock:VNM:close:6m",
    }
    base.update(overrides)
    return base


def test_summarize_none_returns_none():
    assert _summarize_chart_spec(None) is None
    assert _summarize_chart_spec({}) is None
    assert _summarize_chart_spec("not-a-dict") is None


def test_summarize_contains_type_title_symbols():
    summary = _summarize_chart_spec(_spec())
    assert summary is not None
    assert "candlestick" in summary
    assert "VNM" in summary
    assert "time" in summary and "close" in summary


def test_summarize_truncates_long_title():
    summary = _summarize_chart_spec(_spec(title="X" * 500))
    assert summary is not None
    assert len(summary) <= 600


def test_build_messages_injects_dashboard_context():
    agent = _make_agent()
    state = {
        "messages": [HumanMessage(content="Vì sao đoạn tháng 3 giảm?")],
        "iterations": 0,
        "original_query": "Vì sao đoạn tháng 3 giảm?",
        "request_id": "rid-1",
        "memory_context": "",
        "active_chart_spec": "Active dashboard: candlestick VNM",
    }
    messages = agent._build_messages(state)  # type: ignore[typeddict-item]
    systems = [m for m in messages if isinstance(m, SystemMessage)]
    assert any("Dashboard" in m.content for m in systems)


def test_build_messages_without_spec_has_no_dashboard():
    agent = _make_agent()
    state = {
        "messages": [HumanMessage(content="Giá VCB?")],
        "iterations": 0,
        "original_query": "Giá VCB?",
        "request_id": "rid-2",
        "memory_context": "",
    }
    messages = agent._build_messages(state)  # type: ignore[typeddict-item]
    assert not any("Dashboard" in m.content for m in messages if isinstance(m, SystemMessage))


def test_execute_graph_threads_active_spec_to_single():
    agent = _make_agent()
    captured = {}

    def fake_run_single(query, rid, memory_context="", user_id=None, active_chart_summary=None):
        captured["summary"] = active_chart_summary
        return "ok"

    with (
        patch.object(
            agent,
            "_prepare_and_split",
            return_value=("", ["only query"], {"reformulated": "only query", "entities": [], "topics": []}),
        ),
        patch.object(agent, "_run_single", side_effect=fake_run_single),
        patch("application.agents.agent.get_memory_manager", return_value=None),
    ):
        result = agent._execute_graph("q", "rid", active_chart_spec=_spec())
    assert result == "ok"
    assert captured["summary"] is not None
    assert "candlestick" in captured["summary"]


def test_execute_graph_without_spec_passes_none():
    agent = _make_agent()
    captured = {}

    def fake_run_single(query, rid, memory_context="", user_id=None, active_chart_summary=None):
        captured["summary"] = active_chart_summary
        return "ok"

    with (
        patch.object(
            agent,
            "_prepare_and_split",
            return_value=("", ["only query"], {"reformulated": "only query", "entities": [], "topics": []}),
        ),
        patch.object(agent, "_run_single", side_effect=fake_run_single),
        patch("application.agents.agent.get_memory_manager", return_value=None),
    ):
        agent._execute_graph("q", "rid")
    assert captured["summary"] is None


def test_query_request_accepts_active_chart_spec():
    from interfaces.api.app import QueryRequest

    req = QueryRequest(query="Vì sao giảm?", activeChartSpec=_spec())
    assert req.activeChartSpec is not None
    assert req.activeChartSpec["chart_type"] == "candlestick"
    req2 = QueryRequest(query="Giá VCB?")
    assert req2.activeChartSpec is None
