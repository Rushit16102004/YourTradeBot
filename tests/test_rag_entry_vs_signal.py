import unittest
from RAG.rag_service import RAGService
from RAG.llm_client import GeminiLLMClient

class TestRAGEntryVsSignal(unittest.TestCase):
    def setUp(self):
        self.service = RAGService.get_instance()
        self.mock_market_state = {
            "price": 22520.0,
            "username": "TraderRahul",
            "trading_style": "intraday_scalper",
            "technical_eval": {
                "vwap": {
                    "value": 22500.0,
                    "upper_2": 22590.0,
                    "lower_2": 22410.0,
                    "bias": "BULLISH",
                    "dist_pts": 20.0,
                    "dist_pct": 0.09,
                    "exhaustion_status": "Normal Runway",
                },
                "ema": {
                    "ema_9": 22515.0,
                    "ema_20": 22495.0,
                    "ema_50": 22460.0,
                    "ema_200": 22350.0,
                    "alignment": "BULLISH_STACK",
                    "quality": "Clean Bullish Trend",
                    "slope_20": 0.045,
                    "price_above_ema20": True,
                },
                "oscillators": {
                    "rsi_14": 58.4,
                    "rsi_status": "Bullish Momentum",
                    "macd_hist": 4.2,
                    "macd_status": "Bullish Expanding",
                    "atr_14": 32.0,
                },
                "volume": {
                    "current_volume": 1250000,
                    "volume_ma_20": 980000,
                    "volume_ratio": 1.28,
                    "status": "High Volume Expansion",
                },
                "reversal": {
                    "risk_level": "LOW",
                    "triggers": [],
                    "expected_reversal_analysis": "No reversal triggers active.",
                },
            },
            "comb_sr_levels": [
                {"role": "Support", "price": 22450.0, "bounces": 7},
                {"role": "Support", "price": 22400.0, "bounces": 3},  # <= 5 touches, should be filtered out
                {"role": "Resistance", "price": 22580.0, "bounces": 8},
                {"role": "Resistance", "price": 22620.0, "bounces": 2},  # <= 5 touches, should be filtered out
            ],
            "last_signal": {
                "action": "BUY",
                "time": "26-10-2026 10:15 IST",
                "price": 22480.0,
                "reason": "Z-Score Breakout above VWAP",
            },
            "last_entry_signal": {
                "action": "BUY",
                "time": "26-10-2026 10:15 IST",
                "price": 22480.0,
            },
            "recent_signals": [
                {"time": "26-10-2026 09:35 IST", "action": "BUY", "price": 22420.0, "reason": "ORB Breakout"},
                {"time": "26-10-2026 10:15 IST", "action": "BUY", "price": 22480.0, "reason": "Z-Score Breakout above VWAP"},
            ],
            "total_signals_count": 2,
        }

    def test_when_to_enter_gives_copilot_suggestion_not_main_signal(self):
        queries = [
            "when should I enter?",
            "where to enter?",
            "when i have enter",
            "should I buy or sell?",
            "give me an entry suggestion",
        ]
        for q in queries:
            res = self.service.ask(query=q, market_state=self.mock_market_state)
            reply = res["reply"]
            # Must address user by name
            self.assertIn("TraderRahul", reply)
            # Must provide Copilot's own quantitative suggestion
            self.assertTrue(
                "quantitative entry suggestion" in reply or "Suggested Setup & Bias" in reply or "High-Probability Entry Zone" in reply,
                f"Failed for query '{q}': {reply}"
            )
            # MUST NOT dump the main strategy signal details
            self.assertNotIn("Main Strategy Signal Details", reply)
            self.assertNotIn("The last signal was a BUY", reply)
            self.assertNotIn("22480.0", reply) # Not quoting the old signal entry price
            # Must use S&R > 5x touches (22450 with 7 touches or 22580 with 8 touches)
            self.assertTrue("22450" in reply or "22580" in reply)
            # Must NOT use levels with <= 5 touches (22400 or 22620)
            self.assertNotIn("22400", reply)
            self.assertNotIn("22620", reply)

    def test_explicit_signal_queries_provide_main_signal(self):
        signal_queries = [
            "give me info about main signal",
            "what was the last signal?",
            "display signal",
            "tell me about the signal",
        ]
        for q in signal_queries:
            res = self.service.ask(query=q, market_state=self.mock_market_state)
            reply = res["reply"]
            self.assertIn("TraderRahul", reply)
            # MUST give info about the Main Strategy signal
            self.assertTrue(
                "BUY" in reply and ("22480" in reply or "Z-Score Breakout" in reply),
                f"Failed for signal query '{q}': {reply}"
            )

    def test_sr_queries_respect_more_than_5x_touches(self):
        res = self.service.ask(query="what is the nearest support and resistance?", market_state=self.mock_market_state)
        reply = res["reply"]
        self.assertIn("22450", reply)
        self.assertIn("22580", reply)
        self.assertIn("> 5 touches", reply)
        # Filtered out <= 5 touches
        self.assertNotIn("22400", reply)
        self.assertNotIn("22620", reply)

if __name__ == "__main__":
    unittest.main()
