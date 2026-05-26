"""
成交量分析 - 集中最新 5 根
訊號判斷完全基於最新 1-5 根K線的量能行為
"""
import pandas as pd
import numpy as np


def analyze_volume(df: pd.DataFrame) -> dict:
    vol   = df['Volume'].values
    close = df['Close'].values
    high  = df['High'].values
    low   = df['Low'].values
    open_ = df['Open'].values
    n     = len(df)

    # ── 基準：20日均量（做比較基準，不做訊號判斷）────────────────────────────
    avg20    = np.mean(vol[-20:]) if n >= 20 else np.mean(vol)
    avg5     = np.mean(vol[-5:])  if n >= 5  else np.mean(vol)
    last_vol = vol[-1]
    vol_ratio = last_vol / avg20 if avg20 > 0 else 1.0

    # ── 最新 5 根量能趨勢 ─────────────────────────────────────────────────────
    recent5_close = close[-5:] if n >= 5 else close
    recent5_vol   = vol[-5:]   if n >= 5 else vol
    recent5_open  = open_[-5:] if n >= 5 else open_

    # 最新5根的平均成交量 vs 20日均量
    recent5_avg    = np.mean(recent5_vol)
    recent5_ratio  = recent5_avg / avg20 if avg20 > 0 else 1.0

    # 最新5根漲跌量比（多頭量 vs 空頭量）
    bull_vol = sum(recent5_vol[i] for i in range(len(recent5_vol))
                   if recent5_close[i] >= recent5_open[i])
    bear_vol = sum(recent5_vol[i] for i in range(len(recent5_vol))
                   if recent5_close[i] < recent5_open[i])
    vol_bias = "多頭量能主導" if bull_vol > bear_vol * 1.2 else (
               "空頭量能主導" if bear_vol > bull_vol * 1.2 else "多空量能均衡")

    # 量能是否遞增（最新5根）
    vol_trend_up = bool(np.polyfit(range(len(recent5_vol)), recent5_vol, 1)[0] > 0)

    # ── 最新1根訊號（最核心）────────────────────────────────────────────────
    last_close = close[-1]
    last_open  = open_[-1]
    last_high  = high[-1]
    last_low   = low[-1]
    is_bull    = last_close >= last_open
    mean20     = np.mean(close[-20:]) if n >= 20 else np.mean(close)

    # 位置判斷（最新收盤相對20日均線）
    is_low_area  = last_close < mean20
    is_high_area = last_close > mean20

    # 影線計算
    body        = abs(last_close - last_open)
    last_range  = last_high - last_low if last_high != last_low else 1e-9
    upper_ratio = (last_high - max(last_close, last_open)) / last_range
    lower_ratio = (min(last_close, last_open) - last_low)  / last_range

    # ── 訊號分類（最新1根 × 成交量）────────────────────────────────────────
    if vol_ratio >= 2.5:
        if is_bull:
            if is_low_area:
                vol_signal    = "低位爆量陽線 💪"
                interpretation = f"低位爆量（{vol_ratio:.1f}x），主力可能吸籌進場"
                smart_vol      = "疑似主力進場"
            else:
                vol_signal    = "高位爆量陽線 ⚠️"
                interpretation = f"高位爆量（{vol_ratio:.1f}x），需警惕主力派發"
                smart_vol      = "疑似主力出貨"
        else:
            if is_low_area:
                vol_signal    = "低位爆量陰線 🔍"
                interpretation = f"低位恐慌殺跌（{vol_ratio:.1f}x），可能為主力洗盤"
                smart_vol      = "恐慌盤殺出 / 主力洗盤"
            else:
                vol_signal    = "高位爆量陰線 🚨"
                interpretation = f"高位大量下跌（{vol_ratio:.1f}x），空頭主導"
                smart_vol      = "主力出貨訊號"

    elif vol_ratio >= 1.5:
        if is_bull:
            vol_signal    = "放量陽線"
            interpretation = f"成交量放大（{vol_ratio:.1f}x）配合上漲，買盤積極"
            smart_vol      = "多頭動能增強"
        else:
            vol_signal    = "放量陰線"
            interpretation = f"成交量放大（{vol_ratio:.1f}x）配合下跌，賣壓沉重"
            smart_vol      = "空頭動能增強"

    elif vol_ratio < 0.5:
        vol_signal    = "極度縮量"
        interpretation = "市場極度觀望，突破前蓄勢"
        smart_vol      = "等待方向突破"

    elif vol_ratio < 0.8:
        if is_bull:
            vol_signal    = "縮量陽線"
            interpretation = "縮量上漲，主力未大量出貨，健康整理"
            smart_vol      = "主力未出貨"
        else:
            vol_signal    = "縮量陰線"
            interpretation = "縮量下跌，賣壓不重，整理性回調"
            smart_vol      = "籌碼鎖定中"
    else:
        vol_signal    = "正常成交量"
        interpretation = f"成交量正常（{vol_ratio:.1f}x均量），無異常"
        smart_vol      = "無明顯異常"

    # ── 特殊影線組合（最新1根）──────────────────────────────────────────────
    extra = ""
    if vol_ratio > 2.0 and upper_ratio > 0.5:
        extra = f"爆量長上影（上影佔{upper_ratio*100:.0f}%）：主力誘多後打壓，高警惕！"
    elif vol_ratio > 2.0 and lower_ratio > 0.5:
        extra = f"爆量長下影（下影佔{lower_ratio*100:.0f}%）：主力掃盤吸籌，關注反彈"

    # ── 最新5根的量價背離偵測 ────────────────────────────────────────────────
    divergence_desc = ""
    if n >= 5:
        price_5_chg = (close[-1] - close[-5]) / close[-5] * 100
        if price_5_chg > 2 and recent5_ratio < 0.8:
            divergence_desc = f"⚠️ 價升量縮背離：近5根上漲{price_5_chg:.1f}%但成交量萎縮，漲勢缺乏支撐"
        elif price_5_chg < -2 and recent5_ratio < 0.8:
            divergence_desc = f"縮量下跌：近5根跌幅{abs(price_5_chg):.1f}%但量能萎縮，跌勢動能不足"
        elif price_5_chg > 2 and recent5_ratio > 1.3:
            divergence_desc = f"✅ 量價齊升：近5根上漲{price_5_chg:.1f}%且量能放大，多頭動能健康"
        elif price_5_chg < -2 and recent5_ratio > 1.3:
            divergence_desc = f"放量下跌：近5根跌幅{abs(price_5_chg):.1f}%且量能放大，空頭動能強勁"

    return {
        "vol_ratio":      vol_ratio,
        "vol_signal":     vol_signal,
        "interpretation": interpretation,
        "smart_vol":      smart_vol,
        "vol_bias":       vol_bias,          # 最新5根多空量比
        "vol_trend_up":   vol_trend_up,      # 最新5根量能是否遞增
        "recent5_ratio":  recent5_ratio,     # 近5根均量 vs 20日均量
        "vol_divergence": divergence_desc,   # 量價背離描述
        "extra_signal":   extra,
        "avg20":          avg20,
        "volumes":        vol.tolist(),
    }
