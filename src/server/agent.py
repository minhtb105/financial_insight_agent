import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph, END
from llm_tools.nlp_parser import QueryParser
from llm_tools.tools import (
    get_company_info_tool,
    get_ohlcv_tool,
    get_min_open_across_tickers_tool,
    get_price_field_tool,
    get_price_stat_tool,
    get_aggregate_volume_tool,
    compare_volume_tool,
    get_sma_tool,
    get_rsi_tool,
)


class StockAgent:
    def __init__(self, model="llama-3.1-8b-instant"):
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY")

        # LLM (dùng cho trả lời bằng ngôn ngữ tự nhiên)
        self.llm = ChatGroq(model=model, temperature=0, api_key=api_key)

        # Parser
        self.parser = QueryParser(model=model)

        # Build StateGraph
        graph = StateGraph(dict)

        # Node 1: parse query
        def parse_node(state):
            user_input = state.get("input")
            if not user_input:
                raise ValueError("Missing user query in state")

            # Sử dụng parser.parse trực tiếp
            parsed = self.parser.parse(user_input)
            state["parsed_query"] = parsed
            
            return state

        graph.add_node("parse_query", parse_node)

        # Node 2: tự động chọn tool và thực thi
        def execute_node(state):
            parsed = state.get("parsed_query", {})
            intent = parsed.get("intent")
            tickers = parsed.get("tickers")
            start = parsed.get("start")
            end = parsed.get("end")
            field = parsed.get("requested_field")
            aggregate = parsed.get("aggregate")
            indicator_params = parsed.get("indicator_params")
            compare_with = parsed.get("compare_with")
            interval = parsed.get("interval")

            # ensure tickers present when needed
            def missing_ticker_response():
                return "Thiếu ticker trong truy vấn."

            result = None

            # historical_prices → OHLCV: try direct function first
            if intent == "historical_prices" and field == "ohlcv":
                result = get_ohlcv_tool.run({
                    "query": {"tickers": tickers, 
                              "start": start, 
                              "end": end, 
                              "interval": interval}
                })
            # historical_prices → trường giá cụ thể (open, close, high, low, volume)
            elif intent == "historical_prices" and field in ("open_price", "close_price", "high_price", "low_price", "volume"):
                # Nếu có aggregate (min/max/mean), dùng get_price_stat
                if not tickers:
                    result = missing_ticker_response()
                else:
                    if aggregate:
                        result = get_price_stat_tool.run({
                            "query":  {
                                "tickers": tickers,
                                "start": start,
                                "end": end,
                                "interval": interval,
                                "requested_field": field,
                                "aggregate": aggregate,}
                        })
                    else:
                        result = get_price_field_tool.run({"query": {
                            "tickers": tickers,
                            "start": start,
                            "end": end,
                            "interval": interval,
                            "requested_field": field,
                        }})
            # Tổng khối lượng giao dịch
            elif intent == "historical_prices" and field == "volume" and aggregate == "sum":
                result = get_aggregate_volume_tool.run({"query": {
                    "tickers": tickers,
                    "start": start,
                    "end": end,
                    "interval": interval,
                }})
            # So sánh khối lượng giao dịch
            elif intent == "historical_prices" and field == "volume" and compare_with:
                result = compare_volume_tool.run({"query": {
                    "tickers": tickers,
                    "compare_with": compare_with,
                    "start": start,
                    "end": end,
                    "interval": interval,
                }})
            # Tìm mã có open thấp nhất trong danh sách tickers
            elif intent == "historical_prices" and field == "open_price" and aggregate == "min" and tickers and len(tickers) > 1:
                result = get_min_open_across_tickers_tool.run({"query": {
                    "tickers": tickers,
                    "start": start,
                    "end": end,
                    "interval": interval,
                }})
            # technical indicators → SMA, RSI
            elif intent == "technical_indicator":
                result = {}
                if indicator_params and "sma" in indicator_params:
                    result["sma"] = get_sma_tool.run({"query": {
                        "tickers": tickers,
                        "start": start,
                        "end": end,
                        "interval": interval,
                        "indicator_params": indicator_params,
                    }})
                if indicator_params and "rsi" in indicator_params:
                    result["rsi"] = get_rsi_tool.run({"query": {
                        "tickers": tickers,
                        "start": start,
                        "end": end,
                        "interval": interval,
                        "indicator_params": indicator_params,
                    }})
            # company info
            elif intent == "company_info":
                result = get_company_info_tool.run({"query": {
                    "tickers": tickers,
                    "requested_field": field,
                }})
            else:
                result = {"error": "Không xác định được tool để thực thi"}

            state["tool_output"] = result
            
            return state
        
        graph.add_node("execute_tool", execute_node)

        # Node 3: LLM trả lời 
        def llm_node(state):
            parsed = state.get("parsed_query", {})
            tool_output = state.get("tool_output", {})
            user_query = state.get("input", "")

            response = self.llm.invoke(
                f"""
                Bạn là agent chứng khoán Việt Nam.
                Người dùng hỏi: {user_query}
                Parsed query: {parsed}
                Output từ tool: {tool_output}
                Trả lời bằng tiếng Việt, ngắn gọn và dễ hiểu.
                """
            )
            state["llm_output"] = response.content
            
            return state

        graph.add_node("llm_response", llm_node)

        # Kết nối nodes
        graph.set_entry_point("parse_query")
        graph.add_edge("parse_query", "execute_tool")
        graph.add_edge("execute_tool", "llm_response")
        graph.add_edge("llm_response", END)

        # Compile graph
        self.app = graph.compile()

    def run(self, query: str):
        initial_state = {"input": query}
        result = self.app.invoke(initial_state)
        return result.get("llm_output", ""), result.get("tool_output", {})


if __name__ == "__main__":
    agent = StockAgent()
    query = "Lấy dữ liệu OHLCV 10 ngày gần nhất HPG?"
    llm_reply, tool_data = agent.run(query)

    print("=== Tool Output ===")
    print(tool_data)
    print("\n=== LLM Reply ===")
    print(llm_reply)
