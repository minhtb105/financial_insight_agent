import os
from dotenv import load_dotenv
from langchain.agents import initialize_agent, AgentType
from langchain_groq import ChatGroq
from langchain.tools import Tool
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
        
        self.tools = [
            Tool(name="parse_stock_query", func=self.parser.parse_tool, description="Parse câu hỏi thành JSON HistoricalQuery"),
            Tool(name="get_company_info", func=get_company_info_tool, description="Lấy thông tin công ty (shareholders/subsidiaries/executives)"),
            Tool(name="get_ohlcv", func=get_ohlcv_tool, description="Lấy dữ liệu OHLCV cho ticker"),
            Tool(name="get_price_stat", func=get_price_stat_tool, description="Lấy thống kê giá (min/max/mean)"),
            Tool(name="get_aggregate_volume", func=get_aggregate_volume_tool, description="Tính tổng volume"),
            Tool(name="compare_volume", func=compare_volume_tool, description="So sánh volume giữa các ticker"),
            Tool(name="get_sma", func=get_sma_tool, description="Tính SMA theo window"),
            Tool(name="get_rsi", func=get_rsi_tool, description="Tính RSI theo window"),
        ]

        # Khởi tạo agent (ZERO SHOT REACT dùng tools)
        self.agent = initialize_agent(
            tools=self.tools,
            llm=self.llm,
            agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
            verbose=False,  
            handle_parsing_errors=True,
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
