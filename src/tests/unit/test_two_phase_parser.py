from infrastructure.llm.intent_classifier import IntentClassifier, _VALID_INTENTS
from infrastructure.llm.two_phase_parser import TwoPhaseParser, _INTENT_TO_QUERY_TYPE, _INTENT_TO_EXTRACTOR
from infrastructure.llm.extractors import (
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
)
from infrastructure.llm.extractors.aggregate_extractor import AggregateParams
from infrastructure.llm.extractors.comparison_extractor import ComparisonParams
from infrastructure.llm.extractors.indicator_extractor import IndicatorParams
from infrastructure.llm.extractors.price_extractor import PriceParams
from infrastructure.llm.extractors.company_extractor import CompanyParams
from infrastructure.llm.extractors.ranking_extractor import RankingParams
from infrastructure.llm.extractors.financial_ratio_extractor import FinancialRatioParams
from infrastructure.llm.extractors.news_sentiment_extractor import NewsSentimentParams
from infrastructure.llm.extractors.portfolio_extractor import PortfolioParams
from infrastructure.llm.extractors.alert_extractor import AlertParams
from infrastructure.llm.extractors.forecast_extractor import ForecastParams
from infrastructure.llm.extractors.sector_extractor import SectorParams
from infrastructure.llm.extractors import BaseExtractor


class TestIntentClassifier:
    def test_parse_intent_aggregate(self):
        assert IntentClassifier._parse_intent('{"intent": "aggregate"}') == "aggregate"

    def test_parse_intent_compare(self):
        assert IntentClassifier._parse_intent('{"intent": "compare"}') == "compare"

    def test_parse_intent_indicator(self):
        assert IntentClassifier._parse_intent('{"intent": "indicator"}') == "indicator"

    def test_parse_intent_price(self):
        assert IntentClassifier._parse_intent('{"intent": "price"}') == "price"

    def test_parse_intent_company(self):
        assert IntentClassifier._parse_intent('{"intent": "company"}') == "company"

    def test_parse_intent_ranking(self):
        assert IntentClassifier._parse_intent('{"intent": "ranking"}') == "ranking"

    def test_parse_intent_financial_ratio(self):
        assert IntentClassifier._parse_intent('{"intent": "financial_ratio"}') == "financial_ratio"

    def test_parse_intent_news_sentiment(self):
        assert IntentClassifier._parse_intent('{"intent": "news_sentiment"}') == "news_sentiment"

    def test_parse_intent_portfolio(self):
        assert IntentClassifier._parse_intent('{"intent": "portfolio"}') == "portfolio"

    def test_parse_intent_alert(self):
        assert IntentClassifier._parse_intent('{"intent": "alert"}') == "alert"

    def test_parse_intent_forecast(self):
        assert IntentClassifier._parse_intent('{"intent": "forecast"}') == "forecast"

    def test_parse_intent_sector(self):
        assert IntentClassifier._parse_intent('{"intent": "sector"}') == "sector"

    def test_parse_intent_all_valid(self):
        for intent in _VALID_INTENTS:
            assert IntentClassifier._parse_intent(f'{{"intent": "{intent}"}}') == intent

    def test_parse_intent_fallback_price(self):
        assert IntentClassifier._parse_intent("invalid json") == "price"

    def test_parse_intent_empty_fallback(self):
        assert IntentClassifier._parse_intent("") == "price"

    def test_parse_intent_with_extra_text(self):
        result = IntentClassifier._parse_intent(
            'Here is the result: {"intent": "aggregate"}'
        )
        assert result == "aggregate"

    def test_parse_intent_corrupted_json_fallback(self):
        assert IntentClassifier._parse_intent("not a json at all") == "price"

    def test_classify_fallback_keyword_company(self):
        classifier = IntentClassifier()
        result = classifier._fallback_classify("Cổ đông lớn nhất của VNM là ai?")
        assert result == "company"

    def test_classify_fallback_keyword_ranking(self):
        classifier = IntentClassifier()
        result = classifier._fallback_classify("Xếp hạng các mã FPT, MWG, VNM")
        assert result == "ranking"

    def test_classify_fallback_keyword_sector(self):
        classifier = IntentClassifier()
        result = classifier._fallback_classify("Hiệu suất ngành ngân hàng thế nào?")
        assert result == "sector"

    def test_classify_fallback_default_price(self):
        classifier = IntentClassifier()
        result = classifier._fallback_classify("một câu hỏi không xác định abcxyz")
        assert result == "price"


class TestExtractorParams:
    def test_aggregate_params_defaults(self):
        p = AggregateParams(tickers=["VCB"])
        assert p.tickers == ["VCB"]
        assert p.aggregate == "mean"
        assert p.requested_field == "close"
        assert p.days is None

    def test_aggregate_params_full(self):
        p = AggregateParams(
            tickers=["HPG"],
            aggregate="sum",
            requested_field="volume",
            weeks=1,
        )
        assert p.aggregate == "sum"
        assert p.weeks == 1

    def test_aggregate_to_dict(self):
        p = AggregateParams(tickers=["VCB"], aggregate="min", days=10)
        d = AggregateExtractor._to_dict(p)
        assert d["tickers"] == ["VCB"]
        assert d["aggregate"] == "min"
        assert d["days"] == 10
        assert d["requested_field"] == "close"

    def test_comparison_params_defaults(self):
        p = ComparisonParams(tickers=["VIC"], compare_with=["HPG"])
        assert p.requested_field == "close"

    def test_comparison_params_full(self):
        p = ComparisonParams(
            tickers=["TCB"],
            compare_with=["MBB"],
            requested_field="open",
            days=5,
        )
        assert p.requested_field == "open"
        assert p.days == 5

    def test_comparison_to_dict(self):
        p = ComparisonParams(
            tickers=["VIC"], compare_with=["HPG"], requested_field="volume", weeks=1
        )
        d = ComparisonExtractor._to_dict(p)
        assert d["compare_with"] == ["HPG"]
        assert d["requested_field"] == "volume"
        assert d["weeks"] == 1

    def test_indicator_params_defaults(self):
        p = IndicatorParams(tickers=["VCB"], indicator_type="sma")
        assert p.indicator_period is None

    def test_indicator_params_with_period(self):
        p = IndicatorParams(
            tickers=["VCB"], indicator_type="sma", indicator_period=9, weeks=1
        )
        assert p.indicator_period == 9

    def test_indicator_to_dict(self):
        p = IndicatorParams(
            tickers=["VCB"], indicator_type="sma", indicator_period=9, weeks=2
        )
        d = IndicatorExtractor._to_dict(p)
        assert d["indicator_params"] == {"sma": [9]}
        assert d["weeks"] == 2
        assert d["requested_field"] == "sma"

    def test_indicator_to_dict_no_period(self):
        p = IndicatorParams(tickers=["VCB"], indicator_type="rsi")
        d = IndicatorExtractor._to_dict(p)
        assert d["indicator_params"] == {}
        assert d["requested_field"] == "rsi"

    def test_price_params_defaults(self):
        p = PriceParams(tickers=["VCB"])
        assert p.requested_field == "close"
        assert p.days is None

    def test_price_params_full(self):
        p = PriceParams(tickers=["VCB"], requested_field="ohlcv", days=10)
        assert p.requested_field == "ohlcv"
        assert p.days == 10

    def test_price_to_dict(self):
        p = PriceParams(tickers=["HPG"], requested_field="open", days=1)
        d = PriceExtractor._to_dict(p)
        assert d["tickers"] == ["HPG"]
        assert d["requested_field"] == "open"
        assert d["days"] == 1


    def test_company_params_defaults(self):
        p = CompanyParams(tickers=["VNM"])
        assert p.requested_field == "shareholders"

    def test_company_to_dict(self):
        p = CompanyParams(tickers=["VNM"], requested_field="executives")
        d = CompanyExtractor._to_dict(p)
        assert d["query_type"] == "company_query"
        assert d["tickers"] == ["VNM"]
        assert d["requested_field"] == "executives"

    def test_ranking_params_defaults(self):
        p = RankingParams(tickers=["FPT", "MWG"])
        assert p.requested_field == "close"
        assert p.aggregate == "max"

    def test_ranking_to_dict(self):
        p = RankingParams(tickers=["FPT", "MWG", "VNM"], requested_field="volume", aggregate="mean", weeks=2)
        d = RankingExtractor._to_dict(p)
        assert d["query_type"] == "ranking_query"
        assert d["tickers"] == ["FPT", "MWG", "VNM"]
        assert d["requested_field"] == "volume"
        assert d["aggregate"] == "mean"
        assert d["weeks"] == 2

    def test_financial_ratio_params_defaults(self):
        p = FinancialRatioParams(tickers=["VCB"])
        assert p.requested_field == "pe"
        assert p.period is None

    def test_financial_ratio_to_dict(self):
        p = FinancialRatioParams(tickers=["VCB"], requested_field="roe", period="quarter", quarter=1, year=2024)
        d = FinancialRatioExtractor._to_dict(p)
        assert d["query_type"] == "financial_ratio_query"
        assert d["requested_field"] == "roe"
        assert d["period"] == "quarter"
        assert d["quarter"] == 1
        assert d["year"] == 2024

    def test_news_sentiment_params_defaults(self):
        p = NewsSentimentParams(tickers=["VCB"])
        assert p.requested_field == "news"
        assert p.compare_with is None

    def test_news_sentiment_to_dict(self):
        p = NewsSentimentParams(tickers=["VIC"], requested_field="sentiment", compare_with=["VHM"], months=1)
        d = NewsSentimentExtractor._to_dict(p)
        assert d["query_type"] == "news_sentiment_query"
        assert d["compare_with"] == ["VHM"]
        assert d["months"] == 1

    def test_portfolio_params_defaults(self):
        p = PortfolioParams()
        assert p.requested_field == "portfolio_value"
        assert p.portfolio is None

    def test_portfolio_to_dict(self):
        p = PortfolioParams(requested_field="portfolio_performance", portfolio={"VCB": 1000})
        d = PortfolioExtractor._to_dict(p)
        assert d["query_type"] == "portfolio_query"
        assert d["portfolio"] == {"VCB": 1000}

    def test_alert_params_defaults(self):
        p = AlertParams(tickers=["VCB"], threshold=80000)
        assert p.condition == "above"
        assert p.timeframe == "1d"

    def test_alert_to_dict(self):
        p = AlertParams(tickers=["HPG"], threshold=25000, condition="below", timeframe="1h")
        d = AlertExtractor._to_dict(p)
        assert d["query_type"] == "alert_query"
        assert d["threshold"] == 25000
        assert d["condition"] == "below"
        assert d["timeframe"] == "1h"

    def test_forecast_params_defaults(self):
        p = ForecastParams(tickers=["VCB"])
        assert p.timeframe == "1w"
        assert p.model is None

    def test_forecast_to_dict(self):
        p = ForecastParams(tickers=["VIC"], timeframe="3M", model="sma")
        d = ForecastExtractor._to_dict(p)
        assert d["query_type"] == "forecast_query"
        assert d["timeframe"] == "3M"
        assert d["model"] == "sma"

    def test_sector_params_defaults(self):
        p = SectorParams(sector="banking")
        assert p.metric == "performance"
        assert p.timeframe == "1w"

    def test_sector_to_dict(self):
        p = SectorParams(sector="real estate", metric="volume", timeframe="1d")
        d = SectorExtractor._to_dict(p)
        assert d["query_type"] == "sector_query"
        assert d["sector"] == "real estate"
        assert d["metric"] == "volume"
        assert d["timeframe"] == "1d"


class TestTwoPhaseParserRouting:
    def test_intent_to_query_type_all_12(self):
        for intent, qtype in _INTENT_TO_QUERY_TYPE.items():
            assert intent in _VALID_INTENTS
            assert qtype.endswith("_query")

    def test_intent_to_extractor_all_12(self):
        for intent in _INTENT_TO_EXTRACTOR:
            assert issubclass(_INTENT_TO_EXTRACTOR[intent], BaseExtractor)

    def test_intent_to_query_type_mapping(self):
        assert _INTENT_TO_QUERY_TYPE["aggregate"] == "aggregate_query"
        assert _INTENT_TO_QUERY_TYPE["compare"] == "comparison_query"
        assert _INTENT_TO_QUERY_TYPE["indicator"] == "indicator_query"
        assert _INTENT_TO_QUERY_TYPE["price"] == "price_query"
        assert _INTENT_TO_QUERY_TYPE["company"] == "company_query"
        assert _INTENT_TO_QUERY_TYPE["ranking"] == "ranking_query"
        assert _INTENT_TO_QUERY_TYPE["financial_ratio"] == "financial_ratio_query"
        assert _INTENT_TO_QUERY_TYPE["news_sentiment"] == "news_sentiment_query"
        assert _INTENT_TO_QUERY_TYPE["portfolio"] == "portfolio_query"
        assert _INTENT_TO_QUERY_TYPE["alert"] == "alert_query"
        assert _INTENT_TO_QUERY_TYPE["forecast"] == "forecast_query"
        assert _INTENT_TO_QUERY_TYPE["sector"] == "sector_query"


class TestExtractorFallbackDicts:
    def test_aggregate_to_dict_minimal(self):
        p = AggregateParams(tickers=[], aggregate="mean")
        d = AggregateExtractor._to_dict(p)
        assert d["tickers"] == []
        assert d["aggregate"] == "mean"

    def test_comparison_to_dict_minimal(self):
        p = ComparisonParams(tickers=[], compare_with=[])
        d = ComparisonExtractor._to_dict(p)
        assert d["tickers"] == []
        assert d["compare_with"] == []

    def test_indicator_to_dict_minimal(self):
        p = IndicatorParams(tickers=[], indicator_type="sma")
        d = IndicatorExtractor._to_dict(p)
        assert d["indicator_params"] == {}

    def test_price_to_dict_minimal(self):
        p = PriceParams(tickers=[])
        d = PriceExtractor._to_dict(p)
        assert d["tickers"] == []

    def test_company_to_dict_minimal(self):
        p = CompanyParams(tickers=[])
        d = CompanyExtractor._to_dict(p)
        assert d["tickers"] == []
        assert d["requested_field"] == "shareholders"

    def test_ranking_to_dict_minimal(self):
        p = RankingParams(tickers=[], aggregate="latest")
        d = RankingExtractor._to_dict(p)
        assert d["tickers"] == []
        assert d["aggregate"] == "latest"

    def test_financial_ratio_to_dict_minimal(self):
        p = FinancialRatioParams(tickers=[])
        d = FinancialRatioExtractor._to_dict(p)
        assert d["tickers"] == []
        assert d["requested_field"] == "pe"

    def test_news_sentiment_to_dict_minimal(self):
        p = NewsSentimentParams(tickers=[])
        d = NewsSentimentExtractor._to_dict(p)
        assert d["tickers"] == []

    def test_portfolio_to_dict_minimal(self):
        p = PortfolioParams()
        d = PortfolioExtractor._to_dict(p)
        assert d["requested_field"] == "portfolio_value"

    def test_alert_to_dict_minimal(self):
        p = AlertParams(tickers=[], threshold=0)
        d = AlertExtractor._to_dict(p)
        assert d["threshold"] == 0
        assert d["condition"] == "above"

    def test_forecast_to_dict_minimal(self):
        p = ForecastParams(tickers=[])
        d = ForecastExtractor._to_dict(p)
        assert d["timeframe"] == "1w"

    def test_sector_to_dict_minimal(self):
        p = SectorParams(sector="")
        d = SectorExtractor._to_dict(p)
        assert d["sector"] == ""
        assert d["metric"] == "performance"