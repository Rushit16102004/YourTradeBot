"""
Tests for Support and Resistance (S&R) detection algorithm and endpoint.
Verifies line >=3 bounces (spread <= 8 pts), rect >=4 bounces (spread > 8 pts),
and 1-Month vs 2-Month rolling periods.
"""
import os
from datetime import datetime, timedelta
import pandas as pd
import pytz
from fastapi.testclient import TestClient

from server import app
from support_resistance import (
    detect_support_resistance,
    detect_local_support_resistance,
    calculate_sr_periods,
    combine_sr_levels,
)

IST = pytz.timezone("Asia/Kolkata")


def test_detect_support_resistance_synthetic():
    # Build synthetic 5m candles with a tight line level and a wide rectangle level
    base_time = IST.localize(datetime(2026, 10, 1, 9, 15))
    records = []

    # Oscillating candles
    for i in range(120):
        t = base_time + timedelta(minutes=5 * i)
        # Tight support at 25000 (+/- 2 pts), wider resistance zone around 25500 (+/- 10 pts)
        is_bottom = (i // 10) % 2 == 0
        if is_bottom:
            p = 25000.0 + (i % 3) * 1.0  # spread <= 3 pts
            high = p + 4
            low = p - 2
        else:
            p = 25500.0 + ((i % 5) - 2) * 5.0  # spread ~ 20 pts
            high = p + 6
            low = p - 6

        records.append({
            "timestamp": t,
            "open": p,
            "high": high,
            "low": low,
            "close": p,
            "volume": 1000
        })

    df = pd.DataFrame(records).set_index("timestamp")
    levels = detect_support_resistance(
        df,
        swing_window=3,
        line_tolerance=4.0,
        rect_tolerance=12.0,
        line_min_bounces=3,
        rect_min_bounces=4,
    )

    assert len(levels) >= 1
    for lvl in levels:
        # Check white color
        assert lvl["color"] == "#ffffff"
        assert lvl["type"] in ("line", "rect")
        assert "is_sr_auto" in lvl
        assert "opacity" in lvl
        assert "width" in lvl
        if lvl["type"] == "line":
            assert lvl["bounces"] >= 3
            assert lvl["spread"] <= 8.0
        elif lvl["type"] == "rect":
            assert lvl["bounces"] >= 4
            assert lvl["spread"] > 8.0
            assert "fill_opacity" in lvl


def test_calculate_sr_periods():
    # Create 30 days of synthetic candles
    base_time = IST.localize(datetime(2026, 9, 1, 9, 15))
    records = []
    for day in range(30):
        day_date = base_time + timedelta(days=day)
        for m in range(75):
            t = day_date + timedelta(minutes=5 * m)
            p = 25000.0 + (m % 10) * 10
            records.append({
                "timestamp": t,
                "open": p,
                "high": p + 5,
                "low": p - 5,
                "close": p,
                "volume": 1000
            })
    df = pd.DataFrame(records).set_index("timestamp")
    res = calculate_sr_periods(df)
    assert "1m" in res
    assert "2m" in res
    assert "combined" in res
    assert "local_1m" in res
    assert "local_2m" in res
    assert isinstance(res["1m"], list)
    assert isinstance(res["2m"], list)
    assert isinstance(res["combined"], list)


def test_combine_sr_levels_confluence_and_unique():
    # 1M Support at 24000 (4 bounces) and 2M Support at 24004 (5 bounces) -> within 8 pts -> Merge!
    # 1M Resistance at 24500 (3 bounces) and 2M Resistance at 24800 (6 bounces) -> 300 pts -> Keep unique!
    levels_1m = [
        {"id": "s1", "avg_price": 24000.0, "price1": 24000.0, "is_support": True, "bounces": 4, "role": "Support", "type": "line"},
        {"id": "r1", "avg_price": 24500.0, "price1": 24500.0, "is_support": False, "bounces": 3, "role": "Resistance", "type": "line"},
    ]
    levels_2m = [
        {"id": "s2", "avg_price": 24004.0, "price1": 24004.0, "is_support": True, "bounces": 5, "role": "Support", "type": "line"},
        {"id": "r2", "avg_price": 24800.0, "price1": 24800.0, "is_support": False, "bounces": 6, "role": "Resistance", "type": "line"},
    ]

    combined = combine_sr_levels(levels_1m, levels_2m, price_tolerance=8.0, current_price=24300.0)

    # We expect:
    # 1 Confluence Support near 24002.0 with bounces = 5 + 1 = 6, tagged 1M + 2M Confluence
    # 1 Unique 1M Resistance at 24500 with tagged 1M Swing / Local
    # 1 Unique 2M Resistance at 24800 with tagged 2M Macro
    confluence_supports = [l for l in combined if l.get("is_confluence")]
    assert len(confluence_supports) == 1
    conf = confluence_supports[0]
    assert conf["avg_price"] == 24002.0
    assert conf["bounces"] == 6
    assert conf["timeframe_tag"] == "1M + 2M Confluence"
    assert conf["is_support"] is True

    unique_1m = [l for l in combined if l.get("timeframe_tag") == "1M Swing / Local"]
    assert len(unique_1m) == 1
    assert unique_1m[0]["avg_price"] == 24500.0

    unique_2m = [l for l in combined if l.get("timeframe_tag") == "2M Macro"]
    assert len(unique_2m) == 1
    assert unique_2m[0]["avg_price"] == 24800.0


def test_detect_local_support_resistance():
    base_time = IST.localize(datetime(2026, 10, 15, 9, 15))
    records = []
    # 5 days of candles
    for day in range(5):
        day_date = base_time + timedelta(days=day)
        for m in range(75):
            t = day_date + timedelta(minutes=5 * m)
            # Create bounces at 24800
            p = 24800.0 if (m % 15 == 0) else 25000.0 + (m % 5) * 10
            records.append({
                "timestamp": t,
                "open": p,
                "high": p + 2,
                "low": p - 2,
                "close": p,
                "volume": 1000
            })
    df = pd.DataFrame(records).set_index("timestamp")
    local_levels = detect_local_support_resistance(df, major_levels=[], days_back=5, min_bounces=2)
    assert isinstance(local_levels, list)
    for lvl in local_levels:
        assert lvl["color"] == "#cbd5e1"
        assert lvl["is_local"] is True
        assert lvl["type"] == "line"
        assert lvl["bounces"] >= 2


def test_sr_api_endpoint():
    client = TestClient(app)
    resp = client.get("/api/sr-levels?period=1m")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["timeframe"] == "5m"
    assert data["period"] == "1m"
    assert "levels" in data
    assert "levels_1m" in data
    assert "levels_2m" in data
    assert isinstance(data["levels"], list)

    resp2 = client.get("/api/sr-levels?period=2m")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["period"] == "2m"
    assert "count_support" in data2
    assert "count_resistance" in data2
    assert "mode" in data2


def test_few_lines_support_and_resistance_limit():
    """Verifies that S&R calculation strictly limits to max 4 support and max 4 resistance lines."""
    base_time = IST.localize(datetime(2026, 10, 1, 9, 15))
    records = []
    # Generate oscillation around 25000 with multiple pivot levels
    for i in range(200):
        t = base_time + timedelta(minutes=5 * i)
        level_idx = i % 8
        price_target = 24600 + level_idx * 100  # 8 different price levels
        records.append({
            "timestamp": t,
            "open": price_target,
            "high": price_target + 3,
            "low": price_target - 3,
            "close": price_target,
            "volume": 1000
        })
    df = pd.DataFrame(records).set_index("timestamp")

    # Current price in the middle: 25000
    res = detect_support_resistance(
        df,
        swing_window=3,
        line_tolerance=4.0,
        rect_tolerance=12.0,
        line_min_bounces=3,
        current_price=25000.0,
        max_support=4,
        max_resistance=4,
        max_rects=3,
    )

    support_lines = [l for l in res if l.get("is_support")]
    resistance_lines = [l for l in res if not l.get("is_support")]

    assert len(support_lines) <= 4, f"Expected at most 4 supports, got {len(support_lines)}"
    assert len(resistance_lines) <= 4, f"Expected at most 4 resistances, got {len(resistance_lines)}"


def test_sr_rect_min_bounces_and_total_cap():
    """
    Verifies that:
    1. Rectangles require at least 6 bounces (>= 6x).
    2. calculate_sr_periods caps total levels on chart to strictly max_total (default 10).
    """
    base_time = IST.localize(datetime(2026, 9, 1, 9, 15))
    records = []
    for day in range(25):
        day_date = base_time + timedelta(days=day)
        for m in range(75):
            t = day_date + timedelta(minutes=5 * m)
            # Create many oscillating touch points across 12 levels
            p = 24000.0 + (m % 12) * 50
            records.append({
                "timestamp": t,
                "open": p,
                "high": p + 4,
                "low": p - 4,
                "close": p,
                "volume": 1000
            })
    df = pd.DataFrame(records).set_index("timestamp")

    res = calculate_sr_periods(df, current_price=24300.0, max_support=4, max_resistance=4, max_rects=3, rect_min_bounces=6, max_local=4, max_total=10)
    for period_key in ["1m", "2m"]:
        levels = res[period_key]
        assert len(levels) <= 10, f"Expected at most 10 levels on chart for {period_key}, got {len(levels)}"
        rects = [l for l in levels if l.get("type") == "rect"]
        assert len(rects) <= 3, f"Expected at most 3 rectangles, got {len(rects)}"
        for r in rects:
            assert r.get("bounces", 0) >= 6, f"Expected rectangle bounce >= 6, got {r.get('bounces')}"


def test_sr_forward_projection_100_candles():
    """
    Verifies that S&R lines and zones project forward through the current candle + next 100 candles.
    100 candles of 5m = 30,000 seconds.
    """
    base_time = IST.localize(datetime(2026, 10, 1, 9, 15))
    records = []
    for i in range(120):
        t = base_time + timedelta(minutes=5 * i)
        p = 25000.0 if (i % 2 == 0) else 25300.0
        records.append({
            "timestamp": t,
            "open": p,
            "high": p + 3,
            "low": p - 3,
            "close": p,
            "volume": 1000
        })
    df = pd.DataFrame(records).set_index("timestamp")
    last_candle_ts = int(df.index[-1].timestamp())

    # Detect S&R with 100 future candles
    levels = detect_support_resistance(
        df,
        swing_window=3,
        line_tolerance=4.0,
        rect_tolerance=12.0,
        line_min_bounces=3,
        future_candles=100,
    )

    assert len(levels) > 0
    for lvl in levels:
        expected_time2 = last_candle_ts + (100 * 300)
        assert lvl["time2"] == expected_time2, f"Expected time2={expected_time2}, got {lvl['time2']}"


def test_sr_24h_any_time_live_update(tmp_path):
    """
    Verifies that S&R operates 24H any time:
    1. is_within_sr_update_window is True 24/7 (morning, afternoon, night).
    2. Any time code runs or opens, S&R updates according to the latest candles.
    3. Adding new candles triggers live S&R update and replaces old lines.
    """
    from support_resistance import (
        is_within_sr_update_window,
        update_or_get_sr_levels,
        load_sr_cache_from_disk,
    )

    # 1. 24H window check (True at all times)
    dt_morning = IST.localize(datetime(2026, 10, 21, 9, 30))   # 9:30 AM
    dt_afternoon = IST.localize(datetime(2026, 10, 21, 14, 0))  # 2:00 PM
    dt_evening = IST.localize(datetime(2026, 10, 21, 19, 0))    # 7:00 PM
    dt_night = IST.localize(datetime(2026, 10, 21, 23, 30))     # 11:30 PM

    assert is_within_sr_update_window(dt_morning) is True
    assert is_within_sr_update_window(dt_afternoon) is True
    assert is_within_sr_update_window(dt_evening) is True
    assert is_within_sr_update_window(dt_night) is True

    # 2. Initial run creates S&R cache
    test_cache_file = str(tmp_path / "test_24h_sr.json")
    base_time = IST.localize(datetime(2026, 10, 1, 9, 15))
    records_1 = []
    for i in range(100):
        t = base_time + timedelta(minutes=5 * i)
        p = 24500.0 if (i % 2 == 0) else 24800.0
        records_1.append({"timestamp": t, "open": p, "high": p + 2, "low": p - 2, "close": p, "volume": 1000})
    df_1 = pd.DataFrame(records_1).set_index("timestamp")

    res_1 = update_or_get_sr_levels(
        df_5m=df_1,
        current_price=24650.0,
        now_dt=dt_morning,
        future_candles=100,
        filepath=test_cache_file,
    )
    assert res_1["mode"] == "24h_live_updated"
    assert res_1["future_candles"] == 100
    assert os.path.exists(test_cache_file)
    t1_updated = res_1["last_updated_ist"]

    # 3. Simulate new candle arriving (live tick/candle update)
    new_t = base_time + timedelta(minutes=5 * 101)
    records_2 = list(records_1) + [{"timestamp": new_t, "open": 24900.0, "high": 24905.0, "low": 24895.0, "close": 24900.0, "volume": 1500}]
    df_2 = pd.DataFrame(records_2).set_index("timestamp")

    # Call at another time (e.g. night)
    res_2 = update_or_get_sr_levels(
        df_5m=df_2,
        current_price=24900.0,
        now_dt=dt_night,
        future_candles=100,
        filepath=test_cache_file,
    )
    # Detects new candle and updates live!
    assert res_2["mode"] == "24h_live_updated"
    assert res_2["last_candle_count"] == 101
    assert res_2["last_updated_ist"] != t1_updated

    # Verify disk cache is updated with the new lines
    disk_data = load_sr_cache_from_disk(test_cache_file)
    assert disk_data["last_candle_count"] == 101
    assert disk_data["last_updated_ist"] == res_2["last_updated_ist"]


