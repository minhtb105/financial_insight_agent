import json
import time
from unittest.mock import MagicMock

import pytest

from infrastructure.observability.tracing import (
    SpanKind,
    TraceStore,
    Tracer,
)
from infrastructure.observability.tracing.langchain_handler import (
    TracingCallbackHandler,
    _model_info_from_response,
)


@pytest.fixture()
def store(tmp_path):
    return TraceStore(tmp_path / "traces.db")


@pytest.fixture()
def tracer(store):
    return Tracer(store=store, enabled=True, max_content_chars=200)


class TestTracerSpans:
    def test_disabled_tracer_yields_none(self, tmp_path):
        tracer = Tracer(store=None, enabled=False)
        with tracer.start_span("x", SpanKind.NODE) as span:
            assert span is None
        assert tracer.begin_span("y", SpanKind.LLM) is None

    def test_nested_spans_parent_resolution(self, tracer, store):
        with tracer.start_span("root", SpanKind.AGENT) as root:
            with tracer.start_span("child", SpanKind.NODE) as child:
                assert child.parent_span_id == root.span_id
                assert child.trace_id == root.trace_id
        detail = store.get_trace(root.trace_id)
        assert detail is not None
        names = {s["name"] for s in detail["spans"]}
        assert names == {"root", "child"}

    def test_error_status_recorded(self, tracer, store):
        with pytest.raises(ValueError), tracer.start_span("failing", SpanKind.NODE):
            raise ValueError("boom")
        rows = store.list_traces()
        detail = store.get_trace(rows[0]["trace_id"])
        failing = next(s for s in detail["spans"] if s["name"] == "failing")
        assert failing["status"] == "error"
        assert "ValueError" in failing["error"]

    def test_contextvars_restored_after_exit(self, tracer):
        from infrastructure.observability.tracing.context import (
            current_parent_span_id,
            trace_id_var,
        )

        before_tid = trace_id_var.get()
        with tracer.start_span("outer", SpanKind.AGENT) as outer:
            tid_inside = trace_id_var.get()
            assert tid_inside == outer.trace_id
        assert trace_id_var.get() is before_tid
        assert current_parent_span_id() is None

    def test_inputs_outputs_truncated(self, tracer, store):
        long_text = "x" * 5000
        with tracer.start_span("big", SpanKind.TOOL, inputs={"data": long_text}) as span:
            span.outputs = long_text
        rows = store.list_traces()
        detail = store.get_trace(rows[0]["trace_id"])
        big = next(s for s in detail["spans"] if s["name"] == "big")
        assert len(big["inputs"]["data"]) <= 200 + 60
        assert "truncated" in big["outputs"]

    def test_manual_begin_span_resolves_ambient_parent(self, tracer, store):
        with tracer.start_span("outer", SpanKind.AGENT) as outer:
            manual = tracer.begin_span("manual_llm", SpanKind.LLM)
            assert manual.parent_span_id == outer.span_id
            manual.total_tokens = 10
            tracer.finish_span(manual)
        detail = store.get_trace(outer.trace_id)
        total = detail["total_tokens"]
        assert total == 10


class TestTraceStore:
    def test_roundtrip_and_filters(self, store):
        t = Tracer(store=store, enabled=True)
        with t.start_span("ok_run", SpanKind.AGENT) as span:
            llm = t.begin_span("ChatOpenAI", SpanKind.LLM)
            llm.model = "gpt-4o-mini"
            llm.provider = "openai"
            llm.prompt_tokens = 100
            llm.completion_tokens = 50
            llm.total_tokens = 150
            t.finish_span(llm)

        rows = store.list_traces(name_filter="ok_run")
        assert len(rows) == 1
        row = rows[0]
        assert row["num_spans"] == 2
        assert row["llm_call_count"] == 1
        assert row["total_tokens"] == 150
        assert row["status"] == "ok"

        assert store.list_traces(status="error") == []
        assert store.list_traces(min_duration_ms=999999) == []

    def test_get_missing_trace_returns_none(self, store):
        assert store.get_trace("nonexistent") is None

    def test_purge(self, store):
        t = Tracer(store=store, enabled=True)
        with t.start_span("old", SpanKind.AGENT):
            pass
        deleted = store.purge_older_than(days=0)
        assert deleted == 1
        assert store.list_traces() == []


class TestModelInfoExtraction:
    def _fake_response(self, llm_output, metadata):
        response = MagicMock()
        response.llm_output = llm_output
        gen = MagicMock()
        msg = MagicMock()
        msg.response_metadata = metadata
        gen.message = msg
        response.generations = [[gen]]
        return response

    def test_openai_token_usage(self):
        resp = self._fake_response(
            {"token_usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
             "model_name": "gpt-4o-mini"},
            {},
        )
        info = _model_info_from_response(resp)
        assert info == {
            "model": "gpt-4o-mini", "provider": "openai",
            "prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15,
        }

    def test_groq_usage_fallback(self):
        resp = self._fake_response(
            {},
            {"usage": {"prompt_tokens": 7, "completion_tokens": 3, "total_tokens": 10},
             "model_name": "llama-3.1-8b-instant"},
        )
        info = _model_info_from_response(resp)
        assert info["provider"] == "groq"
        assert info["prompt_tokens"] == 7


class TestTracingCallbackHandler:
    def _make_handler(self, tracer):
        return TracingCallbackHandler(tracer)

    def test_chat_model_lifecycle_records_tokens(self, tracer, store):
        handler = self._make_handler(tracer)
        run_id = "run-1"

        msgs = MagicMock()
        msgs.__iter__ = lambda self: iter([])
        handler.on_chat_model_start({"id": ["langchain_openai", "ChatOpenAI"]}, [msgs], run_id=run_id)

        from langchain_core.messages import AIMessage
        from langchain_core.outputs import ChatGeneration, LLMResult

        ai_msg = AIMessage(
            content="giá là 95,000",
            response_metadata={
                "model_name": "gpt-4o-mini",
                "token_usage": {"prompt_tokens": 11, "completion_tokens": 4, "total_tokens": 15},
            },
        )
        result = LLMResult(generations=[[ChatGeneration(message=ai_msg)]])
        handler.on_llm_end(result, run_id=run_id)

        rows = store.list_traces()
        assert len(rows) >= 1
        detail = store.get_trace(rows[0]["trace_id"])
        llm_span = next(s for s in detail["spans"] if s["kind"] == "llm")
        assert llm_span["model"] == "gpt-4o-mini"
        assert llm_span["provider"] == "openai"
        assert llm_span["total_tokens"] == 15
        assert "95,000" in str(llm_span["outputs"])

    def test_llm_error_marks_span(self, tracer, store):
        handler = self._make_handler(tracer)
        run_id = "run-err"
        handler.on_chat_model_start(None, [], run_id=run_id)
        handler.on_llm_error(RuntimeError("api down"), run_id=run_id)

        rows = store.list_traces()
        detail = store.get_trace(rows[0]["trace_id"])
        llm_span = next(s for s in detail["spans"] if s["kind"] == "llm")
        assert llm_span["status"] == "error"
        assert "RuntimeError" in llm_span["error"]

    def test_langgraph_node_span_created_and_nested(self, tracer, store):
        handler = self._make_handler(tracer)
        node_run = "node-run"
        llm_run = "llm-under-node"

        handler.on_chain_start(None, {}, run_id=node_run,
                               parent_run_id="agent-root", metadata={"langgraph_node": "reason"})
        handler.on_chat_model_start(
            {"id": ["langchain_openai", "chat_models", "ChatOpenAI"]}, [],
            run_id=llm_run, parent_run_id=node_run,
            metadata={"langgraph_node": "reason"},
        )
        handler.on_llm_end(MagicMock(), run_id=llm_run)
        handler.on_chain_end({}, run_id=node_run)

        rows = store.list_traces()
        detail = store.get_trace(rows[0]["trace_id"])
        spans = {s["name"]: s for s in detail["spans"]}
        assert "reason" in spans
        assert spans["ChatOpenAI"]["parent_span_id"] == spans["reason"]["span_id"]

    def test_non_graph_chain_runs_ignored(self, tracer, store):
        handler = self._make_handler(tracer)
        handler.on_chain_start(None, {}, run_id="noise", metadata={})
        handler.on_chain_end({}, run_id="noise")
        assert store.list_traces() == []


class TestStorageJsonRoundtrip:
    def test_attributes_json_survives(self, tmp_path):
        store = TraceStore(tmp_path / "t2.db")
        t = Tracer(store=store, enabled=True)
        payload = {"nested": {"a": [1, 2, 3]}, "text": "dữ liệu tiếng Việt"}
        with t.start_span("attr", SpanKind.TOOL, attributes={"payload": payload}) as span:
            span.attributes["extra"] = True
        rows = store.list_traces()
        detail = store.get_trace(rows[0]["trace_id"])
        s = detail["spans"][0]
        assert isinstance(s["attributes"], dict)
        assert s["attributes"]["payload"]["nested"]["a"] == [1, 2, 3]
        assert s["attributes"]["extra"] is True
