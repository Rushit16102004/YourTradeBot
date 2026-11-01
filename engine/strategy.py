"""
Strategy state machine and signal generation rules for ZFTF (Z-Score Trend Following).
Exact replication of the user's Pine Script logic.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Tuple
import pandas as pd
import pytz

IST = pytz.timezone("Asia/Kolkata")



@dataclass
class StrategySignalState:
    signal: int                   # 1: BUY, -1: SELL, 2: HOLD, 0: NONE
    signal_name: str              # BUY, SELL, HOLD, NONE
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    target_price: Optional[float] = None
    live_pnl_pct: Optional[float] = None
    in_position: bool = False
    position_type: str = "FLAT"   # LONG, FLAT
    exit_reason: str = ""
    z_score: float = 0.0
    slope: float = 0.0


class ZFTFStrategy:
    """Exact Python implementation of ZFTF - Z Score Trend Following Indicator."""
    def __init__(self, config):
        self.cfg = config
        self.reset()

    def reset(self):
        self.in_position: bool = False
        self.entry_price: Optional[float] = None
        self.signal: int = 0
        self.exit_reason: str = ""

    def update(self, row: pd.Series, current_price: Optional[float] = None) -> StrategySignalState:
        """
        Processes a candle row and updates position state, entry, target, stop, and PnL.
        """
        close = float(row['close'])
        std = float(row.get('std', 0.0))
        z = float(row.get('z', 0.0))
        slope = float(row.get('slope', 0.0))
        cur_p = float(current_price) if current_price is not None else close

        entry_signal = False
        exit_signal = False
        exit_reason = ""

        # 1. ENTRY LOGIC (Exact Pine Script replication)
        if not self.in_position and std > 0:
            if z > self.cfg.z_threshold and slope > self.cfg.slope_entry:
                self.in_position = True
                self.entry_price = close
                entry_signal = True

        # 2. EXIT LOGIC (Target hit, Stop hit, or Trend exit)
        elif self.in_position:
            target_hit = close >= self.entry_price * (1.0 + self.cfg.target_pct)
            stop_hit   = close <= self.entry_price * (1.0 - self.cfg.stop_pct)
            trend_exit = slope < self.cfg.slope_exit

            if target_hit or stop_hit or trend_exit:
                self.in_position = False
                exit_signal = True
                if target_hit:
                    exit_reason = "TARGET_HIT"
                elif stop_hit:
                    exit_reason = "STOP_HIT"
                elif trend_exit:
                    exit_reason = "TREND_EXIT"

        # 3. CALCULATIONS (Target, Stop, PnL)
        target_line = self.entry_price * (1.0 + self.cfg.target_pct) if self.in_position and self.entry_price else None
        stop_line   = self.entry_price * (1.0 - self.cfg.stop_pct) if self.in_position and self.entry_price else None

        if self.in_position and self.entry_price:
            live_pnl = ((cur_p - self.entry_price) / self.entry_price) * 100.0
            display_entry = self.entry_price
        else:
            live_pnl = None
            display_entry = None

        # 4. SIGNAL CODE
        #  1 = BUY
        # -1 = SELL
        #  2 = HOLD
        #  0 = NONE
        if entry_signal:
            sig = 1
            sig_name = "BUY"
        elif exit_signal:
            sig = -1
            sig_name = "SELL"
        elif self.in_position:
            sig = 2
            sig_name = "HOLD"
        else:
            sig = 0
            sig_name = "NONE"

        return StrategySignalState(
            signal=sig,
            signal_name=sig_name,
            entry_price=display_entry,
            stop_loss=stop_line,
            target_price=target_line,
            live_pnl_pct=live_pnl,
            in_position=self.in_position,
            position_type="LONG" if self.in_position else "FLAT",
            exit_reason=exit_reason,
            z_score=z,
            slope=slope
        )


# Backward compatibility alias
VWAPDualEMAStrategy = ZFTFStrategy
