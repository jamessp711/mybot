from datetime import datetime, timedelta
import os
import random
import time
import telebot

# 讀取環境變數中的 Telegram Token
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
bot = telebot.TeleBot(TOKEN)

# 記憶體資料庫（不使用 Supabase）
criminal_records = {}  # 記錄每個 user_id 的犯案次數（累犯追蹤）
lockup_users = {}  # 記錄每個 user_id 的禁閉/審訊解封時間戳記 (timestamp)


def calculate_tier3_release(days):
  """計算第一級重罪的監禁結束時間：星期六、日不算入，計算至星期日晚上 10 點"""
  now = datetime.now()
  added_days = 0
  end_time = now

  while added_days < days:
    end_time += timedelta(days=1)
    # 星期六 (weekday == 5) 與星期日 (weekday == 6) 不算入監禁天數
    if end_time.weekday() not in [5, 6]:
      added_days += 1

  # 強制結算至星期日晚上 10 點 (22:00)
  return end_time.replace(hour=22, minute=0, second=0)


@bot.message_handler(commands=["start"])
def send_welcome(message):
  bot.reply_to(
      message,
      "⚖️ 【維多利亞王國・最高審訊庭】\n"
      "大門已深鎖。你的每一言每一行，皆已收錄進王國卷宗。\n"
      "法官正在暗中凝視，準備迎接審判吧。",
  )


@bot.message_handler(func=lambda message: True)
def handle_judicial_system(message):
  user_id = message.from_user.id
  current_time = time.time()

  # 1. 攔截機制：檢查被告是否處於禁閉/鎖倉狀態
  if user_id in lockup_users and current_time < lockup_users[user_id]:
    remaining = int(lockup_users[user_id] - current_time)
    mins = remaining // 60
    secs = remaining % 60
    bot.reply_to(
        message,
        f"⛓️ 【禁閉室鐵律】\n"
        f"「肅靜！王國的枷鎖尚未鬆開。」\n"
        f"剩餘盲狙禁閉時間：**{mins} 分 {secs} 秒**。\n"
        "在此期間膽敢喧嘩者，罪加一等！",
    )
    return

  # 2. 累犯與卷宗追蹤（記憶體記錄）
  record_count = criminal_records.get(user_id, 0)
  is_repeat = record_count > 0
  criminal_records[user_id] = record_count + 1

  # 3. 判決分流：累犯或隨機有機率觸發重罪/鞭刑，否則為輕罪
  # 累犯觸發重罪的機率較高
  is_major = is_repeat and (random.random() > 0.3)

  if not is_major:
    # --- 輕罪處理（隨機一項）---
    minor_options = [
        (
            "【輕罪裁決：罰站與羞辱】\n"
            "法官冷酷下令：剝奪所有王國服飾與尊嚴（全裸受罰），罰站反省！"
            "（最多 2 分鐘）"
        ),
        (
            "【輕罪裁決：洗廁所】\n"
            "禁衛軍冷笑：王國地牢深處的馬桶，交給你親自刷洗乾淨。"
        ),
        (
            "【輕罪裁決：罰跪】\n" "大殿石板冰冷，判處當眾罰跪，不得起身！",
        ),
    ]
    chosen_punishment = random.choice(minor_options)

    # 設定盲狙禁閉時間（輕罪最高 2 分鐘 = 120秒，法庭不公開具體秒數）
    lockup_duration = random.randint(60, 120)
    lockup_users[user_id] = current_time + lockup_duration

    response = (
        f"⚖️ 【維多利亞王國・審訊庭宣告】\n"
        f"被告背景：{'【王國卷宗：累犯】' if is_repeat else '【王國卷宗：初犯】'}\n\n"
        f"{chosen_punishment}\n\n"
        f"🔒 法庭已啟動**暗中盲狙倒數**。大門何時開啟，全憑法官心意，休想探知時間！"
    )
    bot.reply_to(message, response)

  else:
    # --- 重罪 / 鞭刑分三級處理 ---
    tier = random.choice([1, 2, 3])

    if tier == 1:
      # 最低級
      lashes = random.randint(1, 6)
      days = random.randint(2, 3)
      tier_name = "最低級鞭刑"
      lockup_users[user_id] = (
          current_time + 300
      )  # 測試期間以5分鐘暗中審訊代替
      time_desc = f"監禁天數：{days} 天"
    elif tier == 2:
      # 第二級
      lashes = random.randint(7, 12)
      days = random.randint(4, 5)
      tier_name = "第二級鞭刑"
      lockup_users[user_id] = current_time + 300
      time_desc = f"監禁天數：{days} 天"
    else:
      # 第一級（最嚴格）
      lashes = random.randint(13, 24)
      days = random.randint(5, 7)
      tier_name = "第一級重罪（嚴格鞭刑）"
      release_dt = calculate_tier3_release(days)
      # 為了系統安全，這裡記錄實際時間戳記
      lockup_users[user_id] = release_dt.timestamp()
      time_desc = (
          f"監禁天數：{days} 天\n"
          "⚠️ **特別條款**：星期六、日不算入刑期，刑期計算至星期日晚上 10 點結算！"
      )

    response = (
        f"🩸 【維多利亞王國・血色重判】 🩸\n"
        f"卷宗核對：查明閣下為重大累犯（累計案底：{record_count} 次）！\n"
        f"判決裁定：**{tier_name}**\n\n"
        f"⚡ 刑罰內容：執行鞭刑 **{lashes} 下**\n"
        f"⛓️ 牢獄裁決：{time_desc}\n\n"
        "「法庭的鐵律不容踐踏。大門已封鎖，在黑暗中好好接受洗禮吧！」"
    )
    bot.reply_to(message, response)


if __name__ == "__main__":
  print("Victoria Kingdom Judicial Bot (In-Memory) is running...")
  bot.infinity_polling()
