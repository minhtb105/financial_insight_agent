"""
Unit tests for QueryRouter.
Uses relative imports for proper module resolution.
"""

from application.handler.query_router import QueryRouter


class TestQueryRouter:
    """Test QueryRouter functionality."""
    
    def __init__(self):
        self.router = QueryRouter()
    
    def test_route_price_query(self):
        """Test routing price queries."""
        test_cases = [
            {
                "query": "Lấy giá đóng cửa của VCB hôm qua.",
                "expected_route": "price_service"
            },
            {
                "query": "Lấy dữ liệu OHLCV của HPG 10 ngày gần nhất.",
                "expected_route": "price_service"
            },
            {
                "query": "Lấy giá mở cửa của VHM trong vòng 2 tuần qua.",
                "expected_route": "price_service"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.router.route_query(test_case["query"])
                success = result["service"] == test_case["expected_route"]
                
                results.append({
                    "query": test_case["query"],
                    "result": result,
                    "expected_route": test_case["expected_route"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['query']}")
                print(f"  Expected route: {test_case['expected_route']}")
                print(f"  Got route: {result['service']}")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "result": None,
                    "expected_route": test_case["expected_route"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['query']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_route_indicator_query(self):
        """Test routing indicator queries."""
        test_cases = [
            {
                "query": "Tính SMA9 cho VCB trong 1 tuần gần nhất.",
                "expected_route": "indicator_service"
            },
            {
                "query": "Cho tôi SMA20 của HPG trong 2 tuần gần đây.",
                "expected_route": "indicator_service"
            },
            {
                "query": "SMA50 của VIC từ đầu tháng 10 đến nay.",
                "expected_route": "indicator_service"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.router.route_query(test_case["query"])
                success = result["service"] == test_case["expected_route"]
                
                results.append({
                    "query": test_case["query"],
                    "result": result,
                    "expected_route": test_case["expected_route"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['query']}")
                print(f"  Expected route: {test_case['expected_route']}")
                print(f"  Got route: {result['service']}")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "result": None,
                    "expected_route": test_case["expected_route"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['query']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_route_company_query(self):
        """Test routing company queries."""
        test_cases = [
            {
                "query": "Danh sách cổ đông lớn của VCB.",
                "expected_route": "company_service"
            },
            {
                "query": "Danh sách lãnh đạo đang làm việc tại HPG.",
                "expected_route": "company_service"
            },
            {
                "query": "Các công ty con của VHM.",
                "expected_route": "company_service"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.router.route_query(test_case["query"])
                success = result["service"] == test_case["expected_route"]
                
                results.append({
                    "query": test_case["query"],
                    "result": result,
                    "expected_route": test_case["expected_route"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['query']}")
                print(f"  Expected route: {test_case['expected_route']}")
                print(f"  Got route: {result['service']}")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "result": None,
                    "expected_route": test_case["expected_route"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['query']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_route_comparison_query(self):
        """Test routing comparison queries."""
        test_cases = [
            {
                "query": "So sánh khối lượng giao dịch của VIC với HPG trong 1 tuần.",
                "expected_route": "comparison_service"
            },
            {
                "query": "So sánh giá đóng của VCB với BID hôm nay.",
                "expected_route": "comparison_service"
            },
            {
                "query": "So sánh giá mở cửa của TCB với MBB 5 ngày gần đây.",
                "expected_route": "comparison_service"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.router.route_query(test_case["query"])
                success = result["service"] == test_case["expected_route"]
                
                results.append({
                    "query": test_case["query"],
                    "result": result,
                    "expected_route": test_case["expected_route"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['query']}")
                print(f"  Expected route: {test_case['expected_route']}")
                print(f"  Got route: {result['service']}")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "result": None,
                    "expected_route": test_case["expected_route"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['query']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_route_ranking_query(self):
        """Test routing ranking queries."""
        test_cases = [
            {
                "query": "Trong các mã VCB, BID, CTG mã nào có giá mở cửa thấp nhất hôm qua?",
                "expected_route": "ranking_service"
            },
            {
                "query": "Mã nào cao nhất trong nhóm VHM, VIC, VRE trong 10 ngày qua?",
                "expected_route": "ranking_service"
            },
            {
                "query": "Trong nhóm HPG, NKG, HSG mã nào có volume thấp nhất tuần này?",
                "expected_route": "ranking_service"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.router.route_query(test_case["query"])
                success = result["service"] == test_case["expected_route"]
                
                results.append({
                    "query": test_case["query"],
                    "result": result,
                    "expected_route": test_case["expected_route"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['query']}")
                print(f"  Expected route: {test_case['expected_route']}")
                print(f"  Got route: {result['service']}")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "result": None,
                    "expected_route": test_case["expected_route"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['query']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_route_aggregate_query(self):
        """Test routing aggregate queries."""
        test_cases = [
            {
                "query": "Tổng khối lượng giao dịch của HPG trong 1 tuần.",
                "expected_route": "aggregate_service"
            },
            {
                "query": "Tổng volume của VCB trong 10 ngày vừa qua.",
                "expected_route": "aggregate_service"
            },
            {
                "query": "Tổng volume của VIC trong 1 tháng gần đây.",
                "expected_route": "aggregate_service"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.router.route_query(test_case["query"])
                success = result["service"] == test_case["expected_route"]
                
                results.append({
                    "query": test_case["query"],
                    "result": result,
                    "expected_route": test_case["expected_route"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['query']}")
                print(f"  Expected route: {test_case['expected_route']}")
                print(f"  Got route: {result['service']}")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "result": None,
                    "expected_route": test_case["expected_route"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['query']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_route_financial_ratio_query(self):
        """Test routing financial ratio queries."""
        test_cases = [
            {
                "query": "Tỷ lệ P/E của VNM hiện tại là bao nhiêu?",
                "expected_route": "financial_ratio_service"
            },
            {
                "query": "So sánh ROE giữa FPT và VNM trong 3 năm gần đây",
                "expected_route": "financial_ratio_service"
            },
            {
                "query": "EPS của HPG trong quý 3/2024 là bao nhiêu?",
                "expected_route": "financial_ratio_service"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.router.route_query(test_case["query"])
                success = result["service"] == test_case["expected_route"]
                
                results.append({
                    "query": test_case["query"],
                    "result": result,
                    "expected_route": test_case["expected_route"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['query']}")
                print(f"  Expected route: {test_case['expected_route']}")
                print(f"  Got route: {result['service']}")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "result": None,
                    "expected_route": test_case["expected_route"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['query']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_route_news_sentiment_query(self):
        """Test routing news sentiment queries."""
        test_cases = [
            {
                "query": "Có tin tức gì về VCB trong tuần này không?",
                "expected_route": "news_sentiment_service"
            },
            {
                "query": "Cảm xúc thị trường đối với nhóm ngân hàng hiện nay ra sao?",
                "expected_route": "news_sentiment_service"
            },
            {
                "query": "Tin tức tích cực về FPT trong tháng 11",
                "expected_route": "news_sentiment_service"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.router.route_query(test_case["query"])
                success = result["service"] == test_case["expected_route"]
                
                results.append({
                    "query": test_case["query"],
                    "result": result,
                    "expected_route": test_case["expected_route"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['query']}")
                print(f"  Expected route: {test_case['expected_route']}")
                print(f"  Got route: {result['service']}")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "result": None,
                    "expected_route": test_case["expected_route"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['query']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_route_portfolio_query(self):
        """Test routing portfolio queries."""
        test_cases = [
            {
                "query": "Nếu tôi mua 100 cổ FPT và 200 cổ VNM thì danh mục hiện tại ra sao?",
                "expected_route": "portfolio_service"
            },
            {
                "query": "Hiệu suất danh mục của tôi trong tháng 11 là bao nhiêu?",
                "expected_route": "portfolio_service"
            },
            {
                "query": "Phân bổ ngành trong danh mục hiện tại",
                "expected_route": "portfolio_service"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.router.route_query(test_case["query"])
                success = result["service"] == test_case["expected_route"]
                
                results.append({
                    "query": test_case["query"],
                    "result": result,
                    "expected_route": test_case["expected_route"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['query']}")
                print(f"  Expected route: {test_case['expected_route']}")
                print(f"  Got route: {result['service']}")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "result": None,
                    "expected_route": test_case["expected_route"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['query']}")
                print(f"  Error: {e}")
        
        return results
    
    def run_all_tests(self):
        """Run all QueryRouter tests."""
        print("=== QUERY ROUTER TESTS ===\n")
        
        # Test price query routing
        print("1. Testing Price Query Routing...")
        price_results = self.test_route_price_query()
        
        # Test indicator query routing
        print("\n2. Testing Indicator Query Routing...")
        indicator_results = self.test_route_indicator_query()
        
        # Test company query routing
        print("\n3. Testing Company Query Routing...")
        company_results = self.test_route_company_query()
        
        # Test comparison query routing
        print("\n4. Testing Comparison Query Routing...")
        comparison_results = self.test_route_comparison_query()
        
        # Test ranking query routing
        print("\n5. Testing Ranking Query Routing...")
        ranking_results = self.test_route_ranking_query()
        
        # Test aggregate query routing
        print("\n6. Testing Aggregate Query Routing...")
        aggregate_results = self.test_route_aggregate_query()
        
        # Test financial ratio query routing
        print("\n7. Testing Financial Ratio Query Routing...")
        financial_ratio_results = self.test_route_financial_ratio_query()
        
        # Test news sentiment query routing
        print("\n8. Testing News Sentiment Query Routing...")
        news_sentiment_results = self.test_route_news_sentiment_query()
        
        # Test portfolio query routing
        print("\n9. Testing Portfolio Query Routing...")
        portfolio_results = self.test_route_portfolio_query()
        
        # Generate comprehensive report
        self._generate_report(price_results, indicator_results, company_results, 
                             comparison_results, ranking_results, aggregate_results,
                             financial_ratio_results, news_sentiment_results, portfolio_results)
        
        return {
            "price_query": price_results,
            "indicator_query": indicator_results,
            "company_query": company_results,
            "comparison_query": comparison_results,
            "ranking_query": ranking_results,
            "aggregate_query": aggregate_results,
            "financial_ratio_query": financial_ratio_results,
            "news_sentiment_query": news_sentiment_results,
            "portfolio_query": portfolio_results
        }
    
    def _generate_report(self, price_results, indicator_results, company_results, 
                        comparison_results, ranking_results, aggregate_results,
                        financial_ratio_results, news_sentiment_results, portfolio_results):
        """Generate comprehensive test report."""
        print("\n" + "="*60)
        print("QUERY ROUTER TEST REPORT")
        print("="*60)
        
        # Price query routing report
        price_total = len(price_results)
        price_passed = sum(1 for r in price_results if r["success"])
        print(f"\n1. PRICE QUERY ROUTING:")
        print(f"   Total: {price_total}, Passed: {price_passed}, Failed: {price_total - price_passed}")
        
        # Indicator query routing report
        indicator_total = len(indicator_results)
        indicator_passed = sum(1 for r in indicator_results if r["success"])
        print(f"\n2. INDICATOR QUERY ROUTING:")
        print(f"   Total: {indicator_total}, Passed: {indicator_passed}, Failed: {indicator_total - indicator_passed}")
        
        # Company query routing report
        company_total = len(company_results)
        company_passed = sum(1 for r in company_results if r["success"])
        print(f"\n3. COMPANY QUERY ROUTING:")
        print(f"   Total: {company_total}, Passed: {company_passed}, Failed: {company_total - company_passed}")
        
        # Comparison query routing report
        comparison_total = len(comparison_results)
        comparison_passed = sum(1 for r in comparison_results if r["success"])
        print(f"\n4. COMPARISON QUERY ROUTING:")
        print(f"   Total: {comparison_total}, Passed: {comparison_passed}, Failed: {comparison_total - comparison_passed}")
        
        # Ranking query routing report
        ranking_total = len(ranking_results)
        ranking_passed = sum(1 for r in ranking_results if r["success"])
        print(f"\n5. RANKING QUERY ROUTING:")
        print(f"   Total: {ranking_total}, Passed: {ranking_passed}, Failed: {ranking_total - ranking_passed}")
        
        # Aggregate query routing report
        aggregate_total = len(aggregate_results)
        aggregate_passed = sum(1 for r in aggregate_results if r["success"])
        print(f"\n6. AGGREGATE QUERY ROUTING:")
        print(f"   Total: {aggregate_total}, Passed: {aggregate_passed}, Failed: {aggregate_total - aggregate_passed}")
        
        # Financial ratio query routing report
        financial_ratio_total = len(financial_ratio_results)
        financial_ratio_passed = sum(1 for r in financial_ratio_results if r["success"])
        print(f"\n7. FINANCIAL RATIO QUERY ROUTING:")
        print(f"   Total: {financial_ratio_total}, Passed: {financial_ratio_passed}, Failed: {financial_ratio_total - financial_ratio_passed}")
        
        # News sentiment query routing report
        news_sentiment_total = len(news_sentiment_results)
        news_sentiment_passed = sum(1 for r in news_sentiment_results if r["success"])
        print(f"\n8. NEWS SENTIMENT QUERY ROUTING:")
        print(f"   Total: {news_sentiment_total}, Passed: {news_sentiment_passed}, Failed: {news_sentiment_total - news_sentiment_passed}")
        
        # Portfolio query routing report
        portfolio_total = len(portfolio_results)
        portfolio_passed = sum(1 for r in portfolio_results if r["success"])
        print(f"\n9. PORTFOLIO QUERY ROUTING:")
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
    test_suite = TestQueryRouter()
    results = test_suite.run_all_tests()
    return results


if __name__ == "__main__":
    main()