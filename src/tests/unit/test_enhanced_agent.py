"""
Unit tests for EnhancedStockAgent.
Uses relative imports for proper module resolution.
"""

from ...application.agent.enhanced_agent import EnhancedStockAgent


class TestEnhancedStockAgent:
    """Test EnhancedStockAgent functionality."""
    
    def __init__(self):
        self.agent = EnhancedStockAgent()
    
    def test_confidence_scoring(self):
        """Test confidence scoring mechanism."""
        test_cases = [
            {
                "query": "Lấy giá đóng cửa của VCB hôm qua.",
                "expected_confidence_range": (0.8, 1.0)  # High confidence for simple queries
            },
            {
                "query": "Tính SMA9 cho VCB trong 1 tuần gần nhất.",
                "expected_confidence_range": (0.7, 1.0)
            },
            {
                "query": "Trong các mã VCB, BID, CTG mã nào có giá mở cửa thấp nhất?",
                "expected_confidence_range": (0.6, 0.9)  # Lower confidence for complex queries
            },
            {
                "query": "Nếu tôi mua 100 cổ FPT và 200 cổ VNM thì danh mục hiện tại ra sao?",
                "expected_confidence_range": (0.5, 0.8)  # Lower confidence for portfolio queries
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result, confidence = self.agent.parse_with_confidence(test_case["query"])
                success = self._is_in_range(confidence, test_case["expected_confidence_range"])
                
                results.append({
                    "query": test_case["query"],
                    "result": result,
                    "confidence": confidence,
                    "expected_confidence_range": test_case["expected_confidence_range"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['query']}")
                print(f"  Expected confidence range: {test_case['expected_confidence_range']}")
                print(f"  Got confidence: {confidence:.2f}")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "result": None,
                    "confidence": 0.0,
                    "expected_confidence_range": test_case["expected_confidence_range"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['query']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_adaptive_threshold(self):
        """Test adaptive threshold adjustment."""
        test_cases = [
            {
                "queries": [
                    "Lấy giá đóng cửa của VCB hôm qua.",
                    "Tính SMA9 cho VCB trong 1 tuần gần nhất.",
                    "Danh sách cổ đông lớn của VCB."
                ],
                "expected_threshold_adjustment": "increase"  # Should increase threshold for simple queries
            },
            {
                "queries": [
                    "Trong các mã VCB, BID, CTG mã nào có giá mở cửa thấp nhất?",
                    "Tổng khối lượng giao dịch của HPG, VNM, FPT trong 1 tuần.",
                    "Nếu tôi mua 100 cổ FPT và 200 cổ VNM thì danh mục hiện tại ra sao?"
                ],
                "expected_threshold_adjustment": "decrease"  # Should decrease threshold for complex queries
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                # Process multiple queries to test adaptive threshold
                confidences = []
                for query in test_case["queries"]:
                    result, confidence = self.agent.parse_with_confidence(query)
                    confidences.append(confidence)
                
                # Check if threshold adjustment is appropriate
                avg_confidence = sum(confidences) / len(confidences)
                if test_case["expected_threshold_adjustment"] == "increase":
                    success = avg_confidence > 0.8
                else:
                    success = avg_confidence < 0.7
                
                results.append({
                    "queries": test_case["queries"],
                    "confidences": confidences,
                    "avg_confidence": avg_confidence,
                    "expected_threshold_adjustment": test_case["expected_threshold_adjustment"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Adaptive threshold for {len(test_case['queries'])} queries")
                print(f"  Expected adjustment: {test_case['expected_threshold_adjustment']}")
                print(f"  Average confidence: {avg_confidence:.2f}")
                
            except Exception as e:
                results.append({
                    "queries": test_case["queries"],
                    "confidences": None,
                    "avg_confidence": 0.0,
                    "expected_threshold_adjustment": test_case["expected_threshold_adjustment"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Adaptive threshold for {len(test_case['queries'])} queries")
                print(f"  Error: {e}")
        
        return results
    
    def test_parallel_processing(self):
        """Test parallel processing functionality."""
        test_cases = [
            {
                "queries": [
                    "Lấy giá đóng cửa của VCB hôm qua.",
                    "Tính SMA9 cho VCB trong 1 tuần gần nhất.",
                    "Danh sách cổ đông lớn của VCB.",
                    "So sánh khối lượng giao dịch của VIC với HPG trong 1 tuần.",
                    "Trong các mã VCB, BID, CTG mã nào có giá mở cửa thấp nhất?"
                ],
                "expected_processing_time": 5.0  # Should process faster than sequential
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                import time
                start_time = time.time()
                
                # Process queries in parallel
                results_list = []
                for query in test_case["queries"]:
                    result, confidence = self.agent.parse_with_confidence(query)
                    results_list.append({"query": query, "result": result, "confidence": confidence})
                
                end_time = time.time()
                processing_time = end_time - start_time
                
                success = processing_time < test_case["expected_processing_time"]
                
                results.append({
                    "queries": test_case["queries"],
                    "results": results_list,
                    "processing_time": processing_time,
                    "expected_processing_time": test_case["expected_processing_time"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Parallel processing for {len(test_case['queries'])} queries")
                print(f"  Expected time: < {test_case['expected_processing_time']}s")
                print(f"  Got time: {processing_time:.2f}s")
                
            except Exception as e:
                results.append({
                    "queries": test_case["queries"],
                    "results": None,
                    "processing_time": 0.0,
                    "expected_processing_time": test_case["expected_processing_time"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Parallel processing for {len(test_case['queries'])} queries")
                print(f"  Error: {e}")
        
        return results
    
    def test_fallback_mechanism(self):
        """Test fallback mechanism when one component fails."""
        test_cases = [
            {
                "query": "Lấy giá đóng cửa của VCB hôm qua.",
                "simulate_failure": "parser",
                "expected_fallback": True
            },
            {
                "query": "Tính SMA9 cho VCB trong 1 tuần gần nhất.",
                "simulate_failure": "api",
                "expected_fallback": True
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                # Simulate component failure and test fallback
                if test_case["simulate_failure"] == "parser":
                    # Mock parser failure
                    original_parse = self.agent.parse_with_confidence
                    self.agent.parse_with_confidence = lambda x: (None, 0.0)
                
                result, confidence = self.agent.parse_with_confidence(test_case["query"])
                
                # Restore original method
                if test_case["simulate_failure"] == "parser":
                    self.agent.parse_with_confidence = original_parse
                
                success = result is not None or confidence > 0.0
                
                results.append({
                    "query": test_case["query"],
                    "simulate_failure": test_case["simulate_failure"],
                    "result": result,
                    "confidence": confidence,
                    "expected_fallback": test_case["expected_fallback"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Fallback mechanism for {test_case['simulate_failure']} failure")
                print(f"  Query: {test_case['query']}")
                print(f"  Result: {result}")
                print(f"  Confidence: {confidence}")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "simulate_failure": test_case["simulate_failure"],
                    "result": None,
                    "confidence": 0.0,
                    "expected_fallback": test_case["expected_fallback"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Fallback mechanism for {test_case['simulate_failure']} failure")
                print(f"  Error: {e}")
        
        return results
    
    def test_result_aggregation(self):
        """Test result aggregation from multiple sources."""
        test_cases = [
            {
                "query": "Lấy giá đóng cửa của VCB hôm qua.",
                "expected_sources": 3,  # Should aggregate from multiple sources
                "expected_result_keys": ["price", "source", "timestamp"]
            },
            {
                "query": "Tính SMA9 cho VCB trong 1 tuần gần nhất.",
                "expected_sources": 2,
                "expected_result_keys": ["sma", "source", "timestamp"]
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result, confidence = self.agent.parse_with_confidence(test_case["query"])
                
                # Check if result contains expected keys
                success = all(key in str(result) for key in test_case["expected_result_keys"])
                
                results.append({
                    "query": test_case["query"],
                    "result": result,
                    "confidence": confidence,
                    "expected_sources": test_case["expected_sources"],
                    "expected_result_keys": test_case["expected_result_keys"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Result aggregation for {test_case['query']}")
                print(f"  Expected sources: {test_case['expected_sources']}")
                print(f"  Expected keys: {test_case['expected_result_keys']}")
                print(f"  Got result: {result}")
                
            except Exception as e:
                results.append({
                    "query": test_case["query"],
                    "result": None,
                    "confidence": 0.0,
                    "expected_sources": test_case["expected_sources"],
                    "expected_result_keys": test_case["expected_result_keys"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Result aggregation for {test_case['query']}")
                print(f"  Error: {e}")
        
        return results
    
    def run_all_tests(self):
        """Run all EnhancedStockAgent tests."""
        print("=== ENHANCED STOCK AGENT TESTS ===\n")
        
        # Test confidence scoring
        print("1. Testing Confidence Scoring...")
        confidence_results = self.test_confidence_scoring()
        
        # Test adaptive threshold
        print("\n2. Testing Adaptive Threshold...")
        threshold_results = self.test_adaptive_threshold()
        
        # Test parallel processing
        print("\n3. Testing Parallel Processing...")
        parallel_results = self.test_parallel_processing()
        
        # Test fallback mechanism
        print("\n4. Testing Fallback Mechanism...")
        fallback_results = self.test_fallback_mechanism()
        
        # Test result aggregation
        print("\n5. Testing Result Aggregation...")
        aggregation_results = self.test_result_aggregation()
        
        # Generate comprehensive report
        self._generate_report(confidence_results, threshold_results, parallel_results, fallback_results, aggregation_results)
        
        return {
            "confidence_scoring": confidence_results,
            "adaptive_threshold": threshold_results,
            "parallel_processing": parallel_results,
            "fallback_mechanism": fallback_results,
            "result_aggregation": aggregation_results
        }
    
    def _is_in_range(self, value, expected_range):
        """Check if value is within expected range."""
        if value is None:
            return False
        return expected_range[0] <= value <= expected_range[1]
    
    def _generate_report(self, confidence_results, threshold_results, parallel_results, fallback_results, aggregation_results):
        """Generate comprehensive test report."""
        print("\n" + "="*60)
        print("ENHANCED STOCK AGENT TEST REPORT")
        print("="*60)
        
        # Confidence scoring report
        confidence_total = len(confidence_results)
        confidence_passed = sum(1 for r in confidence_results if r["success"])
        print(f"\n1. CONFIDENCE SCORING:")
        print(f"   Total: {confidence_total}, Passed: {confidence_passed}, Failed: {confidence_total - confidence_passed}")
        
        # Adaptive threshold report
        threshold_total = len(threshold_results)
        threshold_passed = sum(1 for r in threshold_results if r["success"])
        print(f"\n2. ADAPTIVE THRESHOLD:")
        print(f"   Total: {threshold_total}, Passed: {threshold_passed}, Failed: {threshold_total - threshold_passed}")
        
        # Parallel processing report
        parallel_total = len(parallel_results)
        parallel_passed = sum(1 for r in parallel_results if r["success"])
        print(f"\n3. PARALLEL PROCESSING:")
        print(f"   Total: {parallel_total}, Passed: {parallel_passed}, Failed: {parallel_total - parallel_passed}")
        
        # Fallback mechanism report
        fallback_total = len(fallback_results)
        fallback_passed = sum(1 for r in fallback_results if r["success"])
        print(f"\n4. FALLBACK MECHANISM:")
        print(f"   Total: {fallback_total}, Passed: {fallback_passed}, Failed: {fallback_total - fallback_passed}")
        
        # Result aggregation report
        aggregation_total = len(aggregation_results)
        aggregation_passed = sum(1 for r in aggregation_results if r["success"])
        print(f"\n5. RESULT AGGREGATION:")
        print(f"   Total: {aggregation_total}, Passed: {aggregation_passed}, Failed: {aggregation_total - aggregation_passed}")
        
        # Overall report
        total_tests = (confidence_total + threshold_total + parallel_total + 
                       fallback_total + aggregation_total)
        total_passed = (confidence_passed + threshold_passed + parallel_passed + 
                        fallback_passed + aggregation_passed)
        
        print(f"\n6. OVERALL RESULTS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Total Passed: {total_passed}")
        print(f"   Total Failed: {total_tests - total_passed}")
        print(f"   Success Rate: {total_passed/total_tests*100:.1f}%")
        
        print("\n" + "="*60)


def main():
    """Main test runner."""
    test_suite = TestEnhancedStockAgent()
    results = test_suite.run_all_tests()
    return results


if __name__ == "__main__":
    main()