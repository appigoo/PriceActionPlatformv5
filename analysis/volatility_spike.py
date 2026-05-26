"""
異常波動監控模組
指標一：最新一根收盤漲跌幅絕對值 vs 前X根收盤漲跌幅絕對值的平均
指標二：最新一根成交量變化絕對值（對比前一根）vs 前X根成交量變化絕對值的平均
兩個指標同時 >= Y 倍 → 觸發警報
"""
import numpy as np
import pandas as pd


def compute_volatility_spike(df: pd.DataFrame, x: int = 20) -> dict:
    """
    計算每根K線的兩個波動比率，並返回完整歷史序列。

    price_ratio[i]  = |close[i]-close[i-1]|/close[i-1]  ÷  前X根price_abs的均值
    volume_ratio[i] = |vol[i]-vol[i-1]|/vol[i-1]        ÷  前X根volume_abs的均值

    回傳：
        bars       : 所有bar的資料（日期、數值、比率）
        latest     : 最新一根的詳細數據
        price_ratios  : 全部price_ratio序列（用於圖表）
        volume_ratios : 全部volume_ratio序列（用於圖表）
        triggered_bars: 歷史上同時觸發的bar index列表
    """
    closes = df['Close'].values
    vols   = df['Volume'].values
    dates  = df.index
    n      = len(df)

    if n < x + 2:
        return None

    # ── 計算每根的絕對變化量 ─────────────────────────────────────────────────
    # 收盤漲跌幅絕對值
    price_abs = np.zeros(n)
    for i in range(1, n):
        price_abs[i] = abs(closes[i] - closes[i-1]) / closes[i-1] * 100

    # 成交量變化絕對值（對比前一根）
    vol_abs = np.zeros(n)
    for i in range(1, n):
        if vols[i-1] > 0:
            vol_abs[i] = abs(vols[i] - vols[i-1]) / vols[i-1] * 100

    # ── 計算每根的波動比率（相對前X根的均值）────────────────────────────────
    price_ratios  = np.full(n, np.nan)
    volume_ratios = np.full(n, np.nan)
    bars          = []

    for i in range(x + 1, n):
        # 前X根（不含當根）的均值
        prev_price_abs  = price_abs[i-x:i]
        prev_vol_abs    = vol_abs[i-x:i]
        avg_price_abs   = np.mean(prev_price_abs)  if np.mean(prev_price_abs)  > 0 else 1e-9
        avg_vol_abs     = np.mean(prev_vol_abs)    if np.mean(prev_vol_abs)    > 0 else 1e-9

        pr = price_abs[i]  / avg_price_abs
        vr = vol_abs[i]    / avg_vol_abs

        price_ratios[i]  = pr
        volume_ratios[i] = vr

        bars.append({
            "bar_idx":        i,
            "date":           dates[i],
            "close":          float(closes[i]),
            "price_abs":      float(price_abs[i]),
            "avg_price_abs":  float(avg_price_abs),
            "price_ratio":    float(pr),
            "vol":            float(vols[i]),
            "vol_abs":        float(vol_abs[i]),
            "avg_vol_abs":    float(avg_vol_abs),
            "vol_ratio":      float(vr),
        })

    if not bars:
        return None

    latest = bars[-1]

    return {
        "bars":           bars,
        "latest":         latest,
        "price_ratios":   price_ratios,
        "volume_ratios":  volume_ratios,
        "dates":          dates,
        "x":              x,
        "n":              n,
    }


def find_triggered_bars(result: dict, y: float) -> list[dict]:
    """找出歷史上同時觸發兩個條件（price_ratio >= y AND vol_ratio >= y）的bar"""
    if result is None:
        return []
    return [b for b in result['bars']
            if b['price_ratio'] >= y and b['vol_ratio'] >= y]


def build_spike_tg_msg(ticker: str, interval: str, result: dict,
                       y: float, tg_bar: dict) -> str:
    """生成 Telegram 警報訊息"""
    import datetime as _dt
    nl  = chr(10)
    sep = chr(8212) * 22
    now = _dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    lat = tg_bar

    lines = [
        "⚡ *" + ticker + " 異常波動警報*",
        sep,
        "觸發條件：價格波動 AND 成交量波動同時 ≥ " + f"{y:.1f}x",
        "",
        "📊 *價格波動*",
        "• 最新漲跌幅：" + f"{lat['price_abs']:+.2f}%",
        "• 前" + str(result['x']) + "根均值：" + f"{lat['avg_price_abs']:.2f}%",
        "• 波動倍數：*" + f"{lat['price_ratio']:.2f}x*",
        "",
        "📦 *成交量波動*",
        "• 最新量變幅：" + f"{lat['vol_abs']:+.2f}%",
        "• 前" + str(result['x']) + "根均值：" + f"{lat['avg_vol_abs']:.2f}%",
        "• 波動倍數：*" + f"{lat['vol_ratio']:.2f}x*",
        "",
        "💰 當前收盤：$" + f"{lat['close']:.2f}",
        "時間：" + str(lat['date'])[:16],
        "週期：" + interval,
        sep,
        "_SMC Pro · " + now + "_",
    ]
    return nl.join(lines)
