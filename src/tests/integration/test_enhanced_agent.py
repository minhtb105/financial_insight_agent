from application.agents.agent import StockAgent


def test_enhanced_agent():
    """Test the agent with various query types."""
    agent = StockAgent()

    test_queries = [
        "Lấy giá đóng cửa của VCB hôm qua.",
        "Tính SMA9 cho VCB trong 1 tuần gần nhất.",
        "Danh sách cổ đông lớn của VCB.",
        "So sánh khối lượng giao dịch của VIC với HPG trong 1 tuần.",
        "Trong các mã VCB, BID, CTG mã nào có giá mở cửa thấp nhất hôm qua?",
        "Tổng khối lượng giao dịch của HPG trong 1 tuần.",
        "Tỷ lệ P/E của VNM hiện tại là bao nhiêu?",
        "Có tin tức gì về VCB trong tuần này không?",
        "Nếu tôi mua 100 cổ FPT và 200 cổ VNM thì danh mục hiện tại ra sao?",
        "Cảnh báo khi giá HPG vượt ngưỡng 50.000",
        "Dự báo giá VNM trong tuần tới",
        "Các cổ phiếu ngành chứng khoán có performance tốt nhất tuần này?",
    ]

    print("=== TESTING ENHANCED AGENT ===\n")

    for i, query in enumerate(test_queries):
        print(f"Query {i+1}: {query}")
        print("-" * 50)

        try:
            result = agent.run(query)
            print(f"Result: {result[:200]}..." if len(result) > 200 else f"Result: {result}")
        except Exception as e:
            print(f"Error: {e}")

        print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    test_enhanced_agent()