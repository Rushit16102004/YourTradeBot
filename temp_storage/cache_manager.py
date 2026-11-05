"""
temp_storage/cache_manager.py - High-performance In-Memory Cache Manager with disk persistence.
Part of the Temp Storage Department.
1st Priority: RAM Cache Memory (instant tick-by-tick access with zero lag)
Fallback: Local CSV storage in `temp_storage/` directory (with data_cache/ fallback).
Supports 4 months of NIFTY 50 candles across 1m, 2m, 3m, 5m, 15m, 1h, and 1d timeframes.
"""
from __future__ import annotations

import logging
import os
import threading
from datetime import datetime
from typing import Dict, Optional, Tuple

import pandas as pd
import pytz

logger = logging.getLogger("TempStorageCache")
IST = pytz.timezone("Asia/Kolkata")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BASE_DIR)
CACHE_DIR = BASE_DIR
LEGACY_CACHE_DIR = os.path.join(PROJECT_ROOT, "data_cache")
os.makedirs(CACHE_DIR, exist_ok=True)


class CandleCacheManager:
    """Singleton Memory Cache Manager."""

    _instance: Optional[CandleCacheManager] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> CandleCacheManager:
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def __init__(self):
        # Primary In-Memory Cache: Dict[(symbol, timeframe), pd.DataFrame]
        self._memory_cache: Dict[Tuple[str, str], pd.DataFrame] = {}
        self._cache_lock = threading.Lock()
        self._last_tick_time: Optional[datetime] = None

    def _csv_path(self, symbol: str, timeframe: str) -> str:
        clean_sym = symbol.replace(" ", "_").replace("^", "").lower()
        clean_tf = timeframe.replace(" ", "").lower()
        primary_4mo = os.path.join(CACHE_DIR, f"{clean_sym}_{clean_tf}_4mo.csv")
        legacy_4mo = os.path.join(LEGACY_CACHE_DIR, f"{clean_sym}_{clean_tf}_4mo.csv")
        if os.path.exists(primary_4mo):
            return primary_4mo
        if os.path.exists(legacy_4mo):
            return legacy_4mo

        # Fallback to 2mo if 4mo does not yet exist
        primary_2mo = os.path.join(CACHE_DIR, f"{clean_sym}_{clean_tf}_2mo.csv")
        legacy_2mo = os.path.join(LEGACY_CACHE_DIR, f"{clean_sym}_{clean_tf}_2mo.csv")
        if os.path.exists(primary_2mo):
            return primary_2mo
        if os.path.exists(legacy_2mo):
            return legacy_2mo
        return primary_4mo

    def get_candles(self, symbol: str = "NIFTY 50", timeframe: str = "5m") -> Optional[pd.DataFrame]:
        """
        Retrieves 4-month candles.
        1st Priority: In-Memory RAM Cache.
        2nd Priority: Local CSV on disk in temp_storage.
        """
        key = (symbol, timeframe.lower())

        with self._cache_lock:
            # 1st Priority: Check RAM Cache Memory
            if key in self._memory_cache:
                df = self._memory_cache[key]
                if df is not None and not df.empty:
                    return df.copy()

        # 2nd Priority: Fallback to Disk CSV
        csv_file = self._csv_path(symbol, timeframe)
        if os.path.exists(csv_file):
            try:
                df_csv = pd.read_csv(csv_file, parse_dates=["timestamp"], index_col="timestamp")
                if df_csv.index.tz is None:
                    df_csv.index = df_csv.index.tz_localize(IST)
                else:
                    df_csv.index = df_csv.index.tz_convert(IST)

                # Store in RAM cache for subsequent instant access
                with self._cache_lock:
                    self._memory_cache[key] = df_csv.copy()
                logger.info("Loaded %d candles from CSV fallback into RAM Cache [%s, %s]", len(df_csv), symbol, timeframe)
                return df_csv.copy()
            except Exception as e:
                logger.warning("Error reading CSV cache %s: %s", csv_file, e)

        return None

    def set_candles(self, df: pd.DataFrame, symbol: str = "NIFTY 50", timeframe: str = "5m", persist_csv: bool = True):
        """Stores candles in RAM Cache Memory (1st Priority) and asynchronously persists to CSV in temp_storage."""
        if df is None or df.empty:
            return

        key = (symbol, timeframe.lower())
        df_clean = df.copy()

        # Ensure index is datetime with IST timezone
        if not isinstance(df_clean.index, pd.DatetimeIndex) and "timestamp" in df_clean.columns:
            df_clean["timestamp"] = pd.to_datetime(df_clean["timestamp"])
            df_clean.set_index("timestamp", inplace=True)

        if df_clean.index.tz is None:
            df_clean.index = df_clean.index.tz_localize(IST)
        else:
            df_clean.index = df_clean.index.tz_convert(IST)

        # 1st Priority: Instant Update to In-Memory RAM Cache
        with self._cache_lock:
            self._memory_cache[key] = df_clean.copy()

        # 2nd Priority: Non-blocking Disk CSV Save
        if persist_csv:
            def _async_save():
                try:
                    target_file = os.path.join(CACHE_DIR, f"{symbol.replace(' ', '_').replace('^', '').lower()}_{timeframe.replace(' ', '').lower()}_4mo.csv")
                    df_clean.to_csv(target_file, index=True)
                    logger.debug("Persisted %d candles to %s", len(df_clean), target_file)
                except Exception as e:
                    logger.warning("Error persisting candles to CSV: %s", e)

            threading.Thread(target=_async_save, daemon=True).start()

    def update_tick(self, symbol: str = "NIFTY 50", price: float = 0.0, volume: float = 0.0, tick_time: Optional[datetime] = None):
        """High-frequency real-time tick update directly into In-Memory RAM Cache with auto-forming new 5m candle."""
        # Auto-detect if caller passed (price, volume, symbol)
        if isinstance(symbol, (int, float)) and isinstance(volume, (int, float)) and isinstance(price, str):
            symbol, price = price, float(symbol)
        elif isinstance(symbol, (int, float)):
            price = float(symbol)
            symbol = "NIFTY 50"

        if tick_time is None:
            tick_time = datetime.now(IST)
        elif tick_time.tzinfo is None:
            tick_time = tick_time.replace(tzinfo=IST)

        self._last_tick_time = tick_time
        key_5m = (symbol, "5m")

        with self._cache_lock:
            if key_5m in self._memory_cache:
                df = self._memory_cache[key_5m]
                if df is not None and not df.empty:
                    last_idx = df.index[-1]
                    curr_bucket = tick_time.replace(
                        minute=(tick_time.minute // 5) * 5,
                        second=0,
                        microsecond=0,
                    )
                    last_ts = pd.to_datetime(last_idx)
                    if last_ts.tzinfo is None:
                        curr_bucket_cmp = curr_bucket.replace(tzinfo=None)
                    else:
                        curr_bucket_cmp = curr_bucket

                    if curr_bucket_cmp > last_ts:
                        # Append new forming 5-minute candle
                        new_row = pd.Series({
                            "open": price,
                            "high": price,
                            "low": price,
                            "close": price,
                            "volume": volume if volume > 0 else 0.0,
                        }, name=curr_bucket_cmp)
                        df.loc[curr_bucket_cmp] = new_row
                    else:
                        df.at[last_idx, "close"] = price
                        if price > df.at[last_idx, "high"]:
                            df.at[last_idx, "high"] = price
                        if price < df.at[last_idx, "low"]:
                            df.at[last_idx, "low"] = price
                        if volume > 0 and "volume" in df.columns:
                            df.at[last_idx, "volume"] = df.at[last_idx, "volume"] + volume
                    self._memory_cache[key_5m] = df

    def get_last_tick_time(self) -> Optional[datetime]:
        return self._last_tick_time

    def resample_timeframe(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Resamples 5-minute base candles to 15m, 30m, 1h, and 1d timeframes.
        OHLCV aggregation:
        - open: first
        - high: max
        - low: min
        - close: last
        - volume: sum
        """
        if df is None or df.empty:
            return df

        tf = str(timeframe).lower().strip()
        if tf in ("5m", "5min"):
            return df.copy()

        rule_map = {
            "1m": "1min",
            "2m": "2min",
            "3m": "3min",
            "15m": "15min",
            "15min": "15min",
            "30m": "30min",
            "1h": "1h",
            "60m": "1h",
            "1d": "1D",
            "d": "1D",
        }
        rule = rule_map.get(tf, "15min")

        agg_rules = {
            "open": "first",
            "high": "max",
            "low": "min",
            "close": "last",
        }
        if "volume" in df.columns:
            agg_rules["volume"] = "sum"

        try:
            res = df.resample(rule, closed="left", label="left").agg(agg_rules).dropna(subset=["close"])
            return res
        except Exception as e:
            logger.warning("Error resampling timeframe %s: %s", timeframe, e)
            return df.copy()

    def clear(self):
        with self._cache_lock:
            self._memory_cache.clear()
            self._last_tick_time = None
