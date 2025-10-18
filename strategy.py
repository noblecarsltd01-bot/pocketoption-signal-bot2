# strategy.py
import pandas as pd
import ta
import numpy as np

def add_indicators(df, ema_short=9, ema_long=21, rsi_period=14, macd_fast=12, macd_slow=26, macd_signal=9):
    df = df.copy()
    df['ema_short'] = ta.trend.ema_indicator(df['close'], ema_short)
    df['ema_long'] = ta.trend.ema_indicator(df['close'], ema_long)
    df['rsi'] = ta.momentum.rsi(df['close'], rsi_period)
    macd = ta.trend.MACD(df['close'], window_slow=macd_slow, window_fast=macd_fast, window_sign=macd_signal)
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_hist'] = macd.macd_diff()
    return df

def find_swing_levels(df, lookback=100, tol_frac=0.0009):
    highs = []
    lows = []
    arr_h = df['high'].values
    arr_l = df['low'].values
    for i in range(2, len(df)-2):
        if arr_h[i] > max(arr_h[i-2:i+3]):
            highs.append(arr_h[i])
        if arr_l[i] < min(arr_l[i-2:i+3]):
            lows.append(arr_l[i])
    def cluster(levels):
        clusters = []
        for price in levels:
            placed = False
            for j, lev in enumerate(clusters):
                if abs(price - lev) <= lev * tol_frac:
                    clusters[j] = (clusters[j] + price) / 2
                    placed = True
                    break
            if not placed:
                clusters.append(price)
        clusters.sort()
        return clusters
    return cluster(lows), cluster(highs)

def detect_rsi_divergence(df, lookback=40):
    seg = df[-lookback:]
    lows = []
    highs = []
    for i in range(2, len(seg)-2):
        if seg['low'].iloc[i] < seg['low'].iloc[i-2:i+3].min():
            lows.append(seg.index[i])
        if seg['high'].iloc[i] > seg['high'].iloc[i-2:i+3].max():
            highs.append(seg.index[i])
    if len(lows) >= 2:
        p1, p2 = lows[-2], lows[-1]
        price_p1 = seg.loc[p1]['low']; price_p2 = seg.loc[p2]['low']
        rsi_p1 = seg.loc[p1]['rsi']; rsi_p2 = seg.loc[p2]['rsi']
        if price_p2 < price_p1 and rsi_p2 > rsi_p1:
            return 'bullish'
    if len(highs) >= 2:
        p1, p2 = highs[-2], highs[-1]
        price_p1 = seg.loc[p1]['high']; price_p2 = seg.loc[p2]['high']
        rsi_p1 = seg.loc[p1]['rsi']; rsi_p2 = seg.loc[p2]['rsi']
        if price_p2 > price_p1 and rsi_p2 < rsi_p1:
            return 'bearish'
    return None

def detect_macd_divergence(df, lookback=40):
    seg = df[-lookback:]
    lows = []
    highs = []
    for i in range(2, len(seg)-2):
        if seg['low'].iloc[i] < seg['low'].iloc[i-2:i+3].min():
            lows.append(seg.index[i])
        if seg['high'].iloc[i] > seg['high'].iloc[i-2:i+3].max():
            highs.append(seg.index[i])
    if len(lows) >= 2:
        p1, p2 = lows[-2], lows[-1]
        price_p1 = seg.loc[p1]['low']; price_p2 = seg.loc[p2]['low']
        macd_p1 = seg.loc[p1]['macd_hist']; macd_p2 = seg.loc[p2]['macd_hist']
        if price_p2 < price_p1 and macd_p2 > macd_p1:
            return 'bullish'
    if len(highs) >= 2:
        p1, p2 = highs[-2], highs[-1]
        price_p1 = seg.loc[p1]['high']; price_p2 = seg.loc[p2]['high']
        macd_p1 = seg.loc[p1]['macd_hist']; macd_p2 = seg.loc[p2]['macd_hist']
        if price_p2 > price_p1 and macd_p2 < macd_p1:
            return 'bearish'
    return None

def combined_divergence(df):
    rsi = detect_rsi_divergence(df)
    macd = detect_macd_divergence(df)
    if rsi == macd and rsi in ('bullish','bearish'):
        return rsi
    return None

def price_near_levels(price, levels, tol_frac=0.0009):
    for lev in levels:
        if abs(price - lev) <= lev * tol_frac:
            return True, lev
    return False, None
