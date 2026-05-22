import sys
import os
import json
import uuid
import argparse
import concurrent.futures

from application.agents.agent import StockAgent
from infrastructure.observability import init_observability, get_logger
from infrastructure.observability.logging.logger import request_id_var
from infrastructure.guardrails.pipeline import GuardrailPipeline

BANNER = r"""
====================================================
      Financial Insight Agent - CLI Interface
====================================================
 Nhập câu hỏi tiếng Việt về chứng khoán:
   • "Lấy giá đóng của VCB hôm qua"
   • "Tính SMA9 của HPG trong 2 tuần"
   • "So sánh volume của VIC và HPG tuần này"
   • "/help" để xem hướng dẫn
====================================================
"""


HELP_TEXT = """
Các lệnh hỗ trợ:
  /exit         → Thoát chương trình
  /clear        → Xóa màn hình
  /raw          → Bật/tắt chế độ hiển thị raw JSON
  /help         → Hiển thị hướng dẫn

Ví dụ câu hỏi:
  • Lấy giá mở cửa của VCB hôm qua
  • Lấy dữ liệu OHLCV 10 ngày gần nhất của HPG
  • Tính SMA9 và SMA20 của VIC trong 1 tháng
  • So sánh volume của VIC với HPG trong 2 tuần
"""


class ConsoleApp:
    def __init__(self, raw_output: bool = False) -> None:
        self.agent = None
        self.guardrail_pipeline = None
        self._executor = None
        try:
            self.agent = StockAgent()
        except Exception as e:
            print(f"Failed to initialize agent: {e}")
            print("   Check your API keys and network connection.")
            return
        try:
            self.guardrail_pipeline = GuardrailPipeline()
        except Exception:
            self.guardrail_pipeline = None
        self.raw_output = raw_output
        self.cli_logger = get_logger("cli")
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

    @staticmethod
    def _run_agent(agent, query: str, request_id: str) -> str:
        return agent.run(query, request_id)

    def close(self):
        if self._executor is not None:
            self._executor.shutdown(wait=False)

    def toggle_raw(self):
        self.raw_output = not self.raw_output
        print(f"[DEBUG] Raw JSON mode = {self.raw_output}")

    def print_json(self, data):
        print(json.dumps(data, indent=2, ensure_ascii=False))

    def clear_screen(self):
        os.system("cls" if os.name == "nt" else "clear")

    def handle_command(self, cmd: str):
        """Xử lý các lệnh đặc biệt bắt đầu bằng '/'"""
        if cmd == "/exit":
            print("Bye!")
            raise SystemExit(0)

        elif cmd == "/clear":
            self.clear_screen()

        elif cmd == "/help":
            print(HELP_TEXT)

        elif cmd == "/raw":
            self.toggle_raw()

        else:
            print(f"⚠️  Unknown command: {cmd}")

    def run(self):
        if self.agent is None:
            print("Agent not initialized. Exiting.")
            return
        try:
            print(BANNER)

            while True:
                try:
                    query = input("> ").strip()

                    if not query:
                        continue

                    if query.startswith("/"):
                        self.handle_command(query)
                        continue

                    request_id = str(uuid.uuid4())
                    request_id_var.set(request_id)

                    if self.guardrail_pipeline:
                        result = self.guardrail_pipeline.check(query, "127.0.0.1")
                        if not result.passed:
                            self.cli_logger.warning(
                                "Guardrail blocked CLI query",
                                extra={"query": query, "reason": result.reason, "request_id": request_id},
                            )
                            print(
                                "⚠️  Yêu cầu của bạn không thể xử lý. Vui lòng thử lại với câu hỏi khác."
                            )
                            continue

                    self.cli_logger.info(
                        "Processing CLI query", extra={"query": query, "request_id": request_id}
                    )
                    try:
                        fut = self._executor.submit(self._run_agent, self.agent, query, request_id)
                        response = fut.result(timeout=120)
                    except concurrent.futures.TimeoutError:
                        self.cli_logger.error("Agent run timed out", extra={"request_id": request_id})
                        print("🔥 Yêu cầu xử lý quá lâu. Vui lòng thử lại với câu hỏi đơn giản hơn.")
                        continue
                    except Exception as e:
                        self.cli_logger.exception("Agent run failed", extra={"request_id": request_id})
                        print(f"🔥 Lỗi xử lý: {e!s}")
                        continue

                    if self.raw_output:
                        try:
                            parsed = json.loads(response) if isinstance(response, str) else response
                            self.print_json(parsed)
                        except (json.JSONDecodeError, ValueError):
                            self.print_json(response)
                    else:
                        print(f"\n📊 Kết quả:\n\n{response}\n")

                except SystemExit:
                    break
                except EOFError:
                    print("\nBye!")
                    break
                except KeyboardInterrupt:
                    print("\nBye!")
                    break
                except Exception as e:
                    print(f"🔥 Error: {e!s}")
        finally:
            self.close()


def main():
    parser = argparse.ArgumentParser(description="Financial Insight Agent CLI")
    parser.add_argument("--raw", action="store_true", help="Raw JSON output mode")
    parser.add_argument("--query", "-q", type=str, help="Single query to run (non-interactive)")
    args = parser.parse_args()

    init_observability()
    from infrastructure.dependencies import init_deps
    init_deps()
    app = ConsoleApp(raw_output=args.raw)

    if args.query:
        if app.agent is None:
            print("❌ Agent not initialized. Check your API keys and network connection.")
            sys.exit(1)
        if app.guardrail_pipeline:
            result = app.guardrail_pipeline.check(args.query, "127.0.0.1")
            if not result.passed:
                print("⚠️  Yêu cầu của bạn không thể xử lý. Vui lòng thử lại với câu hỏi khác.")
                sys.exit(1)
        request_id = str(uuid.uuid4())

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(ConsoleApp._run_agent, app.agent, args.query, request_id)
            response = fut.result(timeout=120)
        if isinstance(response, str):
            try:
                parsed = json.loads(response)
                app.print_json(parsed)
            except (json.JSONDecodeError, ValueError):
                print(response)
        else:
            app.print_json(response)
    else:
        app.run()


if __name__ == "__main__":
    main()
