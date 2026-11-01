import unittest
import pandas as pd
from broker.nifty50_volume_aggregator import Nifty50VolumeAggregator, OFFICIAL_NIFTY_50_STOCKS, NIFTY_50_TICKERS

class TestNifty50VolumeAll50(unittest.TestCase):
    def setUp(self):
        self.agg = Nifty50VolumeAggregator.get_instance()

    def test_official_nifty50_constituents_count_and_format(self):
        """Validates that exactly 50 official NIFTY constituent stocks are configured."""
        self.assertEqual(len(OFFICIAL_NIFTY_50_STOCKS), 50, "Must contain exactly 50 official constituent stocks")
        self.assertEqual(len(NIFTY_50_TICKERS), 50, "Must contain exactly 50 .NS tickers")
        
        # Verify heavyweights and recent inclusions are present
        required_symbols = [
            "RELIANCE", "HDFCBANK", "ICICIBANK", "INFY", "ITC", "TCS", "LT",
            "BHARTIARTL", "AXISBANK", "SBIN", "KOTAKBANK", "TATASTEEL", "COALINDIA",
            "ETERNAL", "BEL", "TRENT", "TMPV", "SHRIRAMFIN", "JIOFIN"
        ]
        for sym in required_symbols:
            self.assertIn(sym, OFFICIAL_NIFTY_50_STOCKS, f"{sym} must be in official NIFTY 50 list")
            self.assertIn(f"{sym}.NS", NIFTY_50_TICKERS, f"{sym}.NS must be in ticker list")

    def test_cache_contains_true_volume_bars(self):
        """Validates that cached volume contains thousands of authentic 5m bars without flatlines."""
        self.assertIsNotNone(self.agg._volume_series, "Volume series must be loaded")
        self.assertGreater(len(self.agg._volume_series), 3000, "Cache must contain > 3000 historical 5m bars")
        
        # Check that volume values reflect authentic multi-million share trading
        recent_bars = self.agg._volume_series[self.agg._volume_series > 0].tail(20)
        self.assertTrue((recent_bars > 500000).all(), "5m NIFTY volume bars must reflect multi-million share turnover")
        
        # Verify no flatlines
        diffs = recent_bars.diff().dropna()
        self.assertTrue((diffs != 0).any(), "Volume must not be flat constant values")

    def test_merge_volume_into_candles(self):
        """Validates that merging volume into candles accurately populates volume and volume_ma_20."""
        # Create mock 5m candlestick DataFrame matching timestamps in cache
        sample_idx = self.agg._volume_series.index[-25:]
        df_candles = pd.DataFrame({
            "open": [22500.0 + i for i in range(25)],
            "high": [22510.0 + i for i in range(25)],
            "low": [22490.0 + i for i in range(25)],
            "close": [22505.0 + i for i in range(25)],
        }, index=sample_idx)
        
        merged = self.agg.merge_volume_into_candles(df_candles)
        self.assertIn("volume", merged.columns)
        self.assertIn("volume_ma_20", merged.columns)
        
        # Check volume is authentic (not 0 or scaled)
        for vol in merged["volume"]:
            self.assertGreater(vol, 0.0)
            
        # Check MA 20 is positive and accurate
        self.assertGreater(merged["volume_ma_20"].iloc[-1], 0.0)
        expected_ma = merged["volume"].iloc[-20:].mean()
        self.assertAlmostEqual(merged["volume_ma_20"].iloc[-1], round(expected_ma, 2), delta=1.0)

    def test_stock_list_status_api(self):
        """Validates that get_stock_list_status returns complete constituent status."""
        status = self.agg.get_stock_list_status()
        self.assertEqual(status["total_constituent_count"], 50)
        self.assertEqual(len(status["stocks"]), 50)
        self.assertEqual(len(status["tickers"]), 50)
        self.assertEqual(status["scale_factor"], 1.0)
        self.assertTrue(status["is_authentic_sum"])

if __name__ == "__main__":
    unittest.main()
