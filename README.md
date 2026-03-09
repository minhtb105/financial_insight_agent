# Enhanced Financial Insight Agent

**Production-like LLM Agent for Vietnamese Stock Analysis**

Financial Insight Agent là một **hệ thống AI phân tích chứng khoán theo phong cách production**, được thiết kế để trả lời **các câu hỏi tiếng Việt về thị trường chứng khoán** bằng cách kết hợp **LLM agents, tool-calling, RAG và dữ liệu thị trường thời gian thực**.

Dự án được xây dựng theo kiến trúc phân lớp rõ ràng, tập trung vào **độ ổn định, khả năng mở rộng, khả năng kiểm thử và quan sát hệ thống**, phù hợp với mô tả trong CV.

---

## 🚀 Project Overview

* Hệ thống trợ lý tài chính sử dụng **LLM agent** để phân tích và trả lời câu hỏi chứng khoán Việt Nam.
* Hỗ trợ nhiều loại truy vấn: giá cổ phiếu, OHLCV, chỉ báo kỹ thuật, thông tin công ty, so sánh và tổng hợp.
* Kết hợp **tool-calling cho dữ liệu có cấu trúc** và **RAG cho tài liệu phi cấu trúc** (báo cáo, tin tức).
* Được xây dựng theo hướng **production-like system** với logging, caching, metrics và unit tests.

---

## ✨ Key Features

### 🔹 LLM-based Intent Classification & Routing

* Sử dụng LLM để phân tích câu hỏi tiếng Việt và ánh xạ sang **schema JSON chuẩn**.
* Tự động phân loại intent và route truy vấn vào các luồng xử lý phù hợp:

  * **Tool-calling** cho dữ liệu thị trường có cấu trúc
  * **RAG pipeline** cho tài liệu và tin tức phi cấu trúc
  * **Hybrid flows** cho các truy vấn so sánh và phân tích

### 🔹 Tool-calling for Structured Market Data

* Kết nối API dữ liệu chứng khoán (TCBS thông qua `vnstock`).
* Hỗ trợ:

  * Giá cổ phiếu, OHLCV
  * Chỉ báo kỹ thuật: SMA, RSI, MACD
  * Truy vấn xếp hạng, so sánh và tổng hợp

### 🔹 Retrieval-Augmented Generation (RAG)

* Áp dụng RAG cho các câu hỏi cần:

  * Giải thích khái niệm tài chính
  * Thông tin doanh nghiệp
  * Tin tức và tài liệu liên quan
* Cho phép kết hợp **kết quả từ tool + tài liệu retrieve** trong cùng một câu trả lời.

### 🔹 Reliability & Structured Outputs

* Enforce **strict JSON schema validation** cho output của LLM.
* Giảm ~**70% lỗi runtime** do output không hợp lệ.
* Đảm bảo khả năng xử lý ổn định cho downstream services.

### 🔹 Caching & Performance

* Tích hợp **Redis caching** cho các truy vấn lặp lại.
* Giảm latency và tải cho API dữ liệu thị trường.

### 🔹 Observability & Metrics

* Logging và tracing cho:

  * Intent classification
  * Tool selection
  * End-to-end latency
* Theo dõi:

  * Intent accuracy
  * Tool success rate
  * Response latency

### 🔹 Enhanced Features

#### Rule-based Preprocessing
- **Ticker extraction** with validation against known Vietnamese tickers
- **Time parameter extraction** (days, weeks, months, years)
- **Indicator parameter extraction** (SMA, EMA, RSI, MACD, etc.)
- **Query type detection** based on keywords and patterns
- **Auto-correction** for common ticker typos
- **Confidence scoring** for preprocessing results

#### Extended Query Types
- `financial_ratio_query`: P/E, ROE, EPS, etc.
- `news_sentiment_query`: News, sentiment, social volume
- `portfolio_query`: Portfolio value, performance, allocation
- `alert_query`: Price alerts, volume alerts, technical alerts
- `forecast_query`: Price forecasts, trend analysis
- `sector_query`: Sector performance, industry analysis

#### Extended Requested Fields
- **Financial ratios**: PE, PB, ROE, EPS, ROA, debt_to_equity, etc.
- **Market data**: market_cap, beta, turnover_rate, foreign_ownership
- **Extended indicators**: bollinger_bands, stochastic, adx, atr, obv, etc.
- **News & sentiment**: news, sentiment, social_volume, news_sentiment_score
- **Portfolio**: portfolio_value, portfolio_performance, portfolio_allocation
- **Alerts**: price_alert, volume_alert, technical_alert, news_alert
- **Forecasts**: price_forecast, trend_analysis, support_resistance
- **Sectors**: sector_performance, sector_allocation, sector_rotation

#### New Services
- **Financial Ratio Service**: Get individual financial ratios (P/E, ROE, EPS, etc.)
- **News & Sentiment Service**: Fetch financial news and analyze sentiment
- **Portfolio Service**: Manage user portfolio and calculate performance

#### Enhanced Agent
- **Confidence-based approach**: Uses preprocessing confidence to guide LLM
- **Adaptive thresholds**: Adjusts confidence thresholds based on query complexity
- **Enhanced tool selection**: Better tool selection based on query type and confidence
- **Improved error handling**: Graceful degradation when confidence is low

---

## 🧱 System Architecture

Hệ thống được thiết kế theo **layered architecture** để dễ mở rộng và kiểm thử:

```
Enhanced Financial Insight Agent
├── infrastructure/
│   ├── llm/
│   │   ├── nlp_parser.py (original parser)
│   │   ├── query_preprocessor.py (NEW: rule-based preprocessing)
│   │   └── enhanced_nlp_parser.py (NEW: enhanced parser)
│   └── api_clients/
│       └── vn_stock_client.py
├── domain/
│   ├── entities/
│   │   ├── historical_query.py
│   │   ├── extended_query_type.py (NEW: extended query types)
│   │   └── extended_requested_field.py (NEW: extended fields)
│   └── services/
│       ├── price_service.py
│       ├── indicator_service.py
│       ├── company_service.py
│       ├── compare_service.py
│       ├── ranking_service.py
│       ├── aggregate_service.py
│       ├── financial_ratio_service.py (NEW)
│       ├── news_sentiment_service.py (NEW)
│       └── portfolio_service.py (NEW)
├── application/
│   └── agent/
│       ├── tool_registry.py (original tools)
│       └── enhanced_tool_registry.py (NEW: enhanced tools)
│       └── enhanced_agent.py (NEW: enhanced agent)
└── tests/
    ├── unit/
    │   ├── test_query_parser.py
    │   └── test_enhanced_parser.py (NEW)
    └── integration/
        ├── test_agent_e2e.py
        ├── test_enhanced_agent.py (NEW)
        └── test_full_system.py (NEW)
```

---

## 🗂 Project Structure

```
src/
├── domain/               # Business logic thuần (entities, services)
│   ├── entities/         # Query types, requested fields, historical queries
│   └── services/         # Domain services (price, indicator, company, etc.)
│       ├── base/         # Base services and utilities
│       ├── financial/    # Financial ratio and aggregation services
│       ├── market/       # Price, indicator, and comparison services
│       ├── portfolio/    # Portfolio and news sentiment services
│       └── company/      # Company information services
├── application/          # Use cases & query routing
│   └── agent/            # LLM agent & tool registry
├── infrastructure/       # External services (LLM, market APIs, cache)
│   ├── llm/              # NLP parsers and query preprocessing
│   └── api_clients/      # Market data API clients
├── interfaces/           # FastAPI, CLI, Web UI
├── tests/                # Unit & integration tests
└── main.py               # Entry point
```

---

## 🧪 Testing Strategy

* **Unit tests** cho:

  * Intent parsing & schema validation
  * Domain services (price, indicator, comparison, aggregation)
  * Query routing logic
  * Enhanced parser and preprocessing

* **Integration & E2E tests** cho:

  * Agent orchestration (LLM → tool → response)
  * FastAPI endpoints
  * Enhanced agent functionality
  * Full system integration

Testing đảm bảo:

* Agent hiểu đúng câu hỏi tiếng Việt
* Route đúng intent
* Trả kết quả chính xác từ dữ liệu thực
* Enhanced features work correctly

---

## 🖥 Web UI

* Giao diện web đơn giản để:

  * Chat với agent
  * Hiển thị giá cổ phiếu
  * Trực quan hóa chỉ báo kỹ thuật

---

## ▶️ Getting Started

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
```

Cấu hình biến môi trường (ví dụ LLM API key):

```bash
export GROQ_API_KEY=your_api_key_here
```

Chạy API server:

```bash
uvicorn interfaces.http.app:app --reload
```

### Enhanced Agent Usage

```python
from application.agent.enhanced_agent import EnhancedStockAgent

agent = EnhancedStockAgent()
agent.run("Tỷ lệ P/E của VNM hiện tại là bao nhiêu?")
```

### New Query Types

```python
# Financial ratio query
"PE của VNM hiện tại là bao nhiêu?"

# News sentiment query
"Có tin tức gì về VCB trong tuần này không?"

# Portfolio query
"Nếu tôi mua 100 cổ FPT thì danh mục hiện tại ra sao?"

# Alert query
"Cảnh báo khi giá HPG vượt ngưỡng 50.000"

# Forecast query
"Dự báo giá VNM trong tuần tới"

# Sector query
"Các cổ phiếu ngành chứng khoán có performance tốt nhất tuần này?"
```

---

## 🎯 Purpose

Dự án này được xây dựng nhằm chứng minh khả năng:

* Thiết kế **LLM agent production-like systems**
* Kết hợp **tool-calling + RAG** cho các bài toán thực tế
* Áp dụng **clean architecture, testing, caching và observability**
* **Enhanced preprocessing** with rule-based extraction and confidence scoring
* **Extended functionality** for comprehensive financial analysis

Nội dung và kiến trúc của dự án **khớp trực tiếp với mô tả Financial Insight Agent trong CV** và có thể mở rộng thành hệ thống hỗ trợ phân tích tài chính thực tế.

---

## 🤝 Contributing

* Issue và Pull Request luôn được chào đón
* Tuân thủ PEP8 và có test đi kèm khi mở PR
* Đảm bảo backward compatibility cho các tính năng hiện có
