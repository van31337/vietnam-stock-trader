"""
Trading Strategy Engine
Generates buy/sell signals based on technical analysis, sentiment, and fundamentals
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
from loguru import logger
import pandas as pd
import numpy as np

from .market_data import market_data, MarketDataService
from .news import news_service, NewsService
from ..config import settings


class SignalStrength(Enum):
    STRONG_BUY = 2
    BUY = 1
    HOLD = 0
    SELL = -1
    STRONG_SELL = -2


@dataclass
class TradingSignal:
    """Trading signal with all relevant information"""
    symbol: str
    signal: SignalStrength
    confidence: float  # 0-1
    price: float
    target_price: Optional[float]
    stop_loss: Optional[float]
    technical_score: float
    sentiment_score: float
    fundamental_score: float
    reasons: List[str]
    created_at: datetime


class StrategyEngine:
    """
    Trading strategy engine that combines:
    - Technical Analysis (price patterns, indicators)
    - Sentiment Analysis (news)
    - Fundamental Analysis (financial ratios)

    Strategy for $100/month investment:
    - Focus on VN30 blue-chip stocks for liquidity
    - DCA (Dollar Cost Averaging) approach
    - Maximum 5 stocks in portfolio
    - Risk management: 2% max loss per trade
    """

    def __init__(
        self,
        market_data_service: MarketDataService = None,
        news_service_instance: NewsService = None
    ):
        self.market_data = market_data_service or market_data
        self.news_service = news_service_instance or news_service

        # Strategy parameters
        self.max_positions = settings.max_stocks_in_portfolio
        self.max_loss_percent = settings.max_loss_per_trade_percent
        self.monthly_budget = settings.monthly_budget_vnd

        # Technical indicator weights
        self.weights = {
            "rsi": 0.15,
            "macd": 0.15,
            "sma_crossover": 0.15,
            "bollinger": 0.10,
            "volume": 0.10,
            "sentiment": 0.20,
            "fundamental": 0.15
        }

    async def analyze_stock(self, symbol: str) -> Optional[TradingSignal]:
        """
        Comprehensive analysis of a single stock

        Returns TradingSignal with buy/sell recommendation
        """
        try:
            # Get price data with technical indicators
            price_df = await self.market_data.get_stock_price(symbol)
            if price_df.empty or len(price_df) < 50:
                logger.warning(f"Insufficient price data for {symbol}")
                return None

            price_df = await self.market_data.calculate_technical_indicators(price_df)

            # Get current price
            current_price = float(price_df['close'].iloc[-1])

            # Calculate technical score
            technical_score, tech_reasons = self._calculate_technical_score(price_df)

            # Calculate sentiment score
            sentiment_score, sent_reasons = await self._calculate_sentiment_score(symbol)

            # Calculate fundamental score
            fundamental_score, fund_reasons = await self._calculate_fundamental_score(symbol)

            # Combine scores
            total_score = (
                technical_score * 0.4 +
                sentiment_score * 0.35 +
                fundamental_score * 0.25
            )

            # Determine signal
            signal = self._score_to_signal(total_score)
            confidence = min(abs(total_score) / 100, 1.0)

            # Calculate target and stop loss
            target_price, stop_loss = self._calculate_targets(
                price_df, signal, current_price
            )

            # Combine reasons
            all_reasons = tech_reasons + sent_reasons + fund_reasons

            return TradingSignal(
                symbol=symbol,
                signal=signal,
                confidence=confidence,
                price=current_price,
                target_price=target_price,
                stop_loss=stop_loss,
                technical_score=technical_score,
                sentiment_score=sentiment_score,
                fundamental_score=fundamental_score,
                reasons=all_reasons,
                created_at=datetime.now()
            )

        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {e}")
            return None

    def _calculate_technical_score(
        self,
        df: pd.DataFrame
    ) -> Tuple[float, List[str]]:
        """
        Calculate technical analysis score

        Returns score (-100 to 100) and list of reasons
        """
        score = 0.0
        reasons = []
        latest = df.iloc[-1]

        # 1. RSI Analysis (0-100, oversold < 30, overbought > 70)
        if 'RSI_14' in df.columns and not pd.isna(latest['RSI_14']):
            rsi = latest['RSI_14']
            if rsi < 30:
                score += 20
                reasons.append(f"RSI oversold ({rsi:.1f})")
            elif rsi < 40:
                score += 10
                reasons.append(f"RSI low ({rsi:.1f})")
            elif rsi > 70:
                score -= 20
                reasons.append(f"RSI overbought ({rsi:.1f})")
            elif rsi > 60:
                score -= 10
                reasons.append(f"RSI high ({rsi:.1f})")

        # 2. MACD Analysis
        if all(col in df.columns for col in ['MACD', 'MACD_signal']):
            macd = latest['MACD']
            signal_line = latest['MACD_signal']
            if not pd.isna(macd) and not pd.isna(signal_line):
                if macd > signal_line:
                    if df['MACD'].iloc[-2] <= df['MACD_signal'].iloc[-2]:
                        score += 20
                        reasons.append("MACD bullish crossover")
                    else:
                        score += 10
                        reasons.append("MACD above signal")
                else:
                    if df['MACD'].iloc[-2] >= df['MACD_signal'].iloc[-2]:
                        score -= 20
                        reasons.append("MACD bearish crossover")
                    else:
                        score -= 10
                        reasons.append("MACD below signal")

        # 3. SMA Crossover (20 vs 50)
        if all(col in df.columns for col in ['SMA_20', 'SMA_50']):
            sma20 = latest['SMA_20']
            sma50 = latest['SMA_50']
            if not pd.isna(sma20) and not pd.isna(sma50):
                if sma20 > sma50:
                    score += 15
                    reasons.append("SMA20 > SMA50 (bullish)")
                else:
                    score -= 15
                    reasons.append("SMA20 < SMA50 (bearish)")

                # Price vs SMA
                price = latest['close']
                if price > sma20:
                    score += 5
                else:
                    score -= 5

        # 4. Bollinger Bands
        if all(col in df.columns for col in ['BB_upper', 'BB_lower', 'BB_middle']):
            price = latest['close']
            bb_upper = latest['BB_upper']
            bb_lower = latest['BB_lower']
            if not pd.isna(bb_upper) and not pd.isna(bb_lower):
                if price < bb_lower:
                    score += 15
                    reasons.append("Price below lower Bollinger Band")
                elif price > bb_upper:
                    score -= 15
                    reasons.append("Price above upper Bollinger Band")

        # 5. Volume Analysis
        if 'Volume_SMA_20' in df.columns:
            vol = latest['volume']
            vol_sma = latest['Volume_SMA_20']
            if not pd.isna(vol_sma) and vol_sma > 0:
                vol_ratio = vol / vol_sma
                if vol_ratio > 1.5:
                    score += 10
                    reasons.append(f"High volume ({vol_ratio:.1f}x avg)")
                elif vol_ratio < 0.5:
                    score -= 5
                    reasons.append(f"Low volume ({vol_ratio:.1f}x avg)")

        # 6. Price trend (last 5 days)
        if len(df) >= 5:
            returns = (df['close'].iloc[-1] / df['close'].iloc[-5] - 1) * 100
            if returns > 5:
                score += 10
                reasons.append(f"Strong 5-day return (+{returns:.1f}%)")
            elif returns < -5:
                score -= 10
                reasons.append(f"Weak 5-day return ({returns:.1f}%)")

        return score, reasons

    async def _calculate_sentiment_score(
        self,
        symbol: str
    ) -> Tuple[float, List[str]]:
        """Calculate sentiment score from news"""
        score = 0.0
        reasons = []

        try:
            # Get news for this symbol
            articles = await self.news_service.fetch_news_for_symbol(symbol)

            if not articles:
                return 0.0, ["No recent news"]

            # Analyze sentiment
            sentiments = await self.news_service.analyze_news_sentiment(articles)
            if symbol in sentiments:
                sent_data = sentiments[symbol]
                sent_score = sent_data["score"]

                # Convert to -50 to 50 scale
                score = sent_score * 50

                if sent_data["label"] == "POSITIVE":
                    reasons.append(f"Positive news sentiment ({sent_data['num_articles']} articles)")
                elif sent_data["label"] == "NEGATIVE":
                    reasons.append(f"Negative news sentiment ({sent_data['num_articles']} articles)")
                else:
                    reasons.append(f"Neutral news ({sent_data['num_articles']} articles)")

        except Exception as e:
            logger.error(f"Error calculating sentiment for {symbol}: {e}")

        return score, reasons

    async def _calculate_fundamental_score(
        self,
        symbol: str
    ) -> Tuple[float, List[str]]:
        """Calculate fundamental analysis score"""
        score = 0.0
        reasons = []

        try:
            ratios = await self.market_data.get_financial_ratios(symbol)
            if ratios.empty:
                return 0.0, ["No fundamental data"]

            latest = ratios.iloc[-1] if len(ratios) > 0 else None
            if latest is None:
                return 0.0, ["No fundamental data"]

            # P/E Ratio (lower is better, but not too low)
            if 'priceToEarning' in ratios.columns:
                pe = latest.get('priceToEarning')
                if pe and not pd.isna(pe):
                    if 5 < pe < 15:
                        score += 15
                        reasons.append(f"Attractive P/E ({pe:.1f})")
                    elif pe > 30:
                        score -= 10
                        reasons.append(f"High P/E ({pe:.1f})")
                    elif pe < 0:
                        score -= 15
                        reasons.append("Negative earnings")

            # ROE (higher is better)
            if 'roe' in ratios.columns:
                roe = latest.get('roe')
                if roe and not pd.isna(roe):
                    if roe > 15:
                        score += 15
                        reasons.append(f"Strong ROE ({roe:.1f}%)")
                    elif roe < 5:
                        score -= 10
                        reasons.append(f"Weak ROE ({roe:.1f}%)")

            # Debt ratio (lower is better)
            if 'debtOnEquity' in ratios.columns:
                de = latest.get('debtOnEquity')
                if de and not pd.isna(de):
                    if de < 0.5:
                        score += 10
                        reasons.append(f"Low debt ({de:.2f})")
                    elif de > 2:
                        score -= 15
                        reasons.append(f"High debt ({de:.2f})")

        except Exception as e:
            logger.error(f"Error calculating fundamentals for {symbol}: {e}")

        return score, reasons

    def _score_to_signal(self, score: float) -> SignalStrength:
        """Convert numerical score to signal strength"""
        if score >= 50:
            return SignalStrength.STRONG_BUY
        elif score >= 20:
            return SignalStrength.BUY
        elif score <= -50:
            return SignalStrength.STRONG_SELL
        elif score <= -20:
            return SignalStrength.SELL
        else:
            return SignalStrength.HOLD

    def _calculate_targets(
        self,
        df: pd.DataFrame,
        signal: SignalStrength,
        current_price: float
    ) -> Tuple[Optional[float], Optional[float]]:
        """Calculate target price and stop loss"""
        if signal in [SignalStrength.HOLD]:
            return None, None

        # Use ATR for volatility-based targets
        atr = df['ATR'].iloc[-1] if 'ATR' in df.columns else current_price * 0.02

        if signal in [SignalStrength.STRONG_BUY, SignalStrength.BUY]:
            target = current_price + (atr * 3)  # 3x ATR target
            stop_loss = current_price - (atr * 1.5)  # 1.5x ATR stop
        else:
            target = current_price - (atr * 3)
            stop_loss = current_price + (atr * 1.5)

        return target, stop_loss

    async def get_top_picks(self, num_picks: int = 5) -> List[TradingSignal]:
        """
        Get top stock picks from VN30

        Returns list of buy signals sorted by confidence
        """
        vn30 = await self.market_data.get_vn30_symbols()
        signals = []

        for symbol in vn30:
            try:
                signal = await self.analyze_stock(symbol)
                if signal and signal.signal in [SignalStrength.STRONG_BUY, SignalStrength.BUY]:
                    signals.append(signal)
            except Exception as e:
                logger.error(f"Error analyzing {symbol}: {e}")
                continue

        # Sort by confidence (highest first)
        signals.sort(key=lambda x: x.confidence, reverse=True)
        return signals[:num_picks]

    async def calculate_position_size(
        self,
        available_cash: float,
        stock_price: float,
        num_stocks_to_buy: int = 1
    ) -> int:
        """
        Calculate how many shares to buy based on budget

        For $100/month (~2.5M VND), with 5 stocks max:
        ~500K VND per position
        """
        # Budget per position
        budget_per_position = available_cash / num_stocks_to_buy

        # Vietnam stocks trade in lots of 100
        lot_size = 100

        # Calculate shares
        shares = int(budget_per_position / stock_price)

        # Round down to nearest lot
        shares = (shares // lot_size) * lot_size

        # Minimum 100 shares
        return max(shares, lot_size) if shares >= lot_size else 0


# Singleton instance
strategy_engine = StrategyEngine()
