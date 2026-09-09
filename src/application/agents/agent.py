"""
True tool-calling agent for Vietnamese stock market analysis.

Architecture:
  HumanMessage → [HybridQuerySplitter] → sub-queries
  Each sub-query:  reason_node ↔ action_node ↔ reason_node  (ReAct loop via next_tool_call handshake)
  Results merged → final_answer_node → guardrails

The LLM autonomously decides which tools to call and what arguments to pass.
No deterministic classifier / extractor pipeline is involved.
"""

import time
import uuid
import json
from datetime import datetime, timezone
from dotenv import load_dotenv
from typing import TypedDict, Annotated, Literal, Optional
from collections.abc import Sequence
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from application.agents.custom_tool_node import CustomToolNode
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
from infrastructure.observability.tracing import SpanKind, TracingCallbackHandler, get_tracer
from application.agents.hybrid_splitter import HybridQuerySplitter
from application.agents.multi_query_runner import run_queries_parallel
from application.agents.response_synthesizer import ResponseSynthesizer
from application.agents.fact_verifier import FactVerifier
from infrastructure.guardrails.output_guardrails import get_output_guardrails
from infrastructure.memory.memory_manager import get_memory_manager
from shared.utils.env_helpers import parse_int_env
from contextlib import suppress

logger = get_logger("agent.StockAgent")

MAX_ITERATIONS = parse_int_env("AGENT_MAX_ITERATIONS", 10)
AGENT_TIMEOUT_SECONDS = parse_int_env("AGENT_TIMEOUT_SECONDS", 120)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    iterations: int
    original_query: str
    request_id: str
    memory_context: str
    tool_call_history: list[str]
    tool_call_cache: dict[str, str]
    tool_call_retries: dict[str, int]
    next_tool_call: Optional[list]  # explicit handoff: reason_node → action_node


class StockAgent:
    def __init__(self) -> None:
        load_dotenv()

        # MCP auto-discovery via tools/list (spec). Falls back to in-process if MCP server unreachable.
        try:
            from infrastructure.mcp.loader import load_mcp_tools_sync

            self.tools = load_mcp_tools_sync()
            if not self.tools:
                raise RuntimeError("MCP returned no tools")
        except Exception as e:
            logger.warning("MCP loader failed, fallback to direct mcp_server import: %s", e)
            try:
                import mcp_server.tools  # noqa: F401

                # Convert FastMCP tools to LangChain via fallback loader
                from infrastructure.mcp.loader import load_mcp_tools_sync

                self.tools = load_mcp_tools_sync()
            except Exception as e2:
                logger.error("Fallback also failed: %s", e2)
                self.tools = []

        self.tool_node = CustomToolNode(self.tools) if self.tools else CustomToolNode([])
        try:
            self.llm_provider = LLMProvider()
            self.splitter = HybridQuerySplitter(llm_provider=self.llm_provider)
            # MCP tools carry their own descriptions/JSONSchema — no prompt tax
            if self.tools:
                self.llm = self.llm_provider.get_tool_calling_llm(self.tools)
            else:
                logger.warning("MCP tools empty — agent running without tools (prompt-only fallback)")
                # Create a tool-less chain so LLM can still answer (degraded)
                self.llm = self.llm_provider.get_tool_calling_llm([])
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
        self._fact_verifier = FactVerifier(confidence_threshold=0.8)

        graph = StateGraph(AgentState)
        graph.add_node("reason", self._reason_node)
        graph.add_node("action", self._action_node)
        graph.add_node("final_answer", self._final_answer_node)
        graph.add_node("verify_facts", self._verify_facts_node)

        graph.set_entry_point("reason")
        graph.add_conditional_edges(
            "reason",
            self._should_continue,
            {"continue": "action", "end": "final_answer"},
        )
        graph.add_edge("action", "reason")
        graph.add_edge("final_answer", "verify_facts")
        graph.add_edge("verify_facts", END)

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
    def _build_temporal_context(messages: list, current_date: str) -> str | None:
        tool_msgs = [m for m in messages if isinstance(m, ToolMessage)]
        if not tool_msgs:
            return None
        tickers_seen = {}
        for tm in tool_msgs:
            try:
                data = json.loads(tm.content) if isinstance(tm.content, str) else tm.content
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(data, dict):
                for key, val in data.items():
                    if isinstance(val, dict):
                        t = val.get("ticker") or key
                        end = val.get("end_date") or val.get("end")
                        if end:
                            tickers_seen[t.upper()] = end
        if not tickers_seen:
            return None
        lines = [f"Mốc thời gian dữ liệu ({current_date}):"]
        for t, end in sorted(tickers_seen.items()):
            lines.append(f"- {t}: số liệu mới nhất ngày {end}")
        lines.append("Chỉ sử dụng số liệu từ tool. KHÔNG dùng kiến thức huấn luyện.")
        return "\n".join(lines)

    def _build_messages(self, state: AgentState) -> list:
        """Split static (cacheable) vs dynamic system messages for prompt caching.

        - Static: agent_system (MCP-minimal ~213t) — cacheable prefix, no per-request variance.
        - Dynamic: Current date + memory_context — volatile, sent as second SystemMessage.
        - Temporal: per-ticker end_date — appended after tool results as third SystemMessage.
        This avoids mixing volatile data into the cacheable prefix (anti-pattern).
        """

        from application.prompts import PromptRegistryError, get_registry

        messages = list(state["messages"])
        memory_context = state.get("memory_context", "")
        current_date = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

        temporal_ctx = self._build_temporal_context(messages, current_date)
        if temporal_ctx:
            messages.append(SystemMessage(content=temporal_ctx))

        if not any(isinstance(m, SystemMessage) for m in messages):
            try:
                system_text = get_registry().render("agent_system").text
            except PromptRegistryError:
                logger.exception("agent_system prompt render failed — using empty fallback")
                system_text = "You are a professional stock analysis assistant."
            # 1) Static cacheable prefix — never includes date/memory
            static_msg = SystemMessage(content=system_text)
            # 2) Dynamic per-request context — volatile, not cached
            dynamic_parts = [f"Current date: {current_date}"]
            if memory_context:
                dynamic_parts.append(f"Context from past interactions:\n{memory_context}")
            dynamic_msg = SystemMessage(content="\n\n".join(dynamic_parts))
            messages = [static_msg, dynamic_msg, *messages]
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

    def _reason_node(self, state: AgentState) -> dict:
        node_logger = get_logger("agent.reason_node")
        rid = state.get("request_id") or request_id_var.get() or "unknown"
        start = time.time()
        iterations = state.get("iterations", 0)

        early = self._check_llm_available(node_logger, rid, iterations)
        if early:
            return {**early, "next_tool_call": None}

        early = self._check_max_iterations(node_logger, rid, iterations)
        if early:
            return {**early, "next_tool_call": None}

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
                "next_tool_call": None,
            }

        tool_calls_made = bool(response.tool_calls)
        tool_names = [t["name"] for t in (response.tool_calls or [])]
        node_logger.info(
            "Reason node completed",
            extra={
                "request_id": rid,
                "has_tool_calls": tool_calls_made,
                "tool_calls": tool_names,
                "duration_ms": round((time.time() - start) * 1000, 2),
            },
        )
        return {
            "messages": [response],
            "iterations": iterations + (1 if tool_calls_made else 0),
            "next_tool_call": response.tool_calls if response.tool_calls else None,
        }

    def _action_node(self, state: AgentState) -> dict:
        node_logger = get_logger("agent.action_node")
        rid = state.get("request_id") or request_id_var.get() or "unknown"

        tool_calls = state.get("next_tool_call", None)
        if not tool_calls:
            return {"messages": [], "next_tool_call": None}

        history: set[str] = set(state.get("tool_call_history", []))
        cache: dict[str, str] = dict(state.get("tool_call_cache", {}))
        retries: dict[str, int] = dict(state.get("tool_call_retries", {}))

        tool_messages: list[ToolMessage] = []
        for tc in tool_calls:
            tool_call_id = tc.get("id", "")
            tool_name = tc.get("name", "")
            content = self.tool_node.execute_one(tc, history, cache, retries)
            tool_messages.append(
                ToolMessage(content=content, tool_call_id=tool_call_id, name=tool_name)
            )

        node_logger.info(
            "Action node completed, executed %d tool(s) from next_tool_call",
            len(tool_calls),
            extra={"request_id": rid},
        )

        return {
            "messages": tool_messages,
            "next_tool_call": None,
            "tool_call_history": list(history),
            "tool_call_cache": cache,
            "tool_call_retries": retries,
        }

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

        if self._output_guardrails is None:
            return {"messages": [response]}

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

        # TT135 safety layer (after guardrails)
        try:
            from infrastructure.rag.safety import check_and_sanitize

            sanitized_text, blocked = check_and_sanitize(response.content)
            if blocked or sanitized_text != response.content:
                node_logger.warning("RAG safety sanitized", extra={"request_id": rid, "blocked": blocked})
                response = AIMessage(content=sanitized_text)
        except Exception:
            pass

        return {"messages": [response]}

    def _verify_facts_node(self, state: AgentState) -> dict:
        node_logger = get_logger("agent.verify_facts")
        rid = state.get("request_id") or request_id_var.get() or "unknown"
        messages = state.get("messages", [])
        original_query = state.get("original_query", "")

        last_ai: AIMessage | None = None
        for m in reversed(messages):
            if isinstance(m, AIMessage) and not m.tool_calls:
                last_ai = m
                break

        if not last_ai:
            return {"messages": []}

        result = self._fact_verifier.verify(
            response=last_ai.content,
            messages=messages,
            original_query=original_query,
        )

        confidence = result.get("confidence", 1.0)
        issues = result.get("issues", [])
        total_citations = result.get("total_citations", 0)

        node_logger.info(
            "Fact verification result",
            extra={
                "request_id": rid,
                "mode": result.get("mode", "none"),
                "confidence": confidence,
                "verified": result.get("verified", False),
                "issues": len(issues),
                "total_citations": total_citations,
            },
        )

        if not result["verified"]:
            if issues:
                summary = "\n".join(i["message"] for i in issues[:3])
                warning = (
                    f"\n\n⚠️ Cảnh báo: Một số số liệu cần kiểm tra lại:\n{summary}"
                )
                return {"messages": [AIMessage(content=last_ai.content + warning)]}
            return {"messages": [AIMessage(content=last_ai.content)]}

        if total_citations > 0 and confidence < 1.0:
            score = f"\n\n📊 Độ tin cậy: {int(confidence * 100)}% ({result.get('verified_count')}/{total_citations} số liệu đã xác thực)"
            return {"messages": [AIMessage(content=last_ai.content + score)]}

        return {"messages": []}

    @staticmethod
    def _should_continue(state: AgentState) -> Literal["continue", "end"]:
        if state.get("next_tool_call"):
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

    def _prepare_and_split(self, query: str, user_id: str | None = None) -> tuple[str, list[str]]:
        """Build memory context and split query into sub-queries."""
        memory_context = self._build_memory_context(query, user_id=user_id)
        sub_queries = self.splitter.split(query) if self.splitter else [query]
        if not sub_queries:
            sub_queries = [query]
        return memory_context, sub_queries

    # ------------------------------------------------------------------
    # Multi-query fan-out via HybridQuerySplitter
    # ------------------------------------------------------------------

    def _build_memory_context(self, query: str, user_id: str | None = None) -> str:
        """Search past interactions for context relevant to the current query."""
        memory_mgr = get_memory_manager()
        if not memory_mgr:
            return ""
        try:
            mem_results = memory_mgr.search_memory(query=query, top_k=3, user_id=user_id)
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

    def _run_single(self, query: str, rid: str, memory_context: str = "", user_id: str | None = None) -> str:
        with suppress(Exception):
            request_id_var.set(rid)
        tracer = get_tracer()
        handler = TracingCallbackHandler(tracer) if tracer.enabled else None
        stream_config = (
            {"callbacks": [handler], "configurable": {"thread_id": rid}}
            if handler else None
        )
        try:
            init_state: AgentState = {
                "messages": [HumanMessage(content=query)],
                "iterations": 0,
                "original_query": query,
                "request_id": rid,
                "memory_context": memory_context,
                "tool_call_history": [],
                "tool_call_cache": {},
                "tool_call_retries": {},
                "next_tool_call": None,
            }
            final_response = ""
            deadline = time.time() + AGENT_TIMEOUT_SECONDS
            for step in self.app.stream(init_state, config=stream_config, stream_mode="values"):
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

    def _execute_graph(self, query: str, rid: str, trace_span=None, user_id: str | None = None) -> str:
        try:
            memory_context, sub_queries = self._prepare_and_split(query, user_id=user_id)

            if trace_span is not None:
                trace_span.attributes["num_sub_queries"] = len(sub_queries)
                trace_span.attributes["sub_queries"] = sub_queries

            if len(sub_queries) <= 1:
                result = self._run_single(query, rid, memory_context=memory_context, user_id=user_id)
            else:
                def _run_with_memory(q: str, r: str) -> str:
                    return self._run_single(q, r, memory_context=memory_context, user_id=user_id)
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
                        user_id=user_id,
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

    def run(self, query: str, request_id: str | None = None, user_id: str | None = None) -> str:
        rid = self._resolve_request_id(request_id)
        with suppress(Exception):
            request_id_var.set(rid)
        tracer = get_tracer()
        try:
            with tracer.start_span(
                "agent.run", SpanKind.AGENT,
                attributes={"request_id": rid}, inputs={"query": query},
            ) as span:
                start_time = time.time()
                try:
                    result = self._execute_graph(query, rid, trace_span=span, user_id=user_id)
                    if span is not None:
                        span.outputs = {"answer": str(result)[:4000]}
                        span.attributes["user_id"] = user_id or "anonymous"
                    return result
                finally:
                    latency = time.time() - start_time
                    logger.info(
                        "Agent run complete",
                        extra={
                            "request_id": rid,
                            "latency_ms": round(latency * 1000, 2),
                        },
                    )
        finally:
            with suppress(Exception):
                request_id_var.set(None)

    def _run_single_stream(self, query: str, rid: str, memory_context: str = "", user_id: str | None = None):
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
        tracer = get_tracer()
        handler = TracingCallbackHandler(tracer) if tracer.enabled else None
        stream_config = (
            {"callbacks": [handler], "configurable": {"thread_id": rid}}
            if handler else None
        )
        init_state: AgentState = {
            "messages": [HumanMessage(content=query)],
            "iterations": 0,
            "original_query": query,
            "request_id": rid,
            "memory_context": memory_context,
            "tool_call_history": [],
            "tool_call_cache": {},
            "tool_call_retries": {},
            "next_tool_call": None,
        }
        _STREAM_EVENT_LIMIT = 5000
        event_count = 0
        deadline = time.time() + AGENT_TIMEOUT_SECONDS
        try:
            for event in self.app.stream(init_state, config=stream_config, stream_mode="messages"):
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

    def run_stream(self, query: str, request_id: str | None = None, user_id: str | None = None):
        rid = self._resolve_request_id(request_id)
        with suppress(Exception):
            request_id_var.set(rid)
        tracer = get_tracer()
        try:
            with tracer.start_span(
                "agent.stream", SpanKind.AGENT,
                attributes={"request_id": rid}, inputs={"query": query},
            ) as span:
                start_time = time.time()
                collected: list[str] = []
                memory_context, sub_queries = self._prepare_and_split(query, user_id=user_id)
                if span is not None:
                    span.attributes["num_sub_queries"] = len(sub_queries)
                    span.attributes["sub_queries"] = sub_queries
                    span.attributes["user_id"] = user_id or "anonymous"

                if len(sub_queries) <= 1:
                    try:
                        for token in self._run_single_stream(query, rid, memory_context=memory_context, user_id=user_id):
                            if token:
                                collected.append(token)
                                yield token
                    except GeneratorExit:
                        if span is not None:
                            span.outputs = {"answer": "".join(collected)[:1000]}
                        return
                    except Exception as e:
                        logger.exception(
                            "Agent streaming failed",
                            extra={
                                "request_id": rid,
                                "error": str(e),
                            },
                        )
                        yield "Xin lỗi, đã xảy ra lỗi khi xử lý yêu cầu. Vui lòng thử lại sau."
                else:
                    result = self._execute_graph(query, rid, user_id=user_id)
                    collected.append(result)
                    import re
                    _WORD_CHUNK_SIZE = 5
                    words = re.split(r"(\s+)", result)
                    for i in range(0, len(words), _WORD_CHUNK_SIZE * 2):
                        chunk = "".join(words[i : i + _WORD_CHUNK_SIZE * 2])
                        if chunk:
                            yield chunk

                if span is not None:
                    span.outputs = {"answer": "".join(collected)[:1000]}

                latency = time.time() - start_time
                logger.info(
                    "Agent streaming complete",
                    extra={
                        "request_id": rid,
                        "latency_ms": round(latency * 1000, 2),
                    },
                )
                # Persist interaction for streaming single-query path (multi-query already saved via _execute_graph)
                if collected and len(sub_queries) <= 1:
                    try:
                        from infrastructure.memory.memory_manager import get_memory_manager as _get_mm
                        _mm = _get_mm()
                        if _mm:
                            _mm.add_interaction(
                                user_query=query,
                                agent_response="".join(collected),
                                context={"request_id": rid, "stream": True},
                                user_id=user_id,
                            )
                    except Exception as mem_err:
                        logger.warning("Failed to record stream memory", extra={"request_id": rid, "error": str(mem_err)})
        finally:
            with suppress(Exception):
                request_id_var.set(None)


def build_graph():
    agent = StockAgent()
    return agent.app
