"""Build ground-truth values for the golden dataset by snapshotting tool outputs.

For every case with ``ground_truth: null`` and an ``as_of_date``, this script
calls the REAL service handlers (same code path as the agent tools) with the
case's fixed date window and freezes key figures into ``ground_truth``.

Cases whose services fail (network/market data unavailable) keep
``needs_snapshot: true`` so CI can skip strict numeric checks for them.

Usage::

    python evals/scripts/build_golden_dataset.py            # fill + rewrite dataset
    python evals/scripts/build_golden_dataset.py --dry-run  # show what would be filled
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).parent))

from validate_golden_dataset import validate  # noqa: E402

DEFAULT_DATASET = ROOT / "evals" / "golden" / "golden_dataset.jsonl"


def _price(tickers, field="close", start=None, end=None):
    from application.services.market.price_service import handle_price_query

    return handle_price_query(
        tickers=tickers, field=field,
        start_date=start, end_date=end,
    )


def _indicator(tickers, indicator, period=None, start=None, end=None):
    from application.services.market.indicator_service import handle_indicator_query

    return handle_indicator_query(
        tickers=tickers, indicator=indicator, period=period,
        start_date=start, end_date=end,
    )


def _ratios(tickers, field="pe"):
    from application.services.financial.financial_ratio_service import (
        handle_financial_ratio_query,
    )

    return handle_financial_ratio_query(tickers=tickers, field=field)


def _extract_first_number(payload) -> float | None:
    """Best-effort: dig the first plausible number out of a service payload."""
    if isinstance(payload, (int, float)):
        return round(float(payload), 4)
    if isinstance(payload, str):
        return None
    if isinstance(payload, dict):
        for value in payload.values():
            found = _extract_first_number(value)
            if found is not None:
                return found
    if isinstance(payload, list):
        for item in payload:
            found = _extract_first_number(item)
            if found is not None:
                return found
    return None


def _last_numeric_in_list(payload) -> float | None:
    """Extract the numeric value of the LAST row (e.g., SMA at as-of date)."""
    lists = [
        v2
        for v in (payload or {}).values() if isinstance(v, dict)
        for v2 in v.values() if isinstance(v2, list) and v2
        and all(isinstance(row, dict) for row in v2)
    ]
    if not lists:
        return None
    last = lists[0][-1]
    return _extract_first_number(last)


def _field_series(payload, key: str) -> list[float]:
    """Collect numeric values of ``key`` across all row-dicts in the payload."""
    out: list[float] = []
    def _walk(node):
        if isinstance(node, dict):
            v = node.get(key)
            if isinstance(v, (int, float)):
                out.append(float(v))
            for vv in node.values():
                _walk(vv)
        elif isinstance(node, list):
            for item in node:
                _walk(item)
    _walk(payload)
    return out


def _lookback_start(as_of: str, days: int = 140) -> str:
    from datetime import date, timedelta

    d = date.fromisoformat(as_of)
    return (d - timedelta(days=days)).isoformat()


def build_case(case: dict) -> dict:
    """Fill ground_truth for one case; returns the updated case dict."""
    qid = case["id"]
    as_of = case.get("as_of_date")
    if case.get("ground_truth") is not None or not as_of:
        return case

    gt: dict = {}
    try:
        if qid == "price_001":
            gt["close_vcb"] = _extract_first_number(_price(["VCB"], start=as_of, end=as_of))
        elif qid == "price_002":
            gt["close_vcb"] = _extract_first_number(_price(["VCB"], start=as_of, end=as_of))
            gt["close_bid"] = _extract_first_number(_price(["BID"], start=as_of, end=as_of))
        elif qid == "price_003":
            gt["volume_hpg"] = _extract_first_number(
                _price(["HPG"], field="volume", start=as_of, end=as_of))
        elif qid == "price_004":
            opens = _field_series(
                _price(["FPT"], field="open", start="2024-07-01", end=as_of), "open_price")
            highs = _field_series(
                _price(["FPT"], field="high", start="2024-07-01", end=as_of), "high")
            gt["open_fpt"] = opens[0] if opens else None
            gt["high_fpt"] = max(highs) if highs else None
        elif qid == "ind_001":
            gt["sma20_vcb"] = _last_numeric_in_list(
                _indicator(["VCB"], "sma", 20, _lookback_start(as_of), as_of))
        elif qid == "ind_002":
            gt["rsi14_hpg"] = _last_numeric_in_list(
                _indicator(["HPG"], "rsi", 14, _lookback_start(as_of), as_of))
        elif qid == "ind_003":
            gt["macd_fpt"] = _last_numeric_in_list(
                _indicator(["FPT"], "macd", start=_lookback_start(as_of), end=as_of))
        elif qid == "ind_004":
            gt["sma9_vic"] = _last_numeric_in_list(
                _indicator(["VIC"], "sma", 9, _lookback_start(as_of), as_of))
            gt["sma20_vic"] = _last_numeric_in_list(
                _indicator(["VIC"], "sma", 20, _lookback_start(as_of), as_of))
        elif qid == "ratio_001":
            gt["pe_vcb"] = _extract_first_number(_ratios(["VCB"], "pe"))
        elif qid == "ratio_002":
            gt["roe_fpt"] = _extract_first_number(_ratios(["FPT"], "roe"))
        elif qid == "ratio_003":
            gt["eps_mwg"] = _extract_first_number(_ratios(["MWG"], "eps"))
            gt["de_mwg"] = _extract_first_number(_ratios(["MWG"], "debt_to_equity"))
        else:
            return case  # qualitative cases evaluated via RAGAS metrics instead
    except Exception as exc:
        case["ground_truth"] = {"needs_snapshot": True, "error": f"{type(exc).__name__}: {exc}"}
        return case

    gt = {k: v for k, v in gt.items() if v is not None}
    if not gt:
        case["ground_truth"] = {
            "needs_snapshot": True,
            "error": "no numeric value extracted (check service payload shape)",
        }
    else:
        case["ground_truth"] = gt
    return case


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("dataset", nargs="?", default=str(DEFAULT_DATASET))
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    path = Path(args.dataset)
    lines = [ln for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip()]
    cases = [json.loads(ln) for ln in lines]

    filled = skipped = failed = unchanged = 0
    out_cases = []
    for case in cases:
        before = case.get("ground_truth")
        updated = build_case(case)
        after = updated.get("ground_truth")
        if before is None and after is not None:
            if after.get("needs_snapshot"):
                failed += 1
                print(f"  [SNAPSHOT-MISS] {updated['id']}: {after.get('error', '')[:80]}")
            else:
                filled += 1
                print(f"  [FILLED] {updated['id']} -> {json.dumps(after, ensure_ascii=False)[:100]}")
        else:
            unchanged += 1
        out_cases.append(updated)

    print(f"\nSummary: filled={filled}, snapshot_missed={failed}, "
          f"skipped/qualitative={unchanged - skipped}")

    errors = validate(path)
    if errors:
        print("Dataset has structural errors — NOT writing:")
        for e in errors:
            print(f"  - {e}")
        return 1

    if not args.dry_run:
        path.write_text(
            "\n".join(json.dumps(c, ensure_ascii=False) for c in out_cases) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
