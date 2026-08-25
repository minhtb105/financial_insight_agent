"""Unit tests for LLMProvider, LLMChain, and fallback mechanisms."""

from unittest.mock import patch, MagicMock
import pytest

# -- MultiQuery (simple pydantic model) ----------------------------------


def test_multi_query_model():
    from infrastructure.llm.llm_provider import MultiQuery

    mq = MultiQuery(queries=["q1", "q2"])
    assert mq.queries == ["q1", "q2"]


# -- LLMProvider init ----------------------------------------------------


@patch("infrastructure.llm.llm_provider.ChatOpenAI")
@patch("infrastructure.llm.llm_provider.ChatGroq")
@patch("infrastructure.llm.llm_provider.create_circuit_breaker")
@patch("infrastructure.llm.llm_provider.os.getenv")
def test_llm_provider_init(mock_getenv, mock_cb, mock_groq, mock_openai):
    mock_getenv.return_value = "sk-test-key"
    from infrastructure.llm.llm_provider import LLMProvider

    provider = LLMProvider()
    assert provider._openai_cb is not None
    assert provider._groq_cb is not None


# -- invoke_with_fallback — primary succeeds -----------------------------


@patch("infrastructure.llm.llm_provider.ChatOpenAI")
@patch("infrastructure.llm.llm_provider.ChatGroq")
@patch("infrastructure.llm.llm_provider.create_circuit_breaker")
@patch("infrastructure.llm.llm_provider.os.getenv")
def test_invoke_with_fallback_primary_succeeds(mock_getenv, mock_cb, mock_groq, mock_openai):
    mock_getenv.return_value = "sk-test-key"
    mock_instance = MagicMock()
    mock_instance.invoke.return_value.content = "OpenAI response"
    mock_openai.return_value = mock_instance
    mock_cb.return_value.acquire_permit.return_value = True

    from infrastructure.llm.llm_provider import LLMProvider

    provider = LLMProvider()
    result = provider.invoke_with_fallback("test prompt")
    assert result.content == "OpenAI response"


# -- invoke_with_fallback — primary fails, fallback succeeds -------------


@patch("infrastructure.llm.llm_provider.ChatOpenAI")
@patch("infrastructure.llm.llm_provider.ChatGroq")
@patch("infrastructure.llm.llm_provider.create_circuit_breaker")
@patch("infrastructure.llm.llm_provider.os.getenv")
def test_invoke_with_fallback_fallback_succeeds(mock_getenv, mock_cb, mock_groq, mock_openai):
    mock_getenv.return_value = "sk-test-key"
    mock_openai_instance = MagicMock()
    mock_openai_instance.invoke.side_effect = Exception("OpenAI down")
    mock_openai.return_value = mock_openai_instance

    mock_groq_instance = MagicMock()
    mock_groq_instance.invoke.return_value.content = "Groq response"
    mock_groq.return_value = mock_groq_instance
    mock_cb.return_value.acquire_permit.return_value = True

    from infrastructure.llm.llm_provider import LLMProvider

    provider = LLMProvider()
    result = provider.invoke_with_fallback("test prompt")
    assert result.content == "Groq response"


# -- invoke_with_fallback — both fail ------------------------------------


@patch("infrastructure.llm.llm_provider.ChatOpenAI")
@patch("infrastructure.llm.llm_provider.ChatGroq")
@patch("infrastructure.llm.llm_provider.create_circuit_breaker")
@patch("infrastructure.llm.llm_provider.os.getenv")
def test_invoke_with_fallback_both_fail(mock_getenv, mock_cb, mock_groq, mock_openai):
    mock_getenv.return_value = "sk-test-key"
    mock_openai_instance = MagicMock()
    mock_openai_instance.invoke.side_effect = Exception("OpenAI down")
    mock_openai.return_value = mock_openai_instance

    mock_groq_instance = MagicMock()
    mock_groq_instance.invoke.side_effect = Exception("Groq down")
    mock_groq.return_value = mock_groq_instance
    mock_cb.return_value.acquire_permit.return_value = True

    from infrastructure.llm.llm_provider import LLMProvider, LLMUnavailableError

    provider = LLMProvider()
    with pytest.raises((Exception, LLMUnavailableError)):
        provider.invoke_with_fallback("test prompt")


# -- get_tool_calling_llm -------------------------------------------------


@patch("infrastructure.llm.llm_provider.ChatOpenAI")
@patch("infrastructure.llm.llm_provider.ChatGroq")
@patch("infrastructure.llm.llm_provider.create_circuit_breaker")
@patch("infrastructure.llm.llm_provider.os.getenv")
def test_get_tool_calling_llm(mock_getenv, mock_cb, mock_groq, mock_openai):
    mock_getenv.return_value = "sk-test-key"
    from infrastructure.llm.llm_provider import LLMProvider, LLMChain

    provider = LLMProvider()
    chain = provider.get_tool_calling_llm(tools=[])
    assert isinstance(chain, LLMChain)
    assert chain._label == "tool-calling"


# -- kwarg filtering ------------------------------------------------------


def test_groq_known_kwargs():
    from infrastructure.llm.llm_provider import _GROQ_KNOWN_KWARGS

    for kw in ("temperature", "max_tokens", "model", "top_p", "stop", "stream"):
        assert kw in _GROQ_KNOWN_KWARGS


def test_openai_known_kwargs():
    from infrastructure.llm.llm_provider import _OPENAI_KNOWN_KWARGS

    for kw in ("response_format", "temperature", "max_tokens", "model", "seed", "tools"):
        assert kw in _OPENAI_KNOWN_KWARGS


# -- LLMChain lazy rid ----------------------------------------------------


@patch("infrastructure.llm.llm_provider.ChatOpenAI")
@patch("infrastructure.llm.llm_provider.ChatGroq")
@patch("infrastructure.llm.llm_provider.create_circuit_breaker")
@patch("infrastructure.llm.llm_provider.os.getenv")
@patch("infrastructure.llm.llm_provider.request_id_var")
def test_llmchain_resolves_rid_at_invoke(mock_rid, mock_getenv, mock_cb, mock_groq, mock_openai):
    mock_getenv.return_value = "sk-test-key"
    mock_rid.get.return_value = "req-999"
    mock_instance = MagicMock()
    mock_instance.invoke.return_value.content = "ok"
    mock_openai.return_value = mock_instance
    mock_cb.return_value.can_execute.return_value = True

    from infrastructure.llm.llm_provider import LLMProvider

    provider = LLMProvider()
    chain = provider.get_tool_calling_llm(tools=[])
    chain.invoke("hello")
    assert mock_rid.get.called
