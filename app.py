import os
import sys
import time
from arabic_reshaper import reshape
from bidi.algorithm import get_display
import gspread
import requests

# إجبار التيرمنال على دعم اللغة العربية بشكل صحيح
sys.stdout.reconfigure(encoding='utf-8')


def ar(text):
  """دالة لتنسيق النصوص العربية للتيرمنال"""
  return get_display(reshape(str(text)))


def clean_number(val):
  """دالة لتنظيف النص وتحويله إلى رقم float وإزالة الفواصل وعلامات العملة"""
  if not val:
    return 0.0
  cleaned = (
      str(val)
      .replace(',', '')
      .replace('$', '')
      .replace(' ', '')
      .replace('USD', '')
  )
  return float(cleaned)


def get_btc_price():
  """سحب سعر البيتكوين اللحظي من Binance API"""
  url = 'https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT'
  try:
    response = requests.get(url)
    data = response.json()
    return float(data['price'])
  except Exception as e:
    print(ar(f'خطأ في جلب السعر: {e}'))
    return None


def monitor_and_update_sheet():
  """الاتصال بـ Google Sheets وقراءة وتحديث حالة الصفقة"""
  try:
    credentials_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 'credentials.json'
    )
    gc = gspread.service_account(filename=credentials_path)
    sheet = gc.open('Binance Crypto Bot Journal').sheet1

    # قراءة البيانات وتنظيفها
    entry_price = clean_number(sheet.acell('D2').value)
    tp_price = clean_number(sheet.acell('G2').value)
    sl_price = clean_number(sheet.acell('H2').value)
    current_status = sheet.acell('I2').value

    # جلب السعر اللحظي الآن
    live_price = get_btc_price()
    if not live_price:
      return

    timestamp = time.strftime('%H:%M:%S')
    print(
        ar(
            f'[{timestamp}] السعر اللحظي: ${live_price:,.2f} | الحالة الحالية:'
            f' {current_status}'
        )
    )

    # فحص الصفقة
    if current_status == 'Open':
      if live_price >= tp_price:
        new_status = 'TP Hit 🎯'
        sheet.update_acell('I2', new_status)
        print(ar(f'🎉 مبروك! تم الوصول للهدف والتحديث في الشيت: {new_status}'))
      elif live_price <= sl_price:
        new_status = 'SL Hit 🛑'
        sheet.update_acell('I2', new_status)
        print(
            ar(
                '⚠️ تم الوصول لوقف الخسارة والتحديث في الشيت:'
                f' {new_status}'
            )
        )
      else:
        print(ar('⏳ الصفقة مستمرة...'))
    else:
      print(ar(f'الصفقة مغلقة بالفعل بحالة: {current_status}'))

  except Exception as e:
    print(ar(f'حدث خطأ أثناء الاتصال بالشيت: {e}'))


# حلقة تكرار لانهائية للفحص كل 30 ثانية
if __name__ == '__main__':
  print(ar('🚀 بدأ البوت في مراقبة الصفقة تلقائياً كل 30 ثانية...'))
  print(ar('اضغط Ctrl + C في التيرمنال لإيقاف البوت في أي وقت.\n'))

  while True:
    monitor_and_update_sheet()
    time.sleep(30)  # الانتظار لمدة 30 ثانية قبل الفحص التالي