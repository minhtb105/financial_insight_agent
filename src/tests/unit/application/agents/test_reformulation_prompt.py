"""Unit tests for the query_reformulation prompt template (no LLM needed)."""

from application.prompts import PromptRegistryError, get_registry


def test_reformulation_prompt_renders():
    rendered = get_registry().render(
        "query_reformulation",
        query="Ai là tác giả của nó?",
        prev_q="Khái niệm Transformer là gì?",
        prev_r="Transformer là kiến trúc Attention...",
        sliding="",
        episodic="",
    )
    assert "Ai là tác giả của nó?" in rendered.text
    assert "Transformer" in rendered.text


def test_reformulation_prompt_missing_var_raises():
    try:
        get_registry().render("query_reformulation", query="hello?")
    except PromptRegistryError:
        return
    raise AssertionError("expected PromptRegistryError for missing variables")
