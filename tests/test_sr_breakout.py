"""
Unit tests for S&R Breakout & Breakdown Strategy Engine:
- 2-candle confirmation (no reversal)
- Strong S&R levels only (bounces >= 4)
- Minimum 50-point runway to next S&R
- Repeating text: CALL-CALL-CALL... or PUT-PUT-PUT...
"""
from datetime import datetime, timedelta
import pandas as pd
import pytz
from sr_breakout_engine import (
    evaluate_sr_breakout,
    evaluate_sr_reversal,
    is_level_strong,
    find_next_resistance_above,
    find_next_support_below,
)

IST = pytz.timezone("Asia/Kolkata")


def test_is_level_strong():
    strong_1 = {"bounces": 6, "type": "line", "role": "Resistance"}
    strong_2 = {"bounces": 7, "type": "rect", "role": "S/R Flip Zone"}
    weak_1 = {"bounces": 5, "type": "line", "role": "Strong S/R Flip"}
    weak_2 = {"bounces": 4, "type": "line", "role": "Support"}
    weak_3 = {"bounces": 2, "type": "line", "role": "Local Support"}

    assert is_level_strong(strong_1) is True
    assert is_level_strong(strong_2) is True
    assert is_level_strong(weak_1) is False
    assert is_level_strong(weak_2) is False
    assert is_level_strong(weak_3) is False


def test_next_resistance_and_support_distance():
    sr_levels = [
        {"avg_price": 22400.0, "is_support": True, "bounces": 5},
        {"avg_price": 22500.0, "is_support": False, "bounces": 4},
        {"avg_price": 22580.0, "is_support": False, "bounces": 6},  # gap = 80 pts >= 50
        {"avg_price": 22320.0, "is_support": True, "bounces": 4},   # gap = 80 pts >= 50
    ]

    next_r, gap_r = find_next_resistance_above(22500.0, sr_levels)
    assert next_r == 22580.0
    assert gap_r == 80.0

    next_s, gap_s = find_next_support_below(22400.0, sr_levels)
    assert next_s == 22320.0
    assert gap_s == 80.0


def test_call_breakout_confirmed_with_50pt_gap():
    base_t = IST.localize(datetime(2026, 10, 23, 10, 0))
    # 3 candles:
    # 1. Base candle: close 22490 (below 22500)
    # 2. Breakout candle: close 22510 (breaks above strong resistance 22500)
    # 3. Confirmation candle: close 22525 (continues in same direction, does not reverse below 22500)
    candles = [
        {"timestamp": base_t, "open": 22485, "high": 22495, "low": 22480, "close": 22490},
        {"timestamp": base_t + timedelta(minutes=5), "open": 22490, "high": 22515, "low": 22488, "close": 22510},
        {"timestamp": base_t + timedelta(minutes=10), "open": 22510, "high": 22530, "low": 22504, "close": 22525},
    ]
    df = pd.DataFrame(candles).set_index("timestamp")

    sr_levels = [
        {"id": "r1", "avg_price": 22500.0, "is_support": False, "bounces": 6, "role": "Strong Resistance"},
        {"id": "r2", "avg_price": 22570.0, "is_support": False, "bounces": 4, "role": "Next Resistance"}, # gap 70 >= 50
    ]

    alert = evaluate_sr_breakout(df, sr_levels, min_runway_points=50.0)
    assert alert is not None
    assert alert["type"] == "CALL"
    assert alert["action"] == "BUY CALL"
    assert "CALL-CALL-CALL" in alert["repeating_text"]
    assert alert["broken_level"] == 22500.0
    assert alert["target_level"] == 22570.0
    assert alert["gap_pts"] >= 50.0


def test_call_breakout_rejected_due_to_less_than_50pt_gap():
    base_t = IST.localize(datetime(2026, 10, 23, 10, 0))
    candles = [
        {"timestamp": base_t, "open": 22485, "high": 22495, "low": 22480, "close": 22490},
        {"timestamp": base_t + timedelta(minutes=5), "open": 22490, "high": 22515, "low": 22488, "close": 22510},
        {"timestamp": base_t + timedelta(minutes=10), "open": 22510, "high": 22530, "low": 22504, "close": 22525},
    ]
    df = pd.DataFrame(candles).set_index("timestamp")

    # Next resistance is only 25 pts away (22525) -> should be rejected!
    sr_levels = [
        {"id": "r1", "avg_price": 22500.0, "is_support": False, "bounces": 6, "role": "Strong Resistance"},
        {"id": "r2", "avg_price": 22525.0, "is_support": False, "bounces": 4, "role": "Next Resistance"}, # gap 25 < 50
    ]

    alert = evaluate_sr_breakout(df, sr_levels, min_runway_points=50.0)
    assert alert is None


def test_put_breakdown_confirmed_with_50pt_gap():
    base_t = IST.localize(datetime(2026, 10, 23, 11, 0))
    # 3 candles:
    # 1. Base candle: close 22410 (above 22400)
    # 2. Breakdown candle: close 22390 (breaks below strong support 22400)
    # 3. Confirmation candle: close 22375 (continues in same direction, does not reverse above 22400)
    candles = [
        {"timestamp": base_t, "open": 22415, "high": 22420, "low": 22405, "close": 22410},
        {"timestamp": base_t + timedelta(minutes=5), "open": 22410, "high": 22412, "low": 22385, "close": 22390},
        {"timestamp": base_t + timedelta(minutes=10), "open": 22390, "high": 22394, "low": 22370, "close": 22375},
    ]
    df = pd.DataFrame(candles).set_index("timestamp")

    sr_levels = [
        {"id": "s1", "avg_price": 22400.0, "is_support": True, "bounces": 6, "role": "Strong Support"},
        {"id": "s2", "avg_price": 22330.0, "is_support": True, "bounces": 4, "role": "Next Support"}, # gap 70 >= 50
    ]

    alert = evaluate_sr_breakout(df, sr_levels, min_runway_points=50.0)
    assert alert is not None
    assert alert["type"] == "PUT"
    assert alert["action"] == "BUY PUT"
    assert "PUT-PUT-PUT" in alert["repeating_text"]
    assert alert["broken_level"] == 22400.0
    assert alert["target_level"] == 22330.0
    assert alert["gap_pts"] >= 50.0


def test_bull_trap_reversal_confirmed():
    """High pierces strong resistance, wicks back down >= 40% wick, closes below level with >= 50pt target and 2nd candle confirmation."""
    base_t = datetime(2026, 10, 23, 10, 0, tzinfo=IST)
    candles = [
        {"timestamp": base_t, "open": 22480, "high": 22495, "low": 22475, "close": 22490},
        # Bull Trap candle: high 22515 pierces 22500, close 22485 closes back below 22500, upper wick 25/30 = 83%
        {"timestamp": base_t + timedelta(minutes=5), "open": 22490, "high": 22515, "low": 22485, "close": 22486},
        # Confirmation candle: closes lower without violating trap high
        {"timestamp": base_t + timedelta(minutes=10), "open": 22486, "high": 22490, "low": 22470, "close": 22475},
    ]
    df = pd.DataFrame(candles).set_index("timestamp")

    sr_levels = [
        {"id": "r1", "avg_price": 22500.0, "is_support": False, "bounces": 6, "role": "Strong Resistance"},
        {"id": "s1", "avg_price": 22410.0, "is_support": True, "bounces": 4, "role": "Next Support"}, # gap 90 >= 50
    ]

    alert = evaluate_sr_reversal(df, sr_levels, min_runway_points=50.0)
    assert alert is not None
    assert alert["type"] == "PUT"
    assert alert["sub_type"] == "REVERSAL"
    assert "TRAP-PUT" in alert["repeating_text"]
    assert "BULL TRAP" in alert["title"]
    assert alert["swept_level"] == 22500.0
    assert alert["target_level"] == 22410.0
    assert alert["gap_pts"] >= 50.0
    assert alert["wick_pct"] >= 40.0


def test_bear_trap_reversal_confirmed():
    """Low pierces strong support, wicks back up >= 40% wick, closes above level with >= 50pt target and 2nd candle confirmation."""
    base_t = datetime(2026, 10, 23, 11, 0, tzinfo=IST)
    candles = [
        {"timestamp": base_t, "open": 22415, "high": 22420, "low": 22405, "close": 22410},
        # Bear Trap candle: low 22385 pierces 22400, close 22412 recovers above 22400, lower wick 25/30 = 83%
        {"timestamp": base_t + timedelta(minutes=5), "open": 22410, "high": 22415, "low": 22385, "close": 22412},
        # Confirmation candle: closes higher without violating trap low
        {"timestamp": base_t + timedelta(minutes=10), "open": 22412, "high": 22430, "low": 22408, "close": 22425},
    ]
    df = pd.DataFrame(candles).set_index("timestamp")

    sr_levels = [
        {"id": "s1", "avg_price": 22400.0, "is_support": True, "bounces": 6, "role": "Strong Support"},
        {"id": "r1", "avg_price": 22490.0, "is_support": False, "bounces": 5, "role": "Next Resistance"}, # gap 90 >= 50
    ]

    alert = evaluate_sr_reversal(df, sr_levels, min_runway_points=50.0)
    assert alert is not None
    assert alert["type"] == "CALL"
    assert alert["sub_type"] == "REVERSAL"
    assert "TRAP-CALL" in alert["repeating_text"]
    assert "BEAR TRAP" in alert["title"]
    assert alert["swept_level"] == 22400.0
    assert alert["target_level"] == 22490.0
    assert alert["gap_pts"] >= 50.0
    assert alert["wick_pct"] >= 40.0


def test_reversal_rejected_due_to_small_wick():
    """If rejection wick is small (< 40%), it is not considered a valid liquidity sweep trap."""
    base_t = datetime(2026, 10, 23, 11, 0, tzinfo=IST)
    candles = [
        {"timestamp": base_t, "open": 22480, "high": 22495, "low": 22475, "close": 22490},
        # High 22502 only 2 pts above 22500, but candle range 20, upper wick 3 pts (15% < 40%)
        {"timestamp": base_t + timedelta(minutes=5), "open": 22485, "high": 22502, "low": 22482, "close": 22499},
    ]
    df = pd.DataFrame(candles).set_index("timestamp")

    sr_levels = [
        {"id": "r1", "avg_price": 22500.0, "is_support": False, "bounces": 4, "role": "Strong Resistance"},
        {"id": "s1", "avg_price": 22420.0, "is_support": True, "bounces": 4, "role": "Next Support"},
    ]

    alert = evaluate_sr_reversal(df, sr_levels, min_runway_points=50.0, min_wick_ratio=0.40)
    assert alert is None


def test_reversal_rejected_due_to_less_than_50pt_runway():
    """Even if trap wick is high, rejected if target gap < 50 points."""
    base_t = datetime(2026, 10, 23, 11, 0, tzinfo=IST)
    candles = [
        {"timestamp": base_t, "open": 22480, "high": 22495, "low": 22475, "close": 22490},
        {"timestamp": base_t + timedelta(minutes=5), "open": 22490, "high": 22515, "low": 22485, "close": 22486},
    ]
    df = pd.DataFrame(candles).set_index("timestamp")

    sr_levels = [
        {"id": "r1", "avg_price": 22500.0, "is_support": False, "bounces": 6, "role": "Strong Resistance"},
        # Next support is at 22480 (gap is only 20 pts < 50)
        {"id": "s1", "avg_price": 22480.0, "is_support": True, "bounces": 4, "role": "Close Support"},
    ]

    alert = evaluate_sr_reversal(df, sr_levels, min_runway_points=50.0)
    assert alert is None


def test_sr_signal_timeframe_tags_on_combined_levels():
    """Verifies that signals preserve timeframe tags from combined S&R levels."""
    base_t = IST.localize(datetime(2026, 10, 23, 10, 0))
    candles = [
        {"timestamp": base_t, "open": 22485, "high": 22495, "low": 22480, "close": 22490},
        {"timestamp": base_t + timedelta(minutes=5), "open": 22490, "high": 22515, "low": 22488, "close": 22510},
        {"timestamp": base_t + timedelta(minutes=10), "open": 22510, "high": 22530, "low": 22504, "close": 22525},
    ]
    df = pd.DataFrame(candles).set_index("timestamp")

    sr_levels = [
        {
            "id": "r1",
            "avg_price": 22500.0,
            "is_support": False,
            "bounces": 6,
            "role": "Strong Resistance (1M+2M Confluence)",
            "timeframe_tag": "1M + 2M Confluence",
            "is_confluence": True,
            "origin": "1M + 2M Confluence",
        },
        {
            "id": "r2",
            "avg_price": 22580.0,
            "is_support": False,
            "bounces": 5,
            "role": "Next Resistance (2M Macro)",
            "timeframe_tag": "2M Macro",
            "is_confluence": False,
            "origin": "2M Macro",
        },
    ]

    alert = evaluate_sr_breakout(df, sr_levels, min_runway_points=50.0)
    assert alert is not None
    assert alert["timeframe_tag"] == "1M + 2M Confluence"
    assert alert["is_confluence"] is True
    assert alert["origin"] == "1M + 2M Confluence"




def test_strictly_more_than_5x_threshold():
    """Guarantees that 5x levels are rejected and only > 5x (6x+) trigger breakout & reversal."""
    base_t = IST.localize(datetime(2026, 10, 23, 10, 0))
    candles_breakout = [
        {"timestamp": base_t, "open": 22485, "high": 22495, "low": 22480, "close": 22490},
        {"timestamp": base_t + timedelta(minutes=5), "open": 22490, "high": 22515, "low": 22488, "close": 22510},
        {"timestamp": base_t + timedelta(minutes=10), "open": 22510, "high": 22530, "low": 22504, "close": 22525},
    ]
    df_b = pd.DataFrame(candles_breakout).set_index("timestamp")

    # 1. Level with EXACTLY 5 bounces -> MUST BE REJECTED (more than 5x required)
    sr_5x = [
        {"id": "r5", "avg_price": 22500.0, "is_support": False, "bounces": 5, "role": "Strong Resistance"},
        {"id": "r_next", "avg_price": 22580.0, "is_support": False, "bounces": 6, "role": "Next Resistance"},
    ]
    assert evaluate_sr_breakout(df_b, sr_5x, min_runway_points=50.0) is None

    # 2. Level with 6 bounces (> 5x) -> MUST TRIGGER SIGNAL
    sr_6x = [
        {"id": "r6", "avg_price": 22500.0, "is_support": False, "bounces": 6, "role": "Major Resistance"},
        {"id": "r_next", "avg_price": 22580.0, "is_support": False, "bounces": 6, "role": "Next Resistance"},
    ]
    alert = evaluate_sr_breakout(df_b, sr_6x, min_runway_points=50.0)
    assert alert is not None
    assert alert["type"] == "CALL"

    # 3. Reversal test: 5x level -> REJECTED
    candles_trap = [
        {"timestamp": base_t, "open": 22480, "high": 22495, "low": 22475, "close": 22490},
        {"timestamp": base_t + timedelta(minutes=5), "open": 22490, "high": 22515, "low": 22485, "close": 22486},
        {"timestamp": base_t + timedelta(minutes=10), "open": 22486, "high": 22490, "low": 22470, "close": 22475},
    ]
    df_t = pd.DataFrame(candles_trap).set_index("timestamp")
    assert evaluate_sr_reversal(df_t, sr_5x, min_runway_points=50.0) is None

    # 4. Reversal test: 6x level -> TRIGGERS REVERSAL SIGNAL
    trap_alert = evaluate_sr_reversal(df_t, sr_6x, min_runway_points=50.0)
    assert trap_alert is not None
    assert trap_alert["sub_type"] == "REVERSAL"
