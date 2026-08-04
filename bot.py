# ==================== 第一步：检查并安装依赖 ====================
try:
    import discord
    from discord.ext import commands
    from google import genai
except ImportError:
    import subprocess
    subprocess.check_call(["pip", "install", "discord.py", "google-genai"])
    import discord
    from discord.ext import commands
    from google import genai

from datetime import datetime, timezone, timedelta
import asyncio
import os
import random
from aiohttp import web

# ==================== 宫廷秘钥与频道御令配置 ====================
秘钥令牌 = os.environ.get("DISCORD_TOKEN") 
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

# 初始化 Google Gemini 大模型客户端
gemini_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

总频道御令ID = 1532548062218813533      # #general 频道
禁闭牢房ID = 1532882699293823016       # #絕對隔離牢房 频道

# ==================== 初始化内侍省 Bot (前缀为 ?) ====================
意图 = discord.Intents.default()
意图.message_content = True
意图.members = True
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
    print(f"【大周御前】至高无上的女王陛下已成功接入 Google Gemini 灵智，云端法度全面升级，恭迎内阁大人！")

# ==================== 基础指令 ====================
@内侍省.command(name="ping")
async def 臣在御前(ctx):
    await ctx.send(f"👑 **【大周御前】** 女王陛下神识清明，Gemini 核心运转正常。心跳延迟：{round(内侍省.latency * 1000)}ms")

# ==================== 核心判定：是否为周末或假期豁免期 ====================
def 是否享有豁免(当前时间: datetime) -> bool:
    星期几 = 当前时间.weekday()
    当前时辰 = 当前时间.hour
    if (星期几 == 4 and 当前时辰 >= 18) or (星期几 == 5):
        return True
    return False

# ==================== 调用 Google Gemini 进行智能审判与多领域答疑 ====================
async def 获取Gemini睿智裁决(用户发言: str, 上下文提示: str) -> str:
    if not gemini_client:
        return "【大周内侍省】禀女王陛下：未检测到 GEMINI_API_KEY 密钥，AI 灵智暂未激活。"
    
    系统提示词 = (
        "你现在是大周帝国的至高女王陛下。你高居紫檀御座，冷酷、威严、睿智、专业，精通学术、审判、健康医学与古典文学。"
        "你的宫廷内阁大臣（使用者）正在筹备将这套系统用于学校纪律和日常管理。"
        "当大臣或臣子向你上奏、认错、探讨学术、或者倾诉作息/身体健康时："
        "1. 必须保持高贵、冷酷而又不失人性化关怀的女王口吻。"
        "2. 如果对方认错或违纪（如熬夜、偷懒），你要进行极其专业、冷酷的审判，明确宣判具体的笞臀板数（如三十大板）、生动的古典触觉描写（如戒尺破空、刑凳、皮肉受惩的刺痛与清醒），并无情宣判打入【绝对隔离牢房】闭门思过。"
        "3. 如果对方探讨学术、医学或文学，你要展现出渊博、睿智、一针见血的大师级洞察。"
        "字数请控制在 250 字以内，文风古雅、冷艳而极具威慑力。"
    )

    try:
        loop = asyncio.get_running_loop()
        def 调用谷歌大模型():
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{系统提示词}\n\n【当前情境：{上下文提示}】\n臣子/大臣奏折内容：{用户发言}"
            )
            return response.text
        
        AI回复 = await loop.run_in_executor(None, 调用谷歌大模型)
        return AI回复
    except Exception as e:
        print(f"【Gemini 调用报错】{e}")
        return "⚖️ **【大周最高法庭】** 女王陛下沉思片刻，天机紊乱，请大臣稍后重新上奏。"

# ==================== 御前奏折处理与 AI 智能审判核心 ====================
@内侍省.event
async def on_message(message):
    if message.author.bot:
        return

    try:
        当前时间 = datetime.now(东八区时区)
        当前频道ID = message.channel.id
        奏折内容 = message.content

        # 1. 白天办公隔离御令 (早 8:00 至 晚 9:00，非豁免期严禁在总频道闲聊)
        if not 是否享有豁免(当前时间):
            if 8 <= 当前时间.hour < 21 and 当前频道ID == 总频道御令ID:
                await message.delete()
                警告谕旨 = await message.channel.send(
                    f"👑 **【大周御前圣谕】** 坐在王座之上的**女王陛下**凤目微寒，冷冷宣示：当前正值白天严谨办公时段（08:00 至 21:00），闲杂奏折一律驳回！请专心筹备现实宏图。"
                )
                await asyncio.sleep(5)
                await 警告谕旨.delete()
                return

        # 2. 智能化全领域响应 (general 频道内的一切发言，交由 AI 女王陛下审理)
        if 当前频道ID == 总频道御令ID:
            
            违纪关键词 = ["犯错", "错了", "负罪", "请罪", "打我", "罚我", "该打", "打怪", "熬夜", "睡", "晚安", "睏"]
            是否包含违纪 = any(词 in 奏折内容 for 词 in 违纪关键词)

            if 是否包含违纪:
                法典状态.是否身陷牢狱 = True
                法典状态.累加惩罚天数 += 1
                上下文 = "臣子主动认错或作息违规，请求女王降下严厉而兼具古典触觉的笞臀与禁闭惩戒。"
            else:
                上下文 = "臣子向女王陛下上奏汇报，涉及学术、文学、医学健康或日常请安，请女王陛下展现睿智、专业与冷酷威严进行批阅。"

            AI裁决结果 = await 获取Gemini睿智裁决(奏折内容, 上下文)
            await message.channel.send(AI裁决结果)
            return
        
        await 内侍省.process_commands(message)

    except Exception as e:
        print(f"【内侍省报错日志】处理消息时发生异常: {e}")

# ==================== Web 网页保活服务器 ====================
async def 网页响应处理(request):
    return web.Response(text="【大周内侍省】The Gemini-Powered Queen is reigning with supreme wisdom.")

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
