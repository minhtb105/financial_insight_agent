import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import AgentMiddleware
from langchain.tools import BaseTool
from langchain.messages import HumanMessage
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


class StockAgentState(AgentState):
    messages: list

class StockPromptMiddleware(AgentMiddleware[StockAgentState]):
    def before_model(self, state: StockAgentState, runtime):
        last_input = state.get("messages", [])
        if last_input:
            user_msg = last_input[-1]
            if isinstance(user_msg, HumanMessage):
                new_prompt = f"Bạn là một agent chứng khoán Việt Nam.\nHỏi: {user_msg.content}"
                return {"messages": last_input + [HumanMessage(content=new_prompt)]}
        
        return None

# ───────────────────────────────
# Stock Agent
# ───────────────────────────────
class StockAgent:
    def __init__(self, model="llama-3.1-8b-instant"):
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY")

        self.llm = ChatGroq(
            model=model,
            api_key=api_key,
            temperature=0,
        )

        # Tools
        parser = QueryParser(model=model)
        self.tools: list[BaseTool] = [
            parser.parse_tool,
            get_company_info_tool,
            get_ohlcv_tool,
            get_min_open_across_tickers_tool,
            get_price_field_tool,
            get_price_stat_tool,
            get_aggregate_volume_tool,
            compare_volume_tool,
            get_sma_tool,
            get_rsi_tool,
        ]

        self.agent = create_agent(
            model=self.llm,
            tools=self.tools,
            middleware=[StockPromptMiddleware()],
            state_schema=StockAgentState,
        )

        # Graph wrapper
        self.graph = StateGraph(StockAgentState)

        def llm_node(state: StockAgentState):
            response = self.agent.invoke({"messages": state.get("messages", [])})
            return {"messages": state.get("messages", []) + [response]}

        self.graph.add_node("llm", llm_node)
        self.graph.set_entry_point("llm")
        self.graph.add_edge("llm", END)

        self.app = self.graph.compile()

    # ───────────────────────────────
    # API run
    # ───────────────────────────────
    def run(self, query: str) -> str:
        result = self.app.invoke({"messages": [HumanMessage(content=query)]})
        last = result["messages"][-1]
        
        return last.content
    