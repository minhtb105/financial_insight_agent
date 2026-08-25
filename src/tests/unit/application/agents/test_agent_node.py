"""Unit tests for StockAgent graph nodes — Reason / Action pattern."""

from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage

from application.agents.agent import StockAgent, AgentState
from infrastructure.llm.llm_provider import LLMUnavailableError


def _make_agent(llm_available=True):
    with (
        patch("application.agents.agent.LLMProvider") as mock_provider_cls,
        patch("application.agents.agent.ALL_TOOLS", []),
        patch("application.agents.agent.CustomToolNode"),
        patch("application.agents.agent.ResponseSynthesizer"),
        patch("application.agents.agent.HybridQuerySplitter"),
    ):
        if llm_available:
            mock_llm = MagicMock()
            mock_provider = MagicMock()
            mock_provider.get_tool_calling_llm.return_value = mock_llm
            mock_provider_cls.return_value = mock_provider
        else:
            mock_provider_cls.side_effect = LLMUnavailableError("No LLM")

        agent = StockAgent()
        if llm_available:
            agent.llm = mock_llm
        else:
            agent.llm = None
        return agent


def _state(messages=None, iterations=0, original_query="test query", request_id="test-rid", next_tool_call=None):
    return AgentState(
        messages=messages or [],
        iterations=iterations,
        original_query=original_query,
        request_id=request_id,
        next_tool_call=next_tool_call,
    )


# --- _should_continue ---

def test_should_continue_no_next_tool_call():
    assert StockAgent._should_continue(_state([])) == "end"


def test_should_continue_with_next_tool_call():
    state = _state(
        [AIMessage(content="", tool_calls=[{"name": "t", "args": {}, "id": "1"}])],
        next_tool_call=[{"name": "t", "args": {}, "id": "1"}],
    )
    assert StockAgent._should_continue(state) == "continue"


def test_should_continue_empty_list():
    state = _state(next_tool_call=[])
    assert StockAgent._should_continue(state) == "end"


# --- _reason_node ---

def test_reason_node_llm_none():
    agent = _make_agent(llm_available=False)
    result = agent._reason_node(_state([HumanMessage(content="test")]))
    assert "Hệ thống AI đang không khả dụng" in result["messages"][0].content
    assert result["next_tool_call"] is None


@patch("application.agents.agent.MAX_ITERATIONS", 3)
def test_reason_node_max_iterations():
    agent = _make_agent(llm_available=True)
    result = agent._reason_node(_state([HumanMessage(content="test")], iterations=3))
    assert "Đã đạt giới hạn" in result["messages"][0].content
    assert result["next_tool_call"] is None


def test_reason_node_llm_call_fails():
    agent = _make_agent(llm_available=True)
    agent.llm.invoke.side_effect = Exception("API error")
    result = agent._reason_node(_state([HumanMessage(content="test")]))
    assert "Xin lỗi, đã xảy ra lỗi" in result["messages"][0].content
    assert result["next_tool_call"] is None


def test_reason_node_success_with_tool_calls():
    agent = _make_agent(llm_available=True)
    mock_response = AIMessage(content="", tool_calls=[{"name": "get_price", "args": {"ticker": "VCB"}, "id": "1"}])
    agent.llm.invoke.return_value = mock_response
    result = agent._reason_node(_state([HumanMessage(content="test")]))
    assert result["messages"][0] is mock_response
    assert result["iterations"] == 1
    assert result["next_tool_call"] == [{"name": "get_price", "args": {"ticker": "VCB"}, "id": "1", "type": "tool_call"}]
    agent.llm.invoke.assert_called_once()


def test_reason_node_success_no_tool_calls():
    agent = _make_agent(llm_available=True)
    mock_response = AIMessage(content="final answer")
    agent.llm.invoke.return_value = mock_response
    result = agent._reason_node(_state([HumanMessage(content="test")]))
    assert result["messages"][0] is mock_response
    assert result["iterations"] == 0
    assert result["next_tool_call"] is None


def test_reason_node_with_memory_context():
    agent = _make_agent(llm_available=True)
    mock_response = AIMessage(content="answer", tool_calls=[{"name": "t", "args": {}, "id": "1"}])
    agent.llm.invoke.return_value = mock_response
    state = _state([HumanMessage(content="test")])
    state["memory_context"] = "User previously asked about VCB"
    result = agent._reason_node(state)
    assert result["iterations"] == 1
    assert result["next_tool_call"] is not None


def test_reason_node_empty_llm_response():
    agent = _make_agent(llm_available=True)
    agent.llm.invoke.return_value = AIMessage(content="", tool_calls=[{"name": "t", "args": {}, "id": "1"}])
    result = agent._reason_node(_state([HumanMessage(content="test")]))
    assert result["messages"][0].content == ""
    assert result["iterations"] == 1
    assert result["next_tool_call"] is not None


# --- _action_node (reads from next_tool_call, uses execute_one) ---

def test_action_node_no_next_tool_call():
    agent = _make_agent(llm_available=True)
    result = agent._action_node(_state(next_tool_call=None))
    assert result["next_tool_call"] is None
    assert result["messages"] == []


def test_action_node_empty_list():
    agent = _make_agent(llm_available=True)
    result = agent._action_node(_state(next_tool_call=[]))
    assert result["next_tool_call"] is None
    assert result["messages"] == []


def test_action_node_reads_next_tool_call():
    agent = _make_agent(llm_available=True)
    agent.tool_node.execute_one = MagicMock(return_value='{"price": 95000}')
    state = _state(
        [HumanMessage(content="test")],
        next_tool_call=[{"name": "get_price", "args": {"ticker": "VCB"}, "id": "1"}],
    )
    result = agent._action_node(state)

    assert result["next_tool_call"] is None
    assert len(result["messages"]) == 1
    tm = result["messages"][0]
    assert isinstance(tm, ToolMessage)
    assert '{"price": 95000}' in tm.content
    assert tm.tool_call_id == "1"
    assert tm.name == "get_price"

    # Must call execute_one, NOT __call__
    agent.tool_node.execute_one.assert_called_once_with(
        {"name": "get_price", "args": {"ticker": "VCB"}, "id": "1"},
        set(),
        {},
        {},
    )


def test_action_node_passes_history_cache_retries():
    agent = _make_agent(llm_available=True)
    agent.tool_node.execute_one = MagicMock(return_value='{"price": 95000}')
    state = _state(
        next_tool_call=[{"name": "get_price", "args": {"ticker": "VCB"}, "id": "1"}],
    )
    state["tool_call_history"] = ["prev_fingerprint"]
    state["tool_call_cache"] = {"prev_fingerprint": "old_data"}
    state["tool_call_retries"] = {"prev_fingerprint": 1}

    result = agent._action_node(state)

    # Must propagate history/cache/retries to execute_one
    call_kwargs = agent.tool_node.execute_one.call_args
    assert call_kwargs[0][1] == {"prev_fingerprint"}  # history as set
    assert call_kwargs[0][2] == {"prev_fingerprint": "old_data"}  # cache
    assert call_kwargs[0][3] == {"prev_fingerprint": 1}  # retries

    # Must return updated state
    assert result["tool_call_history"] is not None
    assert result["tool_call_cache"] is not None
    assert result["tool_call_retries"] is not None


def test_action_node_multiple_tool_calls():
    agent = _make_agent(llm_available=True)

    def side_effect(tc, h, c, r):
        return f'result-for-{tc["name"]}'

    agent.tool_node.execute_one = MagicMock(side_effect=side_effect)
    state = _state(
        next_tool_call=[
            {"name": "tool_a", "args": {}, "id": "1"},
            {"name": "tool_b", "args": {}, "id": "2"},
        ],
    )

    result = agent._action_node(state)

    assert result["next_tool_call"] is None
    assert len(result["messages"]) == 2
    assert result["messages"][0].content == "result-for-tool_a"
    assert result["messages"][1].content == "result-for-tool_b"
    assert agent.tool_node.execute_one.call_count == 2


# --- _final_answer_node ---

@patch("application.agents.agent.get_output_guardrails")
def test_final_answer_all_tools_error(mock_get_gr):
    mock_gr = MagicMock()
    mock_gr.validate_tool_results.return_value = "All tools failed"
    mock_get_gr.return_value = mock_gr
    agent = _make_agent(llm_available=True)
    msgs = [ToolMessage(content="TOOL_ERR# failed", tool_call_id="1")]
    result = agent._final_answer_node(_state(msgs))
    assert "All tools failed" in result["messages"][0].content


@patch("application.agents.agent.get_output_guardrails")
def test_final_answer_no_ai_message(mock_get_gr):
    mock_gr = MagicMock()
    mock_gr.validate_tool_results.return_value = None
    mock_get_gr.return_value = mock_gr
    agent = _make_agent(llm_available=True)
    msgs = [ToolMessage(content="some data", tool_call_id="1")]
    result = agent._final_answer_node(_state(msgs))
    assert "Không thể tạo câu trả lời" in result["messages"][0].content


@patch("application.agents.agent.get_output_guardrails")
def test_final_answer_validation_fail(mock_get_gr):
    mock_gr = MagicMock()
    mock_gr.validate_tool_results.return_value = None
    mock_gr.validate_response.return_value = MagicMock(
        status="FAIL",
        issues=[],
        processed_query={"sanitized_response": "sanitized answer"},
    )
    mock_get_gr.return_value = mock_gr
    agent = _make_agent(llm_available=True)
    msgs = [AIMessage(content="original answer", tool_calls=[])]
    result = agent._final_answer_node(_state(msgs))
    assert "sanitized answer" in result["messages"][0].content


@patch("application.agents.agent.get_output_guardrails")
def test_final_answer_validation_pass(mock_get_gr):
    mock_gr = MagicMock()
    mock_gr.validate_tool_results.return_value = None
    mock_gr.validate_response.return_value = MagicMock(
        status="PASS",
        issues=[],
        processed_query={"sanitized_response": "normal answer"},
    )
    mock_get_gr.return_value = mock_gr
    agent = _make_agent(llm_available=True)
    msgs = [AIMessage(content="normal answer", tool_calls=[])]
    result = agent._final_answer_node(_state(msgs))
    assert result["messages"][0].content == "normal answer"


@patch("application.agents.agent.get_output_guardrails")
def test_final_answer_warning_status(mock_get_gr):
    mock_gr = MagicMock()
    mock_gr.validate_tool_results.return_value = None
    mock_gr.validate_response.return_value = MagicMock(
        status="WARNING",
        issues=["Potential hallucination"],
        processed_query={"sanitized_response": "answer after warning"},
    )
    mock_get_gr.return_value = mock_gr
    agent = _make_agent(llm_available=True)
    msgs = [AIMessage(content="answer", tool_calls=[])]
    result = agent._final_answer_node(_state(msgs))
    assert result["messages"][0].content == "answer"


@patch("application.agents.agent.get_output_guardrails")
def test_final_answer_empty_messages(mock_get_gr):
    mock_gr = MagicMock()
    mock_gr.validate_tool_results.return_value = None
    mock_get_gr.return_value = mock_gr
    agent = _make_agent(llm_available=True)
    result = agent._final_answer_node(_state([]))
    assert "Không thể tạo câu trả lời" in result["messages"][0].content
