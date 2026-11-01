"""
Support and Resistance (S&R) Level and Zone Detector.
Detects the most critical, high-impact Support and Resistance levels (Few clean lines: ~3 Support, ~3 Resistance).
Rules:
- 24H Live Updates:
  Any time the code runs or is opened, S&R lines update dynamically according to the newest candles.
  Also updates live in background when new candles form or price moves.
- Forward Projection (Current Candle + Next 100 Candles):
  Lines and rectangle zones extend from their touch pivots through the current candle and 100 candles ahead into the future.
- Clean few lines:
  Enforces limits on lines (<=3 Support, <=3 Resistance) so the chart is never cluttered with excessive levels.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, time
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
import pytz

logger = logging.getLogger("SupportResistance")
IST = pytz.timezone("Asia/Kolkata")
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_DIR = os.path.join(PROJECT_ROOT, "temp_storage")
SR_CACHE_FILE = os.path.join(CACHE_DIR, "sr_levels.json")
LEGACY_SR_FILE = os.path.join(PROJECT_ROOT, "data_cache", "sr_levels.json")


def is_within_sr_update_window(dt: Optional[datetime] = None) -> bool:
    """
    Returns True 24/7.
    S&R updates dynamically 24H any time the code is opened, and updates live with new candles.
    """
    return True


def load_sr_cache_from_disk(filepath: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Loads previously saved S&R lines from disk (temp_storage/sr_levels.json with data_cache fallback)."""
    path = filepath or SR_CACHE_FILE
    if not os.path.exists(path) and os.path.exists(LEGACY_SR_FILE):
        path = LEGACY_SR_FILE
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict) and "periods" in data:
                return data
    except Exception as e:
        logger.warning("Error reading S&R cache from %s: %s", path, e)
    return None


def save_sr_cache_to_disk(cache_dict: Dict[str, Any], filepath: Optional[str] = None) -> bool:
    """Atomically saves S&R lines and metadata to disk."""
    path = filepath or SR_CACHE_FILE
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        temp_path = f"{path}.tmp"
        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump(cache_dict, f, indent=2)
        if os.path.exists(path):
            os.replace(temp_path, path)
        else:
            os.rename(temp_path, path)
        return True
    except Exception as e:
        logger.error("Error saving S&R cache to %s: %s", path, e)
        return False


def detect_support_resistance(
    df: pd.DataFrame,
    swing_window: int = 5,
    line_tolerance: float = 4.0,
    rect_tolerance: float = 12.0,
    line_min_bounces: int = 3,
    rect_min_bounces: int = 6,
    line_max_spread: float = 8.0,
    max_lines: int = 8,
    max_rects: int = 3,
    min_price_gap: float = 20.0,
    future_candles: int = 100,
    current_price: Optional[float] = None,
    max_support: int = 4,
    max_resistance: int = 4,
) -> List[Dict[str, Any]]:
    """
    Scans historical 5-minute candles for the MOST IMPORTANT support & resistance levels that actually work.
    
    Rules:
    - Major Focus on Lines: Levels with bounces < 6x are represented as clean lines.
      Touches within +/- 2 to 4 points (spread <= 8.0), minimum 3 bounces (>=3x).
      Drawn at the exact AVERAGE price of all touch points.
    - Rectangles for Major Flips (>= 6x): Displayed as Rectangle Zones when price touches
      >= 6 times (spread > 8.0) forming a major institutional S/R Flip Zone (Max 3 zones).
    - Resistance: Max 4 lines above price (strongest levels closest to price).
    - Support: Max 4 lines below price (strongest levels closest to price).
    - Forward Extension: Extends forward through current candle + next 100 candles (100 bars = 30,000s)
      so levels are clearly visible ahead of live forming candles.
    - Clean Spacing: Enforces a minimum price gap (>= 20 points) between levels to prevent crowding/overlapping lines.
    - Color: Pure white (#ffffff).
    """
    if df is None or len(df) < swing_window * 3:
        return []

    highs = df["high"].values
    lows = df["low"].values
    n = len(df)

    timestamps = []
    for idx in df.index:
        try:
            t = int(idx.timestamp()) if hasattr(idx, "timestamp") else int(pd.to_datetime(idx).timestamp())
        except Exception:
            t = 0
        timestamps.append(t)

    last_time = timestamps[-1] if timestamps else 0
    future_extension_sec = future_candles * 300  # 100 bars of 5m = 30,000s (current candle + next 100 candles)

    # 1. Detect Pivot Highs & Lows
    pivots = []
    for i in range(swing_window, n - swing_window):
        h = float(highs[i])
        l = float(lows[i])
        t = timestamps[i]

        if h >= np.max(highs[i - swing_window : i + swing_window + 1]):
            pivots.append({"price": h, "type": "high", "time": t, "idx": i})

        if l <= np.min(lows[i - swing_window : i + swing_window + 1]):
            pivots.append({"price": l, "type": "low", "time": t, "idx": i})

    if not pivots:
        return []

    # 2. Line detection (Touches clustered within +/- 2-4 points -> spread <= 8.0, bounces >= 3)
    line_clusters: List[Dict[str, Any]] = []
    for p in pivots:
        matched = False
        for c in line_clusters:
            if abs(p["price"] - c["avg_price"]) <= line_tolerance:
                c["points"].append(p)
                c["prices"].append(p["price"])
                c["avg_price"] = sum(c["prices"]) / len(c["prices"])
                c["min_price"] = min(c["min_price"], p["price"])
                c["max_price"] = max(c["max_price"], p["price"])
                c["min_time"] = min(c["min_time"], p["time"])
                c["max_time"] = max(c["max_time"], p["time"])
                if p["type"] == "low":
                    c["low_bounces"] += 1
                else:
                    c["high_bounces"] += 1
                matched = True
                break

        if not matched:
            line_clusters.append({
                "points": [p],
                "prices": [p["price"]],
                "avg_price": p["price"],
                "min_price": p["price"],
                "max_price": p["price"],
                "min_time": p["time"],
                "max_time": p["time"],
                "low_bounces": 1 if p["type"] == "low" else 0,
                "high_bounces": 1 if p["type"] == "high" else 0,
            })

    cur_p = current_price
    if cur_p is None and df is not None and not df.empty and "close" in df:
        try:
            cur_p = float(df["close"].iloc[-1])
        except Exception:
            cur_p = None

    candidate_lines: List[Dict[str, Any]] = []
    for idx, c in enumerate(line_clusters):
        bounces = len(c["points"])
        spread = c["max_price"] - c["min_price"]
        if bounces >= line_min_bounces and spread <= line_max_spread:
            avg_p = round(c["avg_price"], 2)
            if cur_p is not None:
                is_support = avg_p < cur_p
            else:
                is_support = c["low_bounces"] >= c["high_bounces"]

            base_role = "Support" if is_support else "Resistance"
            if c["low_bounces"] > 0 and c["high_bounces"] > 0:
                role = f"S/R Flip ({base_role})"
            else:
                role = base_role

            # Dynamic Visibility & Thickness Scaling based on Bounce Count (2x to 8x+)
            # High X = Thick & Bold Line (4.0px - 5.0px, 1.00 full brightness)
            # Low X = Thin Hairline (1.0px, 0.28 faint subtle visibility)
            t_factor = min(max((bounces - 2) / 6.0, 0.0), 1.0)
            stroke_op = round(0.28 + t_factor * 0.72, 2)
            w = round(1.0 + t_factor * 4.0, 1)

            candidate_lines.append({
                "id": f"sr_line_{idx}_{int(avg_p)}",
                "type": "line",
                "time1": c["min_time"],
                "time2": last_time + future_extension_sec,
                "price1": avg_p,
                "price2": avg_p,
                "color": "#ffffff",
                "width": w,
                "opacity": stroke_op,
                "remark": f"Strong {role} ({bounces}x) ₹{avg_p:.2f}",
                "is_sr_auto": True,
                "role": role,
                "is_support": is_support,
                "category": "support" if is_support else "resistance",
                "bounces": bounces,
                "avg_price": avg_p,
                "spread": round(spread, 2),
            })

    support_cands = [l for l in candidate_lines if l.get("is_support")]
    resistance_cands = [l for l in candidate_lines if not l.get("is_support")]

    # Sort each side: highest bounce count first; if tied, closest to current price first
    if cur_p is not None:
        support_cands.sort(key=lambda s: (-s["bounces"], abs(s["avg_price"] - cur_p)))
        resistance_cands.sort(key=lambda r: (-r["bounces"], abs(r["avg_price"] - cur_p)))
    else:
        support_cands.sort(key=lambda s: -s["bounces"])
        resistance_cands.sort(key=lambda r: -r["bounces"])

    # Filter few distinct Support lines
    filtered_supports: List[Dict[str, Any]] = []
    for line in support_cands:
        if not any(abs(line["avg_price"] - f["avg_price"]) < min_price_gap for f in filtered_supports):
            filtered_supports.append(line)
            if len(filtered_supports) >= max_support:
                break

    # Filter few distinct Resistance lines
    filtered_resistances: List[Dict[str, Any]] = []
    for line in resistance_cands:
        if not any(abs(line["avg_price"] - f["avg_price"]) < min_price_gap for f in filtered_resistances):
            filtered_resistances.append(line)
            if len(filtered_resistances) >= max_resistance:
                break

    filtered_lines: List[Dict[str, Any]] = filtered_supports + filtered_resistances

    # 3. Rectangle zone detection (Spread > 8.0, bounces >= 4)
    rect_clusters: List[Dict[str, Any]] = []
    for p in pivots:
        matched = False
        for c in rect_clusters:
            if abs(p["price"] - c["avg_price"]) <= rect_tolerance:
                c["points"].append(p)
                c["prices"].append(p["price"])
                c["avg_price"] = sum(c["prices"]) / len(c["prices"])
                c["min_price"] = min(c["min_price"], p["price"])
                c["max_price"] = max(c["max_price"], p["price"])
                c["min_time"] = min(c["min_time"], p["time"])
                c["max_time"] = max(c["max_time"], p["time"])
                if p["type"] == "low":
                    c["low_bounces"] += 1
                else:
                    c["high_bounces"] += 1
                matched = True
                break

        if not matched:
            rect_clusters.append({
                "points": [p],
                "prices": [p["price"]],
                "avg_price": p["price"],
                "min_price": p["price"],
                "max_price": p["price"],
                "min_time": p["time"],
                "max_time": p["time"],
                "low_bounces": 1 if p["type"] == "low" else 0,
                "high_bounces": 1 if p["type"] == "high" else 0,
            })

    # 3. Rectangle zone detection (Spread > 8.0, bounces >= rect_min_bounces)
    candidate_rects: List[Dict[str, Any]] = []
    for idx, c in enumerate(rect_clusters):
        bounces = len(c["points"])
        spread = c["max_price"] - c["min_price"]
        if bounces >= rect_min_bounces and spread > line_max_spread:
            min_p = round(c["min_price"], 2)
            max_p = round(c["max_price"], 2)
            avg_p = round(c["avg_price"], 2)
            is_support = c["low_bounces"] >= c["high_bounces"]
            role = "Support Zone" if is_support else "Resistance Zone"
            if c["low_bounces"] > 0 and c["high_bounces"] > 0:
                role = "S/R Flip Zone"

            # Dynamic Visibility & Thickness Scaling for S&R Zones (4x to 8x+)
            t_factor = min(max((bounces - 2) / 6.0, 0.0), 1.0)
            stroke_op = round(0.30 + t_factor * 0.70, 2)
            fill_op = round(0.05 + t_factor * 0.25, 2)
            w = round(1.0 + t_factor * 2.8, 1)

            # Analyze touch distribution: Upper Line vs Lower Line vs Middle
            # The line with the majority of touches is highlighted in Yellow (#ffd700) to signify it is stronger!
            upper_touches = sum(1 for p in c["points"] if p["price"] >= (min_p + 0.55 * spread))
            lower_touches = sum(1 for p in c["points"] if p["price"] <= (min_p + 0.45 * spread))
            middle_touches = max(0, bounces - upper_touches - lower_touches)

            if lower_touches > upper_touches:
                stronger_line = "lower"
                remark_detail = f"[Lower: {lower_touches}x ★ / Upper: {upper_touches}x]"
            elif upper_touches > lower_touches:
                stronger_line = "upper"
                remark_detail = f"[Upper: {upper_touches}x ★ / Lower: {lower_touches}x]"
            else:
                stronger_line = "equal"
                remark_detail = f"[{upper_touches}x Upper / {lower_touches}x Lower]"

            candidate_rects.append({
                "id": f"sr_rect_{idx}_{int(min_p)}_{int(max_p)}",
                "type": "rect",
                "time1": c["min_time"],
                "time2": last_time + future_extension_sec,
                "price1": max_p,
                "price2": min_p,
                "color": "#ffffff",
                "width": w,
                "opacity": stroke_op,
                "fill_opacity": fill_op,
                "remark": f"{role} ({bounces}x) {remark_detail} ₹{min_p:.1f} - ₹{max_p:.1f}",
                "is_sr_auto": True,
                "role": role,
                "bounces": bounces,
                "min_price": min_p,
                "max_price": max_p,
                "avg_price": avg_p,
                "spread": round(spread, 2),
                "upper_bounces": upper_touches,
                "lower_bounces": lower_touches,
                "middle_bounces": middle_touches,
                "stronger_line": stronger_line,
                "upper_color": "#ffd700" if stronger_line == "upper" else "#ffffff",
                "lower_color": "#ffd700" if stronger_line == "lower" else "#ffffff",
                "upper_width": round(w * 1.15, 1) if stronger_line == "upper" else round(max(1.5, w * 0.75), 1),
                "lower_width": round(w * 1.15, 1) if stronger_line == "lower" else round(max(1.5, w * 0.75), 1),
            })

    candidate_rects.sort(key=lambda s: s["bounces"], reverse=True)

    # 4. Filter Rectangles with >= 7x flips:
    # Major >=7x flip zones are given priority as rectangles.
    filtered_rects: List[Dict[str, Any]] = []
    if max_rects > 0:
        for rect in candidate_rects:
            clash_rect = any(abs(rect["avg_price"] - f["avg_price"]) < min_price_gap for f in filtered_rects)
            if not clash_rect:
                filtered_rects.append(rect)
                if len(filtered_rects) >= max_rects:
                    break

    # 5. Remove any line that falls directly inside a selected >= 7x rectangle zone
    # so the rectangle zone is clearly visible without duplicate lines cluttering it
    final_lines: List[Dict[str, Any]] = []
    for line in filtered_lines:
        inside_rect = any(
            (rect["min_price"] - 2.0) <= line["avg_price"] <= (rect["max_price"] + 2.0)
            for rect in filtered_rects
        )
        if not inside_rect:
            final_lines.append(line)

    selected = final_lines + filtered_rects
    selected.sort(key=lambda s: s["bounces"], reverse=True)
    return selected


def detect_local_support_resistance(
    df_5m: pd.DataFrame,
    major_levels: List[Dict[str, Any]],
    days_back: int = 7,
    swing_window: int = 3,
    line_tolerance: float = 4.0,
    line_max_spread: float = 8.0,
    min_bounces: int = 2,
    max_local: int = 4,
    min_price_gap: float = 16.0,
    major_clash_gap: float = 18.0,
    future_candles: int = 100,
) -> List[Dict[str, Any]]:
    """
    Detects short-term Local Support and Resistance lines over the last 5-7 trading days.
    
    Rendered as Off-White (#cbd5e1) dashed lines on the 5m chart:
    - Scans the most recent 5-7 trading days for active intraday / tactical levels (Max 4 lines).
    - Minimum 2 bounces (>=2x) within +/- 2 to 4 points (spread <= 8.0 pts).
    - Drawn at the exact average price of touch points.
    - Non-clashing: Does not duplicate or overlap existing major white S&R levels.
    - Forward Extension: Extends forward through the current candle + next 100 candles (100 bars = 30,000s).
    - Color: Off-White (#cbd5e1).
    """
    if df_5m is None or df_5m.empty:
        return []

    unique_days = sorted(df_5m.index.normalize().unique())
    days = unique_days[-days_back:] if len(unique_days) >= days_back else unique_days
    df_local = df_5m[df_5m.index.normalize().isin(days)].copy()

    if len(df_local) < swing_window * 3:
        return []

    highs = df_local["high"].values
    lows = df_local["low"].values
    n = len(df_local)

    timestamps = []
    for idx in df_local.index:
        try:
            t = int(idx.timestamp()) if hasattr(idx, "timestamp") else int(pd.to_datetime(idx).timestamp())
        except Exception:
            t = 0
        timestamps.append(t)

    last_time = timestamps[-1] if timestamps else 0
    future_extension_sec = future_candles * 300  # 100 bars of 5m = 30,000s (current candle + next 100 candles)

    pivots = []
    for i in range(swing_window, n - swing_window):
        h = float(highs[i])
        l = float(lows[i])
        t = timestamps[i]

        if h >= np.max(highs[i - swing_window : i + swing_window + 1]):
            pivots.append({"price": h, "type": "high", "time": t, "idx": i})
        if l <= np.min(lows[i - swing_window : i + swing_window + 1]):
            pivots.append({"price": l, "type": "low", "time": t, "idx": i})

    if not pivots:
        return []

    clusters: List[Dict[str, Any]] = []
    for p in pivots:
        matched = False
        for c in clusters:
            if abs(p["price"] - c["avg_price"]) <= line_tolerance:
                c["points"].append(p)
                c["prices"].append(p["price"])
                c["avg_price"] = sum(c["prices"]) / len(c["prices"])
                c["min_price"] = min(c["min_price"], p["price"])
                c["max_price"] = max(c["max_price"], p["price"])
                c["min_time"] = min(c["min_time"], p["time"])
                c["max_time"] = max(c["max_time"], p["time"])
                if p["type"] == "low":
                    c["low_bounces"] += 1
                else:
                    c["high_bounces"] += 1
                matched = True
                break
        if not matched:
            clusters.append({
                "points": [p],
                "prices": [p["price"]],
                "avg_price": p["price"],
                "min_price": p["price"],
                "max_price": p["price"],
                "min_time": p["time"],
                "max_time": p["time"],
                "low_bounces": 1 if p["type"] == "low" else 0,
                "high_bounces": 1 if p["type"] == "high" else 0,
            })

    candidate_lines: List[Dict[str, Any]] = []
    for idx, c in enumerate(clusters):
        bounces = len(c["points"])
        spread = c["max_price"] - c["min_price"]
        if bounces >= min_bounces and spread <= line_max_spread:
            avg_p = round(c["avg_price"], 2)
            is_support = c["low_bounces"] >= c["high_bounces"]
            role = "Local Support" if is_support else "Local Resistance"
            if c["low_bounces"] > 0 and c["high_bounces"] > 0:
                role = "Local S/R"

            # Dynamic Visibility & Thickness Scaling for Local Lines (2x to 8x+)
            # High X = Thick & Bold Line (4.0px - 5.0px, 1.00 full brightness)
            # Low X = Thin Hairline (1.0px, 0.28 faint subtle visibility)
            t_factor = min(max((bounces - 2) / 6.0, 0.0), 1.0)
            stroke_op = round(0.28 + t_factor * 0.72, 2)
            w = round(1.0 + t_factor * 4.0, 1)

            candidate_lines.append({
                "id": f"sr_local_{idx}_{int(avg_p)}",
                "type": "line",
                "time1": c["min_time"],
                "time2": last_time + future_extension_sec,
                "price1": avg_p,
                "price2": avg_p,
                "color": "#cbd5e1",  # Off-White line
                "width": w,
                "opacity": stroke_op,
                "remark": f"{role} ({bounces}x) ₹{avg_p:.2f}",
                "is_sr_auto": True,
                "is_local": True,
                "role": role,
                "is_support": is_support,
                "category": "support" if is_support else "resistance",
                "bounces": bounces,
                "avg_price": avg_p,
                "spread": round(spread, 2),
            })

    candidate_lines.sort(key=lambda s: (s["bounces"], -s["spread"]), reverse=True)

    filtered_local: List[Dict[str, Any]] = []
    for cand in candidate_lines:
        clash_major = any(abs(cand["avg_price"] - m["avg_price"]) < major_clash_gap for m in major_levels)
        clash_local = any(abs(cand["avg_price"] - l["avg_price"]) < min_price_gap for l in filtered_local)
        if not clash_major and not clash_local:
            filtered_local.append(cand)
            if len(filtered_local) >= max_local:
                break

    return filtered_local


def combine_sr_levels(
    levels_1m: List[Dict[str, Any]],
    levels_2m: List[Dict[str, Any]],
    price_tolerance: float = 8.0,
    current_price: Optional[float] = None,
    max_support: int = 4,
    max_resistance: int = 4,
    max_rects: int = 3,
    max_total: int = 12,
) -> List[Dict[str, Any]]:
    """
    Combines 1-Month (1M / 20 trading days) and 2-Month (2M / 45 trading days) Support & Resistance levels.
    
    Rules:
    - Confluence Merging:
      If a 1M level and 2M level share polarity (both Support or both Resistance) and their prices
      are within <= price_tolerance (default 8.0 points):
      - They are merged into a single high-impact Confluence Level.
      - Price: Average price of the two levels.
      - Bounces: max(bounces_1m, bounces_2m) + (1 bonus bounce if min(b1, b2) >= 3).
      - Tagged: origin="1M + 2M Confluence", timeframe_tag="1M + 2M Confluence", is_confluence=True.
      - Color: Pure White (#ffffff), thickness boosted (+1.0px up to 5.0px), opacity 1.0.
      - Role: "Strong Support (1M+2M Confluence)" or "Strong Resistance (1M+2M Confluence)".
    - Unique Retained Levels:
      - Unique 1M levels: Tagged origin="1M Swing / Local", timeframe_tag="1M Swing / Local", is_confluence=False.
      - Unique 2M levels: Tagged origin="2M Macro", timeframe_tag="2M Macro", is_confluence=False.
    - Rectangle Merging:
      - If a line falls within or adjacent to a rectangle zone, it merges into the rectangle zone,
        boosting the rectangle's touches and tagging it as 1M + 2M Confluence.
    - Capped to max_total (prioritizing confluence and highest touches).
    """
    import copy
    copied_1m = [copy.deepcopy(x) for x in (levels_1m or [])]
    copied_2m = [copy.deepcopy(x) for x in (levels_2m or [])]

    for l in copied_1m:
        is_supp = l.get("is_support", "Support" in l.get("role", "") or "support" in l.get("category", ""))
        l["is_support"] = is_supp
        l["origin"] = "1M Swing / Local"
        l["timeframe_tag"] = "1M Swing / Local"
        l["is_confluence"] = False

    for l in copied_2m:
        is_supp = l.get("is_support", "Support" in l.get("role", "") or "support" in l.get("category", ""))
        l["is_support"] = is_supp
        l["origin"] = "2M Macro"
        l["timeframe_tag"] = "2M Macro"
        l["is_confluence"] = False

    matched_2m_idx = set()
    combined_raw: List[Dict[str, Any]] = []

    for l1 in copied_1m:
        l1_p = float(l1.get("avg_price", l1.get("price1", 0.0)))
        l1_is_supp = l1["is_support"]
        l1_is_rect = l1.get("type") == "rect"

        best_match_idx = None
        best_dist = float("inf")

        for idx, l2 in enumerate(copied_2m):
            if idx in matched_2m_idx:
                continue
            if l2["is_support"] != l1_is_supp:
                continue

            l2_p = float(l2.get("avg_price", l2.get("price1", 0.0)))
            l2_is_rect = l2.get("type") == "rect"

            if not l1_is_rect and not l2_is_rect:
                dist = abs(l1_p - l2_p)
            elif l1_is_rect and not l2_is_rect:
                min_p = float(l1.get("min_price", l1_p - 4.0))
                max_p = float(l1.get("max_price", l1_p + 4.0))
                if min_p - price_tolerance <= l2_p <= max_p + price_tolerance:
                    dist = 0.0
                else:
                    dist = min(abs(l2_p - min_p), abs(l2_p - max_p))
            elif not l1_is_rect and l2_is_rect:
                min_p = float(l2.get("min_price", l2_p - 4.0))
                max_p = float(l2.get("max_price", l2_p + 4.0))
                if min_p - price_tolerance <= l1_p <= max_p + price_tolerance:
                    dist = 0.0
                else:
                    dist = min(abs(l1_p - min_p), abs(l1_p - max_p))
            else:
                dist = abs(l1_p - l2_p)

            if dist <= price_tolerance and dist < best_dist:
                best_dist = dist
                best_match_idx = idx

        if best_match_idx is not None:
            matched_2m_idx.add(best_match_idx)
            l2 = copied_2m[best_match_idx]
            l2_p = float(l2.get("avg_price", l2.get("price1", 0.0)))
            l2_is_rect = l2.get("type") == "rect"

            b1 = int(l1.get("bounces", 3))
            b2 = int(l2.get("bounces", 3))
            comb_bounces = max(b1, b2) + (1 if min(b1, b2) >= 3 else 0)
            comb_p = round((l1_p + l2_p) / 2.0, 2)
            comb_spread = round(max(float(l1.get("spread", 0.0)), float(l2.get("spread", 0.0))), 2)
            is_supp = l1_is_supp
            base_role = "Support" if is_supp else "Resistance"
            role_text = f"Strong {base_role} (1M+2M Confluence)"

            # If either is rectangle, produce merged rectangle
            if l1_is_rect or l2_is_rect:
                rect_obj = l1 if l1_is_rect else l2
                other_obj = l2 if l1_is_rect else l1
                other_p = float(other_obj.get("avg_price", other_obj.get("price1", 0.0)))
                min_p = round(min(float(rect_obj.get("min_price", rect_obj.get("price2", comb_p))), other_p), 2)
                max_p = round(max(float(rect_obj.get("max_price", rect_obj.get("price1", comb_p))), other_p), 2)
                w = round(min(max(float(l1.get("width", 2.0)), float(l2.get("width", 2.0))) + 0.8, 5.0), 1)

                comb_level = {
                    "id": f"sr_comb_rect_{int(min_p)}_{int(max_p)}",
                    "type": "rect",
                    "time1": min(l1.get("time1", 0), l2.get("time1", 0)),
                    "time2": max(l1.get("time2", 0), l2.get("time2", 0)),
                    "price1": max_p,
                    "price2": min_p,
                    "color": "#ffffff",
                    "width": w,
                    "opacity": 1.0,
                    "fill_opacity": 0.16,
                    "remark": f"{role_text} Zone ({comb_bounces}x) ₹{min_p:.1f} - ₹{max_p:.1f}",
                    "is_sr_auto": True,
                    "is_confluence": True,
                    "origin": "1M + 2M Confluence",
                    "timeframe_tag": "1M + 2M Confluence",
                    "role": f"{role_text} Zone",
                    "is_support": is_supp,
                    "category": "support" if is_supp else "resistance",
                    "bounces": comb_bounces,
                    "min_price": min_p,
                    "max_price": max_p,
                    "avg_price": comb_p,
                    "spread": round(max_p - min_p, 2),
                    "upper_color": "#ffd700",
                    "lower_color": "#ffd700",
                    "upper_width": round(w * 1.15, 1),
                    "lower_width": round(w * 1.15, 1),
                }
            else:
                # Merged line
                w = round(min(max(float(l1.get("width", 2.0)), float(l2.get("width", 2.0))) + 1.0, 5.0), 1)
                comb_level = {
                    "id": f"sr_comb_{int(comb_p)}_{comb_bounces}x",
                    "type": "line",
                    "time1": min(l1.get("time1", 0), l2.get("time1", 0)),
                    "time2": max(l1.get("time2", 0), l2.get("time2", 0)),
                    "price1": comb_p,
                    "price2": comb_p,
                    "color": "#ffffff",
                    "width": w,
                    "opacity": 1.0,
                    "remark": f"{role_text} ({comb_bounces}x) ₹{comb_p:.2f}",
                    "is_sr_auto": True,
                    "is_confluence": True,
                    "origin": "1M + 2M Confluence",
                    "timeframe_tag": "1M + 2M Confluence",
                    "role": role_text,
                    "is_support": is_supp,
                    "category": "support" if is_supp else "resistance",
                    "bounces": comb_bounces,
                    "avg_price": comb_p,
                    "spread": comb_spread,
                }
            combined_raw.append(comb_level)
        else:
            combined_raw.append(l1)

    for idx, l2 in enumerate(copied_2m):
        if idx not in matched_2m_idx:
            combined_raw.append(l2)

    # De-duplicate any remaining clashing levels (within 10.0 pts)
    sorted_raw = sorted(
        combined_raw,
        key=lambda x: (
            1 if x.get("is_confluence") else 0,
            x.get("bounces", 0),
            -abs(x.get("avg_price", 0.0) - (current_price or 0.0)) if current_price else 0
        ),
        reverse=True
    )

    filtered_combined: List[Dict[str, Any]] = []
    for item in sorted_raw:
        item_p = float(item.get("avg_price", item.get("price1", 0.0)))
        item_is_supp = item.get("is_support", True)
        clash = False
        for ex in filtered_combined:
            if ex.get("is_support") == item_is_supp:
                ex_p = float(ex.get("avg_price", ex.get("price1", 0.0)))
                if abs(item_p - ex_p) < 10.0:
                    clash = True
                    break
        if not clash:
            filtered_combined.append(item)

    # Separate Supports and Resistances and cap them
    supports = [l for l in filtered_combined if l.get("is_support")]
    resistances = [l for l in filtered_combined if not l.get("is_support")]

    if current_price is not None:
        supports.sort(key=lambda s: (-1 if s.get("is_confluence") else 0, -s.get("bounces", 0), abs(s.get("avg_price", current_price) - current_price)))
        resistances.sort(key=lambda r: (-1 if r.get("is_confluence") else 0, -r.get("bounces", 0), abs(r.get("avg_price", current_price) - current_price)))
    else:
        supports.sort(key=lambda s: (-1 if s.get("is_confluence") else 0, -s.get("bounces", 0)))
        resistances.sort(key=lambda r: (-1 if r.get("is_confluence") else 0, -r.get("bounces", 0)))

    eff_supp = max_support if max_support > 0 else 4
    eff_res = max_resistance if max_resistance > 0 else 4
    final_levels = supports[:eff_supp] + resistances[:eff_res]

    # Re-sort final levels by bounces descending
    final_levels.sort(key=lambda s: (-1 if s.get("is_confluence") else 0, -s.get("bounces", 0)))

    if len(final_levels) > max_total:
        final_levels = final_levels[:max_total]

    return final_levels


def calculate_sr_periods(
    df_5m: pd.DataFrame,
    current_price: Optional[float] = None,
    max_support: int = 4,
    max_resistance: int = 4,
    max_rects: int = 3,
    rect_min_bounces: int = 6,
    include_local: bool = True,
    max_local: int = 4,
    days_back: int = 7,
    max_total: int = 10,
    future_candles: int = 100,
) -> Dict[str, List[Dict[str, Any]]]:
    """
    Calculates Support & Resistance levels for both:
    - 1 Month: Rolling last 20 trading days (Major levels in Pure White #ffffff)
    - 2 Months: Rolling last 40-45 trading days (Major levels in Pure White #ffffff)
    - Plus Local S&R: Rolling last 5-7 trading days (Local levels in Off-White #cbd5e1)
    
    Strictly enforces limits to generate only a few clean lines of support and resistance:
    - Max 4 Resistances (above price)
    - Max 4 Supports (below price)
    - Max 3 Rectangles (only >= 6x bounces)
    - Max 4 Local lines (recent 5-7 days)
    - Strictly limited to Max 8 to 10 levels total on chart.
    - Projects lines forward through current candle + next 100 candles.
    """
    if df_5m is None or df_5m.empty:
        return {"1m": [], "2m": [], "major_1m": [], "major_2m": [], "local_1m": [], "local_2m": []}

    cur_p = current_price
    if cur_p is None and df_5m is not None and not df_5m.empty and "close" in df_5m:
        try:
            cur_p = float(df_5m["close"].iloc[-1])
        except Exception:
            cur_p = None

    unique_days = sorted(df_5m.index.normalize().unique())

    # 1 Month (last 20 trading days)
    days_1m = unique_days[-20:] if len(unique_days) >= 20 else unique_days
    df_1m = df_5m[df_5m.index.normalize().isin(days_1m)].copy()
    major_1m = detect_support_resistance(
        df_1m,
        current_price=cur_p,
        max_support=max_support,
        max_resistance=max_resistance,
        max_rects=max_rects,
        rect_min_bounces=rect_min_bounces,
        future_candles=future_candles,
    )

    # 2 Months (last 45 trading days)
    days_2m = unique_days[-45:] if len(unique_days) >= 45 else unique_days
    df_2m = df_5m[df_5m.index.normalize().isin(days_2m)].copy()
    major_2m = detect_support_resistance(
        df_2m,
        current_price=cur_p,
        max_support=max_support,
        max_resistance=max_resistance,
        max_rects=max_rects,
        rect_min_bounces=rect_min_bounces,
        future_candles=future_candles,
    )

    # Local S&R (last 5-7 trading days)
    if include_local and max_local > 0:
        local_1m = detect_local_support_resistance(
            df_5m, major_1m, days_back=days_back, max_local=max_local, future_candles=future_candles
        )
        local_2m = detect_local_support_resistance(
            df_5m, major_2m, days_back=days_back, max_local=max_local, future_candles=future_candles
        )
    else:
        local_1m = []
        local_2m = []

    def _cap_total(levels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if len(levels) <= max_total:
            return levels
        # Keep rectangles (major flip zones with >= 6x bounces)
        rects = [l for l in levels if l.get("type") == "rect"]
        lines = [l for l in levels if l.get("type") != "rect"]
        if len(rects) >= max_total:
            return rects[:max_total]
        # Sort lines by bounce count (highest first) and proximity to current price
        if cur_p is not None:
            lines.sort(key=lambda s: (-s.get("bounces", 0), abs(s.get("avg_price", cur_p) - cur_p)))
        else:
            lines.sort(key=lambda s: -s.get("bounces", 0))
        allowed_lines = max_total - len(rects)
        return rects + lines[:allowed_lines]

    levels_1m = _cap_total(major_1m + local_1m)
    levels_2m = _cap_total(major_2m + local_2m)

    combined_levels = combine_sr_levels(
        levels_1m,
        levels_2m,
        price_tolerance=8.0,
        current_price=cur_p,
        max_support=max_support,
        max_resistance=max_resistance,
        max_rects=max_rects,
        max_total=max_total,
    )

    return {
        "1m": levels_1m,
        "2m": levels_2m,
        "combined": combined_levels,
        "major_1m": major_1m,
        "major_2m": major_2m,
        "local_1m": local_1m,
        "local_2m": local_2m,
    }


def update_or_get_sr_levels(
    df_5m: pd.DataFrame,
    current_price: Optional[float] = None,
    force: bool = False,
    now_dt: Optional[datetime] = None,
    max_support: int = 4,
    max_resistance: int = 4,
    max_rects: int = 3,
    rect_min_bounces: int = 6,
    include_local: bool = True,
    max_local: int = 4,
    days_back: int = 7,
    max_total: int = 10,
    future_candles: int = 100,
    filepath: Optional[str] = None,
) -> Dict[str, Any]:
    """
    24H Live S&R Trading Engine:
    
    1. 24H Any Time Update:
       - Any time the user opens the code or requests levels, S&R updates dynamically according to the newest candles.
       - Continuously updates live when new candles form or price moves.
       - Mode: '24h_live_updated'.
       
    2. Forward Projection (Current Candle + Next 100 Candles):
       - Lines and rectangle zones extend from their touch pivots through the current candle
         and forward for 100 candles into the future (future_candles=100 -> 30,000 seconds).
         
    3. Strictly Limited Levels (Max 8 to 10 Levels Total):
       - ▲ Resistance: Max 4 lines above price (strongest levels closest to price).
       - ▼ Support: Max 4 lines below price (strongest levels closest to price).
       - ■ Rectangles: Max 3 major flip zones (only levels with >= 6x bounces).
       - ┄ Local S&R: Max 4 short-term lines (recent 5-7 days).
       - Total on chart strictly capped to max 10 levels.
       - Purges and replaces old lines with newly generated lines.
    """
    if now_dt is None:
        now_ist = datetime.now(IST)
    elif now_dt.tzinfo is None:
        now_ist = now_dt.replace(tzinfo=IST)
    else:
        now_ist = now_dt.astimezone(IST)

    cached_data = load_sr_cache_from_disk(filepath)

    if df_5m is None or df_5m.empty:
        if cached_data is not None:
            cached_data["mode"] = "24h_live_updated"
            return cached_data
        return {
            "mode": "empty",
            "is_within_window": True,
            "periods": {"1m": [], "2m": [], "combined": [], "major_1m": [], "major_2m": [], "local_1m": [], "local_2m": []}
        }

    cur_p = current_price
    if cur_p is None and not df_5m.empty and "close" in df_5m:
        try:
            cur_p = float(df_5m["close"].iloc[-1])
        except Exception:
            cur_p = None

    last_candle_ts = str(df_5m.index[-1]) if len(df_5m) > 0 else ""
    candle_count = len(df_5m)

    # Fast cache check: if not forced and cached data already matches current candle count & ts & future_candles
    if not force and cached_data is not None:
        c_count = cached_data.get("last_candle_count")
        c_ts = cached_data.get("last_candle_ts")
        c_fut = cached_data.get("future_candles", 100)
        c_lim = cached_data.get("limits", {})
        if (
            c_count == candle_count
            and c_ts == last_candle_ts
            and c_fut == future_candles
            and c_lim.get("max_support") == max_support
            and c_lim.get("max_resistance") == max_resistance
            and c_lim.get("max_rects") == max_rects
            and c_lim.get("rect_min_bounces") == rect_min_bounces
        ):
            cached_data["mode"] = "24h_live_updated"
            cached_data["is_within_window"] = True
            return cached_data

    # Otherwise (new candle added, or code opened, or price moved, or forced):
    # Calculate fresh new lines with current candle + next 100 candles
    computed = calculate_sr_periods(
        df_5m,
        current_price=cur_p,
        max_support=max_support,
        max_resistance=max_resistance,
        max_rects=max_rects,
        rect_min_bounces=rect_min_bounces,
        include_local=include_local,
        max_local=max_local,
        days_back=days_back,
        max_total=max_total,
        future_candles=future_candles,
    )

    new_cache = {
        "last_updated_ist": now_ist.strftime("%Y-%m-%d %H:%M:%S"),
        "last_updated_iso": now_ist.isoformat(),
        "updated_date": now_ist.strftime("%Y-%m-%d"),
        "window": "24H_live",
        "mode": "24h_live_updated",
        "is_within_window": True,
        "window_rule": "24H Live: S&R updates anytime code runs and updates live with new candles (current + next 100 candles).",
        "current_price": round(cur_p, 2) if cur_p else None,
        "last_candle_count": candle_count,
        "last_candle_ts": last_candle_ts,
        "future_candles": future_candles,
        "limits": {
            "max_support": max_support,
            "max_resistance": max_resistance,
            "max_rects": max_rects,
            "rect_min_bounces": rect_min_bounces,
            "max_local": max_local,
            "days_back": days_back,
            "max_total": max_total,
        },
        "periods": computed,
    }

    # Replace old lines completely with new lines on disk
    save_sr_cache_to_disk(new_cache, filepath)
    logger.info(
        "[%s] 24H Live S&R updated with new candles (1M: %d, 2M: %d, Comb: %d, candles=%d, future=%d).",
        now_ist.strftime("%H:%M:%S IST"),
        len(computed.get("1m", [])),
        len(computed.get("2m", [])),
        len(computed.get("combined", [])),
        candle_count,
        future_candles,
    )
    return new_cache
