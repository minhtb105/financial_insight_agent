import time
import uuid
from dotenv import load_dotenv
from typing import Any, Dict, TypedDict, Annotated, Sequence, Optional
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    BaseMessage,
    ToolMessage
)
from langgraph.graph.message import add_messages
from infrastructure.llm.nlp_parser import QueryParser
from infrastructure.llm.llm_provider import LLMProvider
from application.agents.tool_registry import TOOL_REGISTRY
from application.agents.tool_router import route_to_tool
from application.agents.response_formatter import ResponseFormatter
from infrastructure.resilience.guardrails import (
    get_input_guardrails,
    get_step_guardrails,
    get_output_guardrails,
    ValidationResult
)
from infrastructure.cache import get_cache_manager
from infrastructure.observability import get_logger
from infrastructure.observability.logging.logger import request_id_var

ALL_TOOLS = list(TOOL_REGISTRY.values())


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    parsed_query: Dict[str, Any]
    tool_output: Dict[str, Any]
    confidence: float
    selected_tool: Optional[str]
    validation_error: Optional[str]
    retry_count: int


class StockAgent:
    def __init__(self, model="llama-3.1-8b-instant", parser=None):
        load_dotenv()
        get_cache_manager()
        self.formatter = ResponseFormatter()

        self.tools = list(TOOL_REGISTRY.values())

        self.parser = parser or QueryParser(model=model)

        graph = StateGraph(AgentState)

        def parser_node(state: AgentState) -> AgentState:
            node_logger = get_logger("agent.parser_node")
            rid = request_id_var.get() or "unknown"
            request_id_var.set(rid)
            start = time.time()

            user_msg = state.get("messages")[-1].content
            if not user_msg:
                node_logger.error("Missing user query in state", request_id=rid)
                raise ValueError(f"[parser_node] request_id={rid} | Missing user query in state")

            validation_error = state.get("validation_error")
            retry_count = state.get("retry_count", 0)
            if validation_error and retry_count < 2:
                error_context = f"\n[Previous attempt failed: {validation_error}. Please fix the query parameters.]"
                user_msg = user_msg + error_context
                retry_count += 1
                node_logger.info("Retrying parser with error context", extra={
                    "request_id": rid,
                    "retry_count": retry_count,
                    "validation_error": validation_error,
                })

            node_logger.info("Parsing query", extra={"query": user_msg, "request_id": rid})
            try:
                parsed, confidence = self.parser.parse_with_confidence(user_msg)
            except Exception as e:
                node_logger.error("Parser call failed", extra={
                    "request_id": rid,
                    "error_type": type(e).__name__,
                    "error": str(e),
                })
                raise ValueError(f"[parser_node] request_id={rid} | Parser call failed: {e}") from e

            step_guardrails = get_step_guardrails()
            validation_result = step_guardrails.validate_parser_output(parsed)
            if validation_result.status == ValidationResult.FAIL:
                error_msg = f"Parser validation failed: {'; '.join(issue.message for issue in validation_result.issues)}"
                node_logger.error(error_msg, extra={
                    "request_id": rid,
                    "parsed": parsed,
                    "confidence": confidence,
                })
                raise ValueError(f"[parser_node] request_id={rid} | {error_msg}")

            node_logger.info("Parser completed", extra={
                "request_id": rid,
                "query_type": parsed.get("query_type", "unknown"),
                "confidence": confidence,
                "duration_ms": round((time.time() - start) * 1000, 2),
            })

            state["parsed_query"] = parsed
            state["confidence"] = confidence

            ai_msg = AIMessage(
                content=f"Parser result (confidence: {confidence:.2f}): {parsed}. Now selecting appropriate tool...",
            )

            return {
                "messages": [ai_msg],
                "parsed_query": parsed,
                "confidence": confidence,
                "validation_error": None,
                "retry_count": retry_count,
            }

        graph.add_node("parser", parser_node)

        def tool_router_node(state: AgentState) -> dict:
            node_logger = get_logger("agent.tool_router")
            rid = request_id_var.get() or "unknown"
            request_id_var.set(rid)

            parsed = state.get("parsed_query", {})
            tickers = parsed.get("tickers", [])
            query_type = parsed.get("query_type", "")

            if not tickers:
                node_logger.warning("Validation failed: missing tickers", extra={
                    "request_id": rid,
                    "query_type": query_type,
                })
                return {"validation_error": "Missing tickers in parsed query"}

            if query_type == "ranking_query" and len(tickers) < 2:
                node_logger.warning("Validation failed: ranking_query needs >=2 tickers", extra={
                    "request_id": rid,
                    "query_type": query_type,
                    "tickers": tickers,
                })
                return {"validation_error": "ranking_query needs >= 2 tickers"}

            return {"validation_error": None}

        def should_retry(state: AgentState) -> str:
            if state.get("validation_error") and state.get("retry_count", 0) < 2:
                return "retry"
            return "execute"

        graph.add_node("tool_router", tool_router_node)

        def executor_node(state: AgentState) -> dict:
            node_logger = get_logger("agent.executor_node")
            rid = request_id_var.get() or "unknown"
            request_id_var.set(rid)
            start = time.time()

            parsed = state['parsed_query']
            confidence = state['confidence']
            query_type = parsed.get("query_type", "unknown")

            node_logger.info("Executor starting", extra={
                "request_id": rid,
                "query_type": query_type,
                "confidence": confidence,
            })

            step_guardrails = get_step_guardrails()
            tool_params = {"query": parsed}
            validation_result = step_guardrails.validate_tool_input(tool_params)
            if validation_result.status == ValidationResult.FAIL:
                error_msg = f"Tool input validation failed: {'; '.join(issue.message for issue in validation_result.issues)}"
                node_logger.error(error_msg, extra={
                    "request_id": rid,
                    "query_type": query_type,
                    "parsed": parsed,
                })
                raise ValueError(f"[executor_node] request_id={rid} | {error_msg}")

            tool_fn = TOOL_REGISTRY.get(query_type) or TOOL_REGISTRY["price_query"]
            tool_name = tool_fn.name

            ai_msg = AIMessage(
                content=f"Executor routed to tool for query_type={query_type} (confidence: {confidence:.2f})",
                tool_calls=[{
                    "name": tool_name,
                    "args": {"query": parsed},
                    "id": str(uuid.uuid4()),
                    "type": "tool_call",
                }],
            )

            node_logger.info("Executor completed", extra={
                "request_id": rid,
                "query_type": query_type,
                "duration_ms": round((time.time() - start) * 1000, 2),
            })

            return {
                "messages": [ai_msg],
                "selected_tool": tool_name,
                "parsed_query": parsed,
                "confidence": confidence,
                "retry_count": state.get("retry_count", 0),
                "validation_error": state.get("validation_error"),
            }

        graph.add_node("executor", executor_node)
        graph.add_node("tools", ToolNode(ALL_TOOLS))

        def final_answer(state):
            node_logger = get_logger("agent.final_answer")
            rid = request_id_var.get() or "unknown"
            request_id_var.set(rid)
            start = time.time()

            tool_output = None
            parsed_query = state.get("parsed_query", {})
            original_query = state["messages"][0].content if state["messages"] else ""
            confidence = state.get("confidence", 0.0)
            query_type = parsed_query.get("query_type", "price_query")

            node_logger.info("Final answer formatting", extra={
                "request_id": rid,
                "query_type": query_type,
                "confidence": confidence,
            })

            step_guardrails = get_step_guardrails()
            for m in reversed(state["messages"]):
                if isinstance(m, ToolMessage):
                    tool_output = m.content
                    break

            if tool_output:
                validation_result = step_guardrails.validate_tool_output(tool_output)
                if validation_result.status == ValidationResult.FAIL:
                    node_logger.warning("Tool output validation failed", extra={
                        "request_id": rid,
                        "issues": [str(i) for i in validation_result.issues],
                    })

            response_text = self.formatter.format(
                query_type=query_type,
                original_query=original_query,
                raw_output=tool_output or "",
                confidence=confidence,
            )

            response = AIMessage(content=response_text)

            output_guardrails = get_output_guardrails()
            validation_result = output_guardrails.validate_response(response.content, original_query)

            if validation_result.status == ValidationResult.FAIL:
                node_logger.error("Output validation failed", extra={
                    "request_id": rid,
                    "issues": [str(i) for i in validation_result.issues],
                })
                sanitized_response = validation_result.processed_query["sanitized_response"]
                response.content = sanitized_response
            elif validation_result.status == ValidationResult.WARNING:
                node_logger.warning("Output anomalies detected", extra={
                    "request_id": rid,
                    "issues": [str(i) for i in validation_result.issues],
                })

            node_logger.info("Final answer completed", extra={
                "request_id": rid,
                "duration_ms": round((time.time() - start) * 1000, 2),
            })

            return {
                "messages": [response],
                "tool_output": tool_output or {},
                "selected_tool": state.get("selected_tool"),
                "validation_error": state.get("validation_error"),
                "retry_count": state.get("retry_count", 0),
            }

        graph.add_node("final_answer", final_answer)

        graph.set_entry_point("parser")
        graph.add_edge("parser", "tool_router")
        graph.add_conditional_edges(
            "tool_router",
            should_retry,
            {
                "execute": "executor",
                "retry": "parser",
            },
        )
        graph.add_edge("executor", "tools")
        graph.add_edge("tools", "final_answer")
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
                print(f"\nTOOL RESULT: {message.content}")

    def _resolve_request_id(self, provided: Optional[str] = None) -> str:
        if provided:
            return provided
        existing = request_id_var.get()
        if existing:
            return existing
        return str(uuid.uuid4())

    def run(self, query: str, request_id: Optional[str] = None):
        rid = self._resolve_request_id(request_id)
        request_id_var.set(rid)

        start_time = time.time()
        init_state = {
            "messages": [HumanMessage(content=query)],
            "parsed_query": {},
            "tool_output": {},
            "confidence": 0.0,
            "selected_tool": None,
            "validation_error": None,
            "retry_count": 0,
        }
        final_response = ""
        self._last_parsed_query = {}
        self._last_confidence = 0.0
        for step in self.app.stream(init_state, stream_mode="values"):
            if "messages" in step:
                self.print_messages(step["messages"])
                if step["messages"] and isinstance(step["messages"][-1], AIMessage):
                    final_response = step["messages"][-1].content
            if "parsed_query" in step and step["parsed_query"]:
                self._last_parsed_query = step["parsed_query"]
            if "confidence" in step:
                self._last_confidence = step["confidence"]

        end_time = time.time()
        latency = end_time - start_time
        print(f"[LATENCY] Agent xử lý mất {latency:.3f} giây.")
        return final_response

    def run_stream(self, query: str, request_id: Optional[str] = None):
        rid = self._resolve_request_id(request_id)
        request_id_var.set(rid)

        start_time = time.time()
        init_state = {
            "messages": [HumanMessage(content=query)],
            "parsed_query": {},
            "tool_output": {},
            "confidence": 0.0,
            "selected_tool": None,
            "validation_error": None,
            "retry_count": 0,
        }

        self._last_parsed_query = {}
        self._last_confidence = 0.0
        for step in self.app.stream(init_state, stream_mode="values"):
            if "messages" in step:
                self.print_messages(step["messages"])
                if step["messages"] and isinstance(step["messages"][-1], AIMessage):
                    content = step["messages"][-1].content
                    for i in range(0, len(content), 50):
                        chunk = content[i:i+50]
                        if chunk:
                            yield chunk
            if "parsed_query" in step and step["parsed_query"]:
                self._last_parsed_query = step["parsed_query"]
            if "confidence" in step:
                self._last_confidence = step["confidence"]

        end_time = time.time()
        latency = end_time - start_time
        print(f"[LATENCY] Agent streaming mất {latency:.3f} giây.")


def build_graph():
    agent = StockAgent()
    return agent.app


graph = build_graph()
