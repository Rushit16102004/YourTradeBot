"""
Tests Trend Exit (slope < slope_exit) and Entry rules for ZFTF strategy without target/SL.
"""
import pandas as pd
import pytz
from config import StrategyConfig
from strategy import ZFTFStrategy

IST = pytz.timezone("Asia/Kolkata")


def test_zftf_trend_and_slope_exit():
    cfg = StrategyConfig()
    cfg.z_threshold = 2.0
    cfg.slope_entry = 0.001
    cfg.slope_exit = -0.001

    strat = ZFTFStrategy(cfg)

    # 1. Entry Long at 20000
    ts1 = IST.localize(pd.Timestamp("2026-10-14 09:40:00"))
    r1 = pd.Series({
        "timestamp": ts1,
        "close": 20000.0,
        "mean": 19900.0,
        "std": 40.0,
        "z": 2.5,
        "slope": 0.05
    }, name=ts1)
    s1 = strat.update(r1)
    assert s1.signal == 1
    assert s1.in_position is True

    # 2. Maintain position when slope > slope_exit
    ts2 = IST.localize(pd.Timestamp("2026-10-14 09:45:00"))
    r2 = r1.copy()
    r2.name = ts2
    r2["close"] = 20050.0
    r2["slope"] = 0.01  # > -0.001

    s2 = strat.update(r2)
    assert s2.signal == 2
    assert s2.in_position is True

    # 3. Slope Exit when slope < slope_exit (-0.001)
    ts3 = IST.localize(pd.Timestamp("2026-10-14 09:50:00"))
    r3 = r1.copy()
    r3.name = ts3
    r3["close"] = 20010.0
    r3["slope"] = -0.005  # < -0.001

    s3 = strat.update(r3)
    assert s3.signal == -1
    assert s3.exit_reason == "TREND_EXIT"
    assert s3.in_position is False
