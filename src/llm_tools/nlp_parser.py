from langchain_groq import ChatGroq
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from models.historical_query import HistoricalQuery
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

                Yêu cầu người dùng:
                {query}

                Hôm nay là ngày: {today} 
                (BẮT BUỘC phải dùng đúng ngày này khi tính toán thời gian.)

                MAPPING requested_field (bắt buộc sử dụng chính xác các giá trị bên phải):
                - "giá mở cửa", "mở cửa" -> open_price
                - "giá đóng", "giá đóng cửa", "đóng cửa" -> close_price
                - "giá cao nhất", "cao nhất" -> high_price
                - "giá thấp nhất", "thấp nhất" -> low_price
                - "khối lượng", "khối lượng giao dịch", "volume" -> volume
                - "OHLCV", "toàn bộ giá", "toàn bộ OHLCV" -> ohlcv
                
                # Technical indicators mapping (map mọi dạng gọi tên sang chữ phía phải)
                - "SMA", "sma", "sma9", "SMA9", "SMA-9", "sma20", "SMA20" -> sma
                - "RSI", "rsi", "RSI14", "rsi14" -> rsi
                - "MACD", "macd" -> macd

                # Company data mapping
                - "cổ đông lớn", "danh sách cổ đông", "shareholders" -> shareholders
                - "công ty con", "các công ty con", "subsidiaries" -> subsidiaries
                - "lãnh đạo", "ban lãnh đạo", "ban giám đốc", "giám đốc điều hành", "executives" -> executives

                QUY TẮC BẮT BUỘC:

                1) Nếu người dùng nói “X ngày qua”, “X ngày gần nhất”, “trong X ngày”, “10 ngày vừa rồi”…  
                    → Trả về:
                        - days = X
                        - start = today - X ngày
                        - end = today

                2) Nếu người dùng nói “X tuần” → weeks = X, start = today - X tuần

                3) Nếu người dùng nói “X tháng” → months = X, start = today - X tháng

                4) Nếu start có giá trị nhưng end không có  
                    → end = today

                5) Nếu user nêu rõ start và end → giữ nguyên cả hai.

                6) Nếu không có thông tin thời gian → để start = null, end = null.

                7) TUYỆT ĐỐI không được tự chọn ngày hiện tại khác.  
                    Phải sử dụng đúng biến {today} làm mốc thời gian duy nhất.

                8) LUÔN luôn đảm bảo JSON trả về tuân thủ EXACT schema dưới đây và không có text ngoài JSON.
                
                Trả về JSON theo schema sau:
                {format_instructions}"""
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
            return parsed_dict
        except Exception as e:
            raise ValueError(f"ParseError: {e}\nRaw: {raw_text}")
        
    @staticmethod
    def _extract_json(text: str) -> str:
        """Tự động bóc phần JSON hợp lệ ra khỏi text trả về"""
        match = re.search(r"\{.*\}", text, re.DOTALL)
        
        return match.group(0) if match else text
    
if __name__ == "__main__":
    parser = QueryParser()
    q = "Trong các mã BID, TCB và VCB mã nào có giá mở cửa thấp nhất trong 10 ngày qua."
    parsed_dict = parser.parse(q)
    print(parsed_dict)
    