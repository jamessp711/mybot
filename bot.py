import os
import asyncio
from datetime import datetime, time
import discord
from discord.ext import commands, tasks
from aiohttp import web

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================================
# 【大周赛博刑部：双轨制案卷与黑牢托管系统】
# ==========================================
ACTIVE_BLACK_PRISON_SESSIONS = globals().get("ACTIVE_BLACK_PRISON_SESSIONS", {})
OFFICIAL_ARCHIVES = globals().get("OFFICIAL_ARCHIVES", [])  # 全局历史档案
USER_CRIME_RECORDS = globals().get("USER_CRIME_RECORDS", {})  # 个人专属判罪档案库

PUNISHMENT_ROOM_NAME = "punishment-room"

def is_grand_court_open():
    now_time = datetime.now().time()
    return time(6, 0) <= now_time <= time(8, 0)

def is_black_prison_time():
    now_time = datetime.now().time()
    return now_time >= time(22, 0) or now_time < time(6, 0)

@tasks.loop(minutes=5)
async def check_curfew_online_violation():
    if not is_black_prison_time():
        return
    for user_id, session in ACTIVE_BLACK_PRISON_SESSIONS.items():
        session["online_violation_count"] += 1

async def get_punishment_channel(guild):
    """自动寻找名为 punishment-room 的专属刑罚大殿"""
    for channel in guild.text_channels:
        if channel.name == PUNISHMENT_ROOM_NAME:
            return channel
    return None

# ==========================================
# 【核心指令：颁布判罪书、跪看个人档案、领板子】
# ==========================================

@bot.command(name="issue_warrant")
@commands.has_permissions(administrator=True)
async def issue_warrant(ctx, member: discord.Member, days: int, *, crime_reason: str):
    """女王专用：下发正式《大周御前正式判罪书》并打入黑牢"""
    user_id = member.id
    
    # 记录黑牢刑期
    ACTIVE_BLACK_PRISON_SESSIONS[user_id] = {
        "reason": crime_reason,
        "total_days": days,
        "current_day": 1,
        "daily_lashes": 30,
        "online_violation_count": 0
    }
    
    # 格式化正式判罪书
    warrant_text = (
        f"📜 **【大周御前正式判罪书】**\n"
        f"* **案号**：大周刑字〔{datetime.now().strftime('%Y-%m%d')}〕第 0806 号\n"
        f"* **涉案国民**：{member.mention}\n"
        f"* **触犯铁律**：违反《大周国家登记法令》与宵禁条例 ({crime_reason})\n"
        f"* **御前判决**：数罪并罚，判处黑牢收监 **{days} 天**。每日必须在早晨升堂时受领私密家法 **30 大板**（杖责至屁股开花以惩效尤）。\n"
        f"* —— *大周女王 御前钦此*"
    )
    
    # 存入个人档案库（供罪人随时跪看）
    if user_id not in USER_CRIME_RECORDS:
        USER_CRIME_RECORDS[user_id] = []
    USER_CRIME_RECORDS[user_id].append(warrant_text)
    OFFICIAL_ARCHIVES.append(f"【正式判罪】{member.name} 触犯国法，判监 {days} 天。")

    # 投递至 punishment-room
    p_channel = await get_punishment_channel(ctx.guild)
    target_channel = p_channel if p_channel else ctx.channel
    await target_channel.send(warrant_text)
    if target_channel != ctx.channel:
        await ctx.send(f"⚡ 判罪书已正式下发至 #{PUNISHMENT_ROOM_NAME} 刑罚大殿！")

@bot.command(name="my_crimes")
async def my_crimes(ctx):
    """罪人随时跪看自己的国家与家法判刑记录"""
    user_id = ctx.author.id
    if user_id not in USER_CRIME_RECORDS or not USER_CRIME_RECORDS[user_id]:
        await ctx.send(f"⚖️ 【大周档案局】回禀 {ctx.author.mention}，你目前案底清白，未有国法判罪书记录。")
        return
        
    records = "\n\n".join(USER_CRIME_RECORDS[user_id])
    await ctx.send(f"跪下！以下是你的 **【个人国法与家法判刑全记录】**，一目了然：\n\n{records}")


# ==========================================
# 【事件监听与审讯系统】
# ==========================================
@bot.event
async def on_ready():
    print(f"大周刑部大总管 {bot.user} 已登基！当前黑牢在押：{len(ACTIVE_BLACK_PRISON_SESSIONS)}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content
    now_str = datetime.now().strftime("%H:%M")
    user_id = message.author.id
    is_in_punishment_room = (message.channel.name == PUNISHMENT_ROOM_NAME)

    # 1. 凡走过必留痕
    OFFICIAL_ARCHIVES.append(f"[{now_str}] {message.author.name} 在 #{message.channel.name} 留痕：{content}")

    # 2. 罪人每日领板子（如：领取第二天的三十大板）
    if "领取" in content or "领板子" in content or "三十大板" in content:
        if user_id in ACTIVE_BLACK_PRISON_SESSIONS:
            session = ACTIVE_BLACK_PRISON_SESSIONS[user_id]
            reply = (
                f"⚖️ 【大周女王】准奏！犯人 {message.author.mention} 正在服刑第 {session['current_day']}/{session['total_days']} 天。\n"
                f"今日之 **{session['daily_lashes']} 大板** 刑罚执行完毕，家规私刑已生效，屁股开花以儆效尤！\n"
                f"继续回黑牢反省，明日请早起续领！"
            )
            session['current_day'] += 1
            if session['current_day'] > session['total_days']:
                reply += f"\n🎉 恭喜犯人刑满释放！黑牢档案已解除。"
                del ACTIVE_BLACK_PRISON_SESSIONS[user_id]
            
            await message.channel.send(reply)
            return

    # 3. 身份证打卡或常规交互
    if "早安" in content or "打卡" in content:
        reply_msg = f"⚖️ 【大周女王】国民 {message.author.mention} 身份证打卡成功（留痕时间 {now_str}）。"
        if is_in_punishment_room:
            reply_msg += "（身处惩戒室，望尔时刻反省自身罪责！）"
        await message.channel.send(reply_msg)

    elif "半夜" in content or "忘记打卡" in content:
        reply_msg = (
            f"⚖️ 【大周女王】好大胆子！竟敢在 #{message.channel.name} 呈奏「{content}」。"
            f"未带身份证且深夜逗留，当心女王的《御前正式判罪书》直接将你收监！"
        )
        await message.channel.send(reply_msg)

    await bot.process_commands(message)

# ==========================================
# 异步 Web 保活与主程序
# ==========================================
async def 管道响应(request):
    return web.Response(text="The Supreme Queen's Court and Punishment Room are active.")

async def 主程序():
    app = web.Application()
    app.router.add_get('/', 管道响应)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    async with bot:
        if not check_curfew_online_violation.is_running():
            check_curfew_online_violation.start()
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token:
        asyncio.run(Main()) if 'Main' in locals() else asyncio.run(主程序())
