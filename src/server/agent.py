import os
from dotenv import load_dotenv
from langchain.agents import create_agent
from langchain_core.prompts import PromptTemplate
from langchain_groq import ChatGroq
from langchain.tools import tool
from llm_tools.nlp_parser import QueryParser
from llm_tools.tools import (
    get_company_info_tool,
    get_ohlcv_tool,
    get_price_stat_tool,
    get_aggregate_volume_tool,
    compare_volume_tool,
    get_sma_tool,
    get_rsi_tool,
)


class StockAgent:
    def __init__(self, model: str = "llama-3.1-8b-instant"):
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Thiếu GROQ_API_KEY trong .env")

        # LLM
        self.llm = ChatGroq(model=model, temperature=0, api_key=api_key)

        self.parser = QueryParser(model=model)
        
        self.tools = [self.parser.parse_tool, get_company_info_tool, get_ohlcv_tool, 
                    get_price_stat_tool, get_aggregate_volume_tool, 
                    compare_volume_tool, get_sma_tool, get_rsi_tool]

           # ─────────────────────────────
        # Prompt chuẩn cho ReAct agent
        # ─────────────────────────────
        template = """
            Bạn là một assistant phân tích chứng khoán. 
            Bạn sẽ sử dụng tools khi cần thiết để trả lời truy vấn của người dùng.

            Nếu câu hỏi liên quan đến phân tích chứng khoán (SMA, RSI, giá, volume, cổ đông, lãnh đạo...),
            hãy gọi tool parse_stock_query trước.

            Sau khi có JSON schema, hãy chọn đúng tool và trả câu trả lời cuối cùng bằng tiếng Việt.

            Dữ liệu vào: {input}
        """

        prompt = PromptTemplate.from_template(template)

        # ─────────────────────────────
        # Tạo agent chuẩn LangChain
        # ─────────────────────────────
        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            prompt=prompt,
        )

    def run(self, query: str) -> str:
        """
        Chạy agent với truy vấn tự nhiên (tiếng Việt).
        Agent sẽ:
          1) Gọi parse_stock_query để nhận JSON HistoricalQuery
          2) Quyết định tool phù hợp và gọi tool
          3) Trả về text cuối
        """
        try:
            return self.agent.run(query)
        except Exception as e:
            return f"Lỗi Agent: {e}"
