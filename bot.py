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
    return "大周內侍省・無光墨牢運作中，女王威嚴永存，绝不容许任何欺瞒与儿戏。"

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

# ==================== 3. 大周铁律与审判核心引擎（英文高压排版） ====================
async def analyze_and_judge_crime(member: discord.Member, user_message: str) -> dict:
    now = datetime.datetime.now()
    current_month = now.month
    current_hour = now.hour
    current_weekday = now.weekday()
    
    # 8月份时空与休沐宵禁铁律
    is_august = (current_month == 8)
    is_curfew = (current_hour >= 22 or current_hour < 6)
    is_holiday_or_weekend = (current_weekday >= 5)
    
    time_crime_flag = False
    crime_desc = "Standard Imperial Scrutiny"
    
    if is_august:
        if is_curfew:
            time_crime_flag = True
            time_crime_desc = "Defiance of Imperial Curfew & Night Wandering"
        elif is_holiday_or_weekend:
            time_crime_flag = True
            time_crime_desc = "Disturbing Imperial Rest & Holiday Desecration"

    # 深度语义剖析：若字里行间带有敷衍、欺瞒、不敬或把大周当儿戏，直接顶格重判！
    keywords = ["玩", "随便", "开玩笑", "不小心", "game", "play"]
    is_deceitful_or_playful = any(word in user_message for word in keywords)

    if time_crime_flag:
        category = "时空重罪"
        crime_name = time_crime_desc
        timeout_mins = 20
        new_nick = "罪奴-休沐重犯"
        punishment_desc = "1. IMMEDIATE ISOLATION (⛓️ 絕對隔離)\n2. PUNISHMENT OF THE FLESH (🍑 嚴厲鞭刑 / 打屁股)\n3. IMPERIAL CURFEW BREACH PENALTY"
    elif is_deceitful_or_playful:
        category = "欺君犯上"
        crime_name = "Treating the Imperial Court as a Playground"
        timeout_mins = 15
        new_nick = "罪奴-轻浮待罪"
        punishment_desc = "1. SEVERE REPRIMAND FOR ARROGANCE\n2. MENTAL RESTRAINT & SILENCING\n3. STRIPPING OF ALL PRIVILEGES"
    elif "肺腑" in user_message or "安" in user_message or "顺从" in user_message:
        category = "肺腑顺从"
        crime_name = "Sincere Confession & Submission"
        timeout_mins = 0
        new_nick = None
        punishment_desc = "1. TEMPORARY ABSOLUTION\n2. RECORDED SUBMISSION"
    else:
        category = "触犯家法"
        crime_name = "Lack of Proper Respect & Discipline"
        timeout_mins = 5
        new_nick = "罪奴-思过中"
        punishment_desc = "1. ROUTINE DISCIPLINARY STICKS\n2. MANDATORY REFLECTION"

    return {
        "category": category,
        "crime_name": crime_name,
        "timeout_minutes": timeout_mins,
        "new_nick": new_nick,
        "punishment_desc": punishment_desc
    }

# ==================== 4. 全局监听与中央档案库同步执行 ====================
@bot.event
async def on_ready():
    print(f'大周女王化身已顺利降临: {bot.user.name} (ID: {bot.user.id})')
    print('大周高级铁律审判庭已全线激活。')

@bot.event
async def on_message(message: discord.Message):
    if message.author == bot.user:
        return

    ruling = await analyze_and_judge_crime(message.author, message.content)
    
    category = ruling.get("category")
    crime_name = ruling.get("crime_name")
    timeout_mins = ruling.get("timeout_minutes", 0)
    new_nick = ruling.get("new_nick")
    punishment_desc = ruling.get("punishment_desc")
    
    # 构造极具压迫感的英文高压判词表格
    response_text = f"```ansi\n" \
                    f"\u001b[1;31m[ROYAL HIGH COURT OF AUTODISCIPLINE] — ISOLATION & SENTENCING\u001b[0m\n" \
                    f"--------------------------------------------------\n" \
                    f"IN THE HIGH COURT OF THE GREAT ZHOU INTERNAL AFFAIR\n" \
                    f"--------------------------------------------------\n" \
                    f"CASE: {crime_name}\n" \
                    f"CONVICT: {message.author.mention} (Alias: {message.author.name})\n" \
                    f"OFFENDING CHANNEL: {message.channel.mention}\n" \
                    f"--------------------------------------------------\n" \
                    f"THE COURT HEREBY DECREES THE FOLLOWING JUDGMENT:\n\n" \
                    f"{punishment_desc}\n" \
                    f"--------------------------------------------------\n" \
                    f"EXECUTION OF SENTENCE: ACTIVE NOW.\n" \
                    f"--------------------------------------------------\n" \
                    f"Time will not heal your defiance; only complete submission shall purge your weakness.\n" \
                    f"```"

    # 1. 執行耻辱改名
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
            await message.author.timeout(delta, reason="触犯大周高级铁律")
            response_text += f"\n🔒 **黑牢禁闭**：已被执行 Timeout 禁言 {timeout_mins} 分钟！"
        except Exception as e:
            print(f"禁言失败: {e}")

    # 3. 判定是否打入「絕對隔離犯人」黑牢
    if "重罪" in category or "犯上" in category or "家法" in category:
        try:
            target_role = discord.utils.get(message.guild.roles, name="【絕對隔離犯人】")
            if target_role:
                await message.author.add_roles(target_role)
                response_text += f"\n⛓️ **终极牢狱**：已被打入【絕對隔離犯人】重犯行列！"
        except Exception as e:
            print(f"加锁失败: {e}")

    # 4. 全局核心：强制将判决书推送到 punishmentlog-room 中
    log_channel = discord.utils.get(message.guild.text_channels, name="punishmentlog-room")
    if log_channel:
        await log_channel.send(response_text)
    else:
        await message.channel.send(response_text)

    await bot.process_commands(message)

# ==================== 5. 启动总闸 ====================
if __name__ == "__main__":
    keep_alive()
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("错误：未检测到 DISCORD_TOKEN 环境变量！")
    else:
        bot.run(TOKEN)
