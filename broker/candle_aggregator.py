"""
Aggregates live market ticks into 5-minute candles in Asia/Kolkata timezone.
"""
from datetime import datetime
import threading
from typing import Callable, List, Optional
import pandas as pd
import pytz

IST = pytz.timezone("Asia/Kolkata")


class FiveMinuteCandleAggregator:
    def __init__(self, on_candle_close: Optional[Callable[[pd.Series], None]] = None):
        self.on_candle_close = on_candle_close
        self.lock = threading.Lock()
        self.history: List[dict] = []
        
        # Current forming candle state
        self.current_bucket_start: Optional[datetime] = None
        self.open_p: Optional[float] = None
        self.high_p: Optional[float] = None
        self.low_p: Optional[float] = None
        self.close_p: Optional[float] = None
        self.candle_vol: float = 0.0
        self.last_cum_volume: Optional[float] = None
        self.last_tick_time: Optional[datetime] = None

    def _get_candle_bucket_start(self, dt: datetime) -> datetime:
        """Rounds down datetime to the nearest 5-minute bucket."""
        minute = (dt.minute // 5) * 5
        return dt.replace(minute=minute, second=0, microsecond=0)

    def seed_candles(self, df_seed: pd.DataFrame):
        """Initializes historical candles so indicators are immediately calculated."""
        with self.lock:
            self.history.clear()
            for idx, row in df_seed.iterrows():
                ts = idx if isinstance(idx, pd.Timestamp) else row.get("timestamp")
                pdt = pd.to_datetime(ts)
                if pdt.tzinfo is None:
                    pdt = pdt.tz_localize(IST)
                else:
                    pdt = pdt.tz_convert(IST)
                self.history.append({
                    "timestamp": pdt,
                    "open": float(row["open"]),
                    "high": float(row["high"]),
                    "low": float(row["low"]),
                    "close": float(row["close"]),
                    "volume": float(row["volume"]),
                })

    def on_tick(self, ltp: float, cum_vol: float, tick_dt: datetime):
        """
        Processes incoming tick from Angel One WebSocket.
        Note: SmartAPI sends cumulative volume for the trading day.
        Candle volume is the difference in cumulative volume.
        """
        if tick_dt.tzinfo is None:
            tick_dt = IST.localize(tick_dt)
        else:
            tick_dt = tick_dt.astimezone(IST)

        bucket_start = self._get_candle_bucket_start(tick_dt)

        with self.lock:
            self.last_tick_time = tick_dt

            # Check if previous candle bucket ended and finalize it
            if self.current_bucket_start is not None and bucket_start > self.current_bucket_start:
                closed_candle = {
                    "timestamp": self.current_bucket_start,
                    "open": self.open_p,
                    "high": self.high_p,
                    "low": self.low_p,
                    "close": self.close_p,
                    "volume": max(0.0, self.candle_vol),
                }
                self.history.append(closed_candle)

                # Notify listener
                if self.on_candle_close:
                    s = pd.Series(closed_candle)
                    threading.Thread(target=self.on_candle_close, args=(s,), daemon=True).start()

                # Reset forming candle for new bucket
                self.current_bucket_start = bucket_start
                self.open_p = ltp
                self.high_p = ltp
                self.low_p = ltp
                self.close_p = ltp
                self.candle_vol = 0.0
                self.last_cum_volume = cum_vol

            elif self.current_bucket_start is None:
                # First tick received
                self.current_bucket_start = bucket_start
                self.open_p = ltp
                self.high_p = ltp
                self.low_p = ltp
                self.close_p = ltp
                self.candle_vol = 0.0
                self.last_cum_volume = cum_vol
            else:
                # Update current forming candle
                self.high_p = max(self.high_p, ltp)
                self.low_p = min(self.low_p, ltp)
                self.close_p = ltp

                if self.last_cum_volume is not None and cum_vol >= self.last_cum_volume:
                    delta_vol = cum_vol - self.last_cum_volume
                    self.candle_vol += delta_vol
                self.last_cum_volume = cum_vol

    def get_dataframe(self, include_forming: bool = True) -> pd.DataFrame:
        """Returns historical DataFrame including the forming candle."""
        with self.lock:
            rows = list(self.history)
            if include_forming and self.current_bucket_start is not None:
                rows.append({
                    "timestamp": self.current_bucket_start,
                    "open": self.open_p,
                    "high": self.high_p,
                    "low": self.low_p,
                    "close": self.close_p,
                    "volume": max(0.0, self.candle_vol),
                })

        if not rows:
            return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])

        df = pd.DataFrame(rows)
        ts_list = []
        for t in df["timestamp"]:
            pdt = pd.to_datetime(t)
            if pdt.tzinfo is None:
                pdt = pdt.tz_localize(IST)
            else:
                pdt = pdt.tz_convert(IST)
            ts_list.append(pdt)
        df["timestamp"] = ts_list
        df.set_index("timestamp", inplace=True)
        df.sort_index(inplace=True)
        return df


# Backward compatibility alias
CandleAggregator = FiveMinuteCandleAggregator
