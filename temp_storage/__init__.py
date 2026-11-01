"""
Temp Storage Department module for NIFTY 50 Live Trading Terminal.
Provides centralized path management for cached files, candle CSVs,
S&R levels, temporary drawing states, and memory cache managers.
"""
import os
from pathlib import Path
from temp_storage.cache_manager import CandleCacheManager

TEMP_STORAGE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = TEMP_STORAGE_DIR.parent

DRAWINGS_CACHE_FILE = TEMP_STORAGE_DIR / "drawings.json"
SR_LEVELS_FILE = TEMP_STORAGE_DIR / "sr_levels.json"
CANDLE_5M_CSV = TEMP_STORAGE_DIR / "nifty_50_5m_2mo.csv"

# Fallback paths
LEGACY_DATA_CACHE_DIR = PROJECT_ROOT / "data_cache"

__all__ = [
    "CandleCacheManager",
    "TEMP_STORAGE_DIR",
    "DRAWINGS_CACHE_FILE",
    "SR_LEVELS_FILE",
    "CANDLE_5M_CSV",
    "LEGACY_DATA_CACHE_DIR",
]
