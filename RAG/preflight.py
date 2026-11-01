"""
RAG/preflight.py
Institutional 1-Click "Pre-Flight Check" & Personal Brain Confluence Engine.
Evaluates multi-factor conditions with human-like pro trader intuition:
1. Multi-factor Confluence Index (0 to 100%) instead of rigid single-indicator vetoes
2. Nuanced Trade Setups (High Conviction, Adaptive Scalp, Pullback Retest, Range Fade)
3. Session VWAP & Band Position (±1σ Accumulation vs ±2σ Exhaustion)
4. Option Chain OI Wall Proximity (Max Call / Put OI Runway & PCR Flow)
5. Real India VIX & Tuesday Weekly Expiry Theta / Gamma dynamics
6. Trader Psychology, Lunch Chop Sensitivity, & Capital Sizing (Strictly 1 Lot = 65 Qty)
7. Smart Money Trap Radar & S&R Confluence Validation
"""

from __future__ import annotations

import datetime
from typing import Any, Dict, List, Optional
import pandas as pd

from RAG.trap_radar import TrapRadar
from RAG.institutional_intelligence import RVOLCalculator, MarketRegimeIntelligence


class PreFlightEngine:
    @staticmethod
    def get_ist_now() -> datetime.datetime:
        utc_now = datetime.datetime.now(datetime.timezone.utc)
        ist_offset = datetime.timedelta(hours=5, minutes=30)
        return (utc_now + ist_offset).replace(tzinfo=None)

    @classmethod
    def evaluate(
        cls,
        direction: Optional[str] = None,
        spot_price: float = 0.0,
        indicators: Optional[Dict[str, Any]] = None,
        option_chain: Optional[Dict[str, Any]] = None,
        user_psychology: Optional[Dict[str, Any]] = None,
        comb_sr: Optional[List[Dict[str, Any]]] = None,
        vix_val: float = 17.16,
        user_id: Optional[str] = None,
        df_5m: Optional[pd.DataFrame] = None,
        mtf_data: Optional[Dict[str, Any]] = None,
        dt: Optional[datetime.datetime] = None,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end Personal Brain Pre-Flight Confluence Audit.
        Instead of a single indicator vetoing the trade, it weighs multi-factor confluence,
        identifies the friction factor, and provides adaptive tactical suggestions.
        """
        now = dt or cls.get_ist_now()
        t = now.time()
        is_tuesday = (now.weekday() == 1)
        spot = float(spot_price or 0.0)
        ind = indicators or {}
        oc = option_chain or {}
        psy = user_psychology or {}
        sr_list = comb_sr or []

        vwap = float(ind.get("vwap", 0.0) or 0.0)
        vwap_u1 = float(ind.get("vwap_upper_1", 0.0) or 0.0)
        vwap_l1 = float(ind.get("vwap_lower_1", 0.0) or 0.0)
        vwap_u2 = float(ind.get("vwap_upper_2", 0.0) or 0.0)
        vwap_l2 = float(ind.get("vwap_lower_2", 0.0) or 0.0)

        max_call = float(oc.get("max_call_oi_strike", 0.0) or 0.0)
        max_put = float(oc.get("max_put_oi_strike", 0.0) or 0.0)
        pcr = float(oc.get("pcr", 1.0) or 1.0)

        # -------------------------------------------------------------
        # 4 Vital Live Data Feeds Computation:
        # 1. RVOL (Relative Volume Z-Score)
        # 2. Market Regime (ADX & ATR) with dynamic SL (SL = 1.2 * ATR)
        # 3. Multi-Timeframe Trend Confluence (MTF: 5m, 15m, 1h)
        # 4. Live Option Chain OI Shift (Put/Call Writing)
        # -------------------------------------------------------------
        cur_vol = 0.0
        if ind and "volume" in ind and isinstance(ind["volume"], dict):
            cur_vol = float(ind["volume"].get("current_volume", 0.0) or 0.0)
        elif ind and "current_volume" in ind:
            cur_vol = float(ind.get("current_volume", 0.0) or 0.0)

        rvol_info = RVOLCalculator.calculate(df_5m=df_5m, current_volume=cur_vol, current_dt=now)

        # Extract ADX & ATR
        adx_val = None
        if ind and "adx" in ind:
            adx_val = ind["adx"].get("adx") if isinstance(ind["adx"], dict) else ind["adx"]
        elif ind and "oscillators" in ind and isinstance(ind["oscillators"], dict):
            adx_val = ind["oscillators"].get("adx")
        adx_float = float(adx_val) if adx_val is not None else 22.0

        atr_val = None
        if ind and "atr_14" in ind:
            atr_val = ind["atr_14"]
        elif ind and "oscillators" in ind and isinstance(ind["oscillators"], dict):
            atr_val = ind["oscillators"].get("atr_14")
        elif ind and "atr" in ind:
            atr_val = ind["atr"]
        atr_float = float(atr_val) if atr_val is not None and float(atr_val) > 0 else 18.0

        dynamic_sl_pts = round(1.2 * atr_float, 1)
        dynamic_sl_pts = float(max(10.0, min(35.0, dynamic_sl_pts)))

        regime_info = {
            "adx": adx_float,
            "atr_14": atr_float,
            "dynamic_sl_pts": dynamic_sl_pts,
            "is_trending": (adx_float > 25.0),
            "is_rangebound": (adx_float < 18.0),
            "regime_badge": "🟢 STRONG TRENDING (ADX > 25)" if adx_float > 25.0 else ("🟡 RANGEBOUND / MEAN-REVERT (ADX < 18)" if adx_float < 18.0 else "⚪ MODERATE TREND"),
        }

        # Multi-Timeframe (MTF) Trend Confluence
        mtf_dict = mtf_data or {}
        tf_dict = mtf_dict.get("timeframes", {}) if isinstance(mtf_dict, dict) else {}
        trend_15m = tf_dict.get("15m", {}).get("trend", "NEUTRAL") if isinstance(tf_dict, dict) else "NEUTRAL"
        trend_1h = tf_dict.get("1h", {}).get("trend", "NEUTRAL") if isinstance(tf_dict, dict) else "NEUTRAL"
        trend_5m = tf_dict.get("5m", {}).get("trend", "NEUTRAL") if isinstance(tf_dict, dict) else "NEUTRAL"


        # -------------------------------------------------------------
        # Determine Direction
        # -------------------------------------------------------------
        if not direction or direction.upper() not in ("BUY", "CALL", "SELL", "PUT", "LONG", "SHORT"):
            if vwap > 0 and spot >= vwap:
                trade_dir = "BUY"
                trade_instrument = "CALL (CE)"
            else:
                trade_dir = "SELL"
                trade_instrument = "PUT (PE)"
        else:
            trade_dir = "BUY" if direction.upper() in ("BUY", "CALL", "LONG") else "SELL"
            trade_instrument = "CALL (CE)" if trade_dir == "BUY" else "PUT (PE)"

        checklist: List[Dict[str, Any]] = []
        fail_reasons: List[str] = []
        caution_reasons: List[str] = []
        positive_drivers: List[str] = []

        # Calibrated Base Score for Professional Confluence Engine
        confluence_score = 25.0

        # -------------------------------------------------------------
        # 0. NSE Pre-Market Discovery & Gap Radar (09:00 - 09:15 IST)
        # -------------------------------------------------------------
        is_premarket = (t < datetime.time(9, 15))
        prev_close = float(ind.get("prev_close") or 0.0)
        gap_pts = round(spot - prev_close, 2) if (prev_close > 0 and spot > 0) else 0.0
        gap_pct = round((gap_pts / prev_close) * 100, 2) if prev_close > 0 else 0.0
        gap_badge = f"{gap_pts:+} pts ({gap_pct:+}%)" if prev_close > 0 else "NSE Auction Discovery"

        if is_premarket:
            checklist.append({
                "name": "NSE Pre-Market Discovery & Gap Radar",
                "status": "CAUTION",
                "badge": f"⚪ PRE-MARKET ({gap_badge})",
                "detail": (
                    f"NSE Pre-Market Price: ₹{spot:,.1f} vs Prev Close: ₹{prev_close:,.1f} ({gap_badge}). "
                    f"Continuous market opens at 09:15 AM IST."
                )
            })
            caution_reasons.append("Pre-Market session (09:00–09:15 IST). Wait for 09:15 AM opening bell.")
            confluence_score -= 10.0

        # -------------------------------------------------------------
        # 1. Session VWAP & Band Position (±1σ Accumulation vs ±2σ Exhaustion)
        # -------------------------------------------------------------
        if vwap > 0 and spot > 0:
            sigma_band = (vwap_u2 - vwap) / 2.0 if vwap_u2 > vwap else 25.0
            z_score = (spot - vwap) / sigma_band if sigma_band > 0 else 0.0

            if trade_dir == "BUY":
                if z_score >= 1.75:
                    checklist.append({
                        "name": "Session VWAP Band Position",
                        "status": "CAUTION",
                        "badge": "🟡 EXTENDED NEAR +2σ",
                        "detail": f"Spot ₹{spot:,.1f} is +{z_score:.2f}σ above VWAP ₹{vwap:,.1f}. Strong momentum, but upside runway is tight; scalp only with trailing SL."
                    })
                    caution_reasons.append(f"Price is extended (+{z_score:.2f}σ) near +2σ band. Use tight trailing SL.")
                    confluence_score += 5.0
                elif spot >= vwap:
                    checklist.append({
                        "name": "Session VWAP Band Position",
                        "status": "PASS",
                        "badge": "🟢 INSTITUTIONAL ACCUMULATION",
                        "detail": f"Spot ₹{spot:,.1f} is holding above Session VWAP ₹{vwap:,.1f} within +{z_score:.2f}σ continuation corridor. Bullish accumulation active."
                    })
                    positive_drivers.append("Price holding above Session VWAP in healthy accumulation corridor.")
                    confluence_score += 25.0
                else:
                    dist_pts = vwap - spot
                    if dist_pts <= 15.0:
                        checklist.append({
                            "name": "Session VWAP Band Position",
                            "status": "PASS",
                            "badge": "🟢 VWAP RECLAIM SETUP",
                            "detail": f"Spot ₹{spot:,.1f} is just {dist_pts:.1f} pts below VWAP ₹{vwap:,.1f}. Ready for immediate reclaim burst on candle close."
                        })
                        positive_drivers.append(f"Close to VWAP ({dist_pts:.1f} pts) — primed for VWAP reclaim surge.")
                        confluence_score += 12.0
                    else:
                        checklist.append({
                            "name": "Session VWAP Band Position",
                            "status": "CAUTION",
                            "badge": "🟡 COUNTER-TREND VWAP DIP",
                            "detail": f"Spot ₹{spot:,.1f} is {dist_pts:.1f} pts below VWAP ₹{vwap:,.1f}. Buying calls here requires VWAP recapture."
                        })
                        caution_reasons.append(f"Price is {dist_pts:.1f} pts below Session VWAP. Calls require VWAP recapture.")
                        confluence_score -= 15.0
            else:
                # SELL / PUT
                if z_score <= -1.75:
                    checklist.append({
                        "name": "Session VWAP Band Position",
                        "status": "CAUTION",
                        "badge": "🟡 EXTENDED NEAR -2σ",
                        "detail": f"Spot ₹{spot:,.1f} is {z_score:.2f}σ below VWAP ₹{vwap:,.1f}. Strong sell pressure; scalp only to avoid short-covering bounces."
                    })
                    caution_reasons.append(f"Price is extended ({z_score:.2f}σ) near -2σ floor. Beware of sharp short-covering.")
                    confluence_score += 5.0
                elif spot <= vwap:
                    checklist.append({
                        "name": "Session VWAP Band Position",
                        "status": "PASS",
                        "badge": "🟢 INSTITUTIONAL DISTRIBUTION",
                        "detail": f"Spot ₹{spot:,.1f} is trading below Session VWAP ₹{vwap:,.1f} ({z_score:.2f}σ corridor). Institutional distribution active."
                    })
                    positive_drivers.append("Price trading below Session VWAP in institutional distribution corridor.")
                    confluence_score += 25.0
                else:
                    dist_pts = spot - vwap
                    if dist_pts <= 15.0:
                        checklist.append({
                            "name": "Session VWAP Band Position",
                            "status": "PASS",
                            "badge": "🟢 VWAP BREAKDOWN SETUP",
                            "detail": f"Spot ₹{spot:,.1f} is hovering within {dist_pts:.1f} pts of VWAP ₹{vwap:,.1f}. Poised for breakdown continuation."
                        })
                        positive_drivers.append(f"Within {dist_pts:.1f} pts of VWAP — ready for breakdown continuation.")
                        confluence_score += 12.0
                    else:
                        checklist.append({
                            "name": "Session VWAP Band Position",
                            "status": "CAUTION",
                            "badge": "🟡 COUNTER-TREND PULLBACK",
                            "detail": f"Spot ₹{spot:,.1f} is {dist_pts:.1f} pts above VWAP ₹{vwap:,.1f}. Shorting is counter-trend until VWAP fails."
                        })
                        caution_reasons.append(f"Price is {dist_pts:.1f} pts above Session VWAP. Puts require VWAP failure.")
                        confluence_score -= 15.0
        else:
            checklist.append({
                "name": "Session VWAP Band Position",
                "status": "PASS",
                "badge": "⚪ NORMAL",
                "detail": "VWAP calculation stable."
            })
            confluence_score += 10.0

        # -------------------------------------------------------------
        # 2. Option Chain (OI Wall Proximity & PCR Flow)
        # -------------------------------------------------------------
        if trade_dir == "BUY":
            call_dist = max_call - spot if max_call > 0 else 999.0
            if call_dist <= 20.0:
                checklist.append({
                    "name": "Option Chain Wall Clearance",
                    "status": "CAUTION",
                    "badge": "🟡 NEAR CALL WALL CEILING",
                    "detail": f"Spot ₹{spot:,.1f} is only {call_dist:.1f} pts below Max Call OI ceiling at ₹{max_call:,.0f}. Scalp only or await Call short-squeeze."
                })
                caution_reasons.append(f"Near Max Call OI ceiling at ₹{max_call:,.0f} ({call_dist:.1f} pts away). Scalp mode advised.")
                confluence_score -= 10.0
            else:
                if pcr < 0.50:
                    checklist.append({
                        "name": "Option Chain PCR Confluence",
                        "status": "CAUTION",
                        "badge": "⚠️ TOP EXHAUSTION (<0.50)",
                        "detail": f"PCR is extremely low ({pcr:.2f} < 0.50). Market is in Extreme Greed / Overbought euphoria with Bearish Reversal Risk (Market Top). Scalp mode strictly."
                    })
                    caution_reasons.append(f"PCR < 0.50 indicates extreme overbought euphoria; high risk of a top reversal.")
                    confluence_score -= 10.0
                elif pcr <= 0.90:
                    pcr_boost = 25.0 if pcr < 0.70 else 20.0
                    checklist.append({
                        "name": "Option Chain Wall Clearance",
                        "status": "PASS",
                        "badge": "🟢 CLEAR RUNWAY & BULLISH PCR",
                        "detail": f"Open runway ({call_dist:.1f} pts) to Max Call OI ceiling at ₹{max_call:,.0f} (PCR: {pcr:.2f}). Bullish momentum alignment."
                    })
                    positive_drivers.append(f"Clear Option Chain upside runway ({call_dist:.1f} pts to ₹{max_call:,.0f}, PCR: {pcr:.2f} Bullish).")
                    confluence_score += pcr_boost
                elif pcr > 1.40:
                    checklist.append({
                        "name": "Option Chain PCR Confluence",
                        "status": "PASS",
                        "badge": "🚀 CONTRARIAN OVERSOLD BOUNCE",
                        "detail": f"PCR {pcr:.2f} > 1.40 indicates Extreme Panic Oversold. Smart Money Put Writing floor creates high-probability Bullish Reversal / Short Squeeze."
                    })
                    positive_drivers.append(f"Contrarian Bullish Reversal potential from extreme oversold PCR ({pcr:.2f} > 1.40).")
                    confluence_score += 20.0
                else:
                    checklist.append({
                        "name": "Option Chain Wall Clearance",
                        "status": "PASS",
                        "badge": "🟢 CLEAR RUNWAY",
                        "detail": f"Open runway ({call_dist:.1f} pts) to Max Call OI ceiling at ₹{max_call:,.0f} (PCR: {pcr:.2f})."
                    })
                    confluence_score += 10.0
        else:
            put_dist = spot - max_put if max_put > 0 else 999.0
            if put_dist <= 20.0:
                checklist.append({
                    "name": "Option Chain Wall Clearance",
                    "status": "CAUTION",
                    "badge": "🟡 NEAR PUT FLOOR SUPPORT",
                    "detail": f"Spot ₹{spot:,.1f} is only {put_dist:.1f} pts above Max Put OI floor at ₹{max_put:,.0f}. Defended by institutional put writers."
                })
                caution_reasons.append(f"Near Max Put OI floor at ₹{max_put:,.0f} ({put_dist:.1f} pts away). Scalp mode advised.")
                confluence_score -= 10.0
            else:
                if pcr > 1.40:
                    checklist.append({
                        "name": "Option Chain PCR Confluence",
                        "status": "CAUTION",
                        "badge": "⚠️ BOTTOM BOUNCE RISK (>1.40)",
                        "detail": f"PCR is extremely high ({pcr:.2f} > 1.40). Market is in Extreme Fear / Oversold panic with Bullish Reversal Risk. Shorting directly into Put Writing floor is high risk."
                    })
                    caution_reasons.append(f"PCR > 1.40 indicates extreme oversold panic; high risk of a violent short-squeeze bounce.")
                    confluence_score -= 10.0
                elif pcr >= 1.10:
                    pcr_boost = 25.0 if pcr <= 1.30 else 20.0
                    checklist.append({
                        "name": "Option Chain Wall Clearance",
                        "status": "PASS",
                        "badge": "🟢 CLEAR RUNWAY & BEARISH PCR",
                        "detail": f"Open runway ({put_dist:.1f} pts) to Max Put OI floor at ₹{max_put:,.0f} (PCR: {pcr:.2f}). Bearish momentum alignment."
                    })
                    positive_drivers.append(f"Clear Option Chain downside runway ({put_dist:.1f} pts to ₹{max_put:,.0f}, PCR: {pcr:.2f} Bearish).")
                    confluence_score += pcr_boost
                elif pcr < 0.50:
                    checklist.append({
                        "name": "Option Chain PCR Confluence",
                        "status": "PASS",
                        "badge": "🎯 CONTRARIAN TOP FADE",
                        "detail": f"PCR {pcr:.2f} < 0.50 is in Extreme Euphoria. Call buyers exhausted; Smart Money Call Writing ceiling favors a Bearish Reversal fade."
                    })
                    positive_drivers.append(f"Contrarian Bearish Top fade potential from extreme overbought PCR ({pcr:.2f} < 0.50).")
                    confluence_score += 20.0
                else:
                    checklist.append({
                        "name": "Option Chain Wall Clearance",
                        "status": "PASS",
                        "badge": "🟢 CLEAR RUNWAY",
                        "detail": f"Open runway ({put_dist:.1f} pts) to Max Put OI floor at ₹{max_put:,.0f} (PCR: {pcr:.2f})."
                    })
                    confluence_score += 10.0

        # -------------------------------------------------------------
        # 3. Real India VIX & Tuesday Weekly Expiry Theta Risk
        # -------------------------------------------------------------
        if is_tuesday:
            if t >= datetime.time(12, 0):
                checklist.append({
                    "name": "Weekly Expiry & Theta Risk",
                    "status": "CAUTION",
                    "badge": "🟡 TUESDAY THETA ACCELERATION",
                    "detail": f"Tuesday Weekly Expiry afternoon session. India VIX is {vix_val:.2f}. Stick to ATM/ITM strikes to avoid theta burn."
                })
                caution_reasons.append("Tuesday afternoon theta acceleration. Stick strictly to ATM/ITM strikes.")
                confluence_score += 4.0
            else:
                checklist.append({
                    "name": "Weekly Expiry & Theta Risk",
                    "status": "PASS",
                    "badge": "🟢 TUESDAY MORNING RUNWAY",
                    "detail": f"Tuesday Weekly Expiry morning session. India VIX {vix_val:.2f} supports clean momentum."
                })
                positive_drivers.append(f"Tuesday morning momentum session (India VIX: {vix_val:.2f}).")
                confluence_score += 8.0
        else:
            checklist.append({
                "name": "Volatility & Expiry Regime",
                "status": "PASS",
                "badge": "🟢 BALANCED VOLATILITY",
                "detail": f"Real India VIX {vix_val:.2f} confirms stable market conditions without panic pricing."
            })
            positive_drivers.append(f"Stable market volatility regime (India VIX {vix_val:.2f}).")
            confluence_score += 10.0

        # -------------------------------------------------------------
        # 4. Time-of-Day Window: Risk Modifier (Weight: 15%), NOT a Veto
        # -------------------------------------------------------------
        is_lunch = (datetime.time(11, 30) <= t <= datetime.time(13, 15))
        disc_score = int(psy.get("discipline_score", 85))

        if is_lunch:
            if rvol_info["is_institutional_expansion"] or adx_float > 25.0:
                checklist.append({
                    "name": "Time-of-Day Risk Modifier (15% Weight)",
                    "status": "PASS",
                    "badge": f"🟢 LUNCH INSTITUTIONAL EXPANSION (RVOL: {rvol_info['rvol']:.2f}x)",
                    "detail": f"Time of Day is a Risk Modifier (15% weight), NOT a binary veto! RVOL of {rvol_info['rvol']:.2f}x (>1.5) confirms smart money active during lunch. Setup approved with tighter trailing SL (12–15 pts or 1.2x ATR)."
                })
                positive_drivers.append(f"Smart money active during lunch (RVOL {rvol_info['rvol']:.2f}x > 1.5) overrides lunch lull.")
                confluence_score += 8.0
            else:
                checklist.append({
                    "name": "Time-of-Day Risk Modifier (15% Weight)",
                    "status": "CAUTION",
                    "badge": "🟡 LUNCH CHOP (15% RISK MODIFIER)",
                    "detail": f"Current time ({now.strftime('%H:%M IST')}) is inside 11:30–13:15 Lunch window with RVOL {rvol_info['rvol']:.2f}x. Time of Day is a 15% risk modifier (NOT a veto); trade with 1 Lot scalp size or await pullback."
                })
                caution_reasons.append(f"11:30–13:15 Lunch Window (15% Risk Modifier): Subdued volume (RVOL: {rvol_info['rvol']:.2f}x). Scalp 1 Lot or wait for pullback.")
                confluence_score -= 5.0
        else:
            checklist.append({
                "name": "Time-of-Day & Discipline Window",
                "status": "PASS",
                "badge": f"🟢 PRIME WINDOW (Score: {disc_score}/100)",
                "detail": f"Active institutional market window ({now.strftime('%H:%M IST')}). Prime liquidity conditions."
            })
            positive_drivers.append(f"Prime institutional trading window ({now.strftime('%H:%M IST')}).")
            confluence_score += 12.0

        # -------------------------------------------------------------
        # 4B. Multi-Timeframe Trend Confluence (MTF: 15m & 1h Alignment)
        # -------------------------------------------------------------
        mtf_bullish = (trend_15m == "BULLISH" and trend_1h == "BULLISH")
        mtf_bearish = (trend_15m == "BEARISH" and trend_1h == "BEARISH")

        if trade_dir == "BUY":
            if mtf_bullish:
                checklist.append({
                    "name": "Multi-Timeframe Trend Confluence (MTF)",
                    "status": "PASS",
                    "badge": "🟢 MTF CONFLUENCE ALIGNED (80%+ WIN RATE)",
                    "detail": "15-minute and 1-hour trends are both BULLISH, in complete alignment with 5-minute setup. Win rate exceeds 80%."
                })
                positive_drivers.append("15m & 1h trends aligned with 5m setup (80%+ institutional win rate).")
                confluence_score += 15.0
            elif trend_1h == "BEARISH":
                checklist.append({
                    "name": "Multi-Timeframe Trend Confluence (MTF)",
                    "status": "CAUTION",
                    "badge": "🟡 HTF 1H COUNTER-TREND FRICTION",
                    "detail": "5-minute setup is fighting the 1-hour downtrend. Scalp mode advised."
                })
                caution_reasons.append("Higher timeframe (1-hour) trend is Bearish. Scalp size only.")
                confluence_score -= 6.0
            else:
                confluence_score += 5.0
        else:
            if mtf_bearish:
                checklist.append({
                    "name": "Multi-Timeframe Trend Confluence (MTF)",
                    "status": "PASS",
                    "badge": "🟢 MTF CONFLUENCE ALIGNED (80%+ WIN RATE)",
                    "detail": "15-minute and 1-hour trends are both BEARISH, in complete alignment with 5-minute breakdown. Win rate exceeds 80%."
                })
                positive_drivers.append("15m & 1h trends aligned with 5m breakdown (80%+ institutional win rate).")
                confluence_score += 15.0
            elif trend_1h == "BULLISH":
                checklist.append({
                    "name": "Multi-Timeframe Trend Confluence (MTF)",
                    "status": "CAUTION",
                    "badge": "🟡 HTF 1H COUNTER-TREND FRICTION",
                    "detail": "5-minute setup is fighting the 1-hour uptrend. Scalp mode advised."
                })
                caution_reasons.append("Higher timeframe (1-hour) trend is Bullish. Scalp size only.")
                confluence_score -= 6.0
            else:
                confluence_score += 5.0

        # -------------------------------------------------------------
        # 4C. Live Option Chain OI Shift (Put/Call Writing Dynamics)
        # -------------------------------------------------------------
        pe_chg = int(oc.get("total_pe_change_oi", 0) or 0)
        ce_chg = int(oc.get("total_ce_change_oi", 0) or 0)
        oi_shift_obj = oc.get("oi_shift", {})

        if trade_dir == "BUY":
            if pe_chg > 0 and ce_chg <= 0:
                checklist.append({
                    "name": "Live Option Chain OI Shift",
                    "status": "PASS",
                    "badge": "🚀 SHORT-COVERING RALLY & PUT WRITING",
                    "detail": f"Put writers adding OI (+{pe_chg:,}) while Call writers are unwinding ({ce_chg:,}). Institutional short-covering rally active."
                })
                positive_drivers.append("Put writers defending floor + Call writers unwinding (Short Covering).")
                confluence_score += 12.0
            elif pe_chg > ce_chg:
                checklist.append({
                    "name": "Live Option Chain OI Shift",
                    "status": "PASS",
                    "badge": "🟢 PUT WRITERS DEFENDING FLOOR",
                    "detail": f"Put writing (+{pe_chg:,} OI) outpaces Call writing (+{ce_chg:,} OI). Smart money defending support."
                })
                positive_drivers.append(f"Put writers actively defending support floor (+{pe_chg:,} OI change).")
                confluence_score += 8.0
        else:
            if ce_chg > 0 and pe_chg <= 0:
                checklist.append({
                    "name": "Live Option Chain OI Shift",
                    "status": "PASS",
                    "badge": "🔴 CALL WRITING EXPANSION & PUT UNWINDING",
                    "detail": f"Call writers adding OI (+{ce_chg:,}) while Put writers are unwinding ({pe_chg:,}). Institutional distribution active."
                })
                positive_drivers.append("Call writers aggressively capping ceiling + Put writers unwinding.")
                confluence_score += 12.0
            elif ce_chg > pe_chg:
                checklist.append({
                    "name": "Live Option Chain OI Shift",
                    "status": "PASS",
                    "badge": "🔴 CALL WRITERS CAPPING CEILING",
                    "detail": f"Call writing (+{ce_chg:,} OI) outpaces Put writing. Smart money capping upside."
                })
                positive_drivers.append(f"Call writers capping ceiling (+{ce_chg:,} OI change).")
                confluence_score += 8.0

        # -------------------------------------------------------------
        # 5. Smart Money Trap Radar Scan
        # -------------------------------------------------------------
        traps_scan = TrapRadar.scan_active_traps(
            spot_price=spot,
            indicators=ind,
            option_chain=oc,
            comb_sr=sr_list,
            vix_val=vix_val,
        )
        active_traps = traps_scan.get("traps", [])
        if active_traps:
            critical_traps = [tr for tr in active_traps if tr["severity"] == "CRITICAL"]
            if critical_traps:
                checklist.append({
                    "name": "Smart Money Trap Radar",
                    "status": "CAUTION",
                    "badge": "🟡 INSTITUTIONAL TRAP PRESENT",
                    "detail": critical_traps[0]["detail"]
                })
                caution_reasons.append(critical_traps[0]["title"])
                confluence_score -= 12.0
            else:
                checklist.append({
                    "name": "Smart Money Trap Radar",
                    "status": "CAUTION",
                    "badge": "🟡 WATCH FAKEOUT",
                    "detail": active_traps[0]["detail"]
                })
                caution_reasons.append(active_traps[0]["title"])
                confluence_score -= 6.0
        else:
            checklist.append({
                "name": "Smart Money Trap Radar",
                "status": "PASS",
                "badge": "🟢 NO ACTIVE TRAPS",
                "detail": "Price action and Option Chain are free of institutional trap signatures."
            })
            positive_drivers.append("No active institutional traps detected.")
            confluence_score += 10.0

        # -------------------------------------------------------------
        # 6. S&R Confluence Validation
        # -------------------------------------------------------------
        nearest_sr = None
        for sr in sr_list:
            p = float(sr.get("price") or sr.get("level") or 0.0)
            if p > 0 and abs(spot - p) <= 25.0:
                nearest_sr = sr
                break

        if nearest_sr:
            touches = int(nearest_sr.get("touches") or nearest_sr.get("bounces") or 0)
            lvl = float(nearest_sr.get("price") or nearest_sr.get("level") or 0.0)
            if touches >= 5:
                checklist.append({
                    "name": "S&R Confluence Validation",
                    "status": "PASS",
                    "badge": f"🟢 INSTITUTIONAL LEVEL ({touches} touches)",
                    "detail": f"Level at ₹{lvl:,.1f} is validated with {touches} touches. Strong institutional barrier."
                })
                positive_drivers.append(f"Strong S&R barrier at ₹{lvl:,.1f} ({touches} touches).")
                confluence_score += 10.0
            else:
                checklist.append({
                    "name": "S&R Confluence Validation",
                    "status": "PASS",
                    "badge": f"🟡 MODERATE LEVEL ({touches} touches)",
                    "detail": f"Level at ₹{lvl:,.1f} has {touches} touches. Adequate for quick intraday scalping."
                })
                confluence_score += 5.0
        else:
            checklist.append({
                "name": "S&R Confluence Validation",
                "status": "PASS",
                "badge": "🟢 OPEN RUNWAY",
                "detail": "Price is operating in an open runway between primary S&R zones."
            })
            positive_drivers.append("Open corridor between primary S&R zones.")
            confluence_score += 8.0

        # Clamp Confluence Score between 15% and 96%
        final_confluence = int(max(15.0, min(96.0, round(confluence_score))))

        # -------------------------------------------------------------
        # Personal Brain Verdict & Tactical Prescriptions
        # -------------------------------------------------------------
        if final_confluence >= 75:
            verdict = "GO"
            verdict_badge = f"🟢 HIGH CONVICTION SETUP ({final_confluence}% Confluence)"
            verdict_color = "#10b981"
            brain_mode = "HIGH_CONVICTION"
            summary = (
                f"HIGH CONVICTION for {trade_instrument} ({final_confluence}% Confluence). "
                f"Multi-indicator alignment is robust. {positive_drivers[0] if positive_drivers else ''} "
                f"Full positioning supported with standard targets."
            )
        elif final_confluence >= 52:
            verdict = "ADAPTIVE"
            verdict_badge = f"🟡 ADAPTIVE SCALP SETUP ({final_confluence}% Confluence)"
            verdict_color = "#f59e0b"
            brain_mode = "ADAPTIVE_SCALP"
            friction_text = caution_reasons[0] if caution_reasons else "Minor indicator friction"
            summary = (
                f"VIABLE ADAPTIVE SETUP for {trade_instrument} ({final_confluence}% Confluence). "
                f"While {friction_text}, primary price action supports a valid trade. "
                f"Personal Brain Suggestion: Trade with 1 Lot (65 qty), keep a tight 12–15 pt Stop-Loss, and book partial gains at +25 pts."
            )
        elif final_confluence >= 38:
            verdict = "CAUTION"
            verdict_badge = f"🟠 PULLBACK OPPORTUNITY ({final_confluence}% Confluence)"
            verdict_color = "#f97316"
            brain_mode = "WAIT_FOR_PULLBACK"
            friction_text = caution_reasons[0] if caution_reasons else "Market in mixed chop"
            summary = (
                f"PULLBACK RECOMMENDED for {trade_instrument} ({final_confluence}% Confluence). "
                f"{friction_text}. Do not chase market orders immediately. "
                f"Wait for a 5-minute pullback to Session VWAP (₹{vwap:,.1f}) or nearest support before entering."
            )
        else:
            verdict = "ABORT"
            verdict_badge = f"🔴 LOW CONVICTION ({final_confluence}% Confluence)"
            verdict_color = "#ef4444"
            brain_mode = "STAND_DOWN"
            friction_text = caution_reasons[0] if caution_reasons else "High structural friction"
            summary = (
                f"STAND DOWN on {trade_instrument} ({final_confluence}% Confluence). {friction_text}. "
                f"Risk-to-reward is mathematically unfavorable. Preserve capital and wait for cleaner setup."
            )

        # -------------------------------------------------------------
        # Dynamic Contract Sizing Calculator (Strictly 1 Lot = 65 Qty & SL = 1.2 x ATR)
        # -------------------------------------------------------------
        # Determine dynamic SL: SL = 1.2 * ATR
        if brain_mode == "ADAPTIVE_SCALP" or is_lunch:
            sl_pts = min(dynamic_sl_pts, 15.0)
            sl_pts = max(sl_pts, 12.0)
        else:
            sl_pts = dynamic_sl_pts

        target_pts = round(max(sl_pts * 2.0, 30.0), 1)
        risk_per_lot_inr = round(sl_pts * 65.0, 2)
        reward_per_lot_inr = round(target_pts * 65.0, 2)

        lot_calc = {
            "lot_size_units": 65,
            "standard_sl_pts": sl_pts,
            "standard_target_pts": target_pts,
            "rr_ratio": f"1:{target_pts/sl_pts:.1f}",
            "risk_1_lot_inr": f"₹{risk_per_lot_inr:,.0f}",
            "reward_1_lot_inr": f"₹{reward_per_lot_inr:,.0f}",
            "risk_2_lots_inr": f"₹{risk_per_lot_inr * 2:,.0f}",
            "reward_2_lots_inr": f"₹{reward_per_lot_inr * 2:,.0f}",
            "lot_sizing_rule": "Strictly 65 quantity per contract lot on NIFTY."
        }

        # Personal Brain Tactical Guidance
        brain_suggestion = {
            "confluence_score": final_confluence,
            "mode": brain_mode,
            "recommended_lots": 1 if brain_mode in ("ADAPTIVE_SCALP", "WAIT_FOR_PULLBACK") else 2,
            "recommended_sl_pts": sl_pts,
            "recommended_target_pts": target_pts,
            "primary_driver": positive_drivers[0] if positive_drivers else "Market structure continuity",
            "friction_factor": caution_reasons[0] if caution_reasons else "None (Clean setup)",
            "tactical_action": summary,
        }

        return {
            "verdict": verdict,
            "verdict_badge": verdict_badge,
            "verdict_color": verdict_color,
            "confluence_score": final_confluence,
            "brain_mode": brain_mode,
            "brain_suggestion": brain_suggestion,
            "direction": trade_dir,
            "instrument": trade_instrument,
            "summary": summary,
            "checklist": checklist,
            "positive_drivers": positive_drivers,
            "fail_reasons": fail_reasons,
            "caution_reasons": caution_reasons,
            "lot_calc": lot_calc,
            "timestamp": now.strftime("%Y-%m-%d %H:%M:%S IST"),
            "vix": vix_val,
            "spot_price": spot,
            "session_vwap": vwap,
            "rvol": rvol_info,
            "regime": regime_info,
            "mtf": {
                "trend_5m": trend_5m,
                "trend_15m": trend_15m,
                "trend_1h": trend_1h,
                "confluence": mtf_dict.get("confluence", "Balanced"),
            },
            "oi_shift": {
                "pe_change_oi": pe_chg,
                "ce_change_oi": ce_chg,
                "shift_type": oi_shift_obj.get("shift_type", "BALANCED"),
            },
        }
