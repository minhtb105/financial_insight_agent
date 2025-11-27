from fastapi import FastAPI
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from server.agent import StockAgent  


agent = StockAgent()
app = FastAPI(
    title="LLM Stock Agent API",
    description="REST API cho Agent phân tích câu hỏi chứng khoán tiếng Việt.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

class QueryResponse(BaseModel):
    answer: str
# ───────────────────────────────────────────────
# API endpoint chính: /ask
# ───────────────────────────────────────────────
@app.post("/ask", response_model=QueryResponse)
async def ask_stock_agent(body: QueryRequest):
    """
    Nhận câu hỏi tiếng Việt -> Agent phân tích -> trả câu trả lời.
    Trả về JSON: {"answer": "..."}
    """
    question = body.query.strip()

    if not question:
        return QueryResponse(answer="Câu hỏi rỗng.")

    try:
        response_text = agent.run(question)
        return QueryResponse(answer=response_text)

    except Exception as e:
        return QueryResponse(answer=f"Lỗi xử lý: {e}")


# ───────────────────────────────────────────────
# Ping test
# ───────────────────────────────────────────────
@app.get("/ping")
async def ping():
    return {"status": "ok"}
