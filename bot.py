# ==================== 第一步：安装依赖 ====================
try:
    import discord
    from discord.ext import commands, tasks
except ImportError:
    import subprocess
    subprocess.check_call(["pip", "install", "discord.py"])
    import discord
    from discord.ext import commands, tasks

from datetime import datetime, time, timezone, timedelta
import asyncio
import os
from aiohttp import web

# ==================== 配置区域 ====================
TOKEN = os.environ.get("DISCORD_TOKEN") 

CHANNEL_GENERAL_ID = 1532548062218813533      # #general 频道
CHANNEL_SOLITARY_ID = 1532882699293823016     # #絕對隔離牢房 频道
CHANNEL_EXAM_ID = 1532548062218813533         # #科举之路 频道

# ==================== 初始化 Bot (前缀改为 ? 以防撞车) ====================
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="?", intents=intents)

# ==================== 大周法典状态机与核心数据 ====================
class ZhouState:
    def __init__(self):
        self.target_wake_up_hour = 8
        self.target_wake_up_minute = 0
        self.is_in_solitary = False
        self.solitary_end_time = None
        self.accumulated_penalty_days = 0
        self.night_walk_start = None
        self.exam_active = False

state = ZhouState()
TZ = timezone(timedelta(hours=8))

@bot.event
async def on_ready():
    print(f"【大周内侍省】Bot 已成功登录，恭迎女王大人！当前账号: {bot.user}")
    if not daily_court_loop.is_running():
        daily_court_loop.start()

# ==================== 基础指令测试 ====================
@bot.command(name="ping")
async def ping(ctx):
    await ctx.send(f"【大周内侍省】臣在！帝国运转正常，延迟：{round(bot.latency * 1000)}ms")

# ==================== 核心逻辑：时间与作息判定 ====================
def is_work_or_social_exempt(now: datetime) -> bool:
    weekday = now.weekday()
    hour = now.hour
    if (weekday == 4 and hour >= 18) or (weekday == 5):
        return True
    return False

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    now = datetime.now(TZ)
    current_channel_id = message.channel.id
    content = message.content

    # 1. 白天办公隔离检查 (8:00 AM - 9:00 PM)
    if not is_work_or_social_exempt(now):
        if 8 <= now.hour < 21 and current_channel_id == CHANNEL_GENERAL_ID:
            await message.delete()
            warning_msg = await message.channel.send(
                f"{message.author.mention} **【大周禁令】** 报告大人！当前正值白天办公与现实隔离时间（08:00 - 21:00），严禁进入大周女王空间！请专心投入现实生活！"
            )
            await asyncio.sleep(5)
            await warning_msg.delete()
            return

    # 2. 睡眠时间分级汇报与判定 (#general)
    if current_channel_id == CHANNEL_GENERAL_ID and ("睡" in content or "晚安" in content or "打卡" in content):
        hour = now.hour
        minute = now.minute
        
        if is_work_or_social_exempt(now):
            await message.channel.send(f"【大周内侍省】今日乃周末社交豁免期，大人早点安歇，免予作息考核。")
            return

        if hour < 21 or (hour == 21 and minute <= 30):
            await message.channel.send(f"【大周最高法庭】🎉 **特大喜讯**！大人今日极早入睡（9:30 PM 前），自律楷模！特赐高阶功名积分与厚奖！")
        elif hour < 22 or (hour == 22 and minute <= 30):
            await message.channel.send(f"【大周最高法庭】👍 大人 10:30 PM 前入寝，符合标准，予以肯定，鼓励继续保持 10:00 睡前习惯！")
        elif hour < 23:
            await message.channel.send(f"【大周最高法庭】⚠️ **警戒**！大人已至 11 点警戒期，明日需加紧提早！")
        else:
            state.is_in_solitary = True
            state.accumulated_penalty_days += 1
            state.solitary_end_time = now + timedelta(days=1 + state.accumulated_penalty_days)
            
            await message.channel.send(
                f"【大周最高法庭】🚨 **触犯天条**！大人深夜 12 点后入寝！"
                f"\n⚖️ **判决**：即刻处以司法杖责（打屁股）并强制押送至 <#{CHANNEL_SOLITARY_ID}> **绝对隔离牢房**！"
                f"\n🔒 **刑期**：基础 1 天加累加惩罚，关禁闭至清醒反思为止！"
            )

    await bot.process_commands(message)

# ==================== 后台循环任务 ====================
@tasks.loop(minutes=1)
async def daily_court_loop():
    now = datetime.now(TZ)
    hour = now.hour
    minute = now.minute

    if state.is_in_solitary and hour == 6 and minute == 0:
        solitary_channel = bot.get_channel(CHANNEL_SOLITARY_ID)
        if solitary_channel:
            await solitary_channel.send(
                f"【大周牢房】⏰ **早 6:00 放风窗口已开**！"
                f"\n请大人在此进行早晨打卡，简要报告昨晚至早上的情况及是否违规。7:00 AM 将重新严格收监至晚 10:00 PM！"
            )

    if state.is_in_solitary and hour == 7 and minute == 0:
        solitary_channel = bot.get_channel(CHANNEL_SOLITARY_ID)
        if solitary_channel:
            await solitary_channel.send(
                f"【大周牢房】🔒 **放风时间已过**！大周法庭下令：继续高压关押隔离，直到晚上 10:00 PM 禁闭结束。"
            )

# ==================== Web 网页保活服务器（满足 Render 要求） ====================
async def handle(request):
    return web.Response(text="【大周内侍省】Cloud Bot is running perfectly!")

async def start_web_server():
    app = web.Application()
    app.add_routes([web.get('/', handle)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"【大周内侍省】Web 保活服务已在端口 {port} 启动")

# ==================== 主程序入口 ====================
async def main():
    await start_web_server()
    await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())
