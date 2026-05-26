"""Support and Resistance Level Detection - 修正版"""
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema


def find_support_resistance(df: pd.DataFrame, n_levels: int = 5) -> dict:
    closes = df['Close'].values
    highs  = df['High'].values
    lows   = df['Low'].values
    n      = len(df)
    current = closes[-1]

    order = max(3, n // 20)
    local_max_idx = argrelextrema(highs, np.greater_equal, order=order)[0]
    local_min_idx = argrelextrema(lows,  np.less_equal,   order=order)[0]

    resistance_prices = highs[local_max_idx].tolist()
    support_prices    = lows[local_min_idx].tolist()

    def cluster_levels(prices, tol=0.005):
        if not prices:
            return []
        prices = sorted(prices)
        clusters, cur = [], [prices[0]]
        for p in prices[1:]:
            if abs(p - cur[-1]) / cur[-1] < tol:
                cur.append(p)
            else:
                clusters.append(float(np.mean(cur)))
                cur = [p]
        clusters.append(float(np.mean(cur)))
        return clusters

    resistances = cluster_levels(resistance_prices)
    supports    = cluster_levels(support_prices)

    # ── 嚴格過濾：支撐必須低於當前價，阻力必須高於當前價 ──────────────────
    # 不允許任何容差，確保支撐 < current < 阻力
    key_sup = sorted(
        [s for s in supports if s < current],   # 嚴格低於
        reverse=True                              # 由近到遠
    )[:n_levels]

    key_res = sorted(
        [r for r in resistances if r > current], # 嚴格高於
    )[:n_levels]                                  # 由近到遠

    # fallback：若找不到支撐/阻力，用近期高低點
    recent_high = float(max(highs[-20:])) if n >= 20 else float(max(highs))
    recent_low  = float(min(lows[-20:]))  if n >= 20 else float(min(lows))

    if not key_sup:
        key_sup = [recent_low]
    if not key_res:
        key_res = [recent_high]

    # Demand / Supply zones
    demand_zones = [(s * 0.99, s * 1.01) for s in key_sup[:3]]
    supply_zones = [(r * 0.99, r * 1.01) for r in key_res[:3]]

    return {
        "resistances":  key_res,
        "supports":     key_sup,
        "demand_zones": demand_zones,
        "supply_zones": supply_zones,
        "recent_high":  recent_high,
        "recent_low":   recent_low,
        "current":      current,
    }
