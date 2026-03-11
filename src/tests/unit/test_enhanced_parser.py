from infrastructure.llm.nlp_parser import QueryParser


def test_enhanced_parser():
    """Test the enhanced parser with new query types."""
    parser = QueryParser()
    
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
            print(f"[{status}] Case {i+1}: {test_case['query']}")
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
            print(f"[FAIL] Case {i+1}: {test_case['query']}")
            print(f"  Error: {e}")

    # Thống kê kết quả
    total = len(results)
    passed = sum(1 for r in results if r["success"])
    failed = total - passed
    
    print(f"\n=== THỐNG KÊ ===")
    print(f"Tổng số case: {total}")
    print(f"Đạt: {passed}")
    print(f"Fail: {failed}")
    print(f"Tỷ lệ thành công: {passed/total*100:.1f}%")
    
    # Phân tích theo loại query
    query_types = {}
    for r in results:
        qtype = r["parsed"]["query_type"] if r["parsed"] else "error"
        if qtype not in query_types:
            query_types[qtype] = {"total": 0, "passed": 0}
        query_types[qtype]["total"] += 1
        if r["success"]:
            query_types[qtype]["passed"] += 1
    
    print(f"\n=== PHÂN TÍCH THEO LOẠI QUERY ===")
    for qtype, stats in query_types.items():
        rate = stats["passed"] / stats["total"] * 100 if stats["total"] > 0 else 0
        print(f"{qtype}: {stats['passed']}/{stats['total']} ({rate:.1f}%)")
    
    # In các case fail để phân tích
    print(f"\n=== CÁC CASE FAIL ===")
    for r in results:
        if not r["success"]:
            print(f"- {r['query']}")
            if r.get("error"):
                print(f"  Error: {r['error']}")
            else:
                print(f"  Expected: {r['expected_type']}/{r['expected_field']}")
                print(f"  Got: {r['parsed']['query_type'] if r['parsed'] else 'None'}/{r['parsed']['requested_field'] if r['parsed'] else 'None'}")

    return results


if __name__ == "__main__":
    test_enhanced_parser()