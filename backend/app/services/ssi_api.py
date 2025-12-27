"""
SSI FastConnect API Integration
Documentation: https://guide.ssi.com.vn/ssi-products
"""
import asyncio
import hashlib
import hmac
import json
import time
from datetime import datetime
from typing import Optional, Dict, Any, List
from loguru import logger
import aiohttp
import websockets

from ..config import settings, is_ssi_configured


class SSIApiService:
    """Service for interacting with SSI FastConnect API"""

    def __init__(self):
        self.consumer_id = settings.ssi_consumer_id
        self.consumer_secret = settings.ssi_consumer_secret
        self.api_url = settings.ssi_api_url
        self.stream_url = settings.ssi_stream_url
        self.data_url = settings.ssi_data_url
        self.trading_account = settings.trading_account
        self.access_token: Optional[str] = None
        self.token_expiry: Optional[datetime] = None
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()

    def _generate_signature(self, data: str) -> str:
        """Generate HMAC signature for API requests"""
        if not self.consumer_secret:
            raise ValueError("SSI Consumer Secret not configured")
        signature = hmac.new(
            self.consumer_secret.encode('utf-8'),
            data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature

    async def authenticate(self) -> bool:
        """
        Authenticate with SSI FastConnect API
        Returns True if authentication successful
        """
        if not is_ssi_configured():
            logger.warning("SSI API credentials not configured")
            return False

        try:
            session = await self._get_session()
            timestamp = str(int(time.time() * 1000))
            sign_data = f"{self.consumer_id}{timestamp}"
            signature = self._generate_signature(sign_data)

            headers = {
                "Content-Type": "application/json",
                "X-SSI-TIMESTAMP": timestamp,
                "X-SSI-CONSUMERID": self.consumer_id,
                "X-SSI-SIGNATURE": signature
            }

            async with session.post(
                f"{self.api_url}/api/v2/auth/token",
                headers=headers,
                json={"consumerID": self.consumer_id}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        self.access_token = data["data"]["accessToken"]
                        # Token typically valid for 24 hours
                        self.token_expiry = datetime.now()
                        logger.info("SSI API authentication successful")
                        return True
                    else:
                        logger.error(f"SSI auth failed: {data.get('message')}")
                else:
                    logger.error(f"SSI auth failed with status: {response.status}")
                return False
        except Exception as e:
            logger.error(f"SSI authentication error: {e}")
            return False

    async def _ensure_authenticated(self):
        """Ensure we have a valid access token"""
        if not self.access_token or not self.token_expiry:
            await self.authenticate()
        # Re-authenticate if token is older than 23 hours
        elif (datetime.now() - self.token_expiry).total_seconds() > 82800:
            await self.authenticate()

    def _get_auth_headers(self) -> Dict[str, str]:
        """Get headers with authentication"""
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.access_token}"
        }

    # ==================== Account APIs ====================

    async def get_account_balance(self) -> Optional[Dict[str, Any]]:
        """Get account balance and buying power"""
        await self._ensure_authenticated()
        if not self.access_token:
            return None

        try:
            session = await self._get_session()
            async with session.get(
                f"{self.api_url}/api/v2/account/balance",
                headers=self._get_auth_headers(),
                params={"account": self.trading_account}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        return data["data"]
                return None
        except Exception as e:
            logger.error(f"Error getting account balance: {e}")
            return None

    async def get_portfolio(self) -> Optional[List[Dict[str, Any]]]:
        """Get current portfolio positions"""
        await self._ensure_authenticated()
        if not self.access_token:
            return None

        try:
            session = await self._get_session()
            async with session.get(
                f"{self.api_url}/api/v2/account/portfolio",
                headers=self._get_auth_headers(),
                params={"account": self.trading_account}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        return data["data"]
                return None
        except Exception as e:
            logger.error(f"Error getting portfolio: {e}")
            return None

    # ==================== Trading APIs ====================

    async def place_order(
        self,
        symbol: str,
        side: str,  # "B" for buy, "S" for sell
        quantity: int,
        price: float,
        order_type: str = "LO"  # LO=Limit, MP=Market, ATO, ATC
    ) -> Optional[Dict[str, Any]]:
        """
        Place a new order
        Returns order details if successful
        """
        await self._ensure_authenticated()
        if not self.access_token:
            logger.error("Not authenticated - cannot place order")
            return None

        try:
            session = await self._get_session()
            order_data = {
                "account": self.trading_account,
                "symbol": symbol,
                "side": side,
                "quantity": quantity,
                "price": price,
                "orderType": order_type,
                "marketID": "VN"  # Vietnam market
            }

            async with session.post(
                f"{self.api_url}/api/v2/trading/order",
                headers=self._get_auth_headers(),
                json=order_data
            ) as response:
                data = await response.json()
                if response.status == 200 and data.get("status") == "success":
                    logger.info(f"Order placed: {side} {quantity} {symbol} @ {price}")
                    return data["data"]
                else:
                    logger.error(f"Order failed: {data.get('message')}")
                    return None
        except Exception as e:
            logger.error(f"Error placing order: {e}")
            return None

    async def cancel_order(self, order_id: str) -> bool:
        """Cancel an existing order"""
        await self._ensure_authenticated()
        if not self.access_token:
            return False

        try:
            session = await self._get_session()
            async with session.delete(
                f"{self.api_url}/api/v2/trading/order/{order_id}",
                headers=self._get_auth_headers(),
                params={"account": self.trading_account}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    return data.get("status") == "success"
                return False
        except Exception as e:
            logger.error(f"Error cancelling order: {e}")
            return False

    async def get_order_history(
        self,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None
    ) -> Optional[List[Dict[str, Any]]]:
        """Get order history"""
        await self._ensure_authenticated()
        if not self.access_token:
            return None

        try:
            session = await self._get_session()
            params = {"account": self.trading_account}
            if from_date:
                params["fromDate"] = from_date
            if to_date:
                params["toDate"] = to_date

            async with session.get(
                f"{self.api_url}/api/v2/trading/orders",
                headers=self._get_auth_headers(),
                params=params
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        return data["data"]
                return None
        except Exception as e:
            logger.error(f"Error getting order history: {e}")
            return None

    # ==================== Market Data APIs ====================

    async def get_stock_info(self, symbol: str) -> Optional[Dict[str, Any]]:
        """Get stock information"""
        await self._ensure_authenticated()
        if not self.access_token:
            return None

        try:
            session = await self._get_session()
            async with session.get(
                f"{self.data_url}/api/v2/market/stock/{symbol}",
                headers=self._get_auth_headers()
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("status") == "success":
                        return data["data"]
                return None
        except Exception as e:
            logger.error(f"Error getting stock info: {e}")
            return None

    # ==================== WebSocket Streaming ====================

    async def stream_market_data(self, symbols: List[str], callback):
        """
        Stream real-time market data via WebSocket
        callback: async function(data) to handle incoming data
        """
        await self._ensure_authenticated()
        if not self.access_token:
            logger.error("Not authenticated - cannot stream")
            return

        try:
            uri = f"{self.stream_url}?token={self.access_token}"
            async with websockets.connect(uri) as websocket:
                # Subscribe to symbols
                subscribe_msg = {
                    "type": "subscribe",
                    "symbols": symbols
                }
                await websocket.send(json.dumps(subscribe_msg))
                logger.info(f"Subscribed to: {symbols}")

                # Listen for messages
                async for message in websocket:
                    data = json.loads(message)
                    await callback(data)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")


# Singleton instance
ssi_api = SSIApiService()
