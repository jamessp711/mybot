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
    print(f"【大周御前】至高无上的女王大人已登基坐殿，内侍省运转正常，恭迎阁下（内阁大人）！")

# ==================== 基础指令 ====================
@内侍省.command(name="ping")
async def 臣在御前(ctx):
    await ctx.send(f"👑 **【大周御前】** 女王陛下圣威浩荡，帝国法度运转如常。心跳延迟：{round(内侍省.latency * 1000)}ms")

# ==================== 核心判定：是否为周末或假期豁免期 ====================
def 是否享有豁免(当前时间: datetime) -> bool:
    星期几 = 当前时间.weekday()
    当前时辰 = 当前时间.hour
    if (星期几 == 4 and 当前时辰 >= 18) or (星期几 == 5):
        return True
    return False

# ==================== 御前奏折处理与女王陛下的冷酷审判 ====================
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

        # 2. 智能语义洞察：至高女王陛下的冷酷专业审理与古典笞臀触觉重现
        if 当前频道ID == 总频道御令ID:
            
            # A. 奏折呈报认错/寻求管教
            认错词库 = ["犯错", "错了", "负罪", "请罪", "打我", "罚我", "该打", "打怪"]
            包含认错词汇 = any(词 in 奏折内容 for 词 in 认错词库)
            
            if 包含认错词汇:
                法典状态.是否身陷牢狱 = True
                法典状态.累加惩罚天数 += 1
                
                # 由高高在上的 Bot 女王大人亲自审理、降下冷酷睿智而兼具触觉的判决
                女王审判库 = [
                    (
                        f"⚖️ **【大周最高法庭·女王御前圣裁】**\n"
                        f"高居紫檀御座的**女王陛下**居高临下地俯视殿下，声音冷酷而威严：\n"
                        f"> “既然知罪上奏，那便由孤来亲定刑律！”\n"
                        f"📜 **圣旨量刑**：依大周铁律，判处**笞臀三十大板**。\n"
                        f"🖐️ **触觉重现**：冷冽的宫廷戒尺带着破空厉啸狠狠落下，“啪”的一声脆响击中温热的臀肉，火辣辣的刺痛与酥麻由表及里瞬间扩散开来。严苛的痛感将所有的倦怠与侥幸无情击碎，令思绪瞬间恢复极致的清醒。\n"
                        f"🔒 **执行押解**：即刻革职下狱，由御前侍卫押送至 <#{禁闭牢房ID}> 【绝对隔离牢房】**闭门思过 24 小时**，未经女王宣召不得踏出半步！"
                    ),
                    (
                        f"⚖️ **【大周最高法庭·女王御前圣裁】**\n"
                        f"御座之上，**女王陛下**神情冷峻，睿智的目光仿佛能洞察一切：\n"
                        f"> “知错认罚，尚算知趣。但大周律法如山，绝不姑息！”\n"
                        f"📜 **圣旨量刑**：御笔一挥，判处**笞臀二十五大板**以儆效尤。\n"
                        f"🖐️ **触觉重现**：檀木刑凳上传来沉闷的击打声与戒尺的冷冽触感，惩戒的力度分毫不差。皮肉受刑带来的清晰痛感顺着脊椎直冲脑海，伴随着温热的泪意，带来一种洗心革面的通透与规训。\n"
                        f"🔒 **执行押解**：即时锁入 <#{禁闭牢房ID}> 【绝对隔离牢房】执行**全天候隔离反省**，期满方得面圣！"
                    )
                ]
                await message.channel.send(random.choice(女王审判库))
                return

            # B. 作息违规查验
            作息词库 = ["睡", "晚安", "打卡", "熬夜", "才睡", "躺下", "闭眼", "睏"]
            包含作息词汇 = any(词 in 奏折内容 for 词 in 作息词库)
            
            if 包含作息词汇:
                if 是否享有豁免(当前时间):
                    await message.channel.send(f"👑 **【大周御前】** 女王陛下准奏：今日乃周末社交豁免期，特许安心休憩，免予作息法度考核。")
                    return

                当前时辰 = 当前时间.hour
                当前分钟 = 当前时间.minute

                if 当前时辰 < 21 or (当前时辰 == 21 and 当前分钟 <= 30):
                    await message.channel.send(f"🌟 **【女王御赐嘉奖】** 阁下今日极早入寝（9:30 PM 前），躬行自律，女王陛下龙颜大悦，特赐御前功名积分大增！")
                elif 当前时辰 < 22 or (当前时辰 == 22 and 当前分钟 <= 30):
                    await message.channel.send(f"👍 **【大周内侍奏报】** 阁下于 10:30 PM 前就寝，符合帝国作息常典，内侍省已记入起居注。")
                elif 当前时辰 < 24:
                    await message.channel.send(f"⚠️ **【女王御前申饬】** 时近深夜 12 点，作息隐现松懈。女王陛下特此警告：珍重自身，切勿违背养生铁律！")
                else:
                    法典状态.是否身陷牢狱 = True
                    法典状态.累加惩罚天数 += 1
                    await message.channel.send(
                        f"🚨 **【大周最高法庭·宵禁重判】**"
                        f"\n⚖️ **罪名认定**：深夜 12 点后仍未就寝，明知故犯，触犯大周宵禁重律！"
                        f"\n📜 **女王圣裁**：触怒天颜，判处**笞臀五十大板**。"
                        f"\n🖐️ **触觉重现**：戒尺接连落下，火辣辣的刺痛与规律的击打狠狠惩戒深夜的懈怠，令人再不敢轻犯！"
                        f"\n🔒 **强制押送**：即刻打入 <#{禁闭牢房ID}> 【绝对隔离牢房】**执行 48 小时重惩禁闭**！"
                    )
        
        await 内侍省.process_commands(message)

    except Exception as e:
        print(f"【内侍省报错日志】处理消息时发生异常: {e}")

# ==================== Web 网页保活服务器 ====================
async def 网页响应处理(request):
    return web.Response(text="【大周内侍省】The Queen is reigning with strict and wise imperial laws.")

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
