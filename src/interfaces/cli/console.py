import sys
import json
from application.agent.agent import StockAgent


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
    def __init__(self, raw_output: bool = False):
        self.agent = StockAgent()
        self.raw_output = raw_output

    def toggle_raw(self):
        self.raw_output = not self.raw_output
        print(f"[DEBUG] Raw JSON mode = {self.raw_output}")

    def print_json(self, data):
        print(json.dumps(data, indent=2, ensure_ascii=False))

    def clear_screen(self):
        print("\033c", end="")  # ANSI clear screen

    def handle_command(self, cmd: str):
        """Xử lý các lệnh đặc biệt bắt đầu bằng '/'"""
        if cmd == "/exit":
            print("Bye!")
            sys.exit(0)

        elif cmd == "/clear":
            self.clear_screen()

        elif cmd == "/help":
            print(HELP_TEXT)

        elif cmd == "/raw":
            self.toggle_raw()

        else:
            print(f"⚠️  Unknown command: {cmd}")

    def run(self):
        print(BANNER)

        while True:
            try:
                query = input("❯ ").strip()

                # Bỏ qua input rỗng
                if not query:
                    continue

                # Command mode
                if query.startswith("/"):
                    self.handle_command(query)
                    continue

                # Normal question → agent xử lý
                response = self.agent.run(query)

                if self.raw_output:
                    self.print_json(response)
                else:
                    print("\n📊 Kết quả:")
                    self.print_json(response)

            except KeyboardInterrupt:
                print("\nBye!")
                break
            except Exception as e:
                print(f"🔥 Error: {str(e)}")


def main():
    app = ConsoleApp()
    app.run()


if __name__ == "__main__":
    main()
