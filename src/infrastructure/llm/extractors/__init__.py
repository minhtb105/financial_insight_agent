from typing import Dict, Any
from abc import ABC, abstractmethod


class BaseExtractor(ABC):
    @abstractmethod
    def extract(self, query: str) -> Dict[str, Any]:
        pass


from .aggregate_extractor import AggregateExtractor
from .comparison_extractor import ComparisonExtractor
from .indicator_extractor import IndicatorExtractor
from .price_extractor import PriceExtractor
from .company_extractor import CompanyExtractor
from .ranking_extractor import RankingExtractor
from .financial_ratio_extractor import FinancialRatioExtractor
from .news_sentiment_extractor import NewsSentimentExtractor
from .portfolio_extractor import PortfolioExtractor
from .alert_extractor import AlertExtractor
from .forecast_extractor import ForecastExtractor
from .sector_extractor import SectorExtractor

__all__ = [
    "BaseExtractor",
    "AggregateExtractor",
    "ComparisonExtractor",
    "IndicatorExtractor",
    "PriceExtractor",
    "CompanyExtractor",
    "RankingExtractor",
    "FinancialRatioExtractor",
    "NewsSentimentExtractor",
    "PortfolioExtractor",
    "AlertExtractor",
    "ForecastExtractor",
    "SectorExtractor",
]
