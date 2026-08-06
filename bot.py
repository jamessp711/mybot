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

# 专属绝对隔离牢房频道名称
ISOLATION_ROOM_NAME = "绝对隔离牢房"


# ==================== 2. 后台 Gemini 智能审判核心函数 ====================
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
  now = datetime.now()
  current_hour = now.hour
  current_minute = now.minute
  current_weekday = now.weekday()

  # 每天早上 8:00 准时进行放监出狱/解除隔离大典
  if current_hour == 8 and current_minute == 0:
    is_weekend_rest = (current_weekday == 4) or (current_weekday == 5) or (
        current_weekday == 6 and now.hour < 20
    )

    if not is_weekend_rest:
      for guild in bot.guilds:
        isolation_channel = discord.utils.get(
            guild.text_channels, name=ISOLATION_ROOM_NAME
        )
        if isolation_channel:
          embed = discord.Embed(
              title="🏛️ 【大周黑牢·晨时大审】",
              description=(
                  "**时辰已至（晨 08:00）**：\n绝对隔离牢房大门开启！今日刑满之罪奴可恢复自由。"
                  "\n\n⚡ **女王圣裁**：\n> *经查验，未达标者继续锁拿禁言；合规者准予开释出狱！*"
              ),
              color=0x8B0000,
          )
          embed.set_footer( text="大周内侍省・絕對隔离牢房 —— 每日早朝放监与解禁大典")
          await isolation_channel.send(
              content="🔔 **【钟声鸣响】早朝放监时刻已到，隔离牢房罪奴听旨！**",
              embed=embed,
          )

  # 每天晚上 10:00 (22:00) 宵禁就寝提醒
  elif current_hour == 22 and current_minute == 0:
    for guild in bot.guilds:
      isolation_channel = discord.utils.get(
          guild.text_channels, name=ISOLATION_ROOM_NAME
      )
      if isolation_channel:
        await isolation_channel.send(
            "🌙 **【大周宵禁令】夜深十点已至！各方罪奴必须熄灯上床歇息！**"
        )


@grand_prison_judgment_loop.before_loop
async def before_loop():
  await bot.wait_until_ready()


# ==================== 4. Bot 事件监听与完美隔离分流 ====================
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

  isolation_channel = discord.utils.get(
      message.guild.text_channels, name=ISOLATION_ROOM_NAME
  )

  # 【绝对隔离权限控制】：如果罪奴胆敢在 #绝对隔离牢房 里面发言说话，直接予以静音拦截，并警告其此地只许看判词
  if isolation_channel and message.channel.id == isolation_channel.id:
    # 瞬间剥夺其在隔离室的发言权限（禁言）
    try:
      await isolation_channel.set_permissions(message.author, send_messages=False)
    except Exception as ex:
      print(f"权限调整异常: {ex}")

    # 删除其违规发言，维护黑牢纯净
    try:
      await message.delete()
    except Exception as ex:
      print(f"清理违规发言异常: {ex}")

    # 仅降下警告，不进行二次AI审判，保持黑牢纯净
    warning_msg = await isolation_channel.send(
        f"⚡ **【绝对隔离禁令】** 罪奴 {message.author.mention} 敢在黑牢喧哗！此地唯准阅看女王判词，已将你**就地禁言**，闭门思过！"
    )
    # 5秒后自动擦除警告提示，保持黑牢绝对干净整洁
    await warning_msg.delete(delay=5)
    return

  # ==================== 正常日常频道（如 #general）的互动与存档 ====================
  ruling = await analyze_and_judge_crime(message.content)

  category = ruling.get("category", "国法")
  crime_name = ruling.get("crime_name", "日常呈奏")
  sentence = ruling.get("sentence", "准奏，退下吧。")
  punishment = ruling.get("punishment", "免于杖责")

  # 1. 在当前聊天室实时互动宣判
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
  embed.set_footer(text="大周内侍省 —— 罚单已下达，案卷已同步移送绝对隔离牢房。")

  await message.channel.send(
      content=f"⚡ 听候法旨！罪奴 {message.author.mention} 呈上奏疏，女王大人当庭裁决：",
      embed=embed,
  )

  # 2. 【绝对隔离牢房归档与禁言惩戒】：将罪状抄送至 #绝对隔离牢房，并自动将该罪奴在隔离牢房中设为禁言
  if isolation_channel:
    try:
      # 强制设置该罪奴在隔离牢房中无权发言（只能看判词）
      await isolation_channel.set_permissions(message.author, send_messages=False)
    except Exception as ex:
      print(f"设置隔离权限异常: {ex}")

    archive_embed = discord.Embed(
        title=f"📁 【绝对隔离档案】-{category}罪状记录",
        description=(
            f"**服刑罪奴**：{message.author.mention}\n**案发频道**："
            f"`#{message.channel.name}`\n**呈奏内容**：`{message.content}`\n\n-----------------------------------\n"
            f"📜 **律法分类**：`{category}`\n🔍 **定罪名称**：`{crime_name}`\n🏛️"
            f" **女王判词**：\n> *{sentence}*\n\n⛓️ **判决刑罚**：`{punishment}`\n🔒"
            " **状态**：`已押入绝对隔离牢房，剥夺发言权`"
        ),
        color=0x4A0000,
    )
    archive_embed.set_footer(text=f"入狱归档时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    await isolation_channel.send(content=f"📥 【黑牢收监】罪奴 {message.author.mention} 因触犯律法已被押入隔离牢房：", embed=archive_embed)

  await bot.process_commands(message)


# ==================== 5. 启动程序 ====================
if __name__ == "__main__":
  if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
  else:
    print("错误：未找到 DISCORD_TOKEN 环境变量！")
