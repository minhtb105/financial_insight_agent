"""
Unit tests for ResultFormatter.
Uses relative imports for proper module resolution.
"""

from application.handler.result_formatter import ResultFormatter


class TestResultFormatter:
    """Test ResultFormatter functionality."""
    
    def __init__(self):
        self.formatter = ResultFormatter()
    
    def test_format_price_result(self):
        """Test price result formatting."""
        test_cases = [
            {
                "result": {
                    "ticker": "VCB",
                    "price": 120000.0,
                    "date": "2024-03-09"
                },
                "expected_format": "price"
            },
            {
                "result": {
                    "ticker": "HPG",
                    "open": 80000.0,
                    "high": 85000.0,
                    "low": 78000.0,
                    "close": 82000.0,
                    "volume": 1000000
                },
                "expected_format": "ohlcv"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                formatted_result = self.formatter.format_price_result(test_case["result"])
                success = self._validate_price_format(formatted_result, test_case["expected_format"])
                
                results.append({
                    "result": test_case["result"],
                    "formatted_result": formatted_result,
                    "expected_format": test_case["expected_format"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Price result formatting")
                print(f"  Input: {test_case['result']}")
                print(f"  Expected format: {test_case['expected_format']}")
                print(f"  Got: {formatted_result}")
                
            except Exception as e:
                results.append({
                    "result": test_case["result"],
                    "formatted_result": None,
                    "expected_format": test_case["expected_format"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Price result formatting")
                print(f"  Error: {e}")
        
        return results
    
    def test_format_indicator_result(self):
        """Test indicator result formatting."""
        test_cases = [
            {
                "result": {
                    "ticker": "VCB",
                    "sma": 115000.0,
                    "period": 9
                },
                "expected_format": "sma"
            },
            {
                "result": {
                    "ticker": "HPG",
                    "rsi": 65.5,
                    "period": 14
                },
                "expected_format": "rsi"
            },
            {
                "result": {
                    "ticker": "VIC",
                    "macd": {
                        "macd_line": 1000.0,
                        "signal_line": 950.0,
                        "histogram": 50.0
                    }
                },
                "expected_format": "macd"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                formatted_result = self.formatter.format_indicator_result(test_case["result"])
                success = self._validate_indicator_format(formatted_result, test_case["expected_format"])
                
                results.append({
                    "result": test_case["result"],
                    "formatted_result": formatted_result,
                    "expected_format": test_case["expected_format"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Indicator result formatting")
                print(f"  Input: {test_case['result']}")
                print(f"  Expected format: {test_case['expected_format']}")
                print(f"  Got: {formatted_result}")
                
            except Exception as e:
                results.append({
                    "result": test_case["result"],
                    "formatted_result": None,
                    "expected_format": test_case["expected_format"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Indicator result formatting")
                print(f"  Error: {e}")
        
        return results
    
    def test_format_company_result(self):
        """Test company result formatting."""
        test_cases = [
            {
                "result": {
                    "ticker": "VCB",
                    "shareholders": [
                        {"name": "Ngân hàng Nhà nước", "percentage": 60.0},
                        {"name": "Các cổ đông khác", "percentage": 40.0}
                    ]
                },
                "expected_format": "shareholders"
            },
            {
                "result": {
                    "ticker": "HPG",
                    "executives": [
                        {"name": "Mr. Nguyen Van A", "position": "CEO"},
                        {"name": "Mr. Tran Van B", "position": "CFO"}
                    ]
                },
                "expected_format": "executives"
            },
            {
                "result": {
                    "ticker": "VHM",
                    "subsidiaries": [
                        {"name": "Công ty A", "ownership": 100.0},
                        {"name": "Công ty B", "ownership": 70.0}
                    ]
                },
                "expected_format": "subsidiaries"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                formatted_result = self.formatter.format_company_result(test_case["result"])
                success = self._validate_company_format(formatted_result, test_case["expected_format"])
                
                results.append({
                    "result": test_case["result"],
                    "formatted_result": formatted_result,
                    "expected_format": test_case["expected_format"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Company result formatting")
                print(f"  Input: {test_case['result']}")
                print(f"  Expected format: {test_case['expected_format']}")
                print(f"  Got: {formatted_result}")
                
            except Exception as e:
                results.append({
                    "result": test_case["result"],
                    "formatted_result": None,
                    "expected_format": test_case["expected_format"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Company result formatting")
                print(f"  Error: {e}")
        
        return results
    
    def test_format_comparison_result(self):
        """Test comparison result formatting."""
        test_cases = [
            {
                "result": {
                    "ticker1": "VCB",
                    "ticker2": "BID",
                    "comparison": {
                        "price_difference": 5000.0,
                        "volume_difference": 200000,
                        "performance_comparison": "VCB outperforms BID"
                    }
                },
                "expected_format": "comparison"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                formatted_result = self.formatter.format_comparison_result(test_case["result"])
                success = self._validate_comparison_format(formatted_result)
                
                results.append({
                    "result": test_case["result"],
                    "formatted_result": formatted_result,
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Comparison result formatting")
                print(f"  Input: {test_case['result']}")
                print(f"  Got: {formatted_result}")
                
            except Exception as e:
                results.append({
                    "result": test_case["result"],
                    "formatted_result": None,
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Comparison result formatting")
                print(f"  Error: {e}")
        
        return results
    
    def test_format_ranking_result(self):
        """Test ranking result formatting."""
        test_cases = [
            {
                "result": {
                    "tickers": ["VCB", "BID", "CTG"],
                    "ranking": [
                        {"ticker": "VCB", "rank": 1, "value": 120000.0},
                        {"ticker": "BID", "rank": 2, "value": 115000.0},
                        {"ticker": "CTG", "rank": 3, "value": 110000.0}
                    ]
                },
                "expected_format": "ranking"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                formatted_result = self.formatter.format_ranking_result(test_case["result"])
                success = self._validate_ranking_format(formatted_result)
                
                results.append({
                    "result": test_case["result"],
                    "formatted_result": formatted_result,
                    "expected_format": test_case["expected_format"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Ranking result formatting")
                print(f"  Input: {test_case['result']}")
                print(f"  Expected format: {test_case['expected_format']}")
                print(f"  Got: {formatted_result}")
                
            except Exception as e:
                results.append({
                    "result": test_case["result"],
                    "formatted_result": None,
                    "expected_format": test_case["expected_format"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Ranking result formatting")
                print(f"  Error: {e}")
        
        return results
    
    def test_format_aggregate_result(self):
        """Test aggregate result formatting."""
        test_cases = [
            {
                "result": {
                    "ticker": "HPG",
                    "aggregated_value": 5000000000.0,
                    "aggregation_type": "total_volume",
                    "time_range": "1 tuần"
                },
                "expected_format": "aggregate"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                formatted_result = self.formatter.format_aggregate_result(test_case["result"])
                success = self._validate_aggregate_format(formatted_result)
                
                results.append({
                    "result": test_case["result"],
                    "formatted_result": formatted_result,
                    "expected_format": test_case["expected_format"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Aggregate result formatting")
                print(f"  Input: {test_case['result']}")
                print(f"  Expected format: {test_case['expected_format']}")
                print(f"  Got: {formatted_result}")
                
            except Exception as e:
                results.append({
                    "result": test_case["result"],
                    "formatted_result": None,
                    "expected_format": test_case["expected_format"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Aggregate result formatting")
                print(f"  Error: {e}")
        
        return results
    
    def test_format_financial_ratio_result(self):
        """Test financial ratio result formatting."""
        test_cases = [
            {
                "result": {
                    "ticker": "VNM",
                    "pe_ratio": 15.5,
                    "roe_ratio": 0.18,
                    "eps": 8000.0
                },
                "expected_format": "financial_ratio"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                formatted_result = self.formatter.format_financial_ratio_result(test_case["result"])
                success = self._validate_financial_ratio_format(formatted_result)
                
                results.append({
                    "result": test_case["result"],
                    "formatted_result": formatted_result,
                    "expected_format": test_case["expected_format"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Financial ratio result formatting")
                print(f"  Input: {test_case['result']}")
                print(f"  Expected format: {test_case['expected_format']}")
                print(f"  Got: {formatted_result}")
                
            except Exception as e:
                results.append({
                    "result": test_case["result"],
                    "formatted_result": None,
                    "expected_format": test_case["expected_format"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Financial ratio result formatting")
                print(f"  Error: {e}")
        
        return results
    
    def test_format_news_sentiment_result(self):
        """Test news sentiment result formatting."""
        test_cases = [
            {
                "result": {
                    "ticker": "VCB",
                    "sentiment_score": 0.75,
                    "news_count": 15,
                    "positive_news": 10,
                    "negative_news": 3,
                    "neutral_news": 2
                },
                "expected_format": "news_sentiment"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                formatted_result = self.formatter.format_news_sentiment_result(test_case["result"])
                success = self._validate_news_sentiment_format(formatted_result)
                
                results.append({
                    "result": test_case["result"],
                    "formatted_result": formatted_result,
                    "expected_format": test_case["expected_format"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: News sentiment result formatting")
                print(f"  Input: {test_case['result']}")
                print(f"  Expected format: {test_case['expected_format']}")
                print(f"  Got: {formatted_result}")
                
            except Exception as e:
                results.append({
                    "result": test_case["result"],
                    "formatted_result": None,
                    "expected_format": test_case["expected_format"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: News sentiment result formatting")
                print(f"  Error: {e}")
        
        return results
    
    def test_format_portfolio_result(self):
        """Test portfolio result formatting."""
        test_cases = [
            {
                "result": {
                    "portfolio": {
                        "FPT": 100,
                        "VNM": 200
                    },
                    "total_value": 50000000.0,
                    "performance": 0.15,
                    "allocation": {
                        "technology": 60.0,
                        "consumer": 40.0
                    }
                },
                "expected_format": "portfolio"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                formatted_result = self.formatter.format_portfolio_result(test_case["result"])
                success = self._validate_portfolio_format(formatted_result)
                
                results.append({
                    "result": test_case["result"],
                    "formatted_result": formatted_result,
                    "expected_format": test_case["expected_format"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Portfolio result formatting")
                print(f"  Input: {test_case['result']}")
                print(f"  Expected format: {test_case['expected_format']}")
                print(f"  Got: {formatted_result}")
                
            except Exception as e:
                results.append({
                    "result": test_case["result"],
                    "formatted_result": None,
                    "expected_format": test_case["expected_format"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Portfolio result formatting")
                print(f"  Error: {e}")
        
        return results
    
    def run_all_tests(self):
        """Run all ResultFormatter tests."""
        print("=== RESULT FORMATTER TESTS ===\n")
        
        # Test price result formatting
        print("1. Testing Price Result Formatting...")
        price_results = self.test_format_price_result()
        
        # Test indicator result formatting
        print("\n2. Testing Indicator Result Formatting...")
        indicator_results = self.test_format_indicator_result()
        
        # Test company result formatting
        print("\n3. Testing Company Result Formatting...")
        company_results = self.test_format_company_result()
        
        # Test comparison result formatting
        print("\n4. Testing Comparison Result Formatting...")
        comparison_results = self.test_format_comparison_result()
        
        # Test ranking result formatting
        print("\n5. Testing Ranking Result Formatting...")
        ranking_results = self.test_format_ranking_result()
        
        # Test aggregate result formatting
        print("\n6. Testing Aggregate Result Formatting...")
        aggregate_results = self.test_format_aggregate_result()
        
        # Test financial ratio result formatting
        print("\n7. Testing Financial Ratio Result Formatting...")
        financial_ratio_results = self.test_format_financial_ratio_result()
        
        # Test news sentiment result formatting
        print("\n8. Testing News Sentiment Result Formatting...")
        news_sentiment_results = self.test_format_news_sentiment_result()
        
        # Test portfolio result formatting
        print("\n9. Testing Portfolio Result Formatting...")
        portfolio_results = self.test_format_portfolio_result()
        
        # Generate comprehensive report
        self._generate_report(price_results, indicator_results, company_results, 
                             comparison_results, ranking_results, aggregate_results,
                             financial_ratio_results, news_sentiment_results, portfolio_results)
        
        return {
            "price_result": price_results,
            "indicator_result": indicator_results,
            "company_result": company_results,
            "comparison_result": comparison_results,
            "ranking_result": ranking_results,
            "aggregate_result": aggregate_results,
            "financial_ratio_result": financial_ratio_results,
            "news_sentiment_result": news_sentiment_results,
            "portfolio_result": portfolio_results
        }
    
    def _validate_price_format(self, formatted_result, expected_format):
        """Validate price result format."""
        if expected_format == "price":
            return "price" in str(formatted_result) and "ticker" in str(formatted_result)
        elif expected_format == "ohlcv":
            return all(key in str(formatted_result) for key in ["open", "high", "low", "close", "volume"])
        return False
    
    def _validate_indicator_format(self, formatted_result, expected_format):
        """Validate indicator result format."""
        if expected_format == "sma":
            return "SMA" in str(formatted_result)
        elif expected_format == "rsi":
            return "RSI" in str(formatted_result)
        elif expected_format == "macd":
            return "MACD" in str(formatted_result)
        return False
    
    def _validate_company_format(self, formatted_result, expected_format):
        """Validate company result format."""
        if expected_format == "shareholders":
            return "shareholders" in str(formatted_result)
        elif expected_format == "executives":
            return "executives" in str(formatted_result)
        elif expected_format == "subsidiaries":
            return "subsidiaries" in str(formatted_result)
        return False
    
    def _validate_comparison_format(self, formatted_result):
        """Validate comparison result format."""
        return "comparison" in str(formatted_result) and "ticker1" in str(formatted_result) and "ticker2" in str(formatted_result)
    
    def _validate_ranking_format(self, formatted_result):
        """Validate ranking result format."""
        return "ranking" in str(formatted_result) and "ticker" in str(formatted_result) and "rank" in str(formatted_result)
    
    def _validate_aggregate_format(self, formatted_result):
        """Validate aggregate result format."""
        return "aggregated_value" in str(formatted_result) and "aggregation_type" in str(formatted_result)
    
    def _validate_financial_ratio_format(self, formatted_result):
        """Validate financial ratio result format."""
        return "pe_ratio" in str(formatted_result) or "roe_ratio" in str(formatted_result) or "eps" in str(formatted_result)
    
    def _validate_news_sentiment_format(self, formatted_result):
        """Validate news sentiment result format."""
        return "sentiment_score" in str(formatted_result) and "news_count" in str(formatted_result)
    
    def _validate_portfolio_format(self, formatted_result):
        """Validate portfolio result format."""
        return "total_value" in str(formatted_result) and "allocation" in str(formatted_result)
    
    def _generate_report(self, price_results, indicator_results, company_results, 
                        comparison_results, ranking_results, aggregate_results,
                        financial_ratio_results, news_sentiment_results, portfolio_results):
        """Generate comprehensive test report."""
        print("\n" + "="*60)
        print("RESULT FORMATTER TEST REPORT")
        print("="*60)
        
        # Price result formatting report
        price_total = len(price_results)
        price_passed = sum(1 for r in price_results if r["success"])
        print(f"\n1. PRICE RESULT FORMATTING:")
        print(f"   Total: {price_total}, Passed: {price_passed}, Failed: {price_total - price_passed}")
        
        # Indicator result formatting report
        indicator_total = len(indicator_results)
        indicator_passed = sum(1 for r in indicator_results if r["success"])
        print(f"\n2. INDICATOR RESULT FORMATTING:")
        print(f"   Total: {indicator_total}, Passed: {indicator_passed}, Failed: {indicator_total - indicator_passed}")
        
        # Company result formatting report
        company_total = len(company_results)
        company_passed = sum(1 for r in company_results if r["success"])
        print(f"\n3. COMPANY RESULT FORMATTING:")
        print(f"   Total: {company_total}, Passed: {company_passed}, Failed: {company_total - company_passed}")
        
        # Comparison result formatting report
        comparison_total = len(comparison_results)
        comparison_passed = sum(1 for r in comparison_results if r["success"])
        print(f"\n4. COMPARISON RESULT FORMATTING:")
        print(f"   Total: {comparison_total}, Passed: {comparison_passed}, Failed: {comparison_total - comparison_passed}")
        
        # Ranking result formatting report
        ranking_total = len(ranking_results)
        ranking_passed = sum(1 for r in ranking_results if r["success"])
        print(f"\n5. RANKING RESULT FORMATTING:")
        print(f"   Total: {ranking_total}, Passed: {ranking_passed}, Failed: {ranking_total - ranking_passed}")
        
        # Aggregate result formatting report
        aggregate_total = len(aggregate_results)
        aggregate_passed = sum(1 for r in aggregate_results if r["success"])
        print(f"\n6. AGGREGATE RESULT FORMATTING:")
        print(f"   Total: {aggregate_total}, Passed: {aggregate_passed}, Failed: {aggregate_total - aggregate_passed}")
        
        # Financial ratio result formatting report
        financial_ratio_total = len(financial_ratio_results)
        financial_ratio_passed = sum(1 for r in financial_ratio_results if r["success"])
        print(f"\n7. FINANCIAL RATIO RESULT FORMATTING:")
        print(f"   Total: {financial_ratio_total}, Passed: {financial_ratio_passed}, Failed: {financial_ratio_total - financial_ratio_passed}")
        
        # News sentiment result formatting report
        news_sentiment_total = len(news_sentiment_results)
        news_sentiment_passed = sum(1 for r in news_sentiment_results if r["success"])
        print(f"\n8. NEWS SENTIMENT RESULT FORMATTING:")
        print(f"   Total: {news_sentiment_total}, Passed: {news_sentiment_passed}, Failed: {news_sentiment_total - news_sentiment_passed}")
        
        # Portfolio result formatting report
        portfolio_total = len(portfolio_results)
        portfolio_passed = sum(1 for r in portfolio_results if r["success"])
        print(f"\n9. PORTFOLIO RESULT FORMATTING:")
        print(f"   Total: {portfolio_total}, Passed: {portfolio_passed}, Failed: {portfolio_total - portfolio_passed}")
        
        # Overall report
        total_tests = (price_total + indicator_total + company_total + comparison_total + 
                       ranking_total + aggregate_total + financial_ratio_total + 
                       news_sentiment_total + portfolio_total)
        total_passed = (price_passed + indicator_passed + company_passed + comparison_passed + 
                        ranking_passed + aggregate_passed + financial_ratio_passed + 
                        news_sentiment_passed + portfolio_passed)
        
        print(f"\n10. OVERALL RESULTS:")
        print(f"    Total Tests: {total_tests}")
        print(f"    Total Passed: {total_passed}")
        print(f"    Total Failed: {total_tests - total_passed}")
        print(f"    Success Rate: {total_passed/total_tests*100:.1f}%")
        
        print("\n" + "="*60)


def main():
    """Main test runner."""
    test_suite = TestResultFormatter()
    results = test_suite.run_all_tests()
    return results


if __name__ == "__main__":
    main()