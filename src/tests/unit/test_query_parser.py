from langsmith import Client
from infrastructure.llm.nlp_parser import QueryParser


client = Client()
parser = QueryParser()

test_cases = [

    # 1) PRICE QUERY - 20 questions
    "Lấy giá mở cửa của VCB hôm qua.",
    "Lấy giá đóng cửa của HPG hôm nay.",
    "Cho tôi giá cao nhất của VIC trong ngày.",
    "Lấy giá thấp nhất của TCB phiên trước.",
    "Lấy dữ liệu OHLCV của HPG 10 ngày gần nhất.",
    "Lấy OHLCV của VHM trong vòng 2 tuần qua.",
    "Lấy khối lượng giao dịch của MSN hôm nay.",
    "Lấy lịch sử giá mở cửa của SSI trong 30 ngày gần nhất.",
    "Lấy giá đóng của MWG tuần trước.",
    "Lấy dữ liệu OHLCV của STB từ đầu năm đến nay.",
    "Tra cứu giá mở cửa của GAS ngày 1/11/2024.",
    "Lấy giá đóng của FPT từ 1/10 đến 15/10.",
    "Lấy volume của VPB hôm nay.",
    "Lấy dữ liệu OHLCV của PLX trong 1 tháng gần đây.",
    "Tra cứu giá thấp nhất của BVH vào ngày 2/11.",
    "Giá mở cửa của VCB phiên gần nhất.",
    "Giá đóng của VIC trong 5 ngày vừa rồi.",
    "Khối lượng giao dịch của HPG trong 3 ngày qua.",
    "OHLCV của TCB 15 ngày gần nhất.",
    "Lịch sử giá đóng của MBB trong 2 tuần vừa qua.",

    # 2) INDICATOR QUERY – 20 questions
    "Tính SMA9 cho VCB trong 10 ngày gần nhất.",
    "Tính SMA20 cho HPG trong 2 tuần gần đây.",
    "Tính SMA50 của VIC từ đầu tháng 10.",
    "Tính SMA9 và SMA20 cho VHM trong 1 tháng với timeframe 1d.",
    "Tính SMA14 và SMA21 của SSI trong 3 tuần.",
    "Tính RSI14 của VCB trong 2 tuần.",
    "Tính RSI14 và RSI28 cho HPG từ đầu năm.",
    "Cho tôi RSI7 của GAS tuần này.",
    "Tính RSI14 của VNM ngày hôm qua.",
    "Tính MACD của FPT từ tháng 9 đến tháng 10.",
    "MACD của MWG trong 2 tháng gần đây.",
    "Cho tôi SMA9 của TCB trong 1 tuần theo timeframe 1m.",
    "SMA9 và SMA20 của STB từ đầu tháng đến nay.",
    "Tính RSI14 và SMA9 cho VCI trong 10 ngày.",
    "Tính SMA200 cho VIC trong 6 tháng.",
    "Tính MACD của PNJ trong 1 tháng.",
    "Cho tôi RSI7 và RSI14 cho HPG trong 15 ngày.",
    "Tính SMA9 và SMA18 của VCG trong 20 ngày.",
    "Tính SMA9 của MSB từ đầu quý 4.",
    "Tính RSI14 của REE trong 10 ngày vừa qua.",

    # 3) COMPANY QUERY – 15 questions
    "Danh sách cổ đông lớn của VCB.",
    "Danh sách lãnh đạo đang làm việc tại HPG.",
    "Các công ty con của VHM.",
    "Cho tôi danh sách công ty con của FPT.",
    "Lấy danh sách cổ đông chủ chốt của VIC.",
    "Ai là CEO của MWG?",
    "Lấy toàn bộ danh sách lãnh đạo của GAS.",
    "Tra cứu cổ đông của SSI.",
    "Liệt kê công ty con thuộc BIDV.",
    "Cho tôi danh sách cổ đông tổ chức của TCB.",
    "Danh sách cổ đông chiến lược của VNM.",
    "Cho tôi danh sách ban điều hành REE.",
    "Những công ty con của PLX.",
    "Lấy danh sách cổ đông SCP của MSB.",
    "Lãnh đạo cấp cao của VPB.",

    # 4) COMPARISON QUERY – 15 questions
    "So sánh khối lượng giao dịch của VIC với HPG trong 1 tuần.",
    "So sánh giá đóng của VCB với BID hôm nay.",
    "So sánh giá mở cửa của TCB với MBB 5 ngày gần đây.",
    "So sánh volume của FPT với MWG trong 10 ngày.",
    "So sánh giá đóng của SSI với VCI từ đầu tháng.",
    "So sánh OHLCV của HPG với VHM hôm nay.",
    "So sánh giá cao nhất của BID và CTG trong 3 ngày qua.",
    "So sánh volume của VPB với MBB 2 tuần gần nhất.",
    "So sánh giá mở cửa GAS với PLX trong 15 ngày.",
    "So sánh RSI14 của VIC với VCB.",
    "So sánh SMA9 của MBB với STB.",
    "So sánh SMA20 của VHM và VRE.",
    "So sánh MACD của FPT và MWG.",
    "So sánh volume của HPG với SSI trong tháng này.",
    "So sánh giá đóng PNJ với FRT 7 ngày gần đây.",

    # 5) RANKING QUERY – 15 questions
    "Trong các mã VCB, BID, CTG mã nào có giá mở cửa thấp nhất hôm qua?",
    "Mã nào cao nhất trong nhóm VHM, VIC, VRE trong 10 ngày qua?",
    "Trong nhóm HPG, NKG, HSG mã nào có volume thấp nhất tuần này?",
    "Mã nào giá đóng cao nhất trong nhóm FPT, MWG, PNJ tháng trước?",
    "Trong nhóm SSI, VCI, HCM mã nào có giá mở thấp nhất hôm nay?",
    "Mã nào giao dịch lớn nhất trong nhóm GAS, PLX 5 ngày gần đây?",
    "Trong nhóm VPB, MBB, TCB mã nào có volume cao nhất?",
    "Mã nào thấp nhất trong nhóm VCB, BID từ đầu tháng 11 đến nay?",
    "Trong nhóm VNM, QNS, MCH mã nào giá cao nhất?",
    "Nhóm HAG, HNG, TTF mã nào có giá mở thấp nhất tuần trước?",
    "Trong nhóm DXG, KDH, NLG mã nào volume cao nhất tháng này?",
    "Mã nào giá đóng thấp nhất trong nhóm VIC, VHM, VRE?",
    "Lấy mã cao nhất trong các mã BVH, BMI, PVI tuần qua.",
    "Trong nhóm STB, EIB, SHB mã nào thấp nhất 3 ngày gần đây?",
    "Nhóm POW, NT2, PC1 mã nào volume thấp nhất trong 10 ngày?",

    # 6) AGGREGATE QUERY – 15 questions
    "Tổng khối lượng giao dịch của HPG trong 1 tuần.",
    "Tổng volume của VCB trong 10 ngày vừa qua.",
    "Tổng volume của VIC trong 1 tháng gần đây.",
    "Cho tôi giá đóng nhỏ nhất của SSI từ đầu tháng.",
    "Giá đóng trung bình của VCB trong 10 ngày.",
    "Giá mở nhỏ nhất của HPG trong 2 tuần.",
    "Tổng khối lượng của FPT từ 1/10 đến 15/10.",
    "Trung bình volume của VHM 5 ngày gần nhất.",
    "Tổng volume MBB từ đầu quý 4.",
    "Giá đóng lớn nhất của MWG trong tháng này.",
    "Tổng volume của GAS trong 7 ngày vừa qua.",
    "Tổng volume của PLX trong 2 tuần gần đây.",
    "Trung bình khối lượng của TCB 3 ngày gần nhất.",
    "Tổng volume của VCB và BID.",
    "Tổng khối lượng giao dịch của nhóm HPG, HSG, NKG trong 10 ngày."
]

client.run_evaluators(
    data=test_cases,
    run_handler=lambda query: parser.parse(query),
    evaluators=[
        "json_valid",
        "has_field:tickers",
        "enum_valid:query_type",
    ],
    project_name="financial-nlp-parser",
)
