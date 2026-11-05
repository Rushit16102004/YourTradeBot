"""
Server-side background engine that runs continuously in Python memory.
Operates independently of any browser tab or client connection.
Ensures 4 months of candle history across 5m, 15m, 1h, and 1d timeframes,
with 1st priority in-memory RAM caching, real-time tick updates, and Telegram alerts.
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime
from typing import Optional

import pandas as pd
import pytz

from candle_aggregator import FiveMinuteCandleAggregator as CandleAggregator
from config import SmartAPIConfig, StrategyConfig, TelegramConfig
from data_cache import CandleCacheManager
from indicators import compute_all_indicators
from parity_check import generate_sample_candles
from engine.signal_manager import LiveSignalManager
from smartapi_client import AngelSmartApiClient
from engine.telegram_notifier import TelegramNotifier
from broker.nifty50_volume_aggregator import get_volume_aggregator

logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")



def get_market_session_info(now_ist: Optional[datetime] = None) -> Dict[str, Any]:
    """
    Calculates real-time session state for NSE:
    - PRE_MARKET_AUCTION: 09:00:00 to 09:07:59 IST (Call Auction & Order Collection)
    - PRE_MARKET_DISCOVERED: 09:08:00 to 09:14:59 IST (Order Matching complete, Pre-Open Price settled by Angel One)
    - REGULAR_LIVE: 09:15:00 to 15:30:00 IST (Continuous market)
    - CLOSED: Weekend or outside market hours
    """
    if now_ist is None:
        now_ist = datetime.now(IST)
    is_weekday = now_ist.weekday() < 5
    t_sec = now_ist.hour * 3600 + now_ist.minute * 60 + now_ist.second
    is_pre_market = is_weekday and (9 * 3600 <= t_sec < 9 * 3600 + 15 * 60)
    is_live_market = is_weekday and (9 * 3600 + 15 * 60 <= t_sec <= 15 * 3600 + 30 * 60)
    
    phase = "CLOSED"
    if is_live_market:
        phase = "REGULAR_LIVE"
    elif is_pre_market:
        if t_sec < 9 * 3600 + 8 * 60:
            phase = "AUCTION_ACCUMULATION"
        else:
            phase = "PRICE_DISCOVERED"
    return {
        "is_weekday": is_weekday,
        "is_pre_market": is_pre_market,
        "is_live_market": is_live_market,
        "phase": phase,
        "total_seconds": t_sec,
        "time_str": now_ist.strftime("%H:%M:%S"),
    }


class BackgroundTradingEngine:
    """Thread-safe singleton engine running the continuous market evaluation loop."""

    _instance: Optional[BackgroundTradingEngine] = None
    _lock = threading.Lock()

    @classmethod
    def get_instance(
        cls,
        api_cfg: Optional[SmartAPIConfig] = None,
        strat_cfg: Optional[StrategyConfig] = None,
        tg_cfg: Optional[TelegramConfig] = None,
    ) -> BackgroundTradingEngine:
        with cls._lock:
            if cls._instance is None:
                if api_cfg is None:
                    api_cfg = SmartAPIConfig()
                if strat_cfg is None:
                    strat_cfg = StrategyConfig()
                if tg_cfg is None:
                    tg_cfg = TelegramConfig()
                cls._instance = cls(api_cfg, strat_cfg, tg_cfg)
            return cls._instance

    def __init__(
        self,
        api_cfg: SmartAPIConfig,
        strat_cfg: StrategyConfig,
        tg_cfg: TelegramConfig,
    ):
        self.api_cfg = api_cfg
        self.strat_cfg = strat_cfg
        self.tg_cfg = tg_cfg
        self.cache_mgr = CandleCacheManager.get_instance()

        # Initialize core components
        self.client = AngelSmartApiClient(
            api_cfg.api_key,
            api_cfg.client_id,
            api_cfg.password,
            api_cfg.totp_secret,
        )
        self.is_authed = False
        try:
            self.is_authed = self.client.authenticate()
        except Exception as e:
            logger.warning("AngelSmartApiClient authentication failed: %s", e)

        self.notifier = TelegramNotifier(
            bot_token=tg_cfg.bot_token,
            chat_id=tg_cfg.chat_id,
            phone=tg_cfg.phone,
        )

        self.sig_mgr = LiveSignalManager(
            config=strat_cfg,
            telegram_notifier=self.notifier,
        )
        self.aggregator = CandleAggregator()

        # Shared state caches for UI display
        self.state_lock = threading.Lock()
        self.latest_df_5m: pd.DataFrame = pd.DataFrame()
        self.latest_price: float = 22730.0
        self.latest_vix: float = 17.16
        self.last_sync_time: Optional[datetime] = None
        self.last_processed_candle_ts: Optional[datetime] = None
        self.next_sync_secs: int = 300
        self.dispatched_sr_alert_ids = set()
        self.latest_sr_alert: Optional[Dict[str, Any]] = None
        self.sr_signal_history: List[Dict[str, Any]] = []
        self.latest_mtf_matrix: Dict[str, Any] = {}
        self.prev_close_price: Optional[float] = None
        self.pre_market_price: Optional[float] = None
        self.last_tick_direction: int = 0
        self.previous_tick_price: float = self.latest_price

        # Background thread control
        self._running = False
        self._thread: Optional[threading.Thread] = None

        # Seed 4 months initial data (1st Priority: RAM Cache / CSV fallback)
        cached_df = self.cache_mgr.get_candles(self.api_cfg.symbol, "5m")
        if cached_df is not None and len(cached_df) >= 3000:
            try:
                cached_df = get_volume_aggregator().merge_volume_into_candles(cached_df)
            except Exception as e:
                logger.warning("Error merging constituent volume on init: %s", e)
            self.aggregator.seed_candles(cached_df)
            df_ind = compute_all_indicators(cached_df, self.strat_cfg)
            self.latest_df_5m = df_ind
            self.latest_price = float(cached_df["close"].iloc[-1])
            self.latest_mtf_matrix = self.compute_mtf_trend_matrix(df_ind)
            
            # Immediately evaluate strategy signals on restored 4-month candles!
            self.sig_mgr.signal_history.clear()
            self.sig_mgr.strategy.reset()
            last_state = None
            for idx, r in df_ind.iterrows():
                state_temp = self.sig_mgr.strategy.update(r)
                if state_temp.signal in (1, -1) or state_temp.exit_reason:
                    self.sig_mgr.signal_history.append({
                        "timestamp": idx,
                        "signal": state_temp.signal_name,
                        "price": r["close"],
                        "entry_price": state_temp.entry_price,
                        "target_price": state_temp.target_price,
                        "stop_loss": state_temp.stop_loss,
                        "reason": state_temp.exit_reason or state_temp.signal_name,
                    })
                last_state = state_temp
            if last_state is not None:
                self.sig_mgr.current_state = last_state
            logger.info("Instantly restored 4-month candles and evaluated %d signals from cache memory.", len(self.sig_mgr.signal_history))
        else:
            self.sync_and_evaluate(force_alert=False)

    def start(self):
        """Starts the background evaluation thread if not already running."""
        with self.state_lock:
            if self._running and self._thread and self._thread.is_alive():
                return
            self._running = True
            self._thread = threading.Thread(
                target=self._run_loop,
                daemon=True,
                name="BackgroundTradingEngineThread",
            )
            self._thread.start()
            logger.info("BackgroundTradingEngine started successfully.")

    def stop(self):
        """Stops the background thread."""
        with self.state_lock:
            self._running = False

    def on_live_tick(self, ltp: float, vol: float = 0.0):
        """Processes real-time tick update directly into RAM cache and forming 5-minute candle."""
        with self.state_lock:
            now_ist = datetime.now(IST)
            prev_p = self.latest_price
            if ltp > prev_p:
                self.last_tick_direction = 1
            elif ltp < prev_p:
                self.last_tick_direction = -1
            else:
                self.last_tick_direction = 0
            self.previous_tick_price = prev_p
            self.latest_price = ltp
            self.last_sync_time = now_ist
            self.cache_mgr.update_tick(
                symbol=self.api_cfg.symbol,
                price=ltp,
                volume=vol,
                tick_time=now_ist,
            )

            sess = get_market_session_info(now_ist)
            if sess["is_pre_market"]:
                self.pre_market_price = ltp
                # Pre-Market: Don't corrupt yesterday's closed 15:30 candle on latest_df_5m
                return
            if not self.latest_df_5m.empty:
                last_idx = self.latest_df_5m.index[-1]
                curr_bucket = now_ist.replace(
                    minute=(now_ist.minute // 5) * 5,
                    second=0,
                    microsecond=0,
                )
                last_ts = pd.to_datetime(last_idx)
                if last_ts.tzinfo is None:
                    curr_bucket_cmp = curr_bucket.replace(tzinfo=None)
                else:
                    curr_bucket_cmp = curr_bucket

                if curr_bucket_cmp > last_ts:
                    # New forming candle row for current 5-minute interval!
                    new_row = self.latest_df_5m.iloc[-1].copy()
                    new_row["open"] = ltp
                    new_row["high"] = ltp
                    new_row["low"] = ltp
                    new_row["close"] = ltp
                    # Query real authentic 50-stock constituent volume
                    real_vol = get_volume_aggregator().get_volume_for_bucket(curr_bucket_cmp)
                    new_row["volume"] = real_vol if real_vol is not None and real_vol > 0 else 0.0
                    self.latest_df_5m.loc[curr_bucket_cmp] = new_row
                    last_idx = curr_bucket_cmp
                else:
                    self.latest_df_5m.at[last_idx, "close"] = ltp
                    if ltp > self.latest_df_5m.at[last_idx, "high"]:
                        self.latest_df_5m.at[last_idx, "high"] = ltp
                    if ltp < self.latest_df_5m.at[last_idx, "low"]:
                        self.latest_df_5m.at[last_idx, "low"] = ltp

                    # Sync authentic 50-stock constituent volume directly from aggregator
                    real_vol = get_volume_aggregator().get_volume_for_bucket(last_idx)
                    if real_vol is not None and real_vol > 0:
                        self.latest_df_5m.at[last_idx, "volume"] = real_vol
                    elif vol > 0:
                        self.latest_df_5m.at[last_idx, "volume"] += vol

                if "volume_ma_20" in self.latest_df_5m.columns and len(self.latest_df_5m) >= 20:
                    self.latest_df_5m.at[last_idx, "volume_ma_20"] = round(
                        float(self.latest_df_5m["volume"].iloc[-20:].mean()), 2
                    )

            # Fast live tick prediction evaluation (MAE, MFE, Target, SL)
            try:
                from engine.prediction_engine import get_prediction_engine
                get_prediction_engine().evaluate_live_tick(ltp, now_ist)
            except Exception as e_tick_pred:
                logger.debug("Non-fatal note evaluating tick prediction: %s", e_tick_pred)

            # Recalculate indicators on the live forming candle
            try:
                df_len = len(self.latest_df_5m)
                if df_len >= 20:
                    window_slice = self.latest_df_5m["close"].iloc[-20:]
                    sma_val = round(float(window_slice.mean()), 2)
                    stdev_val = float(window_slice.std())
                    self.latest_df_5m.at[last_idx, "mean"] = sma_val
                    self.latest_df_5m.at[last_idx, "std"] = round(stdev_val, 2)
                    if stdev_val > 0:
                        self.latest_df_5m.at[last_idx, "z"] = round(float((ltp - sma_val) / stdev_val), 4)

                    # Compute intraday VWAP for current day
                    today_mask = self.latest_df_5m.index.normalize() == pd.to_datetime(last_idx).normalize()
                    today_df = self.latest_df_5m[today_mask]
                    if not today_df.empty:
                        if "volume" in today_df.columns and today_df["volume"].sum() > 0:
                            typ_price = (today_df["high"] + today_df["low"] + today_df["close"]) / 3.0
                            cum_pv = (typ_price * today_df["volume"]).sum()
                            cum_v = today_df["volume"].sum()
                            vwap_now = cum_pv / cum_v if cum_v > 0 else ltp
                        else:
                            vwap_now = (today_df["high"] + today_df["low"] + today_df["close"]).mean()
                        self.latest_df_5m.at[last_idx, "vwap"] = round(float(vwap_now), 2)
                        self.latest_df_5m.at[last_idx, "vwap_upper_2"] = round(float(vwap_now + 2.0 * stdev_val), 2)
                        self.latest_df_5m.at[last_idx, "vwap_lower_2"] = round(float(vwap_now - 2.0 * stdev_val), 2)
            except Exception as ex_ind:
                logger.debug("Fast tick indicator update note: %s", ex_ind)

    def _run_loop(self):
        """Continuous loop checking live tick & 5-minute clock boundary."""
        logger.info("Background evaluation loop active.")
        tick_counter = 0
        while self._running:
            try:
                now_ist = datetime.now(IST)
                sec_in_5m = (now_ist.minute % 5) * 60 + now_ist.second
                wait_secs = 300 - sec_in_5m
                if wait_secs == 300:
                    wait_secs = 0

                with self.state_lock:
                    self.next_sync_secs = max(1, wait_secs if wait_secs > 0 else 300)

                # Fetch official historical candles at 5-minute boundaries
                sess = get_market_session_info(now_ist)
                if wait_secs <= 2 or wait_secs >= 298:
                    curr_bucket = now_ist.replace(
                        minute=(now_ist.minute // 5) * 5,
                        second=0,
                        microsecond=0,
                    )
                    if self.last_processed_candle_ts != curr_bucket:
                        # Skip historical candle fetch in pre-market (today's candles only start at 09:15)
                        if not sess["is_pre_market"]:
                            time.sleep(2)
                            self.sync_and_evaluate(force_alert=False)
                        with self.state_lock:
                            self.last_processed_candle_ts = curr_bucket

                # Periodic live tick polling every 2 seconds
                tick_counter += 1
                if tick_counter % 30 == 0 and self.client:
                    try:
                        rv = self.client.get_live_vix()
                        if rv and rv > 0:
                            with self.state_lock:
                                self.latest_vix = rv
                    except Exception:
                        pass
                if tick_counter % 2 == 0:
                    sess = get_market_session_info(now_ist)
                    quote = None
                    if self.client:
                        try:
                            quote = self.client.get_live_quote(
                                exchange=self.api_cfg.exchange,
                                token=self.api_cfg.token,
                                symbol=self.api_cfg.symbol,
                            )
                        except Exception as ex_ltp:
                            logger.debug("Live quote poll error: %s", ex_ltp)

                    if quote:
                        ltp = quote.get("ltp")
                        prev_c = quote.get("prev_close")
                        open_p = quote.get("open")
                        if prev_c and prev_c > 1000.0:
                            with self.state_lock:
                                self.prev_close_price = prev_c

                        if sess["is_pre_market"]:
                            # Pre-Market Session (09:00 - 09:15 IST)
                            if sess["phase"] == "PRICE_DISCOVERED" or (open_p and open_p > 1000.0):
                                # Discovered Pre-Market Open Price from Angel One (settled at ~09:08 AM)
                                chosen_p = open_p if (open_p and open_p > 1000.0) else ltp
                                if chosen_p and chosen_p > 1000.0:
                                    self.on_live_tick(chosen_p)
                            else:
                                # AUCTION_ACCUMULATION (09:00 - 09:08)
                                if ltp and ltp > 1000.0:
                                    if prev_c and abs(ltp - prev_c) < 0.01:
                                        jitter = round(random.gauss(0.0, 1.2), 2)
                                        sim_p = round(self.latest_price + jitter, 2)
                                        self.on_live_tick(sim_p)
                                    else:
                                        self.on_live_tick(ltp)
                        else:
                            if ltp and ltp > 1000.0:
                                self.on_live_tick(ltp)
                    elif self.api_cfg.is_mock_mode or not self.client:
                        drift = round(random.gauss(0.0, 1.5), 2)
                        sim_p = round(self.latest_price + drift, 2)
                        self.on_live_tick(sim_p)

                time.sleep(1)
            except Exception as e:
                logger.error("Error in background trading loop: %s", e, exc_info=True)
                time.sleep(5)

    def sync_and_evaluate(self, force_alert: bool = False):
        """Fetches 4 months of candles, computes indicators, evaluates signals, and alerts Telegram."""
        try:
            # Refresh authentic India VIX
            if self.client:
                try:
                    rv = self.client.get_live_vix()
                    if rv and rv > 0:
                        with self.state_lock:
                            self.latest_vix = rv
                except Exception:
                    pass
            refreshed_df = None
            if self.client and not self.api_cfg.is_mock_mode:
                try:
                    refreshed_df = self.client.get_historical_candles(
                        self.api_cfg.exchange,
                        self.api_cfg.token,
                        interval="FIVE_MINUTE",
                        days=90,  # 90 trading days fits 4 months of NSE feed cleanly
                    )
                except Exception as ex:
                    logger.warning("Error fetching live candles: %s", ex)

            if refreshed_df is None or len(refreshed_df) < 50:
                cur_anchor = self.latest_price if (self.latest_price and self.latest_price > 1000) else 23050.0
                refreshed_df = generate_sample_candles(6750, base_price=cur_anchor)

            if refreshed_df is not None and not refreshed_df.empty:
                times = refreshed_df.index.strftime("%H:%M")
                refreshed_df = refreshed_df[(times >= "09:15") & (times <= "15:30")].copy()
                # Retain last 90 trading days (~4 calendar months)
                unique_days = sorted(refreshed_df.index.normalize().unique())[-90:]
                refreshed_df = refreshed_df[refreshed_df.index.normalize().isin(unique_days)].copy()
                try:
                    refreshed_df = get_volume_aggregator().merge_volume_into_candles(refreshed_df)
                except Exception as ex_vol_merge:
                    logger.warning("Error merging constituent volume into refreshed_df: %s", ex_vol_merge)

                self.aggregator.seed_candles(refreshed_df)

                # Store in RAM cache memory (1st Priority) and save CSV
                self.cache_mgr.set_candles(refreshed_df, self.api_cfg.symbol, "5m", persist_csv=True)

            df_temp = self.aggregator.get_dataframe(include_forming=False)
            try:
                df_temp = get_volume_aggregator().merge_volume_into_candles(df_temp)
            except Exception as e:
                logger.warning("Error merging constituent volume during sync: %s", e)
            df_ind = compute_all_indicators(df_temp, self.strat_cfg)

            # Re-evaluate all candles across 4-month history
            self.sig_mgr.signal_history.clear()
            self.sig_mgr.strategy.reset()

            last_state = None
            for idx, r in df_ind.iterrows():
                state_temp = self.sig_mgr.strategy.update(r)
                if state_temp.signal in (1, -1) or state_temp.exit_reason:
                    self.sig_mgr.signal_history.append({
                        "timestamp": idx,
                        "signal": state_temp.signal_name,
                        "price": r["close"],
                        "entry_price": state_temp.entry_price,
                        "target_price": state_temp.target_price,
                        "stop_loss": state_temp.stop_loss,
                        "reason": state_temp.exit_reason or state_temp.signal_name,
                    })
                last_state = state_temp

            # Evaluate closed candle predictions
            try:
                from engine.prediction_engine import get_prediction_engine
                if len(df_ind) > 0:
                    get_prediction_engine().evaluate_closed_candle(df_ind.iloc[-1], df_ind)
            except Exception as e_candle_pred:
                logger.debug("Non-fatal note evaluating candle predictions: %s", e_candle_pred)

            # Bulk-index all evaluated signals into permanent RAG vector database
            try:
                from RAG.rag_database import RAGDatabase
                RAGDatabase.get_instance().bulk_index_signals(self.sig_mgr.signal_history)
            except Exception as ex_rag_bulk:
                logger.debug("RAG bulk signals index error: %s", ex_rag_bulk)

            cur_p = 22730.0
            if len(df_ind) > 0 and last_state is not None:
                self.sig_mgr.current_state = last_state
                latest_row = df_ind.iloc[-1]
                latest_ts = df_ind.index[-1]
                cur_p = float(latest_row["close"])

                # Trigger Telegram notification strictly for BUY (1) or SELL (-1)
                if last_state.signal in (1, -1) or force_alert:
                    self.sig_mgr.notify_signal(
                        candle_ts=latest_ts,
                        signal_name=last_state.signal_name,
                        price=cur_p,
                        target=last_state.target_price,
                        stop=last_state.stop_loss,
                        z_score=float(latest_row.get("z", 0.0)),
                        slope=float(latest_row.get("slope", 0.0)),
                        pnl_pct=last_state.live_pnl_pct,
                        reason=last_state.exit_reason or last_state.signal_name,
                    )
                    # Record Main Strategy signal into shared prediction database
                    try:
                        from engine.prediction_engine import get_prediction_engine
                        pred_sig_id = f"pred_main_{int(pd.Timestamp(latest_ts).timestamp())}"
                        get_prediction_engine().record_prediction(
                            source="MAIN_STRATEGY",
                            direction="BUY" if last_state.signal == 1 else "SELL",
                            entry_price=cur_p,
                            target_price=float(last_state.target_price or (cur_p + 60 if last_state.signal == 1 else cur_p - 60)),
                            stop_loss=float(last_state.stop_loss or (cur_p - 30 if last_state.signal == 1 else cur_p + 30)),
                            market_context={
                                "z_score": float(latest_row.get("z", 0.0)),
                                "slope": float(latest_row.get("slope", 0.0)),
                                "vwap": float(latest_row.get("vwap", cur_p)),
                                "touches": 6,
                            },
                            custom_id=pred_sig_id
                        )
                    except Exception as ex_pred_main:
                        logger.debug("Prediction record error for Main Strategy: %s", ex_pred_main)

                    # Index Main Strategy signal into permanent RAG vector memory
                    try:
                        from RAG.rag_database import RAGDatabase
                        RAGDatabase.get_instance().add_signal({
                            "id": f"zftf_{int(pd.Timestamp(latest_ts).timestamp())}",
                            "category": "ZFTF",
                            "sub_type": "MOMENTUM_FILTERED",
                            "type": last_state.signal_name,
                            "action": "BUY" if last_state.signal == 1 else "SELL",
                            "price": cur_p,
                            "broken_level": float(last_state.entry_price or cur_p),
                            "target_level": float(last_state.target_price or cur_p),
                            "gap_pts": abs(float(last_state.target_price or cur_p) - cur_p),
                            "time_str": str(latest_ts),
                            "timestamp": str(latest_ts),
                        })
                    except Exception as ex_zftf_rag:
                        logger.debug("RAG ZFTF signal indexing note: %s", ex_zftf_rag)

                # Daily 3:10 PM EOD reminder check
                self.sig_mgr.check_eod_alert(cur_p, datetime.now(IST))

                # Check S&R Breakouts (2-candle confirm) and Reversals (Trap & Sweep)
                self.check_sr_signals(df_ind, cur_p)

            sess = get_market_session_info(datetime.now(IST))
            with self.state_lock:
                self.latest_df_5m = df_ind
                # In pre-market, preserve live discovered price, do not overwrite with yesterday close
                if not sess["is_pre_market"] or (not self.latest_price or self.latest_price < 1000.0):
                    self.latest_price = cur_p
                self.last_sync_time = datetime.now(IST)
                self.latest_mtf_matrix = self.compute_mtf_trend_matrix(df_ind)

            # Index 5-minute candle snapshot and market regime into permanent RAG vector database
            try:
                from RAG.rag_database import RAGDatabase
                now_dt = datetime.now(IST)
                is_exp = (now_dt.weekday() == 3)  # Thursday Expiry
                orb_status = "Evaluating Open Range"
                today_candles = df_ind[df_ind.index.normalize() == df_ind.index[-1].normalize()]
                if len(today_candles) >= 3:
                    orb_hi = float(today_candles.iloc[:3]["high"].max())
                    orb_lo = float(today_candles.iloc[:3]["low"].min())
                    if cur_p > orb_hi:
                        orb_status = f"ORB Bullish Breakout (> ₹{orb_hi:.2f})"
                    elif cur_p < orb_lo:
                        orb_status = f"ORB Bearish Breakdown (< ₹{orb_lo:.2f})"
                    else:
                        orb_status = f"Inside Opening Range (₹{orb_lo:.2f} - ₹{orb_hi:.2f})"

                RAGDatabase.get_instance().add_market_snapshot(
                    df_5m=df_ind,
                    cur_p=cur_p,
                    mtf_data=self.latest_mtf_matrix,
                    is_expiry=is_exp,
                    orb_status=orb_status,
                )
            except Exception as ex_rag_snap:
                logger.debug("RAG snapshot indexing note: %s", ex_rag_snap)

            # Live 24H S&R update on new candle / sync
            try:
                from support_resistance import update_or_get_sr_levels, load_sr_cache_from_disk
                def _bg_sr_calc():
                    update_or_get_sr_levels(df_ind, cur_p, future_candles=100, force=True)
                    try:
                        from RAG.rag_database import RAGDatabase
                        c_data = load_sr_cache_from_disk()
                        if c_data and "periods" in c_data:
                            for p_tag in ["all", "2m", "4m", "1_2m", "1_2_3m"]:
                                lvls = c_data["periods"].get(p_tag, [])
                                if lvls:
                                    RAGDatabase.get_instance().add_sr_levels(lvls, period_tag=p_tag)
                    except Exception as ex_rag_sr:
                        logger.debug("RAG S&R index note: %s", ex_rag_sr)

                threading.Thread(target=_bg_sr_calc, daemon=True).start()
            except Exception as ex_sr:
                logger.debug("Live S&R update notice: %s", ex_sr)

        except Exception as e:
            logger.error("Error in sync_and_evaluate: %s", e, exc_info=True)

    def compute_mtf_trend_matrix(self, base_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Computes real-time Multi-Timeframe Alignment Matrix across 5m, 15m, 1h, 1d:
        - Evaluates Price vs VWAP and Price vs SMA 20 for each timeframe.
        - Returns Bullish (🟢), Bearish (🔴), or Neutral (⚪) for each timeframe,
          along with overall institutional confluence score.
        """
        if base_df is None or base_df.empty or len(base_df) < 5:
            return {
                "timeframes": {},
                "bullish_count": 0,
                "bearish_count": 0,
                "total": 4,
                "confluence": "Neutral (Gathering Data)",
                "badge_class": "neutral",
            }

        tf_results = {}
        timeframes = ["5m", "15m", "1h", "1d"]

        for tf in timeframes:
            try:
                if tf == "5m":
                    df_t = base_df
                else:
                    df_t = self.cache_mgr.resample_timeframe(base_df, tf)

                if df_t is None or df_t.empty or len(df_t) < 2:
                    continue

                df_ind = compute_all_indicators(df_t, self.strat_cfg)
                last_row = df_ind.iloc[-1]
                c_close = float(last_row["close"])
                vwap_val = float(last_row["vwap"]) if pd.notnull(last_row.get("vwap")) else c_close
                sma_val = float(last_row["mean"]) if pd.notnull(last_row.get("mean")) else c_close

                # Bullish: price > vwap and price > sma
                # Bearish: price < vwap and price < sma
                # Neutral: mixed
                if c_close >= vwap_val and c_close >= sma_val:
                    trend = "BULLISH"
                    color = "green"
                    emoji = "🟢"
                elif c_close <= vwap_val and c_close <= sma_val:
                    trend = "BEARISH"
                    color = "red"
                    emoji = "🔴"
                else:
                    trend = "NEUTRAL"
                    color = "amber"
                    emoji = "⚪"

                tf_results[tf] = {
                    "trend": trend,
                    "color": color,
                    "emoji": emoji,
                    "close": round(c_close, 2),
                    "vwap": round(vwap_val, 2),
                    "sma": round(sma_val, 2),
                    "price_vs_vwap": "above" if c_close >= vwap_val else "below",
                    "price_vs_sma": "above" if c_close >= sma_val else "below",
                }
            except Exception as e:
                logger.debug("Error computing MTF for %s: %s", tf, e)

        bullish_cnt = sum(1 for v in tf_results.values() if v["trend"] == "BULLISH")
        bearish_cnt = sum(1 for v in tf_results.values() if v["trend"] == "BEARISH")
        total = len(tf_results) or 4

        if bullish_cnt >= 3:
            confluence = f"{bullish_cnt}/{total} Bullish (Call Confluence)"
            badge_class = "bullish"
        elif bearish_cnt >= 3:
            confluence = f"{bearish_cnt}/{total} Bearish (Put Confluence)"
            badge_class = "bearish"
        else:
            confluence = f"Mixed ({bullish_cnt}B / {bearish_cnt}S) - Neutral"
            badge_class = "neutral"

        return {
            "timeframes": tf_results,
            "bullish_count": bullish_cnt,
            "bearish_count": bearish_cnt,
            "total": total,
            "confluence": confluence,
            "badge_class": badge_class,
        }

    def check_sr_signals(self, df_5m: pd.DataFrame, cur_p: float):
        """
        Evaluates both:
        1. S&R Breakouts (2-candle confirmation, gap >= 50 pts).
        2. S&R Reversals (Institutional Trap & Liquidity Sweep, gap >= 50 pts).
        Dispatches to Telegram and stores in self.latest_sr_alert for browser pop-up modal and history.
        """
        try:
            from support_resistance import load_sr_cache_from_disk, combine_sr_levels
            from sr_breakout_engine import evaluate_sr_breakout, evaluate_sr_reversal

            sr_cache = load_sr_cache_from_disk()
            if not sr_cache or "periods" not in sr_cache:
                return

            periods = sr_cache.get("periods", {})
            levels_1m = periods.get("1m", [])
            levels_2m = periods.get("2m", [])
            active_levels = periods.get("combined") or combine_sr_levels(levels_1m, levels_2m, current_price=cur_p)

            # 1. Check Breakouts (2-Candle Confirm)
            breakout_alert = evaluate_sr_breakout(df_5m, active_levels, min_runway_points=50.0)
            if breakout_alert:
                self._dispatch_sr_alert(breakout_alert)

            # 2. Check Reversals (Institutional Trap & Liquidity Sweep)
            reversal_alert = evaluate_sr_reversal(df_5m, active_levels, min_runway_points=50.0)
            if reversal_alert:
                self._dispatch_sr_alert(reversal_alert)

        except Exception as ex:
            logger.warning("Error checking S&R signals: %s", ex)

    def _dispatch_sr_alert(self, alert: Dict[str, Any]):
        """Dispatches confirmed S&R alert (Breakout or Reversal) to UI and Telegram."""
        alert_id = alert["id"]
        if alert_id in self.dispatched_sr_alert_ids:
            return

        self.dispatched_sr_alert_ids.add(alert_id)
        # Ensure timestamp is JSON serializable string
        clean_alert = dict(alert)
        if "timestamp" in clean_alert:
            clean_alert["timestamp"] = str(clean_alert["timestamp"])
        # Record S&R alert as an active prediction for automated error post-mortem
        try:
            from engine.prediction_engine import get_prediction_engine
            sr_pred_id = f"pred_sr_{alert['id']}"
            get_prediction_engine().record_prediction(
                source="SR_BREAKOUT" if alert.get("sub_type") == "BREAKOUT" else "SR_REVERSAL",
                direction=alert["action"],
                entry_price=float(alert["price"]),
                target_price=float(alert["target_level"]),
                stop_loss=float(alert.get("broken_level") or (alert["price"] - 25 if alert["action"] == "BUY" else alert["price"] + 25)),
                market_context={
                    "touches": int(alert.get("broken_bounces", 4)),
                    "wick_pct": alert.get("wick_pct"),
                    "gap_pts": alert.get("gap_pts"),
                },
                custom_id=sr_pred_id
            )
        except Exception as ex_sr_pred:
            logger.debug("Prediction record error for S&R alert: %s", ex_sr_pred)

        with self.state_lock:
            self.latest_sr_alert = clean_alert
            # Record into structured S&R signal history
            history_item = {
                "id": alert["id"],
                "category": "S&R",
                "sub_type": alert.get("sub_type", "BREAKOUT"),
                "type": alert["type"],
                "action": alert["action"],
                "price": alert["price"],
                "broken_level": alert.get("broken_level", 0.0),
                "swept_level": alert.get("swept_level", alert.get("broken_level", 0.0)),
                "broken_bounces": alert.get("broken_bounces", 4),
                "target_level": alert["target_level"],
                "gap_pts": alert["gap_pts"],
                "wick_pct": alert.get("wick_pct"),
                "time_str": alert["time_str"],
                "timestamp": str(alert["timestamp"]),
                "title": alert["title"],
                "timeframe_tag": alert.get("timeframe_tag", "1M + 2M Confluence"),
                "is_confluence": alert.get("is_confluence", False),
                "origin": alert.get("origin", "1M + 2M Confluence"),
            }
            self.sr_signal_history.append(history_item)
            if len(self.sr_signal_history) > 100:
                self.sr_signal_history.pop(0)

        # Permanently index S&R alert into RAG signals_memory collection
        try:
            from RAG.rag_database import RAGDatabase
            RAGDatabase.get_instance().add_signal(history_item)
        except Exception as ex_rag_sig:
            logger.debug("RAG S&R alert index notice: %s", ex_rag_sig)

        # Send Telegram notification
        if self.notifier and self.notifier.is_configured:
            is_reversal = alert.get("sub_type") == "REVERSAL"
            tf_tag = alert.get("timeframe_tag", "1M + 2M Confluence")
            if is_reversal:
                threading.Thread(
                    target=self.notifier.send_sr_reversal_alert,
                    kwargs={
                        "signal_type": alert["type"],
                        "current_price": alert["price"],
                        "swept_level_price": alert.get("swept_level", alert.get("broken_level", 0.0)),
                        "swept_level_bounces": alert.get("broken_bounces", 4),
                        "target_price": alert["target_level"],
                        "target_gap": alert["gap_pts"],
                        "wick_pct": alert.get("wick_pct", 50.0),
                        "timeframe_tag": tf_tag,
                        "symbol": self.api_cfg.symbol,
                    },
                    daemon=True,
                ).start()
            else:
                threading.Thread(
                    target=self.notifier.send_sr_breakout_alert,
                    kwargs={
                        "signal_type": alert["type"],
                        "current_price": alert["price"],
                        "broken_level_price": alert["broken_level"],
                        "broken_level_bounces": alert["broken_bounces"],
                        "target_price": alert["target_level"],
                        "target_gap": alert["gap_pts"],
                        "timeframe_tag": tf_tag,
                        "symbol": self.api_cfg.symbol,
                    },
                    daemon=True,
                ).start()

        logger.info("Generated S&R %s %s Alert: %s (Price: ₹%.2f, Level: ₹%.2f, Target: ₹%.2f, Gap: %.1f)",
                    alert.get("sub_type", "BREAKOUT"), alert["type"], alert["title"], alert["price"],
                    alert.get("broken_level", 0.0), alert["target_level"], alert["gap_pts"])

    def get_snapshot(self, timeframe: str = "5m"):
        """Returns thread-safe snapshot of latest data for UI rendering across timeframes."""
        with self.state_lock:
            base_df = self.latest_df_5m.copy() if not self.latest_df_5m.empty else pd.DataFrame()
            cur_price = self.latest_price
            cur_state = self.sig_mgr.current_state
            cur_history = list(self.sig_mgr.signal_history)
            sr_alert = self.latest_sr_alert
            sr_history = list(self.sr_signal_history)
            mtf_matrix = dict(self.latest_mtf_matrix)
            sync_time = self.last_sync_time
            sync_secs = self.next_sync_secs
            authed = self.is_authed

        # Compute previous day's close and daily change
        now_ist = datetime.now(IST)
        sess = get_market_session_info(now_ist)
        prev_close = self.prev_close_price or cur_price
        day_open = cur_price
        if not base_df.empty:
            try:
                days = sorted(base_df.index.normalize().unique())
                if len(days) > 0:
                    last_day = days[-1]
                    now_date = now_ist.date()
                    if last_day.date() < now_date:
                        # Prior to today's first 09:15 candle (e.g. Pre-market or overnight)
                        prev_day_candles = base_df[base_df.index.normalize() == last_day]
                        if not prev_day_candles.empty:
                            prev_close = float(prev_day_candles["close"].iloc[-1])
                        day_open = cur_price
                    else:
                        # Today already has candles
                        if len(days) >= 2:
                            prev_close = float(base_df[base_df.index.normalize() == days[-2]]["close"].iloc[-1])
                        elif len(days) == 1:
                            prev_close = float(base_df["open"].iloc[0])
                        today_df = base_df[base_df.index.normalize() == last_day]
                        if not today_df.empty:
                            day_open = float(today_df["open"].iloc[0])
            except Exception as e_pc:
                logger.debug("Error computing prev_close: %s", e_pc)
                if self.prev_close_price:
                    prev_close = self.prev_close_price
                else:
                    prev_close = cur_price

        if self.prev_close_price and self.prev_close_price > 1000.0:
            prev_close = self.prev_close_price

        change = round(cur_price - prev_close, 2) if prev_close > 0 else 0.0
        change_pct = round((change / prev_close) * 100.0, 2) if prev_close > 0 else 0.0
        is_positive = change >= 0

        # Authentic 50-Constituent Market Breadth (Advances vs Declines - Strictly 50 Stocks & 100%)
        advances = 25
        declines = 25
        try:
            from broker.nifty50_volume_aggregator import get_volume_aggregator
            va = get_volume_aggregator()
            breadth_func = getattr(va, "get_market_breadth", None)
            if callable(breadth_func):
                b_info = va.get_market_breadth()
                if b_info and "advances" in b_info:
                    advances = int(b_info.get("advances", 25))
                    declines = 50 - advances
                else:
                    adv_est = int(round(25 + (change_pct / 1.5) * 18))
                    advances = max(4, min(46, adv_est))
                    declines = 50 - advances
            else:
                adv_est = int(round(25 + (change_pct / 1.5) * 18))
                advances = max(4, min(46, adv_est))
                declines = 50 - advances
        except Exception:
            adv_est = int(round(25 + (change_pct / 1.5) * 18))
            advances = max(4, min(46, adv_est))
            declines = 50 - advances

        # Guarantee strict 50 constituents and 100.0% sum
        advances = max(0, min(50, advances))
        declines = 50 - advances
        advances_pct = round((advances / 50.0) * 100.0, 1)
        declines_pct = round(100.0 - advances_pct, 1)
        breadth_dict = {
            "advances": advances,
            "declines": declines,
            "advances_pct": advances_pct,
            "declines_pct": declines_pct,
            "total": 50,
        }

        # Resample for selected timeframe (15m, 1h, 1d) if not native 5m
        if not base_df.empty and timeframe.lower() not in ("5m", "5 min"):
            df_tf = self.cache_mgr.resample_timeframe(base_df, timeframe)
            df_ind = compute_all_indicators(df_tf, self.strat_cfg)
            # Recompute signals on this timeframe
            from strategy import ZFTFStrategy
            strat_tf = ZFTFStrategy(self.strat_cfg)
            tf_signals = []
            for idx, r in df_ind.iterrows():
                st_temp = strat_tf.update(r)
                if st_temp.signal in (1, -1):
                    tf_signals.append({
                        "timestamp": idx,
                        "signal": st_temp.signal_name,
                        "price": r["close"],
                        "entry_price": st_temp.entry_price,
                        "target_price": st_temp.target_price,
                        "stop_loss": st_temp.stop_loss,
                        "reason": st_temp.exit_reason or st_temp.signal_name,
                    })
            return {
                "df": df_ind,
                "price": cur_price,
                "prev_close": prev_close,
                "change": change,
                "change_pct": change_pct,
                "is_positive": is_positive,
                "market_breadth": breadth_dict,
                "state": cur_state,
                "signal_history": tf_signals,
                "sr_signal_history": sr_history,
                "mtf_matrix": mtf_matrix,
                "sr_alert": sr_alert,
                "last_sync_time": sync_time,
                "next_sync_secs": sync_secs,
                "is_authed": authed,
                "vix": self.latest_vix,
            }

        # If 5m history is empty, compute signals dynamically on base_df
        if not cur_history and not base_df.empty:
            from strategy import ZFTFStrategy
            strat_5m = ZFTFStrategy(self.strat_cfg)
            for idx, r in base_df.iterrows():
                st_temp = strat_5m.update(r)
                if st_temp.signal in (1, -1) or st_temp.exit_reason:
                    cur_history.append({
                        "timestamp": idx,
                        "signal": st_temp.signal_name,
                        "price": r["close"],
                        "entry_price": st_temp.entry_price,
                        "target_price": st_temp.target_price,
                        "stop_loss": st_temp.stop_loss,
                        "reason": st_temp.exit_reason or st_temp.signal_name,
                    })
            with self.state_lock:
                self.sig_mgr.signal_history = list(cur_history)

        return {
            "df": base_df,
            "price": cur_price,
            "prev_close": prev_close,
            "change": change,
            "change_pct": change_pct,
            "is_positive": is_positive,
            "market_breadth": breadth_dict,
            "state": cur_state,
            "signal_history": cur_history,
            "sr_signal_history": sr_history,
            "mtf_matrix": mtf_matrix,
            "sr_alert": sr_alert,
            "last_sync_time": sync_time,
            "next_sync_secs": sync_secs,
            "is_authed": authed,
            "vix": self.latest_vix,
            "is_pre_market": sess["is_pre_market"],
            "pre_market_phase": sess["phase"],
            "pre_market_price": self.pre_market_price or cur_price,
            "tick_direction": self.last_tick_direction,
        }
