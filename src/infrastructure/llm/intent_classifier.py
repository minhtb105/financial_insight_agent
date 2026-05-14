from typing import Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from infrastructure.llm.llm_provider import LLMProvider


_INTENT_SYSTEM_PROMPT = (
    "Bạn là bộ phân loại ý định cho câu hỏi chứng khoán tiếng Việt.\n"
    "Phân loại câu hỏi sau thành 1 trong 12 loại:\n\n"
    "- price: dữ liệu giá hoặc khối lượng cơ bản (giá, open, close, volume, "
    "OHLCV, mở cửa, đóng cửa, thông tin giá)\n"
    "- aggregate: yêu cầu tổng hợp số liệu (tổng, sum, trung bình, mean, avg, "
    "bình quân, nhỏ nhất, lớn nhất, min, max, median, đầu tiên, cuối cùng)\n"
    "- compare: yêu cầu so sánh giữa 2+ mã (so sánh A với B, compare, "
    "so sánh, A vs B)\n"
    "- indicator: yêu cầu chỉ báo kỹ thuật (SMA, EMA, RSI, MACD, MA, "
    "chỉ báo, BB, Bollinger, stochastic, ADX, ATR, OBV, CCI)\n"
    "- company: thông tin công ty (cổ đông, ban lãnh đạo, công ty con, "
    "shareholders, executives, subsidiaries)\n"
    "- ranking: xếp hạng nhiều mã cổ phiếu (xếp hạng, ranking, top, "
    "cao nhất, thấp nhất, best, worst)\n"
    "- financial_ratio: tỷ lệ tài chính (PE, PB, ROE, EPS, ROA, "
    "chỉ số tài chính, debt_to_equity, dividend_yield)\n"
    "- news_sentiment: tin tức và tâm lý thị trường (news, sentiment, "
    "tin tức, social volume, mặt bằng chung)\n"
    "- portfolio: quản lý danh mục đầu tư (portfolio, danh mục, "
    "cổ phiếu của tôi, tài sản)\n"
    "- alert: cảnh báo giá, khối lượng khi vượt ngưỡng (alert, cảnh báo, "
    "threshold, ngưỡng, vượt quá)\n"
    "- forecast: dự báo giá cổ phiếu, xu hướng (forecast, dự báo, "
    "xu hướng, predict, prediction)\n"
    "- sector: phân tích theo ngành (sector, ngành, banking, real estate, "
    "industry, nhóm ngành)\n\n"
    "Chỉ trả về JSON:\n"
    '{"intent": "price|aggregate|compare|indicator|company|ranking|'
    'financial_ratio|news_sentiment|portfolio|alert|forecast|sector"}\n\n'
    "Không giải thích gì thêm."
)

_VALID_INTENTS = (
    "price", "aggregate", "compare", "indicator", "company", "ranking",
    "financial_ratio", "news_sentiment", "portfolio", "alert", "forecast", "sector"
)

_INTENT_FALLBACK_KEYWORDS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("company", ("cổ đông", "ban lãnh đạo", "công ty con", "shareholders",
                 "executives", "subsidiaries", "hội đồng quản trị", "ban điều hành")),
    ("ranking", ("xếp hạng", "ranking", "top", "cao nhất", "thấp nhất", "best", "worst",
                 "xếp loại")),
    ("financial_ratio", ("tỷ lệ tài chính", "chỉ số tài chính", "pe", "pb", "roe",
                         "eps", "roa", "debt_to_equity", "dividend_yield",
                         "operating_margin", "p/e", "p/b")),
    ("news_sentiment", ("tin tức", "news", "sentiment", "social volume",
                        "tâm lý thị trường", "mặt bằng chung")),
    ("portfolio", ("danh mục", "portfolio", "cổ phiếu của tôi", "tài sản của tôi",
                   "tôi đang nắm giữ")),
    ("alert", ("cảnh báo", "alert", "ngưỡng", "threshold", "vượt quá",
               "khi nào", "nếu giá")),
    ("forecast", ("dự báo", "forecast", "xu hướng", "predict", "prediction",
                  "dự đoán")),
    ("sector", ("ngành", "sector", "banking", "real estate", "industry",
                "nhóm ngành", "bất động sản", "ngân hàng")),
    ("aggregate", ("tổng", "sum", "trung bình", "mean", "avg", "bình quân",
                   "nhỏ nhất", "lớn nhất", "min", "max", "median")),
    ("compare", ("so sánh", "compare", "vs", "với")),
    ("indicator", ("sma", "rsi", "macd", "ma", "chỉ báo", "bb", "bollinger",
                   "stochastic", "adx", "atr", "obv", "cci")),
    ("price", ("giá", "open", "close", "volume", "ohlcv", "mở cửa", "đóng cửa")),
)


class IntentClassificationResult:
    def __init__(self, intent: str, raw: Optional[str] = None):
        self.intent = intent
        self.raw = raw

    def to_dict(self) -> Dict[str, str]:
        return {"intent": self.intent}


class IntentClassifier:
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self._llm_provider = llm_provider or LLMProvider()

    def classify(self, query: str) -> IntentClassificationResult:
        system_msg = SystemMessage(content=_INTENT_SYSTEM_PROMPT)
        human_msg = HumanMessage(content=query)

        try:
            response = self._llm_provider.invoke_with_fallback(
                [system_msg, human_msg]
            )
        except Exception:
            intent = self._fallback_classify(query)
            return IntentClassificationResult(intent=intent, raw=None)

        raw = (response.content or "").strip()
        intent = self._parse_intent(raw)
        if intent not in _VALID_INTENTS:
            intent = self._fallback_classify(query)
        return IntentClassificationResult(intent=intent, raw=raw)

    def _fallback_classify(self, query: str) -> str:
        query_lower = query.lower()
        for intent, keywords in _INTENT_FALLBACK_KEYWORDS:
            for kw in keywords:
                if kw in query_lower:
                    return intent
        return "price"

    @staticmethod
    def _parse_intent(raw: str) -> str:
        import json
        import re

        json_match = re.search(r'\{"intent"\s*:\s*"([^"]+)"\}', raw)
        if json_match:
            return json_match.group(1)

        if "{" in raw:
            try:
                obj = json.loads(raw[raw.index("{"):raw.rindex("}") + 1])
                return obj.get("intent", "price")
            except (json.JSONDecodeError, ValueError):
                pass

        raw_lower = raw.lower()
        for intent in _VALID_INTENTS:
            if intent in raw_lower:
                return intent

        return "price"
