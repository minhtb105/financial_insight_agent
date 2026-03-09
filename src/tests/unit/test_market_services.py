"""
Unit tests for market services.
Uses relative imports for proper module resolution.
"""

from ...domain.services.market.compare_service import CompareService
from ...domain.services.market.indicator_service import IndicatorService
from ...domain.services.market.price_service import PriceService


class TestCompareService:
    """Test compare service."""
    
    def __init__(self):
        self.service = CompareService()
    
    def test_compare_two_stocks(self):
        """Test comparing two stocks."""
        test_cases = [
            {
                "ticker1": "VNM",
                "ticker2": "HPG",
                "metrics": ["price", "volume"],
                "time_range": "1 tuần",
                "expected_keys": ["ticker1", "ticker2", "comparison"]
            },
            {
                "ticker1": "VCB",
                "ticker2": "BID",
                "metrics": ["close", "volume"],
                "time_range": "1 tháng",
                "expected_keys": ["ticker1", "ticker2", "comparison"]
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.compare_two_stocks(
                    test_case["ticker1"],
                    test_case["ticker2"],
                    test_case["metrics"],
                    test_case["time_range"]
                )
                success = all(key in result for key in test_case["expected_keys"])
                
                results.append({
                    "ticker1": test_case["ticker1"],
                    "ticker2": test_case["ticker2"],
                    "metrics": test_case["metrics"],
                    "time_range": test_case["time_range"],
                    "result": result,
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Compare {test_case['ticker1']} vs {test_case['ticker2']}")
                print(f"  Expected keys: {test_case['expected_keys']}")
                print(f"  Got keys: {list(result.keys()) if result else 'None'}")
                
            except Exception as e:
                results.append({
                    "ticker1": test_case["ticker1"],
                    "ticker2": test_case["ticker2"],
                    "metrics": test_case["metrics"],
                    "time_range": test_case["time_range"],
                    "result": None,
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Compare {test_case['ticker1']} vs {test_case['ticker2']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_compare_multiple_stocks(self):
        """Test comparing multiple stocks."""
        test_cases = [
            {
                "tickers": ["VNM", "HPG", "VIC"],
                "metrics": ["price", "volume"],
                "time_range": "1 tuần",
                "expected_length": 3
            },
            {
                "tickers": ["VCB", "BID", "CTG"],
                "metrics": ["close", "volume"],
                "time_range": "1 tháng",
                "expected_length": 3
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.compare_multiple_stocks(
                    test_case["tickers"],
                    test_case["metrics"],
                    test_case["time_range"]
                )
                success = len(result) == test_case["expected_length"]
                
                results.append({
                    "tickers": test_case["tickers"],
                    "metrics": test_case["metrics"],
                    "time_range": test_case["time_range"],
                    "result": result,
                    "expected_length": test_case["expected_length"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Compare multiple stocks {test_case['tickers']}")
                print(f"  Expected length: {test_case['expected_length']}")
                print(f"  Got length: {len(result) if result else 0}")
                
            except Exception as e:
                results.append({
                    "tickers": test_case["tickers"],
                    "metrics": test_case["metrics"],
                    "time_range": test_case["time_range"],
                    "result": None,
                    "expected_length": test_case["expected_length"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Compare multiple stocks {test_case['tickers']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_compare_with_metrics(self):
        """Test comparison with specific metrics."""
        test_cases = [
            {
                "tickers": ["VNM", "HPG"],
                "metrics": ["price_change", "volume_change"],
                "time_range": "1 tuần",
                "expected_metrics": ["price_change", "volume_change"]
            },
            {
                "tickers": ["VCB", "BID"],
                "metrics": ["close_change", "volume_change"],
                "time_range": "1 tháng",
                "expected_metrics": ["close_change", "volume_change"]
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.compare_with_metrics(
                    test_case["tickers"],
                    test_case["metrics"],
                    test_case["time_range"]
                )
                success = all(metric in str(result) for metric in test_case["expected_metrics"])
                
                results.append({
                    "tickers": test_case["tickers"],
                    "metrics": test_case["metrics"],
                    "time_range": test_case["time_range"],
                    "result": result,
                    "expected_metrics": test_case["expected_metrics"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Compare with metrics {test_case['metrics']}")
                print(f"  Expected metrics: {test_case['expected_metrics']}")
                print(f"  Got: {result}")
                
            except Exception as e:
                results.append({
                    "tickers": test_case["tickers"],
                    "metrics": test_case["metrics"],
                    "time_range": test_case["time_range"],
                    "result": None,
                    "expected_metrics": test_case["expected_metrics"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Compare with metrics {test_case['metrics']}")
                print(f"  Error: {e}")
        
        return results


class TestIndicatorService:
    """Test indicator service."""
    
    def __init__(self):
        self.service = IndicatorService()
    
    def test_calculate_bollinger_bands(self):
        """Test Bollinger Bands calculation."""
        test_cases = [
            {
                "ticker": "VNM",
                "period": 20,
                "expected_keys": ["upper_band", "middle_band", "lower_band"]
            },
            {
                "ticker": "HPG",
                "period": 14,
                "expected_keys": ["upper_band", "middle_band", "lower_band"]
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.calculate_bollinger_bands(
                    test_case["ticker"],
                    test_case["period"]
                )
                success = all(key in result for key in test_case["expected_keys"])
                
                results.append({
                    "ticker": test_case["ticker"],
                    "period": test_case["period"],
                    "result": result,
                    "expected_keys": test_case["expected_keys"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Bollinger Bands for {test_case['ticker']}")
                print(f"  Expected keys: {test_case['expected_keys']}")
                print(f"  Got keys: {list(result.keys()) if result else 'None'}")
                
            except Exception as e:
                results.append({
                    "ticker": test_case["ticker"],
                    "period": test_case["period"],
                    "result": None,
                    "expected_keys": test_case["expected_keys"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Bollinger Bands for {test_case['ticker']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_calculate_stochastic(self):
        """Test Stochastic calculation."""
        test_cases = [
            {
                "ticker": "VNM",
                "k_period": 14,
                "d_period": 3,
                "expected_keys": ["k", "d"]
            },
            {
                "ticker": "HPG",
                "k_period": 10,
                "d_period": 3,
                "expected_keys": ["k", "d"]
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.calculate_stochastic(
                    test_case["ticker"],
                    test_case["k_period"],
                    test_case["d_period"]
                )
                success = all(key in result for key in test_case["expected_keys"])
                
                results.append({
                    "ticker": test_case["ticker"],
                    "k_period": test_case["k_period"],
                    "d_period": test_case["d_period"],
                    "result": result,
                    "expected_keys": test_case["expected_keys"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Stochastic for {test_case['ticker']}")
                print(f"  Expected keys: {test_case['expected_keys']}")
                print(f"  Got keys: {list(result.keys()) if result else 'None'}")
                
            except Exception as e:
                results.append({
                    "ticker": test_case["ticker"],
                    "k_period": test_case["k_period"],
                    "d_period": test_case["d_period"],
                    "result": None,
                    "expected_keys": test_case["expected_keys"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: Stochastic for {test_case['ticker']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_calculate_adx(self):
        """Test ADX calculation."""
        test_cases = [
            {
                "ticker": "VNM",
                "period": 14,
                "expected_keys": ["adx", "plus_di", "minus_di"]
            },
            {
                "ticker": "HPG",
                "period": 20,
                "expected_keys": ["adx", "plus_di", "minus_di"]
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.calculate_adx(
                    test_case["ticker"],
                    test_case["period"]
                )
                success = all(key in result for key in test_case["expected_keys"])
                
                results.append({
                    "ticker": test_case["ticker"],
                    "period": test_case["period"],
                    "result": result,
                    "expected_keys": test_case["expected_keys"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: ADX for {test_case['ticker']}")
                print(f"  Expected keys: {test_case['expected_keys']}")
                print(f"  Got keys: {list(result.keys()) if result else 'None'}")
                
            except Exception as e:
                results.append({
                    "ticker": test_case["ticker"],
                    "period": test_case["period"],
                    "result": None,
                    "expected_keys": test_case["expected_keys"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: ADX for {test_case['ticker']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_calculate_atr(self):
        """Test ATR calculation."""
        test_cases = [
            {
                "ticker": "VNM",
                "period": 14,
                "expected_keys": ["atr"]
            },
            {
                "ticker": "HPG",
                "period": 20,
                "expected_keys": ["atr"]
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.calculate_atr(
                    test_case["ticker"],
                    test_case["period"]
                )
                success = all(key in result for key in test_case["expected_keys"])
                
                results.append({
                    "ticker": test_case["ticker"],
                    "period": test_case["period"],
                    "result": result,
                    "expected_keys": test_case["expected_keys"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: ATR for {test_case['ticker']}")
                print(f"  Expected keys: {test_case['expected_keys']}")
                print(f"  Got keys: {list(result.keys()) if result else 'None'}")
                
            except Exception as e:
                results.append({
                    "ticker": test_case["ticker"],
                    "period": test_case["period"],
                    "result": None,
                    "expected_keys": test_case["expected_keys"],
                    "success": False,
                    "error": str(e)
                })
                print(f"[FAIL] Case {i+1}: ATR for {test_case['ticker']}")
                print(f"  Error: {e}")
        
        return results


class TestPriceService:
    """Test price service."""
    
    def __init__(self):
        self.service = PriceService()
    
    def test_get_ohlcv_data(self):
        """Test OHLCV data retrieval."""
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
                result = self.service.get_ohlcv_data(
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
                print(f"[{status}] Case {i+1}: OHLCV data for {test_case['ticker']}")
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
                print(f"[FAIL] Case {i+1}: OHLCV data for {test_case['ticker']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_get_price_history(self):
        """Test price history retrieval."""
        test_cases = [
            {
                "ticker": "VNM",
                "time_range": "1 tuần",
                "expected_keys": ["dates", "prices"]
            },
            {
                "ticker": "HPG",
                "time_range": "1 tháng",
                "expected_keys": ["dates", "prices"]
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.get_price_history(
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
                print(f"[{status}] Case {i+1}: Price history for {test_case['ticker']}")
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
                print(f"[FAIL] Case {i+1}: Price history for {test_case['ticker']}")
                print(f"  Error: {e}")
        
        return results
    
    def test_get_latest_price(self):
        """Test latest price retrieval."""
        test_cases = [
            {
                "ticker": "VNM",
                "expected_range": (10000.0, 200000.0)  # Reasonable price range in VND
            },
            {
                "ticker": "HPG",
                "expected_range": (5000.0, 100000.0)
            },
        ]
        
        results = []
        for i, test_case in enumerate(test_cases):
            try:
                result = self.service.get_latest_price(test_case["ticker"])
                success = self._is_in_range(result, test_case["expected_range"])
                
                results.append({
                    "ticker": test_case["ticker"],
                    "result": result,
                    "expected_range": test_case["expected_range"],
                    "success": success
                })
                
                status = "PASS" if success else "FAIL"
                print(f"[{status}] Case {i+1}: Latest price for {test_case['ticker']}")
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
                print(f"[FAIL] Case {i+1}: Latest price for {test_case['ticker']}")
                print(f"  Error: {e}")
        
        return results
    
    def _is_in_range(self, value, expected_range):
        """Check if value is within expected range."""
        if value is None:
            return False
        return expected_range[0] <= value <= expected_range[1]


def main():
    """Main test runner for market services."""
    print("=== MARKET SERVICES TESTS ===\n")
    
    # Test Compare Service
    print("1. Testing Compare Service...")
    compare_service = TestCompareService()
    compare_results = {
        "two_stocks": compare_service.test_compare_two_stocks(),
        "multiple_stocks": compare_service.test_compare_multiple_stocks(),
        "with_metrics": compare_service.test_compare_with_metrics()
    }
    
    # Test Indicator Service
    print("\n2. Testing Indicator Service...")
    indicator_service = TestIndicatorService()
    indicator_results = {
        "bollinger_bands": indicator_service.test_calculate_bollinger_bands(),
        "stochastic": indicator_service.test_calculate_stochastic(),
        "adx": indicator_service.test_calculate_adx(),
        "atr": indicator_service.test_calculate_atr()
    }
    
    # Test Price Service
    print("\n3. Testing Price Service...")
    price_service = TestPriceService()
    price_results = {
        "ohlcv": price_service.test_get_ohlcv_data(),
        "history": price_service.test_get_price_history(),
        "latest": price_service.test_get_latest_price()
    }
    
    # Generate comprehensive report
    _generate_comprehensive_report(compare_results, indicator_results, price_results)
    
    return {
        "compare": compare_results,
        "indicator": indicator_results,
        "price": price_results
    }


def _generate_comprehensive_report(compare_results, indicator_results, price_results):
    """Generate comprehensive test report."""
    print("\n" + "="*60)
    print("MARKET SERVICES TEST REPORT")
    print("="*60)
    
    # Compare Service report
    print(f"\n1. COMPARE SERVICE:")
    two_stocks_total = len(compare_results["two_stocks"])
    two_stocks_passed = sum(1 for r in compare_results["two_stocks"] if r["success"])
    print(f"   Two Stocks Comparison: {two_stocks_passed}/{two_stocks_total} passed")
    
    multiple_stocks_total = len(compare_results["multiple_stocks"])
    multiple_stocks_passed = sum(1 for r in compare_results["multiple_stocks"] if r["success"])
    print(f"   Multiple Stocks Comparison: {multiple_stocks_passed}/{multiple_stocks_total} passed")
    
    with_metrics_total = len(compare_results["with_metrics"])
    with_metrics_passed = sum(1 for r in compare_results["with_metrics"] if r["success"])
    print(f"   Comparison with Metrics: {with_metrics_passed}/{with_metrics_total} passed")
    
    # Indicator Service report
    print(f"\n2. INDICATOR SERVICE:")
    bollinger_total = len(indicator_results["bollinger_bands"])
    bollinger_passed = sum(1 for r in indicator_results["bollinger_bands"] if r["success"])
    print(f"   Bollinger Bands: {bollinger_passed}/{bollinger_total} passed")
    
    stochastic_total = len(indicator_results["stochastic"])
    stochastic_passed = sum(1 for r in indicator_results["stochastic"] if r["success"])
    print(f"   Stochastic: {stochastic_passed}/{stochastic_total} passed")
    
    adx_total = len(indicator_results["adx"])
    adx_passed = sum(1 for r in indicator_results["adx"] if r["success"])
    print(f"   ADX: {adx_passed}/{adx_total} passed")
    
    atr_total = len(indicator_results["atr"])
    atr_passed = sum(1 for r in indicator_results["atr"] if r["success"])
    print(f"   ATR: {atr_passed}/{atr_total} passed")
    
    # Price Service report
    print(f"\n3. PRICE SERVICE:")
    ohlcv_total = len(price_results["ohlcv"])
    ohlcv_passed = sum(1 for r in price_results["ohlcv"] if r["success"])
    print(f"   OHLCV Data: {ohlcv_passed}/{ohlcv_total} passed")
    
    history_total = len(price_results["history"])
    history_passed = sum(1 for r in price_results["history"] if r["success"])
    print(f"   Price History: {history_passed}/{history_total} passed")
    
    latest_total = len(price_results["latest"])
    latest_passed = sum(1 for r in price_results["latest"] if r["success"])
    print(f"   Latest Price: {latest_passed}/{latest_total} passed")
    
    # Overall report
    total_tests = (two_stocks_total + multiple_stocks_total + with_metrics_total +
                   bollinger_total + stochastic_total + adx_total + atr_total +
                   ohlcv_total + history_total + latest_total)
    total_passed = (two_stocks_passed + multiple_stocks_passed + with_metrics_passed +
                    bollinger_passed + stochastic_passed + adx_passed + atr_passed +
                    ohlcv_passed + history_passed + latest_passed)
    
    print(f"\n4. OVERALL RESULTS:")
    print(f"   Total Tests: {total_tests}")
    print(f"   Total Passed: {total_passed}")
    print(f"   Total Failed: {total_tests - total_passed}")
    print(f"   Success Rate: {total_passed/total_tests*100:.1f}%")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    main()