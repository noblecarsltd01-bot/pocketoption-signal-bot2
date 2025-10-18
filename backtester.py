# backtester.py
import pandas as pd
import argparse
from strategy import add_indicators, find_swing_levels, combined_divergence, price_near_levels

def backtest(candles_csv, out_csv="backtest_trades.csv"):
    df = pd.read_csv(candles_csv, parse_dates=['timestamp']).set_index('timestamp').sort_index()
    df = add_indicators(df)
    trades = []
    for i in range(200, len(df)-1):
        sub = df.iloc[:i+1]
        div = combined_divergence(sub)
        if not div:
            continue
        last = sub.iloc[-1]
        price = last['close']
        supports, resistances = find_swing_levels(sub, lookback=200)
        near_support, _ = price_near_levels(price, supports)
        near_res, _ = price_near_levels(price, resistances)
        ema_bull = last['ema_short'] > last['ema_long'] and price > last['ema_short']
        ema_bear = last['ema_short'] < last['ema_long'] and price < last['ema_short']
        side = None
        if div=='bullish' and (near_support or ema_bull):
            side='CALL'
        if div=='bearish' and (near_res or ema_bear):
            side='PUT'
        if side:
            exit_price = df.iloc[i+1]['close']  # assume 1-period expiry
            win = (exit_price > price and side=='CALL') or (exit_price < price and side=='PUT')
            trades.append({
                'entry_time': sub.index[-1].isoformat(),
                'side': side,
                'entry_price': price,
                'exit_price': exit_price,
                'win': int(win)
            })
    out = pd.DataFrame(trades)
    out.to_csv(out_csv, index=False)
    print("Backtest complete. Trades:", len(out))
    return out

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--candles", required=True, help="CSV file with OHLCV (timestamp,open,high,low,close,volume)")
    p.add_argument("--out", default="backtest_trades.csv")
    args = p.parse_args()
    backtest(args.candles, args.out)
