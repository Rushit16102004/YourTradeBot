"""
rate_limiter.py - Lightweight In-Memory Sliding Window Rate Limiter
Prevents AI Copilot spam, protects Gemini API quotas, and ensures fair resource distribution.
"""
from __future__ import annotations

import time
import threading
from typing import Dict, List, Tuple


class SlidingWindowRateLimiter:
    def __init__(self, max_requests: int = 8, window_seconds: float = 60.0, cooldown_seconds: float = 6.0):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.cooldown_seconds = cooldown_seconds
        self.requests: Dict[str, List[float]] = {}
        self.last_request_time: Dict[str, float] = {}
        self.lock = threading.Lock()

    def check_rate_limit(self, user_key: str) -> Tuple[bool, float, str]:
        """
        Checks if a user request is allowed under rate limits.
        Returns: (allowed: bool, wait_seconds: float, error_message: str)
        """
        now = time.time()
        with self.lock:
            # 1. Check cooldown between consecutive requests
            last_time = self.last_request_time.get(user_key, 0.0)
            elapsed = now - last_time
            if elapsed < self.cooldown_seconds:
                wait_sec = round(self.cooldown_seconds - elapsed, 1)
                return False, wait_sec, f"Please wait {wait_sec}s before asking another question."

            # 2. Check sliding window limit
            user_history = self.requests.get(user_key, [])
            # Evict timestamps outside window
            user_history = [t for t in user_history if now - t < self.window_seconds]

            if len(user_history) >= self.max_requests:
                oldest = user_history[0]
                wait_sec = round(self.window_seconds - (now - oldest), 1)
                wait_sec = max(wait_sec, 1.0)
                return False, wait_sec, f"Rate limit reached ({self.max_requests} questions/min). Please wait {wait_sec}s."

            # Record this request
            user_history.append(now)
            self.requests[user_key] = user_history
            self.last_request_time[user_key] = now

            # Periodic cleanup of inactive users
            if len(self.requests) > 200:
                stale_cutoff = now - (self.window_seconds * 2)
                self.requests = {k: v for k, v in self.requests.items() if v and v[-1] > stale_cutoff}
                self.last_request_time = {k: v for k, v in self.last_request_time.items() if v > stale_cutoff}

            return True, 0.0, ""


# Global singleton rate limiter for Copilot: Max 8 requests/min, 6.0s cooldown between prompts
copilot_rate_limiter = SlidingWindowRateLimiter(max_requests=8, window_seconds=60.0, cooldown_seconds=6.0)
