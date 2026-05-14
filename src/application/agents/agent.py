import time
import uuid
from dotenv import load_dotenv
from typing import Any, Dict, TypedDict, Annotated, Sequence, Optional, Literal
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    BaseMessage,
    ToolMessage,
    SystemMessage,
)
from langgraph.graph.message import add_messages
from infrastructure.llm.llm_provider import LLMProvider
from application.agents.tool_registry import ALL_TOOLS
from infrastructure.resilience.guardrails import (
    get_output_guardrails,
)
from infrastructure.observability import get_logger
from infrastructure.observability.logging.logger import request_id_var

logger = get_logger("agent.StockAgent")

MAX_ITERATIONS = 10

SYSTEM_PROMPT = """Bạn là một agent chứng khoán chuyên nghiệp. Nhiệm vụ của bạn là trả lời câu hỏi của người dùng về cổ phiếu, công ty và dữ liệu tài chính tại thị trường Việt Nam.

Bạn có các công cụ sau để tra cứu thông tin. Hãy sử dụng chúng khi cần thiết:

CÁC LOẠI TRUY VẤN:
1. price_query: Lấy dữ liệu OHLCV (open, close, high, low, volume) cho 1+ tickers. Input: tickers (bắt buộc), requested_field, thời gian.
2. indicator_query: Tính chỉ báo kỹ thuật SMA/RSI/MACD. Input: tickers (bắt buộc), requested_field, indicator_params, thời gian.
3. comparison_query: So sánh nhóm chính vs tham chiếu. Input: tickers (bắt buộc), compare_with (bắt buộc), requested_field, thời gian.
4. ranking_query: Xếp hạng >=2 tickers theo field. Input: tickers (bắt buộc, >=2), requested_field, aggregate, thời gian.
5. aggregate_query: Tính mean/sum/median/std/min/max. Input: tickers (bắt buộc), requested_field, aggregate_fn, thời gian.
6. financial_ratio_query: Lấy PE, PB, ROE, EPS, debt_to_equity. Input: tickers (bắt buộc), requested_field.
7. company_query: Lấy cổ đông, ban lãnh đạo, công ty con. Input: tickers (bắt buộc), requested_field.
8. news_sentiment_query: Lấy tin tức, sentiment, social volume. Input: tickers (bắt buộc), requested_field.
9. portfolio_query: Quản lý danh mục. Input: requested_field, portfolio {ticker: số_lượng}.
10. alert_query: Cảnh báo giá khi ticker vượt ngưỡng. Input: tickers (bắt buộc), threshold (bắt buộc), condition.
11. forecast_query: Dự báo giá cổ phiếu. Input: tickers (bắt buộc), timeframe.
12. sector_query: Phân tích hiệu suất cổ phiếu theo ngành. Input: sector (bắt buộc), metric.

QUY TẮC:
1. Gọi công cụ phù hợp dựa trên câu hỏi của người dùng.
2. Nếu câu hỏi cần nhiều dữ liệu, hãy gọi nhiều công cụ tuần tự.
3. Sau khi nhận kết quả từ công cụ, tổng hợp thành câu trả lời rõ ràng bằng tiếng Việt.
4. Dừng lại khi đã có câu trả lời hoàn chỉnh.
5. Nếu công cụ trả về lỗi (bắt đầu bằng TOOL_ERR#), hãy giải thích lỗi cho người dùng và dừng lại.
6. Hãy ngắn gọn nhưng đầy đủ thông tin. Đưa ra số liệu cụ thể khi có thể."""


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    parsed_query: Dict[str, Any]
    tool_output: Dict[str, Any]
    confidence: float
    selected_tool: Optional[str]
    validation_error: Optional[str]
    retry_count: int
    iterations: int


class StockAgent:
    def __init__(self, model="llama-3.1-8b-instant"):
        load_dotenv()

        self.llm_provider = LLMProvider()
        self.tools = ALL_TOOLS
        self.tool_node = ToolNode(self.tools)
        self.llm = self.llm_provider.get_tool_calling_llm(self.tools)

        graph = StateGraph(AgentState)

        def agent_node(state: AgentState) -> dict:
            node_logger = get_logger("agent.agent_node")
            rid = request_id_var.get() or "unknown"
            request_id_var.set(rid)
            start = time.time()

            iterations = state.get("iterations", 0)
            if iterations >= MAX_ITERATIONS:
                node_logger.warning("Max iterations reached", extra={
                    "request_id": rid,
                    "iterations": iterations,
                })
                return {
                    "messages": [AIMessage(
                        content="Đã đạt giới hạn số lần xử lý. Vui lòng thử lại với câu hỏi đơn giản hơn."
                    )],
                    "iterations": iterations,
                }

            messages = list(state["messages"])

            if not any(isinstance(m, SystemMessage) for m in messages):
                messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages

            node_logger.info("Agent node calling LLM", extra={
                "request_id": rid,
                "message_count": len(messages),
                "iterations": iterations,
            })

            try:
                response = self.llm.invoke(messages)
            except Exception as e:
                node_logger.error("Agent LLM call failed", extra={
                    "request_id": rid,
                    "error_type": type(e).__name__,
                    "error": str(e),
                })
                return {
                    "messages": [AIMessage(
                        content="Xin lỗi, đã xảy ra lỗi khi xử lý yêu cầu của bạn. Vui lòng thử lại sau."
                    )],
                    "iterations": iterations + 1,
                }

            node_logger.info("Agent node completed", extra={
                "request_id": rid,
                "has_tool_calls": bool(response.tool_calls),
                "tool_calls": [t["name"] for t in (response.tool_calls or [])],
                "duration_ms": round((time.time() - start) * 1000, 2),
            })

            return {
                "messages": [response],
                "iterations": iterations + 1,
            }

        graph.add_node("agent", agent_node)
        graph.add_node("tools", self.tool_node)

        def final_answer_node(state: AgentState) -> dict:
            node_logger = get_logger("agent.final_answer")
            rid = request_id_var.get() or "unknown"
            request_id_var.set(rid)

            messages = state.get("messages", [])
            original_query = messages[0].content if messages else ""

            last_ai = None
            for m in reversed(messages):
                if isinstance(m, AIMessage) and not m.tool_calls:
                    last_ai = m
                    break

            if not last_ai:
                last_ai = AIMessage(content="Không thể tạo câu trả lời.")

            response = last_ai

            output_guardrails = get_output_guardrails()
            validation_result = output_guardrails.validate_response(
                response.content, original_query
            )

            if validation_result.status == "FAIL":
                node_logger.error("Output validation failed", extra={
                    "request_id": rid,
                    "issues": [str(i) for i in validation_result.issues],
                })
                sanitized_response = validation_result.processed_query["sanitized_response"]
                response = AIMessage(content=sanitized_response)
            elif validation_result.status == "WARNING":
                node_logger.warning("Output anomalies detected", extra={
                    "request_id": rid,
                    "issues": [str(i) for i in validation_result.issues],
                })

            return {"messages": [response]}

        graph.add_node("final_answer", final_answer_node)

        def should_continue(state: AgentState) -> Literal["continue", "end"]:
            messages = state["messages"]
            if not messages:
                return "end"
            last_message = messages[-1]
            if isinstance(last_message, AIMessage) and last_message.tool_calls:
                return "continue"
            return "end"

        graph.set_entry_point("agent")
        graph.add_conditional_edges(
            "agent",
            should_continue,
            {
                "continue": "tools",
                "end": "final_answer",
            },
        )
        graph.add_edge("tools", "agent")
        graph.add_edge("final_answer", END)

        self.app = graph.compile(
            checkpointer=None,
            interrupt_before=None,
        )

    def print_messages(self, messages):
        if not messages:
            return
        for message in messages[-3:]:
            if isinstance(message, ToolMessage):
                logger.info("Tool result", extra={"content": message.content})

    def _resolve_request_id(self, provided: Optional[str] = None) -> str:
        if provided:
            return provided
        existing = request_id_var.get()
        if existing:
            return existing
        return str(uuid.uuid4())

    def _execute_graph(self, query: str, rid: str) -> str:
        request_id_var.set(rid)
        init_state = {
            "messages": [HumanMessage(content=query)],
            "parsed_query": {},
            "tool_output": {},
            "confidence": 0.0,
            "selected_tool": None,
            "validation_error": None,
            "retry_count": 0,
            "iterations": 0,
        }
        final_response = ""
        try:
            for step in self.app.stream(init_state, stream_mode="values"):
                if "messages" in step:
                    self.print_messages(step["messages"])
                    if step["messages"] and isinstance(step["messages"][-1], AIMessage):
                        final_response = step["messages"][-1].content
                if "parsed_query" in step and step["parsed_query"]:
                    self._last_parsed_query = step["parsed_query"]
                if "confidence" in step:
                    self._last_confidence = step["confidence"]
        except Exception as e:
            agent_logger = get_logger("agent._execute_graph")
            agent_logger.exception("Agent execution failed", extra={
                "request_id": rid, "error": str(e)
            })
            final_response = "Xin lỗi, đã xảy ra lỗi trong quá trình xử lý. Vui lòng thử lại sau."
        return final_response

    def run(self, query: str, request_id: Optional[str] = None):
        rid = self._resolve_request_id(request_id)
        request_id_var.set(rid)
        start_time = time.time()
        self._last_parsed_query = {}
        self._last_confidence = 0.0

        result = self._execute_graph(query, rid)

        latency = time.time() - start_time
        logger.info("Agent run complete", extra={
            "request_id": rid,
            "latency_ms": round(latency * 1000, 2),
        })
        return result

    def run_stream(self, query: str, request_id: Optional[str] = None):
        rid = self._resolve_request_id(request_id)
        request_id_var.set(rid)
        start_time = time.time()
        self._last_parsed_query = {}
        self._last_confidence = 0.0

        result = self._execute_graph(query, rid)
        for i in range(0, len(result), 50):
            chunk = result[i:i+50]
            if chunk:
                yield chunk

        latency = time.time() - start_time
        logger.info("Agent streaming complete", extra={
            "request_id": rid,
            "latency_ms": round(latency * 1000, 2),
        })


def build_graph():
    agent = StockAgent()
    return agent.app