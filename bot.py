import time
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

# 1. 启动一个极简的网页服务器应付 Render 的端口检测
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")

def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

Thread(target=run_web, daemon=True).start()

# 2. 大人原本的机器人循环逻辑
print("Bot is starting up...")
while True:
    print("Bot is running...")
    time.sleep(10)
