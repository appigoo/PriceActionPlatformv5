"""
跳空歷史分析模組 - 修正版
Bug 修復：
  1. avg_vol20 改用 rolling mean，避免 convolve padding zeros 問題
  2. Gap Up  回補條件：lows[j]  <= gap_low  (prev_high，缺口下沿)
  3. Gap Down 回補條件：highs[j] >= gap_high (prev_low， 缺口下沿)
  4. UI 標籤更精確：「第N根收盤 vs 當根收盤」
"""
import numpy as np
import pandas as pd


def scan_gaps(df: pd.DataFrame, min_gap_atr_ratio: float = 0.3) -> list[dict]:
    """
    掃描所有跳空事件
    min_gap_atr_ratio: 最小缺口過濾，缺口幅度需 >= ATR × 此比例
                       預設 0.3（即至少 0.3 個 ATR），過濾微小噪音缺口
    """
    gaps   = []
    closes = df['Close'].values
    opens  = df['Open'].values
    highs  = df['High'].values
    lows   = df['Low'].values
    vols   = df['Volume'].values
    dates  = df.index
    n      = len(df)

    # ── 計算 ATR(14) 用於最小缺口過濾 ───────────────────────────────────────
    atr_period = min(14, n - 1)
    tr_arr = np.zeros(n)
    for k in range(1, n):
        tr_arr[k] = max(highs[k] - lows[k],
                        abs(highs[k] - closes[k-1]),
                        abs(lows[k]  - closes[k-1]))
    # 滾動14根ATR
    atr_rolling = pd.Series(tr_arr).rolling(atr_period, min_periods=1).mean().values

    # ── 計算前20根均量（不含當根本身）──────────────────────────────────────
    vol_series = pd.Series(vols)
    avg_vol20  = vol_series.shift(1).rolling(20, min_periods=1).mean().values

    for i in range(1, n):
        cur_high   = float(highs[i])
        cur_low    = float(lows[i])
        cur_close  = float(closes[i])
        cur_open   = float(opens[i])
        cur_vol    = float(vols[i])
        prev_high  = float(highs[i-1])
        prev_low   = float(lows[i-1])
        prev_close = float(closes[i-1])

        avg_v     = float(avg_vol20[i]) if avg_vol20[i] > 0 else 1.0
        vol_ratio = cur_vol / avg_v

        if cur_low > prev_high:
            direction = "up"
            gap_size  = (cur_low - prev_high) / prev_high * 100
            gap_low   = prev_high   # 缺口下沿
            gap_high  = cur_low     # 缺口上沿

        elif cur_high < prev_low:
            direction = "down"
            gap_size  = (prev_low - cur_high) / prev_low * 100
            gap_low   = cur_high    # 缺口上沿
            gap_high  = prev_low    # 缺口下沿

        else:
            continue

        # ── ATR 最小缺口過濾：缺口幅度需 >= min_gap_atr_ratio 個 ATR ────────
        atr_now     = float(atr_rolling[i]) if atr_rolling[i] > 0 else 1e-9
        atr_pct_now = atr_now / cur_close * 100
        min_gap_pct = atr_pct_now * min_gap_atr_ratio
        if gap_size < min_gap_pct:
            continue   # 過濾微小噪音缺口

        close_chg     = (cur_close - prev_close) / prev_close * 100
        future_closes = [float(closes[i+j]) for j in range(1, 6) if i+j < n]  # 後5根收盤
        future_vols   = [float(vols[i+j])   for j in range(1, 6) if i+j < n]  # 後5根成交量

        gaps.append({
            "bar_idx":       i,
            "date":          dates[i],
            "direction":     direction,
            "gap_size":      gap_size,
            "gap_size_signed": gap_size if direction == "up" else -gap_size,  # 有方向的幅度
            "gap_low":       gap_low,
            "gap_high":      gap_high,
            "cur_close":     cur_close,
            "cur_open":      cur_open,
            "cur_high":      cur_high,
            "cur_low":       cur_low,
            "prev_high":     prev_high,
            "prev_low":      prev_low,
            "close_chg":     close_chg,
            "volume":        cur_vol,
            "vol_ratio":     vol_ratio,
            "future_closes": future_closes,
            "future_vols":   future_vols,
        })

    return gaps


def analyze_gap_stats(gaps: list[dict], df: pd.DataFrame) -> dict:
    """統計跳空後行為"""
    highs = df['High'].values
    lows  = df['Low'].values
    n     = len(df)

    up_gaps   = [g for g in gaps if g['direction'] == 'up']
    down_gaps = [g for g in gaps if g['direction'] == 'down']

    def calc_stats(gap_list, direction):
        if not gap_list:
            return {
                'count': 0, 'avg_size': 0,
                'fill_rate': 0, 'avg_fill_bars': 0,
                'avg_after1': 0, 'avg_after3': 0, 'avg_after5': 0,
                'avg_after10': 0, 'avg_after20': 0,
                'continue_rate': 0,
            }

        fill_count     = 0
        fill_bars_list = []
        after1_list, after3_list, after5_list, after10_list, after20_list = [], [], [], [], []
        continue_count = 0

        for g in gap_list:
            i  = g['bar_idx']
            c0 = g['cur_close']
            gl = g['gap_low']
            gh = g['gap_high']

            # 後市漲跌（第N根收盤 vs 跳空當根收盤）
            fc = g['future_closes']
            if len(fc) >= 1:
                after1_list.append((fc[0]  - c0) / c0 * 100)
            if len(fc) >= 3:
                after3_list.append((fc[2]  - c0) / c0 * 100)
            if len(fc) >= 5:
                after5_list.append((fc[4]  - c0) / c0 * 100)
            if len(fc) >= 10:
                after10_list.append((fc[9]  - c0) / c0 * 100)
            if len(fc) >= 20:
                after20_list.append((fc[19] - c0) / c0 * 100)

            # 次根延續率
            if len(fc) >= 1:
                if direction == 'up'   and fc[0] > c0: continue_count += 1
                if direction == 'down' and fc[0] < c0: continue_count += 1

            # ── FIX 2 & 3：回補條件使用正確邊界 ─────────────────────────────
            # Gap Up 回補：後續某根最低點 <= gap_low（前根最高，缺口下沿）
            #   → 價格真正回到缺口區間以下，缺口才算被填補
            # Gap Down 回補：後續某根最高點 >= gap_high（前根最低，缺口下沿）
            #   → 價格真正回到缺口區間以上，缺口才算被填補
            for j in range(i+1, min(i+21, n)):
                if direction == 'up':
                    if lows[j] <= gl:          # ← FIX: gl = prev_high（缺口下沿）
                        fill_count += 1
                        fill_bars_list.append(j - i)
                        break
                else:
                    if highs[j] >= gh:         # ← FIX: gh = prev_low（缺口下沿）
                        fill_count += 1
                        fill_bars_list.append(j - i)
                        break

        cnt = len(gap_list)
        return {
            'count':          cnt,
            'avg_size':       float(np.mean([g['gap_size'] for g in gap_list])),
            'fill_rate':      fill_count / cnt * 100,
            'avg_fill_bars':  float(np.mean(fill_bars_list)) if fill_bars_list else 0,
            'avg_after1':     float(np.mean(after1_list))    if after1_list   else 0,
            'avg_after3':     float(np.mean(after3_list))    if after3_list   else 0,
            'avg_after5':     float(np.mean(after5_list))    if after5_list   else 0,
            'avg_after10':    float(np.mean(after10_list))   if after10_list  else 0,
            'avg_after20':    float(np.mean(after20_list))   if after20_list  else 0,
            'continue_rate':  continue_count / cnt * 100,
        }

    return {
        'up':        calc_stats(up_gaps,   'up'),
        'down':      calc_stats(down_gaps, 'down'),
        'total':     len(gaps),
        'up_gaps':   up_gaps,
        'down_gaps': down_gaps,
    }


def generate_gap_advice(stats: dict, current_price: float,
                        last_gap: dict | None, ticker: str) -> str:
    up   = stats['up']
    down = stats['down']

    if stats['total'] == 0:
        return f"{ticker} 在當前時間週期內未偵測到符合定義的跳空缺口，無法生成建議。"

    lines = [f"【{ticker} 跳空行為規律分析】", ""]

    if up['count'] > 0:
        fill_char = "容易回補" if up['fill_rate'] > 60 else (
                    "難以回補" if up['fill_rate'] < 35 else "回補率中等")
        up_cont_rate  = up['continue_rate']          # 次根繼續上漲的比率
        up_rev_rate   = 100 - up_cont_rate             # 次根回落的比率
        cont_char = "傾向繼續上漲" if up_cont_rate > 55 else (
                    "傾向回落"     if up_cont_rate < 45 else "方向不確定")
        cont_pct  = up_cont_rate if up_cont_rate > 55 else (
                    up_rev_rate   if up_cont_rate < 45 else up_cont_rate)
        # 樣本數警告
        sample_warn = f"⚠️ 樣本數僅{up['count']}次，參考性有限。" if up['count'] < 10 else ""
        lines.append(
            f"▸ 向上跳空（{up['count']}次）：平均缺口 {up['avg_size']:.2f}%，"
            f"20根內回補率 {up['fill_rate']:.0f}%（{fill_char}），"
            f"次根{cont_char}（{cont_pct:.0f}%）。{sample_warn}")
        lines.append(
            f"  後市：第1根 {up['avg_after1']:+.2f}% ／"
            f"第3根 {up['avg_after3']:+.2f}% ／"
            f"第5根 {up['avg_after5']:+.2f}% ／"
            f"第10根 {up['avg_after10']:+.2f}% ／"
            f"第20根 {up['avg_after20']:+.2f}%（均相對跳空當根收盤）")

    if down['count'] > 0:
        fill_char = "容易回補" if down['fill_rate'] > 60 else (
                    "難以回補" if down['fill_rate'] < 35 else "回補率中等")
        dn_cont_rate = down['continue_rate']          # 次根繼續下跌的比率
        dn_rev_rate  = 100 - dn_cont_rate              # 次根反彈的比率
        cont_char = "傾向繼續下跌" if dn_cont_rate > 55 else (
                    "傾向反彈"     if dn_cont_rate < 45 else "方向不確定")
        # 顯示對應方向的比率（傾向反彈時顯示反彈比率）
        cont_pct  = dn_cont_rate if dn_cont_rate > 55 else (
                    dn_rev_rate   if dn_cont_rate < 45 else dn_cont_rate)
        sample_warn_d = f"⚠️ 樣本數僅{down['count']}次，參考性有限。" if down['count'] < 10 else ""
        lines.append(
            f"▸ 向下跳空（{down['count']}次）：平均缺口 {down['avg_size']:.2f}%，"
            f"20根內回補率 {down['fill_rate']:.0f}%（{fill_char}），"
            f"次根{cont_char}（{cont_pct:.0f}%）。{sample_warn_d}")
        lines.append(
            f"  後市：第1根 {down['avg_after1']:+.2f}% ／"
            f"第3根 {down['avg_after3']:+.2f}% ／"
            f"第5根 {down['avg_after5']:+.2f}% ／"
            f"第10根 {down['avg_after10']:+.2f}% ／"
            f"第20根 {down['avg_after20']:+.2f}%（均相對跳空當根收盤）")

    lines.append("")

    if last_gap:
        d      = last_gap['direction']
        sz     = last_gap['gap_size']
        gl, gh = last_gap['gap_low'], last_gap['gap_high']
        ref    = stats[d]
        fill_r = ref['fill_rate']
        cont_r = ref['continue_rate']

        lines.append("【最新跳空交易建議】")

        if d == 'up':
            if cont_r > 60 and fill_r < 40:
                advice = (
                    f"🟢 強勢向上跳空，歷史 {cont_r:.0f}% 機率繼續上漲，"
                    f"回補率僅 {fill_r:.0f}%。"
                    f"建議順勢追多，以缺口上沿 ${gh:.2f} 為支撐，"
                    f"跌破缺口下沿 ${gl:.2f} 止損。")
            elif fill_r > 60:
                advice = (
                    f"⚠️ 向上跳空但歷史回補率 {fill_r:.0f}%，"
                    f"缺口 ${gl:.2f}–${gh:.2f} 大概率被回測。"
                    f"建議不追高，等回補至 ${gl:.2f}–${gh:.2f} 附近做多，"
                    f"止損缺口下沿 ${gl:.2f} 以下。")
            else:
                advice = (
                    f"🟡 向上跳空，方向不確定（延續率 {cont_r:.0f}%，回補率 {fill_r:.0f}%）。"
                    f"建議等價格在缺口上沿 ${gh:.2f} 站穩後做多，"
                    f"或等回補 ${gl:.2f} 確認支撐再入場。")
        else:
            if cont_r > 60 and fill_r < 40:
                advice = (
                    f"🔴 強勢向下跳空，歷史 {cont_r:.0f}% 機率繼續下跌，"
                    f"回補率僅 {fill_r:.0f}%。"
                    f"建議不抄底，可順勢做空，缺口下沿 ${gl:.2f} 為阻力，"
                    f"回補 ${gh:.2f} 以上止損。")
            elif fill_r > 60:
                advice = (
                    f"⚠️ 向下跳空但歷史回補率 {fill_r:.0f}%，"
                    f"缺口 ${gl:.2f}–${gh:.2f} 大概率被回測。"
                    f"建議輕倉逆勢做多（反彈至缺口下沿 ${gl:.2f}），"
                    f"跌破當根低點止損。")
            else:
                advice = (
                    f"🟡 向下跳空，方向不明確（延續率 {cont_r:.0f}%，回補率 {fill_r:.0f}%）。"
                    f"建議觀望，待缺口 ${gl:.2f}–${gh:.2f} 方向確認後再行動。")

        lines += [advice, "",
                  f"缺口關鍵位：下沿 ${gl:.2f} ／上沿 ${gh:.2f}（缺口幅度 {sz:.2f}%）"]
    else:
        lines += ["【當前無最新跳空】",
                  "基於歷史規律，當下無即時跳空機會，建議按正常 Price Action 框架操作。"]

    return "\n".join(lines)
