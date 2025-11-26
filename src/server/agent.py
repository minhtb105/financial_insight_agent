import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from typing import TypedDict, Annotated, Sequence
from langgraph.graph import StateGraph, END
from langchain_core.messages import (
    HumanMessage,
    SystemMessage,
    AIMessage,
    BaseMessage,
    ToolMessage
)
from langgraph.prebuilt import ToolNode
from langgraph.graph.message import add_messages
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


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    parsed_query: dict
    tool_output: dict

class StockAgent:
    def __init__(self, model="llama-3.1-8b-instant"):
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY")

        self.model = ChatGroq(
            model=model, temperature=0, api_key=api_key
        )

        self.tools = [
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
        
        
        # LLM with tool-binding
        self.model_with_tools = self.model.bind_tools(self.tools)

        graph = StateGraph(AgentState)

        # Parser agent
        self.parser = QueryParser(model=model)

        # Node 1: parse query
        def parser_node(state: AgentState) -> AgentState:
            user_msg = state.get("messages")[-1].content
            if not user_msg:
                raise ValueError("Missing user query in state")

            parsed = self.parser.parse(user_msg)
            state["parsed_query"] = parsed
            
            ai_msg = AIMessage(
                content=f"Parser result: {parsed}. Now selecting appropriate tool...",
            )
            
            return {
                "messages": [ai_msg],  
                "parsed_query": parsed
            }

        graph.add_node("parser", parser_node)

        # Node 2: tool-selector
        def executor_node(state: AgentState) -> AgentState:
            parsed = state['parsed_query']
            system = SystemMessage(content="""
                Bạn PHẢI gọi tool theo đúng schema JSON sau:

                {
                "query": {
                    "tickers": ["HPG"],
                    "start": "YYYY-MM-DD",
                    "end": "YYYY-MM-DD",
                    "interval": "1d",
                    "requested_field": "...",
                    "aggregate": "...",
                    "compare_with": [...],
                    "indicator_params": {...}
                }
                }

                KHÔNG bao giờ được dùng:
                - query: "HPG"
                - query: ["HPG"]
                - days: 10
                - hoặc bất kỳ trường nào không được định nghĩa
                """)

            prompt = [
                system,
                HumanMessage(content=f"Hãy gọi tool phù hợp cho parsed_query sau: {parsed}")
            ]

            response = self.model_with_tools.invoke(prompt)

            return {"messages": [response], "parsed_query": parsed}
        
        graph.add_node("executor", executor_node)

        # Node 3: final answer agent
        def final_answer(state):
            tool_output = None
            for m in reversed(state["messages"]):
                if isinstance(m, ToolMessage):
                    tool_output = m.content
                    break

            text = f"""
            Bạn là chuyên gia chứng khoán.

            Truy vấn gốc: {state['messages'][0].content}
            Output từ tool: {tool_output}

            Hãy trả lời người dùng bằng tiếng Việt,
            ngắn gọn, dễ hiểu, và đưa ra insight nếu có.
            """

            response = self.model.invoke([HumanMessage(content=text)])

            return {"messages": [response], "tool_output": tool_output}

        graph.add_node("final_answer", final_answer)
        
        graph.add_node("tools", ToolNode(self.tools))

        graph.set_entry_point("parser")
        graph.add_edge("parser", "executor")
        graph.add_edge("executor", "tools")
        graph.add_edge("tools", "final_answer")
        graph.add_edge("final_answer", END)

        self.app = graph.compile()

    def print_messages(self, messages):
        if not messages:
            return

        for message in messages[-3:]:
            if isinstance(message, ToolMessage):
                print(f"\nTOOL RESULT: {message.content}")

    def run(self, query: str):
        init_state = {
            "messages": [HumanMessage(content=query)],
            "parsed_query": {},
            "tool_output": {},
        }
        for step in self.app.stream(init_state, stream_mode="values"):
            if "messages" in step:
                self.print_messages(step["messages"])

def build_graph():
    agent = StockAgent()
    
    return agent.app  # graph instance

graph = build_graph()
