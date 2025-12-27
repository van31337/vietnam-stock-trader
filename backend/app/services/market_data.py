"""
Market Data Service using vnstock library
Documentation: https://docs.vnstock.site/
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from loguru import logger
import pandas as pd
import numpy as np

# Technical analysis
import ta

# vnstock for Vietnamese market data
try:
    from vnstock import Vnstock
    VNSTOCK_AVAILABLE = True
except ImportError:
    VNSTOCK_AVAILABLE = False
    logger.warning("vnstock not installed. Run: pip install vnstock")


class MarketDataService:
    """Service for fetching Vietnamese stock market data"""

    def __init__(self, source: str = "VCI"):
        """
        Initialize market data service

        Args:
            source: Data source - "VCI" (default), "TCBS", "SSI"
        """
        self.source = source
        self._stock_client = None
        if VNSTOCK_AVAILABLE:
            self._init_client()

    def _init_client(self, symbol: str = "VNM"):
        """Initialize vnstock client"""
        try:
            self._stock_client = Vnstock().stock(symbol=symbol, source=self.source)
        except Exception as e:
            logger.error(f"Failed to initialize vnstock: {e}")

    def _get_client(self, symbol: str):
        """Get vnstock client for a specific symbol"""
        if not VNSTOCK_AVAILABLE:
            raise RuntimeError("vnstock library not available")
        return Vnstock().stock(symbol=symbol, source=self.source)

    async def get_vn30_symbols(self) -> List[str]:
        """Get list of VN30 index components"""
        try:
            # VN30 components (blue-chip stocks)
            vn30 = [
                "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR",
                "HDB", "HPG", "MBB", "MSN", "MWG", "NVL", "PDR", "PLX",
                "PNJ", "POW", "SAB", "SSI", "STB", "TCB", "TPB", "VCB",
                "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"
            ]
            return vn30
        except Exception as e:
            logger.error(f"Error getting VN30 symbols: {e}")
            return []

    async def get_stock_list(self, exchange: str = "HOSE") -> pd.DataFrame:
        """
        Get list of all stocks on an exchange

        Args:
            exchange: "HOSE", "HNX", or "UPCOM"
        """
        try:
            stock = Vnstock().stock(symbol="VNM", source=self.source)
            listing = stock.listing.all_symbols()
            if exchange:
                listing = listing[listing['exchange'] == exchange]
            return listing
        except Exception as e:
            logger.error(f"Error getting stock list: {e}")
            return pd.DataFrame()

    async def get_stock_price(
        self,
        symbol: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        interval: str = "1D"
    ) -> pd.DataFrame:
        """
        Get historical stock prices

        Args:
            symbol: Stock symbol (e.g., "VNM", "FPT")
            start_date: Start date in "YYYY-MM-DD" format
            end_date: End date in "YYYY-MM-DD" format
            interval: "1D" for daily, "1W" for weekly
        """
        try:
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            if not start_date:
                start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")

            stock = self._get_client(symbol)
            df = stock.quote.history(
                start=start_date,
                end=end_date,
                interval=interval
            )
            return df
        except Exception as e:
            logger.error(f"Error getting price for {symbol}: {e}")
            return pd.DataFrame()

    async def get_current_price(self, symbol: str) -> Optional[float]:
        """Get the current/latest price for a stock"""
        try:
            df = await self.get_stock_price(
                symbol,
                start_date=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
            )
            if not df.empty:
                return float(df['close'].iloc[-1])
            return None
        except Exception as e:
            logger.error(f"Error getting current price for {symbol}: {e}")
            return None

    async def get_intraday_data(self, symbol: str) -> pd.DataFrame:
        """Get intraday trading data"""
        try:
            stock = self._get_client(symbol)
            df = stock.quote.intraday()
            return df
        except Exception as e:
            logger.error(f"Error getting intraday data for {symbol}: {e}")
            return pd.DataFrame()

    async def get_company_profile(self, symbol: str) -> Dict[str, Any]:
        """Get company profile and overview"""
        try:
            stock = self._get_client(symbol)
            profile = stock.company.profile()
            return profile.to_dict('records')[0] if not profile.empty else {}
        except Exception as e:
            logger.error(f"Error getting company profile for {symbol}: {e}")
            return {}

    async def get_financial_ratios(self, symbol: str) -> pd.DataFrame:
        """Get financial ratios (P/E, P/B, ROE, etc.)"""
        try:
            stock = self._get_client(symbol)
            ratios = stock.finance.ratio()
            return ratios
        except Exception as e:
            logger.error(f"Error getting financial ratios for {symbol}: {e}")
            return pd.DataFrame()

    async def calculate_technical_indicators(
        self,
        df: pd.DataFrame
    ) -> pd.DataFrame:
        """
        Calculate technical indicators for price data

        Returns DataFrame with added columns:
        - SMA_20, SMA_50, SMA_200
        - RSI_14
        - MACD, MACD_signal, MACD_hist
        - Bollinger Bands
        - ATR
        """
        if df.empty:
            return df

        try:
            df = df.copy()

            # Simple Moving Averages
            df['SMA_20'] = ta.trend.sma_indicator(df['close'], window=20)
            df['SMA_50'] = ta.trend.sma_indicator(df['close'], window=50)
            df['SMA_200'] = ta.trend.sma_indicator(df['close'], window=200)

            # RSI
            df['RSI_14'] = ta.momentum.rsi(df['close'], window=14)

            # MACD
            macd = ta.trend.MACD(df['close'])
            df['MACD'] = macd.macd()
            df['MACD_signal'] = macd.macd_signal()
            df['MACD_hist'] = macd.macd_diff()

            # Bollinger Bands
            bollinger = ta.volatility.BollingerBands(df['close'])
            df['BB_upper'] = bollinger.bollinger_hband()
            df['BB_middle'] = bollinger.bollinger_mavg()
            df['BB_lower'] = bollinger.bollinger_lband()

            # Average True Range
            df['ATR'] = ta.volatility.average_true_range(
                df['high'], df['low'], df['close']
            )

            # Volume indicators
            df['Volume_SMA_20'] = ta.trend.sma_indicator(df['volume'], window=20)

            return df
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {e}")
            return df

    async def get_market_overview(self) -> Dict[str, Any]:
        """Get overall market overview (VN-Index, etc.)"""
        try:
            stock = Vnstock().stock(symbol="VNINDEX", source=self.source)
            df = stock.quote.history(
                start=(datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
                end=datetime.now().strftime("%Y-%m-%d")
            )
            if not df.empty:
                current = df.iloc[-1]
                prev = df.iloc[-2] if len(df) > 1 else current
                return {
                    "index": "VN-Index",
                    "value": float(current['close']),
                    "change": float(current['close'] - prev['close']),
                    "change_percent": float((current['close'] - prev['close']) / prev['close'] * 100),
                    "volume": int(current['volume']),
                    "date": str(current.name if hasattr(current, 'name') else datetime.now())
                }
            return {}
        except Exception as e:
            logger.error(f"Error getting market overview: {e}")
            return {}

    async def screen_stocks(
        self,
        min_volume: int = 100000,
        min_price: float = 10000,
        max_price: float = 200000,
        exchange: str = "HOSE"
    ) -> List[Dict[str, Any]]:
        """
        Screen stocks based on criteria

        Args:
            min_volume: Minimum average daily volume
            min_price: Minimum price in VND
            max_price: Maximum price in VND
            exchange: Stock exchange
        """
        try:
            results = []
            stocks = await self.get_stock_list(exchange)

            for _, stock in stocks.iterrows():
                symbol = stock['symbol']
                try:
                    price_df = await self.get_stock_price(symbol)
                    if price_df.empty:
                        continue

                    current_price = price_df['close'].iloc[-1]
                    avg_volume = price_df['volume'].tail(20).mean()

                    if (min_volume <= avg_volume and
                        min_price <= current_price <= max_price):
                        results.append({
                            "symbol": symbol,
                            "price": current_price,
                            "avg_volume": avg_volume,
                            "exchange": exchange
                        })
                except Exception:
                    continue

            return results
        except Exception as e:
            logger.error(f"Error screening stocks: {e}")
            return []


# Singleton instance
market_data = MarketDataService()
