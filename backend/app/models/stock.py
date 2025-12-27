"""Stock models for caching stock data"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, BigInteger
from sqlalchemy.sql import func
from ..database import Base


class Stock(Base):
    """Stock master data"""
    __tablename__ = "stocks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, unique=True, index=True)
    name = Column(String(200), nullable=False)
    exchange = Column(String(20), nullable=False)  # HOSE, HNX, UPCOM
    industry = Column(String(100), nullable=True)
    sector = Column(String(100), nullable=True)
    market_cap = Column(BigInteger, nullable=True)
    is_vn30 = Column(Boolean, nullable=False, default=False)
    is_active = Column(Boolean, nullable=False, default=True)
    last_updated = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<Stock {self.symbol}: {self.name}>"


class StockPrice(Base):
    """Historical and current stock prices"""
    __tablename__ = "stock_prices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(20), nullable=False, index=True)
    date = Column(DateTime(timezone=True), nullable=False, index=True)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(BigInteger, nullable=False)
    value = Column(BigInteger, nullable=True)  # Trading value in VND

    # Technical indicators (pre-calculated)
    sma_20 = Column(Float, nullable=True)
    sma_50 = Column(Float, nullable=True)
    rsi_14 = Column(Float, nullable=True)
    macd = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    class Meta:
        unique_together = [("symbol", "date")]

    def __repr__(self):
        return f"<StockPrice {self.symbol} {self.date}: {self.close}>"
