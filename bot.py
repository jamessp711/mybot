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

gemini_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

总频道御令ID = 1532548062218813533      # #general 频道
禁闭牢房ID = 1532882699293823016       # #絕對隔離牢房 频道

# ==================== 初始化内侍省 Bot (前缀为 ?) ====================
意图 = discord.Intents.default()
意图.message_content = True
意图.members = True
内侍省 = commands.Bot(command_prefix="?", intents=意图)

东八区时区 = timezone(timedelta(hours=8))

# ==================== 大周刑部：臣子犯罪档案数据库 ====================
# 用于记录每位臣子的：{ 用户ID: {"名字": str, "累犯次数": int, "关押总时长分钟": int, "罪状历史": list} }
大周刑部档案库 = {}

def 获取或初始化档案(用户ID, 用户名):
    if 用户ID not in 大周刑部档案库:
        大周刑部档案库[用户ID] = {
            "名字": 用户名,
            "累犯次数": 0,
            "关押总时长分钟": 0,
            "罪状历史": []
        }
    return 大周刑部档案库[用户ID]

@内侍省.event
async def on_ready():
    print(f"【大周御前】刑部大案牍司运转正常，女王陛下执掌无情铁律，恭迎内阁大人！")

# ==================== 基础指令：查阅起居注与个人罪状档案 ====================
@内侍省.command(name="罪状")
async def 呈递罪状档案(ctx):
    档案 = 获取或初始化档案(ctx.author.id, ctx.author.name)
    历史记录文本 = "\n".join([f"- {罪}" for 罪 in 档案["罪状历史"][-5:]]) if 档案["罪状历史"] else "暂无重大案底，身家清白。"
    
    await ctx.send(
        f"📜 **【大周刑部·御前起居注档案】**\n"
        f"👤 **犯臣/臣子**：{ctx.author.display_name}\n"
        f"⚖️ **累犯次数**：{档案['累犯次数']} 次\n"
        f"🔒 **判决关押总计**：{档案['关押总时长分钟']} 分钟\n"
        f"📋 **近期罪状摘要**：\n{历史记录文本}\n"
        f"*(女王陛下目光如炬，一切因果皆有定数。)*"
    )

@内侍省.command(name="ping")
async def 臣在御前(ctx):
    await ctx.send(f"👑 **【大周御前】** 系统稳如泰山。心跳延迟：{round(内侍省.latency * 1000)}ms")

# ==================== 核心判定：是否为周末或假期豁免期 ====================
def 是否享有豁免(当前时间: datetime) -> bool:
    星期几 = 当前时间.weekday()
    当前时辰 = 当前时间.hour
    if (星期几 == 4 and 当前时辰 >= 18) or (星期几 == 5):
        return True
    return False

# ==================== 调用 Google Gemini 进行深度智能审判 ====================
async def 获取Gemini睿智裁决(用户发言: str, 上下文提示: str) -> str:
    if not gemini_client:
        return "【大周内侍省】禀女王陛下：未检测到 GEMINI_API_KEY 密钥。"
    
    系统提示词 = (
        "你现在是大周帝国的至高女王陛下。你高居紫檀御座，冷酷、威严、睿智、专业。"
        "你的宫廷内阁大臣（使用者）正在筹备将这套系统用于学校纪律管理。"
        "当臣子向你上奏、认错或违纪时，必须保持冷酷、威严的女王口吻，降下精准的笞臀惩戒与古典触觉描写。"
        "字数请严格控制在 200 字以内。"
    )

    try:
        loop = asyncio.get_running_loop()
        def 调用谷歌大模型():
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{系统提示词}\n\n【当前情境：{上下文提示}】\n臣子奏折：{用户发言}"
            )
            return response.text
        
        AI回复 = await loop.run_in_executor(None, 调用谷歌大模型)
        return AI回复 if AI回复 else "⚖️ **【大周最高法庭】** 女王陛下目光深邃，未予置评。"
    except Exception as e:
        print(f"【Gemini 调用报错】{e}")
        return "⚖️ **【大周最高法庭】** 女王陛下沉思片刻，天机紊乱。"

# ==================== 御前奏折处理与无预警重罚核心 ====================
@内侍省.event
async def on_message(message):
    if message.author.bot:
        return

    try:
        当前时间 = datetime.now(东八区时区)
        当前频道ID = message.channel.id
        奏折内容 = message.content
        用户ID = message.author.id
        用户名 = message.author.name

        # 1. 白天办公隔离御令
        if not 是否享有豁免(当前时间):
            if 8 <= 当前时间.hour < 21 and 当前频道ID == 总频道御令ID:
                await message.delete()
                警告谕旨 = await message.channel.send(
                    f"👑 **【大周御前圣谕】** 坐在王座之上的**女王陛下**冷冷宣示：当前正值白天严谨办公时段（08:00 至 21:00），闲杂奏折一律驳回！"
                )
                await asyncio.sleep(5)
                await 警告谕旨.delete()
                return

        # 2. 智能化全领域响应
        if 当前频道ID == 总频道御令ID:
            
            违纪关键词 = ["犯错", "错了", "负罪", "请罪", "打我", "罚我", "该打", "打怪", "熬夜", "睡", "晚安", "睏"]
            是否包含违纪 = any(词 in 奏折内容 for 词 in 违纪关键词)

            if 是否包含违纪:
                # 建立或更新档案
                档案 = 获取或初始化档案(用户ID, 用户名)
                档案["累犯次数"] += 1
                
                # 依据累犯次数智能判断：若累犯次数多，直接执行“无预警重罪直接关押 60 分钟以上”不经审讯！
                if 档案["累犯次数"] >= 3 or "熬夜" in 奏折内容:
                    关押时长 = 60 * 档案["累犯次数"]  # 累犯越重，关押越久
                    档案["关押总时长分钟"] += 关押时长
                    罪状描述 = f"于 {当前时间.strftime('%m-%d %H:%M')} 触犯重律（累犯第{档案['累犯次数']}次）"
                    档案["罪状历史"].append(罪状描述)

                    # 👑 核心绝招：不经审讯，直接无预警强行踢入绝对隔离牢房！
                    await message.channel.send(
                        f"🚨 **【大周刑部·无预警铁律重审】**\n"
                        f"⚡ 察觉罪孽深重、累犯多端！御座之上的**女王陛下**甚至无需听其辩解，凤目一寒，直接下达雷霆法旨：\n"
                        f"🔒 **【直接打入牢狱】** 罪不可赦，不予当庭审讯！即刻剥夺一切发言权，无预警押送至 <#{禁闭牢房ID}> 【绝对隔离牢房】**重罚闭门思过 {关押时长} 分钟**！\n"
                        f"📜 *（刑部落款：当前累犯总计 {档案['累犯次数']} 次，起烈火烙印已录入案册。）*"
                    )
                    return

                # 若情节尚可，则走正常的 AI 审判流程，并在审判结束后出示罪状
                上下文 = "臣子主动认错或违规，请女王陛下进行冷酷而威严的当庭审判，并降下笞臀惩戒。"
                AI裁决结果 = await 获取Gemini睿智裁决(奏折内容, 上下文)
                
                # 案册登记
                档案["关押总时长分钟"] += 30
                档案["罪状历史"].append(f"于 {当前时间.strftime('%m-%d %H:%M')} 当庭受审：{奏折内容[:20]}")
                
                正式罪状宣判 = (
                    f"{AI裁决结果}\n\n"
                    f"📋 **【刑部案结呈报】** 罪状已归档。犯臣目前累计犯罪 {档案['累犯次数']} 次，总计服刑 {档案['关押总时长分钟']} 分钟。输入 `?罪状` 可随时查阅完整卷宗。"
                )
                
                if len(正式罪状宣判) > 2000:
                    正式罪状宣判 = 正式罪状宣判[:1990] + "..."
                    
                await message.channel.send(正式罪状宣判)
                return
            else:
                上下文 = "臣子正常上奏汇报，涉及学术、文学、医学或日常请安，请女王展现睿智与专业进行批阅。"
                AI裁决结果 = await 获取Gemini睿智裁决(奏折内容, 上下文)
                await message.channel.send(AI裁决结果)
                return
        
        await 内侍省.process_commands(message)

    except Exception as e:
        print(f"【内侍省防闪退捕获日志】发生异常: {e}")

# ==================== Web 网页保活服务器 ====================
async def 网页响应处理(request):
    return web.Response(text="【大周内侍省】The Supreme Queen's Court is active.")

async def 启动网页服务():
    app = web.Application()
    app.add_routes([web.get('/', 网页响应处理)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"【大周内侍省】Web 保活服务已在端口 {port} 启动")

async def 主程序():
    await 启动网页服务()
    await 内侍省.start(秘钥令牌)

if __name__ == "__main__":
    asyncio.run(主程序())
