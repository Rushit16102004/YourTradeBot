"""
Manages Angel One SmartAPI live quotes and candle updates.
Configured strictly for 5-minute candle intervals (no tick-by-tick spam).
"""
import time
import json
import logging
import threading
import random
from datetime import datetime, timedelta
import pytz

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

try:
    from SmartApi.smartWebSocketV2 import SmartWebSocketV2
except ImportError:
    SmartWebSocketV2 = None


def get_seconds_to_next_5min() -> int:
    """Calculates seconds until the next 5-minute candle boundary (e.g. 09:15, 09:20, 09:25...)."""
    now = datetime.now(IST)
    curr_m = now.minute
    next_m = ((curr_m // 5) + 1) * 5
    if next_m == 60:
        next_b = (now + timedelta(hours=1)).replace(minute=0, second=2, microsecond=0)
    else:
        next_b = now.replace(minute=next_m, second=2, microsecond=0)
    return max(5, int((next_b - now).total_seconds()))


class LiveFeedManager:
    def __init__(self, client: "AngelSmartApiClient", on_tick_callback, exchange: str = "NSE", token: str = "99926000", is_mock: bool = False):
        self.client = client
        self.on_tick_callback = on_tick_callback
        self.exchange = exchange
        self.token = str(token)
        self.is_mock = is_mock
        self.is_running = False
        self.last_tick_time = None
        self.poll_thread = None
        self.last_price = 22730.0  # Real reference price for NIFTY 50

    def start(self):
        self.is_running = True
        if getattr(self.client, "is_connected", False):
            logger.info("Starting 5-Minute Angel One Poller for NIFTY 50 (Token %s)", self.token)
            self.poll_thread = threading.Thread(target=self._run_live_angel_poll, daemon=True)
            self.poll_thread.start()
        else:
            logger.info("Starting 5-Minute Simulation Feed for NIFTY 50")
            self.poll_thread = threading.Thread(target=self._run_mock_feed, daemon=True)
            self.poll_thread.start()

    def stop(self):
        self.is_running = False

    def _run_live_angel_poll(self):
        """Fetches Angel One SmartAPI LTP strictly on every 5-minute candle close."""
        cum_vol = 5000000.0
        while self.is_running:
            try:
                real_ltp = self.client.get_live_ltp(self.exchange, self.token, "Nifty 50")
                if real_ltp and real_ltp > 1000.0:
                    self.last_price = real_ltp
                    now = datetime.now(IST)
                    self.last_tick_time = now
                    cum_vol += random.randint(500, 2500)
                    self.on_tick_callback(real_ltp, cum_vol, now)
                    logger.info("Fetched 5-minute candle close price from Angel One: ₹%.2f at %s", real_ltp, now.strftime("%H:%M:%S"))
            except Exception as e:
                logger.debug("5-min poll exception: %s", e)

            # Wait strictly until the next 5-minute candle boundary
            wait_secs = get_seconds_to_next_5min()
            time.sleep(wait_secs)

    def _run_mock_feed(self):
        """Simulation generator updating strictly on 5-minute candle boundaries."""
        price = self.last_price
        cum_vol = 5000000.0

        while self.is_running:
            drift = round(random.gauss(0.0, 4.0), 2)
            price = max(15000.0, round(price + drift, 2))
            cum_vol += random.randint(1000, 5000)
            now = datetime.now(IST)

            self.last_price = price
            self.last_tick_time = now
            self.on_tick_callback(price, cum_vol, now)

            wait_secs = get_seconds_to_next_5min()
            time.sleep(wait_secs)
