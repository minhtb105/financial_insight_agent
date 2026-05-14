from typing import Dict, Any, Optional

from .intent_classifier import IntentClassifier
from .extractors import (
    AggregateExtractor,
    ComparisonExtractor,
    IndicatorExtractor,
    PriceExtractor,
    CompanyExtractor,
    RankingExtractor,
    FinancialRatioExtractor,
    NewsSentimentExtractor,
    PortfolioExtractor,
    AlertExtractor,
    ForecastExtractor,
    SectorExtractor,
    BaseExtractor,
)
from infrastructure.llm.llm_provider import LLMProvider


_INTENT_TO_QUERY_TYPE = {
    "price": "price_query",
    "aggregate": "aggregate_query",
    "compare": "comparison_query",
    "indicator": "indicator_query",
    "company": "company_query",
    "ranking": "ranking_query",
    "financial_ratio": "financial_ratio_query",
    "news_sentiment": "news_sentiment_query",
    "portfolio": "portfolio_query",
    "alert": "alert_query",
    "forecast": "forecast_query",
    "sector": "sector_query",
}

_INTENT_TO_EXTRACTOR: Dict[str, type[BaseExtractor]] = {
    "price": PriceExtractor,
    "aggregate": AggregateExtractor,
    "compare": ComparisonExtractor,
    "indicator": IndicatorExtractor,
    "company": CompanyExtractor,
    "ranking": RankingExtractor,
    "financial_ratio": FinancialRatioExtractor,
    "news_sentiment": NewsSentimentExtractor,
    "portfolio": PortfolioExtractor,
    "alert": AlertExtractor,
    "forecast": ForecastExtractor,
    "sector": SectorExtractor,
}


class TwoPhaseParser:
    def __init__(self, llm_provider: Optional[LLMProvider] = None):
        self._llm_provider = llm_provider or LLMProvider()
        self._classifier = IntentClassifier(llm_provider=self._llm_provider)
        self._extractors: Dict[str, BaseExtractor] = {}

    def _get_extractor(self, intent: str) -> BaseExtractor:
        if intent not in self._extractors:
            cls = _INTENT_TO_EXTRACTOR.get(intent, PriceExtractor)
            self._extractors[intent] = cls(llm_provider=self._llm_provider)
        return self._extractors[intent]

    def parse(self, query: str) -> Dict[str, Any]:
        intent_result = self._classifier.classify(query)
        intent = intent_result.intent

        extractor = self._get_extractor(intent)
        params = extractor.extract(query)

        query_type = _INTENT_TO_QUERY_TYPE.get(intent, "price_query")
        params["query_type"] = query_type

        return params
