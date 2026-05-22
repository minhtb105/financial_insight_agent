from typing import Any
import re
from datetime import datetime, timedelta, timezone
from shared.constants import NEWS_TTL_HOURS
from vnstock import Company
from infrastructure.cache import get_cache_manager
from infrastructure.cache.cache_keys import make_cache_key
from shared.base_service import BaseService

_NEGATION_WORDS = frozenset(
    {
        "không",
        "chẳng",
        "chưa",
        "đừng",
        "không phải",
        "không có",
        "not",
        "no",
        "never",
        "neither",
        "nor",
    }
)

_WORD_SPLIT = re.compile(r"\w+|[^\w\s]")


def _negation_in_prefix(prefix: list[str]) -> bool:
    for n in _NEGATION_WORDS:
        nt = n.split()
        if len(nt) == 1:
            if nt[0] in prefix:
                return True
        else:
            for j in range(len(prefix) - len(nt) + 1):
                if prefix[j : j + len(nt)] == nt:
                    return True
    return False


def _is_negated(keyword: str, text_lower: str, window: int = 3) -> bool:
    tokens = _WORD_SPLIT.findall(text_lower)
    kw_tokens = keyword.split()
    for i, tok in enumerate(tokens):
        if tok == kw_tokens[0] and tokens[i : i + len(kw_tokens)] == kw_tokens:
            start = max(0, i - window)
            prefix = tokens[start:i]
            if _negation_in_prefix(prefix):
                return True
    return False


_POSITIVE_KEYWORDS = {
    "tăng",
    "lợi nhuận",
    "doanh thu",
    "tích cực",
    "khả quan",
    "tăng trưởng",
    "mở rộng",
    "đầu tư",
    "cổ tức",
    "thưởng",
    "hợp tác",
    "chiến lược",
    "đột phá",
    "hiệu quả",
    "cải thiện",
    "phục hồi",
    "lãi",
    "thuận lợi",
    "triển vọng",
    "kỳ vọng",
    "mua vào",
    "outperform",
    "upgrade",
}

_NEGATIVE_KEYWORDS = {
    "giảm",
    "lỗ",
    "thua lỗ",
    "rủi ro",
    "tiêu cực",
    "cảnh báo",
    "khó khăn",
    "suy thoái",
    "khủng hoảng",
    "phá sản",
    "kiện tụng",
    "cắt lỗ",
    "bán ra",
    "thoái vốn",
    "nợ xấu",
    "mất thanh khoản",
    "downgrade",
    "underperform",
}


def _fetch_news_from_vnstock(ticker: str) -> list[dict[str, Any]]:
    try:
        company = Company(symbol=ticker, source="VCI")
        df = company.news()
        if df is None or df.empty:
            return []
        records = []
        for _, row in df.iterrows():
            records.append(
                {
                    "title": row.get("news_title", ""),
                    "content": row.get("news_short_content") or row.get("news_full_content", ""),
                    "source": row.get("news_source", ""),
                    "url": row.get("news_source_link", ""),
                    "date": row.get("public_date", ""),
                    "ticker": row.get("ticker", ticker),
                }
            )
        return records
    except Exception:
        return []


def _classify_sentiment(text: str) -> float:
    if not text:
        return 0.0
    text_lower = text.lower()
    pos_count = 0
    neg_count = 0
    for kw in _POSITIVE_KEYWORDS:
        if kw in text_lower:
            pos_count += -1 if _is_negated(kw, text_lower) else 1
    for kw in _NEGATIVE_KEYWORDS:
        if kw in text_lower:
            neg_count += -1 if _is_negated(kw, text_lower) else 1
    if pos_count < 0:
        neg_count += -pos_count
        pos_count = 0
    if neg_count < 0:
        pos_count += -neg_count
        neg_count = 0
    total = pos_count + neg_count
    if total == 0:
        return 0.0
    return round((pos_count - neg_count) / total, 4)


def _calc_sentiment_from_articles(articles: list[dict]) -> float:
    if not articles:
        return 0.0
    scores = []
    for a in articles:
        title_score = _classify_sentiment(a.get("title", ""))
        content_score = _classify_sentiment(a.get("content", ""))
        combined = title_score * 0.6 + content_score * 0.4
        scores.append(combined)
    return round(sum(scores) / len(scores), 4) if scores else 0.0


class NewsSentimentService(BaseService):
    def __init__(self) -> None:
        """Khởi tạo NewsSentimentService."""
        super().__init__("NewsSentimentService")

    def _filter_articles_by_time(self, articles: list[dict], query: dict) -> list[dict]:
        days = query.get("days")
        weeks = query.get("weeks")
        months = query.get("months")
        if not (days or weeks or months):
            return articles
        total_days = (days or 0) + (weeks or 0) * 7 + (months or 0) * 30
        cutoff = datetime.now(timezone.utc) - timedelta(days=total_days)
        filtered = []
        for a in articles:
            date_str = a.get("date", "")
            if not date_str:
                filtered.append(a)
                continue
            try:
                date_clean = date_str.replace("Z", "+00:00")
                if "+" not in date_clean and date_clean.endswith("Z"):
                    date_clean = date_clean.rstrip("Z") + "+00:00"
                article_date = datetime.fromisoformat(date_clean)
                if article_date.tzinfo is None:
                    article_date = article_date.replace(tzinfo=timezone.utc)
                if article_date >= cutoff:
                    filtered.append(a)
                else:
                    continue
            except (ValueError, TypeError):
                filtered.append(a)
        return filtered

    def _fetch_single_news(self, ticker: str) -> list[dict[str, Any]]:
        cm = self._get_cache_manager()
        cache_key = make_cache_key("news", ticker)
        cached = cm.get(cache_key) if cm else None
        if cached:
            return cached
        articles = _fetch_news_from_vnstock(ticker)
        if not articles:
            self.logger.warning(f"No news found for {ticker}")
        if cm:
            cm.set(cache_key, articles, ttl_hours=NEWS_TTL_HOURS)
        return articles

    def get_news_data(self, query: dict) -> dict[str, Any]:
        tickers = query.get("tickers", [])
        if not tickers:
            return {"news": {}, "note": "No tickers provided"}
        raw = self.for_each_ticker(tickers, self._fetch_single_news)
        result = {}
        for ticker in tickers:
            articles = raw.get(ticker, [])
            if isinstance(articles, dict) and "error" in articles:
                self.logger.error(f"Failed to fetch news for {ticker}: {articles.get('error')}")
                result[ticker] = []
            else:
                articles = articles if articles else []
                result[ticker] = self._filter_articles_by_time(articles, query)
        return {"news": result}

    def get_sentiment_data(self, query: dict) -> dict[str, Any]:
        tickers = query.get("tickers", [])
        if not tickers:
            return {"sentiment": {}, "note": "No tickers provided"}
        news_result = self.get_news_data(query)
        news_by_ticker = news_result.get("news", {})
        sentiment = {}
        for ticker in tickers:
            articles = news_by_ticker.get(ticker, [])
            sentiment[ticker] = _calc_sentiment_from_articles(articles)
        return {"sentiment": sentiment}

    def analyze_news_sentiment(self, query: dict) -> dict[str, Any]:
        """Phân tích tin tức và cảm xúc thị trường cho danh sách mã chứng khoán.

        Args:
            query: Dict chứa tham số truy vấn (tickers, ...).

        Returns:
            Dict chứa tin tức, điểm cảm xúc và khối lượng xã hội cho từng mã.
        """
        tickers = query.get("tickers", [])
        err = self._require_tickers(tickers)
        if err:
            return err
        try:
            news_data = self.get_news_data(query)
            news_by_ticker = news_data.get("news", {})

            result = {}
            for ticker in tickers:
                articles = news_by_ticker.get(ticker, [])
                result[ticker] = {
                    "news": articles,
                    "sentiment": _calc_sentiment_from_articles(articles),
                    "social_volume": len(articles),
                }
            return result
        except Exception as e:
            self.logger.error(
                "Error analyzing news sentiment for %s: %s", tickers, e, exc_info=True
            )
            return {"error": str(e)}

    def compare_news_sentiment(self, query: dict) -> dict[str, Any]:
        tickers = query.get("tickers", [])
        err = self._require_tickers(tickers)
        if err:
            return err
        compare_tickers = query.get("compare_with", [])
        all_tickers = list(set(tickers + compare_tickers))
        if not all_tickers:
            return {"error": "No tickers to compare"}
        try:
            sentiment_result = self.get_sentiment_data({"tickers": all_tickers})
            sentiment_by_ticker = sentiment_result.get("sentiment", {})
            return sentiment_by_ticker
        except Exception as e:
            self.logger.error(f"Error comparing news sentiment: {e}", exc_info=True)
            return {"error": str(e)}

_news_sentiment_service = NewsSentimentService()


def handle_news_sentiment_query(
    tickers: list[str],
    field: str = "all",
    compare_with: list[str] | None = None,
    days: int | None = None,
    weeks: int | None = None,
    months: int | None = None,
) -> dict[str, Any]:
    """Fetch news and market sentiment for tickers."""
    if not tickers:
        return {"error": "Missing ticker"}
    svc = _news_sentiment_service
    requested_field = field if field != "all" else None
    try:
        if compare_with and requested_field not in (None, "sentiment"):
            return {"error": "Comparison only supported for sentiment field"}
        if compare_with:
            return svc.compare_news_sentiment(
                {"tickers": tickers, "compare_with": compare_with}
            )
        time_kw: dict[str, Any] = {}
        if days is not None:
            time_kw["days"] = days
        if weeks is not None:
            time_kw["weeks"] = weeks
        if months is not None:
            time_kw["months"] = months
        query = {"tickers": tickers}
        if requested_field:
            query["requested_field"] = requested_field
        query.update(time_kw)
        dispatch = {
            "news": svc.get_news_data,
            "sentiment": svc.get_sentiment_data,
        }
        return dispatch.get(requested_field, svc.analyze_news_sentiment)(query)
    except Exception as e:
        return {"error": str(e)}
