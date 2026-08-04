import discord
from discord.ext import commands
from google import genai
from datetime import datetime, timezone, timedelta
import asyncio
import os
import random
from aiohttp import web

# ==================== 1. 配置加载 ====================
秘钥令牌 = os.environ.get("DISCORD_TOKEN") 
GEMINI_KEY = os.environ.get("GEMINI_API_KEY")

print(f"【系统初始化】Token: {'已配置' if 秘钥令牌 else '未配置！'}, Gemini: {'已配置' if GEMINI_KEY else '未配置！'}")

gemini_client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

总频道御令ID = 1532548062218813533
禁闭牢房ID = 1532882699293823016  # 务必确保此ID为私密频道的ID

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

# ==================== 3. 刑满释放异步协程 ====================
async def 执行刑满释放(member, 牢房频道, 分钟数):
    await asyncio.sleep(分钟数 * 60) # 等待真实的禁闭时间过去
    try:
        # 1. 解除系统级禁言 (Timeout)
        await member.timeout(None, reason="刑满释放，重获自由")
    except Exception as e:
        print(f"【解除禁言失败】{e}")

    try:
        # 2. 从私密牢房频道中移除其访问权限
        if 牢房频道:
            await 牢房频道.set_permissions(member, overwrite=None)
            await 牢房频道.send(f"🕊️ **【刑满释放】** 犯臣 {member.mention} 已服刑期满，剥夺牢房权限，遣送回宫！")
    except Exception as e:
        print(f"【移除牢房权限失败】{e}")

# ==================== 4. 核心事件与裁决 ====================
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
                
                # 1. 抹杀原罪臣发言
                try:
                    await message.delete()
                except:
                    pass

                # 2. 真实系统级禁言 (Timeout)
                try:
                    解除禁言时间 = datetime.now(timezone.utc) + timedelta(minutes=分钟)
                    await message.author.timeout(解除禁言时间, reason=f"大周刑部判决：{刑罚}")
                except Exception as e:
                    print(f"【禁言执行失败】{e}")

                # 3. 授予私密隔离牢房权限并押送
                try:
                    牢房频道 = 内侍省.get_channel(禁闭牢房ID)
                    if 牢房频道:
                        # 赋予该犯臣查看和发言权限
                        await 牢房频道.set_permissions(message.author, read_messages=True, send_messages=True, reason="押入私密隔离牢房")
                        await 牢房频道.send(f"🚨 **【押解入狱】** 犯臣 {message.author.mention} 犯下 `{刑罚}`，被女王陛下打入私密牢房禁闭 {分钟} 分钟！(原奏：{message.content})")
                        
                        # 启动后台计时，刑满后自动释放
                        内侍省.loop.create_task(执行刑满释放(message.author, 牢房频道, 分钟))
                except Exception as e:
                    print(f"【私密牢房权限赋予失败】{e}")

                # 4. 在总大殿留下审判公告
                正式宣判文书 = (
                    f"{AI结果.get('response_text')}\n\n"
                    f"👑 **【御前雷霆裁决】** 犯臣 {message.author.mention} 犯下 `{刑罚}`，**已被剥夺大殿发言权并打入私密 #絕對隔離牢房 禁闭 {分钟} 分钟**！\n"
                    f"📋 案卷已归档（累计犯罪 {档案['累犯次数']} 次，总计服刑 {档案['关押总时长分钟']} 分钟）。"
                )
                await message.channel.send(正式宣判文书)
                return
            else:
                await message.channel.send(AI结果.get("response_text"))
                return
        await 内侍省.process_commands(message)
    except Exception as e:
        print(f"【异常】{e}")

# ==================== 5. 异步 Web 保活服务 ====================
async def 首页响应(request):
return web.Response(text="The Supreme Queen's Court is active.")

   # ==========================================
# 【大周新政：八月宵禁、黑牢与黎明审判独立增量模块】
# ==========================================

from datetime import datetime, time
from discord.ext import tasks

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
   
async def 主程序():
    app = web.Application()
    app.router.add_get('/', 首页响应)
    runner = web.AppRunner(app)
    await runner.setup()
    
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    print(f"【Web服务】已成功绑定端口 {port}")

    print("【Discord Bot】正在连接服务器...")
    async with 内侍省:
        await 内侍省.start(秘钥令牌)

if __name__ == "__main__":
    if not 秘钥令牌:
        print("【错误】未找到 DISCORD_TOKEN 环境变量！")
    else:
       
        asyncio.run(主程序())
