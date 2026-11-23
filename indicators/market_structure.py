"""
indicators/market_structure.py
Institutional Multi-Timeframe Market Structure Engine:
- Break of Structure (BoS): Trend Continuation
- Change of Character (CHoCH): Early Trend Reversal
- Swings: Higher Highs (HH), Higher Lows (HL), Lower Highs (LH), Lower Lows (LL)
- Multi-Timeframe Analysis: 5m, 15m, 1h, 1d calculated independently on authentic candles
- Natural, zero forced structures: Requires real body candle close beyond structural pivots
"""

import math
import logging
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np

logger = logging.getLogger(__name__)


class MarketStructureEngine:
    _instance: Optional["MarketStructureEngine"] = None

    @classmethod
    def get_instance(cls) -> "MarketStructureEngine":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @staticmethod
    def find_swing_pivots(df: pd.DataFrame, left_bars: int = 3, right_bars: int = 3) -> List[Dict[str, Any]]:
        """
        Identifies authentic swing highs and swing lows using fractal pivot window.
        left_bars: number of bars to the left that must be lower (for high) or higher (for low)
        right_bars: number of bars to the right that must be lower (for high) or higher (for low)
        """
        if df is None or len(df) < (left_bars + right_bars + 2):
            return []

        pivots = []
        highs = df["high"].values
        lows = df["low"].values
        timestamps = df["timestamp"].values if "timestamp" in df.columns else df.index.values

        n = len(df)
        for i in range(left_bars, n - right_bars):
            # Check Swing High
            is_high = True
            current_h = highs[i]
            for j in range(i - left_bars, i + right_bars + 1):
                if j != i and highs[j] >= current_h:
                    is_high = False
                    break

            if is_high:
                pivots.append({
                    "index": i,
                    "type": "HIGH",
                    "price": round(float(current_h), 2),
                    "timestamp": str(timestamps[i]),
                })

            # Check Swing Low
            is_low = True
            current_l = lows[i]
            for j in range(i - left_bars, i + right_bars + 1):
                if j != i and lows[j] <= current_l:
                    is_low = False
                    break

            if is_low:
                pivots.append({
                    "index": i,
                    "type": "LOW",
                    "price": round(float(current_l), 2),
                    "timestamp": str(timestamps[i]),
                })

        # Sort pivots strictly by chronological index
        pivots.sort(key=lambda x: x["index"])
        return pivots

    @classmethod
    def analyze_structure_timeframe(cls, df: pd.DataFrame, timeframe: str = "5m") -> Dict[str, Any]:
        """
        Calculates authentic BoS and CHoCH on a single timeframe DataFrame.
        Returns:
        - trend: BULLISH, BEARISH, or CONSOLIDATION
        - last_event: dict of latest BoS/CHoCH
        - active_structures: list of structural breakout lines for chart rendering
        - key_levels: dict with recent swing high, swing low, choch level, bos level
        """
        tf_clean = str(timeframe or "5m").lower()
        if df is None or len(df) < 15:
            return {
                "timeframe": tf_clean,
                "trend": "NEUTRAL",
                "last_event": None,
                "active_structures": [],
                "key_levels": {},
                "summary": f"{tf_clean.upper()}: Insufficient candle data for market structure."
            }

        # Window tuning per timeframe
        if tf_clean in ("1m", "2m", "3m", "5m"):
            left_bars, right_bars = 3, 2
        elif tf_clean in ("15m", "30m"):
            left_bars, right_bars = 3, 2
        elif tf_clean in ("1h", "2h", "4h"):
            left_bars, right_bars = 2, 2
        else:  # 1d
            left_bars, right_bars = 2, 2

        pivots = cls.find_swing_pivots(df, left_bars=left_bars, right_bars=right_bars)
        if len(pivots) < 4:
            return {
                "timeframe": tf_clean,
                "trend": "CONSOLIDATION",
                "last_event": None,
                "active_structures": [],
                "key_levels": {},
                "summary": f"{tf_clean.upper()}: Natural consolidation, swing structure forming."
            }

        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values
        timestamps = df["timestamp"].values if "timestamp" in df.columns else df.index.values

        # Structural State
        current_trend = "NEUTRAL"
        last_high = None
        last_low = None
        higher_high = None
        higher_low = None
        lower_high = None
        lower_low = None

        structures: List[Dict[str, Any]] = []

        # Iterate forward through pivots to track structure formation
        for p in pivots:
            if p["type"] == "HIGH":
                if last_high is not None:
                    if p["price"] > last_high["price"]:
                        higher_high = p
                    else:
                        lower_high = p
                last_high = p
            elif p["type"] == "LOW":
                if last_low is not None:
                    if p["price"] < last_low["price"]:
                        lower_low = p
                    else:
                        higher_low = p
                last_low = p

        # Scan candles after the last 2-3 pivots for authentic BoS & CHoCH breaks
        # Initial estimate of trend from recent pivot sequence
        if len(pivots) >= 4:
            recent_pivots = pivots[-4:]
            recent_highs = [p["price"] for p in recent_pivots if p["type"] == "HIGH"]
            recent_lows = [p["price"] for p in recent_pivots if p["type"] == "LOW"]
            if len(recent_highs) >= 2 and len(recent_lows) >= 2:
                if recent_highs[-1] > recent_highs[-2] and recent_lows[-1] >= recent_lows[-2]:
                    current_trend = "BULLISH"
                elif recent_highs[-1] <= recent_highs[-2] and recent_lows[-1] < recent_lows[-2]:
                    current_trend = "BEARISH"
                else:
                    current_trend = "CONSOLIDATION"

        # Track verified breaks across the candle history
        active_high_pivot = None
        active_low_pivot = None

        for i in range(len(df)):
            cur_close = float(closes[i])
            cur_time = str(timestamps[i])

            # Update active pivots that were confirmed prior to this candle
            for p in pivots:
                if p["index"] + right_bars == i:
                    if p["type"] == "HIGH":
                        active_high_pivot = p
                    elif p["type"] == "LOW":
                        active_low_pivot = p

            if active_high_pivot is None or active_low_pivot is None:
                continue

            # Check Bullish Breakout (Close > active_high_pivot)
            if cur_close > active_high_pivot["price"] and i > active_high_pivot["index"]:
                # Is it BoS (continuation) or CHoCH (reversal)?
                is_choch = (current_trend == "BEARISH")
                event_type = "CHOCH" if is_choch else "BOS"
                current_trend = "BULLISH"

                structures.append({
                    "timeframe": tf_clean,
                    "type": event_type,
                    "direction": "BULLISH",
                    "broken_level": active_high_pivot["price"],
                    "breakout_price": cur_close,
                    "pivot_index": active_high_pivot["index"],
                    "pivot_timestamp": active_high_pivot["timestamp"],
                    "breakout_index": i,
                    "breakout_timestamp": cur_time,
                    "status": "CONFIRMED",
                    "label": f"[{tf_clean.upper()} {event_type} ↑]"
                })
                # Reset pivot so we don't re-trigger on the same level
                active_high_pivot = None

            # Check Bearish Breakdown (Close < active_low_pivot)
            elif cur_close < active_low_pivot["price"] and i > active_low_pivot["index"]:
                is_choch = (current_trend == "BULLISH")
                event_type = "CHOCH" if is_choch else "BOS"
                current_trend = "BEARISH"

                structures.append({
                    "timeframe": tf_clean,
                    "type": event_type,
                    "direction": "BEARISH",
                    "broken_level": active_low_pivot["price"],
                    "breakout_price": cur_close,
                    "pivot_index": active_low_pivot["index"],
                    "pivot_timestamp": active_low_pivot["timestamp"],
                    "breakout_index": i,
                    "breakout_timestamp": cur_time,
                    "status": "CONFIRMED",
                    "label": f"[{tf_clean.upper()} {event_type} ↓]"
                })
                # Reset pivot so we don't re-trigger on the same level
                active_low_pivot = None

        # Extract latest event and key levels
        last_event = structures[-1] if structures else None
        recent_high = max([p["price"] for p in pivots[-3:] if p["type"] == "HIGH"], default=None)
        recent_low = min([p["price"] for p in pivots[-3:] if p["type"] == "LOW"], default=None)

        # Retain last 3 active structures for chart display
        display_structures = structures[-3:] if len(structures) >= 3 else structures

        # Build natural summary
        if last_event:
            ev_dir = "Bullish" if last_event["direction"] == "BULLISH" else "Bearish"
            ev_type = last_event["type"]
            ev_lvl = last_event["broken_level"]
            if ev_type == "CHOCH":
                summary = f"{tf_clean.upper()} {ev_dir} Change of Character (CHoCH) triggered at ₹{ev_lvl:.1f} (Early Trend Shift to {current_trend})."
            else:
                summary = f"{tf_clean.upper()} {ev_dir} Break of Structure (BoS) confirmed at ₹{ev_lvl:.1f} (Trend Continuation in {current_trend})."
        else:
            summary = f"{tf_clean.upper()} Structure: Rangebound consolidation between ₹{recent_low or 0:.1f} - ₹{recent_high or 0:.1f}."

        return {
            "timeframe": tf_clean,
            "trend": current_trend,
            "last_event": last_event,
            "active_structures": display_structures,
            "key_levels": {
                "recent_swing_high": recent_high,
                "recent_swing_low": recent_low,
                "current_trend": current_trend,
            },
            "summary": summary
        }

    @classmethod
    def scan_all_timeframes(cls, engine: Any) -> Dict[str, Any]:
        """
        Executes parallel scan across all 4 core timeframes (5m, 15m, 1h, 1d).
        Returns comprehensive multi-timeframe structural mapping for chart and AI Copilot.
        """
        timeframes = ["5m", "15m", "1h", "1d"]
        results: Dict[str, Any] = {}
        alignment_score = 0
        bullish_count = 0
        bearish_count = 0

        for tf in timeframes:
            try:
                snap = engine.get_snapshot(timeframe=tf)
                df_tf = snap.get("df", pd.DataFrame()) if isinstance(snap, dict) else pd.DataFrame()
                if df_tf is None or df_tf.empty:
                    df_tf = engine.cache_mgr.get_candles(symbol="NIFTY 50", timeframe=tf)

                tf_res = cls.analyze_structure_timeframe(df_tf, timeframe=tf)
                results[tf] = tf_res

                trend = tf_res.get("trend", "NEUTRAL")
                if trend == "BULLISH":
                    bullish_count += 1
                elif trend == "BEARISH":
                    bearish_count += 1
            except Exception as e:
                logger.error("Error evaluating market structure for %s: %s", tf, e)
                results[tf] = {
                    "timeframe": tf,
                    "trend": "NEUTRAL",
                    "last_event": None,
                    "active_structures": [],
                    "key_levels": {},
                    "summary": f"{tf.upper()}: Structure calculation pending."
                }

        # Multi-timeframe consensus
        if bullish_count >= 3:
            overall_structure = "STRONG BULLISH ALIGNMENT"
        elif bearish_count >= 3:
            overall_structure = "STRONG BEARISH ALIGNMENT"
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
                briefing_lines.append(f"{tf.upper()}: {ev.get('type')} {ev.get('direction')} @ ₹{ev.get('broken_level'):.1f} ({res.get('trend')})")
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
