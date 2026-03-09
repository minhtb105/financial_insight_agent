"""
Unit tests for portfolio services.
Uses relative imports for proper module resolution.
"""

from ...domain.services.portfolio.news_sentiment_service import NewsSentimentService
from ...domain.services.portfolio.news_sentiment_service import PortfolioService


class TestNewsSentimentService:
    """Test news sentiment service."""
    
    def __init__(self):
        self.service = NewsSentimentService()
    
    def test_get_news_sentiment(self):
        """Test news sentiment analysis."""
        test_cases = [
            {
                "ticker": "VNM",
                "time_range": "1 tuần",
                "expected_keys": ["sentiment_score", "news_count", "positive_news", "negative_news"]
            },
            {
                "ticker": "HPG",
                "time_range": "1 tháng",
                "expected_keys": ["sentiment_score", "news_count", "positive_news", "negative_news"]
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.get_news_sentiment(
                    test_case["ticker"],
                    test_case["time_range"]
                )
                success = all(key in result for key in test_case["expected_keys"])
                
                results.append({
                    "ticker": test_case["ticker"],
                    "time_range": test_case["time_range"],
                    "result": result,
                    "expected_keys": test_case["expected_keys"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: News sentiment for {test_case['ticker']}")
                print(f"  Expected keys: {test_case['expected_keys']}")
                print(f"  Got keys: {list(result.keys()) if result else 'None'}")
                
            except Exception as e:
                results.append({
                    "ticker": test_case["ticker"],
                    "time_range": test_case["time_range"],
                    "result": None,
                    "expected_keys": test_case["expected_keys"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: News sentiment for {test_case['ticker']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_get_sector_sentiment(self):
        """Test sector sentiment analysis."""
        test_cases = [
            {
                "sector": "ngân hàng",
                "time_range": "1 tuần",
                "expected_keys": ["sector_sentiment", "sector_tickers", "sector_performance"]
            },
            {
                "sector": "bất động sản",
                "time_range": "1 tháng",
                "expected_keys": ["sector_sentiment", "sector_tickers", "sector_performance"]
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.get_sector_sentiment(
                    test_case["sector"],
                    test_case["time_range"]
                )
                success = all(key in result for key in test_case["expected_keys"])
                
                results.append({
                    "sector": test_case["sector"],
                    "time_range": test_case["time_range"],
                    "result": result,
                    "expected_keys": test_case["expected_keys"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Sector sentiment for {test_case['sector']}")
                print(f"  Expected keys: {test_case['expected_keys']}")
                print(f"  Got keys: {list(result.keys()) if result else 'None'}")
                
            except Exception as e:
                results.append({
                    "sector": test_case["sector"],
                    "time_range": test_case["time_range"],
                    "result": None,
                    "expected_keys": test_case["expected_keys"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Sector sentiment for {test_case['sector']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_get_market_sentiment(self):
        """Test market sentiment analysis."""
        test_cases = [
            {
                "time_range": "1 tuần",
                "expected_keys": ["market_sentiment", "market_trend", "market_volume"]
            },
            {
                "time_range": "1 tháng",
                "expected_keys": ["market_sentiment", "market_trend", "market_volume"]
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.get_market_sentiment(test_case["time_range"])
                success = all(key in result for key in test_case["expected_keys"])
                
                results.append({
                    "time_range": test_case["time_range"],
                    "result": result,
                    "expected_keys": test_case["expected_keys"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Market sentiment for {test_case['time_range']}")
                print(f"  Expected keys: {test_case['expected_keys']}")
                print(f"  Got keys: {list(result.keys()) if result else 'None'}")
                
            except Exception as e:
                results.append({
                    "time_range": test_case["time_range"],
                    "result": None,
                    "expected_keys": test_case["expected_keys"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Market sentiment for {test_case['time_range']}")
                print(f"  Error: {e}")
        
        return results


class TestPortfolioService:
    """Test portfolio service."""
    
    def __init__(self):
        self.service = PortfolioService()
    
    def test_calculate_portfolio_performance(self):
        """Test portfolio performance calculation."""
        test_cases = [
            {
                "portfolio": {
                    "VNM": 100,
                    "HPG": 200,
                    "VIC": 50
                },
                "time_range": "1 tuần",
                "expected_keys": ["total_value", "total_return", "daily_returns", "portfolio_performance"]
            },
            {
                "portfolio": {
                    "VCB": 150,
                    "BID": 100,
                    "CTG": 75
                },
                "time_range": "1 tháng",
                "expected_keys": ["total_value", "total_return", "daily_returns", "portfolio_performance"]
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.calculate_portfolio_performance(
                    test_case["portfolio"],
                    test_case["time_range"]
                )
                success = all(key in result for key in test_case["expected_keys"])
                
                results.append({
                    "portfolio": test_case["portfolio"],
                    "time_range": test_case["time_range"],
                    "result": result,
                    "expected_keys": test_case["expected_keys"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Portfolio performance calculation")
                print(f"  Expected keys: {test_case['expected_keys']}")
                print(f"  Got keys: {list(result.keys()) if result else 'None'}")
                
            except Exception as e:
                results.append({
                    "portfolio": test_case["portfolio"],
                    "time_range": test_case["time_range"],
                    "result": None,
                    "expected_keys": test_case["expected_keys"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Portfolio performance calculation")
                print(f"  Error: {e}")
        
        return results
    
    def test_calculate_portfolio_allocation(self):
        """Test portfolio allocation calculation."""
        test_cases = [
            {
                "portfolio": {
                    "VNM": 100,
                    "HPG": 200,
                    "VIC": 50
                },
                "expected_keys": ["sector_allocation", "ticker_allocation", "allocation_percentage"]
            },
            {
                "portfolio": {
                    "VCB": 150,
                    "BID": 100,
                    "CTG": 75
                },
                "expected_keys": ["sector_allocation", "ticker_allocation", "allocation_percentage"]
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.calculate_portfolio_allocation(test_case["portfolio"])
                success = all(key in result for key in test_case["expected_keys"])
                
                results.append({
                    "portfolio": test_case["portfolio"],
                    "result": result,
                    "expected_keys": test_case["expected_keys"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Portfolio allocation calculation")
                print(f"  Expected keys: {test_case['expected_keys']}")
                print(f"  Got keys: {list(result.keys()) if result else 'None'}")
                
            except Exception as e:
                results.append({
                    "portfolio": test_case["portfolio"],
                    "result": None,
                    "expected_keys": test_case["expected_keys"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Portfolio allocation calculation")
                print(f"  Error: {e}")
        
        return results
    
    def test_get_portfolio_holdings(self):
        """Test portfolio holdings retrieval."""
        test_cases = [
            {
                "portfolio": {
                    "VNM": 100,
                    "HPG": 200,
                    "VIC": 50
                },
                "expected_keys": ["holdings", "total_value", "current_prices"]
            },
            {
                "portfolio": {
                    "VCB": 150,
                    "BID": 100,
                    "CTG": 75
                },
                "expected_keys": ["holdings", "total_value", "current_prices"]
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.get_portfolio_holdings(test_case["portfolio"])
                success = all(key in result for key in test_case["expected_keys"])
                
                results.append({
                    "portfolio": test_case["portfolio"],
                    "result": result,
                    "expected_keys": test_case["expected_keys"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Portfolio holdings retrieval")
                print(f"  Expected keys: {test_case['expected_keys']}")
                print(f"  Got keys: {list(result.keys()) if result else 'None'}")
                
            except Exception as e:
                results.append({
                    "portfolio": test_case["portfolio"],
                    "result": None,
                    "expected_keys": test_case["expected_keys"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Portfolio holdings retrieval")
                print(f"  Error: {e}")
        
        return results


def main():
    """Main test runner for portfolio services."""
    print("=== PORTFOLIO SERVICES TESTS ===\n")
    
    # Test News Sentiment Service
    print("1. Testing News Sentiment Service...")
    news_service = TestNewsSentimentService()
    news_results = {
        "news_sentiment": news_service.test_get_news_sentiment(),
        "sector_sentiment": news_service.test_get_sector_sentiment(),
        "market_sentiment": news_service.test_get_market_sentiment()
    }
    
    # Test Portfolio Service
    print("\n2. Testing Portfolio Service...")
    portfolio_service = TestPortfolioService()
    portfolio_results = {
        "performance": portfolio_service.test_calculate_portfolio_performance(),
        "allocation": portfolio_service.test_calculate_portfolio_allocation(),
        "holdings": portfolio_service.test_get_portfolio_holdings()
    }
    
    # Generate comprehensive report
    _generate_comprehensive_report(news_results, portfolio_results)
    
    return {
        "news_sentiment": news_results,
        "portfolio": portfolio_results
    }


def _generate_comprehensive_report(news_results, portfolio_results):
    """Generate comprehensive test report."""
    print("\n" + "="*60)
    print("PORTFOLIO SERVICES TEST REPORT")
    print("="*60)
    
    # News Sentiment Service report
    print(f"\n1. NEWS SENTIMENT SERVICE:")
    news_sentiment_total = len(news_results["news_sentiment"])
    news_sentiment_passed = sum(1 for r in news_results["news_sentiment"] if r["success"])
    print(f"   News Sentiment: {news_sentiment_passed}/{news_sentiment_total} passed")
    
    sector_sentiment_total = len(news_results["sector_sentiment"])
    sector_sentiment_passed = sum(1 for r in news_results["sector_sentiment"] if r["success"])
    print(f"   Sector Sentiment: {sector_sentiment_passed}/{sector_sentiment_total} passed")
    
    market_sentiment_total = len(news_results["market_sentiment"])
    market_sentiment_passed = sum(1 for r in news_results["market_sentiment"] if r["success"])
    print(f"   Market Sentiment: {market_sentiment_passed}/{market_sentiment_total} passed")
    
    # Portfolio Service report
    print(f"\n2. PORTFOLIO SERVICE:")
    performance_total = len(portfolio_results["performance"])
    performance_passed = sum(1 for r in portfolio_results["performance"] if r["success"])
    print(f"   Portfolio Performance: {performance_passed}/{performance_total} passed")
    
    allocation_total = len(portfolio_results["allocation"])
    allocation_passed = sum(1 for r in portfolio_results["allocation"] if r["success"])
    print(f"   Portfolio Allocation: {allocation_passed}/{allocation_total} passed")
    
    holdings_total = len(portfolio_results["holdings"])
    holdings_passed = sum(1 for r in portfolio_results["holdings"] if r["success"])
    print(f"   Portfolio Holdings: {holdings_passed}/{holdings_total} passed")
    
    # Overall report
    total_tests = (news_sentiment_total + sector_sentiment_total + market_sentiment_total +
                   performance_total + allocation_total + holdings_total)
    total_passed = (news_sentiment_passed + sector_sentiment_passed + market_sentiment_passed +
                    performance_passed + allocation_passed + holdings_passed)
    
    print(f"\n3. OVERALL RESULTS:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Total Passed: {total_passed}")
    print(f"   Total Failed: {total_tests - total_passed}")
    print(f"   Success Rate: {total_passed/total_tests*100:.1f}%")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()