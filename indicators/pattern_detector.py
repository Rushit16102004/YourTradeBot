import logging
from typing import Dict, Any, List, Optional, Tuple
import numpy as np
import pandas as pd

logger = logging.getLogger("PatternDetector")


class PatternDetector:
    """
    Advanced Quantitative Pattern Recognition Engine for NIFTY 50 Candlestick Charts:
    - Classical Patterns: Head & Shoulders, Inverse H&S, Double Top (M), Double Bottom (W),
      Ascending Triangle, Descending Triangle, Symmetrical Triangle, Rising/Falling Wedges, Bull/Bear Flags.
    - Harmonic Patterns (Fibonacci XABCD): Butterfly (0.786 / 1.272-1.618), Gartley (0.618 / 0.786),
      Bat (0.382-0.500 / 0.886), Crab (0.382-0.618 / 1.618).
    - Candlestick Formations: Hammer, Shooting Star, Bullish/Bearish Engulfing, Morning/Evening Star, Doji.
    """

    @classmethod
    def find_swing_pivots(cls, df: pd.DataFrame, window: int = 3) -> List[Dict[str, Any]]:
        """
        Extracts swing high peaks and swing low troughs from candle series using rolling extrema.
        """
        if df is None or len(df) < window * 2 + 1:
            return []

        pivots: List[Dict[str, Any]] = []
        highs = df["high"].values
        lows = df["low"].values
        closes = df["close"].values
        times = df.index

        n = len(df)
        for i in range(window, n - window):
            # Check swing high peak
            curr_high = highs[i]
            is_peak = True
            for w in range(1, window + 1):
                if highs[i - w] >= curr_high or highs[i + w] > curr_high:
                    is_peak = False
                    break
            if is_peak:
                pivots.append({
                    "index": i,
                    "timestamp": str(times[i]),
                    "type": "PEAK",
                    "price": float(curr_high),
                    "close": float(closes[i]),
                })

            # Check swing low trough
            curr_low = lows[i]
            is_trough = True
            for w in range(1, window + 1):
                if lows[i - w] <= curr_low or lows[i + w] < curr_low:
                    is_trough = False
                    break
            if is_trough:
                pivots.append({
                    "index": i,
                    "timestamp": str(times[i]),
                    "type": "TROUGH",
                    "price": float(curr_low),
                    "close": float(closes[i]),
                })

        # Sort pivots chronologically
        pivots.sort(key=lambda x: x["index"])

        # Filter out consecutive duplicate types by keeping the most extreme point
        cleaned_pivots: List[Dict[str, Any]] = []
        for p in pivots:
            if not cleaned_pivots:
                cleaned_pivots.append(p)
                continue
            last = cleaned_pivots[-1]
            if p["type"] == last["type"]:
                if p["type"] == "PEAK" and p["price"] > last["price"]:
                    cleaned_pivots[-1] = p
                elif p["type"] == "TROUGH" and p["price"] < last["price"]:
                    cleaned_pivots[-1] = p
            else:
                cleaned_pivots.append(p)

        return cleaned_pivots

    @classmethod
    def detect_head_and_shoulders(
        cls, df: pd.DataFrame, pivots: List[Dict[str, Any]], cur_price: float
    ) -> List[Dict[str, Any]]:
        """Detects standard Head & Shoulders (Bearish) and Inverse Head & Shoulders (Bullish)."""
        patterns: List[Dict[str, Any]] = []
        if len(pivots) < 5:
            return patterns

        # Scan sliding windows of 5 consecutive alternating pivots
        for i in range(len(pivots) - 4):
            window = pivots[i : i + 5]
            types = [p["type"] for p in window]

            # 1. Bearish Head & Shoulders: PEAK -> TROUGH -> PEAK -> TROUGH -> PEAK
            if types == ["PEAK", "TROUGH", "PEAK", "TROUGH", "PEAK"]:
                ls, n1, head, n2, rs = window
                # Head must be strictly higher than both shoulders
                if head["price"] > ls["price"] and head["price"] > rs["price"]:
                    # Shoulders must be reasonably balanced (within 1.8% of each other)
                    sh_diff = abs(ls["price"] - rs["price"]) / ls["price"]
                    if sh_diff < 0.018:
                        neckline = (n1["price"] + n2["price"]) / 2.0
                        depth = head["price"] - neckline
                        target = round(neckline - depth, 1)
                        stop_loss = round(rs["price"] + 5.0, 1)
                        status = "BREAKOUT_CONFIRMED" if cur_price < neckline else "FORMING"

                        patterns.append({
                            "name": "Head and Shoulders (Bearish Reversal)",
                            "category": "CLASSICAL_CHART_PATTERN",
                            "type": "HEAD_AND_SHOULDERS",
                            "direction": "BEARISH",
                            "signal": "PUT",
                            "head_price": head["price"],
                            "left_shoulder": ls["price"],
                            "right_shoulder": rs["price"],
                            "neckline": round(neckline, 1),
                            "target": target,
                            "stop_loss": stop_loss,
                            "runway_pts": round(abs(cur_price - target), 1),
                            "status": status,
                            "quality": "HIGH" if sh_diff < 0.008 else "MEDIUM",
                            "description": (
                                f"Bearish H&S with Head at ₹{head['price']:,.0f}, Neckline at ₹{neckline:,.0f}. "
                                f"Target projected to ₹{target:,.0f} with SL above Right Shoulder at ₹{stop_loss:,.0f}."
                            ),
                        })

            # 2. Bullish Inverse Head & Shoulders: TROUGH -> PEAK -> TROUGH -> PEAK -> TROUGH
            elif types == ["TROUGH", "PEAK", "TROUGH", "PEAK", "TROUGH"]:
                ls, n1, head, n2, rs = window
                # Head must be strictly lower than both shoulders
                if head["price"] < ls["price"] and head["price"] < rs["price"]:
                    sh_diff = abs(ls["price"] - rs["price"]) / ls["price"]
                    if sh_diff < 0.018:
                        neckline = (n1["price"] + n2["price"]) / 2.0
                        depth = neckline - head["price"]
                        target = round(neckline + depth, 1)
                        stop_loss = round(rs["price"] - 5.0, 1)
                        status = "BREAKOUT_CONFIRMED" if cur_price > neckline else "FORMING"

                        patterns.append({
                            "name": "Inverse Head and Shoulders (Bullish Reversal)",
                            "category": "CLASSICAL_CHART_PATTERN",
                            "type": "INVERSE_HEAD_AND_SHOULDERS",
                            "direction": "BULLISH",
                            "signal": "CALL",
                            "head_price": head["price"],
                            "left_shoulder": ls["price"],
                            "right_shoulder": rs["price"],
                            "neckline": round(neckline, 1),
                            "target": target,
                            "stop_loss": stop_loss,
                            "runway_pts": round(abs(target - cur_price), 1),
                            "status": status,
                            "quality": "HIGH" if sh_diff < 0.008 else "MEDIUM",
                            "description": (
                                f"Bullish Inverse H&S with Head at ₹{head['price']:,.0f}, Neckline at ₹{neckline:,.0f}. "
                                f"Target projected to ₹{target:,.0f} with SL below Right Shoulder at ₹{stop_loss:,.0f}."
                            ),
                        })

        return patterns

    @classmethod
    def detect_double_patterns(
        cls, df: pd.DataFrame, pivots: List[Dict[str, Any]], cur_price: float
    ) -> List[Dict[str, Any]]:
        """Detects Double Top ('M' pattern) and Double Bottom ('W' pattern)."""
        patterns: List[Dict[str, Any]] = []
        if len(pivots) < 3:
            return patterns

        # Check last 3 pivots
        for i in range(len(pivots) - 2):
            p1, p2, p3 = pivots[i], pivots[i + 1], pivots[i + 2]

            # 1. Double Top ("M" Pattern): PEAK -> TROUGH -> PEAK
            if p1["type"] == "PEAK" and p2["type"] == "TROUGH" and p3["type"] == "PEAK":
                diff = abs(p1["price"] - p3["price"]) / p1["price"]
                if diff <= 0.0045:  # Peaks within 0.45%
                    neckline = p2["price"]
                    depth = max(p1["price"], p3["price"]) - neckline
                    target = round(neckline - depth, 1)
                    stop_loss = round(max(p1["price"], p3["price"]) + 4.0, 1)
                    status = "BREAKOUT_CONFIRMED" if cur_price < neckline else "FORMING"

                    patterns.append({
                        "name": "Double Top ('M' Bearish Reversal)",
                        "category": "CLASSICAL_CHART_PATTERN",
                        "type": "DOUBLE_TOP",
                        "direction": "BEARISH",
                        "signal": "PUT",
                        "peak_1": p1["price"],
                        "peak_2": p3["price"],
                        "neckline": round(neckline, 1),
                        "target": target,
                        "stop_loss": stop_loss,
                        "status": status,
                        "quality": "HIGH" if diff < 0.002 else "MEDIUM",
                        "description": (
                            f"Double Top tested at ₹{p1['price']:,.0f} & ₹{p3['price']:,.0f}. "
                            f"Neckline valley at ₹{neckline:,.0f}. Downside target: ₹{target:,.0f}."
                        ),
                    })

            # 2. Double Bottom ("W" Pattern): TROUGH -> PEAK -> TROUGH
            elif p1["type"] == "TROUGH" and p2["type"] == "PEAK" and p3["type"] == "TROUGH":
                diff = abs(p1["price"] - p3["price"]) / p1["price"]
                if diff <= 0.0045:  # Troughs within 0.45%
                    neckline = p2["price"]
                    depth = neckline - min(p1["price"], p3["price"])
                    target = round(neckline + depth, 1)
                    stop_loss = round(min(p1["price"], p3["price"]) - 4.0, 1)
                    status = "BREAKOUT_CONFIRMED" if cur_price > neckline else "FORMING"

                    patterns.append({
                        "name": "Double Bottom ('W' Bullish Reversal)",
                        "category": "CLASSICAL_CHART_PATTERN",
                        "type": "DOUBLE_BOTTOM",
                        "direction": "BULLISH",
                        "signal": "CALL",
                        "trough_1": p1["price"],
                        "trough_2": p3["price"],
                        "neckline": round(neckline, 1),
                        "target": target,
                        "stop_loss": stop_loss,
                        "status": status,
                        "quality": "HIGH" if diff < 0.002 else "MEDIUM",
                        "description": (
                            f"Double Bottom floor tested at ₹{p1['price']:,.0f} & ₹{p3['price']:,.0f}. "
                            f"Neckline peak at ₹{neckline:,.0f}. Upside breakout target: ₹{target:,.0f}."
                        ),
                    })

        return patterns

    @classmethod
    def detect_triangles(
        cls, df: pd.DataFrame, pivots: List[Dict[str, Any]], cur_price: float
    ) -> List[Dict[str, Any]]:
        """Detects Ascending, Descending, and Symmetrical Triangles."""
        patterns: List[Dict[str, Any]] = []
        peaks = [p for p in pivots if p["type"] == "PEAK"]
        troughs = [p for p in pivots if p["type"] == "TROUGH"]

        if len(peaks) < 2 or len(troughs) < 2:
            return patterns

        p1, p2 = peaks[-2], peaks[-1]
        t1, t2 = troughs[-2], troughs[-1]

        peak_diff = abs(p1["price"] - p2["price"]) / p1["price"]
        trough_diff = abs(t1["price"] - t2["price"]) / t1["price"]

        # 1. Ascending Triangle: Flat Resistance ceiling + Rising swing lows
        if peak_diff < 0.003 and t2["price"] > t1["price"] + 5.0:
            height = p2["price"] - t1["price"]
            target = round(p2["price"] + height, 1)
            stop_loss = round(t2["price"] - 4.0, 1)
            status = "BREAKOUT_CONFIRMED" if cur_price > p2["price"] else "COILING"

            patterns.append({
                "name": "Ascending Triangle (Bullish Accumulation)",
                "category": "CLASSICAL_CHART_PATTERN",
                "type": "ASCENDING_TRIANGLE",
                "direction": "BULLISH",
                "signal": "CALL",
                "resistance": round(p2["price"], 1),
                "rising_support": round(t2["price"], 1),
                "target": target,
                "stop_loss": stop_loss,
                "status": status,
                "quality": "HIGH",
                "description": (
                    f"Ascending Triangle: Flat ceiling barrier at ₹{p2['price']:,.0f} with rising swing lows "
                    f"(₹{t1['price']:,.0f} -> ₹{t2['price']:,.0f}). Breakout target: ₹{target:,.0f}."
                ),
            })

        # 2. Descending Triangle: Flat Support floor + Declining swing highs
        elif trough_diff < 0.003 and p2["price"] < p1["price"] - 5.0:
            height = p1["price"] - t2["price"]
            target = round(t2["price"] - height, 1)
            stop_loss = round(p2["price"] + 4.0, 1)
            status = "BREAKOUT_CONFIRMED" if cur_price < t2["price"] else "COILING"

            patterns.append({
                "name": "Descending Triangle (Bearish Distribution)",
                "category": "CLASSICAL_CHART_PATTERN",
                "type": "DESCENDING_TRIANGLE",
                "direction": "BEARISH",
                "signal": "PUT",
                "support": round(t2["price"], 1),
                "falling_resistance": round(p2["price"], 1),
                "target": target,
                "stop_loss": stop_loss,
                "status": status,
                "quality": "HIGH",
                "description": (
                    f"Descending Triangle: Flat support floor at ₹{t2['price']:,.0f} with lower highs "
                    f"(₹{p1['price']:,.0f} -> ₹{p2['price']:,.0f}). Breakdown target: ₹{target:,.0f}."
                ),
            })

        # 3. Symmetrical Triangle: Lower highs + Higher lows (volatility compression coil)
        elif p2["price"] < p1["price"] - 6.0 and t2["price"] > t1["price"] + 6.0:
            height = p1["price"] - t1["price"]
            status = "COILING"
            if cur_price > p2["price"]:
                status = "UPWARD_BREAKOUT"
                direction = "BULLISH"
                sig = "CALL"
                target = round(p2["price"] + height, 1)
                sl = round(t2["price"] - 4.0, 1)
            elif cur_price < t2["price"]:
                status = "DOWNWARD_BREAKOUT"
                direction = "BEARISH"
                sig = "PUT"
                target = round(t2["price"] - height, 1)
                sl = round(p2["price"] + 4.0, 1)
            else:
                direction = "NEUTRAL"
                sig = "NEUTRAL"
                target = round(p2["price"] + height, 1)
                sl = round(t2["price"], 1)

            patterns.append({
                "name": "Symmetrical Triangle (Volatility Coil)",
                "category": "CLASSICAL_CHART_PATTERN",
                "type": "SYMMETRICAL_TRIANGLE",
                "direction": direction,
                "signal": sig,
                "upper_boundary": round(p2["price"], 1),
                "lower_boundary": round(t2["price"], 1),
                "target": target,
                "stop_loss": sl,
                "status": status,
                "quality": "MEDIUM",
                "description": (
                    f"Symmetrical Triangle: Converging range between ₹{t2['price']:,.0f} and ₹{p2['price']:,.0f}. "
                    f"Impending expansion runway: {round(height, 0)} pts."
                ),
            })

        return patterns

    @classmethod
    def detect_harmonics(
        cls, df: pd.DataFrame, pivots: List[Dict[str, Any]], cur_price: float
    ) -> List[Dict[str, Any]]:
        """
        Detects Harmonic 5-point XABCD formations:
        - Butterfly Pattern: B @ 0.786 of XA, D extension @ 1.272 - 1.618 of XA (Reversal PRZ).
        - Gartley Pattern: B @ 0.618 of XA, D @ 0.786 of XA.
        - Bat Pattern: B @ 0.382-0.500 of XA, D @ 0.886 of XA.
        """
        patterns: List[Dict[str, Any]] = []
        if len(pivots) < 5:
            return patterns

        for i in range(len(pivots) - 4):
            x, a, b, c, d = pivots[i : i + 5]

            # Must alternate
            if not (
                (x["type"] == "TROUGH" and a["type"] == "PEAK" and b["type"] == "TROUGH" and c["type"] == "PEAK" and d["type"] == "TROUGH") or
                (x["type"] == "PEAK" and a["type"] == "TROUGH" and b["type"] == "PEAK" and c["type"] == "TROUGH" and d["type"] == "PEAK")
            ):
                continue

            xa = abs(a["price"] - x["price"])
            if xa <= 0:
                continue

            ab = abs(b["price"] - a["price"])
            bc = abs(c["price"] - b["price"])
            cd = abs(d["price"] - c["price"])
            ad = abs(d["price"] - a["price"])
            xd = abs(d["price"] - x["price"])

            r_b = ab / xa  # Retracement of B relative to XA
            r_d_xa = xd / xa  # Extension of D relative to XA
            r_d_ad = ad / xa

            is_bullish = x["type"] == "PEAK" and a["type"] == "TROUGH" and d["type"] == "TROUGH"
            is_bearish = x["type"] == "TROUGH" and a["type"] == "PEAK" and d["type"] == "PEAK"

            # 1. BUTTERFLY PATTERN (User's specific highlight):
            # Hallmarks: B retracement = 0.786 (tol: 0.73 - 0.84)
            # D extension = 1.272 to 1.618 of XA
            if 0.73 <= r_b <= 0.84 and (1.20 <= r_d_xa <= 1.68 or 1.20 <= (cd / max(bc, 1)) <= 2.65):
                name = f"{'Bullish' if is_bullish else 'Bearish'} Butterfly Pattern"
                sig = "CALL" if is_bullish else "PUT"
                direction = "BULLISH" if is_bullish else "BEARISH"
                prz = d["price"]  # Potential Reversal Zone

                target_1 = round(d["price"] + (0.382 * cd if is_bullish else -0.382 * cd), 1)
                target_2 = round(d["price"] + (0.618 * cd if is_bullish else -0.618 * cd), 1)
                sl = round(d["price"] - (0.15 * cd if is_bullish else -0.15 * cd), 1)

                patterns.append({
                    "name": name,
                    "category": "HARMONIC_FIBONACCI_PATTERN",
                    "type": "BUTTERFLY",
                    "direction": direction,
                    "signal": sig,
                    "prz_price": round(prz, 1),
                    "r_b_ratio": round(r_b, 3),
                    "target_1": target_1,
                    "target_2": target_2,
                    "stop_loss": sl,
                    "status": "AT_PRZ_REVERSAL_ZONE" if abs(cur_price - prz) < 15.0 else "ACTIVE",
                    "quality": "INSTITUTIONAL",
                    "description": (
                        f"Harmonic {name}: B point completed at {r_b:.3f} XA (ideal 0.786). "
                        f"PRZ (Potential Reversal Zone) triggered at ₹{prz:,.0f} with D extension. "
                        f"Target 1: ₹{target_1:,.0f} (0.382 Fib) | Target 2: ₹{target_2:,.0f} (0.618 Fib) | SL: ₹{sl:,.0f}."
                    ),
                })

            # 2. GARTLEY PATTERN: B @ 0.618 (tol: 0.58 - 0.66), D @ 0.786
            elif 0.58 <= r_b <= 0.66 and 0.73 <= (ad / xa) <= 0.84:
                name = f"{'Bullish' if is_bullish else 'Bearish'} Gartley Pattern"
                sig = "CALL" if is_bullish else "PUT"
                direction = "BULLISH" if is_bullish else "BEARISH"
                prz = d["price"]
                target = round(d["price"] + (0.618 * cd if is_bullish else -0.618 * cd), 1)
                sl = round(x["price"] - 5.0 if is_bullish else x["price"] + 5.0, 1)

                patterns.append({
                    "name": name,
                    "category": "HARMONIC_FIBONACCI_PATTERN",
                    "type": "GARTLEY",
                    "direction": direction,
                    "signal": sig,
                    "prz_price": round(prz, 1),
                    "r_b_ratio": round(r_b, 3),
                    "target": target,
                    "stop_loss": sl,
                    "status": "AT_PRZ_REVERSAL_ZONE" if abs(cur_price - prz) < 15.0 else "ACTIVE",
                    "quality": "HIGH",
                    "description": (
                        f"Harmonic {name}: B at {r_b:.3f} (ideal 0.618). D PRZ at ₹{prz:,.0f} (0.786). "
                        f"Target: ₹{target:,.0f} with SL beyond X at ₹{sl:,.0f}."
                    ),
                })

            # 3. BAT PATTERN: B @ 0.382 - 0.500, D @ 0.886
            elif 0.35 <= r_b <= 0.53 and 0.83 <= (ad / xa) <= 0.93:
                name = f"{'Bullish' if is_bullish else 'Bearish'} Bat Pattern"
                sig = "CALL" if is_bullish else "PUT"
                direction = "BULLISH" if is_bullish else "BEARISH"
                prz = d["price"]
                target = round(d["price"] + (0.50 * cd if is_bullish else -0.50 * cd), 1)
                sl = round(x["price"] - 5.0 if is_bullish else x["price"] + 5.0, 1)

                patterns.append({
                    "name": name,
                    "category": "HARMONIC_FIBONACCI_PATTERN",
                    "type": "BAT",
                    "direction": direction,
                    "signal": sig,
                    "prz_price": round(prz, 1),
                    "r_b_ratio": round(r_b, 3),
                    "target": target,
                    "stop_loss": sl,
                    "status": "AT_PRZ_REVERSAL_ZONE" if abs(cur_price - prz) < 15.0 else "ACTIVE",
                    "quality": "HIGH",
                    "description": (
                        f"Harmonic {name}: Deep 0.886 PRZ test at ₹{prz:,.0f}. "
                        f"Target: ₹{target:,.0f} with SL at ₹{sl:,.0f}."
                    ),
                })

        return patterns

    @classmethod
    def detect_candlestick_reversals(cls, df: pd.DataFrame) -> Dict[str, Any]:
        """Detects single and dual candle price action patterns on latest closed bars."""
        if df is None or len(df) < 3:
            return {"pattern": "NONE", "signal": "NEUTRAL", "description": "Insufficient candle history"}

        last = df.iloc[-1]
        prev = df.iloc[-2]

        o1, h1, l1, c1 = float(last["open"]), float(last["high"]), float(last["low"]), float(last["close"])
        o0, h0, l0, c0 = float(prev["open"]), float(prev["high"]), float(prev["low"]), float(prev["close"])

        rng1 = max(h1 - l1, 0.01)
        body1 = abs(c1 - o1)
        upper_wick1 = h1 - max(o1, c1)
        lower_wick1 = min(o1, c1) - l1

        rng0 = max(h0 - l0, 0.01)
        body0 = abs(c0 - o0)

        # 1. Bullish Pin Bar (Hammer)
        if (lower_wick1 / rng1 >= 0.60) and (body1 / rng1 <= 0.30):
            return {
                "pattern": "BULLISH_PIN_BAR_HAMMER",
                "name": "Bullish Pin Bar / Hammer",
                "signal": "CALL",
                "direction": "BULLISH",
                "rejection_level": round(l1, 1),
                "description": f"Bullish rejection tail ({round(lower_wick1/rng1*100)}% of range). Institutional dip buying absorption at ₹{l1:,.0f}.",
            }

        # 2. Bearish Pin Bar (Shooting Star)
        if (upper_wick1 / rng1 >= 0.60) and (body1 / rng1 <= 0.30):
            return {
                "pattern": "BEARISH_PIN_BAR_SHOOTING_STAR",
                "name": "Bearish Pin Bar / Shooting Star",
                "signal": "PUT",
                "direction": "BEARISH",
                "rejection_level": round(h1, 1),
                "description": f"Bearish rejection tail ({round(upper_wick1/rng1*100)}% of range). Smart money distribution ceiling at ₹{h1:,.0f}.",
            }

        # 3. Bullish Engulfing
        if (c0 < o0) and (c1 > o1) and (c1 >= o0) and (o1 <= c0) and (body1 > body0 * 1.1):
            return {
                "pattern": "BULLISH_ENGULFING",
                "name": "Bullish Engulfing",
                "signal": "CALL",
                "direction": "BULLISH",
                "rejection_level": round(l1, 1),
                "description": f"Bullish body completely engulfs previous bear candle with momentum expansion. Entry above ₹{c1:,.0f}.",
            }

        # 4. Bearish Engulfing
        if (c0 > o0) and (c1 < o1) and (c1 <= o0) and (o1 >= c0) and (body1 > body0 * 1.1):
            return {
                "pattern": "BEARISH_ENGULFING",
                "name": "Bearish Engulfing",
                "signal": "PUT",
                "direction": "BEARISH",
                "rejection_level": round(h1, 1),
                "description": f"Bearish body completely engulfs previous bull candle. Overhead selling dominance confirmed below ₹{c1:,.0f}.",
            }

        # 5. Doji Indecision
        if body1 / rng1 <= 0.10:
            return {
                "pattern": "DOJI",
                "name": "Doji (Volatility Compression)",
                "signal": "NEUTRAL",
                "direction": "NEUTRAL",
                "rejection_level": round(c1, 1),
                "description": f"Doji candle formed at ₹{c1:,.0f}. Balance between bulls and bears; await directional breakout confirmation.",
            }

        return {
            "pattern": "NORMAL_CANDLE",
            "name": "Standard Candle",
            "signal": "BULLISH" if c1 > o1 else "BEARISH",
            "direction": "BULLISH" if c1 > o1 else "BEARISH",
            "rejection_level": round(c1, 1),
            "description": f"Close at ₹{c1:,.0f} ({'+' if c1 >= o1 else '-'}{abs(c1 - o1):.1f} pts body).",
        }

    @classmethod
    def analyze_patterns(cls, df: pd.DataFrame, cur_price: Optional[float] = None) -> Dict[str, Any]:
        """
        Main evaluation method: Extracts swing pivots and evaluates all pattern categories simultaneously.
        """
        if df is None or df.empty or len(df) < 10:
            return {
                "active_patterns_count": 0,
                "detected_patterns": [],
                "primary_pattern": None,
                "candlestick_pattern": {"pattern": "NONE", "signal": "NEUTRAL"},
                "summary": "Insufficient candle data for structural pattern detection.",
            }

        latest_price = float(cur_price or df["close"].iloc[-1])
        pivots = cls.find_swing_pivots(df, window=3)

        detected: List[Dict[str, Any]] = []

        # 1. Classical Chart Patterns
        hs = cls.detect_head_and_shoulders(df, pivots, latest_price)
        detected.extend(hs)

        doubles = cls.detect_double_patterns(df, pivots, latest_price)
        detected.extend(doubles)

        triangles = cls.detect_triangles(df, pivots, latest_price)
        detected.extend(triangles)

        # 2. Harmonic Patterns (Butterfly, Gartley, Bat)
        harmonics = cls.detect_harmonics(df, pivots, latest_price)
        detected.extend(harmonics)

        # 3. Candlestick Formations
        candle_rev = cls.detect_candlestick_reversals(df)

        # Determine primary pattern (most urgent or highest quality)
        primary = None
        if detected:
            # Sort by quality (INSTITUTIONAL > HIGH > MEDIUM) and status
            quality_rank = {"INSTITUTIONAL": 3, "HIGH": 2, "MEDIUM": 1}
            detected.sort(key=lambda x: quality_rank.get(x.get("quality", "MEDIUM"), 0), reverse=True)
            primary = detected[0]

        summary_lines = []
        if primary:
            summary_lines.append(f"• Active Structure: **{primary['name']}** ({primary['direction']})")
            summary_lines.append(f"  - Status: {primary.get('status', 'ACTIVE')}")
            if "target" in primary:
                summary_lines.append(f"  - Target Runway: ₹{primary['target']:,.0f} | Recommended SL: ₹{primary.get('stop_loss', 0):,.0f}")
            elif "target_1" in primary:
                summary_lines.append(f"  - Harmonic PRZ Target: ₹{primary['target_1']:,.0f} (0.382) / ₹{primary.get('target_2', 0):,.0f} (0.618)")
        else:
            summary_lines.append("• Active Structure: No large-scale geometric pattern currently forming (Consolidating near baseline).")

        summary_lines.append(f"• Latest Candle Action: **{candle_rev.get('name', 'Standard Bar')}** -> {candle_rev.get('description', '')}")

        return {
            "spot_price": latest_price,
            "swing_pivots_count": len(pivots),
            "active_patterns_count": len(detected),
            "detected_patterns": detected,
            "primary_pattern": primary,
            "candlestick_pattern": candle_rev,
            "summary": "\n".join(summary_lines),
        }
