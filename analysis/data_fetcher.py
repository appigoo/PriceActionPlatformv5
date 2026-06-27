"""Data fetching with yfinance + curl_cffi fallback - 過濾非交易時段"""
import yfinance as yf
import pandas as pd
import numpy as np
import json
from datetime import datetime, timedelta

def _fetch_via_curl(ticker: str, interval: str, lookback_days: int) -> pd.DataFrame | None:
    """
    用 curl_cffi 模擬瀏覽器直接抓 Yahoo Finance API
    繞過 yfinance 的數據延遲問題
    """
    try:
        from curl_cffi import requests as curl_requests

        now      = datetime.utcnow()
        end_ts   = int((now + timedelta(days=2)).timestamp())
        start_ts = int((now - timedelta(days=lookback_days)).timestamp())

        INTERVAL_MAP = {
            '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
            '1h': '60m', '1d': '1d', '1wk': '1wk',
        }
        yf_interval = INTERVAL_MAP.get(interval, '1d')

        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
            f"?interval={yf_interval}&period1={start_ts}&period2={end_ts}"
            f"&includePrePost=false&events=div%2Csplit"
        )

        resp = curl_requests.get(
            url,
            impersonate="chrome124",
            timeout=15,
            headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                              "AppleWebKit/537.36 (KHTML, like Gecko) "
                              "Chrome/124.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

        if resp.status_code != 200:
            return None

        data   = resp.json()
        result = data.get('chart', {}).get('result', [])
        if not result:
            return None

        r         = result[0]
        timestamps= r.get('timestamp', [])
        quote     = r.get('indicators', {}).get('quote', [{}])[0]
        adjclose  = r.get('indicators', {}).get('adjclose', [{}])
        adj_arr   = adjclose[0].get('adjclose', []) if adjclose else []

        if not timestamps:
            return None

        opens   = quote.get('open',   [None]*len(timestamps))
        highs   = quote.get('high',   [None]*len(timestamps))
        lows    = quote.get('low',    [None]*len(timestamps))
        closes  = quote.get('close',  [None]*len(timestamps))
        volumes = quote.get('volume', [None]*len(timestamps))

        rows = []
        for i, ts in enumerate(timestamps):
            o = opens[i]; h = highs[i]; l = lows[i]
            c = closes[i]; v = volumes[i]
            if any(x is None for x in [o, h, l, c]):
                continue
            # 用 adjclose 調整（若有）
            if adj_arr and i < len(adj_arr) and adj_arr[i] and c and c != 0:
                ratio = adj_arr[i] / c
                o *= ratio; h *= ratio; l *= ratio; c = adj_arr[i]
            rows.append({
                'Open': o, 'High': h, 'Low': l, 'Close': c,
                'Volume': v or 0,
            })

        if not rows:
            return None

        idx = pd.to_datetime(timestamps, unit='s', utc=True).tz_convert('America/New_York')
        df  = pd.DataFrame(rows, index=idx)

        # 日線：只保留日期部分
        if interval == '1d':
            df.index = df.index.normalize().tz_localize(None)
            df = df[~df.index.duplicated(keep='last')]

        df = df.dropna(subset=['Open','High','Low','Close'])
        df = df[df['Volume'] > 0]
        return df if len(df) >= 5 else None

    except Exception:
        return None


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
    """
    多策略抓取 OHLCV，確保拿到最新數據。
    策略順序：
      1. start/end + auto_adjust=True
      2. start/end + auto_adjust=False（手動調整）
      3. period 參數 fallback
    """
    now    = datetime.utcnow()
    end_dt = now + timedelta(days=3)   # +3天緩衝

    LOOKBACK_DAYS = {
        "1m": 7, "5m": 60, "15m": 60, "30m": 60,
        "1h": 730, "1d": 1825, "1wk": 3650,
    }
    lookback = LOOKBACK_DAYS.get(interval, 365)
    start_dt = now - timedelta(days=lookback)
    s_str    = start_dt.strftime('%Y-%m-%d')
    e_str    = end_dt.strftime('%Y-%m-%d')

    def _clean(df):
        """清洗 df：去 NaN、過濾非交易時段、過濾零成交量"""
        if df is None or len(df) < 10:
            return None
        # 儲存原始最新日期（清洗前）供診斷
        _raw_latest = str(df.index[-1])[:10] if len(df) > 0 else 'N/A'
        # 記錄 NaN 過濾情況
        _nan_rows = df[df[["Open","High","Low","Close"]].isnull().any(axis=1)]
        if len(_nan_rows) > 0:
            df.attrs['filtered_nan'] = [str(d)[:10] for d in _nan_rows.index[-3:]]
        # 只要求 Close 有值（Open/High/Low 缺失時用 Close 填補）
        df = df.dropna(subset=["Close"])
        df["Open"]  = df["Open"].fillna(df["Close"])
        df["High"]  = df["High"].fillna(df["Close"])
        df["Low"]   = df["Low"].fillna(df["Close"])
        if interval in INTRADAY_INTERVALS:
            df = _filter_trading_hours(df, interval)
        # 記錄零成交量過濾情況
        if "Volume" in df.columns:
            _zero_vol = df[df["Volume"] <= 0]
            if len(_zero_vol) > 0:
                df.attrs['filtered_zero_vol'] = [str(d)[:10] for d in _zero_vol.index[-3:]]
            df = df[df["Volume"] > 0]
        df.attrs['raw_latest'] = _raw_latest
        if len(df) < 10:
            return None
        return df

    tk = yf.Ticker(ticker)
    df = None

    # ── 策略0：curl_cffi 直接抓 Yahoo Finance API（最新，繞過延遲）────────
    _strategy_used = "none"
    try:
        df = _fetch_via_curl(ticker, interval, lookback)
        if df is not None:
            df = _clean(df)
        if df is not None:
            _strategy_used = "curl_cffi"
    except Exception:
        df = None

    # ── 策略1：start/end + auto_adjust=False（避免除息調整導致價格偏移）─────
    if df is None:
        try:
            raw = tk.history(start=s_str, end=e_str,
                             interval=interval, auto_adjust=False, actions=False)
            df = _clean(raw)
            if df is not None:
                _strategy_used = "yf_start_end_noadjust"
        except Exception:
            df = None

    # ── 策略2：start/end + auto_adjust=True ────────────────────────────
    if df is None:
        try:
            raw = tk.history(start=s_str, end=e_str,
                             interval=interval, auto_adjust=True, actions=False)
            df = _clean(raw)
            if df is not None:
                _strategy_used = "yf_start_end_adjust"
        except Exception:
            df = None

    # ── 策略3：period 參數 fallback ──────────────────────────────────────
    if df is None:
        try:
            period = INTERVAL_PERIOD_MAP.get(interval, "1y")
            raw = tk.history(period=period, interval=interval, auto_adjust=True)
            df = _clean(raw)
            if df is not None:
                _strategy_used = "yf_period"
        except Exception:
            df = None

    if df is None:
        return None

    # 記錄使用的策略和最新日期（供 UI 顯示）
    df.attrs['strategy'] = _strategy_used
    df.attrs['fetch_time'] = datetime.utcnow().strftime('%H:%M:%S UTC')

    df = df.tail(bar_count)
    df.index = pd.to_datetime(df.index)

    # ── 新鮮度補充：若日線最新K線過舊，嘗試用 fast_info 補入最新收盤 ──────
    if interval == '1d':
        try:
            latest_date = df.index[-1].date()
            today       = datetime.utcnow().date()
            days_gap    = (today - latest_date).days

            if days_gap >= 2:
                # 方法A：用 fast_info 取最新價格（不需要完整 OHLCV）
                try:
                    fi = tk.fast_info
                    last_price = float(fi.last_price)
                    last_vol   = float(fi.three_month_average_volume or 0)
                    # 構造一根近似K線（OHLC 都用 last_price）
                    from datetime import date as _date
                    # 找最近的交易日（今天或昨天）
                    target_date = today
                    if today.weekday() >= 5:  # 週末用週五
                        target_date = today - timedelta(days=today.weekday()-4)
                    target_ts = pd.Timestamp(target_date)
                    if target_ts not in df.index and target_ts > df.index[-1]:
                        new_row = pd.DataFrame([{
                            'Open': last_price, 'High': last_price,
                            'Low':  last_price, 'Close': last_price,
                            'Volume': last_vol,
                        }], index=[target_ts])
                        # 時區對齊
                        if hasattr(df.index, 'tz') and df.index.tz is not None:
                            df.index = df.index.tz_localize(None)
                        df = pd.concat([df, new_row])
                        df = df[~df.index.duplicated(keep='last')]
                        df = df.sort_index()
                        df.attrs['patched_with_fast_info'] = str(target_date)
                except Exception:
                    pass

                # 方法B：yf.download fallback
                if df.index[-1].date() < today - timedelta(days=1):
                    try:
                        patch_dl = yf.download(
                            ticker, period='5d', interval='1d',
                            auto_adjust=False, progress=False,
                        )
                        if patch_dl is not None and len(patch_dl) > 0:
                            if isinstance(patch_dl.columns, pd.MultiIndex):
                                patch_dl.columns = patch_dl.columns.get_level_values(0)
                            patch_dl = patch_dl.dropna(subset=['Close'])
                            patch_dl['Open']   = patch_dl['Open'].fillna(patch_dl['Close'])
                            patch_dl['High']   = patch_dl['High'].fillna(patch_dl['Close'])
                            patch_dl['Low']    = patch_dl['Low'].fillna(patch_dl['Close'])
                            patch_dl['Volume'] = patch_dl['Volume'].fillna(0)
                            patch_dl.index = pd.to_datetime(patch_dl.index)
                            if hasattr(patch_dl.index,'tz') and patch_dl.index.tz:
                                patch_dl.index = patch_dl.index.tz_localize(None)
                            if hasattr(df.index,'tz') and df.index.tz:
                                df.index = df.index.tz_localize(None)
                            new_bars = patch_dl[patch_dl.index > df.index[-1]]
                            if len(new_bars) > 0:
                                df = pd.concat([df, new_bars])
                                df = df[~df.index.duplicated(keep='last')]
                                df = df.sort_index()
                    except Exception:
                        pass
        except Exception:
            pass

    return df


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
