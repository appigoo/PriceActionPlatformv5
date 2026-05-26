"""
市場結構分析 - 修正版
核心修正：
1. window 根據 bar 數量自適應（360根不能用 window=5）
2. 最小振幅過濾：擺動點之間必須 > ATR，排除噪音小波
3. 雙時間框架：長期擺動點判斷大趨勢 / 近期30根判斷局部結構，分開不互相污染
"""
import numpy as np
import pandas as pd


def _ema(data, period):
    k = 2 / (period + 1)
    ema = np.zeros(len(data))
    ema[0] = data[0]
    for i in range(1, len(data)):
        ema[i] = data[i] * k + ema[i-1] * (1 - k)
    return ema


def find_swing_points(df: pd.DataFrame, window: int) -> dict:
    """找擺動高低點，並用最小振幅過濾噪音"""
    highs = df['High'].values
    lows  = df['Low'].values
    n     = len(df)

    # ATR 用來過濾太小的擺動（小於 0.5 ATR 的不算）
    atr_arr = (df['High'] - df['Low']).rolling(14).mean().bfill().values
    atr_mean = np.mean(atr_arr[-20:]) if n >= 20 else atr_arr[-1]

    sh, sl = [], []
    for i in range(window, n - window):
        local_max = max(highs[i-window:i+window+1])
        local_min = min(lows[i-window:i+window+1])

        if highs[i] == local_max:
            # 過濾：這個高點必須比左右 window 根的低點高出至少 0.5 ATR
            surrounding_lows = min(lows[i-window:i+window+1])
            if highs[i] - surrounding_lows >= atr_mean * 0.5:
                sh.append((i, highs[i]))

        if lows[i] == local_min:
            surrounding_highs = max(highs[i-window:i+window+1])
            if surrounding_highs - lows[i] >= atr_mean * 0.5:
                sl.append((i, lows[i]))

    return {"swing_highs": sh, "swing_lows": sl}


def analyze_market_structure(df: pd.DataFrame) -> dict:
    n       = len(df)
    closes  = df['Close'].values
    highs   = df['High'].values
    lows    = df['Low'].values
    current = closes[-1]

    ema20 = _ema(closes, 20)
    ema50 = _ema(closes, 50)

    # ── EMA 斜率（全局趨勢判斷）─────────────────────────────────────────────
    ema50_slope = (ema50[-1] - ema50[-10]) / (ema50[-10] + 1e-9) * 100
    ema20_slope = (ema20[-1] - ema20[-5])  / (ema20[-5]  + 1e-9) * 100
    global_bull = ema50_slope >  0.5
    global_bear = ema50_slope < -0.5
    local_bull  = ema20_slope >  0.3
    local_bear  = ema20_slope < -0.3

    # ── 自適應 window ────────────────────────────────────────────────────────
    # 規則：window = max(5, n // 15)
    # 120根 → window=8，360根 → window=24，500根 → window=33
    window_global = max(5, n // 15)
    window_local  = max(3, min(8, n // 30))   # 近期結構用更小窗口，捕捉最新反彈

    # ── 長期擺動點（判斷大趨勢結構）────────────────────────────────────────
    swings_global = find_swing_points(df, window_global)
    sh_global = swings_global['swing_highs'][-6:]
    sl_global = swings_global['swing_lows'][-6:]

    # ── 近期擺動點（判斷局部/最新結構，只看最近 60 根）────────────────────
    local_bars = min(60, n)
    df_local   = df.iloc[-local_bars:]
    swings_local = find_swing_points(df_local, window_local)

    # 索引換算回全局（+offset）
    offset = n - local_bars
    sh_local = [(i + offset, v) for i, v in swings_local['swing_highs'][-4:]]
    sl_local = [(i + offset, v) for i, v in swings_local['swing_lows'][-4:]]

    # ── 選擇哪套擺動點做 HH/HL 判斷 ──────────────────────────────────────────
    # 優先用局部擺動點（更能反映最新市場方向）
    # 若局部點不足則 fallback 到全局點
    sh_use = sh_local if len(sh_local) >= 2 else sh_global
    sl_use = sl_local if len(sl_local) >= 2 else sl_global

    # 圖表顯示用（取全局點，讓圖上標記更清晰）
    sh_display = sh_global[-8:]
    sl_display = sl_global[-8:]

    if len(sh_use) < 2 or len(sl_use) < 2:
        return _default_struct(ema20, ema50, current, highs, lows, n,
                               sh_display, sl_display,
                               global_bull, global_bear, local_bull,
                               ema20_slope, ema50_slope)

    # ── HH / HL / LH / LL 判斷 ───────────────────────────────────────────────
    hh = sh_use[-1][1] > sh_use[-2][1]
    hl = sl_use[-1][1] > sl_use[-2][1]
    lh = sh_use[-1][1] < sh_use[-2][1]
    ll = sl_use[-1][1] < sl_use[-2][1]

    # ── 大趨勢結構（用全局擺動點再判斷一次）──────────────────────────────────
    macro_hh = macro_hl = macro_lh = macro_ll = False
    if len(sh_global) >= 2 and len(sl_global) >= 2:
        macro_hh = sh_global[-1][1] > sh_global[-2][1]
        macro_hl = sl_global[-1][1] > sl_global[-2][1]
        macro_lh = sh_global[-1][1] < sh_global[-2][1]
        macro_ll = sl_global[-1][1] < sl_global[-2][1]

    # ── 趨勢判斷（局部結構 + EMA 大趨勢結合）────────────────────────────────
    if hh and hl:
        if global_bull:
            trend = "多頭趨勢"
            sub   = "Higher High + Higher Low，主趨勢多頭延續"
        else:
            trend = "局部多頭反彈"
            sub   = "近期出現 HH + HL 結構，大趨勢仍偏空，注意上方阻力"
        swing_desc    = "HH ▲ + HL ▲"
        strength_base = 80 if global_bull else 62

    elif lh and ll:
        # 再確認：如果局部點顯示 LH+LL，但 EMA20 已明顯回升，降低空頭權重
        if local_bull:
            trend = "局部反彈中"
            sub   = "擺動結構仍為 LH+LL，但 EMA20 開始上翹，局部動能轉強"
            swing_desc    = "LH ▼ + LL ▼（EMA20 回升）"
            strength_base = 38
        else:
            trend = "空頭趨勢"
            sub   = "Lower High + Lower Low，空頭結構完整"
            swing_desc    = "LH ▼ + LL ▼"
            strength_base = 20

    elif lh and hl:
        trend = "橫盤收斂"
        sub   = "Lower High + Higher Low，三角收斂蓄勢"
        swing_desc    = "LH ▼ + HL ▲（收斂）"
        strength_base = 50

    elif hh and ll:
        trend = "趨勢發散"
        sub   = "Higher High + Lower Low，多空均有力，震盪擴大"
        swing_desc    = "HH ▲ + LL ▼（發散）"
        strength_base = 45

    else:
        trend = "橫盤整理"
        sub   = "無明確擺動結構，區間震盪"
        swing_desc    = "無明確 HH/HL/LH/LL"
        strength_base = 45

    # ── 趨勢反轉偵測 ─────────────────────────────────────────────────────────
    reversal_signal = ""
    if global_bear and hh and hl:
        reversal_signal = "⚠️ 大趨勢空頭中出現局部多頭結構（HH+HL），疑似底部反轉初期"
    elif global_bear and local_bull and not (lh and ll):
        reversal_signal = "⚠️ EMA20 開始回升，局部動能轉多，空頭結構可能弱化"
    elif global_bull and lh and ll:
        reversal_signal = "⚠️ 大趨勢多頭中出現局部空頭結構（LH+LL），疑似頂部反轉初期"

    # ── 趨勢強度 ─────────────────────────────────────────────────────────────
    strength       = strength_base
    above_ema20    = current > ema20[-1]
    above_ema50    = current > ema50[-1]
    ema_aligned    = ema20[-1] > ema50[-1]

    if "多頭" in trend:
        if above_ema20:  strength = min(strength + 8,  100)
        if above_ema50:  strength = min(strength + 7,  100)
        if ema_aligned:  strength = min(strength + 5,  100)
    elif "空頭" in trend:
        if not above_ema20: strength = max(strength - 8, 0)
        if not above_ema50: strength = max(strength - 7, 0)
        if not ema_aligned: strength = max(strength - 5, 0)

    # ── 結構突破 ──────────────────────────────────────────────────────────────
    recent_high = max(highs[-20:])
    recent_low  = min(lows[-20:])
    if current > recent_high * 0.999:
        struct_break = "突破阻力 ↑"
    elif current < recent_low * 1.001:
        struct_break = "跌破支撐 ↓"
    else:
        struct_break = "區間內整理"

    # ── 市場狀態 ──────────────────────────────────────────────────────────────
    atr     = float((df['High'] - df['Low']).rolling(14).mean().iloc[-1])
    vol_std = float(df['Close'].rolling(20).std().iloc[-1])
    if atr > vol_std * 1.6:
        market_state = "高波動擴張"
    elif atr < vol_std * 0.6:
        market_state = "低波動蓄勢"
    else:
        market_state = "正常波動"

    return {
        "trend":           trend,
        "sub_trend":       sub,
        "swing_desc":      swing_desc,
        "trend_strength":  int(strength),
        "market_state":    market_state,
        "structure_break": struct_break,
        "reversal_signal": reversal_signal,
        "swing_highs":     sh_display,
        "swing_lows":      sl_display,
        "ema20":           ema20,
        "ema50":           ema50,
        "global_bull":     global_bull,
        "global_bear":     global_bear,
        "local_bull":      local_bull,
        "hh": hh, "hl": hl, "lh": lh, "ll": ll,
        "macro_hh": macro_hh, "macro_hl": macro_hl,
        "macro_lh": macro_lh, "macro_ll": macro_ll,
        "above_ema20":     above_ema20,
        "above_ema50":     above_ema50,
        "ema_aligned":     ema_aligned,
        "ema20_slope":     ema20_slope,
        "ema50_slope":     ema50_slope,
        "recent_high":     recent_high,
        "recent_low":      recent_low,
    }


def _default_struct(ema20, ema50, current, highs, lows, n,
                    sh, sl, global_bull, global_bear, local_bull,
                    ema20_slope, ema50_slope):
    return {
        "trend": "橫盤整理", "sub_trend": "數據不足",
        "swing_desc": "N/A", "trend_strength": 45,
        "market_state": "觀望", "structure_break": "無",
        "reversal_signal": "", "swing_highs": sh, "swing_lows": sl,
        "ema20": ema20, "ema50": ema50,
        "global_bull": global_bull, "global_bear": global_bear,
        "local_bull": local_bull,
        "hh": False, "hl": False, "lh": False, "ll": False,
        "macro_hh": False, "macro_hl": False, "macro_lh": False, "macro_ll": False,
        "above_ema20": current > ema20[-1], "above_ema50": current > ema50[-1],
        "ema_aligned": ema20[-1] > ema50[-1],
        "ema20_slope": ema20_slope, "ema50_slope": ema50_slope,
        "recent_high": max(highs[-20:]) if n >= 20 else highs[-1],
        "recent_low":  min(lows[-20:])  if n >= 20 else lows[-1],
    }
