"""
Trading Scheduler
Automated task scheduling for market data, trading, and portfolio updates
"""
import asyncio
from datetime import datetime, time
from typing import Optional, Callable, List
from loguru import logger
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from ..config import settings


class TradingScheduler:
    """
    Scheduler for automated trading tasks

    Vietnam Market Hours (UTC+7):
    - Morning session: 09:00 - 11:30
    - Afternoon session: 13:00 - 15:00

    Scheduled Tasks:
    - Pre-market: 08:30 - Fetch news, analyze sentiment
    - Market open: 09:00 - Check signals, execute trades
    - Mid-day: 11:00 - Update positions, check stop-losses
    - Afternoon: 13:30 - Re-analyze, adjust positions
    - Market close: 15:00 - End-of-day summary
    - Post-market: 17:00 - Update portfolio history, calculate returns
    """

    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone="Asia/Ho_Chi_Minh")
        self._is_running = False
        self._tasks: List[str] = []

    def start(self):
        """Start the scheduler"""
        if not self._is_running:
            self.scheduler.start()
            self._is_running = True
            logger.info("Trading scheduler started")

    def stop(self):
        """Stop the scheduler"""
        if self._is_running:
            self.scheduler.shutdown()
            self._is_running = False
            logger.info("Trading scheduler stopped")

    @property
    def is_running(self) -> bool:
        return self._is_running

    def add_job(
        self,
        func: Callable,
        job_id: str,
        trigger: str = "cron",
        **trigger_args
    ):
        """Add a scheduled job"""
        try:
            if trigger == "cron":
                self.scheduler.add_job(
                    func,
                    CronTrigger(**trigger_args),
                    id=job_id,
                    replace_existing=True
                )
            elif trigger == "interval":
                self.scheduler.add_job(
                    func,
                    IntervalTrigger(**trigger_args),
                    id=job_id,
                    replace_existing=True
                )
            self._tasks.append(job_id)
            logger.info(f"Added job: {job_id}")
        except Exception as e:
            logger.error(f"Error adding job {job_id}: {e}")

    def remove_job(self, job_id: str):
        """Remove a scheduled job"""
        try:
            self.scheduler.remove_job(job_id)
            if job_id in self._tasks:
                self._tasks.remove(job_id)
            logger.info(f"Removed job: {job_id}")
        except Exception as e:
            logger.error(f"Error removing job {job_id}: {e}")

    def setup_trading_schedule(
        self,
        pre_market_task: Callable,
        market_open_task: Callable,
        mid_day_task: Callable,
        afternoon_task: Callable,
        market_close_task: Callable,
        post_market_task: Callable,
        news_update_task: Callable
    ):
        """
        Set up the full trading schedule

        All times are Vietnam time (UTC+7)
        """
        # Pre-market analysis (08:30)
        self.add_job(
            pre_market_task,
            "pre_market_analysis",
            trigger="cron",
            hour=8,
            minute=30,
            day_of_week="mon-fri"
        )

        # Market open check (09:05 - 5 minutes after open)
        self.add_job(
            market_open_task,
            "market_open_check",
            trigger="cron",
            hour=9,
            minute=5,
            day_of_week="mon-fri"
        )

        # Mid-day check (11:00)
        self.add_job(
            mid_day_task,
            "mid_day_check",
            trigger="cron",
            hour=11,
            minute=0,
            day_of_week="mon-fri"
        )

        # Afternoon session (13:30)
        self.add_job(
            afternoon_task,
            "afternoon_check",
            trigger="cron",
            hour=13,
            minute=30,
            day_of_week="mon-fri"
        )

        # Market close summary (15:05)
        self.add_job(
            market_close_task,
            "market_close_summary",
            trigger="cron",
            hour=15,
            minute=5,
            day_of_week="mon-fri"
        )

        # Post-market analysis (17:00)
        self.add_job(
            post_market_task,
            "post_market_analysis",
            trigger="cron",
            hour=17,
            minute=0,
            day_of_week="mon-fri"
        )

        # News updates every 2 hours during market hours
        self.add_job(
            news_update_task,
            "news_update",
            trigger="interval",
            hours=2
        )

        logger.info("Trading schedule configured")

    def is_market_open(self) -> bool:
        """Check if Vietnam stock market is currently open"""
        now = datetime.now()

        # Check if weekday (Monday = 0, Sunday = 6)
        if now.weekday() >= 5:  # Saturday or Sunday
            return False

        current_time = now.time()

        # Morning session: 09:00 - 11:30
        morning_open = time(9, 0)
        morning_close = time(11, 30)

        # Afternoon session: 13:00 - 15:00
        afternoon_open = time(13, 0)
        afternoon_close = time(15, 0)

        if morning_open <= current_time <= morning_close:
            return True
        if afternoon_open <= current_time <= afternoon_close:
            return True

        return False

    def get_next_market_open(self) -> datetime:
        """Get datetime of next market open"""
        now = datetime.now()
        current_date = now.date()

        # If before 09:00 today (weekday)
        if now.weekday() < 5 and now.time() < time(9, 0):
            return datetime.combine(current_date, time(9, 0))

        # If during lunch break
        if now.weekday() < 5 and time(11, 30) < now.time() < time(13, 0):
            return datetime.combine(current_date, time(13, 0))

        # Otherwise, next business day
        days_ahead = 1
        if now.weekday() == 4:  # Friday
            days_ahead = 3
        elif now.weekday() == 5:  # Saturday
            days_ahead = 2

        next_open = datetime.combine(
            current_date + timedelta(days=days_ahead),
            time(9, 0)
        )
        return next_open

    def get_scheduled_jobs(self) -> List[dict]:
        """Get list of all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "next_run": str(job.next_run_time),
                "trigger": str(job.trigger)
            })
        return jobs


# Import timedelta for get_next_market_open
from datetime import timedelta

# Singleton instance
trading_scheduler = TradingScheduler()
