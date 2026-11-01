import unittest
import datetime
import pandas as pd
from RAG.rag_service import RAGService, ConversationMemoryEngine
from RAG.preflight import PreFlightEngine
from RAG.institutional_intelligence import (
    TimeOfDayRiskEngine,
    RVOLCalculator,
    MarketRegimeIntelligence,
    OptionChainIntelligence,
)


class TestRAGAdvancedArchitecture(unittest.TestCase):
    """
    Comprehensive verification for:
    1. Dynamic Time-of-Day Risk Modifier (15% Weight, NOT a binary veto) & Lunch RVOL Override.
    2. The 4 Vital Live Data Feeds (RVOL, ADX/ATR with SL = 1.2 x ATR, MTF Confluence, OI Shift).
    3. Multi-Agent Devil's Advocate Architecture (Alpha Scout, Devil's Advocate, Senior Prop Synthesizer CoT).
    4. Stateful Session Memory (Sliding Window, Contextual Follow-up Query Rewriting, Active Trade Tracking).
    """

    def setUp(self):
        self.service = RAGService.get_instance()
        self.memory = ConversationMemoryEngine.get_instance()

    def test_01_lunch_window_is_risk_modifier_not_veto(self):
        """
        Verify that Time of Day is a Risk Modifier (15% Weight), NOT a Veto.
        If a breakout occurs during lunch (11:30-13:15) with expanding volume (RVOL > 1.5),
        the AI approves the trade with a tight trailing Stop-Loss (12-15 pts) instead of vetoing!
        """
        # TimeOfDayRiskEngine check
        lunch_dt = datetime.datetime(2026, 10, 29, 12, 15)
        tw = TimeOfDayRiskEngine.evaluate_window(lunch_dt)
        self.assertTrue(tw["allow_entries"], "Lunch window must allow entries (adaptive scalp mode)")
        self.assertFalse(tw.get("is_veto", True), "Lunch window must NOT be a veto")
        self.assertEqual(tw.get("risk_modifier_weight"), 0.15, "Lunch window must carry 15% risk weight")

        # PreFlight check during lunch with expanding volume (RVOL > 1.5)
        res_lunch_expansion = PreFlightEngine.evaluate(
            direction="BUY",
            spot_price=22550.0,
            indicators={
                "vwap": 22500.0,
                "atr_14": 15.0,
                "adx": 28.0,
                "volume": {"current_volume": 4000000},
            },
            option_chain={"pcr": 1.15, "max_call_oi_strike": 22700.0, "max_put_oi_strike": 22400.0},
            dt=lunch_dt,
        )

        self.assertIn(res_lunch_expansion["verdict"], ["GO", "ADAPTIVE"])
        # Stop-loss should be tight (12-15 pts) during lunch
        self.assertLessEqual(res_lunch_expansion["lot_calc"]["standard_sl_pts"], 18.0)
        # Verify RVOL override is present in checklist or positive drivers
        checklist_names = [item["name"] for item in res_lunch_expansion["checklist"]]
        self.assertIn("Time-of-Day Risk Modifier (15% Weight)", checklist_names)

        # Check badge shows institutional expansion during lunch
        lunch_item = next(it for it in res_lunch_expansion["checklist"] if it["name"] == "Time-of-Day Risk Modifier (15% Weight)")
        self.assertIn("LUNCH INSTITUTIONAL EXPANSION", lunch_item["badge"])

        # Also test with subdued volume (RVOL <= 1.0) during lunch: should be CAUTION, NOT an outright Veto!
        res_lunch_subdued = PreFlightEngine.evaluate(
            direction="BUY",
            spot_price=22550.0,
            indicators={
                "vwap": 22500.0,
                "atr_14": 15.0,
                "adx": 19.0,
                "volume": {"current_volume": 50000}, # low volume
            },
            option_chain={"pcr": 1.15, "max_call_oi_strike": 22700.0, "max_put_oi_strike": 22400.0},
            dt=lunch_dt,
        )
        self.assertNotEqual(res_lunch_subdued["verdict"], "ABORT", "Subdued lunch should NOT cause a binary ABORT/VETO")

    def test_02_four_vital_live_data_feeds(self):
        """
        Verify the 4 vital live data feeds attached to RAG:
        1. RVOL (Relative Volume Z-Score)
        2. Market Regime (ADX & ATR, SL = 1.2 x ATR)
        3. Multi-Timeframe Trend Confluence (MTF)
        4. Live Option Chain OI Shift (Put/Call Writing)
        """
        # 1. RVOL calculation
        df_mock = pd.DataFrame({
            "timestamp": pd.date_range("2026-10-29 09:15", periods=20, freq="5min"),
            "open": [22500.0] * 20,
            "high": [22520.0] * 20,
            "low": [22490.0] * 20,
            "close": [22510.0] * 20,
            "volume": [100000.0] * 19 + [250000.0], # 2.5x volume surge
        })
        rvol_res = RVOLCalculator.calculate(df_5m=df_mock, current_volume=250000.0)
        self.assertGreaterEqual(rvol_res["rvol_ratio"], 1.5)
        self.assertTrue(rvol_res["is_institutional_expansion"])
        self.assertTrue(rvol_res["smart_money_active"])

        # 2. Market Regime (ADX & ATR with dynamic SL = 1.2 * ATR)
        atr_test = 20.0
        mr_trending = MarketRegimeIntelligence.evaluate(atr_14=atr_test, adx_val=30.0)
        self.assertEqual(mr_trending["adx_regime"], "STRONG_TRENDING")
        self.assertEqual(mr_trending["dynamic_sl_pts"], round(1.2 * atr_test, 1)) # 24.0 pts

        mr_rangebound = MarketRegimeIntelligence.evaluate(atr_14=12.0, adx_val=15.0)
        self.assertEqual(mr_rangebound["adx_regime"], "RANGEBOUND_MEAN_REVERTING")
        self.assertEqual(mr_rangebound["dynamic_sl_pts"], round(1.2 * 12.0, 1)) # 14.4 pts

        # 3. MTF Confluence & Option Chain OI Shift in PreFlight payload
        mtf_mock = {
            "timeframes": {
                "5m": {"trend": "BULLISH"},
                "15m": {"trend": "BULLISH"},
                "1h": {"trend": "BULLISH"},
            },
            "confluence": "Bullish",
        }
        oc_mock = {
            "pcr": 1.20,
            "total_pe_change_oi": 150000,
            "total_ce_change_oi": -25000, # Put writing surge + Call unwinding
            "max_call_oi_strike": 22700.0,
            "max_put_oi_strike": 22400.0,
        }
        preflight_res = PreFlightEngine.evaluate(
            direction="BUY",
            spot_price=22550.0,
            indicators={"vwap": 22500.0, "atr_14": 18.0, "adx": 27.0},
            option_chain=oc_mock,
            mtf_data=mtf_mock,
        )

        self.assertTrue(preflight_res["mtf"]["trend_15m"] == "BULLISH")
        self.assertTrue(preflight_res["mtf"]["trend_1h"] == "BULLISH")
        # Dynamic SL = 1.2 * 18.0 = 21.6 pts
        self.assertEqual(preflight_res["regime"]["dynamic_sl_pts"], 21.6)
        # Check positive driver includes MTF
        mtf_driver_found = any("80%+" in d for d in preflight_res["positive_drivers"])
        self.assertTrue(mtf_driver_found, "Expected 80%+ MTF win rate driver")

    def test_03_multi_agent_devils_advocate_architecture(self):
        """
        Verify that trade suggestions are structured through the Multi-Agent Debate:
        - Agent 1: Alpha Scout (Opportunity Hunter)
        - Agent 2: Devil's Advocate (Risk Manager)
        - Senior Prop Synthesizer (Chain-of-Thought with Steps 1-4)
        """
        market_state = {
            "price": 22520.0,
            "username": "Vikram",
            "trading_style": "intraday_scalper",
            "technical_eval": {
                "vwap": {"value": 22500.0, "upper_2": 22590.0, "lower_2": 22410.0, "bias": "BULLISH"},
                "ema": {"ema_20": 22495.0, "alignment": "BULLISH_STACK"},
                "oscillators": {"rsi_14": 56.0, "atr_14": 16.0},
                "volume": {"current_volume": 1200000, "volume_ratio": 1.45},
            },
            "comb_sr_levels": [
                {"role": "Support", "price": 22450.0, "bounces": 7},
                {"role": "Resistance", "price": 22580.0, "bounces": 8},
            ],
            "option_chain": {"pcr": 1.10, "max_call_oi_strike": 22650.0, "max_put_oi_strike": 22400.0},
        }

        res = self.service.ask(query="Where to enter?", market_state=market_state)
        reply = res["reply"]

        self.assertIn("Vikram", reply)
        # Check Agent 1
        self.assertIn("Alpha Scout", reply)
        # Check Agent 2
        self.assertIn("Devil's Advocate", reply)
        # Check Senior Prop Synthesizer
        self.assertIn("Senior Prop Synthesizer", reply)
        # Check Chain-of-Thought Steps
        self.assertIn("Step 1 (Structure)", reply)
        self.assertIn("Step 2 (Momentum)", reply)
        self.assertIn("Step 3 (Risk Mitigation)", reply)
        self.assertIn("Step 4 (Verdict)", reply)
        # Check required tags
        self.assertIn("Suggested Setup & Bias", reply)
        self.assertIn("High-Probability Entry Zone", reply)
        self.assertIn("1 Lot = 65 Quantity", reply)

    def test_04_stateful_session_memory_and_trade_tracking(self):
        """
        Verify Multi-Turn Memory & Trade State Tracking:
        Turn 1: User asks: "Is NIFTY Call good at 22,720?" -> AI records trade at 22,720.
        Turn 2: 15 mins later, user asks: "Should I exit now?" with LTP = 22,755.
        AI replies with +35 points profit recognition, suggests moving SL to cost (22,720)
        and holding for target!
        """
        user_id = "test_user_multi_turn_101"
        self.memory.clear_active_trade(user_id)

        # Turn 1: User asks about entry at 22,720
        market_t1 = {
            "price": 22720.0,
            "username": "Amit",
            "trading_style": "intraday_scalper",
            "technical_eval": {
                "vwap": {"value": 22700.0, "upper_2": 22780.0, "lower_2": 22620.0, "bias": "BULLISH"},
                "ema": {"ema_20": 22695.0, "alignment": "BULLISH_STACK"},
                "oscillators": {"rsi_14": 55.0, "atr_14": 15.0},
                "volume": {"volume_ratio": 1.3},
            },
            "comb_sr_levels": [
                {"role": "Support", "price": 22680.0, "bounces": 6},
                {"role": "Resistance", "price": 22780.0, "bounces": 7},
            ],
            "option_chain": {"pcr": 1.15, "max_call_oi_strike": 22800.0, "max_put_oi_strike": 22650.0},
        }

        res1 = self.service.ask(query="Is NIFTY Call good at 22,720?", market_state=market_t1, user_id=user_id)
        # Verify trade was logged in memory
        active_trade = self.memory.get_active_trade(user_id)
        self.assertIsNotNone(active_trade, "Active trade must be recorded in session memory")
        self.assertEqual(active_trade["direction"], "CALL")
        self.assertEqual(active_trade["entry_price"], 22720.0)

        # Verify sliding window buffer has the turns
        history = self.memory.get_history(user_id)
        self.assertGreaterEqual(len(history), 2) # 1 user + 1 assistant

        # Turn 2: Market moves to 22,755 (+35 pts). User asks: "Should I exit now?"
        market_t2 = dict(market_t1)
        market_t2["price"] = 22755.0

        res2 = self.service.ask(query="Should I exit now?", market_state=market_t2, user_id=user_id)
        reply2 = res2["reply"]

        # Must recognize user is in profit (+35 points) on the 22,720 Call
        self.assertIn("+35", reply2)
        self.assertIn("22,720", reply2)
        # Must advise moving Stop-Loss to Cost (22,720) to lock in risk-free trade
        self.assertTrue("Cost" in reply2 or "cost" in reply2 or "risk-free" in reply2 or "Risk-Free" in reply2)


if __name__ == "__main__":
    unittest.main()
