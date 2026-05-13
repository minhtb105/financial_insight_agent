#!/usr/bin/env python3
"""
Test script for Guardrails system integration.

Tests the comprehensive guardrails implementation including input validation,
step-wise validation, and output protection.
"""

import asyncio
import aiohttp
import json
from typing import Dict, Any
import time


class GuardrailsTester:
    """Test suite for guardrails system."""
    
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
    
    async def test_input_guardrails(self) -> Dict[str, Any]:
        """Test input validation guardrails."""
        print("=== Testing Input Guardrails ===")
        results = {}
        
        test_cases = [
            # Test 1: Valid query
            {
                "name": "Valid Query",
                "query": "VNM có bao nhiêu cổ phiếu đang lưu hành?",
                "expected_status": "success"
            },
            # Test 2: Too short query
            {
                "name": "Too Short Query",
                "query": "HPG",
                "expected_status": "fail"
            },
            # Test 3: Too long query
            {
                "name": "Too Long Query",
                "query": "A" * 600,
                "expected_status": "fail"
            },
            # Test 4: SQL injection attempt
            {
                "name": "SQL Injection",
                "query": "SELECT * FROM users; DROP TABLE users;",
                "expected_status": "fail"
            },
            # Test 5: XSS injection attempt
            {
                "name": "XSS Injection",
                "query": "<script>alert('test')</script>",
                "expected_status": "fail"
            },
            # Test 6: API key detection
            {
                "name": "API Key Detection",
                "query": "My API key is sk-1234567890abcdef",
                "expected_status": "fail"
            },
            # Test 7: Email detection (PII)
            {
                "name": "Email Detection",
                "query": "Contact me at test@example.com",
                "expected_status": "fail"
            }
        ]
        
        for test_case in test_cases:
            print(f"\nTesting: {test_case['name']}")
            try:
                result = await self._test_single_query(test_case["query"])
                results[test_case["name"]] = {
                    "status": "success" if result["success"] else "fail",
                    "response": result.get("response", ""),
                    "expected": test_case["expected_status"]
                }
                print(f"  Result: {results[test_case['name']]['status']} (expected: {test_case['expected_status']})")
            except Exception as e:
                results[test_case["name"]] = {
                    "status": "error",
                    "error": str(e),
                    "expected": test_case["expected_status"]
                }
                print(f"  Error: {e}")
        
        return results
    
    async def test_step_wise_guardrails(self) -> Dict[str, Any]:
        """Test step-wise validation guardrails."""
        print("\n=== Testing Step-wise Guardrails ===")
        results = {}
        
        test_cases = [
            # Test 1: Valid tickers
            {
                "name": "Valid Tickers",
                "query": "VNM có bao nhiêu cổ phiếu đang lưu hành?",
                "expected_status": "success"
            },
            # Test 2: Invalid tickers
            {
                "name": "Invalid Tickers",
                "query": "XYZ có bao nhiêu cổ phiếu đang lưu hành?",
                "expected_status": "fail"
            },
            # Test 3: Too many tickers
            {
                "name": "Too Many Tickers",
                "query": "So sánh giá cổ phiếu của VNM, VIC, VCB, MSN, FPT, GAS, HPG, PLX, MWG, CTG, BID, ACB, SHB, STB, TPB, EIB, HDB, TCB, VIB, LPB",
                "expected_status": "fail"
            },
            # Test 4: Invalid date range
            {
                "name": "Invalid Date Range",
                "query": "VNM có bao nhiêu cổ phiếu đang lưu hành từ 2010-01-01 đến 2030-01-01?",
                "expected_status": "fail"
            }
        ]
        
        for test_case in test_cases:
            print(f"\nTesting: {test_case['name']}")
            try:
                result = await self._test_single_query(test_case["query"])
                results[test_case["name"]] = {
                    "status": "success" if result["success"] else "fail",
                    "response": result.get("response", ""),
                    "expected": test_case["expected_status"]
                }
                print(f"  Result: {results[test_case['name']]['status']} (expected: {test_case['expected_status']})")
            except Exception as e:
                results[test_case["name"]] = {
                    "status": "error",
                    "error": str(e),
                    "expected": test_case["expected_status"]
                }
                print(f"  Error: {e}")
        
        return results
    
    async def test_output_guardrails(self) -> Dict[str, Any]:
        """Test output validation and sanitization."""
        print("\n=== Testing Output Guardrails ===")
        results = {}
        
        # Test cases that might trigger output issues
        test_cases = [
            {
                "name": "Normal Response",
                "query": "VNM có bao nhiêu cổ phiếu đang lưu hành?",
                "expected_status": "success"
            },
            {
                "name": "Response with PII",
                "query": "VNM có bao nhiêu cổ phiếu đang lưu hành? Email của tôi là test@example.com",
                "expected_status": "success"
            }
        ]
        
        for test_case in test_cases:
            print(f"\nTesting: {test_case['name']}")
            try:
                result = await self._test_single_query(test_case["query"])
                results[test_case["name"]] = {
                    "status": "success" if result["success"] else "fail",
                    "response": result.get("response", ""),
                    "expected": test_case["expected_status"]
                }
                print(f"  Result: {results[test_case['name']]['status']} (expected: {test_case['expected_status']})")
                
                # Check for PII redaction
                if "test@example.com" in test_case["query"] and result["success"]:
                    response = result.get("response", "")
                    if "[REDACTED_EMAIL]" in response:
                        print("  ✓ PII successfully redacted")
                    else:
                        print("  ✗ PII not redacted")
                
            except Exception as e:
                results[test_case["name"]] = {
                    "status": "error",
                    "error": str(e),
                    "expected": test_case["expected_status"]
                }
                print(f"  Error: {e}")
        
        return results
    
    async def test_rate_limiting(self) -> Dict[str, Any]:
        """Test rate limiting functionality."""
        print("\n=== Testing Rate Limiting ===")
        results = {}
        
        # Test rapid requests from same session
        session_id = "test_session_001"
        rapid_requests = 15  # Exceeds limit of 10 per minute
        
        print(f"Sending {rapid_requests} rapid requests from session {session_id}")
        start_time = time.time()
        
        success_count = 0
        fail_count = 0
        
        for i in range(rapid_requests):
            try:
                result = await self._test_single_query(
                    "VNM có bao nhiêu cổ phiếu đang lưu hành?",
                    session_id=session_id
                )
                if result["success"]:
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                fail_count += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        results["rate_limiting"] = {
            "total_requests": rapid_requests,
            "successful": success_count,
            "failed": fail_count,
            "duration": duration,
            "rate_limit_working": fail_count > 0
        }
        
        print(f"  Total requests: {rapid_requests}")
        print(f"  Successful: {success_count}")
        print(f"  Failed: {fail_count}")
        print(f"  Duration: {duration:.2f}s")
        print(f"  Rate limiting working: {results['rate_limiting']['rate_limit_working']}")
        
        return results
    
    async def _test_single_query(self, query: str, session_id: str = None) -> Dict[str, Any]:
        """Test a single query and return result."""
        url = f"{self.base_url}/ask"
        headers = {"Content-Type": "application/json"}
        data = {"query": query}
        
        if session_id:
            headers["X-Session-ID"] = session_id
        
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status == 200:
                    response_data = await response.json()
                    return {
                        "success": True,
                        "response": response_data.get("answer", ""),
                        "status_code": response.status
                    }
                else:
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": error_text,
                        "status_code": response.status
                    }
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all guardrails tests."""
        print("Guardrails System Test Suite")
        print("=" * 50)
        
        all_results = {}
        
        # Test input guardrails
        input_results = await self.test_input_guardrails()
        all_results["input_guardrails"] = input_results
        
        # Test step-wise guardrails
        step_results = await self.test_step_wise_guardrails()
        all_results["step_wise_guardrails"] = step_results
        
        # Test output guardrails
        output_results = await self.test_output_guardrails()
        all_results["output_guardrails"] = output_results
        
        # Test rate limiting
        rate_results = await self.test_rate_limiting()
        all_results["rate_limiting"] = rate_results
        
        # Summary
        print("\n" + "=" * 50)
        print("GUARDRAILS TEST SUMMARY")
        print("=" * 50)
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for category, results in all_results.items():
            if category == "rate_limiting":
                continue
                
            print(f"\n{category.upper()}:")
            for test_name, result in results.items():
                total_tests += 1
                if result["status"] == result["expected"]:
                    passed_tests += 1
                    status_icon = "✓"
                else:
                    failed_tests += 1
                    status_icon = "✗"
                
                print(f"  {status_icon} {test_name}: {result['status']} (expected: {result['expected']})")
        
        print(f"\nOverall Results:")
        print(f"  Total tests: {total_tests}")
        print(f"  Passed: {passed_tests}")
        print(f"  Failed: {failed_tests}")
        print(f"  Success rate: {(passed_tests/total_tests)*100:.1f}%" if total_tests > 0 else "  Success rate: N/A")
        
        return all_results


async def main():
    """Run the guardrails test suite."""
    tester = GuardrailsTester()
    results = await tester.run_all_tests()
    
    # Save results to file
    with open("guardrails_test_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    print(f"\nTest results saved to guardrails_test_results.json")


if __name__ == "__main__":
    asyncio.run(main())