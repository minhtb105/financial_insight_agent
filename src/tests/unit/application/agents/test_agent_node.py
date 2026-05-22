"""Unit tests for StockAgent graph nodes."""

from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage, ToolMessage, HumanMessage

from application.agents.agent import StockAgent, AgentState
from infrastructure.llm.llm_provider import LLMUnavailableError


def _make_agent(llm_available=True):
    with (
        patch("application.agents.agent.LLMProvider") as mock_provider_cls,
        patch("application.agents.agent.ALL_TOOLS", []),
        patch("application.agents.agent.ToolNode"),
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


def _state(messages=None, iterations=0, original_query="test query", request_id="test-rid"):
    return AgentState(
        messages=messages or [],
        iterations=iterations,
        original_query=original_query,
        request_id=request_id,
    )


# --- _should_continue ---

def test_should_continue_empty():
    assert StockAgent._should_continue(_state([])) == "end"


def test_should_continue_ai_with_tool_calls():
    msg = AIMessage(content="", tool_calls=[{"name": "t", "args": {}, "id": "1"}])
    assert StockAgent._should_continue(_state([msg])) == "continue"


def test_should_continue_ai_no_tool_calls():
    msg = AIMessage(content="final")
    assert StockAgent._should_continue(_state([msg])) == "end"


def test_should_continue_tool_message():
    msg = ToolMessage(content="result", tool_call_id="1")
    assert StockAgent._should_continue(_state([msg])) == "end"


def test_should_continue_ai_with_content_and_tool_calls():
    msg = AIMessage(content="let me look that up", tool_calls=[{"name": "t", "args": {}, "id": "1"}])
    assert StockAgent._should_continue(_state([msg])) == "continue"


# --- _agent_node ---

def test_agent_node_llm_none():
    agent = _make_agent(llm_available=False)
    result = agent._agent_node(_state([HumanMessage(content="test")]))
    assert "Hệ thống AI đang không khả dụng" in result["messages"][0].content
    assert result["iterations"] == 1


@patch("application.agents.agent.MAX_ITERATIONS", 3)
def test_agent_node_max_iterations():
    agent = _make_agent(llm_available=True)
    result = agent._agent_node(_state([HumanMessage(content="test")], iterations=3))
    assert "Đã đạt giới hạn" in result["messages"][0].content


def test_agent_node_llm_call_fails():
    agent = _make_agent(llm_available=True)
    agent.llm.invoke.side_effect = Exception("API error")
    result = agent._agent_node(_state([HumanMessage(content="test")]))
    assert "Xin lỗi, đã xảy ra lỗi" in result["messages"][0].content
    assert result["iterations"] == 1


def test_agent_node_success():
    agent = _make_agent(llm_available=True)
    mock_response = AIMessage(content="some data", tool_calls=[])
    agent.llm.invoke.return_value = mock_response
    result = agent._agent_node(_state([HumanMessage(content="test")]))
    assert result["messages"][0] is mock_response
    assert result["iterations"] == 1
    agent.llm.invoke.assert_called_once()


def test_agent_node_with_memory_context():
    agent = _make_agent(llm_available=True)
    mock_response = AIMessage(content="answer", tool_calls=[])
    agent.llm.invoke.return_value = mock_response
    state = _state([HumanMessage(content="test")])
    state["memory_context"] = "User previously asked about VCB"
    result = agent._agent_node(state)
    assert result["iterations"] == 1


def test_agent_node_empty_llm_response():
    agent = _make_agent(llm_available=True)
    agent.llm.invoke.return_value = AIMessage(content="", tool_calls=[])
    result = agent._agent_node(_state([HumanMessage(content="test")]))
    assert result["messages"][0].content == ""
    assert result["iterations"] == 1


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
