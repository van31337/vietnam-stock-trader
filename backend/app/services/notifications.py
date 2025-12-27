"""
Notification Service
Sends alerts via Telegram and other channels
"""
import asyncio
from typing import Optional
from loguru import logger

from ..config import settings, is_telegram_configured

# Telegram bot
try:
    from telegram import Bot
    from telegram.error import TelegramError
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot not installed")


class NotificationService:
    """Service for sending notifications and alerts"""

    def __init__(self):
        self._bot: Optional[Bot] = None
        if TELEGRAM_AVAILABLE and is_telegram_configured():
            self._bot = Bot(token=settings.telegram_bot_token)

    async def send_telegram(self, message: str) -> bool:
        """Send message via Telegram"""
        if not self._bot or not settings.telegram_chat_id:
            logger.warning("Telegram not configured")
            return False

        try:
            await self._bot.send_message(
                chat_id=settings.telegram_chat_id,
                text=message,
                parse_mode="HTML"
            )
            return True
        except Exception as e:
            logger.error(f"Telegram send error: {e}")
            return False

    async def notify_trade(
        self,
        action: str,
        symbol: str,
        quantity: int,
        price: float,
        total: float
    ):
        """Send trade notification"""
        emoji = "🟢" if action == "BUY" else "🔴"
        message = f"""
{emoji} <b>Trade Executed</b>

<b>Action:</b> {action}
<b>Symbol:</b> {symbol}
<b>Quantity:</b> {quantity:,}
<b>Price:</b> {price:,.0f} VND
<b>Total:</b> {total:,.0f} VND
"""
        await self.send_telegram(message)

    async def notify_signal(
        self,
        symbol: str,
        signal: str,
        confidence: float,
        reasons: list
    ):
        """Send trading signal notification"""
        emoji = "📈" if "BUY" in signal else "📉" if "SELL" in signal else "➡️"
        reasons_text = "\n".join(f"• {r}" for r in reasons[:5])
        message = f"""
{emoji} <b>Trading Signal: {signal}</b>

<b>Symbol:</b> {symbol}
<b>Confidence:</b> {confidence*100:.0f}%

<b>Reasons:</b>
{reasons_text}
"""
        await self.send_telegram(message)

    async def notify_daily_summary(
        self,
        total_value: float,
        daily_pnl: float,
        daily_pnl_percent: float,
        positions: list
    ):
        """Send daily portfolio summary"""
        pnl_emoji = "📈" if daily_pnl >= 0 else "📉"
        positions_text = "\n".join(
            f"• {p['symbol']}: {p['pnl_percent']:+.2f}%"
            for p in positions[:5]
        )
        message = f"""
📊 <b>Daily Portfolio Summary</b>

<b>Total Value:</b> {total_value:,.0f} VND
{pnl_emoji} <b>Daily P&L:</b> {daily_pnl:+,.0f} VND ({daily_pnl_percent:+.2f}%)

<b>Positions:</b>
{positions_text}
"""
        await self.send_telegram(message)

    async def notify_error(self, error_type: str, details: str):
        """Send error notification"""
        message = f"""
⚠️ <b>Error Alert</b>

<b>Type:</b> {error_type}
<b>Details:</b> {details}
"""
        await self.send_telegram(message)

    async def notify_balance_update(
        self,
        new_balance: float,
        change: float,
        reason: str
    ):
        """Send balance update notification"""
        emoji = "💰" if change > 0 else "💸"
        message = f"""
{emoji} <b>Balance Update</b>

<b>New Balance:</b> {new_balance:,.0f} VND
<b>Change:</b> {change:+,.0f} VND
<b>Reason:</b> {reason}
"""
        await self.send_telegram(message)


# Singleton instance
notification_service = NotificationService()
