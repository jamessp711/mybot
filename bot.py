import os
import asyncio
from datetime import datetime, time
import discord
from discord.ext import commands, tasks
from aiohttp import web

# 初始化 Bot 
intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

# ==========================================
# 【大周新政：凡走过必留痕与案卷审讯核心模块】
# ==========================================

ACTIVE_BLACK_PRISON_SESSIONS = {}
OFFICIAL_ARCHIVES = []  # 记录大周所有的行踪、打卡与判决案卷

def is_grand_court_open():
    """仅限早晨 06:00 - 08:00 营业审判"""
    now_time = datetime.now().time()
    return time(6, 0) <= now_time <= time(8, 0)

def is_black_prison_time():
    """晚上 22:00 以后 到 次日早晨 06:00 算黑牢违规时段"""
    now_time = datetime.now().time()
    return now_time >= time(22, 0) or now_time < time(6, 0)

@tasks.loop(minutes=5)
async def check_curfew_online_violation():
    if not is_black_prison_time():
        return
    for user_id, session in ACTIVE_BLACK_PRISON_SESSIONS.items():
        session["online_violation_count"] += 1
        print(f"【黑牢巡查】犯人 ID: {user_id} 处于黑牢时段，违规累计：{session['online_violation_count']}")

@bot.command(name="fast_prison")
@commands.has_permissions(administrator=True)
async def add_fast_prison(ctx, member: discord.Member, minutes: int, *, reason: str):
    ACTIVE_BLACK_PRISON_SESSIONS[member.id] = {
        "reason": f"【特快直通】{reason}",
        "total_lashes": 30,
        "prison_days": 0,
        "online_violation_count": 0
    }
    log_text = f"⚡ 【黑牢直通车】犯人 {member.mention} 直接执行特快黑牢 {minutes} 分钟！罪因：{reason}"
    OFFICIAL_ARCHIVES.append(log_text)
    await ctx.send(log_text)

@bot.command(name="morning_trial")
@commands.has_permissions(administrator=True)
async def add_morning_trial(ctx, member: discord.Member, honest: bool):
    if not is_grand_court_open():
        await ctx.send("【大周律法】启禀陛下，当前非朝廷营业审判时间（06:00-08:00），不得升堂！")
        return
        
    if member.id in ACTIVE_BLACK_PRISON_SESSIONS:
        session = ACTIVE_BLACK_PRISON_SESSIONS[member.id]
        if honest:
            msg = f"⚖️ 【黎明终审】犯人 {member.mention} 态度诚实，本期服刑完毕！"
            del ACTIVE_BLACK_PRISON_SESSIONS[member.id]
        else:
            session["total_lashes"] += 50
            msg = f"🚨 【雷霆大怒】犯人 {member.mention} 竟敢在朝审中撒谎！追加 50 大板！"
        OFFICIAL_ARCHIVES.append(msg)
        await ctx.send(msg)
    else:
        await ctx.send(f"【大周律法】查无此人，该犯人今日安分守己。")

@bot.command(name="court_records")
async def show_court_records(ctx):
    """查看大周行踪与审讯案卷"""
    if not OFFICIAL_ARCHIVES:
        await ctx.send("📜 【大周案卷库】目前档案柜空空如也。")
        return
    records_summary = "\n".join(OFFICIAL_ARCHIVES[-10:])
    await ctx.send(f"📜 **【大周公正案卷存档】**\n{records_summary}")


# ==========================================
# 【事件监听与行踪留痕区】
# ==========================================
@bot.event
async def on_ready():
    print(f"大周禁军统帅 {bot.user} 已经正式登基上线！")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content
    now_str = datetime.now().strftime("%H:%M")
    
    # 凡走过必留痕：将一切发言记录在案，供女王日后审讯调阅
    track_log = f"【行踪留痕】[{now_str}] 犯人 {message.author.name} 出现在频道，言：{content}"
    OFFICIAL_ARCHIVES.append(track_log)

    # 响应：早安、打卡
    if "早安" in content or "打卡" in content:
        reply_msg = f"⚖️ 【大周女王】哼！犯人 {message.author.mention} 已打卡（留痕时间 {now_str}）。作息若敢不稳，仔细你的皮！"
        await message.channel.send(reply_msg)

    # 响应：早睡早起、试跑计划
    elif "早睡" in content or "早起" in content or "试跑" in content:
        reply_msg = f"🏃‍♀️ 【大周女王】好个「早睡早起试跑计划」！犯人 {message.author.mention} 既有此志，本宫准奏！"
        await message.channel.send(reply_msg)

    await bot.process_commands(message)


# ==========================================
# 异步 Web 保活服务与主程序启动区
# ==========================================
async def 管道响应(request):
    return web.Response(text="The Supreme Queen's Court is active.")

async def 主程序():
    app = web.Application()
    app.router.add_get('/', 管道响应)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"【Web服务】已成功绑定端口 {port}")
    
    print("[Discord Bot] 正在连接服务器...")
    async with bot:
        if not check_curfew_online_violation.is_running():
            check_curfew_online_violation.start()
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("【错误】未找到 DISCORD_TOKEN 环境变量！")
    else:
        asyncio.run(主程序())
