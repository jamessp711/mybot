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

# 基础行为数值与心境模拟
BEHAVIOR_SCORE = 50

def get_mood_instruction():
    if BEHAVIOR_SCORE < 30:
        return "极度暴怒、冷酷至极。对于罪奴的任何狡辩与敷衍，必施以雷霆万钧之重罚。"
    elif BEHAVIOR_SCORE < 60:
        return "高傲、居高临下、不屑一顾。将罪奴视作毫无尊严的提线玩偶。"
    else:
        return "威严、冷漠，时刻审视罪奴是否有得过且过的心思。"

# ==================== 3. 大周铁律与时空审判核心引擎 ====================
async def analyze_and_judge_crime(member: discord.Member, user_message: str) -> dict:
    now = datetime.datetime.now()
    current_month = now.month
    current_hour = now.hour
    current_weekday = now.weekday() # 0-6 周一到周日
    
    # 时空铁律：8月份全天候开放，但严打休沐与宵禁违抗
    is_august = (current_month == 8)
    is_curfew = (current_hour >= 22 or current_hour < 6)
    is_holiday_or_weekend = (current_weekday >= 5) # 周六、周日
    
    time_crime_flag = False
    time_crime_desc = ""
    
    if is_august:
        if is_curfew:
            time_crime_flag = True
            time_crime_desc = "触犯宵禁密令罪：深夜游荡，妄图逃避管教"
        elif is_holiday_or_weekend:
            time_crime_flag = True
            time_crime_desc = "扰乱圣驾休沐罪：胆敢在法定假日/周日私闯公堂、得过且过"

    # 深度语义剖析：若字里行间带有敷衍、欺瞒、不敬或把大周当儿戏，直接顶格重判！
    is_deceitful_or_playful = any(word in user_message for: "玩" in user_message or "随便" in user_message or "开玩笑" in user_message or "不小心" in user_message)

    if time_crime_flag:
        category = "时空重罪"
        crime_name = time_crime_desc
        sentence = f"放肆！大周不是你的游乐场，竟敢在「{crime_name}」之时段冒犯圣驾，罪加一等，绝不姑息！"
        duration_minutes = 40
        timeout_minutes = 20
        new_nick = "罪奴-休沐重犯"
        punishment_type = "大板鞭刑、剥去外衣、赤裸示众与耻辱烙印"
    elif is_deceitful_or_playful:
        category = "欺君犯上"
        crime_name = "视大周如儿戏、态度轻浮"
        sentence = "好大的狗胆！把本宫的御前公堂当成什么地方？竟敢抱有得过且过的心思，给本宫彻底清醒过来！"
        duration_minutes = 30
        timeout_minutes = 15
        new_nick = "罪奴-轻浮待罪"
        punishment_type = "笞刑三十、剥除一切伪装与禁言反省"
    elif "肺腑" in user_message or "安" in user_message or "顺从" in user_message:
        category = "肺腑顺从"
        crime_name = "深刻剖白与服从"
        sentence = "准奏。这才是你身为卑贱罪奴该有的清醒认知，暂且记下你的顺从。"
        duration_minutes = 15
        timeout_minutes = 0
        new_nick = None
        punishment_type = "口头勉励，暂免皮肉之苦"
    else:
        category = "触犯家法"
        crime_name = "言辞不够恭顺、心存侥幸"
        sentence = "字里行间透着一股懒散与敷衍，看来平时的管教还是太轻了！"
        duration_minutes = 20
        timeout_minutes = 5
        new_nick = "罪奴-思过中"
        punishment_type = "杖责二十，加固精神枷锁"

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
    print('大周铁律已全面激活：严禁欺瞒、杜绝过场、中央刑名总库全天候运转。')

@bot.event
async def on_message(message: discord.Message):
    # 忽略 Bot 自身的发言
    if message.author == bot.user:
        return

    # 全局放行并抓取：在大周任何角落发言，皆受铁律审判
    ruling = await analyze_and_judge_crime(message.author, message.content)
    
    category = ruling.get("category")
    sentence = ruling.get("sentence")
    timeout_mins = ruling.get("timeout_minutes", 0)
    new_nick = ruling.get("new_nick")
    punishment = ruling.get("punishment_type")
    
    response_text = f"👑 **【大周御前中央刑名档案】** - 铁律圣裁下达\n" \
                    f"案发殿宇：{message.channel.mention}\n" \
                    f"罪奴：{message.author.mention}\n" \
                    f"罪名：`{ruling.get('crime_name')}`\n" \
                    f"判词：{sentence}\n" \
                    f"刑罚手段：{punishment}"

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
            await message.author.timeout(delta, reason="触犯大周铁律与防伪禁令")
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

    # 4. 全局核心机制：强制将所有判决与罪状同步推送到 punishmentlog-room 中
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
