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
                """Bạn là một parser. Nhiệm vụ của bạn là phân tích câu hỏi và chỉ trả về JSON hợp lệ theo đúng schema (KHÔNG giải thích thêm). 
                
                ! QUY TẮC BẮT BUỘC (ưu tiên cao nhất):
                - JSON phản hồi phải đúng EXACT schema: {format_instructions}
                - Không có bất kỳ nội dung nào ngoài JSON.
                - TẤT CẢ các ticker phải chuyển thành CHỮ IN HOA (VIC, VCB…), kể cả nếu người dùng nhập chữ thường.
                - Bắt buộc sử dụng đúng biến {today} khi tính toán thời gian.
                - KHÔNG được viết bất kỳ giải thích nào.
                - Tất cả các trường không có giá trị phải đặt là null (JSON null), tuyệt đối không đặt là "null".
                - Nếu không chắc chắn → vẫn phải chọn giá trị hợp lệ theo schema, KHÔNG được tự giả định sang loại khác.

                === INPUT ===
                Câu hỏi: {query}
                Hôm nay: {today}
                
                1) query_type (bắt buộc phải chọn 1 - ƯU TIÊN THEO THỨ TỰ):
                - aggregate_query → nếu câu hỏi có bất kỳ từ khóa nào sau:
                    "tổng", "sum" -> aggregate = "sum"
                    "nhỏ nhất", "thấp nhất", "min" -> aggregate = "min"
                    "cao nhất", "lớn nhất", "max" -> aggregate = "max"
                    "trung bình", "average", "avg" → aggregate = "avg"
                (LUÔN CHỌN aggregate_query — kể cả khi câu có chữ "giá", "open", "close", "volume")
                - price_query → dùng khi hỏi giá/khối lượng/ohlcv mà KHÔNG yêu cầu tổng hợp/min/max.
                - indicator_query → SMA, RSI, MACD
                - company_query → shareholders, executives, subsidiaries
                - comparison_query → có chữ 'so sánh'
                - ranking_query → 'mã nào thấp nhất/cao nhất'

                2) requested_field (bắt buộc chọn 1):
                nếu câu hỏi có bất kỳ từ khóa nào sau:
                - 'giá mở', 'open', 'mở cửa' -> requested_field = 'open'
                - 'giá đóng', 'giá chốt', 'close' -> requested_field = 'close'
                - 'volume', 'khối lượng', 'GT khớp lệnh' -> requested_field = 'volume'
                - 'ohlcv', 'toàn bộ ohlcv', 'giá mở - cao - thấp - đóng' -> requested_field = 'ohlcv'
                - 'SMA', 'MA' → requested_field = 'sma' 
                - 'RSI' → requested_field = 'rsi'
                - 'MACD' → requested_field = 'macd'
                - 'cổ đông lớn' → requested_field = 'shareholders'  
                - 'ban lãnh đạo', 'CEO', 'BOD', 'board' → requested_field = 'executives'  
                - 'công ty con', 'subsidiary' → requested_field = 'subsidiaries'  

                **Nếu user chỉ hỏi 'giá' mà không rõ mở hay đóng:**  
                → BẮT BUỘC chọn 'close'.
                
                3) Quy tắc tách tickers khi so sánh (BẮT BUỘC tuân thủ):
                - Câu có dạng 'so sánh X với Y, Z' → tickers = [X], compare_with = [Y, Z]
                - Câu có dạng 'so sánh X với Y' → tickers = [X], compare_with = [Y]
                - Không được đưa mã X vào compare_with.
                - Không được đưa mã Y/Z vào tickers.
                
                4) ranking query:
                - 'Trong các mã A,B,C mã nào thấp nhất/cao nhất'
                → query_type = 'ranking_query'
                → aggregate = min/max
                → tickers = toàn bộ danh sách

                5) Technical indicators:
                - SMA9 → {{'sma':[9]}}
                - SMA9 và SMA20 → {{'sma':[9, 20]}}
                - RSI14 -> {{'rsi': [14]}}
                - SMA9, SMA20 và RSI14 -> {{'sma':[9, 20], 'rsi': [14]}}
                
                6) Quy tắc thời gian: 
                - 'X ngày qua', 'X ngày gần nhất', 'trong X ngày', 'X ngày vừa rồi' → Trả về: 
                    - days = X 
                    - start = today - X ngày 
                    - end = today 
                - 'X tuần', 'X tuần qua', 'X tuần vừa rồi', 'trong X tuần' → weeks = X, start = today - X tuần 
                - 'X tháng', 'X tháng qua', 'X tháng vừa rồi', 'trong X tháng' → months = X, start = today - X tháng 
                - Nếu end không được nêu rõ → end = today 
                - Nếu user nêu rõ start và end → giữ nguyên cả hai. 
                - Nếu không có thông tin thời gian → để start = null, end = null. 
                
                === OUTPUT ===
                Trả về JSON theo schema sau: {format_instructions}"""
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
