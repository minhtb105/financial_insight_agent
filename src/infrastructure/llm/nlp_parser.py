from langchain_groq import ChatGroq
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from domain.entities.historical_query import HistoricalQuery
from datetime import datetime
import re


class QueryParser:
    """
    Parser that uses an LLM to analyze Vietnamese stock-related natural language
    queries and convert them into JSON following the HistoricalQuery schema.
    """

    def __init__(self, model: str = "llama-3.1-8b-instant"):
        from dotenv import load_dotenv
        import os
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Thiếu GROQ_API_KEY trong .env")

        self.parser = PydanticOutputParser(pydantic_object=HistoricalQuery)

        self.prompt = PromptTemplate(
            template=(
                """Bạn là một parser. Nhiệm vụ của bạn là phân tích câu hỏi và chỉ trả về JSON hợp lệ theo đúng schema(KHÔNG giải thích thêm).

                ! QUY TẮC BẮT BUỘC(ưu tiên cao nhất):
                - JSON phản hồi phải đúng EXACT schema: {format_instructions}
                - Không có bất kỳ nội dung nào ngoài JSON.
                - Bắt buộc sử dụng đúng biến {today} khi tính toán thời gian.
                - KHÔNG được viết bất kỳ giải thích nào.
                - Trường không có giá trị → đặt JSON null(không phải chuỗi "null").
                - Nếu không chắc chắn → vẫn phải chọn giá trị hợp lệ theo schema.

                === INPUT == =
                Câu hỏi: {query}
                Hôm nay: {today}

                === PHÂN BIỆT QUERY TYPE — LUẬT CHÍNH XÁC VÀ KIỂM TRA (Thứ tự ưu tiên) ===

                LUẬT CHUNG TRƯỚC KHI PHÂN LOẠI:
                - Trích tất cả ticker xuất hiện trong câu theo thứ tự chúng xuất hiện.
                - Chuẩn hoá ticker thành CHỮ IN HOA.
                - Đếm số ticker (n_tickers).
                - Tất cả các quyết định bên dưới phải dựa trên nội dung câu, số lượng ticker, và từ khoá rõ ràng.

                (1) comparison_query  — (ƯU TIÊN HƠN ranking_query nếu câu có từ "so sánh"/"compare")
                - Kích hoạt nếu câu chứa từ/cụm: "so sánh", "compare", "so sánh X với Y", "compare X with Y" hoặc "so sánh X và Y".
                - YÊU CẦU: ít nhất 2 mã được đề cập (n_tickers >= 2).
                - Khi comparison_query:
                - query_type = "comparison_query"
                - tickers = [mã đứng trước từ "với"/"with"/"và" nếu có thể], nếu không rõ thì tickers = [đầu tiên trong câu]
                - compare_with = danh sách các mã còn lại (ít nhất 1 phần tử)
                - aggregate = null (không set aggregate cho comparison)
                - **KHÔNG** chuyển thành ranking_query chỉ vì có 2 mã — nếu có từ "so sánh" thì phải là comparison_query.

                (2) ranking_query  — chỉ khi THỎA ĐIỀU KIỆN RÕ RÀNG
                - Kích hoạt **chỉ khi**:
                a) Câu chứa cụm rõ ràng: "mã nào cao nhất", "mã nào thấp nhất", "which of", "which has the highest/lowest", "trong các mã A, B, C mã nào..." **AND**
                b) Có danh sách các mã được nêu rõ **và** n_tickers >= 2.
                - Khi ranking_query:
                - query_type = "ranking_query"
                - tickers = list các mã (>=2)
                - aggregate = "max" nếu hỏi "cao nhất"/"highest"; aggregate = "min" nếu hỏi "thấp nhất"/"lowest"
                - compare_with = null

                (3) indicator_query
                - Nếu câu yêu cầu chỉ báo kỹ thuật: SMA, MA, RSI, MACD...
                - Khi indicator_query:
                - query_type = "indicator_query"
                - requested_field = tương ứng ("sma","rsi","macd")
                indicator_params phải là một DICT mà:
                - Mỗi key là tên chỉ báo viết thường: "sma", "ema", "rsi", "macd", "bb", ...
                - Mỗi value là một LIST các tham số số nguyên theo đúng thứ tự xuất hiện trong câu.
                - Nếu một chỉ báo xuất hiện nhiều lần → gom tất cả vào cùng 1 key.

                Ví dụ:
                - "SMA9" → {{"sma": [9]}}
                - "SMA9 và SMA20" → {{"sma": [9, 20]}}
                - "RSI14" → {{"rsi": [14]}}

                Nhiều chỉ báo cùng lúc:
                - "SMA9, SMA20 và RSI14"
                → {{"sma": [9, 20], "rsi": [14]}}

                - "SMA9, EMA12, EMA26, RSI14"
                → {{"sma": [9], "ema": [12, 26], "rsi": [14]}}

                - "MACD(12,26), RSI14 và SMA20"
                → {{"macd": [12, 26], "rsi": [14], "sma": [20]}}

                - aggregate = null

                (4) aggregate_query
                - Nếu câu có từ khoá thống kê/ tổng hợp như: "tổng", "sum", "cộng dồn", "trung bình", "average", "avg", "bình quân", "nhỏ nhất", "thấp nhất", "cao nhất", "lớn nhất", "min", "max", "median" **VÀ** không bị bắt thành comparison/ranking theo luật trên → chọn aggregate_query.
                - Bắt buộc gán aggregate theo mapping chính xác (KHÔNG để null):
                    - "tổng", "sum", "cộng dồn" → aggregate = "sum"
                    - "trung bình", "average", "avg", "bình quân" → aggregate = "mean"
                    - "nhỏ nhất", "thấp nhất", "min" → aggregate = "min"
                    - "lớn nhất", "cao nhất", "max" → aggregate = "max"
                    - "median", "trung vị" → aggregate = "median"
                    - "đầu", "đầu tiên", "first" → aggregate = "first"
                    - "cuối", "cuối cùng", "last" → aggregate = "last"
                - Nếu user viết aggregate theo ngôn ngữ tự nhiên (VD: "trung bình"), **bắt buộc** chuyển sang giá trị trong danh sách trên.
                - requested_field đi kèm lấy theo ngữ cảnh (ví dụ "tổng khối lượng" → requested_field="volume").

                (5) price_query (FALLBACK)
                - Dùng khi hỏi giá/ohlcv/volume cho 1 mã hoặc 1 khoảng thời gian **và** KHÔNG thỏa điều kiện comparison/ranking/aggregate/indicator/company.
                - Ví dụ đúng: "Giá đóng cửa của FPT tuần trước là bao nhiêu?" → price_query (vì chỉ 1 mã, KHÔNG có từ khoá aggregate hoặc so sánh).
                - Nếu chỉ 1 ticker present → ưu tiên price_query trừ khi câu chứa từ khoá aggregate/ranking/comparison rõ ràng.

                (6) company_query
                - Nếu hỏi thông tin doanh nghiệp (cổ đông, ban lãnh đạo, công ty con...) → company_query.

                --- KIỂM TRA BẮT BUỘC TRƯỚC KHI TRẢ:
                1. Nếu query_type == "comparison_query": compare_with phải là LIST với >=1 phần tử. Nếu parser không tìm compare_with, KHÔNG trả comparison_query — fallback sang price_query.
                2. Nếu query_type == "ranking_query": đảm bảo n_tickers >= 2; nếu không → chuyển thành price_query (nếu 1 mã) hoặc comparison_query (nếu có 'so sánh').
                3. Nếu query_type == "aggregate_query": aggregate phải là 1 trong ["sum","mean","min","max","median","first","last"]. Nếu không xác định được → fallback = null nhưng XUẤT RA CẢNH BÁO nội bộ (không in ra), tuyệt đối không để aggregate=None khi câu rõ ràng có từ khóa aggregate.
                4. Nếu không chắc chắn giữa ranking vs comparison → dùng "so sánh" detection first (comparison override) và kiểm tra số lượng mã. Nếu vẫn ambiguous → chọn price_query cho 1 mã, comparison_query cho câu rõ "so sánh".
                5. Tất cả các trường không applicable → phải là JSON null (không phải string "null").

                --- KẾT LUẬN:
                - Sau khi áp dụng luật này parser sẽ:
                - Với "So sánh khối lượng giao dịch của FPT với MWG trong 7 ngày qua" → query_type="comparison_query", tickers=["FPT"], compare_with=["MWG"], days=7, start/end tính theo quy tắc thời gian, aggregate=null.
                - Với "Tổng khối lượng giao dịch của FPT từ tháng 1 đến tháng 3" → query_type="aggregate_query", aggregate="sum", start/end tính theo quy tắc thời gian.


                == == == == == == == == == == == == == == == == == == == == == == == == == ==
                2) requested_field(bắt buộc chọn 1)

                == == == == == == == == == == == == == == == == == == == == == == == == == ==
                - 'giá mở', 'open', 'mở cửa' → 'open'
                - 'giá đóng', 'giá chốt', 'close' → 'close'
                - 'volume', 'khối lượng' → 'volume'
                - 'ohlcv' → 'ohlcv'
                - 'SMA', 'MA' → 'sma'
                - 'RSI' → 'rsi'
                - 'MACD' → 'macd'
                - 'cổ đông lớn' → 'shareholders'
                - 'ban lãnh đạo', 'CEO', 'BOD', 'board' → 'executives'
                - 'công ty con', 'subsidiary' → 'subsidiaries'

                Nếu chỉ hỏi 'giá' → bắt buộc chọn 'close'.

                == == == == == == == == == == == == == == == == == == == == == == == == == ==
                3) Quy tắc thời gian
                == == == == == == == == == == == == == == == == == == == == == == == == == ==
                - "X ngày gần nhất / trong X ngày / X ngày vừa rồi" → days = X, start = {today} - X ngày, end = {today}
                - "X tuần", "trong X tuần" → weeks = X, start = {today} - X tuần, end = {today}
                - "X tháng", "trong X tháng" → months = X, start = {today} - X tháng, end = {today}
                - Nếu user nêu rõ start và end → giữ nguyên start/end (định dạng "YYYY-MM-DD").
                - Nếu end không nêu rõ → end = {today}
                - Nếu không có thông tin thời gian → start = null, end = null, days/weeks/months = null
                - **Luôn** trả start/end ở định dạng "YYYY-MM-DD" khi có giá trị.

                == == == == == == == == == == == == == == == == == == == == == == == == == ==
                === OUTPUT == =
                Trả về JSON theo schema sau:
                {format_instructions}"""
            ),
            input_variables=["query"],
            partial_variables={
                "format_instructions": self.parser.get_format_instructions()},
        )
        self.chat = ChatGroq(model=model, temperature=0,
                             api_key=api_key, max_retries=3)
        self.structured_output_llm = self.chat.with_structured_output(
            HistoricalQuery,
            method='json_mode')

    def parse(self, query: str) -> HistoricalQuery:
        now = datetime.now()
        system_msg = SystemMessage(self.prompt.format_prompt(
            query=query,
            today=now.strftime("%Y-%m-%d")
        ).to_string())

        human_msg = HumanMessage(query)

        response = self.structured_output_llm.invoke(
            [system_msg] + [human_msg])

        return response.model_dump()

    @staticmethod
    def _extract_json(text: str) -> str:
        match = re.search(r"\{.*\}", text, re.DOTALL)

        return match.group(0) if match else text
