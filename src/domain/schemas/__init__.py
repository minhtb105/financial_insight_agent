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

from typing import Union
QueryParams = Union[
    PriceQueryParams, RankingQueryParams, ComparisonQueryParams,
    AggregateQueryParams, IndicatorQueryParams, CompanyQueryParams,
    FinancialRatioQueryParams, NewsSentimentQueryParams,
    PortfolioQueryParams, AlertQueryParams, ForecastQueryParams,
    SectorQueryParams
]