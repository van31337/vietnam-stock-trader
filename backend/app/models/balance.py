"""Balance models for tracking cash and deposits"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Enum as SQLEnum
from sqlalchemy.sql import func
from ..database import Base
import enum


class TransactionType(enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"
    COMMISSION = "COMMISSION"


class Balance(Base):
    """Current cash balance"""
    __tablename__ = "balance"

    id = Column(Integer, primary_key=True, autoincrement=True)
    cash_balance = Column(Float, nullable=False, default=0.0)
    total_deposits = Column(Float, nullable=False, default=0.0)
    total_withdrawals = Column(Float, nullable=False, default=0.0)
    total_dividends = Column(Float, nullable=False, default=0.0)
    total_commissions_paid = Column(Float, nullable=False, default=0.0)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Balance: {self.cash_balance:,.0f} VND>"


class BalanceHistory(Base):
    """Historical balance transactions"""
    __tablename__ = "balance_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    transaction_type = Column(SQLEnum(TransactionType), nullable=False)
    amount = Column(Float, nullable=False)
    balance_before = Column(Float, nullable=False)
    balance_after = Column(Float, nullable=False)
    description = Column(String(500), nullable=True)
    reference_id = Column(String(100), nullable=True)  # Trade ID, deposit reference, etc.
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<BalanceHistory {self.transaction_type.value}: {self.amount:,.0f} VND>"
