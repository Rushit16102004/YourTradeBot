"""
Tests for 5-minute candle aggregation, interval boundaries, and cumulative volume.
"""
from datetime import datetime
import time
import pytz
import pandas as pd
from candle_aggregator import FiveMinuteCandleAggregator

IST = pytz.timezone("Asia/Kolkata")


def test_candle_bucket_boundary():
    agg = FiveMinuteCandleAggregator()
    dt1 = IST.localize(datetime(2026, 10, 14, 9, 16, 23))
    bucket = agg._get_candle_bucket_start(dt1)
    assert bucket.minute == 15
    assert bucket.second == 0

    dt2 = IST.localize(datetime(2026, 10, 14, 9, 20, 0))
    bucket2 = agg._get_candle_bucket_start(dt2)
    assert bucket2.minute == 20


def test_cumulative_volume_aggregation():
    closed = []
    agg = FiveMinuteCandleAggregator(on_candle_close=lambda s: closed.append(s))

    # Ticks in 09:15 bucket
    t1 = IST.localize(datetime(2026, 10, 14, 9, 15, 10))
    agg.on_tick(ltp=100.0, cum_vol=1000, tick_dt=t1)

    t2 = IST.localize(datetime(2026, 10, 14, 9, 17, 30))
    agg.on_tick(ltp=105.0, cum_vol=1500, tick_dt=t2)

    # Next bucket (09:20) triggers closing of 09:15 bucket
    t3 = IST.localize(datetime(2026, 10, 14, 9, 20, 2))
    agg.on_tick(ltp=103.0, cum_vol=1800, tick_dt=t3)

    time.sleep(0.1)

    assert len(closed) == 1
    assert closed[0]["open"] == 100.0
    assert closed[0]["high"] == 105.0
    assert closed[0]["low"] == 100.0
    assert closed[0]["close"] == 105.0
    assert closed[0]["volume"] == 500.0  # 1500 - 1000


def test_supported_timeframes_5m_15m_1h_1d():
    from background_engine import BackgroundTradingEngine
    engine = BackgroundTradingEngine.get_instance()
    for tf in ["5m", "15m", "1h", "1d"]:
        snap = engine.get_snapshot(timeframe=tf)
        assert "df" in snap
        df = snap["df"]
        assert not df.empty, f"Expected non-empty candles for {tf}"
        assert "close" in df.columns
        assert "vwap" in df.columns
