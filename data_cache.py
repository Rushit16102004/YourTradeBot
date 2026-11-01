"""
Compatibility shim for data_cache.
Redirects to the Temp Storage Department in `temp_storage/cache_manager.py`.
"""
from temp_storage.cache_manager import CandleCacheManager, CACHE_DIR, IST

__all__ = ["CandleCacheManager", "CACHE_DIR", "IST"]
