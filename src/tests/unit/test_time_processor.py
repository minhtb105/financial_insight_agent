"""
Unit tests for TimeProcessor class.
Uses relative imports for proper module resolution.
"""

from domain.services.base.time_processor import TimeProcessor


class TestTimeProcessor:
    """Test TimeProcessor functionality."""
    
    def __init__(self):
        self.processor = TimeProcessor()
    
    def test_parse_time_range(self):
        """Test parsing various time range formats using process_time_params."""
        test_cases = [
            {
                "input": {"days": 7},
                "expected": {"start_date": "2026-03-03", "end_date": "2026-03-10"}
            },
            {
                "input": {"months": 1},
                "expected": {"start_date": "2026-02-10", "end_date": "2026-03-10"}
            },
            {
                "input": {"weeks": 3},
                "expected": {"start_date": "2026-02-17", "end_date": "2026-03-10"}
            },
            {
                "input": {"start": "2026-01-01", "end": "2026-01-31"},
                "expected": {"start_date": "2026-01-01", "end_date": "2026-01-31"}
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.processor.process_time_params(test_case["input"])
                success = result["start_date"] == test_case["expected"]["start_date"] and result["end_date"] == test_case["expected"]["end_date"]
                
                results.append({
                    "input": test_case["input"],
                    "result": result,
                    "expected": test_case["expected"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['input']}")
                print(f"  Expected: {test_case['expected']}")
                print(f"  Got: {result}")
                
            except Exception as e:
                results.append({
                    "input": test_case["input"],
                    "result": None,
                    "expected": test_case["expected"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['input']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_parse_specific_date(self):
        """Test parsing specific dates using process_time_params."""
        test_cases = [
            {
                "input": {"end": "yesterday"},
                "expected": "2026-03-09"
            },
            {
                "input": {"end": "today"},
                "expected": "2026-03-10"
            },
            {
                "input": {"end": "last_week"},
                "expected": "2026-03-03"
            },
            {
                "input": {"end": "last_month"},
                "expected": "2026-02-10"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.processor.process_time_params(test_case["input"])
                success = result["end_date"] == test_case["expected"]
                
                results.append({
                    "input": test_case["input"],
                    "result": result,
                    "expected": test_case["expected"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['input']}")
                print(f"  Expected: {test_case['expected']}")
                print(f"  Got: {result}")
                
            except Exception as e:
                results.append({
                    "input": test_case["input"],
                    "result": None,
                    "expected": test_case["expected"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['input']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_parse_relative_date(self):
        """Test parsing relative dates using process_time_params."""
        test_cases = [
            {
                "input": {"end": "yesterday", "days": 7},
                "expected": "2026-03-03"
            },
            {
                "input": {"end": "yesterday", "months": 1},
                "expected": "2026-02-10"
            },
            {
                "input": {"end": "yesterday", "weeks": 3},
                "expected": "2026-02-17"
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.processor.process_time_params(test_case["input"])
                success = result["start_date"] == test_case["expected"]
                
                results.append({
                    "input": test_case["input"],
                    "result": result,
                    "expected": test_case["expected"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['input']}")
                print(f"  Expected: {test_case['expected']}")
                print(f"  Got: {result}")
                
            except Exception as e:
                results.append({
                    "input": test_case["input"],
                    "result": None,
                    "expected": test_case["expected"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['input']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_validate_time_parameters(self):
        """Test time parameter validation using validate_time_range."""
        test_cases = [
            {
                "input": {"start_date": "2026-03-01", "end_date": "2026-03-09"},
                "expected": True
            },
            {
                "input": {"start_date": "2026-03-09", "end_date": "2026-03-01"},
                "expected": False  # start > end
            },
            {
                "input": {"start_date": "2027-01-01", "end_date": "2027-01-09"},
                "expected": False  # future dates
            },
            {
                "input": {"start_date": "2026-01-01", "end_date": "2026-12-31"},
                "expected": False  # too long range
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.processor.validate_time_range(test_case["input"]["start_date"], test_case["input"]["end_date"])
                success = result == test_case["expected"]
                
                results.append({
                    "input": test_case["input"],
                    "result": result,
                    "expected": test_case["expected"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: {test_case['input']}")
                print(f"  Expected: {test_case['expected']}")
                print(f"  Got: {result}")
                
            except Exception as e:
                results.append({
                    "input": test_case["input"],
                    "result": None,
                    "expected": test_case["expected"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: {test_case['input']}")
                print(f"  Error: {e}")
        
        return results
    
    def run_all_tests(self):
        """Run all TimeProcessor tests."""
        print("=== TIME PROCESSOR TESTS ===\n")
        
        # Test time range parsing
        print("1. Testing Time Range Parsing...")
        range_results = self.test_parse_time_range()
        
        # Test specific date parsing
        print("\n2. Testing Specific Date Parsing...")
        specific_results = self.test_parse_specific_date()
        
        # Test relative date parsing
        print("\n3. Testing Relative Date Parsing...")
        relative_results = self.test_parse_relative_date()
        
        # Test validation
        print("\n4. Testing Time Parameter Validation...")
        validation_results = self.test_validate_time_parameters()
        
        # Generate report
        self._generate_report(range_results, specific_results, relative_results, validation_results)
        
        return {
            "time_range": range_results,
            "specific_date": specific_results,
            "relative_date": relative_results,
            "validation": validation_results
        }
    
    def _generate_report(self, range_results, specific_results, relative_results, validation_results):
        """Generate test report."""
        print("\n" + "="*50)
        print("TIME PROCESSOR TEST REPORT")
        print("="*50)
        
        # Time range parsing report
        range_total = len(range_results)
        range_passed = sum(1 for r in range_results if r["success"])
        print(f"\n1. TIME RANGE PARSING:")
        print(f"   Total: {range_total}, Passed: {range_passed}, Failed: {range_total - range_passed}")
        
        # Specific date parsing report
        specific_total = len(specific_results)
        specific_passed = sum(1 for r in specific_results if r["success"])
        print(f"\n2. SPECIFIC DATE PARSING:")
        print(f"   Total: {specific_total}, Passed: {specific_passed}, Failed: {specific_total - specific_passed}")
        
        # Relative date parsing report
        relative_total = len(relative_results)
        relative_passed = sum(1 for r in relative_results if r["success"])
        print(f"\n3. RELATIVE DATE PARSING:")
        print(f"   Total: {relative_total}, Passed: {relative_passed}, Failed: {relative_total - relative_passed}")
        
        # Validation report
        validation_total = len(validation_results)
        validation_passed = sum(1 for r in validation_results if r["success"])
        print(f"\n4. TIME PARAMETER VALIDATION:")
        print(f"   Total: {validation_total}, Passed: {validation_passed}, Failed: {validation_total - validation_passed}")
        
        # Overall report
        total_tests = range_total + specific_total + relative_total + validation_total
        total_passed = range_passed + specific_passed + relative_passed + validation_passed
        print(f"\n5. OVERALL RESULTS:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Total Passed: {total_passed}")
        print(f"   Total Failed: {total_tests - total_passed}")
        print(f"   Success Rate: {total_passed/total_tests*100:.1f}%")
        
        print("\n" + "="*50)


def main():
    """Main test runner."""
    test_suite = TestTimeProcessor()
    results = test_suite.run_all_tests()
    return results


if __name__ == "__main__":
    main()