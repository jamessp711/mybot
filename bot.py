import discord
from discord.ext import commands
from google import genai
from datetime import datetime, timezone, timedelta
import asyncio
import os
import random
import threading
from aiohttp import web

# ==================== 1. 配置加载 ====================
秘钥令牌 = os.environ.get("DISCORD_TOKEN") 
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

print(f"【系统初始化】Token: {'已配置' if 秘钥令牌 else '未配置！'}, Gemini: {'已配置' if GEMINI_KEY else '未配置！'}")

gemini_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

总频道御令ID = 1532548062218813533
禁闭牢房ID = 1532882699293823016

# ==================== 2. Bot 初始化 ====================
意图 = discord.Intents.default()
意图.message_content = True
意图.members = True
内侍省 = commands.Bot(command_prefix="?", intents=意图)

东八区时区 = timezone(timedelta(hours=8))
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
    print(f"【大周御前】女王陛下已成功上线！Bot: {内侍省.user.name}")

# ==================== 3. 指令与核心事件 ====================
@内侍省.command(name="罪状")
async def 呈递罪状档案(ctx):
    try:
        档案 = 获取或初始化档案(ctx.author.id, ctx.author.name)
        历史记录 = "\n".join([f"- {罪}" for 罪 in 档案["罪状历史"][-5:]]) if 档案["罪状历史"] else "身家清白。"
        await ctx.send(
            f"📜 **【大周刑部·档案】**\n"
            f"👤 犯臣：{ctx.author.display_name} | 累犯：{档案['累犯次数']} 次\n"
            f"📋 近期罪状：\n{历史记录}"
        )
    except Exception as e:
        print(f"【报错】{e}")

async def 获取Gemini刑部裁决(用户发言: str, 累犯次数: int) -> dict:
    if not gemini_client:
        return {"is_guilty": True, "刑罚类型": "笞臀轻惩", "禁闭分钟数": 10, "response_text": "女王陛下冷哼一声。"}
    
    系统提示词 = (
        "你现在是大周帝国的至高女王陛下。高居御座，冷酷威严。\n"
        f"当前臣子累犯次数：{累犯次数}。\n"
        "请对臣子的奏折进行智能洞察，判定其是否有罪及态度，并严格按以下 JSON 格式回复（不要有多余标记）：\n"
        "{\n"
        "  \"is_guilty\": true 或 false,\n"
        "  \"刑罚类型\": \"笞臀轻惩\" 或 \"掌嘴禁闭\" 或 \"死牢重判\",\n"
        "  \"禁闭分钟数\": 数字 (如5, 15, 30),\n"
        "  \"response_text\": \"女王陛下的冷酷威严批阅，包含古典惩戒描写，字数在150字以内。\"\n"
        "}"
    )
    try:
        loop = asyncio.get_running_loop()
        def 调AI():
            res = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{系统提示词}\n\n奏折：{用户发言}"
            )
            return res.text
        raw = await loop.run_in_executor(None, 调AI)
        import json, re
        return json.loads(re.sub(r'```json|```', '', raw).strip())
    except Exception:
        return {"is_guilty": True, "刑罚类型": "笞臀轻惩", "禁闭分钟数": 10, "response_text": "⚖️ 女王陛下凤目含威，下令杖笞三十！"}

@内侍省.event
async def on_message(message):
    if message.author.bot:
        return
    try:
        if message.channel.id == 总频道御令ID:
            档案 = 获取或初始化档案(message.author.id, message.author.name)
            AI结果 = await 获取Gemini刑部裁决(message.content, 档案["累犯次数"])
            
            if AI结果.get("is_guilty", False):
                档案["累犯次数"] += 1
                分钟 = int(AI结果.get("禁闭分钟数", 15))
                档案["关押总时长分钟"] += 分钟
                刑罚 = AI结果.get("刑罚类型", "笞臀")
                
                try:
                    await message.delete()
                except:
                    pass

                try:
                    牢房 = 内侍省.get_channel(禁闭牢房ID)
                    if 牢房:
                        await 牢房.send(f"🚨 犯臣 {message.author.mention} 犯下 `{刑罚}`，被女王陛下禁闭 {分钟} 分钟！(原奏：{message.content})")
                except:
                    pass

                公告 = await message.channel.send(f"{AI结果.get('response_text')}\n👑 **【判决】** 犯臣 {message.author.mention} 遭 `{刑罚}` 禁闭 {分钟} 分钟！")
                await asyncio.sleep(8)
                try:
                    await 公告.delete()
                except:
                    pass
                return
            else:
                await message.channel.send(AI结果.get("response_text"))
                return
        await 内侍省.process_commands(message)
    except Exception as e:
        print(f"【异常】{e}")

# ==================== 4. Web 端口保活服务（秒过 Render 检查） ====================
async def 首页响应(request):
    return web.Response(text="The Supreme Queen's Court is active.")

def 启动Web服务():
    app = web.Application()
    app.router.add_get('/', 首页响应)
    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host='0.0.0.0', port=port)

# ==================== 5. 主程序入口（多线程并行） ====================
if __name__ == "__main__":
    if not 秘钥令牌:
        print("【错误】未找到 DISCORD_TOKEN 环境变量！")
    else:
        # 开启独立线程运行 Web 端口保活，主线程留给 Discord Bot
        web_thread = threading.Thread(target=启动Web服务, daemon=True)
        web_thread.start()
        print("【Web服务】已在后台多线程启动保活端口...")
        
        print("【Discord Bot】正在连接服务器...")
        内侍省.run(秘钥令牌)
