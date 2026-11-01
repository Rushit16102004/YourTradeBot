"""
Prediction Engine and Post-Mortem Continuous Learning Pipeline.
Tracks active trade predictions (Bot Signals, User On-Chart Drawings, RAG setups),
monitors live ticks and candle bars for Target/Stop-Loss resolution,
and generates deep error post-mortems and lessons stored in SQLite & ChromaDB.
"""

from __future__ import annotations

import json
import logging
import threading
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from database.user_db import (
    get_active_predictions,
    get_all_predictions,
    get_prediction_by_id,
    get_prediction_stats,
    save_prediction,
    update_prediction,
)
from RAG.rag_database import RAGDatabase

logger = logging.getLogger("prediction_engine")


class PredictionEngine:
    _instance: Optional[PredictionEngine] = None
    _lock = threading.Lock()

    def __init__(self):
        self.lock = threading.Lock()
        self.rag_db = RAGDatabase.get_instance()
        self.last_candle_eval_time = None
        logger.info("Prediction & Error Post-Mortem Engine initialized.")

    @classmethod
    def get_instance(cls) -> PredictionEngine:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def record_prediction(
        self,
        source: str,
        direction: str,
        entry_price: float,
        target_price: float,
        stop_loss: float,
        user_id: Optional[str] = None,
        username: Optional[str] = "Trader",
        symbol: str = "NIFTY 50",
        timeframe: str = "5m",
        market_context: Optional[Dict[str, Any]] = None,
        custom_id: Optional[str] = None,
    ) -> str:
        """
        Records a new prediction into SQLite and indexes it in RAG vector memory.
        """
        pred_id = custom_id or f"pred_{source.lower()}_{int(time.time() * 1000)}"
        direction = str(direction).upper()

        data = {
            "id": pred_id,
            "user_id": user_id,
            "username": username,
            "source": source,
            "symbol": symbol,
            "timeframe": timeframe,
            "direction": direction,
            "entry_price": float(entry_price),
            "target_price": float(target_price),
            "stop_loss": float(stop_loss),
            "market_context": market_context or {},
        }

        with self.lock:
            save_prediction(data)

        try:
            self.rag_db.add_prediction(data)
        except Exception as e:
            logger.debug("Non-fatal note indexing active prediction in RAG: %s", e)

        return pred_id

    def sync_user_target_sl_drawings(
        self,
        drawings: List[Dict[str, Any]],
        user_id: Optional[str] = None,
        username: str = "Trader",
        current_market_context: Optional[Dict[str, Any]] = None,
    ):
        """
        Inspects user drawings; if any 'target_sl' shape is not yet in the common prediction
        database, records it so that user-drawn setups are also tracked and learned from.
        """
        if not drawings:
            return

        for d in drawings:
            if d.get("type") == "target_sl":
                shape_id = str(d.get("id"))
                pred_id = f"user_shape_{shape_id}"
                existing = get_prediction_by_id(pred_id)
                if not existing:
                    entry = float(d.get("entry", 0.0))
                    target = float(d.get("target", 0.0))
                    stop = float(d.get("stop", 0.0))
                    if entry > 0 and target > 0 and stop > 0:
                        direction = "BUY" if target > entry else "SELL"
                        ctx = dict(current_market_context or {})
                        ctx["remark"] = d.get("remark", "User Trade Setup")
                        self.record_prediction(
                            source="USER_DRAWING",
                            direction=direction,
                            entry_price=entry,
                            target_price=target,
                            stop_loss=stop,
                            user_id=user_id,
                            username=username,
                            market_context=ctx,
                            custom_id=pred_id,
                        )

    def evaluate_live_tick(self, ltp: float, timestamp: Any = None):
        """
        Fast path evaluated on incoming live ticks to track MAE/MFE and immediate Target/SL hits.
        """
        if ltp <= 0:
            return

        active_preds = get_active_predictions(limit=100)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for p in active_preds:
            pid = p["id"]
            direction = str(p.get("direction", "BUY")).upper()
            entry = float(p.get("entry_price", 0.0))
            target = float(p.get("target_price", 0.0))
            stop = float(p.get("stop_loss", 0.0))
            mae = float(p.get("mae_pts", 0.0) or 0.0)
            mfe = float(p.get("mfe_pts", 0.0) or 0.0)

            if entry <= 0:
                continue

            if direction in ("BUY", "CALL", "LONG"):
                adverse = entry - ltp
                favorable = ltp - entry
                mae = max(mae, adverse)
                mfe = max(mfe, favorable)

                if ltp >= target:
                    self._resolve_prediction(p, status="TARGET_HIT", exit_price=target, exit_time=now_str, mae=mae, mfe=mfe)
                elif ltp <= stop:
                    self._resolve_prediction(p, status="SL_HIT", exit_price=stop, exit_time=now_str, mae=mae, mfe=mfe)
                else:
                    update_prediction(pid, {"mae_pts": round(mae, 2), "mfe_pts": round(mfe, 2)})

            elif direction in ("SELL", "PUT", "SHORT"):
                adverse = ltp - entry
                favorable = entry - ltp
                mae = max(mae, adverse)
                mfe = max(mfe, favorable)

                if ltp <= target:
                    self._resolve_prediction(p, status="TARGET_HIT", exit_price=target, exit_time=now_str, mae=mae, mfe=mfe)
                elif ltp >= stop:
                    self._resolve_prediction(p, status="SL_HIT", exit_price=stop, exit_time=now_str, mae=mae, mfe=mfe)
                else:
                    update_prediction(pid, {"mae_pts": round(mae, 2), "mfe_pts": round(mfe, 2)})

    def evaluate_closed_candle(self, closed_row: Any, df_ind: Any = None):
        """
        Evaluates active predictions against 5-minute candle high, low, close for precise multi-candle verification.
        """
        if closed_row is None:
            return
        if hasattr(closed_row, "empty") and closed_row.empty:
            return

        high = float(closed_row.get("high", 0.0)) if hasattr(closed_row, "get") else float(closed_row["high"])
        low = float(closed_row.get("low", 0.0)) if hasattr(closed_row, "get") else float(closed_row["low"])
        close = float(closed_row.get("close", 0.0)) if hasattr(closed_row, "get") else float(closed_row["close"])

        candle_time = closed_row.name if hasattr(closed_row, "name") else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        candle_time_str = str(candle_time)

        active_preds = get_active_predictions(limit=100)

        for p in active_preds:
            pid = p["id"]
            direction = str(p.get("direction", "BUY")).upper()
            entry = float(p.get("entry_price", 0.0))
            target = float(p.get("target_price", 0.0))
            stop = float(p.get("stop_loss", 0.0))
            mae = float(p.get("mae_pts", 0.0) or 0.0)
            mfe = float(p.get("mfe_pts", 0.0) or 0.0)

            if entry <= 0:
                continue

            if direction in ("BUY", "CALL", "LONG"):
                adverse = entry - low
                favorable = high - entry
                mae = max(mae, adverse)
                mfe = max(mfe, favorable)

                if high >= target:
                    self._resolve_prediction(p, status="TARGET_HIT", exit_price=target, exit_time=candle_time_str, mae=mae, mfe=mfe, candle_row=closed_row)
                elif low <= stop:
                    self._resolve_prediction(p, status="SL_HIT", exit_price=stop, exit_time=candle_time_str, mae=mae, mfe=mfe, candle_row=closed_row)
                else:
                    update_prediction(pid, {"mae_pts": round(mae, 2), "mfe_pts": round(mfe, 2)})

            elif direction in ("SELL", "PUT", "SHORT"):
                adverse = high - entry
                favorable = entry - low
                mae = max(mae, adverse)
                mfe = max(mfe, favorable)

                if low <= target:
                    self._resolve_prediction(p, status="TARGET_HIT", exit_price=target, exit_time=candle_time_str, mae=mae, mfe=mfe, candle_row=closed_row)
                elif high >= stop:
                    self._resolve_prediction(p, status="SL_HIT", exit_price=stop, exit_time=candle_time_str, mae=mae, mfe=mfe, candle_row=closed_row)
                else:
                    update_prediction(pid, {"mae_pts": round(mae, 2), "mfe_pts": round(mfe, 2)})

    def _resolve_prediction(
        self,
        pred: Dict[str, Any],
        status: str,
        exit_price: float,
        exit_time: str,
        mae: float,
        mfe: float,
        candle_row: Any = None,
    ):
        """
        Executes deep technical post-mortem analysis:
        - Classifies error category.
        - Calculates PnL error points and percentages.
        - Synthesizes learned reflection rule.
        - Permanently updates SQLite and ChromaDB.
        """
        pid = pred["id"]
        direction = str(pred.get("direction", "BUY")).upper()
        entry = float(pred.get("entry_price", 0.0))
        target = float(pred.get("target_price", 0.0))
        stop = float(pred.get("stop_loss", 0.0))
        pred_pnl = float(pred.get("predicted_pnl_pts", 0.0) or 0.0)

        if direction in ("BUY", "CALL", "LONG"):
            actual_pnl = round(exit_price - entry, 2)
        else:
            actual_pnl = round(entry - exit_price, 2)

        actual_pct = round((actual_pnl / entry) * 100, 2) if entry > 0 else 0.0
        pnl_error = round(actual_pnl - pred_pnl, 2)

        # Context analysis
        ctx = pred.get("market_context") or {}
        if isinstance(ctx, str):
            try:
                ctx = json.loads(ctx)
            except Exception:
                ctx = {}

        sr_touches = int(ctx.get("touches", 0) or 0)
        z_score = float(ctx.get("z_score", 0.0) or 0.0)
        vwap_slope = float(ctx.get("slope", 0.0) or 0.0)

        # Post-mortem error classification
        if status == "TARGET_HIT":
            error_cat = "NONE_TARGET_HIT"
            if mae <= 0.35 * abs(entry - stop):
                error_analysis = f"Clean institutional expansion! Price moved directly toward target ₹{target:.2f} with minimal adverse heat (MAE {mae:.1f} pts). Order flow and VWAP slope provided strong tailwind."
                reflection = f"High-confidence setup confirmed. Entering with alignment to VWAP slope and verified S&R confluence consistently reaches full 1:{pred.get('rr_ratio', 1.0)} target runway."
            else:
                error_analysis = f"Target hit (+{actual_pnl:.1f} pts) after enduring consolidation heat (MAE {mae:.1f} pts). The stop loss buffer at ₹{stop:.2f} successfully protected the position from being shaken out."
                reflection = "Patience and wider ATR stop buffer proved essential: position survived initial chop before expanding to target."
        else:
            # SL_HIT diagnoses
            if mfe >= 0.4 * abs(target - entry) and abs(exit_price - stop) <= 6.0:
                error_cat = "SL_TOO_TIGHT"
                error_analysis = f"Premature Stop Loss hit! Price breached SL ₹{stop:.2f} by only {abs(exit_price - stop):.1f} pts before expanding favorably by +{mfe:.1f} pts toward target. The stop was placed directly in normal ATR market noise."
                reflection = f"Prediction Error Rule: Stop Loss was too tight for current volatility. In future setups near ₹{entry:.2f}, place the SL at least 12-15 points below the primary S&R zone rather than at the exact wick boundary."
            elif (direction in ("BUY", "CALL", "LONG") and z_score >= 1.8) or (direction in ("SELL", "PUT", "SHORT") and z_score <= -1.8):
                error_cat = "EXHAUSTION_BAND_COUNTER"
                error_analysis = f"Exhaustion Trap! Prediction entered at extreme VWAP z-score ({z_score:.2f}) near the ±2σ exhaustion band. Institutional profit-taking triggered an immediate mean-reversion counter-wave."
                reflection = "Prediction Error Rule: Avoid directional breakouts when z-score is beyond ±1.8σ. Wait for price to mean-revert back to Session VWAP before initiating continuation trades."
            elif sr_touches > 0 and sr_touches < 5:
                error_cat = "WEAK_SR_TOUCHES"
                error_analysis = f"False Breakout / Liquidity Sweep! The broken S&R level had only {sr_touches} touches (< 5 touch requirement). Smart money swept retail breakout orders, creating a rapid trap."
                reflection = f"Prediction Error Rule: Breakout failed due to insufficient level testing ({sr_touches} touches). Strictly require > 5 confirmed touches before taking breakout predictions."
            elif (direction in ("BUY", "CALL", "LONG") and vwap_slope < -0.05) or (direction in ("SELL", "PUT", "SHORT") and vwap_slope > 0.05):
                error_cat = "SLOPE_DIVERGENCE"
                error_analysis = f"Fought Institutional Trend! Direction ({direction}) was taken opposite to the Linear Regression VWAP slope ({vwap_slope:.4f}), resulting in heavy counter-trend pressure."
                reflection = "Prediction Error Rule: Never enter counter to institutional VWAP slope. Long trades require positive slope (> 0); Short trades require negative slope (< 0)."
            else:
                error_cat = "TREND_INVALIDATION"
                error_analysis = f"Macro Trend Invalidation. Price violated technical structure at ₹{exit_price:.2f} (Adverse MAE {mae:.1f} pts). Disciplined stop execution prevented severe drawdown."
                reflection = "Prediction Error Rule: Order flow shifted abruptly; disciplined stop execution preserved capital."

        now_resolved = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        update_payload = {
            "status": status,
            "exit_price": exit_price,
            "exit_time": exit_time,
            "actual_pnl_pts": actual_pnl,
            "actual_pnl_pct": actual_pct,
            "pnl_error_pts": pnl_error,
            "mae_pts": round(mae, 2),
            "mfe_pts": round(mfe, 2),
            "error_category": error_cat,
            "error_analysis": error_analysis,
            "reflection_text": reflection,
            "resolved_at": now_resolved,
        }

        update_prediction(pid, update_payload)

        resolved_pred = dict(pred)
        resolved_pred.update(update_payload)

        try:
            self.rag_db.index_prediction_outcome(resolved_pred)
        except Exception as e:
            logger.warning("Error indexing prediction outcome in RAG: %s", e)

        logger.info(
            "Resolved prediction %s -> %s (Actual: %+.1f pts, Error: %+.1f pts, Category: %s)",
            pid,
            status,
            actual_pnl,
            pnl_error,
            error_cat,
        )


def get_prediction_engine() -> PredictionEngine:
    return PredictionEngine.get_instance()
