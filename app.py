import os
import time
import requests
import gspread

# 1. Connect to Google Sheets
gc = gspread.service_account(filename="credentials.json")
sh = gc.open("Binance Crypto Bot Journal")
worksheet = sh.sheet1

def get_btc_price():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    try:
        response = requests.get(url)
        data = response.json()
        return float(data["price"])
    except Exception as e:
        print(f"Error fetching price: {e}")
        return None

print("🚀 Bot started monitoring trades...")

while True:
    try:
        # Read status from row 2
        status = worksheet.acell("I2").value
        
        if status == "Open":
            # Read target values and handle string commas (e.g. '66,180.45')
            raw_tp = str(worksheet.acell("G2").value).replace(',', '')
            raw_sl = str(worksheet.acell("H2").value).replace(',', '')
            
            tp = float(raw_tp)
            sl = float(raw_sl)
            
            current_price = get_btc_price()
            
            if current_price:
                timestamp = time.strftime("%H:%M:%S")
                print(f"[{timestamp}] Current Price: ${current_price:,.2f} | Status: Open")
                
                if current_price >= tp:
                    worksheet.update_acell("I2", "TP Hit")
                    print("🎉 Target Price (TP) Hit! Sheet updated.")
                elif current_price <= sl:
                    worksheet.update_acell("I2", "SL Hit")
                    print("🛑 Stop Loss (SL) Hit! Sheet updated.")
        else:
            timestamp = time.strftime("%H:%M:%S")
            print(f"[{timestamp}] Trade status is '{status}'. Waiting...")

    except Exception as e:
        print(f"Error in main loop: {e}")

    time.sleep(30)