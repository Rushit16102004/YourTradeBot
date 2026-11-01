"""
Indicators Department module for NIFTY 50 Live Trading Terminal.
Provides all indicator mathematical formulas, session VWAP with SD bands,
24H live support & resistance level detection, zone metrics, and breakout engines.
"""
from indicators.indicators import (
    calculate_sma,
    calculate_stdev,
    calculate_z_score,
    calculate_linreg_slope,
    calculate_session_vwap_with_bands,
    compute_all_indicators,
)
from indicators.support_resistance import (
    detect_support_resistance,
    detect_local_support_resistance,
    combine_sr_levels,
    calculate_sr_periods,
    update_or_get_sr_levels,
    load_sr_cache_from_disk,
    save_sr_cache_to_disk,
    is_within_sr_update_window,
)
from indicators.sr_breakout_engine import (
    evaluate_sr_breakout,
    evaluate_sr_reversal,
)

__all__ = [
    "calculate_sma",
    "calculate_stdev",
    "calculate_z_score",
    "calculate_linreg_slope",
    "calculate_session_vwap_with_bands",
    "compute_all_indicators",
    "detect_support_resistance",
    "detect_local_support_resistance",
    "combine_sr_levels",
    "calculate_sr_periods",
    "update_or_get_sr_levels",
    "load_sr_cache_from_disk",
    "save_sr_cache_to_disk",
    "is_within_sr_update_window",
    "evaluate_sr_breakout",
    "evaluate_sr_reversal",
]
