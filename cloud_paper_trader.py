import urllib.request
import json
import time
import datetime
import os

# ==========================================
# TELEGRAM NOTIFICATION CONFIG (OPTIONAL)
# ==========================================
# اتركها فارغة إذا لم تكن تريد التليجرام، أو أدخل بياناتك للحصول على إشعارات فورية
TELEGRAM_BOT_TOKEN = "" 
TELEGRAM_CHAT_ID = ""   

def send_telegram_msg(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = json.dumps({"chat_id": TELEGRAM_CHAT_ID, "text": message}).encode('utf-8')
        req = urllib.request.Request(url, data=payload, headers={'Content-Type': 'application/json'})
        urllib.request.urlopen(req)
    except Exception as e:
        print(f"⚠️ Telegram Error: {e}")

# ==========================================
# BINANCE API FETCH
# ==========================================
def fetch_klines(symbol='SOLUSDT', interval='4h', limit=100):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    req = urllib.request.urlopen(url)
    return json.loads(req.read().decode('utf-8'))

def calculate_sma(closes, period):
    sma = []
    for i in range(len(closes)):
        if i < period - 1:
            sma.append(closes[i])
        else:
            sma.append(sum(closes[i-period+1:i+1]) / period)
    return sma

# ==========================================
# TRADER CLASS WITH DAILY REPORTING
# ==========================================
class CloudPaperTrader:
    def __init__(self, symbols=['BTCUSDT', 'ETHUSDT', 'SOLUSDT'], capital=1000.0):
        self.symbols = symbols
        self.capital = capital
        self.allocation = capital / len(symbols)
        self.positions = {s: None for s in symbols}
        self.balances = {s: self.allocation for s in symbols}
        
        self.last_daily_report = datetime.datetime.now().date()
        self.daily_pnl_history = []

    def log(self, msg):
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_line = f"[{timestamp}] {msg}"
        print(log_line)
        with open("bot_execution.log", "a", encoding="utf-8") as f:
            f.write(log_line + "\n")

    def generate_daily_report(self):
        total_balance = sum(self.balances.values())
        # Add unrealized PnL for active positions
        for symbol, pos in self.positions.items():
            if pos:
                try:
                    candles = fetch_klines(symbol, interval='4h', limit=5)
                    price = float(candles[-1][4])
                    pnl = (price - pos['entry']) / pos['entry']
                    total_balance += pos['amount'] * (1 + pnl)
                except:
                    total_balance += pos['amount']

        net_profit = total_balance - self.capital
        net_pct = (net_profit / self.capital) * 100

        report = f"""
========================================
📊 DAILY PERFORMANCE REPORT
Date: {datetime.datetime.now().strftime('%Y-%m-%d')}
========================================
Initial Capital:  ${self.capital:.2f}
Current Portfolio:${total_balance:.2f}
Total Net PnL:    ${net_profit:+.2f} ({net_pct:+.2f}%)

🔹 ACTIVE POSITIONS:
"""
        active_cnt = 0
        for symbol, pos in self.positions.items():
            if pos:
                active_cnt += 1
                report += f" • {symbol}: Entry ${pos['entry']:.2f} | Alloc ${pos['amount']:.2f}\n"
        if active_cnt == 0:
            report += " • No active trades currently.\n"
            
        report += "========================================\n"

        # Save to file
        with open("daily_report.txt", "a", encoding="utf-8") as f:
            f.write(report + "\n")

        self.log("📋 Daily Report Generated Successfully.")
        send_telegram_msg(report)

    def run_check(self):
        self.log("🔍 Checking 4H Golden Cross Conditions...")
        
        # Check if 24 hours passed to issue daily report
        today = datetime.datetime.now().date()
        if today > self.last_daily_report:
            self.generate_daily_report()
            self.last_daily_report = today

        for symbol in self.symbols:
            candles = fetch_klines(symbol, interval='4h', limit=100)
            closes = [float(c[4]) for c in candles]
            
            sma20 = calculate_sma(closes, 20)
            sma50 = calculate_sma(closes, 50)
            price = closes[-1]
            
            bullish_cross = sma20[-2] <= sma50[-2] and sma20[-1] > sma50[-1]
            bearish_cross = sma20[-2] >= sma50[-2] and sma20[-1] < sma50[-1]
            
            pos = self.positions[symbol]
            
            # Entry Signal
            if not pos and bullish_cross:
                amt = self.balances[symbol] * 0.95
                self.positions[symbol] = {'entry': price, 'amount': amt, 'highest': price}
                self.balances[symbol] -= amt
                msg = f"🟢 [PAPER BUY] {symbol} @ ${price:.2f} | Allocated: ${amt:.2f}"
                self.log(msg)
                send_telegram_msg(msg)

            # Exit Signal
            elif pos:
                if price > pos['highest']:
                    pos['highest'] = price
                
                entry = pos['entry']
                highest = pos['highest']
                pnl = (price - entry) / entry
                drop_from_peak = (highest - price) / highest
                
                # Exit Logic: Bearish Cross OR Trailing Drop (3.5%) OR Stop Loss (-4%)
                if bearish_cross or (pnl > 0.05 and drop_from_peak >= 0.035) or pnl <= -0.04:
                    ret = pos['amount'] * (1 + pnl)
                    self.balances[symbol] += (ret - (ret * 0.00075))
                    status = "🟢 PROFIT" if pnl > 0 else "🔴 LOSS"
                    msg = f"{status} [PAPER SELL] {symbol} @ ${price:.2f} | PnL: {pnl*100:+.2f}% | New Balance: ${self.balances[symbol]:.2f}"
                    self.log(msg)
                    send_telegram_msg(msg)
                    self.positions[symbol] = None

if __name__ == "__main__":
    print("🚀 STARTING CLOUD PAPER TRADER ON PYTHONANYWHERE...")
    trader = CloudPaperTrader()
    
    # Generate initial status report on start
    trader.generate_daily_report()
    
    while True:
        try:
            trader.run_check()
            time.sleep(3600)  # Sleep for 1 hour between checks
        except Exception as e:
            print(f"⚠️ Exception encountered: {e}")
            time.sleep(300)