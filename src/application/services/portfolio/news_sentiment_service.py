import re
from datetime import datetime, timedelta, timezone
from typing import Any

from shared.base_service import BaseService
from shared.constants import NEWS_TTL_HOURS
from shared.ports.cache_port import CachePort
from shared.ports.news_port import NewsPort
from shared.utils.cache_keys import make_cache_key

_NEGATION_WORDS = frozenset({"không", "chẳng", "chưa", "đừng", "không phải", "không có", "not", "no", "never", "neither", "nor"})
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


_POSITIVE_KEYWORDS = {"tăng", "lợi nhuận", "doanh thu", "tích cực", "khả quan", "tăng trưởng", "mở rộng", "đầu tư", "cổ tức", "thưởng", "hợp tác", "chiến lược", "đột phá", "hiệu quả", "cải thiện", "phục hồi", "lãi", "thuận lợi", "triển vọng", "kỳ vọng", "mua vào", "outperform", "upgrade"}
_NEGATIVE_KEYWORDS = {"giảm", "lỗ", "thua lỗ", "rủi ro", "tiêu cực", "cảnh báo", "khó khăn", "suy thoái", "khủng hoảng", "phá sản", "kiện tụng", "cắt lỗ", "bán ra", "thoái vốn", "nợ xấu", "mất thanh khoản", "downgrade", "underperform"}


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
    def __init__(self, cache: CachePort, news_port: NewsPort) -> None:
        super().__init__("NewsSentimentService", cache)
        self._news = news_port

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
            except (ValueError, TypeError):
                filtered.append(a)
        return filtered

    def _fetch_single_news(self, ticker: str) -> list[dict[str, Any]]:
        cache_key = make_cache_key("news", ticker)
        cached = self._cache.get(cache_key)
        if cached is not None:
            return cached  # type: ignore
        articles = self._news.fetch_news(ticker)
        if not articles:
            self.logger.warning("No news found for %s", ticker)
        self._cache.set(cache_key, articles, ttl_hours=NEWS_TTL_HOURS)
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
                self.logger.error("Failed to fetch news for %s: %s", ticker, articles.get("error"))
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
                result[ticker] = {"news": articles, "sentiment": _calc_sentiment_from_articles(articles), "social_volume": len(articles)}
            return result
        except Exception as e:
            self.logger.error("Error analyzing news sentiment for %s: %s", tickers, e, exc_info=True)
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
            return sentiment_result.get("sentiment", {})
        except Exception as e:
            self.logger.error("Error comparing news sentiment: %s", e, exc_info=True)
            return {"error": str(e)}

    def handle_query(
        self,
        tickers: list[str],
        field: str = "all",
        compare_with: list[str] | None = None,
        days: int | None = None,
        weeks: int | None = None,
        months: int | None = None,
    ) -> dict[str, Any]:
        if not tickers:
            return {"error": "Missing ticker"}
        try:
            if compare_with and field not in (None, "sentiment", "all"):
                return {"error": "Comparison only supported for sentiment field"}
            if compare_with:
                return self.compare_news_sentiment({"tickers": tickers, "compare_with": compare_with})
            time_kw: dict[str, Any] = {}
            if days is not None:
                time_kw["days"] = days
            if weeks is not None:
                time_kw["weeks"] = weeks
            if months is not None:
                time_kw["months"] = months
            query = {"tickers": tickers}
            if field != "all":
                query["requested_field"] = field
            query.update(time_kw)
            dispatch = {"news": self.get_news_data, "sentiment": self.get_sentiment_data}
            return dispatch.get(field, self.analyze_news_sentiment)(query)
        except Exception as e:
            return {"error": str(e)}


def handle_news_sentiment_query(
    tickers: list[str],
    field: str = "all",
    compare_with: list[str] | None = None,
    days: int | None = None,
    weeks: int | None = None,
    months: int | None = None,
) -> dict[str, Any]:
    from shared.service_helpers import call_service
    return call_service("news", tickers=tickers, field=field, compare_with=compare_with, days=days, weeks=weeks, months=months)
