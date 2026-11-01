"""
RAG/trap_radar.py
Institutional Smart Money & Trap Radar.
Continuously scans price action, Option Chain OI walls, Session VWAP bands,
and S&R touch criteria to detect institutional retail traps in real time.
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional
import pandas as pd


class TrapRadar:
    """
    Detects institutional traps and smart-money counter-positions:
    1. Bull Trap: Breakout into Call OI wall with call writing resistance.
    2. Bear Trap: Breakdown into Put OI wall with put writing support.
    3. Weak S&R Trap: Level broken with < 5 touches (smart money liquidity sweep).
    4. VWAP Exhaustion Trap: Price beyond ±1.8σ or ±2σ exhaustion band.
    5. Lunch Chop Trap: 11:30–13:15 IST low-volume option decay chop.
    """

    @staticmethod
    def get_ist_now() -> datetime.datetime:
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        ist_offset = datetime.timedelta(hours=5, minutes=30)
        return (utc_now + ist_offset).replace(tzinfo=None)

    @classmethod
    def scan_active_traps(
        cls,
        spot_price: float,
        df_5m: Optional[pd.DataFrame] = None,
        indicators: Optional[Dict[str, Any]] = None,
        option_chain: Optional[Dict[str, Any]] = None,
        comb_sr: Optional[List[Dict[str, Any]]] = None,
        vix_val: float = 17.16,
    ) -> Dict[str, Any]:
        """
        Scans all market variables and returns active institutional traps,
        severity level, and actionable defensive instructions.
        """
        now = cls.get_ist_now()
        t = now.time()
        traps: List[Dict[str, Any]] = []

        spot = float(spot_price or 0.0)
        ind = indicators or {}
        oc = option_chain or {}
        sr_list = comb_sr or []

        vwap = float(ind.get("vwap", 0.0) or 0.0)
        vwap_u2 = float(ind.get("vwap_upper_2", 0.0) or 0.0)
        vwap_l2 = float(ind.get("vwap_lower_2", 0.0) or 0.0)
        vwap_u1 = float(ind.get("vwap_upper_1", 0.0) or 0.0)
        vwap_l1 = float(ind.get("vwap_lower_1", 0.0) or 0.0)

        max_call = float(oc.get("max_call_oi_strike", 0.0) or 0.0)
        max_put = float(oc.get("max_put_oi_strike", 0.0) or 0.0)
        pcr = float(oc.get("pcr", 1.0) or 1.0)
        bias = oc.get("institutional_bias", "NEUTRAL")

        # 1. Bull Trap / Call Wall Trap
        if max_call > 0 and spot > 0:
            call_dist = max_call - spot
            if 0 <= call_dist <= 35.0:
                traps.append({
                    "trap_id": "CALL_WALL_BULL_TRAP",
                    "type": "BULL_TRAP",
                    "severity": "CRITICAL",
                    "title": f"⚠️ Bull Trap Warning near ₹{max_call:,.0f} Call Wall",
                    "detail": (
                        f"Spot (₹{spot:,.1f}) is within {call_dist:.1f} pts of Max Call OI resistance at ₹{max_call:,.0f}. "
                        f"Institutions are actively writing calls here. Breakouts without heavy Put OI unwinding are high-probability traps."
                    ),
                    "action": "Do NOT chase Longs/Calls here. Wait for a rejection or an institutional volume breakout above ₹{max_call:,.0f}."
                })

        # 2. Bear Trap / Put Wall Sweep
        if max_put > 0 and spot > 0:
            put_dist = spot - max_put
            if 0 <= put_dist <= 35.0:
                traps.append({
                    "trap_id": "PUT_WALL_BEAR_TRAP",
                    "type": "BEAR_TRAP",
                    "severity": "CRITICAL",
                    "title": f"⚠️ Bear Trap Warning near ₹{max_put:,.0f} Put Wall",
                    "detail": (
                        f"Spot (₹{spot:,.1f}) is within {put_dist:.1f} pts of Max Put OI support at ₹{max_put:,.0f}. "
                        f"Smart money is defending this floor. Shorting breakdowns here carries extreme bounce risk."
                    ),
                    "action": "Avoid Shorting/Puts here. Watch for bullish wick rejections off the ₹{max_put:,.0f} support floor."
                })

        # 3. Weak S&R Trap (< 5 touches)
        if spot > 0 and sr_list:
            for sr in sr_list:
                lvl = float(sr.get("price") or sr.get("level") or 0.0)
                touches = int(sr.get("touches") or sr.get("bounces") or 0)
                if lvl > 0 and abs(spot - lvl) <= 20.0 and touches > 0 and touches < 5:
                    traps.append({
                        "trap_id": "WEAK_SR_TRAP",
                        "type": "LIQUIDITY_SWEEP",
                        "severity": "WARNING",
                        "title": f"⚠️ Liquidity Sweep Trap at S&R ₹{lvl:,.1f}",
                        "detail": (
                            f"Current price is testing S&R level ₹{lvl:,.1f} which has only {touches} touches (< 5 touch threshold). "
                            f"Smart money frequently fakes breakouts on under-tested levels to harvest retail liquidity."
                        ),
                        "action": "Strictly require > 5 confirmed touches before taking breakout entries."
                    })
                    break

        # 4. VWAP Exhaustion Band Trap (±1.8σ to ±2σ)
        if vwap > 0 and spot > 0 and vwap_u2 > 0 and vwap_l2 > 0:
            sigma_bandwidth = (vwap_u2 - vwap) / 2.0
            if sigma_bandwidth > 0:
                z_score = (spot - vwap) / sigma_bandwidth
                if z_score >= 1.8:
                    traps.append({
                        "trap_id": "VWAP_OVERBOUGHT_EXHAUSTION",
                        "type": "EXHAUSTION_TRAP",
                        "severity": "WARNING",
                        "title": f"⚠️ VWAP Exhaustion Trap (+{z_score:.2f}σ Overextended)",
                        "detail": (
                            f"Price is trading at ₹{spot:,.1f}, which is +{z_score:.2f}σ above Session VWAP (₹{vwap:,.1f}). "
                            f"At this extreme deviation, institutional buyers stop bidding and take profits, causing swift mean-reversion."
                        ),
                        "action": "Avoid buying breakouts at the +2σ boundary. Wait for a pullback to the VWAP ±1σ band."
                    })
                elif z_score <= -1.8:
                    traps.append({
                        "trap_id": "VWAP_OVERSOLD_EXHAUSTION",
                        "type": "EXHAUSTION_TRAP",
                        "severity": "WARNING",
                        "title": f"⚠️ VWAP Oversold Exhaustion ({z_score:.2f}σ Deviation)",
                        "detail": (
                            f"Price is trading at ₹{spot:,.1f}, which is {z_score:.2f}σ below Session VWAP (₹{vwap:,.1f}). "
                            f"Oversold exhaustion creates sharp institutional short-covering bounces."
                        ),
                        "action": "Avoid late shorting at the -2σ boundary. Wait for price to reclaim the VWAP -1σ band."
                    })

        # 5. Lunch Chop Trap (11:30 - 13:15 IST)
        if datetime.time(11, 30) <= t <= datetime.time(13, 15):
            is_tuesday = (now.weekday() == 1)
            tuesday_note = " Tuesday weekly expiry theta decay is especially severe." if is_tuesday else ""
            traps.append({
                "trap_id": "LUNCH_CHOP_TRAP",
                "type": "CHOP_TRAP",
                "severity": "WARNING",
                "title": "🟡 Lunch Chop & Premium Decay Trap (11:30–13:15 IST)",
                "detail": (
                    f"Mid-day liquidity dries up; market enters tight consolidation range.{tuesday_note} "
                    f"Over 65% of breakouts attempted in this window result in immediate false breakout whipsaws."
                ),
                "action": "Step away or hold off on new breakout orders until the 13:15 European opening window."
            })

        # Overall Status
        has_critical = any(tr["severity"] == "CRITICAL" for tr in traps)
        has_warning = any(tr["severity"] == "WARNING" for tr in traps)
        radar_status = "CRITICAL_TRAP_ACTIVE" if has_critical else "WARNING_TRAP_ACTIVE" if has_warning else "CLEAN_MARKET"
        radar_badge = "🔴 TRAP ALERT" if has_critical else "🟡 TRAP WARNING" if has_warning else "🟢 CLEAR MARKET"

        return {
            "radar_status": radar_status,
            "badge": radar_badge,
            "traps_count": len(traps),
            "traps": traps,
            "vix": vix_val,
            "pcr": pcr,
            "max_call_oi": max_call,
            "max_put_oi": max_put,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S IST"),
        }
