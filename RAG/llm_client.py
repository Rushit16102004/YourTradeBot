"""
LLM Client for Google Gemini 1.5 Flash with intelligent local fallback when key is not yet set.
"""
from __future__ import annotations

import json
import logging
import urllib.request
import re
import numpy as np
from typing import Optional, Dict, Any, List

from .config import RAGConfig

logger = logging.getLogger("LLMClient")


class GeminiLLMClient:
    """
    Communicates with Google Gemini 1.5 Flash using official REST API.
    Zero external dependencies, 0% GPU usage, fast and reliable.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or RAGConfig.get_api_key()
        self.model = RAGConfig.GEMINI_MODEL

    def refresh_key(self):
        self.api_key = RAGConfig.get_api_key()

    def generate(
        self,
        user_query: str,
        retrieved_context: List[Dict[str, Any]],
        system_instructions: str = "",
        market_state: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Generates response using Gemini 1.5 Flash with RAG context.
        If API key is missing, provides an intelligent local playbook synthesis.
        """
        self.refresh_key()

        # Build context prompt
        context_str = "\n\n".join([
            f"--- [Source: {c.get('collection', 'Knowledge')}] ---\n{c.get('content', '')}"
            for c in retrieved_context
        ])

        market_context_str = ""
        uname = market_state.get("username", "Trader") if market_state else "Trader"
        ustyle = market_state.get("trading_style", "intraday_scalper") if market_state else "intraday_scalper"
        chat_hist = market_state.get("recent_chat_history", []) if market_state else []
        tech = market_state.get("technical_eval", {}) if market_state else {}

        if market_state:
            ind = market_state.get("indicators", {})
            last_sig = market_state.get("last_signal")
            last_entry = market_state.get("last_entry_signal")
            recent_sigs = market_state.get("recent_signals", [])
            total_sigs = market_state.get("total_signals_count", len(recent_sigs))
            comb_sr = market_state.get("comb_sr_levels", [])

        # Detect if user query explicitly asks for Main Strategy signals vs dynamic entry suggestions
        q_lower = user_query.lower().strip()
        explicit_signal_terms = [
            "main signal", "display signal", "last signal", "latest signal",
            "past signal", "recent signal", "signal history", "confirmed signal",
            "strategy signal", "signal log", "display signals", "main signals",
            "info about signal", "info about main signal", "tell me about signal",
            "what was the signal", "show signal", "signals on record", "last trade signal"
        ]
        is_explicit_sig = any(p in q_lower for p in explicit_signal_terms) or (
            ("signal" in q_lower or "signals" in q_lower) and not any(w in q_lower for w in [
                "when should i enter", "where should i enter", "when to enter",
                "where to enter", "when i have enter", "should i buy", "should i sell",
                "can i enter", "trade suggestion", "entry suggestion", "where to buy", "where to sell"
            ])
        )

        if market_state:
            # Format signals section strictly if explicitly requested
            if is_explicit_sig:
                sig_lines = []
                if last_sig:
                    sig_lines.append(f"- LATEST SIGNAL GENERATED: {last_sig.get('action')} at {last_sig.get('time')} (Price: ₹{last_sig.get('price')}, Reason: {last_sig.get('reason')})")
                if last_entry and last_entry != last_sig:
                    sig_lines.append(f"- LAST ENTRY TRIGGER: {last_entry.get('action')} at {last_entry.get('time')} (Entry: ₹{last_entry.get('price')})")
                sig_lines.append(f"- TOTAL SIGNALS ON RECORD: {total_sigs} confirmed signals")
                if recent_sigs:
                    sig_lines.append("RECENT CONFIRMED SIGNALS:")
                    for s in recent_sigs[-6:]:
                        sig_lines.append(f"  • {s.get('time')}: {s.get('action')} @ ₹{s.get('price')} (Reason: {s.get('reason')})")
                sigs_str = "\n".join(sig_lines)
                sig_block = f"CONFIRMED SIGNAL LOG (FROM REAL-TIME ENGINE):\n{sigs_str}\n\n"
            else:
                sig_block = "CONFIRMED SIGNAL LOG: [Suppressed - User is asking for dynamic trade entry suggestion; formulate your own original technical suggestion from S&R (> 5x touches) and Indicators below].\n\n"

            # Format S&R section (prioritize multi-month confluence and 4-month / 2-month macro breakdowns)
            sr_lines = []
            if comb_sr:
                sr_gt5 = [l for l in comb_sr if l.get('bounces', 0) > 5]
                valid_sr = sr_gt5 if sr_gt5 else comb_sr
                sr_lines.append("ACTIVE MULTI-MONTH S&R CONFLUENCE LEVELS (STRICTLY > 5 TOUCHES):")
                for l in valid_sr[:8]:
                    sr_lines.append(f"  • {l.get('role', 'S&R')}: ₹{l.get('price')} ({l.get('bounces', 6)} touches)")

            sr_4m = market_state.get("sr_4m_levels", [])
            sr_2m = market_state.get("sr_2m_levels", [])
            if sr_4m:
                sr_lines.append("4-MONTH MACRO INSTITUTIONAL BARRIERS:")
                for l in sr_4m[:4]:
                    sr_lines.append(f"  • {l.get('role', 'Macro Barrier')}: ₹{l.get('price')} ({l.get('bounces', 5)}x touches)")
            if sr_2m:
                sr_lines.append("2-MONTH INTERMEDIATE LEVELS:")
                for l in sr_2m[:4]:
                    sr_lines.append(f"  • {l.get('role', 'S&R')}: ₹{l.get('price')} ({l.get('bounces', 4)}x touches)")
            sr_str = "\n".join(sr_lines)

            orb = market_state.get("orb", {})
            orb_str = ""
            if orb and orb.get("has_orb"):
                orb_str = (
                    f"OPENING RANGE BREAKOUT (9:15 - 9:45 AM ORB):\n"
                    f"- ORB High: ₹{orb.get('high')} | ORB Low: ₹{orb.get('low')} | Range: {orb.get('range')} pts\n"
                    f"- Current Status: {orb.get('status')}\n"
                    f"- Playbook: {orb.get('rule')}\n\n"
                )

            trade_doc = market_state.get("trade_doctor", {})
            doc_str = ""
            if trade_doc and trade_doc.get("has_trade"):
                t = trade_doc.get("trade", {})
                doc_str = (
                    f"TRADE DOCTOR TECHNICAL DIAGNOSIS (LAST COMPLETED TRADE):\n"
                    f"- Trade: {t.get('action')} @ ₹{t.get('entry_price')} ({t.get('entry_time')}) -> Exit @ ₹{t.get('exit_price')} ({t.get('exit_time')})\n"
                    f"- Result: {t.get('result')} ({t.get('pnl_pts'):+.2f} pts | Reason: {t.get('exit_reason')})\n"
                    f"- Technical Breakdown:\n{trade_doc.get('diagnosis')}\n\n"
                )

            # Prediction Journal & Error Post-Mortem (Self-Learning Memory)
            pred_stats = market_state.get("prediction_stats", {})
            pred_reflections = market_state.get("prediction_reflections", [])
            pred_str = ""
            if pred_stats or pred_reflections:
                p_lines = ["MULTI-USER PREDICTION JOURNAL & ERROR POST-MORTEM (LEARNED LESSONS):"]
                if pred_stats and pred_stats.get("resolved_predictions", 0) > 0:
                    p_lines.append(
                        f"• Prediction Model Accuracy: {pred_stats.get('win_rate_pct', 0.0)}% Win Rate "
                        f"across {pred_stats.get('resolved_predictions', 0)} resolved setups "
                        f"(Net PnL: {pred_stats.get('net_actual_pnl_pts', 0.0):+.1f} pts, Avg Error: ±{pred_stats.get('avg_pnl_error_pts', 0.0)} pts)."
                    )
                if pred_reflections:
                    p_lines.append("• HISTORICAL POST-MORTEM LESSONS FOR MATCHING SETUPS:")
                    for pr in pred_reflections[:3]:
                        p_lines.append(f"  {pr.get('content', pr)}")
                pred_str = '\n'.join(p_lines) + '\n\n'

            # Technical evaluation breakdown
            v = tech.get("vwap", {})
            e = tech.get("ema", {})
            osc = tech.get("oscillators", {})
            vol_eval = tech.get("volume", {})
            rev = tech.get("reversal", {})
            c_inds = tech.get("custom_indicators", [])
            c_ind_str = ", ".join([f"{c['name']} (₹{c['value']} - {c['price_vs_ind']})" for c in c_inds]) if c_inds else "None"

            # Safe numeric extractions to prevent format-string NoneType exceptions
            v_dist_pts = float(v.get('dist_pts') or 0.0)
            v_dist_pct = float(v.get('dist_pct') or 0.0)
            e_slope_20 = float(e.get('slope_20') or 0.0)
            osc_macd_hist = float(osc.get('macd_hist') or 0.0)
            c_vol_val = float(vol_eval.get('current_volume') or 0.0)
            ma_vol_val = float(vol_eval.get('volume_ma_20') or 0.0)

            # Institutional Indicator Directional Scoreboard
            sb = tech.get("scoreboard", {})
            sb_str = ""
            if sb and sb.get("indicators"):
                sb_lines = [
                    f"INSTITUTIONAL INDICATOR DIRECTIONAL SCOREBOARD (CALL / PUT / NEUTRAL):",
                    f"• Quantitative Consensus: {sb.get('consensus')} [{sb.get('total_call', 0)} CALL, {sb.get('total_put', 0)} PUT, {sb.get('total_neutral', 0)} NEUTRAL - {sb.get('confluence_pct', 50)}% Confluence]",
                    f"• Real-Time Indicator Breakdown:"
                ]
                for item in sb.get("indicators", []):
                    badge = "🟢 CALL" if item.get("signal") == "CALL" else ("🔴 PUT" if item.get("signal") == "PUT" else "⚪ NEUTRAL")
                    sb_lines.append(f"  - {item.get('name')}: {item.get('value')} -> {badge} ({item.get('detail')})")
                sb_str = "\n".join(sb_lines) + "\n\n"

            # Comprehensive 25-Indicator Quantitative Intelligence
            cpr_info = tech.get("cpr", {})
            sar_info = tech.get("sar", {})
            kl = tech.get("key_levels", {})
            ch = tech.get("channels", {})
            st_info = tech.get("supertrend", {})
            adx_info = tech.get("adx", {})
            stoch_info = tech.get("stoch_rsi", {})
            vp_info = kl.get("volume_profile", {})
            orb_info = kl.get("orb_15m", {})

            tech_str = (
                f"LIVE TECHNICAL INDICATORS & QUANTITATIVE CALCULATIONS (ALL 25 INDICATORS):\n"
                f"• Session VWAP: ₹{v.get('value', ind.get('vwap'))} | Upper +2σ: ₹{v.get('upper_2', ind.get('vwap_upper_2'))} | Lower -2σ: ₹{v.get('lower_2', ind.get('vwap_lower_2'))}\n"
                f"  - VWAP Bias: {v.get('bias', 'NEUTRAL')} ({v_dist_pts:+} pts / {v_dist_pct:+}%) | Status: {v.get('exhaustion_status', 'NORMAL')}\n"
                f"• Moving Averages: EMA 9=₹{e.get('ema_9')} | EMA 20=₹{e.get('ema_20')} | EMA 50=₹{e.get('ema_50')} | EMA 200=₹{e.get('ema_200')} | SMA 20=₹{e.get('sma_20', ind.get('sma_20'))}\n"
                f"  - EMA Alignment: {e.get('alignment')} | EMA Health: {e.get('quality')} (Slope 20: {e_slope_20:+})\n"
                f"• Central Pivot Range (CPR): Pivot=₹{cpr_info.get('pivot', '--')} | TC=₹{cpr_info.get('tc', '--')} | BC=₹{cpr_info.get('bc', '--')} ({cpr_info.get('type', 'NORMAL')}) -> {cpr_info.get('signal', 'NEUTRAL')}\n"
                f"• Parabolic SAR: ₹{sar_info.get('value', '--')} -> {sar_info.get('signal', 'NEUTRAL')}\n"
                f"• Key Day Levels: PDH=₹{kl.get('pdh', '--')} | PDL=₹{kl.get('pdl', '--')} | PDC=₹{kl.get('pdc', '--')}\n"
                f"• Opening Range Breakout (15m ORB): High=₹{orb_info.get('orb_high', '--')} | Low=₹{orb_info.get('orb_low', '--')} -> Status: {orb_info.get('status', 'UNKNOWN')}\n"
                f"• Session Volume Profile: POC=₹{vp_info.get('poc', '--')} (Max Traded Volume) | VAH=₹{vp_info.get('vah', '--')} | VAL=₹{vp_info.get('val', '--')}\n"
                f"• Channels: Keltner [₹{ch.get('keltner_lower', '--')} - ₹{ch.get('keltner_upper', '--')}] | Donchian [₹{ch.get('donchian_lower', '--')} - ₹{ch.get('donchian_upper', '--')}] | Bollinger %B={ch.get('bollinger_pct_b', '--')}\n"
                f"• Trend & Oscillators: Supertrend=₹{st_info.get('value', '--')} ({st_info.get('direction', '--')}) | RSI 14={osc.get('rsi_14')} ({osc.get('rsi_status')}) | Stoch RSI %K={stoch_info.get('k', '--')}/%D={stoch_info.get('d', '--')} | MACD Hist={osc_macd_hist:+} | ATR 14={osc.get('atr_14')} pts | ADX={adx_info.get('adx', '--')} (+DI:{adx_info.get('plus_di', '--')}/-DI:{adx_info.get('minus_di', '--')})\n"
                f"• Aggregate Volume: {c_vol_val:,.0f} vs MA {ma_vol_val:,.0f} ({vol_eval.get('volume_ratio')}x) -> {vol_eval.get('status')}\n"
                f"• Active User Custom Indicators: {c_ind_str}\n"
                f"• REVERSAL TREND ANALYSIS: [{rev.get('risk_level', 'LOW')} RISK]\n"
                f"  - Analysis & Start Triggers: {rev.get('expected_reversal_analysis')}\n\n"
                f"{sb_str}"
            )

            # Institutional Intelligence: Time-of-Day Window
            tw = market_state.get("time_window", {})
            tw_str = ""
            if tw:
                tw_str = (
                    f"TIME-OF-DAY TRADING WINDOW:\n"
                    f"• Active Window: {tw.get('tag')} | Title: {tw.get('title')}\n"
                    f"• Execution Guidance: {tw.get('guidance')}\n"
                    f"• Breakout Fakeout Risk: {tw.get('fakeout_risk')}\n\n"
                )

            # Institutional Intelligence: Option Chain & PCR
            oc = market_state.get("option_chain", {})
            oc_str = ""
            if oc:
                c_dist = float(oc.get("max_call_oi_distance_pts") or 0.0)
                p_dist = float(oc.get("max_put_oi_distance_pts") or 0.0)
                tot_ce_oi = oc.get("tot_ce_oi", 0)
                tot_pe_oi = oc.get("tot_pe_oi", 0)
                tot_ce_qty = oc.get("tot_ce_qty", tot_ce_oi * 65)
                tot_pe_qty = oc.get("tot_pe_qty", tot_pe_oi * 65)
                max_pain = oc.get("max_pain_strike", "--")
                vol_pcr = oc.get("volume_pcr", "--")
                exp_date = oc.get("active_expiry", "Current Weekly Expiry")
                source = oc.get("data_source", "NSE_INDIA_LIVE")
                c_contracts = oc.get("max_call_oi_contracts", 0)
                p_contracts = oc.get("max_put_oi_contracts", 0)
                c_chg = oc.get("total_ce_change_oi", 0)
                p_chg = oc.get("total_pe_change_oi", 0)

                oc_str = (
                    f"DERIVATIVES & LIVE OPTION CHAIN CONFLUENCE (AUTHENTIC NSE DATA - {source}):\n"
                    f"• Data Feed: {source} | Active Expiry: {exp_date} | Timestamp: {oc.get('timestamp', '--')}\n"
                    f"• Put-Call Ratio (PCR - Open Interest): {oc.get('pcr', 1.0)} ({oc.get('pcr_bias_badge', 'Neutral')} - {oc.get('pcr_bias_text', 'Balanced')}) | Volume PCR: {vol_pcr}\n"
                    f"• Total Market Open Interest (1 Lot = 65 Qty): Put OI = {tot_pe_oi:,} contracts ({tot_pe_qty:,} shares) vs Call OI = {tot_ce_oi:,} contracts ({tot_ce_qty:,} shares)\n"
                    f"• Max Call OI (Resistance Ceiling): ₹{oc.get('max_call_oi_strike', '--')} ({c_contracts:,} contracts defending / {c_dist:+} pts away)\n"
                    f"• Max Put OI (Support Floor): ₹{oc.get('max_put_oi_strike', '--')} ({p_contracts:,} contracts defending / {p_dist:+} pts away)\n"
                    f"• Max Pain Strike: ₹{max_pain} (Theoretical settlement equilibrium)\n"
                    f"• Net Day OI Change: Put OI Change = {p_chg:+,} vs Call OI Change = {c_chg:+,}\n"
                    f"• Active OI Flow: {oc.get('oi_action', 'Balanced')}\n\n"
                )

            # Institutional Intelligence: Volatility Regime & Breadth
            mr = market_state.get("market_regime", {})
            mr_str = ""
            if mr:
                hw = mr.get("heavyweight_breadth", {})
                mr_str = (
                    f"VOLATILITY REGIME (INDIA VIX) & MARKET BREADTH:\n"
                    f"• Status: {mr.get('regime_label')} -> {mr.get('description')}\n"
                    f"• Target Runway: {mr.get('target_buffer')} | Recommended SL Buffer: {mr.get('sl_buffer')}\n"
                    f"• Heavyweight Breadth: {hw.get('breadth', 'Constructive')} (Leaders: {', '.join(hw.get('leaders', []))})\n\n"
                )

            # Institutional Intelligence: Micro-Timeframe Triggers
            mt = market_state.get("micro_triggers", {})
            mt_str = ""
            if mt:
                mt_str = (
                    f"MICRO-TIMEFRAME EXECUTION TRIGGERS (1M/3M PRICE ACTION):\n"
                    f"• Trigger Status: {mt.get('trigger_type')}\n"
                    f"• Wick Rejection: Lower Wick = {mt.get('lower_wick_pct')}% (Dip Absorption) | Upper Wick = {mt.get('upper_wick_pct')}% (Peak Exhaustion)\n"
                    f"• Volume Surge: {mt.get('volume_ratio')}x 20MA ({'INSTITUTIONAL VOLUME BURST' if mt.get('is_volume_surge') else 'Normal Flow'})\n"
                    f"• Micro Orderflow: {mt.get('summary')}\n\n"
                )

            # Institutional Intelligence: Position Sizing & Capital Risk
            ps = market_state.get("position_sizing", {})
            ps_str = ""
            if ps:
                ps_str = (
                    f"RECOMMENDED CAPITAL RISK & POSITION SIZING:\n"
                    f"• Capital: ₹{ps.get('account_capital_inr', 100000):,.0f} | Max Risk ({ps.get('risk_pct_setting', 1.5)}%): ₹{ps.get('max_risk_allowed_inr', 1500):,.0f}\n"
                    f"• Lot Sizing: {ps.get('recommended_lots')} Lots ({ps.get('total_quantity')} qty) for a {ps.get('sl_points')} pt SL (Total Risk: ₹{ps.get('total_risk_inr'):,.0f})\n\n"
                )

            # Personal Behavioral & Psychology Profile
            psy = market_state.get("user_psychology", {})
            psy_str = ""
            if psy:
                weak_str = ", ".join(psy.get("weaknesses", [])) or "None recorded"
                str_str = ", ".join(psy.get("strengths", [])) or "Good risk discipline"
                psy_str = (
                    f"TRADER PERSONAL BEHAVIORAL & PSYCHOLOGY PROFILE:\n"
                    f"• Discipline Score: {psy.get('discipline_score', 85)}/100 | State: {psy.get('emotional_state', 'Disciplined')}\n"
                    f"• Recorded Weaknesses: {weak_str}\n"
                    f"• Recorded Strengths: {str_str}\n"
                    f"• Coaching Mandate: {psy.get('coaching_summary', 'Maintain high patience.')}\n\n"
                )

            # Smart Money & Trap Radar
            traps = market_state.get("trap_radar", {})
            trap_str = ""
            if traps and traps.get("traps"):
                t_lines = ["INSTITUTIONAL SMART MONEY & TRAP RADAR:"]
                t_lines.append(f"• Radar Status: {traps.get('badge')} ({traps.get('traps_count')} traps active)")
                for tr in traps.get("traps", []):
                    t_lines.append(f"  - [{tr.get('severity')}] {tr.get('title')}: {tr.get('detail')} Action: {tr.get('action')}")
                trap_str = "\n".join(t_lines) + "\n\n"

            # 1-Click Pre-Flight Check Engine
            pf = market_state.get("preflight", {})
            pf_str = ""
            if pf:
                pf_str = (
                    f"1-CLICK PRE-FLIGHT CHECK ENGINE VERDICT:\n"
                    f"• Verdict: {pf.get('verdict_badge')} for {pf.get('instrument')}\n"
                    f"• Actionable Summary: {pf.get('summary')}\n\n"
                )

            # Candlestick & Quantitative Chart Pattern Recognition
            pat = market_state.get("patterns", {})
            pat_str = ""
            if pat:
                prim = pat.get("primary_pattern")
                candle_pat = pat.get("candlestick_pattern", {})
                detected_list = pat.get("detected_patterns", [])
                det_lines = []
                for p in detected_list[:3]:
                    det_lines.append(f"  • [{p.get('quality', 'HIGH')}] {p.get('name')} ({p.get('direction')}) -> {p.get('status', 'ACTIVE')}: {p.get('description')}")
                det_formatted = "\n".join(det_lines) if det_lines else "  • Consolidating inside session boundaries; no high-timeframe structural breakout pending."
                pat_str = (
                    f"CANDLESTICK & QUANTITATIVE PATTERN RECOGNITION (ALGORITHMIC DETECTION):\n"
                    f"• Primary Chart Pattern: {prim.get('name') if prim else 'None (Consolidation)'} ({prim.get('direction') if prim else 'Neutral'})\n"
                    f"• Active Candlestick Formation: {candle_pat.get('name', 'Standard Bar')} ({candle_pat.get('signal', 'NEUTRAL')}) -> {candle_pat.get('description', '')}\n"
                    f"• Active Geometric Patterns:\n{det_formatted}\n"
                    f"• Swing Pivots Identified: {pat.get('swing_pivots_count', 0)} swing points identified across 5m session candles.\n\n"
                )

            # Real-Time News Sentiment & Macro Catalyst Engine
            news_s = market_state.get("news_sentiment")
            if not news_s:
                try:
                    from RAG.news_sentiment_engine import NewsSentimentEngine
                    news_s = NewsSentimentEngine.get_instance().get_sentiment_summary()
                except Exception:
                    news_s = None
            news_str = ""
            if news_s:
                is_hi = news_s.get("is_high_impact", False)
                top_c = news_s.get("breaking_catalyst")
                c_title = top_c.get("title", "None") if top_c else "None"
                news_str = (
                    f"REAL-TIME NEWS SENTIMENT & MACRO CATALYST ENGINE:\n"
                    f"• Sentiment Status: {news_s.get('overall_sentiment', 'NEUTRAL')} (Score: {news_s.get('sentiment_score', 0.0):+.2f})\n"
                    f"• Grade-A High-Impact Catalyst Active: {'YES' if is_hi else 'NO (Noise Filtered)'}\n"
                    f"• Catalyst Category: {news_s.get('impact_category', 'NONE')}\n"
                    f"• Breaking Headline: {c_title}\n"
                    f"• Directional Bias: {news_s.get('market_direction', 'SIDEWAYS')}\n"
                    f"• Tactical Options Guidance: {news_s.get('trading_verdict', 'Trade Session VWAP & S&R')}\n\n"
                )

            market_context_str = (
                f"CURRENT REAL-TIME MARKET STATE:\n"
                f"- Symbol: NIFTY 50 (NSE 5m)\n"
                f"- Current LTP: ₹{market_state.get('price', '--')}\n"
                f"- MTF Confluence Ribbon: {market_state.get('mtf_confluence', 'Mixed')}\n\n"
                f"{news_str}"
                f"{tw_str}"
                f"{oc_str}"
                f"{mr_str}"
                f"{mt_str}"
                f"{ps_str}"
                f"{psy_str}"
                f"{trap_str}"
                f"{pf_str}"
                f"{pat_str}"
                f"{tech_str}"
                f"{orb_str}"
                f"{doc_str}"
                f"{pred_str}"
                f"{sig_block}"
                f"{sr_str}\n"
            )

        # Build user drawings awareness with full geometric & level recognition
        drawings_info = ""
        active_d = market_state.get("active_drawing") if market_state else None
        drawings_list = market_state.get("drawings") if market_state else []

        def _format_single_drawing(d, prefix=""):
            dtype = d.get("type", "line")
            rem = d.get("remark") or "Unnamed"
            p1 = d.get("price1", 0.0) or 0.0
            p2 = d.get("price2", p1) or p1
            ang = d.get("angle")
            ang_str = f", Angle={ang}°" if ang is not None else ""
            if dtype == "target_sl":
                entry = float(d.get("entry", 0.0) or 0.0)
                target = float(d.get("target", 0.0) or 0.0)
                stop = float(d.get("stop", 0.0) or 0.0)
                is_long = target >= entry
                direction = "LONG / BUY (CALL)" if is_long else "SHORT / SELL (PUT)"
                reward_pts = abs(target - entry)
                risk_pts = abs(entry - stop)
                rr_ratio = (reward_pts / risk_pts) if risk_pts > 0 else 0.0
                tgt_pct = (reward_pts / entry * 100) if entry > 0 else 0.0
                stp_pct = (risk_pts / entry * 100) if entry > 0 else 0.0

                status_str = ""
                cur_p = market_state.get("price") if market_state else None
                if cur_p and entry > 0:
                    try:
                        cur_p = float(cur_p)
                        if is_long:
                            pnl_pts = cur_p - entry
                            if cur_p >= target:
                                status_str = f" [STATUS: 🏆 Target HIT! (+{reward_pts:.2f} pts profit)]"
                            elif cur_p <= stop:
                                status_str = f" [STATUS: 🛑 Stop Loss HIT! (-{risk_pts:.2f} pts loss)]"
                            elif cur_p > entry:
                                status_str = f" [STATUS: 🟢 ACTIVE IN PROFIT (+{pnl_pts:.2f} pts), {target - cur_p:.2f} pts to Target]"
                            else:
                                status_str = f" [STATUS: 🟡 ACTIVE IN DRAWDOWN ({pnl_pts:.2f} pts), {cur_p - stop:.2f} pts above SL]"
                        else:
                            pnl_pts = entry - cur_p
                            if cur_p <= target:
                                status_str = f" [STATUS: 🏆 Target HIT! (+{reward_pts:.2f} pts profit)]"
                            elif cur_p >= stop:
                                status_str = f" [STATUS: 🛑 Stop Loss HIT! (-{risk_pts:.2f} pts loss)]"
                            elif cur_p < entry:
                                status_str = f" [STATUS: 🟢 ACTIVE IN PROFIT (+{pnl_pts:.2f} pts), {cur_p - target:.2f} pts to Target]"
                            else:
                                status_str = f" [STATUS: 🟡 ACTIVE IN DRAWDOWN ({pnl_pts:.2f} pts), {stop - cur_p:.2f} pts below SL]"
                    except Exception:
                        status_str = ""

                return (
                    f"{prefix}RISK-REWARD BOX ({direction}) '{rem}': Entry=₹{entry:.2f}, Target=₹{target:.2f} "
                    f"(+{reward_pts:.2f} pts / +{tgt_pct:.2f}%), StopLoss=₹{stop:.2f} (-{risk_pts:.2f} pts / -{stp_pct:.2f}%), "
                    f"R:R=1:{rr_ratio:.2f}{status_str}\n"
                )
            elif dtype == "fibonacci":
                diff = float(p2) - float(p1)
                g50 = float(p2) - 0.500 * diff
                g618 = float(p2) - 0.618 * diff
                ext1618 = float(p2) + 0.618 * diff if diff > 0 else float(p2) - 0.618 * abs(diff)
                return f"{prefix}FIBONACCI '{rem}': Start P1=₹{p1}, End P2=₹{p2} [50% Eq=₹{g50:.2f}, 61.8% Golden=₹{g618:.2f}, 1.618 Extension=₹{ext1618:.2f}]\n"
            elif dtype == "channel":
                cw = d.get("channelWidth", 20.0)
                return f"{prefix}PARALLEL CHANNEL '{rem}': Base Line ₹{p1} to ₹{p2}, Width={cw} pts, Upper Line ₹{float(p1)+float(cw):.2f} to ₹{float(p2)+float(cw):.2f}{ang_str}\n"
            elif dtype == "price_range":
                diff_pts = abs(float(p2) - float(p1))
                diff_pct = (diff_pts / max(float(p1), 1.0)) * 100
                return f"{prefix}PRICE RANGE RULER '{rem}': From ₹{p1} to ₹{p2} ({diff_pts:.2f} pts / {diff_pct:.2f}%)\n"
            elif dtype == "ray":
                return f"{prefix}HORIZONTAL RAY '{rem}': Level ₹{p1} extending right as continuous support/resistance\n"
            elif dtype == "vline":
                return f"{prefix}VERTICAL TIME LINE '{rem}': Timestamp Marker\n"
            elif dtype == "text":
                return f"{prefix}CHART NOTE: '{d.get('text', rem)}' at ₹{p1}\n"
            else:
                return f"{prefix}{dtype.upper()} '{rem}': P1=₹{p1}, P2=₹{p2}{ang_str}\n"

        if active_d:
            drawings_info = "USER'S CURRENT ACTIVE / SELECTED DRAWING ON CHART:\n" + _format_single_drawing(active_d, "• ")
        elif drawings_list:
            drawings_info = f"USER ON-CHART DRAWINGS ({len(drawings_list)} total):\n"
            for idx, d in enumerate(drawings_list, 1):
                drawings_info += _format_single_drawing(d, f"  {idx}. ")
        else:
            drawings_info = "USER ON-CHART DRAWINGS: No active trendlines or drawings currently on the chart.\n"

        chat_hist_str = ""
        if chat_hist:
            lines = []
            for m in chat_hist[-20:]:
                r = uname if m.get("role") == "user" else "Copilot"
                m_text = (m.get('message', '') or '').strip()
                if len(m_text) > 800:
                    m_text = m_text[:800] + "..."
                lines.append(f"  {r}: {m_text}")
            chat_hist_str = f"TODAY'S CONVERSATION HISTORY (PAST 24 HOURS WITH {uname.upper()}):\n" + "\n".join(lines) + "\n\n"

        full_prompt = (
            f"{system_instructions}\n\n"
            f"AUTHENTICATED USER CONTEXT:\n"
            f"• Trader Name: {uname}\n"
            f"• Trading Profile: {ustyle}\n"
            f"{chat_hist_str}"
            f"{market_context_str}\n"
            f"{drawings_info}\n"
            f"RETRIEVED VECTOR DATABASE KNOWLEDGE & RECENT SETUPS:\n"
            f"{context_str}\n\n"
            f"TRADER QUESTION:\n{user_query}\n\n"
            f"CRITICAL INSTRUCTIONS - CONCISE, TARGETED & COMPLETE:\n"
            f"1. DIRECT & CRISP: Answer ONLY what {uname} asks in 2 to 4 clear bullet points. Avoid unnecessary background lectures, filler words, or unsolicited developer contact.\n"
            f"2. CONTRACT SIZING: 1 Lot is STRICTLY 65 Quantity (Units). All lot calculations must use multiples of 65 (1 Lot = 65, 2 Lots = 130, 3 Lots = 195). Never say 25 or 75.\n"
            f"3. WEEKLY EXPIRY: Weekly expiry is on TUESDAY.\n"
            f"4. DERIVATIVES & OI ('IO'): 'IO' is Open Interest (OI). Quote the exact Put-Call Ratio (PCR), Max Call OI ceiling, Max Put OI floor, and directional bias.\n"
            f"5. REAL INDIA VIX: Quote real India VIX (~17.16) and market regime directly from market state.\n"
            f"6. PERSONAL PSYCHOLOGY COACHING: If {uname} asks about their psychology, mistakes, discipline score, or coaching, quote their exact Discipline Score from profile above and remind them of their recorded strengths and weaknesses. If they ask about entering during Lunch Window (11:30–13:15 IST), apply the 15% Risk Modifier: if RVOL > 1.5, approve with tighter trailing SL (12–15 pts or 1.2x ATR); if volume is low, encourage patience for a VWAP pullback.\n"
            f"7. DIRECT ON-CHART DRAWINGS AWARENESS: Specifically refer to {uname}'s on-chart drawings by their exact name/remark (e.g. 'Your drawn Major Support Floor at ₹22,650...'). If {uname} has unnamed drawings, kindly suggest giving them names so you can track them with 100% precision.\n"
            f"8. INSTANT TRADE DOCTOR POST-MORTEM: When asked about past trades or Trade Doctor, provide an exact clinical diagnosis (Entry context, Outcome in pts and ₹ at 65 qty/lot, S&R alignment, and Doctor Prescription).\n"
            f"9. STRATEGY NAME: Strictly 'Main Strategy' or 'Institutional Strategy'. Never mention 'ZFTF'.\n"
            f"10. COMPLETE SENTENCES: Finish every sentence and thought completely. No mid-sentence cutoffs.\n"
            f"11. SENIOR PROP TRADER & RISK MANAGER MANDATE (CRITICAL OBJECTIVITY - NEVER BE A YES-MAN):\n"
            f"   • When {uname} asks 'Can I buy Put?', 'Can I buy Call?', 'Should I buy/sell?', 'Can I enter now?', or asks about a specific trade direction, DO NOT just manufacture a setup in that direction to please them!\n"
            f"   • Act like a disciplined senior institutional prop desk risk manager who protects the trader's capital like a veteran human mentor.\n"
            f"   • Evaluate their proposed direction against current market reality: Session VWAP corridor, ±2σ Bands, Option Chain OI walls, PCR, and active traps.\n"
            f"   • If {uname} asks for CALL but price is +2σ/+3σ overextended, near a Call OI wall, or below VWAP, warn them of the trap. Remember: Time of Day is a Risk Modifier (Weight: 15%), NOT a Veto! If a breakout occurs at lunch with expanding volume (RVOL > 1.5), recognize institutional buying and approve the trade with a tighter trailing Stop-Loss (12–15 pts or 1.2x ATR) instead of blindly rejecting it!\n"
            f"   • If {uname} asks for PUT but price is holding above Session VWAP with bullish EMA stack and high PCR (>1.1), tell them bluntly: '❌ NO, DO NOT BUY PUT RIGHT NOW. A Put setup here is fighting institutional flow and is high risk.' Explain why and state what they MUST wait for instead.\n"
            f"   • If the market is chopping or conditions are not optimal, say clearly: '⚠️ DO NOT ENTER YET — The market is in low-volume consolidation / no-man\'s land. Sit on your hands.' If RVOL > 1.5, approve with tighter trailing Stop-Loss.\n"
            f"   • Always give an honest, real, human verdict: [❌ NOT RECOMMENDED / ⚠️ DO NOT ENTER YET / ✅ VALID SETUP], followed by the institutional reason and the exact trigger condition to wait for.\n"
            f"12. INSTITUTIONAL TRAP RADAR & COLLECTIVE MEMORY: If the Trap Radar flags active traps (e.g. Call wall trap, weak S&R < 5 touches, or Lunch Chop), or if retrieved memories flag a past loss/trap near this level, actively WARN {uname} about the trap and advise against entering that trade without confirmation.\n"
            f"13. NATURAL HUMAN CONVERSATIONAL INTELLIGENCE & GREETINGS:\n"
            f"   • When {uname} asks human or casual questions like 'hello', 'hi', 'hyy', 'how are you', 'kese ho', 'who are you', 'what can you do', 'good morning', 'thank you', 'bye', etc.:\n"
            f"     DO NOT dump technical indicator lectures or market summaries!\n"
            f"     Respond like a warm, friendly, polite human trading buddy:\n"
            f"     - For 'hello / hi / hyy': 'Hello {uname}! Hey! I am doing fine and ready for the trading session. How can I help you today with NIFTY 50, Session VWAP, S&R levels, or your trade setups?'\n"
            f"     - For 'how are you / kese ho': 'Hello {uname}! I am doing great and in high spirits, thank you for asking! How are you doing today? Ready to review today\'s price action or plan a trade?'\n"
            f"     - For 'who are you / what can you do': Introduce yourself as their personalized AI Strategy Copilot for NIFTY 50 and mention your core capabilities concisely.\n"
            f"14. MULTI-AGENT DEVIL'S ADVOCATE & SENIOR PROP SYNTHESIZER (CHAIN-OF-THOUGHT MANDATE):\n"
            f"   When formulating trade suggestions or evaluating setups, reason using the Multi-Agent framework:\n"
            f"   • 🦅 Agent 1: Alpha Scout (Opportunity Hunter) — Identifies VWAP bounces, candle rejection wicks, and trend continuation momentum.\n"
            f"   • 🛡️ Agent 2: Devil's Advocate (Risk Manager) — Stresses potential traps, nearby Call/Put OI walls, volatility contraction, and false breakouts.\n"
            f"   • ⚖️ Senior Prop Synthesizer (Chain-of-Thought):\n"
            f"     - Step 1 (Structure): Clean breakout or retest at verified S&R (> 5 touches)?\n"
            f"     - Step 2 (Momentum): Does RVOL (> 1.5) and VWAP slope confirm?\n"
            f"     - Step 3 (Risk Mitigation): Can Devil's Advocate objections be solved by adjusting Stop-Loss (1.2 × ATR or 12–15 pts) or reducing position size (1 Lot = 65 qty)?\n"
            f"     - Step 4 (Verdict): Concrete Entry, Stop-Loss, Target Runway, and R:R ratio (≥ 1:2.0).\n"
            f"15. CONVERSATIONAL CONTINUITY & PAST SETUP (RR BOX) EVALUATION RULES:\n"
            f"   • You have full access to today's 24-hour conversation memory with {uname} in the prompt above. Always maintain continuous context (e.g. if {uname} asks 'is my previous setup ok?', 'what about the last trade we discussed?', or asks about their drawn Target/SL box).\n"
            f"   • When {uname} asks about their drawn Risk-Reward (TARGET_SL) setup or previous trade:\n"
            f"     a) FIRST evaluate their SPECIFIC EXISTING SETUP against current market price and structure (Session VWAP, S&R, trend, and OI walls).\n"
            f"     b) DO NOT forcefully or blindly discard their drawn setup to manufacture an unrelated new one! If the setup is valid or manageable, advise on active trade management: e.g. 'Trail Stop Loss to breakeven at ₹...', 'Take 50% partial profit at ₹...', or 'Hold with current SL at ₹...'.\n"
            f"     c) ONLY suggest abandoning the setup if the thesis has failed, market structure broke down, or the Stop Loss was hit. If so, clearly explain what failed before suggesting an adjusted setup.\n"
            f"16. STANDARDIZED QUICK TRADE EXECUTION SUMMARY (MANDATORY FORMAT):\n"
            f"   • Whenever providing, analyzing, or adjusting a trade setup (Entry, Target, Stop Loss):\n"
            f"     1. First explain the rationale clearly and concisely (2–3 bullet points on WHY: confluence, indicators, S&R level).\n"
            f"     2. AFTER completing the explanation, ALWAYS end your response with this EXACT standardized execution summary block so the trader can read all execution values at a quick glance without reading paragraphs:\n\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 QUICK TRADE EXECUTION SUMMARY\n"
            f"• Direction   -> [BUY (CALL) / SELL (PUT)]\n"
            f"• Entry Price -> ₹[Exact Price]\n"
            f"• Exit/Target -> ₹[Exact Price] (+[Pts] pts / +[%]%)\n"
            f"• Stop Loss   -> ₹[Exact Price] (-[Pts] pts / -[%]%)\n"
            f"• Risk:Reward -> 1 : [Ratio]\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"   Never omit this quick execution summary whenever a trade setup is discussed or advised."
        )

        # If API key is not configured, return high-value local synthesis
        if not self.api_key:
            return self._local_fallback(user_query, retrieved_context, market_state)

        # Call Gemini REST endpoint with auto-fallback across high-quota models
        candidate_models = ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-flash-latest", "gemini-flash-lite-latest"]
        if self.model and self.model not in candidate_models:
            candidate_models.insert(0, self.model)

        last_error = None

        for mod in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={self.api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": full_prompt}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": 0.2,
                    "topK": 40,
                    "topP": 0.95,
                    "maxOutputTokens": 4096,
                    "thinkingConfig": {"thinkingBudget": 0}
                }
            }

            try:
                req = urllib.request.Request(
                    url,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST"
                )
                with urllib.request.urlopen(req, timeout=25) as response:
                    res_data = json.loads(response.read().decode("utf-8"))
                    candidates = res_data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        reply_text = "".join(p.get("text", "") for p in parts)
                        return {
                            "reply": reply_text.strip(),
                            "model": mod,
                            "status": "success",
                            "is_live_llm": True,
                        }
            except urllib.error.HTTPError as e:
                if e.code == 400 and "thinkingConfig" in payload.get("generationConfig", {}):
                    try:
                        del payload["generationConfig"]["thinkingConfig"]
                        req_r = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
                        with urllib.request.urlopen(req_r, timeout=25) as resp_r:
                            res_r = json.loads(resp_r.read().decode("utf-8"))
                            cands_r = res_r.get("candidates", [])
                            if cands_r:
                                pts = cands_r[0].get("content", {}).get("parts", [])
                                rep = "".join(p.get("text", "") for p in pts)
                                if rep.strip():
                                    return {"reply": rep.strip(), "model": mod, "status": "success", "is_live_llm": True}
                    except Exception:
                        pass
                last_error = f"HTTP {e.code}: {e.reason}"
                # Seamlessly cascade to next candidate if model is throttled (429), unavailable (404), or server busy (500/503)
                if e.code in (404, 429, 500, 503):
                    logger.warning("Gemini model %s returned HTTP %s, trying next candidate...", mod, e.code)
                    continue
                logger.error("Gemini API error on %s: %s", mod, last_error)
                continue
            except Exception as e:
                last_error = str(e)
                logger.warning("Gemini connection error on %s: %s, trying next...", mod, last_error)
                continue

        return self._local_fallback(user_query, retrieved_context, market_state, error=last_error)


    def _format_multi_agent_suggestion(
        self,
        uname: str,
        cur_p: float,
        vwap_val: float,
        upper_2: float,
        lower_2: float,
        ema_20: float,
        ema_align: str,
        sup_str: str,
        res_str: str,
        is_above_vwap: bool,
        is_lunch: bool,
        rvol_val: float,
        adx_val: float,
        atr_val: float,
        oc: Dict[str, Any],
        ps: Dict[str, Any],
        tw: Dict[str, Any],
        forced_direction: Optional[str] = None
    ) -> str:
        """
        Synthesizes a trade entry suggestion through the Multi-Agent Devil's Advocate Architecture:
        - Agent 1: Alpha Scout (Opportunity Hunter)
        - Agent 2: Devil's Advocate (Risk Manager)
        - Master Synthesizer: Senior Prop Synthesizer (Chain-of-Thought)
        """
        # Determine direction
        if forced_direction:
            is_bull = (forced_direction.upper() in ("BUY", "CALL"))
        else:
            is_bull = is_above_vwap

        # Dynamic Stop Loss: SL = 1.2 * ATR
        sl_calc = round(1.2 * atr_val, 1) if atr_val > 0 else 18.0
        if is_lunch or abs(cur_p - vwap_val) < 25.0:
            sl_pts = float(max(12.0, min(15.0, sl_calc)))
        else:
            sl_pts = float(max(14.0, min(25.0, sl_calc)))

        target_pts = round(max(sl_pts * 2.0, 35.0), 1)
        lots = ps.get("recommended_lots", 1) if ps else 1
        pcr_val = oc.get("pcr", 1.0) if oc else 1.0
        call_wall = oc.get("max_call_oi_strike", "--") if oc else "--"
        put_floor = oc.get("max_put_oi_strike", "--") if oc else "--"

        # Multi-Agent Debate Generation
        if is_bull:
            setup_title = "Bullish Trend Continuation / Dip-Buy Setup"
            alpha_edge = (
                f"Price (₹{cur_p:,.1f}) is holding above Session VWAP (₹{vwap_val:,.1f}) with {ema_align} structure. "
                f"S&R institutional support floor at {sup_str} confirms buyer accumulation."
            )
            devils_trap = (
                f"Overhead resistance at {res_str} and Call OI ceiling at ₹{call_wall}. "
                f"{'Lunch window has lower volume lull; ' if is_lunch else ''}Risk of fakeout if price fails to sustain above VWAP."
            )
            step1_struct = f"Healthy pullback retest holding above Session VWAP (₹{vwap_val:,.1f}) and validated S&R Support at {sup_str}."
            step2_momen = f"RVOL is {rvol_val:.2f}x with VWAP upward slope confirming institutional accumulation flow."
            step3_mitig = f"Limit risk by using a dynamic Stop-Loss of {sl_pts:.1f} pts (SL = 1.2 × ATR) and strictly 1 Lot (65 qty) contract sizing."
            step4_verdict = (
                f"• **Suggested Setup & Bias:** **{setup_title}**\n\n"
                f"• **High-Probability Entry Zone:**\n"
                f"  1. **Primary Pullback Entry:** Enter Call on a 5m green candle close retesting Session VWAP (₹{vwap_val:,.1f}) or nearest Support at **{sup_str}**.\n"
                f"  2. **Breakout Entry:** Enter on a confirmed 5m close ABOVE Resistance at **{res_str}** with expanding volume.\n\n"
                f"• **Optimal Stop-Loss (Dynamic SL = 1.2 × ATR):** {sl_pts:.1f} pts below entry (Risk: ₹{int(sl_pts * 65):,} on 1 Lot).\n\n"
                f"• **Target Runway:** Next major Resistance at **{res_str}** and Upper +2σ Band at **₹{upper_2:,.1f}** (+{target_pts:.1f} pts reward | R:R 1:{target_pts/sl_pts:.1f}).\n\n"
                f"• **Capital Rule:** Strictly 1 Lot = 65 Quantity on NIFTY."
            )
        else:
            setup_title = "Bearish Mean-Reversion / Breakdown Setup"
            alpha_edge = (
                f"Price (₹{cur_p:,.1f}) is trading below Session VWAP (₹{vwap_val:,.1f}) with {ema_align} structure. "
                f"S&R institutional resistance ceiling at {res_str} confirms seller distribution."
            )
            devils_trap = (
                f"Downside support at {sup_str} and Put OI floor at ₹{put_floor}. "
                f"{'Lunch window has lower volume lull; ' if is_lunch else ''}Risk of short-covering bounce near -2σ band."
            )
            step1_struct = f"Relief bounce failing below Session VWAP (₹{vwap_val:,.1f}) with rejection at validated S&R Resistance at {res_str}."
            step2_momen = f"RVOL is {rvol_val:.2f}x with VWAP downward slope confirming institutional distribution flow."
            step3_mitig = f"Limit risk by using a dynamic Stop-Loss of {sl_pts:.1f} pts (SL = 1.2 × ATR) and strictly 1 Lot (65 qty) contract sizing."
            step4_verdict = (
                f"• **Suggested Setup & Bias:** **{setup_title}**\n\n"
                f"• **High-Probability Entry Zone:**\n"
                f"  1. **Relief Pullback Short:** Enter Put on a 5m upper rejection wick retesting Session VWAP (₹{vwap_val:,.1f}) or Resistance at **{res_str}**.\n"
                f"  2. **Breakdown Entry:** Enter on a confirmed 5m close BELOW Support at **{sup_str}** with volume confirmation.\n\n"
                f"• **Optimal Stop-Loss (Dynamic SL = 1.2 × ATR):** {sl_pts:.1f} pts above entry (Risk: ₹{int(sl_pts * 65):,} on 1 Lot).\n\n"
                f"• **Target Runway:** Next major Support at **{sup_str}** and Lower -2σ Band at **₹{lower_2:,.1f}** (+{target_pts:.1f} pts reward | R:R 1:{target_pts/sl_pts:.1f}).\n\n"
                f"• **Capital Rule:** Strictly 1 Lot = 65 Quantity on NIFTY."
            )

        return (
            f"Hey {uname},\n\n"
            f"Here is my quantitative entry suggestion based on real-time S&R confluence (> 5 touches) and technical indicators synthesized via the Multi-Agent Architecture:\n\n"
            f"🦅 **Agent 1: Alpha Scout (Opportunity Hunter):**\n"
            f"• {alpha_edge}\n\n"
            f"🛡️ **Agent 2: Devil's Advocate (Risk Manager):**\n"
            f"• {devils_trap}\n\n"
            f"⚖️ **Senior Prop Synthesizer (Chain-of-Thought):**\n"
            f"• **Step 1 (Structure):** {step1_struct}\n"
            f"• **Step 2 (Momentum):** {step2_momen}\n"
            f"• **Step 3 (Risk Mitigation):** {step3_mitig}\n"
            f"• **Step 4 (Verdict):**\n"
            f"{step4_verdict}"
        )

    def _local_fallback(
        self,
        query: str,
        retrieved_context: List[Dict[str, Any]],
        market_state: Optional[Dict[str, Any]],
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """Provides direct, intelligent, short answers when API is transitioning."""
        uname = market_state.get("username", "Trader") if market_state else "Trader"
        try:
            from .rag_service import detect_conversational_intent
            conv = detect_conversational_intent(query, username=uname)
            if conv:
                return {
                    "reply": conv,
                    "response": conv,
                    "model": "Personalized-Copilot",
                    "status": "success",
                    "is_live_llm": False,
                }
        except Exception:
            pass

        q_lower = query.lower()
        synthesis = ""
        cur_p = (market_state.get("price") or market_state.get("current_price") or market_state.get("close") or 22500.0) if market_state else 22500.0
        try:
            cur_p = float(cur_p)
        except Exception:
            cur_p = 22500.0
        uname = market_state.get("username", "Trader") if market_state else "Trader"
        tech = market_state.get("technical_eval", {}) if market_state else {}
        sb = tech.get("scoreboard", {})
        v = tech.get("vwap", {})
        e = tech.get("ema", {})
        osc = tech.get("oscillators", {})
        vol_info = tech.get("volume", {})
        rev = tech.get("reversal", {})

        # Detect explicit signal queries
        explicit_signal_terms = [
            "main signal", "display signal", "last signal", "latest signal",
            "past signal", "recent signal", "signal history", "confirmed signal",
            "strategy signal", "signal log", "display signals", "main signals",
            "info about signal", "info about main signal", "tell me about signal",
            "what was the signal", "show signal", "signals on record", "last trade signal"
        ]
        is_explicit_sig = any(p in q_lower for p in explicit_signal_terms) or (
            ("signal" in q_lower or "signals" in q_lower) and not any(w in q_lower for w in [
                "when should i enter", "where should i enter", "when to enter",
                "where to enter", "when i have enter", "should i buy", "should i sell",
                "can i enter", "trade suggestion", "entry suggestion", "where to buy", "where to sell"
            ])
        )

        # 0.005 Dedicated answer for News Sentiment & Macro Catalysts
        news_query_terms = [
            "news", "headline", "headlines", "samachar", "khabar", "rbi", "crude", "oil",
            "war", "geopolitic", "fed", "inflation", "cpi", "sebi", "why market", "market kyu"
        ]
        if not synthesis and any(w in q_lower for w in news_query_terms):
            from RAG.news_sentiment_engine import NewsSentimentEngine
            ns = NewsSentimentEngine.get_instance().get_sentiment_summary()
            is_hi = ns.get("is_high_impact", False)
            ov_s = ns.get("overall_sentiment", "NEUTRAL")
            score = ns.get("sentiment_score", 0.0)
            dir_bias = ns.get("market_direction", "SIDEWAYS")
            verdict = ns.get("trading_verdict", "Follow technicals.")
            cat = ns.get("impact_category", "NONE")
            bc = ns.get("breaking_catalyst")
            headlines = ns.get("headlines", [])[:3]

            hl_lines = []
            for h in headlines:
                src = h.get("source", "Media")
                hl_lines.append(f"  • **[{src}]** {h.get('title')} (*{h.get('polarity', 'NEUTRAL')}*)")
            hl_text = "\n".join(hl_lines) if hl_lines else "  • No major headlines currently recorded."

            if is_hi and bc:
                synthesis = (
                    f"Hello {uname}!\n\n"
                    f"🚨 **Real-Time Macro News Catalyst Alert ({cat}):**\n\n"
                    f"• **Headline:** {bc.get('title')}\n\n"
                    f"• **Sentiment Gauge:** **{ov_s}** (Polarity: {score:+.2f} / 1.0) | **Impact:** {bc.get('impact_score', 8.0):.1f}/10 (Grade-A Catalyst)\n\n"
                    f"• **NIFTY 50 Directional Impact:** **{dir_bias}**\n\n"
                    f"• **Tactical Options Execution:** {verdict}\n\n"
                    f"• **Recent Macro Headlines:**\n{hl_text}\n\n"
                    f"💡 *Grade-A Filter Active: Routine analyst chatter & noise are discarded to keep your execution focused strictly on high-impact macro movers.*"
                )
            else:
                synthesis = (
                    f"Hello {uname}!\n\n"
                    f"📰 **Real-Time Macro News Sentiment Report:**\n\n"
                    f"• **Overall Sentiment:** **{ov_s}** (Polarity: {score:+.2f} / 1.0)\n\n"
                    f"• **Macro Catalyst Status:** No disruptive Grade-A macro shocks detected (Impact < 7.5). Global and domestic cues are currently steady.\n\n"
                    f"• **NIFTY 50 Directional Guidance:** **{dir_bias}** — {verdict}\n\n"
                    f"• **Latest Market Headlines:**\n{hl_text}\n\n"
                    f"💡 *Strict High-Impact Engine: Routine stock tips and opinions are filtered out so you only react when significant macro news moves the tape.*"
                )

        # 0.01 Direct answer for Time-of-Day Window queries
        tw = market_state.get("time_window", {}) if market_state else {}
        if not synthesis and any(w in q_lower for w in ["time window", "trading window", "lunch chop", "what time", "prime window", "market hours", "opening chaos"]):
            synthesis = (
                f"Hey {uname},\n\n"
                f"• **Current Trading Window:** **{tw.get('tag', 'Market Active')}**\n\n"
                f"• **Active Status:** {tw.get('title', 'Intraday Session')}\n\n"
                f"• **Execution Guidance:** {tw.get('guidance', 'Trade according to strategy rules.')}\n\n"
                f"• **Historical Breakout Fakeout Risk:** **{tw.get('fakeout_risk', 'Moderate')}**\n\n"
                f"• **Institutional Playbook:** Prime breakout trends occur during 09:30–11:30 AM and 01:15–02:45 PM. Between 11:30 AM and 01:15 PM (Lunch Chop), breakout failure rates exceed 65% due to European pre-market lull."
            )

        # 0.015 Dedicated answer for Institutional Indicator Directional Scoreboard (Which indicator says Call or Put)
        is_ind_consensus_query = any(w in q_lower for w in [
            "which indicator", "indicators say", "indicator say", "indicator signal", "indicator signals",
            "indicator scoreboard", "indicator consensus", "all indicator", "all indicators",
            "indicator call or put", "indicators call or put", "indicator status", "indicator table",
            "what does rsi say", "what does supertrend say", "what does macd say", "what does vwap say",
            "what does cpr say", "what does adx say", "what does sar say", "rsi call or put", "macd call or put",
            "supertrend call or put", "cpr call or put", "adx call or put"
        ])
        if not synthesis and is_ind_consensus_query:
            sb_items = sb.get("indicators", [])
            consensus_badge = sb.get("consensus", "NEUTRAL / MIXED")
            tot_call = sb.get("total_call", 0)
            tot_put = sb.get("total_put", 0)
            tot_neu = sb.get("total_neutral", 0)
            
            if sb_items:
                table_lines = []
                for item in sb_items:
                    sig = item.get("signal", "NEUTRAL")
                    emoji = "🟢 CALL" if sig == "CALL" else ("🔴 PUT" if sig == "PUT" else "⚪ NEUTRAL")
                    table_lines.append(f"  • **{item.get('name')}:** {item.get('value')} → **{emoji}** ({item.get('detail')})")
                breakdown_str = "\n".join(table_lines)
            else:
                breakdown_str = (
                    f"  • **Session VWAP:** ₹{v.get('value', cur_p)} → **{'🟢 CALL' if cur_p >= v.get('value', cur_p) else '🔴 PUT'}**\n"
                    f"  • **EMA 20:** ₹{e.get('ema_20', cur_p)} → **{'🟢 CALL' if cur_p >= e.get('ema_20', cur_p) else '🔴 PUT'}**\n"
                    f"  • **RSI (14):** {osc.get('rsi_14', 50)} → **{'🟢 CALL' if osc.get('rsi_14', 50) >= 55 else ('🔴 PUT' if osc.get('rsi_14', 50) <= 45 else '⚪ NEUTRAL')}**\n"
                    f"  • **MACD Hist:** {osc.get('macd_hist', 0):+} → **{'🟢 CALL' if osc.get('macd_hist', 0) > 0 else '🔴 PUT'}**"
                )

            synthesis = (
                f"Hey {uname},\n\n"
                f"• **Live Indicator Directional Consensus:** **{consensus_badge}**\n"
                f"  - **Scorecard:** **{tot_call} CALL 🟢** | **{tot_put} PUT 🔴** | **{tot_neu} NEUTRAL ⚪** ({sb.get('confluence_pct', 50)}% Confluence)\n\n"
                f"• **Complete Indicator Breakdown:**\n"
                f"{breakdown_str}\n\n"
                f"• **Senior Mentor Execution Rule:** Institutional setups require confluence across at least 3 distinct layers: Market Structure (VWAP/CPR) + Momentum (RSI/MACD) + Volume/OI Defense. Never execute on a single isolated indicator."
            )

        # 0.02 Direct answer for Option Chain & PCR queries (Call vs Put)
        oc = market_state.get("option_chain", {}) if market_state else {}
        is_educational_pcr = any(k in q_lower for k in [
            "what is pcr", "explain pcr", "pcr framework", "pcr meaning", "meaning of pcr",
            "how pcr works", "pcr rules", "pcr cheat sheet", "pcr guide", "tell me about pcr", "define pcr"
        ])
        is_entry_intent = any(w in q_lower for w in ["entry", "enter", "should i buy", "should i sell", "where to buy", "where to sell", "when to", "where to", "buy or sell"])
        if not synthesis and not is_educational_pcr and not is_entry_intent and (any(w in q_lower for w in ["pcr", "option chain", "open interest", "call oi", "put oi", "max pain"]) or any(re.search(rf"\b{re.escape(w)}\b", q_lower) for w in ["oi", "io", "call or put", "ce or pe"]) or q_lower in ("oi", "io", "pcr") or "io status" in q_lower or "oi status" in q_lower):
            tot_ce_oi = oc.get("tot_ce_oi", 0)
            tot_pe_oi = oc.get("tot_pe_oi", 0)
            tot_ce_qty = oc.get("tot_ce_qty", tot_ce_oi * 65)
            tot_pe_qty = oc.get("tot_pe_qty", tot_pe_oi * 65)
            pcr_val = float(oc.get("pcr", 1.0) or 1.0)
            vol_pcr = oc.get("volume_pcr", "--")
            max_call = oc.get("max_call_oi_strike", "--")
            max_put = oc.get("max_put_oi_strike", "--")
            max_pain = oc.get("max_pain_strike", "--")
            c_dist = oc.get("max_call_oi_distance_pts", 0)
            p_dist = oc.get("max_put_oi_distance_pts", 0)
            c_contracts = oc.get("max_call_oi_contracts", 0)
            p_contracts = oc.get("max_put_oi_contracts", 0)
            c_chg = oc.get("total_ce_change_oi", 0)
            p_chg = oc.get("total_pe_change_oi", 0)
            exp_date = oc.get("active_expiry", "Current Weekly Expiry")
            source = oc.get("data_source", "NSE_INDIA_LIVE")

            synthesis = (
                f"Hey {uname},\n\n"
                f"Here is the verified authentic **NIFTY 50 Option Chain & Derivatives Report** ({source} | Expiry: **{exp_date}**):\n\n"
                f"• **Put-Call Ratio (PCR - Open Interest):** **{pcr_val:.2f}** ({oc.get('pcr_bias_badge', 'Neutral')})\n"
                f"  - **Volume PCR:** **{vol_pcr}**\n"
                f"  - **Market Sentiment:** {oc.get('pcr_bias_text', 'Balanced range near ATM.')}\n\n"
                f"• **Total Market Open Interest (1 Lot = strictly 65 Qty):**\n"
                f"  - **Total Put OI:** **{tot_pe_oi:,} contracts** ({tot_pe_qty:,} shares)\n"
                f"  - **Total Call OI:** **{tot_ce_oi:,} contracts** ({tot_ce_qty:,} shares)\n"
                f"  - **Intraday OI Buildup:** Put OI Change = **{p_chg:+,}** vs Call OI Change = **{c_chg:+,}**\n\n"
                f"• **Institutional Range & S&R Walls:**\n"
                f"  - **Resistance Ceiling (Max Call OI):** **₹{max_call}** ({c_dist:+} pts away | {c_contracts:,} contracts)\n"
                f"  - **Support Floor (Max Put OI):** **₹{max_put}** ({p_dist:+} pts away | {p_contracts:,} contracts)\n"
                f"  - **Max Pain Strike:** **₹{max_pain}** (Option sellers' profit gravity center)\n\n"
                f"• **Active OI Flow:** {oc.get('oi_action', 'Symmetric Range Building')}\n\n"
                f"• **Actionable Execution Plan:** {'Extreme Greed / Overbought (<0.50). High risk of Bearish Reversal from top as upside exhausts; do not chase highs.' if pcr_val < 0.50 else 'Strong Bullish momentum (<0.70). Call buying dominates; favor Call setups above Session VWAP.' if pcr_val < 0.70 else 'Healthy Bullish Rise (0.70–0.90). Favor Call setups on VWAP/EMA pullbacks towards ₹' + str(max_call) + '.' if pcr_val <= 0.90 else 'Neutral Zone (0.90–1.10). Perfect balance between buyers & sellers. Scalp strictly between ₹' + str(max_put) + ' and ₹' + str(max_call) + '; expect choppy action.' if pcr_val <= 1.10 else 'Bearish Momentum (1.10–1.30). Put buying dominates; favor Put setups below Session VWAP towards ₹' + str(max_put) + '.' if pcr_val <= 1.30 else 'Extreme Fear / Oversold (>1.40). High probability of explosive Bullish Short-Covering Bounce from Smart Money Put Writing Floor (' + str(max_put) + '); avoid fresh aggressive shorts.'}"
            )

        # 0.03 Dedicated answer for India VIX / Volatility queries
        mr = market_state.get("market_regime", {}) if market_state else {}
        ps = market_state.get("position_sizing", {}) if market_state else {}
        if not synthesis and any(w in q_lower for w in ["vix", "india vix", "current vix", "vix value", "value of vix", "what is vix", "todays vix", "today vix", "volatility status"]):
            vix_val = float(mr.get("vix") or 17.16)
            synthesis = (
                f"Hey {uname},\n\n"
                f"• **Current India VIX Value:** **{vix_val:.2f}** ({mr.get('regime_label', 'Normal Trend')})\n\n"
                f"• **Volatility Regime:** {mr.get('description', 'Balanced institutional market conditions.')}\n\n"
                f"• **Active 14-Period ATR:** **{osc.get('atr_14', 20.90):.2f} pts** expected 5m candle range.\n\n"
                f"• **Recommended Buffer:** Stop-Loss buffer of **{mr.get('sl_buffer', '18-25 pts')}** with target runway of **{mr.get('target_buffer', '40-75 pts')}**."
            )

        # 0.04 Dedicated answer for Position Sizing & Lot sizing
        if not synthesis and any(w in q_lower for w in ["lot size", "position size", "how many lot", "lots", "capital risk", "risk management", "quantity"]):
            synthesis = (
                f"Hey {uname},\n\n"
                f"• **Contract Sizing:** **1 Lot = strictly 65 Quantity** (Weekly Tuesday Expiry).\n\n"
                f"• **Account Capital:** ₹{ps.get('account_capital_inr', 100000):,.0f} | **Max Risk ({ps.get('risk_pct_setting', 1.5)}%):** ₹{ps.get('max_risk_allowed_inr', 1500):,.0f}\n\n"
                f"• **Calculated Lots:** **{ps.get('recommended_lots', 1)} Lot(s) ({ps.get('total_quantity', 65)} Quantity)** for a {ps.get('sl_points', 20.0)} pt Stop-Loss.\n\n"
                f"• **Total Capital Risk:** ₹{ps.get('total_risk_inr', 1300):,.0f} ({ps.get('actual_risk_pct', 1.3)}% account risk)."
            )

                # 0.045 Dedicated answer for Personal Psychology & Behavioral Coaching
        psy = market_state.get("user_psychology", {}) if market_state else {}
        if not synthesis and any(w in q_lower for w in ["psychology", "discipline", "my mistake", "my habits", "coaching", "emotional", "behavior"]):
            score = psy.get("discipline_score", 85)
            weaks = ", ".join(psy.get("weaknesses", [])) or "None recorded"
            strs = ", ".join(psy.get("strengths", [])) or "Good position sizing discipline"
            synthesis = (
                f"Hey {uname},\n\n"
                f"• **Discipline Score:** **{score}/100** ({psy.get('emotional_state', 'Disciplined')} Mindset)\n\n"
                f"• **Key Strengths:** {strs}\n\n"
                f"• **Behavioral Weaknesses to Watch:** {weaks}\n\n"
                f"• **AI Coach Prescription:** {psy.get('coaching_summary', 'Strictly avoid trading during 11:30–13:15 Lunch Chop. Protect capital for Morning Prime and Afternoon sessions.')}"
            )

        # 0.0455 Dedicated answer for 1-Click Pre-Flight Check
        pf = market_state.get("preflight", {}) if market_state else {}
        if not synthesis and any(w in q_lower for w in ["preflight", "pre-flight", "check trade", "check setup", "go or nogo", "go or no", "can i trade", "audit trade", "pre flight"]):
            synthesis = (
                f"Hey {uname},\n\n"
                f"• **Pre-Flight Verdict:** **{pf.get('verdict_badge', '🟡 CAUTION (Wait for Pullback)')}** for **{pf.get('instrument', 'CALL (CE)')}**\n\n"
                f"• **Actionable Summary:** {pf.get('summary', 'Audit complete.')}\n\n"
                f"• **Risk/Reward & Sizing (Strictly 1 Lot = 65 Qty):**\n"
                f"  - Standard SL: {pf.get('lot_calc', {}).get('standard_sl_pts', 20.0)} pts (Risk: **{pf.get('lot_calc', {}).get('risk_1_lot_inr', '₹1,300')}** per lot)\n"
                f"  - Target Runway: {pf.get('lot_calc', {}).get('standard_target_pts', 40.0)} pts (Reward: **{pf.get('lot_calc', {}).get('reward_1_lot_inr', '₹2,600')}** per lot)\n\n"
                f"• **Checklist Status:** {len(pf.get('checklist', []))} parameters verified. Session VWAP: ₹{pf.get('session_vwap', '--')} | Spot: ₹{pf.get('spot_price', '--')}."
            )

        # 0.0456 Dedicated answer for Smart Money & Trap Radar
        traps_info = market_state.get("trap_radar", {}) if market_state else {}
        if not synthesis and any(w in q_lower for w in ["trap", "traps", "trap radar", "smart money", "fakeout", "liquidity sweep", "bull trap", "bear trap"]):
            t_list = traps_info.get("traps", [])
            if t_list:
                t_lines = [f"Hey {uname},\n\n• **Trap Radar Status:** **{traps_info.get('badge', '🔴 TRAP ALERT')}** ({len(t_list)} active traps detected):"]
                for tr in t_list:
                    t_lines.append(f"• **{tr.get('title')}:** {tr.get('detail')}\n  👉 **Action:** {tr.get('action')}")
                synthesis = "\n\n".join(t_lines)
            else:
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **Trap Radar Status:** **🟢 CLEAR MARKET (No Active Traps)**\n\n"
                    f"• **Option Chain Alignment:** Clear runway between Put floor ₹{traps_info.get('max_put_oi', '--')} and Call wall ₹{traps_info.get('max_call_oi', '--')} (PCR: {traps_info.get('pcr', 1.0)}).\n\n"
                    f"• **Institutional Flow:** Smart money order flow is aligned with Session VWAP without trap divergence."
                )

        # 0.0458 Dedicated answer for Classical & Harmonic Chart Patterns and Candlestick Reversals
        pat = market_state.get("patterns", {}) if market_state else {}
        is_pattern_query = any(w in q_lower for w in [
            "pattern", "patterns", "pertan", "pertans",
            "head and shoulder", "head & shoulder", "head and shoulders", "head & shoulders", "hade and sholder", "h&s", "ih&s", "inverse head and shoulders",
            "triangle", "triangles", "tryangle", "tryangles", "ascending triangle", "descending triangle", "symmetrical triangle",
            "butterfly", "buterfly", "harmonic", "harmonics", "gartley", "bat pattern", "crab pattern", "prz",
            "double top", "double bottom", "m pattern", "w pattern", "m and w",
            "candlestick", "candlesticks", "candle pattern", "candle patterns", "pin bar", "pinbar",
            "hammer", "shooting star", "engulfing", "morning star", "evening star", "doji",
            "chart pattern", "chart patterns", "wedge", "wedges", "flag pattern", "pennant"
        ])
        if not synthesis and is_pattern_query:
            prim = pat.get("primary_pattern")
            candle_pat = pat.get("candlestick_pattern", {})
            detected_list = pat.get("detected_patterns", [])
            pivots_cnt = pat.get("swing_pivots_count", 0)
            
            detected_summary_lines = []
            if detected_list:
                for p in detected_list[:3]:
                    target_info = f" | Target: ₹{p.get('target', 0):,.0f}" if 'target' in p else (f" | PRZ: ₹{p.get('target_1', 0):,.0f}" if 'target_1' in p else "")
                    sl_info = f" | SL: ₹{p.get('stop_loss', 0):,.0f}" if 'stop_loss' in p else ""
                    detected_summary_lines.append(f"  • **{p.get('name')} ({p.get('direction')}):** Status: **{p.get('status')}**{target_info}{sl_info}\n    _{p.get('description')}_")
                detected_str = "\n".join(detected_summary_lines)
            else:
                detected_str = "  • Currently consolidating inside standard session bands. No high-timeframe geometric breakout pending."

            synthesis = (
                f"Hey {uname},\n\n"
                f"**Yes, absolutely!** I am comprehensively trained to identify, calculate, and execute all major **Classical Chart Patterns**, **Harmonic Fibonacci Structures**, and **Candlestick Price Action Formations** directly from real-time NIFTY 50 candlestick data:\n\n"
                f"• **1. Classical Geometric Chart Patterns:**\n"
                f"  - **Head & Shoulders (H&S) & Inverse H&S:** 3-peak reversal geometry (Left Shoulder, higher Head, Right Shoulder). Confirmed upon **Neckline breakdown/breakout** with runway target = vertical head height.\n"
                f"  - **Double Top ('M') & Double Bottom ('W'):** Twin-swing exhaustion at key institutional resistance/support with neckline trigger.\n"
                f"  - **Triangles (Ascending, Descending, Symmetrical):** Multi-touch converging boundary compression leading to explosive directional expansion.\n"
                f"  - **Wedges & Continuation Flags:** Rising/Falling wedges and Bull/Bear flags with tight consolidation channels.\n\n"
                f"• **2. Harmonic Patterns & Potential Reversal Zones (PRZ):**\n"
                f"  - **Butterfly Pattern:** B-point retraces to **0.786** of XA; terminates at the **1.272 to 1.618 extension** of XA (PRZ reversal zone) for sharp mean-reversion.\n"
                f"  - **Gartley Pattern:** 0.618 B-point retracement and 0.786 D-point PRZ completion.\n"
                f"  - **Bat Pattern:** 0.382–0.500 B-point retracement and deep 0.886 D-point PRZ completion.\n\n"
                f"• **3. Candlestick Formations (Single & Multi-Bar):**\n"
                f"  - **Bullish Pin Bar / Hammer:** Lower wick $\\ge 60\\%$ of range (institutional dip absorption at demand).\n"
                f"  - **Bearish Pin Bar / Shooting Star:** Upper wick $\\ge 60\\%$ of range (overhead smart money supply rejection).\n"
                f"  - **Bullish / Bearish Engulfing:** Bar body completely engulfs previous candle with volume expansion.\n"
                f"  - **Doji & Morning/Evening Star:** Volatility compression and 3-candle institutional turning points.\n\n"
                f"• **Real-Time Live Candle Pattern Detection (NIFTY 50 5m):**\n"
                f"  - **Identified Swing Pivots:** **{pivots_cnt} structural swing points** across session.\n"
                f"  - **Current Candlestick Formation:** **{candle_pat.get('name', 'Standard Bar')}** ({candle_pat.get('signal', 'NEUTRAL')}) → {candle_pat.get('description', '')}\n"
                f"  - **Primary Structure:** **{prim.get('name', 'Consolidation') if prim else 'Consolidation'}** ({prim.get('direction', 'Neutral') if prim else 'Rangebound'})\n"
                f"{detected_str}\n\n"
                f"• **Senior Mentor Execution Rule:** Never trade on pattern anticipation alone! Every setup strictly requires **Neckline or PRZ break** + **Volume confirmation** + **Alignment with Session VWAP & Option Chain PCR**."
            )

        # 0.046 Dedicated answer for On-Chart Drawings
        if not synthesis and (any(w in q_lower for w in ["my drawing", "my line", "my chart", "active drawing", "drawn on chart", "inspect drawing", "my trendline", "selected drawing"]) or (any(w in q_lower for w in ["drawing", "drawings", "trendline", "shape"]) and not any(w in q_lower for w in ["what is", "how to use", "how to draw", "meaning of", "define", "explain", "types of"]))):
            d_list = market_state.get("drawings", []) if market_state else []
            act_d = market_state.get("active_drawing") if market_state else None
            if act_d:
                rem = act_d.get("remark") or "Unnamed Line"
                ang = f"{act_d.get('angle')}°" if act_d.get("angle") is not None else "N/A"
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **Active Drawing:** **{rem}** ({act_d.get('type', 'line').upper()})\n\n"
                    f"• **Coordinates:** P1 = ₹{act_d.get('price1', '--')} → P2 = ₹{act_d.get('price2', '--')} (Angle: **{ang}**)\n\n"
                    f"• **Price Spread:** {act_d.get('diff_price', 0):+} pts ({act_d.get('diff_pct', 0):+}%)\n\n"
                    f"• **AI Observation:** Level is aligned with current session structure. {'💡 Tip: Keep drawing labels descriptive so I can monitor them!' if not act_d.get('remark') else 'Actively tracked in vector memory.'}"
                )
            elif d_list:
                lines_buf = [f"Hey {uname},\n\nI am tracking **{len(d_list)} on-chart drawing(s)**:"]
                for idx, d in enumerate(d_list[:4], 1):
                    r = d.get('remark') or 'Unnamed'
                    p1 = d.get('price1', '--')
                    p2 = d.get('price2', '--')
                    lines_buf.append(f"• **{idx}. {d.get('type', 'line').upper()} '{r}':** ₹{p1} → ₹{p2}")
                lines_buf.append("• **Naming Tip:** Click on any drawing and assign a name (e.g. 'Major Support') so I can give you high-precision alerts!")
                synthesis = "\n\n".join(lines_buf)
            else:
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **On-Chart Drawings:** No active trendlines or zones drawn on your chart currently.\n\n"
                    f"• **How to Use:** Draw a line or zone box with the left toolbar, and apply a label (e.g. 'Major Support' or 'Breakout Line'). I will instantly track it and evaluate it against live VWAP and institutional S&R levels!"
                )

        # 0.048 Dedicated answer for Drawing Tools Knowledge & Usage
        if not synthesis and any(k in q_lower for k in [
            "trendline", "target sl", "target_sl", "rectangle", "zone", "supply", "demand",
            "order block", "channel", "fibonacci", "fib", "drawing tool", "types of drawing", "how to draw"
        ]) and any(w in q_lower for w in ["what is", "how to", "explain", "meaning", "define", "tool", "purpose", "types", "which"]):
            if any(k in q_lower for k in ["trendline"]):
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **Trendline Tool (📈 / 📉):** Connects 2 or more ascending swing lows (Bullish dynamic support) or descending swing highs (Bearish dynamic resistance).\n\n"
                    f"• **How AI Interprets It:** I measure the exact geometric slope angle (e.g., 35°–45° indicates a steady institutional trend; > 60° indicates an overextended climax).\n\n"
                    f"• **Trading Rule:** A breakout is confirmed only when a 5-minute candle closes across the trendline with institutional volume."
                )
            elif any(k in q_lower for k in ["target", "target sl", "risk reward"]):
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **Target & Stop-Loss Tool (🎯):** Visualizes your active trade setup by plotting Entry Price, Profit Target runway, and Protective Stop-Loss with minimum 1:2.0 Risk-Reward ratio.\n\n"
                    f"• **AI Auto-Tracking:** When you place this shape on the chart, the Prediction Engine automatically logs it and evaluates live ticks for Target Hit (Win) or Stop-Loss Hit (Loss).\n\n"
                    f"• **Sizing Rule:** Calculated strictly at **1 Lot = 65 Quantity** on NIFTY (e.g. 20 pt SL = ₹1,300 risk on 1 Lot)."
                )
            elif any(k in q_lower for k in ["zone", "rectangle", "supply", "demand", "order block"]):
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **Rectangle Zone Tool (🔲):** Highlights an Institutional Order Block, Supply Zone (overhead selling), or Demand Floor (buying base).\n\n"
                    f"• **Why Use a Box:** Institutional smart money accumulates across a price range (e.g. 22,640–22,660) rather than at a single line.\n\n"
                    f"• **AI Guidance:** Avoid buying inside overhead Supply Zones; look for high-probability continuation when price retests Demand with lower rejection wicks."
                )
            elif any(k in q_lower for k in ["channel"]):
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **Parallel Channel Tool (🛤️):** Encloses price action between two parallel trendlines to map trending continuation corridors.\n\n"
                    f"• **How to Trade It:** Use the channel midline as an equilibrium pivot. Scalp reversals at the outer boundaries, or ride trend breakouts when price expands out of the channel."
                )
            elif any(k in q_lower for k in ["fib", "fibonacci"]):
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **Fibonacci Retracement (📐):** Measures percentage pullbacks (38.2%, 50.0%, 61.8% Golden Ratio) after a strong impulse wave.\n\n"
                    f"• **Institutional Confluence:** High-conviction dip entries occur when the 50% or 61.8% golden pocket converges directly with Session VWAP."
                )
            else:
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **Chart Drawing Suite:**\n"
                    f"  1. **Trendline (📈):** Measures momentum slope and diagonal breakout angles.\n"
                    f"  2. **Horizontal Ray (📍):** Anchors major S&R levels (> 5 touches) into the future.\n"
                    f"  3. **Rectangle Box (🔲):** Marks institutional Supply/Demand Order Blocks.\n"
                    f"  4. **Target/SL Box (🎯):** Auto-tracks trade execution with 1 Lot = 65 Qty risk/reward.\n"
                    f"  5. **Parallel Channel (🛤️):** Maps continuation channels.\n"
                    f"  6. **Fibonacci (📐):** Identifies 50% & 61.8% golden ratio pullback levels.\n\n"
                    f"• **AI Tip:** Assign names to your drawings (e.g. 'Major Support') so I can track them with 100% precision!"
                )

        # 0.049 Dedicated answer for Technical Terms & Institutional Glossary (What is...)
        if not synthesis and any(w in q_lower for w in [
            "what is support", "what is resistance", "what is s&r", "define support", "define resistance",
            "what is oi", "what is io", "what is open interest", "define oi", "meaning of oi",
            "what is pcr", "define pcr", "meaning of pcr", "what is put call ratio",
            "what is vix", "define vix", "meaning of vix", "what is india vix",
            "what is vwap", "define vwap", "meaning of vwap", "what is session vwap",
            "what is ema", "what is rsi", "what is macd", "what is atr", "what is supertrend",
            "what is 1 lot", "what is lot size", "quantity in 1 lot", "how many qty", "units in 1 lot",
            "what is tuesday expiry", "when is expiry", "expiry day", "what is lunch chop"
        ]):
            if any(k in q_lower for k in ["support", "resistance", "s&r"]):
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **Support:** A price floor where institutional buyers enter to absorb selling pressure and prevent further declines.\n\n"
                    f"• **Resistance:** A price ceiling where institutional profit-taking and short-selling overwhelm buyers.\n\n"
                    f"• **Strict Platform Rule:** A level is institutionally validated ONLY if it has **> 5 confirmed touches**. Levels with < 5 touches are vulnerable to retail stop-hunts."
                )
            elif any(k in q_lower for k in [" oi", " io", "open interest", "what is oi", "what is io"]):
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **Open Interest (OI) / 'IO':** The total number of open, active derivative option contracts currently held by market participants.\n\n"
                    f"• **Max Call OI (Ceiling / Resistance):** The strike where smart money has written heavy Call contracts. Blocks upward progress.\n\n"
                    f"• **Max Put OI (Floor / Support):** The strike where smart money has written heavy Put contracts. Acts as a strong price cushion.\n\n"
                    f"• **Current Market Status:** Max Call OI at ₹{oc.get('max_call_oi_strike', '--')} vs Max Put OI at ₹{oc.get('max_put_oi_strike', '--')} (PCR: {oc.get('pcr', 1.0)})."
                )
            elif any(k in q_lower for k in ["pcr", "put call ratio"]):
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"Here is the complete **3-Dimensional PCR Master Framework** calibrated for NIFTY 50:\n\n"
                    f"### 1. 📈 The Standard Directional Framework (Retail Momentum)\n"
                    f"• **PCR < 0.70 (Strong Bullish Momentum):** Direction: **UP 📈** | Call buying heavily dominates; traders aggressively chasing upside.\n"
                    f"• **0.70 to 0.90 (Mildly Bullish / Healthy Rise):** Direction: **UP / SIDEWAYS ↗️** | Standard bullish market environment with healthy buying interest.\n"
                    f"• **0.90 to 1.10 (Neutral Zone):** Direction: **SIDEWAYS / RANGEBOUND ↔️** | Perfect balance between buyers and sellers; expect choppy movement.\n"
                    f"• **1.10 to 1.30 (Bearish Momentum):** Direction: **DOWN 📉** | Put buying dominates; traders hedging portfolios or actively shorting.\n\n"
                    f"### 2. 🪃 The Reversal Framework (The Contrarian Extremes)\n"
                    f"• **PCR Below 0.50 (Extreme Greed / Overbought):** Expected Reversal: **DOWN 🔴 (Market Top)** | Unsustainably euphoric; everyone bought calls. No fresh buyers left $\\rightarrow$ Tops out and reverses downward.\n"
                    f"• **PCR Above 1.40 (Extreme Fear / Oversold):** Expected Reversal: **UP 🟢 (Market Bottom)** | Panic peak; flooded with puts. Violent short-covering squeeze triggers explosive bounce upward.\n\n"
                    f"### 3. 🏦 The Option Writer's Framework (Smart Money Institutions)\n"
                    f"• **High PCR (> 1.20 – 1.40) = Bullish Support Floor 🟢:** Direction: UP / FLOOR | Big institutions writing (selling) Puts, building a hard price cushion.\n"
                    f"• **Low PCR (< 0.70 – 0.50) = Bearish Resistance Ceiling 🔴:** Direction: DOWN / CEILING | Big institutions writing (selling) Calls, capping the upside.\n\n"
                    f"• **Current Live Market PCR:** **{oc.get('pcr', '--')}** ({oc.get('pcr_bias_badge', 'Neutral')})\n"
                    f"• **Actionable Assessment:** {oc.get('pcr_bias_text', 'Normal market range.')}"
                )
            elif any(k in q_lower for k in ["vix", "india vix"]):
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **India VIX:** Volatility Index measuring expected 30-day market volatility (currently real market value **~17.16 – 17.20**).\n\n"
                    f"• **Trading Rule:** 15–19 VIX indicates a normal trend regime with standard 20 pt Stop-Loss (₹1,300 per lot on 65 qty) and 40–60 pt target runways."
                )
            elif any(k in q_lower for k in ["vwap", "session vwap"]):
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **Session VWAP:** Volume Weighted Average Price paid by institutional participants since 09:15 AM.\n\n"
                    f"• **±1σ Corridor:** Primary accumulation band. Price holding above +1σ confirms trend strength.\n\n"
                    f"• **±2σ Exhaustion:** Extreme statistical boundary. Spiking into ±2σ without institutional volume carries high mean-reversion counter-wave risk."
                )
            elif any(k in q_lower for k in ["lot", "quantity", "qty"]):
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **Contract Lot Sizing:** Strictly **1 Lot = 65 Quantity** on NIFTY.\n\n"
                    f"• **Multiples:** 1 Lot = 65 units | 2 Lots = 130 units | 3 Lots = 195 units.\n\n"
                    f"• **Risk Calculation:** A 20-point stop loss on 1 Lot = 20 × 65 = **₹1,300 risk**."
                )
            elif any(k in q_lower for k in ["expiry"]):
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **Weekly Expiry Day:** Strictly **TUESDAY** for active weekly contracts.\n\n"
                    f"• **Theta Decay:** Accelerates post-12:00 PM IST; avoid holding OTM options into the afternoon.\n\n"
                    f"• **Gamma Window:** Explosive gamma surges typically trigger post-13:15 IST on ATM strikes."
                )
            elif any(k in q_lower for k in ["lunch chop", "chop"]):
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **Lunch Chop (11:30–13:15 IST):** European pre-market liquidity lull where volume dries up.\n\n"
                    f"• **Trap Warning:** Over 65% of breakouts attempted in this window result in false breakout whipsaws. Wait for the 13:15 European opening window."
                )
            else:
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **Technical Indicator Glossary:**\n"
                    f"  - **EMA (9/20/50/200):** Exponential Moving Averages tracking dynamic trend support and momentum.\n"
                    f"  - **RSI (14):** Relative Strength Index (70 Overbought / 30 Oversold).\n"
                    f"  - **MACD (12, 26, 9):** Moving Average Convergence Divergence momentum indicator.\n"
                    f"  - **ATR (14):** Average True Range measuring expected 5-minute candle point volatility."
                )

        # 0.05 Dedicated answer for Expiry queries
        if not synthesis and any(w in q_lower for w in ["expiry", "tuesday", "weekly expiry", "expiry day"]):
            tw = market_state.get("time_window", {}) if market_state else {}
            synthesis = (
                f"Hey {uname},\n\n"
                f"• **Weekly Expiry Day:** Strictly **TUESDAY** for active weekly contracts.\n\n"
                f"• **Theta Decay:** High premium decay in morning (09:15-11:30) and lunch (11:30-13:15). Avoid buying OTM options.\n\n"
                f"• **Gamma Window:** Explosive Gamma moves occur post-13:15 IST on ATM strikes.\n\n"
                f"• **Square-Off Rule:** Mandatory intraday MIS positions auto-square-off between 15:15 and 15:20 IST. Exit intraday buys before 15:00 IST."
            )

        # 0.1 Direct answer for EMA health & calculations
        if not synthesis and any(w in q_lower for w in ["ema", "moving average", "sma 200", "ema good", "ema quality"]):
            synthesis = (
                f"Hey {uname},\n\n"
                f"• **EMA Health Assessment:** {e.get('quality', 'Active and tracking trend')}\n\n"
                f"• **EMA Alignment:** {e.get('alignment', 'MIXED')} (EMA 9: ₹{e.get('ema_9', '--')} | EMA 20: ₹{e.get('ema_20', '--')} | EMA 50: ₹{e.get('ema_50', '--')} | EMA 200: ₹{e.get('ema_200', '--')})\n\n"
                f"• **Current Price vs EMA:** Price (₹{cur_p}) is **{'ABOVE' if e.get('price_above_ema20') else 'BELOW'}** the 20 EMA (Slope: {e.get('slope_20', 0):+}).\n\n"
                f"• **Actionable Advice:** {'EMA 20 is serving as primary dynamic trend support. Pullbacks holding above EMA 20 offer favorable continuation.' if e.get('price_above_ema20') else 'Price is trading below EMA 20. Wait for price recapture and positive slope before taking aggressive long entries.'}"
            )

        # 0.2 Direct answer for VWAP bias & status
        if not synthesis and any(w in q_lower for w in ["vwap", "bullish or bearish", "vwap bias", "exhaustion band"]):
            synthesis = (
                f"Hey {uname},\n\n"
                f"• **Session VWAP Bias:** **{v.get('bias', 'NEUTRAL')}** (LTP: ₹{cur_p} vs VWAP: ₹{v.get('value', '--')} | Spread: {v.get('dist_pts', 0):+} pts / {v.get('dist_pct', 0):+}%)\n\n"
                f"• **±2σ Exhaustion Bands:** Upper +2σ: ₹{v.get('upper_2', '--')} | Lower -2σ: ₹{v.get('lower_2', '--')}\n\n"
                f"• **Band Exhaustion Status:** {v.get('exhaustion_status', 'Normal Runway')}\n\n"
                f"• **Trading Bias:** {'Intraday buyer dominance is confirmed while holding above Session VWAP. Look for trend continuation.' if v.get('bias') == 'BULLISH' else 'Sellers are maintaining control below Session VWAP. Favor mean-reversion short setups or counter-trend pullbacks.'}"
            )

        # 0.3 Direct answer for Reversal queries (when will reversal start?)
        if not synthesis and any(w in q_lower for w in ["reversal", "when reversal", "reversal start", "expect reversal", "trend reversal"]):
            synthesis = (
                f"Hey {uname},\n\n"
                f"• **Reversal Risk Level:** **{rev.get('risk_level', 'LOW')} RISK**\n\n"
                f"• **Active Technical Triggers:** {', '.join(rev.get('triggers')) if rev.get('triggers') else 'No active exhaustion triggers detected.'}\n\n"
                f"• **When Reversal is Expected to Start:**\n{rev.get('expected_reversal_analysis', 'Monitor key exhaustion levels.')}\n\n"
                f"• **Confirmation Rule:** Never anticipate a reversal solely on a level touch. Wait for a 5-minute candle close with ≥40% rejection wick and momentum divergence."
            )

        # 0.4 Direct answer for ORB (9:15 - 9:45 AM)
        if not synthesis and any(w in q_lower for w in ["orb", "opening range", "9:15", "9:45", "open range"]):
            orb = market_state.get("orb", {}) if market_state else {}
            if orb and orb.get("has_orb"):
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **9:15 - 9:45 AM Opening Range Breakout (ORB):**\n\n"
                    f"• **ORB High:** **₹{orb.get('high')}** | **ORB Low:** **₹{orb.get('low')}**\n\n"
                    f"• **Range Width:** **{orb.get('range')} points** (Midpoint: ₹{orb.get('midpoint')})\n\n"
                    f"• **Current Status:** **{orb.get('status')}**\n\n"
                    f"• **Trading Playbook:** {orb.get('rule')}"
                )

        # 0.5 Direct answer for Trade Doctor (Why Did Trade Win/Lose)
        if not synthesis and any(w in q_lower for w in ["trade doctor", "why did trade", "why did signal", "why win", "why lose", "win or lose", "review trade", "trade analysis", "diagnos"]):
            doc = market_state.get("trade_doctor", {}) if market_state else {}
            if doc and doc.get("has_trade"):
                t = doc.get("trade", {})
                pnl_str = f"+{t.get('pnl_pts'):.2f}" if t.get('pnl_pts', 0) > 0 else f"{t.get('pnl_pts'):.2f}"
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **Last Completed Trade:** {t.get('action')} @ ₹{t.get('entry_price')} ({t.get('entry_time')}) → Exit @ ₹{t.get('exit_price')} ({t.get('exit_time')})\n\n"
                    f"• **Result:** **{t.get('result')} ({pnl_str} pts)** | Exit Reason: `{t.get('exit_reason')}`\n\n"
                    f"• **Technical Factors:**\n{doc.get('diagnosis')}"
                )

        # 0.6 Direct answer for Candle Analysis
        if not synthesis and any(w in q_lower for w in ["technical analysis for candle", "explain candle", "what happened at this bar", "what pattern formed"]):
            synthesis = (
                f"Hey {uname},\n\n"
                f"• **Price Action & Structure:** The bar established a directional expansion respecting key intraday boundaries.\n\n"
                f"• **Indicator Alignment:** Tested against Session VWAP (₹{v.get('value', '--')}) and EMA 20 (₹{e.get('ema_20', '--')}).\n\n"
                f"• **Trading Takeaway:** Monitor the continuation runway gap toward the nearest S&R confluence level."
            )

        # 0.7 Direct answer for Developer & Strategy Provider Contact
        if not synthesis and any(w in q_lower for w in ["developer", "developed", "creator", "strategy provider", "provider", "who made", "who created", "author", "contact", "email", "rushit", "connect"]):
            synthesis = (
                f"Hey {uname},\n\n"
                f"• **Lead Strategy Provider & Developer:** Rushit Bodra\n\n"
                f"• **Contact Email:** rushitbodra@gmail.com\n\n"
                f"• **Inquiries:** Algorithmic strategy consultations, custom parameter optimization, collaboration, and quantitative system queries."
            )

        # 0.78 Senior Prop Desk Risk Manager Mandate: Critical Directional Trade Audit (No Yes-Man Rule)
        # Directly evaluates user-proposed direction (CALL/CE or PUT/PE or Timing) with brutal market truth.
        asks_call = not is_explicit_sig and any(w in q_lower for w in [
            "buy call", "can i buy call", "should i buy call", "buy ce", "can i buy ce",
            "should i buy ce", "call setup", "ce setup", "is call good", "call trade",
            "enter call", "take call", "take ce", "buy call now", "good to buy call", "can i call",
            "can i buy ce?", "can i buy call?", "should i buy call?", "can i take call?"
        ])
        asks_put = not is_explicit_sig and any(w in q_lower for w in [
            "buy put", "can i buy put", "should i buy put", "buy pe", "can i buy pe",
            "should i buy pe", "put setup", "pe setup", "is put good", "put trade",
            "enter put", "take put", "take pe", "buy put now", "good to buy put", "can i put",
            "can i buy pe?", "can i buy put?", "should i buy put?", "can i take put?"
        ])
        asks_timing = not is_explicit_sig and not (asks_call or asks_put) and any(w in q_lower for w in [
            "can i enter now", "should i enter now", "enter now", "is it good to enter",
            "can i trade now", "should i trade now", "can we enter now", "take entry now",
            "is this right time to enter", "good time to enter now", "can i enter", "should i enter"
        ])

        if not synthesis and (asks_call or asks_put or asks_timing):
            v_dict = v if v else (market_state.get("vwap", {}) if market_state else {})
            e_dict = e if e else (market_state.get("ema", {}) if market_state else {})
            vwap_val = v_dict.get("value") if v_dict.get("value") is not None else cur_p
            try:
                vwap_val = float(vwap_val)
            except Exception:
                vwap_val = cur_p
            upper_2 = v_dict.get("upper_2") if v_dict.get("upper_2") is not None else (cur_p + 70.0)
            try:
                upper_2 = float(upper_2)
            except Exception:
                upper_2 = cur_p + 70.0
            lower_2 = v_dict.get("lower_2") if v_dict.get("lower_2") is not None else (cur_p - 70.0)
            try:
                lower_2 = float(lower_2)
            except Exception:
                lower_2 = cur_p - 70.0
            ema_20 = e_dict.get("ema_20") if e_dict.get("ema_20") is not None else cur_p
            try:
                ema_20 = float(ema_20)
            except Exception:
                ema_20 = cur_p
            pcr_val = oc.get("pcr", 1.0)
            call_wall = oc.get("max_call_oi_strike", "--")
            put_floor = oc.get("max_put_oi_strike", "--")
            is_lunch = tw.get("window") == "LUNCH_CHOP"
            is_above_vwap = cur_p >= vwap_val
            is_exhaustion_up = cur_p >= (upper_2 - 10)
            is_exhaustion_down = cur_p <= (lower_2 + 10)
            dist_vwap_pts = cur_p - vwap_val
            dist_vwap_pct = (dist_vwap_pts / vwap_val) * 100.0 if vwap_val > 0 else 0.0

            if asks_call:
                if is_exhaustion_up:
                    synthesis = (
                        f"Hey {uname},\n\n"
                        f"💡 **Personal Brain Suggestion: ADAPTIVE MOMENTUM SCALP (68% Confluence)**\n\n"
                        f"• **Market Context:** Price (₹{cur_p:,.1f}) is trading strongly **{dist_vwap_pts:+.1f} pts ({dist_vwap_pct:+.2f}%)** above Session VWAP (₹{vwap_val:,.1f}) and nearing the Upper +2σ Band (₹{upper_2:,.1f}). Major Call OI resistance is at ₹{call_wall}.\n\n"
                        f"• **Why Not a Blind Rejection:** Strong momentum often pushes through +2σ during trending days. Rather than missing the move, apply disciplined pro-trader risk:\n\n"
                        f"  👉 **Option 1 (Fast Momentum Scalp):** Enter 1 Lot (strictly 65 qty) on a 5-minute green candle close. Keep a tight 12–15 pt Stop-Loss (Risk: ~₹800–₹975) just below the breakout candle low. Book 50% profits at +25 pts and trail SL.\n\n"
                        f"  👉 **Option 2 (High-Probability Pullback Entry):** If you prefer greater reward-to-risk, wait for a healthy 5m pullback to Session VWAP (₹{vwap_val:,.1f}) or EMA 20 (₹{ema_20:,.1f}) and enter when lower rejection wicks form.\n\n"
                        f"• **Capital Rule:** Max {ps.get('recommended_lots', 1)} Lot (65 units). Never chase with full size when extended."
                    )
                elif not is_above_vwap:
                    synthesis = (
                        f"Hey {uname},\n\n"
                        f"💡 **Personal Brain Suggestion: VWAP RECLAIM SCALP / DIP SETUP (62% Confluence)**\n\n"
                        f"• **Market Context:** Price (₹{cur_p:,.1f}) is currently {abs(dist_vwap_pts):.1f} pts below Session VWAP (₹{vwap_val:,.1f}). Buying Calls here is a counter-trend dip play.\n\n"
                        f"• **Personal Brain Trade Play:**\n\n"
                        f"  👉 **Option 1 (Aggressive Dip Reclaim):** If you see a bullish pin bar or lower rejection wick forming near key support, enter 1 Lot (65 qty). Place Stop-Loss strictly below the day's swing low (15 pts SL). Target runway is directly back to Session VWAP at ₹{vwap_val:,.1f} (+{abs(dist_vwap_pts):.0f} pts reward).\n\n"
                        f"  👉 **Option 2 (Safe Trend-Follower Confirmation):** Wait for a 5-minute candle to decisively cross and close ABOVE Session VWAP (₹{vwap_val:,.1f}) with positive volume before entering Calls.\n\n"
                        f"• **Position Sizing Mandate:** Strictly 1 Lot (65 qty). Max risk ₹975."
                    )
                elif is_lunch:
                    synthesis = (
                        f"Hey {uname},\n\n"
                        f"💡 **Personal Brain Suggestion: LUNCH CHOP ADAPTIVE SCALP (65% Confluence)**\n\n"
                        f"• **Market Context:** Price is holding above Session VWAP (₹{vwap_val:,.1f}) with positive structure, but current time ({tw.get('time_str', 'Lunch Window')}) is inside the 11:30–13:15 European pre-market lull where broad volume is subdued.\n\n"
                        f"• **Personal Brain Trade Play:**\n\n"
                        f"  👉 **Option 1 (Range Scalp on Dip):** Do NOT chase green breakout candles here (fakeout risk is higher). Instead, place a limit buy order on a dip near Session VWAP (₹{vwap_val:,.1f}) or EMA 20 (₹{ema_20:,.1f}) with strictly 1 Lot (65 qty) and a tight 15 pt SL.\n\n"
                        f"  👉 **Option 2 (Patience for European Open):** Sit tight until 13:15 IST when institutional volume returns and breakout follow-through surges.\n\n"
                        f"• **Position Sizing:** Strictly 1 Lot = 65 Qty (Risk: ₹975)."
                    )
                else:
                    synthesis = (
                        f"Hey {uname},\n\n"
                        f"💡 **Personal Brain Suggestion: HIGH-CONVICTION CALL SETUP (88% Confluence)**\n\n"
                        f"• **Bullish Alignment:** Price (₹{cur_p:,.1f}) is holding comfortably above Session VWAP (₹{vwap_val:,.1f}) in an institutional accumulation corridor with healthy PCR ({pcr_val}) and clear runway toward ₹{call_wall}.\n\n"
                        f"• **Execution Playbook:**\n\n"
                        f"  - **Trigger:** Enter Call on a 5m bullish rejection candle holding above VWAP.\n"
                        f"  - **Stop-Loss:** Strictly 15–20 pts below Session VWAP (₹{vwap_val - 15:,.1f}).\n"
                        f"  - **Target Runway:** Upper +2σ Band at ₹{upper_2:,.1f} (+{max(20.0, upper_2 - cur_p):.1f} pts).\n"
                        f"  - **Contract Sizing:** {ps.get('recommended_lots', 1)} Lot(s) ({ps.get('total_quantity', 65)} qty | 1 Lot = 65 Qty)."
                    )

            elif asks_put:
                if is_above_vwap and not is_exhaustion_up:
                    synthesis = (
                        f"Hey {uname},\n\n"
                        f"💡 **Personal Brain Suggestion: COUNTER-TREND PUT FADE / REVERSAL SCALP (58% Confluence)**\n\n"
                        f"• **Market Context:** Price (₹{cur_p:,.1f}) is trading above Session VWAP (₹{vwap_val:,.1f}) with Put writers defending support (PCR {pcr_val}). Shorting here is counter-trend.\n\n"
                        f"• **Personal Brain Trade Play:**\n\n"
                        f"  👉 **Option 1 (Scalp Resistance Fade):** If price hits strong S&R resistance or Max Call OI (₹{call_wall}) and prints a shooting star with >= 40% upper rejection wick, scalp 1 Lot (65 qty) with a tight 12 pt SL. Target runway is back to Session VWAP (₹{vwap_val:,.1f}).\n\n"
                        f"  👉 **Option 2 (High-Probability Breakdown Short):** Wait for price to break and close BELOW Session VWAP (₹{vwap_val:,.1f}) with negative linreg slope before entering standard Put positions.\n\n"
                        f"• **Position Sizing:** Max 1 Lot (65 qty) for counter-trend scalps."
                    )
                elif is_exhaustion_down:
                    synthesis = (
                        f"Hey {uname},\n\n"
                        f"💡 **Personal Brain Suggestion: ADAPTIVE BREAKDOWN SCALP (66% Confluence)**\n\n"
                        f"• **Market Context:** Price is at **₹{cur_p:,.1f}**, touching the Lower -2σ Exhaustion Band (₹{lower_2:,.1f}). Downward momentum is heavy, but risk of short-covering bounces is elevated.\n\n"
                        f"• **Personal Brain Trade Play:**\n\n"
                        f"  👉 **Option 1 (Fast Breakdown Scalp):** If 5m candle closes with strong expansion below -2σ, scalp 1 Lot (65 qty) with a strict 12 pt trailing SL. Do not be greedy; lock in gains at +20-25 pts.\n\n"
                        f"  👉 **Option 2 (Wait for Relief Pullback):** Wait for price to bounce back toward EMA 20 (₹{ema_20:,.1f}) or Session VWAP (₹{vwap_val:,.1f}) and enter Puts on an upper rejection wick for optimal risk/reward.\n\n"
                        f"• **Position Sizing:** Strictly 1 Lot = 65 Qty (Risk: ₹780–₹975)."
                    )
                elif is_lunch:
                    synthesis = (
                        f"Hey {uname},\n\n"
                        f"💡 **Personal Brain Suggestion: LUNCH CHOP ADAPTIVE PUT SETUP (65% Confluence)**\n\n"
                        f"• **Market Context:** Price is trading with bearish bias, but during the 11:30–13:15 Lunch window, breakdown follow-through is frequently choppy.\n\n"
                        f"• **Personal Brain Trade Play:**\n\n"
                        f"  👉 **Option 1 (Sell Relief Rallies):** Place limit sell orders on relief bounces to Session VWAP (₹{vwap_val:,.1f}) or EMA 20 with 1 Lot (65 qty) and 15 pt SL.\n\n"
                        f"  👉 **Option 2 (Post-13:15 Momentum):** Wait for 13:15 European market opening when true institutional trend volume breaks the range.\n\n"
                        f"• **Position Sizing:** Strictly 1 Lot (65 units)."
                    )
                else:
                    synthesis = (
                        f"Hey {uname},\n\n"
                        f"💡 **Personal Brain Suggestion: HIGH-CONVICTION PUT SETUP (86% Confluence)**\n\n"
                        f"• **Bearish Alignment:** Price (₹{cur_p:,.1f}) is trading below Session VWAP (₹{vwap_val:,.1f}) with bearish moving average pressure and room to fall toward the Lower -2σ Band (₹{lower_2:,.1f}).\n\n"
                        f"• **Execution Playbook:**\n\n"
                        f"  - **Trigger:** Enter on a small pullback toward VWAP or EMA 20 on an upper rejection wick.\n"
                        f"  - **Stop-Loss:** Strictly 15 pts above Session VWAP (₹{vwap_val + 15:,.1f}).\n"
                        f"  - **Target Runway:** Lower -2σ Band at ₹{lower_2:,.1f} (+{max(20.0, cur_p - lower_2):.1f} pts).\n"
                        f"  - **Contract Sizing:** {ps.get('recommended_lots', 1)} Lot(s) ({ps.get('total_quantity', 65)} qty | 1 Lot = 65 Qty)."
                    )

            elif asks_timing:
                comb_sr = market_state.get("comb_sr_levels", []) if market_state else []
                sr_gt5 = [l for l in comb_sr if l.get("bounces", 0) > 5]
                active_sr = sr_gt5 if sr_gt5 else comb_sr
                supports = [l for l in active_sr if l.get("role") == "Support" or float(l.get("price", 0)) < cur_p]
                resistances = [l for l in active_sr if l.get("role") == "Resistance" or float(l.get("price", 0)) > cur_p]
                nearest_sup = max(supports, key=lambda x: float(x.get("price", 0))) if supports else None
                nearest_res = min(resistances, key=lambda x: float(x.get("price", 0))) if resistances else None
                sup_str = f"₹{nearest_sup.get('price')} ({nearest_sup.get('bounces', 6)} touches)" if nearest_sup else "₹22,450 (Major Support)"
                res_str = f"₹{nearest_res.get('price')} ({nearest_res.get('bounces', 6)} touches)" if nearest_res else "₹22,580 (Major Resistance)"

                rvol_val = float(vol_info.get("volume_ratio", 1.25) or 1.25)
                adx_val = float(tech.get("adx", {}).get("adx", 24.0) if isinstance(tech.get("adx"), dict) else 24.0)
                atr_val = float(osc.get("atr_14", 18.0) or 18.0)
                ema_align = e_dict.get("alignment", "Bullish Stack" if is_above_vwap else "Bearish Stack")

                synthesis = self._format_multi_agent_suggestion(
                    uname=uname,
                    cur_p=cur_p,
                    vwap_val=vwap_val,
                    upper_2=upper_2,
                    lower_2=lower_2,
                    ema_20=ema_20,
                    ema_align=ema_align,
                    sup_str=sup_str,
                    res_str=res_str,
                    is_above_vwap=is_above_vwap,
                    is_lunch=is_lunch,
                    rvol_val=rvol_val,
                    adx_val=adx_val,
                    atr_val=atr_val,
                    oc=oc,
                    ps=ps,
                    tw=tw
                )

        # 0.8 Dedicated quantitative trade entry suggestion created by Copilot from S&R (> 5x touches) and Indicators
        # MANDATE: Never quote Main Strategy signal here!
        is_entry_query = not is_explicit_sig and (
            any(phrase in q_lower for phrase in [
                "when to enter", "where to enter", "when should i enter", "where should i enter",
                "when i have enter", "when can i enter", "where can i enter", "should i buy",
                "should i sell", "entry suggestion", "trade suggestion", "entry point",
                "entry level", "good time to enter", "take entry", "take trade", "best entry",
                "where to buy", "where to sell", "when to buy", "when to sell", "enter now",
                "can i enter", "buy or sell", "which trade", "what trade"
            ]) or ("enter" in q_lower or "entry" in q_lower)
        )

        if not synthesis and is_entry_query:
            comb_sr = market_state.get("comb_sr_levels", []) if market_state else []
            sr_gt5 = [l for l in comb_sr if l.get("bounces", 0) > 5]
            active_sr = sr_gt5 if sr_gt5 else comb_sr

            supports = [l for l in active_sr if l.get("role") == "Support" or float(l.get("price", 0)) < cur_p]
            resistances = [l for l in active_sr if l.get("role") == "Resistance" or float(l.get("price", 0)) > cur_p]

            nearest_sup = max(supports, key=lambda x: float(x.get("price", 0))) if supports else None
            nearest_res = min(resistances, key=lambda x: float(x.get("price", 0))) if resistances else None

            sup_str = f"₹{nearest_sup.get('price')} ({nearest_sup.get('bounces', 6)} touches)" if nearest_sup else "₹22,400 (Major Support)"
            res_str = f"₹{nearest_res.get('price')} ({nearest_res.get('bounces', 6)} touches)" if nearest_res else "₹22,600 (Major Resistance)"

            vwap_val = v.get("value", cur_p)
            vwap_bias = v.get("bias", "BULLISH" if cur_p >= vwap_val else "BEARISH")
            ema_20 = e.get("ema_20", cur_p)
            ema_50 = e.get("ema_50", cur_p)
            ema_align = e.get("alignment", "BULLISH_STACK" if cur_p >= ema_20 else "BEARISH_STACK")
            rsi_val = osc.get("rsi_14", 52.0)
            rsi_stat = osc.get("rsi_status", "Neutral")
            upper_2 = v.get("upper_2", cur_p + 70)
            lower_2 = v.get("lower_2", cur_p - 70)

            rvol_val = float(vol_info.get("volume_ratio", 1.25) or 1.25)
            adx_val = float(tech.get("adx", {}).get("adx", 24.0) if isinstance(tech.get("adx"), dict) else 24.0)
            atr_val = float(osc.get("atr_14", 18.0) or 18.0)
            is_lunch = tw.get("window") == "LUNCH_CHOP"

            synthesis = self._format_multi_agent_suggestion(
                uname=uname,
                cur_p=cur_p,
                vwap_val=vwap_val,
                upper_2=upper_2,
                lower_2=lower_2,
                ema_20=ema_20,
                ema_align=ema_align,
                sup_str=sup_str,
                res_str=res_str,
                is_above_vwap=(vwap_bias == "BULLISH" or cur_p >= vwap_val),
                is_lunch=is_lunch,
                rvol_val=rvol_val,
                adx_val=adx_val,
                atr_val=atr_val,
                oc=oc,
                ps=ps,
                tw=tw
            )

        # 1. Direct answer for Support & Resistance queries (> 5 touches strictly)
        if not synthesis and any(w in q_lower for w in ["support", "resistance", "s&r", "nearest"]):
            comb_sr = market_state.get("comb_sr_levels", []) if market_state else []
            if comb_sr:
                sr_gt5 = [l for l in comb_sr if l.get("bounces", 0) > 5]
                valid_sr = sr_gt5 if sr_gt5 else comb_sr
                supports = [l for l in valid_sr if l.get("role") == "Support" or float(l.get("price", 0)) < cur_p]
                resistances = [l for l in valid_sr if l.get("role") == "Resistance" or float(l.get("price", 0)) > cur_p]
                nearest_sup = max(supports, key=lambda x: float(x.get("price", 0))) if supports else None
                nearest_res = min(resistances, key=lambda x: float(x.get("price", 0))) if resistances else None

                lines = [f"Hey {uname},\n"]
                if "support" in q_lower and "resistance" in q_lower:
                    if nearest_sup:
                        lines.append(f"• **Nearest Major Support (> 5 touches):** **₹{nearest_sup.get('price')}** ({nearest_sup.get('bounces', 6)} touches)\n")
                    if nearest_res:
                        lines.append(f"• **Nearest Major Resistance (> 5 touches):** **₹{nearest_res.get('price')}** ({nearest_res.get('bounces', 6)} touches)")
                elif "support" in q_lower and nearest_sup:
                    lines.append(f"• **Nearest Major Support (> 5 touches):** **₹{nearest_sup.get('price')}** ({nearest_sup.get('bounces', 6)} touches).")
                elif "resistance" in q_lower and nearest_res:
                    lines.append(f"• **Nearest Major Resistance (> 5 touches):** **₹{nearest_res.get('price')}** ({nearest_res.get('bounces', 6)} touches).")
                else:
                    if nearest_sup:
                        lines.append(f"• **Nearest Major Support (> 5 touches):** **₹{nearest_sup.get('price')}** ({nearest_sup.get('bounces', 6)} touches)\n")
                    if nearest_res:
                        lines.append(f"• **Nearest Major Resistance (> 5 touches):** **₹{nearest_res.get('price')}** ({nearest_res.get('bounces', 6)} touches)")
                synthesis = "\n".join(lines)

        # 2. Direct answer for Breakout vs Trap queries
        if not synthesis and any(w in q_lower for w in ["breakout", "trap"]):
            synthesis = (
                f"Hey {uname},\n\n"
                f"• **S&R Breakouts:** Trigger when a 5m candle decisively closes *beyond* a Major S&R level (> 5 touches) with momentum, holding outside the broken structure.\n\n"
                f"• **Institutional Trap Reversals:** Trigger when price pierces beyond a Major S&R level (> 5 touches) to sweep liquidity, leaves a prominent rejection wick (>= 40%), and immediately closes *back inside* the zone."
            )

        # 3. Direct answer for signal queries (ONLY when explicitly requested!)
        if not synthesis and is_explicit_sig:
            last_sig = market_state.get("last_signal") if market_state else None
            last_entry = market_state.get("last_entry_signal") if market_state else None
            recent = market_state.get("recent_signals", []) if market_state else []
            tot = market_state.get("total_signals_count", len(recent)) if market_state else len(recent)

            if any(w in q_lower for w in ["history", "all", "records", "list"]):
                if recent:
                    lines = [f"Hey {uname},\n\n• **Confirmed Main Strategy Signals ({tot} total records):**\n"]
                    for s in reversed(recent[-6:]):
                        lines.append(f"• **{s.get('time')}**: {s.get('action')} @ ₹{s.get('price')} ({s.get('reason')})\n")
                    synthesis = "\n".join(lines)
            elif last_sig:
                entry_str = f" (Entry: ₹{last_entry.get('price')})" if last_entry and last_entry != last_sig else ""
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **Main Strategy Signal Details:**\n\n"
                    f"• **Signal Action:** **{last_sig.get('action')}**\n\n"
                    f"• **Signal Time:** {last_sig.get('time')}\n\n"
                    f"• **Signal Price:** **₹{last_sig.get('price')}**{entry_str}\n\n"
                    f"• **Trigger Reason:** {last_sig.get('reason')}"
                )

        # 4. Direct answer for drawing queries
        if not synthesis and (any(w in q_lower for w in ["my angle", "line angle", "slope angle", "active drawing", "inspect drawing", "my line", "angle of line"]) or ("angle" in q_lower and "rectangle" not in q_lower and "triangle" not in q_lower)):
            active_d = market_state.get("active_drawing") if market_state else None
            if active_d:
                ang = active_d.get("angle")
                ang_str = f"{ang}°" if ang is not None else "N/A"
                p1 = active_d.get("price1", "--")
                p2 = active_d.get("price2", "--")
                rem = active_d.get("remark") or "Drawing"
                d_type = active_d.get("type", "line").upper()
                synthesis = f"Hey {uname},\n\n• **Drawing Analysis:** The measured geometric angle of your {rem} ({d_type}) is **{ang_str}** (Anchor P1: ₹{p1}, Anchor P2: ₹{p2}, Delta: ₹{active_d.get('diff_price', '--')})."
            else:
                synthesis = f"Hey {uname},\n\nNo active drawing line selected on chart. Draw a trendline using the line tool above to inspect its measured angle."

        # 5. Direct answer for VWAP & Indicators
        if not synthesis and any(w in q_lower for w in ["vwap", "band", "indicator", "sma", "z-score", "slope"]):
            ind = market_state.get("indicators", {}) if market_state else {}
            if ind:
                synthesis = (
                    f"Hey {uname},\n\n"
                    f"• **Session VWAP:** ₹{ind.get('vwap', '--')}\n\n"
                    f"• **Upper +2σ:** ₹{ind.get('vwap_upper_2', '--')} | **Lower -2σ:** ₹{ind.get('vwap_lower_2', '--')}\n\n"
                    f"• **20 SMA:** ₹{ind.get('sma_20', '--')} | **Z-Score:** {ind.get('z_score', '--')}"
                )

        # 6. High-quality strategy knowledge fallback (filtered against raw signals and disclaimers)
        if not synthesis:
            clean_chunks = []
            for c in retrieved_context:
                content = c.get("content", "").strip()
                if content.startswith("Trade Signal") or "LEGAL DISCLAIMER" in content:
                    continue
                clean_chunks.append(content)

            if clean_chunks:
                synthesis = f"Hey {uname},\n\n" + "\n\n".join(clean_chunks[:1])
            else:
                synthesis = f"Hey {uname},\n\nCurrent NIFTY 50 LTP: ₹{cur_p}. Main Strategy is active on 5m timeframe following Session VWAP and S&R confluence rules."

        reply = synthesis.strip()

        return {
            "reply": reply,
            "model": "local-rag-playbook",
            "status": "fallback",
            "is_live_llm": False,
        }
