"""
True tool-calling agent for Vietnamese stock market analysis.

Architecture:
  HumanMessage → [HybridQuerySplitter] → sub-queries
  Each sub-query:  agent_node ↔ tools ↔ agent_node  (ReAct loop)
  Results merged → final_answer_node → guardrails

The LLM autonomously decides which tools to call and what arguments to pass.
No deterministic classifier / extractor pipeline is involved.
"""

import time
import uuid
from dotenv import load_dotenv
from typing import TypedDict, Annotated, Literal
from collections.abc import Sequence
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import (
    HumanMessage,
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    ToolMessage,
    SystemMessage,
)
from langgraph.graph.message import add_messages
from infrastructure.llm.llm_provider import LLMProvider, LLMUnavailableError
from infrastructure.observability import get_logger
from infrastructure.observability.logging.logger import request_id_var
from application.agents.tool_registry import ALL_TOOLS
from application.agents.hybrid_splitter import HybridQuerySplitter
from application.agents.multi_query_runner import run_queries_parallel
from application.agents.response_synthesizer import ResponseSynthesizer
from infrastructure.guardrails.output_guardrails import get_output_guardrails
from infrastructure.memory.memory_manager import get_memory_manager
from shared.utils.env_helpers import parse_int_env
from contextlib import suppress

logger = get_logger("agent.StockAgent")

MAX_ITERATIONS = parse_int_env("AGENT_MAX_ITERATIONS", 10)
AGENT_TIMEOUT_SECONDS = parse_int_env("AGENT_TIMEOUT_SECONDS", 120)

SYSTEM_PROMPT = """You are a professional stock analysis assistant for the Vietnamese market.

You have tools to query real data. Follow these rules:
1. Analyze the question and decide which tool to call with what arguments.
2. If multiple data is needed, call multiple tools in parallel or sequentially.
3. After receiving results, synthesize a clear answer in Vietnamese.
4. Include specific numbers and figures when data is available.
5. If the question is ambiguous (missing ticker, threshold, etc.), ask the user for clarification.
6. If a tool returns an error (prefixed with TOOL_ERR#), explain the error to the user and stop."""


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    iterations: int
    original_query: str
    request_id: str
    memory_context: str


class StockAgent:
    def __init__(self) -> None:
        load_dotenv()

        self.tools = ALL_TOOLS
        self.tool_node = ToolNode(self.tools)
        try:
            self.llm_provider = LLMProvider()
            self.splitter = HybridQuerySplitter(llm_provider=self.llm_provider)
            self.llm = self.llm_provider.get_tool_calling_llm(self.tools)
            self._synthesizer = ResponseSynthesizer(self.llm_provider)
        except LLMUnavailableError:
            logger.error("No LLM provider available — agent running in degraded mode")
            self.llm_provider = None
            self.splitter = None
            self.llm = None
            self._synthesizer = None
        except Exception:
            logger.exception("Unexpected agent init failure — starting in degraded mode")
            self.llm_provider = None
            self.splitter = None
            self.llm = None
            self._synthesizer = None

        self._output_guardrails = get_output_guardrails()

        graph = StateGraph(AgentState)
        graph.add_node("agent", self._agent_node)
        graph.add_node("tools", self.tool_node)
        graph.add_node("final_answer", self._final_answer_node)

        graph.set_entry_point("agent")
        graph.add_conditional_edges(
            "agent",
            self._should_continue,
            {"continue": "tools", "end": "final_answer"},
        )
        graph.add_edge("tools", "agent")
        graph.add_edge("final_answer", END)

        self.app = graph.compile(checkpointer=MemorySaver(), interrupt_before=None)

    # ------------------------------------------------------------------
    # Graph nodes
    # ------------------------------------------------------------------

    def _check_llm_available(self, node_logger, rid: str, iterations: int) -> dict | None:
        if self.llm is None:
            node_logger.error("LLM unavailable", extra={"request_id": rid})
            return {
                "messages": [
                    AIMessage(
                        content="Hệ thống AI đang không khả dụng do thiếu cấu hình API. Vui lòng kiểm tra OPENAI_API_KEY hoặc GROQ_API_KEY."
                    )
                ],
                "iterations": iterations,
            }
        return None

    def _check_max_iterations(self, node_logger, rid: str, iterations: int) -> dict | None:
        if iterations >= MAX_ITERATIONS:
            node_logger.warning(
                "Max iterations reached",
                extra={"request_id": rid, "iterations": iterations},
            )
            return {
                "messages": [
                    AIMessage(
                        content="Đã đạt giới hạn số lần xử lý. Vui lòng thử lại với câu hỏi đơn giản hơn."
                    )
                ],
                "iterations": iterations,
            }
        return None

    @staticmethod
    def _build_messages(state: AgentState) -> list:
        messages = list(state["messages"])
        memory_context = state.get("memory_context", "")
        if not any(isinstance(m, SystemMessage) for m in messages):
            content = SYSTEM_PROMPT
            if memory_context:
                content = f"{content}\n\nContext from past interactions:\n{memory_context}"
            messages = [SystemMessage(content=content), *messages]
        return messages

    def _invoke_llm(self, node_logger, messages: list, rid: str) -> tuple:
        node_logger.info(
            "Agent node calling LLM",
            extra={
                "request_id": rid,
                "message_count": len(messages),
                "iterations": int(any(isinstance(m, ToolMessage) for m in messages)),
            },
        )
        try:
            response = self.llm.invoke(messages)
            return response, None
        except Exception as e:
            node_logger.error(
                "Agent LLM call failed",
                extra={
                    "request_id": rid,
                    "error_type": type(e).__name__,
                    "error": str(e),
                },
            )
            return None, e

    def _agent_node(self, state: AgentState) -> dict:
        node_logger = get_logger("agent.agent_node")
        rid = state.get("request_id") or request_id_var.get() or "unknown"
        start = time.time()
        iterations = state.get("iterations", 0)

        early = self._check_llm_available(node_logger, rid, iterations)
        if early:
            return early

        early = self._check_max_iterations(node_logger, rid, iterations)
        if early:
            return early

        messages = self._build_messages(state)
        response, err = self._invoke_llm(node_logger, messages, rid)
        if err:
            return {
                "messages": [
                    AIMessage(
                        content="Xin lỗi, đã xảy ra lỗi khi xử lý yêu cầu. Vui lòng thử lại sau."
                    )
                ],
                "iterations": iterations,
            }

        tool_calls_made = bool(response.tool_calls)
        tool_names = [t["name"] for t in (response.tool_calls or [])]
        node_logger.info(
            "Agent node completed",
            extra={
                "request_id": rid,
                "has_tool_calls": tool_calls_made,
                "tool_calls": tool_names,
                "duration_ms": round((time.time() - start) * 1000, 2),
            },
        )
        return {"messages": [response], "iterations": iterations + (1 if tool_calls_made else 0)}

    def _final_answer_node(self, state: AgentState) -> dict:
        node_logger = get_logger("agent.final_answer")
        rid = state.get("request_id") or request_id_var.get() or "unknown"

        messages = state.get("messages", [])
        original_query = state.get("original_query", "")

        tool_error = self._output_guardrails.validate_tool_results(messages) if self._output_guardrails else None
        if tool_error:
            node_logger.warning(
                "All tools returned errors",
                extra={
                    "request_id": rid,
                },
            )
            return {"messages": [AIMessage(content=tool_error)]}

        last_ai: AIMessage | None = None
        for m in reversed(messages):
            if isinstance(m, AIMessage) and not m.tool_calls:
                last_ai = m
                break

        if not last_ai:
            last_ai = AIMessage(content="Không thể tạo câu trả lời.")

        response = last_ai

        validation_result = self._output_guardrails.validate_response(response.content, original_query)

        if validation_result.status == "FAIL":
            node_logger.error(
                "Output validation failed",
                extra={
                    "request_id": rid,
                    "issues": [str(i) for i in validation_result.issues],
                },
            )
            sanitized = validation_result.processed_query.get(
                "sanitized_response", response.content
            )
            response = AIMessage(content=sanitized)
        elif validation_result.status == "WARNING":
            node_logger.warning(
                "Output anomalies detected",
                extra={
                    "request_id": rid,
                    "issues": [str(i) for i in validation_result.issues],
                },
            )

        return {"messages": [response]}

    @staticmethod
    def _should_continue(state: AgentState) -> Literal["continue", "end"]:
        messages = state["messages"]
        if not messages:
            return "end"
        last = messages[-1]
        if isinstance(last, AIMessage) and last.tool_calls:
            return "continue"
        return "end"

    # ------------------------------------------------------------------
    # Output guardrails helper
    # ------------------------------------------------------------------

    def _apply_output_guardrails(self, text: str, original_query: str) -> str:
        if self._output_guardrails is None:
            return text
        result = self._output_guardrails.validate_response(text, original_query)
        sanitized = result.processed_query.get("sanitized_response", text) if result.processed_query else text
        return sanitized

    # ------------------------------------------------------------------
    # Shared preamble: memory + split
    # ------------------------------------------------------------------

    def _prepare_and_split(self, query: str) -> tuple[str, list[str]]:
        """Build memory context and split query into sub-queries."""
        memory_context = self._build_memory_context(query)
        sub_queries = self.splitter.split(query) if self.splitter else [query]
        if not sub_queries:
            sub_queries = [query]
        return memory_context, sub_queries

    # ------------------------------------------------------------------
    # Multi-query fan-out via HybridQuerySplitter
    # ------------------------------------------------------------------

    def _build_memory_context(self, query: str) -> str:
        """Search past interactions for context relevant to the current query."""
        memory_mgr = get_memory_manager()
        if not memory_mgr:
            return ""
        try:
            mem_results = memory_mgr.search_memory(query=query, top_k=3)
            tier_data = mem_results.get("short_term", {})
            if not tier_data or "error" in tier_data:
                return ""
            snippets = []
            for ia in tier_data.get("interactions", [])[:2]:
                if isinstance(ia, dict):
                    uq = ia.get("user_query", "")
                    ar = ia.get("agent_response", "")
                    if uq and ar:
                        snippets.append(f"Q: {uq}\nA: {ar[:300]}")
            return "\n\n".join(snippets) if snippets else ""
        except Exception as mem_err:
            logger.warning("Failed to search memory", extra={"error": str(mem_err)})
            return ""

    def _run_single(self, query: str, rid: str, memory_context: str = "") -> str:
        with suppress(Exception):
            request_id_var.set(rid)
        try:
            init_state: AgentState = {
                "messages": [HumanMessage(content=query)],
                "iterations": 0,
                "original_query": query,
                "request_id": rid,
                "memory_context": memory_context,
            }
            final_response = ""
            deadline = time.time() + AGENT_TIMEOUT_SECONDS
            for step in self.app.stream(init_state, stream_mode="values"):
                if time.time() > deadline:
                    logger.warning(
                        "Agent execution timed out",
                        extra={"request_id": rid, "timeout": AGENT_TIMEOUT_SECONDS},
                    )
                    return "Xin lỗi, quá trình xử lý đã vượt quá thời gian cho phép. Vui lòng thử lại với câu hỏi đơn giản hơn."
                if "messages" in step:
                    msgs = step["messages"]
                    for m in msgs[-3:]:
                        if isinstance(m, ToolMessage):
                            logger.info(
                                "Tool result",
                                extra={
                                    "request_id": rid,
                                    "tool": m.name if hasattr(m, "name") else "unknown",
                                    "content_preview": str(m.content)[:200],
                                },
                            )
                    if msgs and isinstance(msgs[-1], AIMessage):
                        final_response = msgs[-1].content
            return final_response
        finally:
            with suppress(Exception):
                request_id_var.set(None)

    def _execute_graph(self, query: str, rid: str) -> str:
        try:
            memory_context, sub_queries = self._prepare_and_split(query)

            if len(sub_queries) <= 1:
                result = self._run_single(query, rid, memory_context=memory_context)
            else:
                def _run_with_memory(q: str, r: str) -> str:
                    return self._run_single(q, r, memory_context=memory_context)
                merged = run_queries_parallel(
                    sub_queries=sub_queries,
                    request_id=rid,
                    run_single_fn=_run_with_memory,
                    synthesize_fn=self._synthesizer.synthesize,
                    original_query=query,
                )
                result = self._apply_output_guardrails(merged, query)

            memory_mgr = get_memory_manager()
            if memory_mgr:
                try:
                    memory_mgr.add_interaction(
                        user_query=query,
                        agent_response=result,
                        context={
                            "sub_queries": sub_queries,
                            "request_id": rid,
                        },
                    )
                except Exception as mem_err:
                    logger.warning("Failed to record memory", extra={"request_id": rid, "error": str(mem_err)})

            return result
        except Exception as e:
            logger.exception(
                "Agent execution failed", extra={"request_id": rid, "error": str(e)}
            )
            return "Xin lỗi, đã xảy ra lỗi trong quá trình xử lý. Vui lòng thử lại sau."

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _resolve_request_id(self, provided: str | None = None) -> str:
        if provided:
            return provided
        existing = request_id_var.get()
        if existing:
            return existing
        return str(uuid.uuid4())

    def run(self, query: str, request_id: str | None = None) -> str:
        rid = self._resolve_request_id(request_id)
        with suppress(Exception):
            request_id_var.set(rid)
        start_time = time.time()
        try:
            result = self._execute_graph(query, rid)
            return result
        finally:
            with suppress(Exception):
                request_id_var.set(None)
            latency = time.time() - start_time
            logger.info(
                "Agent run complete",
                extra={
                    "request_id": rid,
                    "latency_ms": round(latency * 1000, 2),
                },
            )

    def _run_single_stream(self, query: str, rid: str, memory_context: str = ""):
        try:
            request_id_var.set(rid)
        except Exception as exc:
            logger.warning(
                "Failed to set request_id_var in stream",
                extra={
                    "request_id": rid,
                    "error": str(exc),
                },
            )
        init_state: AgentState = {
            "messages": [HumanMessage(content=query)],
            "iterations": 0,
            "original_query": query,
            "request_id": rid,
            "memory_context": memory_context,
        }
        _STREAM_EVENT_LIMIT = 5000
        event_count = 0
        deadline = time.time() + AGENT_TIMEOUT_SECONDS
        try:
            for event in self.app.stream(init_state, stream_mode="messages"):
                if time.time() > deadline:
                    logger.warning(
                        "Stream execution timed out",
                        extra={"request_id": rid, "timeout": AGENT_TIMEOUT_SECONDS},
                    )
                    yield "Quá trình xử lý đã vượt quá thời gian cho phép. Vui lòng thử lại."
                    return
                event_count += 1
                if event_count > _STREAM_EVENT_LIMIT:
                    logger.warning(
                        "Stream event limit reached",
                        extra={"request_id": rid, "events": event_count},
                    )
                    yield "Đã đạt giới hạn xử lý. Vui lòng thử lại."
                    return
                if not isinstance(event, (list, tuple)) or len(event) != 2:
                    continue
                chunk, _metadata = event
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    yield chunk.content
        except Exception as e:
            logger.exception(
                "Streaming execution failed",
                extra={
                    "request_id": rid,
                    "error": str(e),
                },
            )
            yield "Xin lỗi, đã xảy ra lỗi khi xử lý yêu cầu. Vui lòng thử lại sau."

    def run_stream(self, query: str, request_id: str | None = None):
        rid = self._resolve_request_id(request_id)
        with suppress(Exception):
            request_id_var.set(rid)
        try:
            start_time = time.time()

            memory_context, sub_queries = self._prepare_and_split(query)

            if len(sub_queries) <= 1:
                try:
                    for token in self._run_single_stream(query, rid, memory_context=memory_context):
                        if token:
                            yield token
                except Exception as e:
                    logger.exception(
                        "Agent streaming failed",
                        extra={
                            "request_id": rid,
                            "error": str(e),
                        },
                    )
                    yield "Xin lỗi, đã xảy ra lỗi trong quá trình xử lý."
            else:
                result = self._execute_graph(query, rid)
                import re
                _WORD_CHUNK_SIZE = 5
                words = re.split(r"(\s+)", result)
                for i in range(0, len(words), _WORD_CHUNK_SIZE * 2):
                    chunk = "".join(words[i : i + _WORD_CHUNK_SIZE * 2])
                    if chunk:
                        yield chunk

            latency = time.time() - start_time
            logger.info(
                "Agent streaming complete",
                extra={
                    "request_id": rid,
                    "latency_ms": round(latency * 1000, 2),
                },
            )
        finally:
            with suppress(Exception):
                request_id_var.set(None)


def build_graph():
    agent = StockAgent()
    return agent.app
