import urllib.request
import json
import time
import datetime
import os
import traceback

# ==========================================
# CONFIGURATION
# ==========================================
TELEGRAM_BOT_TOKEN = "8821314570:AAFp7Y2NM0CFeWtdMCmmLA6TBXU7MMPbQTA"  # ضع توكن التليجرام هنا
TELEGRAM_CHAT_ID = "27755694"      # ضع Chat ID هنا
SYMBOL = "BTCUSDT"
INITIAL_BALANCE = 1000.0
STATE_FILE = "state.json"

# ==========================================
# TELEGRAM NOTIFIER WITH ERROR HANDLING
# ==========================================
def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
        print(f"[LOCAL LOG]: {message}")
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req, timeout=10)
    except Exception as e:
        print(f"❌ Failed to send Telegram message: {e}")

# ==========================================
# TECHNICAL INDICATORS & DATA FETCHING
# ==========================================
def fetch_klines(symbol='BTCUSDT', interval='15m', limit=205):
    # المحاولة الأولى: السحب من CoinGecko
    try:
        url = "https://api.coingecko.com/api/v3/coins/bitcoin/ohlc?vs_currency=usd&days=1"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
        res = urllib.request.urlopen(req, timeout=10)
        raw_data = json.loads(res.read().decode('utf-8'))
        return [[item[0], item[1], item[2], item[3], item[4]] for item in raw_data[-limit:]]
    except Exception:
        # المحاولة الثانية (Fallback): السحب من CryptoCompare لتفادي 429 أو 451
        url = "https://min-api.cryptocompare.com/data/v2/histominute?fsym=BTC&tsym=USD&limit=200"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        res = urllib.request.urlopen(req, timeout=10)
        data = json.loads(res.read().decode('utf-8'))['Data']['Data']
        return [[d['time']*1000, d['open'], d['high'], d['low'], d['close']] for d in data]

def calculate_ema(closes, period=200):
    ema = [closes[0]] * len(closes)
    multiplier = 2 / (period + 1)
    for i in range(1, len(closes)):
        ema[i] = (closes[i] - ema[i-1]) * multiplier + ema[i-1]
    return ema

def calculate_rsi(closes, period=14):
    rsi = [50] * len(closes)
    gains, losses = [], []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i-1]
        gains.append(max(change, 0))
        losses.append(max(-change, 0))
        if i >= period:
            avg_gain = sum(gains[-period:]) / period
            avg_loss = sum(losses[-period:]) / period
            rsi[i] = 100 if avg_loss == 0 else (100 - (100 / (1 + (avg_gain / avg_loss))))
    return rsi

# ==========================================
# PAPER TRADER ENGINE WITH PERSISTENCE
# ==========================================
class RobustPaperTrader:
    def __init__(self):
        self.symbol = SYMBOL
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 43200  # 12 Hours in seconds
        
        # تحميل البيانات السابقة أو إنشاء ملف جديد
        self.load_state()
        
        send_telegram(
            f"🚀 *Bot Engine Started/Restarted*\n"
            f"• Pair: `{self.symbol}`\n"
            f"• Capital: `${self.balance:.2f}`\n"
            f"• Status: Active 24/7\n"
            f"• Active Trade: `{ 'YES' if self.position else 'NO' }`"
        )

    def load_state(self):
        """تحميل الرصيد والصفقة من ملف JSON في السيرفر"""
        if os.path.exists(STATE_FILE):
            try:
                with open(STATE_FILE, 'r') as f:
                    state = json.load(f)
                    self.balance = state.get('balance', INITIAL_BALANCE)
                    self.position = state.get('position', None)
                    print(f"📦 Loaded state successfully! Balance: ${self.balance:.2f}")
                    return
            except Exception as e:
                print(f"⚠️ Failed to load state file, fallback to defaults: {e}")
        
        self.balance = INITIAL_BALANCE
        self.position = None
        self.save_state()

    def save_state(self):
        """حفظ الرصيد والصفقة الحالية تلقائياً"""
        try:
            state = {
                'balance': self.balance,
                'position': self.position
            }
            with open(STATE_FILE, 'w') as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            print(f"⚠️ Error saving state: {e}")

    def send_heartbeat(self, current_price, rsi, is_uptrend):
        status_msg = (
            f"🟢 *HEARTBEAT: Bot is Active & Running*\n"
            f"• Date: `{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`\n"
            f"• Price: `${current_price:,.2f}`\n"
            f"• RSI: `{rsi:.1f}` | Uptrend: `{is_uptrend}`\n"
            f"• Balance: `${self.balance:.2f}`\n"
            f"• Active Trade: `{ 'YES' if self.position else 'NO' }`"
        )
        send_telegram(status_msg)

    def run_tick(self):
        candles = fetch_klines(self.symbol, interval='15m', limit=205)
        closes = [float(c[4]) for c in candles]
        
        price = closes[-1]
        rsi = calculate_rsi(closes, 14)[-1]
        ema200 = calculate_ema(closes, 200)[-1]
        is_uptrend = price > ema200

        print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Price: ${price:,.2f} | EMA200: ${ema200:,.2f} | RSI: {rsi:.1f}")

        # Send Heartbeat every 12 Hours
        if time.time() - self.last_heartbeat >= self.heartbeat_interval:
            self.send_heartbeat(price, rsi, is_uptrend)
            self.last_heartbeat = time.time()

        # Check Entry Signal
        if not self.position and is_uptrend and rsi < 28:
            amt = self.balance * 0.5
            self.position = {'price': price, 'amount': amt, 'units': amt / price}
            self.balance -= amt
            self.save_state()  # حفظ الشراء تلقائياً
            send_telegram(f"🟢 *PAPER BUY EXECUTED*\n• Entry: `${price:,.2f}`\n• Amount: `${amt:.2f}`")

        # Check Exit Signal
        elif self.position:
            entry_price = self.position['price']
            pnl = (price - entry_price) / entry_price
            
            if pnl >= 0.015 or pnl <= -0.020:
                ret = self.position['amount'] * (1 + pnl)
                self.balance += (ret - (ret * 0.00075))
                status = "🟢 PROFIT" if pnl > 0 else "🔴 LOSS"
                send_telegram(f"{status} *POSITION CLOSED*\n• PnL: `{pnl*100:+.2f}%`\n• New Balance: `${self.balance:.2f}`")
                self.position = None
                self.save_state()  # حفظ حالة إغلاق الصفقة

def main():
    trader = RobustPaperTrader()
    
    while True:
        try:
            trader.run_tick()
            time.sleep(60)  # الانتظار دقيقة كاملة لمنع Rate limit 429
        except Exception as e:
            err_details = traceback.format_exc()
            print(f"⚠️ Error encountered: {e}")
            send_telegram(f"⚠️ *ALERT: Bot Encountered Error*\n`{str(e)}`\n\n_Retrying in 60 seconds..._")
            time.sleep(60)

if __name__ == "__main__":
    main()
