"""
Market Data API Routes
Endpoints for market data, news, and stock information
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from loguru import logger

from ..services.market_data import market_data
from ..services.news import news_service

router = APIRouter(prefix="/market", tags=["market"])


# ============ Pydantic Models ============

class StockQuote(BaseModel):
    symbol: str
    price: float
    change: Optional[float]
    change_percent: Optional[float]
    volume: Optional[int]
    high: Optional[float]
    low: Optional[float]
    open: Optional[float]


class NewsArticle(BaseModel):
    title: str
    url: str
    source: str
    summary: Optional[str]
    published_at: Optional[datetime]
    symbols: List[str]
    sentiment: Optional[str] = None


class MarketOverview(BaseModel):
    index_name: str
    value: float
    change: float
    change_percent: float
    volume: int
    market_status: str
    last_updated: datetime


# ============ Endpoints ============

@router.get("/overview", response_model=MarketOverview)
async def get_market_overview():
    """Get Vietnam market overview (VN-Index)"""
    try:
        overview = await market_data.get_market_overview()
        if not overview:
            raise HTTPException(
                status_code=503,
                detail="Market data unavailable"
            )

        # Determine market status
        from ..services.scheduler import trading_scheduler
        is_open = trading_scheduler.is_market_open()
        status = "OPEN" if is_open else "CLOSED"

        return MarketOverview(
            index_name=overview.get("index", "VN-Index"),
            value=overview.get("value", 0),
            change=overview.get("change", 0),
            change_percent=overview.get("change_percent", 0),
            volume=overview.get("volume", 0),
            market_status=status,
            last_updated=datetime.now()
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting market overview: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/vn30")
async def get_vn30_stocks():
    """Get list of VN30 stocks with current prices"""
    try:
        symbols = await market_data.get_vn30_symbols()
        stocks = []

        for symbol in symbols[:10]:  # Limit for performance
            try:
                price = await market_data.get_current_price(symbol)
                if price:
                    stocks.append({
                        "symbol": symbol,
                        "price": price
                    })
            except Exception:
                continue

        return {"stocks": stocks, "total": len(symbols)}
    except Exception as e:
        logger.error(f"Error getting VN30: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/quote/{symbol}", response_model=StockQuote)
async def get_stock_quote(symbol: str):
    """Get current quote for a stock"""
    try:
        # Get recent price data
        df = await market_data.get_stock_price(
            symbol,
            start_date=(datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        )

        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for {symbol}"
            )

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        change = float(latest['close'] - prev['close'])
        change_pct = (change / prev['close'] * 100) if prev['close'] > 0 else 0

        return StockQuote(
            symbol=symbol.upper(),
            price=float(latest['close']),
            change=change,
            change_percent=change_pct,
            volume=int(latest['volume']),
            high=float(latest['high']),
            low=float(latest['low']),
            open=float(latest['open'])
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting quote for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{symbol}")
async def get_price_history(
    symbol: str,
    days: int = Query(default=30, ge=1, le=365)
):
    """Get historical price data for a stock"""
    try:
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        df = await market_data.get_stock_price(symbol, start_date=start_date)

        if df.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for {symbol}"
            )

        # Add technical indicators
        df = await market_data.calculate_technical_indicators(df)

        # Convert to list of dicts
        data = []
        for idx, row in df.iterrows():
            data.append({
                "date": str(idx) if hasattr(idx, '__str__') else str(row.get('time', idx)),
                "open": float(row['open']),
                "high": float(row['high']),
                "low": float(row['low']),
                "close": float(row['close']),
                "volume": int(row['volume']),
                "sma_20": float(row['SMA_20']) if 'SMA_20' in row and not pd.isna(row['SMA_20']) else None,
                "sma_50": float(row['SMA_50']) if 'SMA_50' in row and not pd.isna(row['SMA_50']) else None,
                "rsi": float(row['RSI_14']) if 'RSI_14' in row and not pd.isna(row['RSI_14']) else None
            })

        return {"symbol": symbol, "data": data}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting history for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/company/{symbol}")
async def get_company_info(symbol: str):
    """Get company profile and information"""
    try:
        profile = await market_data.get_company_profile(symbol)
        if not profile:
            raise HTTPException(
                status_code=404,
                detail=f"No company info for {symbol}"
            )
        return profile
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting company info for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/financials/{symbol}")
async def get_financials(symbol: str):
    """Get financial ratios for a stock"""
    try:
        ratios = await market_data.get_financial_ratios(symbol)
        if ratios.empty:
            raise HTTPException(
                status_code=404,
                detail=f"No financial data for {symbol}"
            )
        return ratios.to_dict('records')
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting financials for {symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news", response_model=List[NewsArticle])
async def get_news(
    symbol: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100)
):
    """Get latest financial news"""
    try:
        if symbol:
            articles = await news_service.fetch_news_for_symbol(symbol)
        else:
            articles = await news_service.fetch_all_news()

        # Analyze sentiment for each article
        result = []
        for article in articles[:limit]:
            sentiment = await news_service.analyze_sentiment(
                article.get("title", "") + " " + article.get("summary", "")
            )
            result.append(NewsArticle(
                title=article.get("title", ""),
                url=article.get("url", ""),
                source=article.get("source", ""),
                summary=article.get("summary"),
                published_at=article.get("published_at"),
                symbols=article.get("symbols", []),
                sentiment=sentiment.get("label")
            ))

        return result
    except Exception as e:
        logger.error(f"Error getting news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/sentiment")
async def get_market_sentiment():
    """Get overall market sentiment from news"""
    try:
        sentiment = await news_service.get_market_sentiment()
        return {
            "sentiment": sentiment.get("label", "NEUTRAL"),
            "score": sentiment.get("score", 0),
            "num_articles": sentiment.get("num_articles", 0),
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        logger.error(f"Error getting sentiment: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Import pandas for type checking
import pandas as pd
