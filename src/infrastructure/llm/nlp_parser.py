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
            "financial_ratio_query": [
                {
                    "input": "Tỷ lệ P/E của VNM hiện tại là bao nhiêu?",
                    "output": {
                        "query_type": "financial_ratio_query",
                        "requested_field": "pe",
                        "tickers": ["VNM"]
                    }
                },
                {
                    "input": "So sánh ROE giữa FPT và VNM trong 3 năm gần đây",
                    "output": {
                        "query_type": "financial_ratio_query",
                        "requested_field": "roe",
                        "tickers": ["FPT"],
                        "compare_with": ["VNM"],
                        "years": 3
                    }
                },
                {
                    "input": "EPS của HPG trong quý 3/2024 là bao nhiêu?",
                    "output": {
                        "query_type": "financial_ratio_query",
                        "requested_field": "eps",
                        "tickers": ["HPG"],
                        "period": "quarter",
                        "quarter": 3,
                        "year": 2024
                    }
                }
            ],
            "price_query": [
                {
                    "input": "Lấy giá mở cửa của VCB hôm qua.",
                    "output": {
                        "query_type": "price_query",
                        "requested_field": "open",
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
                },
                {
                    "input": "Trong nhóm HPG, NKG, HSG mã nào có volume thấp nhất tuần này?",
                    "output": {
                        "query_type": "ranking_query",
                        "requested_field": "volume",
                        "tickers": ["HPG", "NKG", "HSG"],
                        "aggregate": "min",
                        "weeks": 1
                    }
                },
                {
                    "input": "Trong các mã HSG, HPG, NKG mã nào tăng mạnh nhất trong tháng?",
                    "output": {
                        "query_type": "ranking_query",
                        "requested_field": "close",
                        "tickers": ["HSG", "HPG", "NKG"],
                        "aggregate": "max",
                        "months": 1
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
            ],
            "news_sentiment_query": [
                {
                    "input": "Có tin tức gì về VCB trong tuần này không?",
                    "output": {
                        "query_type": "news_sentiment_query",
                        "requested_field": "news",
                        "tickers": ["VCB"],
                        "weeks": 1
                    }
                },
                {
                    "input": "Cảm xúc thị trường đối với nhóm ngân hàng hiện nay ra sao?",
                    "output": {
                        "query_type": "news_sentiment_query",
                        "requested_field": "sentiment",
                        "tickers": ["VCB", "BID", "CTG", "MBB", "ACB"],
                        "days": 7
                    }
                },
                {
                    "input": "Tin tức tích cực về FPT trong tháng 11",
                    "output": {
                        "query_type": "news_sentiment_query",
                        "requested_field": "positive_news",
                        "tickers": ["FPT"],
                        "months": 1
                    }
                }
            ],
            "portfolio_query": [
                {
                    "input": "Nếu tôi mua 100 cổ FPT và 200 cổ VNM thì danh mục hiện tại ra sao?",
                    "output": {
                        "query_type": "portfolio_query",
                        "requested_field": "portfolio_summary",
                        "portfolio": {
                            "FPT": 100,
                            "VNM": 200
                        }
                    }
                },
                {
                    "input": "Hiệu suất danh mục của tôi trong tháng 11 là bao nhiêu?",
                    "output": {
                        "query_type": "portfolio_query",
                        "requested_field": "performance",
                        "months": 1
                    }
                },
                {
                    "input": "Phân bổ ngành trong danh mục hiện tại",
                    "output": {
                        "query_type": "portfolio_query",
                        "requested_field": "sector_allocation"
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

            QUY TẮC PHÂN LOẠI QUERY:
            - Nếu query chứa các chỉ số tài chính (P/E, PE, P/B, PB, ROE, EPS, tỷ lệ, ratio) → financial_ratio_query (ƯU TIÊN CAO NHẤT)
            - Nếu query có từ khóa so sánh (so sánh, compare) nhưng KHÔNG có chỉ số tài chính → comparison_query
            - Nếu query có từ khóa xếp hạng (cao nhất, thấp nhất, lớn nhất, nhỏ nhất, min, max, top, bottom) → ranking_query
            - Nếu query có từ khóa tổng hợp (tổng, sum, trung bình, mean, nhỏ nhất, lớn nhất, min, max) → aggregate_query
            - Nếu query có từ khóa chỉ báo (SMA, EMA, RSI, MACD, MA, chỉ báo, indicator) → indicator_query
            - Nếu query có từ khóa công ty (cổ đông, lãnh đạo, CEO, BOD, công ty con, công ty mẹ) → company_query
            - Nếu query có từ khóa tin tức (tin tức, news, cảm xúc, sentiment, tích cực, tiêu cực) → news_sentiment_query
            - Nếu query có từ khóa danh mục (danh mục, portfolio, hiệu suất, phân bổ, giá trị) → portfolio_query
            - Các trường hợp còn lại → price_query

            QUY TẮC ƯU TIÊN:
            1. Financial ratio query có ưu tiên CAO NHẤT - luôn kiểm tra trước
            2. Nếu có "so sánh" + chỉ số tài chính → financial_ratio_query
            3. Nếu có "so sánh" nhưng KHÔNG có chỉ số tài chính → comparison_query
            4. Các loại khác theo thứ tự ưu tiên giảm dần

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
        """Parse query using enhanced approach with smart priority detection."""
        # Step 1: Preprocess with rule-based approach
        preprocessed = self.preprocessor.preprocess(query)
        confidence = self.preprocessor.calculate_confidence(query, preprocessed)
        
        # Step 1.5: Smart detection for priority handling
        has_financial_metrics = self.preprocessor.has_financial_metrics(query)
        has_ranking_keywords = self.preprocessor.has_ranking_keywords(query)
        has_comparison_keywords = self.preprocessor.has_comparison_keywords(query)
        
        # Build priority instruction
        priority_instruction = ""
        if has_financial_metrics and has_comparison_keywords:
            # Case: "So sánh ROE giữa FPT và VNM" 
            # Both have financial metrics AND comparison keywords
            # Priority: financial_ratio_query > comparison_query
            priority_instruction = "\n⚠️ ƯU TIÊN CAO: Query này có cả từ khóa 'so sánh' lẫn chỉ số tài chính (ROE, PE, EPS). ĐÃY LÀ financial_ratio_query, KHÔNG phải comparison_query."
        elif has_ranking_keywords and has_comparison_keywords:
            # Case: "Mã nào ... trong nhóm"
            # Both ranking and comparison keywords - prioritize ranking
            priority_instruction = "\n⚠️ ƯU TIÊN CAO: Query này yêu cầu xếp hạng (min, max, cao nhất, thấp nhất). ĐÃY LÀ ranking_query, KHÔNG phải comparison_query."
        
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
            {priority_instruction}
            """)
        else:
            # Low confidence: use preprocessed as suggestion only
            system_msg = SystemMessage(f"""
            Bạn là một parser chuyên nghiệp. Thông tin đã xử lý trước có thể có lỗi, hãy kiểm tra kỹ.
            
            Thông tin đã xử lý trước (độ tin cậy thấp):
            {preprocessed}
            
            Hãy đảm bảo kết quả cuối cùng đúng với schema:
            {self.parser.get_format_instructions()}
            {priority_instruction}
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
