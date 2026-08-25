"""End-to-end pipeline tests for StockAgent — Reason/Action graph wiring.

Tests the complete node sequence using real CustomToolNode, FactVerifier,
and LangGraph graph, with LangGraph execution layer mocked
(LangGraph 1.x requires thread_id in config with MemorySaver).

Architecture:
  reason → action → reason → final_answer → verify_facts → END
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from application.agents.agent import AgentState


# =========================================================================
# Mock tool compatible with CustomToolNode
# =========================================================================


class _MockTool:
    """Drop-in for a LangChain StructuredTool — needs name + invoke()."""

    def __init__(self, name: str, result: str):
        self.name = name
        self._result = result

    def invoke(self, args: dict) -> str:
        return self._result


# =========================================================================
# Shared fixtures
# =========================================================================


@pytest.fixture
def mock_tools():
    return [
        _MockTool(
            "get_stock_price",
            json.dumps({
                "VCB": {"price": 95000, "ticker": "VCB", "end_date": "2026-05-22"},
            }),
        ),
    ]


@pytest.fixture
def mock_llm_with_tool_call():
    llm = MagicMock()
    llm.invoke.side_effect = [
        AIMessage(
            content="",
            tool_calls=[{
                "name": "get_stock_price",
                "args": {"tickers": ["VCB"]},
                "id": "tool_call_1",
            }],
        ),
        AIMessage(
            content=(
                "Giá đóng cửa của VCB là 95,000 VND "
                "[VCB: 95000, nguồn: get_stock_price]"
            ),
        ),
    ]
    return llm


def _build_agent(mock_tools, mock_llm, guardrails_config=None):
    """Build a StockAgent with all external deps mocked.

    Real: CustomToolNode, FactVerifier, graph wiring
    Mocked: LLMProvider, HybridQuerySplitter, ResponseSynthesizer, guardrails, memory
    """
    if guardrails_config is None:
        guardrails_config = {"status": "PASS", "tool_error": None}

    with (
        patch("application.agents.agent.LLMProvider") as mock_provider_cls,
        patch("application.agents.agent.HybridQuerySplitter"),
        patch("application.agents.agent.ResponseSynthesizer"),
        patch("application.agents.agent.get_output_guardrails") as mock_gr_fn,
        patch("application.agents.agent.get_memory_manager") as mock_mem_fn,
    ):
        mock_provider = MagicMock()
        mock_provider.get_tool_calling_llm.return_value = mock_llm
        mock_provider_cls.return_value = mock_provider

        mock_guardrails = MagicMock()
        mock_guardrails.validate_tool_results.return_value = guardrails_config["tool_error"]
        mock_guardrails.validate_response.return_value = MagicMock(
            status=guardrails_config["status"],
            issues=[],
            processed_query={
                "original_response": "dummy",
                "sanitized_response": "dummy",
            },
        )
        mock_gr_fn.return_value = mock_guardrails

        mock_mem_fn.return_value = None

        with patch("application.agents.agent.ALL_TOOLS", mock_tools):
            from application.agents.agent import StockAgent

            agent = StockAgent()
            agent.llm = mock_llm
            return agent


def _make_state(messages, iterations=0, query="test query", rid="test-rid", next_tool_call=None):
    return AgentState(
        messages=messages,
        iterations=iterations,
        original_query=query,
        request_id=rid,
        memory_context="",
        tool_call_history=[],
        tool_call_cache={},
        tool_call_retries={},
        next_tool_call=next_tool_call,
    )


# =========================================================================
# Tests — graph node sequence
# =========================================================================


class TestNodeSequence:
    """Verify each node in the Reason/Action graph produces correct outputs.

    Tests execute nodes in the actual graph order, simulating the
    full reason → action → reason → final_answer → verify_facts flow.
    """

    def test_reason_node_requests_tool_call(self, mock_tools, mock_llm_with_tool_call):
        agent = _build_agent(mock_tools, mock_llm_with_tool_call)
        state = _make_state([HumanMessage(content="Giá VCB?")])

        result = agent._reason_node(state)
        msgs = result["messages"]

        assert len(msgs) == 1
        ai = msgs[0]
        assert isinstance(ai, AIMessage)
        assert len(ai.tool_calls) == 1
        assert ai.tool_calls[0]["name"] == "get_stock_price"
        # next_tool_call must be set for action_node routing
        assert result["next_tool_call"] == ai.tool_calls

    def test_tool_node_executes_and_returns_data(self, mock_tools, mock_llm_with_tool_call):
        agent = _build_agent(mock_tools, mock_llm_with_tool_call)
        ai = AIMessage(
            content="",
            tool_calls=[{"name": "get_stock_price", "args": {"tickers": ["VCB"]}, "id": "1"}],
        )
        state = _make_state([HumanMessage(content="Giá VCB?"), ai])

        result = agent.tool_node(state)
        msgs = result["messages"]

        assert len(msgs) == 1
        tm = msgs[0]
        assert isinstance(tm, ToolMessage)
        assert "VCB" in str(tm.content)
        assert "price" in str(tm.content)

    def test_action_node_resets_next_tool_call(self, mock_tools, mock_llm_with_tool_call):
        agent = _build_agent(mock_tools, mock_llm_with_tool_call)
        state = _make_state(
            [HumanMessage(content="Giá VCB?")],
            next_tool_call=[{"name": "get_stock_price", "args": {"tickers": ["VCB"]}, "id": "1"}],
        )

        result = agent._action_node(state)
        msgs = result["messages"]

        assert len(msgs) == 1
        assert isinstance(msgs[0], ToolMessage)
        assert result["next_tool_call"] is None
        assert "VCB" in str(msgs[0].content)

    def test_action_node_ignores_messages_without_next_tool_call(self, mock_tools, mock_llm_with_tool_call):
        """Verifies _action_node reads from next_tool_call field, NOT from messages."""
        agent = _build_agent(mock_tools, mock_llm_with_tool_call)
        ai = AIMessage(
            content="",
            tool_calls=[{"name": "get_stock_price", "args": {"tickers": ["VCB"]}, "id": "1"}],
        )
        state = _make_state(
            [HumanMessage(content="Giá VCB?"), ai],
            next_tool_call=None,  # No pending tool call despite AIMessage having one
        )

        result = agent._action_node(state)

        # No tool should be executed since next_tool_call is None
        assert result["messages"] == []
        assert result["next_tool_call"] is None

    def test_action_node_reads_next_tool_call_not_messages(self, mock_tools, mock_llm_with_tool_call):
        """Proves _action_node uses next_tool_call as the authoritative source."""
        agent = _build_agent(mock_tools, mock_llm_with_tool_call)
        state = _make_state(
            [HumanMessage(content="No tool here")],
            next_tool_call=[{"name": "get_stock_price", "args": {"tickers": ["VCB"]}, "id": "1"}],
        )

        result = agent._action_node(state)

        # Executes even though the last message has no tool_calls
        assert len(result["messages"]) == 1
        assert isinstance(result["messages"][0], ToolMessage)
        assert "VCB" in str(result["messages"][0].content)
        assert result["next_tool_call"] is None

    def test_reason_node_produces_final_answer(self, mock_tools):
        llm = MagicMock()
        llm.invoke.return_value = AIMessage(
            content="Giá VCB là 95,000 [VCB: 95000, nguồn: get_stock_price]",
        )
        agent = _build_agent(mock_tools, llm)
        tool_result = ToolMessage(
            content=json.dumps({"VCB": {"price": 95000, "ticker": "VCB"}}),
            tool_call_id="1",
            name="get_stock_price",
        )
        state = _make_state([HumanMessage(content="Giá VCB?"), tool_result])

        result = agent._reason_node(state)
        msgs = result["messages"]

        assert len(msgs) == 1
        ai = msgs[0]
        assert isinstance(ai, AIMessage)
        assert "95,000" in ai.content
        assert "[VCB: 95000, nguồn: get_stock_price]" in ai.content
        # No tool calls → next_tool_call must be None
        assert result["next_tool_call"] is None

    def test_final_answer_node_passes_through(self, mock_tools, mock_llm_with_tool_call):
        agent = _build_agent(mock_tools, mock_llm_with_tool_call)
        final_ai = AIMessage(
            content="Giá VCB là 95,000 [VCB: 95000, nguồn: get_stock_price]",
        )
        state = _make_state([
            HumanMessage(content="Giá VCB?"),
            ToolMessage(content="data", tool_call_id="1"),
            final_ai,
        ])

        result = agent._final_answer_node(state)
        msgs = result["messages"]

        assert len(msgs) == 1
        assert msgs[0].content == final_ai.content

    def test_verify_facts_node_passes_verified(self, mock_tools):
        agent = _build_agent(mock_tools, MagicMock())
        state = _make_state([
            HumanMessage(content="Giá VCB?"),
            AIMessage(content="", tool_calls=[{"name": "get_stock_price", "args": {}, "id": "1"}]),
            ToolMessage(
                content=json.dumps({"VCB": {"price": 95000, "ticker": "VCB"}}),
                tool_call_id="1",
                name="get_stock_price",
            ),
            AIMessage(content="Giá VCB là 95,000 [VCB: 95000, nguồn: get_stock_price]"),
            AIMessage(content="Giá VCB là 95,000 [VCB: 95000, nguồn: get_stock_price]"),
        ])

        result = agent._verify_facts_node(state)
        assert len(result.get("messages", [])) == 0

    def test_verify_facts_warns_on_mismatch(self, mock_tools):
        agent = _build_agent(mock_tools, MagicMock())
        state = _make_state([
            HumanMessage(content="Giá VCB?"),
            AIMessage(content="", tool_calls=[{"name": "get_stock_price", "args": {}, "id": "1"}]),
            ToolMessage(
                content=json.dumps({"VCB": {"price": 95000, "ticker": "VCB"}}),
                tool_call_id="1",
                name="get_stock_price",
            ),
            AIMessage(content="Giá VCB là 100,000 [VCB: 100000, nguồn: get_stock_price]"),
            AIMessage(content="Giá VCB là 100,000 [VCB: 100000, nguồn: get_stock_price]"),
        ])

        result = agent._verify_facts_node(state)
        msgs = result.get("messages", [])
        assert len(msgs) > 0
        assert "Cảnh báo" in msgs[0].content


# =========================================================================
# Tests — guardrails integration
# =========================================================================


class TestGuardrailsIntegration:
    """Verify _final_answer_node delegates to OutputGuardrails correctly."""

    def test_graceful_degradation_no_guardrails(self, mock_tools, mock_llm_with_tool_call):
        agent = _build_agent(mock_tools, mock_llm_with_tool_call)
        agent._output_guardrails = None
        ai = AIMessage(content="Giá VCB là 95,000")
        state = _make_state([ai])

        result = agent._final_answer_node(state)
        assert result["messages"][0].content == "Giá VCB là 95,000"


# =========================================================================
# Tests — graph wiring (structure, not execution)
# =========================================================================


class TestGraphStructure:
    """Verify the compiled graph has the expected nodes and edges."""

    def test_graph_has_all_nodes(self, mock_tools, mock_llm_with_tool_call):
        agent = _build_agent(mock_tools, mock_llm_with_tool_call)
        expected = {"reason", "action", "final_answer", "verify_facts"}
        assert expected.issubset(set(agent.app.nodes.keys()))

    def test_graph_has_stream(self, mock_tools, mock_llm_with_tool_call):
        agent = _build_agent(mock_tools, mock_llm_with_tool_call)
        assert hasattr(agent.app, "stream")

    def test_should_continue_to_action(self, mock_tools, mock_llm_with_tool_call):
        agent = _build_agent(mock_tools, mock_llm_with_tool_call)
        state = _make_state(
            [AIMessage(content="", tool_calls=[{"name": "t", "args": {}, "id": "1"}])],
            next_tool_call=[{"name": "t", "args": {}, "id": "1"}],
        )
        assert agent._should_continue(state) == "continue"

    def test_should_continue_to_end(self, mock_tools, mock_llm_with_tool_call):
        agent = _build_agent(mock_tools, mock_llm_with_tool_call)
        state = _make_state([AIMessage(content="done")], next_tool_call=None)
        assert agent._should_continue(state) == "end"

    def test_should_continue_empty_list(self, mock_tools, mock_llm_with_tool_call):
        agent = _build_agent(mock_tools, mock_llm_with_tool_call)
        state = _make_state([], next_tool_call=[])
        assert agent._should_continue(state) == "end"
