# AGENTS.md — Financial Insight Agent

## Mục tiêu và phạm vi

Đây là repo trợ lý phân tích chứng khoán Việt Nam (FastAPI, LangGraph, Next.js), có dữ liệu thị trường, RAG, eval và các thành phần dự báo. Đọc `README.md` để hiểu sản phẩm. Không tự động cài Vnstock hoặc chạy setup tài khoản khi nhiệm vụ chỉ là sửa code.

Trước mỗi thay đổi:
1. Đọc yêu cầu, `README.md`, phần liên quan của `WORKFLOW_STATE.md` và tài liệu đúng phạm vi trong `docs/`. `WORKFLOW_STATE.md` có lịch sử dài; ưu tiên phần trạng thái mới nhất có liên quan, không coi một kế hoạch cũ là yêu cầu hiện tại.
2. Nêu mục tiêu, phạm vi file/module, điều kiện hoàn thành có thể kiểm tra, các phụ thuộc bên ngoài và giả định cần xác nhận. Làm từng phần nhỏ; không tự mở rộng sang sản phẩm giáo dục hoặc huấn luyện ML nếu nhiệm vụ không yêu cầu.
3. Xem `git status` trước khi sửa, giữ nguyên thay đổi có sẵn của người khác. Khi kết thúc, báo file đã đổi, lệnh đã chạy và kết quả; ghi rõ các kiểm tra chưa chạy, lý do và rủi ro còn lại. Chỉ cập nhật trạng thái bàn giao nếu thực sự có tiến độ mới; không ghi đè lịch sử.

## Bản đồ repo

- `src/application/`: điều phối use case và agent; `src/domain/`: logic nghiệp vụ; `src/infrastructure/`: nhà cung cấp dữ liệu, lưu trữ và tích hợp; `src/interfaces/`: API; `src/shared/`: mã dùng chung.
- `src/tests/unit/`, `integration/`, `e2e/`: kiểm thử theo mức; xem marker và cấu hình trong `pyproject.toml`.
- `evals/`: golden dataset, benchmark, baseline và so sánh regression; đọc `evals/README.md` trước khi thay prompt, tool, RAG, dashboard hoặc đường đi dữ liệu.
- `frontend/`: Next.js; đọc thêm `frontend/AGENTS.md` trước khi sửa UI. `docs/` chứa đặc tả pipeline, RAG, observability và query.
- `.github/workflows/ci.yml`: các bước đang chạy trên CI; `WORKFLOW_STATE.md`: ghi chép tiến độ, không thay thế yêu cầu mới nhất của người dùng.

## Môi trường và khởi động

- CI dùng Python 3.13. Tạo môi trường ảo riêng cho repo (ví dụ `python3.13 -m venv .venv`); cài từ manifest: `python -m pip install -e ".[dev]"`. Lệnh cài cần index Vnstock như `.github/workflows/ci.yml`; chỉ cấu hình index theo hướng dẫn chính thức khi cần, không in URL có credential.
- Frontend: trong `frontend/` chạy `npm ci`, `npm run dev`. Backend và dịch vụ phụ trợ: xem `README.md`, `docker-compose.dev.yml` hoặc `docker-compose.yml` trước khi khởi chạy. Không chạy migration, crawl, benchmark live hay dịch vụ có chi phí chỉ để sửa tài liệu.
- Không ghi API key vào code, URL, log hoặc hội thoại. Dùng biến môi trường / file `.env` bị gitignore và secret của CI. Không nhúng key vào query string của request kiểm tra license.
- Chỉ khi tác vụ **yêu cầu thiết lập Vnstock**: kiểm tra Python và môi trường, cài dependency tương thích với `pyproject.toml`; tham khảo tài liệu Vnstock và yêu cầu người dùng cung cấp key qua kênh an toàn nếu thực sự cần. Không chạy phát hiện tier, đồng bộ skill hay tải dữ liệu sponsor mặc định.

## Xác minh theo loại thay đổi

Chạy test sát phần sửa trước; chọn thêm bước dưới đây phù hợp phạm vi. Không coi một lệnh chưa chạy là đã đạt.

| Thay đổi | Kiểm tra tối thiểu |
|---|---|
| Python backend | `pytest src/tests/unit/ -q`; `ruff check src/`; `black --check src/`. Thêm integration/e2e liên quan khi thay hợp đồng API, DB hay luồng agent. |
| Kiểu dữ liệu Python | `mypy src/ --ignore-missing-imports --no-strict-optional`; hiện job typecheck CI là `continue-on-error`, nên ghi rõ lỗi nếu có. |
| Frontend | Trong `frontend/`: `npm run lint`, `npx tsc --noEmit`, `npm run build`; thử luồng UI liên quan khi có thể. |
| Golden dataset | `python evals/scripts/validate_golden_dataset.py`. |
| Prompt, tool, RAG, dashboard | Chọn smoke/eval tương ứng theo `evals/README.md`; so report với baseline cùng tập case bằng `evals/compare_reports.py`. Ghi rõ dataset, model, mốc dữ liệu, chi phí và các case bỏ qua. |

Benchmark có thể cần API, dịch vụ ngoài hoặc tốn tiền; không chạy `--pin-baseline` để ghi đè chuẩn khi chưa có yêu cầu rõ. Với luồng dự báo, phải định nghĩa target, horizon, thời điểm dữ liệu khả dụng, chia tập theo thời gian, baseline, metric và kiểm tra leakage trước khi tuyên bố cải thiện.

## Hoàn thành và bàn giao

Một tác vụ chỉ hoàn thành khi hành vi đáp ứng tiêu chí đã nêu, test phù hợp chạy đạt và không có regression được phát hiện. Nếu môi trường hoặc dịch vụ ngoài chặn kiểm chứng, ghi trạng thái là **chưa xác minh đầy đủ**, nêu lệnh cần chạy tiếp và không suy diễn rằng thay đổi đã an toàn. Bàn giao ngắn gọn: mục tiêu, thay đổi, bằng chứng (lệnh và kết quả), việc còn mở, trạng thái working tree và bước tiếp theo.
