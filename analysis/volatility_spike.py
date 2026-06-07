"""
異常波動監控模組 - 雙根版
同時檢查最新第-1根和第-2根，任何一根觸發即發警報。

基準統一：兩根都用 bar[-3] 往前的X根作為基準
（不含最新兩根，避免異常值污染基準）

price_ratio[-1] = |close[-1]-close[-2]|/close[-2]  ÷ avg(price_abs[-3-X:-3])
price_ratio[-2] = |close[-2]-close[-3]|/close[-3]  ÷ avg(price_abs[-3-X:-3])

vol_ratio[-1]   = |vol[-1]-vol[-2]|/vol[-2]        ÷ avg(vol_abs[-3-X:-3])
vol_ratio[-2]   = |vol[-2]-vol[-3]|/vol[-3]        ÷ avg(vol_abs[-3-X:-3])

觸發：price_ratio >= Y AND vol_ratio >= Y（任意一根）
"""
import numpy as np
import pandas as pd


def compute_volatility_spike(df: pd.DataFrame, x: int = 20) -> dict | None:
    """
    計算所有歷史K線的波動比率，並針對最新兩根做雙根分析。

    回傳：
        bars          : 歷史所有bar資料（用於圖表和觸發記錄）
        bar_minus1    : 第-1根詳細數據
        bar_minus2    : 第-2根詳細數據
        price_ratios  : 全部price_ratio序列
        volume_ratios : 全部volume_ratio序列
        x, n
    """
    closes = df['Close'].values
    vols   = df['Volume'].values
    dates  = df.index
    n      = len(df)

    # 需要至少 X+3 根（X根基準 + 第-3根 + 第-2根 + 第-1根）
    if n < x + 3:
        return None

    # ── 計算每根的變化量 ──────────────────────────────────────────────────────
    # 價格：取絕對值（暴漲和暴跌都算異常）
    # 成交量：不取絕對值，只有量增（>0）才算有效訊號，量縮設為 0
    price_abs = np.zeros(n)
    vol_abs   = np.zeros(n)
    for i in range(1, n):
        if closes[i-1] > 0:
            price_abs[i] = abs(closes[i] - closes[i-1]) / closes[i-1] * 100
        if vols[i-1] > 0:
            raw_vol_chg  = (vols[i] - vols[i-1]) / vols[i-1] * 100
            vol_abs[i]   = max(raw_vol_chg, 0.0)   # 量縮設為 0，不觸發

    # ── 歷史序列計算（每根對比其前X根基準）──────────────────────────────────
    price_ratios  = np.full(n, np.nan)
    volume_ratios = np.full(n, np.nan)
    bars          = []

    for i in range(x + 1, n):
        avg_p = np.mean(price_abs[i-x:i]) or 1e-9
        # 基準均值只計算量增的根（排除量縮的0值），使基準更準確
        base_v_window = vol_abs[i-x:i]
        pos_v = base_v_window[base_v_window > 0]
        avg_v = float(np.mean(pos_v)) if len(pos_v) > 0 else 1e-9
        pr    = price_abs[i] / avg_p
        vr    = vol_abs[i]   / avg_v

        price_ratios[i]  = pr
        volume_ratios[i] = vr

        # 後5根數據（用於觸發後走勢分析）
        future_closes = []
        future_vols   = []
        for fj in range(1, 6):
            if i + fj < n:
                future_closes.append(float(closes[i + fj]))
                future_vols.append(float(vols[i + fj]))

        bars.append({
            "bar_idx":       i,
            "date":          dates[i],
            "bar_label":     "",
            "close":         float(closes[i]),
            "price_chg":     float(closes[i] - closes[i-1]),
            "price_abs":     float(price_abs[i]),
            "avg_price_abs": float(avg_p),
            "price_ratio":   float(pr),
            "vol":           float(vols[i]),
            "vol_chg":       float(vols[i] - vols[i-1]),
            "vol_abs":       float(vol_abs[i]),
            "avg_vol_abs":   float(avg_v),
            "vol_ratio":     float(vr),
            "future_closes": future_closes,   # 後5根收盤
            "future_vols":   future_vols,     # 後5根成交量
        })

    if not bars:
        return None

    # ── 雙根分析：-1根和-2根使用同一個基準（bar[-3]往前X根）────────────────
    # 基準窗口：index[-3-X : -3]（不含最新兩根）
    base_start = n - 3 - x
    base_end   = n - 2          # 不含 -2、-1 根（即只到 -3 根）

    if base_start < 0:
        return None

    base_price = price_abs[base_start:base_end]
    base_vol   = vol_abs[base_start:base_end]
    avg_p_base = float(np.mean(base_price)) if np.mean(base_price) > 0 else 1e-9
    # 基準成交量均值只計算量增的根
    pos_base_v = base_vol[base_vol > 0]
    avg_v_base = float(np.mean(pos_base_v)) if len(pos_base_v) > 0 else 1e-9

    def _make_bar(offset: int, label: str) -> dict:
        """offset=1 → bar[-1], offset=2 → bar[-2]"""
        idx   = n - offset
        p_abs = float(price_abs[idx])
        v_abs = float(vol_abs[idx])
        pr    = p_abs / avg_p_base
        vr    = v_abs / avg_v_base
        return {
            "bar_idx":       idx,
            "date":          dates[idx],
            "bar_label":     label,
            "close":         float(closes[idx]),
            "price_chg":     float(closes[idx] - closes[idx-1]),
            "price_abs":     p_abs,
            "avg_price_abs": avg_p_base,
            "price_ratio":   pr,
            "vol":           float(vols[idx]),
            "vol_chg":       float(vols[idx] - vols[idx-1]),
            "vol_abs":       v_abs,
            "avg_vol_abs":   avg_v_base,
            "vol_ratio":     vr,
        }

    bar_m1 = _make_bar(1, f"最新根（-1）")
    bar_m2 = _make_bar(2, f"前一根（-2）")

    return {
        "bars":           bars,
        "bar_minus1":     bar_m1,
        "bar_minus2":     bar_m2,
        "latest":         bar_m1,       # 向下相容
        "price_ratios":   price_ratios,
        "volume_ratios":  volume_ratios,
        "avg_p_base":     avg_p_base,
        "avg_v_base":     avg_v_base,
        "dates":          dates,
        "x":              x,
        "n":              n,
    }


def find_triggered_bars(result: dict, y: float) -> list[dict]:
    """找出歷史上同時觸發兩個條件的bar（用於圖表標記和統計）"""
    if result is None:
        return []
    return [b for b in result['bars']
            if b['price_ratio'] >= y and b['vol_ratio'] >= y]


def get_triggered_two_bars(result: dict, y: float) -> list[dict]:
    """
    檢查最新兩根是否觸發，回傳觸發的bar列表（可能0~2個）
    每個bar包含 bar_label 說明是哪根
    """
    if result is None:
        return []
    triggered = []
    for bar in [result['bar_minus2'], result['bar_minus1']]:
        if bar['price_ratio'] >= y and bar['vol_ratio'] >= y:
            triggered.append(bar)
    return triggered


def bar_status(bar: dict, y: float) -> tuple[str, str]:
    """
    回傳 (狀態圖示, 背景色)
    ⚡ 兩個均超標 → 觸發
    🟡 只有一個超標 → 接近觸發
    ○  均未超標 → 正常
    """
    p_ok = bar['price_ratio'] >= y
    v_ok = bar['vol_ratio']   >= y
    if p_ok and v_ok:
        return "⚡ 觸發", "#fdecea"
    elif p_ok or v_ok:
        return "🟡 接近", "#fffde7"
    else:
        return "○ 正常", "#f9f7f4"


def build_spike_tg_msg(ticker: str, interval: str, result: dict,
                       y: float, tg_bar: dict) -> str:
    """生成 Telegram 警報訊息"""
    import datetime as _dt
    nl  = chr(10)
    sep = chr(8212) * 22
    now = _dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    b   = tg_bar
    x   = result['x']

    lines = [
        "⚡ *" + ticker + " 異常波動警報*",
        sep,
        "觸發根：*" + b['bar_label'] + "*",
        "觸發條件：價格波動 AND 成交量波動同時 ≥ " + f"{y:.1f}x",
        "",
        "📊 *價格波動*",
        "• 漲跌幅：" + f"{b['price_abs']:+.2f}%",
        "• 前" + str(x) + "根基準均值：" + f"{b['avg_price_abs']:.2f}%",
        "• 波動倍數：*" + f"{b['price_ratio']:.2f}x*",
        "",
        "📦 *成交量放量*",
        "• 量增幅：+" + f"{b['vol_abs']:.2f}%（對比前一根）",
        "• 前" + str(x) + "根量增均值：" + f"{b['avg_vol_abs']:.2f}%",
        "• 放量倍數：*" + f"{b['vol_ratio']:.2f}x*",
        "",
        "💰 收盤：$" + f"{b['close']:.2f}",
        "時間：" + str(b['date'])[:16],
        "週期：" + interval,
        sep,
        "_SMC Pro · " + now + "_",
    ]
    return nl.join(lines)
