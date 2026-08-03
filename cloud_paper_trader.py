import urllib.request
import json
import time
import datetime
import traceback

# ==========================================
# CONFIGURATION
# ==========================================
TELEGRAM_BOT_TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"  # ضع توكن التليجرام هنا
TELEGRAM_CHAT_ID = "YOUR_TELEGRAM_CHAT_ID"      # ضع Chat ID هنا
SYMBOL = "BTCUSDT"
INITIAL_BALANCE = 1000.0

# ==========================================
# TELEGRAM NOTIFIER WITH ERROR HANDLING
# ==========================================
def send_telegram(message):
    if TELEGRAM_BOT_TOKEN == "YOUR_TELEGRAM_BOT_TOKEN":
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
# TECHNICAL INDICATORS
# ==========================================
def fetch_klines(symbol='BTCUSDT', interval='15m', limit=205):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    res = urllib.request.urlopen(req, timeout=10)
    return json.loads(res.read().decode('utf-8'))

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
# PAPER TRADER ENGINE (PROTECTED LOOP)
# ==========================================
class RobustPaperTrader:
    def __init__(self):
        self.symbol = SYMBOL
        self.balance = INITIAL_BALANCE
        self.position = None
        self.last_heartbeat = time.time()
        self.heartbeat_interval = 43200  # 12 Hours in seconds
        
        send_telegram(f"🚀 *Bot Engine Started/Restarted*\n• Pair: `{self.symbol}`\n• Capital: `${self.balance:.2f}`\n• Status: Active 24/7")

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

def main():
    trader = RobustPaperTrader()
    
    while True:
        try:
            trader.run_tick()
            time.sleep(30)
        except Exception as e:
            err_details = traceback.format_exc()
            print(f"⚠️ Error encountered: {e}")
            send_telegram(f"⚠️ *ALERT: Bot Encountered Error*\n`{str(e)}`\n\n_Retrying in 60 seconds..._")
            time.sleep(60)  # Safe wait before auto-recovery

if __name__ == "__main__":
    main()