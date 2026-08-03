import os
import discord
from discord.ext import commands
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Thread

# 1. 启动一个极简的网页服务器应付 Render 的端口检测
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Big Zhou Discord Bot is alive!")

def run_web():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# 在后台线程启动网页服务
Thread(target=run_web, daemon=True).start()

# 2. 配置 Discord 机器人
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"大周帝国 Discord 机器人已成功登录！当前账号：{bot.user}")

@bot.command(name="ping")
async def ping(ctx):
    await ctx.send("大周帝国万岁！臣在！")

# 3. 运行机器人（请把 Token 换成大人自己的 Discord Bot Token，或者用环境变量）
TOKEN = os.environ.get("DISCORD_TOKEN", "填入大人的Discord_Bot_Token")

if __name__ == "__main__":
    bot.run(TOKEN)
