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
├── api_clients/       # Kết nối và lấy dữ liệu từ các nguồn chứng khoán (TCBS, vnstock)
│   └── vn_stock_client.py
│
├── data/              # Các hàm xử lý, tính toán chỉ báo, tổng hợp dữ liệu
│   └── indicators.py
│
├── llm_tools/         # Xử lý truy vấn bằng LLM, định nghĩa các tool cho agent
│   ├── nlp_parser.py
│   └── tools.py
│
├── models/            # Định nghĩa schema, intent, các model Pydantic
│   ├── historical_query.py
│   └── intent.py
│
├── server/            # Agent, API server (FastAPI)
│   ├── agent.py
│   └── app.py
│
└── tests/             # Unit test cho parser, tools, agent
    ├── test_query_parser_datetime.py
    └── test_questions.py
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

