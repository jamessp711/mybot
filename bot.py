import datetime
import discord
from discord.ext import commands

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 频道名称定义
CONFESSION_ROOM = "罪奴忏悔牢"  # 8月份24小时常态开放特许频道
LOG_ROOM = "punishmentlog-room"  # 中央审判日志记录室


def is_curfew_time(dt: datetime.datetime) -> bool:
  """判定当前是否处于宵禁时间段：

  规则：周五早上至周日晚上 20:00 为宵禁/休假状态（禁止违规发言）。
  weekday(): 周一为0, 周五为4, 周日为6
  """
  weekday = dt.weekday()
  hour = dt.hour

  # 周五 (4) 全天禁言
  if weekday == 4:
    return True
  # 周六 (5) 全天禁言
  if weekday == 5:
    return True
  # 周日 (6) 晚上 20:00 之前禁言 (20点整及之后解禁)
  if weekday == 6 and hour < 20:
    return True

  return False


@bot.event
async def on_ready():
  print(f"大周化身 [{bot.user}] 已成功登基，铁律开始运转。")


@bot.event
async def on_message(message: discord.Message):
  # 严禁 Bot 自我审判触发死循环
  if message.author.bot:
    return

  channel_name = message.channel.name
  author_mention = message.author.mention
  timestamp = message.created_at  # 抓取消息的时间戳印

  # 1. 特许通道校验：如果是 `#罪奴忏悔牢`，8月份允许 24 小时常态畅通，不予宵禁拦截
  if channel_name == CONFESSION_ROOM:
    print(f"【特许放行】罪奴 {message.author} 在忏悔牢呈交言论。时间戳: {timestamp}")
    await bot.process_commands(message)
    return

  # 2. 宵禁与时间戳印判定逻辑
  if is_curfew_time(timestamp):
    # 如果在宵禁期间胆敢在其他频道（非忏悔牢）发言，直接判定违规！
    try:
      # 尝试抹杀违规言论
      await message.delete()
    except discord.Forbidden:
      pass

    # 寻找审判日志室（punishmentlog-room）进行铁证同步
    log_channel = discord.utils.get(
        message.guild.text_channels, name=LOG_ROOM
    )
    if log_channel:
      # 下达冰冷的审判判词与时间戳铁证
      await log_channel.send(
          f"🚨 **【大周宵禁违规铁证】**\n"
          f"- 违规罪奴：{author_mention}\n"
          f"- 越权频道：`#{channel_name}`\n"
          f"- 抓取时间戳：`{timestamp.strftime('%Y-%m-%d %H:%M:%S')}`\n"
          f"- 判词：周五至周日晚八点宵禁期间，擅自于非忏悔牢发言，罪加一等！"
      )
    return

  await bot.process_commands(message)


bot.run(os.environ.get("DISCORD_TOKEN")) # 或者填入你的真实 Token
