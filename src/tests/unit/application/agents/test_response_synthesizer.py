"""Unit tests for ResponseSynthesizer."""

from unittest.mock import MagicMock
from application.agents.response_synthesizer import ResponseSynthesizer
from infrastructure.llm.llm_provider import LLMProvider


class _MockResponse:
    def __init__(self, content):
        self.content = content


def test_synthesize_empty_answers():
    syn = ResponseSynthesizer(MagicMock(spec=LLMProvider))
    assert syn.synthesize([], "test") == ""


def test_synthesize_single_answer():
    syn = ResponseSynthesizer(MagicMock(spec=LLMProvider))
    assert syn.synthesize(["only one"], "test") == "only one"


def test_synthesize_llm_fallback_to_dedup():
    mock_provider = MagicMock(spec=LLMProvider)
    mock_provider.invoke_with_fallback.side_effect = Exception("LLM down")
    syn = ResponseSynthesizer(mock_provider)

    answers = ["**Kết quả [1] — giá VCB**\nVCB: 100", "**Kết quả [2] — giá HPG**\nHPG: 50"]
    result = syn.synthesize(answers, "test")
    assert "VCB" in result
    assert "HPG" in result


def test_synthesize_dedup_same_content():
    mock_provider = MagicMock(spec=LLMProvider)
    mock_provider.invoke_with_fallback.side_effect = Exception("LLM down")
    syn = ResponseSynthesizer(mock_provider)

    result = syn.synthesize(["data1", "data1", "data2"], "test")
    assert result.count("data1") == 1
    assert "data2" in result


def test_synthesize_llm_success():
    mock_provider = MagicMock(spec=LLMProvider)
    mock_provider.invoke_with_fallback.return_value = _MockResponse("synthesized result")
    syn = ResponseSynthesizer(mock_provider)

    result = syn.synthesize(["ans1", "ans2"], "test query")
    assert result == "synthesized result"
    mock_provider.invoke_with_fallback.assert_called_once()
