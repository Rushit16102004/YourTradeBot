"""
indicators/market_structure.py
LuxAlgo - Smart Money Concepts (SMC) Engine
Implemented in Python based on the official Pine Script v5 specification:
- Dual-Layer Structure: Real-Time Swing Structure & Real-Time Internal Structure
- Leg Scanner: high[size] > ta.highest(size) / low[size] < ta.lowest(size)
- Trend State Machine: True continuation (BOS) vs reversal (CHoCH) tracking
- Authentic Horizontal Segments: Line drawn strictly between Pivot candle and Breakout candle
- Centered Label Positioning: math.round(0.5 * (pivot_bar + breakout_bar))
- Colors: LuxAlgo Green (#089981) for Bullish, LuxAlgo Red (#F23645) for Bearish
- Additional SMC Analytics: Strong/Weak Highs & Lows, Equal Highs/Lows (EQH/EQL), and Order Blocks
- Multi-Timeframe Analysis: 5m, 15m, 1h, 1d independent calculation and RAG intelligence
"""

import math
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


def to_unix_seconds(val: Any) -> int:
    """Normalizes any timestamp (int, float, str, pd.Timestamp) to Unix seconds."""
    if val is None:
        return 0
    if isinstance(val, (int, float, np.integer, np.floating)):
        v = float(val)
        return int(v / 1000) if v > 1e11 else int(v)
    if isinstance(val, pd.Timestamp):
        return int(val.timestamp())
    try:
        dt = pd.to_datetime(val)
        return int(dt.timestamp())
    except Exception:
        return 0


class MarketStructureEngine:
    _instance: Optional["MarketStructureEngine"] = None

    @classmethod
    def get_instance(cls) -> "MarketStructureEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def calculate_luxalgo_smc(
        df: pd.DataFrame,
        swing_size: int = 50,
        internal_size: int = 5,
        timeframe: str = "5m"
    ) -> Dict[str, Any]:
        """
        Calculates authentic Smart Money Concepts according to the LuxAlgo Pine Script v5 logic:
        1. leg(size): Identifies swing extremes via directional high/low dominance.
        2. Internal Structure (size=5) for micro order flow (dashed lines).
        3. Swing Structure (size=50 or adaptive) for macro market shifts (solid lines).
        4. Trend State Machine: Bearish breaking high -> CHOCH; Bullish breaking high -> BOS.
        5. Strong / Weak High & Low trailing extremes.
        6. Equal Highs / Lows (EQH / EQL).
        """
        tf_clean = str(timeframe or "5m").lower()
        if df is None or len(df) < 15:
            return {
                "timeframe": tf_clean,
                "trend": "NEUTRAL",
                "internal_trend": "NEUTRAL",
                "last_event": None,
                "active_structures": [],
                "strong_weak_levels": {},
                "equal_highs_lows": [],
                "order_blocks": [],
                "key_levels": {},
                "summary": f"{tf_clean.upper()}: Insufficient candle data for LuxAlgo SMC."
            }

        # Adapt swing size if candle count is limited
        n = len(df)
        actual_swing_size = min(swing_size, max(12, n // 5))
        actual_internal_size = min(internal_size, max(3, actual_swing_size // 3))

        highs = df["high"].values.astype(float)
        lows = df["low"].values.astype(float)
        closes = df["close"].values.astype(float)
        raw_ts = df["timestamp"].values if "timestamp" in df.columns else df.index.values
        timestamps = [to_unix_seconds(t) for t in raw_ts]

        # Calculate standard ATR(14) for Equal Highs / Lows thresholding
        atr_14 = 20.0
        try:
            tr = np.maximum(
                highs[1:] - lows[1:],
                np.maximum(np.abs(highs[1:] - closes[:-1]), np.abs(lows[1:] - closes[:-1]))
            )
            if len(tr) >= 14:
                atr_14 = float(np.mean(tr[-14:]))
            elif len(tr) > 0:
                atr_14 = float(np.mean(tr))
        except Exception:
            atr_14 = 20.0

        all_structures: List[Dict[str, Any]] = []
        equal_highs_lows: List[Dict[str, Any]] = []
        order_blocks: List[Dict[str, Any]] = []

        # ====================================================================
        # RUN LAYER SCANNER (INTERNAL: size=5, SWING: size=50)
        # ====================================================================
        def process_layer(size: int, is_internal: bool):
            leg = 0  # 0 = BEARISH_LEG, 1 = BULLISH_LEG
            pivot_high = None  # Dict of {level, index, time, crossed}
            pivot_low = None   # Dict of {level, index, time, crossed}
            trend_bias = 0     # 1 = BULLISH, -1 = BEARISH, 0 = NEUTRAL
            layer_structures: List[Dict[str, Any]] = []

            # Trailing extremes for Strong / Weak levels (only for swing layer)
            trailing_top = float("-inf")
            trailing_top_time = 0
            trailing_bottom = float("inf")
            trailing_bottom_time = 0

            for i in range(size, n):
                sub_h = highs[i - size + 1 : i + 1]
                sub_l = lows[i - size + 1 : i + 1]
                candle_h = highs[i - size]
                candle_l = lows[i - size]
                candle_time = timestamps[i - size]

                new_leg_high = candle_h > np.max(sub_h)
                new_leg_low = candle_l < np.min(sub_l)

                last_leg = leg
                if new_leg_high:
                    leg = 0  # BEARISH_LEG
                elif new_leg_low:
                    leg = 1  # BULLISH_LEG

                # Start of New Leg (inflection)
                if leg != last_leg:
                    if leg == 1:  # startOfBullishLeg -> Previous candle was Swing Low
                        new_low_price = round(float(candle_l), 2)
                        # Check Equal Low (EQL)
                        if pivot_low is not None and not is_internal and atr_14 > 0:
                            if abs(pivot_low["price"] - new_low_price) < (0.15 * atr_14):
                                equal_highs_lows.append({
                                    "type": "EQL",
                                    "price": new_low_price,
                                    "time1": pivot_low["time"],
                                    "time2": candle_time,
                                    "timeframe": tf_clean,
                                    "label": "EQL"
                                })
                        pivot_low = {
                            "price": new_low_price,
                            "index": i - size,
                            "time": candle_time,
                            "crossed": False
                        }
                        if not is_internal:
                            trailing_bottom = new_low_price
                            trailing_bottom_time = candle_time

                    elif leg == 0:  # startOfBearishLeg -> Previous candle was Swing High
                        new_high_price = round(float(candle_h), 2)
                        # Check Equal High (EQH)
                        if pivot_high is not None and not is_internal and atr_14 > 0:
                            if abs(pivot_high["price"] - new_high_price) < (0.15 * atr_14):
                                equal_highs_lows.append({
                                    "type": "EQH",
                                    "price": new_high_price,
                                    "time1": pivot_high["time"],
                                    "time2": candle_time,
                                    "timeframe": tf_clean,
                                    "label": "EQH"
                                })
                        pivot_high = {
                            "price": new_high_price,
                            "index": i - size,
                            "time": candle_time,
                            "crossed": False
                        }
                        if not is_internal:
                            trailing_top = new_high_price
                            trailing_top_time = candle_time

                # Check Live Breakouts on Current Candle Close
                cur_close = closes[i]

                # 1. Bullish Breakout (Candle Close crosses ABOVE pivot_high)
                if pivot_high is not None and not pivot_high["crossed"]:
                    if cur_close > pivot_high["price"]:
                        # LuxAlgo Rule: If trend was BEARISH (-1), breaking high is CHOCH; else BOS
                        tag = "CHOCH" if trend_bias == -1 else "BOS"
                        trend_bias = 1
                        pivot_high["crossed"] = True

                        broken_lvl = pivot_high["price"]
                        break_dist = round(float(cur_close - broken_lvl), 2)
                        break_pct = round(float((break_dist / broken_lvl) * 100), 2) if broken_lvl > 0 else 0.0

                        layer_structures.append({
                            "layer": "internal" if is_internal else "swing",
                            "is_internal": is_internal,
                            "timeframe": tf_clean,
                            "type": tag,
                            "direction": "BULLISH",
                            "broken_level": broken_lvl,
                            "breakout_price": round(float(cur_close), 2),
                            "break_distance": break_dist,
                            "break_percentage": break_pct,
                            "pivot_index": pivot_high["index"],
                            "pivot_timestamp": pivot_high["time"],
                            "breakout_index": i,
                            "breakout_timestamp": timestamps[i],
                            "color": "#089981",  # LuxAlgo Green
                            "line_style": "dashed" if is_internal else "solid",
                            "label": tag,
                            "status": "CONFIRMED"
                        })

                        # Order Block: Origin low candle between pivot and breakout
                        p_idx = pivot_high["index"]
                        if i > p_idx:
                            sub_low_slice = lows[p_idx : i + 1]
                            ob_rel_idx = int(np.argmin(sub_low_slice))
                            ob_idx = p_idx + ob_rel_idx
                            order_blocks.append({
                                "bias": "BULLISH",
                                "layer": "internal" if is_internal else "swing",
                                "high": round(float(highs[ob_idx]), 2),
                                "low": round(float(lows[ob_idx]), 2),
                                "time": timestamps[ob_idx],
                                "color": "#089981"
                            })

                # 2. Bearish Breakdown (Candle Close crosses BELOW pivot_low)
                if pivot_low is not None and not pivot_low["crossed"]:
                    if cur_close < pivot_low["price"]:
                        # LuxAlgo Rule: If trend was BULLISH (1), breaking low is CHOCH; else BOS
                        tag = "CHOCH" if trend_bias == 1 else "BOS"
                        trend_bias = -1
                        pivot_low["crossed"] = True

                        broken_lvl = pivot_low["price"]
                        break_dist = round(float(broken_lvl - cur_close), 2)
                        break_pct = round(float((break_dist / broken_lvl) * 100), 2) if broken_lvl > 0 else 0.0

                        layer_structures.append({
                            "layer": "internal" if is_internal else "swing",
                            "is_internal": is_internal,
                            "timeframe": tf_clean,
                            "type": tag,
                            "direction": "BEARISH",
                            "broken_level": broken_lvl,
                            "breakout_price": round(float(cur_close), 2),
                            "break_distance": break_dist,
                            "break_percentage": break_pct,
                            "pivot_index": pivot_low["index"],
                            "pivot_timestamp": pivot_low["time"],
                            "breakout_index": i,
                            "breakout_timestamp": timestamps[i],
                            "color": "#F23645",  # LuxAlgo Red
                            "line_style": "dashed" if is_internal else "solid",
                            "label": tag,
                            "status": "CONFIRMED"
                        })

                        # Order Block: Origin high candle between pivot and breakout
                        p_idx = pivot_low["index"]
                        if i > p_idx:
                            sub_high_slice = highs[p_idx : i + 1]
                            ob_rel_idx = int(np.argmax(sub_high_slice))
                            ob_idx = p_idx + ob_rel_idx
                            order_blocks.append({
                                "bias": "BEARISH",
                                "layer": "internal" if is_internal else "swing",
                                "high": round(float(highs[ob_idx]), 2),
                                "low": round(float(lows[ob_idx]), 2),
                                "time": timestamps[ob_idx],
                                "color": "#F23645"
                            })

                # Pine Script updateTrailingExtremes: continuously tracks the true swing peak and trough on EVERY bar
                if not is_internal:
                    if highs[i] > trailing_top:
                        trailing_top = round(float(highs[i]), 2)
                        trailing_top_time = timestamps[i]
                    if lows[i] < trailing_bottom:
                        trailing_bottom = round(float(lows[i]), 2)
                        trailing_bottom_time = timestamps[i]

            trend_str = "BULLISH" if trend_bias == 1 else ("BEARISH" if trend_bias == -1 else "NEUTRAL")
            extremes = {
                "top": trailing_top if trailing_top != float("-inf") else None,
                "top_time": trailing_top_time,
                "bottom": trailing_bottom if trailing_bottom != float("inf") else None,
                "bottom_time": trailing_bottom_time,
                "trend": trend_str
            }

            # Active Future Breakout Levels to watch on upcoming candles:
            active_levels = {}
            if pivot_high is not None and not pivot_high["crossed"]:
                ev_tag = "CHOCH" if trend_bias == -1 else "BOS"
                active_levels["high"] = {
                    "price": pivot_high["price"],
                    "time": pivot_high["time"],
                    "type": ev_tag,
                    "direction": "BULLISH",
                    "color": "#089981",
                    "label": f"Active {ev_tag}: ₹{pivot_high['price']:.1f}",
                    "is_internal": is_internal
                }
            elif trailing_top > 0 and trailing_top != float("-inf"):
                ev_tag = "CHOCH" if trend_bias == -1 else "BOS"
                active_levels["high"] = {
                    "price": trailing_top,
                    "time": trailing_top_time,
                    "type": ev_tag,
                    "direction": "BULLISH",
                    "color": "#089981",
                    "label": f"Active {ev_tag}: ₹{trailing_top:.1f}",
                    "is_internal": is_internal
                }

            if pivot_low is not None and not pivot_low["crossed"]:
                ev_tag = "CHOCH" if trend_bias == 1 else "BOS"
                active_levels["low"] = {
                    "price": pivot_low["price"],
                    "time": pivot_low["time"],
                    "type": ev_tag,
                    "direction": "BEARISH",
                    "color": "#F23645",
                    "label": f"Active {ev_tag}: ₹{pivot_low['price']:.1f}",
                    "is_internal": is_internal
                }
            elif trailing_bottom > 0 and trailing_bottom != float("inf"):
                ev_tag = "CHOCH" if trend_bias == 1 else "BOS"
                active_levels["low"] = {
                    "price": trailing_bottom,
                    "time": trailing_bottom_time,
                    "type": ev_tag,
                    "direction": "BEARISH",
                    "color": "#F23645",
                    "label": f"Active {ev_tag}: ₹{trailing_bottom:.1f}",
                    "is_internal": is_internal
                }

            return layer_structures, trend_str, extremes, active_levels

        # Execute Internal Structure (size = 5)
        internal_structs, internal_trend, _, internal_active = process_layer(actual_internal_size, is_internal=True)
        # Execute Swing Structure (size = 50)
        swing_structs, swing_trend, swing_extremes, swing_active = process_layer(actual_swing_size, is_internal=False)

        active_future_levels = {
            "high": swing_active.get("high") or internal_active.get("high"),
            "low": swing_active.get("low") or internal_active.get("low")
        }

        # Merge structures: Retain recent internal and swing structures
        # Filter duplicates: If internal structure has identical level and breakout bar as swing, prefer swing
        swing_keys = {(s["broken_level"], s["breakout_index"]) for s in swing_structs}
        filtered_internal = [s for s in internal_structs if (s["broken_level"], s["breakout_index"]) not in swing_keys]

        all_structures = swing_structs + filtered_internal
        all_structures.sort(key=lambda s: s["breakout_index"])

        # Display Structures: Keep last 10 structures for clean TradingView display
        display_structures = all_structures[-10:] if len(all_structures) >= 10 else all_structures

        # LuxAlgo Strong / Weak High & Low
        strong_weak_levels = {}
        if swing_extremes.get("top") is not None:
            is_strong_high = (swing_trend == "BEARISH")
            strong_weak_levels["high"] = {
                "price": swing_extremes["top"],
                "time": swing_extremes["top_time"],
                "label": "Strong High" if is_strong_high else "Weak High",
                "color": "#F23645" if is_strong_high else "#878b94"
            }
        if swing_extremes.get("bottom") is not None:
            is_strong_low = (swing_trend == "BULLISH")
            strong_weak_levels["low"] = {
                "price": swing_extremes["bottom"],
                "time": swing_extremes["bottom_time"],
                "label": "Strong Low" if is_strong_low else "Weak Low",
                "color": "#089981" if is_strong_low else "#878b94"
            }

        # Last verified event
        last_event = display_structures[-1] if display_structures else None

        # Natural summary for AI Copilot & RAG
        if last_event:
            ev_layer = "Swing" if not last_event.get("is_internal") else "Internal"
            ev_type = last_event["type"]
            ev_dir = last_event["direction"]
            ev_lvl = last_event["broken_level"]
            ev_dist = last_event.get("break_distance", 0)
            ev_pct = last_event.get("break_percentage", 0)
            summary = (
                f"{tf_clean.upper()} LuxAlgo SMC: {ev_layer} {ev_type} ({ev_dir}) at ₹{ev_lvl:.1f} "
                f"(+{ev_dist:.1f} pts / +{ev_pct:.2f}% into {swing_trend} trend)."
            )
        else:
            summary = f"{tf_clean.upper()} LuxAlgo SMC: Neutral consolidation, structure developing."

        # Keep recent Order Blocks (last 4)
        recent_order_blocks = order_blocks[-4:] if len(order_blocks) >= 4 else order_blocks

        return {
            "timeframe": tf_clean,
            "trend": swing_trend,
            "internal_trend": internal_trend,
            "last_event": last_event,
            "active_structures": display_structures,
            "active_future_levels": active_future_levels,
            "strong_weak_levels": strong_weak_levels,
            "equal_highs_lows": equal_highs_lows[-4:],
            "order_blocks": recent_order_blocks,
            "key_levels": {
                "strong_weak": strong_weak_levels,
                "current_trend": swing_trend,
                "internal_trend": internal_trend
            },
            "summary": summary
        }

    @classmethod
    def analyze_structure_timeframe(cls, df: pd.DataFrame, timeframe: str = "5m") -> Dict[str, Any]:
        """Entry point for single timeframe structure request."""
        return cls.calculate_luxalgo_smc(df, swing_size=50, internal_size=5, timeframe=timeframe)

    @classmethod
    def scan_all_timeframes(cls, engine: Any) -> Dict[str, Any]:
        """
        Executes parallel scan across all 4 core timeframes (5m, 15m, 1h, 1d)
        using the LuxAlgo Smart Money Concepts engine.
        """
        timeframes = ["5m", "15m", "1h", "1d"]
        results: Dict[str, Any] = {}
        bullish_count = 0
        bearish_count = 0

        for tf in timeframes:
            try:
                snap = engine.get_snapshot(timeframe=tf)
                df_tf = snap.get("df", pd.DataFrame()) if isinstance(snap, dict) else pd.DataFrame()
                if df_tf is None or df_tf.empty:
                    df_tf = engine.cache_mgr.get_candles(symbol="NIFTY 50", timeframe=tf)

                tf_res = cls.calculate_luxalgo_smc(df_tf, swing_size=50, internal_size=5, timeframe=tf)
                results[tf] = tf_res

                trend = tf_res.get("trend", "NEUTRAL")
                if trend == "BULLISH":
                    bullish_count += 1
                elif trend == "BEARISH":
                    bearish_count += 1
            except Exception as e:
                logger.error("Error evaluating LuxAlgo SMC for %s: %s", tf, e)
                results[tf] = {
                    "timeframe": tf,
                    "trend": "NEUTRAL",
                    "internal_trend": "NEUTRAL",
                    "last_event": None,
                    "active_structures": [],
                    "strong_weak_levels": {},
                    "equal_highs_lows": [],
                    "order_blocks": [],
                    "key_levels": {},
                    "summary": f"{tf.upper()}: LuxAlgo SMC calculation pending."
                }

        # Multi-timeframe consensus
        if bullish_count >= 3:
            overall_structure = "STRONG BULLISH SMC ALIGNMENT"
        elif bearish_count >= 3:
            overall_structure = "STRONG BEARISH SMC ALIGNMENT"
        elif bullish_count > bearish_count:
            overall_structure = "MODERATE BULLISH BIAS"
        elif bearish_count > bullish_count:
            overall_structure = "MODERATE BEARISH BIAS"
        else:
            overall_structure = "MIXED / CONFLICTING TIMEFRAMES"

        # Build concise executive briefing for RAG / AI Copilot
        briefing_lines = []
        for tf in timeframes:
            res = results.get(tf, {})
            ev = res.get("last_event")
            if ev:
                ev_layer = "Swing" if not ev.get("is_internal") else "Internal"
                ev_dist = ev.get("break_distance", 0)
                ev_pct = ev.get("break_percentage", 0)
                dist_str = f" (+{ev_dist:.1f} pts / +{ev_pct:.2f}%)" if ev_dist else ""
                briefing_lines.append(f"{tf.upper()}: {ev_layer} {ev.get('type')} {ev.get('direction')} @ ₹{ev.get('broken_level'):.1f}{dist_str} ({res.get('trend')})")
            else:
                briefing_lines.append(f"{tf.upper()}: Rangebound ({res.get('trend')})")

        return {
            "status": "ok",
            "overall_structure": overall_structure,
            "bullish_timeframes": bullish_count,
            "bearish_timeframes": bearish_count,
            "timeframes": results,
            "executive_summary": " • ".join(briefing_lines)
        }
