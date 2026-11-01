"""
Tests ZFTF Strategy BUY, SELL, HOLD, and NONE signal generation matching exact Pine Script:
- Entry on z > z_threshold and slope > slope_entry
- Exit on target_hit, stop_hit, or trend_exit (slope < slope_exit)
"""
import pandas as pd
import pytz
from config import StrategyConfig
from strategy import ZFTFStrategy

IST = pytz.timezone("Asia/Kolkata")


def test_zftf_buy_entry_and_hold_state():
    cfg = StrategyConfig()
    cfg.z_threshold = 2.0
    cfg.slope_entry = 0.001
    cfg.target_pct = 0.06
    cfg.stop_pct = 0.03

    strat = ZFTFStrategy(cfg)

    # 1. Entry Long
    ts = IST.localize(pd.Timestamp("2026-10-14 09:45:00"))
    row = pd.Series({
        "timestamp": ts,
        "open": 22400.0,
        "high": 22460.0,
        "low": 22390.0,
        "close": 22450.0,
        "mean": 22350.0,
        "std": 40.0,
        "z": 2.5,          # > z_threshold (2.0)
        "slope": 0.05      # > slope_entry (0.001)
    }, name=ts)

    state = strat.update(row)
    assert state.signal == 1
    assert state.signal_name == "BUY"
    assert state.in_position is True
    assert state.entry_price == 22450.0
    assert state.target_price == 22450.0 * 1.06
    assert state.stop_loss == 22450.0 * 0.97

    # 2. Next bar within range maintains HOLD
    ts2 = IST.localize(pd.Timestamp("2026-10-14 09:50:00"))
    hold_row = row.copy()
    hold_row.name = ts2
    hold_row["close"] = 22470.0
    hold_row["slope"] = 0.02  # Still > slope_exit (-0.001)

    state2 = strat.update(hold_row)
    assert state2.signal == 2
    assert state2.signal_name == "HOLD"
    assert state2.in_position is True

    # 3. Target hit exit (+6%)
    ts3 = IST.localize(pd.Timestamp("2026-10-14 10:30:00"))
    tgt_row = row.copy()
    tgt_row.name = ts3
    tgt_row["close"] = 22450.0 * 1.07  # Above +6%
    state_tgt = strat.update(tgt_row)
    assert state_tgt.signal == -1
    assert state_tgt.signal_name == "SELL"
    assert state_tgt.in_position is False
    assert state_tgt.exit_reason == "TARGET_HIT"
