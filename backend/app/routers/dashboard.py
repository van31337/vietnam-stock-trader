"""
Dashboard API Routes
Endpoints for the frontend dashboard
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from pydantic import BaseModel
from loguru import logger

from ..database import get_db
from ..models.portfolio import Portfolio, PortfolioHistory
from ..models.balance import Balance, BalanceHistory
from ..models.trade import Trade, TradeSignal
from ..services.market_data import market_data
from ..services.news import news_service
from ..services.scheduler import trading_scheduler
from ..config import settings, is_ssi_configured

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


# ============ Pydantic Models ============

class DashboardSummary(BaseModel):
    total_portfolio_value: float
    cash_balance: float
    total_invested: float
    total_pnl: float
    total_pnl_percent: float
    num_positions: int
    market_status: str
    ssi_connected: bool
    auto_trading_enabled: bool
    last_updated: datetime


class PerformanceData(BaseModel):
    date: str
    value: float
    pnl: float
    pnl_percent: float


class RecentActivity(BaseModel):
    type: str  # "trade", "signal", "deposit"
    description: str
    timestamp: datetime
    symbol: Optional[str] = None
    amount: Optional[float] = None


# ============ Endpoints ============

@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(db: AsyncSession = Depends(get_db)):
    """Get complete dashboard summary"""
    try:
        # Get positions
        pos_result = await db.execute(
            select(Portfolio).where(Portfolio.quantity > 0)
        )
        positions = pos_result.scalars().all()

        # Calculate portfolio value
        total_value = 0.0
        total_cost = 0.0

        for pos in positions:
            price = await market_data.get_current_price(pos.symbol)
            if price:
                total_value += price * pos.quantity
            else:
                total_value += pos.total_cost
            total_cost += pos.total_cost

        # Get cash balance
        balance_result = await db.execute(select(Balance).limit(1))
        balance = balance_result.scalar_one_or_none()
        cash = balance.cash_balance if balance else 0.0

        total_portfolio = total_value + cash
        total_pnl = total_value - total_cost
        pnl_percent = (total_pnl / total_cost * 100) if total_cost > 0 else 0

        return DashboardSummary(
            total_portfolio_value=total_portfolio,
            cash_balance=cash,
            total_invested=total_cost,
            total_pnl=total_pnl,
            total_pnl_percent=pnl_percent,
            num_positions=len(positions),
            market_status="OPEN" if trading_scheduler.is_market_open() else "CLOSED",
            ssi_connected=is_ssi_configured(),
            auto_trading_enabled=settings.enable_auto_trading,
            last_updated=datetime.now()
        )

    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_performance_data(
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get portfolio performance over time"""
    try:
        start_date = datetime.now() - timedelta(days=days)
        result = await db.execute(
            select(PortfolioHistory)
            .where(PortfolioHistory.date >= start_date)
            .order_by(PortfolioHistory.date)
        )
        history = result.scalars().all()

        return [
            {
                "date": h.date.strftime("%Y-%m-%d"),
                "value": h.total_value,
                "pnl": h.total_pnl,
                "pnl_percent": h.total_pnl_percent
            }
            for h in history
        ]
    except Exception as e:
        logger.error(f"Error getting performance data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/activity", response_model=List[RecentActivity])
async def get_recent_activity(
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Get recent trading activity"""
    try:
        activities = []

        # Get recent trades
        trades_result = await db.execute(
            select(Trade)
            .order_by(desc(Trade.created_at))
            .limit(limit // 2)
        )
        trades = trades_result.scalars().all()

        for trade in trades:
            activities.append(RecentActivity(
                type="trade",
                description=f"{trade.trade_type.value} {trade.quantity} {trade.symbol} @ {trade.price:,.0f}",
                timestamp=trade.created_at,
                symbol=trade.symbol,
                amount=trade.total_value
            ))

        # Get recent signals
        signals_result = await db.execute(
            select(TradeSignal)
            .order_by(desc(TradeSignal.created_at))
            .limit(limit // 2)
        )
        signals = signals_result.scalars().all()

        for signal in signals:
            activities.append(RecentActivity(
                type="signal",
                description=f"{signal.signal_type.value} signal for {signal.symbol} (conf: {signal.confidence:.0%})",
                timestamp=signal.created_at,
                symbol=signal.symbol
            ))

        # Sort by timestamp
        activities.sort(key=lambda x: x.timestamp, reverse=True)
        return activities[:limit]

    except Exception as e:
        logger.error(f"Error getting recent activity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/watchlist")
async def get_watchlist():
    """Get VN30 watchlist with current prices"""
    try:
        symbols = await market_data.get_vn30_symbols()
        watchlist = []

        for symbol in symbols[:15]:  # Limit for performance
            try:
                price = await market_data.get_current_price(symbol)
                if price:
                    watchlist.append({
                        "symbol": symbol,
                        "price": price,
                        "in_portfolio": False  # TODO: Check portfolio
                    })
            except Exception:
                continue

        return watchlist
    except Exception as e:
        logger.error(f"Error getting watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/news-feed")
async def get_news_feed(limit: int = 10):
    """Get latest news for dashboard"""
    try:
        articles = await news_service.fetch_all_news()
        return [
            {
                "title": a.get("title", ""),
                "source": a.get("source", ""),
                "url": a.get("url", ""),
                "published": a.get("published_at").isoformat() if a.get("published_at") else None,
                "symbols": a.get("symbols", [])
            }
            for a in articles[:limit]
        ]
    except Exception as e:
        logger.error(f"Error getting news feed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_trading_stats(db: AsyncSession = Depends(get_db)):
    """Get trading statistics"""
    try:
        # Total trades
        trades_count = await db.execute(
            select(func.count(Trade.id))
        )
        total_trades = trades_count.scalar() or 0

        # Winning trades
        # This is simplified - would need more complex P&L tracking
        trades_result = await db.execute(select(Trade))
        trades = trades_result.scalars().all()

        winning = 0
        total_profit = 0.0
        total_loss = 0.0

        # Calculate statistics from balance history
        balance_result = await db.execute(select(Balance).limit(1))
        balance = balance_result.scalar_one_or_none()

        return {
            "total_trades": total_trades,
            "winning_trades": winning,
            "win_rate": (winning / total_trades * 100) if total_trades > 0 else 0,
            "total_profit": total_profit,
            "total_loss": total_loss,
            "net_profit": total_profit - total_loss,
            "total_deposits": balance.total_deposits if balance else 0,
            "total_commissions": balance.total_commissions_paid if balance else 0
        }
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/settings")
async def get_settings():
    """Get current trading settings"""
    return {
        "monthly_budget": settings.monthly_budget_vnd,
        "max_positions": settings.max_stocks_in_portfolio,
        "max_loss_percent": settings.max_loss_per_trade_percent,
        "auto_trading_enabled": settings.enable_auto_trading,
        "ssi_configured": is_ssi_configured(),
        "market_hours": {
            "open": f"{settings.market_open_hour:02d}:{settings.market_open_minute:02d}",
            "close": f"{settings.market_close_hour:02d}:{settings.market_close_minute:02d}"
        }
    }


@router.get("/health")
async def health_check():
    """API health check"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "market_open": trading_scheduler.is_market_open()
    }
