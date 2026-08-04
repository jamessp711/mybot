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
import random
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
    await ctx.send(f"【大周内侍省】臣 in！帝国法度运转正常，当前心跳延迟：{round(内侍省.latency * 1000)}ms")

# ==================== 核心判定：是否为周末或假期豁免期 ====================
def 是否享有豁免(当前时间: datetime) -> bool:
    星期几 = 当前时间.weekday()
    当前时辰 = 当前时间.hour
    if (星期几 == 4 and 当前时辰 >= 18) or (星期几 == 5):
        return True
    return False

# ==================== 御前奏折处理与严谨法度宣判 ====================
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

    # 2. 智能语义洞察：严谨明确的罪名、笞臀板数与禁闭期限
    if 当前频道ID == 总频道御令ID:
        
        # A. 主动认错/招供查验
        认错词库 = ["犯错", "错了", "负罪", "请罪", "打我", "罚我"]
        包含认错词汇 = any(词 in 奏折内容 for 词 in 认错词库)
        
        if 包含认错词汇:
            法典状态.是否身陷牢狱 = True
            法典状态.累加惩罚天数 += 1
            
            # 严格、明确规定板数与禁闭时长的御前宣判台词
            严谨宣判库 = [
                f"【大周最高法庭】大胆女王大人！既然知罪，**还不速速跪下领命！** 依大周律例：判处**笞臀三十大板**，并即刻打入 <#{禁闭牢房ID}> 【绝对隔离牢房】**闭门思过 24 小时**，非期满绝不释放！",
                f"【大周最高法庭】哼！犯了错还敢站着？**还不给本官跪好！** 念其主动坦白，从轻发落：依律判罚**笞臀二十大板**，即刻押送至 <#{禁闭牢房ID}> 【绝对隔离牢房】**严格禁闭一天**以儆效尤！",
                f"【大周最高法庭】台下可是女王大人？既然口称有罪，**还不双膝着地！** 经内侍省御前合议：判处**笞臀四十大板**，并即时锁入 <#{禁闭牢房ID}> 【绝对隔离牢房】执行**全天候隔离反省**！"
            ]
            await message.channel.send(random.choice(严谨宣判库))
            return

        # B. 作息违规查验
        作息词库 = ["睡", "晚安", "打卡", "熬夜", "才睡", "躺下", "闭眼", "睏"]
        包含作息词汇 = any(词 in 奏折内容 for 词 in 作息词库)
        
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
                法典状态.是否身陷牢狱 = True
                法典状态.累加惩罚天数 += 1
                await message.channel.send(
                    f"【大周最高法庭】🚨 **御前宣判：触犯帝国宵禁铁律**！"
                    f"\n⚖️ **罪名认定**：大人深夜 12 点后方才入寝，明知故犯！**还不跪下！**"
                    f"\n⚡ **刑律宣判**：依大周宵禁重律，判处**笞臀五十大板**，并**强制押送至 <#{禁闭牢房ID}> 【绝对隔离牢房】执行 48 小时重惩禁闭**！"
                )

    await 内侍省.process_commands(message)

# ==================== Web 网页保活服务器（满足 Render 要求） ====================
async def 网页响应处理(request):
    return web.Response(text="【大周内侍省】Imperial Cloud Bot is operating under strict and clear royal laws.")

async def 启动网页服务():
    app = web.Application()
    app.add_routes([web.get('/', 网页响应处理)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"【大周内侍省】Web 保活服务已在端口 {port} 启动")

# ==================== 帝国主程序入口 ====================
async def 主程序():
    await 启动网页服务()
    await 内侍省.start(秘钥令牌)

if __name__ == "__main__":
    asyncio.run(主程序())
