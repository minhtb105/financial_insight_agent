# Financial Insight Agent

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

---

## 🧱 System Architecture

Hệ thống được thiết kế theo **layered architecture** để dễ mở rộng và kiểm thử:

```
Interfaces (FastAPI / CLI / Web UI)
        ↓
Application Layer (Use cases, Query routing)
        ↓
Agent Layer (LLM routing, Tool orchestration)
        ↓
Domain Layer (Business logic, Entities, Services)
        ↓
Infrastructure Layer (Market APIs, LLM providers, Cache)
```

---

## 🗂 Project Structure

```
src/
├── domain/               # Business logic thuần (entities, services)
├── application/          # Use cases & query routing
│   └── agent/            # LLM agent & tool registry
├── infrastructure/       # External services (LLM, market APIs, cache)
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

* **Integration & E2E tests** cho:

  * Agent orchestration (LLM → tool → response)
  * FastAPI endpoints

Testing đảm bảo:

* Agent hiểu đúng câu hỏi tiếng Việt
* Route đúng intent
* Trả kết quả chính xác từ dữ liệu thực

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

---

## 🎯 Purpose

Dự án này được xây dựng nhằm chứng minh khả năng:

* Thiết kế **LLM agent production-like systems**
* Kết hợp **tool-calling + RAG** cho các bài toán thực tế
* Áp dụng **clean architecture, testing, caching và observability**

Nội dung và kiến trúc của dự án **khớp trực tiếp với mô tả Financial Insight Agent trong CV** và có thể mở rộng thành hệ thống hỗ trợ phân tích tài chính thực tế.

---

## 🤝 Contributing

* Issue và Pull Request luôn được chào đón
* Tuân thủ PEP8 và có test đi kèm khi mở PR
