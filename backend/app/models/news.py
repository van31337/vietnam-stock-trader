"""News models for storing articles and sentiment"""
from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, Text
from sqlalchemy.sql import func
from ..database import Base


class NewsArticle(Base):
    """News articles related to stocks"""
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), nullable=False, unique=True)
    source = Column(String(100), nullable=False)  # CafeF, VnExpress, etc.
    summary = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)

    # Related stocks
    symbols = Column(String(500), nullable=True)  # Comma-separated symbols

    # Processing status
    is_processed = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<NewsArticle {self.source}: {self.title[:50]}>"


class NewsSentiment(Base):
    """Sentiment analysis results for news articles"""
    __tablename__ = "news_sentiment"

    id = Column(Integer, primary_key=True, autoincrement=True)
    article_id = Column(Integer, nullable=False, index=True)
    symbol = Column(String(20), nullable=False, index=True)

    # Sentiment scores (-1 to 1)
    sentiment_score = Column(Float, nullable=False)
    sentiment_magnitude = Column(Float, nullable=False)

    # Classification
    sentiment_label = Column(String(20), nullable=False)  # POSITIVE, NEGATIVE, NEUTRAL
    confidence = Column(Float, nullable=False)

    # Impact assessment
    impact_score = Column(Float, nullable=True)  # How impactful is this news

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<NewsSentiment {self.symbol}: {self.sentiment_label} ({self.sentiment_score:.2f})>"
