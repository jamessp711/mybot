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
# 【大周新政：八月宵禁、黑牢与黎明审判独立增量模块】
# ==========================================

# 1. 内存中独立存储当期 Session 罪行的字典
ACTIVE_BLACK_PRISON_SESSIONS = {}

# 2. 时间校验函数：大周营业与闭关作息表
def is_grand_court_open():
    """判定当前是否处于大周允许的营业/审判时间 (06:00 - 08:00)"""
    now_time = datetime.now().time()
    return time(6, 0) <= now_time <= time(8, 0)

def is_curfew_time():
    """判定是否进入夜间宵禁/黑牢时间 (20:00 以后 到 次日 06:00 以前)"""
    now_time = datetime.now().time()
    return now_time >= time(20, 0) or now_time < time(6, 0)

# 3. 独立后台循环：每5分钟自动巡查宵禁期间在线超时的犯人
@tasks.loop(minutes=5)
async def check_curfew_online_violation():
    if not is_curfew_time():
        return
    for user_id, session in ACTIVE_BLACK_PRISON_SESSIONS.items():
        session["online_violation_count"] += 1
        print(f"【黑牢巡查】犯人 ID: {user_id} 宵禁期逗留，当前Session罪行累计违规：{session['online_violation_count']}")

# 4. 独立指令：重犯特快直通车（无需审问，直接强制黑牢）
@bot.command(name="fast_prison")
@commands.has_permissions(administrator=True)
async def add_fast_prison(ctx, member: discord.Member, minutes: int, *, reason: str):
    ACTIVE_BLACK_PRISON_SESSIONS[member.id] = {
        "reason": f"【特快直通】{reason}",
        "total_lashes": 30,
        "prison_days": 0,
        "online_violation_count": 0
    }
    await ctx.send(f"⚡ 【黑牢直通车】犯人 {member.mention} 记录不良，直接执行特快黑牢 {minutes} 分钟！罪因：{reason}")

# 5. 独立指令：黎明审判窗口（早 6am 至 7am 监狱长拷问与放风）
@bot.command(name="morning_trial")
@commands.has_permissions(administrator=True)
async def add_morning_trial(ctx, member: discord.Member, honest: bool):
    if not is_grand_court_open():
        await ctx.send("【大周律法】启禀大人，当前非朝廷营业与审判时间（06:00-08:00），不得升堂！")
        return
        
    if member.id in ACTIVE_BLACK_PRISON_SESSIONS:
        session = ACTIVE_BLACK_PRISON_SESSIONS[member.id]
        if honest:
            await ctx.send(f"⚖️ 【黎明终审】犯人 {member.mention} 经监狱长拷问，态度诚实。本期Session（{session['reason']}，共挨 {session['total_lashes']} 板）服刑完毕！7:00 准时开释！")
            del ACTIVE_BLACK_PRISON_SESSIONS[member.id]
        else:
            session["total_lashes"] += 50
            session["prison_days"] += 3
            await ctx.send(f"🚨 【雷霆大怒】犯人 {member.mention} 竟敢在黑牢朝审中撒谎！当场加判 3 天黑牢、追加 50 大板！")
    else:
        await ctx.send(f"【大周律法】查无此人，该国民昨夜安分守己，无需受审。")


# ==========================================
# 【大人原有的核心逻辑与事件监听区】
# ==========================================
@bot.event
async def on_ready():
    print(f"大周禁军统帅 {bot.user} 已经正式登基上线！")


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
        # 启动后台黑牢巡查任务
        if not check_curfew_online_violation.is_running():
            check_curfew_online_violation.start()
        await bot.start(os.getenv("DISCORD_TOKEN"))

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if not token:
        print("【错误】未找到 DISCORD_TOKEN 环境变量！")
    else:
        asyncio.run(主程序())
