from infrastructure.llm.nlp_parser import QueryParser


def test_query_parser():
    parser = QueryParser()
    test_cases = [
        # 1) PRICE QUERY - 5 questions
        "Lấy giá mở cửa của VCB hôm qua.",
        "Lấy giá đóng cửa của HPG hôm nay.",
        "Cho tôi giá chốt của VIC trong ngày.",
        "Lấy dữ liệu OHLCV của HPG 10 ngày gần nhất.",
        "Lấy OHLCV của VHM trong vòng 2 tuần qua.",

        # 2) INDICATOR QUERY – 5 questions
        "Tính SMA9 cho VCB trong 1 tuần gần nhất.",
        "Cho tôi SMA20 của HPG trong 2 tuần gần đây.",
        "SMA50 của VIC từ đầu tháng 10 đến nay.",
        "Tính SMA9 và SMA20 cho VHM trong 1 tháng qua.",
        "Cho tôi SMA14 và SMA21 của SSI trong 3 tuần gần đây.",

        # 3) COMPANY QUERY – 5 questions
        "Danh sách cổ đông lớn của VCB.",
        "Danh sách lãnh đạo đang làm việc tại HPG.",
        "Các công ty con của VHM.",
        "Cho tôi danh sách công ty con của FPT.",
        "Lấy danh sách cổ đông chủ chốt của VIC.",

        # 4) COMPARISON QUERY – 5 questions
        "So sánh khối lượng giao dịch của VIC với HPG trong 1 tuần.",
        "So sánh giá đóng của VCB với BID hôm nay.",
        "So sánh giá mở cửa của TCB với MBB 5 ngày gần đây.",
        "So sánh volume của FPT với MWG trong 10 ngày.",
        "So sánh giá đóng của SSI với VCI từ đầu tháng.",

        # 5) RANKING QUERY – 5 questions
        "Trong các mã VCB, BID, CTG mã nào có giá mở cửa thấp nhất hôm qua?",
        "Mã nào cao nhất trong nhóm VHM, VIC, VRE trong 10 ngày qua?",
        "Trong nhóm HPG, NKG, HSG mã nào có volume thấp nhất tuần này?",
        "Mã nào giá đóng cao nhất trong nhóm FPT, MWG, PNJ tháng trước?",
        "Trong nhóm SSI, VCI, HCM mã nào có giá mở thấp nhất hôm nay?",

        # 6) AGGREGATE QUERY – 5 questions
        "Tổng khối lượng giao dịch của HPG trong 1 tuần.",
        "Tổng volume của VCB trong 10 ngày vừa qua.",
        "Tổng volume của VIC trong 1 tháng gần đây.",
        "Cho tôi giá đóng nhỏ nhất của SSI từ đầu tháng.",
        "Giá đóng trung bình của VCB trong 10 ngày.",
    ]

    results = []
    for i, query in enumerate(test_cases):
        try:
            parsed = parser.parse(query)
            results.append({
                "query": query,
                "parsed": parsed,
                "success": True,
                "error": None
            })
            print(f"[PASS] Case {i+1}: {query}")
            print(f"  Parsed: {parsed}")
        except Exception as e:
            results.append({
                "query": query,
                "parsed": None,
                "success": False,
                "error": str(e)
            })
            print(f"[FAIL] Case {i+1}: {query}")
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

    # In các case fail để phân tích
    print(f"\n=== CÁC CASE FAIL ===")
    for r in results:
        if not r["success"]:
            print(f"- {r['query']}: {r['error']}")

    return results


if __name__ == "__main__":
    test_query_parser()