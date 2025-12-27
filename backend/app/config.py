"""
Configuration management for Vietnam Stock Trader
Loads settings from environment variables
"""
import os
from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional

# Project root directory
BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # Application
    app_name: str = "Vietnam Stock Trader"
    debug: bool = False
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # Database
    database_url: str = f"sqlite+aiosqlite:///{BASE_DIR}/data/trading.db"

    # SSI FastConnect API Credentials
    ssi_consumer_id: Optional[str] = Field(default=None, alias="SSI_CONSUMER_ID")
    ssi_consumer_secret: Optional[str] = Field(default=None, alias="SSI_CONSUMER_SECRET")
    ssi_api_url: str = "https://fc-tradeapi.ssi.com.vn"
    ssi_stream_url: str = "wss://fc-tradehub.ssi.com.vn"
    ssi_data_url: str = "https://fc-data.ssi.com.vn"

    # Trading Account (from SSI)
    trading_account: Optional[str] = Field(default=None, alias="SSI_TRADING_ACCOUNT")

    # Investment Settings
    monthly_budget_vnd: int = 2_500_000  # ~$100 USD
    max_stocks_in_portfolio: int = 5
    max_loss_per_trade_percent: float = 2.0

    # News API
    newsapi_key: Optional[str] = Field(default=None, alias="NEWSAPI_KEY")

    # Telegram Notifications
    telegram_bot_token: Optional[str] = Field(default=None, alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: Optional[str] = Field(default=None, alias="TELEGRAM_CHAT_ID")

    # Dashboard
    dashboard_url: str = "https://van31337.github.io/vietnam-stock-trader"

    # Trading Hours (Vietnam Time, UTC+7)
    market_open_hour: int = 9
    market_open_minute: int = 0
    market_close_hour: int = 15
    market_close_minute: int = 0

    # Scheduler
    enable_auto_trading: bool = False  # Set to True when ready for live trading

    class Config:
        env_file = str(BASE_DIR / ".env")
        env_file_encoding = "utf-8"
        extra = "ignore"


# Global settings instance
settings = Settings()


def is_ssi_configured() -> bool:
    """Check if SSI API credentials are configured"""
    return bool(settings.ssi_consumer_id and settings.ssi_consumer_secret)


def is_telegram_configured() -> bool:
    """Check if Telegram notifications are configured"""
    return bool(settings.telegram_bot_token and settings.telegram_chat_id)
