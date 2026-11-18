"""
indicators/pattern_detector.py - Advanced Multi-Timeframe Candlestick Pattern Detection Engine.
Part of the Indicators Department for NIFTY 50 Pro Terminal.

Detects geometric and harmonic chart formations:
1. Harmonic Patterns (Bullish & Bearish Butterfly, Gartley, Bat with Fibonacci ratios)
2. Head & Shoulders & Inverse Head & Shoulders (with Slanted / Angled Necklines)
3. Slanted Trendline Breakouts (Ascending / Descending Triangles, Converging Wedges, Channels)
4. Double Tops (M) & Double Bottoms (W)

Supports:
- Multi-timeframe evaluation: 5m, 15m, 1h, 1d
- Multi-day spanning: Analyzes swing peaks/troughs across multiple trading days
- 1-Click chart auto-drawing: Produces lightweight-charts compatible SVG drawing shapes
- RAG Copilot context integration: Synthesizes rich geometry & risk-reward metrics
"""
from __future__ import annotations

import logging
import math
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import pytz

logger = logging.getLogger("PatternDetector")
IST = pytz.timezone("Asia/Kolkata")


def _to_unix_sec(ts: Any) -> int:
    """Safely converts pandas Timestamp or datetime string to Unix seconds."""
    if ts is None:
        return int(time.time())
    if isinstance(ts, (int, float)):
        return int(ts)
    if hasattr(ts, "timestamp"):
        try:
            return int(ts.timestamp())
        except Exception:
            pass
    try:
        dt = pd.to_datetime(ts)
        return int(dt.timestamp())
    except Exception:
        return int(time.time())


def find_swings(
    df: pd.DataFrame,
    window: int = 5,
    min_pct: float = 0.0015
) -> List[Dict[str, Any]]:
    """
    Identifies clean alternating swing peaks (Highs) and troughs (Lows) via ZigZag algorithm.
    window: Number of bars before and after to establish local extremum.
    min_pct: Minimum percentage move to filter out minor market noise.
    """
    if df.empty or len(df) < window * 2 + 1:
        return []

    highs = df["high"].values
    lows = df["low"].values
    times = df.index
    n = len(df)

    candidates = []
    for i in range(window, n - window):
        is_high = highs[i] == np.max(highs[i - window : i + window + 1])
        is_low = lows[i] == np.min(lows[i - window : i + window + 1])

        if is_high and not is_low:
            candidates.append({
                "type": "H",
                "bar_idx": i,
                "time": _to_unix_sec(times[i]),
                "time_raw": times[i],
                "price": float(highs[i])
            })
        elif is_low and not is_high:
            candidates.append({
                "type": "L",
                "bar_idx": i,
                "time": _to_unix_sec(times[i]),
                "time_raw": times[i],
                "price": float(lows[i])
            })
        elif is_high and is_low:
            c = float(df["close"].iloc[i])
            o = float(df["open"].iloc[i])
            candidates.append({
                "type": "H" if c >= o else "L",
                "bar_idx": i,
                "time": _to_unix_sec(times[i]),
                "time_raw": times[i],
                "price": float(highs[i] if c >= o else lows[i])
            })

    if not candidates:
        return []

    # Filter consecutive swings of the same type (keep the highest High or lowest Low)
    filtered = []
    for c in candidates:
        if not filtered:
            filtered.append(c)
            continue
        last = filtered[-1]
        if c["type"] == last["type"]:
            if c["type"] == "H" and c["price"] > last["price"]:
                filtered[-1] = c
            elif c["type"] == "L" and c["price"] < last["price"]:
                filtered[-1] = c
        else:
            pct_move = abs(c["price"] - last["price"]) / max(1.0, last["price"])
            if pct_move >= min_pct or len(filtered) < 2:
                filtered.append(c)

    return filtered


class PatternDetector:
    """
    Autonomous multi-timeframe pattern detection engine.
    """

    def __init__(self):
        pass

    @classmethod
    def analyze_patterns(cls, df: pd.DataFrame, latest_price: float, timeframe: str = "5m") -> Dict[str, Any]:
        """
        Classmethod compatibility endpoint for server.py and RAG integration.
        Returns primary pattern, all detected patterns, drawing shapes, and summary.
        """
        detector = get_pattern_detector()
        detected = detector.detect_all_patterns(df, timeframe=timeframe, cur_price=latest_price)
        primary = detected[0] if detected else None
        summary_lines = []
        if primary:
            summary_lines.append(f"• Active Structure: **{primary['name']}** ({primary['direction']})")
            summary_lines.append(f"  - Status: {primary.get('status', 'ACTIVE')} | Timeframe: {primary.get('timeframe', timeframe).upper()}")
            summary_lines.append(f"  - Entry / Trigger: ₹{primary.get('entry_price', 0):,.1f} | Target: ₹{primary.get('target_price', 0):,.1f} | SL: ₹{primary.get('stop_loss', 0):,.1f}")
            summary_lines.append(f"  - Structure Span: {primary.get('span_str', 'Multi-Day')}")
            summary_lines.append(f"  - Risk:Reward: {primary.get('risk_reward', '1 : 2.5')}")
        else:
            summary_lines.append("• Active Structure: No large-scale geometric pattern currently forming (Consolidating near baseline).")

        return {
            "spot_price": latest_price,
            "timeframe": timeframe,
            "active_patterns_count": len(detected),
            "detected_patterns": detected,
            "primary_pattern": primary,
            "summary": "\n".join(summary_lines),
        }

    def detect_all_patterns(
        self,
        df: pd.DataFrame,
        timeframe: str = "5m",
        cur_price: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Detects all active and forming patterns on the given DataFrame.
        Returns a sorted list of patterns (confirmed/active ones first).
        """
        if df.empty or len(df) < 20:
            return []

        if cur_price is None or cur_price <= 0:
            cur_price = float(df["close"].iloc[-1])

        tf_clean = timeframe.lower()
        if "1d" in tf_clean:
            window = 3
            min_pct = 0.0035
        elif "1h" in tf_clean or "60m" in tf_clean:
            window = 4
            min_pct = 0.0022
        elif "15m" in tf_clean:
            window = 4
            min_pct = 0.0016
        else:
            window = 5
            min_pct = 0.0012

        swings = find_swings(df, window=window, min_pct=min_pct)
        if len(swings) < 5:
            swings = find_swings(df, window=max(3, window - 2), min_pct=min_pct * 0.7)

        if len(swings) < 5:
            return []

        patterns: List[Dict[str, Any]] = []

        # 1. Harmonic Patterns (Butterfly, Gartley, Bat)
        harmonics = self._detect_harmonics(swings, df, cur_price, timeframe)
        patterns.extend(harmonics)

        # 2. Head & Shoulders (Standard & Inverse with Slanted Neckline)
        hns = self._detect_head_and_shoulders(swings, df, cur_price, timeframe)
        patterns.extend(hns)

        # 3. Slanted Trendline Breakouts (Triangles & Wedges)
        triangles = self._detect_triangles_and_wedges(swings, df, cur_price, timeframe)
        patterns.extend(triangles)

        # 4. Double Tops / Bottoms
        doubles = self._detect_double_tops_bottoms(swings, df, cur_price, timeframe)
        patterns.extend(doubles)

        # 5. Filter out patterns that have already completed (Target Hit or SL Hit)
        # Strictly active trades only: once Target or SL is touched by live or historical bars, the trade is retired!
        active_patterns: List[Dict[str, Any]] = []
        n_bars = len(df)
        for p in patterns:
            is_buy = "BUY" in p["direction"]
            target = p["target_price"]
            stop = p["stop_loss"]
            end_bar = p.get("end_bar_idx", 0)

            # Check if target or stop has been hit by live cur_price
            target_hit = (cur_price >= target) if is_buy else (cur_price <= target)
            sl_hit = (cur_price <= stop) if is_buy else (cur_price >= stop)

            # Check historical bars since pattern completion bar
            if not target_hit and not sl_hit and end_bar < n_bars:
                sub_df = df.iloc[max(0, end_bar):]
                if not sub_df.empty:
                    if is_buy:
                        max_high = float(sub_df["high"].max())
                        min_low = float(sub_df["low"].min())
                        if max_high >= target:
                            target_hit = True
                        elif min_low <= stop:
                            sl_hit = True
                    else:
                        min_low = float(sub_df["low"].min())
                        max_high = float(sub_df["high"].max())
                        if min_low <= target:
                            target_hit = True
                        elif max_high >= stop:
                            sl_hit = True

            if target_hit:
                p["is_completed"] = True
                p["completion_reason"] = "TARGET_HIT"
                p["status"] = "TARGET_HIT"
            elif sl_hit:
                p["is_completed"] = True
                p["completion_reason"] = "SL_HIT"
                p["status"] = "SL_HIT"
            else:
                p["is_completed"] = False
                active_patterns.append(p)

        # Sort by relevance: Confirmed breakouts & PRZ reversals first, then by recency
        def _sort_key(p: Dict[str, Any]) -> Tuple[int, int]:
            status_priority = {
                "CONFIRMED_BREAKOUT": 0,
                "PRZ_REVERSAL": 1,
                "TESTING_NECKLINE": 2,
                "TESTING_TRIGGER": 3,
                "FORMING": 4
            }
            pri = status_priority.get(p.get("status", "FORMING"), 5)
            last_bar = p.get("end_bar_idx", 0)
            return (pri, -last_bar)

        active_patterns.sort(key=_sort_key)
        return active_patterns

    # =========================================================================
    # 1. HARMONIC PATTERNS (BUTTERFLY, GARTLEY, BAT)
    # =========================================================================
    def _detect_harmonics(
        self,
        swings: List[Dict[str, Any]],
        df: pd.DataFrame,
        cur_price: float,
        timeframe: str
    ) -> List[Dict[str, Any]]:
        patterns = []
        n_swings = len(swings)
        if n_swings < 5:
            return patterns

        # Scan recent 35 swings
        scan_count = min(35, n_swings - 4)
        for start in range(n_swings - scan_count - 4, n_swings - 4):
            if start < 0:
                continue
            X, A, B, C, D = swings[start : start + 5]

            # Alternate verification: X->A->B->C->D
            if not (X["type"] != A["type"] and A["type"] != B["type"] and B["type"] != C["type"] and C["type"] != D["type"]):
                continue

            xa = abs(A["price"] - X["price"])
            ab = abs(B["price"] - A["price"])
            bc = abs(C["price"] - B["price"])
            cd = abs(D["price"] - C["price"])

            if xa < 20.0 or ab < 12.0 or bc < 12.0 or cd < 15.0:
                continue

            ab_xa = ab / xa
            bc_ab = bc / ab
            cd_bc = cd / bc
            cd_xa = cd / xa

            # ----------------------------------------------------
            # BULLISH HARMONICS (Buy at D, where D is a swing LOW)
            # D["type"] == "L"
            # ----------------------------------------------------
            if D["type"] == "L":
                is_butterfly = (0.70 <= ab_xa <= 0.88) and (0.35 <= bc_ab <= 0.90) and (1.20 <= cd_xa <= 2.20 or 1.40 <= cd_bc <= 2.80)
                is_bat = (0.35 <= ab_xa <= 0.55) and (0.35 <= bc_ab <= 0.90) and (1.50 <= cd_bc <= 2.70 or 0.80 <= cd_xa <= 1.20)
                is_gartley = (0.58 <= ab_xa <= 0.68) and (0.35 <= bc_ab <= 0.90) and (1.10 <= cd_bc <= 1.80)

                pat_name = None
                if is_butterfly:
                    pat_name = "Bullish Butterfly Harmonic"
                elif is_bat:
                    pat_name = "Bullish Bat Harmonic"
                elif is_gartley:
                    pat_name = "Bullish Gartley Harmonic"

                if pat_name:
                    d_price = D["price"]
                    entry = round(cur_price if abs(cur_price - d_price) < 40.0 else d_price, 1)
                    target_dist = max(45.0, cd * 0.50)
                    target = round(entry + target_dist, 1)
                    sl_dist = max(20.0, cd * 0.20)
                    stop = round(d_price - sl_dist, 1)
                    rr = round(target_dist / max(1.0, sl_dist), 1)

                    status = "PRZ_REVERSAL" if cur_price >= d_price else "TESTING_TRIGGER"
                    span_str = self._format_span(X["time_raw"], D["time_raw"])

                    drawing_shapes = [
                        {"id": f"harm_{start}_xa", "type": "line", "time1": X["time"], "price1": X["price"], "time2": A["time"], "price2": A["price"], "color": "#38bdf8", "width": "2", "remark": f"XA Leg (₹{xa:.1f} pts)"},
                        {"id": f"harm_{start}_ab", "type": "line", "time1": A["time"], "price1": A["price"], "time2": B["time"], "price2": B["price"], "color": "#38bdf8", "width": "2", "remark": f"AB ({ab_xa:.3f})"},
                        {"id": f"harm_{start}_bc", "type": "line", "time1": B["time"], "price1": B["price"], "time2": C["time"], "price2": C["price"], "color": "#38bdf8", "width": "2", "remark": f"BC ({bc_ab:.3f})"},
                        {"id": f"harm_{start}_cd", "type": "line", "time1": C["time"], "price1": C["price"], "time2": D["time"], "price2": D["price"], "color": "#22c55e", "width": "3", "remark": f"CD ({cd_bc:.2f} PRZ Reversal)"},
                        {"id": f"harm_{start}_box", "type": "target_sl", "entry": entry, "target": target, "stop": stop, "timeStart": D["time"], "timeEnd": D["time"] + self._get_future_time_span(timeframe, 25), "color": "#22c55e", "remark": f"AI {pat_name}"}
                    ]

                    patterns.append({
                        "id": f"pat_harmonic_bull_{D['bar_idx']}",
                        "name": pat_name,
                        "type": "harmonic",
                        "direction": "BUY (CALL)",
                        "timeframe": timeframe,
                        "status": status,
                        "entry_price": entry,
                        "target_price": target,
                        "stop_loss": stop,
                        "risk_reward": f"1 : {rr}",
                        "span_str": span_str,
                        "end_bar_idx": D["bar_idx"],
                        "ratios": {
                            "AB_XA": round(ab_xa, 3),
                            "BC_AB": round(bc_ab, 3),
                            "CD_BC": round(cd_bc, 3),
                            "CD_XA": round(cd_xa, 3)
                        },
                        "points": [
                            {"label": "X", "time": X["time"], "price": X["price"]},
                            {"label": "A", "time": A["time"], "price": A["price"]},
                            {"label": "B", "time": B["time"], "price": B["price"]},
                            {"label": "C", "time": C["time"], "price": C["price"]},
                            {"label": "D (PRZ)", "time": D["time"], "price": D["price"]},
                        ],
                        "drawing_shapes": drawing_shapes
                    })

            # ----------------------------------------------------
            # BEARISH HARMONICS (Sell at D, where D is a swing HIGH)
            # D["type"] == "H"
            # ----------------------------------------------------
            elif D["type"] == "H":
                is_butterfly = (0.70 <= ab_xa <= 0.88) and (0.35 <= bc_ab <= 0.90) and (1.20 <= cd_xa <= 2.20 or 1.40 <= cd_bc <= 2.80)
                is_bat = (0.35 <= ab_xa <= 0.55) and (0.35 <= bc_ab <= 0.90) and (1.50 <= cd_bc <= 2.70 or 0.80 <= cd_xa <= 1.20)
                is_gartley = (0.58 <= ab_xa <= 0.68) and (0.35 <= bc_ab <= 0.90) and (1.10 <= cd_bc <= 1.80)

                pat_name = None
                if is_butterfly:
                    pat_name = "Bearish Butterfly Harmonic"
                elif is_bat:
                    pat_name = "Bearish Bat Harmonic"
                elif is_gartley:
                    pat_name = "Bearish Gartley Harmonic"

                if pat_name:
                    d_price = D["price"]
                    entry = round(cur_price if abs(cur_price - d_price) < 40.0 else d_price, 1)
                    target_dist = max(45.0, cd * 0.50)
                    target = round(entry - target_dist, 1)
                    sl_dist = max(20.0, cd * 0.20)
                    stop = round(d_price + sl_dist, 1)
                    rr = round(target_dist / max(1.0, sl_dist), 1)

                    status = "PRZ_REVERSAL" if cur_price <= d_price else "TESTING_TRIGGER"
                    span_str = self._format_span(X["time_raw"], D["time_raw"])

                    drawing_shapes = [
                        {"id": f"harm_{start}_xa", "type": "line", "time1": X["time"], "price1": X["price"], "time2": A["time"], "price2": A["price"], "color": "#f59e0b", "width": "2", "remark": f"XA Leg (₹{xa:.1f} pts)"},
                        {"id": f"harm_{start}_ab", "type": "line", "time1": A["time"], "price1": A["price"], "time2": B["time"], "price2": B["price"], "color": "#f59e0b", "width": "2", "remark": f"AB ({ab_xa:.3f})"},
                        {"id": f"harm_{start}_bc", "type": "line", "time1": B["time"], "price1": B["price"], "time2": C["time"], "price2": C["price"], "color": "#f59e0b", "width": "2", "remark": f"BC ({bc_ab:.3f})"},
                        {"id": f"harm_{start}_cd", "type": "line", "time1": C["time"], "price1": C["price"], "time2": D["time"], "price2": D["price"], "color": "#ef4444", "width": "3", "remark": f"CD ({cd_bc:.2f} PRZ Short)"},
                        {"id": f"harm_{start}_box", "type": "target_sl", "entry": entry, "target": target, "stop": stop, "timeStart": D["time"], "timeEnd": D["time"] + self._get_future_time_span(timeframe, 25), "color": "#ef4444", "remark": f"AI {pat_name}"}
                    ]

                    patterns.append({
                        "id": f"pat_harmonic_bear_{D['bar_idx']}",
                        "name": pat_name,
                        "type": "harmonic",
                        "direction": "SELL (PUT)",
                        "timeframe": timeframe,
                        "status": status,
                        "entry_price": entry,
                        "target_price": target,
                        "stop_loss": stop,
                        "risk_reward": f"1 : {rr}",
                        "span_str": span_str,
                        "end_bar_idx": D["bar_idx"],
                        "ratios": {
                            "AB_XA": round(ab_xa, 3),
                            "BC_AB": round(bc_ab, 3),
                            "CD_BC": round(cd_bc, 3),
                            "CD_XA": round(cd_xa, 3)
                        },
                        "points": [
                            {"label": "X", "time": X["time"], "price": X["price"]},
                            {"label": "A", "time": A["time"], "price": A["price"]},
                            {"label": "B", "time": B["time"], "price": B["price"]},
                            {"label": "C", "time": C["time"], "price": C["price"]},
                            {"label": "D (PRZ)", "time": D["time"], "price": D["price"]},
                        ],
                        "drawing_shapes": drawing_shapes
                    })

        return patterns

    # =========================================================================
    # 2. HEAD & SHOULDERS (STANDARD & INVERSE WITH SLANTED NECKLINE)
    # =========================================================================
    def _detect_head_and_shoulders(
        self,
        swings: List[Dict[str, Any]],
        df: pd.DataFrame,
        cur_price: float,
        timeframe: str
    ) -> List[Dict[str, Any]]:
        patterns = []
        n_swings = len(swings)
        if n_swings < 5:
            return patterns

        cur_bar = len(df) - 1
        scan_count = min(35, n_swings - 4)

        for start in range(n_swings - scan_count - 4, n_swings - 4):
            if start < 0:
                continue
            s1, s2, s3, s4, s5 = swings[start : start + 5]

            # ----------------------------------------------------
            # STANDARD HEAD & SHOULDERS (Bearish Reversal)
            # s1=Peak1 (LS), s2=Trough1, s3=Peak2 (Head), s4=Trough2, s5=Peak3 (RS)
            # ----------------------------------------------------
            if s1["type"] == "H" and s2["type"] == "L" and s3["type"] == "H" and s4["type"] == "L" and s5["type"] == "H":
                ls, t1, head, t2, rs = s1, s2, s3, s4, s5

                # Head must be strictly higher than both shoulders
                if head["price"] > ls["price"] + 15.0 and head["price"] > rs["price"] + 15.0:
                    head_height = head["price"] - max(t1["price"], t2["price"])
                    shoulder_diff = abs(ls["price"] - rs["price"])

                    if head_height >= 30.0 and (shoulder_diff / head_height) < 0.45:
                        # Slanted Neckline calculation (Line connecting t1 and t2)
                        bar_delta = max(1, t2["bar_idx"] - t1["bar_idx"])
                        slope = (t2["price"] - t1["price"]) / bar_delta
                        proj_bars = cur_bar - t2["bar_idx"]
                        neckline_cur = round(t2["price"] + (slope * proj_bars), 1)

                        is_broken = cur_price < neckline_cur
                        status = "CONFIRMED_BREAKOUT" if is_broken else "TESTING_NECKLINE"

                        entry = round(neckline_cur, 1)
                        target = round(neckline_cur - (head_height * 0.90), 1)
                        # Structural invalidation: right shoulder pullback or max 38% head depth buffer
                        sl_dist = max(20.0, min(abs(rs["price"] - entry) + 10.0, round(head_height * 0.38, 1)))
                        stop = round(entry + sl_dist, 1)
                        rr = round(abs(entry - target) / max(1.0, abs(stop - entry)), 1)
                        span_str = self._format_span(ls["time_raw"], rs["time_raw"])

                        ext_time = _to_unix_sec(df.index[min(len(df) - 1, t2["bar_idx"] + 20)])
                        ext_price = round(t2["price"] + (slope * 20), 1)

                        drawing_shapes = [
                            {"id": f"hns_{start}_ls_head", "type": "line", "time1": ls["time"], "price1": ls["price"], "time2": head["time"], "price2": head["price"], "color": "#f87171", "width": "2", "remark": "H&S Left Shoulder -> Head"},
                            {"id": f"hns_{start}_head_rs", "type": "line", "time1": head["time"], "price1": head["price"], "time2": rs["time"], "price2": rs["price"], "color": "#f87171", "width": "2", "remark": "H&S Head -> Right Shoulder"},
                            {"id": f"hns_{start}_neckline", "type": "line", "time1": t1["time"], "price1": t1["price"], "time2": ext_time, "price2": ext_price, "color": "#ef4444", "width": "3", "remark": f"Slanted Neckline ({slope:+.1f} pts/bar)"},
                            {"id": f"hns_{start}_box", "type": "target_sl", "entry": entry, "target": target, "stop": stop, "timeStart": rs["time"], "timeEnd": rs["time"] + self._get_future_time_span(timeframe, 25), "color": "#ef4444", "remark": "AI Head & Shoulders"}
                        ]

                        patterns.append({
                            "id": f"pat_hns_{rs['bar_idx']}",
                            "name": "Head & Shoulders (Bearish Reversal)",
                            "type": "head_and_shoulders",
                            "direction": "SELL (PUT)",
                            "timeframe": timeframe,
                            "status": status,
                            "entry_price": entry,
                            "target_price": target,
                            "stop_loss": stop,
                            "risk_reward": f"1 : {rr}",
                            "span_str": span_str,
                            "end_bar_idx": rs["bar_idx"],
                            "neckline_slope": round(slope, 3),
                            "points": [
                                {"label": "Left Shoulder", "time": ls["time"], "price": ls["price"]},
                                {"label": "Trough 1", "time": t1["time"], "price": t1["price"]},
                                {"label": "Head", "time": head["time"], "price": head["price"]},
                                {"label": "Trough 2", "time": t2["time"], "price": t2["price"]},
                                {"label": "Right Shoulder", "time": rs["time"], "price": rs["price"]},
                            ],
                            "drawing_shapes": drawing_shapes
                        })

            # ----------------------------------------------------
            # INVERSE HEAD & SHOULDERS (Bullish Reversal)
            # s1=Trough1 (LS), s2=Peak1, s3=Trough2 (Head), s4=Peak2, s5=Trough3 (RS)
            # ----------------------------------------------------
            elif s1["type"] == "L" and s2["type"] == "H" and s3["type"] == "L" and s4["type"] == "H" and s5["type"] == "L":
                ls, p1, head, p2, rs = s1, s2, s3, s4, s5

                # Head must be strictly lower than both shoulders
                if head["price"] < ls["price"] - 15.0 and head["price"] < rs["price"] - 15.0:
                    head_depth = min(p1["price"], p2["price"]) - head["price"]
                    shoulder_diff = abs(ls["price"] - rs["price"])

                    if head_depth >= 30.0 and (shoulder_diff / head_depth) < 0.45:
                        bar_delta = max(1, p2["bar_idx"] - p1["bar_idx"])
                        slope = (p2["price"] - p1["price"]) / bar_delta
                        proj_bars = cur_bar - p2["bar_idx"]
                        neckline_cur = round(p2["price"] + (slope * proj_bars), 1)

                        is_broken = cur_price > neckline_cur
                        status = "CONFIRMED_BREAKOUT" if is_broken else "TESTING_NECKLINE"

                        entry = round(neckline_cur, 1)
                        target = round(neckline_cur + (head_depth * 0.90), 1)
                        # Structural invalidation: right shoulder pullback or max 38% head depth buffer
                        sl_dist = max(20.0, min(abs(entry - rs["price"]) + 10.0, round(head_depth * 0.38, 1)))
                        stop = round(entry - sl_dist, 1)
                        rr = round(abs(target - entry) / max(1.0, abs(entry - stop)), 1)
                        span_str = self._format_span(ls["time_raw"], rs["time_raw"])

                        ext_time = _to_unix_sec(df.index[min(len(df) - 1, p2["bar_idx"] + 20)])
                        ext_price = round(p2["price"] + (slope * 20), 1)

                        drawing_shapes = [
                            {"id": f"inv_hns_{start}_ls_head", "type": "line", "time1": ls["time"], "price1": ls["price"], "time2": head["time"], "price2": head["price"], "color": "#4ade80", "width": "2", "remark": "Inv H&S Left Shoulder -> Head"},
                            {"id": f"inv_hns_{start}_head_rs", "type": "line", "time1": head["time"], "price1": head["price"], "time2": rs["time"], "price2": rs["price"], "color": "#4ade80", "width": "2", "remark": "Inv H&S Head -> Right Shoulder"},
                            {"id": f"inv_hns_{start}_neckline", "type": "line", "time1": p1["time"], "price1": p1["price"], "time2": ext_time, "price2": ext_price, "color": "#22c55e", "width": "3", "remark": f"Slanted Neckline ({slope:+.1f} pts/bar)"},
                            {"id": f"inv_hns_{start}_box", "type": "target_sl", "entry": entry, "target": target, "stop": stop, "timeStart": rs["time"], "timeEnd": rs["time"] + self._get_future_time_span(timeframe, 25), "color": "#22c55e", "remark": "AI Inverse H&S"}
                        ]

                        patterns.append({
                            "id": f"pat_inv_hns_{rs['bar_idx']}",
                            "name": "Inverse Head & Shoulders (Bullish Reversal)",
                            "type": "head_and_shoulders",
                            "direction": "BUY (CALL)",
                            "timeframe": timeframe,
                            "status": status,
                            "entry_price": entry,
                            "target_price": target,
                            "stop_loss": stop,
                            "risk_reward": f"1 : {rr}",
                            "span_str": span_str,
                            "end_bar_idx": rs["bar_idx"],
                            "neckline_slope": round(slope, 3),
                            "points": [
                                {"label": "Left Shoulder", "time": ls["time"], "price": ls["price"]},
                                {"label": "Peak 1", "time": p1["time"], "price": p1["price"]},
                                {"label": "Head", "time": head["time"], "price": head["price"]},
                                {"label": "Peak 2", "time": p2["time"], "price": p2["price"]},
                                {"label": "Right Shoulder", "time": rs["time"], "price": rs["price"]},
                            ],
                            "drawing_shapes": drawing_shapes
                        })

        return patterns

    # =========================================================================
    # 3. SLANTED TRENDLINE BREAKOUTS (TRIANGLES, WEDGES & CHANNELS)
    # =========================================================================
    def _detect_triangles_and_wedges(
        self,
        swings: List[Dict[str, Any]],
        df: pd.DataFrame,
        cur_price: float,
        timeframe: str
    ) -> List[Dict[str, Any]]:
        patterns = []
        recent_highs = [s for s in swings if s["type"] == "H"][-5:]
        recent_lows = [s for s in swings if s["type"] == "L"][-5:]

        if len(recent_highs) < 2 or len(recent_lows) < 2:
            return patterns

        h1, h2 = recent_highs[-2], recent_highs[-1]
        l1, l2 = recent_lows[-2], recent_lows[-1]

        cur_bar = len(df) - 1
        h_bars = max(1, h2["bar_idx"] - h1["bar_idx"])
        l_bars = max(1, l2["bar_idx"] - l1["bar_idx"])

        slope_high = (h2["price"] - h1["price"]) / h_bars
        slope_low = (l2["price"] - l1["price"]) / l_bars

        # Extrapolate to current candle
        res_cur = round(h2["price"] + slope_high * (cur_bar - h2["bar_idx"]), 1)
        sup_cur = round(l2["price"] + slope_low * (cur_bar - l2["bar_idx"]), 1)

        base_height = abs(h1["price"] - l1["price"])
        if base_height < 30.0:
            return patterns

        pat_name = None
        direction = None
        is_buy = False

        if abs(slope_high) < 0.20 and slope_low > 0.20:
            pat_name = "Ascending Triangle Breakout"
            direction = "BUY (CALL)"
            is_buy = True
        elif abs(slope_low) < 0.20 and slope_high < -0.20:
            pat_name = "Descending Triangle Breakdown"
            direction = "SELL (PUT)"
            is_buy = False
        elif slope_high < -0.12 and slope_low > 0.12:
            pat_name = "Symmetrical Triangle"
            is_buy = cur_price >= res_cur
            direction = "BUY (CALL)" if is_buy else "SELL (PUT)"
        elif slope_high < -0.25 and slope_low < -0.08 and (slope_high < slope_low):
            pat_name = "Falling Wedge (Bullish Reversal)"
            direction = "BUY (CALL)"
            is_buy = True
        elif slope_high > 0.08 and slope_low > 0.25 and (slope_low > slope_high):
            pat_name = "Rising Wedge (Bearish Reversal)"
            direction = "SELL (PUT)"
            is_buy = False

        if pat_name:
            if is_buy:
                is_broken = cur_price > res_cur
                entry = round(res_cur, 1)
                target = round(res_cur + (base_height * 0.85), 1)
                # Invalidation: If price drops back 35% of pattern height, breakout has failed
                sl_dist = max(20.0, round(base_height * 0.35, 1))
                stop = round(entry - sl_dist, 1)
            else:
                is_broken = cur_price < sup_cur
                entry = round(sup_cur, 1)
                target = round(sup_cur - (base_height * 0.85), 1)
                # Invalidation: If price rallies back 35% of pattern height, breakdown has failed
                sl_dist = max(20.0, round(base_height * 0.35, 1))
                stop = round(entry + sl_dist, 1)

            status = "CONFIRMED_BREAKOUT" if is_broken else "TESTING_TRIGGER"
            rr_val = round(abs(target - entry) / max(1.0, abs(stop - entry)), 1)
            span_str = self._format_span(min(h1["time_raw"], l1["time_raw"]), max(h2["time_raw"], l2["time_raw"]))

            ext_time = _to_unix_sec(df.index[min(len(df) - 1, max(h2["bar_idx"], l2["bar_idx"]) + 20)])
            ext_res = round(h2["price"] + slope_high * 20, 1)
            ext_sup = round(l2["price"] + slope_low * 20, 1)

            drawing_shapes = [
                {"id": f"tri_res_{cur_bar}", "type": "line", "time1": h1["time"], "price1": h1["price"], "time2": ext_time, "price2": ext_res, "color": "#ef4444" if not is_buy else "#f59e0b", "width": "2", "remark": f"Slanted Resistance ({slope_high:+.1f} pts/bar)"},
                {"id": f"tri_sup_{cur_bar}", "type": "line", "time1": l1["time"], "price1": l1["price"], "time2": ext_time, "price2": ext_sup, "color": "#22c55e" if is_buy else "#38bdf8", "width": "2", "remark": f"Slanted Support ({slope_low:+.1f} pts/bar)"},
                {"id": f"tri_box_{cur_bar}", "type": "target_sl", "entry": entry, "target": target, "stop": stop, "timeStart": max(h2["time"], l2["time"]), "timeEnd": max(h2["time"], l2["time"]) + self._get_future_time_span(timeframe, 20), "color": "#22c55e" if is_buy else "#ef4444", "remark": f"AI {pat_name}"}
            ]

            patterns.append({
                "id": f"pat_triangle_{cur_bar}",
                "name": pat_name,
                "type": "triangle",
                "direction": direction,
                "timeframe": timeframe,
                "status": status,
                "entry_price": entry,
                "target_price": target,
                "stop_loss": stop,
                "risk_reward": f"1 : {rr_val}",
                "span_str": span_str,
                "end_bar_idx": max(h2["bar_idx"], l2["bar_idx"]),
                "points": [
                    {"label": "Resistance High 1", "time": h1["time"], "price": h1["price"]},
                    {"label": "Resistance High 2", "time": h2["time"], "price": h2["price"]},
                    {"label": "Support Low 1", "time": l1["time"], "price": l1["price"]},
                    {"label": "Support Low 2", "time": l2["time"], "price": l2["price"]},
                ],
                "drawing_shapes": drawing_shapes
            })

        return patterns

    # =========================================================================
    # 4. DOUBLE TOPS (M) & DOUBLE BOTTOMS (W)
    # =========================================================================
    def _detect_double_tops_bottoms(
        self,
        swings: List[Dict[str, Any]],
        df: pd.DataFrame,
        cur_price: float,
        timeframe: str
    ) -> List[Dict[str, Any]]:
        patterns = []
        n_swings = len(swings)
        if n_swings < 3:
            return patterns

        scan_count = min(15, n_swings - 2)
        for i in range(n_swings - scan_count - 2, n_swings - 2):
            if i < 0:
                continue
            s1, s2, s3 = swings[i : i + 3]

            # Double Top (M-Pattern)
            if s1["type"] == "H" and s2["type"] == "L" and s3["type"] == "H":
                top_diff = abs(s1["price"] - s3["price"])
                valley_depth = min(s1["price"], s3["price"]) - s2["price"]
                if valley_depth >= 30.0 and (top_diff / valley_depth) < 0.25:
                    neckline = s2["price"]
                    is_broken = cur_price < neckline
                    status = "CONFIRMED_BREAKOUT" if is_broken else "TESTING_NECKLINE"

                    entry = round(neckline, 1)
                    target = round(neckline - (valley_depth * 0.85), 1)
                    # Structural invalidation: price rallying 35% back above neckline invalidates breakdown
                    sl_dist = max(20.0, round(valley_depth * 0.35, 1))
                    stop = round(entry + sl_dist, 1)
                    rr = round(abs(entry - target) / max(1.0, abs(stop - entry)), 1)
                    span_str = self._format_span(s1["time_raw"], s3["time_raw"])

                    drawing_shapes = [
                        {"id": f"dt_{i}_line", "type": "line", "time1": s1["time"], "price1": s1["price"], "time2": s3["time"], "price2": s3["price"], "color": "#ef4444", "width": "2", "remark": "Double Top Resistance"},
                        {"id": f"dt_{i}_neck", "type": "line", "time1": s2["time"], "price1": s2["price"], "time2": s3["time"] + self._get_future_time_span(timeframe, 15), "price2": s2["price"], "color": "#f87171", "width": "2", "remark": f"Neckline (₹{neckline})"},
                        {"id": f"dt_{i}_box", "type": "target_sl", "entry": entry, "target": target, "stop": stop, "timeStart": s3["time"], "timeEnd": s3["time"] + self._get_future_time_span(timeframe, 20), "color": "#ef4444", "remark": "AI Double Top Breakdown"}
                    ]

                    patterns.append({
                        "id": f"pat_dt_{s3['bar_idx']}",
                        "name": "Double Top (M-Pattern Breakdown)",
                        "type": "double_top_bottom",
                        "direction": "SELL (PUT)",
                        "timeframe": timeframe,
                        "status": status,
                        "entry_price": entry,
                        "target_price": target,
                        "stop_loss": stop,
                        "risk_reward": f"1 : {rr}",
                        "span_str": span_str,
                        "end_bar_idx": s3["bar_idx"],
                        "points": [
                            {"label": "Peak 1", "time": s1["time"], "price": s1["price"]},
                            {"label": "Valley Neckline", "time": s2["time"], "price": s2["price"]},
                            {"label": "Peak 2", "time": s3["time"], "price": s3["price"]},
                        ],
                        "drawing_shapes": drawing_shapes
                    })

            # Double Bottom (W-Pattern)
            elif s1["type"] == "L" and s2["type"] == "H" and s3["type"] == "L":
                bottom_diff = abs(s1["price"] - s3["price"])
                peak_height = s2["price"] - max(s1["price"], s3["price"])
                if peak_height >= 30.0 and (bottom_diff / peak_height) < 0.25:
                    neckline = s2["price"]
                    is_broken = cur_price > neckline
                    status = "CONFIRMED_BREAKOUT" if is_broken else "TESTING_NECKLINE"

                    entry = round(neckline, 1)
                    target = round(neckline + (peak_height * 0.85), 1)
                    # Structural invalidation: price dropping 35% back below neckline invalidates breakout
                    sl_dist = max(20.0, round(peak_height * 0.35, 1))
                    stop = round(entry - sl_dist, 1)
                    rr = round(abs(target - entry) / max(1.0, abs(entry - stop)), 1)
                    span_str = self._format_span(s1["time_raw"], s3["time_raw"])

                    drawing_shapes = [
                        {"id": f"db_{i}_line", "type": "line", "time1": s1["time"], "price1": s1["price"], "time2": s3["time"], "price2": s3["price"], "color": "#22c55e", "width": "2", "remark": "Double Bottom Support"},
                        {"id": f"db_{i}_neck", "type": "line", "time1": s2["time"], "price1": s2["price"], "time2": s3["time"] + self._get_future_time_span(timeframe, 15), "price2": s2["price"], "color": "#4ade80", "width": "2", "remark": f"Neckline (₹{neckline})"},
                        {"id": f"db_{i}_box", "type": "target_sl", "entry": entry, "target": target, "stop": stop, "timeStart": s3["time"], "timeEnd": s3["time"] + self._get_future_time_span(timeframe, 20), "color": "#22c55e", "remark": "AI Double Bottom Breakout"}
                    ]

                    patterns.append({
                        "id": f"pat_db_{s3['bar_idx']}",
                        "name": "Double Bottom (W-Pattern Breakout)",
                        "type": "double_top_bottom",
                        "direction": "BUY (CALL)",
                        "timeframe": timeframe,
                        "status": status,
                        "entry_price": entry,
                        "target_price": target,
                        "stop_loss": stop,
                        "risk_reward": f"1 : {rr}",
                        "span_str": span_str,
                        "end_bar_idx": s3["bar_idx"],
                        "points": [
                            {"label": "Trough 1", "time": s1["time"], "price": s1["price"]},
                            {"label": "Peak Neckline", "time": s2["time"], "price": s2["price"]},
                            {"label": "Trough 2", "time": s3["time"], "price": s3["price"]},
                        ],
                        "drawing_shapes": drawing_shapes
                    })

        return patterns

    # =========================================================================
    # HELPER FORMATTING UTILITIES
    # =========================================================================
    def _format_span(self, start_t: Any, end_t: Any) -> str:
        """Formats multi-day span human readable string."""
        try:
            d1 = pd.to_datetime(start_t)
            d2 = pd.to_datetime(end_t)
            days = abs((d2.date() - d1.date()).days)
            d1_str = d1.strftime("%d-%b")
            d2_str = d2.strftime("%d-%b")
            if days <= 0:
                return f"Intraday ({d1_str})"
            return f"{days + 1} trading days ({d1_str} to {d2_str})"
        except Exception:
            return "Multi-Day Span"

    def _get_future_time_span(self, timeframe: str, num_bars: int = 20) -> int:
        tf = timeframe.lower()
        if "1d" in tf:
            return 86400 * num_bars
        if "1h" in tf or "60m" in tf:
            return 3600 * num_bars
        if "15m" in tf:
            return 900 * num_bars
        return 300 * num_bars  # 5m

    def scan_all_timeframes(
        self,
        engine_obj: Any,
        cur_price: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Scans all 4 timeframes (5m, 15m, 1h, 1d) concurrently.
        Returns active natural patterns, breakout alerts, and aggregated shapes.
        Strictly zero forced patterns: returns None if natural structure is not present.
        """
        cur_p = float(cur_price or getattr(engine_obj, "latest_price", 22750.0) or 22750.0)
        timeframes = ["5m", "15m", "1h", "1d"]
        results = {}
        all_shapes = []
        breakout_count = 0
        breakout_alerts = []

        for tf in timeframes:
            try:
                snap = engine_obj.get_snapshot(timeframe=tf)
                df_tf = snap.get("df", pd.DataFrame()) if isinstance(snap, dict) else pd.DataFrame()
                if df_tf.empty and tf == "5m":
                    df_tf = getattr(engine_obj, "latest_df_5m", pd.DataFrame())

                pats = self.detect_all_patterns(df_tf, timeframe=tf, cur_price=cur_p)
                primary = pats[0] if pats else None

                if primary:
                    is_bo = primary.get("status") == "CONFIRMED_BREAKOUT"
                    if is_bo:
                        breakout_count += 1
                        breakout_alerts.append(f"{tf.upper()}: {primary['name']} ({primary['direction']})")

                    # Add timeframe prefix to remarks for multi-timeframe chart overlay
                    shapes_with_tf = []
                    for s in primary.get("drawing_shapes", []):
                        sc = dict(s)
                        sc["timeframe"] = tf
                        if "remark" in sc and sc["remark"]:
                            if not sc["remark"].startswith(f"[{tf.upper()}]"):
                                sc["remark"] = f"[{tf.upper()}] {sc['remark']}"
                        shapes_with_tf.append(sc)
                    
                    primary["drawing_shapes"] = shapes_with_tf
                    all_shapes.extend(shapes_with_tf)

                    results[tf] = {
                        "has_pattern": True,
                        "pattern": primary,
                        "primary_pattern": primary,
                        "active_patterns": pats,
                        "other_patterns_count": max(0, len(pats) - 1),
                        "status": primary.get("status"),
                        "is_breakout": is_bo
                    }
                else:
                    results[tf] = {
                        "has_pattern": False,
                        "pattern": None,
                        "primary_pattern": None,
                        "active_patterns": [],
                        "message": "Rangebound Consolidation (No Natural Pattern)",
                        "status": "CONSOLIDATION",
                        "is_breakout": False
                    }
            except Exception as e:
                logger.debug("Error scanning timeframe %s: %s", tf, e)
                results[tf] = {
                    "has_pattern": False,
                    "pattern": None,
                    "primary_pattern": None,
                    "active_patterns": [],
                    "message": "Consolidation",
                    "status": "CONSOLIDATION",
                    "is_breakout": False
                }

        total_active = sum(1 for v in results.values() if v.get("has_pattern"))
        return {
            "status": "ok",
            "spot_price": cur_p,
            "total_active_patterns": total_active,
            "breakout_count": breakout_count,
            "active_breakouts_count": breakout_count,
            "breakout_alerts": breakout_alerts,
            "timeframes": results,
            "all_drawing_shapes": all_shapes,
            "timestamp": datetime.now(IST).strftime("%H:%M:%S")
        }


# Global Singleton instance
_detector_instance: Optional[PatternDetector] = None

def get_pattern_detector() -> PatternDetector:
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = PatternDetector()
    return _detector_instance
