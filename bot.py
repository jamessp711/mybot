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
# 【大周新政：八月 12am 宵禁、黑牢、打卡整顿与大殿案卷公示模块】
# ==========================================

# 1. 内存中独立存储当期 Session 罪行与打卡档案的字典
ACTIVE_BLACK_PRISON_SESSIONS = {}
OFFICIAL_ARCHIVES = []  # 记录大周所有的打卡与判决案卷

# 2. 时间校验函数：大周营业、宵禁与黑牢作息表
def is_grand_court_open():
    """判定当前是否处于大周允许的营业/审判时间 (仅限早晨 06:00 - 08:00)"""
    now_time = datetime.now().time()
    return time(6, 0) <= now_time <= time(8, 0)

def is_curfew_time():
    """判定是否进入夜间宵禁时间 (午夜 00:00 以后 到 早晨 06:00 以前)"""
    now_time = datetime.now().time()
    return time(0, 0) <= now_time < time(6, 0)

def is_black_prison_time():
    """判定是否达到黑牢入狱/违规时段 (晚上 22:00 以后 到 次日早晨 06:00 以前)"""
    now_time = datetime.now().time()
    return now_time >= time(22, 0) or now_time < time(6, 0)

# 3. 独立后台循环：每5分钟自动巡查黑牢时段内在线超时的犯人
@tasks.loop(minutes=5)
async def check_curfew_online_violation():
    if not is_black_prison_time():
        return
    for user_id, session in ACTIVE_BLACK_PRISON_SESSIONS.items():
        session["online_violation_count"] += 1
        print(f"【黑牢巡查】犯人 ID: {user_id} 处于黑牢有效时段（22:00后），当前Session违规累计：{session['online_violation_count']}")

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
    log_text = f"⚡ 【黑牢直通车】犯人 {member.mention} 记录不良，直接执行特快黑牢 {minutes} 分钟！罪因：{reason}"
    OFFICIAL_ARCHIVES.append(log_text)
    await ctx.send(log_text)

# 5. 独立指令：黎明审判窗口（仅限早 6am 至 8am 升堂）
@bot.command(name="morning_trial")
@commands.has_permissions(administrator=True)
async def add_morning_trial(ctx, member: discord.Member, honest: bool):
    if not is_grand_court_open():
        await ctx.send("【大周律法】启禀陛下，当前非朝廷营业与审判时间（仅限早晨 06:00-08:00，其余时间皆因 RL 生活闭关），不得升堂！")
        return
        
    if member.id in ACTIVE_BLACK_PRISON_SESSIONS:
        session = ACTIVE_BLACK_PRISON_SESSIONS[member.id]
        if honest:
            msg = f"⚖️ 【黎明终审】犯人 {member.mention} 经监狱长拷问，态度诚实。本期Session（{session['reason']}，共挨 {session['total_lashes']} 板）服刑完毕！8:00 前准时开释！"
            del ACTIVE_BLACK_PRISON_SESSIONS[member.id]
        else:
            session["total_lashes"] += 50
            session["prison_days"] += 3
            msg = f"🚨 【雷霆大怒】犯人 {member.mention} 竟敢在黑牢朝审中撒谎！当场加判 3 天黑牢、追加 50 大板！"
        OFFICIAL_ARCHIVES.append(msg)
        await ctx.send(msg)
    else:
        await ctx.send(f"【大周律法】查无此人，该犯人今日安分守己，无需受审。")

# 6. 独立指令：查看大周国法案卷与历史记录 (方便 Review)
@bot.command(name="court_records")
async def show_court_records(ctx):
    """公开展示大周朝廷近期所有的犯罪、打卡与刑罚案卷"""
    if not OFFICIAL_ARCHIVES:
        await ctx.send("📜 【大周案卷库】目前档案柜空空如也，暂无重大案件或打卡记录。")
        return
    
    records_summary = "\n".join(OFFICIAL_ARCHIVES[-10:])  # 仅展示最近10条
    await ctx.send(f"📜 **【大周朝廷公正案卷存档】（最近记录）**\n{records_summary}")


# ==========================================
# 【核心逻辑与事件监听区】
# ==========================================
@bot.event
async def on_ready():
    print(f"大周禁军统帅 {bot.user} 已经正式登基上线！")

@bot.event
async def on_message(message):
    # 防止机器人自己和自己对话陷入死循环
    if message.author.bot:
        return

    content = message.content

    # 1. 响应：早安、打卡（结合 12am 宵禁与 8am 起床规条进行警告/提醒）
    if "早安" in content or "打卡" in content:
        reply_msg = (
            f"⚖️ 【大周女王】哼！犯人 {message.author.mention} 虽已打卡，但本月实行 12am 宵禁、8am 起床与 8pm 闭门作息！"
            f"若作息不稳，休怪本宫动用刑法。今日暂且记下，给本宫把皮绷紧点！"
        )
        OFFICIAL_ARCHIVES.append(f"【打卡记录】{message.author.name} 进行打卡报到。")
        await message.channel.send(reply_msg)

    # 2. 响应：早睡早起、试跑计划
    elif "早睡" in content or "早起" in content or "试跑" in content:
        reply_msg = (
            f"🏃‍♀️ 【大周女王】好个「早睡早起试跑计划」！犯人 {message.author.mention} 既然立下志向要赶在 12am 前入睡、8pm 前作息，"
            f"本宫姑且准奏并记入案卷！若敢半途而废，仔细你的皮！"
        )
        OFFICIAL_ARCHIVES.append(f"【作息整顿】{message.author.name} 启动早睡早起试跑计划。")
        await message.channel.send(reply_msg)

    # 必须保留这句，否则感叹号开头的指令会失效
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
        # 启动后台黑牢巡查任务
