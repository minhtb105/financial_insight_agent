"""E2E tests for StockAgent with mocked infrastructure.

NOTE: Full graph execution tests are covered by unit tests
(test_agent_node.py). This file focuses on construction and
non-graph method verification."""

from unittest.mock import MagicMock, patch
import pytest


@pytest.fixture
def agent_with_mocks():
    """Build a StockAgent with ALL external deps mocked.

    The LangGraph graph is compiled but never invoked (that is tested
    in the unit layer at test_agent_node.py).
    """
    with (
        patch("application.agents.agent.LLMProvider") as mock_provider_cls,
        patch("application.agents.agent.ALL_TOOLS", []),
        patch("application.agents.agent.ToolNode"),
        patch("application.agents.agent.ResponseSynthesizer"),
        patch("application.agents.agent.HybridQuerySplitter"),
        patch("application.agents.agent.get_output_guardrails"),
        patch("application.agents.agent.get_memory_manager"),
    ):
        mock_provider = MagicMock()
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content="VCB price is 105,000 VND")
        mock_provider.get_tool_calling_llm.return_value = mock_llm
        mock_provider_cls.return_value = mock_provider

        from application.agents.agent import StockAgent

        agent = StockAgent()
        agent.llm = mock_llm
        return agent


def test_agent_initialization(agent_with_mocks):
    assert agent_with_mocks is not None
    assert hasattr(agent_with_mocks, "tools")
    assert hasattr(agent_with_mocks, "run")


def test_agent_resolve_request_id(agent_with_mocks):
    rid = agent_with_mocks._resolve_request_id("custom-rid")
    assert rid == "custom-rid"
    rid2 = agent_with_mocks._resolve_request_id()
    assert rid2 is not None
    assert isinstance(rid2, str)
    assert len(rid2) > 0


@patch("application.agents.agent.get_memory_manager")
def test_agent_build_memory_context_no_memory(mock_mem):
    mock_mem.return_value = None
    with (
        patch("application.agents.agent.LLMProvider"),
        patch("application.agents.agent.ALL_TOOLS", []),
        patch("application.agents.agent.ToolNode"),
        patch("application.agents.agent.ResponseSynthesizer"),
        patch("application.agents.agent.HybridQuerySplitter"),
    ):
        from application.agents.agent import StockAgent

        agent = StockAgent()
        ctx = agent._build_memory_context("test query")
        assert ctx == ""


@patch("application.agents.agent.get_output_guardrails")
def test_agent_output_guardrails_sanitizes(mock_guardrails):
    mock_gr = MagicMock()
    mock_gr.validate_tool_results.return_value = None
    mock_gr.validate_response.return_value = MagicMock(
        status="PASS",
        issues=[],
        processed_query={"sanitized_response": "sanitized answer"},
    )
    mock_guardrails.return_value = mock_gr
    with (
        patch("application.agents.agent.LLMProvider"),
        patch("application.agents.agent.ALL_TOOLS", []),
        patch("application.agents.agent.ToolNode"),
        patch("application.agents.agent.ResponseSynthesizer"),
        patch("application.agents.agent.HybridQuerySplitter"),
    ):
        from application.agents.agent import StockAgent

        agent = StockAgent()
        result = agent._apply_output_guardrails("raw answer", "test")
        assert result == "sanitized answer"
