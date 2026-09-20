from datetime import datetime, time
import os
import pytz
import telebot

# 從環境變數讀取 Telegram Bot Token（安全又不會外洩）
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "你的Telegram_Token")
bot = telebot.TeleBot(TOKEN)

# 設定時區（新加坡/馬來西亞時區）
TZ = pytz.timezone("Asia/Singapore")

# 定義精確的法庭開庭時間區段
# 星期天(6) 到 星期四(3)：21:00 - 22:00
# 星期一(0) 到 星期五(4)：06:30 - 07:30
COURT_SCHEDULES = {
    "night_session": (time(21, 0), time(22, 0), [0, 1, 2, 3, 6]),  # 週日到週四
    "morning_session": (time(6, 30), time(7, 30), [0, 1, 2, 3, 4]),  # 週一到週五
}


def is_court_open(now: datetime) -> bool:
    """檢查當前時間是否在法庭開庭時間內"""
    current_time = now.time()
    current_weekday = now.weekday()  # 0是週一，6是週日

    for session_name, (start, end, allowed_weekdays) in COURT_SCHEDULES.items():
        if current_weekday in allowed_weekdays:
            if start <= current_time <= end:
                return True
    return False


def evaluate_spy_report(report_content: str) -> bool:
    """法庭審查密探（煦閣）的報告，判斷是否有立案（Have a Case）"""
    # 這裡未來可以對接 AI 模型；目前先以訊息長度或關鍵字作為簡易判斷
    if len(report_content.strip()) > 3:
        return True
    return False


# --- Telegram 訊息處理 ---
@bot.message_handler(commands=["start", "help"])
def send_welcome(message):
    bot.reply_to(
        message,
        "【維權帝國司法系統】啟動成功！\n"
        "煦閣密探正在暗中觀察你的行為……任何訴苦或發言都會被記錄審查。",
    )


@bot.message_handler(func=lambda message: True)
def handle_user_message(message):
    user_text = message.text
    now = datetime.now(TZ)

    # 1. 模擬煦閣密探捕捉到被告行為並生成報告
    spy_report = f"被告於 {now.strftime('%H:%M')} 傳送了訊息：『{user_text}』"

    # 2. 法庭進行 Case 立案審查
    has_case = evaluate_spy_report(user_text)

    if not has_case:
        bot.reply_to(
            message,
            f"【煦閣密探觀察報分散】\n{spy_report}\n\n[法庭裁定]：情節輕微，暫無 Case，不予追究。",
        )
        return

    # 3. Case 成立：發出逮捕令，判斷是否開庭或送進 Lockup
    court_open = is_court_open(now)

    if court_open:
        response_msg = (
            f"🚨 【法庭逮捕令】 🚨\n"
            f"密探報告：{spy_report}\n\n"
            f"⚖️ 【法庭裁定】：Case 成立！正值法庭開庭時間，被告當庭受審！"
        )
    else:
        response_msg = (
            f"🔒 【法庭逮捕令與留置】 🔒\n"
            f"密探報告：{spy_report}\n\n"
            f"⚖️ 【法庭裁定】：Case 成立！非開庭時間，立即送入 **Lockup（留置室）** 關押至少 5 分鐘，"
            f"並持續監禁至下一個指定的開庭時段為止！"
        )

    bot.reply_to(message, response_msg)


if __name__ == "__main__":
    print("Bot is running...")
    bot.infinity_polling()
