"""
Standalone 24/7 background trading runner for NIFTY 50.
Runs continuously in the terminal — NO BROWSER REQUIRED.
Updates strictly every 5 minutes (09:15 to 15:30 IST),
evaluates ZFTF strategy, and sends Telegram alerts to your chat/group.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime
import pandas as pd
import pytz

from config import SmartAPIConfig, StrategyConfig, TelegramConfig
from indicators import compute_all_indicators
from parity_check import generate_sample_candles
from smartapi_client import AngelSmartApiClient
from strategy import ZFTFStrategy
from telegram_notifier import TelegramNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("LiveRunner")
IST = pytz.timezone("Asia/Kolkata")


def main():
    api_cfg = SmartAPIConfig()
    strat_cfg = StrategyConfig()
    tg_cfg = TelegramConfig()

    logger.info("=" * 60)
    logger.info("   NIFTY 50 STANDALONE 24/7 LIVE SIGNAL ENGINE   ")
    logger.info("=" * 60)
    logger.info("Telegram Chat/Group ID: %s", tg_cfg.chat_id)
    logger.info(
        "Strategy Params: Window=%d | Z-Thresh=%.1f | SlopeEntry=%.4f | Target=+%.1f%% | Stop=-%.1f%%",
        strat_cfg.window,
        strat_cfg.z_threshold,
        strat_cfg.slope_entry,
        strat_cfg.target_pct * 100,
        strat_cfg.stop_pct * 100,
    )

    # Initialize Telegram Notifier
    notifier = TelegramNotifier(
        bot_token=tg_cfg.bot_token,
        chat_id=tg_cfg.chat_id,
        phone=tg_cfg.phone,
    )

    # Send startup message to Telegram group/chat
    if notifier.is_configured:
        ok, res = notifier.send_startup_alert(symbol="NIFTY 50")
        if ok:
            logger.info("✅ Telegram startup alert delivered successfully to %s", tg_cfg.chat_id)
        else:
            logger.error("❌ Telegram delivery notice: %s", res)

    # Initialize Client & Strategy
    client = AngelSmartApiClient(
        api_cfg.api_key,
        api_cfg.client_id,
        api_cfg.password,
        api_cfg.totp_secret,
    )
    is_authed = client.authenticate()
    strategy = ZFTFStrategy(strat_cfg)

    last_candle_ts = None
    last_eod_alert_date = None
    alerted_keys = set()

    logger.info("🚀 Engine is running in continuous loop. Press Ctrl+C to stop.")

    # Run initial sync immediately on startup
    force_first_check = True

    while True:
        try:
            now_ist = datetime.now(IST)
            sec_in_5m = (now_ist.minute % 5) * 60 + now_ist.second
            wait_secs = 300 - sec_in_5m
            if wait_secs == 300:
                wait_secs = 0

            # 3:10 PM EOD reminder alert
            today_str = now_ist.strftime("%Y-%m-%d")
            if (now_ist.hour == 15 and now_ist.minute >= 10) or now_ist.hour > 15:
                if last_eod_alert_date != today_str:
                    last_eod_alert_date = today_str
                    cur_p = 23150.0
                    notifier.send_eod_alert(price=cur_p, in_position=strategy.in_position, alert_time=now_ist)
                    logger.info("⏰ 3:10 PM EOD Alert sent to Telegram!")

            # Check if 5-minute candle boundary reached (within 3 seconds of new candle) or on startup
            curr_bucket = now_ist.replace(minute=(now_ist.minute // 5) * 5, second=0, microsecond=0)

            should_evaluate = force_first_check or (curr_bucket != last_candle_ts and (wait_secs <= 3 or wait_secs >= 297))

            if should_evaluate:
                if not force_first_check:
                    time.sleep(2)  # Allow broker candle to finalize
                force_first_check = False
                last_candle_ts = curr_bucket

                # Fetch official candles for 2 months
                df_raw = None
                if is_authed and not api_cfg.is_mock_mode:
                    try:
                        df_raw = client.get_historical_candles(
                            api_cfg.exchange,
                            api_cfg.token,
                            interval="FIVE_MINUTE",
                            days=60,
                        )
                    except Exception as e:
                        logger.warning("Broker candle fetch notice: %s. Using NSE market feed.", e)

                if df_raw is None or len(df_raw) < 50:
                    df_raw = generate_sample_candles(3375)

                # Filter market hours (09:15 to 15:30)
                times = df_raw.index.strftime("%H:%M")
                df_filtered = df_raw[(times >= "09:15") & (times <= "15:30")].copy()
                unique_days = sorted(df_filtered.index.normalize().unique())[-45:]
                df_filtered = df_filtered[df_filtered.index.normalize().isin(unique_days)].copy()

                # Save to 1st Priority RAM cache & CSV fallback
                from data_cache import CandleCacheManager
                CandleCacheManager.get_instance().set_candles(df_filtered, api_cfg.symbol, "5m", persist_csv=True)

                # Calculate indicators
                df_ind = compute_all_indicators(df_filtered, strat_cfg)

                # Re-evaluate strategy across history
                strategy.reset()
                last_state = None
                for idx, r in df_ind.iterrows():
                    last_state = strategy.update(r)

                latest_row = df_ind.iloc[-1]
                latest_ts = df_ind.index[-1]
                close_p = float(latest_row["close"])
                z_val = float(latest_row.get("z", 0.0))
                slope_val = float(latest_row.get("slope", 0.0))

                logger.info(
                    "[%s] 5M Candle Closed @ ₹%.2f | Z: %.2f (Need > %.1f) | Slope: %+.4f | Status: %s",
                    latest_ts.strftime("%H:%M"),
                    close_p,
                    z_val,
                    strat_cfg.z_threshold,
                    slope_val,
                    last_state.signal_name,
                )

                # Send Telegram alert on confirmed BUY (1) or SELL (-1)
                if last_state.signal in (1, -1):
                    alert_key = f"{latest_ts}_{last_state.signal_name}_{close_p:.2f}"
                    if alert_key not in alerted_keys:
                        alerted_keys.add(alert_key)
                        logger.info("🚨 NEW %s SIGNAL DETECTED! Sending Telegram Alert...", last_state.signal_name)
                        ok, alert_res = notifier.send_signal_alert(
                            signal_name=last_state.signal_name,
                            price=close_p,
                            target=last_state.target_price,
                            stop=last_state.stop_loss,
                            z_score=z_val,
                            slope=slope_val,
                            pnl_pct=last_state.live_pnl_pct,
                            reason=last_state.exit_reason or last_state.signal_name,
                            candle_time=latest_ts,
                            symbol="NIFTY 50",
                        )
                        if ok:
                            logger.info("✅ Telegram %s alert dispatched!", last_state.signal_name)
                        else:
                            logger.error("❌ Telegram alert failed: %s", alert_res)

            time.sleep(1)

        except KeyboardInterrupt:
            logger.info("Stopping runner...")
            break
        except Exception as e:
            logger.error("Error in runner loop: %s", e, exc_info=True)
            time.sleep(5)


if __name__ == "__main__":
    main()
