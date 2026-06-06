"""
Smart Money Concept (SMC) 主力行為分析
流動性清洗、Stop Hunt、吸籌、派發、假突破、爆量洗盤
"""
import numpy as np
import pandas as pd


def analyze_smart_money(df: pd.DataFrame, vol_analysis: dict) -> dict:
    closes = df['Close'].values
    opens  = df['Open'].values
    highs  = df['High'].values
    lows   = df['Low'].values
    vols   = df['Volume'].values
    n = len(df)

    avg_vol  = np.mean(vols[-20:]) if n >= 20 else np.mean(vols)
    mean_20  = np.mean(closes[-20:]) if n >= 20 else np.mean(closes)
    mean_50  = np.mean(closes[-50:]) if n >= 50 else np.mean(closes)
    current  = closes[-1]
    vol_r    = vols[-1] / avg_vol if avg_vol > 0 else 1.0

    # ── 流動性清洗（Liquidity Grab）─────────────────────────────────────────
    liquidity_grab = "無"
    lg_desc = ""

    # 向下流動性清洗：跌破前5根低點後收回
    recent_low_5 = min(lows[-6:-1]) if n >= 6 else lows[0]
    recent_high_5 = max(highs[-6:-1]) if n >= 6 else highs[0]

    if lows[-1] < recent_low_5 and closes[-1] > recent_low_5:
        grab_depth = (recent_low_5 - lows[-1]) / recent_low_5 * 100
        liquidity_grab = f"下方流動性清洗 ↓↑ ({grab_depth:.1f}%)"
        lg_desc = (f"價格跌破前低 ${recent_low_5:.2f}，觸及 ${lows[-1]:.2f}（向下 {grab_depth:.1f}%）後快速收回，"
                   f"伴隨成交量 {vol_r:.1f}x 均量。典型主力掃除下方止損單後吸籌行為。")

    elif highs[-1] > recent_high_5 and closes[-1] < recent_high_5:
        grab_depth = (highs[-1] - recent_high_5) / recent_high_5 * 100
        liquidity_grab = f"上方流動性清洗 ↑↓ ({grab_depth:.1f}%)"
        lg_desc = (f"價格突破前高 ${recent_high_5:.2f}，觸及 ${highs[-1]:.2f}（向上 {grab_depth:.1f}%）後快速回落，"
                   f"主力誘多吸引追漲後打壓出貨。")

    # ── Stop Hunt 偵測 ────────────────────────────────────────────────────
    stop_hunt = False
    stop_hunt_desc = ""
    if n >= 4:
        # 跌破前2根所有低點後反彈超過前低
        prev_lows = [lows[i] for i in range(n-4, n-1)]
        if lows[-1] < min(prev_lows) and closes[-1] > np.mean(prev_lows):
            stop_hunt = True
            stop_hunt_desc = (f"偵測到 Stop Hunt：價格瞬間跌破 ${min(prev_lows):.2f} 觸發止損，"
                              f"但隨即強力拉回至 ${closes[-1]:.2f}，主力洗盤後重新拉升。")

    # ── 吸籌概率 ──────────────────────────────────────────────────────────
    accum = 0
    accum_factors = []

    if current < mean_20:
        accum += 20
        accum_factors.append("低於20日均價（低位）")
    if current < mean_50:
        accum += 10
        accum_factors.append("低於50日均價（深度低位）")
    if vols[-1] > avg_vol * 1.2 and closes[-1] > opens[-1]:
        accum += 25
        accum_factors.append(f"放量陽線（{vol_r:.1f}x均量）")
    lower_shadow = min(closes[-1], opens[-1]) - lows[-1]
    body = abs(closes[-1] - opens[-1])
    if lower_shadow > body * 1.5:
        accum += 20
        accum_factors.append("長下影承接")
    if "下方" in liquidity_grab:
        accum += 25
        accum_factors.append("流動性清洗後收回")
    if stop_hunt:
        accum += 15
        accum_factors.append("Stop Hunt 後反彈")
    # 連續縮量整理後放量
    if n >= 5 and vols[-1] > avg_vol * 1.5 and np.mean(vols[-5:-1]) < avg_vol * 0.8:
        accum += 15
        accum_factors.append("縮量整理後突然放量")

    accum = min(accum, 100)

    # ── 派發風險 ──────────────────────────────────────────────────────────
    dist = 0
    dist_factors = []

    if current > mean_20 * 1.05:
        dist += 20
        dist_factors.append("高於20日均價5%以上（高位）")
    if vols[-1] > avg_vol * 1.5 and closes[-1] < opens[-1]:
        dist += 30
        dist_factors.append(f"高位放量陰線（{vol_r:.1f}x均量）")
    upper_shadow = highs[-1] - max(closes[-1], opens[-1])
    if upper_shadow > body * 1.5 and vols[-1] > avg_vol:
        dist += 25
        dist_factors.append("放量長上影（主力誘多出貨）")
    if "上方" in liquidity_grab:
        dist += 25
        dist_factors.append("上方流動性清洗")
    if n >= 3:
        # 高位連續縮量但價格未跌：籌碼鎖定完成，準備出貨
        if current > mean_20 and all(vols[i] < avg_vol * 0.7 for i in range(n-3, n)):
            dist += 10
            dist_factors.append("高位持續縮量（籌碼鎖定完成）")

    # ── 大跌幅直接提升派發風險（即使不在高位）──────────────────────────────
    price_chg_pct = 0.0
    if n >= 2 and closes[-2] > 0:
        price_chg_pct = (closes[-1] - closes[-2]) / closes[-2] * 100
    if price_chg_pct <= -3.0:
        drop_dist = int(abs(price_chg_pct) * 8)  # 每跌1%加8分
        dist = max(dist, drop_dist)
        if f"大跌" not in ' '.join(dist_factors):
            dist_factors.append(f"大跌 {price_chg_pct:.1f}%（賣方主導，派發風險提升）")
    if price_chg_pct <= -5.0:
        dist = max(dist, 60)
    if price_chg_pct <= -7.0:
        dist = max(dist, 80)

    dist = min(dist, 100)

    # ── 行為分類 ──────────────────────────────────────────────────────────
    if accum >= 70:
        behavior = "主力吸籌"
        fakeout_risk = "低"
    elif dist >= 70:
        behavior = "主力派發"
        fakeout_risk = "高"
    elif stop_hunt:
        behavior = "Stop Hunt / 主力洗盤"
        fakeout_risk = "中"
    elif "清洗" in liquidity_grab:
        behavior = "流動性清洗"
        fakeout_risk = "中"
    elif vol_r > 2.5:
        behavior = "爆量異動（方向待確認）"
        fakeout_risk = "中"
    elif accum > dist and accum > 30:
        behavior = "疑似吸籌"
        fakeout_risk = "低至中"
    elif dist > accum and dist > 30:
        behavior = "疑似派發"
        fakeout_risk = "中至高"
    else:
        behavior = "正常市場波動"
        fakeout_risk = "低"

    # ── 自然語言描述（對齊專業分析師報告）──────────────────────────────────
    description = _build_description(
        behavior, liquidity_grab, lg_desc,
        stop_hunt, stop_hunt_desc,
        accum, accum_factors,
        dist, dist_factors,
        vol_analysis, vol_r, current, mean_20
    )

    return {
        "behavior":          behavior,
        "accumulation_prob": accum,
        "distribution_risk": dist,
        "liquidity_grab":    liquidity_grab,
        "stop_hunt":         "是 ⚠️" if stop_hunt else "否",
        "fakeout_risk":      fakeout_risk,
        "description":       description,
        "accum_factors":     accum_factors,
        "dist_factors":      dist_factors,
        "lg_desc":           lg_desc,
        "stop_hunt_desc":    stop_hunt_desc,
    }


def _build_description(behavior, liquidity_grab, lg_desc,
                        stop_hunt, stop_hunt_desc,
                        accum, accum_factors,
                        dist, dist_factors,
                        vol_analysis, vol_r, current, mean20):
    parts = []

    # 核心行為描述
    if behavior == "主力吸籌":
        parts.append(
            f"主力吸籌訊號明確（吸籌概率 {accum}%）。"
            f"確認因素：{' / '.join(accum_factors[:4])}。"
        )
    elif behavior == "主力派發":
        parts.append(
            f"主力派發風險高（派發風險 {dist}%）。"
            f"警示因素：{' / '.join(dist_factors[:4])}。"
        )
    elif behavior == "Stop Hunt / 主力洗盤":
        parts.append(stop_hunt_desc)
    elif behavior in ("疑似吸籌",):
        parts.append(f"疑似主力吸籌（概率 {accum}%），但確認度不足，需更多K線驗證。")
    elif behavior in ("疑似派發",):
        parts.append(f"疑似主力派發（風險 {dist}%），建議謹慎，等待確認。")

    # 流動性清洗補充
    if lg_desc:
        parts.append(lg_desc)

    # 成交量異動補充
    extra = vol_analysis.get('extra_signal', '')
    if extra:
        parts.append(extra)

    # 如果無明顯異動
    if not parts:
        parts.append(
            "目前無明顯主力異常行為，市場屬正常波動。"
            f"成交量維持 {vol_r:.1f}x 均量水平，方向性不明確，建議等待明確訊號。"
        )

    return " ".join(parts)
