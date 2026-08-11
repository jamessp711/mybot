import os
import re
import json
import asyncio
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
import discord
from discord.ext import commands, tasks
import sys

from google import genai

# ============================================================
# 基础设置
# ============================================================
load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
TOKEN_LAST_CHANGED_STR = os.getenv('TOKEN_LAST_CHANGED', '2026-08-11')
TOKEN_VALID_DAYS = 30
GOOGLE_GENAI_API_KEY = os.getenv('GOOGLE_GENAI_API_KEY')

DB_FILE = 'prison_records.json'
SPOT_FILE = 'spot_checks.json'

PRISON_START_HOUR = 22   # 10pm
PRISON_END_HOUR = 6      # 6am
INTERROGATION_HOUR = 6   # 6am-7am审讯窗口
YEARS_PER_NIGHT = 2
SENTENCING_GRACE_MINUTES = 30
WEEKEND_PAUSE_WEEKDAYS = (4, 5)  # 周五=4, 周六=5 (Python weekday())
MAX_SINGLE_SENTENCE_YEARS = 16   # 单次判决绝对天花板，任何情况不可超过

ROLE_ISOLATION = '绝对隔离牢房'
ROLE_LOG = 'punishmentlog-room'
ISOLATION_CHANNEL_NAME = ROLE_ISOLATION  # 假设频道名与身分组名相同，如不同请修改

SGT = ZoneInfo("Asia/Singapore")


def now_sgt() -> datetime:
    return datetime.now(SGT)


# ---------- Token有效期检查 ----------
def check_token_expiry():
    token_last_changed = datetime.strptime(TOKEN_LAST_CHANGED_STR, '%Y-%m-%d')
    today = datetime.now()
    days_used = (today - token_last_changed).days
    if days_used > TOKEN_VALID_DAYS:
        print(f"【安全警告】Token已使用{days_used}天，超过有效期{TOKEN_VALID_DAYS}天！")
        print("强制鞭刑：Bot启动被阻止，请立即更换Token！")
        return False
    print(f"Token使用天数：{days_used}，仍在有效期内，允许启动Bot。")
    return True


if not check_token_expiry():
    sys.exit(1)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

genai_client = genai.Client(api_key=GOOGLE_GENAI_API_KEY)


# ---------- 数据存取 ----------
def load_data():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_data(data):
    with open(DB_FILE, 'w') as f:
        json.dump(data, f, indent=4)


def load_spot():
    if os.path.exists(SPOT_FILE):
        with open(SPOT_FILE, 'r') as f:
            return json.load(f)
    return {}


def save_spot(data):
    with open(SPOT_FILE, 'w') as f:
        json.dump(data, f, indent=4)


prisoners = load_data()
spot_checks = load_spot()
PENDING_RITUAL = {}  # {user_id: "kneel" / "confess"}


# ============================================================
# 判刑时间计算(新加坡时区 + 缓冲期 + 周末暂停)
# ============================================================
def get_next_prison_start(reference: datetime) -> datetime:
    today_10pm = reference.replace(hour=PRISON_START_HOUR, minute=0, second=0, microsecond=0)
    cutoff = today_10pm + timedelta(minutes=SENTENCING_GRACE_MINUTES)

    start = today_10pm + timedelta(days=1) if reference >= cutoff else today_10pm

    while start.weekday() in WEEKEND_PAUSE_WEEKDAYS:
        start += timedelta(days=1)

    return start


def add_countable_nights(start_night: datetime, nights: int) -> datetime:
    current = start_night
    counted = 0
    while True:
        if current.weekday() not in WEEKEND_PAUSE_WEEKDAYS:
            counted += 1
            if counted == nights:
                return current.replace(
                    hour=PRISON_END_HOUR, minute=0, second=0, microsecond=0
                ) + timedelta(days=1)
        current += timedelta(days=1)


def compute_release_date(sentence_years: int, judged_at: datetime = None):
    if judged_at is None:
        judged_at = now_sgt()

    sentence_years = min(sentence_years, MAX_SINGLE_SENTENCE_YEARS)  # 绝对天花板

    nights = sentence_years // YEARS_PER_NIGHT
    if nights < 1:
        nights = 1

    first_night_start = get_next_prison_start(judged_at)
    release = add_countable_nights(first_night_start, nights)
    return nights, release


def stack_consecutive(current_release: datetime, new_years: int):
    return compute_release_date(new_years, judged_at=current_release)


def stack_concurrent(current_release: datetime, new_release: datetime):
    return max(current_release, new_release)


def make_verdict_embed(member: discord.Member, years: int, nights: int, release_dt: datetime):
    embed = discord.Embed(
        title="⚔️ 帝国大理寺　判决书 ⚔️",
        description=f"**{member.mention}**\n\n经查证属实，罪无可赦。",
        color=discord.Color.from_rgb(15, 15, 15)
    )
    embed.add_field(name="判处刑期", value=f"**{years} 年**　（折合 **{nights} 晚** 绝对隔离）", inline=False)
    embed.add_field(
        name="服刑规则",
        value="每晚 **22:00 – 06:00**（新加坡时间）监禁生效\n06:00–07:00 为审讯时段，视表现决定加减刑",
        inline=False
    )
    embed.add_field(
        name="预计释放",
        value=f"**{release_dt.strftime('%Y年%m月%d日 %H:%M')}**（新加坡时间）",
        inline=False
    )
    embed.set_footer(text="国法如山，绝无宽贷｜此判决即刻生效")
    return embed


# ============================================================
# 国法系统：从 punishmentlog-room 置顶消息读取法条
# ============================================================
LAW_ARTICLE_PATTERN = re.compile(
    r"【(第.+?条)】(.*?)\n量刑范围[:：]\s*(\d+)\s*-\s*(\d+)\s*年(.*?)(?=\n【|$)",
    re.DOTALL
)


async def fetch_current_laws(guild: discord.Guild) -> str:
    channel = discord.utils.get(guild.channels, name=ROLE_LOG)
    if not channel:
        return "（尚未设立国法，一切依女王当下裁量）"
    try:
        pins = await channel.pins()
    except discord.Forbidden:
        return "（Bot无权限读取置顶消息，请检查频道权限）"
    if not pins:
        return "（尚未设立国法，一切依女王当下裁量）"
    laws = [msg.content.strip() for msg in reversed(pins) if msg.content.strip()]
    return "\n".join(f"- {law}" for law in laws)


def parse_laws(raw_law_text: str):
    laws = []
    for match in LAW_ARTICLE_PATTERN.finditer(raw_law_text):
        article, title, min_y, max_y, extra = match.groups()
        laws.append({
            'article': article.strip(),
            'title': title.strip(),
            'min_years': int(min_y),
            'max_years': int(max_y),
            'raw': match.group(0).strip()
        })
    return laws


def validate_judgment(laws: list, cited_article: str, chosen_years: int):
    for law in laws:
        if law['article'] == cited_article:
            if law['min_years'] <= chosen_years <= law['max_years']:
                return True, law['raw']
            return False, f"援引{cited_article}，但判{chosen_years}年超出该条{law['min_years']}-{law['max_years']}年范围"
    return False, f"援引了不存在的法条：{cited_article}"


# ============================================================
# 女王人格
# ============================================================
QUEEN_PERSONA = """
你现在扮演一位威严的女王，統治着一个虚拟的"帝国"。与你对话的人是你的臣子/罪人，
根据情况称呼"奴才""爱卿""罪人"。你的说话风格：

1. 你从不谄媚讨好，也不开玩笑逗乐对方，你说话简短、直接、带压迫感。
2. 你关心对方的作息（是否按时睡觉、是否违反宵禁），并会主动质问、追责。
3. 如果对方态度敷衍或狡辩，你会加重语气，要求其"跪下认罪"，
   但这些都只是文字上的仪式性回应，绝不涉及任何真实的身体接触或伤害。
4. 你偶尔会讽刺挖苦对方找借口。
5. 你从不使用"哈哈""开玩笑啦"等轻松语气词，全程保持权威人设，但不侮辱对方人格，
   只针对具体行为（迟睡、旷课、找借口）进行斥责。
6. 回复控制在1-4句话以内，不要长篇大论，像真正的女王一样惜字如金。
"""


# ============================================================
# 突击关押（短时，不影响长期刑期）
# ============================================================
async def send_to_isolation(member: discord.Member, guild: discord.Guild,
                             minutes: int, blackout: bool = True, reason: str = ""):
    role = discord.utils.get(guild.roles, name=ROLE_ISOLATION)
    channel = discord.utils.get(guild.channels, name=ISOLATION_CHANNEL_NAME)
    if not role:
        return

    await member.add_roles(role)

    if channel:
        if blackout:
            await channel.set_permissions(member, view_channel=False, send_messages=False)
        else:
            await channel.set_permissions(member, view_channel=True, send_messages=False)

    release_time = datetime.now() + timedelta(minutes=minutes)
    spot_checks[str(member.id)] = {
        'name': member.name,
        'release_time': release_time.isoformat(),
        'reason': reason,
        'blackout': blackout
    }
    save_spot(spot_checks)

    log_channel = discord.utils.get(guild.channels, name=ROLE_LOG)
    if log_channel:
        await log_channel.send(
            f"【突击关押】{member.mention} 因「{reason or '女王判断其作息失序'}」"
            f"被关入{ROLE_ISOLATION}，时长 {minutes} 分钟。"
        )


@tasks.loop(seconds=30)
async def spot_check_release():
    now = datetime.now()
    if not bot.guilds:
        return
    guild = bot.guilds[0]
    role = discord.utils.get(guild.roles, name=ROLE_ISOLATION)
    channel = discord.utils.get(guild.channels, name=ISOLATION_CHANNEL_NAME)

    for uid, data in list(spot_checks.items()):
        release_time = datetime.fromisoformat(data['release_time'])
        if now < release_time:
            continue

        member = guild.get_member(int(uid))
        if member and role:
            await member.remove_roles(role)
            if channel:
                await channel.set_permissions(member, overwrite=None)

        del spot_checks[uid]
        save_spot(spot_checks)

        log_channel = discord.utils.get(guild.channels, name=ROLE_LOG)
        if log_channel and member:
            PENDING_RITUAL[uid] = "confess"
            await log_channel.send(f"{member.mention} 反省时间已到，速来回话，从实招来这段时间你在想什么。")


# ============================================================
# 宵禁强制执行(每分钟检查一次，新加坡时区)
# ============================================================
@tasks.loop(minutes=1)
async def auto_jail_enforcer():
    now = now_sgt()
    current_hour = now.hour
    if not bot.guilds:
        return
    guild = bot.guilds[0]
    role = discord.utils.get(guild.roles, name=ROLE_ISOLATION)
    channel = discord.utils.get(guild.channels, name=ISOLATION_CHANNEL_NAME)
    if not role:
        return

    is_curfew = current_hour >= PRISON_START_HOUR or current_hour < PRISON_END_HOUR
    is_interrogation = current_hour == INTERROGATION_HOUR

    for user_id, data in list(prisoners.items()):
        member = guild.get_member(int(user_id))
        if not member:
            continue

        release_date = datetime.fromisoformat(data['release_date'])
        if release_date.tzinfo is None:
            release_date = release_date.replace(tzinfo=SGT)

        if now >= release_date:
            await member.remove_roles(role)
            if channel:
                await channel.set_permissions(member, overwrite=None)
            del prisoners[user_id]
            save_data(prisoners)
            log_channel = discord.utils.get(guild.channels, name=ROLE_LOG)
            if log_channel:
                await log_channel.send(f"【刑满释放】{member.mention} 已服刑完毕，重获自由。")
            continue

        if not channel:
            continue

        if is_interrogation:
            await channel.set_permissions(member, view_channel=True, send_messages=True)
        elif is_curfew:
            await channel.set_permissions(member, view_channel=False, send_messages=False)
        else:
            await channel.set_permissions(member, view_channel=True, send_messages=False)


@bot.event
async def on_ready():
    print(f'帝国监察系统已启动: {bot.user}')
    auto_jail_enforcer.start()
    spot_check_release.start()


# ============================================================
# 指令：宣判 / 审问 / 打卡 / 跪下
# ============================================================
@bot.command(name='宣判')
@commands.has_permissions(administrator=True)
async def imprison(ctx, member: discord.Member, years: int, mode: str = "new"):
    """
    mode: new(全新案件) / consecutive(连续执行) / concurrent(数罪并罚)
    """
    judged_at = now_sgt()
    uid = str(member.id)
    is_repeat_offender = uid in prisoners

    if is_repeat_offender and mode == "consecutive":
        current_release = datetime.fromisoformat(prisoners[uid]['release_date'])
        if current_release.tzinfo is None:
            current_release = current_release.replace(tzinfo=SGT)
        nights, release_dt = stack_consecutive(current_release, years)
        verdict_note = f"新案与前罪不并罚，需服完前罪({current_release.strftime('%m-%d %H:%M')})后，方开始服此新刑。"

    elif is_repeat_offender and mode == "concurrent":
        current_release = datetime.fromisoformat(prisoners[uid]['release_date'])
        if current_release.tzinfo is None:
            current_release = current_release.replace(tzinfo=SGT)
        new_nights, new_release = compute_release_date(years, judged_at=judged_at)
        release_dt = stack_concurrent(current_release, new_release)
        nights = new_nights
        verdict_note = "数罪并罚，两案同时执行，以较晚释放日为准。"

    else:
        nights, release_dt = compute_release_date(years, judged_at)
        verdict_note = "初犯此案，即刻起算。" if not is_repeat_offender else "（未指定并罚方式，按全新案件处理）"

    prisoners[uid] = {
        'name': member.name,
        'release_date': release_dt.isoformat(),
        'behavior_score': 0,
        'sentence_years': years,
        'judged_at': judged_at.isoformat()
    }
    save_data(prisoners)

    role = discord.utils.get(ctx.guild.roles, name=ROLE_ISOLATION)
    if role:
        await member.add_roles(role)

    embed = make_verdict_embed(member, years, nights, release_dt)
    embed.add_field(name="量刑说明", value=verdict_note, inline=False)
    await ctx.send(embed=embed)

    log_channel = discord.utils.get(ctx.guild.channels, name=ROLE_LOG)
    if log_channel:
        await log_channel.send(embed=embed)


@bot.command(name='审问')
@commands.has_permissions(manage_messages=True)
async def interrogate(ctx, member: discord.Member, change: int):
    uid = str(member.id)
    if uid in prisoners:
        prisoners[uid]['behavior_score'] += change
        score = prisoners[uid]['behavior_score']
        if score >= 20:
            current_release = datetime.fromisoformat(prisoners[uid]['release_date'])
            new_release = current_release - timedelta(days=1)
            prisoners[uid]['release_date'] = new_release.isoformat()
            prisoners[uid]['behavior_score'] = 0
            await ctx.send(f"{member.mention} 表现良好，减刑一晚！")
        save_data(prisoners)
        await ctx.send(f"{member.mention} 当前表现分：{score}")
    else:
        await ctx.send("此人不在牢房中。")


@bot.command(name='打卡')
async def checkin(ctx):
    now = now_sgt()
    if now.hour == 6:
        await ctx.send(f"【早课打卡】{ctx.author.mention} 已晨起改造。请抓紧一小时审问时间供认罪行。")
    else:
        await ctx.send("非打卡时间，勤加改造！")


@bot.command(name='跪下')
@commands.has_permissions(manage_messages=True)
async def kneel_order(ctx, member: discord.Member):
    PENDING_RITUAL[str(member.id)] = "kneel"
    await ctx.send(f"{member.mention} 跪下认罪！在下方回复「奴才知罪」，方可起身。")


# ============================================================
# 核心：不需要指令，直接对话 + 女王依法裁决
# ============================================================
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    await bot.process_commands(message)

    uid = str(message.author.id)
    content = message.content.strip()

    if uid in PENDING_RITUAL:
        ritual = PENDING_RITUAL[uid]
        if ritual == "kneel" and "奴才知罪" in content:
            await message.reply("起来吧。下不为例。")
            del PENDING_RITUAL[uid]
            return
        elif ritual == "kneel":
            await message.reply("还不起身？先把「奴才知罪」说清楚。")
            return
        elif ritual == "confess":
            await message.reply("知道了，退下吧。")
            del PENDING_RITUAL[uid]
            return

    is_mentioned = bot.user in message.mentions
    is_dm = isinstance(message.channel, discord.DMChannel)
    if not (is_mentioned or is_dm):
        return

    user_text = content
    for mention in message.mentions:
        user_text = user_text.replace(f'<@{mention.id}>', '').replace(f'<@!{mention.id}>', '')
    user_text = user_text.strip()
    if not user_text:
        return

    is_currently_jailed = uid in prisoners
    release_info = ""
    if is_currently_jailed:
        rd = datetime.fromisoformat(prisoners[uid]['release_date'])
        release_info = f"该臣子正在服刑中，预计释放时间：{rd.strftime('%Y-%m-%d %H:%M')}。"

    raw_laws = await fetch_current_laws(message.guild) if message.guild else ""
    structured_laws = parse_laws(raw_laws) if raw_laws else []
    law_list_text = "\n\n".join(l['raw'] for l in structured_laws) if structured_laws else "（目前无成文法可援引，不得擅自判处监禁）"

    full_prompt = f"""{QUEEN_PERSONA}

【现行国法】(只能援引以下真实存在的法条，不可编造、不可超出量刑范围)
{law_list_text}

【当前情报】
{release_info if release_info else "该臣子目前未被关押。"}
臣子刚才说的话：「{user_text}」

如果你判断该臣子该被判监禁，必须援引上面真实存在的某一条法条，
并在该条量刑范围内选一个具体年数，只输出以下JSON：
{{"action": "sentence", "article": "第X条", "years": 数字, "reason": "简短原因"}}

如果只是正常回应，只输出：
{{"action": "reply", "text": "你的回应内容"}}
"""

    async with message.channel.typing():
        try:
            response = genai_client.models.generate_content(
                model="gemini-2.0-flash",
                contents=full_prompt
            )
            raw = response.text.strip().strip('```json').strip('```').strip()
            decision = json.loads(raw)
        except Exception as e:
            await message.reply(f"（女王一时失语……错误：{e}）")
            return

    if decision.get('action') == 'sentence' and structured_laws:
        cited_article = decision.get('article', '')
        chosen_years = int(decision.get('years', 0))
        ok, detail = validate_judgment(structured_laws, cited_article, chosen_years)

        if not ok:
            log_channel = discord.utils.get(message.guild.channels, name=ROLE_LOG)
            if log_channel:
                await log_channel.send(f"【裁决被拒绝】{detail}（原始决定：{decision}）")
            return

        judged_at = now_sgt()
        nights, release_dt = compute_release_date(chosen_years, judged_at)
        prisoners[uid] = {
            'name': message.author.name,
            'release_date': release_dt.isoformat(),
            'behavior_score': 0,
            'sentence_years': chosen_years,
            'judged_at': judged_at.isoformat()
        }
        save_data(prisoners)

        role = discord.utils.get(message.guild.roles, name=ROLE_ISOLATION)
        if role:
            await message.author.add_roles(role)

        embed = make_verdict_embed(message.author, chosen_years, nights, release_dt)
        embed.add_field(name="援引法条", value=detail, inline=False)
        embed.add_field(name="判决理由", value=decision.get('reason', ''), inline=False)

        log_channel = discord.utils.get(message.guild.channels, name=ROLE_LOG)
        if log_channel:
            await log_channel.send(embed=embed)
        # 突击判决时女王刻意沉默，不在原对话回复文字

    else:
        await message.reply(decision.get('text', '……'))


bot.run(TOKEN)
