# ==================== 第一步：检查并安装依赖 ====================
try:
    import discord
    from discord.ext import commands, tasks
except ImportError:
    import subprocess
    subprocess.check_call(["pip", "install", "discord.py"])
    import discord
    from discord.ext import commands, tasks

from datetime import datetime, timezone, timedelta
import asyncio
import os
from aiohttp import web

# ==================== 宫廷秘钥与频道御令配置 ====================
秘钥令牌 = os.environ.get("DISCORD_TOKEN") 

总频道御令ID = 1532548062218813533      # #general 频道
禁闭牢房ID = 1532882699293823016       # #絕對隔離牢房 频道

# ==================== 初始化内侍省 Bot (前缀为 ?) ====================
意图 = discord.Intents.default()
意图.message_content = True
内侍省 = commands.Bot(command_prefix="?", intents=意图)

# ==================== 大周律例状态机与核心数据 ====================
class 大周法典状态:
    def __init__(self):
        self.累加惩罚天数 = 0
        self.是否身陷牢狱 = False

法典状态 = 大周法典状态()
东八区时区 = timezone(timedelta(hours=8))

@内侍省.event
async def on_ready():
    print(f"【大周内侍省】Bot 已成功登录，恭迎女王大人！当前账号: {内侍省.user}")

# ==================== 基础指令：臣在测试 ====================
@内侍省.command(name="ping")
async def 臣在御前(ctx):
    await ctx.send(f"【大周内侍省】臣在！帝国法度运转正常，当前心跳延迟：{round(内侍省.latency * 1000)}ms")

# ==================== 核心判定：是否为周末或假期豁免期 ====================
def 是否享有豁免(当前时间: datetime) -> bool:
    星期几 = 当前时间.weekday()
    当前时辰 = 当前时间.hour
    # 周五傍晚 6 点后或整整周五、周六，享受豁免
    if (星期几 == 4 and 当前时辰 >= 18) or (星期几 == 5):
        return True
    return False

# ==================== 御前奏折处理与智能语义监察 ====================
@内侍省.event
async def on_message(message):
    if message.author.bot:
        return

    当前时间 = datetime.now(东八区时区)
    当前频道ID = message.channel.id
    奏折内容 = message.content

    # 1. 白天办公隔离御令 (早 8:00 至 晚 9:00，非豁免期严禁在总频道闲聊)
    if not 是否享有豁免(当前时间):
        if 8 <= 当前时间.hour < 21 and 当前频道ID == 总频道御令ID:
            await message.delete()
            警告谕旨 = await message.channel.send(
                f"{message.author.mention} **【大周禁令】** 奉天承运，内侍省宣示：当前正值白天办公与现实隔离时段（08:00 至 21:00），严禁擅入大周女王空间！请大人回心专注现实事务！"
            )
            await asyncio.sleep(5)
            await 警告谕旨.delete()
            return

    # 2. 智能语义洞察：人性化识别日常口语与作息罪名
    if 当前频道ID == 总频道御令ID:
        # 智能匹配日常作息口语或正式汇报
        包含作息词汇 = any(关键字 in 奏折内容 for关键字 in ["睡", "晚安", "打卡", "熬夜", "才睡", "躺下", "闭眼", "睏"])
        
        if 包含作息词汇:
            if 是否享有豁免(当前时间):
                await message.channel.send(f"【大周最高法庭】准奏。今日乃周末社交豁免期，特许大人安心休憩，免予作息法度考核。")
                return

            当前时辰 = 当前时间.hour
            当前分钟 = 当前时间.minute

            if 当前时辰 < 21 or (当前时辰 == 21 and 当前分钟 <= 30):
                await message.channel.send(f"【大周最高法庭】🎉 **大喜！嘉奖**！经内侍省核查，大人今日极早入寝（9:30 PM 前），躬行自律，堪为帝国楷模！特赐高阶功名积分以资鼓励！")
            elif 当前时辰 < 22 or (当前时辰 == 22 and 当前分钟 <= 30):
                await message.channel.send(f"【大周最高法庭】👍 **准许**。大人于 10:30 PM 前就寝，符合帝国作息常典，特此记录在案，望日后保持更佳。")
            elif 当前时辰 < 24:
                await message.channel.send(f"【大周最高法庭】⚠️ **申饬警示**！大人已近深夜 12 点边缘，作息隐现松懈之兆，内侍省奉劝大人即刻收心安歇，切勿触犯宵禁重律！")
            else:
                # 深夜 12 点后入寝，触犯天条，强制押入绝对隔离牢房并宣判笞臀
                法典状态.是否身陷牢狱 = True
                法典状态.累加惩罚天数 += 1
                
                await message.channel.send(
                    f"【大周最高法庭】🚨 **特大御前宣判：触犯帝国宵禁铁律**！"
                    f"\n⚖️ **罪名认定**：经内侍省智能查验，大人深夜 12 点后方才入寝，属于明知故犯、扰乱作息大纲！"
                    f"\n⚡ **刑律宣判**：依大周律例，即刻对大人施以**司法杖责（笞臀惩戒）**，并即时剥夺自由，**强制押送至 <#{禁闭牢房ID}> 【绝对隔离牢房】**严加反省！"
                    f"\n🔒 **刑期标定**：基础禁闭 1 天并叠加累加惩罚，非至清醒悔悟之日不得释放！"
                )

    await 内侍省.process_commands(message)

# ==================== Web 网页保活服务器（满足 Render 要求） ====================
async def 网页响应处理(request):
    return web.Response(text="【大周内侍省】Imperial Cloud Bot is operating under strict laws.")

async def 启动网页服务():
    app = web.Application()
    app.add_routes([web.get('/', 网页响应处理)])
    runner = web.AppRunner(app)
    await runner.setup()
    端口号 = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', 端口号)
    await site.start()
    print(f"【大周内侍省】Web 保活服务已在端口 {端口号} 启动")

# ==================== 帝国主程序入口 ====================
async def 主程序():
    await 启动网页服务()
    await 内侍省.start(秘钥令牌)

if __name__ == "__main__":
    asyncio.run(主程序())
