"""
Coordinates state updates between aggregator, strategy, Telegram notifications, and dashboard UI.
"""
from datetime import datetime
import threading
import logging
from typing import Optional, Set
import pandas as pd
from indicators import compute_all_indicators
from engine.strategy import VWAPDualEMAStrategy, StrategySignalState
from telegram_notifier import TelegramNotifier

logger = logging.getLogger(__name__)


class LiveSignalManager:
    def __init__(self, config, telegram_notifier: Optional[TelegramNotifier] = None):
        self.cfg = config
        self.strategy = VWAPDualEMAStrategy(config)
        self.current_state = StrategySignalState(signal=0, signal_name="NONE", in_position=False)
        self.last_candle_row: Optional[pd.Series] = None
        self.signal_history = []
        self.telegram_notifier = telegram_notifier
        self.alerted_keys: Set[str] = set()
        self.last_eod_alert_date: Optional[str] = None
        self.lock = threading.Lock()

    def set_telegram_notifier(self, notifier: TelegramNotifier):
        """Allows updating or reconfiguring Telegram notifier dynamically."""
        with self.lock:
            self.telegram_notifier = notifier

    def notify_signal(self, candle_ts, signal_name: str, price: float,
                      target: float = None, stop: float = None,
                      z_score: float = None, slope: float = None,
                      pnl_pct: float = None, reason: str = ""):
        """Sends Telegram notification for a confirmed signal if not already sent."""
        key = f"{candle_ts}_{signal_name}_{price:.2f}"
        if key in self.alerted_keys:
            return

        self.alerted_keys.add(key)
        if self.telegram_notifier and self.telegram_notifier.is_configured:
            threading.Thread(
                target=self.telegram_notifier.send_signal_alert,
                kwargs={
                    "signal_name": signal_name,
                    "price": price,
                    "target": target,
                    "stop": stop,
                    "z_score": z_score,
                    "slope": slope,
                    "pnl_pct": pnl_pct,
                    "reason": reason,
                    "candle_time": candle_ts if isinstance(candle_ts, datetime) else None,
                    "symbol": "NIFTY 50"
                },
                daemon=True
            ).start()
            logger.info("Dispatched Telegram alert for %s at ₹%.2f (Key: %s)", signal_name, price, key)

    def on_candle_closed(self, closed_series: pd.Series, full_df: pd.DataFrame):
        """Called at every 5-minute candle boundary to evaluate strategy rules."""
        with self.lock:
            df_ind = compute_all_indicators(full_df, self.cfg)
            if len(df_ind) < 2:
                return

            last_closed = df_ind.iloc[-1]
            self.last_candle_row = last_closed
            state = self.strategy.update(last_closed)

            ts = last_closed.name if isinstance(last_closed.name, (pd.Timestamp, datetime)) else datetime.now()

            if state.signal in (1, -1) or state.exit_reason:
                self.signal_history.append({
                    "timestamp": ts,
                    "signal": state.signal_name,
                    "price": last_closed['close'],
                    "entry_price": state.entry_price,
                    "reason": state.exit_reason or state.signal_name
                })

                # Trigger Telegram notification for BUY (1) or SELL (-1)
                if state.signal in (1, -1):
                    self.notify_signal(
                        candle_ts=ts,
                        signal_name=state.signal_name,
                        price=float(last_closed['close']),
                        target=state.target_price,
                        stop=state.stop_loss,
                        z_score=float(last_closed.get('z', 0.0)),
                        slope=float(last_closed.get('slope', 0.0)),
                        pnl_pct=state.live_pnl_pct,
                        reason=state.exit_reason or state.signal_name
                    )

            self.current_state = state

            # Check if 3:10 PM EOD square-off alert should be dispatched
            self.check_eod_alert(float(last_closed['close']), ts)

    def check_eod_alert(self, price: float, current_dt: Optional[datetime] = None) -> bool:
        """Dispatches daily 3:10 PM EOD reminder to exit all trades (once per day)."""
        import pytz
        ist = pytz.timezone("Asia/Kolkata")
        if current_dt is None:
            current_dt = datetime.now(ist)
        elif getattr(current_dt, "tzinfo", None) is not None:
            current_dt = current_dt.astimezone(ist)
        else:
            current_dt = ist.localize(current_dt)

        today_str = current_dt.strftime("%Y-%m-%d")
        # Check if 15:10 or later
        if (current_dt.hour == 15 and current_dt.minute >= 10) or current_dt.hour > 15:
            if self.last_eod_alert_date != today_str:
                self.last_eod_alert_date = today_str
                if self.telegram_notifier and self.telegram_notifier.is_configured:
                    state = self.current_state
                    threading.Thread(
                        target=self.telegram_notifier.send_eod_alert,
                        kwargs={
                            "price": price,
                            "in_position": state.in_position,
                            "entry_price": state.entry_price,
                            "pnl_pct": state.live_pnl_pct,
                            "alert_time": current_dt,
                            "symbol": "NIFTY 50"
                        },
                        daemon=True
                    ).start()
                    logger.info("Dispatched 3:10 PM EOD Exit alert for %s", today_str)
                    return True
        return False


    def get_live_display(self, current_ltp: float) -> StrategySignalState:
        """Updates live unrealized P&L on incoming ticks without modifying confirmed signal."""
        with self.lock:
            state = self.current_state
            live_pnl = None
            if state.in_position and state.entry_price and state.entry_price > 0:
                if state.position_type == "LONG":
                    live_pnl = ((current_ltp - state.entry_price) / state.entry_price) * 100.0
                elif state.position_type == "SHORT":
                    live_pnl = ((state.entry_price - current_ltp) / state.entry_price) * 100.0

            return StrategySignalState(
                signal=state.signal,
                signal_name=state.signal_name,
                entry_price=state.entry_price,
                stop_loss=state.stop_loss,
                target_price=state.target_price,
                live_pnl_pct=live_pnl,
                in_position=state.in_position,
                position_type=state.position_type,
                exit_reason=state.exit_reason,
                z_score=state.z_score,
                slope=state.slope
            )
