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
from infrastructure.llm.nlp_parser import QueryParser
from application.agent.enhanced_tool_registry import ENHANCED_TOOLS


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    parsed_query: dict
    tool_output: dict
    confidence: float


class EnhancedStockAgent:
    """
    Enhanced agent that uses the improved parser with rule-based preprocessing
    and confidence-based approach.
    """
    
    def __init__(self, model="llama-3.1-8b-instant"):
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Missing GROQ_API_KEY")

        self.model = ChatGroq(
            model=model, temperature=0, api_key=api_key
        )

        # Use enhanced tools
        self.tools = ENHANCED_TOOLS

        # LLM with tool-binding
        self.model_with_tools = self.model.bind_tools(self.tools)

        graph = StateGraph(AgentState)

        # Enhanced parser agent
        self.parser = QueryParser(model=model)

        # Node 1: parse query with confidence
        def parser_node(state: AgentState) -> AgentState:
            user_msg = state.get("messages")[-1].content
            if not user_msg:
                raise ValueError("Missing user query in state")

            # Parse with confidence
            parsed, confidence = self.parser.parse_with_confidence(user_msg)
            
            state["parsed_query"] = parsed
            state["confidence"] = confidence

            ai_msg = AIMessage(
                content=f"Parser result (confidence: {confidence:.2f}): {parsed}. Now selecting appropriate tool...",
            )

            return {
                "messages": [ai_msg],
                "parsed_query": parsed,
                "confidence": confidence
            }

        graph.add_node("parser", parser_node)

        # Node 2: tool-selector with confidence-based approach
        def executor_node(state: AgentState) -> AgentState:
            parsed = state['parsed_query']
            confidence = state['confidence']
            
            # Set adaptive threshold based on confidence
            threshold = 0.8 if confidence >= 0.7 else 0.6
            
            system_content = f"""
            Bạn PHẢI gọi tool theo đúng schema JSON sau:

            {{
                "query": {{
                    "tickers": ["HPG"],
                    "start": "YYYY-MM-DD",
                    "end": "YYYY-MM-DD",
                    "interval": "1d",
                    "requested_field": "...",
                    "aggregate": "...",
                    "compare_with": [...],
                    "indicator_params": {{...}}
                }}
            }}

            KHÔNG bao giờ được dùng:
            - query: "HPG"
            - query: ["HPG"]
            - days: 10
            - hoặc bất kỳ trường nào không được định nghĩa

            GỢI Ý:
            - Nếu confidence >= {threshold:.2f}: tin tưởng kết quả parser, dùng như hướng dẫn
            - Nếu confidence < {threshold:.2f}: kiểm tra kỹ, có thể cần hỏi clarification
            - Nếu không chắc chắn: dùng tool phù hợp nhất dựa trên query_type
            """

            system = SystemMessage(content=system_content)

            prompt = [
                system,
                HumanMessage(
                    content=f"Hãy gọi tool phù hợp cho parsed_query sau (confidence: {confidence:.2f}): {parsed}")
            ]

            response = self.model_with_tools.invoke(prompt)

            return {
                "messages": [response], 
                "parsed_query": parsed,
                "confidence": confidence
            }

        graph.add_node("executor", executor_node)

        # Node 3: final answer agent
        def final_answer(state):
            tool_output = None
            for m in reversed(state["messages"]):
                if isinstance(m, ToolMessage):
                    tool_output = m.content
                    break

            # Get original query
            original_query = state["messages"][0].content if state["messages"] else ""

            text = f"""
            Bạn là chuyên gia chứng khoán.

            Truy vấn gốc: {original_query}
            Confidence score: {state.get('confidence', 0):.2f}
            Output từ tool: {tool_output}

            Hãy trả lời người dùng bằng tiếng Việt,
            ngắn gọn, dễ hiểu, và đưa ra insight nếu có.
            
            GỢI Ý:
            - Nếu confidence >= 0.8: trả lời tự tin, cung cấp insight chi tiết
            - Nếu confidence 0.5-0.8: trả lời cẩn trọng, đề cập đến độ tin cậy
            - Nếu confidence < 0.5: đề xuất xác nhận thông tin hoặc cung cấp câu trả lời chung chung
            """

            response = self.model.invoke([HumanMessage(content=text)])

            return {
                "messages": [response], 
                "tool_output": tool_output
            }

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
        import time
        start_time = time.time()
        init_state = {
            "messages": [HumanMessage(content=query)],
            "parsed_query": {},
            "tool_output": {},
            "confidence": 0.0,
        }
        for step in self.app.stream(init_state, stream_mode="values"):
            if "messages" in step:
                self.print_messages(step["messages"])
        end_time = time.time()
        latency = end_time - start_time
        print(f"[LATENCY] Agent xử lý mất {latency:.3f} giây.")


def build_enhanced_graph():
    agent = EnhancedStockAgent()
    return agent.app  # graph instance


enhanced_graph = build_enhanced_graph()