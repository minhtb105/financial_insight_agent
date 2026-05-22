"""Unit tests for MultiQueryRunner."""

from unittest.mock import MagicMock
from application.agents.multi_query_runner import run_queries_parallel


def test_empty_sub_queries():
    result = run_queries_parallel([], "rid", lambda q, r: "", lambda a, q: "", "original")
    assert result == ""


def test_single_sub_query():
    result = run_queries_parallel(["query1"], "rid", lambda q, r: "answer1", lambda a, q: "", "original")
    assert result == "answer1"


def test_multiple_sub_queries():
    run_single = MagicMock(side_effect=["ans1", "ans2"])
    synthesize = MagicMock(return_value="final")

    result = run_queries_parallel(["query1", "query2"], "rid", run_single, synthesize, "original")

    assert result == "final"
    assert run_single.call_count == 2
    synthesize.assert_called_once_with(["**Kết quả [1] — query1**\nans1", "**Kết quả [2] — query2**\nans2"], "original")


def test_sub_query_exception():
    run_single = MagicMock(side_effect=[ValueError("error"), "ans2"])
    synthesize = MagicMock(return_value="final")

    result = run_queries_parallel(["q1", "q2"], "rid", run_single, synthesize, "original")

    assert result == "final"
    synthesize.assert_called_once()
    answers_arg = synthesize.call_args[0][0]
    assert any("Không thể lấy dữ liệu" in a for a in answers_arg)
    assert any("q2" in a for a in answers_arg)


def test_answers_preserve_order():
    run_single = MagicMock(side_effect=["aaa", "bbb"])
    synthesize = MagicMock(return_value="merged")

    run_queries_parallel(["first", "second"], "rid", run_single, synthesize, "original")

    answers_arg = synthesize.call_args[0][0]
    assert "first" in answers_arg[0]
    assert "second" in answers_arg[1]
