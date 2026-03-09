"""
Comprehensive test suite for query parsing functionality.
Uses relative imports to avoid sys.path manipulation.
"""

from ...infrastructure.llm.nlp_parser import QueryParser
from ...infrastructure.llm.nlp_parser import EnhancedQueryParser
from ...domain.entities.extended_query_type import ExtendedQueryType
from ...domain.entities.extended_requested_field import ExtendedRequestedField


class TestQueryParserComprehensive:
    """Comprehensive test suite for query parsing functionality."""
    
    def __init__(self):
        self.basic_parser = QueryParser()
        self.enhanced_parser = EnhancedQueryParser()
    
    def test_basic_parser(self):
        """Test basic query parser with core functionality."""
        test_cases = [
            # PRICE QUERY - 5 questions
            {
                "query": "Lấy giá mở cửa của VCB hôm qua.",
                "expected_type": "price_query",
                "expected_field": "open"
            },
            {
                "query": "Lấy giá đóng cửa của HPG hôm nay.",
                "expected_type": "price_query", 
                "expected_field": "close"
            },
            {
                "query": "Cho tôi giá chốt của VIC trong ngày.",
                "expected_type": "price_query",
                "expected_field": "close"
            },
            {
                "query": "Lấy dữ liệu OHLCV của HPG 10 ngày gần nhất.",
                "expected_type": "price_query",
                "expected_field": "ohlcv"
            },
            {
                "query": "Lấy OHLCV của VHM trong vòng 2 tuần qua.",
                "expected_type": "price_query",
                "expected_field": "ohlcv"
            },
            
            # INDICATOR QUERY - 5 questions
            {
                "query": "Tính SMA9 cho VCB trong 1 tuần gần nhất.",
                "expected_type": "indicator_query",
                "expected_field": "sma"
            },
            {
                "query": "Cho tôi SMA20 của HPG trong 2 tuần gần đây.",
                "expected_type": "indicator_query",
                "expected_field": "sma"
            },
            {
                "query": "SMA50 của VIC từ đầu tháng 10 đến nay.",
                "expected_type": "indicator_query",
                "expected_field": "sma"
            },
            {
                "query": "Tính SMA9 và SMA20 cho VHM trong 1 tháng qua.",
                "expected_type": "indicator_query",
                "expected_field": "sma"
            },
            {
                "query": "Cho tôi SMA14 và SMA21 của SSI trong 3 tuần gần đây.",
                "expected_type": "indicator_query",
                "expected_field": "sma"
            },
            
            # COMPANY QUERY - 5 questions
            {
                "query": "Danh sách cổ đông lớn của VCB.",
                "expected_type": "company_query",
                "expected_field": "shareholders"
            },
            {
                "query": "Danh sách lãnh đạo đang làm việc tại HPG.",
                "expected_type": "company_query",
                "expected_field": "executives"
            },
            {
                "query": "Các công ty con của VHM.",
                "expected_type": "company_query",
                "expected_field": "subsidiaries"
            },
            {
                "query": "Cho tôi danh sách công ty con của FPT.",
                "expected_type": "company_query",
                "expected_field": "subsidiaries"
            },
            {
                "query": "Lấy danh sách cổ đông chủ chốt của VIC.",
                "expected_type": "company_query",
                "expected_field": "shareholders"
            },
            
            # COMPARISON QUERY - 5 questions
            {
                "query": "So sánh khối lượng giao dịch của VIC với HPG trong 1 tuần.",
                "expected_type": "comparison_query",
                "expected_field": "volume"
            },
            {
                "query": "So sánh giá đóng của VCB với BID hôm nay.",
                "expected_type": "comparison_query",
                "expected_field": "close"
            },
            {
                "query": "So sánh giá mở cửa của TCB với MBB 5 ngày gần đây.",
                "expected_type": "comparison_query",
                "expected_field": "open"
            },
            {
                "query": "So sánh volume của FPT với MWG trong 10 ngày.",
                "expected_type": "comparison_query",
                "expected_field": "volume"
            },
            {
                "query": "So sánh giá đóng của SSI với VCI từ đầu tháng.",
                "expected_type": "comparison_query",
                "expected_field": "close"
            },
            
            # RANKING QUERY - 5 questions
            {
                "query": "Trong các mã VCB, BID, CTG mã nào có giá mở cửa thấp nhất hôm qua?",
                "expected_type": "ranking_query",
                "expected_field": "open"
            },
            {
                "query": "Mã nào cao nhất trong nhóm VHM, VIC, VRE trong 10 ngày qua?",
                "expected_type": "ranking_query",
                "expected_field": "close"
            },
            {
                "query": "Trong nhóm HPG, NKG, HSG mã nào có volume thấp nhất tuần này?",
                "expected_type": "ranking_query",
                "expected_field": "volume"
            },
            {
                "query": "Mã nào giá đóng cao nhất trong nhóm FPT, MWG, PNJ tháng trước?",
                "expected_type": "ranking_query",
                "expected_field": "close"
            },
            {
                "query": "Trong nhóm SSI, VCI, HCM mã nào có giá mở thấp nhất hôm nay?",
                "expected_type": "ranking_query",
                "expected_field": "open"
            },
            
            # AGGREGATE QUERY - 5 questions
            {
                "query": "Tổng khối lượng giao dịch của HPG trong 1 tuần.",
                "expected_type": "aggregate_query",
                "expected_field": "volume"
            },
            {
                "query": "Tổng volume của VCB trong 10 ngày vừa qua.",
                "expected_type": "aggregate_query",
                "expected_field": "volume"
            },
            {
                "query": "Tổng volume của VIC trong 1 tháng gần đây.",
                "expected_type": "aggregate_query",
                "expected_field": "volume"
            },
            {
                "query": "Cho tôi giá đóng nhỏ nhất của SSI từ đầu tháng.",
                "expected_type": "aggregate_query",
                "expected_field": "close"
            },
            {
                "query": "Giá đóng trung bình của VCB trong 10 ngày.",
                "expected_type": "aggregate_query",
                "expected_field": "close"
            },
        ]
        
        return self._run_test_cases(test_cases, self.basic_parser, "Basic Parser")
    
    def test_enhanced_parser(self):
        """Test enhanced parser with new query types."""
        test_cases = [
            # Original query types
            {
                "query": "Lấy giá đóng cửa của VCB hôm qua.",
                "expected_type": "price_query",
                "expected_field": "close"
            },
            {
                "query": "Tính SMA9 cho VCB trong 1 tuần gần nhất.",
                "expected_type": "indicator_query",
                "expected_field": "sma"
            },
            {
                "query": "Danh sách cổ đông lớn của VCB.",
                "expected_type": "company_query",
                "expected_field": "shareholders"
            },
            {
                "query": "So sánh khối lượng giao dịch của VIC với HPG trong 1 tuần.",
                "expected_type": "comparison_query",
                "expected_field": "volume"
            },
            {
                "query": "Trong các mã VCB, BID, CTG mã nào có giá mở cửa thấp nhất hôm qua?",
                "expected_type": "ranking_query",
                "expected_field": "open"
            },
            {
                "query": "Tổng khối lượng giao dịch của HPG trong 1 tuần.",
                "expected_type": "aggregate_query",
                "expected_field": "volume"
            },
            
            # New financial ratio queries
            {
                "query": "Tỷ lệ P/E của VNM hiện tại là bao nhiêu?",
                "expected_type": "financial_ratio_query",
                "expected_field": "pe"
            },
            {
                "query": "So sánh ROE giữa FPT và VNM trong 3 năm gần đây",
                "expected_type": "financial_ratio_query",
                "expected_field": "roe"
            },
            {
                "query": "EPS của HPG trong quý 3/2024 là bao nhiêu?",
                "expected_type": "financial_ratio_query",
                "expected_field": "eps"
            },
            
            # New news and sentiment queries
            {
                "query": "Có tin tức gì về VCB trong tuần này không?",
                "expected_type": "news_sentiment_query",
                "expected_field": "news"
            },
            {
                "query": "Cảm xúc thị trường đối với nhóm ngân hàng hiện nay ra sao?",
                "expected_type": "news_sentiment_query",
                "expected_field": "sentiment"
            },
            {
                "query": "Tin tức tích cực về FPT trong tháng 11",
                "expected_type": "news_sentiment_query",
                "expected_field": "news"
            },
            
            # New portfolio queries
            {
                "query": "Nếu tôi mua 100 cổ FPT và 200 cổ VNM thì danh mục hiện tại ra sao?",
                "expected_type": "portfolio_query",
                "expected_field": "portfolio_value"
            },
            {
                "query": "Hiệu suất danh mục của tôi trong tháng 11 là bao nhiêu?",
                "expected_type": "portfolio_query",
                "expected_field": "portfolio_performance"
            },
            {
                "query": "Phân bổ ngành trong danh mục hiện tại",
                "expected_type": "portfolio_query",
                "expected_field": "portfolio_allocation"
            },
            
            # New alert queries
            {
                "query": "Cảnh báo khi giá HPG vượt ngưỡng 50.000",
                "expected_type": "alert_query",
                "expected_field": "price_alert"
            },
            {
                "query": "Thông báo khi volume VNM tăng 50% so với trung bình 20 ngày",
                "expected_type": "alert_query",
                "expected_field": "volume_alert"
            },
            
            # New forecast queries
            {
                "query": "Dự báo giá VNM trong tuần tới",
                "expected_type": "forecast_query",
                "expected_field": "price_forecast"
            },
            {
                "query": "Xu hướng của VN-Index trong tháng 12",
                "expected_type": "forecast_query",
                "expected_field": "trend_analysis"
            },
            
            # New sector queries
            {
                "query": "Các cổ phiếu ngành chứng khoán có performance tốt nhất tuần này?",
                "expected_type": "sector_query",
                "expected_field": "sector_performance"
            },
            {
                "query": "So sánh hiệu suất giữa ngành ngân hàng và bất động sản",
                "expected_type": "sector_query",
                "expected_field": "sector_performance"
            },
        ]
        
        return self._run_enhanced_test_cases(test_cases, self.enhanced_parser, "Enhanced Parser")
    
    def _run_test_cases(self, test_cases, parser, parser_name):
        """Run test cases for a parser."""
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                parsed = parser.parse(test_case["query"])
                success = (
                    parsed.get("query_type") == test_case["expected_type"] and
                    parsed.get("requested_field") == test_case["expected_field"]
                )
                
                results.append({
                    "query": test_case["query"],
                    "parsed": parsed,
                    "success": success,
                    "expected_type": test_case["expected_type"],
                    "expected_field": test_case["expected_field"]
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] {parser_name} - Case {i+1}: {test_case['query']}")
                print(f"  Expected: type={test_case['expected_type']}, field={test_case['expected_field']}")
                print(f"  Got: type={parsed.get('query_type')}, field={parsed.get('requested_field')}")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "parsed": None,
                    "success": False,
                    "expected_type": test_case["expected_type"],
                    "expected_field": test_case["expected_field"],
                    "error": str(e)
                })
                print(f"[FAIL] {parser_name} - Case {i+1}: {test_case['query']}")
                print(f"  Error: {e}")
        
        return results
    
    def _run_enhanced_test_cases(self, test_cases, parser, parser_name):
        """Run test cases for enhanced parser with confidence scoring."""
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                parsed, confidence = parser.parse_with_confidence(test_case["query"])
                success = (
                    parsed.get("query_type") == test_case["expected_type"] and
                    parsed.get("requested_field") == test_case["expected_field"]
                )
                
                results.append({
                    "query": test_case["query"],
                    "parsed": parsed,
                    "confidence": confidence,
                    "success": success,
                    "expected_type": test_case["expected_type"],
                    "expected_field": test_case["expected_field"]
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] {parser_name} - Case {i+1}: {test_case['query']}")
                print(f"  Expected: type={test_case['expected_type']}, field={test_case['expected_field']}")
                print(f"  Got: type={parsed.get('query_type')}, field={parsed.get('requested_field')}")
                print(f"  Confidence: {confidence:.2f}")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "parsed": None,
                    "confidence": 0.0,
                    "success": False,
                    "expected_type": test_case["expected_type"],
                    "expected_field": test_case["expected_field"],
                    "error": str(e)
                })
                print(f"[FAIL] {parser_name} - Case {i+1}: {test_case['query']}")
                print(f"  Error: {e}")
        
        return results
    
    def run_all_tests(self):
        """Run all test suites and generate comprehensive report."""
        print("=== COMPREHENSIVE QUERY PARSER TESTS ===\n")
        
        # Test basic parser
        print("1. Testing Basic Parser...")
        basic_results = self.test_basic_parser()
        
        # Test enhanced parser
        print("\n2. Testing Enhanced Parser...")
        enhanced_results = self.test_enhanced_parser()
        
        # Generate comprehensive report
        self._generate_report(basic_results, enhanced_results)
        
        return {
            "basic_parser": basic_results,
            "enhanced_parser": enhanced_results
        }
    
    def _generate_report(self, basic_results, enhanced_results):
        """Generate comprehensive test report."""
        print("\n" + "="*60)
        print("COMPREHENSIVE TEST REPORT")
        print("="*60)
        
        # Basic parser report
        basic_total = len(basic_results)
        basic_passed = sum(1 for r in basic_results if r["success"])
        basic_failed = basic_total - basic_passed
        
        print(f"\n1. BASIC PARSER RESULTS:")
        print(f"   Total: {basic_total}")
        print(f"   Passed: {basic_passed}")
        print(f"   Failed: {basic_failed}")
        print(f"   Success Rate: {basic_passed/basic_total*100:.1f}%")
        
        # Enhanced parser report
        enhanced_total = len(enhanced_results)
        enhanced_passed = sum(1 for r in enhanced_results if r["success"])
        enhanced_failed = enhanced_total - enhanced_passed
        
        print(f"\n2. ENHANCED PARSER RESULTS:")
        print(f"   Total: {enhanced_total}")
        print(f"   Passed: {enhanced_passed}")
        print(f"   Failed: {enhanced_failed}")
        print(f"   Success Rate: {enhanced_passed/enhanced_total*100:.1f}%")
        
        # Overall report
        total_tests = basic_total + enhanced_total
        total_passed = basic_passed + enhanced_passed
        total_failed = basic_failed + enhanced_failed
        
        print(f"\n3. OVERALL RESULTS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Total Passed: {total_passed}")
        print(f"   Total Failed: {total_failed}")
        print(f"   Overall Success Rate: {total_passed/total_tests*100:.1f}%")
        
        # Detailed failure analysis
        print(f"\n4. DETAILED FAILURE ANALYSIS:")
        
        # Basic parser failures
        print(f"\n   Basic Parser Failures:")
        for r in basic_results:
            if not r["success"]:
                print(f"     - {r['query']}")
                print(f"       Expected: {r['expected_type']}/{r['expected_field']}")
                print(f"       Got: {r['parsed']['query_type'] if r['parsed'] else 'None'}/{r['parsed']['requested_field'] if r['parsed'] else 'None'}")
        
        # Enhanced parser failures
        print(f"\n   Enhanced Parser Failures:")
        for r in enhanced_results:
            if not r["success"]:
                print(f"     - {r['query']}")
                print(f"       Expected: {r['expected_type']}/{r['expected_field']}")
                print(f"       Got: {r['parsed']['query_type'] if r['parsed'] else 'None'}/{r['parsed']['requested_field'] if r['parsed'] else 'None'}")
        
        # Query type analysis
        print(f"\n5. QUERY TYPE ANALYSIS:")
        query_types = {}
        
        # Analyze basic parser
        for r in basic_results:
            qtype = r["expected_type"]
            if qtype not in query_types:
                query_types[qtype] = {"total": 0, "passed": 0, "failed": 0}
            query_types[qtype]["total"] += 1
            if r["success"]:
                query_types[qtype]["passed"] += 1
            else:
                query_types[qtype]["failed"] += 1
        
        # Analyze enhanced parser
        for r in enhanced_results:
            qtype = r["expected_type"]
            if qtype not in query_types:
                query_types[qtype] = {"total": 0, "passed": 0, "failed": 0}
            query_types[qtype]["total"] += 1
            if r["success"]:
                query_types[qtype]["passed"] += 1
            else:
                query_types[qtype]["failed"] += 1
        
        for qtype, stats in query_types.items():
            rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
            print(f"   {qtype}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")
        
        print("\n" + "="*60)


def main():
    """Main test runner."""
    test_suite = TestQueryParserComprehensive()
    results = test_suite.run_all_tests()
    return results


if __name__ == "__main__":
    main()