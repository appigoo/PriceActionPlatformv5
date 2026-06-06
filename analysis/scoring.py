"""
評分系統 - 修正版
核心原則：overall_rating 必須與 primary 訊號方向完全一致，不能自相矛盾。
強度由 buy_score 與 sell_score 的差值決定。
"""


def compute_scores(market_struct, volume_analysis, smart_money, signals) -> dict:
    trend_strength = market_struct.get('trend_strength', 50)
    accum_score    = smart_money.get('accumulation_prob', 0)
    dist_score     = smart_money.get('distribution_risk', 0)
    vol_ratio      = volume_analysis.get('vol_ratio', 1.0)
    price_chg_pct  = volume_analysis.get('price_chg_pct', 0.0)   # 當日漲跌幅

    struct_break   = market_struct.get('structure_break', '')
    trend          = market_struct.get('trend', '')

    # ── breakout_score：納入結構突破和當日跌幅 ───────────────────────────────
    if "突破阻力" in struct_break:
        breakout_score = min(50 + int(vol_ratio * 15), 100)
    elif "跌破支撐" in struct_break:
        breakout_score = max(50 - int(vol_ratio * 15), 0)
    else:
        breakout_score = 45

    # ── dist_score：大跌幅 + 空頭趨勢 → 出貨風險提高 ────────────────────────
    if price_chg_pct <= -3.0:
        dist_score = max(dist_score, 30 + int(abs(price_chg_pct) * 5))
    if price_chg_pct <= -5.0:
        dist_score = max(dist_score, 60)
    if "空頭趨勢" in trend and price_chg_pct < 0:
        dist_score = max(dist_score, 25)
    dist_score = min(dist_score, 100)

    # ── fakeout_score：M頂跌破頸線 → 假突破風險高 ────────────────────────────
    macro_pats = [p.get('name','') for p in signals.get('macro_targets', [])]
    m_top_broken = any('M頂' in p for p in macro_pats)
    fakeout_score = dist_score
    if m_top_broken:
        fakeout_score = max(fakeout_score, 45)
    if price_chg_pct <= -5.0:
        fakeout_score = max(fakeout_score, 35)
    fakeout_score = min(fakeout_score, 100)

    # ── 核心：從 signals 取主訊號和分數 ──────────────────────────────────────
    primary    = signals.get('primary', 'NEUTRAL')
    buy_score  = signals.get('buy_score', 0)
    sell_score = signals.get('sell_score', 0)
    gap        = abs(buy_score - sell_score)   # 多空分差

    # ── overall_rating 完全跟隨 primary，強度由分差決定 ──────────────────────
    # 規則：
    #   primary=BUY  → 只能是 強烈看多 / 偏多
    #   primary=SELL → 只能是 強烈看空 / 偏空
    #   primary=NEUTRAL → 中性
    if primary == 'BUY':
        if gap >= 30:
            overall_rating = "強烈看多 🚀"
        else:
            overall_rating = "偏多 📈"
        dominant_score = buy_score

    elif primary == 'SELL':
        if gap >= 30:
            overall_rating = "強烈看空 💀"
        else:
            overall_rating = "偏空 📉"
        dominant_score = sell_score

    else:
        overall_rating = "中性 ⟷"
        dominant_score = max(buy_score, sell_score, 10)

    # confidence = 主導方向的得分，上限 95
    # 風報比過低時降低信心上限
    trade_setup  = signals.get('trade_setup', {})
    rrr_poor     = trade_setup.get('rrr_poor', False)
    atr          = trade_setup.get('atr', 0)
    # 矛盾型態（多空並存）時也降低信心
    macro_targets = signals.get('macro_targets', [])
    macro_biases  = set(t.get('pattern','')[:2] for t in macro_targets)
    has_conflict  = len(macro_biases) > 1

    conf_cap = 95
    if rrr_poor:       conf_cap = min(conf_cap, 45)   # 風報比差 → 上限45%
    if has_conflict:   conf_cap = min(conf_cap, 65)   # 型態矛盾 → 上限65%
    confidence = min(dominant_score, conf_cap)

    return {
        "trend_strength":    trend_strength,
        "accumulation_score": accum_score,
        "distribution_score": dist_score,
        "breakout_score":    breakout_score,
        "fakeout_score":     fakeout_score,
        "overall_rating":    overall_rating,
        "confidence":        confidence,
        "buy_score":         buy_score,
        "sell_score":        sell_score,
        "gap":               gap,
    }
