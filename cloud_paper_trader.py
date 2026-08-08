import os
import time
import threading
import requests
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
# 3. دالة إرسال الرسائل النصية للتليجرام
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
# 4. دالة إنشاء رسالة حالة البوت (Status Report)
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
# 5. دالة إرسال ملف الإكسيل/CSV للتليجرام
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
# 6. جدولة إرسال التقرير (12 ظهراً و 12 منتصف الليل)
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
# 7. خادم استماع الأوامر (مقتصر على /file و /update)
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
                    
                    # 1. أمر الحصول على الملف
                    if text == '/file':
                        send_excel_file()
                        
                    # 2. أمر الحصول على التحديث المباشر
                    elif text == '/update':
                        send_telegram_message(get_status_report())
                        
        except Exception as e:
            time.sleep(5)

# ==========================================
# 8. تشغيل البوت والمحرك الأساسي
# ==========================================
def main():
    print("Starting Crypto Paper Trader Engine...")
    
    # إرسال إشعار بدء تشغيل المحرك
    start_msg = (
        "🚀 *Bot Engine Started/Restarted*\n"
        "• Pair: BTCUSDT\n"
        "• Capital: $1000.00\n"
        "• Status: Active 24/7\n"
        "• Active Trade: NO"
    )
    send_telegram_message(start_msg)
    
    # تشغيل الأوامر والجدولة في الخلفية
    threading.Thread(target=telegram_command_listener, daemon=True).start()
    threading.Thread(target=scheduled_daily_reports, daemon=True).start()
    
    # الحلقة الرئيسية للتداول (Trading Loop)
    while True:
        time.sleep(60)

if __name__ == "__main__":
    main()
