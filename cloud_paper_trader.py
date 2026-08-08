import os
import time
import threading
import requests
from dotenv import load_dotenv

# ==========================================
# 1. تحميل التوكن والـ Chat ID من ملف .env
# ==========================================
# يقرأ الملف الموجود في مجلد المشروع تلقائياً
load_dotenv(os.path.expanduser('~/mybot/.env'))

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# مسار ملف سجل الصفقات CSV
CSV_FILE_PATH = os.path.expanduser('~/mybot/trades_journal.csv')

# ==========================================
# 2. دالة إرسال الرسائل النصية للتليجرام
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
# 3. دالة إرسال ملف الإكسيل/CSV للتليجرام
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
# 4. خادم استماع للأوامر من التليجرام (/excel)
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
                    
                    # التحقق من الأمر
                    if text in ['/excel', '/report', '/file']:
                        send_excel_file()
                        
        except Exception as e:
            time.sleep(5)  # إعادة المحاولة في حالة انقطاع الشبكة

# ==========================================
# 5. تشغيل البوت والمحرك الأساسي
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
    
    # تشغيل مستمع التليجرام في Thread منفصل حتى لا يعطل محرك التداول
    listener_thread = threading.Thread(target=telegram_command_listener, daemon=True)
    listener_thread.start()
    
    # الحلقة الرئيسية للتداول (Trading Loop)
    while True:
        # هنا يتم تنفيذ خوارزمية التداول الخاصة بك
        # print("Bot is analyzing market...")
        time.sleep(60)

if __name__ == "__main__":
    main()
