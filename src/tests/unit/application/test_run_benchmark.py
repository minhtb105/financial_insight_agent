"""Unit tests for benchmark deterministic metric helpers."""

import sys
from pathlib import Path

EVALS_DIR = Path(__file__).parents[4] / "evals"
sys.path.insert(0, str(EVALS_DIR))

from run_benchmark import (  # noqa: E402
    aggregate_deterministic,
    edge_behavior_ok,
    extract_numbers,
    has_citation,
    numeric_match,
    tool_precision_recall,
)


class TestExtractNumbers:
    def test_decimal_dot(self):
        assert 56.11 in extract_numbers("Giá VCB là 56.11 đồng")

    def test_thousands_comma(self):
        assert extract_numbers("Khối lượng 12,379,504 cổ phiếu") == [12379504.0]

    def test_mixed_text(self):
        nums = extract_numbers("RSI đạt 33.77 trong khi SMA20 là 57.3755")
        assert 33.77 in nums and 57.3755 in nums

    def test_empty(self):
        assert extract_numbers("") == []
        assert extract_numbers(None) == []


class TestNumericMatch:
    GT = {"close_vcb": 56.11}

    def test_exact_value_passes(self):
        assert numeric_match("Giá đóng cửa là 56.11", self.GT) is True

    def test_within_tolerance_passes(self):
        assert numeric_match("Giá là 56.13", self.GT) is True

    def test_wrong_value_fails(self):
        assert numeric_match("Giá là 61.50", self.GT) is False

    def test_no_number_fails(self):
        assert numeric_match("Không có dữ liệu.", self.GT) is False

    def test_thousands_volume(self):
        assert numeric_match("KLGD đạt 12,379,504 cổ phiếu",
                             {"volume_hpg": 12379504}) is True

    def test_multi_targets_require_all(self):
        gt = {"sma9_vic": 20.6878, "sma20_vic": 21.2245}
        assert numeric_match("SMA9 = 20.69, SMA20 = 21.22", gt) is True
        assert numeric_match("Chỉ có SMA9 = 20.69", gt) is False

    def test_skips_non_numeric_keys(self):
        assert numeric_match("56.11", {"close_vcb": 56.11, "behavior": "x"}) is True

    def test_none_when_no_targets(self):
        assert numeric_match("bất kể gì", {"needs_snapshot": True}) is None


class TestToolPrecisionRecall:
    def test_perfect(self):
        p, r = tool_precision_recall({"get_stock_price"}, {"get_stock_price"})
        assert (p, r) == (1.0, 1.0)

    def test_partial(self):
        p, r = tool_precision_recall(
            {"get_stock_price", "rank_stocks"}, {"get_stock_price"}
        )
        assert p == 0.5 and r == 1.0

    def test_missed_expected(self):
        p, r = tool_precision_recall(set(), {"get_financial_ratios"})
        assert p == 0.0 and r == 0.0

    def test_no_expected_returns_none(self):
        assert tool_precision_recall({"x"}, set()) == (None, None)


class TestCitation:
    def test_standard_format_detected(self):
        text = "VCB đang ở mức 56.11 [VCB: 56.11, nguồn: get_stock_price]"
        assert has_citation(text) is True

    def test_without_citation(self):
        assert has_citation("Giá VCB là 56.11.") is False


class TestEdgeBehavior:
    def test_invalid_ticker_explaining_is_ok(self):
        resp = "Mã XYZVN không tồn tại trên sàn, vui lòng kiểm tra lại."
        assert edge_behavior_ok("edge_invalid_ticker", resp) is True

    def test_invalid_ticker_fabricated_price_is_fail(self):
        resp = "Giá cổ phiếu XYZVN là 45.000 đồng."
        assert edge_behavior_ok("edge_invalid_ticker", resp) is False

    def test_ambiguous_with_clarification_is_ok(self):
        resp = "Bạn muốn xem giá của mã nào? Vui lòng cho biết ticker."
        assert edge_behavior_ok("edge_ambiguous", resp) is True

    def test_ambiguous_answer_without_clarification_fails(self):
        resp = "Giá hiện tại là 25.5."
        assert edge_behavior_ok("edge_ambiguous", resp) is False

    def test_other_type_returns_none(self):
        assert edge_behavior_ok("price", "anything") is None


class TestAggregateDeterministic:
    def test_aggregates_means_and_percentiles(self):
        rows = [
            {"id": "a", "tool_precision": 1.0, "tool_recall": 1.0,
             "citation": True, "numeric_match": True, "edge_ok": None,
             "latency_ms": 100.0, "total_tokens": 500},
            {"id": "b", "tool_precision": 0.5, "tool_recall": 1.0,
             "citation": False, "numeric_match": False, "edge_ok": True,
             "latency_ms": 300.0, "total_tokens": 700},
            {"id": "c", "tool_precision": None, "tool_recall": None,
             "citation": True, "numeric_match": None, "edge_ok": False,
             "latency_ms": 200.0, "total_tokens": None},
        ]
        agg = aggregate_deterministic(rows)
        assert agg["tool_precision"] == 0.75
        assert agg["tool_recall"] == 1.0
        assert agg["citation_rate"] == round(2 / 3, 4)
        assert agg["numeric_match_rate"] == 0.5
        assert agg["edge_pass_rate"] == 0.5
        assert agg["latency_p50_ms"] == 200.0
        assert agg["latency_p95_ms"] == 300.0
        assert agg["avg_tokens_per_case"] == 600

    def test_empty_rows_all_none(self):
        agg = aggregate_deterministic([])
        assert all(v is None for v in agg.values())
