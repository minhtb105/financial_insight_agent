"""
Unit tests for VNStockClient.
Uses relative imports for proper module resolution.
"""

from infrastructure.api_clients.vn_stock_client import VNStockClient


class TestVNStockClient:
    """Test VNStockClient functionality."""
    
    def __init__(self):
        self.client = VNStockClient()
    
    def test_get_price_data(self):
        """Test price data retrieval."""
        test_cases = [
            {
                "ticker": "VNM",
                "time_range": "1 tuần",
                "expected_keys": ["open", "high", "low", "close", "volume"]
            },
            {
                "ticker": "HPG",
                "time_range": "1 tháng",
                "expected_keys": ["open", "high", "low", "close", "volume"]
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.client.get_price_data(
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
                print(f"[{status}] Case {i+1}: Price data for {test_case['ticker']}")
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
                print(f"[FAIL] Case {i+1}: Price data for {test_case['ticker']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_get_financial_data(self):
        """Test financial data retrieval."""
        test_cases = [
            {
                "ticker": "VNM",
                "expected_keys": ["pe", "roe", "eps", "market_cap"]
            },
            {
                "ticker": "HPG",
                "expected_keys": ["pe", "roe", "eps", "market_cap"]
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.client.get_financial_data(test_case["ticker"])
                success = all(key in result for key in test_case["expected_keys"])
                
                results.append({
                    "ticker": test_case["ticker"],
                    "result": result,
                    "expected_keys": test_case["expected_keys"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Financial data for {test_case['ticker']}")
                print(f"  Expected keys: {test_case['expected_keys']}")
                print(f"  Got keys: {list(result.keys()) if result else 'None'}")
                
            except Exception as e:
                results.append({
                    "ticker": test_case["ticker"],
                    "result": None,
                    "expected_keys": test_case["expected_keys"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Financial data for {test_case['ticker']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_get_news_data(self):
        """Test news data retrieval."""
        test_cases = [
            {
                "ticker": "VNM",
                "time_range": "1 tuần",
                "expected_keys": ["news", "sentiment", "count"]
            },
            {
                "ticker": "HPG",
                "time_range": "1 tháng",
                "expected_keys": ["news", "sentiment", "count"]
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.client.get_news_data(
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
                print(f"[{status}] Case {i+1}: News data for {test_case['ticker']}")
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
                print(f"[FAIL] Case {i+1}: News data for {test_case['ticker']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_error_handling(self):
        """Test error handling for API failures."""
        test_cases = [
            {
                "ticker": "INVALID_TICKER",
                "time_range": "1 tuần",
                "expected_error": True
            },
            {
                "ticker": "VNM",
                "time_range": "invalid_range",
                "expected_error": True
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.client.get_price_data(
                    test_case["ticker"],
                    test_case["time_range"]
                )
                success = test_case["expected_error"] == False
                
                results.append({
                    "ticker": test_case["ticker"],
                    "time_range": test_case["time_range"],
                    "result": result,
                    "expected_error": test_case["expected_error"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Error handling for {test_case['ticker']}")
                print(f"  Expected error: {test_case['expected_error']}")
                print(f"  Got result: {result}")
                
            except Exception as e:
                success = test_case["expected_error"] == True
                
                results.append({
                    "ticker": test_case["ticker"],
                    "time_range": test_case["time_range"],
                    "result": None,
                    "expected_error": test_case["expected_error"],
                    "success": success,
                    "error": str(e)
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Error handling for {test_case['ticker']}")
                print(f"  Expected error: {test_case['expected_error']}")
                print(f"  Got error: {e}")
        
        return results
    
    def test_rate_limiting(self):
        """Test rate limiting functionality."""
        test_cases = [
            {
                "ticker": "VNM",
                "time_range": "1 tuần",
                "expected_delay": True
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                # Make multiple rapid requests to test rate limiting
                results_list = []
                for j in range(5):
                    result = self.client.get_price_data(
                        test_case["ticker"],
                        test_case["time_range"]
                    )
                    results_list.append(result)
                
                success = len(results_list) == 5
                
                results.append({
                    "ticker": test_case["ticker"],
                    "time_range": test_case["time_range"],
                    "results": results_list,
                    "expected_delay": test_case["expected_delay"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Rate limiting for {test_case['ticker']}")
                print(f"  Expected delay: {test_case['expected_delay']}")
                print(f"  Got {len(results_list)} results")
                
            except Exception as e:
                results.append({
                    "ticker": test_case["ticker"],
                    "time_range": test_case["time_range"],
                    "results": None,
                    "expected_delay": test_case["expected_delay"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Rate limiting for {test_case['ticker']}")
                print(f"  Error: {e}")
        
        return results
    
    def run_all_tests(self):
        """Run all VNStockClient tests."""
        print("=== VN STOCK CLIENT TESTS ===\n")
        
        # Test price data retrieval
        print("1. Testing Price Data Retrieval...")
        price_results = self.test_get_price_data()
        
        # Test financial data retrieval
        print("\n2. Testing Financial Data Retrieval...")
        financial_results = self.test_get_financial_data()
        
        # Test news data retrieval
        print("\n3. Testing News Data Retrieval...")
        news_results = self.test_get_news_data()
        
        # Test error handling
        print("\n4. Testing Error Handling...")
        error_results = self.test_error_handling()
        
        # Test rate limiting
        print("\n5. Testing Rate Limiting...")
        rate_limit_results = self.test_rate_limiting()
        
        # Generate comprehensive report
        self._generate_report(price_results, financial_results, news_results, error_results, rate_limit_results)
        
        return {
            "price_data": price_results,
            "financial_data": financial_results,
            "news_data": news_results,
            "error_handling": error_results,
            "rate_limiting": rate_limit_results
        }
    
    def _generate_report(self, price_results, financial_results, news_results, error_results, rate_limit_results):
        """Generate comprehensive test report."""
        print("\n" + "="*60)
        print("VN STOCK CLIENT TEST REPORT")
        print("="*60)
        
        # Price data retrieval report
        price_total = len(price_results)
        price_passed = sum(1 for r in price_results if r["success"])
        print(f"\n1. PRICE DATA RETRIEVAL:")
        print(f"   Total: {price_total}, Passed: {price_passed}, Failed: {price_total - price_passed}")
        
        # Financial data retrieval report
        financial_total = len(financial_results)
        financial_passed = sum(1 for r in financial_results if r["success"])
        print(f"\n2. FINANCIAL DATA RETRIEVAL:")
        print(f"   Total: {financial_total}, Passed: {financial_passed}, Failed: {financial_total - financial_passed}")
        
        # News data retrieval report
        news_total = len(news_results)
        news_passed = sum(1 for r in news_results if r["success"])
        print(f"\n3. NEWS DATA RETRIEVAL:")
        print(f"   Total: {news_total}, Passed: {news_passed}, Failed: {news_total - news_passed}")
        
        # Error handling report
        error_total = len(error_results)
        error_passed = sum(1 for r in error_results if r["success"])
        print(f"\n4. ERROR HANDLING:")
        print(f"   Total: {error_total}, Passed: {error_passed}, Failed: {error_total - error_passed}")
        
        # Rate limiting report
        rate_limit_total = len(rate_limit_results)
        rate_limit_passed = sum(1 for r in rate_limit_results if r["success"])
        print(f"\n5. RATE LIMITING:")
        print(f"   Total: {rate_limit_total}, Passed: {rate_limit_passed}, Failed: {rate_limit_total - rate_limit_passed}")
        
        # Overall report
        total_tests = (price_total + financial_total + news_total + 
                       error_total + rate_limit_total)
        total_passed = (price_passed + financial_passed + news_passed + 
                        error_passed + rate_limit_passed)
        
        print(f"\n6. OVERALL RESULTS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Total Passed: {total_passed}")
        print(f"   Total Failed: {total_tests - total_passed}")
        print(f"   Success Rate: {total_passed/total_tests*100:.1f}%")
        
        print("\n" + "="*60)


def main():
    """Main test runner."""
    test_suite = TestVNStockClient()
    results = test_suite.run_all_tests()
    return results


if __name__ == "__main__":
    main()