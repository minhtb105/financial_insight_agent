"""
Fact-verification layer for the ReAct agent.

Cross-references LLM-generated citations (numeric claims) against actual
tool-returned data to detect and flag hallucinations before delivery.

Works in two modes:
1. Structured citations  — [TICKER: value, nguồn: tool_name]  (LLM follows format)
2. Loose numeric check   — scans for stray numbers and warns on bounds violations
"""

import json
import re
import logging
from typing import Any
from collections.abc import Sequence

from langchain_core.messages import ToolMessage, BaseMessage

logger = logging.getLogger(__name__)

CITATION_PATTERN = re.compile(
    r'\[([A-Z]{2,4})\s*:\s*([\d,]+\.?\d*)\s*,?\s*(?:ngu[oôồốổỗộ]\`?n|source)\s*:\s*([a-z_]+)\]',
    re.I,
)

FINANCIAL_KEYWORDS = {
    "giá": {"bounds": (0, 1_000_000), "field": "price"},
    "pe": {"bounds": (0, 100), "field": "pe_ratio"},
    "pb": {"bounds": (0, 50), "field": "pb_ratio"},
    "roe": {"bounds": (0, 100), "field": "roe"},
    "eps": {"bounds": (-100_000, 1_000_000), "field": "eps"},
    "khối lượng": {"bounds": (0, 1_000_000_000), "field": "volume"},
    "volume": {"bounds": (0, 1_000_000_000), "field": "volume"},
    "nợ": {"bounds": (0, 1_000_000_000_000_000), "field": "debt"},
    "doanh thu": {"bounds": (0, 1_000_000_000_000_000), "field": "revenue"},
    "lợi nhuận": {"bounds": (0, 1_000_000_000_000_000), "field": "profit"},
}


class DataExtractor:
    """Extract ticker→value mappings from ToolMessage JSON payloads."""

    @staticmethod
    def extract_all(messages: Sequence[BaseMessage]) -> dict[str, list[dict[str, Any]]]:
        data: dict[str, list[dict[str, Any]]] = {}
        for msg in messages:
            if not isinstance(msg, ToolMessage):
                continue
            try:
                content = json.loads(msg.content)
            except (json.JSONDecodeError, TypeError):
                continue
            tool_name = getattr(msg, "name", "unknown") or "unknown"
            DataExtractor._dig(content, tool_name, data)
        return data

    @staticmethod
    def _dig(
        obj: Any,
        source: str,
        accumulator: dict[str, list[dict[str, Any]]],
        current_ticker: str = "",
    ) -> None:
        if isinstance(obj, dict):
            ticker = obj.get("ticker") or current_ticker
            for key, value in obj.items():
                if key in ("date", "start_date", "end_date", "note", "_partial_error", "_error"):
                    continue
                if isinstance(value, (int, float)) and not isinstance(value, bool):
                    if ticker:
                        accumulator.setdefault(ticker.upper(), []).append({
                            "value": float(value),
                            "field": key,
                            "source": source,
                        })
                elif isinstance(value, (dict, list)):
                    DataExtractor._dig(value, source, accumulator, ticker or current_ticker)
        elif isinstance(obj, list):
            for item in obj:
                DataExtractor._dig(item, source, accumulator, current_ticker)


class CitationParser:
    """Parse structured citations from LLM response."""

    PATTERN = CITATION_PATTERN

    @classmethod
    def parse(cls, response: str) -> list[dict[str, Any]]:
        citations = []
        for match in cls.PATTERN.finditer(response):
            raw_value = match.group(2).replace(",", "")
            try:
                value = float(raw_value)
            except ValueError:
                continue
            citations.append({
                "ticker": match.group(1).upper(),
                "value": value,
                "source": match.group(3).lower(),
                "matched_text": match.group(0),
            })
        return citations


class FactVerifier:
    """Cross-reference LLM citations against tool-returned data.

    Two-tier design:
      Tier 1 — structured citations are verified exactly.
      Tier 2 — if no citations found, scan for loose numbers and check bounds.
    """

    def __init__(self, confidence_threshold: float = 0.8):
        self.confidence_threshold = confidence_threshold

    def verify(
        self,
        response: str,
        messages: Sequence[BaseMessage],
        original_query: str = "",
    ) -> dict[str, Any]:
        citations = CitationParser.parse(response)
        tool_data = DataExtractor.extract_all(messages)

        if not citations:
            return self._loose_check(response, tool_data, original_query)

        return self._strict_check(citations, tool_data)

    def _strict_check(
        self,
        citations: list[dict[str, Any]],
        tool_data: dict[str, list[dict[str, Any]]],
    ) -> dict[str, Any]:
        issues = []
        verified_count = 0

        for citation in citations:
            ticker = citation["ticker"]
            value = citation["value"]
            entries = tool_data.get(ticker, [])

            if not entries:
                issues.append({
                    "type": "no_tool_data",
                    "ticker": ticker,
                    "value": value,
                    "message": f"[{ticker}] Không tìm thấy dữ liệu tool nào cho mã này",
                })
                continue

            match = self._find_match(value, entries)
            if match:
                verified_count += 1
            else:
                closest = min(entries, key=lambda e: abs(e["value"] - value))
                issues.append({
                    "type": "value_mismatch",
                    "ticker": ticker,
                    "cited_value": value,
                    "tool_value": closest["value"],
                    "tool_field": closest["field"],
                    "tool_source": closest["source"],
                    "message": (
                        f"[{ticker}] Giá trị {value} không khớp dữ liệu tool "
                        f"({closest['value']} từ {closest['source']}/{closest['field']})"
                    ),
                })

        total = len(citations)
        confidence = verified_count / total if total else 1.0
        return {
            "verified": confidence >= self.confidence_threshold,
            "mode": "strict",
            "total_citations": total,
            "verified_count": verified_count,
            "confidence": round(confidence, 3),
            "issues": issues,
            "citations": citations,
        }

    def _loose_check(
        self,
        response: str,
        tool_data: dict[str, list[dict[str, Any]]],
        original_query: str = "",
    ) -> dict[str, Any]:
        issues = []
        numbers_found = []
        for match in re.finditer(r'(?<!\d)([\d,]+\.?\d*)\s*(VND|đ|%)?', response):
            raw = match.group(1).replace(",", "")
            try:
                val = float(raw)
            except ValueError:
                continue
            unit = match.group(2) or ""
            if val > 1_000_000_000_000:
                issues.append({
                    "type": "outlier_value",
                    "value": val,
                    "message": f"Số {val:,.0f} {unit}vượt quá giới hạn tài chính hợp lý",
                })
            numbers_found.append({"value": val, "unit": unit})

        for ticker, entries in tool_data.items():
            for entry in entries:
                for nf in numbers_found:
                    field = entry["field"]
                    if abs(entry["value"] - nf["value"]) / max(abs(nf["value"]), 1) < 0.001:
                        break

        return {
            "verified": len(issues) == 0,
            "mode": "loose",
            "total_citations": 0,
            "confidence": 0.0 if issues else 1.0,
            "issues": issues,
            "citations": [],
        }

    @staticmethod
    def _find_match(value: float, entries: list[dict[str, Any]], tolerance: float = 0.01) -> bool:
        return any(
            abs(entry["value"] - value) / max(abs(entry["value"]), 0.001) < tolerance
            for entry in entries
        )
