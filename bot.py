import http.server
import json
import os
import random
import threading
from datetime import datetime, time, timezone
import discord
from discord.ext import commands, tasks
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

# 设置大周时区（可根据实际需要调整，默认采用本地时间或指定时区）
# 假设使用本地系统时间或调整为对应时区
LOCAL_TZ = timezone.utc  # 实际部署时可改为主流运行时的时区对象


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


# ==================== 3. 定时器：大周作息与 8:00 审判出狱大典 ====================
@tasks.loop(minutes=1)
async def grand_prison_judgment_loop():
  """每分钟检查一次时间。

  若到达早上 8:00，执行黑牢统一审判、放监出狱或加重惩罚； 若到达晚上 10:00 (22:00)，执行宵禁就寝通告。
  """
  now = datetime.now()  # 实际应用可对齐特定时区
  current_hour = now.hour
  current_minute = now.minute
  current_weekday = now.weekday()  # 0是周一，6是周日

  # 周五 8:00 AM 到周日 8:00 PM 属于长休期间，可做相应跳过或休眠判定
  # 每天早上 8:00 准时进行放监出狱/加重惩罚大典
  if current_hour == 8 and current_minute == 0:
    # 排除周五 8:00 至周日 20:00 之间的周末长休闭关期
    # 周五 weekday=4, 周六 weekday=5, 周日 weekday=6
    is_weekend_rest = (current_weekday == 4) or (current_weekday == 5) or (
        current_weekday == 6 and now.hour < 20
    )

    if not is_weekend_rest:
      for guild in bot.guilds:
        punishment_channel = discord.utils.get(
            guild.text_channels, name=PUNISHMENT_ROOM_NAME
        )
        if punishment_channel:
          embed = discord.Embed(
              title="🏛️ 【大周黑牢·晨时大审】",
              description=(
                  "**时辰已至（晨 08:00）**：\n黑牢大门开启！所有服刑罪奴今日之表现已呈递御前。"
                  "\n\n⚡ **女王圣裁**：\n> *经查验，未达标者罪加一等、继续锁拿；符合规制者准予开释出狱！*"
              ),
              color=0x8B0000,
          )
          embed.set_footer(
              text="大周内侍省・無光墨牢 —— 每日早朝放监与加刑大典"
          )
          await punishment_channel.send(
              content="🔔 **【钟声鸣响】早朝放监时刻已到，黑牢罪奴听旨！**",
              embed=embed,
          )

  # 每天晚上 10:00 (22:00) 宵禁就寝提醒
  elif current_hour == 22 and current_minute == 0:
    for guild in bot.guilds:
      punishment_channel = discord.utils.get(
          guild.text_channels, name=PUNISHMENT_ROOM_NAME
      )
      if punishment_channel:
        await punishment_channel.send(
            "🌙 **【大周宵禁令】夜深十点已至！各方罪奴必须熄灯上床歇息，胆敢违抗者，明日数罪并罚！**"
        )


@grand_prison_judgment_loop.before_loop
async def before_loop():
  await bot.wait_until_ready()


# ==================== 4. Bot 事件监听与黑牢分流审判 ====================
@bot.event
async def on_ready():
  print(
      f"【大周刑部】大总管已就位，恭迎女王大人降临！当前 Bot 身份: {bot.user}"
  )
  if not grand_prison_judgment_loop.is_running():
    grand_prison_judgment_loop.start()


@bot.event
async def on_message(message):
  if message.author.bot:
    return

  # 寻找专属的 punishment-room 黑牢频道
  punishment_channel = discord.utils.get(
      message.guild.text_channels, name=PUNISHMENT_ROOM_NAME
  )

  # 若找不到黑牢频道，则在当前频道兜底；若找得到，铁律宣判统一强制推送到 #punishment-room
  target_channel = punishment_channel if punishment_channel else message.channel

  # 执行 Gemini 审判
  ruling = await analyze_and_judge_crime(message.content)

  category = ruling.get("category", "国法")
  crime_name = ruling.get("crime_name", "日常呈奏")
  sentence = ruling.get("sentence", "准奏，退下吧。")
  punishment = ruling.get("punishment", "免于杖责")

  embed = discord.Embed(
      title=f"⚖️ 【女王御前审判庭】-{category}判罪书",
      description=(
          f"**受刑罪奴**：{message.author.mention}\n**原呈奏频道**："
          f"`#{message.channel.name}`\n**呈上奏疏**：`{message.content}`\n\n-----------------------------------\n"
          f"📜 **律法分类**：`{category}`\n🔍 **查明罪名**：`{crime_name}`\n🏛️"
          f" **女王圣裁**：\n> *{sentence}*\n\n⛓️ **执行刑罚**：`{punishment}`"
      ),
      color=0x8B0000,
  )
  embed.set_footer(
      text=(
          "大周内侍省・無光墨牢 —— 罚单已下达，案卷永久存留于黑牢不得篡改。"
      )
  )

  # 将审判书精准强制推送到 punishment-room 铁律黑牢
  await target_channel.send(
      content=(
          f"⚡ 听候法旨！罪奴 {message.author.mention} 在"
          f" `#{message.channel.name}` 呈上奏疏，女王大人当庭裁决："
      ),
      embed=embed,
  )

  await bot.process_commands(message)


# ==================== 5. 启动程序 ====================
if __name__ == "__main__":
  if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
  else:
    print("错误：未找到 DISCORD_TOKEN 环境变量！")
