import json
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

from langchain.tools import tool

from data.indicators import (
    get_company_info,
    get_ohlcv,
    get_min_open_across_tickers,
    get_price_field,
    get_price_stat,
    get_aggregate_volume,
    compare_volume,
    get_sma,
    get_rsi,
)


# -------------------------
# Helpers
# -------------------------
def to_pretty_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def _ensure_list(x):
    if x is None:
        return []
    if isinstance(x, list):
        return x
    # if comma separated string
    if isinstance(x, str):
        return [t.strip().upper() for t in x.split(",") if t.strip()]
    return [x]


def normalize_query(query: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
    """
    Normalize input from either:
      - query: {...}
      - kwargs: ticker='HPG', start_date='2025-11-01', days=10, field='close', ...
    into canonical query dict used by indicators functions:
      - tickers: list[str]
      - start: 'YYYY-MM-DD' or None
      - end: 'YYYY-MM-DD' or None
      - interval: '1d', ...
      - requested_field: open_price / close_price / high_price / low_price / volume / ohlcv
      - days/weeks/months/indicator_params/aggregate etc as appropriate
    """
    q = {}
    if query:
        q.update({k: v for k, v in query.items() if v is not None})

    # merge kwargs (LLM-generated top-level args)
    for k, v in kwargs.items():
        if v is None:
            continue
        q[k] = v

    # Normalize tickers
    if "ticker" in q and "tickers" not in q:
        # single ticker -> list
        q["tickers"] = _ensure_list(q.pop("ticker"))
    if "tickers" in q:
        q["tickers"] = [t.upper() for t in _ensure_list(q["tickers"])]

    # Map date keys
    if "start_date" in q and "start" not in q:
        q["start"] = q.pop("start_date")
    if "end_date" in q and "end" not in q:
        q["end"] = q.pop("end_date")

    # If user passed 'days'/'weeks' as relative duration, compute start/end using today
    today = datetime.now().date()
    if "days" in q and (not q.get("start")):
        try:
            days = int(q["days"])
            q["end"] = q.get("end") or today.strftime("%Y-%m-%d")
            q["start"] = (today - timedelta(days=days)).strftime("%Y-%m-%d")
        except Exception:
            pass
    if "weeks" in q and (not q.get("start")):
        try:
            weeks = int(q["weeks"])
            q["end"] = q.get("end") or today.strftime("%Y-%m-%d")
            q["start"] = (today - timedelta(weeks=weeks)).strftime("%Y-%m-%d")
        except Exception:
            pass
    if "months" in q and (not q.get("start")):
        # approximate months as 30 days
        try:
            months = int(q["months"])
            q["end"] = q.get("end") or today.strftime("%Y-%m-%d")
            q["start"] = (today - timedelta(days=30 * months)).strftime("%Y-%m-%d")
        except Exception:
            pass

    # Map 'field' or 'price_field' to our requested_field enum names
    if "field" in q and "requested_field" not in q:
        f = str(q.pop("field")).lower()
        if f in ("close", "close_price", "price_close"):
            q["requested_field"] = "close_price"
        elif f in ("open", "open_price", "price_open"):
            q["requested_field"] = "open_price"
        elif f in ("high", "high_price"):
            q["requested_field"] = "high_price"
        elif f in ("low", "low_price"):
            q["requested_field"] = "low_price"
        elif f in ("volume", "vol"):
            q["requested_field"] = "volume"
        elif f in ("ohlcv", "all", "toàn bộ", "toan bo"):
            q["requested_field"] = "ohlcv"
        else:
            q["requested_field"] = f

    # Map aggregate synonyms
    if "stat" in q and "aggregate" not in q:
        q["aggregate"] = q.pop("stat")

    # Normalize interval case
    if "interval" in q and isinstance(q["interval"], str):
        q["interval"] = q["interval"].lower()

    # indicator params: accept indicator_params or sma/rsi lists directly
    if "sma" in q and "indicator_params" not in q:
        try:
            sizes = q.pop("sma")
            q.setdefault("indicator_params", {})["sma"] = sizes if isinstance(sizes, list) else [int(sizes)]
        except Exception:
            pass
    if "rsi" in q and "indicator_params" not in q:
        try:
            sizes = q.pop("rsi")
            q.setdefault("indicator_params", {})["rsi"] = sizes if isinstance(sizes, list) else [int(sizes)]
        except Exception:
            pass

    # final canonical keys only if present
    return q


# -------------------------
# Tools (all accept either query dict or kwargs)
# -------------------------


@tool("get_company_info", description="Trả về thông tin cổ đông, lãnh đạo hoặc công ty con của mã cổ phiếu theo truy vấn.")
def get_company_info_tool(query: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    q = normalize_query(query, **kwargs)
    if not q.get("tickers"):
        return "Thiếu ticker trong truy vấn."

    try:
        info = get_company_info(q)
    except Exception as e:
        return f"Lỗi khi lấy thông tin công ty: {e}"

    if not info:
        return "Không có dữ liệu công ty."

    return to_pretty_json(info)


@tool("get_ohlcv", description="Trả về dữ liệu OHLCV cho mã cổ phiếu theo truy vấn.")
def get_ohlcv_tool(query: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    q = normalize_query(query, **kwargs)
    if not q.get("tickers"):
        return "Thiếu ticker trong truy vấn."

    try:
        records = get_ohlcv(q)
    except Exception as e:
        return f"Lỗi khi lấy OHLCV: {e}"

    if not records:
        return "Không có dữ liệu OHLCV."

    return to_pretty_json(records)


@tool("get_price_field", description="Trả về chuỗi thời gian của 1 trường giá.")
def get_price_field_tool(query: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    q = normalize_query(query, **kwargs)
    if not q.get("tickers"):
        return "Thiếu ticker trong truy vấn."

    if not q.get("requested_field"):
        return "Thiếu trường giá (requested_field) trong truy vấn."

    try:
        records = get_price_field(q)
    except Exception as e:
        return f"Lỗi khi lấy trường giá: {e}"

    if not records:
        return "Không có dữ liệu trường giá."

    return to_pretty_json(records)


@tool("get_price_stat", description="Tính toán giá trị min/max/mean cho trường giá.")
def get_price_stat_tool(query: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    q = normalize_query(query, **kwargs)
    if not q.get("tickers"):
        return "Thiếu ticker trong truy vấn."

    stat = q.get("aggregate")
    if not stat:
        return "Thiếu thông tin aggregate (min/max/mean)."

    try:
        val = get_price_stat(q, stat)
    except Exception as e:
        return f"Lỗi khi tính thống kê giá: {e}"

    if val is None:
        return "Không có dữ liệu thống kê."

    try:
        return f"{stat}: {round(float(val), 2)}"
    except Exception:
        return f"{stat}: {val}"


@tool("get_aggregate_volume", description="Tính tổng khối lượng giao dịch trong khoảng thời gian.")
def get_aggregate_volume_tool(query: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    q = normalize_query(query, **kwargs)
    if not q.get("tickers"):
        return "Thiếu ticker trong truy vấn."

    try:
        total = get_aggregate_volume(q)
    except Exception as e:
        return f"Lỗi khi tính volume: {e}"

    if total is None:
        return "Không có dữ liệu khối lượng."

    return f"Tổng khối lượng: {int(total)}"


@tool("compare_volume", description="So sánh tổng volume giữa các mã cổ phiếu.")
def compare_volume_tool(query: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    q = normalize_query(query, **kwargs)
    # allow tickers OR ticker + compare_with
    tickers = q.get("tickers") or _ensure_list(q.get("ticker")) or []
    compare_with = _ensure_list(q.get("compare_with"))
    if not tickers and not compare_with:
        return "Thiếu ticker(s) để so sánh."

    # compose compare list
    if not compare_with and len(tickers) > 1:
        # first is base, rest are compare_with
        base = tickers[0]
        compare_with = tickers[1:]
        tickers = [base]
    q["tickers"] = tickers

    try:
        results = compare_volume(q)
    except Exception as e:
        return f"Lỗi khi so sánh volume: {e}"

    if not results:
        return "Không có dữ liệu."

    return to_pretty_json(results)


@tool("get_min_open_across_tickers", description="Tìm mã có giá mở cửa thấp nhất.")
def get_min_open_across_tickers_tool(query: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    q = normalize_query(query, **kwargs)
    if not q.get("tickers"):
        return "Thiếu tickers trong truy vấn."

    try:
        result = get_min_open_across_tickers(q)
    except Exception as e:
        return f"Lỗi khi tìm min open: {e}"

    if not result:
        return "Không có dữ liệu."

    return to_pretty_json(result)


@tool("get_sma", description="Tính chỉ báo SMA cho các window size đã chỉ định.")
def get_sma_tool(query: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    q = normalize_query(query, **kwargs)
    if not q.get("tickers"):
        return "Thiếu ticker trong truy vấn."

    try:
        result = get_sma(q)
    except Exception as e:
        return f"Lỗi khi tính SMA: {e}"

    if not result:
        return "Không có dữ liệu SMA."

    return to_pretty_json(result)


@tool("get_rsi", description="Tính chỉ báo RSI cho các window size đã chỉ định.")
def get_rsi_tool(query: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    q = normalize_query(query, **kwargs)
    if not q.get("tickers"):
        return "Thiếu ticker trong truy vấn."

    try:
        result = get_rsi(q)
    except Exception as e:
        return f"Lỗi khi tính RSI: {e}"

    if not result:
        return "Không có dữ liệu RSI."

    return to_pretty_json(result)
