"""
Portfolio API Routes
Endpoints for portfolio management and balance tracking
"""
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from pydantic import BaseModel
from loguru import logger

from ..database import get_db
from ..models.portfolio import Portfolio, PortfolioHistory
from ..models.balance import Balance, BalanceHistory, TransactionType
from ..models.trade import Trade, TradeType, TradeStatus
from ..services.market_data import market_data
from ..services.ssi_api import ssi_api
from ..config import is_ssi_configured

router = APIRouter(prefix="/portfolio", tags=["portfolio"])


# ============ Pydantic Models ============

class PortfolioPosition(BaseModel):
    symbol: str
    quantity: int
    avg_buy_price: float
    current_price: Optional[float]
    total_cost: float
    current_value: Optional[float]
    unrealized_pnl: Optional[float]
    unrealized_pnl_percent: Optional[float]

    class Config:
        from_attributes = True


class PortfolioSummary(BaseModel):
    total_value: float
    total_cost: float
    total_pnl: float
    total_pnl_percent: float
    cash_balance: float
    positions: List[PortfolioPosition]
    last_updated: datetime


class BalanceResponse(BaseModel):
    cash_balance: float
    total_deposits: float
    total_withdrawals: float
    total_dividends: float
    total_commissions_paid: float
    last_updated: datetime

    class Config:
        from_attributes = True


class DepositRequest(BaseModel):
    amount: float
    description: Optional[str] = None


class BalanceHistoryItem(BaseModel):
    transaction_type: str
    amount: float
    balance_before: float
    balance_after: float
    description: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


# ============ Endpoints ============

@router.get("/summary", response_model=PortfolioSummary)
async def get_portfolio_summary(db: AsyncSession = Depends(get_db)):
    """Get complete portfolio summary with current values"""
    try:
        # Get all positions
        result = await db.execute(
            select(Portfolio).where(Portfolio.quantity > 0)
        )
        positions = result.scalars().all()

        # Update current prices and calculate values
        portfolio_positions = []
        total_value = 0.0
        total_cost = 0.0

        for pos in positions:
            # Get current price
            current_price = await market_data.get_current_price(pos.symbol)
            if current_price:
                pos.current_price = current_price
                pos.current_value = current_price * pos.quantity
                pos.unrealized_pnl = pos.current_value - pos.total_cost
                pos.unrealized_pnl_percent = (
                    (pos.unrealized_pnl / pos.total_cost * 100)
                    if pos.total_cost > 0 else 0
                )
                total_value += pos.current_value
            else:
                pos.current_value = pos.total_cost
                total_value += pos.total_cost

            total_cost += pos.total_cost
            portfolio_positions.append(PortfolioPosition.model_validate(pos))

        # Get cash balance
        balance_result = await db.execute(select(Balance).limit(1))
        balance = balance_result.scalar_one_or_none()
        cash = balance.cash_balance if balance else 0.0

        total_value += cash
        total_pnl = total_value - total_cost - cash
        total_pnl_percent = (total_pnl / total_cost * 100) if total_cost > 0 else 0

        await db.commit()

        return PortfolioSummary(
            total_value=total_value,
            total_cost=total_cost,
            total_pnl=total_pnl,
            total_pnl_percent=total_pnl_percent,
            cash_balance=cash,
            positions=portfolio_positions,
            last_updated=datetime.now()
        )

    except Exception as e:
        logger.error(f"Error getting portfolio summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions", response_model=List[PortfolioPosition])
async def get_positions(db: AsyncSession = Depends(get_db)):
    """Get all current positions"""
    result = await db.execute(
        select(Portfolio).where(Portfolio.quantity > 0)
    )
    positions = result.scalars().all()
    return [PortfolioPosition.model_validate(p) for p in positions]


@router.get("/balance", response_model=BalanceResponse)
async def get_balance(db: AsyncSession = Depends(get_db)):
    """Get current cash balance"""
    result = await db.execute(select(Balance).limit(1))
    balance = result.scalar_one_or_none()

    if not balance:
        # Create initial balance record
        balance = Balance(cash_balance=0.0)
        db.add(balance)
        await db.commit()
        await db.refresh(balance)

    return BalanceResponse.model_validate(balance)


@router.post("/deposit")
async def deposit_funds(
    request: DepositRequest,
    db: AsyncSession = Depends(get_db)
):
    """Add funds to trading account (manual deposit record)"""
    if request.amount <= 0:
        raise HTTPException(status_code=400, detail="Amount must be positive")

    # Get or create balance
    result = await db.execute(select(Balance).limit(1))
    balance = result.scalar_one_or_none()

    if not balance:
        balance = Balance(cash_balance=0.0)
        db.add(balance)

    old_balance = balance.cash_balance
    balance.cash_balance += request.amount
    balance.total_deposits += request.amount

    # Record transaction
    history = BalanceHistory(
        transaction_type=TransactionType.DEPOSIT,
        amount=request.amount,
        balance_before=old_balance,
        balance_after=balance.cash_balance,
        description=request.description or "Manual deposit"
    )
    db.add(history)

    await db.commit()

    return {
        "message": "Deposit recorded",
        "amount": request.amount,
        "new_balance": balance.cash_balance
    }


@router.get("/balance-history", response_model=List[BalanceHistoryItem])
async def get_balance_history(
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """Get balance transaction history"""
    result = await db.execute(
        select(BalanceHistory)
        .order_by(desc(BalanceHistory.created_at))
        .limit(limit)
    )
    history = result.scalars().all()
    return [
        BalanceHistoryItem(
            transaction_type=h.transaction_type.value,
            amount=h.amount,
            balance_before=h.balance_before,
            balance_after=h.balance_after,
            description=h.description,
            created_at=h.created_at
        )
        for h in history
    ]


@router.get("/history")
async def get_portfolio_history(
    days: int = 30,
    db: AsyncSession = Depends(get_db)
):
    """Get portfolio value history for charts"""
    start_date = datetime.now() - timedelta(days=days)
    result = await db.execute(
        select(PortfolioHistory)
        .where(PortfolioHistory.date >= start_date)
        .order_by(PortfolioHistory.date)
    )
    history = result.scalars().all()

    return [
        {
            "date": h.date.isoformat(),
            "total_value": h.total_value,
            "total_cost": h.total_cost,
            "total_pnl": h.total_pnl,
            "total_pnl_percent": h.total_pnl_percent,
            "cash_balance": h.cash_balance
        }
        for h in history
    ]


@router.post("/sync-ssi")
async def sync_with_ssi(db: AsyncSession = Depends(get_db)):
    """Sync portfolio with SSI account (requires SSI API credentials)"""
    if not is_ssi_configured():
        raise HTTPException(
            status_code=400,
            detail="SSI API credentials not configured"
        )

    try:
        # Get portfolio from SSI
        ssi_portfolio = await ssi_api.get_portfolio()
        if not ssi_portfolio:
            raise HTTPException(
                status_code=500,
                detail="Failed to fetch SSI portfolio"
            )

        # Get balance from SSI
        ssi_balance = await ssi_api.get_account_balance()

        # Update local database
        for item in ssi_portfolio:
            symbol = item.get("symbol")
            quantity = item.get("quantity", 0)
            avg_price = item.get("avgPrice", 0)

            # Find or create position
            result = await db.execute(
                select(Portfolio).where(Portfolio.symbol == symbol)
            )
            position = result.scalar_one_or_none()

            if position:
                position.quantity = quantity
                position.avg_buy_price = avg_price
                position.total_cost = quantity * avg_price
            else:
                position = Portfolio(
                    symbol=symbol,
                    quantity=quantity,
                    avg_buy_price=avg_price,
                    total_cost=quantity * avg_price
                )
                db.add(position)

        # Update balance
        if ssi_balance:
            result = await db.execute(select(Balance).limit(1))
            balance = result.scalar_one_or_none()
            if balance:
                balance.cash_balance = ssi_balance.get("cashBalance", 0)
            else:
                balance = Balance(
                    cash_balance=ssi_balance.get("cashBalance", 0)
                )
                db.add(balance)

        await db.commit()

        return {"message": "Portfolio synced with SSI"}

    except Exception as e:
        logger.error(f"Error syncing with SSI: {e}")
        raise HTTPException(status_code=500, detail=str(e))
