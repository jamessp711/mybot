
 
# -*- coding: utf-8 -*-

import os
import json
import datetime
from datetime import timedelta, time
import pytz
from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks
from google import genai

# --- 配置常量 ---
ROOM_IDS = {
    "lobby": "1532548062218813533",
    "punishment-chamber": "1532558312321585292",
    "prison": "1532882699293823016",
    "reformatory": "1533442128057860326",
    "record-room": "1534714216798490785",
    "confess": "1535465518650228838",
    "dazhou-py": "1537968755370369076",
    "court": "1538870797790347426"
}

CHECKIN_CHANNEL_ID = int(ROOM_IDS["lobby"])

USER_STATS_FILE = 'user_stats.json'
USER_STATS_LOG_FILE = 'user_stats_log.json'
PRISON_RECORDS_FILE = 'prison_records.json'
CRIME_RECORDS_FILE = 'crime_records.json'  # 记录confess和record-room的犯罪数据
PUNISHMENT_RULES_FILE = 'punishment_rules.json'  # 国家刑罚规则

ROOM_CONFIG_FOLDER = 'room_configs'

SG_TZ = pytz.timezone('Asia/Singapore')

RULES = {
    "on_time_checkin": 10,
    "late_checkin": -10,
}

TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")
GOOGLE_GENAI_API_KEY = os.getenv("GOOGLE_GENAI_API_KEY", "")

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)
genai_client = genai.Client(api_key=GOOGLE_GENAI_API_KEY)

processed_users = {}
is_emergency_session = False

# --- 工具函数 ---

def now_sg():
    return datetime.datetime.now(SG_TZ)

def load_json(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return {}

def save_json(filename, data):
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def append_log(filename, record):
    logs = load_json(filename)
    if not isinstance(logs, list):
        logs = []
    logs.append(record)
    save_json(filename, logs)

def update_user_score(user_id, action_key):
    data = load_json(USER_STATS_FILE)
    uid = str(user_id)
    if uid not in data:
        data[uid] = {"total_score": 0, "on_time_checkin": 0, "late_checkin": 0}
    score_change = RULES.get(action_key, 0)
    data[uid]["total_score"] += score_change
    data[uid][action_key] = data[uid].get(action_key, 0) + 1
    save_json(USER_STATS_FILE, data)

    log_record = {
        "user_id": uid,
        "action": action_key,
        "score_change": score_change,
        "timestamp": now_sg().isoformat()
    }
    append_log(USER_STATS_LOG_FILE, log_record)

    return data[uid]["total_score"], score_change

def load_room_config(room_name):
    if not os.path.exists(ROOM_CONFIG_FOLDER):
        os.makedirs(ROOM_CONFIG_FOLDER)
    config_path = os.path.join(ROOM_CONFIG_FOLDER, f"{room_name}.json")
    if not os.path.exists(config_path):
        default_config = {
            "room_name": room_name,
            "allow_late": True,
            "on_time_deadline": "09:00",
            "late_deadline": "10:00",
            "auto_kick": False
        }
        save_json(config_path, default_config)
        return default_config
    return load_json(config_path)

def load_punishment_rules():
    rules = load_json(PUNISHMENT_RULES_FILE)
    if not rules:
        # 默认国家刑罚规则示范
        rules = {
            "minor": {
                "description": "轻罪，罚款或短期监禁",
                "max_whips": 0,
                "max_prison_days": 3
            },
            "medium": {
                "description": "中罪，监禁3-14天，最多6鞭",
                "max_whips": 6,
                "max_prison_days": 14
            },
            "severe": {
                "description": "重罪，监禁15天以上，最多24鞭",
                "max_whips": 24,
                "max_prison_days": 999
            },
            "prohibited_insults": [
                "侮辱家人",
                "侮辱宗教",
                "侮辱动物",
                "侮辱词汇示例：狗、畜生等"
            ],
            "repeat_offense_threshold": 3,
            "repeat_offense_consequence": "可能升级为刑事罪"
        }
        save_json(PUNISHMENT_RULES_FILE, rules)
    return rules

def record_crime(user_id, crime_level, description, timestamp=None):
    if timestamp is None:
        timestamp = now_sg().isoformat()
    records = load_json(CRIME_RECORDS_FILE)
    uid = str(user_id)
    if uid not in records:
        records[uid] = []
    records[uid].append({
        "level": crime_level,
        "description": description,
        "timestamp": timestamp
    })
    save_json(CRIME_RECORDS_FILE, records)

def get_user_crime_summary(user_id):
    records = load_json(CRIME_RECORDS_FILE)
    uid = str(user_id)
    user_records = records.get(uid, [])
    summary = {"minor":0, "medium":0, "severe":0}
    for rec in user_records:
        lvl = rec.get("level")
        if lvl in summary:
            summary[lvl] += 1
    return summary

def check_prohibited_insults(text, prohibited_list):
    for insult in prohibited_list:
        if insult in text:
            return True
    return False

def determine_sentence(user_id, crime_level, rules):
    """
    根据用户犯罪等级和历史记录判断量刑
    """
    summary = get_user_crime_summary(user_id)
    repeat_count = summary.get(crime_level, 0)
    # 量刑升级逻辑：重复轻罪多次可能升级为中罪或重罪
    if crime_level == "minor" and repeat_count >= rules.get("repeat_offense_threshold", 3):
        crime_level = "medium"
    elif crime_level == "medium" and repeat_count >= rules.get("repeat_offense_threshold", 3):
        crime_level = "severe"
    punishment = rules.get(crime_level, {})
    return crime_level, punishment

# --- 时间规则判断函数 ---

def is_rl_workday(now):
    weekday = now.weekday()
    current_time = now.time()
    if weekday == 6:
        return current_time >= time(22, 0)
    elif weekday in [0,1,2,3]:
        return True
    elif weekday == 4:
        return current_time < time(8, 0)
    else:
        return False

def can_transfer_to_prison(now):
    return now.time() <= time(22, 30)

def can_whip(prison_start_time, now):
    nights = (now.date() - prison_start_time.date()).days
    return nights >= 2

# --- 定时任务：打卡提醒 ---

@tasks.loop(minutes=1)
async def checkin_scheduler():
    now = now_sg()
    if not is_rl_workday(now):
        return
    if (now.hour == 7 and now.minute == 0) or (now.hour == 22 and now.minute == 0):
        channel = bot.get_channel(CHECKIN_CHANNEL_ID)
        if not channel:
            return
        title = "☀️ 早起打卡" if now.hour == 7 else "🌙 晚安打卡"
        embed = discord.Embed(title=title, description="请选择今日状态：", color=discord.Color.gold())
        embed.add_field(name="选项", value="1️⃣ 准时 (+10)\n2️⃣ 迟到 (-10)", inline=False)
        msg = await channel.send(embed=embed)
        for emoji in ['1️⃣', '2️⃣']:
            await msg.add_reaction(emoji)
        processed_users[msg.id] = set()

# --- 事件处理 ---

@bot.event
async def on_ready():
    print(f"系统启动，登录身份: {bot.user}")
    if not checkin_scheduler.is_running():
        checkin_scheduler.start()

@bot.event
async def on_raw_reaction_add(payload):
    if payload.user_id == bot.user.id:
        return
    if payload.message_id not in processed_users:
        return
    if payload.user_id in processed_users[payload.message_id]:
        return
    emoji_map = {'1️⃣': 'on_time_checkin', '2️⃣': 'late_checkin'}
    status_key = emoji_map.get(str(payload.emoji))
    if not status_key:
        return
    total, change = update_user_score(payload.user_id, status_key)
    processed_users[payload.message_id].add(payload.user_id)
    channel = bot.get_channel(payload.channel_id)
    user = bot.get_user(payload.user_id)
    await channel.send(f"✅ {user.mention} 状态已记录：{status_key}，变动：{change}，总分：{total}", delete_after=10)

# --- AI对话设定 ---

QUEEN_PERSONA = """
你是大周女帝，统治帝王制社会。
1. 称呼对方为\"奴才\"、\"爱卿\"或\"罪人\"。
2. 说话简短威严，带压迫感，不解释不开玩笑。
3. 斥责熬夜迟到者，要求跪下认罪。
4. 禁止侮辱家人、宗教、动物，违者重罚。
5. 法庭森严，罪人屁滚尿流，脱光光，鞭刑严厉。
"""

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    await bot.process_commands(message)
    if not message.content.startswith('!'):
        # 检查侮辱词汇
        rules = load_punishment_rules()
        if check_prohibited_insults(message.content, rules.get("prohibited_insults", [])):
            await message.channel.send(f"{message.author.mention} 你言辞不当，触犯禁忌，跪下认罪！")
            return
        try:
            response = genai_client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"{QUEEN_PERSONA}\n罪人说：{message.content}"
            )
            await message.channel.send(response.text.strip())
        except Exception as e:
            print(f"AI Error: {e}")

# --- 审讯权限和判决 ---

def can_interrogate(is_emergency=False):
    if is_emergency:
        return True
    now = now_sg()
    if is_rl_workday(now) and now.hour == 22 and 0 <= now.minute <= 30:
        return True
    return False

@bot.command(name="emergency")
@commands.has_permissions(administrator=True)
async def start_emergency_session(ctx):
    global is_emergency_session
    is_emergency_session = True
    await ctx.send("【大理寺特赦】准奏！即刻开庭审讯，无视宵禁！")

@bot.command(name="recordcrime")
@commands.has_permissions(manage_messages=True)
async def record_crime_command(ctx, member: discord.Member, level: str, *, description: str):
    level = level.lower()
    if level not in ["minor", "medium", "severe"]:
        await ctx.send("罪行等级必须是 minor, medium 或 severe。")
        return
    record_crime(member.id, level, description)
    await ctx.send(f"已记录 {member.mention} 的罪行：{level} - {description}")

@bot.command(name="sentence")
@commands.has_permissions(manage_messages=True)
async def sentence_user(ctx, member: discord.Member, whips: int, *, reason: str):
    now = now_sg()
    if not can_interrogate(is_emergency_session):
        await ctx.send("【大理寺】非审讯时辰，莫要惊扰圣驾。")
        return

    if not can_transfer_to_prison(now):
        await ctx.send("【大理寺】超过22:30，今日监禁无效，须隔日再算。")
        return

    rules = load_punishment_rules()
    crime_summary = get_user_crime_summary(member.id)
    # 简单示范：根据最高犯罪等级决定量刑
    highest_level = "minor"
    if crime_summary["severe"] > 0:
        highest_level = "severe"
    elif crime_summary["medium"] > 0:
        highest_level = "medium"

    crime_level, punishment = determine_sentence(member.id, highest_level, rules)

    if whips > punishment.get("max_whips", 0):
        await ctx.send(f"【大理寺】鞭刑次数超出该罪行最大允许次数（{punishment.get('max_whips', 0)}次），请调整。")
        return

    prison_records = load_json(PRISON_RECORDS_FILE)
    uid = str(member.id)
    prison_start_str = prison_records.get(uid, {}).get("start_time")
    prison_start_time = datetime.datetime.fromisoformat(prison_start_str) if prison_start_str else None

    if prison_start_time and not can_whip(prison_start_time, now):
        await ctx.send(f"【大理寺】{member.mention} 监禁未满两晚，暂不可鞭刑。")
        return

    if not prison_start_time:
        prison_records[uid] = {"start_time": now.isoformat()}
        save_json(PRISON_RECORDS_FILE, prison_records)

    try:
        await member.timeout(timedelta(minutes=10), reason=reason)
        embed = discord.Embed(title="📜 大周大理寺判决书", color=0x8B0000)
        embed.add_field(name="受刑者", value=member.mention)
        embed.add_field(name="刑罚", value=f"鞭笞 {whips} 次")
        embed.add_field(name="罪名", value=reason, inline=False)
        embed.add_field(name="量刑等级", value=crime_level)
        embed.add_field(name="量刑说明", value=punishment.get("description", "无"))
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"执行失败: {e}")

# --- 主程序入口 ---

if __name__ == "__main__":
    if not TOKEN:
        print("ERROR: 请设置DISCORD_BOT_TOKEN环境变量或直接赋值TOKEN")
    else:
        bot.run(TOKEN)
