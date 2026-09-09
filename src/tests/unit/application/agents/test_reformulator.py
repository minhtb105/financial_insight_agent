"""Unit tests for QueryReformulator (FakeLLM, no API keys needed)."""

import pytest

from application.agents import reformulator as reform_module
from application.agents.reformulator import QueryReformulator


class FakeStructuredLLM:
    def __init__(self, behavior="ok"):
        self.behavior = behavior
        self.calls = 0

    def invoke(self, messages, timeout=30):
        self.calls += 1
        if self.behavior == "raise":
            raise RuntimeError("llm down")
        if self.behavior == "empty":
            return None

        class Resp:
            def __init__(self):
                self.rewritten = "Giá đóng cửa của HPG hôm qua là bao nhiêu?"
                self.entities = ["HPG"]
                self.topics = ["price"]

        return Resp()


class FakeProvider:
    def __init__(self, llm):
        self._llm = llm

    def with_structured_output(self, pydantic_object, method="json_mode", fallback=False):
        assert method == "json_schema"
        return self._llm


@pytest.fixture(autouse=True)
def clear_cache():
    reform_module._cache.clear()
    yield
    reform_module._cache.clear()


def _mem_inputs():
    return {
        "working": {
            "turn_id": "7",
            "previous_user_query": "HPG là mã ngành gì?",
            "previous_system_response": "HPG là cổ phiếu ngành thép...",
            "current_raw_query": "Giá đóng cửa của nó hôm qua?",
        },
        "sliding": {"turns": [], "summary": {}, "count": 0},
        "episodic": {"hits": [], "context": "", "count": 0},
    }


def test_no_history_passthrough_without_llm():
    llm = FakeStructuredLLM()
    r = QueryReformulator(FakeProvider(llm))
    out = r.rewrite("Giá VCB hôm nay?", mem_inputs={}, user_id="u1")
    assert out == ("Giá VCB hôm nay?", [], [])
    assert llm.calls == 0


def test_empty_query_passthrough():
    llm = FakeStructuredLLM()
    r = QueryReformulator(FakeProvider(llm))
    assert r.rewrite("", mem_inputs=_mem_inputs()) == ("", [], [])
    assert llm.calls == 0


def test_rewrite_with_history():
    llm = FakeStructuredLLM()
    r = QueryReformulator(FakeProvider(llm))
    rewritten, entities, topics = r.rewrite("Giá đóng cửa của nó hôm qua?", mem_inputs=_mem_inputs(), user_id="u1")
    assert rewritten == "Giá đóng cửa của HPG hôm qua là bao nhiêu?"
    assert entities == ["HPG"]
    assert topics == ["price"]
    assert llm.calls == 1


def test_cache_hit_skips_llm():
    llm = FakeStructuredLLM()
    r = QueryReformulator(FakeProvider(llm))
    first = r.rewrite("Giá của nó?", mem_inputs=_mem_inputs(), user_id="u1")
    second = r.rewrite("Giá của nó?", mem_inputs=_mem_inputs(), user_id="u1")
    assert first == second
    assert llm.calls == 1


def test_llm_failure_falls_back_to_raw():
    llm = FakeStructuredLLM(behavior="raise")
    r = QueryReformulator(FakeProvider(llm))
    out = r.rewrite("Giá của nó?", mem_inputs=_mem_inputs(), user_id="u1")
    assert out[0] == "Giá của nó?"
    assert out[1] == [] and out[2] == []


def test_empty_response_falls_back_to_raw():
    llm = FakeStructuredLLM(behavior="empty")
    r = QueryReformulator(FakeProvider(llm))
    out = r.rewrite("Giá của nó?", mem_inputs=_mem_inputs(), user_id="u1")
    assert out[0] == "Giá của nó?"


def test_prompt_input_truncates_context():
    mem = _mem_inputs()
    mem["sliding"] = {
        "turns": [
            {"user_query": f"q{i}", "agent_response": "x" * 2000} for i in range(5)
        ]
    }
    mem["episodic"] = {"context": "y" * 5000}
    variables = QueryReformulator._build_prompt_input("Giá của nó?", mem)
    assert len(variables["episodic"]) <= 600
    assert len(variables["prev_r"]) <= 800
    # only last 2 turns included
    assert "q4" in variables["sliding"] and "q0" not in variables["sliding"]
