"""
Trading API Routes
Endpoints for trade execution and order management
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from loguru import logger

from ..database import get_db
from ..models.trade import Trade, TradeSignal, TradeType, TradeStatus, SignalType
from ..models.portfolio import Portfolio
from ..models.balance import Balance, BalanceHistory, TransactionType
from ..services.ssi_api import ssi_api
from ..services.strategy import strategy_engine, SignalStrength
from ..services.market_data import market_data
from ..services.notifications import notification_service
from ..config import settings, is_ssi_configured

router = APIRouter(prefix="/trading", tags=["trading"])


# ============ Pydantic Models ============

class OrderRequest(BaseModel):
    symbol: str
    side: str  # "BUY" or "SELL"
    quantity: int
    price: Optional[float] = None  # None for market order
    order_type: str = "LO"  # LO=Limit, MP=Market


class TradeResponse(BaseModel):
    id: int
    order_id: Optional[str]
    symbol: str
    trade_type: str
    quantity: int
    price: float
    total_value: float
    status: str
    executed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class SignalResponse(BaseModel):
    id: int
    symbol: str
    signal_type: str
    confidence: float
    price_at_signal: float
    target_price: Optional[float]
    stop_loss_price: Optional[float]
    technical_score: Optional[float]
    sentiment_score: Optional[float]
    analysis: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class AnalysisRequest(BaseModel):
    symbol: str


# ============ Endpoints ============

@router.post("/order")
async def place_order(
    order: OrderRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Place a new order

    For live trading, requires SSI API credentials.
    Otherwise, simulates the trade locally.
    """
    try:
        # Validate side
        if order.side not in ["BUY", "SELL"]:
            raise HTTPException(status_code=400, detail="Side must be BUY or SELL")

        # Get current price if not provided
        price = order.price
        if not price:
            price = await market_data.get_current_price(order.symbol)
            if not price:
                raise HTTPException(
                    status_code=400,
                    detail=f"Could not get price for {order.symbol}"
                )

        total_value = price * order.quantity
        trade_type = TradeType.BUY if order.side == "BUY" else TradeType.SELL

        # Check balance for buy orders
        if trade_type == TradeType.BUY:
            balance_result = await db.execute(select(Balance).limit(1))
            balance = balance_result.scalar_one_or_none()
            if not balance or balance.cash_balance < total_value:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient balance. Need {total_value:,.0f} VND"
                )

        # Check position for sell orders
        if trade_type == TradeType.SELL:
            pos_result = await db.execute(
                select(Portfolio).where(Portfolio.symbol == order.symbol)
            )
            position = pos_result.scalar_one_or_none()
            if not position or position.quantity < order.quantity:
                raise HTTPException(
                    status_code=400,
                    detail=f"Insufficient shares of {order.symbol}"
                )

        # Create trade record
        trade = Trade(
            symbol=order.symbol,
            trade_type=trade_type,
            quantity=order.quantity,
            price=price,
            total_value=total_value,
            commission=total_value * 0.0015,  # 0.15% commission
            status=TradeStatus.PENDING
        )

        if is_ssi_configured() and settings.enable_auto_trading:
            # Live trading via SSI
            ssi_side = "B" if order.side == "BUY" else "S"
            result = await ssi_api.place_order(
                symbol=order.symbol,
                side=ssi_side,
                quantity=order.quantity,
                price=price,
                order_type=order.order_type
            )
            if result:
                trade.order_id = result.get("orderId")
                trade.status = TradeStatus.PENDING
            else:
                trade.status = TradeStatus.REJECTED
                trade.reason = "SSI API rejected order"
        else:
            # Simulate trade (paper trading)
            trade.status = TradeStatus.FILLED
            trade.filled_quantity = order.quantity
            trade.filled_price = price
            trade.executed_at = datetime.now()
            trade.reason = "Simulated trade (paper trading)"

            # Update portfolio
            await _update_portfolio_after_trade(db, trade)

        db.add(trade)
        await db.commit()
        await db.refresh(trade)

        # Send notification
        await notification_service.notify_trade(
            action=order.side,
            symbol=order.symbol,
            quantity=order.quantity,
            price=price,
            total=total_value
        )

        return {
            "trade_id": trade.id,
            "order_id": trade.order_id,
            "status": trade.status.value,
            "message": "Order placed successfully"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error placing order: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _update_portfolio_after_trade(db: AsyncSession, trade: Trade):
    """Update portfolio and balance after a filled trade"""
    # Get or create position
    result = await db.execute(
        select(Portfolio).where(Portfolio.symbol == trade.symbol)
    )
    position = result.scalar_one_or_none()

    # Get balance
    balance_result = await db.execute(select(Balance).limit(1))
    balance = balance_result.scalar_one_or_none()
    if not balance:
        balance = Balance(cash_balance=0.0)
        db.add(balance)

    if trade.trade_type == TradeType.BUY:
        # Update position
        if position:
            # Calculate new average price
            total_shares = position.quantity + trade.quantity
            total_cost = position.total_cost + trade.total_value
            position.avg_buy_price = total_cost / total_shares
            position.quantity = total_shares
            position.total_cost = total_cost
        else:
            position = Portfolio(
                symbol=trade.symbol,
                quantity=trade.quantity,
                avg_buy_price=trade.price,
                total_cost=trade.total_value
            )
            db.add(position)

        # Deduct from balance
        old_balance = balance.cash_balance
        balance.cash_balance -= (trade.total_value + trade.commission)

        # Record transaction
        history = BalanceHistory(
            transaction_type=TransactionType.BUY,
            amount=-(trade.total_value + trade.commission),
            balance_before=old_balance,
            balance_after=balance.cash_balance,
            description=f"Buy {trade.quantity} {trade.symbol} @ {trade.price:,.0f}",
            reference_id=str(trade.id)
        )
        db.add(history)

    else:  # SELL
        if position:
            position.quantity -= trade.quantity
            if position.quantity > 0:
                position.total_cost = position.quantity * position.avg_buy_price

        # Add to balance
        old_balance = balance.cash_balance
        net_proceeds = trade.total_value - trade.commission
        balance.cash_balance += net_proceeds

        # Record transaction
        history = BalanceHistory(
            transaction_type=TransactionType.SELL,
            amount=net_proceeds,
            balance_before=old_balance,
            balance_after=balance.cash_balance,
            description=f"Sell {trade.quantity} {trade.symbol} @ {trade.price:,.0f}",
            reference_id=str(trade.id)
        )
        db.add(history)


@router.get("/trades", response_model=List[TradeResponse])
async def get_trades(
    limit: int = 50,
    symbol: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """Get trade history"""
    query = select(Trade).order_by(desc(Trade.created_at)).limit(limit)
    if symbol:
        query = query.where(Trade.symbol == symbol)

    result = await db.execute(query)
    trades = result.scalars().all()

    return [
        TradeResponse(
            id=t.id,
            order_id=t.order_id,
            symbol=t.symbol,
            trade_type=t.trade_type.value,
            quantity=t.quantity,
            price=t.price,
            total_value=t.total_value,
            status=t.status.value,
            executed_at=t.executed_at,
            created_at=t.created_at
        )
        for t in trades
    ]


@router.post("/analyze")
async def analyze_stock(
    request: AnalysisRequest,
    db: AsyncSession = Depends(get_db)
):
    """Analyze a stock and get trading signal"""
    try:
        signal = await strategy_engine.analyze_stock(request.symbol)
        if not signal:
            raise HTTPException(
                status_code=404,
                detail=f"Could not analyze {request.symbol}"
            )

        # Save signal to database
        db_signal = TradeSignal(
            symbol=signal.symbol,
            signal_type=SignalType[signal.signal.name],
            confidence=signal.confidence,
            price_at_signal=signal.price,
            target_price=signal.target_price,
            stop_loss_price=signal.stop_loss,
            technical_score=signal.technical_score,
            sentiment_score=signal.sentiment_score,
            fundamental_score=signal.fundamental_score,
            analysis="; ".join(signal.reasons)
        )
        db.add(db_signal)
        await db.commit()

        return {
            "symbol": signal.symbol,
            "signal": signal.signal.name,
            "confidence": signal.confidence,
            "price": signal.price,
            "target_price": signal.target_price,
            "stop_loss": signal.stop_loss,
            "scores": {
                "technical": signal.technical_score,
                "sentiment": signal.sentiment_score,
                "fundamental": signal.fundamental_score
            },
            "reasons": signal.reasons
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing {request.symbol}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals", response_model=List[SignalResponse])
async def get_signals(
    limit: int = 20,
    db: AsyncSession = Depends(get_db)
):
    """Get recent trading signals"""
    result = await db.execute(
        select(TradeSignal)
        .order_by(desc(TradeSignal.created_at))
        .limit(limit)
    )
    signals = result.scalars().all()

    return [
        SignalResponse(
            id=s.id,
            symbol=s.symbol,
            signal_type=s.signal_type.value,
            confidence=s.confidence,
            price_at_signal=s.price_at_signal,
            target_price=s.target_price,
            stop_loss_price=s.stop_loss_price,
            technical_score=s.technical_score,
            sentiment_score=s.sentiment_score,
            analysis=s.analysis,
            created_at=s.created_at
        )
        for s in signals
    ]


@router.get("/top-picks")
async def get_top_picks(num_picks: int = 5):
    """Get top stock recommendations"""
    try:
        picks = await strategy_engine.get_top_picks(num_picks)
        return [
            {
                "symbol": p.symbol,
                "signal": p.signal.name,
                "confidence": p.confidence,
                "price": p.price,
                "target_price": p.target_price,
                "stop_loss": p.stop_loss,
                "reasons": p.reasons[:3]
            }
            for p in picks
        ]
    except Exception as e:
        logger.error(f"Error getting top picks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/auto-trade")
async def execute_auto_trade(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Execute automated trading based on signals

    This endpoint triggers analysis of VN30 stocks and
    executes trades based on strong signals.
    """
    if not settings.enable_auto_trading:
        raise HTTPException(
            status_code=400,
            detail="Auto-trading is disabled. Enable in settings."
        )

    try:
        # Get balance
        balance_result = await db.execute(select(Balance).limit(1))
        balance = balance_result.scalar_one_or_none()
        available_cash = balance.cash_balance if balance else 0

        if available_cash < 100000:  # Minimum 100k VND
            return {"message": "Insufficient balance for trading"}

        # Get current positions
        pos_result = await db.execute(
            select(Portfolio).where(Portfolio.quantity > 0)
        )
        current_positions = pos_result.scalars().all()
        num_positions = len(current_positions)

        # Get top picks
        picks = await strategy_engine.get_top_picks(
            settings.max_stocks_in_portfolio - num_positions
        )

        trades_made = []
        for pick in picks:
            if pick.signal in [SignalStrength.STRONG_BUY, SignalStrength.BUY]:
                # Calculate position size
                quantity = await strategy_engine.calculate_position_size(
                    available_cash / len(picks),
                    pick.price
                )
                if quantity > 0:
                    # Place order
                    order = OrderRequest(
                        symbol=pick.symbol,
                        side="BUY",
                        quantity=quantity,
                        price=pick.price
                    )
                    result = await place_order(order, db)
                    trades_made.append(result)

        return {
            "message": f"Auto-trade executed",
            "trades": trades_made
        }

    except Exception as e:
        logger.error(f"Error in auto-trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))
