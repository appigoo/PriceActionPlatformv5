"""
Candlestick Chart - Warm Cream Theme
風格完全對齊附件截圖：白/米色背景、淺灰網格、柔和紅綠
"""
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# ── Colour palette（附件風格）──────────────────────────────────────────────────
BULL_CANDLE  = "#3d8c5f"       # 柔和綠
BEAR_CANDLE  = "#c0392b"       # 柔和紅
BULL_FILL    = "#3d8c5f"
BEAR_FILL    = "#c0392b"
VOL_BULL     = "rgba(61,140,95,0.55)"
VOL_BEAR     = "rgba(192,57,43,0.55)"
VOL_BULL_DIM = "rgba(61,140,95,0.25)"
VOL_BEAR_DIM = "rgba(192,57,43,0.25)"
EMA20_COLOR  = "#5b8fd4"       # 藍
EMA50_COLOR  = "#b07d2e"       # 金
GRID_COLOR   = "#ede9e3"       # 淺米灰
AXIS_COLOR   = "#b8b2aa"
BG_PLOT      = "#ffffff"
BG_PAPER     = "#f9f7f4"
FONT_COLOR   = "#6b6560"
SUP_COLOR    = "#3d8c5f"
RES_COLOR    = "#c0392b"
ZONE_BULL    = "rgba(61,140,95,0.05)"
ZONE_BEAR    = "rgba(192,57,43,0.05)"


def build_chart(df, ticker, interval, sr_levels, signals, market_struct, patterns) -> go.Figure:
    dates  = df.index
    opens  = df['Open'].values
    highs  = df['High'].values
    lows   = df['Low'].values
    closes = df['Close'].values
    vols   = df['Volume'].values
    n      = len(df)

    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.02,
        row_heights=[0.70, 0.30],
    )

    # ── CANDLESTICKS ──────────────────────────────────────────────────────────
    fig.add_trace(go.Candlestick(
        x=dates,
        open=opens, high=highs, low=lows, close=closes,
        name="K線",
        increasing_line_color=BULL_CANDLE,
        decreasing_line_color=BEAR_CANDLE,
        increasing_fillcolor=BULL_FILL,
        decreasing_fillcolor=BEAR_FILL,
        line_width=1,
    ), row=1, col=1)

    # ── EMA LINES ─────────────────────────────────────────────────────────────
    ema20 = market_struct.get('ema20')
    ema50 = market_struct.get('ema50')
    if ema20 is not None:
        fig.add_trace(go.Scatter(
            x=dates, y=ema20, name="EMA 20",
            line=dict(color=EMA20_COLOR, width=1.5, dash='dot'),
            opacity=0.85,
        ), row=1, col=1)
    if ema50 is not None:
        fig.add_trace(go.Scatter(
            x=dates, y=ema50, name="EMA 50",
            line=dict(color=EMA50_COLOR, width=1.5, dash='dot'),
            opacity=0.85,
        ), row=1, col=1)

    # ── DEMAND ZONES（淡綠色區塊）────────────────────────────────────────────
    for (lo, hi) in sr_levels.get('demand_zones', [])[:2]:
        fig.add_hrect(
            y0=lo, y1=hi, row=1, col=1,
            fillcolor=ZONE_BULL, line_width=0,
        )

    # ── SUPPLY ZONES（淡紅色區塊）────────────────────────────────────────────
    for (lo, hi) in sr_levels.get('supply_zones', [])[:2]:
        fig.add_hrect(
            y0=lo, y1=hi, row=1, col=1,
            fillcolor=ZONE_BEAR, line_width=0,
        )

    # ── SUPPORT LINES ─────────────────────────────────────────────────────────
    for i, s in enumerate(sr_levels.get('supports', [])[:3]):
        fig.add_hline(
            y=s, row=1, col=1,
            line=dict(color=SUP_COLOR, width=1, dash='dash'),
            annotation_text=f"支撐 ${s:.2f}" if i == 0 else f"S {s:.2f}",
            annotation_position="left",
            annotation_font=dict(color=SUP_COLOR, size=9, family="IBM Plex Mono"),
            opacity=0.65,
        )

    # ── RESISTANCE LINES ──────────────────────────────────────────────────────
    for i, r in enumerate(sr_levels.get('resistances', [])[:3]):
        fig.add_hline(
            y=r, row=1, col=1,
            line=dict(color=RES_COLOR, width=1, dash='dash'),
            annotation_text=f"阻力 ${r:.2f}" if i == 0 else f"R {r:.2f}",
            annotation_position="right",
            annotation_font=dict(color=RES_COLOR, size=9, family="IBM Plex Mono"),
            opacity=0.65,
        )

    # ── SWING HIGH / LOW MARKERS ──────────────────────────────────────────────
    sh = market_struct.get('swing_highs', [])
    sl = market_struct.get('swing_lows', [])
    if sh:
        sh_x = [dates[min(i, n-1)] for i, _ in sh]
        sh_y = [v for _, v in sh]
        fig.add_trace(go.Scatter(
            x=sh_x, y=sh_y, mode='markers',
            marker=dict(symbol='triangle-down', color=RES_COLOR, size=7, opacity=0.75),
            name='Swing High', showlegend=False,
        ), row=1, col=1)
    if sl:
        sl_x = [dates[min(i, n-1)] for i, _ in sl]
        sl_y = [v for _, v in sl]
        fig.add_trace(go.Scatter(
            x=sl_x, y=sl_y, mode='markers',
            marker=dict(symbol='triangle-up', color=SUP_COLOR, size=7, opacity=0.75),
            name='Swing Low', showlegend=False,
        ), row=1, col=1)

    # ── BUY / SELL SIGNAL ARROWS ──────────────────────────────────────────────
    primary = signals.get('primary', 'NEUTRAL')
    if primary == 'BUY':
        fig.add_trace(go.Scatter(
            x=[dates[-1]], y=[lows[-1] * 0.994],
            mode='markers+text',
            marker=dict(symbol='triangle-up', color=BULL_CANDLE, size=18,
                        line=dict(width=1.5, color='#2a6b48')),
            text=["▲ BUY"],
            textposition="bottom center",
            textfont=dict(color=BULL_CANDLE, size=10, family="IBM Plex Mono"),
            name='BUY Signal',
        ), row=1, col=1)
    elif primary == 'SELL':
        fig.add_trace(go.Scatter(
            x=[dates[-1]], y=[highs[-1] * 1.006],
            mode='markers+text',
            marker=dict(symbol='triangle-down', color=BEAR_CANDLE, size=18,
                        line=dict(width=1.5, color='#8b1a10')),
            text=["▼ SELL"],
            textposition="top center",
            textfont=dict(color=BEAR_CANDLE, size=10, family="IBM Plex Mono"),
            name='SELL Signal',
        ), row=1, col=1)

    # ── VOLUME BARS ───────────────────────────────────────────────────────────
    avg_vol = np.mean(vols[-20:]) if n >= 20 else np.mean(vols)
    vol_colors = []
    for i in range(n):
        is_bull = closes[i] >= opens[i]
        above_avg = vols[i] > avg_vol
        if is_bull:
            vol_colors.append(VOL_BULL if above_avg else VOL_BULL_DIM)
        else:
            vol_colors.append(VOL_BEAR if above_avg else VOL_BEAR_DIM)

    fig.add_trace(go.Bar(
        x=dates, y=vols,
        name="成交量",
        marker_color=vol_colors,
    ), row=2, col=1)

    # Vol MA20
    fig.add_trace(go.Scatter(
        x=dates, y=[avg_vol] * n,
        name="Vol MA20",
        line=dict(color=EMA50_COLOR, width=1.2, dash='dot'),
        opacity=0.75,
    ), row=2, col=1)

    # ── LAYOUT（附件風格：白底，淺灰網格，柔和字體）────────────────────────────
    trend = market_struct.get('trend', '')
    trend_icon = "📈" if "多頭" in trend else ("📉" if "空頭" in trend else "⟷")

    fig.update_layout(
        title=dict(
            text=f"{ticker} &nbsp;·&nbsp; {interval} &nbsp;·&nbsp; {trend_icon} {trend}",
            font=dict(family="Noto Sans TC", size=13, color=FONT_COLOR),
            x=0.01,
        ),
        plot_bgcolor=BG_PLOT,
        paper_bgcolor=BG_PAPER,
        height=600,
        margin=dict(l=65, r=85, t=48, b=8),
        font=dict(family="IBM Plex Mono", color=FONT_COLOR, size=10),
        legend=dict(
            bgcolor="rgba(255,255,255,0.85)",
            bordercolor=GRID_COLOR,
            borderwidth=1,
            font=dict(size=9, color=FONT_COLOR),
            orientation="h",
            x=0, y=1.04,
        ),
        hovermode='x unified',
        hoverlabel=dict(
            bgcolor="rgba(255,255,255,0.95)",
            bordercolor=GRID_COLOR,
            font=dict(family="IBM Plex Mono", size=10, color=FONT_COLOR),
        ),
        xaxis_rangeslider_visible=False,
        dragmode='zoom',
    )

    # ── AXES ─────────────────────────────────────────────────────────────────
    shared_axis = dict(
        gridcolor=GRID_COLOR,
        zerolinecolor=GRID_COLOR,
        linecolor=GRID_COLOR,
        tickfont=dict(size=9, color=AXIS_COLOR, family="IBM Plex Mono"),
        showspikes=True,
        spikecolor=AXIS_COLOR,
        spikedash='dot',
        spikethickness=1,
    )
    fig.update_xaxes(**shared_axis)
    fig.update_yaxes(**shared_axis)
    fig.update_yaxes(tickprefix='$', row=1, col=1)
    fig.update_yaxes(title_text="成交量", title_font=dict(size=9, color=AXIS_COLOR), row=2, col=1)

    # ── RANGEBREAKS：隱藏非交易時段空白 ──────────────────────────────────────
    intraday = interval in {"1m", "5m", "15m", "30m", "1h"}
    if intraday:
        # 隱藏週末 + 非交易時段（16:00 到次日 09:30 ET）
        fig.update_xaxes(rangebreaks=[
            dict(bounds=["sat", "mon"]),
            dict(bounds=[16, 9.5], pattern="hour"),
        ])
    else:
        # 日線/週線：只隱藏週末
        fig.update_xaxes(rangebreaks=[
            dict(bounds=["sat", "mon"]),
        ])

    return fig
