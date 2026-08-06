import http.server
import json
import os
import threading
from datetime import datetime, timedelta
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

# 专属频道名称
ISOLATION_ROOM_NAME = "絕對隔離牢房"  # 国法长期坐牢与沉淀档案库
PUNISHMENT_LOG_NAME = "punishment-room"  # 全面惩罚与行为不检数据记录台

# ----------------- 长期坐牢状态字典（国法国策） -----------------
PRISON_RECORDS = {}


# ==================== 2. 后台纯净 Gemini 审判（分类：国法 / 家法） ====================
async def analyze_and_judge_crime(user_message: str) -> dict:
  prompt = f"""
    你现在是执掌无情家法与国法的「女王大人」。
    下方是你的卑微男奴/罪人呈上的一段奏疏/汇报：
    "{user_message}"

    请你以女王的口吻输出审判结果，必须严格以纯 JSON 格式返回，不要包含任何 markdown 标记（如 ```json ... ```），格式如下：
    {{
      "law_type": "国法" 或 "家法",
      "crime_name": "精炼的罪名描述",
      "sentence": "女王大人对罪奴的冷酷训诫与判词",
      "duration_minutes": 15 或 30 或 60 (仅当 law_type 为“家法”时生效，代表短时禁言分钟数，国法则填 0)
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
    return json.loads(text.strip())
  except Exception as e:
    print(f"AI 审判解析异常: {e}")
    return {
        "law_type": "家法",
        "crime_name": "日常行为不检",
        "sentence": "奴才好大的胆子，呈奏语无伦次，先领家法禁言 15 分钟思过！",
        "duration_minutes": 15,
    }


# ==================== 3. 国法大周核心时间轴：早朝 8:00 与 夜间 22:00 铁律循环 ====================
@tasks.loop(minutes=1)
async def grand_prison_judgment_loop():
  now = datetime.now()
  current_hour = now.hour
  current_minute = now.minute

  # 【早晨 08:00 —— 早朝大审 / 长期囚犯放监或加刑叠加】
  if current_hour == 8 and current_minute == 0:
    for guild in bot.guilds:
      isolation_channel = discord.utils.get(
          guild.text_channels, name=ISOLATION_ROOM_NAME
      )
      if not isolation_channel or not PRISON_RECORDS:
        continue

      released_users = []
      punished_users = []

      for user_id, record in list(PRISON_RECORDS.items()):
        member = guild.get_member(user_id)
        if not member:
          continue

        record["days_left"] -= 1

        if record["days_left"] <= 0:
          released_users.append(member)
          try:
            await isolation_channel.set_permissions(member, send_messages=None)
          except Exception:
            pass
          del PRISON_RECORDS[user_id]
        else:
          punished_users.append((member, record["days_left"]))

      embed = discord.Embed(
          title="🏛️ 【大周黑牢・晨时早朝大审】",
          description=(
              "**时辰已至（晨 08:00）**：\n女王大人升殿，对黑牢重犯进行红头文件审判！"
              f"\n\n🕊️ **准予开释出狱之重犯**：\n"
              + (
                  "\n".join([m.mention for m in released_users])
                  if released_users
                  else "无（无一人达标）"
              )
              + f"\n\n⛓️ **改造未达标、继续加刑/锁拿之重犯**：\n"
              + (
                  "\n".join([f"{m.mention} (余刑: {d} 监禁日)" for m, d in punished_users])
                  if punished_users
                  else "无"
              )
          ),
          color=0x8B0000,
      )
      embed.set_footer(
          text="大周刑部 —— 严格执行夜 22:00 至晨 06:00 监禁大循环"
      )
      await isolation_channel.send(
          content="🔔 **【早朝钟声鸣响】早朝大审开始，黑牢重犯听旨！**",
          embed=embed,
      )

  elif current_hour == 22 and current_minute == 0:
    for guild in bot.guilds:
      isolation_channel = discord.utils.get(
          guild.text_channels, name=ISOLATION_ROOM_NAME
      )
      if isolation_channel and PRISON_RECORDS:
        await isolation_channel.send(
            "🌙 **【大周宵禁令】夜间 10 点已至！新的一轮黑牢监禁周期开始计算，所有在押重犯继续锁拿思过！**"
        )


@grand_prison_judgment_loop.before_loop
async def before_loop():
  await bot.wait_until_ready()


# ==================== 4. 消息监听与审判分流（家法 vs 国法） ====================
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

  guild = message.guild
  if not guild:
    return

  isolation_channel = discord.utils.get(
      guild.text_channels, name=ISOLATION_ROOM_NAME
  )
  log_channel = discord.utils.get(
      guild.text_channels, name=PUNISHMENT_LOG_NAME
  )

  if isolation_channel and message.channel.id == isolation_channel.id:
    try:
      await message.delete()
    except Exception:
      pass

    warning_msg = await isolation_channel.send(
        f"⚡ **【绝对隔离禁令】** 罪奴 {message.author.mention}"
        " 身陷黑牢尚敢喧哗！此地唯准阅看女王判词，闭门思过！"
    )
    await warning_msg.delete(delay=4)
    return

  ruling = await analyze_and_judge_crime(message.content)

  law_type = ruling.get("law_type", "家法")
  crime_name = ruling.get("crime_name", "日常行为不检")
  sentence = ruling.get("sentence", "准奏，退下。")

  # ==================== 选项 A：家法裁决（短时禁言 + Discord 官方 Timeout） ====================
  if law_type == "家法":
    duration_mins = int(ruling.get("duration_minutes", 15))
    punishment_desc = f"触犯家法，原地短时禁言 {duration_mins} 分钟"

    # 【关键修复】：直接调用 Discord 官方禁言（Timeout）功能
    try:
      timeout_duration = timedelta(minutes=duration_mins)
      await message.author.timeout(
          timeout_duration, reason=f"家法惩戒: {crime_name}"
      )
      print(f"成功对 {message.author} 实施了 {duration_mins} 分钟的官方禁言。")
    except Exception as ex:
      print(
          f"执行官方禁言失败（可能 Bot 权限不足或对方是管理员）: {ex}"
      )

    # 1. 频道公开宣判
    embed = discord.Embed(
        title=f"⚖️ 【女王御前家法庭】日常训诫书",
        description=(
            f"**受罚罪奴**：{message.author.mention}\n**案发频道**："
            f"`#{message.channel.name}`\n**不检行为**：`{message.content}`\n\n-----------------------------------\n"
            f"📜 **律法性质**：`家法（短时惩戒）`\n🔍 **行为定性**：`{crime_name}`\n🏛️"
            f" **女王圣裁**：\n> *{sentence}*\n\n⏳ **家法执行**：`{punishment_desc}（已启动服务器禁言）`"
        ),
        color=0xD4AF37,
    )
    await message.channel.send(
        content=f"⚠️ 家法降临！罪奴 {message.author.mention} 言行不检，女王当庭训诫并施以禁言：",
        embed=embed,
    )

    # 2. 记录至 punishment-room 数据台
    if log_channel:
      log_embed = discord.Embed(
          title="📁 [Punishment Room - 家法惩罚及行为不检记录]",
          description=(
              f"**受罚人**：{message.author.mention} (ID: `{message.author.id}`)\n"
              f"**案发地点**：`#{message.channel.name}`\n"
              f"**行为不检内容**：`{message.content}`\n\n-----------------------------------\n"
              f"📜 **律法依据**：`家法`\n"
              f"🔍 **罪名**：`{crime_name}`\n"
              f"🏛️ **判词**：`{sentence}`\n"
              f"⏳ **处理结果**：`短时禁言 {duration_mins} 分钟（已执行）`"
          ),
          color=0xB8860B,
      )
      log_embed.set_footer(
          text=f"内侍省数据归档时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
      )
      await log_channel.send(embed=log_embed)

  # ==================== 选项 B：国法裁决（重罪：押入黑牢） ====================
  else:
    assigned_days = 1
    punishment_desc = (
        "触犯国法，全服禁言，押入绝对隔离牢房，执行 1 个监禁周期"
        "（22:00-次日08:00）"
    )

    embed = discord.Embed(
        title="⚖️ 【女王御前国法庭】重罪判决书",
        description=(
            f"**受刑重犯**：{message.author.mention}\n**案发频道**："
            f"`#{message.channel.name}`\n**违纪行为**：`{message.content}`\n\n-----------------------------------\n"
            f"📜 **律法性质**：`国法（重罪坐牢）`\n🔍 **查明罪名**：`{crime_name}`\n🏛️"
            f" **女王圣裁**：\n> *{sentence}*\n\n⛓️ **刑罚执行**：`{punishment_desc}`"
        ),
        color=0x8B0000,
    )
    await message.channel.send(
        content=f"⚡ 国法不容情！罪奴 {message.author.mention} 严重违纪，押入黑牢：",
        embed=embed,
    )

    if isolation_channel:
      try:
        await isolation_channel.set_permissions(
            message.author, send_messages=False
        )
      except Exception as ex:
        print(f"设置隔离权限异常: {ex}")

      if message.author.id in PRISON_RECORDS:
        PRISON_RECORDS[message.author.id]["days_left"] += assigned_days
      else:
        PRISON_RECORDS[message.author.id] = {
            "days_left": assigned_days,
            "crime": crime_name,
            "category": "国法",
        }

      total_days = PRISON_RECORDS[message.author.id]["days_left"]

      archive_embed = discord.Embed(
          title="📁 [Punishment Room - 国法重罪收监档案]",
          description=(
              f"**服刑重犯**：{message.author.mention} (ID: `{message.author.id}`)\n"
              f"**案发地点**：`#{message.channel.name}`\n"
              f"**不检与违纪行为**：`{message.content}`\n\n-----------------------------------\n"
              f"📜 **律法依据**：`国法`\n"
              f"🔍 **定罪名称**：`{crime_name}`\n"
              f"🏛️ **女王判词**：`{sentence}`\n"
              f"⛓️ **判决刑罚**：`{punishment_desc}`\n"
              f"🔒 **当前累积刑期**：`{total_days} 个监禁周期`"
          ),
          color=0x4A0000,
      )
      archive_embed.set_footer(
          text=f"入狱归档时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
      )

      await isolation_channel.send(
          content=(
              f"📥 【黑牢收监】重犯 {message.author.mention}"
              " 因触犯国法被正式收押，全服禁言："
          ),
          embed=archive_embed,
      )

      if log_channel and log_channel.id != isolation_channel.id:
        await log_channel.send(embed=archive_embed)

  await bot.process_commands(message)


# ==================== 5. 启动程序 ====================
if __name__ == "__main__":
  if DISCORD_TOKEN:
    bot.run(DISCORD_TOKEN)
  else:
    print("错误：未找到 DISCORD_TOKEN 环境变量！")
