import os
import requests
import yfinance as yf
import pandas_ta as ta
import pandas as pd
from datetime import datetime
import pytz

# GET CREDENTIALS FROM GITHUB SECRETS
TELEGRAM_BOT_TOKEN = os.environ["TG_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TG_CHAT_ID"]

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print(f"Error: {e}")

def check_market():
    # Fetch Data (Yahoo Finance)
    df = yf.download("^NSEI", period="1d", interval="5m", progress=False)
    if df.empty: return

    if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
    
    # Indicators
    df['EMA_9'] = ta.ema(df['Close'], length=9)
    df['EMA_21'] = ta.ema(df['Close'], length=21)
    df['EMA_33'] = ta.ema(df['Close'], length=33)
    
    curr = df.iloc[-2] # Last completed candle
    prev = df.iloc[-3]
    price = curr['Close']
    
    # SIGNAL LOGIC
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
        print("Alert Sent")
    else:
        print("No Signal Found")

if __name__ == "__main__":
    check_market()