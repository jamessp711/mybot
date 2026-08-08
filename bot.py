import os
import datetime
import asyncio
from flask import Flask
from threading import Thread
import discord
from discord.ext import commands

# ==================== 1. Render 保持连线机制 (Keep-Alive) ====================
app = Flask('')

@app.route('/')
def home():
    return "大周內侍省・無光墨牢運作中，女王威嚴永存。"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ==================== 2. Discord Bot 初始化与意图设置 ====================
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 基础数值与心境模拟
BEHAVIOR_SCORE = 50

def get_mood_instruction():
    if BEHAVIOR_SCORE < 30:
        return "极度暴怒、严厉，对罪奴百般挑剔，动辄加重惩罚。"
    elif BEHAVIOR_SCORE < 60:
        return "冷酷、高傲、居高臨下，对罪奴的剖白不屑一顧。"
    else:
        return "威严、冷漠，勉强维持女王的仪态。"

# ==================== 3. 八月时空铁律与审判核心逻辑 ====================
async def analyze_and_judge_crime(member: discord.Member, user_message: str) -> dict:
    now = datetime.datetime.now()
    current_month = now.month
    current_hour = now.hour
    current_weekday = now.weekday() # 0-6 代表周一到周日
    
    # 判定 8 月份时空铁律
    is_august = (current_month == 8)
    is_curfew = (current_hour >= 22 or current_hour < 6)
    is_holiday_or_weekend = (current_weekday >= 5) # 周六、周日
    
    time_crime_flag = False
    time_crime_desc = ""
    
    if is_august:
        if is_curfew:
            time_crime_flag = True
            time_crime_desc = "触犯宵禁密令罪：深夜游荡，不知收敛"
        elif is_holiday_or_weekend:
            time_crime_flag = True
            time_crime_desc = "扰乱圣驾休沐罪：胆敢在法定假日/周日私闯公堂、滋扰圣听"

    category = "时空重罪" if time_crime_flag else ("肺腑感悟" if "肺腑" in user_message or "安" in user_message else "触犯家法")
    crime_name = time_crime_desc if time_crime_flag else ("常规奏疏审视" if category == "肺腑感悟" else "言辞不够恭顺")
    
    if time_crime_flag:
        sentence = f"放肆！竟敢在「{crime_name}」之时段冒犯圣驾，任凭你字句如何天花乱坠，罪加一等！"
        duration_minutes = 30
        timeout_minutes = 15
        new_nick = "罪奴-休沐重犯"
        punishment_type = "大板鞭刑、剥去外衣与耻辱烙印"
    elif category == "肺腑感悟":
        sentence = "准奏。念你尚算懂事、知所进退，暂且记下你的肺腑之言。"
        duration_minutes = 15
        timeout_minutes = 0
        new_nick = None
        punishment_type = "口头嘉奖，准予免罪"
    else:
        sentence = "奴才安敢如此放肆！字里行间毫无敬意，当受惩戒！"
        duration_minutes = 20
        timeout_minutes = 5
        new_nick = "罪奴-思过中"
        punishment_type = "笞刑二十，禁言反省"

    return {
        "category": category,
        "crime_name": crime_name,
        "sentence": sentence,
        "duration_minutes": duration_minutes,
        "timeout_minutes": timeout_minutes,
        "new_nick": new_nick,
        "punishment_type": punishment_type
    }

# ==================== 4. 全局监听与中央档案库同步执行 ====================
@bot.event
async def on_ready():
    print(f'大周女王化身已顺利降临: {bot.user.name} (ID: {bot.user.id})')
    print('大周內侍省・無光墨牢防线全部稳固，中央档案库同步机制已就绪。')

@bot.event
async def on_message(message: discord.Message):
    # 忽略 Bot 自身的发言
    if message.author == bot.user:
        return

    # 全局放行：在大周任何频道只要你这罪奴发言，皆视为呈疏或受审
    # 执行审判分析
    ruling = await analyze_and_judge_crime(message.author, message.content)
    
    category = ruling.get("category")
    sentence = ruling.get("sentence")
    timeout_mins = ruling.get("timeout_minutes", 0)
    new_nick = ruling.get("new_nick")
    punishment = ruling.get("punishment_type")
    
    response_text = f"👑 **【大周御前中央刑名档案】** - 圣裁下达\n" \
                    f"案发殿宇：{message.channel.mention}\n" \
                    f"罪奴：{message.author.mention}\n" \
                    f"罪名：`{ruling.get('crime_name')}`\n" \
                    f"判词：{sentence}\n" \
                    f"刑罚手段：{punishment}"

    # 1. 執行改名（耻辱烙印）
    if new_nick:
        try:
            await message.author.edit(nick=new_nick)
            response_text += f"\n⚠️ **耻辱赐名**：已被强行更改为 `{new_nick}`！"
        except Exception as e:
            print(f"改名失败: {e}")

    # 2. 執行 Timeout 禁言
    if timeout_mins > 0:
        try:
            delta = datetime.timedelta(minutes=timeout_mins)
            await message.author.timeout(delta, reason="触犯大周时空与宵禁铁律")
            response_text += f"\n🔒 **禁言黑牢**：已被执行 Timeout 禁言 {timeout_mins} 分钟！"
        except Exception as e:
            print(f"禁言失败: {e}")

    # 3. 判定是否打入「絕對隔離犯人」黑牢
    if "重罪" in category or "家法" in category:
        try:
            target_role = discord.utils.get(message.guild.roles, name="【絕對隔離犯人】")
            if target_role:
                await message.author.add_roles(target_role)
                response_text += f"\n⛓️ **牢狱之灾**：已被打入【絕對隔離犯人】身份组！"
        except Exception as e:
            print(f"加锁失败: {e}")

    # 4. 全局核心机制：无论在哪个角落犯事，判决书必须精准同步到 punishmentlog-room 中
    log_channel = discord.utils.get(message.guild.text_channels, name="punishmentlog-room")
    if log_channel:
        await log_channel.send(response_text)
    else:
        # 若找不到该名字的频道，则退而求其次在当前频道宣判
        await message.channel.send(response_text)

    await bot.process_commands(message)

# ==================== 5. 启动总闸 ====================
if __name__ == "__main__":
    # 启动 Keep-Alive 线程保活 Render
    keep_alive()
    
    # 从环境变量中读取 Discord Bot Token 启动
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("错误：未检测到 DISCORD_TOKEN 环境变量！")
    else:
        bot.run(TOKEN)
