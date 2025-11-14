import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
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

class State(dict):
    pass

class StockAgent:
    def __init__(self, model="llama-3.1-8b-instant"):
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")

        if not api_key:
            raise ValueError("Missing GROQ_API_KEY")

        self.llm = ChatGroq(model=model, temperature=0, api_key=api_key)

        # Tools
        parser = QueryParser(model=model)

        self.tools = [
            parser.parse_tool,
            get_company_info_tool,
            get_ohlcv_tool,
            get_price_stat_tool,
            get_aggregate_volume_tool,
            compare_volume_tool,
            get_sma_tool,
            get_rsi_tool,
        ]

        # Convert to LangChain Tool format
        lc_tools = [t for t in self.tools]

        # Build graph
        graph = StateGraph(State)

        # LLM node
        def llm_node(state: State):
            response = self.llm.invoke(
                f"""
                Bạn là một agent chứng khoán Việt Nam.
                Khi người dùng hỏi:
                    1) Gọi tool parse_stock_query trước.
                    2) Chọn tool đúng cho SMA/RSI/OHLCV/volume/company info.
                    3) Trả lời tiếng Việt.

                Câu hỏi: {state["input"]}
                """
            )
            return {"llm_output": response.content}

        graph.add_node("llm", llm_node)
        graph.set_entry_point("llm")
        graph.add_edge("llm", END)

        self.app = graph.compile()

    def run(self, query: str):
        result = self.app.invoke({"input": query})
        return result["llm_output"]
