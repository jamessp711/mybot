from datetime import datetime, time
import pytz

# 設定時區（配合你的帝國時區）
TZ = pytz.timezone("Asia/Singapore")

# 定義精確的法庭開庭時間區段
# 星期天(6) 到 星期四(3)：21:00 - 22:00
# 星期一(0) 到 星期五(4)：06:30 - 07:30
COURT_SCHEDULES = {
    # (start_time, end_time)
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
    # 這裡可以接 AI 或是簡單的關鍵字/邏輯判斷
    # 如果內容包含明顯的違法行為或耍廢事實，則成立 Case
    if len(report_content.strip()) > 5:
        return True
    return False


def process_arrest_and_detention(report_content: str):
    """處理密探報告：判斷 Case ➔ 發出逮捕令 ➔ 進入 Lockup ➔ 計算開庭時間"""
    now = datetime.now(TZ)

    # 1. 法庭判斷是否有 Case
    has_case = evaluate_spy_report(report_content)

    if not has_case:
        return {
            "status": "dismissed",
            "message": "法庭審查完畢：密探呈報之事證不足，此案不予立案。",
        }

    # 2. 有 Case 成立：發出逮捕令，強制送入 Lockup（最少 5 分鐘）
    # 3. 檢查當前是否為開庭時間
    court_open = is_court_open(now)

    if court_open:
        verdict_status = "immediate_trial"
        message = (
            f"【法庭逮捕令】\n"
            f"根據密探回報：{report_content}\n"
            f"法庭裁定：Case 成立！正值開庭時間，被告當庭受審！"
        )
    else:
        verdict_status = "detained_in_lockup"
        message = (
            f"【法庭逮捕令】\n"
            f"根據密探回報：{report_content}\n"
            f"法庭裁定：Case 成立！非開庭時間，立即送入 Lockup（留置室）關押至少 5 分鐘，"
            f"並持續監禁至下一個開庭時段為止！"
        )

    return {
        "status": verdict_status,
        "arrest_time": now.strftime("%Y-%m-%d %H:%M:%S"),
        "message": message,
    }


# === 測試範例 ===
if __name__ == "__main__":
    test_report = "被告於下午在辦公室偷懶耍廢，未依規定執行帝國交辦事項。"
    result = process_arrest_and_detention(test_report)
    print(result["message"])
