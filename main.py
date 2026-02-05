import os
import time
import requests
from tradingview_ta import TA_Handler, Interval, Exchange

# 1. SETUP CREDENTIALS
TELEGRAM_BOT_TOKEN = os.getenv("TG_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TG_CHAT_ID")

def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID: return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except:
        pass

def check_market():
    print("🤖 Live Scanner starting...")
    
    # 2. FETCH LIVE DATA FROM TRADINGVIEW
    try:
        nifty = TA_Handler(
            symbol="NIFTY",
            screener="india",
            exchange="NSE",
            interval=Interval.INTERVAL_5_MINUTES
        )
        analysis = nifty.get_analysis()
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    # 3. GET INDICATORS (Using Proxies)
    # We use 10 for 9, 20 for 21, 30 for 33
    indicators = analysis.indicators
    
    close = indicators['close']
    open_price = indicators['open']
    high = indicators['high']
    low = indicators['low']
    
    ema_9  = indicators['EMA10'] # Approx for 9
    ema_21 = indicators['EMA20'] # Approx for 21
    ema_33 = indicators['EMA30'] # Approx for 33
    
    print(f"🔍 NIFTY LIVE: {close} | EMA21: {ema_21:.2f} | EMA33: {ema_33:.2f}")
    send_telegram(f"🔔 TEST ALERT: Nifty is LIVE at {close}")

    # 4. SIGNAL LOGIC
    msg = ""
    
    # Candle Color
    is_green = close > open_price
    is_red = close < open_price
    
    # --- BUY (CE) ---
    # Trend: Close > EMA 21
    if close > ema_21:
        # Pullback: Low touched EMA 9 (10) and closed Green
        if low <= ema_9 and close > ema_9 and is_green:
             msg = f"⚡ *LIVE CE ALERT: PULLBACK*\nPrice: {close}\nBounce off EMA 10"
        # Momentum: Crossed above EMA 9 (10)
        elif close > ema_9 and open_price < ema_9:
             msg = f"⚡ *LIVE CE ALERT: MOMENTUM*\nPrice: {close}\nCrossed EMA 10"

    # --- SELL (PE) ---
    # Rejection: High touched EMA 33 (30) but Close < EMA 33 (30)
    if high >= ema_33 and close < ema_33 and is_red:
        msg = f"⚡ *LIVE PE ALERT: 33 REJECTION*\nPrice: {close}\nResisted at EMA 30"
        
    elif close < ema_21:
        # Pullback: High touched EMA 9 (10) and closed Red
        if high >= ema_9 and close < ema_9 and is_red:
            msg = f"⚡ *LIVE PE ALERT: PULLBACK*\nPrice: {close}\nRejected EMA 10"
        # Momentum: Dropped below EMA 9 (10)
        elif close < ema_9 and open_price > ema_9:
             msg = f"⚡ *LIVE PE ALERT: MOMENTUM*\nPrice: {close}\nDropped below EMA 10"

    if msg:
        send_telegram(msg)
        print("✅ Alert Sent")
    else:
        print("No Signal Found")

if __name__ == "__main__":
    check_market()
