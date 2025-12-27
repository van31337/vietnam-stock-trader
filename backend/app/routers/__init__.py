"""API Routers"""
from .portfolio import router as portfolio_router
from .trading import router as trading_router
from .market import router as market_router
from .dashboard import router as dashboard_router

__all__ = [
    "portfolio_router",
    "trading_router",
    "market_router",
    "dashboard_router",
]
