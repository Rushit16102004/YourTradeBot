"""
Tests verifying accuracy of ZFTF indicators (Mean, Std Dev, Z-Score, Linreg Slope).
"""
import pandas as pd
import numpy as np
from config import StrategyConfig
from indicators import calculate_sma, calculate_stdev, calculate_z_score, calculate_linreg_slope, compute_all_indicators


def test_sma_calculation():
    data = pd.Series([10.0, 11.0, 12.0, 13.0, 14.0])
    mean = calculate_sma(data, window=5)
    assert mean.iloc[-1] == 12.0


def test_z_score():
    close = pd.Series([10.0, 10.0, 10.0, 10.0, 14.0])
    mean = calculate_sma(close, window=5)
    std = calculate_stdev(close, window=5)
    z = calculate_z_score(close, mean, std)
    assert not np.isnan(z.iloc[-1])
    assert z.iloc[-1] > 1.5  # Outlier close=14 has high z-score


def test_linreg_slope():
    # Linear series with step 2.0 per bar
    close = pd.Series([10.0, 12.0, 14.0, 16.0, 18.0, 20.0])
    slope = calculate_linreg_slope(close, window=5)
    assert round(slope.iloc[-1], 4) == 2.0


def test_vwap_and_bands_calculation():
    from indicators import calculate_session_vwap_with_bands
    import pytz
    from datetime import datetime, timedelta

    IST = pytz.timezone("Asia/Kolkata")
    base_time = IST.localize(datetime(2026, 10, 23, 9, 15))
    records = []
    for i in range(15):
        t = base_time + timedelta(minutes=5 * i)
        p = 22500.0 + i * 10
        records.append({
            "timestamp": t,
            "open": p,
            "high": p + 5,
            "low": p - 5,
            "close": p,
            "volume": 1000
        })
    df = pd.DataFrame(records).set_index("timestamp")
    res = calculate_session_vwap_with_bands(df, num_std=2.0)
    assert "vwap" in res.columns
    assert "vwap_upper_2" in res.columns
    assert "vwap_lower_2" in res.columns
    assert res["vwap_upper_2"].iloc[-1] > res["vwap"].iloc[-1]
    assert res["vwap_lower_2"].iloc[-1] < res["vwap"].iloc[-1]
