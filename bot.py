import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks
import sys

# 假设你用的google-genai库
from google_genai import Client

# 加载环境变量
load_dotenv()

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
TOKEN_LAST_CHANGED_STR = os.getenv('TOKEN_LAST_CHANGED', '2026-07-10')
TOKEN_VALID_DAYS = 30
GOOGLE_GENAI_API_KEY = os.getenv('GOOGLE_GENAI_API_KEY')

DB_FILE = 'prison_records.json'
PRISON_START_HOUR = 22
PRISON_END_HOUR = 6
YEARS_PER_NIGHT = 2
ROLE_ISOLATION = '绝对隔离牢房'
ROLE_LOG = 'punishmentlog-room'

# Token有效期检查
def check_token_expiry():
    token_last_changed = datetime.strptime(TOKEN_LAST_CHANGED_STR, '%Y-%m-%d')
    today = datetime.now()
    days_used = (today - token_last_changed).days
    if days_used > TOKEN_VALID_DAYS:
        print(f"【安全警告】Token已使用{days_used}天，超过有效期{TOKEN_VALID_DAYS}天！")
        print("强制鞭刑：Bot启动被阻止，请立即更换Token！")
        return False
    else:
        print(f"Token使用天数：{days_used}，仍在有效期内，允许启动Bot。")
        return True

if not check_token_expiry():
    sys.exit(1)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# 初始化google-genai客户端
genai_client = Client(api_key=GOOGLE_GENAI_API_KEY)

def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)

prisoners = load_data()

@bot.event
async def on_ready():
    print(f'帝国监察系统已启动: {bot.user}')
    auto_jail_enforcer.start()

@tasks.loop(minutes=1)
async def auto_jail_enforcer():
    now = datetime.now()
    current_hour = now.hour
    if not bot.guilds:
        return
    guild = bot.guilds[0]
    prison_role = discord.utils.get(guild.roles, name=ROLE_ISOLATION)
    if not prison_role:
        return
    is_curfew = current_hour >= PRISON_START_HOUR or current_hour < PRISON_END_HOUR
    for user_id, data in list(prisoners.items()):
        member = guild.get_member(int(user_id))
        if not member:
            continue
        release_date = datetime.fromisoformat(data['release_date'])
        if now >= release_date:
            await member.remove_roles(prison_role)
            await member.edit(mute=False)
            del prisoners[user_id]
            save_data(prisoners)
            log_channel = discord.utils.get(guild.channels, name=ROLE_LOG)
            if log_channel:
                await log_channel.send(f"【刑满释放】{member.mention} 已服刑完毕，重获自由。")
            continue
        if is_curfew:
            await prison_role.edit(permissions=discord.Permissions(send_messages=False, connect=False))
        else:
            await prison_role.edit(permissions=discord.Permissions(send_messages=True))

@bot.command(name='宣判')
@commands.has_permissions(administrator=True)
async def imprison(ctx, member: discord.Member, years: int):
    nights = years // YEARS_PER_NIGHT
    release_date = datetime.now() + timedelta(days=nights)
    prisoners[str(member.id)] = {
        'name': member.name,
        'release_date': release_date.isoformat(),
        'behavior_score': 0,
        'sentence_years': years
    }
    save_data(prisoners)
    role = discord.utils.get(ctx.guild.roles, name=ROLE_ISOLATION)
    if role:
        await member.add_roles(role)
    embed = discord.Embed(title="帝国大理寺判决书", color=discord.Color.red())
    embed.add_field(name="人犯", value=member.mention)
    embed.add_field(name="刑期", value=f"{years} 年 (折合 {nights} 晚)")
    embed.add_field(name="预计释放时间", value=release_date.strftime("%Y-%m-%d %H:%M"))
    await ctx.send(embed=embed)
    log_channel = discord.utils.get(ctx.guild.channels, name=ROLE_LOG)
    if log_channel:
        await log_channel.send(f"【国法处置】{member.name} 被判处 {years} 年。")

@bot.command(name='审问')
@commands.has_permissions(manage_messages=True)
async def interrogate(ctx, member: discord.Member, change: int):
    uid = str(member.id)
    if uid in prisoners:
        prisoners[uid]['behavior_score'] += change
        score = prisoners[uid]['behavior_score']
        if score >= 20:
            current_release = datetime.fromisoformat(prisoners[uid]['release_date'])
            new_release = current_release - timedelta(days=1)
            prisoners[uid]['release_date'] = new_release.isoformat()
            prisoners[uid]['behavior_score'] = 0
            await ctx.send(f"{member.mention} 表现良好，减刑一晚！")
        save_data(prisoners)
        await ctx.send(f"{member.mention} 当前表现分：{score}")
    else:
        await ctx.send("此人不在牢房中。")

@bot.command(name='打卡')
async def checkin(ctx):
    now = datetime.now()
    if now.hour == 6:
        await ctx.send(f"【早课打卡】{ctx.author.mention} 已晨起改造。请抓紧一小时审问时间供认罪行。")
    else:
        await ctx.send("非打卡时间，勤加改造！")

# 新增智能聊天命令，调用google-genai
@bot.command(name='chat')
async def chat(ctx, *, message: str):
    """用google-genai生成回复"""
    try:
        response = genai_client.generate_text(
            model="chat-bison-001",
            prompt=message,
            temperature=0.7,
            max_tokens=200
        )
        await ctx.send(response.text)
    except Exception as e:
        await ctx.send(f"出错了: {e}")

bot.run(TOKEN)
