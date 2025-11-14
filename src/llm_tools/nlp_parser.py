from langchain_groq import ChatGroq
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from models.historical_query import HistoricalQuery
from langchain.tools import tool
from datetime import datetime
import re


class QueryParser:
    """Parser dùng LLM để phân tích câu truy vấn chứng khoán sang cấu trúc JSON."""

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
                Yêu cầu người dùng: {query} 
                Hôm nay là ngày: {today} 
                (BẮT BUỘC phải dùng đúng ngày này khi tính toán thời gian.) 
                
                ❗ Quy tắc BẮT BUỘC: 
                - KHÔNG trả về mapping keyword. 
                - KHÔNG ghi chú giải. 
                - KHÔNG viết text ngoài JSON. 
                - JSON phải đúng schema 100%. 
                
                ❗ Cách xác định intent: 
                - Nếu câu hỏi liên quan SMA, RSI, MACD → intent = "technical_indicator" 
                - Nếu câu hỏi về giá quá khứ (open, close, high, low, ohlcv, volume) → intent = "historical_prices" 
                - Nếu câu hỏi về lãnh đạo, cổ đông, công ty con → intent = "company_info" 
                
                ❗ Cách xác định requested_field: 
                - Giá mở → "open_price" 
                - Giá đóng → "close_price" 
                - OHLCV → "ohlcv" 
                - Khối lượng → "volume" 
                - SMA* → "sma" 
                - RSI* → "rsi" 
                - MACD → "macd" 
                - Cổ đông → "shareholders" 
                - Công ty con → "subsidiaries" 
                - Lãnh đạo → "executives" 
                
                ❗ Quy tắc technical indicators: 
                - SMA9 → indicator_params = {{"sma": [9]}} 
                - SMA9 và SMA20 → indicator_params = {{"sma": [9, 20]}} 
                - RSI14 → indicator_params = {{"rsi": [14]}} 
                indicator_params LUÔN LUÔN phải có nếu intent = "technical_indicator". 
                
                ❗ Quy tắc cho aggregate: 
                - 'lớn nhất', 'cao nhất', 'max' → aggregate = 'max' 
                - 'nhỏ nhất', 'thấp nhất', 'min' → aggregate = 'min' 
                - 'tổng', 'tổng cộng', 'sum', 'tổng khối lượng' → aggregate = 'sum' 
                - 'trung bình', 'bình quân', 'average', 'mean' → aggregate = 'average' 
                
                ❗ Quy tắc cho compare (so sánh giữa các mã): 
                - Nếu câu chứa 'so sánh' → tickers = [mã đầu tiên], compare_with = [các mã còn lại]
                - Ví dụ: 'So sánh khối lượng giao dịch của VIC với HPG và BID trong 2 tuần gần đây'
                    → tickers = ['VIC']
                    → compare_with = ['HPG', 'BID']
                - KHÔNG đưa tất cả các mã vào tickers, chỉ mã đầu tiên vào tickers, các mã còn lại vào compare_with.
                                        
                ❗ Trường hợp đặc biệt: 
                - Nếu câu ở dạng 'Trong các mã A,B,C mã nào…' 
                → Đây KHÔNG phải compare 
                → Không dùng compare_with 
                → aggregate = min/max theo câu 
                → tickers = toàn bộ danh sách 
                
                ❗ Quy tắc thời gian: 
                1) 'X ngày qua', 'X ngày gần nhất', 'trong X ngày', '10 ngày vừa rồi'… → Trả về: 
                    - days = X 
                    -start = today - X ngày 
                    - end = today 
                2) 'X tuần' → weeks = X, start = today - X tuần 
                3) 'X tháng' → months = X, start = today - X tháng 
                4) Nếu end không được nêu rõ → end = today 
                5) Nếu user nêu rõ start và end → giữ nguyên cả hai. 
                6) Nếu không có thông tin thời gian → để start = null, end = null. 
                7) TUYỆT ĐỐI không được tự chọn ngày hiện tại khác. 
                Phải sử dụng đúng biến {today} làm mốc thời gian duy nhất. 
                
                LUÔN luôn đảm bảo JSON trả về tuân thủ EXACT schema dưới đây và không có text ngoài JSON. 
                Trả về JSON theo schema sau: {format_instructions}"""
            ),
            input_variables=["query"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )

        self.chat = ChatGroq(model=model, temperature=0, api_key=api_key)

    def parse(self, query: str) -> HistoricalQuery:
        """Phân tích câu truy vấn tự nhiên -> cấu trúc HistoricalQuery"""
        now = datetime.now()
        input_text = self.prompt.format_prompt(query=query, today=now.strftime("%Y-%m-%d")).to_string()
        resp = self.chat.invoke(input_text)

        raw_text = resp.content if hasattr(resp, "content") else str(resp)
        json_str = self._extract_json(raw_text)
        
        try:
            parsed_model = self.parser.parse(json_str)
            parsed_dict = parsed_model.model_dump() if hasattr(parsed_model, "model_dump") else dict(parsed_model)
            if parsed_dict.get("start") and not parsed_dict.get("end"):
                parsed_dict["end"] = now.strftime("%Y-%m-%d")
                
            # Nếu là intent so sánh, tickers có nhiều mã, compare_with chưa có, thì tự động chuyển
            if (
                parsed_dict.get("intent") == "historical_prices"
                and parsed_dict.get("compare_with") is None
                and parsed_dict.get("tickers")
                and len(parsed_dict["tickers"]) > 1
            ):
                parsed_dict["compare_with"] = parsed_dict["tickers"][1:]
                parsed_dict["tickers"] = [parsed_dict["tickers"][0]]
                
            return parsed_dict
        except Exception as e:
            raise ValueError(f"ParseError: {e}\nRaw: {raw_text}")
        
    @staticmethod
    def _extract_json(text: str) -> str:
        """Tự động bóc phần JSON hợp lệ ra khỏi text trả về"""
        match = re.search(r"\{.*\}", text, re.DOTALL)
        
        return match.group(0) if match else text
    
    @tool(
        "parse_stock_query",
        description="""Phân tích câu hỏi tiếng Việt về chứng khoán thành JSON chuẩn để các tool khác sử dụng.
                    Dùng cho mọi truy vấn về giá, chỉ báo kỹ thuật, thông tin công ty, so sánh, tổng hợp, v.v.
                    Đầu vào là câu hỏi tự nhiên, đầu ra là dict theo schema HistoricalQuery."""
    )
    def parse_tool(self, query: str):
        return self.parse(query)
    