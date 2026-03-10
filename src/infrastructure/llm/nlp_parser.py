from langchain_groq import ChatGroq
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from langchain_core.messages import HumanMessage, SystemMessage
from domain.entities.historical_query import HistoricalQuery
from datetime import datetime
import re
from typing import Dict, Any, Tuple
from infrastructure.llm.query_preprocessor import QueryPreprocessor


class QueryParser:
    """
    Enhanced parser that combines rule-based preprocessing with LLM refinement.
    Uses QueryPreprocessor for initial extraction and LLM for final validation.
    """
    
    def __init__(self, model: str = "llama-3.1-8b-instant"):
        from dotenv import load_dotenv
        import os
        load_dotenv()
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise ValueError("Thiếu GROQ_API_KEY trong .env")

        self.preprocessor = QueryPreprocessor()
        self.parser = PydanticOutputParser(pydantic_object=HistoricalQuery)

        # Few-shot examples for each query type
        self.few_shot_examples = {
            "price_query": [
                {
                    "input": "Lấy giá đóng cửa của VCB hôm qua.",
                    "output": {
                        "query_type": "price_query",
                        "requested_field": "close",
                        "tickers": ["VCB"],
                        "days": 1
                    }
                },
                {
                    "input": "Lấy dữ liệu OHLCV của HPG 10 ngày gần nhất.",
                    "output": {
                        "query_type": "price_query",
                        "requested_field": "ohlcv",
                        "tickers": ["HPG"],
                        "days": 10
                    }
                },
                {
                    "input": "Giá mở cửa của VIC trong 5 ngày vừa rồi.",
                    "output": {
                        "query_type": "price_query",
                        "requested_field": "open",
                        "tickers": ["VIC"],
                        "days": 5
                    }
                }
            ],
            "indicator_query": [
                {
                    "input": "Tính SMA9 cho VCB trong 1 tuần gần nhất.",
                    "output": {
                        "query_type": "indicator_query",
                        "requested_field": "sma",
                        "tickers": ["VCB"],
                        "indicator_params": {"sma": [9]},
                        "weeks": 1
                    }
                },
                {
                    "input": "Cho tôi SMA20 của HPG trong 2 tuần gần đây.",
                    "output": {
                        "query_type": "indicator_query",
                        "requested_field": "sma",
                        "tickers": ["HPG"],
                        "indicator_params": {"sma": [20]},
                        "weeks": 2
                    }
                },
                {
                    "input": "RSI14 của VIC từ đầu tháng 10 đến nay.",
                    "output": {
                        "query_type": "indicator_query",
                        "requested_field": "rsi",
                        "tickers": ["VIC"],
                        "indicator_params": {"rsi": [14]}
                    }
                }
            ],
            "company_query": [
                {
                    "input": "Danh sách cổ đông lớn của VCB.",
                    "output": {
                        "query_type": "company_query",
                        "requested_field": "shareholders",
                        "tickers": ["VCB"]
                    }
                },
                {
                    "input": "Danh sách lãnh đạo đang làm việc tại HPG.",
                    "output": {
                        "query_type": "company_query",
                        "requested_field": "executives",
                        "tickers": ["HPG"]
                    }
                },
                {
                    "input": "Các công ty con của VHM.",
                    "output": {
                        "query_type": "company_query",
                        "requested_field": "subsidiaries",
                        "tickers": ["VHM"]
                    }
                }
            ],
            "comparison_query": [
                {
                    "input": "So sánh khối lượng giao dịch của VIC với HPG trong 1 tuần.",
                    "output": {
                        "query_type": "comparison_query",
                        "requested_field": "volume",
                        "tickers": ["VIC"],
                        "compare_with": ["HPG"],
                        "weeks": 1
                    }
                },
                {
                    "input": "So sánh giá đóng của VCB với BID hôm nay.",
                    "output": {
                        "query_type": "comparison_query",
                        "requested_field": "close",
                        "tickers": ["VCB"],
                        "compare_with": ["BID"],
                        "days": 1
                    }
                }
            ],
            "ranking_query": [
                {
                    "input": "Trong các mã VCB, BID, CTG mã nào có giá mở cửa thấp nhất hôm qua?",
                    "output": {
                        "query_type": "ranking_query",
                        "requested_field": "open",
                        "tickers": ["VCB", "BID", "CTG"],
                        "aggregate": "min",
                        "days": 1
                    }
                },
                {
                    "input": "Mã nào cao nhất trong nhóm VHM, VIC, VRE trong 10 ngày qua?",
                    "output": {
                        "query_type": "ranking_query",
                        "requested_field": "close",
                        "tickers": ["VHM", "VIC", "VRE"],
                        "aggregate": "max",
                        "days": 10
                    }
                }
            ],
            "aggregate_query": [
                {
                    "input": "Tổng khối lượng giao dịch của HPG trong 1 tuần.",
                    "output": {
                        "query_type": "aggregate_query",
                        "requested_field": "volume",
                        "tickers": ["HPG"],
                        "aggregate": "sum",
                        "weeks": 1
                    }
                },
                {
                    "input": "Giá đóng trung bình của VCB trong 10 ngày.",
                    "output": {
                        "query_type": "aggregate_query",
                        "requested_field": "close",
                        "tickers": ["VCB"],
                        "aggregate": "mean",
                        "days": 10
                    }
                },
                {
                    "input": "Cho tôi giá đóng nhỏ nhất của SSI từ đầu tháng.",
                    "output": {
                        "query_type": "aggregate_query",
                        "requested_field": "close",
                        "tickers": ["SSI"],
                        "aggregate": "min"
                    }
                }
            ]
        }

        self.prompt = PromptTemplate(
            template=self._build_prompt_template(),
            input_variables=["query", "preprocessed", "few_shot_examples"],
            partial_variables={
                "format_instructions": self.parser.get_format_instructions(),
                "today": datetime.now().strftime("%Y-%m-%d")
            }
        )
        
        self.chat = ChatGroq(model=model, temperature=0, api_key=api_key, max_retries=3)
        self.structured_output_llm = self.chat.with_structured_output(
            HistoricalQuery,
            method='json_mode'
        )

    def _build_prompt_template(self) -> str:
        """Build the enhanced prompt template with few-shot examples."""
        return """
            Bạn là một parser chuyên nghiệp. Nhiệm vụ của bạn là phân tích câu hỏi và trả về JSON theo schema sau:

            {format_instructions}

            Few-shot examples:
            {few_shot_examples}

            Câu hỏi: {query}
            Hôm nay: {today}

            Thông tin đã được xử lý trước (có thể có lỗi):
            {preprocessed}

            QUY TẮC THỜI GIAN:
            - "X ngày gần nhất / trong X ngày / X ngày vừa rồi" → days = X, start = {today} - X ngày, end = {today}
            - "X tuần", "trong X tuần" → weeks = X, start = {today} - X tuần, end = {today}
            - "X tháng", "trong X tháng" → months = X, start = {today} - X tháng, end = {today}
            - Nếu user nêu rõ start và end → giữ nguyên start/end (định dạng "YYYY-MM-DD").
            - Nếu end không nêu rõ → end = {today}
            - Nếu không có thông tin thời gian → start = null, end = null, days/weeks/months = null
            - **Luôn** trả start/end ở định dạng "YYYY-MM-DD" khi có giá trị.

            Hãy sử dụng thông tin đã xử lý trước để hỗ trợ việc phân tích, nhưng hãy kiểm tra và điều chỉnh nếu cần.
            Hãy trả lời ngắn gọn, chỉ trả về JSON, không giải thích thêm.
        """

    def _get_few_shot_examples(self, query_type: str) -> str:
        """Get few-shot examples for a specific query type."""
        examples = self.few_shot_examples.get(query_type, [])
        if not examples:
            return "Không có ví dụ mẫu."
        
        result = []
        for i, example in enumerate(examples[:3]):  # Limit to 3 examples
            result.append(f"Ví dụ {i+1}:")
            result.append(f"Input: {example['input']}")
            result.append(f"Output: {example['output']}")
            result.append("")
        
        return "\n".join(result)

    def _build_few_shot_context(self, query: str, preprocessed_type: str) -> str:
        """Build few-shot context based on the preprocessed query type."""
        # Get examples for the detected type
        context = self._get_few_shot_examples(preprocessed_type)
        
        # Also include examples from similar types if confidence is low
        if preprocessed_type in ["comparison_query", "ranking_query"]:
            context += "\n" + self._get_few_shot_examples("price_query")
        elif preprocessed_type == "aggregate_query":
            context += "\n" + self._get_few_shot_examples("price_query")
        
        return context

    def parse(self, query: str) -> Dict[str, Any]:
        """Parse query using enhanced approach."""
        # Step 1: Preprocess with rule-based approach
        preprocessed = self.preprocessor.preprocess(query)
        confidence = self.preprocessor.calculate_confidence(query, preprocessed)
        
        # Step 2: Get few-shot context
        few_shot_context = self._build_few_shot_context(query, preprocessed["query_type"])
        
        # Step 3: Build prompt
        prompt = self.prompt.format(
            query=query,
            preprocessed=preprocessed,
            few_shot_examples=few_shot_context
        )
        
        # Step 4: Call LLM with confidence-based approach
        if confidence >= 0.8:
            # High confidence: use preprocessed as strong guidance
            system_msg = SystemMessage(f"""
            Bạn là một parser chuyên nghiệp. Dựa trên thông tin đã xử lý trước, hãy xác nhận và điều chỉnh nếu cần.
            
            Thông tin đã xử lý trước (độ tin cậy cao):
            {preprocessed}
            
            Hãy đảm bảo kết quả cuối cùng đúng với schema:
            {self.parser.get_format_instructions()}
            """)
        else:
            # Low confidence: use preprocessed as suggestion only
            system_msg = SystemMessage(f"""
            Bạn là một parser chuyên nghiệp. Thông tin đã xử lý trước có thể có lỗi, hãy kiểm tra kỹ.
            
            Thông tin đã xử lý trước (độ tin cậy thấp):
            {preprocessed}
            
            Hãy đảm bảo kết quả cuối cùng đúng với schema:
            {self.parser.get_format_instructions()}
            """)

        human_msg = HumanMessage(query)

        # Step 5: Get LLM response
        response = self.structured_output_llm.invoke([system_msg] + [human_msg])
        
        # Step 6: Post-process and validate
        result = response.model_dump()
        result = self._post_process(result, preprocessed, confidence)
        
        return result

    def _post_process(self, result: Dict[str, Any], preprocessed: Dict[str, Any], confidence: float) -> Dict[str, Any]:
        """Post-process the LLM result with validation and corrections."""
        # Validate required fields
        if not result.get("tickers"):
            result["tickers"] = preprocessed.get("tickers", [])
        
        if not result.get("query_type"):
            result["query_type"] = preprocessed.get("query_type", "price_query")
        
        if not result.get("requested_field"):
            result["requested_field"] = preprocessed.get("requested_field")
        
        # Validate time parameters
        if result.get("days") and result.get("weeks"):
            # If both are present, prioritize the one from preprocessing
            if "days" in preprocessed:
                result.pop("weeks", None)
            else:
                result.pop("days", None)
        
        # Validate comparison query
        if result.get("query_type") == "comparison_query":
            if not result.get("compare_with") and len(result.get("tickers", [])) > 1:
                tickers = result["tickers"]
                result["tickers"] = [tickers[0]]
                result["compare_with"] = tickers[1:]
        
        # Validate ranking query
        if result.get("query_type") == "ranking_query":
            if len(result.get("tickers", [])) < 2:
                result["query_type"] = "price_query"
        
        # Add confidence score
        result["_confidence"] = confidence
        
        return result

    def parse_with_confidence(self, query: str) -> Tuple[Dict[str, Any], float]:
        """Parse query and return both result and confidence score."""
        result = self.parse(query)
        confidence = result.pop("_confidence", 0.0)
        return result, confidence

    @staticmethod
    def _extract_json(text: str) -> str:
        """Extract JSON from text."""
        match = re.search(r"\{.*\}", text, re.DOTALL)
        return match.group(0) if match else text
