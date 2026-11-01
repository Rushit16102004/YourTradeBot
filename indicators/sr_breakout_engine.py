"""
Support & Resistance Breakout & Breakdown Strategy Engine:

1. CALL Signal (Buy Call):
   - Candle 1 (Breakout): Closes strictly ABOVE a Strong Resistance level.
   - Candle 2 (Confirmation): Closes in the SAME direction without reversing back below the resistance.
   - Strong Level: Level has >= 4 bounces (or is a Rectangle Flip Zone >= 6x).
   - Runway / Distance Filter: The distance from the broken resistance to the NEXT resistance above it must be >= 50 points.
   - Repeating Text: 'S&R Signal: CALL-CALL-CALL-CALL-CALL...'

2. PUT Signal (Buy Put):
   - Candle 1 (Breakdown): Closes strictly BELOW a Strong Support level.
   - Candle 2 (Confirmation): Closes in the SAME direction without reversing back above the support.
   - Strong Level: Level has >= 4 bounces (or is a Rectangle Flip Zone >= 6x).
   - Runway / Distance Filter: The distance from the broken support to the NEXT support below it must be >= 50 points.
   - Repeating Text: 'S&R Signal: PUT-PUT-PUT-PUT-PUT...'

3. Delivery:
   - Telegram rich alert.
   - Real-time in-browser popup modal (with close button; stays on screen until dismissed).
   - Does NOT draw signal markers on the chart.
"""
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional, Tuple
import pytz
import pandas as pd

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")


def is_level_strong(level: Dict[str, Any], min_bounces: int = 5) -> bool:
    """
    Returns True if an S&R level is historically strong (> 5x touches):
    - Level must have strictly MORE THAN 5x touches (bounces > 5).
    """
    bounces = int(level.get("bounces", 0))
    return bounces > min_bounces


def find_next_resistance_above(price: float, levels: List[Dict[str, Any]]) -> Tuple[float, float]:
    """
    Finds the next resistance level strictly above `price`.
    Returns (next_resistance_price, gap_points).
    If no resistance exists above, returns open target (+100 pts).
    """
    higher = []
    for l in levels:
        if l.get("is_support", False):
            continue
        p = float(l.get("avg_price") or l.get("price1", 0.0))
        if p > price + 3.0:
            higher.append(p)

    if higher:
        next_res = min(higher)
        return next_res, round(next_res - price, 2)
    return round(price + 100.0, 2), 100.0


def find_next_support_below(price: float, levels: List[Dict[str, Any]]) -> Tuple[float, float]:
    """
    Finds the next support level strictly below `price`.
    Returns (next_support_price, gap_points).
    If no support exists below, returns open target (-100 pts).
    """
    lower = []
    for l in levels:
        if not l.get("is_support", True):
            continue
        p = float(l.get("avg_price") or l.get("price1", 0.0))
        if p < price - 3.0:
            lower.append(p)

    if lower:
        next_sup = max(lower)
        return next_sup, round(price - next_sup, 2)
    return round(price - 100.0, 2), 100.0


def evaluate_sr_breakout(
    df_5m: pd.DataFrame,
    sr_levels: List[Dict[str, Any]],
    min_runway_points: float = 50.0,
) -> Optional[Dict[str, Any]]:
    """
    Evaluates 5-minute candles against Strong S&R levels:
    - Requires 3 closed candles (c_base, c_breakout, c_confirm).
    - Checks 2-candle confirmation without reversal.
    - Requires next target distance >= 50 points.
    Returns signal metadata dictionary if confirmed, else None.
    """
    if df_5m is None or len(df_5m) < 3 or not sr_levels:
        return None

    c_base = df_5m.iloc[-3]
    c_breakout = df_5m.iloc[-2]
    c_confirm = df_5m.iloc[-1]

    close_base = float(c_base["close"])
    open_break = float(c_breakout["open"])
    close_break = float(c_breakout["close"])
    low_break = float(c_breakout["low"])
    high_break = float(c_breakout["high"])

    open_conf = float(c_confirm["open"])
    close_conf = float(c_confirm["close"])
    low_conf = float(c_confirm["low"])
    high_conf = float(c_confirm["high"])

    confirm_ts = df_5m.index[-1]
    time_str = confirm_ts.strftime("%d-%m-%Y %H:%M:%S IST") if hasattr(confirm_ts, "strftime") else str(confirm_ts)

    # Filter to only STRONG S&R levels
    strong_levels = [l for l in sr_levels if is_level_strong(l)]
    if not strong_levels:
        return None

    # ----------------------------------------------------
    # 1. Check CALL Signal (Bullish Strong Resistance Breakout)
    # ----------------------------------------------------
    resistances = [l for l in strong_levels if not l.get("is_support", False)]
    for r_lvl in resistances:
        r_price = float(r_lvl.get("avg_price") or r_lvl.get("price1", 0.0))
        bounces = int(r_lvl.get("bounces", 0))
        if bounces <= 5:
            continue

        # Candle 1: Closes above resistance (was previously below or testing it)
        breakout_ok = (close_break > r_price) and (close_base <= r_price + 1.5 or open_break <= r_price + 1.5)

        # Candle 2 (Confirmation): Closes in same upward direction, not reversing back below resistance
        confirm_ok = (close_conf >= close_break - 2.0) and (low_conf >= r_price - 3.5) and (close_conf > r_price)

        if breakout_ok and confirm_ok:
            # Check Next Resistance Runway >= 50 points
            next_res, gap_pts = find_next_resistance_above(r_price, sr_levels)
            if gap_pts >= min_runway_points:
                alert_id = f"SR_CALL_{int(r_price)}_{confirm_ts}"
                return {
                    "id": alert_id,
                    "category": "S&R",
                    "sub_type": "BREAKOUT",
                    "type": "CALL",
                    "action": "BUY CALL",
                    "repeating_text": "CALL-CALL-CALL-CALL-CALL-CALL-CALL",
                    "title": "S&R SIGNAL: CALL-CALL-CALL-CALL-CALL",
                    "price": round(close_conf, 2),
                    "broken_level": round(r_price, 2),
                    "broken_bounces": bounces,
                    "target_level": round(next_res, 2),
                    "gap_pts": round(gap_pts, 2),
                    "time_str": time_str,
                    "timestamp": confirm_ts,
                    "role": r_lvl.get("role", "Resistance"),
                    "timeframe_tag": r_lvl.get("timeframe_tag", "1M + 2M Confluence"),
                    "is_confluence": r_lvl.get("is_confluence", False),
                    "origin": r_lvl.get("origin", "1M + 2M Confluence"),
                }

    # ----------------------------------------------------
    # 2. Check PUT Signal (Bearish Strong Support Breakdown)
    # ----------------------------------------------------
    supports = [l for l in strong_levels if l.get("is_support", True)]
    for s_lvl in supports:
        s_price = float(s_lvl.get("avg_price") or s_lvl.get("price1", 0.0))
        bounces = int(s_lvl.get("bounces", 0))
        if bounces <= 5:
            continue

        # Candle 1: Closes below support (was previously above or testing it)
        breakdown_ok = (close_break < s_price) and (close_base >= s_price - 1.5 or open_break >= s_price - 1.5)

        # Candle 2 (Confirmation): Closes in same downward direction, not reversing back above support
        confirm_ok = (close_conf <= close_break + 2.0) and (high_conf <= s_price + 3.5) and (close_conf < s_price)

        if breakdown_ok and confirm_ok:
            # Check Next Support Runway >= 50 points
            next_sup, gap_pts = find_next_support_below(s_price, sr_levels)
            if gap_pts >= min_runway_points:
                alert_id = f"SR_PUT_{int(s_price)}_{confirm_ts}"
                return {
                    "id": alert_id,
                    "category": "S&R",
                    "sub_type": "BREAKOUT",
                    "type": "PUT",
                    "action": "BUY PUT",
                    "repeating_text": "PUT-PUT-PUT-PUT-PUT-PUT-PUT",
                    "title": "S&R SIGNAL: PUT-PUT-PUT-PUT-PUT",
                    "price": round(close_conf, 2),
                    "broken_level": round(s_price, 2),
                    "broken_bounces": bounces,
                    "target_level": round(next_sup, 2),
                    "gap_pts": round(gap_pts, 2),
                    "time_str": time_str,
                    "timestamp": confirm_ts,
                    "role": s_lvl.get("role", "Support"),
                    "timeframe_tag": s_lvl.get("timeframe_tag", "1M + 2M Confluence"),
                    "is_confluence": s_lvl.get("is_confluence", False),
                    "origin": s_lvl.get("origin", "1M + 2M Confluence"),
                }

    return None


def evaluate_sr_reversal(
    df_5m: pd.DataFrame,
    sr_levels: List[Dict[str, Any]],
    min_runway_points: float = 50.0,
    min_wick_ratio: float = 0.40,
) -> Optional[Dict[str, Any]]:
    """
    Evaluates 5-minute candles against Strong S&R levels for Institutional Traps / Liquidity Sweeps
    with strict 2-candle confirmation:
    1. Bull Trap (Reversal to PUT):
       - Candle 1 (Sweep/Trap): High breaches Strong Resistance (liquidity sweep), body closes back below,
         upper rejection wick is >= 40% of total candle range.
       - Candle 2 (Confirmation): Confirms downward reversal without invalidating trap high or breaking back above resistance.
       - Next Support runway gap >= 50 points.
    2. Bear Trap (Reversal to CALL):
       - Candle 1 (Sweep/Trap): Low breaches Strong Support (stop run), body closes back above,
         lower rejection wick is >= 40% of total candle range.
       - Candle 2 (Confirmation): Confirms upward reversal without invalidating trap low or breaking back below support.
       - Next Resistance runway gap >= 50 points.
    """
    if df_5m is None or len(df_5m) < 2 or not sr_levels:
        return None

    # Use Candle 1 as Trap and Candle 2 as Confirmation
    c_trap = df_5m.iloc[-2]
    c_confirm = df_5m.iloc[-1]

    trap_open = float(c_trap["open"])
    trap_close = float(c_trap["close"])
    trap_high = float(c_trap["high"])
    trap_low = float(c_trap["low"])
    trap_range = trap_high - trap_low

    conf_open = float(c_confirm["open"])
    conf_close = float(c_confirm["close"])
    conf_high = float(c_confirm["high"])
    conf_low = float(c_confirm["low"])

    if trap_range <= 1.0:
        return None

    confirm_ts = df_5m.index[-1]
    time_str = confirm_ts.strftime("%d-%m-%Y %H:%M:%S IST") if hasattr(confirm_ts, "strftime") else str(confirm_ts)

    # Filter to only STRONG S&R levels (> 5x touches)
    strong_levels = [l for l in sr_levels if is_level_strong(l)]
    if not strong_levels:
        return None

    # 1. Bull Trap Check (Liquidity Sweep of Resistance -> Reversal BUY PUT)
    resistances = [l for l in strong_levels if not l.get("is_support", False)]
    for r_lvl in resistances:
        r_price = float(r_lvl.get("avg_price") or r_lvl.get("price1", 0.0))
        bounces = int(r_lvl.get("bounces", 0))
        if bounces <= 5:
            continue

        # Candle 1 (Trap): High pierced above resistance, close fell back below
        trap_ok = (trap_high >= r_price + 1.0) and (trap_close <= r_price)
        if trap_ok:
            upper_wick = trap_high - max(trap_open, trap_close)
            wick_ratio = upper_wick / trap_range

            if wick_ratio >= min_wick_ratio:
                # Candle 2 (Confirmation): Confirms downward move, doesn't break trap high, holds below resistance
                confirm_ok = (conf_close <= r_price) and (conf_high <= trap_high + 1.0) and (conf_close <= trap_close + 2.0)
                if confirm_ok:
                    next_sup, gap_pts = find_next_support_below(r_price, sr_levels)
                    if gap_pts >= min_runway_points:
                        alert_id = f"SR_TRAP_PUT_{int(r_price)}_{confirm_ts}"
                        return {
                            "id": alert_id,
                            "category": "S&R",
                            "sub_type": "REVERSAL",
                            "type": "PUT",
                            "action": "BUY PUT (Bull Trap Reversal)",
                            "repeating_text": "TRAP-PUT-TRAP-PUT-TRAP-PUT-TRAP-PUT",
                            "title": "🪤 S&R REVERSAL: BULL TRAP DETECTED",
                            "price": round(conf_close, 2),
                            "broken_level": round(r_price, 2),
                            "swept_level": round(r_price, 2),
                            "broken_bounces": bounces,
                            "target_level": round(next_sup, 2),
                            "gap_pts": round(gap_pts, 2),
                            "wick_pct": round(wick_ratio * 100, 1),
                            "time_str": time_str,
                            "timestamp": confirm_ts,
                            "role": r_lvl.get("role", "Resistance"),
                            "timeframe_tag": r_lvl.get("timeframe_tag", "1M + 2M Confluence"),
                            "is_confluence": r_lvl.get("is_confluence", False),
                            "origin": r_lvl.get("origin", "1M + 2M Confluence"),
                            "is_reversal": True,
                        }

    # 2. Bear Trap Check (Liquidity Sweep of Support -> Reversal BUY CALL)
    supports = [l for l in strong_levels if l.get("is_support", True)]
    for s_lvl in supports:
        s_price = float(s_lvl.get("avg_price") or s_lvl.get("price1", 0.0))
        bounces = int(s_lvl.get("bounces", 0))
        if bounces <= 5:
            continue

        # Candle 1 (Trap): Low pierced below support, close recovered back above
        trap_ok = (trap_low <= s_price - 1.0) and (trap_close >= s_price)
        if trap_ok:
            lower_wick = min(trap_open, trap_close) - trap_low
            wick_ratio = lower_wick / trap_range

            if wick_ratio >= min_wick_ratio:
                # Candle 2 (Confirmation): Confirms upward move, doesn't break trap low, holds above support
                confirm_ok = (conf_close >= s_price) and (conf_low >= trap_low - 1.0) and (conf_close >= trap_close - 2.0)
                if confirm_ok:
                    next_res, gap_pts = find_next_resistance_above(s_price, sr_levels)
                    if gap_pts >= min_runway_points:
                        alert_id = f"SR_TRAP_CALL_{int(s_price)}_{confirm_ts}"
                        return {
                            "id": alert_id,
                            "category": "S&R",
                            "sub_type": "REVERSAL",
                            "type": "CALL",
                            "action": "BUY CALL (Bear Trap Reversal)",
                            "repeating_text": "TRAP-CALL-TRAP-CALL-TRAP-CALL-TRAP-CALL",
                            "title": "🪤 S&R REVERSAL: BEAR TRAP DETECTED",
                            "price": round(conf_close, 2),
                            "broken_level": round(s_price, 2),
                            "swept_level": round(s_price, 2),
                            "broken_bounces": bounces,
                            "target_level": round(next_res, 2),
                            "gap_pts": round(gap_pts, 2),
                            "wick_pct": round(wick_ratio * 100, 1),
                            "time_str": time_str,
                            "timestamp": confirm_ts,
                            "role": s_lvl.get("role", "Support"),
                            "timeframe_tag": s_lvl.get("timeframe_tag", "1M + 2M Confluence"),
                            "is_confluence": s_lvl.get("is_confluence", False),
                            "origin": s_lvl.get("origin", "1M + 2M Confluence"),
                            "is_reversal": True,
                        }

    return None
