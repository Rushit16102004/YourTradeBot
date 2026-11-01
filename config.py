"""
Application configuration module for ZFTF (Z-Score Trend Following Strategy).
"""
import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class SmartAPIConfig:
    api_key: str = os.getenv("ANGEL_API_KEY", "")
    client_id: str = os.getenv("ANGEL_CLIENT_ID", "")
    password: str = os.getenv("ANGEL_PASSWORD", "")
    totp_secret: str = os.getenv("ANGEL_TOTP_SECRET", "")
    exchange: str = os.getenv("DEFAULT_EXCHANGE", "NSE")
    symbol: str = os.getenv("DEFAULT_SYMBOL", "NIFTY 50")
    token: str = os.getenv("DEFAULT_TOKEN", "99926000")  # NIFTY 50 spot index token on NSE
    is_mock_mode: bool = os.getenv("MOCK_MODE", "false").lower() == "true"


@dataclass
class StrategyConfig:
    # ZFTF Strategy Parameters (Matching user's Pine Script)
    window: int = 20                # Rolling Window
    z_threshold: float = 2.0        # Z Entry Threshold (e.g. 1.5 - 2.0)
    slope_entry: float = 0.001      # Slope Entry Threshold
    slope_exit: float = -0.001      # Slope Exit Threshold
    target_pct: float = 0.06        # Target % (6% per Pine Script)
    stop_pct: float = 0.03          # Stop % (3% per Pine Script)
    
    # Capital & Cost Settings
    initial_capital: float = 100000.0
    commission_per_order: float = 20.0
    slippage_points: float = 0.50


@dataclass
class TelegramConfig:
    bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id: str = os.getenv("TELEGRAM_CHAT_ID", "")
    phone: str = os.getenv("TELEGRAM_PHONE", "")
    enabled: bool = os.getenv("TELEGRAM_ENABLED", "true").lower() == "true"


