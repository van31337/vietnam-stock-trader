"""
Vietnam Stock Trader - Main Application
Automated stock trading system for Vietnamese market
"""
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys

from .config import settings
from .database import init_db
from .routers import portfolio_router, trading_router, market_router, dashboard_router
from .services.scheduler import trading_scheduler
from .services.ssi_api import ssi_api
from .services.market_data import market_data
from .services.news import news_service
from .services.strategy import strategy_engine
from .services.notifications import notification_service

# Configure logging
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO"
)
logger.add(
    "logs/trading_{time:YYYY-MM-DD}.log",
    rotation="1 day",
    retention="30 days",
    level="DEBUG"
)


# ============ Scheduled Task Functions ============

async def pre_market_analysis():
    """Pre-market analysis task"""
    logger.info("Running pre-market analysis...")
    try:
        # Fetch latest news
        articles = await news_service.fetch_all_news()
        logger.info(f"Fetched {len(articles)} news articles")

        # Get market sentiment
        sentiment = await news_service.get_market_sentiment()
        logger.info(f"Market sentiment: {sentiment.get('label')}")

        # Notify if significant
        if abs(sentiment.get('score', 0)) > 0.3:
            await notification_service.send_telegram(
                f"📰 Pre-market sentiment: {sentiment.get('label')}\n"
                f"Score: {sentiment.get('score', 0):.2f}"
            )
    except Exception as e:
        logger.error(f"Pre-market analysis error: {e}")


async def market_open_check():
    """Market open task"""
    logger.info("Market open - checking signals...")
    try:
        if settings.enable_auto_trading:
            picks = await strategy_engine.get_top_picks(3)
            for pick in picks:
                await notification_service.notify_signal(
                    pick.symbol,
                    pick.signal.name,
                    pick.confidence,
                    pick.reasons
                )
    except Exception as e:
        logger.error(f"Market open check error: {e}")


async def mid_day_check():
    """Mid-day portfolio check"""
    logger.info("Mid-day portfolio check...")


async def afternoon_check():
    """Afternoon session check"""
    logger.info("Afternoon session analysis...")


async def market_close_summary():
    """End of day summary"""
    logger.info("Market closed - generating summary...")
    try:
        overview = await market_data.get_market_overview()
        if overview:
            await notification_service.send_telegram(
                f"📊 Market Close Summary\n"
                f"VN-Index: {overview.get('value', 0):,.2f}\n"
                f"Change: {overview.get('change_percent', 0):+.2f}%"
            )
    except Exception as e:
        logger.error(f"Market close summary error: {e}")


async def post_market_analysis():
    """Post-market analysis and portfolio update"""
    logger.info("Post-market analysis...")


async def news_update():
    """Periodic news update"""
    logger.info("Updating news...")
    try:
        await news_service.fetch_all_news()
    except Exception as e:
        logger.error(f"News update error: {e}")


# ============ Application Lifecycle ============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle manager"""
    # Startup
    logger.info("Starting Vietnam Stock Trader...")

    # Initialize database
    await init_db()
    logger.info("Database initialized")

    # Setup trading scheduler
    if settings.enable_auto_trading:
        trading_scheduler.setup_trading_schedule(
            pre_market_task=pre_market_analysis,
            market_open_task=market_open_check,
            mid_day_task=mid_day_check,
            afternoon_task=afternoon_check,
            market_close_task=market_close_summary,
            post_market_task=post_market_analysis,
            news_update_task=news_update
        )
        trading_scheduler.start()
        logger.info("Trading scheduler started")

    logger.info("Application started successfully")

    yield

    # Shutdown
    logger.info("Shutting down...")
    trading_scheduler.stop()
    await ssi_api.close()
    await news_service.close()
    logger.info("Application shutdown complete")


# ============ FastAPI Application ============

app = FastAPI(
    title="Vietnam Stock Trader",
    description="Automated stock trading system for Vietnamese market",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware for dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "https://van31337.github.io",
        "*"  # Allow all for development
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(portfolio_router)
app.include_router(trading_router)
app.include_router(market_router)
app.include_router(dashboard_router)


# ============ Root Endpoints ============

@app.get("/")
async def root():
    """API root endpoint"""
    return {
        "name": "Vietnam Stock Trader API",
        "version": "1.0.0",
        "status": "running",
        "market_open": trading_scheduler.is_market_open(),
        "auto_trading": settings.enable_auto_trading,
        "docs": "/docs"
    }


@app.get("/health")
async def health():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }


# ============ Run Application ============

def main():
    """Run the application"""
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )


if __name__ == "__main__":
    main()
