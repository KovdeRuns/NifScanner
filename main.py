import os
import json
import time
import requests
import pytz
from datetime import datetime
from tradingview_ta import TA_Handler, Interval

# --- 1. LOAD CONFIGURATION ---
try:
    with open('config.json', 'r') as f:
        CONFIG = json.load(f)
except FileNotFoundError:
    # Fallback defaults if file is missing
    CONFIG = {"SYMBOL": "NIFTY", "START_TIME": [9, 45], "END_TIME": [15, 0], "SCAN_INTERVAL_MIN": 5, "ATR_MULTIPLIER": 3.0, "ADX_THRESHOLD": 20}

# --- 2. SETUP ENVIRONMENT ---
TELEGRAM_TOKEN = os.getenv("TG_TOKEN")
CHAT_ID = os.getenv("TG_CHAT_ID")
IST = pytz.timezone('Asia/Kolkata')

def is_market_session():
    now = datetime.now(IST)
    if now.weekday() > 4: return False # Skip Sat/Sun
    
    start_h, start_m = CONFIG["START_TIME"]
    end_h, end_m = CONFIG["END_TIME"]
    
    session_start = now.replace(hour=start_h, minute=start_m, second=0)
    session_end = now.replace(hour=end_h, minute=end_m, second=0)
    return session_start <= now <= session_end

def send_alert(message):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("⚠️ Missing Telegram Credentials")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"})
    except Exception as e:
        print(f"❌ Telegram Error: {e}")

# --- 3. THE LOGIC ---
def scan_market():
    print(f"🔍 Scanning {CONFIG['SYMBOL']} at {datetime.now(IST).strftime('%H:%M:%S')}")
    try:
        handler = TA_Handler(
            symbol=CONFIG['SYMBOL'],
            screener="india",
            exchange="NSE",
            interval=Interval.INTERVAL_5_MINUTES
        )
        analysis = handler.get_analysis()
        ind = analysis.indicators

        # Data Points
        close = ind['close']
        ema10 = ind['EMA10'] # Using 10 as proxy for 9
        ema20 = ind['EMA20'] # Using 20 as proxy for 21
        atr   = ind.get('ATR', 15)
        adx   = ind.get('ADX', 0)
        
        # Robust Stop Loss distance (ATR 3.0)
        sl_dist = round(atr * CONFIG['ATR_MULTIPLIER'], 1)

        # ENTRY LOGIC (Mounir Validated)
        if adx > CONFIG['ADX_THRESHOLD']:
            # CE SETUP: Trend is Up + Pullback to 9 EMA
            if close > ema20 and ind['low'] <= ema10 and close > ema10:
                msg = (f"🚀 *NIFTY CE SETUP*\n"
                       f"Price: {close}\n"
                       f"🛡️ Robust SL: {round(close - sl_dist, 1)}\n"
                       f"Exit: Trail with ATR-3")
                send_alert(msg)

            # PE SETUP: Trend is Down + Pullback to 9 EMA
            elif close < ema20 and ind['high'] >= ema10 and close < ema10:
                msg = (f"📉 *NIFTY PE SETUP*\n"
                       f"Price: {close}\n"
                       f"🛡️ Robust SL: {round(close + sl_dist, 1)}\n"
                       f"Exit: Trail with ATR-3")
                send_alert(msg)
                
    except Exception as e:
        print(f"❌ Scanner Error: {e}")

# --- 4. EXECUTION ---
if __name__ == "__main__":
    print("💎 System 12.1 Ready")
    while True:
        if is_market_session():
            scan_market()
            # Wait for next 5-minute candle
            time.sleep(CONFIG['SCAN_INTERVAL_MIN'] * 60)
        else:
            # Check every 10 mins if market is about to open
            print("💤 Outside session hours. Waiting...")
            time.sleep(600)
