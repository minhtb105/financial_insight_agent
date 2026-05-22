"""Unit tests for HybridQuerySplitter — rule-based and LLM fallback."""

from unittest.mock import MagicMock
from application.agents.hybrid_splitter import HybridQuerySplitter


class _MockResult:
    def __init__(self, queries):
        self.queries = queries


def _make_splitter():
    mock_provider = MagicMock()
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _MockResult(queries=["mock query"])
    mock_provider.with_structured_output.return_value = mock_llm
    return HybridQuerySplitter(llm_provider=mock_provider)


# --- Integration: split() calls rule then LLM fallback ---

def test_empty_text_returns_empty():
    s = _make_splitter()
    assert s.split("") == []
    assert s.split(None) == []
    assert s.split("   ") == []


def test_single_query_returns_one_part():
    s = _make_splitter()
    result = s.split("Lấy giá đóng cửa của VCB hôm qua")
    assert len(result) == 1


def test_sma_and_sma_is_not_split():
    s = _make_splitter()
    result = s.split("Tính SMA9 và SMA20 của VIC")
    assert len(result) == 1


def test_period_sentence_boundary_split():
    s = _make_splitter()
    result = s.split("Có chuyện gì? Tính SMA9 của HPG.")
    assert len(result) >= 2


# --- Rule-based split edge cases ---


def test_rule_split_numbered_period_no_split():
    s = _make_splitter()
    result = s.split("Tính SMA20 của VIC, tăng 12.5% so với tuần trước")
    assert len(result) == 1


def test_rule_split_ticker_period_no_split():
    s = _make_splitter()
    result = s.split("Giá VCB.HNX hôm qua là bao nhiêu")
    assert len(result) == 1


def test_rule_split_roi_connector():
    s = _make_splitter()
    result = s.split("Lấy giá VCB rồi tính SMA9 của HPG")
    assert len(result) >= 2
    assert "VCB" in result[0]
    assert "HPG" in result[1]


def test_rule_split_single_action_va_no_split():
    s = _make_splitter()
    result = s.split("Tính SMA9 và SMA20 của VIC")
    assert len(result) == 1


def test_rule_split_multi_action_va_splits():
    s = _make_splitter()
    result = s.split("Lấy giá VCB và tính SMA9 của HPG")
    assert len(result) >= 2


# --- _llm_split (direct unit tests) ---

def test_llm_split_empty():
    s = _make_splitter()
    assert s._llm_split("") == []
    assert s._llm_split("   ") == []


def test_llm_split_success():
    mock_provider = MagicMock()
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _MockResult(queries=["q1", "q2"])
    mock_provider.with_structured_output.return_value = mock_llm
    s = HybridQuerySplitter(llm_provider=mock_provider)

    result = s._llm_split("some query")
    assert result == ["q1", "q2"]


def test_llm_split_single_result():
    mock_provider = MagicMock()
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _MockResult(queries=["single query"])
    mock_provider.with_structured_output.return_value = mock_llm
    s = HybridQuerySplitter(llm_provider=mock_provider)

    result = s._llm_split("test")
    assert result == ["single query"]


def test_llm_split_retry_on_exception():
    mock_provider = MagicMock()
    mock_llm = MagicMock()
    mock_llm.invoke.side_effect = Exception("API error")
    mock_provider.with_structured_output.return_value = mock_llm
    s = HybridQuerySplitter(llm_provider=mock_provider)

    result = s._llm_split("test query")
    assert result == ["test query"]
    assert mock_llm.invoke.call_count == 3


def test_llm_split_fallback_when_queries_none():
    mock_provider = MagicMock()
    mock_llm = MagicMock()
    resp = MagicMock()
    resp.queries = None
    mock_llm.invoke.return_value = resp
    mock_provider.with_structured_output.return_value = mock_llm
    s = HybridQuerySplitter(llm_provider=mock_provider)

    result = s._llm_split("test")
    assert result == ["test"]


def test_llm_split_returns_empty_list():
    mock_provider = MagicMock()
    mock_llm = MagicMock()
    mock_llm.invoke.return_value = _MockResult(queries=[])
    mock_provider.with_structured_output.return_value = mock_llm
    s = HybridQuerySplitter(llm_provider=mock_provider)

    result = s._llm_split("test query")
    assert result == ["test query"]
