"""
訊號生成系統
BUY / SELL / NEUTRAL
+ 條件性多頭（大趨勢空頭但局部反轉）
+ W底 / 頭肩底目標位計算
"""
import numpy as np
import pandas as pd


def generate_signals(df, patterns, market_struct, volume_analysis, sr_levels) -> dict:
    closes = df['Close'].values
    highs  = df['High'].values
    lows   = df['Low'].values
    vols   = df['Volume'].values
    n = len(df)
    current = closes[-1]

    buy_score  = 0
    sell_score = 0
    buy_reasons  = []
    sell_reasons = []

    trend        = market_struct.get('trend', '')
    global_bear  = market_struct.get('global_bear', False)
    global_bull  = market_struct.get('global_bull', False)
    hh = market_struct.get('hh', False)
    hl = market_struct.get('hl', False)
    lh = market_struct.get('lh', False)
    ll = market_struct.get('ll', False)
    vol_r = volume_analysis.get('vol_ratio', 1.0)
    vol_sig = volume_analysis.get('vol_signal', '')

    # ── 1. 市場結構得分 ───────────────────────────────────────────────────
    if "多頭趨勢" == trend:
        buy_score += 35
        buy_reasons.append("主趨勢多頭 (HH+HL)")
    elif "局部多頭反彈" == trend:
        # 大趨勢空頭但局部多頭——條件性做多，給予中等分數
        buy_score += 22
        buy_reasons.append("局部多頭結構 (HH+HL)，大趨勢仍偏空")
    elif "空頭趨勢" == trend:
        sell_score += 35
        sell_reasons.append("主趨勢空頭 (LH+LL)")
    elif "橫盤收斂" == trend:
        # 收斂視乎突破方向
        if market_struct.get('above_ema20') and vol_r > 1.3:
            buy_score += 12
        elif not market_struct.get('above_ema20') and vol_r > 1.3:
            sell_score += 12

    # ── 2. EMA 位置 ───────────────────────────────────────────────────────
    if market_struct.get('above_ema20'):
        buy_score += 8
        buy_reasons.append("站上 EMA20")
    else:
        sell_score += 8
    if market_struct.get('above_ema50'):
        buy_score += 7
        buy_reasons.append("站上 EMA50")
    else:
        sell_score += 7
    if market_struct.get('ema_aligned'):
        buy_score += 5
    else:
        sell_score += 5

    # ── 3. 成交量 ─────────────────────────────────────────────────────────
    if "低位爆量陽線" in vol_sig:
        buy_score += 28
        buy_reasons.append(f"低位爆量陽線 ({vol_r:.1f}x)")
    elif "放量突破" in vol_sig:
        buy_score += 20
        buy_reasons.append("放量突破")
    elif "縮量回調" in vol_sig:
        buy_score += 12
        buy_reasons.append("縮量健康回調")
    elif "高位爆量陰線" in vol_sig:
        sell_score += 28
        sell_reasons.append(f"高位爆量陰線 ({vol_r:.1f}x)")
    elif "放量下跌" in vol_sig:
        sell_score += 20
        sell_reasons.append("放量下跌")

    # ── 4. K線型態得分（精確位置：單K=-1根，雙K=-2~-1根，三K=-5~-1根）────
    # 直接用已分類好的 single_k / double_k / triple_k / macro
    high_weight_bull = {"啟明星", "多頭吞噬", "紅三兵", "穿刺線", "頭肩底", "W底型態", "上升三法"}
    high_weight_bear = {"黃昏星", "空頭吞噬", "三隻烏鴉", "烏雲蓋頂", "頭肩頂", "M頂型態", "下跌三法"}

    all_scored = (patterns.get('single_k', []) +
                  patterns.get('double_k', []) +
                  patterns.get('triple_k', []) +
                  patterns.get('macro', []))

    for p in all_scored:
        pname = p['name']
        if p['bias'] == 'bull':
            weight = 15 if any(k in pname for k in high_weight_bull) else 8
            buy_score += weight
            buy_reasons.append(pname.split()[0])
        elif p['bias'] == 'bear':
            weight = 15 if any(k in pname for k in high_weight_bear) else 8
            sell_score += weight
            sell_reasons.append(pname.split()[0])

    # ── 5. 支撐阻力 ───────────────────────────────────────────────────────
    supports    = sr_levels.get('supports', [])
    resistances = sr_levels.get('resistances', [])

    if supports:
        nearest_sup = supports[0]
        if abs(current - nearest_sup) / current < 0.025:
            buy_score += 18
            buy_reasons.append(f"回踩支撐 ${nearest_sup:.2f}")

    if resistances:
        nearest_res = resistances[0]
        if abs(current - nearest_res) / current < 0.025:
            sell_score += 18
            sell_reasons.append(f"觸及阻力 ${nearest_res:.2f}")

    # ── 6. 結構突破 ───────────────────────────────────────────────────────
    struct_break = market_struct.get('structure_break', '')
    if "突破阻力" in struct_break and vol_r > 1.3:
        buy_score += 22
        buy_reasons.append("放量突破阻力")
    elif "跌破支撐" in struct_break and vol_r > 1.3:
        sell_score += 22
        sell_reasons.append("放量跌破支撐")

    # ── 7. 流動性清洗加分（底部反轉）────────────────────────────────────
    reversal_signal = market_struct.get('reversal_signal', '')
    if reversal_signal and "多頭" in reversal_signal:
        buy_score += 15
        buy_reasons.append("大空頭趨勢中局部多頭反轉訊號")

    # ── 8. 最終訊號 ───────────────────────────────────────────────────────
    # 特殊情況：大趨勢空頭但局部多頭強烈——標記為「條件性多頭」
    conditional_bull = global_bear and buy_score >= 50 and buy_score > sell_score

    if buy_score >= 55 and buy_score > sell_score + 15:
        primary  = "BUY"
        strength = "強" if buy_score >= 75 else "中"
    elif sell_score >= 55 and sell_score > buy_score + 15:
        primary  = "SELL"
        strength = "強" if sell_score >= 75 else "中"
    elif buy_score >= 45 and buy_score > sell_score:
        primary  = "BUY"
        strength = "弱"
    elif sell_score >= 45 and sell_score > buy_score:
        primary  = "SELL"
        strength = "弱"
    else:
        primary  = "NEUTRAL"
        strength = "觀望"

    if conditional_bull and primary == "BUY":
        strength = f"{strength}（條件性，大趨勢仍偏空）"

    # ── 9. 交易建議 ───────────────────────────────────────────────────────
    # 防呆：確保 key_support < current < key_resistance
    sup_candidates = [s for s in supports    if s < current]
    res_candidates = [r for r in resistances if r > current]

    key_support    = sup_candidates[0] if sup_candidates else current * 0.97
    key_resistance = res_candidates[0] if res_candidates else current * 1.03
    breakout_level = key_resistance

    # 極端情況兜底
    if key_support >= current:   key_support    = current * 0.97
    if key_resistance <= current: key_resistance = current * 1.03

    if primary == "BUY":
        stop_loss = key_support * 0.983
        target    = key_resistance
        risk      = max(current - stop_loss, 0.01)
        reward    = max(target - current, 0.01)
        short_dir = "看多 📈"
    elif primary == "SELL":
        stop_loss = key_resistance * 1.017
        target    = key_support
        risk      = max(stop_loss - current, 0.01)
        reward    = max(current - target, 0.01)
        short_dir = "看空 📉"
    else:
        stop_loss = current * 0.97
        target    = current * 1.03
        risk      = current - stop_loss
        reward    = target - current
        short_dir = "觀望 ⟷"
    rrr = f"1 : {reward/risk:.1f}" if risk > 0 else "N/A"

    macro_trend = market_struct.get('trend', '橫盤')
    mid_dir = ("多頭 ▲" if "多頭" in macro_trend
               else ("空頭 ▼" if "空頭" in macro_trend else "中性 ⟷"))

    # ── 10. W底 / 頭肩底目標位（從 macro 型態取）────────────────────────────
    macro_targets = []
    for p in patterns.get('macro', []):
        if p.get('target'):
            macro_targets.append({
                "pattern":  p['name'],
                "target":   p['target'],
                "neckline": p.get('neckline', 0),
            })

    # ── 歷史訊號（回測用）────────────────────────────────────────────────
    signal_history = _generate_historical_signals(df, market_struct)

    return {
        "primary":          primary,
        "strength":         strength,
        "buy_score":        buy_score,
        "sell_score":       sell_score,
        "buy_reasons":      buy_reasons,
        "sell_reasons":     sell_reasons,
        "conditional_bull": conditional_bull,
        "macro_targets":    macro_targets,
        "trade_setup": {
            "short_term":       short_dir,
            "mid_term":         mid_dir,
            "key_support":      key_support,
            "key_resistance":   key_resistance,
            "breakout_level":   breakout_level,
            "stop_loss":        stop_loss,
            "rrr":              rrr,
        },
        "signal_history": signal_history,
    }


def _generate_historical_signals(df, market_struct):
    signals = []
    closes = df['Close'].values
    vols   = df['Volume'].values
    n = len(df)
    avg_vol = np.mean(vols[-20:]) if n >= 20 else np.mean(vols)

    for i in range(5, n - 1):
        momentum = (closes[i] - closes[i-5]) / (closes[i-5] + 1e-9)
        vr = vols[i] / (avg_vol + 1e-9)
        if momentum > 0.02 and vr > 1.3:
            signals.append({"index": i, "type": "BUY",  "price": closes[i]})
        elif momentum < -0.02 and vr > 1.3:
            signals.append({"index": i, "type": "SELL", "price": closes[i]})

    return signals
