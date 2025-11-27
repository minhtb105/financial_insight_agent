# Financial Insight Agent

**Financial Insight Agent** là hệ thống AI hỗ trợ phân tích và trả lời tự động các câu hỏi tiếng Việt về chứng khoán Việt Nam, sử dụng LLM (Large Language Model) và dữ liệu thực tế từ các nguồn như TCBS.

---

## Tính năng nổi bật

- **Hiểu tiếng Việt tự nhiên:** Phân tích câu hỏi tiếng Việt về giá cổ phiếu, chỉ báo kỹ thuật (SMA, RSI...), thông tin công ty, so sánh, tổng hợp, v.v.
- **Tích hợp LLM:** Sử dụng mô hình ngôn ngữ lớn (Groq, Llama, v.v.) để chuyển đổi câu hỏi sang schema JSON chuẩn.
- **Kết nối dữ liệu thực:** Lấy dữ liệu chứng khoán từ API TCBS thông qua thư viện `vnstock`.
- **API REST:** Triển khai FastAPI cho phép tích hợp với các hệ thống khác.
- **Agent đa công cụ:** Tự động chọn tool phù hợp để trả lời từng loại truy vấn.

---

## Cấu trúc thư mục

```
src/
│
├── domain/                         # Business logic thuần (models, entities, value objects)
│   ├── entities/
│   │   ├── historical_query.py     # Pydantic models, domain rules
│   │   ├── query_type.py
│   │   ├── interval.py
│   │   └── requested_field.py
│   │
│   ├── services/                   # Logic nghiệp vụ KHÔNG phụ thuộc hạ tầng
│   │   ├── price_service.py        # xử lý price_query
│   │   ├── indicator_service.py    # xử lý sma/rsi/macd
│   │   ├── company_service.py      # xử lý company_query
│   │   ├── compare_service.py      # xử lý comparison_query
│   │   ├── ranking_service.py      # xử lý ranking_query
│   │   └── aggregate_service.py    # xử lý aggregate_query
│   │
│   └── utils/
│       └── date_utils.py           # last N days, tuần, tháng
│
├── application/                    # Lớp điều phối (use cases)
│   ├── handlers/                   
│   │   ├── query_router.py         # route theo QueryType → Service tương ứng
│   │   └── result_formatter.py
│   │
│   └── agent/
│       ├── stock_agent.py          # orchestrator gọi parser + router + service
│       └── tool_registry.py        # đăng ký tools
│
├── infrastructure/                 # External services có thể thay thế
│   ├── api_clients/
│   │   └── vn_stock_client.py      # wrapper của vnstock
│   │
│   ├── llm/
│   │   ├── nlp_parser.py           # gọi LLM → JSON
│   │   └── groq_client.py          # LLM provider
│   │
│   └── cache/
│       └── redis_cache.py          # optional
│
├── interfaces/                     # Entry points (FastAPI, CLI, Webhook)
│   ├── http/
│   │   └── app.py                  # FastAPI server
│   │
│   └── cli/
│       └── console.py              # CLI chạy agent
│
├── tests/  
│   ├── unit/
│   │   ├── test_parser.py
│   │   ├── test_price_service.py
│   │   ├── test_indicator_service.py
│   │   └── test_router.py
│   │
│   ├── integration/
│   │   ├── test_agent_e2e.py
│   │   └── test_api_endpoints.py
│   │
│   └── data/
│       └── test_questions.xlsx
│
└── main.py # entry point cho chạy CLI hoặc server
```

---

## Hướng dẫn cài đặt

1. **Clone dự án:**
```bash
git clone https://github.com/yourusername/financial_insight_agent.git
cd financial_insight_agent
```

2. **Tạo môi trường ảo và cài đặt phụ thuộc:**
```bash
python -m venv .venv
.venv\Scripts\activate       # Windows
source .venv/bin/activate    # macOS/Linux
pip install -r requirements.txt
```

3. **Cấu hình biến môi trường (nếu cần):**
- Tạo file `.env` và điền các thông tin API key, v.v. nếu sử dụng Groq hoặc các dịch vụ khác.

---

## Chạy API server

```bash
cd src
uvicorn server.app:app --reload
```

API sẽ chạy tại `http://localhost:8000` với docs tại `/docs`.

- **Sử dụng:**  
Gửi câu hỏi tiếng Việt về chứng khoán qua API endpoint `/ask` (hoặc endpoint bạn định nghĩa).  
Agent sẽ tự động phân tích, chọn tool phù hợp, truy vấn dữ liệu và trả về kết quả.

---

## Unit Test

Hệ thống có hai bộ test chính để đảm bảo hoạt động chính xác:

### 1. `test_query_parser_datetime.py`

**Mục đích:**  
Kiểm tra parser (`QueryParser`) chuyển đổi chính xác câu hỏi tiếng Việt sang JSON chuẩn.

**Kiểm tra các yếu tố:**
- `intent`: loại truy vấn (`historical_prices`, `technical_indicator`, `company_info`)
- `tickers`: danh sách mã chứng khoán
- `requested_field`: trường dữ liệu yêu cầu (`ohlcv`, `open_price`, `close_price`, `sma`, `rsi`, v.v.)
- Khoảng thời gian `start`/`end` dựa trên số ngày, tuần, tháng
- Các tham số khác: `aggregate`, `compare_with`, `interval`, `window_size`

**Ví dụ test case:**
```python
query = "Lấy dữ liệu OHLCV 10 ngày gần nhất HPG?"
expected = {
    "intent": Intent.historical_prices,
    "tickers": ["HPG"],
    "requested_field": "ohlcv",
    "start": days_ago(10),
    "end": today()
}
parsed_dict = parser.parse(query)
assert parsed_dict["tickers"] == expected["tickers"]
assert parsed_dict["requested_field"] == expected["requested_field"]
```

**Tác dụng:**  
Đảm bảo parser hiểu đúng câu hỏi tiếng Việt và xác định đúng intent, tickers, thời gian, trường dữ liệu và các tham số kỹ thuật.

---

### 2. `test_questions.py`

**Mục đích:**  
Kiểm thử agent end-to-end (`StockAgent`) trên các câu hỏi thực tế từ file Excel:

- Phân tích câu hỏi bằng parser + LLM
- Tự động chọn tool phù hợp
- Truy vấn dữ liệu từ API (`vnstock`, TCBS)
- Trả về câu trả lời chính xác hoặc phù hợp

**Cách hoạt động:**
1. Đọc câu hỏi từ Excel (`AI Intern test questions.xlsx`)
2. Gọi `agent.run(question)` cho từng câu hỏi
3. So sánh output với `expected_answer`
4. Lưu trạng thái test (`passed`/`failed`) cùng kết quả thực tế
5. Xuất kết quả test ra JSON (`test_results.json`)

**Ví dụ logic:**
```python
for _, row in df.iterrows():
    question = str(row["question"])
    expected = str(row["expected_answer"])
    answer = agent.run(question)
    passed = answer == expected
```

**Tác dụng:**  
Đảm bảo agent hoạt động chính xác end-to-end từ nhận diện truy vấn tiếng Việt đến trả kết quả.

---

### Tóm tắt

| File | Kiểm tra | Mục tiêu |
|------|---------|----------|
| `test_query_parser_datetime.py` | Parser | Xác nhận parser trả JSON đúng schema, xác định chính xác `intent`, tickers, trường dữ liệu, thời gian và các tham số liên quan |
| `test_questions.py` | Agent | Đánh giá agent end-to-end, đảm bảo từ câu hỏi đến câu trả lời, kết hợp parser + tool + dữ liệu thực hoạt động chính xác |

---

## Kiểm thử

```bash
cd src
pytest tests/test_query_parser_datetime.py

cd src
python tests/test_questions.py

```

---

## Đóng góp

- Pull request, issue và góp ý luôn được hoan nghênh!
- Đảm bảo code tuân thủ chuẩn PEP8 và có test đi kèm.

