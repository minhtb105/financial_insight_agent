from application.agents.agent import StockAgent


class TestEnhancedStockAgent:
    def __init__(self):
        self.agent = StockAgent()

    def test_agent_initialization(self):
        assert len(self.agent.tools) > 0
        assert self.agent.llm is not None
        assert self.agent.app is not None

    def test_single_tool_call(self):
        query = "Lấy giá đóng cửa của VCB hôm qua."
        result = self.agent.run(query)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_indicator_tool_call(self):
        query = "Tính SMA9 cho VCB trong 1 tuần gần nhất."
        result = self.agent.run(query)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_company_info_tool_call(self):
        query = "Danh sách cổ đông lớn của VCB."
        result = self.agent.run(query)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_comparison_tool_call(self):
        query = "So sánh khối lượng giao dịch của VIC với HPG trong 1 tuần."
        result = self.agent.run(query)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_ranking_tool_call(self):
        query = "Trong các mã VCB, BID, CTG mã nào có giá mở cửa thấp nhất hôm qua?"
        result = self.agent.run(query)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_aggregate_tool_call(self):
        query = "Tổng khối lượng giao dịch của HPG trong 1 tuần."
        result = self.agent.run(query)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_error_handling_empty_ticker(self):
        result = self.agent.run("")
        assert isinstance(result, str)

    def test_error_handling_invalid_input(self):
        result = self.agent.run("abc123xyz")
        assert isinstance(result, str)

    def test_stream_output(self):
        query = "Lấy giá đóng cửa của VCB hôm qua."
        chunks = list(self.agent.run_stream(query))
        assert len(chunks) > 0
        combined = "".join(chunks)
        assert len(combined) > 0

    def run_all_tests(self):
        print("=== ENHANCED STOCK AGENT TESTS ===\n")

        tests = [
            ("Agent Initialization", self.test_agent_initialization),
            ("Single Tool Call", self.test_single_tool_call),
            ("Indicator Tool Call", self.test_indicator_tool_call),
            ("Company Info Tool Call", self.test_company_info_tool_call),
            ("Comparison Tool Call", self.test_comparison_tool_call),
            ("Ranking Tool Call", self.test_ranking_tool_call),
            ("Aggregate Tool Call", self.test_aggregate_tool_call),
            ("Error Handling Empty", self.test_error_handling_empty_ticker),
            ("Error Handling Invalid", self.test_error_handling_invalid_input),
            ("Stream Output", self.test_stream_output),
        ]

        passed = 0
        failed = 0
        for name, test_fn in tests:
            try:
                test_fn()
                print(f"[PASS] {name}")
                passed += 1
            except Exception as e:
                print(f"[FAIL] {name}: {e}")
                failed += 1

        print(f"\n{'='*60}")
        print(f"Total: {len(tests)}, Passed: {passed}, Failed: {failed}")
        print(f"Success Rate: {passed/len(tests)*100:.1f}%")
        print(f"{'='*60}")

        return passed, failed


def main():
    test_suite = TestEnhancedStockAgent()
    return test_suite.run_all_tests()


if __name__ == "__main__":
    main()