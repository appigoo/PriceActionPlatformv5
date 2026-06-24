"""Data fetching with yfinance - 過濾非交易時段"""
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

INTERVAL_PERIOD_MAP = {
    "1m":  "5d",
    "5m":  "60d",
    "15m": "60d",
    "30m": "60d",
    "1h":  "730d",
    "1d":  "5y",
    "1wk": "10y",
}

# 美股正式交易時段（ET）= UTC-4/5，這裡用 UTC 時間範圍
# 美股：09:30–16:00 ET = 13:30–20:00 UTC（夏令），14:30–21:00 UTC（冬令）
# 用寬鬆範圍：UTC 12:00–22:00 保留（含盤前盤後少量），其餘過濾
INTRADAY_INTERVALS = {"1m", "5m", "15m", "30m", "1h"}


def fetch_ohlcv(ticker: str, interval: str, bar_count: int = 120) -> pd.DataFrame | None:
    try:
        tk  = yf.Ticker(ticker)
        now = datetime.utcnow()

        # ── 用 start/end 取代 period，確保拿到最新數據 ───────────────────────
        # 加 2 天緩衝到 end，避免時區問題導致漏掉今天/昨天
        end_dt   = now + timedelta(days=2)

        # 根據 interval 決定往前取多少天
        LOOKBACK_DAYS = {
            "1m":  7,      # yfinance 最多7天
            "5m":  60,
            "15m": 60,
            "30m": 60,
            "1h":  730,
            "1d":  1825,   # 5年
            "1wk": 3650,   # 10年
        }
        lookback  = LOOKBACK_DAYS.get(interval, 365)
        start_dt  = now - timedelta(days=lookback)

        df = tk.history(
            start=start_dt.strftime('%Y-%m-%d'),
            end=end_dt.strftime('%Y-%m-%d'),
            interval=interval,
            auto_adjust=True
        )

        if df is None or len(df) < 10:
            # Fallback：用 period 參數再試一次
            period = INTERVAL_PERIOD_MAP.get(interval, "1y")
            df = tk.history(period=period, interval=interval, auto_adjust=True)
            if df is None or len(df) < 10:
                return None

        df = df.dropna(subset=["Open","High","Low","Close"])

        # ── 過濾非交易時段（只對分鐘/小時級別）────────────────────────────
        if interval in INTRADAY_INTERVALS:
            df = _filter_trading_hours(df, interval)

        # ── 過濾成交量為 0 的 bar ────────────────────────────────────────────
        if "Volume" in df.columns:
            df = df[df["Volume"] > 0]

        if len(df) < 10:
            return None

        df = df.tail(bar_count)
        df.index = pd.to_datetime(df.index)
        return df

    except Exception:
        return None


def _filter_trading_hours(df: pd.DataFrame, interval: str) -> pd.DataFrame:
    """
    過濾非交易時段 K 線。
    美股正式盤：09:30-16:00 ET（America/New_York）
    """
    try:
        idx = df.index

        # 統一轉換為 America/New_York
        if idx.tz is None:
            idx_et = idx.tz_localize("America/New_York")
        else:
            idx_et = idx.tz_convert("America/New_York")

        hour_et   = idx_et.hour
        minute_et = idx_et.minute
        time_min  = hour_et * 60 + minute_et

        # 只保留周一到周五
        is_weekday = idx_et.dayofweek <= 4

        # 只保留 09:30-15:59 ET（正式交易時段）
        is_market = (time_min >= 570) & (time_min < 960)

        mask = is_weekday & is_market

        # mask 可能是 Index 或 array，統一轉 numpy
        filtered = df[mask.to_numpy() if hasattr(mask, 'to_numpy') else mask]

        # fallback：過濾後太少就退回原始（可能是非美股）
        if len(filtered) < max(5, len(df) // 4):
            return df

        return filtered

    except Exception:
        return df
