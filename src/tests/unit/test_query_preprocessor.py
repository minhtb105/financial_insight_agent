"""
Unit tests for QueryPreprocessor.
Uses relative imports for proper module resolution.
"""

from infrastructure.llm.query_preprocessor import QueryPreprocessor


class TestQueryPreprocessor:
    """Test QueryPreprocessor functionality."""
    
    def __init__(self):
        self.preprocessor = QueryPreprocessor()
    
    def test_extract_stock_symbols(self):
        """Test stock symbol extraction."""
        test_cases = [
            {
                "query": "Lấy giá đóng cửa của VCB hôm qua.",
                "expected_symbols": ["VCB"]
            },
            {
                "query": "So sánh khối lượng giao dịch của VIC với HPG trong 1 tuần.",
                "expected_symbols": ["VIC", "HPG"]
            },
            {
                "query": "Trong các mã VCB, BID, CTG mã nào có giá mở cửa thấp nhất?",
                "expected_symbols": ["VCB", "BID", "CTG"]
            },
            {
                "query": "Tổng khối lượng giao dịch của HPG, VNM, FPT trong 1 tuần.",
                "expected_symbols": ["HPG", "VNM", "FPT"]
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.preprocessor.extract_stock_symbols(test_case["query"])
                success = set(result) == set(test_case["expected_symbols"])
                
                results.append({
                    "query": test_case["query"],
                    "result": result,
                    "expected_symbols": test_case["expected_symbols"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['query']}")
                print(f"  Expected symbols: {test_case['expected_symbols']}")
                print(f"  Got symbols: {result}")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "result": None,
                    "expected_symbols": test_case["expected_symbols"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['query']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_extract_time_parameters(self):
        """Test time parameter extraction."""
        test_cases = [
            {
                "query": "Lấy giá đóng cửa của VCB hôm qua.",
                "expected_time": "hôm qua"
            },
            {
                "query": "Tính SMA9 cho VCB trong 1 tuần gần nhất.",
                "expected_time": "1 tuần gần nhất"
            },
            {
                "query": "So sánh khối lượng giao dịch của VIC với HPG trong 1 tuần.",
                "expected_time": "1 tuần"
            },
            {
                "query": "Tổng khối lượng giao dịch của HPG trong 1 tuần.",
                "expected_time": "1 tuần"
            },
            {
                "query": "Lấy dữ liệu OHLCV của HPG 10 ngày gần nhất.",
                "expected_time": "10 ngày gần nhất"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.preprocessor.extract_time_parameters(test_case["query"])
                success = result == test_case["expected_time"]
                
                results.append({
                    "query": test_case["query"],
                    "result": result,
                    "expected_time": test_case["expected_time"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['query']}")
                print(f"  Expected time: {test_case['expected_time']}")
                print(f"  Got time: {result}")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "result": None,
                    "expected_time": test_case["expected_time"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['query']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_extract_query_type(self):
        """Test query type detection."""
        test_cases = [
            {
                "query": "Lấy giá đóng cửa của VCB hôm qua.",
                "expected_type": "price_query"
            },
            {
                "query": "Tính SMA9 cho VCB trong 1 tuần gần nhất.",
                "expected_type": "indicator_query"
            },
            {
                "query": "Danh sách cổ đông lớn của VCB.",
                "expected_type": "company_query"
            },
            {
                "query": "So sánh khối lượng giao dịch của VIC với HPG trong 1 tuần.",
                "expected_type": "comparison_query"
            },
            {
                "query": "Trong các mã VCB, BID, CTG mã nào có giá mở cửa thấp nhất?",
                "expected_type": "ranking_query"
            },
            {
                "query": "Tổng khối lượng giao dịch của HPG trong 1 tuần.",
                "expected_type": "aggregate_query"
            },
            {
                "query": "Tỷ lệ P/E của VNM hiện tại là bao nhiêu?",
                "expected_type": "financial_ratio_query"
            },
            {
                "query": "Có tin tức gì về VCB trong tuần này không?",
                "expected_type": "news_sentiment_query"
            },
            {
                "query": "Nếu tôi mua 100 cổ FPT và 200 cổ VNM thì danh mục hiện tại ra sao?",
                "expected_type": "portfolio_query"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.preprocessor.extract_query_type(test_case["query"])
                success = result == test_case["expected_type"]
                
                results.append({
                    "query": test_case["query"],
                    "result": result,
                    "expected_type": test_case["expected_type"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['query']}")
                print(f"  Expected type: {test_case['expected_type']}")
                print(f"  Got type: {result}")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "result": None,
                    "expected_type": test_case["expected_type"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['query']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_extract_requested_fields(self):
        """Test requested field extraction."""
        test_cases = [
            {
                "query": "Lấy giá đóng cửa của VCB hôm qua.",
                "expected_fields": ["close"]
            },
            {
                "query": "Tính SMA9 cho VCB trong 1 tuần gần nhất.",
                "expected_fields": ["sma"]
            },
            {
                "query": "Danh sách cổ đông lớn của VCB.",
                "expected_fields": ["shareholders"]
            },
            {
                "query": "So sánh khối lượng giao dịch của VIC với HPG trong 1 tuần.",
                "expected_fields": ["volume"]
            },
            {
                "query": "Trong các mã VCB, BID, CTG mã nào có giá mở cửa thấp nhất?",
                "expected_fields": ["open"]
            },
            {
                "query": "Tổng khối lượng giao dịch của HPG trong 1 tuần.",
                "expected_fields": ["volume"]
            },
            {
                "query": "Tỷ lệ P/E của VNM hiện tại là bao nhiêu?",
                "expected_fields": ["pe"]
            },
            {
                "query": "Có tin tức gì về VCB trong tuần này không?",
                "expected_fields": ["news"]
            },
            {
                "query": "Nếu tôi mua 100 cổ FPT và 200 cổ VNM thì danh mục hiện tại ra sao?",
                "expected_fields": ["portfolio_value"]
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.preprocessor.extract_requested_fields(test_case["query"])
                success = set(result) == set(test_case["expected_fields"])
                
                results.append({
                    "query": test_case["query"],
                    "result": result,
                    "expected_fields": test_case["expected_fields"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['query']}")
                print(f"  Expected fields: {test_case['expected_fields']}")
                print(f"  Got fields: {result}")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "result": None,
                    "expected_fields": test_case["expected_fields"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['query']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_normalize_query(self):
        """Test query normalization."""
        test_cases = [
            {
                "query": "  Lấy giá đóng cửa của VCB hôm qua.  ",
                "expected_normalized": "Lấy giá đóng cửa của VCB hôm qua."
            },
            {
                "query": "Lấy   giá   đóng   cửa   của   VCB   hôm   qua.",
                "expected_normalized": "Lấy giá đóng cửa của VCB hôm qua."
            },
            {
                "query": "Lấy giá đóng cửa của VCB hôm qua.",
                "expected_normalized": "Lấy giá đóng cửa của VCB hôm qua."
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.preprocessor.normalize_query(test_case["query"])
                success = result == test_case["expected_normalized"]
                
                results.append({
                    "query": test_case["query"],
                    "result": result,
                    "expected_normalized": test_case["expected_normalized"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['query']}")
                print(f"  Expected normalized: '{test_case['expected_normalized']}'")
                print(f"  Got normalized: '{result}'")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "result": None,
                    "expected_normalized": test_case["expected_normalized"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['query']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_detect_query_complexity(self):
        """Test query complexity detection."""
        test_cases = [
            {
                "query": "Lấy giá đóng cửa của VCB hôm qua.",
                "expected_complexity": "simple"
            },
            {
                "query": "Tính SMA9 cho VCB trong 1 tuần gần nhất.",
                "expected_complexity": "simple"
            },
            {
                "query": "So sánh khối lượng giao dịch của VIC với HPG trong 1 tuần.",
                "expected_complexity": "simple"
            },
            {
                "query": "Trong các mã VCB, BID, CTG mã nào có giá mở cửa thấp nhất?",
                "expected_complexity": "complex"
            },
            {
                "query": "Tổng khối lượng giao dịch của HPG, VNM, FPT trong 1 tuần.",
                "expected_complexity": "complex"
            },
            {
                "query": "Nếu tôi mua 100 cổ FPT và 200 cổ VNM thì danh mục hiện tại ra sao?",
                "expected_complexity": "complex"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.preprocessor.detect_query_complexity(test_case["query"])
                success = result == test_case["expected_complexity"]
                
                results.append({
                    "query": test_case["query"],
                    "result": result,
                    "expected_complexity": test_case["expected_complexity"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['query']}")
                print(f"  Expected complexity: {test_case['expected_complexity']}")
                print(f"  Got complexity: {result}")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "result": None,
                    "expected_complexity": test_case["expected_complexity"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['query']}")
                print(f"  Error: {e}")
        
        return results
    
    def run_all_tests(self):
        """Run all QueryPreprocessor tests."""
        print("=== QUERY PREPROCESSOR TESTS ===\n")
        
        # Test stock symbol extraction
        print("1. Testing Stock Symbol Extraction...")
        symbol_results = self.test_extract_stock_symbols()
        
        # Test time parameter extraction
        print("\n2. Testing Time Parameter Extraction...")
        time_results = self.test_extract_time_parameters()
        
        # Test query type detection
        print("\n3. Testing Query Type Detection...")
        type_results = self.test_extract_query_type()
        
        # Test requested field extraction
        print("\n4. Testing Requested Field Extraction...")
        field_results = self.test_extract_requested_fields()
        
        # Test query normalization
        print("\n5. Testing Query Normalization...")
        normalize_results = self.test_normalize_query()
        
        # Test query complexity detection
        print("\n6. Testing Query Complexity Detection...")
        complexity_results = self.test_detect_query_complexity()
        
        # Generate comprehensive report
        self._generate_report(symbol_results, time_results, type_results, field_results, normalize_results, complexity_results)
        
        return {
            "stock_symbols": symbol_results,
            "time_parameters": time_results,
            "query_type": type_results,
            "requested_fields": field_results,
            "normalization": normalize_results,
            "complexity": complexity_results
        }
    
    def _generate_report(self, symbol_results, time_results, type_results, field_results, normalize_results, complexity_results):
        """Generate comprehensive test report."""
        print("\n" + "="*60)
        print("QUERY PREPROCESSOR TEST REPORT")
        print("="*60)
        
        # Stock symbol extraction report
        symbol_total = len(symbol_results)
        symbol_passed = sum(1 for r in symbol_results if r["success"])
        print(f"\n1. STOCK SYMBOL EXTRACTION:")
        print(f"   Total: {symbol_total}, Passed: {symbol_passed}, Failed: {symbol_total - symbol_passed}")
        
        # Time parameter extraction report
        time_total = len(time_results)
        time_passed = sum(1 for r in time_results if r["success"])
        print(f"\n2. TIME PARAMETER EXTRACTION:")
        print(f"   Total: {time_total}, Passed: {time_passed}, Failed: {time_total - time_passed}")
        
        # Query type detection report
        type_total = len(type_results)
        type_passed = sum(1 for r in type_results if r["success"])
        print(f"\n3. QUERY TYPE DETECTION:")
        print(f"   Total: {type_total}, Passed: {type_passed}, Failed: {type_total - type_passed}")
        
        # Requested field extraction report
        field_total = len(field_results)
        field_passed = sum(1 for r in field_results if r["success"])
        print(f"\n4. REQUESTED FIELD EXTRACTION:")
        print(f"   Total: {field_total}, Passed: {field_passed}, Failed: {field_total - field_passed}")
        
        # Query normalization report
        normalize_total = len(normalize_results)
        normalize_passed = sum(1 for r in normalize_results if r["success"])
        print(f"\n5. QUERY NORMALIZATION:")
        print(f"   Total: {normalize_total}, Passed: {normalize_passed}, Failed: {normalize_total - normalize_passed}")
        
        # Query complexity detection report
        complexity_total = len(complexity_results)
        complexity_passed = sum(1 for r in complexity_results if r["success"])
        print(f"\n6. QUERY COMPLEXITY DETECTION:")
        print(f"   Total: {complexity_total}, Passed: {complexity_passed}, Failed: {complexity_total - complexity_passed}")
        
        # Overall report
        total_tests = (symbol_total + time_total + type_total + field_total + 
                       normalize_total + complexity_total)
        total_passed = (symbol_passed + time_passed + type_passed + field_passed + 
                        normalize_passed + complexity_passed)
        
        print(f"\n7. OVERALL RESULTS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Total Passed: {total_passed}")
        print(f"   Total Failed: {total_tests - total_passed}")
        print(f"   Success Rate: {total_passed/total_tests*100:.1f}%")
        
        print("\n" + "="*60)


def main():
    """Main test runner."""
    test_suite = TestQueryPreprocessor()
    results = test_suite.run_all_tests()
    return results


if __name__ == "__main__":
    main()