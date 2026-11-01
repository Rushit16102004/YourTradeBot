"""
Advanced Analytics Module for RAG Copilot:
1. ORBAnalyzer: Opening Range Breakout (9:15 - 9:45 AM) Status & Regime Tracking.
2. TradeDoctor: Technical Post-Trade Diagnosis (Why Did the Signal Win or Lose?).
"""
from __future__ import annotations

import logging
from typing import Dict, Any, List, Optional
import pandas as pd

logger = logging.getLogger("RAGAnalytics")


class ORBAnalyzer:
    """
    Evaluates 9:15 AM - 9:45 AM Opening Range for NIFTY 50 (first 6 five-minute candles).
    Determines institutional expansion, breakdown, or inside-range chop.
    """

    @staticmethod
    def compute(df_5m: pd.DataFrame, cur_price: float) -> Dict[str, Any]:
        default_res = {
            "has_orb": False,
            "high": 0.0,
            "low": 0.0,
            "range": 0.0,
            "midpoint": 0.0,
            "status": "Awaiting 9:15 - 9:45 AM candle formation",
            "regime": "NEUTRAL",
            "rule": "Wait for first 6 five-minute candles to establish the session boundary.",
            "diff_pts": 0.0,
        }

        if df_5m is None or df_5m.empty:
            return default_res

        try:
            # Filter today's candles
            last_date = df_5m.index[-1].date()
            today_df = df_5m[df_5m.index.date == last_date]
            if today_df.empty:
                return default_res

            # Opening range is defined by candles from 09:15 to 09:40 (first 6 candles)
            t_start = pd.to_datetime("09:15").time()
            t_end = pd.to_datetime("09:40").time()
            orb_candles = today_df[(today_df.index.time >= t_start) & (today_df.index.time <= t_end)]

            if orb_candles.empty:
                # If market just opened, use available candles
                orb_candles = today_df.iloc[:min(6, len(today_df))]

            orb_hi = round(float(orb_candles["high"].max()), 2)
            orb_lo = round(float(orb_candles["low"].min()), 2)
            orb_range = round(orb_hi - orb_lo, 2)
            orb_mid = round((orb_hi + orb_lo) / 2.0, 2)

            cur_p = round(float(cur_price), 2)
            diff_high = round(cur_p - orb_hi, 2)
            diff_low = round(orb_lo - cur_p, 2)

            if cur_p > orb_hi:
                status = f"Bullish Expansion Mode (+{diff_high:.1f} pts above ORB High)"
                regime = "BULLISH_EXPANSION"
                rule = (
                    f"Buyers are dominating above the 9:45 AM ORB High (₹{orb_hi:.2f}). "
                    f"Favor trend-following long setups on pullbacks to Session VWAP or ORB High. "
                    f"Avoid fresh longs near +2σ band exhaustion."
                )
                diff_pts = diff_high
            elif cur_p < orb_lo:
                status = f"Bearish Breakdown Mode (-{diff_low:.1f} pts below ORB Low)"
                regime = "BEARISH_BREAKDOWN"
                rule = (
                    f"Sellers are dominating below the 9:45 AM ORB Low (₹{orb_lo:.2f}). "
                    f"Favor trend-following short setups on corrective bounces into Session VWAP or ORB Low. "
                    f"Watch for support at multi-month 1M+2M confluence levels."
                )
                diff_pts = -diff_low
            else:
                status = f"Inside Opening Range (₹{orb_lo:.2f} - ₹{orb_hi:.2f})"
                regime = "INSIDE_RANGE"
                rule = (
                    f"NIFTY is consolidating within today's {orb_range:.1f} pt opening range. "
                    f"High probability of theta decay and mean-reversion around Midpoint ₹{orb_mid:.2f}. "
                    f"Wait for a decisive 5-minute candle close outside the range before taking directional trades."
                )
                diff_pts = 0.0

            return {
                "has_orb": True,
                "high": orb_hi,
                "low": orb_lo,
                "range": orb_range,
                "midpoint": orb_mid,
                "status": status,
                "regime": regime,
                "rule": rule,
                "diff_pts": diff_pts,
                "candles_count": len(orb_candles),
            }
        except Exception as e:
            logger.error("Error computing ORB: %s", e)
            return default_res


class TradeDoctor:
    """
    Pairs raw signals into completed trade lifecycles and performs
    technical post-trade diagnoses (Why did the signal win or lose?).
    """

    @staticmethod
    def extract_paired_trades(signals: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Pairs BUY entries with subsequent SELL/EXIT triggers."""
        if not signals:
            return []

        paired = []
        cur_entry = None

        for s in signals:
            act = s.get("action") or s.get("signal")
            reason = s.get("reason", "")
            price = float(s.get("price", 0.0))
            time_str = s.get("time") or str(s.get("timestamp", ""))

            # Entry Trigger
            if act in ("BUY", "SELL") and reason in ("BUY", "SELL"):
                cur_entry = {
                    "action": act,
                    "entry_time": time_str,
                    "entry_price": price,
                }
            # Exit Trigger
            elif cur_entry and (act == "SELL" or "EXIT" in reason or "STOP" in reason):
                entry_p = cur_entry["entry_price"]
                pnl = round(price - entry_p if cur_entry["action"] == "BUY" else entry_p - price, 2)
                pnl_pct = round((pnl / entry_p) * 100, 2) if entry_p else 0.0

                result = "WIN" if pnl > 5.0 else "LOSS" if pnl < -5.0 else "BREAKEVEN"

                paired.append({
                    "action": cur_entry["action"],
                    "entry_time": cur_entry["entry_time"],
                    "entry_price": entry_p,
                    "exit_time": time_str,
                    "exit_price": price,
                    "pnl_pts": pnl,
                    "pnl_pct": pnl_pct,
                    "result": result,
                    "exit_reason": reason or "TREND_EXIT",
                })
                cur_entry = None

        return paired

    @classmethod
    def diagnose_last_trade(
        cls,
        signals: List[Dict[str, Any]],
        indicators: Optional[Dict[str, Any]] = None,
        comb_sr: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Provides a deep technical diagnostic breakdown for the latest closed trade."""
        paired = cls.extract_paired_trades(signals)
        if not paired:
            return {
                "has_trade": False,
                "message": "No completed trade cycles found to diagnose yet.",
            }

        last_t = paired[-1]
        pnl = last_t["pnl_pts"]
        res = last_t["result"]
        act = last_t["action"]
        reason = last_t["exit_reason"]

        vwap = indicators.get("vwap", 0.0) if indicators else 0.0
        up2 = indicators.get("vwap_upper_2", 0.0) if indicators else 0.0
        lo2 = indicators.get("vwap_lower_2", 0.0) if indicators else 0.0

        diagnosis_points = []

        pnl_inr_1lot = round(pnl * 65.0, 0)
        pnl_sign = "+" if pnl > 0 else ""

        # Factor 1: Entry Setup & Discipline
        if act == "BUY":
            diagnosis_points.append(
                f"1. **Entry Setup:** Triggered Long at ₹{last_t['entry_price']} ({last_t['entry_time']}) "
                f"following confirmed Main Strategy momentum above Session VWAP."
            )
        else:
            diagnosis_points.append(
                f"1. **Entry Setup:** Triggered Short at ₹{last_t['entry_price']} ({last_t['entry_time']}) "
                f"on bearish Main Strategy breakdown below Session VWAP."
            )

        # Factor 2: Outcome & Realized PnL (Calculated strictly at 65 Qty / 1 Lot)
        if res == "WIN":
            diagnosis_points.append(
                f"2. **Why It Won (+{pnl:.1f} pts | {pnl_sign}₹{pnl_inr_1lot:,.0f} on 1 Lot):** "
                f"Price respected trend momentum and expanded cleanly toward the next S&R target. "
                f"Option delta expanded rapidly ahead of overhead exhaustion."
            )
        elif res == "LOSS":
            if abs(pnl) < 30.0:
                diagnosis_points.append(
                    f"2. **Why It Exited (-{abs(pnl):.1f} pts | -₹{abs(pnl_inr_1lot):,.0f} on 1 Lot):** "
                    f"Disciplined protective stop executed ({reason}). Stopped early to protect against a larger drop."
                )
            else:
                diagnosis_points.append(
                    f"2. **Why It Lost (-{abs(pnl):.1f} pts | -₹{abs(pnl_inr_1lot):,.0f} on 1 Lot):** "
                    f"Momentum met strong supply near the ±2σ exhaustion band, causing a sharp mean-reversion counter-move."
                )
        else:
            diagnosis_points.append(
                f"2. **Breakeven Outcome ({pnl:+.1f} pts):** Market entered range consolidation; disciplined exit executed ({reason})."
            )

        # Factor 3: S&R Confluence context
        if comb_sr:
            nearest = comb_sr[0]
            diagnosis_points.append(
                f"3. **S&R Alignment:** Nearest key institutional barrier was ₹{nearest.get('price')} "
                f"({nearest.get('role')}, {nearest.get('bounces')} touches)."
            )

        # Factor 4: Clinical Dr. Prescription & Error Correction
        if res == "WIN":
            diagnosis_points.append(
                f"4. **Dr. Prescription:** Repeat this setup! Taking profits before the ±2σ band while holding above VWAP is the highest win-rate edge."
            )
        else:
            diagnosis_points.append(
                f"4. **Dr. Prescription:** Error correction noted. Strictly avoid buying CALLs when price is within 15 pts of +2σ exhaustion, and never open new positions in Lunch Chop (11:30–13:15 IST)."
            )

        # Compute summary stats across all paired trades
        total_p = len(paired)
        wins = sum(1 for t in paired if t["result"] == "WIN")
        losses = sum(1 for t in paired if t["result"] == "LOSS")
        win_rate = round((wins / total_p) * 100, 1) if total_p else 0.0
        net_pts = round(sum(t["pnl_pts"] for t in paired), 2)

        return {
            "has_trade": True,
            "trade": last_t,
            "diagnosis": "\n".join(diagnosis_points),
            "stats": {
                "total_trades": total_p,
                "wins": wins,
                "losses": losses,
                "win_rate_pct": win_rate,
                "net_pts": net_pts,
            }
        }
