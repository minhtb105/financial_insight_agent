"""Unit tests for MCP server — tools/list discovery (replaces tool_registry tests)."""

import json

import pytest

from mcp_server.instance import mcp
import mcp_server.tools  # noqa: F401 — ensure registration


def test_mcp_has_13_tools():
    assert len(mcp._tool_manager._tools) == 13


def test_mcp_tool_names():
    expected = {
        "get_stock_price",
        "calculate_technical_indicator",
        "compare_stocks",
        "rank_stocks",
        "aggregate_prices",
        "get_financial_ratios",
        "get_company_info",
        "get_news_and_sentiment",
        "manage_portfolio",
        "check_price_alert",
        "forecast_stock_price",
        "analyze_sector",
        "search_knowledge",
    }
    assert set(mcp._tool_manager._tools.keys()) == expected


def test_strict_literal_field_enum():
    # 5 đầu phải có enum strict
    for name in ["get_stock_price", "compare_stocks", "rank_stocks", "aggregate_prices"]:
        tool = mcp._tool_manager._tools[name]
        schema = tool.parameters
        assert "properties" in schema
        assert "field" in schema["properties"]
        assert "enum" in schema["properties"]["field"]
        assert set(schema["properties"]["field"]["enum"]) >= {"close", "volume"}

    # calculate_technical_indicator indicator enum
    tool = mcp._tool_manager._tools["calculate_technical_indicator"]
    assert "enum" in tool.parameters["properties"]["indicator"]
    assert set(tool.parameters["properties"]["indicator"]["enum"]) == {"sma", "rsi", "macd"}

    # aggregate aggregate_fn enum
    tool = mcp._tool_manager._tools["aggregate_prices"]
    assert "enum" in tool.parameters["properties"]["aggregate_fn"]


def test_all_tools_have_descriptions():
    for name, tool in mcp._tool_manager._tools.items():
        assert tool.description and len(tool.description) > 20, name


def test_search_knowledge_has_citation_guidance():
    tool = mcp._tool_manager._tools["search_knowledge"]
    desc = tool.description.lower()
    assert "priority" in desc
    assert "vbpl" in desc


def test_mcp_tool_invocation_via_helpers():
    from unittest.mock import patch

    from mcp_server.tools.helpers import _wrap, _categorize_error, TOOL_ERR_PREFIX

    # helpers still work (migrated from tool_registry)
    assert _categorize_error(ValueError("bad")).startswith(f"{TOOL_ERR_PREFIX}VALIDATION")
    assert "note" in json.loads(_wrap("fn", None))


def test_tool_call_returns_json_string():
    from unittest.mock import patch

    # pick one tool and mock its service
    tool = mcp._tool_manager._tools["get_stock_price"]
    with patch("mcp_server.tools.price.handle_price_query", return_value={"VCB": {"close": 100}}):
        result = tool.fn(tickers=["VCB"])  # type: ignore
        assert isinstance(result, str)
        parsed = json.loads(result)
        assert "VCB" in parsed
