import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import time, hashlib

st.set_page_config(page_title="SMC Pro | Multi-Stock", page_icon="📊",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600;700&family=Noto+Sans+TC:wght@300;400;500;700&display=swap');
:root{--bg:#f5f2ed;--bg2:#edeae4;--card:#ffffff;--card2:#f9f7f4;--border:#e0dbd2;
  --border2:#ccc8be;--bull:#3d8c5f;--bull-bg:#eaf4ee;--bear:#c0392b;--bear-bg:#fdecea;
  --gold:#b07d2e;--gold-bg:#fdf6e3;--text:#1a1a1a;--text2:#6b6560;--text3:#9e9890;
  --accent:#4a7c6f;--mono:'IBM Plex Mono',monospace;--sans:'Noto Sans TC',sans-serif;}
html,body,[class*="css"]{font-family:var(--sans);background-color:var(--bg)!important;color:var(--text);}
.main{background-color:var(--bg)!important;}
.main .block-container{padding:1rem 1.5rem 2rem;max-width:100%;background:var(--bg);}
section[data-testid="stSidebar"]{background:var(--card)!important;border-right:1px solid var(--border)!important;}
section[data-testid="stSidebar"] *{color:var(--text)!important;}
.metric-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:.9rem 1.1rem .8rem;}
.metric-label{font-size:.7rem;color:var(--text2);margin-bottom:5px;}
.metric-value{font-family:var(--mono);font-size:1.7rem;font-weight:700;color:var(--text);line-height:1.1;}
.metric-sub{font-size:.73rem;margin-top:3px;}
.bull{color:var(--bull);} .bear{color:var(--bear);} .gold{color:var(--gold);}
.section-heading{font-size:.95rem;font-weight:700;color:var(--text);margin:1.3rem 0 .65rem;}
.analysis-block{background:var(--card2);border:1px solid var(--border);border-left:3px solid var(--accent);
  border-radius:0 8px 8px 0;padding:1rem 1.2rem;font-size:.86rem;line-height:1.8;}
.white-card{background:var(--card);border:1px solid var(--border);border-radius:10px;padding:.85rem 1.1rem;margin-bottom:.65rem;}
.info-row{display:flex;justify-content:space-between;align-items:center;padding:7px 0;border-bottom:1px solid var(--border);font-size:.82rem;}
.info-row:last-child{border-bottom:none;}
.info-key{color:var(--text2);}
.info-val{font-family:var(--mono);font-weight:600;color:var(--text);}
.score-wrap{margin-bottom:10px;}
.score-label-row{display:flex;justify-content:space-between;font-size:.77rem;margin-bottom:4px;color:var(--text2);}
.score-num{font-family:var(--mono);font-weight:700;}
.score-bar-bg{background:var(--bg2);border-radius:3px;height:5px;overflow:hidden;}
.score-bar-fill{height:100%;border-radius:3px;}
.rating-badge{display:inline-block;padding:6px 20px;border-radius:20px;font-family:var(--mono);font-weight:700;font-size:.87rem;}
.pattern-pill{display:inline-block;border-radius:14px;padding:3px 10px;font-size:.71rem;font-family:var(--mono);margin:2px 3px 2px 0;border:1px solid;}
.pill-bull{background:var(--bull-bg);border-color:#a8d5b8;color:var(--bull);}
.pill-bear{background:var(--bear-bg);border-color:#f5b8b3;color:var(--bear);}
.pill-neutral{background:var(--bg2);border-color:var(--border2);color:var(--text2);}
/* monitor badge */
.mon-badge{display:inline-flex;align-items:center;gap:5px;background:var(--bull-bg);
  border:1px solid #a8d5b8;border-radius:20px;padding:2px 10px;font-size:.7rem;color:var(--bull);font-family:var(--mono);}
.mon-badge-off{background:var(--bg2);border-color:var(--border2);color:var(--text3);}
/* stock tab pills */
.stTabs [data-baseweb="tab"]{font-family:var(--mono);font-size:.82rem;padding:6px 14px;}
.stButton>button{background:var(--accent)!important;color:#fff!important;font-family:var(--mono)!important;
  font-weight:600!important;border:none!important;border-radius:7px!important;}
.stButton>button:hover{opacity:.88!important;}
div[data-testid="stSelectbox"]>div>div,div[data-testid="stTextInput"]>div>div{
  background:var(--bg2)!important;border-color:var(--border)!important;border-radius:7px!important;}
hr{border-color:var(--border)!important;}
</style>
""", unsafe_allow_html=True)

# ── imports ───────────────────────────────────────────────────────────────────
from analysis.data_fetcher       import fetch_ohlcv
from analysis.pattern_detector   import detect_all_patterns
from analysis.market_structure   import analyze_market_structure
from analysis.volume_analysis    import analyze_volume
from analysis.support_resistance import find_support_resistance
from analysis.smart_money        import analyze_smart_money
from analysis.signals            import generate_signals
from analysis.scoring            import compute_scores
from analysis.backtest           import run_backtest
from analysis.ai_analysis        import generate_ai_analysis
from analysis.telegram_bot       import send_telegram_alert
from charts.candlestick_chart    import build_chart

# ── session state ─────────────────────────────────────────────────────────────
def _ss(key, val):
    if key not in st.session_state: st.session_state[key] = val

_ss("stock_list",    ["TSLA", "NVDA", "META", "AAPL"])
_ss("cached",        {})      # {ticker: result_dict}
_ss("monitors",      {})      # {ticker: {levels, triggered, active}}
_ss("alert_hashes",  set())
_ss("active_tab",    0)
_ss("gap_alerts",    {})   # {ticker: {cond_key: {enabled, last_fired}}}
_ss("gap_monitor_on", False)  # 跳空監控總開關
_ss("gap_monitor_fired",  {})  # {ticker_dir_hash: True} 去重
_ss("spike_monitor_fired",{})  # {ticker_bar_hash: True} 去重
_ss("spike_monitor_on",  False)  # 全部異常波動監控總開關
_ss("spike_x",            20)   # 參考根數 X
_ss("spike_y",            2.0)  # 觸發倍數 Y

# ── helpers ───────────────────────────────────────────────────────────────────
import re as _re

def _strip_html(html: str) -> str:
    text = _re.sub('<br/?>', chr(10), html)
    text = _re.sub('<[^>]+>', '', text)
    lines = [l for l in text.split(chr(10)) if l.strip()]
    return chr(10).join(lines).strip()

def _build_tg_signal_msg(ticker, sig, trend, overall, patterns,
                          signals, volume_analysis, market_struct,
                          scores, sr_levels, interval_lbl, current_price,
                          ai_text="") -> str:
    """生成格式完整的 Telegram 交易訊號（純 Markdown）"""
    import datetime as _dt
    nl  = chr(10)
    sep = chr(8212) * 20

    # ── 基本訊號 ──────────────────────────────────────────────────────────────
    sig_icon  = "🟢 BUY 做多" if sig == "BUY" else "🔴 SELL 做空"
    sig_emoji = "🚀" if "強烈看多" in overall else ("📈" if "偏多" in overall else
                "💀" if "強烈看空" in overall else ("📉" if "偏空" in overall else "⟷"))
    confidence = scores.get('confidence', 0)

    # ── 市場結構 ──────────────────────────────────────────────────────────────
    swing    = market_struct.get('swing_desc', '-')
    reversal = _strip_html(market_struct.get('reversal_signal', ''))

    # ── 型態 ──────────────────────────────────────────────────────────────────
    sk = patterns.get('single_k',[{}])[0].get('name','-') if patterns.get('single_k') else '-'
    dk = patterns.get('double_k',[{}])[0].get('name','-') if patterns.get('double_k') else '-'
    tk = patterns.get('triple_k',[{}])[0].get('name','-') if patterns.get('triple_k') else '-'
    macro_pats = patterns.get('macro', [])
    macro_str  = ', '.join([p['name'].split()[0] for p in macro_pats[:2]]) if macro_pats else '-'

    # ── 成交量 ────────────────────────────────────────────────────────────────
    vol_sig  = volume_analysis.get('vol_signal', '-')
    vol_r    = volume_analysis.get('vol_ratio', 1.0)
    vbias    = volume_analysis.get('vol_bias', '')
    vdiv     = volume_analysis.get('vol_divergence', '')

    # ── 交易建議 ──────────────────────────────────────────────────────────────
    trade = signals.get('trade_setup', {})
    entry = current_price
    ks    = trade.get('key_support', 0)
    kr    = trade.get('key_resistance', 0)
    bp    = trade.get('breakout_level', 0)
    sl    = trade.get('stop_loss', 0)
    rrr   = trade.get('rrr', 'N/A')
    short = trade.get('short_term', '-')
    mid   = trade.get('mid_term', '-')

    # ── 支撐阻力詳細 ──────────────────────────────────────────────────────────
    supports    = sr_levels.get('supports', [])
    resistances = sr_levels.get('resistances', [])
    sup_str = ' / '.join(['$'+str(round(s,2)) for s in supports[:3]]) if supports else '-'
    res_str = ' / '.join(['$'+str(round(r,2)) for r in resistances[:3]]) if resistances else '-'
    dz = sr_levels.get('demand_zones', [])
    sz = sr_levels.get('supply_zones', [])
    dz_str = ('$'+str(round(dz[0][0],2))+'-$'+str(round(dz[0][1],2))) if dz else '-'
    sz_str = ('$'+str(round(sz[0][0],2))+'-$'+str(round(sz[0][1],2))) if sz else '-'

    # ── 綜合結論（純文字）────────────────────────────────────────────────────
    conclusion = _strip_html(ai_text)
    # 只取綜合結論段落
    if '綜合結論' in conclusion:
        idx = conclusion.find('綜合結論')
        conclusion = conclusion[idx+4:].strip()
        conclusion = conclusion[:250]  # 最多250字
    else:
        # fallback：用評級＋原因
        reasons = signals.get('buy_reasons' if sig=='BUY' else 'sell_reasons', [])
        reason_txt = ' + '.join(reasons[:4]) if reasons else ''
        conclusion = overall + '｜' + reason_txt

    # ── 組裝訊息 ──────────────────────────────────────────────────────────────
    now = _dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    lines = [
        sig_emoji + " *" + ticker + " 交易訊號*",
        sep,
        # 基本訊號
        "訊號：*" + sig_icon + "*",
        "評級：*" + overall + "*  信心 " + str(confidence) + "%",
        "時間週期：" + interval_lbl,
        "當前價格：*$" + str(round(entry, 2)) + "*",
        "",
        # 趨勢
        "📊 *市場結構*",
        "• " + trend + "（" + swing + "）",
    ]
    if reversal:
        r_clean = reversal.replace("⚠️ ", "").replace("⚠️", "").strip()
        lines.append("• ⚠️ " + r_clean)
    lines += [
        "",
        # 型態
        "📐 *K線型態*",
        "• 單K：" + sk,
        "• 雙K：" + dk,
        "• 多K：" + tk,
        "• 型態學：" + macro_str,
        "",
        # 成交量
        "📦 *成交量*",
        "• " + vol_sig + "（" + str(round(vol_r,1)) + "x均量）",
        "• " + vbias,
    ]
    if vdiv:
        lines.append("• " + vdiv)
    lines += [
        "",
        # 支撐阻力
        "🗺 *支撐與阻力*",
        "• 關鍵支撐：" + sup_str,
        "• 關鍵阻力：" + res_str,
        "• Demand Zone：" + dz_str,
        "• Supply Zone：" + sz_str,
        "",
        # 交易建議
        "💰 *交易建議*",
        "• 入市價格：*$" + str(round(entry, 2)) + "*",
        "• 短線方向：" + short,
        "• 中線方向：" + mid,
        "• 關鍵支撐：$" + str(round(ks, 2)),
        "• 關鍵阻力：$" + str(round(kr, 2)),
        "• 突破價位：$" + str(round(bp, 2)),
        "• 止損位：  *$" + str(round(sl, 2)) + "*",
        "• 風報比：  " + str(rrr),
        "",
        # 綜合結論
        "🧠 *綜合結論*",
        conclusion,
        "",
        sep,
        "_SMC Pro · " + now + "_",
    ]
    return nl.join(lines)


def _compute_gap_conditions(df) -> list:
    """計算三個收盤價條件的當前狀態"""
    if len(df) < 2:
        return []

    c = df.iloc[-1]   # 最新一根
    p = df.iloc[-2]   # 前一根

    close_c = float(c['Close'])   # 今收
    low_c   = float(c['Low'])     # 今低
    close_p = float(p['Close'])   # 前收
    high_p  = float(p['High'])    # 前高

    # ── 條件1：收盤 vs 前收（今日漲跌幅）────────────────────────────────────
    gap1_pct  = (close_c - close_p) / close_p * 100
    gap1_up   = close_c >= close_p
    gap1_fire = abs(gap1_pct) > 0.3

    if gap1_pct > 1.5:
        gap1_status = f"強勢上漲 +{gap1_pct:.2f}%（收盤大幅高於前收）"
    elif gap1_pct > 0.3:
        gap1_status = f"跳空高收 +{gap1_pct:.2f}%（收盤高於前收）"
    elif gap1_pct < -1.5:
        gap1_status = f"大幅下跌 {gap1_pct:.2f}%（收盤大幅低於前收）"
    elif gap1_pct < -0.3:
        gap1_status = f"跳空低收 {gap1_pct:.2f}%（收盤低於前收）"
    else:
        gap1_status = f"平收 ({gap1_pct:+.2f}%)（幅度不足 0.3%）"

    # ── 條件2：收盤 vs 前高（是否突破前高收盤）──────────────────────────────
    gap2_pct  = (close_c - high_p) / high_p * 100
    gap2_up   = close_c > high_p
    gap2_fire = gap2_up  # 收盤突破前高才算觸發

    if close_c > high_p:
        gap2_status = f"強勢！收盤突破前高 +{gap2_pct:.2f}%（收 ${close_c:.2f} > 前高 ${high_p:.2f}）"
    elif gap2_pct > -0.5:
        gap2_status = f"貼近前高 {gap2_pct:.2f}%（收 ${close_c:.2f} vs 前高 ${high_p:.2f}，關鍵位置）"
    else:
        gap2_status = f"低於前高 {gap2_pct:.2f}%（收 ${close_c:.2f} 未能守住前高 ${high_p:.2f}）"

    # ── 條件3：今低 vs 前高（日內最低是否守住前高支撐）──────────────────────
    gap3_pct   = (low_c - high_p) / high_p * 100
    gap3_above = low_c > high_p
    gap3_fire  = low_c > high_p  # 今低守住前高 = 強勢訊號

    if low_c > high_p:
        gap3_status = f"極強！今低守住前高之上 +{gap3_pct:.2f}%（今低 ${low_c:.2f} > 前高 ${high_p:.2f}）"
    elif gap3_pct > -0.5:
        gap3_status = f"今低貼近前高 {gap3_pct:.2f}%（${low_c:.2f} vs ${high_p:.2f}，前高支撐測試）"
    else:
        gap3_status = f"今低跌破前高 {gap3_pct:.2f}%（今低 ${low_c:.2f} < 前高 ${high_p:.2f}，前高支撐失守 ⚠️）"

    return [
        {
            "key":    "close_vs_prev_close",
            "label":  "① 收盤 vs 前收",
            "sub":    f"今收 ${close_c:.2f}  vs  前收 ${close_p:.2f}",
            "status": gap1_status,
            "fired":  gap1_fire,
            "up":     gap1_up,
            "pct":    gap1_pct,
            "icon":   "🔼" if gap1_up else "🔽",
        },
        {
            "key":    "close_vs_prev_high",
            "label":  "② 收盤 vs 前高",
            "sub":    f"今收 ${close_c:.2f}  vs  前高 ${high_p:.2f}",
            "status": gap2_status,
            "fired":  gap2_fire,
            "up":     gap2_up,
            "pct":    gap2_pct,
            "icon":   "🚀" if gap2_up else "📉",
        },
        {
            "key":    "low_vs_prev_high",
            "label":  "③ 今低 vs 前高",
            "sub":    f"今低 ${low_c:.2f}  vs  前高 ${high_p:.2f}",
            "status": gap3_status,
            "fired":  gap3_fire,
            "up":     gap3_above,
            "pct":    gap3_pct,
            "icon":   "✅" if gap3_above else "⚠️",
        },
    ]


def _render_gap_alerts(ticker: str, df, tg_token: str, tg_chat_id: str):
    """渲染跳空警報區塊 - 三個條件 + Telegram 警報開關"""
    from analysis.telegram_bot import send_telegram_alert

    conditions = _compute_gap_conditions(df)
    if not conditions:
        st.info("數據不足，無法計算跳空條件")
        return

    has_tg = bool(tg_token and tg_chat_id)

    # 初始化該股票的 gap_alerts 狀態
    if ticker not in st.session_state.gap_alerts:
        st.session_state.gap_alerts[ticker] = {
            c['key']: {"enabled": False, "last_fired": None}
            for c in conditions
        }

    ga = st.session_state.gap_alerts[ticker]

    # ── Telegram 總開關 ──────────────────────────────────────────────────────
    col_sw1, col_sw2 = st.columns([3, 1])
    with col_sw1:
        st.markdown(
            "<div style='font-size:.78rem;color:#6b6560;padding:.3rem 0'>"
            "開啟各條件的警報開關，觸發時自動發送 Telegram</div>",
            unsafe_allow_html=True
        )
    with col_sw2:
        if not has_tg:
            st.markdown(
                "<div style='font-size:.7rem;color:#c0392b;text-align:right'>"
                "⚠️ 請先填寫<br>Telegram 設定</div>",
                unsafe_allow_html=True
            )

    # ── 三個條件卡片 ─────────────────────────────────────────────────────────
    for cond in conditions:
        key      = cond['key']
        fired    = cond['fired']
        up       = cond['up']
        pct      = cond['pct']
        icon     = cond['icon']
        enabled  = ga.get(key, {}).get('enabled', False)

        # 顏色
        if fired:
            card_bg      = "#eaf4ee" if up else "#fdecea"
            card_bdr     = "#3d8c5f" if up else "#c0392b"
            val_col      = "#3d8c5f" if up else "#c0392b"
            status_badge = f"{icon} 已觸發"
        else:
            card_bg      = "#f9f7f4"
            card_bdr     = "#e0dbd2"
            val_col      = "#6b6560"
            status_badge = "○ 監控中" if enabled else "○ 未啟動"

        c_info, c_toggle = st.columns([4, 1])
        with c_info:
            st.markdown(
                f"<div style='background:{card_bg};border:1px solid {card_bdr};"
                f"border-radius:8px;padding:.65rem 1rem;margin-bottom:.4rem'>"
                f"<div style='font-size:.72rem;color:#6b6560;margin-bottom:3px'>"
                f"{cond['label']}</div>"
                f"<div style='font-family:IBM Plex Mono,monospace;font-size:.8rem;"
                f"color:#6b6560;margin-bottom:4px'>{cond['sub']}</div>"
                f"<div style='font-family:IBM Plex Mono,monospace;font-size:.82rem;"
                f"color:{val_col};font-weight:600'>{cond['status']}</div>"
                f"<div style='font-size:.68rem;color:{val_col};margin-top:3px'>"
                f"{status_badge}</div>"
                f"</div>",
                unsafe_allow_html=True
            )
        with c_toggle:
            new_enabled = st.toggle(
                "警報",
                value=enabled,
                key=f"gap_{ticker}_{key}",
                disabled=not has_tg,
                help="需先填入 Telegram Token 和 Chat ID" if not has_tg else "開啟後觸發條件時自動發送 Telegram",
            )
            if new_enabled != enabled:
                ga[key]['enabled'] = new_enabled
                st.rerun()

        # 觸發 Telegram（條件成立 + 開關開啟 + 未重複發送）
        if fired and enabled and has_tg:
            last = ga.get(key, {}).get('last_fired')
            # 每天只發一次（同一條件同一天）
            today = __import__('datetime').date.today().isoformat()
            if last != today:
                nl  = chr(10)
                sep = chr(8212) * 16
                now_str = __import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')
                lines_tg = [
                    cond['icon'] + " *" + ticker + " 收盤價警報*",
                    sep,
                    "條件：" + cond['label'],
                    "數值：" + cond['sub'],
                    "結果：*" + cond['status'] + "*",
                    "幅度：" + f"{pct:+.2f}%",
                    sep,
                    "_SMC Pro · " + now_str + "_",
                ]
                msg = chr(10).join(lines_tg)
                if send_telegram_alert(tg_token, tg_chat_id, msg):
                    ga[key]['last_fired'] = today
                    st.toast(
                        f"{'🔼' if up else '🔽'} {ticker} 跳空警報已發送！",
                        icon="🔔"
                    )

def _cc(val):
    sv = str(val)
    if any(k in sv for k in ("多頭","突破","吸籌","放量","低位","看多","看漲","上漲","飆升","跳空上")): return "bull"
    if any(k in sv for k in ("空頭","派發","高位","跌破","出貨","看空","看跌","下跌","跳空下")): return "bear"
    return ""


def _analyze_close_prices(df) -> dict:
    """分析最新5根K線的收盤價行為"""
    import numpy as np
    closes = df['Close'].values
    opens  = df['Open'].values
    highs  = df['High'].values
    lows   = df['Low'].values
    n = len(df)
    if n < 2:
        return {k: '-' for k in ['latest_close_desc','last1_chg','last5_trend','price_smart','gap_desc']}

    c0 = closes[-1]   # 最新
    c1 = closes[-2]   # 前一根
    o0 = opens[-1]
    h0 = highs[-1]
    l0 = lows[-1]

    # ── 最新收盤描述 ─────────────────────────────────────────────────────────
    mean20 = float(np.mean(closes[-20:])) if n >= 20 else float(np.mean(closes))
    pos = "高位" if c0 > mean20 * 1.03 else ("低位" if c0 < mean20 * 0.97 else "中位")
    dir0 = "陽線收盤" if c0 >= o0 else "陰線收盤"
    latest_close_desc = f"{pos} · {dir0} · ${c0:.2f}"

    # ── 最新1根漲跌幅 ────────────────────────────────────────────────────────
    chg1 = (c0 - c1) / c1 * 100 if c1 > 0 else 0
    chg1_icon = "▲" if chg1 >= 0 else "▼"
    last1_chg = f"{chg1_icon} {abs(chg1):.2f}%（${c0:.2f} vs ${c1:.2f}）"

    # ── 近5根走勢 ────────────────────────────────────────────────────────────
    if n >= 5:
        c5 = closes[-5:]
        chg5 = (c5[-1] - c5[0]) / c5[0] * 100
        bull5 = sum(1 for i in range(1,5) if c5[i] > c5[i-1])
        bear5 = 4 - bull5
        # 趨勢強度：連續上漲/下跌
        streak = 1
        streak_dir = "上漲" if c5[-1] > c5[-2] else "下跌"
        for i in range(len(c5)-2, 0, -1):
            if (c5[i] > c5[i-1]) == (c5[-1] > c5[-2]):
                streak += 1
            else:
                break
        trend_desc = f"{'▲' if chg5>=0 else '▼'} {abs(chg5):.1f}%（{bull5}漲{bear5}跌，連續{streak}根{streak_dir}）"
        last5_trend = trend_desc
    else:
        chg5 = (c0 - closes[0]) / closes[0] * 100
        last5_trend = f"{'▲' if chg5>=0 else '▼'} {abs(chg5):.1f}%"

    # ── 收盤價主力動向判斷 ───────────────────────────────────────────────────
    # 收盤相對日內高低點的位置（越靠近日高 = 多方強）
    rng0 = h0 - l0
    close_pos = (c0 - l0) / rng0 if rng0 > 0 else 0.5
    if close_pos >= 0.80:
        price_smart = "收盤靠近日高（多方主導，主力護盤）"
    elif close_pos >= 0.60:
        price_smart = "收盤偏高（買方積極）"
    elif close_pos <= 0.20:
        price_smart = "收盤靠近日低（空方主導，主力打壓）"
    elif close_pos <= 0.40:
        price_smart = "收盤偏低（賣方積極）"
    else:
        price_smart = f"收盤居中（{close_pos*100:.0f}%位置，多空拉鋸）"

    # ── 跳空缺口偵測 ─────────────────────────────────────────────────────────
    h1 = highs[-2]
    l1 = lows[-2]

    gap_desc = "無跳空"
    gap_cls  = ""
    if l0 > h1:
        gap_size = (l0 - h1) / h1 * 100
        gap_desc = f"跳空向上 ↑ 缺口 +{gap_size:.2f}%（${h1:.2f} → ${l0:.2f}）"
    elif h0 < l1:
        gap_size = (l1 - h0) / l1 * 100
        gap_desc = f"跳空向下 ↓ 缺口 -{gap_size:.2f}%（${l1:.2f} → ${h0:.2f}）"
    elif abs(o0 - c1) / c1 * 100 > 0.5:
        # 小跳空（開盤與前收盤有差距）
        gap_pct = (o0 - c1) / c1 * 100
        if gap_pct > 0:
            gap_desc = f"小跳空高開 +{gap_pct:.2f}%（開盤 ${o0:.2f} 高於前收 ${c1:.2f}）"
        else:
            gap_desc = f"小跳空低開 {gap_pct:.2f}%（開盤 ${o0:.2f} 低於前收 ${c1:.2f}）"

    return {
        'latest_close_desc': latest_close_desc,
        'last1_chg':         last1_chg,
        'last5_trend':       last5_trend,
        'price_smart':       price_smart,
        'gap_desc':          gap_desc,
    }

def _row(k, v, cls=""):
    return (f"<div class='info-row'><span class='info-key'>{k}</span>"
            f"<span class='info-val {cls}'>{v}</span></div>")


def _bar(label, val, color):
    return (f"<div class='score-wrap'><div class='score-label-row'><span>{label}</span>"
            f"<span class='score-num' style='color:{color}'>{val}</span></div>"
            f"<div class='score-bar-bg'><div class='score-bar-fill' "
            f"style='width:{val}%;background:{color}'></div></div></div>")


def _fetch_market_env() -> dict:
    """抓取大盤環境：SPY 和 QQQ 最新數據，加入 Prompt 作為大盤背景"""
    result = {
        'spy_close': None, 'spy_chg': None, 'spy_trend': None,
        'qqq_close': None, 'qqq_chg': None, 'qqq_trend': None,
        'vix': None, 'error': None,
    }
    try:
        import yfinance as yf
        for sym, keys in [('SPY', ('spy_close','spy_chg','spy_trend')),
                           ('QQQ', ('qqq_close','qqq_chg','qqq_trend'))]:
            tk = yf.Ticker(sym)
            df_m = tk.history(period='10d', interval='1d', auto_adjust=True)
            df_m = df_m.dropna()
            df_m = df_m[df_m['Volume'] > 0]
            if len(df_m) >= 2:
                c0, c1 = float(df_m['Close'].iloc[-1]), float(df_m['Close'].iloc[-2])
                chg    = (c0 - c1) / c1 * 100
                # 簡單趨勢：5日均線 vs 10日均線
                ma5  = float(df_m['Close'].iloc[-5:].mean()) if len(df_m) >= 5  else c0
                ma10 = float(df_m['Close'].iloc[-10:].mean()) if len(df_m) >= 10 else c0
                trend = '多頭' if ma5 > ma10 else '空頭'
                result[keys[0]] = c0
                result[keys[1]] = chg
                result[keys[2]] = trend

        # VIX
        vix_tk = yf.Ticker('^VIX')
        vix_df = vix_tk.history(period='3d', interval='1d', auto_adjust=True)
        if len(vix_df) >= 1:
            result['vix'] = float(vix_df['Close'].iloc[-1])

    except Exception as e:
        result['error'] = str(e)[:60]

    return result


def _build_ai_prompt(ticker, interval_lbl, df, patterns, market_struct,
                     volume_analysis, sr_levels, smart_money, signals,
                     scores, ai_text) -> str:
    """生成完整的 AI 分析 Prompt（改進版）"""
    import datetime as _dt

    current   = float(df['Close'].iloc[-1])
    prev      = float(df['Close'].iloc[-2])
    chg_pct   = (current - prev) / prev * 100

    trend     = market_struct.get('trend', '-')
    swing     = market_struct.get('swing_desc', '-')
    t_str     = market_struct.get('trend_strength', 0)
    reversal  = _strip_html(market_struct.get('reversal_signal', ''))
    ema20_sl  = market_struct.get('ema20_slope', 0)
    ema50_sl  = market_struct.get('ema50_slope', 0)
    above_e20 = market_struct.get('above_ema20', False)
    above_e50 = market_struct.get('above_ema50', False)

    vol_sig   = volume_analysis.get('vol_signal', '-')
    vol_r     = volume_analysis.get('vol_ratio', 1.0)
    vbias     = volume_analysis.get('vol_bias', '-')
    vdiv      = volume_analysis.get('vol_divergence', '') or '無'

    behavior  = smart_money.get('behavior', '-')
    accum     = smart_money.get('accumulation_prob', 0)
    dist      = smart_money.get('distribution_risk', 0)
    lg        = smart_money.get('liquidity_grab', '無')
    sm_desc   = _strip_html(smart_money.get('description', ''))

    sig       = signals.get('primary', 'NEUTRAL')
    strength  = signals.get('strength', '-')
    buy_sc    = signals.get('buy_score', 0)
    sell_sc   = signals.get('sell_score', 0)
    buy_rsns  = signals.get('buy_reasons', [])
    sell_rsns = signals.get('sell_reasons', [])
    trade     = signals.get('trade_setup', {})
    overall   = scores.get('overall_rating', '-')
    conf      = scores.get('confidence', 0)

    # 風報比警告
    rrr_poor    = trade.get('rrr_poor', False)
    too_close   = trade.get('too_close', False)
    entry_warn  = trade.get('entry_warning', '')
    atr_val     = trade.get('atr', 0)
    reward_atr  = trade.get('reward_atr', 0)

    supports    = sr_levels.get('supports', [])
    resistances = sr_levels.get('resistances', [])
    sup_str = ' / '.join([f'${s:.2f}' for s in supports[:3]]) or '-'
    res_str = ' / '.join([f'${r:.2f}' for r in resistances[:3]]) or '-'
    dz = sr_levels.get('demand_zones', [])
    sz = sr_levels.get('supply_zones', [])
    dz_str = f'${dz[0][0]:.2f}–${dz[0][1]:.2f}' if dz else '無'
    sz_str = f'${sz[0][0]:.2f}–${sz[0][1]:.2f}' if sz else '無'

    sk = patterns.get('single_k', [{}])[0] if patterns.get('single_k') else {}
    dk = patterns.get('double_k', [{}])[0] if patterns.get('double_k') else {}
    tk = patterns.get('triple_k', [{}])[0] if patterns.get('triple_k') else {}

    # 型態學：主導優先（urgency 高的排前）
    macro_raw = patterns.get('macro', [])
    _rb = "bear" if any(p.get('bias')=='bear' for p in
          patterns.get('single_k',[]) + patterns.get('double_k',[])) else "bull"
    macro_sorted = sorted(macro_raw,
                          key=lambda p: (p.get('urgency',1), 1 if p.get('bias')==_rb else 0),
                          reverse=True)
    macro_lines = []
    for i, p in enumerate(macro_sorted):
        tag  = "【主導】" if i == 0 else "【參考】"
        desc = _strip_html(p.get('desc',''))
        macro_lines.append(f'  {tag} {p.get("name","")}：{desc}')
    macro_str = chr(10).join(macro_lines) or '  無'

    # 型態學中有多空並存時的說明
    bull_macro_ct = sum(1 for p in macro_raw if p.get('bias')=='bull')
    bear_macro_ct = sum(1 for p in macro_raw if p.get('bias')=='bear')
    conflict_note = ''
    if bull_macro_ct > 0 and bear_macro_ct > 0:
        dom = macro_sorted[0]
        conflict_note = (f'  ⚠️ 多空型態並存（多頭{bull_macro_ct}個/空頭{bear_macro_ct}個），'
                         f'主導：{dom.get("name","").split()[0]}（{dom.get("bias","")}），其餘供參考')

    sk_str = sk.get('name','無') + '：' + _strip_html(sk.get('desc','')) if sk else '無'
    dk_str = dk.get('name','無') + '：' + _strip_html(dk.get('desc','')) if dk else '無'
    tk_str = tk.get('name','無') + '：' + _strip_html(tk.get('desc','')) if tk else '無'

    ai_summary = _strip_html(ai_text)
    # 取綜合結論段落
    if '綜合結論' in ai_summary:
        ai_summary = ai_summary[ai_summary.find('綜合結論'):].strip()
    ai_summary = ai_summary[:400]

    now = _dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    nl  = chr(10)

    # 入場條件警告文字
    if entry_warn:
        warn_line = f'⚠️ 入場警告：{entry_warn}'
    elif rrr_poor:
        warn_line = f'⚠️ 風報比過低（{trade.get("rrr","N/A")}），不建議當前位置入場'
    else:
        warn_line = '✅ 入場條件合理'

    lines = [
        '你是一位專業的 Price Action 交易員兼 Smart Money Concept（SMC）分析師。',
        '請根據以下完整技術分析數據給出深度分析和具體交易建議。',
        '要求：直接給出明確方向，像職業交易員一樣做決策，並說明具體觸發條件。',
        '',
        '=' * 60,
        '【股票資訊】',
        '=' * 60,
        f'股票代號：{ticker}',
        f'時間週期：{interval_lbl}',
        f'分析時間：{now}',
        f'當前價格：${current:.2f}（較前根 {chg_pct:+.2f}%）',
        '',
        '=' * 60,
        '【大盤環境（重要背景）】',
        '=' * 60,
    ]

    # 抓大盤數據（緩存於 session state 避免重複請求）
    env_key = '_market_env_cache'
    import time as _time
    env_cache = st.session_state.get(env_key, {})
    env_stale = (_time.time() - env_cache.get('_ts', 0)) > 300   # 5分鐘過期
    if env_stale:
        env = _fetch_market_env()
        env['_ts'] = _time.time()
        st.session_state[env_key] = env
    else:
        env = env_cache

    if env.get('error'):
        lines.append(f'  （大盤數據獲取失敗：{env["error"]}，請自行評估大盤環境）')
    else:
        spy_line = (f'  SPY：${env["spy_close"]:.2f}（{env["spy_chg"]:+.2f}%），'
                    f'短期趨勢 {env["spy_trend"]}')      if env.get('spy_close') else '  SPY：數據不可用'
        qqq_line = (f'  QQQ：${env["qqq_close"]:.2f}（{env["qqq_chg"]:+.2f}%），'
                    f'短期趨勢 {env["qqq_trend"]}')      if env.get('qqq_close') else '  QQQ：數據不可用'
        vix_level = env.get('vix', 0) or 0
        vix_desc  = ('恐慌（>30，市場風險高）' if vix_level > 30
                     else '偏高（20-30，謹慎）' if vix_level > 20
                     else '正常（<20）')
        vix_line  = f'  VIX恐慌指數：{vix_level:.1f}（{vix_desc}）' if vix_level else '  VIX：數據不可用'

        lines += [spy_line, qqq_line, vix_line]

        # 大盤 vs 個股背離提示
        if env.get('spy_chg') is not None and env.get('qqq_chg') is not None:
            mkt_avg = (env['spy_chg'] + env['qqq_chg']) / 2
            diverge = chg_pct - mkt_avg
            if abs(diverge) > 2:
                dir_word = '跑贏' if diverge > 0 else '跑輸'
                lines.append(f'  ⚡ 個股 vs 大盤背離：{ticker} 今日較大盤{dir_word} {abs(diverge):.1f}%'
                              f'（{ticker} {chg_pct:+.2f}% vs 大盤均 {mkt_avg:+.2f}%）')
            else:
                lines.append(f'  ○ 個股與大盤走勢基本一致（{ticker} {chg_pct:+.2f}% vs 大盤均 {mkt_avg:+.2f}%）')

    lines += [
        '',
        '=' * 60,
        '【市場結構】',
        '=' * 60,
        f'趨勢方向：{trend}',
        f'擺動結構：{swing}',
        f'趨勢強度：{t_str}/100',
        f'EMA20 斜率：{ema20_sl:.3f}%（{"站上" if above_e20 else "跌破"} EMA20）',
        f'EMA50 斜率：{ema50_sl:.3f}%（{"站上" if above_e50 else "跌破"} EMA50）',
        f'反轉訊號：{reversal if reversal else "無"}',
        '',
        '=' * 60,
        '【K線型態（精確位置）】',
        '=' * 60,
        f'單K（最新第-1根）：{sk_str}',
        f'雙K（最新-2,-1根）：{dk_str}',
        f'三K以上（最新-5~-1根）：{tk_str}',
        '型態學（長期結構，主導優先排列）：',
    ]
    if conflict_note:
        lines.append(conflict_note)
    lines += [
        macro_str,
        '',
        '=' * 60,
        '【成交量分析（最新5根）】',
        '=' * 60,
        f'最新1根：{vol_sig}（{vol_r:.1f}x均量）',
        f'近5根偏向：{vbias}',
        f'量價背離：{vdiv}',
        '',
        '=' * 60,
        '【Smart Money 主力行為】',
        '=' * 60,
        f'主力行為：{behavior}',
        f'吸籌概率：{accum}%',
        f'派發風險：{dist}%',
        f'流動性獵殺：{lg}',
        f'SMC描述：{sm_desc}',
        '',
        '=' * 60,
        '【支撐與阻力】',
        '=' * 60,
        f'關鍵支撐（由近到遠）：{sup_str}',
        f'關鍵阻力（由近到遠）：{res_str}',
        f'需求區（Demand Zone）：{dz_str}',
        f'供應區（Supply Zone）：{sz_str}',
        '',
        '=' * 60,
        '【評分系統詳情】',
        '=' * 60,
        f'多頭得分：{buy_sc}分  空頭得分：{sell_sc}分',
        f'分差：{"多頭領先" if buy_sc > sell_sc else "空頭領先"} {abs(buy_sc - sell_sc)} 分',
        f'多頭得分來源：{", ".join(buy_rsns[:5]) if buy_rsns else "無"}',
        f'空頭得分來源：{", ".join(sell_rsns[:5]) if sell_rsns else "無"}',
        f'主要訊號：{sig}（強度：{strength}）',
        f'綜合評級：{overall}（信心：{conf}%）',
        '',
        '=' * 60,
        '【交易建議數據】',
        '=' * 60,
        f'短線方向：{trade.get("short_term", "-")}',
        f'中線方向：{trade.get("mid_term", "-")}',
        f'關鍵支撐：${trade.get("key_support", 0):.2f}',
        f'關鍵阻力：${trade.get("key_resistance", 0):.2f}',
        f'突破價位：${trade.get("breakout_level", 0):.2f}',
        f'ATR（14日）：${atr_val:.2f}',
        f'止損位：${trade.get("stop_loss", 0):.2f}（基於 ATR）',
        f'風報比：{trade.get("rrr", "N/A")}（收益空間 {reward_atr:.1f} ATR）',
        warn_line,
        '',
        '=' * 60,
        '【系統綜合結論摘要】',
        '=' * 60,
        ai_summary,
        '',
        '=' * 60,
        '【請完成以下分析（用繁體中文回答）】',
        '=' * 60,
        '1. 【最關鍵訊號】當前最重要的訊號是什麼？多空訊號中哪個更可信？為什麼？',
        '2. 【位置評估】當前 $' + f'{current:.2f} 的位置風險與機會如何？距關鍵位的距離重要嗎？',
        '3. 【做多方案】最佳做多入場觸發條件（不是「現在買」，而是「什麼情況下才買」）、止損位、目標位，以及成功率評估。',
        '4. 【做空方案】最佳做空入場觸發條件、止損位、目標位，以及成功率評估。',
        '5. 【風險因素】有哪些可能讓當前判斷完全失效的風險？（包括大盤風險、消息面風險）',
        '6. 【最終建議】明確說明：做多 / 做空 / 觀望，並給出：',
        '   - 具體觸發條件（價格突破/跌破某位才入場）',
        '   - 入場價格區間',
        '   - 止損價格',
        '   - 第一目標位、第二目標位',
        '   - 倉位建議（輕倉/半倉/全倉）',
        '',
        '⚠️ 注意：系統已偵測到以下問題，請在分析中特別處理：',
        f'   - {warn_line}',
        f'   - 多空型態並存：{conflict_note if conflict_note else "無"}',
        f'   - 信心度僅 {conf}%，意味著訊號可靠性有限',
        '',
        '請像一個真正承擔風險的職業交易員一樣給出判斷，而不是模稜兩可的「兩面都說」。',
    ]

    return nl.join(lines)

# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""<div style='padding:.6rem 0 1rem'>
      <div style='font-family:IBM Plex Mono,monospace;font-size:1.05rem;font-weight:700;
                  color:#4a7c6f;letter-spacing:.08em'>◈ SMC PRO</div>
      <div style='font-size:.62rem;color:#9e9890;letter-spacing:.15em;margin-top:3px'>
        MULTI-STOCK PLATFORM</div></div>""", unsafe_allow_html=True)

    # ── 股票池管理 ────────────────────────────────────────────────────────────
    st.markdown("**股票池**")

    # ── 批量輸入 ──────────────────────────────────────────────────────────────
    batch_input = st.text_input(
        "批量輸入（逗號分隔）",
        placeholder="TSLA, AAPL, AMZN, META, ...",
        label_visibility="visible",
        key="batch_tk_input"
    )

    if batch_input.strip():
        # 解析：支援逗號、空格、換行、中文逗號等分隔
        import re as _re
        raw_list = _re.split('[, \t\n\r\u3001\uff0c]+', batch_input.strip())
        # 清理：轉大寫、只保留字母數字點橫線（合法股票代號字符）
        parsed = [_re.sub(r'[^A-Z0-9.-]', '', t.upper().strip())
                  for t in raw_list]
        parsed = [t for t in parsed if 1 <= len(t) <= 10]  # 長度合理

        already  = [t for t in parsed if t in st.session_state.stock_list]
        to_add   = [t for t in parsed if t not in st.session_state.stock_list]
        # 去重
        seen = set(); to_add_dedup = []
        for t in to_add:
            if t not in seen:
                seen.add(t); to_add_dedup.append(t)
        to_add = to_add_dedup

        # 結果預覽
        if to_add or already:
            preview_parts = []
            if to_add:
                preview_parts.append(
                    f"<span style='color:#3d8c5f'>✅ 新加入 {len(to_add)} 個：{', '.join(to_add)}</span>")
            if already:
                preview_parts.append(
                    f"<span style='color:#9e9890'>⚠️ 已存在 {len(already)} 個：{', '.join(already)}</span>")
            st.markdown(
                "<div style='font-size:.72rem;line-height:1.7;padding:.3rem 0'>" +
                "<br>".join(preview_parts) + "</div>",
                unsafe_allow_html=True)

        if to_add:
            if st.button(f"➕ 批量加入 {len(to_add)} 支", use_container_width=True,
                         key="batch_add_btn"):
                st.session_state.stock_list.extend(to_add)
                st.rerun()
        elif parsed:
            st.caption("所有代號已在股票池中")

    # ── 單個快速加入 ──────────────────────────────────────────────────────────
    with st.expander("＋ 單個加入", expanded=False):
        new_tk = st.text_input("股票代號", placeholder="例如 GOOGL",
                               label_visibility="collapsed",
                               key="new_tk_input").upper().strip()
        import re as _re2
        new_tk = _re2.sub(r'[^A-Z0-9.\-]', '', new_tk)
        if new_tk and new_tk not in st.session_state.stock_list and 1 <= len(new_tk) <= 10:
            if st.button("➕ 加入", use_container_width=True, key="add_tk"):
                st.session_state.stock_list.append(new_tk)
                st.rerun()
        elif new_tk and new_tk in st.session_state.stock_list:
            st.caption(f"{new_tk} 已在股票池中")

    # ── 股票池列表 + 刪除 + 清空 ──────────────────────────────────────────────
    cur_pool = st.session_state.stock_list
    if cur_pool:
        st.markdown(
            f"<div style='font-size:.68rem;color:#9e9890;margin:.3rem 0 .2rem'>"
            f"股票池（{len(cur_pool)} 支）</div>",
            unsafe_allow_html=True)
        for tk in list(cur_pool):
            mon_on = st.session_state.monitors.get(tk, {}).get("active", False)
            badge  = "🔔" if mon_on else "○"
            cached = "✓" if tk in st.session_state.cached else " "
            col1, col2 = st.columns([4, 1])
            with col1:
                st.markdown(
                    f"<div style='font-family:IBM Plex Mono,monospace;font-size:.8rem;"
                    f"padding:2px 0;color:{'#3d8c5f' if mon_on else '#1a1a1a'}'>"
                    f"{badge} {tk} "
                    f"<span style='color:#9e9890;font-size:.66rem'>[{cached}]</span></div>",
                    unsafe_allow_html=True)
            with col2:
                if st.button("✕", key=f"del_{tk}", help=f"移除 {tk}"):
                    st.session_state.stock_list.remove(tk)
                    st.session_state.cached.pop(tk, None)
                    st.session_state.monitors.pop(tk, None)
                    st.rerun()

        # 清空按鈕
        if st.button("🗑️ 清空股票池", use_container_width=True, key="clear_pool"):
            st.session_state.stock_list     = []
            st.session_state.cached         = {}
            st.session_state.monitors       = {}
            st.session_state.gap_alerts     = {}
            st.session_state.gap_monitor_fired = {}
            st.rerun()

    st.markdown("---")

    # ── 全局設定 ──────────────────────────────────────────────────────────────
    st.markdown("**時間週期**")
    interval_map = {"1分鐘":"1m","5分鐘":"5m","15分鐘":"15m",
                    "30分鐘":"30m","1小時":"1h","日線":"1d","週線":"1wk"}
    interval_lbl = st.selectbox("", list(interval_map.keys()), index=5, label_visibility="collapsed")
    interval = interval_map[interval_lbl]

    st.markdown("**K線數量**")
    bar_count = st.slider("", 50, 500, 120, 10, label_visibility="collapsed")

    st.markdown("**自動刷新**")
    refresh_map = {"關閉":0,"30秒":30,"1分鐘":60,"2分鐘":120,"5分鐘":300,"15分鐘":900}
    refresh_lbl = st.selectbox("", list(refresh_map.keys()), index=0, label_visibility="collapsed")
    refresh_sec = refresh_map[refresh_lbl]

    st.markdown("---")
    st.markdown("**Telegram 通知**")

    # ── 三層 fallback：Secrets → Session → 手動輸入 ─────────────────────────
    # 層1：Streamlit Secrets
    _secret_token   = st.secrets.get("TELEGRAM_BOT_TOKEN", "") if hasattr(st, "secrets") else ""
    _secret_chat    = st.secrets.get("TELEGRAM_CHAT_ID",   "") if hasattr(st, "secrets") else ""
    _secrets_loaded = bool(_secret_token and _secret_chat)

    if _secrets_loaded:
        # Secrets 已設定 → 直接使用，顯示提示，隱藏 input
        tg_token   = _secret_token
        tg_chat_id = _secret_chat
        st.session_state["_tg_token"] = tg_token
        st.session_state["_tg_chat"]  = tg_chat_id
        st.markdown(
            "<div style='background:#eaf4ee;border:1px solid #a8d5b8;"
            "border-radius:7px;padding:.45rem .8rem;font-size:.72rem;"
            "color:#2d6a4f;margin-bottom:.4rem'>"
            "✅ 已從 Streamlit Secrets 載入<br>"
            "<span style='color:#6b9e8a;font-family:IBM Plex Mono,monospace'>"
            "TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID</span></div>",
            unsafe_allow_html=True
        )
    else:
        # 層2/3：Session state 或手動輸入
        _input_token   = st.text_input("Bot Token",  type="password",
                                        placeholder="或在 Secrets 設定",
                                        value=st.session_state.get("_tg_token",""))
        _input_chat    = st.text_input("Chat ID",    placeholder="或在 Secrets 設定",
                                        value=st.session_state.get("_tg_chat",""))
        tg_token   = _input_token   or st.session_state.get("_tg_token", "")
        tg_chat_id = _input_chat    or st.session_state.get("_tg_chat",  "")
        if _input_token:   st.session_state["_tg_token"] = _input_token
        if _input_chat:    st.session_state["_tg_chat"]  = _input_chat

        # 提示如何設定 Secrets
        with st.expander("如何用 Secrets 設定（更安全）", expanded=False):
            _secrets_help = (
                "**Streamlit Cloud 設定路徑：**"
                "  你的 App → Settings → Secrets，加入："
                "\n\n```toml"
                "\nTELEGRAM_BOT_TOKEN = \"你的 Bot Token\""
                "\nTELEGRAM_CHAT_ID   = \"你的 Chat ID\""
                "\n```"
                "\n\n本地開發：新增 `.streamlit/secrets.toml`，並將此檔加入 `.gitignore`。"
            )
            st.markdown(_secrets_help)

    # ── 跳空監控按鈕（自動刷新下方）────────────────────────────────────────
    gap_mon_on = st.session_state.gap_monitor_on
    has_tg_now = bool(st.session_state.get("_tg_token") and st.session_state.get("_tg_chat"))

    gap_btn_lbl = ("⏹ 停止跳空監控" if gap_mon_on
                   else "🚨 一鍵跳空監控" if has_tg_now
                   else "🚨 跳空監控（需填 Telegram）")
    if st.button(gap_btn_lbl, use_container_width=True, key="gap_mon_toggle",
                 disabled=(not has_tg_now and not gap_mon_on)):
        st.session_state.gap_monitor_on  = not gap_mon_on
        st.session_state.gap_monitor_fired = {}   # 切換時清空去重記錄
        st.rerun()

    # 跳空監控狀態指示
    if gap_mon_on:
        fired_cnt = len(st.session_state.gap_monitor_fired)
        st.markdown(
            f"<div style='background:#eaf4ee;border:1px solid #a8d5b8;border-radius:7px;"
            f"padding:.5rem .75rem;font-size:.72rem;color:#2d6a4f;margin-bottom:.5rem'>"
            f"🚨 跳空監控中 · {interval_lbl} · {len(st.session_state.stock_list)} 支<br>"
            f"<span style='color:#6b9e8a'>已觸發 {fired_cnt} 次提醒</span></div>",
            unsafe_allow_html=True)

    # ── 全部異常波動監控按鈕 ──────────────────────────────────────────────────
    spike_mon_on = st.session_state.spike_monitor_on
    spike_btn_lbl = ("⏹ 停止異常波動監控" if spike_mon_on
                     else "⚡ 一鍵全部異常波動監控" if has_tg_now
                     else "⚡ 異常波動監控（需填 Telegram）")
    if st.button(spike_btn_lbl, use_container_width=True, key="spike_mon_toggle",
                 disabled=(not has_tg_now and not spike_mon_on)):
        st.session_state.spike_monitor_on   = not spike_mon_on
        st.session_state.spike_monitor_fired = {}
        st.rerun()

    # 異常波動監控狀態指示
    if spike_mon_on:
        spike_fired_cnt = len(st.session_state.spike_monitor_fired)
        x_cur = st.session_state.get('spike_x', 20)
        y_cur = st.session_state.get('spike_y', 2.0)
        st.markdown(
            f"<div style='background:#fff3e0;border:1px solid #ffcc80;border-radius:7px;"
            f"padding:.5rem .75rem;font-size:.72rem;color:#b07d2e;margin-bottom:.5rem'>"
            f"⚡ 異常波動監控中 · X={x_cur} · Y={y_cur:.1f}x · {len(st.session_state.stock_list)} 支<br>"
            f"<span style='color:#c49a3c'>已觸發 {spike_fired_cnt} 次提醒</span></div>",
            unsafe_allow_html=True)

    st.markdown("---")
    # 全部分析按鈕
    analyze_all = st.button("🔍 分析全部股票", use_container_width=True, key="analyze_all")

    # 監控總覽
    active_mons = [tk for tk, m in st.session_state.monitors.items() if m.get("active")]
    if active_mons:
        st.markdown(f"**🔔 監控中 ({len(active_mons)} 支)**")
        for tk in active_mons:
            m = st.session_state.monitors[tk]
            trig = len(m.get("triggered", set()))
            st.markdown(
                f"<div style='font-size:.75rem;font-family:IBM Plex Mono,monospace;"
                f"color:#3d8c5f;padding:2px 0'>{tk} · 已觸發 {trig} 次</div>",
                unsafe_allow_html=True)

    st.markdown("""<div style='margin-top:1rem;font-size:.6rem;color:#9e9890;line-height:1.7'>
    ⚠️ 本平台僅供教育研究用途<br>不構成投資建議<br>交易有風險，請自行承擔
    </div>""", unsafe_allow_html=True)


# ── 跳空歷史分析渲染 ──────────────────────────────────────────────────────────
def _render_gap_history(df, ticker: str, interval: str):
    """渲染完整跳空歷史分析區塊"""
    from analysis.gap_analysis import scan_gaps, analyze_gap_stats, generate_gap_advice
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    # 最小缺口過濾（ATR 倍數）
    min_gap_ratio = st.slider(
        "最小缺口過濾（ATR 倍數）",
        min_value=0.0, max_value=1.0, value=0.05, step=0.05,
        key=f"gap_min_atr_{ticker}",
        help="0 = 不過濾；0.05 = 建議日線（收錄 0.3%+ 缺口）；0.1 = 只看較明顯缺口；0.2 = 只看大缺口"
    )
    # 顯示當前過濾門檻（讓用戶知道多小的缺口會被過濾）
    try:
        import numpy as _np_g
        _hg = df['High'].values; _lg = df['Low'].values; _cg = df['Close'].values
        _trg = [max(_hg[i]-_lg[i], abs(_hg[i]-_cg[i-1]), abs(_lg[i]-_cg[i-1]))
                for i in range(1, len(df))]
        _atrg = float(_np_g.mean(_trg[-14:])) if _trg else 0
        _atr_pct_g = _atrg / float(_cg[-1]) * 100 if _cg[-1] > 0 else 0
        _cur_min = _atr_pct_g * min_gap_ratio
        if min_gap_ratio > 0:
            st.caption(
                f"當前門檻：ATR {_atr_pct_g:.2f}% × {min_gap_ratio:.2f} = "
                f"缺口需 ≥ {_cur_min:.3f}% 才會顯示（缺口小於此值的會被過濾）"
            )
        else:
            st.caption("當前門檻：0（顯示所有缺口，含微小噪音）")
    except Exception:
        pass
    try:
        gaps = scan_gaps(df, min_gap_atr_ratio=min_gap_ratio)
    except TypeError:
        # 兼容舊版 gap_analysis.py（未更新 GitHub 時的 fallback）
        gaps = scan_gaps(df)
        if min_gap_ratio > 0:
            # 手動過濾：計算 ATR 再過濾
            import numpy as _np
            _h = df['High'].values; _l = df['Low'].values; _c = df['Close'].values
            _tr = [max(_h[i]-_l[i], abs(_h[i]-_c[i-1]), abs(_l[i]-_c[i-1]))
                   for i in range(1, len(df))]
            _atr = float(_np.mean(_tr[-14:])) if _tr else 0
            _min_pct = (_atr / float(_c[-1]) * 100) * min_gap_ratio if _atr > 0 else 0
            gaps = [g for g in gaps if g['gap_size'] >= _min_pct]
    stats = analyze_gap_stats(gaps, df)

    up_gaps   = stats['up_gaps']
    down_gaps = stats['down_gaps']
    total     = stats['total']

    # ── 統計摘要卡片 ──────────────────────────────────────────────────────────
    sc1, sc2, sc3, sc4 = st.columns(4)
    _up_warn  = " ⚠️" if len(up_gaps)  < 10 else ""
    _dn_warn  = " ⚠️" if len(down_gaps) < 10 else ""
    with sc1:
        st.markdown(f"""<div class='metric-card' style='text-align:center;border-left:3px solid #3d8c5f'>
          <div class='metric-label'>向上跳空次數</div>
          <div class='metric-value' style='color:#3d8c5f;font-size:1.6rem'>{len(up_gaps)}{_up_warn}</div>
          <div class='metric-sub' style='color:#9e9890'>Gap Up ↑{"　樣本數不足" if len(up_gaps) < 10 else ""}</div>
        </div>""", unsafe_allow_html=True)
    with sc2:
        st.markdown(f"""<div class='metric-card' style='text-align:center;border-left:3px solid #c0392b'>
          <div class='metric-label'>向下跳空次數</div>
          <div class='metric-value' style='color:#c0392b;font-size:1.6rem'>{len(down_gaps)}{_dn_warn}</div>
          <div class='metric-sub' style='color:#9e9890'>Gap Down ↓{"　樣本數不足" if len(down_gaps) < 10 else ""}</div>
        </div>""", unsafe_allow_html=True)
    with sc3:
        up_fill = stats['up']['fill_rate'] if stats['up']['count'] > 0 else 0
        down_fill = stats['down']['fill_rate'] if stats['down']['count'] > 0 else 0
        avg_fill = (up_fill + down_fill) / 2 if total > 0 else 0
        fill_col = "#3d8c5f" if avg_fill < 50 else "#c0392b"
        st.markdown(f"""<div class='metric-card' style='text-align:center;border-left:3px solid {fill_col}'>
          <div class='metric-label'>平均回補率</div>
          <div class='metric-value' style='color:{fill_col};font-size:1.6rem'>{avg_fill:.0f}%</div>
          <div class='metric-sub' style='color:#9e9890'>20根內</div>
        </div>""", unsafe_allow_html=True)
    with sc4:
        st.markdown(f"""<div class='metric-card' style='text-align:center;border-left:3px solid #b07d2e'>
          <div class='metric-label'>總跳空次數</div>
          <div class='metric-value' style='color:#b07d2e;font-size:1.6rem'>{total}</div>
          <div class='metric-sub' style='color:#9e9890'>{interval} 週期</div>
        </div>""", unsafe_allow_html=True)

    # 樣本數不足全局警告
    if len(up_gaps) < 10 or len(down_gaps) < 10:
        warn_parts = []
        if len(up_gaps) < 10:   warn_parts.append(f"向上跳空僅 {len(up_gaps)} 次")
        if len(down_gaps) < 10: warn_parts.append(f"向下跳空僅 {len(down_gaps)} 次")
        st.warning(
            f"⚠️ 樣本數不足（{'、'.join(warn_parts)}），統計結論可靠性有限。"
            f"建議加載更多歷史數據（增加 K線數量）或降低過濾閾值以獲得更多樣本。"
        )

    if total == 0:
        filter_note = f"（最小缺口過濾：{min_gap_ratio:.1f} ATR）" if min_gap_ratio > 0 else ""
        st.info(f"當前時間週期內未偵測到有效跳空缺口{filter_note}，可嘗試降低過濾閾值")
        return

    st.markdown("")

    # ── 後市統計表 ────────────────────────────────────────────────────────────
    st.markdown("<div class='section-heading' style='font-size:.85rem'>📊 跳空後市統計</div>",
                unsafe_allow_html=True)
    stat_cols = st.columns(2)

    for col_widget, direction, d_stats, color, icon in [
        (stat_cols[0], "向上跳空 Gap Up ↑",   stats['up'],   "#3d8c5f", "🟢"),
        (stat_cols[1], "向下跳空 Gap Down ↓", stats['down'], "#c0392b", "🔴"),
    ]:
        with col_widget:
            if d_stats['count'] == 0:
                st.markdown(f"<div class='white-card'><span style='color:#9e9890'>無{direction}記錄</span></div>",
                            unsafe_allow_html=True)
                continue
            rows = "".join([
                _row("發生次數",       str(d_stats['count'])),
                _row("平均缺口幅度",   f"{d_stats['avg_size']:.2f}%"),
                _row("20根內回補率",   f"{d_stats['fill_rate']:.0f}%"),
                _row("平均回補時間",   f"{d_stats['avg_fill_bars']:.1f} 根" if d_stats['avg_fill_bars'] > 0 else "未回補"),
                _row("次根延續率",     f"{d_stats['continue_rate']:.0f}%"),
                _row("第1根平均漲跌",  f"{d_stats['avg_after1']:+.2f}%"),
                _row("第3根平均漲跌",  f"{d_stats['avg_after3']:+.2f}%"),
                _row("第5根平均漲跌",  f"{d_stats['avg_after5']:+.2f}%"),
                _row("第10根平均漲跌", f"{d_stats['avg_after10']:+.2f}%" if d_stats.get('avg_after10') != 0 or d_stats['count'] > 0 else "數據不足"),
                _row("第20根平均漲跌", f"{d_stats['avg_after20']:+.2f}%" if d_stats.get('avg_after20') != 0 or d_stats['count'] > 0 else "數據不足"),
            ])
            st.markdown(
                f"<div class='white-card'>"
                f"<div style='font-size:.75rem;font-weight:700;color:{color};"
                f"margin-bottom:8px'>{icon} {direction}</div>{rows}</div>",
                unsafe_allow_html=True)

    # ── K線圖：標記所有跳空 ───────────────────────────────────────────────────
    st.markdown("<div class='section-heading' style='font-size:.85rem'>📈 跳空位置走勢圖</div>",
                unsafe_allow_html=True)

    dates  = df.index
    opens  = df['Open'].values
    highs  = df['High'].values
    lows   = df['Low'].values
    closes = df['Close'].values
    vols   = df['Volume'].values
    n      = len(df)

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.03, row_heights=[0.72, 0.28])

    # K線
    fig.add_trace(go.Candlestick(
        x=dates, open=opens, high=highs, low=lows, close=closes,
        name="K線",
        increasing_line_color='#3d8c5f', decreasing_line_color='#c0392b',
        increasing_fillcolor='#3d8c5f',  decreasing_fillcolor='#c0392b',
        line_width=1,
    ), row=1, col=1)

    # 標記跳空區域（矩形缺口）
    for g in gaps:
        i   = g['bar_idx']
        col = 'rgba(61,140,95,0.15)' if g['direction']=='up' else 'rgba(192,57,43,0.15)'
        bdr = 'rgba(61,140,95,0.6)'  if g['direction']=='up' else 'rgba(192,57,43,0.6)'
        fig.add_hrect(y0=g['gap_low'], y1=g['gap_high'], row=1, col=1,
                      fillcolor=col, line_width=1, line_color=bdr, opacity=0.8)

    # 跳空箭頭標記
    for g in gaps[-30:]:  # 只標最近30個避免過密
        i    = g['bar_idx']
        if i >= n: continue
        d    = g['direction']
        icon = "▲" if d == 'up' else "▼"
        ypos = lows[i]*0.994  if d=='up'  else highs[i]*1.006
        col  = '#3d8c5f'      if d=='up'  else '#c0392b'
        tpos = "bottom center" if d=='up' else "top center"
        fig.add_trace(go.Scatter(
            x=[dates[i]], y=[ypos],
            mode='markers+text',
            marker=dict(symbol='triangle-up' if d=='up' else 'triangle-down',
                        color=col, size=10),
            text=[f"{icon}{g['gap_size']:.1f}%"],
            textposition=tpos,
            textfont=dict(size=8, color=col, family='IBM Plex Mono'),
            showlegend=False,
        ), row=1, col=1)

    # 成交量
    avg_v = float(np.mean(vols[-20:])) if n >= 20 else float(np.mean(vols))
    vol_colors = []
    for i in range(n):
        is_gap_bar = any(g['bar_idx']==i for g in gaps)
        if is_gap_bar:
            g_this = next(g for g in gaps if g['bar_idx']==i)
            vol_colors.append('rgba(61,140,95,0.9)' if g_this['direction']=='up'
                              else 'rgba(192,57,43,0.9)')
        elif closes[i] >= opens[i]:
            vol_colors.append('rgba(61,140,95,0.45)')
        else:
            vol_colors.append('rgba(192,57,43,0.45)')

    fig.add_trace(go.Bar(x=dates, y=vols, name="成交量",
                         marker_color=vol_colors), row=2, col=1)
    fig.add_trace(go.Scatter(x=dates, y=[avg_v]*n, name="Vol MA20",
                             line=dict(color='#b07d2e', width=1, dash='dot'),
                             opacity=0.7), row=2, col=1)

    fig.update_layout(
        plot_bgcolor='#ffffff', paper_bgcolor='#f9f7f4',
        height=520, margin=dict(l=60, r=60, t=36, b=8),
        font=dict(family='IBM Plex Mono', color='#6b6560', size=9),
        legend=dict(bgcolor='rgba(255,255,255,.8)', bordercolor='#ede9e3',
                    borderwidth=1, font=dict(size=8), orientation='h', x=0, y=1.04),
        hovermode='x unified', xaxis_rangeslider_visible=False,
        title=dict(text=f'{ticker} 跳空缺口分佈（綠=Gap Up，紅=Gap Down）',
                   font=dict(size=12, color='#6b6560'), x=0.01),
    )
    axis_style = dict(gridcolor='#ede9e3', linecolor='#e0dbd2',
                      tickfont=dict(size=8, color='#9e9890'))
    fig.update_xaxes(**axis_style)
    fig.update_yaxes(**axis_style)
    fig.update_yaxes(tickprefix='$', row=1, col=1)

    # rangebreaks
    intraday = interval in {"1m","5m","15m","30m","1h"}
    if intraday:
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat","mon"]),
                                       dict(bounds=[16,9.5], pattern="hour")])
    else:
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat","mon"])])

    st.plotly_chart(fig, use_container_width=True,
                    config={"scrollZoom": True, "displaylogo": False})

    # ── 數據診斷（Debug）────────────────────────────────────────────────────
    with st.expander("🔍 數據診斷（最新5根K線原始數據）", expanded=False):
        _diag_df = df.tail(5)[['Open','High','Low','Close','Volume']].copy()
        _diag_df.index = _diag_df.index.strftime('%Y-%m-%d')
        _diag_df['Volume'] = (_diag_df['Volume']/1e6).round(1).astype(str) + 'M'
        for col in ['Open','High','Low','Close']:
            _diag_df[col] = _diag_df[col].round(2)
        st.dataframe(_diag_df, use_container_width=True)
        st.caption(
            f"數據來源：yfinance（auto_adjust=True）　"
            f"最新日期：{str(df.index[-1])[:10]}　"
            f"總根數：{len(df)}"
        )
        # Gap check with ATR filter diagnosis
        st.markdown("**最近3根間的跳空偵測（含ATR過濾診斷）：**")
        import numpy as _np_d
        _dh = df['High'].values; _dl = df['Low'].values
        _dc = df['Close'].values; _n_d = len(df)
        # ATR rolling
        _tr_d = [max(_dh[i]-_dl[i], abs(_dh[i]-_dc[i-1]), abs(_dl[i]-_dc[i-1]))
                 for i in range(1, _n_d)]
        _atr_d = _np_d.array([0.0] + _tr_d)
        import pandas as _pd_d
        _atr_roll = _pd_d.Series(_atr_d).rolling(14, min_periods=1).mean().values

        for _i in range(max(1, _n_d-3), _n_d):
            _ph = float(df['High'].iloc[_i-1])
            _pl = float(df['Low'].iloc[_i-1])
            _ch = float(df['High'].iloc[_i])
            _cl_v = float(df['Low'].iloc[_i])
            _cc = float(df['Close'].iloc[_i])
            _d1 = str(df.index[_i-1])[:10]
            _d2 = str(df.index[_i])[:10]
            _atr_i = float(_atr_roll[_i]) if _atr_roll[_i] > 0 else 1e-9
            _atr_pct_i = _atr_i / _cc * 100
            _min_pct_i = _atr_pct_i * min_gap_ratio

            if _ch < _pl:
                _gs = (_pl - _ch) / _pl * 100
                _pass = _gs >= _min_pct_i
                _status = "✅ 通過過濾" if _pass else f"❌ 被過濾（缺口{_gs:.3f}% < 門檻{_min_pct_i:.3f}%）"
                st.markdown(
                    f"**Gap Down** {_d1}→{_d2}: 今高{_ch:.2f} < 前低{_pl:.2f}，"
                    f"缺口{_gs:.3f}%　ATR={_atr_pct_i:.2f}%　門檻={_min_pct_i:.3f}%　{_status}"
                )
            elif _cl_v > _ph:
                _gs = (_cl_v - _ph) / _ph * 100
                _pass = _gs >= _min_pct_i
                _status = "✅ 通過過濾" if _pass else f"❌ 被過濾（缺口{_gs:.3f}% < 門檻{_min_pct_i:.3f}%）"
                st.markdown(
                    f"**Gap Up** {_d1}→{_d2}: 今低{_cl_v:.2f} > 前高{_ph:.2f}，"
                    f"缺口{_gs:.3f}%　ATR={_atr_pct_i:.2f}%　門檻={_min_pct_i:.3f}%　{_status}"
                )
            else:
                st.markdown(
                    f"○ 無跳空 {_d1}→{_d2}: "
                    f"前高{_ph:.2f} 前低{_pl:.2f} | 今高{_ch:.2f} 今低{_cl_v:.2f}"
                )

    # ── 詳細記錄表格 ──────────────────────────────────────────────────────────
    if gaps:
        st.markdown("<div class='section-heading' style='font-size:.85rem'>📋 跳空詳細記錄（最近20次）</div>",
                    unsafe_allow_html=True)

        # Sparkline helper（與異常波動表格共用相同邏輯）
        def _gap_spark(values, fmt_fn, positive_good=True):
            if not values:
                return "<span style='color:#b8b2aa'>—</span>"
            parts = []
            for v in values:
                color = ("#3d8c5f" if v >= 0 else "#c0392b") if positive_good else (
                        "#c0392b" if v >= 0 else "#3d8c5f")
                parts.append(
                    f"<span style='color:{color};font-size:.68rem;"
                    f"font-family:IBM Plex Mono,monospace'>{fmt_fn(v)}</span>"
                )
            return "<span style='color:#d0cbc5;font-size:.65rem'> │ </span>".join(parts)

        recent_gaps = sorted(gaps, key=lambda x: x['bar_idx'], reverse=True)[:20]
        table_rows = ""
        for g in recent_gaps:
            d     = g['direction']
            color = "#3d8c5f" if d=='up' else "#c0392b"
            icon  = "▲ Gap Up" if d=='up' else "▼ Gap Down"
            bg    = "#f0f9f4" if d=='up' else "#fdf0f0"
            date_str = str(g['date'])[:10]
            vol_r    = g['vol_ratio']
            vol_col  = "#3d8c5f" if vol_r > 1.5 else ("#c0392b" if vol_r < 0.7 else "#6b6560")

            # 後5根 sparkline
            fc       = g.get('future_closes', [])
            fv       = g.get('future_vols',   [])
            c0       = g['cur_close']
            v0       = g['volume'] or 1
            fc_pcts  = [(c - c0) / c0 * 100 for c in fc]
            fv_ratios= [v / v0 for v in fv]
            p_spark  = _gap_spark(fc_pcts,   lambda v: f"{v:+.1f}%", positive_good=True)
            v_spark  = _gap_spark(fv_ratios, lambda v: f"{v:.1f}x",  positive_good=True)

            table_rows += (
                f"<tr style='background:{bg}'>"
                f"<td style='padding:6px 10px;font-size:.78rem;color:#6b6560'>{date_str}</td>"
                f"<td style='padding:6px 10px;font-weight:700;color:{color}'>{icon}</td>"
                f"<td style='padding:6px 10px;font-family:IBM Plex Mono,monospace;font-size:.78rem'>"
                f"${g['cur_close']:.2f}</td>"
                f"<td style='padding:6px 10px;color:{color};font-family:IBM Plex Mono,monospace;font-size:.78rem'>"
                f"{g.get('gap_size_signed', g['gap_size'] if d=='up' else -g['gap_size']):+.2f}%</td>"
                f"<td style='padding:6px 10px;color:{('#3d8c5f' if g['close_chg']>=0 else '#c0392b')};"
                f"font-family:IBM Plex Mono,monospace;font-size:.78rem'>"
                f"{g['close_chg']:+.2f}%</td>"
                f"<td style='padding:6px 10px;font-family:IBM Plex Mono,monospace;font-size:.78rem'>"
                f"{g['volume']/1e6:.1f}M</td>"
                f"<td style='padding:6px 10px;color:{vol_col};"
                f"font-family:IBM Plex Mono,monospace;font-size:.78rem'>"
                f"{vol_r:.1f}x</td>"
                f"<td style='padding:6px 12px;min-width:220px'>{p_spark}</td>"
                f"<td style='padding:6px 12px;min-width:180px'>{v_spark}</td>"
                f"</tr>"
            )

        st.markdown(
            f"<div style='border:1px solid #e0dbd2;border-radius:8px;overflow:auto;max-height:440px'>"
            f"<table style='width:100%;border-collapse:collapse'>"
            f"<thead><tr style='background:#f9f7f4;border-bottom:1.5px solid #e0dbd2'>"
            f"<th style='padding:7px 10px;text-align:left;font-size:.72rem;color:#9e9890;font-weight:600'>時間</th>"
            f"<th style='padding:7px 10px;text-align:left;font-size:.72rem;color:#9e9890;font-weight:600'>方向</th>"
            f"<th style='padding:7px 10px;text-align:left;font-size:.72rem;color:#9e9890;font-weight:600'>收盤價</th>"
            f"<th style='padding:7px 10px;text-align:left;font-size:.72rem;color:#9e9890;font-weight:600'>缺口幅度</th>"
            f"<th style='padding:7px 10px;text-align:left;font-size:.72rem;color:#9e9890;font-weight:600'>當根漲跌</th>"
            f"<th style='padding:7px 10px;text-align:left;font-size:.72rem;color:#9e9890;font-weight:600'>成交量</th>"
            f"<th style='padding:7px 10px;text-align:left;font-size:.72rem;color:#9e9890;font-weight:600'>量比</th>"
            f"<th style='padding:7px 10px;text-align:left;font-size:.72rem;color:#4a7c6f;font-weight:600'>後5根價格</th>"
            f"<th style='padding:7px 10px;text-align:left;font-size:.72rem;color:#5b8fd4;font-weight:600'>後5根量比</th>"
            f"</tr></thead>"
            f"<tbody>{table_rows}</tbody>"
            f"</table></div>",
            unsafe_allow_html=True
        )
        st.caption("後5根價格：各根收盤相對跳空當根收盤的漲跌幅　後5根量比：各根成交量相對跳空當根成交量的倍數")

        # ── 方案A：Gap Up vs Gap Down 後市平均走勢圖 ─────────────────────────
        import plotly.graph_objects as go
        from plotly.subplots import make_subplots as _msp

        # 收集 Gap Up 和 Gap Down 各自的後5根數據
        gap_avgs = {}
        for direction, label, line_color, fill_color in [
            ('up',   'Gap Up ↑',   '#3d8c5f', 'rgba(61,140,95,0.12)'),
            ('down', 'Gap Down ↓', '#c0392b', 'rgba(192,57,43,0.12)'),
        ]:
            dir_gaps = [g for g in gaps if g['direction'] == direction]
            if not dir_gaps:
                continue
            price_by_bar = [[] for _ in range(5)]
            vol_by_bar   = [[] for _ in range(5)]
            for g in dir_gaps:
                fc = g.get('future_closes', [])
                fv = g.get('future_vols',   [])
                c0 = g['cur_close']
                v0 = g['volume'] or 1
                for j in range(min(5, len(fc))):
                    price_by_bar[j].append((fc[j] - c0) / c0 * 100)
                for j in range(min(5, len(fv))):
                    vol_by_bar[j].append(fv[j] / v0)
            import numpy as _np
            avg_p = [0.0] + [float(_np.mean(lst)) if lst else 0 for lst in price_by_bar]
            avg_v = [1.0] + [float(_np.mean(lst)) if lst else 1 for lst in vol_by_bar]
            gap_avgs[direction] = {'avg_p': avg_p, 'avg_v': avg_v,
                                   'label': label, 'p_color': line_color,
                                   'fill': fill_color, 'count': len(dir_gaps)}

        if gap_avgs:
            x_labels = ["觸發", "+1根", "+2根", "+3根", "+4根", "+5根"]
            fig_gap = _msp(rows=1, cols=2, subplot_titles=["跳空後平均價格走勢", "跳空後平均成交量變化"],
                           horizontal_spacing=0.1)

            for direction, info in gap_avgs.items():
                avg_p  = info['avg_p']
                avg_v  = info['avg_v']
                pc     = info['p_color']
                lbl    = f"{info['label']}（{info['count']}次）"
                x_p    = x_labels[:len(avg_p)]

                # 價格走勢
                fig_gap.add_trace(go.Scatter(
                    x=x_p, y=avg_p,
                    mode='lines+markers+text',
                    name=lbl,
                    line=dict(color=pc, width=2.5),
                    marker=dict(size=9, color=[("#3d8c5f" if v>=0 else "#c0392b") for v in avg_p],
                                line=dict(width=1.5, color='white')),
                    text=[f"{v:+.1f}%" for v in avg_p],
                    textposition='top center',
                    textfont=dict(size=8, color=pc, family='IBM Plex Mono'),
                ), row=1, col=1)

                # 成交量走勢
                x_v = x_labels[:len(avg_v)]
                fig_gap.add_trace(go.Scatter(
                    x=x_v, y=avg_v,
                    mode='lines+markers+text',
                    name=lbl, showlegend=False,
                    line=dict(color=pc, width=2, dash='dot'),
                    marker=dict(size=8, color=pc, line=dict(width=1.5, color='white')),
                    text=[f"{v:.1f}x" for v in avg_v],
                    textposition='bottom center',
                    textfont=dict(size=8, color=pc, family='IBM Plex Mono'),
                ), row=1, col=2)

            fig_gap.add_hline(y=0, row=1, col=1,
                              line=dict(color='#e0dbd2', width=1, dash='dash'))
            fig_gap.add_hline(y=1, row=1, col=2,
                              line=dict(color='#e0dbd2', width=1, dash='dash'))

            fig_gap.update_layout(
                plot_bgcolor='#ffffff', paper_bgcolor='#f9f7f4',
                height=300, margin=dict(l=45, r=45, t=40, b=15),
                font=dict(family='IBM Plex Mono', color='#6b6560', size=9),
                legend=dict(orientation='h', x=0.5, xanchor='center', y=1.12,
                            bgcolor='rgba(255,255,255,.85)', bordercolor='#ede9e3',
                            borderwidth=1, font=dict(size=9)),
                hovermode='x unified',
            )
            fig_gap.update_yaxes(gridcolor='#ede9e3', tickfont=dict(size=8),
                                 ticksuffix='%', row=1, col=1)
            fig_gap.update_yaxes(gridcolor='#ede9e3', tickfont=dict(size=8),
                                 ticksuffix='x', row=1, col=2)
            fig_gap.update_xaxes(tickfont=dict(size=8))

            st.markdown("<div class='section-heading' style='font-size:.85rem'>📈 跳空後平均走勢對比</div>",
                        unsafe_allow_html=True)
            st.plotly_chart(fig_gap, use_container_width=True,
                            config={"displaylogo": False, "scrollZoom": False})

    # ── 主觀交易建議 ──────────────────────────────────────────────────────────
    st.markdown("<div class='section-heading' style='font-size:.85rem'>💡 跳空交易建議</div>",
                unsafe_allow_html=True)

    # 找最近一次跳空（最新一根）
    last_gap = None
    if gaps:
        latest_idx = max(g['bar_idx'] for g in gaps)
        n_total = len(df)
        # 只有在最近5根內才算「最新跳空」
        recent = [g for g in gaps if g['bar_idx'] >= n_total - 5]
        last_gap = max(recent, key=lambda x: x['bar_idx']) if recent else None

    current_price = float(df['Close'].iloc[-1])
    advice_text = generate_gap_advice(stats, current_price, last_gap, ticker)

    advice_color = "#3d8c5f" if last_gap and last_gap['direction']=='up' else (
                   "#c0392b" if last_gap and last_gap['direction']=='down' else "#b07d2e")
    st.markdown(
        f"<div style='background:#f9f7f4;border:1px solid #e0dbd2;"
        f"border-left:3px solid {advice_color};"
        f"border-radius:0 8px 8px 0;padding:1rem 1.2rem;"
        f"font-size:.86rem;line-height:1.9;color:#1a1a1a;"
        f"white-space:pre-wrap;font-family:Noto Sans TC,sans-serif'>"
        f"{advice_text}</div>",
        unsafe_allow_html=True
    )


# ── 異常波動監控渲染 ──────────────────────────────────────────────────────────
def _render_volatility_spike(df, ticker: str, interval: str,
                             tg_token: str, tg_chat_id: str):
    """渲染異常波動監控區塊：表格、圖表、Telegram 警報"""
    from analysis.volatility_spike import (compute_volatility_spike,
                                           find_triggered_bars,
                                           build_spike_tg_msg)
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    # ── 參數輸入 ──────────────────────────────────────────────────────────────
    pc1, pc2, pc3 = st.columns([2, 2, 3])
    with pc1:
        x_val = st.number_input(
            "參考根數 X", min_value=5, max_value=100,
            value=st.session_state.spike_x, step=1,
            key=f"spike_x_{ticker}",
            help="用前X根的均值作為基準"
        )
        st.session_state.spike_x = x_val
    with pc2:
        y_val = st.number_input(
            "觸發倍數 Y", min_value=1.0, max_value=10.0,
            value=st.session_state.spike_y, step=0.5,
            format="%.1f",
            key=f"spike_y_{ticker}",
            help="兩個指標同時 ≥ Y 倍才觸發警報"
        )
        st.session_state.spike_y = y_val
    with pc3:
        has_tg = bool(tg_token and tg_chat_id)
        spike_tg_key = f"spike_tg_{ticker}"
        if spike_tg_key not in st.session_state:
            st.session_state[spike_tg_key] = False
        tg_enabled = st.toggle(
            "🔔 Telegram 警報",
            value=st.session_state[spike_tg_key],
            key=f"spike_tg_toggle_{ticker}",
            disabled=not has_tg,
            help="需先填寫 Telegram 設定"
        )
        st.session_state[spike_tg_key] = tg_enabled
        if not has_tg:
            st.caption("⚠️ 請先填寫 Telegram 設定")

    # ── 計算 ──────────────────────────────────────────────────────────────────
    result = compute_volatility_spike(df, x=int(x_val))
    if result is None:
        st.info(f"數據不足（需要至少 {int(x_val)+3} 根K線）")
        return

    from analysis.volatility_spike import get_triggered_two_bars, bar_status
    b1      = result['bar_minus1']   # 第-1根
    b2      = result['bar_minus2']   # 第-2根
    bars    = result['bars']
    n       = result['n']
    dates   = result['dates']

    # 任何一根同時觸發即為 any_triggered
    trig_two   = get_triggered_two_bars(result, y_val)
    any_triggered = len(trig_two) > 0
    triggered_hist = find_triggered_bars(result, y_val)

    # ── 四張摘要卡片（取兩根中較大的倍數顯示）────────────────────────────────
    max_p = max(b1['price_ratio'], b2['price_ratio'])
    max_v = max(b1['vol_ratio'],   b2['vol_ratio'])
    p_col = "#c0392b" if max_p >= y_val else ("#b07d2e" if max_p >= y_val*0.7 else "#3d8c5f")
    v_col = "#c0392b" if max_v >= y_val else ("#b07d2e" if max_v >= y_val*0.7 else "#3d8c5f")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""<div class='metric-card' style='text-align:center'>
          <div class='metric-label'>最大價格波動幅（2根）</div>
          <div class='metric-value' style='font-size:1.2rem;color:{p_col}'>
            {max(b1['price_abs'],b2['price_abs']):+.2f}%</div>
          <div class='metric-sub' style='color:#9e9890'>基準均值 {b1['avg_price_abs']:.2f}%</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        st.markdown(f"""<div class='metric-card' style='text-align:center'>
          <div class='metric-label'>最大價格波動倍數</div>
          <div class='metric-value' style='font-size:1.5rem;color:{p_col}'>{max_p:.2f}x</div>
          <div class='metric-sub' style='color:#9e9890'>門檻 {y_val:.1f}x</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        st.markdown(f"""<div class='metric-card' style='text-align:center'>
          <div class='metric-label'>最大成交量放量幅（2根）</div>
          <div class='metric-value' style='font-size:1.2rem;color:{v_col}'>
            {max(b1['vol_abs'],b2['vol_abs']):+.2f}%</div>
          <div class='metric-sub' style='color:#9e9890'>基準均值 {b1['avg_vol_abs']:.2f}%</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        st.markdown(f"""<div class='metric-card' style='text-align:center'>
          <div class='metric-label'>最大成交量波動倍數</div>
          <div class='metric-value' style='font-size:1.5rem;color:{v_col}'>{max_v:.2f}x</div>
          <div class='metric-sub' style='color:#9e9890'>門檻 {y_val:.1f}x</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("")

    # ── 警報橫幅 ─────────────────────────────────────────────────────────────
    if any_triggered:
        trig_labels = " ＆ ".join([b["bar_label"] for b in trig_two])
        st.markdown(
            f"<div style='background:#fdecea;border:2px solid #c0392b;border-radius:8px;"
            f"padding:.75rem 1.2rem;text-align:center;font-weight:700;color:#c0392b;"
            f"font-size:.92rem'>⚡ 異常波動警報！{trig_labels} 同時超過 {y_val:.1f}x 門檻</div>",
            unsafe_allow_html=True)
    else:
        st.markdown(
            f"<div style='background:#f9f7f4;border:1px solid #e0dbd2;border-radius:8px;"
            f"padding:.6rem 1.2rem;text-align:center;color:#9e9890;font-size:.82rem'>"
            f"○ 未觸發（-1根 價格{b1['price_ratio']:.2f}x 量{b1['vol_ratio']:.2f}x"
            f"　-2根 價格{b2['price_ratio']:.2f}x 量{b2['vol_ratio']:.2f}x）</div>",
            unsafe_allow_html=True)

    st.markdown("")

    # ── 雙根詳細表格 ─────────────────────────────────────────────────────────
    st.markdown(
        f"<div class='section-heading' style='font-size:.85rem'>"
        f"📋 最新兩根 vs 基準（前{int(x_val)}根，統一基準）</div>",
        unsafe_allow_html=True)

    def _tbl_row(bar: dict) -> str:
        status, bg = bar_status(bar, y_val)
        p_ok  = bar['price_ratio'] >= y_val
        v_ok  = bar['vol_ratio']   >= y_val
        pc    = "#c0392b" if p_ok else "#6b6560"
        vc    = "#c0392b" if v_ok else "#6b6560"
        sc    = "#c0392b" if (p_ok and v_ok) else ("#b07d2e" if (p_ok or v_ok) else "#9e9890")
        return (
            f"<tr style='background:{bg}'>"
            f"<td style='padding:8px 10px;font-size:.8rem;font-weight:600;color:#1a1a1a'>"
            f"{bar['bar_label']}</td>"
            f"<td style='padding:8px 10px;font-family:IBM Plex Mono,monospace;font-size:.78rem;color:#6b6560'>"
            f"{str(bar['date'])[:16]}</td>"
            f"<td style='padding:8px 10px;font-family:IBM Plex Mono,monospace;font-size:.78rem'>"
            f"${bar['close']:.2f}</td>"
            f"<td style='padding:8px 10px;font-family:IBM Plex Mono,monospace;font-size:.8rem;color:{pc}'>"
            f"{bar['price_abs']:+.2f}%</td>"
            f"<td style='padding:8px 10px;font-family:IBM Plex Mono,monospace;font-size:.88rem;"
            f"font-weight:700;color:{pc}'>{bar['price_ratio']:.2f}x</td>"
            f"<td style='padding:8px 10px;font-family:IBM Plex Mono,monospace;font-size:.8rem;color:{vc}'>"
            f"{bar['vol_abs']:+.2f}%</td>"
            f"<td style='padding:8px 10px;font-family:IBM Plex Mono,monospace;font-size:.88rem;"
            f"font-weight:700;color:{vc}'>{bar['vol_ratio']:.2f}x</td>"
            f"<td style='padding:8px 10px;font-size:.8rem;font-weight:700;color:{sc}'>{status}</td>"
            f"</tr>"
        )

    tbl_html = (
        f"<div style='border:1px solid #e0dbd2;border-radius:8px;overflow:hidden'>"
        f"<table style='width:100%;border-collapse:collapse'>"
        f"<thead><tr style='background:#f9f7f4;border-bottom:1.5px solid #e0dbd2'>"
        f"<th style='padding:7px 10px;text-align:left;font-size:.71rem;color:#9e9890'>K線</th>"
        f"<th style='padding:7px 10px;text-align:left;font-size:.71rem;color:#9e9890'>時間</th>"
        f"<th style='padding:7px 10px;text-align:left;font-size:.71rem;color:#9e9890'>收盤</th>"
        f"<th style='padding:7px 10px;text-align:left;font-size:.71rem;color:#9e9890'>價格漲跌幅</th>"
        f"<th style='padding:7px 10px;text-align:left;font-size:.71rem;color:#c0392b'>價格倍數</th>"
        f"<th style='padding:7px 10px;text-align:left;font-size:.71rem;color:#9e9890'>成交量放量幅</th>"
        f"<th style='padding:7px 10px;text-align:left;font-size:.71rem;color:#c0392b'>量倍數</th>"
        f"<th style='padding:7px 10px;text-align:left;font-size:.71rem;color:#9e9890'>狀態</th>"
        f"</tr></thead>"
        f"<tbody>{_tbl_row(b2)}{_tbl_row(b1)}</tbody>"
        f"</table>"
        f"<div style='padding:5px 10px;font-size:.67rem;color:#b8b2aa;border-top:1px solid #e0dbd2'>"
        f"基準：前{int(x_val)}根均值（不含最新兩根，量縮根不計）— 價格基準 {b1['avg_price_abs']:.2f}% ／ 放量基準 {b1['avg_vol_abs']:.2f}%</div>"
        f"</div>"
    )
    st.markdown(tbl_html, unsafe_allow_html=True)

    st.markdown("")

    # ── 圖表：歷史波動倍數走勢 ────────────────────────────────────────────────
    st.markdown("<div class='section-heading' style='font-size:.85rem'>📈 歷史波動倍數走勢</div>",
                unsafe_allow_html=True)

    bar_dates    = [b['date'] for b in bars]
    p_ratios_arr = [b['price_ratio']  for b in bars]
    v_ratios_arr = [b['vol_ratio']    for b in bars]

    fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                        vertical_spacing=0.06, row_heights=[0.5, 0.5],
                        subplot_titles=["價格波動倍數", "成交量波動倍數"])

    # 顏色：超標的bar顯示紅色，正常顯示藍/綠
    p_colors = ["#c0392b" if p >= y_val else "#4a7c6f" for p in p_ratios_arr]
    v_colors = ["#c0392b" if v >= y_val else "#5b8fd4" for v in v_ratios_arr]

    fig.add_trace(go.Bar(
        x=bar_dates, y=p_ratios_arr, name="價格波動倍數",
        marker_color=p_colors, opacity=0.85,
    ), row=1, col=1)

    fig.add_trace(go.Bar(
        x=bar_dates, y=v_ratios_arr, name="成交量波動倍數",
        marker_color=v_colors, opacity=0.85,
    ), row=2, col=1)

    # 觸發門檻線
    fig.add_hline(y=y_val, row=1, col=1,
                  line=dict(color='#c0392b', width=1.5, dash='dash'),
                  annotation_text=f"門檻 {y_val:.1f}x",
                  annotation_font=dict(color='#c0392b', size=9))
    fig.add_hline(y=y_val, row=2, col=1,
                  line=dict(color='#c0392b', width=1.5, dash='dash'),
                  annotation_text=f"門檻 {y_val:.1f}x",
                  annotation_font=dict(color='#c0392b', size=9))

    # 標記歷史同時觸發的時間點
    trig_dates = [b['date'] for b in triggered_hist]
    trig_p     = [b['price_ratio']  for b in triggered_hist]
    trig_v     = [b['vol_ratio']    for b in triggered_hist]
    if trig_dates:
        fig.add_trace(go.Scatter(
            x=trig_dates, y=trig_p, mode='markers',
            marker=dict(symbol='star', color='#c0392b', size=12,
                        line=dict(width=1, color='#8b1a10')),
            name='同時觸發', showlegend=True,
        ), row=1, col=1)
        fig.add_trace(go.Scatter(
            x=trig_dates, y=trig_v, mode='markers',
            marker=dict(symbol='star', color='#c0392b', size=12,
                        line=dict(width=1, color='#8b1a10')),
            name='同時觸發', showlegend=False,
        ), row=2, col=1)

    fig.update_layout(
        plot_bgcolor='#ffffff', paper_bgcolor='#f9f7f4',
        height=480, margin=dict(l=55, r=60, t=40, b=15),
        font=dict(family='IBM Plex Mono', color='#6b6560', size=9),
        legend=dict(bgcolor='rgba(255,255,255,.85)', bordercolor='#ede9e3',
                    borderwidth=1, font=dict(size=9)),
        hovermode='x unified',
        showlegend=True,
    )
    axis_style = dict(gridcolor='#ede9e3', linecolor='#e0dbd2',
                      tickfont=dict(size=8, color='#9e9890'))
    fig.update_xaxes(**axis_style)
    fig.update_yaxes(**axis_style)

    intraday = interval in {"1m","5m","15m","30m","1h"}
    if intraday:
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat","mon"]),
                                       dict(bounds=[16,9.5], pattern="hour")])
    else:
        fig.update_xaxes(rangebreaks=[dict(bounds=["sat","mon"])])

    st.plotly_chart(fig, use_container_width=True,
                    config={"scrollZoom": True, "displaylogo": False})

    # ── 歷史觸發詳細表格 ─────────────────────────────────────────────────────
    if triggered_hist:
        st.markdown(
            f"<div class='section-heading' style='font-size:.85rem'>"
            f"⚡ 歷史同時觸發記錄（共 {len(triggered_hist)} 次，門檻 {y_val:.1f}x）</div>",
            unsafe_allow_html=True)

        # ── 統計摘要（Fix：第4卡改為最大成交量倍數）────────────────────────
        avg_p = sum(b['price_ratio']  for b in triggered_hist) / len(triggered_hist)
        avg_v = sum(b['vol_ratio']    for b in triggered_hist) / len(triggered_hist)
        max_p = max(b['price_ratio']  for b in triggered_hist)
        max_v = max(b['vol_ratio']    for b in triggered_hist)  # Fix: was max_p shown as 4th

        sc1, sc2, sc3, sc4 = st.columns(4)
        for col, label, val, suffix in [
            (sc1, "觸發次數",     len(triggered_hist), "次"),
            (sc2, "均價格倍數",   avg_p,               "x"),
            (sc3, "均成交量倍數", avg_v,               "x"),
            (sc4, "最大成交量倍數", max_v,             "x"),  # Fix: max_v not max_p
        ]:
            with col:
                st.markdown(
                    f"<div class='metric-card' style='text-align:center'>"
                    f"<div class='metric-label'>{label}</div>"
                    f"<div class='metric-value' style='color:#c0392b;font-size:1.4rem'>"
                    f"{val:.2f}{suffix}</div></div>" if isinstance(val, float)
                    else
                    f"<div class='metric-card' style='text-align:center'>"
                    f"<div class='metric-label'>{label}</div>"
                    f"<div class='metric-value' style='color:#c0392b;font-size:1.4rem'>"
                    f"{val}{suffix}</div></div>",
                    unsafe_allow_html=True)

        st.markdown("")

        # ── 詳細表格（Fix1：漲跌幅加方向；Fix3：日期截到10位）────────────────
        def _spark_cells(values, fmt_fn, positive_good=True):
            """生成後5根的彩色文字序列 HTML"""
            if not values:
                return "<span style='color:#b8b2aa'>—</span>"
            parts = []
            for v in values:
                color = ("#3d8c5f" if v >= 0 else "#c0392b") if positive_good else (
                        "#c0392b" if v >= 0 else "#3d8c5f")
                parts.append(
                    f"<span style='color:{color};font-size:.68rem;"
                    f"font-family:IBM Plex Mono,monospace'>{fmt_fn(v)}</span>"
                )
            return "<span style='color:#d0cbc5;font-size:.65rem'> │ </span>".join(parts)

        trig_rows = ""
        for b in reversed(triggered_hist):
            date_str  = str(b['date'])[:10]
            p_r       = b['price_ratio']
            v_r       = b['vol_ratio']
            p_abs     = b['price_abs']
            v_abs     = b['vol_abs']
            close_v   = b['close']
            close_chg = b.get('price_chg', 0)
            is_up     = close_chg >= 0
            chg_color   = "#3d8c5f" if is_up else "#c0392b"
            chg_display = f"+{p_abs:.2f}%" if is_up else f"-{p_abs:.2f}%"

            # 後5根走勢（方案B）
            fc = b.get('future_closes', [])
            fv = b.get('future_vols',   [])
            # 價格：相對觸發當根收盤的漲跌幅
            fc_pcts = [(c - close_v) / close_v * 100 for c in fc] if fc else []
            # 成交量：相對觸發當根成交量的倍數
            base_vol = b.get('vol', 1) or 1
            fv_ratios = [v / base_vol for v in fv] if fv else []

            price_spark = _spark_cells(fc_pcts,   lambda v: f"{v:+.1f}%", positive_good=True)
            vol_spark   = _spark_cells(fv_ratios, lambda v: f"{v:.1f}x",  positive_good=True)

            # 強度評級
            both_max = max(p_r, v_r)
            if both_max >= y_val * 3:
                grade, gbg = "🔴 極強", "#fdecea"
            elif both_max >= y_val * 2:
                grade, gbg = "🟠 強",   "#fff3e0"
            else:
                grade, gbg = "🟡 中",   "#fffde7"

            trig_rows += (
                f"<tr style='background:{gbg}'>"
                f"<td style='padding:6px 10px;font-size:.78rem;color:#6b6560'>{date_str}</td>"
                f"<td style='padding:6px 10px;font-family:IBM Plex Mono,monospace;font-size:.78rem'>${close_v:.2f}</td>"
                f"<td style='padding:6px 10px;font-family:IBM Plex Mono,monospace;font-size:.78rem;color:{chg_color}'>{chg_display}</td>"
                f"<td style='padding:6px 10px;font-family:IBM Plex Mono,monospace;font-size:.82rem;font-weight:700;color:#c0392b'>{p_r:.2f}x</td>"
                f"<td style='padding:6px 10px;font-family:IBM Plex Mono,monospace;font-size:.78rem'>+{v_abs:.2f}%</td>"
                f"<td style='padding:6px 10px;font-family:IBM Plex Mono,monospace;font-size:.82rem;font-weight:700;color:#c0392b'>{v_r:.2f}x</td>"
                f"<td style='padding:6px 10px;font-size:.76rem'>{grade}</td>"
                f"<td style='padding:6px 12px;min-width:200px'>{price_spark}</td>"
                f"<td style='padding:6px 12px;min-width:200px'>{vol_spark}</td>"
                f"</tr>"
            )

        st.markdown(
            f"<div style='border:1px solid #e0dbd2;border-radius:8px;overflow:auto;max-height:420px'>"
            f"<table style='width:100%;border-collapse:collapse'>"
            f"<thead><tr style='background:#fdecea;border-bottom:1.5px solid #f5b8b3;position:sticky;top:0'>"
            f"<th style='padding:7px 10px;text-align:left;font-size:.71rem;color:#9e9890'>時間</th>"
            f"<th style='padding:7px 10px;text-align:left;font-size:.71rem;color:#9e9890'>收盤價</th>"
            f"<th style='padding:7px 10px;text-align:left;font-size:.71rem;color:#9e9890'>漲跌幅</th>"
            f"<th style='padding:7px 10px;text-align:left;font-size:.71rem;color:#c0392b'>價格倍數</th>"
            f"<th style='padding:7px 10px;text-align:left;font-size:.71rem;color:#9e9890'>量增幅</th>"
            f"<th style='padding:7px 10px;text-align:left;font-size:.71rem;color:#c0392b'>量倍數</th>"
            f"<th style='padding:7px 10px;text-align:left;font-size:.71rem;color:#9e9890'>強度</th>"
            f"<th style='padding:7px 10px;text-align:left;font-size:.71rem;color:#4a7c6f'>後5根價格</th>"
            f"<th style='padding:7px 10px;text-align:left;font-size:.71rem;color:#5b8fd4'>後5根量比</th>"
            f"</tr></thead>"
            f"<tbody>{trig_rows}</tbody>"
            f"</table></div>",
            unsafe_allow_html=True
        )
        st.caption("後5根價格：各根收盤相對觸發當根收盤的漲跌幅　後5根量比：各根成交量相對觸發當根成交量的倍數")

        # ── 方案A：平均後市走勢圖 ────────────────────────────────────────────
        import plotly.graph_objects as go

        # 收集所有觸發事件的後5根數據
        all_price_pcts  = [[], [], [], [], []]   # [根1列表, 根2列表, ...]
        all_vol_ratios  = [[], [], [], [], []]

        for b in triggered_hist:
            fc     = b.get('future_closes', [])
            fv     = b.get('future_vols',   [])
            c0     = b['close']
            v0     = b.get('vol', 1) or 1
            for j in range(min(5, len(fc))):
                all_price_pcts[j].append((fc[j] - c0) / c0 * 100)
            for j in range(min(5, len(fv))):
                all_vol_ratios[j].append(fv[j] / v0)

        avg_price = [float(np.mean(lst)) if lst else None for lst in all_price_pcts]
        avg_vol   = [float(np.mean(lst)) if lst else None for lst in all_vol_ratios]
        x_labels  = ["觸發", "+1根", "+2根", "+3根", "+4根", "+5根"]

        # 加入觸發點（0,0）
        avg_price_plot = [0.0] + [v for v in avg_price if v is not None]
        avg_vol_plot   = [1.0] + [v for v in avg_vol   if v is not None]
        x_plot = x_labels[:len(avg_price_plot)]

        fig_after = go.Figure()

        # 價格走勢（左軸）
        price_colors = ["#3d8c5f" if v >= 0 else "#c0392b" for v in avg_price_plot]
        fig_after.add_trace(go.Scatter(
            x=x_plot, y=avg_price_plot,
            mode='lines+markers+text',
            name='平均價格漲跌',
            line=dict(color='#4a7c6f', width=2.5),
            marker=dict(size=10, color=price_colors,
                        line=dict(width=1.5, color='white')),
            text=[f"{v:+.2f}%" for v in avg_price_plot],
            textposition='top center',
            textfont=dict(size=9, color='#4a7c6f', family='IBM Plex Mono'),
            yaxis='y1',
        ))

        # 成交量走勢（右軸）
        fig_after.add_trace(go.Scatter(
            x=x_plot, y=avg_vol_plot,
            mode='lines+markers+text',
            name='平均量比',
            line=dict(color='#5b8fd4', width=2, dash='dot'),
            marker=dict(size=8, color='#5b8fd4',
                        line=dict(width=1.5, color='white')),
            text=[f"{v:.2f}x" for v in avg_vol_plot],
            textposition='bottom center',
            textfont=dict(size=9, color='#5b8fd4', family='IBM Plex Mono'),
            yaxis='y2',
        ))

        # 零線
        fig_after.add_hline(y=0, line=dict(color='#e0dbd2', width=1, dash='dash'), yref='y1')
        fig_after.add_hline(y=1, line=dict(color='#bbd4f0', width=1, dash='dash'), yref='y2')

        fig_after.update_layout(
            title=dict(
                text=f"觸發後平均走勢（共 {len(triggered_hist)} 次樣本）",
                font=dict(size=12, color='#6b6560'), x=0.01
            ),
            plot_bgcolor='#ffffff', paper_bgcolor='#f9f7f4',
            height=300,
            margin=dict(l=55, r=55, t=42, b=30),
            font=dict(family='IBM Plex Mono', color='#6b6560', size=9),
            legend=dict(orientation='h', x=0.5, xanchor='center', y=1.12,
                        bgcolor='rgba(255,255,255,.8)', bordercolor='#ede9e3',
                        borderwidth=1, font=dict(size=9)),
            yaxis=dict(title='價格漲跌幅 (%)', gridcolor='#ede9e3',
                       tickfont=dict(size=8), ticksuffix='%',
                       zeroline=True, zerolinecolor='#e0dbd2'),
            yaxis2=dict(title='成交量倍數 (x)', overlaying='y', side='right',
                        gridcolor='#dceaf8', tickfont=dict(size=8),
                        ticksuffix='x', showgrid=False),
            hovermode='x unified',
        )

        st.markdown("<div class='section-heading' style='font-size:.85rem'>📊 觸發後平均走勢（方案A）</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(fig_after, use_container_width=True,
                        config={"displaylogo": False, "scrollZoom": False})

        # ── 歷史推測 ──────────────────────────────────────────────────────────
        st.markdown("<div class='section-heading' style='font-size:.85rem'>🔮 基於歷史數據的後市推測</div>",
                    unsafe_allow_html=True)

        # 分析最新觸發事件
        latest = triggered_hist[-1] if triggered_hist else None
        if latest and avg_price_plot and len(avg_price_plot) >= 4:
            lat_close  = latest['close']
            lat_chg    = latest.get('price_chg', 0)
            lat_chg_pct= lat_chg / (lat_close - lat_chg) * 100 if (lat_close - lat_chg) > 0 else 0
            lat_p_r    = latest['price_ratio']
            lat_v_r    = latest['vol_ratio']
            lat_date   = str(latest['date'])[:10]

            # 找最相似的歷史事件（同方向 + 跌幅最接近）
            is_latest_down = lat_chg < 0
            similar = [b for b in triggered_hist[:-1]
                       if (b.get('price_chg', 0) < 0) == is_latest_down]
            # 按漲跌幅絕對值差排序
            lat_abs = abs(lat_chg_pct)
            similar.sort(key=lambda b: abs(
                abs(b.get('price_chg',0) / max(b['close']-b.get('price_chg',0), 1) * 100) - lat_abs
            ))
            top3 = similar[:3]

            # 平均後市走勢統計
            p1 = avg_price_plot[1] if len(avg_price_plot) > 1 else 0
            p3 = avg_price_plot[3] if len(avg_price_plot) > 3 else 0
            p5 = avg_price_plot[5] if len(avg_price_plot) > 5 else (avg_price_plot[-1] if avg_price_plot else 0)

            # 判斷後市傾向
            n_positive_5 = sum(1 for b in triggered_hist[:-1]
                               if len(b.get('future_closes',[])) >= 5
                               and b['future_closes'][4] > b['close'])
            n_total_5    = sum(1 for b in triggered_hist[:-1]
                               if len(b.get('future_closes',[])) >= 5)
            up_rate_5    = n_positive_5 / n_total_5 * 100 if n_total_5 > 0 else 50

            # 生成推測文字
            direction_5  = "上漲" if p5 > 0 else "下跌"
            d_color_5    = "#3d8c5f" if p5 > 0 else "#c0392b"
            conf_level   = (
                "較高（>65%）" if up_rate_5 > 65 or up_rate_5 < 35
                else "中等（45-65%）" if 45 <= up_rate_5 <= 65
                else "偏低（<45%）"
            )

            # 相似事件文字
            similar_html = ""
            for b in top3:
                b_date = str(b['date'])[:10]
                b_chg_pct = b.get('price_chg', 0) / max(b['close']-b.get('price_chg',0),1) * 100
                fc = b.get('future_closes', [])
                b_p5 = (fc[4] - b['close']) / b['close'] * 100 if len(fc) >= 5 else None
                b_p5_str = f"+{b_p5:.1f}%" if b_p5 and b_p5 >= 0 else (f"{b_p5:.1f}%" if b_p5 else "—")
                b_p5_col = "#3d8c5f" if b_p5 and b_p5 >= 0 else "#c0392b"
                similar_html += (
                    f"<div style='display:flex;justify-content:space-between;"
                    f"padding:4px 0;border-bottom:1px solid #f0ede8;font-size:.78rem'>"
                    f"<span style='color:#9e9890'>{b_date}</span>"
                    f"<span style='color:{'#c0392b' if b_chg_pct < 0 else '#3d8c5f'};"
                    f"font-family:IBM Plex Mono,monospace'>{b_chg_pct:+.1f}%</span>"
                    f"<span style='color:#9e9890'>→ 5根後</span>"
                    f"<span style='color:{b_p5_col};font-family:IBM Plex Mono,monospace'>{b_p5_str}</span>"
                    f"</div>"
                )

            # 目標價位（預先計算所有變數，避免 f-string 內三元表達式衝突）
            target_1   = lat_close * (1 + p1/100)
            target_3   = lat_close * (1 + p3/100)
            target_5   = lat_close * (1 + p5/100)
            n_warn     = f"（樣本數 {n_total_5} 次，{'統計意義有限' if n_total_5 < 10 else '具參考價值'}）" if n_total_5 > 0 else ""
            chg_col    = "#c0392b" if lat_chg < 0 else "#3d8c5f"
            p1_col     = "#3d8c5f" if p1 >= 0 else "#c0392b"
            p3_col     = "#3d8c5f" if p3 >= 0 else "#c0392b"
            up_col     = "#3d8c5f" if up_rate_5 > 50 else "#c0392b"
            conc_bg    = "#eaf4ee" if p5 >= 0 else "#fdecea"
            conc_col   = "#2d6a4f" if p5 >= 0 else "#922b21"

            similar_sec = ""
            if similar_html:
                similar_sec = (
                    "<div style='margin-bottom:.8rem'>"
                    "<div style='font-size:.72rem;color:#9e9890;margin-bottom:.4rem'>"
                    "🔍 最相似歷史事件（同方向、漲跌幅最接近）</div>"
                    + similar_html + "</div>"
                )

            st.markdown(
                "<div style='background:#f9f7f4;border:1px solid #e0dbd2;"
                "border-radius:8px;padding:1.1rem 1.3rem;font-family:Noto Sans TC,sans-serif'>"

                # 最新觸發摘要
                f"<div style='font-size:.8rem;color:#6b6560;margin-bottom:.8rem'>"
                f"最新觸發：<b style='color:#1a1a1a'>{lat_date}</b>　"
                f"收盤 <b>${lat_close:.2f}</b>　"
                f"漲跌 <b style='color:{chg_col}'>{lat_chg_pct:+.1f}%</b>　"
                f"價格倍數 <b style='color:#c0392b'>{lat_p_r:.2f}x</b>　"
                f"量倍數 <b style='color:#c0392b'>{lat_v_r:.2f}x</b></div>"

                # 均值推測卡
                f"<div style='background:#fff;border:1px solid #e8e3dc;border-radius:6px;"
                f"padding:.7rem 1rem;margin-bottom:.8rem'>"
                f"<div style='font-size:.72rem;color:#9e9890;margin-bottom:.5rem'>📊 歷史均值推測 {n_warn}</div>"
                f"<div style='display:flex;gap:1.5rem;flex-wrap:wrap'>"
                f"<div style='text-align:center'>"
                f"<div style='font-size:.68rem;color:#9e9890'>第1根均值</div>"
                f"<div style='font-size:1.1rem;font-weight:700;color:{p1_col};"
                f"font-family:IBM Plex Mono,monospace'>{p1:+.2f}%</div>"
                f"<div style='font-size:.68rem;color:#9e9890'>${target_1:.2f}</div></div>"
                f"<div style='text-align:center'>"
                f"<div style='font-size:.68rem;color:#9e9890'>第3根均值</div>"
                f"<div style='font-size:1.1rem;font-weight:700;color:{p3_col};"
                f"font-family:IBM Plex Mono,monospace'>{p3:+.2f}%</div>"
                f"<div style='font-size:.68rem;color:#9e9890'>${target_3:.2f}</div></div>"
                f"<div style='text-align:center'>"
                f"<div style='font-size:.68rem;color:#9e9890'>第5根均值</div>"
                f"<div style='font-size:1.1rem;font-weight:700;color:{d_color_5};"
                f"font-family:IBM Plex Mono,monospace'>{p5:+.2f}%</div>"
                f"<div style='font-size:.68rem;color:#9e9890'>${target_5:.2f}</div></div>"
                f"<div style='text-align:center'>"
                f"<div style='font-size:.68rem;color:#9e9890'>5根後上漲概率</div>"
                f"<div style='font-size:1.1rem;font-weight:700;color:{up_col}'>{up_rate_5:.0f}%</div>"
                f"<div style='font-size:.68rem;color:#9e9890'>信心：{conf_level}</div></div>"
                f"</div></div>"

                + similar_sec

                # 推測結論
                + f"<div style='background:{conc_bg};border-radius:6px;padding:.6rem .9rem;"
                f"font-size:.82rem;color:{conc_col};border-left:3px solid {d_color_5}'>"
                f"<b>📌 推測結論：</b>"
                f"基於 {n_total_5} 次歷史同類事件，觸發後第5根收盤平均"
                f"<b>{direction_5} {abs(p5):.2f}%</b>"
                f"，目標價約 <b>${target_5:.2f}</b>。"
                f"5根後上漲概率 <b>{up_rate_5:.0f}%</b>（{conf_level}）。"
                "<br><span style='font-size:.73rem;opacity:.8'>"
                "⚠️ 歷史統計僅供參考，不構成交易建議。</span></div>"
                "</div>",
                unsafe_allow_html=True
            )

    # ── Telegram 警報（任何一根觸發即發）────────────────────────────────────
    if tg_enabled and trig_two:
        from analysis.volatility_spike import build_spike_tg_msg
        from analysis.telegram_bot    import send_telegram_alert
        for trig_bar in trig_two:
            spike_key = f"{ticker}_{trig_bar['bar_label']}_{str(trig_bar['date'])[:16]}"
            if spike_key in st.session_state.spike_monitor_fired:
                continue
            st.session_state.spike_monitor_fired[spike_key] = True
            msg = build_spike_tg_msg(ticker, interval, result, y_val, trig_bar)
            if send_telegram_alert(tg_token, tg_chat_id, msg):
                st.toast(
                    f"⚡ {ticker} {trig_bar['bar_label']} 異常波動！"
                    f"價格 {trig_bar['price_ratio']:.2f}x ＆ 量 {trig_bar['vol_ratio']:.2f}x",
                    icon="⚡")


# ── 跳空監控核心 ──────────────────────────────────────────────────────────────
def _detect_gaps_two_bars(ticker: str, interval: str, bar_count: int) -> list[dict]:
    """
    監控最新兩根 K 線，任何一根出現跳空即記錄。
    檢查：
      pair A : bar[-1] vs bar[-2]  （最新根）
      pair B : bar[-2] vs bar[-3]  （前一根）
    回傳 list，可能含 0~2 個跳空事件。
    """
    try:
        import yfinance as yf
        from analysis.data_fetcher import INTERVAL_PERIOD_MAP, _filter_trading_hours
        from analysis.gap_analysis import scan_gaps, analyze_gap_stats

        period = INTERVAL_PERIOD_MAP.get(interval, "1d")
        df = yf.Ticker(ticker).history(period=period, interval=interval, auto_adjust=True)
        if df is None or len(df) < 3:
            return []
        df = df.dropna()
        if interval in {"1m","5m","15m","30m","1h"}:
            df = _filter_trading_hours(df, interval)
        df = df[df["Volume"] > 0]
        if len(df) < 3:
            return []

        # 計算歷史統計（供 Telegram 附上回補率）
        try:
            all_gaps = scan_gaps(df, min_gap_atr_ratio=0.3)
            stats    = analyze_gap_stats(all_gaps, df)
        except Exception:
            stats = None

        found = []
        # 檢查最近兩對 K 線
        for offset in [1, 2]:      # offset=1 → bar[-1]/bar[-2]; offset=2 → bar[-2]/bar[-3]
            if len(df) < offset + 2:
                continue
            cur  = df.iloc[-(offset)]
            prev = df.iloc[-(offset+1)]

            cur_high  = float(cur['High'])
            cur_low   = float(cur['Low'])
            cur_close = float(cur['Close'])
            cur_open  = float(cur['Open'])
            cur_vol   = float(cur['Volume'])
            prev_high = float(prev['High'])
            prev_low  = float(prev['Low'])
            cur_time  = str(df.index[-offset])[:16]

            # 均量
            avg_v = float(df['Volume'].rolling(20).mean().iloc[-(offset)]) or 1.0
            vol_ratio = cur_vol / avg_v if avg_v > 0 else 1.0

            bar_label = "最新根（-1）" if offset == 1 else "前一根（-2）"

            if cur_low > prev_high:
                pct = (cur_low - prev_high) / prev_high * 100
                gap_low, gap_high = prev_high, cur_low
                direction = "up"

                # 歷史統計
                hist_txt = ""
                if stats and stats['up']['count'] > 0:
                    u = stats['up']
                    hist_txt = (f"歷史統計（{u['count']}次）："
                                f"回補率 {u['fill_rate']:.0f}%"
                                f"（平均 {u['avg_fill_bars']:.1f} 根）"
                                f"｜次根均 {u['avg_after1']:+.2f}%"
                                f"／5根後均 {u['avg_after5']:+.2f}%"
                                f"／10根後均 {u['avg_after10']:+.2f}%"
                                f"／20根後均 {u['avg_after20']:+.2f}%")

                found.append({
                    "ticker":    ticker,
                    "direction": direction,
                    "bar_label": bar_label,
                    "icon":      "🟢",
                    "label":     "向上跳空 Gap Up ↑",
                    "gap_low":   gap_low,
                    "gap_high":  gap_high,
                    "detail":    f"低 ${cur_low:.2f} > 前高 ${prev_high:.2f}",
                    "pct":       pct,
                    "cur_close": cur_close,
                    "cur_open":  cur_open,
                    "vol_ratio": vol_ratio,
                    "cur_time":  cur_time,
                    "hist_txt":  hist_txt,
                    "dedup_key": f"{ticker}_up_{cur_time}",
                })

            elif cur_high < prev_low:
                pct = (prev_low - cur_high) / prev_low * 100
                gap_low, gap_high = cur_high, prev_low
                direction = "down"

                hist_txt = ""
                if stats and stats['down']['count'] > 0:
                    d = stats['down']
                    hist_txt = (f"歷史統計（{d['count']}次）："
                                f"回補率 {d['fill_rate']:.0f}%"
                                f"（平均 {d['avg_fill_bars']:.1f} 根）"
                                f"｜次根均 {d['avg_after1']:+.2f}%"
                                f"／5根後均 {d['avg_after5']:+.2f}%"
                                f"／10根後均 {d['avg_after10']:+.2f}%"
                                f"／20根後均 {d['avg_after20']:+.2f}%")

                found.append({
                    "ticker":    ticker,
                    "direction": direction,
                    "bar_label": bar_label,
                    "icon":      "🔴",
                    "label":     "向下跳空 Gap Down ↓",
                    "gap_low":   gap_low,
                    "gap_high":  gap_high,
                    "detail":    f"高 ${cur_high:.2f} < 前低 ${prev_low:.2f}",
                    "pct":       pct,
                    "cur_close": cur_close,
                    "cur_open":  cur_open,
                    "vol_ratio": vol_ratio,
                    "cur_time":  cur_time,
                    "hist_txt":  hist_txt,
                    "dedup_key": f"{ticker}_down_{cur_time}",
                })

        return found

    except Exception:
        return []


def _run_gap_monitor(stock_list: list, interval: str, bar_count: int):
    """
    遍歷所有股票，監控最新兩根 K 線跳空。
    bar[-1] vs bar[-2]，bar[-2] vs bar[-3] 各自獨立檢查。
    附帶歷史回補率統計，讓用戶收到 Telegram 即知操作方向。
    """
    if not st.session_state.gap_monitor_on:
        return

    tg_t = st.session_state.get("_tg_token", "")
    tg_c = st.session_state.get("_tg_chat", "")
    if not tg_t or not tg_c:
        return

    from analysis.telegram_bot import send_telegram_alert
    import datetime as _dt

    for ticker in stock_list:
        gaps = _detect_gaps_two_bars(ticker, interval, bar_count)
        if not gaps:
            continue

        for gap in gaps:
            dedup_key = gap['dedup_key']
            if dedup_key in st.session_state.gap_monitor_fired:
                continue

            # 記錄已觸發
            st.session_state.gap_monitor_fired[dedup_key] = True

            # ── 組裝 Telegram 訊息 ─────────────────────────────────────────
            nl  = chr(10)
            sep = chr(8212) * 22
            now = _dt.datetime.now().strftime('%Y-%m-%d %H:%M')

            # 缺口區間
            gap_range = f"${gap['gap_low']:.2f} – ${gap['gap_high']:.2f}"

            # 操作建議（根據歷史統計自動生成）
            hist = gap.get('hist_txt', '')
            if gap['direction'] == 'up':
                if '回補率' in hist:
                    # 從 hist_txt 提取回補率數字
                    import re
                    m = re.search('回補率 ([0-9]+)%', hist)
                    fill_r = int(m.group(1)) if m else 50
                    if fill_r >= 60:
                        op_hint = f"⚠️ 歷史回補率高（{fill_r}%），建議等回補至缺口 {gap_range} 再做多"
                    else:
                        op_hint = f"🚀 歷史回補率低（{fill_r}%），可考慮順勢追多，止損缺口下沿 ${gap['gap_low']:.2f}"
                else:
                    op_hint = f"缺口區間 {gap_range}，等待價格在上沿 ${gap['gap_high']:.2f} 站穩確認"
            else:
                if '回補率' in hist:
                    import re
                    m = re.search('回補率 ([0-9]+)%', hist)
                    fill_r = int(m.group(1)) if m else 50
                    if fill_r >= 60:
                        op_hint = f"⚠️ 歷史回補率高（{fill_r}%），可輕倉逆勢做多，目標回補缺口下沿 ${gap['gap_low']:.2f}"
                    else:
                        op_hint = f"🔻 歷史回補率低（{fill_r}%），建議順勢做空，止損缺口上沿 ${gap['gap_high']:.2f}"
                else:
                    op_hint = f"缺口區間 {gap_range}，等待確認方向後再入場"

            lines = [
                gap['icon'] + " *" + ticker + " 跳空警報*",
                sep,
                "觸發根：" + gap['bar_label'],
                "方向：*" + gap['label'] + "*",
                "缺口區間：" + gap_range,
                "缺口幅度：+" + f"{gap['pct']:.2f}%",
                "當根收盤：$" + f"{gap['cur_close']:.2f}",
                "成交量比：" + f"{gap['vol_ratio']:.1f}x 均量",
                "時間：" + gap['cur_time'],
                "週期：" + interval,
            ]
            if hist:
                lines += ["", "📊 " + hist]
            lines += [
                "",
                "💡 " + op_hint,
                sep,
                "_SMC Pro · " + now + "_",
            ]
            msg = nl.join(lines)
            send_telegram_alert(tg_t, tg_c, msg)

            # 頁面 Toast
            st.toast(
                f"{gap['icon']} {ticker} {gap['bar_label']} {gap['label']} "
                f"+{gap['pct']:.2f}%",
                icon="🚨"
            )


# ── 計算單支股票 ───────────────────────────────────────────────────────────────
def compute_ticker(ticker: str) -> dict | None:
    df = fetch_ohlcv(ticker, interval, bar_count)
    if df is None or len(df) < 20:
        return None
    patterns        = detect_all_patterns(df)
    market_struct   = analyze_market_structure(df)
    volume_analysis = analyze_volume(df)
    sr_levels       = find_support_resistance(df)
    smart_money     = analyze_smart_money(df, volume_analysis)
    signals         = generate_signals(df, patterns, market_struct, volume_analysis, sr_levels)
    scores          = compute_scores(market_struct, volume_analysis, smart_money, signals)
    ai_text         = generate_ai_analysis(ticker, df, patterns, market_struct,
                                           volume_analysis, sr_levels, smart_money, signals, scores)
    import time as _t
    return dict(ticker=ticker, interval=interval, interval_lbl=interval_lbl,
                df=df, patterns=patterns, market_struct=market_struct,
                volume_analysis=volume_analysis, sr_levels=sr_levels,
                smart_money=smart_money, signals=signals, scores=scores,
                ai_text=ai_text, tg_token=tg_token, tg_chat_id=tg_chat_id,
                timestamp=datetime.now().strftime('%Y-%m-%d %H:%M'),
                fetch_ts=_t.time(),                          # Unix 時間戳供新鮮度檢查
                df_latest=str(df.index[-1])[:10])            # 最新K線日期


# ── 渲染單支股票分析 ───────────────────────────────────────────────────────────
def render_ticker(ctx: dict):
    ticker          = ctx["ticker"]
    interval_label  = ctx["interval_lbl"]
    df              = ctx["df"]
    patterns        = ctx["patterns"]
    market_struct   = ctx["market_struct"]
    volume_analysis = ctx["volume_analysis"]
    sr_levels       = ctx["sr_levels"]
    smart_money     = ctx["smart_money"]
    signals         = ctx["signals"]
    scores          = ctx["scores"]
    ai_text         = ctx["ai_text"]
    # 優先用 session state 的最新值（可能已由 Secrets 更新）
    tg_token   = st.session_state.get("_tg_token") or ctx.get("tg_token", "")
    tg_chat_id = st.session_state.get("_tg_chat")  or ctx.get("tg_chat_id", "")

    latest    = df.iloc[-1];  prev = df.iloc[-2]
    price_chg = latest['Close'] - prev['Close']
    price_pct = price_chg / prev['Close'] * 100
    vol_avg   = df['Volume'].rolling(20).mean().iloc[-1]
    vol_ratio = latest['Volume'] / vol_avg if vol_avg > 0 else 1.0
    trend     = market_struct.get('trend','橫盤整理')
    sig       = signals.get('primary','NEUTRAL')
    overall   = scores.get('overall_rating','中性 ⟷')

    chg_cls  = "bull" if price_chg >= 0 else "bear"
    chg_icon = "▲" if price_chg >= 0 else "▼"
    sig_icon = "🟢" if sig=="BUY" else ("🔴" if sig=="SELL" else "🟡")
    r_col    = "#3d8c5f" if "看多" in overall else ("#c0392b" if "看空" in overall else "#b07d2e")
    mon_on   = st.session_state.monitors.get(ticker, {}).get("active", False)

    # header
    ts = ctx['timestamp']
    df_latest  = ctx.get('df_latest', str(df.index[-1])[:10])
    mon_badge_html = '<span class="mon-badge">🔔 監控中</span>' if mon_on else ''

    # 數據新鮮度提示
    from datetime import datetime as _dt2
    try:
        _today     = _dt2.utcnow().strftime('%Y-%m-%d')
        _df_date   = df_latest
        _days_old  = (_dt2.strptime(_today,'%Y-%m-%d') - _dt2.strptime(_df_date,'%Y-%m-%d')).days
        # 扣除週末（粗略）
        _trading_days_old = max(0, _days_old - (_days_old // 7) * 2)
        if _trading_days_old >= 3:
            _fresh_badge = (f"<span style='background:#fdecea;color:#c0392b;border-radius:4px;"
                           f"padding:1px 7px;font-size:.66rem;margin-left:8px'>"
                           f"⚠️ 數據最新至 {_df_date}（{_trading_days_old}個交易日前），請重新分析</span>")
        elif _trading_days_old >= 1:
            _fresh_badge = (f"<span style='background:#fff3e0;color:#b07d2e;border-radius:4px;"
                           f"padding:1px 7px;font-size:.66rem;margin-left:8px'>"
                           f"最新K線：{_df_date}</span>")
        else:
            _fresh_badge = (f"<span style='background:#eaf4ee;color:#3d8c5f;border-radius:4px;"
                           f"padding:1px 7px;font-size:.66rem;margin-left:8px'>"
                           f"✓ 最新</span>")
    except Exception:
        _fresh_badge = f"<span style='font-size:.66rem;color:#9e9890;margin-left:8px'>最新K線：{df_latest}</span>"

    st.markdown(
        f"<div style='display:flex;align-items:baseline;gap:10px;padding:.3rem 0 .8rem;flex-wrap:wrap'>"
        f"<span style='font-family:IBM Plex Mono,monospace;font-size:1.6rem;font-weight:700'>{ticker}</span>"
        f"<span style='font-size:.7rem;color:#9e9890;margin-left:8px'>{interval_label} · SMC + Price Action</span>"
        f"{mon_badge_html}"
        f"{_fresh_badge}"
        f"<span style='margin-left:auto;font-size:.66rem;color:#b8b2aa;font-family:IBM Plex Mono,monospace'>{ts}</span>"
        f"</div>",
        unsafe_allow_html=True
    )

    # metric cards
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1:
        st.markdown(f"""<div class='metric-card'>
          <div class='metric-label'>最新收盤</div>
          <div class='metric-value'>${latest['Close']:.2f}</div>
          <div class='metric-sub {chg_cls}'>{chg_icon} {abs(price_chg):.2f} ({abs(price_pct):.2f}%)</div>
        </div>""", unsafe_allow_html=True)
    with c2:
        tc = "bull" if "多頭" in trend else ("bear" if "空頭" in trend else "gold")
        st.markdown(f"""<div class='metric-card'>
          <div class='metric-label'>趨勢結構</div>
          <div class='metric-value {tc}' style='font-size:1.05rem;padding-top:5px'>{trend}</div>
          <div class='metric-sub' style='color:#9e9890'>{market_struct.get('swing_desc','')}</div>
        </div>""", unsafe_allow_html=True)
    with c3:
        vc = "bull" if vol_ratio>1.5 else ("bear" if vol_ratio<0.5 else "gold")
        st.markdown(f"""<div class='metric-card'>
          <div class='metric-label'>成交量比率</div>
          <div class='metric-value {vc}'>{vol_ratio:.1f}x</div>
          <div class='metric-sub' style='color:#9e9890'>{volume_analysis.get('vol_signal','')}</div>
        </div>""", unsafe_allow_html=True)
    with c4:
        sc2 = "bull" if sig=="BUY" else ("bear" if sig=="SELL" else "gold")
        st.markdown(f"""<div class='metric-card'>
          <div class='metric-label'>主要訊號</div>
          <div class='metric-value {sc2}' style='font-size:1.35rem;padding-top:4px'>{sig_icon} {sig}</div>
          <div class='metric-sub' style='color:#9e9890'>{signals.get('strength','')}</div>
        </div>""", unsafe_allow_html=True)
    with c5:
        st.markdown(f"""<div class='metric-card'>
          <div class='metric-label'>綜合評級</div>
          <div class='metric-value' style='font-size:.95rem;color:{r_col};padding-top:7px'>{overall}</div>
          <div class='metric-sub' style='color:#9e9890'>信心 {scores.get('confidence',0)}%</div>
        </div>""", unsafe_allow_html=True)

    # chart
    st.markdown("<div class='section-heading'>📈 K線圖表 · 市場結構 · 訊號</div>", unsafe_allow_html=True)
    fig = build_chart(df, ticker, interval, sr_levels, signals, market_struct, patterns)
    st.plotly_chart(fig, use_container_width=True, config={"scrollZoom":True,"displaylogo":False})

    col_l, col_r = st.columns([3, 2])
    with col_l:
        st.markdown("<div class='section-heading'>🧠 AI 綜合分析</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='analysis-block'>{ai_text}</div>", unsafe_allow_html=True)

        # ── AI Prompt 生成按鈕 ───────────────────────────────────────────────
        st.markdown("""<div style='font-size:.7rem;color:#9e9890;margin:.6rem 0 .4rem;
            letter-spacing:.05em'>📋 生成 Prompt · 複製後貼入任意 AI 進行深度分析</div>""",
            unsafe_allow_html=True)
        _prompt_key = f"ai_prompt_{ticker}"
        if _prompt_key not in st.session_state:
            st.session_state[_prompt_key] = ""
        pb1, pb2, pb3, pb4 = st.columns(4)
        _ai_labels = [
            ("pb1", pb1, "📋 Claude"),
            ("pb2", pb2, "📋 ChatGPT"),
            ("pb3", pb3, "📋 Gemini"),
            ("pb4", pb4, "📋 Grok"),
        ]
        for _key, _col, _lbl in _ai_labels:
            with _col:
                if st.button(_lbl, use_container_width=True, key=f"prompt_{_key}_{ticker}"):
                    st.session_state[_prompt_key] = _build_ai_prompt(
                        ticker, interval_label, df, patterns, market_struct,
                        volume_analysis, sr_levels, smart_money, signals,
                        scores, ai_text
                    )
        if st.session_state[_prompt_key]:
            st.text_area(
                "📋 已生成 Prompt（全選複製後貼入 AI）",
                value=st.session_state[_prompt_key],
                height=220,
                key=f"prompt_area_{ticker}",
            )
            st.caption("💡 點擊文字框 → Ctrl+A 全選 → Ctrl+C 複製")

        st.markdown("<div class='section-heading'>📐 市場結構</div>", unsafe_allow_html=True)
        st.markdown(f"""<div class='white-card'>
          {_row("趨勢方向",  trend,                                       _cc(trend))}
          {_row("擺動結構",  market_struct.get('swing_desc','-'),         _cc(market_struct.get('swing_desc','')))}
          {_row("趨勢強度",  f"{market_struct.get('trend_strength',0)}/100")}
          {_row("市場狀態",  market_struct.get('market_state','-'))}
          {_row("結構突破",  market_struct.get('structure_break','-'),    _cc(market_struct.get('structure_break','')))}
        </div>""", unsafe_allow_html=True)

        st.markdown("<div class='section-heading'>💰 Smart Money 主力行為</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='analysis-block' style='border-left-color:#b07d2e'>{smart_money.get('description','')}</div>", unsafe_allow_html=True)
        st.markdown(f"""<div class='white-card'>
          {_row("主力行為",   smart_money.get('behavior','-'),            _cc(smart_money.get('behavior','')))}
          {_row("吸籌概率",   f"{smart_money.get('accumulation_prob',0)}%")}
          {_row("派發風險",   f"{smart_money.get('distribution_risk',0)}%")}
          {_row("流動性獵殺", smart_money.get('liquidity_grab','-'))}
          {_row("假突破風險", smart_money.get('fakeout_risk','-'))}
        </div>""", unsafe_allow_html=True)

    with col_r:
        # scores
        st.markdown("<div class='section-heading'>📊 評分系統</div>", unsafe_allow_html=True)
        r_bg = "#eaf4ee" if "看多" in overall else ("#fdecea" if "看空" in overall else "#fdf6e3")

        # ── 評級理由 ──────────────────────────────────────────────────────────
        buy_rsns_sc  = signals.get('buy_reasons',  [])
        sell_rsns_sc = signals.get('sell_reasons', [])
        conf_sc      = scores.get('confidence', 0)
        dist_sc      = scores.get('distribution_score', 0)
        fake_sc      = scores.get('fakeout_score', 0)
        buy_sc_val   = signals.get('buy_score',  0)
        sell_sc_val  = signals.get('sell_score', 0)

        # 看多理由（正面因素）
        bull_items = []
        for r in buy_rsns_sc[:6]:
            bull_items.append(
                f"<div style='display:flex;align-items:center;gap:6px;padding:3px 0'>"
                f"<span style='color:#3d8c5f;font-size:.9rem'>✓</span>"
                f"<span style='font-size:.78rem;color:#2d6a4f'>{r}</span></div>"
            )
        # 看空理由（風險因素）
        bear_items = []
        for r in sell_rsns_sc[:6]:
            bear_items.append(
                f"<div style='display:flex;align-items:center;gap:6px;padding:3px 0'>"
                f"<span style='color:#c0392b;font-size:.9rem'>✗</span>"
                f"<span style='font-size:.78rem;color:#922b21'>{r}</span></div>"
            )
        # 額外風險提示
        risk_notes = []
        if dist_sc >= 50:
            risk_notes.append(f"主力出貨風險 {dist_sc}% — 疑似主力派發，謹慎追多")
        if fake_sc >= 50:
            risk_notes.append(f"假突破風險 {fake_sc}% — 突破後可能快速回落")
        if conf_sc <= 45:
            risk_notes.append(f"信心度僅 {conf_sc}% — 訊號可靠性有限，建議輕倉")

        # 組裝理由 HTML
        reasons_html = ""
        if bull_items or bear_items or risk_notes:
            bull_col_html = (
                f"<div style='flex:1;min-width:180px'>"
                f"<div style='font-size:.72rem;font-weight:700;color:#3d8c5f;"
                f"margin-bottom:4px;padding-bottom:4px;border-bottom:1px solid #c8e6c9'>"
                f"✅ 看多理由（多頭得分 {buy_sc_val}）</div>"
                + ("".join(bull_items) if bull_items else
                   "<div style='font-size:.76rem;color:#9e9890'>無明顯看多訊號</div>")
                + "</div>"
            ) if bull_items or not bear_items else ""

            bear_col_html = (
                f"<div style='flex:1;min-width:180px'>"
                f"<div style='font-size:.72rem;font-weight:700;color:#c0392b;"
                f"margin-bottom:4px;padding-bottom:4px;border-bottom:1px solid #ffcdd2'>"
                f"⚠️ 風險因素（空頭得分 {sell_sc_val}）</div>"
                + ("".join(bear_items) if bear_items else
                   "<div style='font-size:.76rem;color:#9e9890'>無明顯看空訊號</div>")
                + "</div>"
            ) if bear_items else ""

            risk_html = ""
            if risk_notes:
                risk_items = "".join([
                    f"<div style='font-size:.75rem;color:#b07d2e;padding:2px 0'>"
                    f"⚡ {n}</div>" for n in risk_notes
                ])
                risk_html = (
                    f"<div style='margin-top:.6rem;padding-top:.6rem;"
                    f"border-top:1px solid #ede9e3'>"
                    f"<div style='font-size:.72rem;font-weight:700;color:#b07d2e;"
                    f"margin-bottom:4px'>⚡ 需要警惕</div>"
                    + risk_items + "</div>"
                )

            reasons_html = (
                f"<div style='margin-top:.8rem;padding-top:.8rem;"
                f"border-top:1px solid #ede9e3'>"
                f"<div style='display:flex;gap:1.2rem;flex-wrap:wrap'>"
                + bull_col_html + bear_col_html
                + "</div>"
                + risk_html
                + "</div>"
            )

        sh = (_bar("趨勢強度",     scores.get('trend_strength',0),     "#4a7c6f") +
              _bar("主力吸籌概率", scores.get('accumulation_score',0), "#3d8c5f") +
              _bar("主力出貨風險", scores.get('distribution_score',0), "#c0392b") +
              _bar("突破成功率",   scores.get('breakout_score',0),     "#b07d2e") +
              _bar("假突破風險",   scores.get('fakeout_score',0),      "#c0706a") +
              f"<div style='text-align:center;margin-top:1rem'>"
              f"<div class='rating-badge' style='background:{r_bg};border:1.5px solid {r_col};color:{r_col}'>"
              f"{overall}</div></div>"
              + reasons_html)
        st.markdown(f"<div class='white-card'>{sh}</div>", unsafe_allow_html=True)

        # trade setup + monitor button
        st.markdown("<div class='section-heading'>📋 交易建議</div>", unsafe_allow_html=True)
        trade = signals.get('trade_setup', {})
        _ks = trade.get('key_support',0)
        _kr = trade.get('key_resistance',0)
        _bp = trade.get('breakout_level',0)
        _sl = trade.get('stop_loss',0)
        _rrr_str     = trade.get('rrr', '-')
        _rrr_poor    = trade.get('rrr_poor', False)
        _too_close   = trade.get('too_close', False)
        _entry_warn  = trade.get('entry_warning', '')
        _atr_val     = trade.get('atr', 0)
        _reward_atr  = trade.get('reward_atr', 0)
        _any_warn    = _rrr_poor or _too_close or bool(_entry_warn)

        if _entry_warn:
            _warn_html = (
                "<div style='background:#fdecea;border-radius:6px;padding:8px 12px;"
                "font-size:.78rem;color:#c0392b;margin-top:8px;line-height:1.7'>"
                "⚠️ <b>入場警告</b><br>" + _entry_warn + "</div>"
            )
        elif _rrr_poor:
            _warn_html = (
                "<div style='background:#fdecea;border-radius:6px;padding:8px 12px;"
                "font-size:.78rem;color:#c0392b;margin-top:8px'>"
                "⚠️ 風報比過低（" + _rrr_str + "），當前位置不建議入場，"
                "等待更好的入場點。</div>"
            )
        else:
            _warn_html = ""

        _atr_note = (
            "<div style='font-size:.68rem;color:#9e9890;padding:4px 0 2px'>"
            "止損基於 ATR（" + f"{_atr_val:.2f}" + "）計算"
            + (f"　收益空間 {_reward_atr:.1f} ATR" if _reward_atr > 0 else "")
            + "</div>"
        ) if _atr_val > 0 else ""

        st.markdown(
            "<div class='white-card'>"
            + _row("短線方向", trade.get("short_term","-"), _cc(trade.get("short_term","")))
            + _row("中線方向", trade.get("mid_term","-"),   _cc(trade.get("mid_term","")))
            + _row("關鍵支撐", f"${_ks:.2f}")
            + _row("關鍵阻力", f"${_kr:.2f}")
            + _row("突破價位", f"${_bp:.2f}")
            + _row("止損位",   f"${_sl:.2f}（ATR）", "bear")
            + _row("風報比",   _rrr_str, "bear" if _any_warn else "")
            + _atr_note + _warn_html + "</div>",
            unsafe_allow_html=True
        )

        # ── 監控按鈕（該股票獨立）────────────────────────────────────────────
        mon = st.session_state.monitors.get(ticker, {})
        mon_active = mon.get("active", False)
        has_tg = bool(st.session_state.get("_tg_token") and st.session_state.get("_tg_chat"))

        if mon_active:
            trig_ct = len(mon.get("triggered", set()))
            st.markdown(f"""<div style='background:#eaf4ee;border:1.5px solid #3d8c5f;
                border-radius:8px;padding:.65rem 1rem;margin-bottom:.5rem;font-size:.78rem'>
              <span style='color:#3d8c5f;font-weight:700'>🔔 監控中</span>
              <span style='color:#6b6560;margin-left:8px;font-family:IBM Plex Mono,monospace;font-size:.72rem'>
                支撐${_ks:.2f} / 阻力${_kr:.2f} / 突破${_bp:.2f} / 止損${_sl:.2f}</span>
              <span style='float:right;color:#9e9890;font-size:.68rem'>已觸發 {trig_ct} 次</span>
            </div>""", unsafe_allow_html=True)
            if st.button(f"⏹ 停止監控 {ticker}", use_container_width=True, key=f"stop_{ticker}"):
                st.session_state.monitors.pop(ticker, None)
                st.rerun()
        else:
            btn_lbl = f"🔔 一鍵監控 {ticker}" if has_tg else f"🔔 監控 {ticker}（請先填 Telegram）"
            if st.button(btn_lbl, use_container_width=True,
                         key=f"start_{ticker}", disabled=not has_tg):
                st.session_state.monitors[ticker] = {
                    "active": True,
                    "triggered": set(),
                    "levels": {
                        "關鍵支撐": {"price":_ks, "direction":"below", "icon":"🟢"},
                        "關鍵阻力": {"price":_kr, "direction":"above", "icon":"🔴"},
                        "突破價位": {"price":_bp, "direction":"above", "icon":"🚀"},
                        "止損位":   {"price":_sl, "direction":"below", "icon":"🛑"},
                    }
                }
                st.rerun()

        # patterns
        st.markdown("<div class='section-heading'>🕯️ K線型態</div>", unsafe_allow_html=True)
        all_pats = (patterns.get('single_k',[]) + patterns.get('double_k',[]) +
                    patterns.get('triple_k',[]) + patterns.get('macro',[]))
        pills = ""
        for p in all_pats:
            cls = "pill-bull" if p['bias']=='bull' else ("pill-bear" if p['bias']=='bear' else "pill-neutral")
            pills += f"<span class='pattern-pill {cls}'>{p['name']}</span>"
        if not pills:
            pills = "<span style='color:#9e9890;font-size:.78rem'>未偵測到明顯型態</span>"
        st.markdown(f"<div class='white-card' style='line-height:2.2'>{pills}</div>", unsafe_allow_html=True)

        # volume
        st.markdown("<div class='section-heading'>📦 成交量（最新5根）</div>", unsafe_allow_html=True)
        r5    = volume_analysis.get('recent5_ratio',1.0)
        vbias = volume_analysis.get('vol_bias','')
        vdiv  = volume_analysis.get('vol_divergence','') or '無'
        st.markdown(f"""<div class='white-card'>
          {_row("最新1根訊號", volume_analysis.get('vol_signal','-'),  _cc(volume_analysis.get('vol_signal','')))}
          {_row("最新1根量比", f"{vol_ratio:.1f}x 均量")}
          {_row("近5根量比",   f"{r5:.1f}x · {vbias}",
                "bull" if "多頭" in vbias else ("bear" if "空頭" in vbias else ""))}
          {_row("主力動向",   volume_analysis.get('smart_vol','-'),   _cc(volume_analysis.get('smart_vol','')))}
          {_row("量價背離",   vdiv)}
        </div>""", unsafe_allow_html=True)

        # ── 收盤價分析（最新5根）─────────────────────────────────────────────
        st.markdown("<div class='section-heading'>💹 收盤價分析（最新5根）</div>", unsafe_allow_html=True)
        price_analysis = _analyze_close_prices(df)
        pa = price_analysis
        st.markdown(f"""<div class='white-card'>
          {_row("最新收盤",    pa['latest_close_desc'],             _cc(pa['latest_close_desc']))}
          {_row("最新1根漲跌", pa['last1_chg'],                     _cc(pa['last1_chg']))}
          {_row("近5根走勢",   pa['last5_trend'],                   _cc(pa['last5_trend']))}
          {_row("主力動向",    pa['price_smart'],                   _cc(pa['price_smart']))}
          {_row("跳空缺口",    pa['gap_desc'],                      _cc(pa['gap_desc']))}
        </div>""", unsafe_allow_html=True)

        # ── 跳空警報區塊 ──────────────────────────────────────────────────────
        st.markdown("<div class='section-heading'>🚨 跳空警報</div>", unsafe_allow_html=True)
        _render_gap_alerts(ticker, df, tg_token, tg_chat_id)

    # backtest
    st.markdown("<div class='section-heading'>📉 回測系統</div>", unsafe_allow_html=True)
    bt = run_backtest(df, signals.get('signal_history',[]))
    bc = st.columns(5)
    for col,(lbl,val,good) in zip(bc,[
        ("勝率",     f"{bt.get('win_rate',0):.1f}%",    bt.get('win_rate',0)>50),
        ("盈虧比",   f"{bt.get('profit_factor',0):.2f}", bt.get('profit_factor',0)>1.5),
        ("最大回撤", f"{bt.get('max_dd',0):.1f}%",       bt.get('max_dd',0)<15),
        ("交易次數", str(bt.get('total_trades',0)),       True),
        ("淨收益率", f"{bt.get('net_return',0):.1f}%",   bt.get('net_return',0)>0),
    ]):
        color = "#3d8c5f" if good else "#c0392b"
        with col:
            st.markdown(f"""<div class='metric-card' style='text-align:center'>
              <div class='metric-label'>{lbl}</div>
              <div class='metric-value' style='color:{color};font-size:1.3rem'>{val}</div>
            </div>""", unsafe_allow_html=True)

    # equity curve
    eq = bt.get('equity_curve',[])
    if len(eq) > 2:
        ec = "#3d8c5f" if eq[-1]>=eq[0] else "#c0392b"
        ef = "rgba(61,140,95,.08)" if eq[-1]>=eq[0] else "rgba(192,57,43,.08)"
        efig = go.Figure()
        efig.add_trace(go.Scatter(y=eq,mode='lines',line=dict(color=ec,width=2),
                                  fill='tozeroy',fillcolor=ef))
        efig.update_layout(plot_bgcolor='#fff',paper_bgcolor='#f9f7f4',height=160,
            margin=dict(l=45,r=15,t=28,b=25),showlegend=False,
            title=dict(text='Equity Curve',font=dict(family='Noto Sans TC',size=11,color='#6b6560'),x=.01),
            xaxis=dict(showgrid=False,tickfont=dict(size=8,color='#9e9890')),
            yaxis=dict(gridcolor='#ede9e3',tickfont=dict(size=8,color='#9e9890')))
        st.plotly_chart(efig, use_container_width=True)

    # ── 跳空歷史分析區塊 ─────────────────────────────────────────────────────
    st.markdown("<div class='section-heading'>🕳️ 跳空歷史分析</div>", unsafe_allow_html=True)
    _render_gap_history(df, ticker, interval)

    # ── 異常波動監控區塊 ─────────────────────────────────────────────────────
    st.markdown("<div class='section-heading'>⚡ 異常波動監控</div>", unsafe_allow_html=True)
    _render_volatility_spike(df, ticker, interval, tg_token, tg_chat_id)

    # Telegram signal alert (BUY/SELL) - 純文字格式，無 HTML
    if tg_token and tg_chat_id and sig in ('BUY','SELL'):
        h = hashlib.md5(f"{ticker}{interval}{sig}{datetime.now().strftime('%Y%m%d%H')}".encode()).hexdigest()
        if h not in st.session_state.alert_hashes:
            msg = _build_tg_signal_msg(
                            ticker, sig, trend, overall, patterns,
                            signals, volume_analysis, market_struct,
                            scores, sr_levels, interval_label,
                            float(latest['Close']), ai_text)
            if send_telegram_alert(tg_token, tg_chat_id, msg):
                st.session_state.alert_hashes.add(h)
                st.success(f"📱 {ticker} Telegram 訊號已發送")


# ── 背景監控（所有股票）────────────────────────────────────────────────────────
def run_all_monitors():
    active = {tk: m for tk, m in st.session_state.monitors.items() if m.get("active")}
    if not active: return
    tg_t = st.session_state.get("_tg_token","")
    tg_c = st.session_state.get("_tg_chat","")
    if not tg_t or not tg_c: return

    import yfinance as yf
    for ticker, mon in active.items():
        try:
            cur = float(yf.Ticker(ticker).fast_info.last_price)
        except Exception:
            continue
        for label, cfg in mon["levels"].items():
            key = f"{ticker}_{label}_{cfg['price']:.2f}"
            if key in mon["triggered"]: continue
            hit = ((cfg["direction"]=="above" and cur >= cfg["price"]) or
                   (cfg["direction"]=="below" and cur <= cfg["price"]))
            if hit:
                mon["triggered"].add(key)
                arrow = "突破 ↑" if cfg["direction"]=="above" else "跌破 ↓"
                msg = (f"{cfg['icon']} *{ticker} 價位觸及*\n\n"
                       f"觸發：*{label}*\n監控價：${cfg['price']:.2f}\n"
                       f"當前價：${cur:.2f}\n方向：{arrow}\n"
                       f"時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                send_telegram_alert(tg_t, tg_c, msg)
                st.toast(f"{cfg['icon']} {ticker} {label} ${cfg['price']:.2f} 已觸及！", icon="🔔")

run_all_monitors()


# ── 全部異常波動背景監控 ────────────────────────────────────────────────────────
def _run_spike_monitor(stock_list: list, interval: str, bar_count: int):
    """
    遍歷所有股票，即時計算最新一根的異常波動，觸發時發 Telegram。
    使用 session_state 中的 spike_x / spike_y 參數。
    """
    if not st.session_state.spike_monitor_on:
        return

    tg_t = st.session_state.get("_tg_token", "")
    tg_c = st.session_state.get("_tg_chat",  "")
    if not tg_t or not tg_c:
        return

    x_val = int(st.session_state.get("spike_x", 20))
    y_val = float(st.session_state.get("spike_y", 2.0))

    from analysis.data_fetcher      import fetch_ohlcv
    from analysis.volatility_spike  import (compute_volatility_spike,
                                            build_spike_tg_msg)
    from analysis.telegram_bot      import send_telegram_alert

    for ticker in stock_list:
        try:
            df = fetch_ohlcv(ticker, interval, bar_count)
            if df is None or len(df) < x_val + 2:
                continue

            result = compute_volatility_spike(df, x=x_val)
            if result is None:
                continue

            from analysis.volatility_spike import get_triggered_two_bars
            trig_two = get_triggered_two_bars(result, y_val)
            if not trig_two:
                continue

            for trig_bar in trig_two:
                spike_key = f"{ticker}_{trig_bar['bar_label']}_{str(trig_bar['date'])[:16]}"
                if spike_key in st.session_state.spike_monitor_fired:
                    continue
                st.session_state.spike_monitor_fired[spike_key] = True
                msg = build_spike_tg_msg(ticker, interval, result, y_val, trig_bar)
                send_telegram_alert(tg_t, tg_c, msg)
                st.toast(
                    f"⚡ {ticker} {trig_bar['bar_label']} 異常波動！"
                    f"價格 {trig_bar['price_ratio']:.2f}x ＆ 量 {trig_bar['vol_ratio']:.2f}x",
                    icon="⚡"
                )

        except Exception:
            continue


# ── 主介面：多股票 Tabs ────────────────────────────────────────────────────────
stock_list = st.session_state.stock_list
_run_gap_monitor(stock_list, interval, bar_count)
_run_spike_monitor(stock_list, interval, bar_count)
if not stock_list:
    st.info("請在左側股票池新增股票代號")
    st.stop()

# 「分析全部」按鈕
if analyze_all:
    progress = st.progress(0, text="分析中...")
    for i, tk in enumerate(stock_list):
        progress.progress((i+1)/len(stock_list), text=f"正在分析 {tk}...")
        result = compute_ticker(tk)
        if result:
            st.session_state.cached[tk] = result
        else:
            st.warning(f"⚠️ {tk} 數據獲取失敗")
    progress.empty()
    st.rerun()

# 個別分析按鈕：放在 Tab 內部，由 render_ticker 處理

# Tabs
tab_labels = []
for tk in stock_list:
    cached_ok = tk in st.session_state.cached
    mon_on    = st.session_state.monitors.get(tk,{}).get("active",False)
    prefix    = "🔔 " if mon_on else ("✓ " if cached_ok else "○ ")
    tab_labels.append(f"{prefix}{tk}")

tabs = st.tabs(tab_labels)
for tab, tk in zip(tabs, stock_list):
    with tab:
        if tk in st.session_state.cached:
            _ctx = st.session_state.cached[tk]
            # 新鮮度警告：日線快取超過6小時提示重新分析
            import time as _t2
            _age_h = (_t2.time() - _ctx.get('fetch_ts', 0)) / 3600
            _df_latest = _ctx.get('df_latest', '')
            _stale_warn = ""
            if interval == '1d' and _age_h > 6:
                _stale_warn = (
                    f"⚠️ 數據已快取 {_age_h:.0f} 小時（最新K線：{_df_latest}），"
                    f"請點擊「重新分析」取得最新數據。"
                )
            elif interval in ('1m','5m','15m','30m') and _age_h > 0.25:
                _stale_warn = (
                    f"⚠️ 數據已快取 {_age_h*60:.0f} 分鐘（最新K線：{_df_latest}），"
                    f"短線週期建議重新分析。"
                )
            if _stale_warn:
                st.warning(_stale_warn)
            render_ticker(_ctx)
        else:
            st.markdown(
                f"<div style='text-align:center;padding:3rem 2rem;color:#b8b2aa'>"
                f"<div style='font-size:2rem;margin-bottom:.8rem;color:#ccc8be'>◈</div>"
                f"<div style='font-size:.9rem;color:#9e9890'>{tk} 尚未分析</div>"
                f"</div>",
                unsafe_allow_html=True
            )
            c_btn = st.columns([1, 2, 1])
            with c_btn[1]:
                if st.button(f"🔍 分析 {tk}", use_container_width=True, key=f"single_{tk}"):
                    with st.spinner(f"正在分析 {tk}..."):
                        result = compute_ticker(tk)
                    if result:
                        st.session_state.cached[tk] = result
                        st.rerun()
                    else:
                        st.error(f"❌ {tk} 數據獲取失敗，請確認代號是否正確")

# 自動刷新
if refresh_sec > 0 and st.session_state.cached:
    time.sleep(refresh_sec)
    for tk in list(st.session_state.cached.keys()):
        result = compute_ticker(tk)
        if result: st.session_state.cached[tk] = result
    st.rerun()
elif st.session_state.monitors and any(m.get("active") for m in st.session_state.monitors.values()):
    time.sleep(30)
    st.rerun()
