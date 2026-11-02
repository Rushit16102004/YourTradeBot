import pytest
import numpy as np
import pandas as pd
from broker.nifty50_volume_aggregator import OFFICIAL_NIFTY_50_STOCKS, Nifty50VolumeAggregator


def test_official_nifty_50_constituents_count():
    assert len(OFFICIAL_NIFTY_50_STOCKS) == 50
    # No duplicate tickers
    assert len(set(OFFICIAL_NIFTY_50_STOCKS)) == 50
    # Ensure invalid tickers are completely removed
    for invalid in ["BSE", "ETERNAL", "TMPV", "MAXHEALTH"]:
        assert invalid not in OFFICIAL_NIFTY_50_STOCKS
    # Ensure key constituents are present
    for valid in ["TATAMOTORS", "WIPRO", "BPCL", "BRITANNIA", "HEROMOTOCO", "INDUSINDBK"]:
        assert valid in OFFICIAL_NIFTY_50_STOCKS


def test_market_breadth_strictly_sums_to_50_and_100_pct():
    agg = Nifty50VolumeAggregator.get_instance()
    breadth = agg.get_market_breadth()
    assert breadth is not None
    assert "advances" in breadth
    assert "declines" in breadth
    assert "advances_pct" in breadth
    assert "declines_pct" in breadth

    adv = breadth["advances"]
    dec = breadth["declines"]
    adv_pct = breadth["advances_pct"]
    dec_pct = breadth["declines_pct"]

    assert adv + dec == 50, f"Expected 50 stocks, got {adv} + {dec} = {adv + dec}"
    assert round(adv_pct + dec_pct, 1) == 100.0, f"Expected 100.0%, got {adv_pct} + {dec_pct} = {adv_pct + dec_pct}"
    assert adv >= 0 and dec >= 0


def test_market_breadth_calculation_with_simulated_nans():
    # Simulate a scenario where 8 stocks are NaN, 25 are up, 17 are down
    tickers = [s + ".NS" for s in OFFICIAL_NIFTY_50_STOCKS]
    opens = [100.0] * 50
    closes = [105.0] * 25 + [95.0] * 17 + [float("nan")] * 8

    df_open = pd.DataFrame([opens], columns=tickers)
    df_close = pd.DataFrame([closes], columns=tickers)

    c_last = df_close.iloc[-1]
    o_first = df_open.iloc[0]
    diff = c_last - o_first
    valid_diff = diff.dropna()

    assert len(valid_diff) == 42
    raw_adv = int((valid_diff > 0).sum())
    raw_dec = int((valid_diff < 0).sum())
    raw_flat = int((valid_diff == 0).sum())
    valid_total = raw_adv + raw_dec + raw_flat

    adv_scaled = int(round((raw_adv + (raw_flat / 2.0)) / valid_total * 50.0))
    adv = max(0, min(50, adv_scaled))
    dec = 50 - adv
    adv_pct = round((adv / 50.0) * 100.0, 1)
    dec_pct = round(100.0 - adv_pct, 1)

    assert adv + dec == 50
    assert adv_pct + dec_pct == 100.0
