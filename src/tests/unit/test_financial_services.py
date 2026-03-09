"""
Unit tests for financial services.
Uses relative imports for proper module resolution.
"""

from domain.services.financial.financial_ratio_service import FinancialRatioService
from domain.services.financial.aggregate_service import AggregateService
from domain.services.financial.ranking_service import RankingService


class TestFinancialRatioService:
    """Test financial ratio service."""
    
    def __init__(self):
        self.service = FinancialRatioService()
    
    def test_get_pe_ratio(self):
        """Test P/E ratio calculation."""
        test_cases = [
            {
                "ticker": "VNM",
                "expected_range": (5.0, 50.0)  # Reasonable P/E range
            },
            {
                "ticker": "HPG",
                "expected_range": (3.0, 30.0)
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.get_pe_ratio(test_case["ticker"])
                success = self._is_in_range(result, test_case["expected_range"])
                
                results.append({
                    "ticker": test_case["ticker"],
                    "result": result,
                    "expected_range": test_case["expected_range"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: P/E ratio for {test_case['ticker']}")
                print(f"  Expected range: {test_case['expected_range']}")
                print(f"  Got: {result}")
                
            except Exception as e:
                results.append({
                    "ticker": test_case["ticker"],
                    "result": None,
                    "expected_range": test_case["expected_range"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: P/E ratio for {test_case['ticker']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_get_roe_ratio(self):
        """Test ROE ratio calculation."""
        test_cases = [
            {
                "ticker": "VNM",
                "expected_range": (0.05, 0.30)  # 5% to 30%
            },
            {
                "ticker": "HPG",
                "expected_range": (0.02, 0.25)  # 2% to 25%
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.get_roe_ratio(test_case["ticker"])
                success = self._is_in_range(result, test_case["expected_range"])
                
                results.append({
                    "ticker": test_case["ticker"],
                    "result": result,
                    "expected_range": test_case["expected_range"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: ROE ratio for {test_case['ticker']}")
                print(f"  Expected range: {test_case['expected_range']}")
                print(f"  Got: {result}")
                
            except Exception as e:
                results.append({
                    "ticker": test_case["ticker"],
                    "result": None,
                    "expected_range": test_case["expected_range"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: ROE ratio for {test_case['ticker']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_get_eps(self):
        """Test EPS calculation."""
        test_cases = [
            {
                "ticker": "VNM",
                "expected_range": (0.0, 10000.0)  # Reasonable EPS range in VND
            },
            {
                "ticker": "HPG",
                "expected_range": (0.0, 5000.0)
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.get_eps(test_case["ticker"])
                success = self._is_in_range(result, test_case["expected_range"])
                
                results.append({
                    "ticker": test_case["ticker"],
                    "result": result,
                    "expected_range": test_case["expected_range"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: EPS for {test_case['ticker']}")
                print(f"  Expected range: {test_case['expected_range']}")
                print(f"  Got: {result}")
                
            except Exception as e:
                results.append({
                    "ticker": test_case["ticker"],
                    "result": None,
                    "expected_range": test_case["expected_range"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: EPS for {test_case['ticker']}")
                print(f"  Error: {e}")
        
        return results
    
    def _is_in_range(self, value, expected_range):
        """Check if value is within expected range."""
        if value is None:
            return False
        return expected_range[0] <= value <= expected_range[1]


class TestAggregateService:
    """Test aggregate service."""
    
    def __init__(self):
        self.service = AggregateService()
    
    def test_calculate_market_cap(self):
        """Test market cap calculation."""
        test_cases = [
            {
                "ticker": "VNM",
                "expected_range": (1000000000000.0, 10000000000000.0)  # 1T to 10T VND
            },
            {
                "ticker": "HPG",
                "expected_range": (500000000000.0, 5000000000000.0)  # 500B to 5T VND
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.calculate_market_cap(test_case["ticker"])
                success = self._is_in_range(result, test_case["expected_range"])
                
                results.append({
                    "ticker": test_case["ticker"],
                    "result": result,
                    "expected_range": test_case["expected_range"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Market cap for {test_case['ticker']}")
                print(f"  Expected range: {test_case['expected_range']}")
                print(f"  Got: {result}")
                
            except Exception as e:
                results.append({
                    "ticker": test_case["ticker"],
                    "result": None,
                    "expected_range": test_case["expected_range"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Market cap for {test_case['ticker']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_calculate_beta(self):
        """Test beta calculation."""
        test_cases = [
            {
                "ticker": "VNM",
                "expected_range": (0.5, 2.0)  # Reasonable beta range
            },
            {
                "ticker": "HPG",
                "expected_range": (0.8, 2.5)
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.calculate_beta(test_case["ticker"])
                success = self._is_in_range(result, test_case["expected_range"])
                
                results.append({
                    "ticker": test_case["ticker"],
                    "result": result,
                    "expected_range": test_case["expected_range"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Beta for {test_case['ticker']}")
                print(f"  Expected range: {test_case['expected_range']}")
                print(f"  Got: {result}")
                
            except Exception as e:
                results.append({
                    "ticker": test_case["ticker"],
                    "result": None,
                    "expected_range": test_case["expected_range"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Beta for {test_case['ticker']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_calculate_dividend_yield(self):
        """Test dividend yield calculation."""
        test_cases = [
            {
                "ticker": "VNM",
                "expected_range": (0.0, 0.15)  # 0% to 15%
            },
            {
                "ticker": "HPG",
                "expected_range": (0.0, 0.20)  # 0% to 20%
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.calculate_dividend_yield(test_case["ticker"])
                success = self._is_in_range(result, test_case["expected_range"])
                
                results.append({
                    "ticker": test_case["ticker"],
                    "result": result,
                    "expected_range": test_case["expected_range"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Dividend yield for {test_case['ticker']}")
                print(f"  Expected range: {test_case['expected_range']}")
                print(f"  Got: {result}")
                
            except Exception as e:
                results.append({
                    "ticker": test_case["ticker"],
                    "result": None,
                    "expected_range": test_case["expected_range"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Dividend yield for {test_case['ticker']}")
                print(f"  Error: {e}")
        
        return results
    
    def _is_in_range(self, value, expected_range):
        """Check if value is within expected range."""
        if value is None:
            return False
        return expected_range[0] <= value <= expected_range[1]


class TestRankingService:
    """Test ranking service."""
    
    def __init__(self):
        self.service = RankingService()
    
    def test_rank_by_performance(self):
        """Test performance ranking."""
        test_cases = [
            {
                "tickers": ["VNM", "HPG", "VIC"],
                "time_range": "1 tuần",
                "expected_length": 3
            },
            {
                "tickers": ["VCB", "BID", "CTG"],
                "time_range": "1 tháng",
                "expected_length": 3
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.rank_by_performance(test_case["tickers"], test_case["time_range"])
                success = len(result) == test_case["expected_length"]
                
                results.append({
                    "tickers": test_case["tickers"],
                    "time_range": test_case["time_range"],
                    "result": result,
                    "expected_length": test_case["expected_length"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Performance ranking for {test_case['tickers']}")
                print(f"  Expected length: {test_case['expected_length']}")
                print(f"  Got length: {len(result)}")
                print(f"  Result: {result}")
                
            except Exception as e:
                results.append({
                    "tickers": test_case["tickers"],
                    "time_range": test_case["time_range"],
                    "result": None,
                    "expected_length": test_case["expected_length"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Performance ranking for {test_case['tickers']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_rank_by_volume(self):
        """Test volume ranking."""
        test_cases = [
            {
                "tickers": ["VNM", "HPG", "VIC"],
                "time_range": "1 tuần",
                "expected_length": 3
            },
            {
                "tickers": ["VCB", "BID", "CTG"],
                "time_range": "1 tháng",
                "expected_length": 3
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.rank_by_volume(test_case["tickers"], test_case["time_range"])
                success = len(result) == test_case["expected_length"]
                
                results.append({
                    "tickers": test_case["tickers"],
                    "time_range": test_case["time_range"],
                    "result": result,
                    "expected_length": test_case["expected_length"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Volume ranking for {test_case['tickers']}")
                print(f"  Expected length: {test_case['expected_length']}")
                print(f"  Got length: {len(result)}")
                print(f"  Result: {result}")
                
            except Exception as e:
                results.append({
                    "tickers": test_case["tickers"],
                    "time_range": test_case["time_range"],
                    "result": None,
                    "expected_length": test_case["expected_length"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Volume ranking for {test_case['tickers']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_rank_by_market_cap(self):
        """Test market cap ranking."""
        test_cases = [
            {
                "tickers": ["VNM", "HPG", "VIC"],
                "expected_length": 3
            },
            {
                "tickers": ["VCB", "BID", "CTG"],
                "expected_length": 3
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.rank_by_market_cap(test_case["tickers"])
                success = len(result) == test_case["expected_length"]
                
                results.append({
                    "tickers": test_case["tickers"],
                    "result": result,
                    "expected_length": test_case["expected_length"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Market cap ranking for {test_case['tickers']}")
                print(f"  Expected length: {test_case['expected_length']}")
                print(f"  Got length: {len(result)}")
                print(f"  Result: {result}")
                
            except Exception as e:
                results.append({
                    "tickers": test_case["tickers"],
                    "result": None,
                    "expected_length": test_case["expected_length"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Market cap ranking for {test_case['tickers']}")
                print(f"  Error: {e}")
        
        return results


def main():
    """Main test runner for financial services."""
    print("=== FINANCIAL SERVICES TESTS ===\n")
    
    # Test Financial Ratio Service
    print("1. Testing Financial Ratio Service...")
    ratio_service = TestFinancialRatioService()
    ratio_results = {
        "pe_ratio": ratio_service.test_get_pe_ratio(),
        "roe_ratio": ratio_service.test_get_roe_ratio(),
        "eps": ratio_service.test_get_eps()
    }
    
    # Test Aggregate Service
    print("\n2. Testing Aggregate Service...")
    aggregate_service = TestAggregateService()
    aggregate_results = {
        "market_cap": aggregate_service.test_calculate_market_cap(),
        "beta": aggregate_service.test_calculate_beta(),
        "dividend_yield": aggregate_service.test_calculate_dividend_yield()
    }
    
    # Test Ranking Service
    print("\n3. Testing Ranking Service...")
    ranking_service = TestRankingService()
    ranking_results = {
        "performance": ranking_service.test_rank_by_performance(),
        "volume": ranking_service.test_rank_by_volume(),
        "market_cap": ranking_service.test_rank_by_market_cap()
    }
    
    # Generate comprehensive report
    _generate_comprehensive_report(ratio_results, aggregate_results, ranking_results)
    
    return {
        "financial_ratio": ratio_results,
        "aggregate": aggregate_results,
        "ranking": ranking_results
    }


def _generate_comprehensive_report(ratio_results, aggregate_results, ranking_results):
    """Generate comprehensive test report."""
    print("\n" + "="*60)
    print("FINANCIAL SERVICES TEST REPORT")
    print("="*60)
    
    # Financial Ratio Service report
    print(f"\n1. FINANCIAL RATIO SERVICE:")
    pe_total = len(ratio_results["pe_ratio"])
    pe_passed = sum(1 for r in ratio_results["pe_ratio"] if r["success"])
    print(f"   P/E Ratio: {pe_passed}/{pe_total} passed")
    
    roe_total = len(ratio_results["roe_ratio"])
    roe_passed = sum(1 for r in ratio_results["roe_ratio"] if r["success"])
    print(f"   ROE Ratio: {roe_passed}/{roe_total} passed")
    
    eps_total = len(ratio_results["eps"])
    eps_passed = sum(1 for r in ratio_results["eps"] if r["success"])
    print(f"   EPS: {eps_passed}/{eps_total} passed")
    
    # Aggregate Service report
    print(f"\n2. AGGREGATE SERVICE:")
    market_cap_total = len(aggregate_results["market_cap"])
    market_cap_passed = sum(1 for r in aggregate_results["market_cap"] if r["success"])
    print(f"   Market Cap: {market_cap_passed}/{market_cap_total} passed")
    
    beta_total = len(aggregate_results["beta"])
    beta_passed = sum(1 for r in aggregate_results["beta"] if r["success"])
    print(f"   Beta: {beta_passed}/{beta_total} passed")
    
    dividend_total = len(aggregate_results["dividend_yield"])
    dividend_passed = sum(1 for r in aggregate_results["dividend_yield"] if r["success"])
    print(f"   Dividend Yield: {dividend_passed}/{dividend_total} passed")
    
    # Ranking Service report
    print(f"\n3. RANKING SERVICE:")
    performance_total = len(ranking_results["performance"])
    performance_passed = sum(1 for r in ranking_results["performance"] if r["success"])
    print(f"   Performance Ranking: {performance_passed}/{performance_total} passed")
    
    volume_total = len(ranking_results["volume"])
    volume_passed = sum(1 for r in ranking_results["volume"] if r["success"])
    print(f"   Volume Ranking: {volume_passed}/{volume_total} passed")
    
    market_cap_rank_total = len(ranking_results["market_cap"])
    market_cap_rank_passed = sum(1 for r in ranking_results["market_cap"] if r["success"])
    print(f"   Market Cap Ranking: {market_cap_rank_passed}/{market_cap_rank_total} passed")
    
    # Overall report
    total_tests = (pe_total + roe_total + eps_total + 
                   market_cap_total + beta_total + dividend_total +
                   performance_total + volume_total + market_cap_rank_total)
    total_passed = (pe_passed + roe_passed + eps_passed +
                    market_cap_passed + beta_passed + dividend_passed +
                    performance_passed + volume_passed + market_cap_rank_passed)
    
    print(f"\n4. OVERALL RESULTS:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Total Passed: {total_passed}")
    print(f"   Total Failed: {total_tests - total_passed}")
    print(f"   Success Rate: {total_passed/total_tests*100:.1f}%")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()