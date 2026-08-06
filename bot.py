import http.server
import json
import os
import random
import threading
import discord
from discord.ext import commands
from google import genai

# ==================== 0. 应对 Render 免费端口要求的轻量 Web 服务 ====================
PORT = int(os.environ.get("PORT", 10000))


class DummyHandler(http.server.BaseHTTPRequestHandler):

  def do_GET(self):
    self.send_response(200)
    self.end_headers()
    self.wfile.write(b"Bot is alive and running!")

  def log_message(self, format, *args):
    pass


def run_web_server():
  server_address = ("", PORT)
  httpd = http.server.HTTPServer(server_address, DummyHandler)
  print(f"【HTTP 守卫】已在端口 {PORT} 启动，专供 Render 扫描。")
  httpd.serve_forever()


web_thread = threading.Thread(target=run_web_server, daemon=True)
web_thread.start()

# ==================== 1. 初始化各项配置 ====================
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
gemini_client = genai.Client()

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 专属惩戒大殿频道名称
PUNISHMENT_ROOM_NAME = "punishment-room"


# ==================== 2. 后台 Gemini 智能审判核心函数（女王大人视角） ====================
async def analyze_and_judge_crime(user_message: str) -> dict:
  prompt = f"""
    你现在是至高无上、执掌无情家法与国法的「女王大人」。
    下方是你的卑微男奴/罪人呈上的一段奏疏/汇报：
    "{user_message}"

    请你以女王的口吻执行以下审判任务：
    1. 【罪名定性】：判断其究竟触犯了「国法」（如公开打卡迟到、考勤疏漏、常规纪律违背）还是「家法」（如深夜起居失律、作息不规律、私密仪态与自我约束违背），或者只是普通的日常觐见。
    2. 【刑罚随机调度】：根据罪行轻重，随机判处对应的杖责（例如杖责三十大板、五十大板）以及黑牢禁闭时间。
    3. 【输出格式要求】：必须严格以纯 JSON 格式返回，不要包含任何 markdown 标记（如 ```json ... ```），格式如下：
    {{
      "category": "国法" 或 "家法",
      "crime_name": "精炼的罪名描述",
      "sentence": "女王大人对罪奴的冷酷训诫与判词",
      "punishment": "具体的刑罚（如：杖责三十大板，禁闭黑牢 15 分钟）"
    }}
    """

  try:
    response = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    text = response.text.strip()
    if text.startswith("```json"):
      text = text[7:]
    if text.endswith("```"):
      text = text[:-3]

    result = json.loads(text.strip())
    return result
  except Exception as e:
    print(f"AI 审判解析异常: {e}")
    return {
        "category": "国法",
        "crime_name": "言行无状，思虑不周",
        "sentence": "奴才好大的胆子，连呈奏都语无伦次，着令拖下去杖责二十！",
        "punishment": "杖责二十大板",
    }


# ==================== 3. Bot 事件监听与审判触发 ====================
@bot.event
async def on_ready():
  print(f"【大周刑部】大总管已就位，恭迎女王大人降临！当前 Bot 身份: {bot.user}")


@bot.event
async def on_message(message):
  if message.author.bot:
    return

  punishment_channel = discord.utils.get(
      message.guild.text_channels, name=PUNISHMENT_ROOM_NAME
  )
  target_channel = punishment_channel if punishment_channel else message.channel

  # 【已移除关键词卡控】只要国民发言，一律送交女王大人审判，彻底根除“失语”现象
  ruling = await analyze_and_judge_crime(message.content)

  category = ruling.get("category", "国法")
  crime_name = ruling.get("crime_name", "日常呈奏")
  sentence = ruling.get("sentence", "准奏，退下吧。")
  punishment = ruling.get("punishment", "免于杖责")

  embed = discord.Embed(
      title=f"⚖️ 【女王御前审判庭】-{category}判罪书",
      description=(
          f"**受刑罪奴**：{message.author.mention}\n**呈上奏疏**：`{message.content}`\n\n-----------------------------------\n"
          f"📜 **律法分类**：`{category}`\n🔍 **查明罪名**：`{crime_name}`\n🏛️ **女王圣裁**：\n> *{sentence}*\n\n⛓️ **执行刑罚**：`{punishment}`"
      ),
      color=0x8B0000,
  )
  embed.set_footer(text="大周内侍省・無光墨牢 —— 罚单已下达，案卷永久存档。")

  await target_channel.send(
      content=f"⚡ 听候法旨！罪奴 {message.author.mention} 呈上奏疏，女王大人当庭裁决：",
      embed=embed,
  )

  await bot.process_commands(message)


# ==================== 4. 启动程序 ====================
if __name__ == "__main__":
  if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
  else:
    print("错误：未找到 DISCORD_TOKEN 环境变量！")
