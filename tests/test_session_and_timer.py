"""
Unit tests for Market Session Status and Candle Countdown Clock UI & Logic.
"""
from pathlib import Path
import re


def test_index_html_has_market_status_and_countdown_clock():
    """Verify that templates/index.html includes all required elements, CSS, and JS."""
    template_path = Path("templates/index.html")
    assert template_path.exists(), "templates/index.html must exist"
    content = template_path.read_text(encoding="utf-8")

    # 1. Market Status Elements & CSS
    assert 'id="market-status-pill"' in content
    assert 'id="market-status-text"' in content
    assert '.market-status-live' in content
    assert '.market-status-pre' in content
    assert '.market-status-closed' in content

    # 2. Candle Countdown Clock Elements & CSS
    assert 'id="candle-timer-pill"' in content
    assert 'id="candle-timer-val"' in content
    assert 'id="candle-timer-tf"' in content
    assert '.candle-timer-pill' in content
    assert '.candle-timer-pill.urgent' in content

    # 3. JS Functions & Clock in Sub-bar
    assert 'function getISTDetails()' in content
    assert 'function updateMarketStatusAndCandleTimer()' in content
    assert 'id="sub-ist-clock"' in content
    assert 'setInterval(updateMarketStatusAndCandleTimer, 1000)' in content


def calculate_nse_session(hour: int, minute: int, second: int, is_weekend: bool):
    """Mirror test of the IST Market Session determination logic."""
    total_seconds = hour * 3600 + minute * 60 + second
    if is_weekend:
        return "closed_weekend"
    # Pre-market: 09:00:00 to 09:14:59 (32400 to 33299)
    if 32400 <= total_seconds < 33300:
        return "pre_market"
    # Live market: 09:15:00 to 15:30:00 (33300 to 55800)
    if 33300 <= total_seconds < 55800:
        return "live_market"
    return "closed"


def calculate_candle_rem_sec(tf: str, hour: int, minute: int, second: int):
    """Mirror test of candle countdown remaining seconds calculation."""
    total_seconds = hour * 3600 + minute * 60 + second
    if tf == "5m":
        sec_in = (minute % 5) * 60 + second
        rem = 300 - sec_in
        return 300 if (rem <= 0 or rem > 300) else rem
    elif tf == "15m":
        sec_in = (minute % 15) * 60 + second
        rem = 900 - sec_in
        return 900 if (rem <= 0 or rem > 900) else rem
    elif tf == "1h":
        if total_seconds >= (15 * 3600 + 15 * 60):
            rem = (15 * 3600 + 30 * 60) - total_seconds
        else:
            min_to_next_15 = (15 - minute) if minute < 15 else (75 - minute)
            rem = min_to_next_15 * 60 - second
        return 3600 if rem <= 0 else rem
    elif tf == "1d":
        rem = (15 * 3600 + 30 * 60) - total_seconds
        return max(0, rem)
    raise ValueError(f"Unknown timeframe {tf}")


def test_nse_market_sessions():
    """Verify session transitions throughout the day."""
    # Weekend
    assert calculate_nse_session(10, 30, 0, is_weekend=True) == "closed_weekend"
    assert calculate_nse_session(14, 0, 0, is_weekend=True) == "closed_weekend"

    # Weekday Early Morning
    assert calculate_nse_session(8, 59, 59, is_weekend=False) == "closed"

    # Pre-Market: 09:00:00 to 09:14:59
    assert calculate_nse_session(9, 0, 0, is_weekend=False) == "pre_market"
    assert calculate_nse_session(9, 14, 59, is_weekend=False) == "pre_market"

    # Live Market: 09:15:00 to 15:30:00
    assert calculate_nse_session(9, 15, 0, is_weekend=False) == "live_market"
    assert calculate_nse_session(11, 45, 30, is_weekend=False) == "live_market"
    assert calculate_nse_session(15, 29, 59, is_weekend=False) == "live_market"

    # Post-Market / EOD: 15:30:00 onwards
    assert calculate_nse_session(15, 30, 0, is_weekend=False) == "closed"
    assert calculate_nse_session(17, 30, 0, is_weekend=False) == "closed"
    assert calculate_nse_session(23, 0, 0, is_weekend=False) == "closed"


def test_candle_countdown_accuracy():
    """Verify countdown calculation across all timeframes."""
    # At 09:17:15 (2m 15s into current 5m candle):
    # 5m: Remaining = 300 - 135 = 165s (02:45)
    rem_5m = calculate_candle_rem_sec("5m", 9, 17, 15)
    assert rem_5m == 165
    assert f"{rem_5m // 60:02d}:{rem_5m % 60:02d}" == "02:45"

    # 15m: Remaining at 09:17:15 (2m 15s into current 15m candle):
    # Remaining = 900 - 135 = 765s (12:45)
    rem_15m = calculate_candle_rem_sec("15m", 9, 17, 15)
    assert rem_15m == 765
    assert f"{rem_15m // 60:02d}:{rem_15m % 60:02d}" == "12:45"

    # 1h: At 09:17:15, candle started at 09:15:00, next closes at 10:15:00:
    # (75 - 17) * 60 - 15 = 58 * 60 - 15 = 3480 - 15 = 3465s (57:45)
    rem_1h = calculate_candle_rem_sec("1h", 9, 17, 15)
    assert rem_1h == 3465
    assert f"{rem_1h // 60:02d}:{rem_1h % 60:02d}" == "57:45"

    # 1d: At 09:17:15, closes at 15:30:00 (55800 total seconds)
    # Total current sec = 9*3600 + 17*60 + 15 = 32400 + 1020 + 15 = 33435
    # Rem = 55800 - 33435 = 22365s (06h 12m 45s)
    rem_1d = calculate_candle_rem_sec("1d", 9, 17, 15)
    assert rem_1d == 22365
    h = rem_1d // 3600
    m = (rem_1d % 3600) // 60
    s = rem_1d % 60
    assert f"{h:02d}:{m:02d}:{s:02d}" == "06:12:45"


def test_index_html_has_mtf_ribbon_and_signal_history_modal():
    """Verify that templates/index.html includes MTF ribbon and structured Signal History modal."""
    template_path = Path("templates/index.html")
    assert template_path.exists()
    content = template_path.read_text(encoding="utf-8")

    # MTF ribbon elements
    assert 'id="mtf-ribbon"' in content
    assert 'id="mtf-pill-5m"' in content
    assert 'id="mtf-pill-15m"' in content
    assert 'id="mtf-pill-1h"' in content
    assert 'id="mtf-pill-1d"' in content
    assert 'id="mtf-confluence-badge"' in content

    # Signal History modal & tabs
    assert 'id="signal-history-modal"' in content
    assert 'id="tab-btn-original"' in content
    assert 'id="tab-btn-sr"' in content
    assert 'id="sr-sub-tabs"' in content
    assert 'id="sub-pill-breakout"' in content
    assert 'id="sub-pill-reversal"' in content
    assert 'function openSignalHistoryModal()' in content
    assert 'function switchHistoryTab(' in content
    assert 'function renderSignalHistory()' in content


def test_mtf_trend_matrix_computation():
    """Verify MTF matrix trend computation."""
    import pandas as pd
    import numpy as np
    from config import StrategyConfig
    from background_engine import BackgroundTradingEngine

    engine = BackgroundTradingEngine.get_instance()
    # Create synthetic DataFrame
    dates = pd.date_range("2026-10-23 09:15", periods=50, freq="5min")
    prices = np.linspace(22400, 22600, 50)
    df = pd.DataFrame({
        "open": prices - 2,
        "high": prices + 5,
        "low": prices - 5,
        "close": prices,
        "volume": 1000,
    }, index=dates)

    mtf = engine.compute_mtf_trend_matrix(df)
    assert "timeframes" in mtf
    assert "5m" in mtf["timeframes"]
    assert mtf["total"] >= 1
    assert "confluence" in mtf
    assert mtf["badge_class"] in ("bullish", "bearish", "neutral")

