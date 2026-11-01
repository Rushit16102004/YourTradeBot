"""
Realistic historical backtesting engine for ZFTF Strategy with commission, slippage, and performance metrics.
"""
from dataclasses import dataclass
from typing import Dict, List
import pandas as pd
import numpy as np
from indicators import compute_all_indicators


@dataclass
class TradeRecord:
    entry_time: pd.Timestamp
    exit_time: pd.Timestamp
    direction: str          # LONG
    entry_price: float
    exit_price: float
    qty: int
    gross_pnl: float
    net_pnl: float
    pnl_pct: float
    exit_reason: str
    bars_held: int


class HistoricalBacktester:
    def __init__(self, config):
        self.cfg = config

    def run(self, df_raw: pd.DataFrame) -> Dict:
        df = compute_all_indicators(df_raw, self.cfg)
        trades: List[TradeRecord] = []
        equity = float(self.cfg.initial_capital)
        equity_curve = [equity]
        timestamps = [df.index[0]]

        in_pos = False
        entry_p = 0.0
        entry_time = None
        bars_held = 0

        start_idx = min(self.cfg.window + 1, len(df) - 1)
        for i in range(start_idx, len(df)):
            row = df.iloc[i]
            ts = row.name if isinstance(row.name, pd.Timestamp) else pd.to_datetime(row['timestamp'])
            close = float(row['close'])
            std = float(row.get('std', 0.0))
            z = float(row.get('z', 0.0))
            slope = float(row.get('slope', 0.0))

            # EOD 3:10 PM cutoff check
            is_eod = False
            ts_pdt = pd.to_datetime(ts)
            if (ts_pdt.hour == 15 and ts_pdt.minute >= 10) or ts_pdt.hour > 15:
                is_eod = True

            # 1. Manage Active Trade Exits
            if in_pos:
                bars_held += 1
                exit_p = None
                reason = ""

                trend_exit = slope < self.cfg.slope_exit

                if is_eod:
                    exit_p = close - self.cfg.slippage_points
                    reason = "EOD_EXIT_3_10"
                elif trend_exit:
                    exit_p = close - self.cfg.slippage_points
                    reason = "TREND_EXIT"

                if exit_p is not None:
                    qty = max(1, int(equity // entry_p))
                    gross = (exit_p - entry_p) * qty
                    pct = ((exit_p - entry_p) / entry_p) * 100.0
                    cost = self.cfg.commission_per_order * 2.0
                    net = gross - cost
                    equity += net

                    trades.append(TradeRecord(
                        entry_time=entry_time,
                        exit_time=ts,
                        direction="LONG",
                        entry_price=entry_p,
                        exit_price=exit_p,
                        qty=qty,
                        gross_pnl=gross,
                        net_pnl=net,
                        pnl_pct=pct,
                        exit_reason=reason,
                        bars_held=bars_held
                    ))

                    in_pos = False
                    bars_held = 0

            # 2. Check Entries if Flat (blocked at/after 3:10 PM)
            if not in_pos and not is_eod and std > 0:
                if z > self.cfg.z_threshold and slope > self.cfg.slope_entry:
                    in_pos = True
                    entry_p = close + self.cfg.slippage_points
                    entry_time = ts
                    bars_held = 0

            equity_curve.append(equity)
            timestamps.append(ts)

        total_trades = len(trades)
        wins = [t for t in trades if t.net_pnl > 0]
        losses = [t for t in trades if t.net_pnl <= 0]
        win_rate = (len(wins) / total_trades * 100.0) if total_trades > 0 else 0.0

        gross_profit = sum(t.gross_pnl for t in wins)
        gross_loss = abs(sum(t.gross_pnl for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (gross_profit if gross_profit > 0 else 1.0)

        eq_series = pd.Series(equity_curve)
        cum_max = eq_series.cummax()
        drawdown = (cum_max - eq_series) / cum_max * 100.0
        max_dd = drawdown.max() if not drawdown.empty else 0.0

        return {
            "initial_capital": self.cfg.initial_capital,
            "final_equity": equity,
            "net_pnl": equity - self.cfg.initial_capital,
            "total_trades": total_trades,
            "win_rate": win_rate,
            "profit_factor": profit_factor,
            "max_drawdown_pct": max_dd,
            "avg_trade_pnl": (equity - self.cfg.initial_capital) / total_trades if total_trades > 0 else 0.0,
            "trades": trades,
            "equity_curve": pd.Series(equity_curve, index=timestamps)
        }



