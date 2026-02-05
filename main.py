import os
import requests
import yfinance as yf
import pandas as pd
from datetime import datetime
import pytz

# 1. SETUP CREDENTIALS
TELEGRAM_BOT_TOKEN = os.getenv("TG_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID")

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ ERROR: Secrets are missing!")
        return
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error sending msg: {e}")

def check_market():
    print("🤖 Scanner starting...")
    
    # 2. FETCH DATA
    try:
        # Fetch slightly more data to ensure EMA calculation is accurate
        df = yf.download("^NSEI", period="5d", interval="5m", progress=False)
        if df.empty: 
            print("⚠️ Market data empty.")
            return
    except Exception as e:
        print(f"❌ Yahoo Error: {e}")
        return

    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # 3. CALCULATE INDICATORS (Using Standard Pandas - No External Libs)
    # EMA Formula: ewm(span=Length, adjust=False).mean()
    try:
        df['EMA_9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA_21'] = df['Close'].ewm(span=21, adjust=False).mean()
        df['EMA_33'] = df['Close'].ewm(span=33, adjust=False).mean()
    except Exception as e:
        print(f"❌ Math Error: {e}")
        return
    
    # Get Last Candle
    curr = df.iloc[-2]
    prev = df.iloc[-3]
    price = curr['Close']
    
    print(f"🔍 Checked Market at {price:.2f}. Math is working!")
    send_telegram(f"🔔 System Check: Bot is alive! Nifty is at {price:.2f}")

    # 4. SIGNAL LOGIC
    msg = ""
    
    # BUY (CE)
    if curr['Close'] > curr['EMA_21']:
        if curr['Low'] <= curr['EMA_9'] and curr['Close'] > curr['EMA_9'] and curr['Close'] > curr['Open']:
            msg = f"🚀 *CE PULLBACK ALERT*\nPrice: {price:.2f}\nBounce off 9 EMA"
        elif curr['Close'] > curr['EMA_9'] and prev['Close'] <= curr['EMA_9']:
            msg = f"🚀 *CE MOMENTUM ALERT*\nPrice: {price:.2f}\nCrossed 9 EMA"

    # SELL (PE)
    if curr['High'] >= curr['EMA_33'] and curr['Close'] < curr['EMA_33'] and curr['Close'] < curr['Open']:
        msg = f"📉 *PE 33-REJECTION ALERT*\nPrice: {price:.2f}\nResisted at 33 EMA"
    elif curr['Close'] < curr['EMA_21']:
        if curr['High'] >= curr['EMA_9'] and curr['Close'] < curr['EMA_9'] and curr['Close'] < curr['Open']:
            msg = f"📉 *PE PULLBACK ALERT*\nPrice: {price:.2f}\nRejected 9 EMA"
        elif curr['Close'] < curr['EMA_9'] and prev['Close'] >= curr['EMA_9']:
            msg = f"📉 *PE MOMENTUM ALERT*\nPrice: {price:.2f}\nDropped below 9 EMA"

    if msg:
        send_telegram(msg)
        print("✅ Alert Sent")
    else:
        print("No Signal Found")

if __name__ == "__main__":
    check_market()
