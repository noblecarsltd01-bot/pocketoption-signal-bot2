# scanner.py
import os, time, csv, json
from datetime import datetime, timezone
import requests
import pandas as pd
import yfinance as yf
from dotenv import load_dotenv

from strategy import add_indicators, find_swing_levels, combined_divergence, price_near_levels
from utils.telegram_bot import TelegramReporter

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TIMEFRAME = int(os.getenv("TIMEFRAME", "60"))
ASSETS = os.getenv("ASSETS", "GOLD,BTCUSD").split(",")
ALERT_COOLDOWN = int(os.getenv("ALERT_COOLDOWN", "30"))
LOG_FILE = os.getenv("LOG_FILE", "signals_log.csv")

bot = TelegramReporter(TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)

# simple logger
def ensure_log():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['timestamp','asset','timeframe','price','signal','reasons'])

def log_signal(rec):
    with open(LOG_FILE, "a", newline='') as f:
        writer = csv.writer(f)
        writer.writerow(rec)

# fetch BTC 1m candles from Binance public REST (kline endpoint)
def fetch_binance(symbol="BTCUSDT", interval="1m", limit=500):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    df = pd.DataFrame(data, columns=[
        "open_time","open","high","low","close","volume","close_time","qav","num_trades","taker_base","taker_quote","ignore"
    ])
    df['open'] = df['open'].astype(float); df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float); df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
    df.set_index('timestamp', inplace=True)
    return df[['open','high','low','close','volume']]

# fetch gold candles via yfinance using symbol 'XAUUSD=X' or 'GC=F'
def fetch_gold(period="7d", interval="1m", limit=500):
    # yfinance returns index tz-aware; we keep it simple
    ticker = yf.Ticker("XAUUSD=X")
    df = ticker.history(period=period, interval=interval)
    if df.empty:
        # fallback to futures
        ticker2 = yf.Ticker("GC=F")
        df = ticker2.history(period=period, interval=interval)
    df = df[-limit:]
    df = df.rename(columns={"Open":"open","High":"high","Low":"low","Close":"close","Volume":"volume"})
    df = df[['open','high','low','close','volume']]
    df.index = pd.to_datetime(df.index)
    return df

# state
last_alert_time = {}  # map (asset,side) -> timestamp
ensure_log()

def scan_asset(asset):
    if asset == "BTCUSD":
        df = fetch_binance(symbol="BTCUSDT", interval="1m", limit=600)
    elif asset == "GOLD":
        df = fetch_gold(period="7d", interval="1m", limit=600)
    else:
        return None
    df = add_indicators(df)
    supports, resistances = find_swing_levels(df, lookback=200)
    div = combined_divergence(df)
    last = df.iloc[-1]
    price = last['close']

    near_support, slev = price_near_levels(price, supports)
    near_res, rlev = price_near_levels(price, resistances)
    ema_bull = last['ema_short'] > last['ema_long'] and price > last['ema_short']
    ema_bear = last['ema_short'] < last['ema_long'] and price < last['ema_short']

    signal = None
    reasons = []
    if div == 'bullish' and (near_support or ema_bull):
        signal = 'CALL'
        reasons.append('divergence(bullish)')
        if near_support: reasons.append(f'near_support={slev:.5f}')
        if ema_bull: reasons.append('ema_confluence(bull)')
    if div == 'bearish' and (near_res or ema_bear):
        signal = 'PUT'
        reasons.append('divergence(bearish)')
        if near_res: reasons.append(f'near_resistance={rlev:.5f}')
        if ema_bear: reasons.append('ema_confluence(bear)')

    return {'signal': signal, 'price': price, 'reasons': ";".join(reasons), 'df': df}

def main_loop():
    print("Starting scanner (1min) for GOLD and BTCUSD. Signals -> Telegram.")
    while True:
        for asset in ASSETS:
            try:
                res = scan_asset(asset)
                if not res:
                    continue
                signal = res['signal']
                price = res['price']
                reasons = res['reasons'] or "-"
                if signal:
                    key = (asset, signal)
                    now_ts = time.time()
                    last = last_alert_time.get(key, 0)
                    if now_ts - last > ALERT_COOLDOWN:
                        ts = datetime.utcnow().isoformat()
                        rec = [ts, asset, TIMEFRAME, f"{price:.6f}", signal, reasons]
                        log_signal(rec)
                        bot.send_signal(asset, TIMEFRAME, signal, price, reasons)
                        last_alert_time[key] = now_ts
                        print(f"[{ts}] {asset} {signal} {price} {reasons}")
                else:
                    print(f"[{datetime.utcnow().isoformat()}] {asset} no signal")
            except Exception as e:
                print("Error scanning", asset, e)
        # sleep until next candle (align to 60s grid)
        now = time.time()
        sleep_for = TIMEFRAME - (int(now) % TIMEFRAME) + 0.5
        time.sleep(sleep_for)

if __name__ == "__main__":
    main_loop()
