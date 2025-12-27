"""
News Fetching and Sentiment Analysis Service
Fetches news from Vietnamese sources and analyzes sentiment
"""
import asyncio
import re
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from loguru import logger
import aiohttp
import feedparser
from textblob import TextBlob

# Vietnamese NLP
try:
    from underthesea import sentiment as vn_sentiment
    UNDERTHESEA_AVAILABLE = True
except ImportError:
    UNDERTHESEA_AVAILABLE = False
    logger.warning("underthesea not installed. Vietnamese sentiment analysis limited.")


class NewsService:
    """Service for fetching and analyzing financial news"""

    # Vietnamese financial news RSS feeds
    RSS_FEEDS = {
        "cafef": {
            "url": "https://cafef.vn/rss/chung-khoan.rss",
            "name": "CafeF Chứng Khoán"
        },
        "cafef_business": {
            "url": "https://cafef.vn/rss/kinh-doanh.rss",
            "name": "CafeF Kinh Doanh"
        },
        "vnexpress": {
            "url": "https://vnexpress.net/rss/kinh-doanh.rss",
            "name": "VnExpress Kinh Doanh"
        },
        "vnexpress_stock": {
            "url": "https://vnexpress.net/rss/chung-khoan.rss",
            "name": "VnExpress Chứng Khoán"
        },
        "vietstock": {
            "url": "https://vietstock.vn/rss/tin-tuc.rss",
            "name": "VietStock"
        }
    }

    # Common Vietnamese stock symbols for matching
    VN30_SYMBOLS = {
        "ACB", "BCM", "BID", "BVH", "CTG", "FPT", "GAS", "GVR",
        "HDB", "HPG", "MBB", "MSN", "MWG", "NVL", "PDR", "PLX",
        "PNJ", "POW", "SAB", "SSI", "STB", "TCB", "TPB", "VCB",
        "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VRE"
    }

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession()
        return self._session

    async def close(self):
        """Close the aiohttp session"""
        if self._session and not self._session.closed:
            await self._session.close()

    async def fetch_rss_feed(self, feed_key: str) -> List[Dict[str, Any]]:
        """Fetch articles from a specific RSS feed"""
        if feed_key not in self.RSS_FEEDS:
            logger.error(f"Unknown feed: {feed_key}")
            return []

        feed_info = self.RSS_FEEDS[feed_key]
        try:
            session = await self._get_session()
            async with session.get(feed_info["url"], timeout=30) as response:
                if response.status == 200:
                    content = await response.text()
                    feed = feedparser.parse(content)

                    articles = []
                    for entry in feed.entries[:20]:  # Limit to 20 articles
                        article = {
                            "title": entry.get("title", ""),
                            "url": entry.get("link", ""),
                            "summary": entry.get("summary", ""),
                            "source": feed_info["name"],
                            "published_at": self._parse_date(entry.get("published")),
                            "symbols": self._extract_symbols(
                                entry.get("title", "") + " " + entry.get("summary", "")
                            )
                        }
                        articles.append(article)
                    return articles
        except Exception as e:
            logger.error(f"Error fetching feed {feed_key}: {e}")
        return []

    async def fetch_all_news(self) -> List[Dict[str, Any]]:
        """Fetch news from all configured RSS feeds"""
        all_articles = []
        tasks = [self.fetch_rss_feed(key) for key in self.RSS_FEEDS.keys()]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"Feed fetch error: {result}")

        # Sort by date, most recent first
        all_articles.sort(
            key=lambda x: x.get("published_at") or datetime.min,
            reverse=True
        )
        return all_articles

    async def fetch_news_for_symbol(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetch news related to a specific stock symbol"""
        all_news = await self.fetch_all_news()
        return [
            article for article in all_news
            if symbol in article.get("symbols", [])
        ]

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str:
            return None
        try:
            # Try common formats
            formats = [
                "%a, %d %b %Y %H:%M:%S %z",
                "%a, %d %b %Y %H:%M:%S GMT",
                "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%d %H:%M:%S"
            ]
            for fmt in formats:
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    continue
        except Exception:
            pass
        return None

    def _extract_symbols(self, text: str) -> List[str]:
        """Extract stock symbols from text"""
        text_upper = text.upper()
        found_symbols = []

        # Look for VN30 symbols
        for symbol in self.VN30_SYMBOLS:
            # Match whole word
            if re.search(rf'\b{symbol}\b', text_upper):
                found_symbols.append(symbol)

        # Also look for patterns like "cổ phiếu ABC" or "mã ABC"
        patterns = [
            r'cổ phiếu\s+([A-Z]{3})',
            r'mã\s+([A-Z]{3})',
            r'cp\s+([A-Z]{3})',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if match.upper() not in found_symbols:
                    found_symbols.append(match.upper())

        return found_symbols

    async def analyze_sentiment(
        self,
        text: str,
        language: str = "vi"
    ) -> Dict[str, Any]:
        """
        Analyze sentiment of text

        Args:
            text: Text to analyze
            language: "vi" for Vietnamese, "en" for English

        Returns:
            Dictionary with sentiment score, magnitude, and label
        """
        try:
            if language == "vi" and UNDERTHESEA_AVAILABLE:
                # Use underthesea for Vietnamese
                result = vn_sentiment(text)
                # Convert to standard format
                if result == "positive":
                    score = 0.7
                elif result == "negative":
                    score = -0.7
                else:
                    score = 0.0
            else:
                # Use TextBlob for English or fallback
                blob = TextBlob(text)
                score = blob.sentiment.polarity  # -1 to 1

            # Determine label and confidence
            if score > 0.3:
                label = "POSITIVE"
                confidence = min(abs(score), 1.0)
            elif score < -0.3:
                label = "NEGATIVE"
                confidence = min(abs(score), 1.0)
            else:
                label = "NEUTRAL"
                confidence = 1.0 - abs(score)

            return {
                "score": score,
                "magnitude": abs(score),
                "label": label,
                "confidence": confidence
            }
        except Exception as e:
            logger.error(f"Error analyzing sentiment: {e}")
            return {
                "score": 0.0,
                "magnitude": 0.0,
                "label": "NEUTRAL",
                "confidence": 0.0
            }

    async def analyze_news_sentiment(
        self,
        articles: List[Dict[str, Any]]
    ) -> Dict[str, Dict[str, Any]]:
        """
        Analyze sentiment for multiple articles grouped by symbol

        Returns:
            Dictionary mapping symbol to aggregated sentiment
        """
        symbol_sentiments: Dict[str, List[float]] = {}

        for article in articles:
            text = article.get("title", "") + " " + article.get("summary", "")
            sentiment = await self.analyze_sentiment(text)
            score = sentiment["score"]

            for symbol in article.get("symbols", []):
                if symbol not in symbol_sentiments:
                    symbol_sentiments[symbol] = []
                symbol_sentiments[symbol].append(score)

        # Aggregate sentiments per symbol
        results = {}
        for symbol, scores in symbol_sentiments.items():
            avg_score = sum(scores) / len(scores)
            results[symbol] = {
                "score": avg_score,
                "num_articles": len(scores),
                "label": "POSITIVE" if avg_score > 0.1 else (
                    "NEGATIVE" if avg_score < -0.1 else "NEUTRAL"
                )
            }

        return results

    async def get_market_sentiment(self) -> Dict[str, Any]:
        """Get overall market sentiment from recent news"""
        articles = await self.fetch_all_news()

        if not articles:
            return {"score": 0.0, "label": "NEUTRAL", "num_articles": 0}

        all_scores = []
        for article in articles[:50]:  # Analyze last 50 articles
            text = article.get("title", "") + " " + article.get("summary", "")
            sentiment = await self.analyze_sentiment(text)
            all_scores.append(sentiment["score"])

        avg_score = sum(all_scores) / len(all_scores) if all_scores else 0
        return {
            "score": avg_score,
            "label": "POSITIVE" if avg_score > 0.1 else (
                "NEGATIVE" if avg_score < -0.1 else "NEUTRAL"
            ),
            "num_articles": len(all_scores)
        }


# Singleton instance
news_service = NewsService()
