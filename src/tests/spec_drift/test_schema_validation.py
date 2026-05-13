import pytest
from pydantic import ValidationError
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


class TestPriceQueryParams:
    def test_valid_price_query(self):
        p = PriceQueryParams(tickers=["VCB"])
        assert p.query_type == "price_query"
        assert p.requested_field == "close"

    def test_valid_ohlcv(self):
        p = PriceQueryParams(tickers=["VCB"], requested_field="ohlcv", days=10)
        assert p.requested_field == "ohlcv"

    def test_invalid_field(self):
        with pytest.raises(ValidationError):
            PriceQueryParams(tickers=["VCB"], requested_field="invalid_field")

    def test_empty_tickers_fails(self):
        with pytest.raises(ValidationError):
            PriceQueryParams(tickers=[])

    def test_negative_days_fails(self):
        with pytest.raises(ValidationError):
            PriceQueryParams(tickers=["VCB"], days=-1)


class TestRankingQueryParams:
    def test_valid_ranking(self):
        p = RankingQueryParams(tickers=["VCB", "HPG"])
        assert p.aggregate == "max"

    def test_single_ticker_fails(self):
        with pytest.raises(ValidationError):
            RankingQueryParams(tickers=["VCB"])

    def test_invalid_aggregate(self):
        with pytest.raises(ValidationError):
            RankingQueryParams(tickers=["VCB", "HPG"], aggregate="invalid")


class TestComparisonQueryParams:
    def test_valid_comparison(self):
        p = ComparisonQueryParams(tickers=["VCB"], compare_with=["BID"])
        assert p.query_type == "comparison_query"

    def test_missing_compare_with_fails(self):
        with pytest.raises(ValidationError):
            ComparisonQueryParams(tickers=["VCB"])

    def test_empty_compare_with_fails(self):
        with pytest.raises(ValidationError):
            ComparisonQueryParams(tickers=["VCB"], compare_with=[])


class TestAggregateQueryParams:
    def test_valid_aggregate(self):
        p = AggregateQueryParams(tickers=["VCB", "HPG"])
        assert p.aggregate == "mean"

    def test_single_ticker_fails(self):
        with pytest.raises(ValidationError):
            AggregateQueryParams(tickers=["VCB"])

    def test_invalid_aggregate(self):
        with pytest.raises(ValidationError):
            AggregateQueryParams(tickers=["VCB", "HPG"], aggregate="invalid")


class TestIndicatorQueryParams:
    def test_valid_indicator(self):
        p = IndicatorQueryParams(tickers=["VCB"])
        assert p.requested_field == "sma"

    def test_valid_with_params(self):
        p = IndicatorQueryParams(tickers=["VCB"], indicator_params={"sma": [20]}, requested_field="sma")
        assert p.indicator_params == {"sma": [20]}

    def test_invalid_field(self):
        with pytest.raises(ValidationError):
            IndicatorQueryParams(tickers=["VCB"], requested_field="invalid")


class TestCompanyQueryParams:
    def test_valid_company(self):
        p = CompanyQueryParams(tickers=["VCB"])
        assert p.requested_field == "shareholders"

    def test_invalid_field(self):
        with pytest.raises(ValidationError):
            CompanyQueryParams(tickers=["VCB"], requested_field="invalid")


class TestFinancialRatioQueryParams:
    def test_valid_ratio(self):
        p = FinancialRatioQueryParams(tickers=["VCB"])
        assert p.requested_field == "pe"

    def test_invalid_field(self):
        with pytest.raises(ValidationError):
            FinancialRatioQueryParams(tickers=["VCB"], requested_field="invalid")

    def test_non_string_ticker(self):
        with pytest.raises(ValidationError):
            FinancialRatioQueryParams(tickers=[123])


class TestNewsSentimentQueryParams:
    def test_valid_news(self):
        p = NewsSentimentQueryParams(tickers=["VCB"])
        assert p.requested_field == "news"

    def test_invalid_field(self):
        with pytest.raises(ValidationError):
            NewsSentimentQueryParams(tickers=["VCB"], requested_field="invalid")

    def test_with_compare(self):
        p = NewsSentimentQueryParams(tickers=["VCB"], compare_with=["BID", "CTG"])
        assert p.compare_with == ["BID", "CTG"]


class TestPortfolioQueryParams:
    def test_valid_portfolio(self):
        p = PortfolioQueryParams()
        assert p.query_type == "portfolio_query"

    def test_with_portfolio(self):
        p = PortfolioQueryParams(portfolio={"FPT": 100, "VNM": 200})
        assert p.portfolio["FPT"] == 100

    def test_invalid_field(self):
        with pytest.raises(ValidationError):
            PortfolioQueryParams(requested_field="invalid_field")


class TestAlertQueryParams:
    def test_valid_alert(self):
        p = AlertQueryParams(tickers=["VCB"], threshold=100000.0)
        assert p.condition == "above"

    def test_missing_threshold_fails(self):
        with pytest.raises(ValidationError):
            AlertQueryParams(tickers=["VCB"])

    def test_invalid_condition(self):
        with pytest.raises(ValidationError):
            AlertQueryParams(tickers=["VCB"], threshold=100000.0, condition="invalid")


class TestForecastQueryParams:
    def test_valid_forecast(self):
        p = ForecastQueryParams(tickers=["VCB"])
        assert p.timeframe == "1w"

    def test_custom_timeframe(self):
        p = ForecastQueryParams(tickers=["VCB"], timeframe="1m")
        assert p.timeframe == "1m"


class TestSectorQueryParams:
    def test_valid_sector(self):
        p = SectorQueryParams(sector="banking")
        assert p.metric == "performance"

    def test_missing_sector_fails(self):
        with pytest.raises(ValidationError):
            SectorQueryParams()

    def test_invalid_metric(self):
        with pytest.raises(ValidationError):
            SectorQueryParams(sector="banking", metric="invalid")