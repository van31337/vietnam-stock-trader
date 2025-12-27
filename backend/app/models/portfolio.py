"""Portfolio models for tracking stock holdings"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from ..database import Base


class Portfolio(Base):
    """Current stock holdings in the portfolio"""
    __tablename__ = "portfolio"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, unique=True, index=True)
    quantity = Column(Integer, nullable=False, default=0)
    avg_buy_price = Column(Float, nullable=False, default=0.0)
    current_price = Column(Float, nullable=True)
    total_cost = Column(Float, nullable=False, default=0.0)
    current_value = Column(Float, nullable=True)
    unrealized_pnl = Column(Float, nullable=True)
    unrealized_pnl_percent = Column(Float, nullable=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<Portfolio {self.symbol}: {self.quantity} shares @ {self.avg_buy_price}>"


class PortfolioHistory(Base):
    """Historical snapshots of portfolio value"""
    __tablename__ = "portfolio_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    total_value = Column(Float, nullable=False)
    total_cost = Column(Float, nullable=False)
    total_pnl = Column(Float, nullable=False)
    total_pnl_percent = Column(Float, nullable=False)
    cash_balance = Column(Float, nullable=False)
    num_positions = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<PortfolioHistory {self.date}: {self.total_value} VND>"
