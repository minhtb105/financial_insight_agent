from typing import Dict, Any, Optional
from domain.schemas.price import PriceQueryParams
from domain.schemas.ranking import RankingQueryParams
from domain.schemas.comparison import ComparisonQueryParams
from domain.schemas.aggregate import AggregateQueryParams
from domain.schemas.indicator import IndicatorQueryParams
from domain.schemas.company import CompanyQueryParams
from domain.schemas.financial_ratio import FinancialRatioQueryParams
from domain.schemas.news_sentiment import NewsSentimentQueryParams
from domain.schemas.portfolio import PortfolioQueryParams
from domain.schemas.alert import AlertQueryParams
from domain.schemas.forecast import ForecastQueryParams
from domain.schemas.sector import SectorQueryParams
from pydantic import ValidationError


class TypeValidator:
    """Base validator for query type schemas."""
    
    def validate(self, parsed: Dict[str, Any]) -> Optional[str]:
        try:
            self._get_schema()(**parsed)
            return None
        except ValidationError as e:
            return "; ".join(f"{err['loc']}: {err['msg']}" for err in e.errors())

    def _get_schema(self):
        raise NotImplementedError


class PriceQueryValidator(TypeValidator):
    def _get_schema(self):
        return PriceQueryParams


class RankingQueryValidator(TypeValidator):
    def _get_schema(self):
        return RankingQueryParams


class ComparisonQueryValidator(TypeValidator):
    def _get_schema(self):
        return ComparisonQueryParams


class AggregateQueryValidator(TypeValidator):
    def _get_schema(self):
        return AggregateQueryParams


class IndicatorQueryValidator(TypeValidator):
    def _get_schema(self):
        return IndicatorQueryParams


class CompanyQueryValidator(TypeValidator):
    def _get_schema(self):
        return CompanyQueryParams


class FinancialRatioQueryValidator(TypeValidator):
    def _get_schema(self):
        return FinancialRatioQueryParams


class NewsSentimentQueryValidator(TypeValidator):
    def _get_schema(self):
        return NewsSentimentQueryParams


class PortfolioQueryValidator(TypeValidator):
    def _get_schema(self):
        return PortfolioQueryParams


class AlertQueryValidator(TypeValidator):
    def _get_schema(self):
        return AlertQueryParams


class ForecastQueryValidator(TypeValidator):
    def _get_schema(self):
        return ForecastQueryParams


class SectorQueryValidator(TypeValidator):
    def _get_schema(self):
        return SectorQueryParams


_TYPE_VALIDATORS: Dict[str, TypeValidator] = {
    "price_query": PriceQueryValidator(),
    "ranking_query": RankingQueryValidator(),
    "comparison_query": ComparisonQueryValidator(),
    "aggregate_query": AggregateQueryValidator(),
    "indicator_query": IndicatorQueryValidator(),
    "company_query": CompanyQueryValidator(),
    "financial_ratio_query": FinancialRatioQueryValidator(),
    "news_sentiment_query": NewsSentimentQueryValidator(),
    "portfolio_query": PortfolioQueryValidator(),
    "alert_query": AlertQueryValidator(),
    "forecast_query": ForecastQueryValidator(),
    "sector_query": SectorQueryValidator(),
}


def validate_parsed_query(parsed: Dict[str, Any]) -> Optional[str]:
    query_type = parsed.get("query_type", "price_query")
    validator = _TYPE_VALIDATORS.get(query_type)
    if validator is None:
        return f"Unknown query_type: {query_type}"
    return validator.validate(parsed)