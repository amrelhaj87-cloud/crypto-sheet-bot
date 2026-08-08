import os
import sys
import time
import threading
import requests
import subprocess
from datetime import datetime
from dotenv import load_dotenv

# ==========================================
# 1. تحميل التوكن والـ Chat ID من ملف .env
# ==========================================
load_dotenv(os.path.expanduser('~/mybot/.env'))

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# مسار ملف سجل الصفقات CSV
CSV_FILE_PATH = os.path.expanduser('~/mybot/trades_journal.csv')

# ==========================================
# 2. متغيرات حالة البوت (State Variables)
# ==========================================
current_price = 64962.00
current_rsi = 69.7
is_uptrend = True
current_balance = 1000.00
is_active_trade = False

# ==========================================
# 3. برمجة وإضافة الأوامر في التليجرام تلقائياً
# ==========================================
def setup_telegram_menu():
    if not TELEGRAM_BOT_TOKEN:
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setMyCommands"
    commands = {
        "commands": [
            {"command": "update", "description": "🟢 إرسال تقرير حالة البوت والسعر الحالي"},
            {"command": "file", "description": "📊 تحميل ملف سجل الصفقات (Excel/CSV)"},
            {"command": "restart", "description": "🔄 إعادة تشغيل البوت"},
            {"command": "pull", "description": "⬇️ سحب أحدث كود من GitHub وإعادة التشغيل"}
        ]
    }
    try:
        requests.post(url, json=commands, timeout=10)
        print("Telegram Bot Menu Commands Set Successfully!")
    except Exception as e:
        print(f"Error setting bot commands: {e}")

# ==========================================
# 4. دالة إرسال الرسائل النصية للتليجرام
# ==========================================
def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Error: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is missing!")
        return
    
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"Error sending message: {e}")

# ==========================================
# 5. دالة إنشاء رسالة حالة البوت (Status Report)
# ==========================================
def get_status_report():
    now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    trade_status = 'YES' if is_active_trade else 'NO'
    
    status_msg = (
        f"🟢 *HEARTBEAT: Bot is Active & Running*\n"
        f"• *Date:* `{now_str}`\n"
        f"• *Price:* `${current_price:,.2f}`\n"
        f"• *RSI:* `{current_rsi:.1f}` | *Uptrend:* `{is_uptrend}`\n"
        f"• *Balance:* `${current_balance:,.2f}`\n"
        f"• *Active Trade:* `{trade_status}`"
    )
    return status_msg

# ==========================================
# 6. دالة إرسال ملف الإكسيل/CSV للتليجرام
# ==========================================
def send_excel_file():
    if not os.path.exists(CSV_FILE_PATH):
        send_telegram_message("⚠️ *تنبيه:* ملف سجل الصفقات غير موجود حالياً!")
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendDocument"
    try:
        with open(CSV_FILE_PATH, 'rb') as doc:
            files = {'document': doc}
            data = {
                'chat_id': TELEGRAM_CHAT_ID,
                'caption': '📊 *ملف سجل الصفقات المحدث (CSV/Excel)*'
            }
            requests.post(url, data=data, files=files, timeout=15)
            print("Excel file sent successfully to Telegram!")
    except Exception as e:
        print(f"Error sending file: {e}")

# ==========================================
# 7. دالتا الريستارت والـ Git Pull
# ==========================================
def handle_restart():
    send_telegram_message("🔄 *جاري إعادة تشغيل البوت...*")
    time.sleep(1)
    os.execv(sys.executable, [sys.executable] + sys.argv)

def handle_git_pull_and_restart():
    send_telegram_message("⏳ *جاري سحب أحدث كود من GitHub...*")
    try:
        result = subprocess.run(["git", "pull"], capture_output=True, text=True, check=True)
        out_msg = result.stdout.strip() if result.stdout else "Up to date."
        send_telegram_message(f"✅ *تم التحديث من GitHub بنجاح:*\n```\n{out_msg}\n```")
        send_telegram_message("🔄 *جاري إعادة التشغيل لتطبيق التحديثات...*")
        time.sleep(1)
        os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        send_telegram_message(f"❌ *حدث خطأ أثناء السحب من Git:*\n`{str(e)}`")

# ==========================================
# 8. جدولة إرسال التقرير (12 ظهراً و 12 منتصف الليل)
# ==========================================
def scheduled_daily_reports():
    sent_noon = False
    sent_midnight = False
    print("Daily Scheduler Thread Started...")
    
    while True:
        try:
            now = datetime.now()
            hour = now.hour
            
            # الساعة 12:00 ظهراً
            if hour == 12 and not sent_noon:
                send_telegram_message(get_status_report())
                sent_noon = True
                sent_midnight = False
                
            # الساعة 00:00 منتصف الليل
            elif hour == 0 and not sent_midnight:
                send_telegram_message(get_status_report())
                sent_midnight = True
                sent_noon = False
                
            # إعادة الضبط في باقي الساعات
            if hour not in [12, 0]:
                sent_noon = False
                sent_midnight = False

        except Exception as e:
            print(f"Scheduler error: {e}")
            
        time.sleep(30)

# ==========================================
# 9. خادم استماع الأوامر (/file, /update, /restart, /pull)
# ==========================================
def telegram_command_listener():
    offset = 0
    print("Telegram Listener Started...")
    while True:
        try:
            url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates?offset={offset}&timeout=30"
            response = requests.get(url, timeout=35).json()
            
            if response.get("ok") and response.get("result"):
                for update in response["result"]:
                    offset = update["update_id"] + 1
                    message = update.get("message", {})
                    text = message.get("text", "").strip()
                    
                    if text == '/file':
                        send_excel_file()
                    elif text == '/update':
                        send_telegram_message(get_status_report())
                    elif text == '/restart':
                        handle_restart()
                    elif text == '/pull':
                        handle_git_pull_and_restart()
                        
        except Exception as e:
            time.sleep(5)

# ==========================================
# 10. تشغيل البوت والمحرك الأساسي
# ==========================================
def main():
    print("Starting Crypto Paper Trader Engine...")
    
    # 1. تسجيل قائمة الأوامر في التليجرام
    setup_telegram_menu()
    
    # 2. إرسال إشعار بدء تشغيل المحرك
    start_msg = (
        "🚀 *Bot Engine Started/Restarted*\n"
        "• Pair: BTCUSDT\n"
        "• Capital: $1000.00\n"
        "• Status: Active 24/7\n"
        "• Active Trade: NO"
    )
    send_telegram_message(start_msg)
    
    # 3. تشغيل الأوامر والجدولة في الخلفية
    threading.Thread(target=telegram_command_listener, daemon=True).start()
    threading.Thread(target=scheduled_daily_reports, daemon=True).start()
    
    # 4. الحلقة الرئيسية للتداول (Trading Loop)
    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
