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

print(f"【系统初始化】正在加载配置... Token 状态: {'已配置' if 秘钥令牌 else '未配置！'}, Gemini Key 状态: {'已配置' if GEMINI_KEY else '未配置！'}")

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
    print(f"【大周御前】女王陛下已成功上线！Bot 账号名称: {内侍省.user.name} (ID: {内侍省.user.id})")

# ==================== 基础指令 ====================
@内侍省.command(name="罪状")
async def 呈递罪状档案(ctx):
    try:
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
    except Exception as e:
        print(f"【指令报错】?罪状 执行异常: {e}")

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

# ==================== 调用 Google Gemini 进行动态恐怖心理压迫审判 ====================
async def 获取Gemini动态恐怖裁决(用户发言: str, 累犯次数: int) -> dict:
    if not gemini_client:
        return {"is_guilty": True, "is_severe": False, "response_text": "【大周内侍省】禀女王陛下：未检测到 GEMINI_API_KEY 密钥。"}
    
    # 动态切换恐怖话术风格池，确保每次审判花样百出、直击心魄
    风格列表 = [
        "风格A：【极度冰冷蔑视】女王高高在上，嫌弃臣子连这点自控力都没有，言语如冰刀刮骨。",
        "风格B：【暴虐雷霆震怒】女王凤目圆睁，拍案而起，历数臣子屡教不改之罪，满殿森然。",
        "风格C：【猫捉老鼠戏谑】女王带着玩味的笑意，像审视一只逃不出掌心的蝼蚁，字字诛心。",
        "风格D：【深宫心理压迫】女王不怒自威，通过阴暗压抑的宫廷细节描写，让臣子从灵魂深处感到颤栗。"
    ]
    当前选定风格 = random.choice(风格列表)

    系统提示词 = (
        "你现在是大周帝国的至高女王陛下。你高居紫檀御座，冷酷、威严、睿智、令人不寒而栗。\n"
        f"当前臣子的累计犯罪次数已达 {累犯次数} 次。\n"
        f"本次审判请严格采用以下设定：【{当前选定风格}】\n"
        "请对臣子的奏折进行深度洞察，并严格按以下 JSON 格式回复（不要包含多余的markdown标记，直接输出JSON）：\n"
        "{\n"
        "  \"is_guilty\": true 或 false (判断臣子是否在认错、犯懒、熬夜、违纪),\n"
        "  \"is_severe\": true 或 false (若涉及熬夜、累犯多次或大不敬，必须为true),\n"
        "  \"response_text\": \"女王陛下的冷酷威严批阅，包含极其生动、绝不重复的古典刑罚与心理压迫描写，字数控制在180字以内。\"\n"
        "}"
    )

    try:
        loop = asyncio.get_running_loop()
        def 调用谷歌大模型():
            response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{系统提示词}\n\n臣子奏折：{用户发言}"
            )
            return response.text
        
        AI原始回复 = await loop.run_in_executor(None, 调用谷歌大模型)
        print(f"【AI审判日志】原始返回: {AI原始回复}")
        
        import json
        import re
        clean_text = re.sub(r'```json|```', '', AI原始回复).strip()
        result_data = json.loads(clean_text)
        return result_data
    except Exception as e:
        print(f"【Gemini 审判解析报错】{e}")
        return {
            "is_guilty": True,
            "is_severe": False,
            "response_text": "⚖️ **【大周最高法庭】** 女王陛下冷冷地扫视一眼，降下三十御前笞臀，以示惩戒。"
        }

# ==================== 御前奏折处理核心 ====================
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

        # 2. 全智能动态话术御前审判
        if 当前频道ID == 总频道御令ID:
            
            # 获取当前档案中的累犯次数传入 AI
            临时档案 = 获取或初始化档案(用户ID, 用户名)
            当前累犯数 = 临时档案["累犯次数"]

            AI审判结果 = await 获取Gemini动态恐怖裁决(奏折内容, 当前累犯数)
            
            is_guilty = AI审判结果.get("is_guilty", False)
            is_severe = AI审判结果.get("is_severe", False)
            AI回复文本 = AI审判结果.get("response_text", "女王陛下冷哼一声。")

            if is_guilty:
                档案 = 获取或初始化档案(用户ID, 用户名)
                档案["累犯次数"] += 1
                
                # 如果触犯重罪或累犯过多，直接拉入绝对隔离牢房禁言！
                if is_severe or 档案["累犯次数"] >= 3:
                    关押时长 = 60 * 档案["累犯次数"]
                    档案["关押总时长分钟"] += 关押时长
                    罪状描述 = f"于 {当前时间.strftime('%m-%d %H:%M')} 触犯重律（动态审判重罪：{奏折内容[:15]}）"
                    档案["罪状历史"].append(罪状描述)

                    await message.channel.send(
                        f"🚨 **【大周刑部·雷霆死牢判决】**\n"
                        f"⚡ 御座之上的**女王陛下**缓缓站起身来，居高临下地俯视着罪臣，眼中没有一丝温度：\n"
                        f"🔒 **【无预警投入死牢】** 罪名：`{奏折内容}`。多端不化，罪无可赦！即刻剥夺一切在大殿的发言权，无预警押送至 <#{禁闭牢房ID}> 【绝对隔离牢房】**严惩闭门思过 {关押时长} 分钟**！\n"
                        f"📜 *（刑部落款：当前累犯总计 {档案['累犯次数']} 次，起暗牢铁锁已上。）*"
                    )
                    return

                # 普通违纪：多变话术当庭杖刑与案卷录入
                档案["关押总时长分钟"] += 30
                档案["罪状历史"].append(f"于 {当前时间.strftime('%m-%d %H:%M')} 动态受审：{奏折内容[:20]}")
                
                正式罪状宣判 = (
                    f"{AI回复文本}\n\n"
                    f"📋 **【刑部案结呈报】** 罪状已归档。犯臣目前累计犯罪 {档案['累犯次数']} 次，总计服刑 {档案['关押总时长分钟']} 分钟。输入 `?罪状` 可随时查阅完整卷宗。"
                )
                
                if len(正式罪状宣判) > 2000:
                    正式罪状宣判 = 正式罪状宣判[:1990] + "..."
                    
                await message.channel.send(正式罪状宣判)
                return
            else:
                # 正常学术、日常汇报
                await message.channel.send(AI回复文本)
                return
        
        await 内侍省.process_commands(message)

    except Exception as e:
        print(f"【on_message 发生严重异常】: {e}")

# ==================== Web 网页保活服务器 ====================
async def 网页响应处理(request):
    return web.Response(text="The Supreme Queen's Court is active.")

async def 启动网页服务():
    app = web.Application()
    app.add_routes([web.get('/', 网页响应处理)])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"【Web服务】保活服务已在端口 {port} 启动")

async def 主程序():
    await 启动网页服务()
    print("【Discord Bot】正在尝试连接 Discord 服务器...")
    await 内侍省.start(秘钥令牌)

if __name__ == "__main__":
    asyncio.run(主程序())
