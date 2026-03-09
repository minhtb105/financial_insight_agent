import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))

from application.agent.enhanced_agent import enhanced_graph


def test_full_system():
    """Test the full enhanced system with end-to-end queries."""
    
    test_queries = [
        # Original query types
        "Lấy giá đóng cửa của VCB hôm qua.",
        "Tính SMA9 cho VCB trong 1 tuần gần nhất.",
        "Danh sách cổ đông lớn của VCB.",
        "So sánh khối lượng giao dịch của VIC với HPG trong 1 tuần.",
        "Trong các mã VCB, BID, CTG mã nào có giá mở cửa thấp nhất hôm qua?",
        "Tổng khối lượng giao dịch của HPG trong 1 tuần.",
        
        # New query types
        "Tỷ lệ P/E của VNM hiện tại là bao nhiêu?",
        "Có tin tức gì về VCB trong tuần này không?",
        "Nếu tôi mua 100 cổ FPT và 200 cổ VNM thì danh mục hiện tại ra sao?",
        "Cảnh báo khi giá HPG vượt ngưỡng 50.000",
        "Dự báo giá VNM trong tuần tới",
        "Các cổ phiếu ngành chứng khoán có performance tốt nhất tuần này?",
        
        # Complex queries
        "So sánh P/E giữa FPT và VNM, đồng thời cho tôi tin tức tích cực về FPT trong tháng này",
        "Tổng hợp danh mục hiện tại của tôi và đánh giá rủi ro theo ngành",
        "Dự báo xu hướng VN-Index trong tháng 12 và cảnh báo khi có biến động lớn",
    ]
    
    print("=== TESTING FULL ENHANCED SYSTEM ===\n")
    
    for i, query in enumerate(test_queries):
        print(f"Query {i+1}: {query}")
        print("-" * 70)
        
        try:
            # Run the enhanced graph
            init_state = {
                "messages": [{"role": "user", "content": query}],
                "parsed_query": {},
                "tool_output": {},
                "confidence": 0.0,
            }
            
            # Stream the graph execution
            for step in enhanced_graph.stream(init_state, stream_mode="values"):
                if "messages" in step:
                    # Print the final response
                    final_msg = step["messages"][-1]
                    if hasattr(final_msg, 'content'):
                        print(f"Response: {final_msg.content}")
            
        except Exception as e:
            print(f"Error: {e}")
        
        print("\n" + "="*90 + "\n")


if __name__ == "__main__":
    test_full_system()