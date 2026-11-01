"""
indicators/indicators.py - Mathematical indicator calculations.
Part of the Indicators Department.
Calculates:
- Rolling mean (ta.sma)
- Rolling standard deviation (ta.stdev)
- Z-Score (close - mean) / std
- Linear regression slope: ta.linreg(close, window, 0) - ta.linreg(close, window, 1)
- True Volume-Weighted Average Price (Session VWAP) with ±1σ and ±2σ Exhaustion Bands
- 20-period Volume Moving Average (volume_ma_20)
"""
import numpy as np
import pandas as pd


def calculate_sma(series: pd.Series, window: int) -> pd.Series:
    """Pine Script equivalent ta.sma(close, window)."""
    return series.rolling(window=window, min_periods=window).mean()


def calculate_stdev(series: pd.Series, window: int) -> pd.Series:
    """
    Pine Script equivalent ta.stdev(close, window).
    TradingView calculates population standard deviation (ddof=0).
    """
    return series.rolling(window=window, min_periods=window).std(ddof=0)


def calculate_z_score(close: pd.Series, mean: pd.Series, std: pd.Series) -> pd.Series:
    """Pine Script equivalent: z = std > 0 ? (close - mean) / std : 0."""
    z = np.where(std > 0, (close - mean) / std, 0.0)
    return pd.Series(z, index=close.index)


def calculate_linreg_slope(series: pd.Series, window: int) -> pd.Series:
    """
    Pine Script equivalent: ta.linreg(close, window, 0) - ta.linreg(close, window, 1).
    This computes the exact slope of the linear regression line over the rolling window.
    """
    x = np.arange(window)
    x_mean = (window - 1) / 2.0
    denom = np.sum((x - x_mean) ** 2)
    weights = (x - x_mean) / denom

    def get_slope(y):
        return float(np.dot(y, weights))

    slope = series.rolling(window=window, min_periods=window).apply(get_slope, raw=True)
    return slope


def calculate_session_vwap_with_bands(df: pd.DataFrame, num_std: float = 2.0) -> pd.DataFrame:
    """
    Calculates Intraday Session VWAP with Standard Deviation Bands:
    - VWAP (Session volume-weighted average price)
    - Upper +2σ Exhaustion Band (Overbought reversal zone)
    - Lower -2σ Exhaustion Band (Oversold reversal zone)
    Resets at 9:15 AM IST daily.
    When true constituent aggregate volume is supplied, produces authentic institutional VWAP.
    """
    if df is None or df.empty or "close" not in df:
        return df

    res = df.copy()
    tp = (res["high"] + res["low"] + res["close"]) / 3.0
    vol = res["volume"].copy() if "volume" in res else pd.Series(1.0, index=res.index)

    # If volume is all zeros, default to 1.0 per bar
    if (vol > 0).sum() == 0:
        vol = pd.Series(1.0, index=res.index)
    else:
        vol = vol.replace(0, 1.0)

    dates = res.index.normalize()
    tp_vol = tp * vol

    cum_tp_vol = tp_vol.groupby(dates).cumsum()
    cum_vol = vol.groupby(dates).cumsum()
    cum_vol_safe = np.maximum(cum_vol, 1e-9)
    vwap = cum_tp_vol / cum_vol_safe
    res["vwap"] = vwap

    # Volume-weighted variance
    dev_sq_vol = vol * (tp - vwap) ** 2
    cum_dev_sq_vol = dev_sq_vol.groupby(dates).cumsum()
    variance = cum_dev_sq_vol / cum_vol_safe
    std_dev = np.sqrt(np.maximum(variance, 0.0))

    res["vwap_std"] = std_dev
    res["vwap_upper_1"] = vwap + 1.0 * std_dev
    res["vwap_lower_1"] = vwap - 1.0 * std_dev
    res["vwap_upper_2"] = vwap + num_std * std_dev  # +2σ Exhaustion Band
    res["vwap_lower_2"] = vwap - num_std * std_dev  # -2σ Exhaustion Band
    return res


def compute_all_indicators(df: pd.DataFrame, cfg) -> pd.DataFrame:
    """Appends all Strategy and VWAP/Bands indicators to historical DataFrame."""
    res = df.copy()
    close = res['close']
    window = cfg.window

    mean = calculate_sma(close, window)
    std = calculate_stdev(close, window)
    z = calculate_z_score(close, mean, std)
    slope = calculate_linreg_slope(close, window)

    res['mean'] = mean
    res['std'] = std
    res['z'] = z
    res['slope'] = slope

    # Volume Moving Average (20-period standard)
    if "volume" in res:
        res['volume_ma_20'] = res['volume'].rolling(20, min_periods=1).mean().round(2)
    else:
        res['volume_ma_20'] = 0.0

    # Session VWAP and +2σ / -2σ Exhaustion Bands
    res = calculate_session_vwap_with_bands(res, num_std=2.0)
    return res


# -------------------------------------------------------------
# 📈 Extended Multi-Length Moving Averages & Oscillators
# -------------------------------------------------------------

def calculate_ema(series: pd.Series, span: int) -> pd.Series:
    """Computes Exponential Moving Average (EMA) with given period span."""
    return series.ewm(span=span, adjust=False).mean()


def calculate_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    """Computes Relative Strength Index (RSI)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / np.maximum(avg_loss, 1e-9)
    return 100.0 - (100.0 / (1.0 + rs))


def calculate_macd(series: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Computes MACD Line, Signal Line, and Histogram."""
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal, adjust=False).mean()
    macd_hist = macd_line - macd_signal
    return macd_line, macd_signal, macd_hist


def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Computes Average True Range (ATR)."""
    high_low = df["high"] - df["low"]
    high_close = (df["high"] - df["close"].shift(1)).abs()
    low_close = (df["low"] - df["close"].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.ewm(com=period - 1, min_periods=period).mean()


def calculate_bollinger_bands(series: pd.Series, period: int = 20, std: float = 2.0):
    """Computes Bollinger Bands (Upper, Middle, Lower)."""
    middle = series.rolling(window=period, min_periods=period).mean()
    rolling_std = series.rolling(window=period, min_periods=period).std(ddof=0)
    upper = middle + (std * rolling_std)
    lower = middle - (std * rolling_std)
    return upper, middle, lower


def calculate_supertrend(df: pd.DataFrame, period: int = 10, multiplier: float = 3.0):
    """
    Computes Supertrend (ATR Trailing Stop & Trend Direction).
    Returns (latest_val, latest_direction: 1 for CALL/BULLISH, -1 for PUT/BEARISH).
    """
    if df is None or len(df) < period:
        return 0.0, 1
    high, low, close = df['high'], df['low'], df['close']
    hl2 = (high + low) / 2.0
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    atr = tr.ewm(com=period - 1, min_periods=period).mean()
    up = hl2 - (multiplier * atr)
    dn = hl2 + (multiplier * atr)
    st = pd.Series(index=df.index, dtype=float)
    direction = pd.Series(index=df.index, dtype=int)
    in_up = True
    for i in range(len(df)):
        c = close.iloc[i]
        u = up.iloc[i]
        d = dn.iloc[i]
        if i == 0:
            st.iloc[i] = u
            direction.iloc[i] = 1
            continue
        prev = st.iloc[i-1]
        if in_up:
            curr = max(u, prev) if close.iloc[i-1] > prev else u
            if c < curr:
                in_up = False
                curr = d
            st.iloc[i] = curr
            direction.iloc[i] = 1 if in_up else -1
        else:
            curr = min(d, prev) if close.iloc[i-1] < prev else d
            if c > curr:
                in_up = True
                curr = u
            st.iloc[i] = curr
            direction.iloc[i] = 1 if in_up else -1
    return round(float(st.iloc[-1]), 2), int(direction.iloc[-1])


def calculate_adx(df: pd.DataFrame, period: int = 14):
    """
    Computes Average Directional Index (ADX) & Directional Movement (+DI / -DI).
    Returns (adx, plus_di, minus_di).
    """
    if df is None or len(df) < period + 1:
        return 20.0, 20.0, 20.0
    high, low, close = df['high'], df['low'], df['close']
    up_m = high.diff()
    dn_m = -low.diff()
    p_dm = np.where((up_m > dn_m) & (up_m > 0), up_m, 0.0)
    m_dm = np.where((dn_m > up_m) & (dn_m > 0), dn_m, 0.0)
    tr = pd.concat([high - low, (high - close.shift(1)).abs(), (low - close.shift(1)).abs()], axis=1).max(axis=1)
    tr_s = tr.ewm(com=period - 1, min_periods=period).mean()
    p_di = 100 * pd.Series(p_dm, index=df.index).ewm(com=period - 1, min_periods=period).mean() / np.maximum(tr_s, 1e-9)
    m_di = 100 * pd.Series(m_dm, index=df.index).ewm(com=period - 1, min_periods=period).mean() / np.maximum(tr_s, 1e-9)
    dx = 100 * (p_di - m_di).abs() / np.maximum(p_di + m_di, 1e-9)
    adx = dx.ewm(com=period - 1, min_periods=period).mean()
    return round(float(adx.iloc[-1]), 2), round(float(p_di.iloc[-1]), 2), round(float(m_di.iloc[-1]), 2)


def calculate_cpr(df: pd.DataFrame):
    """
    Computes Central Pivot Range (CPR: Pivot, Top Central TC, Bottom Central BC).
    Uses previous trading day's high, low, close.
    Returns (pivot, tc, bc, cpr_type).
    """
    if df is None or df.empty:
        return 22500.0, 22520.0, 22480.0, 'NORMAL'
    days = df.index.normalize().unique()
    prev_d = days[-2] if len(days) >= 2 else days[-1]
    p_df = df[df.index.normalize() == prev_d]
    if p_df.empty:
        p_df = df
    ph, pl, pc = float(p_df['high'].max()), float(p_df['low'].min()), float(p_df['close'].iloc[-1])
    pivot = (ph + pl + pc) / 3.0
    bc = (ph + pl) / 2.0
    tc = (pivot - bc) + pivot
    w = abs(tc - bc)
    cpr_type = 'NARROW_TRENDING' if w <= 35.0 else 'WIDE_RANGEBOUND'
    return round(pivot, 2), round(tc, 2), round(bc, 2), cpr_type


def calculate_stoch_rsi(series: pd.Series, period: int = 14, k_period: int = 3, d_period: int = 3):
    """
    Computes Stochastic RSI (%K and %D).
    Returns (k, d).
    """
    if series is None or len(series) < period + k_period:
        return 50.0, 50.0
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(com=period - 1, min_periods=period).mean()
    avg_loss = loss.ewm(com=period - 1, min_periods=period).mean()
    rs = avg_gain / np.maximum(avg_loss, 1e-9)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    ll = rsi.rolling(period, min_periods=period).min()
    hh = rsi.rolling(period, min_periods=period).max()
    stoch = 100.0 * (rsi - ll) / np.maximum(hh - ll, 1e-9)
    k = stoch.rolling(k_period, min_periods=k_period).mean()
    d = k.rolling(d_period, min_periods=d_period).mean()
    k_val = round(float(k.iloc[-1]), 2) if pd.notnull(k.iloc[-1]) else 50.0
    d_val = round(float(d.iloc[-1]), 2) if pd.notnull(d.iloc[-1]) else 50.0
    return k_val, d_val


def calculate_parabolic_sar(df: pd.DataFrame, step: float = 0.02, max_step: float = 0.2):
    """
    Computes Wilder's Parabolic SAR.
    Returns latest SAR price level.
    """
    if df is None or len(df) < 5:
        return round(float(df['close'].iloc[-1]), 2) if df is not None and not df.empty else 22500.0
    high = df['high'].values
    low = df['low'].values
    close = df['close'].values
    n = len(df)
    sar = np.zeros(n)
    bull = close[1] >= close[0]
    af = step
    ep = high[0] if bull else low[0]
    sar[0] = low[0] if bull else high[0]
    for i in range(1, n):
        prev_sar = sar[i-1]
        if bull:
            sar[i] = prev_sar + af * (ep - prev_sar)
            sar[i] = min(sar[i], low[i-1], low[i-2] if i >= 2 else low[i-1])
            if low[i] < sar[i]:
                bull = False
                sar[i] = ep
                ep = low[i]
                af = step
            else:
                if high[i] > ep:
                    ep = high[i]
                    af = min(af + step, max_step)
        else:
            sar[i] = prev_sar + af * (ep - prev_sar)
            sar[i] = max(sar[i], high[i-1], high[i-2] if i >= 2 else high[i-1])
            if high[i] > sar[i]:
                bull = True
                sar[i] = ep
                ep = high[i]
                af = step
            else:
                if low[i] < ep:
                    ep = low[i]
                    af = min(af + step, max_step)
    return round(float(sar[-1]), 2)




def calculate_pdh_pdl(df: pd.DataFrame) -> dict:
    """
    Computes Previous Day High (PDH), Previous Day Low (PDL), and Previous Day Close (PDC).
    Key institutional intraday reference levels.
    """
    if df is None or df.empty:
        return {"pdh": 22600.0, "pdl": 22400.0, "pdc": 22500.0}
    try:
        # Determine day boundaries
        idx = pd.to_datetime(df.index)
        days = idx.normalize().unique()
        if len(days) >= 2:
            prev_day = days[-2]
            p_df = df[idx.normalize() == prev_day]
            if not p_df.empty:
                return {
                    "pdh": round(float(p_df['high'].max()), 2),
                    "pdl": round(float(p_df['low'].min()), 2),
                    "pdc": round(float(p_df['close'].iloc[-1]), 2)
                }
        return {
            "pdh": round(float(df['high'].max()), 2),
            "pdl": round(float(df['low'].min()), 2),
            "pdc": round(float(df['close'].iloc[-1]), 2)
        }
    except Exception:
        return {"pdh": 0.0, "pdl": 0.0, "pdc": 0.0}


def calculate_orb(df: pd.DataFrame, minutes: int = 15) -> dict:
    """
    Computes Opening Range Breakout (ORB 15m / 30m) High and Low (09:15 to 09:30 IST).
    """
    if df is None or df.empty:
        return {"orb_high": 0.0, "orb_low": 0.0, "status": "UNKNOWN"}
    try:
        idx = pd.to_datetime(df.index)
        today = idx.normalize().unique()[-1]
        today_df = df[idx.normalize() == today]
        if today_df.empty:
            today_df = df
        
        # 09:15 to 09:30
        orb_bars = today_df[(today_df.index.time >= pd.to_datetime('09:15').time()) & (today_df.index.time <= pd.to_datetime('09:30').time())]
        if not orb_bars.empty:
            orb_high = round(float(orb_bars['high'].max()), 2)
            orb_low = round(float(orb_bars['low'].min()), 2)
            cur_close = float(today_df['close'].iloc[-1])
            status = "BULLISH_BREAKOUT" if cur_close > orb_high else ("BEARISH_BREAKDOWN" if cur_close < orb_low else "INSIDE_RANGE")
            return {"orb_high": orb_high, "orb_low": orb_low, "status": status}
        return {"orb_high": round(float(today_df['high'].iloc[0]), 2), "orb_low": round(float(today_df['low'].iloc[0]), 2), "status": "INITIALIZING"}
    except Exception:
        return {"orb_high": 0.0, "orb_low": 0.0, "status": "UNKNOWN"}


def calculate_bollinger_pct_b(series: pd.Series, period: int = 20, num_std: float = 2.0) -> pd.Series:
    """Computes Bollinger %B oscillator: (Price - Lower) / (Upper - Lower)."""
    if series is None or len(series) < period:
        return pd.Series([0.5] * (len(series) if series is not None else 0))
    sma = series.rolling(period).mean()
    std = series.rolling(period).std(ddof=0)
    upper = sma + (num_std * std)
    lower = sma - (num_std * std)
    pct_b = (series - lower) / np.maximum(upper - lower, 1e-9)
    return pct_b


def calculate_keltner_channels(df: pd.DataFrame, ema_period: int = 20, atr_period: int = 10, mult: float = 2.0):
    """Computes Keltner Channels (EMA 20 ± 2 * ATR 10)."""
    if df is None or len(df) < max(ema_period, atr_period):
        return None, None, None
    close = df['close']
    ema = close.ewm(span=ema_period, adjust=False).mean()
    atr = calculate_atr(df, atr_period)
    upper = ema + (mult * atr)
    lower = ema - (mult * atr)
    return upper, ema, lower


def calculate_donchian_channels(df: pd.DataFrame, period: int = 20):
    """Computes Donchian Channels (20-period Highest High and Lowest Low)."""
    if df is None or len(df) < period:
        return None, None, None
    upper = df['high'].rolling(period).max()
    lower = df['low'].rolling(period).min()
    mid = (upper + lower) / 2.0
    return upper, mid, lower


def calculate_volume_profile(df: pd.DataFrame, num_bins: int = 40) -> dict:
    """
    Computes Session Volume Profile:
    - POC (Point of Control / Maximum Traded Volume Price)
    - VAH (Value Area High - 70% Volume Boundary)
    - VAL (Value Area Low - 70% Volume Boundary)
    """
    if df is None or df.empty or len(df) < 5:
        return {"poc": 22500.0, "vah": 22550.0, "val": 22450.0}
    try:
        p_min = float(df['low'].min())
        p_max = float(df['high'].max())
        if p_max <= p_min:
            return {"poc": p_min, "vah": p_min, "val": p_min}
        bins = np.linspace(p_min, p_max, num_bins)
        vols = np.zeros(num_bins - 1)
        for _, row in df.iterrows():
            c = float(row['close'])
            v = float(row.get('volume', 1.0))
            b = np.digitize(c, bins) - 1
            if 0 <= b < len(vols):
                vols[b] += v
        poc_idx = int(np.argmax(vols))
        poc = (bins[poc_idx] + bins[poc_idx + 1]) / 2.0
        tot_vol = vols.sum()
        target_70 = tot_vol * 0.70
        cum = float(vols[poc_idx])
        l_idx = poc_idx
        h_idx = poc_idx
        while cum < target_70 and (l_idx > 0 or h_idx < len(vols) - 1):
            next_l = vols[l_idx - 1] if l_idx > 0 else 0
            next_h = vols[h_idx + 1] if h_idx < len(vols) - 1 else 0
            if next_l >= next_h and l_idx > 0:
                l_idx -= 1
                cum += next_l
            elif h_idx < len(vols) - 1:
                h_idx += 1
                cum += next_h
            else:
                if l_idx > 0:
                    l_idx -= 1
                    cum += next_l
                else:
                    break
        vah = float(bins[h_idx + 1])
        val = float(bins[l_idx])
        return {"poc": round(float(poc), 2), "vah": round(vah, 2), "val": round(val, 2)}
    except Exception:
        return {"poc": 0.0, "vah": 0.0, "val": 0.0}


def calculate_anchored_vwap(df: pd.DataFrame, anchor_timestamp=None) -> pd.Series:
    """Computes Anchored VWAP starting from a specific event or swing anchor."""
    if df is None or df.empty:
        return pd.Series(dtype=float)
    if anchor_timestamp is None:
        return calculate_session_vwap_with_bands(df)['vwap']
    mask = pd.to_datetime(df.index) >= pd.to_datetime(anchor_timestamp)
    sub = df[mask].copy()
    if sub.empty:
        return pd.Series([float(df['close'].iloc[-1])] * len(df), index=df.index)
    pv = (sub['close'] * sub['volume']).cumsum()
    v = sub['volume'].cumsum()
    avwap = pv / np.maximum(v, 1e-9)
    return avwap.reindex(df.index).ffill()

def evaluate_market_indicators(
    df: pd.DataFrame,
    current_price: float,
    comb_sr: list = None,
    custom_indicators: list = None
) -> dict:
    """
    Performs comprehensive technical evaluation of all indicators, parameters,
    EMA health, VWAP bias, volume conviction, and expected reversal timing.
    Feeds high-precision quantitative intelligence into Copilot RAG.
    """
    if df is None or df.empty or len(df) < 5:
        return {}

    close = df["close"]
    cur_p = round(float(current_price if current_price else close.iloc[-1]), 2)
    last_row = df.iloc[-1]

    # 1. VWAP & ±2σ Exhaustion Bands Evaluation
    vwap_val = round(float(last_row.get("vwap", 0.0)), 2) if pd.notnull(last_row.get("vwap")) else None
    u2_val = round(float(last_row.get("vwap_upper_2", 0.0)), 2) if pd.notnull(last_row.get("vwap_upper_2")) else None
    l2_val = round(float(last_row.get("vwap_lower_2", 0.0)), 2) if pd.notnull(last_row.get("vwap_lower_2")) else None
    
    vwap_bias = "NEUTRAL"
    vwap_dist_pts = 0.0
    vwap_dist_pct = 0.0
    if vwap_val is not None:
        vwap_dist_pts = round(cur_p - vwap_val, 2)
        vwap_dist_pct = round((vwap_dist_pts / vwap_val) * 100, 2)
        vwap_bias = "BULLISH" if vwap_dist_pts > 0 else "BEARISH"

    vwap_exhaustion = "NORMAL_RUNWAY"
    dist_to_u2 = round(u2_val - cur_p, 2) if u2_val else 999.0
    dist_to_l2 = round(cur_p - l2_val, 2) if l2_val else 999.0
    if u2_val and dist_to_u2 <= 20.0:
        vwap_exhaustion = "APPROACHING_+2σ_EXHAUSTION_BAND (Overbought Reversal Watch)"
    elif l2_val and dist_to_l2 <= 20.0:
        vwap_exhaustion = "APPROACHING_-2σ_EXHAUSTION_BAND (Oversold Reversal Watch)"

    # 2. Multi-Period Moving Averages (EMA 9, 20, 50, 200, SMA 20)
    ema9_series = calculate_ema(close, 9)
    ema20_series = calculate_ema(close, 20)
    ema50_series = calculate_ema(close, 50)
    ema200_series = calculate_ema(close, 200) if len(close) >= 200 else pd.Series([None] * len(close), index=close.index)

    e9 = round(float(ema9_series.iloc[-1]), 2)
    e20 = round(float(ema20_series.iloc[-1]), 2)
    e50 = round(float(ema50_series.iloc[-1]), 2)
    e200 = round(float(ema200_series.iloc[-1]), 2) if pd.notnull(ema200_series.iloc[-1]) else None
    sma20 = round(float(last_row.get("mean", e20)), 2) if pd.notnull(last_row.get("mean")) else e20

    # EMA Alignment & Quality Assessment
    ema_slope_20 = round(float(ema20_series.iloc[-1] - ema20_series.iloc[-3]) / 2.0, 2) if len(ema20_series) >= 3 else 0.0
    is_bullish_stack = (e9 > e20 > e50)
    is_bearish_stack = (e9 < e20 < e50)

    if cur_p >= e20 and is_bullish_stack:
        ema_quality = "EXCELLENT_BULLISH (Holding cleanly above EMA 20 support with bullish EMA 9/20/50 stack)"
    elif cur_p < e20 and cur_p >= e50 and is_bullish_stack:
        ema_quality = "HEALTHY_PULLBACK (Retracing toward EMA 50 support in an overall uptrend)"
    elif cur_p < e50 and is_bearish_stack:
        ema_quality = "STRONG_BEARISH (Trading below EMA 20 & 50 with bearish slope)"
    else:
        ema_quality = "MIXED_CONSOLIDATION (Moving averages compressing / crossing)"

    # 3. Oscillators: RSI (14) & MACD (12, 26, 9)
    rsi_series = calculate_rsi(close, 14)
    rsi_val = round(float(rsi_series.iloc[-1]), 2) if len(rsi_series) > 0 and pd.notnull(rsi_series.iloc[-1]) else 50.0

    if rsi_val >= 70.0:
        rsi_status = "OVERBOUGHT (>= 70, watch for divergence or wick rejection)"
    elif rsi_val <= 30.0:
        rsi_status = "OVERSOLD (<= 30, watch for trap reversal / liquidity sweep)"
    elif rsi_val >= 55.0:
        rsi_status = "BULLISH_EXPANSION (55-70, solid buying momentum)"
    elif rsi_val <= 45.0:
        rsi_status = "BEARISH_EXPANSION (30-45, selling momentum active)"
    else:
        rsi_status = "NEUTRAL (45-55, rangebound chop)"

    macd_line, macd_sig, macd_hist = calculate_macd(close, 12, 26, 9)
    m_line = round(float(macd_line.iloc[-1]), 2) if pd.notnull(macd_line.iloc[-1]) else 0.0
    m_sig = round(float(macd_sig.iloc[-1]), 2) if pd.notnull(macd_sig.iloc[-1]) else 0.0
    m_h = round(float(macd_hist.iloc[-1]), 2) if pd.notnull(macd_hist.iloc[-1]) else 0.0

    if m_h > 0 and m_line > m_sig:
        macd_status = "BULLISH_EXPANSION (Histogram expanding positive)"
    elif m_h < 0 and m_line < m_sig:
        macd_status = "BEARISH_EXPANSION (Histogram expanding negative)"
    else:
        macd_status = "MOMENTUM_CONTRACTING (Histogram narrowing near zero-line)"

    # 4. Volatility (ATR 14) & Bollinger Bands
    atr_series = calculate_atr(df, 14)
    atr_val = round(float(atr_series.iloc[-1]), 2) if pd.notnull(atr_series.iloc[-1]) else 20.0

    bb_u, bb_m, bb_l = calculate_bollinger_bands(close, 20, 2.0)
    bb_upper = round(float(bb_u.iloc[-1]), 2) if pd.notnull(bb_u.iloc[-1]) else None
    bb_lower = round(float(bb_l.iloc[-1]), 2) if pd.notnull(bb_l.iloc[-1]) else None

    # 4b. Additional Institutional Indicators (PDH/PDL, ORB, Keltner, Donchian, Volume Profile, %B)
    pdh_pdl = calculate_pdh_pdl(df)
    orb = calculate_orb(df)
    pct_b_series = calculate_bollinger_pct_b(close)
    pct_b_val = round(float(pct_b_series.iloc[-1]), 2) if len(pct_b_series) > 0 and pd.notnull(pct_b_series.iloc[-1]) else 0.5
    kc_u, kc_m, kc_l = calculate_keltner_channels(df)
    kc_upper = round(float(kc_u.iloc[-1]), 2) if kc_u is not None and pd.notnull(kc_u.iloc[-1]) else None
    kc_lower = round(float(kc_l.iloc[-1]), 2) if kc_l is not None and pd.notnull(kc_l.iloc[-1]) else None
    dc_u, dc_m, dc_l = calculate_donchian_channels(df)
    dc_upper = round(float(dc_u.iloc[-1]), 2) if dc_u is not None and pd.notnull(dc_u.iloc[-1]) else None
    dc_lower = round(float(dc_l.iloc[-1]), 2) if dc_l is not None and pd.notnull(dc_l.iloc[-1]) else None
    vol_profile = calculate_volume_profile(df)

    # 5. Volume Analytics (Top 50 Constituent Aggregate)
    cur_vol = float(last_row.get("volume", 0.0))
    vol_ma = float(last_row.get("volume_ma_20", 0.0))
    vol_ratio = round(cur_vol / vol_ma, 2) if vol_ma > 0 else 1.0
    if vol_ratio >= 1.5:
        vol_status = f"HIGH_INSTITUTIONAL_CONVICTION ({vol_ratio}x 20-period avg volume)"
    elif vol_ratio >= 0.8:
        vol_status = f"NORMAL_HEALTHY_VOLUME ({vol_ratio}x avg)"
    else:
        vol_status = f"LOW_VOLUME_CONSOLIDATION ({vol_ratio}x avg)"

    # 6. Reversal Trend Start Analysis
    reversal_triggers = []
    reversal_risk = "LOW"

    if u2_val and cur_p >= (u2_val - 25.0):
        reversal_triggers.append(f"Price is within {dist_to_u2} pts of Upper +2σ Exhaustion Band (₹{u2_val}).")
        reversal_risk = "HIGH" if dist_to_u2 <= 8.0 else "MODERATE"
    elif l2_val and cur_p <= (l2_val + 25.0):
        reversal_triggers.append(f"Price is within {dist_to_l2} pts of Lower -2σ Exhaustion Band (₹{l2_val}).")
        reversal_risk = "HIGH" if dist_to_l2 <= 8.0 else "MODERATE"

    if rsi_val >= 68.0:
        reversal_triggers.append(f"RSI is stretched at {rsi_val} (near overbought threshold 70).")
    elif rsi_val <= 32.0:
        reversal_triggers.append(f"RSI is oversold at {rsi_val} (near oversold threshold 30).")

    # Check recent candle wick rejection
    last_candle_body = abs(float(last_row["close"]) - float(last_row["open"]))
    last_candle_range = max(float(last_row["high"]) - float(last_row["low"]), 1e-4)
    upper_wick = float(last_row["high"]) - max(float(last_row["close"]), float(last_row["open"]))
    lower_wick = min(float(last_row["close"]), float(last_row["open"])) - float(last_row["low"])
    upper_wick_pct = round((upper_wick / last_candle_range) * 100, 1)
    lower_wick_pct = round((lower_wick / last_candle_range) * 100, 1)

    if upper_wick_pct >= 40.0:
        reversal_triggers.append(f"Recent bar formed a {upper_wick_pct}% upper rejection wick, showing overhead selling pressure.")
        if reversal_risk == "LOW": reversal_risk = "MODERATE"
    elif lower_wick_pct >= 40.0:
        reversal_triggers.append(f"Recent bar formed a {lower_wick_pct}% lower absorption wick, showing dip buying support.")
        if reversal_risk == "LOW": reversal_risk = "MODERATE"

    # Nearest S&R level for reversal interaction
    nearest_sr = None
    if comb_sr:
        for s in comb_sr:
            p = float(s.get("avg_price", s.get("price1", 0.0)))
            if abs(p - cur_p) <= 30.0:
                nearest_sr = {"role": s.get("role", "S&R"), "price": p, "bounces": s.get("bounces", 4)}
                reversal_triggers.append(f"Testing active {nearest_sr['role']} level at ₹{p} ({nearest_sr['bounces']} historical touches).")
                break

    if reversal_risk == "HIGH":
        expected_reversal_text = (
            f"REVERSAL WATCH: HIGH PROBABILITY. Price is testing key exhaustion threshold ({', '.join(reversal_triggers)}). "
            f"A trend reversal is expected to confirm once a 5-minute candle closes back with an opposite directional body "
            f"and MACD histogram rolls over."
        )
    elif reversal_risk == "MODERATE":
        expected_reversal_text = (
            f"REVERSAL WATCH: MODERATE. Current momentum is extended ({', '.join(reversal_triggers)}). "
            f"Watch for a failure swing or 2-candle rejection pattern before anticipating a full trend flip."
        )
    else:
        expected_reversal_text = (
            f"REVERSAL WATCH: LOW. The prevailing trend structure remains intact with solid EMA 20 slope and healthy VWAP gap. "
            f"No structural reversal is expected until price breaks decisively through EMA 20 (₹{e20}) or tests ±2σ bands."
        )

    # 7. Evaluate Custom Indicators if provided
    custom_eval = []
    if custom_indicators:
        for c in custom_indicators:
            ctype = c.get("type", "ema")
            clen = int(c.get("length", c.get("period", 20)))
            col = c.get("color", "#38bdf8")
            if ctype == "ema":
                c_val = round(float(calculate_ema(close, clen).iloc[-1]), 2)
                custom_eval.append({
                    "id": c.get("id"),
                    "name": f"EMA {clen}",
                    "value": c_val,
                    "price_vs_ind": "ABOVE" if cur_p >= c_val else "BELOW",
                    "color": col
                })
            elif ctype == "sma":
                c_val = round(float(calculate_sma(close, clen).iloc[-1]), 2)
                custom_eval.append({
                    "id": c.get("id"),
                    "name": f"SMA {clen}",
                    "value": c_val,
                    "price_vs_ind": "ABOVE" if cur_p >= c_val else "BELOW",
                    "color": col
                })

    # 8. Compute Extended Indicators: Supertrend, ADX, CPR, Stoch RSI, Parabolic SAR
    st_val, st_dir = calculate_supertrend(df, 10, 3.0)
    adx_val, p_di_val, m_di_val = calculate_adx(df, 14)
    pivot_val, tc_val, bc_val, cpr_type = calculate_cpr(df)
    sar_val = calculate_parabolic_sar(df, 0.02, 0.2)
    stoch_k, stoch_d = calculate_stoch_rsi(close, 14, 3, 3)

    # 9. Institutional Indicator Directional Scoreboard (CALL / PUT / NEUTRAL Evaluation Matrix)
    # Evaluates every single indicator with live numerical values and objective trading signal
    scoreboard_list = [
        {
            "name": "Session VWAP",
            "value": f"₹{vwap_val:,.1f}" if vwap_val else "--",
            "signal": "CALL" if vwap_bias == "BULLISH" else ("PUT" if vwap_bias == "BEARISH" else "NEUTRAL"),
            "detail": f"Price is {vwap_dist_pts:+.1f} pts ({vwap_dist_pct:+.2f}%) vs Session VWAP",
        },
        {
            "name": "VWAP ±2σ Bands",
            "value": f"+2σ: ₹{u2_val:,.1f} / -2σ: ₹{l2_val:,.1f}" if (u2_val and l2_val) else "--",
            "signal": "PUT" if "APPROACHING_+2" in vwap_exhaustion else ("CALL" if "APPROACHING_-2" in vwap_exhaustion else "NEUTRAL"),
            "detail": vwap_exhaustion,
        },
        {
            "name": "EMA Ribbon (9/20/50)",
            "value": f"EMA20: ₹{e20:,.1f} | EMA50: ₹{e50:,.1f}",
            "signal": "CALL" if is_bullish_stack and cur_p >= e20 else ("PUT" if is_bearish_stack and cur_p < e20 else "NEUTRAL"),
            "detail": ema_quality,
        },
        {
            "name": "Supertrend (10, 3.0)",
            "value": f"₹{st_val:,.1f}",
            "signal": "CALL" if st_dir == 1 else "PUT",
            "detail": f"Trailing {'Support' if st_dir == 1 else 'Resistance'} at ₹{st_val:,.1f}",
        },
        {
            "name": "RSI (14)",
            "value": f"{rsi_val:.1f}",
            "signal": "CALL" if (55.0 <= rsi_val < 70.0 or rsi_val <= 30.0) else ("PUT" if (30.0 < rsi_val <= 45.0 or rsi_val >= 70.0) else "NEUTRAL"),
            "detail": rsi_status,
        },
        {
            "name": "MACD (12, 26, 9)",
            "value": f"Hist: {m_h:+.2f} (Line: {m_line:.2f})",
            "signal": "CALL" if m_h > 0 and m_line > m_sig else ("PUT" if m_h < 0 and m_line < m_sig else "NEUTRAL"),
            "detail": macd_status,
        },
        {
            "name": "Stochastic RSI (14, 3, 3)",
            "value": f"%K: {stoch_k:.1f} | %D: {stoch_d:.1f}",
            "signal": "CALL" if stoch_k > stoch_d and stoch_k < 80 else ("PUT" if stoch_k < stoch_d and stoch_k > 20 else "NEUTRAL"),
            "detail": "Bullish Crossover" if stoch_k > stoch_d else "Bearish Crossover",
        },
        {
            "name": "Bollinger Bands (20, 2.0)",
            "value": f"Upper: ₹{bb_upper:,.1f} | Lower: ₹{bb_lower:,.1f}" if (bb_upper and bb_lower) else "--",
            "signal": "PUT" if (bb_upper and cur_p >= (bb_upper - 10)) else ("CALL" if (bb_lower and cur_p <= (bb_lower + 10)) else "NEUTRAL"),
            "detail": "At Upper Band" if (bb_upper and cur_p >= (bb_upper - 10)) else ("At Lower Band" if (bb_lower and cur_p <= (bb_lower + 10)) else "Consolidating Inside Envelope"),
        },
        {
            "name": "ADX Trend Strength (14)",
            "value": f"ADX: {adx_val:.1f} (+DI: {p_di_val:.1f}, -DI: {m_di_val:.1f})",
            "signal": "CALL" if (adx_val >= 20 and p_di_val > m_di_val) else ("PUT" if (adx_val >= 20 and m_di_val > p_di_val) else "NEUTRAL"),
            "detail": f"{'Strong Trend' if adx_val >= 25 else 'Moderate Trend'} (+DI {p_di_val} vs -DI {m_di_val})",
        },
        {
            "name": "Central Pivot Range (CPR)",
            "value": f"Pivot: ₹{pivot_val:,.1f} (TC: ₹{tc_val:,.1f}, BC: ₹{bc_val:,.1f})",
            "signal": "CALL" if cur_p >= tc_val else ("PUT" if cur_p <= bc_val else "NEUTRAL"),
            "detail": f"{'Above TC (Bullish)' if cur_p >= tc_val else ('Below BC (Bearish)' if cur_p <= bc_val else 'Inside CPR Range')} [{cpr_type}]",
        },
        {
            "name": "Parabolic SAR (0.02, 0.2)",
            "value": f"₹{sar_val:,.1f}",
            "signal": "CALL" if cur_p >= sar_val else "PUT",
            "detail": f"Dots {'Below Price (Bullish Trend)' if cur_p >= sar_val else 'Above Price (Bearish Trend)'}",
        },
        {
            "name": "Volume (Top-50 Constituent)",
            "value": f"{vol_ratio:.1f}x 20MA ({cur_vol:,.0f})",
            "signal": "CALL" if (vol_ratio >= 1.2 and cur_p >= float(last_row.get('open', cur_p))) else ("PUT" if (vol_ratio >= 1.2 and cur_p < float(last_row.get('open', cur_p))) else "NEUTRAL"),
            "detail": vol_status,
        },
    ]

    total_call = sum(1 for item in scoreboard_list if item["signal"] == "CALL")
    total_put = sum(1 for item in scoreboard_list if item["signal"] == "PUT")
    total_neutral = sum(1 for item in scoreboard_list if item["signal"] == "NEUTRAL")
    total_active = len(scoreboard_list)
    confluence_pct = round((max(total_call, total_put) / total_active) * 100.0, 1) if total_active > 0 else 50.0

    if total_call > total_put and total_call >= 5:
        overall_consensus = f"CALL (BULLISH CONFLUENCE {confluence_pct}%)"
    elif total_put > total_call and total_put >= 5:
        overall_consensus = f"PUT (BEARISH CONFLUENCE {confluence_pct}%)"
    else:
        overall_consensus = f"NEUTRAL / MIXED ({total_call} Call vs {total_put} Put)"

    return {
        "current_price": cur_p,
        "scoreboard": {
            "total_call": total_call,
            "total_put": total_put,
            "total_neutral": total_neutral,
            "total_indicators": total_active,
            "consensus": overall_consensus,
            "confluence_pct": confluence_pct,
            "indicators": scoreboard_list,
        },
        "vwap": {
            "value": vwap_val,
            "upper_2": u2_val,
            "lower_2": l2_val,
            "bias": vwap_bias,
            "dist_pts": vwap_dist_pts,
            "dist_pct": vwap_dist_pct,
            "exhaustion_status": vwap_exhaustion
        },
        "ema": {
            "ema_9": e9,
            "ema_20": e20,
            "ema_50": e50,
            "ema_200": e200,
            "sma_20": sma20,
            "slope_20": ema_slope_20,
            "alignment": "BULLISH_STACK" if is_bullish_stack else ("BEARISH_STACK" if is_bearish_stack else "MIXED"),
            "quality": ema_quality,
            "price_above_ema20": (cur_p >= e20)
        },
        "supertrend": {
            "value": st_val,
            "direction": st_dir,
            "signal": "CALL" if st_dir == 1 else "PUT"
        },
        "cpr": {
            "pivot": pivot_val,
            "tc": tc_val,
            "bc": bc_val,
            "type": cpr_type,
            "signal": "CALL" if cur_p >= tc_val else ("PUT" if cur_p <= bc_val else "NEUTRAL")
        },
        "adx": {
            "adx": adx_val,
            "plus_di": p_di_val,
            "minus_di": m_di_val,
            "signal": "CALL" if (adx_val >= 20 and p_di_val > m_di_val) else ("PUT" if (adx_val >= 20 and m_di_val > p_di_val) else "NEUTRAL")
        },
        "sar": {
            "value": sar_val,
            "signal": "CALL" if cur_p >= sar_val else "PUT"
        },
        "stoch_rsi": {
            "k": stoch_k,
            "d": stoch_d,
            "signal": "CALL" if stoch_k > stoch_d and stoch_k < 80 else ("PUT" if stoch_k < stoch_d and stoch_k > 20 else "NEUTRAL")
        },
        "key_levels": {
            "pdh": pdh_pdl.get("pdh"),
            "pdl": pdh_pdl.get("pdl"),
            "pdc": pdh_pdl.get("pdc"),
            "orb_15m": orb,
            "volume_profile": vol_profile,
        },
        "channels": {
            "keltner_upper": kc_upper,
            "keltner_lower": kc_lower,
            "donchian_upper": dc_upper,
            "donchian_lower": dc_lower,
            "bollinger_pct_b": pct_b_val
        },
        "oscillators": {
            "rsi_14": rsi_val,
            "rsi_status": rsi_status,
            "macd_line": m_line,
            "macd_signal": m_sig,
            "macd_hist": m_h,
            "macd_status": macd_status,
            "atr_14": atr_val,
            "bb_upper": bb_upper,
            "bb_lower": bb_lower
        },
        "volume": {
            "current_volume": cur_vol,
            "volume_ma_20": vol_ma,
            "volume_ratio": vol_ratio,
            "status": vol_status
        },
        "reversal": {
            "risk_level": reversal_risk,
            "triggers": reversal_triggers,
            "expected_reversal_analysis": expected_reversal_text
        },
        "custom_indicators": custom_eval
    }
