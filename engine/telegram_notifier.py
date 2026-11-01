"""
Telegram Notification Dispatcher for ZFTF NIFTY 50 Strategy.
Sends instant rich alerts to the user's phone on every strategy signal.
"""
import os
import logging
from datetime import datetime
from typing import Optional, Tuple
import pytz
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)
IST = pytz.timezone("Asia/Kolkata")

DEFAULT_CONTACT_PHONE = ""
DEFAULT_CHAT_ID = ""
DEFAULT_BOT_TOKEN = ""


class TelegramNotifier:
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None, phone: Optional[str] = None):
        self.bot_token = bot_token.strip() if bot_token is not None else os.getenv("TELEGRAM_BOT_TOKEN", DEFAULT_BOT_TOKEN).strip()
        self.chat_id = chat_id.strip() if chat_id is not None else os.getenv("TELEGRAM_CHAT_ID", DEFAULT_CHAT_ID).strip()
        self.phone = phone.strip() if phone is not None else os.getenv("TELEGRAM_PHONE", DEFAULT_CONTACT_PHONE).strip()

    @property
    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send_message(self, text: str, parse_mode: str = "HTML") -> Tuple[bool, str]:
        """Sends an HTML or Markdown formatted message via Telegram Bot API."""
        if not self.bot_token:
            return False, "Telegram Bot Token is missing. Set TELEGRAM_BOT_TOKEN in .env or sidebar."
        if not self.chat_id:
            return False, "Telegram Chat ID is missing. Set TELEGRAM_CHAT_ID in .env or sidebar."

        targets = [c.strip() for c in self.chat_id.split(",") if c.strip()]
        if not targets:
            return False, "No valid Telegram chat IDs found."

        overall_ok = False
        last_msg = ""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"

        for target_id in targets:
            payload = {
                "chat_id": target_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            }
            try:
                resp = requests.post(url, json=payload, timeout=8)
                data = resp.json()
                if resp.status_code == 200 and data.get("ok"):
                    logger.info("Telegram notification sent successfully to %s", target_id)
                    overall_ok = True
                    last_msg = "Notification sent successfully!"
                else:
                    err_desc = data.get("description", resp.text)
                    logger.error("Telegram API error for %s (%d): %s", target_id, resp.status_code, err_desc)
                    last_msg = f"Telegram error for {target_id}: {err_desc}"
            except Exception as ex:
                logger.error("Failed to connect to Telegram for %s: %s", target_id, ex)
                last_msg = f"Connection error: {str(ex)}"

        return overall_ok, last_msg

    def send_signal_alert(
        self,
        signal_name: str,          # "BUY" or "SELL"
        price: float,
        target: Optional[float] = None,
        stop: Optional[float] = None,
        z_score: Optional[float] = None,
        slope: Optional[float] = None,
        pnl_pct: Optional[float] = None,
        reason: str = "",
        candle_time: Optional[datetime] = None,
        symbol: str = "NIFTY 50"
    ) -> Tuple[bool, str]:
        """Formats and sends a comprehensive strategy alert message."""
        if candle_time is None:
            candle_time = datetime.now(IST)
        elif getattr(candle_time, "tzinfo", None) is None:
            candle_time = IST.localize(candle_time)
        else:
            candle_time = candle_time.astimezone(IST)

        time_str = candle_time.strftime("%d-%b-%Y %H:%M:%S IST")

        # Color & Icon based on signal
        if signal_name == "BUY":
            icon = "🟢"
            action_title = "<b>BUY / LONG ENTRY</b>"
            header = "🚀 <b>NIFTY 50 NEW BUY SIGNAL</b> 🚀"
        elif signal_name == "SELL":
            icon = "🔴"
            action_title = "<b>SELL / EXIT POSITION</b>"
            header = "⚠️ <b>NIFTY 50 EXIT / SELL SIGNAL</b> ⚠️"
        else:
            icon = "ℹ️"
            action_title = f"<b>{signal_name}</b>"
            header = f"📊 <b>NIFTY 50 SIGNAL UPDATE: {signal_name}</b>"

        # Format details
        lines = [
            header,
            "━━━━━━━━━━━━━━━━━━━━━━",
            f"📊 <b>Instrument:</b> {symbol} (NSE)",
            f"⚡ <b>Action / Direction:</b> {icon} {action_title}",
            f"💰 <b>Execution Price:</b> ₹{price:,.2f}",
        ]

        if target is not None:
            lines.append(f"🎯 <b>Target (+6%):</b> ₹{target:,.2f}")
        if stop is not None:
            lines.append(f"🛑 <b>Stop Loss (-3%):</b> ₹{stop:,.2f}")

        if pnl_pct is not None:
            pnl_icon = "📈" if pnl_pct >= 0 else "📉"
            lines.append(f"{pnl_icon} <b>Unrealized P&L:</b> {pnl_pct:+.2f}%")

        if z_score is not None:
            lines.append(f"📐 <b>Z-Score:</b> {z_score:.2f} (Entry Thresh: 2.00)")
        if slope is not None:
            lines.append(f"📈 <b>Linreg Slope:</b> {slope:+.4f}")

        if reason:
            lines.append(f"📝 <b>Trigger Reason:</b> {reason}")

        lines.extend([
            f"🕒 <b>Candle Close Time:</b> {time_str}",
            "━━━━━━━━━━━━━━━━━━━━━━",
            "<i>ZFTF 5-Minute Algorithmic System</i>"
        ])

        msg = "\n".join(lines)
        return self.send_message(msg, parse_mode="HTML")

    def send_startup_alert(self, symbol: str = "NIFTY 50") -> Tuple[bool, str]:
        """Startup alerts disabled per notification policy (only Main Signal, S&R Breakout/Reversal, and 3:30 PM Force Exit are active)."""
        logger.info("Startup alert skipped (policy: strictly trading & exit signals only)")
        return True, "Startup alerts disabled"

    def send_test_alert(self) -> Tuple[bool, str]:
        """Sends a verification message to confirm Telegram integration is working."""
        now_str = datetime.now(IST).strftime("%d-%b-%Y %H:%M:%S IST")
        msg = (
            "✅ <b>NIFTY 50 TERMINAL TELEGRAM TEST</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"🕒 <b>Timestamp:</b> {now_str}\n"
            "🟢 <b>Status:</b> Connection verified successfully!\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "Automatic alerts will be delivered whenever a confirmed signal triggers."
        )
        return self.send_message(msg, parse_mode="HTML")

    def send_eod_alert(
        self,
        price: Optional[float] = None,
        in_position: bool = False,
        entry_price: Optional[float] = None,
        pnl_pct: Optional[float] = None,
        alert_time: Optional[datetime] = None,
        symbol: str = "NIFTY 50"
    ) -> Tuple[bool, str]:
        """Sends daily EOD square-off reminder that all positions are exited with today's date and time."""
        if alert_time is None:
            alert_time = datetime.now(IST)
        elif getattr(alert_time, "tzinfo", None) is None:
            alert_time = IST.localize(alert_time)
        else:
            alert_time = alert_time.astimezone(IST)

        date_str = alert_time.strftime("%d-%m-%Y")
        time_str = alert_time.strftime("%H:%M:%S IST")

        msg = (
            "🛑 <b>3:30 PM FORCE EXIT: ALL POSITIONS SQUARED OFF</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ <b>ALL POSITIONS EXIT TODAY (3:30 PM MANDATORY EXIT)</b>\n"
            f"📅 <b>Date:</b> {date_str}\n"
            f"⏰ <b>Time:</b> {time_str}\n"
            f"📊 <b>Instrument:</b> {symbol}\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "🛑 <i>3:30 PM Market close square-off completed. All intraday positions force-exited.</i>"
        )
        return self.send_message(msg, parse_mode="HTML")

    def send_sr_breakout_alert(
        self,
        signal_type: str,            # "CALL" or "PUT"
        current_price: float,
        broken_level_price: float,
        broken_level_bounces: int,
        target_price: float,
        target_gap: float,
        timeframe_tag: str = "1M + 2M Confluence",
        alert_time: Optional[datetime] = None,
        symbol: str = "NIFTY 50",
    ) -> Tuple[bool, str]:
        """
        Sends S&R Breakout/Breakdown notification:
        - Repeating alert: 'S&R Signal: CALL-CALL-CALL-CALL-CALL...' or 'S&R Signal: PUT-PUT-PUT-PUT-PUT...'
        - Only sent for Strong S&R levels with target gap >= 50 points after 2-candle confirmation.
        """
        if alert_time is None:
            alert_time = datetime.now(IST)
        elif getattr(alert_time, "tzinfo", None) is None:
            alert_time = IST.localize(alert_time)
        else:
            alert_time = alert_time.astimezone(IST)

        date_str = alert_time.strftime("%d-%m-%Y")
        time_str = alert_time.strftime("%H:%M:%S IST")

        is_call = signal_type.upper() == "CALL"
        if is_call:
            repeating_text = "CALL-CALL-CALL-CALL-CALL-CALL-CALL"
            header = "🚀 <b>S&R SIGNAL: CALL-CALL-CALL-CALL-CALL</b> 🚀"
            action_text = "BUY CALL (Bullish Strong Resistance Breakout)"
            level_label = "Broken Strong Resistance"
            target_label = "Next Resistance Target"
        else:
            repeating_text = "PUT-PUT-PUT-PUT-PUT-PUT-PUT"
            header = "🔻 <b>S&R SIGNAL: PUT-PUT-PUT-PUT-PUT</b> 🔻"
            action_text = "BUY PUT (Bearish Strong Support Breakdown)"
            level_label = "Broken Strong Support"
            target_label = "Next Support Target"

        tf_info = f" • {timeframe_tag}" if timeframe_tag else ""

        lines = [
            header,
            "━━━━━━━━━━━━━━━━━━━━━━",
            f"⚡ <b>Action:</b> {action_text}",
            f"📊 <b>Instrument:</b> {symbol}",
            f"💰 <b>Trigger Price:</b> ₹{current_price:,.2f}",
            f"🛡️ <b>{level_label}:</b> ₹{broken_level_price:,.2f} ({broken_level_bounces}x touches{tf_info})",
            f"🎯 <b>{target_label}:</b> ₹{target_price:,.2f} (Gap: {target_gap:.1f} pts >= 50 pts)",
            "✅ <b>Confirmation:</b> 2-Candle breakout confirmed without reversal",
            f"📅 <b>Date:</b> {date_str}",
            f"⏰ <b>Time:</b> {time_str}",
            "━━━━━━━━━━━━━━━━━━━━━━",
            f"🔔 <b>S&R Signal:</b> {repeating_text}...",
        ]
        msg = "\n".join(lines)
        return self.send_message(msg, parse_mode="HTML")

    def send_sr_reversal_alert(
        self,
        signal_type: str,            # "CALL" or "PUT"
        current_price: float,
        swept_level_price: float,
        swept_level_bounces: int,
        target_price: float,
        target_gap: float,
        wick_pct: float,
        timeframe_tag: str = "1M + 2M Confluence",
        alert_time: Optional[datetime] = None,
        symbol: str = "NIFTY 50",
    ) -> Tuple[bool, str]:
        """
        Sends Institutional Trap & Liquidity Sweep (S&R Reversal) notification:
        - Repeating alert: 'S&R Reversal: TRAP-CALL-TRAP-CALL...' or 'S&R Reversal: TRAP-PUT-TRAP-PUT...'
        - Target gap >= 50 points, strong level with long rejection wick.
        """
        if alert_time is None:
            alert_time = datetime.now(IST)
        elif getattr(alert_time, "tzinfo", None) is None:
            alert_time = IST.localize(alert_time)
        else:
            alert_time = alert_time.astimezone(IST)

        date_str = alert_time.strftime("%d-%m-%Y")
        time_str = alert_time.strftime("%H:%M:%S IST")

        is_call = signal_type.upper() == "CALL"
        if is_call:
            repeating_text = "TRAP-CALL-TRAP-CALL-TRAP-CALL-TRAP-CALL"
            header = "🪤 <b>S&R REVERSAL: TRAP-CALL-TRAP-CALL</b> 🪤"
            action_text = "BUY CALL (Bear Trap / Liquidity Sweep Reversal)"
            level_label = "Swept Strong Support"
            target_label = "Next Resistance Target"
            trap_desc = f"Institutional sell-stops swept with {wick_pct:.1f}% lower rejection wick"
        else:
            repeating_text = "TRAP-PUT-TRAP-PUT-TRAP-PUT-TRAP-PUT"
            header = "🪤 <b>S&R REVERSAL: TRAP-PUT-TRAP-PUT</b> 🪤"
            action_text = "BUY PUT (Bull Trap / Liquidity Sweep Reversal)"
            level_label = "Swept Strong Resistance"
            target_label = "Next Support Target"
            trap_desc = f"Institutional buy-stops swept with {wick_pct:.1f}% upper rejection wick"

        tf_info = f" • {timeframe_tag}" if timeframe_tag else ""

        lines = [
            header,
            "━━━━━━━━━━━━━━━━━━━━━━",
            f"⚡ <b>Action:</b> {action_text}",
            f"📊 <b>Instrument:</b> {symbol}",
            f"💰 <b>Trigger Price:</b> ₹{current_price:,.2f}",
            f"🛡️ <b>{level_label}:</b> ₹{swept_level_price:,.2f} ({swept_level_bounces}x touches{tf_info})",
            f"🎯 <b>{target_label}:</b> ₹{target_price:,.2f} (Gap: {target_gap:.1f} pts >= 50 pts)",
            f"🕯️ <b>Setup:</b> {trap_desc}",
            f"📅 <b>Date:</b> {date_str}",
            f"⏰ <b>Time:</b> {time_str}",
            "━━━━━━━━━━━━━━━━━━━━━━",
            f"🔔 <b>S&R Reversal:</b> {repeating_text}...",
        ]
        msg = "\n".join(lines)
        return self.send_message(msg, parse_mode="HTML")



