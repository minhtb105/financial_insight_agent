from __future__ import annotations
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate
from models.historical_query import HistoricalQuery
import os
import re


class QueryParser:
    """Parser dùng LLM để phân tích câu truy vấn chứng khoán sang cấu trúc JSON."""

    def __init__(self, model_id: str = "openai/gpt-oss-20b"):
        load_dotenv()
        hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
        if not hf_token:
            raise ValueError("Thiếu HUGGINGFACEHUB_API_TOKEN trong .env")

        os.environ["HUGGINGFACEHUB_API_TOKEN"] = hf_token

        self.parser = PydanticOutputParser(pydantic_object=HistoricalQuery)

        self.prompt = PromptTemplate(
            template=(
                "Bạn là parser. Chỉ trả về JSON hợp lệ (KHÔNG giải thích thêm).\n\n"
                "Yêu cầu người dùng:\n{query}\n\n"
                "Trả về JSON theo schema sau:\n{format_instructions}"
            ),
            input_variables=["query"],
            partial_variables={"format_instructions": self.parser.get_format_instructions()},
        )

        hf_llm = HuggingFaceEndpoint(
            repo_id=model_id,
            task="text-generation",
            max_new_tokens=512,
            temperature=0.0,
            do_sample=False,
            repetition_penalty=1.03,
        )

        self.chat = ChatHuggingFace(llm=hf_llm, verbose=True)

    def parse(self, query: str) -> HistoricalQuery:
        """Phân tích câu truy vấn tự nhiên -> cấu trúc HistoricalQuery"""
        input_text = self.prompt.format_prompt(query=query).to_string()
        resp = self.chat.invoke(input_text)

        raw_text = resp.content if hasattr(resp, "content") else str(resp)
        json_str = self._extract_json(raw_text)
        try:
            parsed = self.parser.parse(json_str)
            return parsed
        except Exception as e:
            raise ValueError(f"ParseError: {e}\nRaw: {raw_text}")
        
    @staticmethod
    def _extract_json(text: str) -> str:
        """Tự động bóc phần JSON hợp lệ ra khỏi text trả về"""
        match = re.search(r"\{.*\}", text, re.DOTALL)
        
        return match.group(0) if match else text
    
if __name__ == "__main__":
    parser = QueryParser()
    q = "Cho tôi dữ liệu giá cổ phiếu VCB trong 3 tháng gần nhất, interval 30m, RSI window 14"
    print(parser.parse(q))
    