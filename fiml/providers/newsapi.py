"""
NewsAPI Provider Implementation

Provides news and sentiment data using NewsAPI v2.
Supports free tier (100 requests/day) and paid tier (1000 requests/day).
"""

import asyncio
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

import aiohttp

from fiml.core.exceptions import ProviderError, RateLimitError
from fiml.core.logging import get_logger
from fiml.core.models import Asset, DataType, ProviderHealth
from fiml.providers.base import BaseProvider, ProviderConfig, ProviderResponse

logger = get_logger(__name__)


class NewsArticle:
    """Standardized news article format"""

    def __init__(
        self,
        title: str,
        description: Optional[str],
        url: str,
        source: str,
        published_at: datetime,
        content: Optional[str] = None,
        author: Optional[str] = None,
        sentiment: Optional[float] = None,
    ):
        self.title = title
        self.description = description
        self.url = url
        self.source = source
        self.published_at = published_at
        self.content = content
        self.author = author
        self.sentiment = sentiment

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "title": self.title,
            "description": self.description,
            "url": self.url,
            "source": self.source,
            "published_at": self.published_at.isoformat() if self.published_at else None,
            "content": self.content,
            "author": self.author,
            "sentiment": self.sentiment,
        }


class NewsAPIProvider(BaseProvider):
    """
    NewsAPI data provider

    Provides news articles and sentiment data
    """

    BASE_URL = "https://newsapi.org/v2"

    def __init__(self, api_key: Optional[str] = None):
        # Get API key from parameter or environment
        api_key = api_key or os.getenv("NEWSAPI_KEY") or os.getenv("NEWSAPI_API_KEY")

        if not api_key:
            raise ValueError("NewsAPI API key is required")

        config = ProviderConfig(
            name="newsapi",
            enabled=True,
            priority=8,  # High priority for news/sentiment data
            rate_limit_per_minute=20,  # Conservative for free tier (100/day)
            timeout_seconds=10,
            api_key=api_key,
        )
        super().__init__(config)

        self._session: Optional[aiohttp.ClientSession] = None
        self._request_times: List[datetime] = []
        self._daily_request_count = 0
        self._daily_limit = 100  # Free tier default
        self._last_reset = datetime.now(timezone.utc)

    async def initialize(self) -> None:
        """Initialize NewsAPI provider"""
        logger.info("Initializing NewsAPI provider")
        self._session = aiohttp.ClientSession()
        self._is_initialized = True

    async def shutdown(self) -> None:
        """Shutdown NewsAPI provider"""
        logger.info("Shutting down NewsAPI provider")
        if self._session:
            await self._session.close()
        self._is_initialized = False

    async def _check_rate_limit(self) -> None:
        """Check and enforce rate limiting"""
        now = datetime.now(timezone.utc)

        # Reset daily counter if new day
        if (now - self._last_reset).total_seconds() > 86400:
            self._daily_request_count = 0
            self._last_reset = now

        # Check daily limit
        if self._daily_request_count >= self._daily_limit:
            raise RateLimitError(f"Daily limit of {self._daily_limit} requests reached for NewsAPI")

        # Check per-minute limit
        one_minute_ago = now.timestamp() - 60
        self._request_times = [t for t in self._request_times if t.timestamp() > one_minute_ago]

        if len(self._request_times) >= self.config.rate_limit_per_minute:
            wait_time = 60 - (now.timestamp() - self._request_times[0].timestamp())
            if wait_time > 0:
                logger.warning(f"Rate limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)

        self._request_times.append(now)
        self._daily_request_count += 1

    async def _make_request(
        self, endpoint: str, params: Dict[str, Any], max_retries: int = 3
    ) -> Dict[str, Any]:
        """Make HTTP request to NewsAPI with retries and exponential backoff"""
        if not self._session:
            raise ProviderError("NewsAPI provider not initialized")

        await self._check_rate_limit()

        params["apiKey"] = self.config.api_key
        url = f"{self.BASE_URL}/{endpoint}"

        for attempt in range(max_retries):
            try:
                timeout = aiohttp.ClientTimeout(total=self.config.timeout_seconds)
                async with self._session.get(url, params=params, timeout=timeout) as response:
                    if response.status == 429:
                        # Rate limited
                        retry_after = int(response.headers.get("Retry-After", "60"))
                        raise RateLimitError(f"Rate limited, retry after {retry_after}s")

                    if response.status == 401:
                        raise ProviderError("Invalid API key")

                    if response.status != 200:
                        error_text = await response.text()
                        raise ProviderError(
                            f"NewsAPI request failed: {response.status} - {error_text}"
                        )

                    data = await response.json()

                    if data.get("status") != "ok":
                        error_msg = data.get("message", "Unknown error")
                        raise ProviderError(f"NewsAPI error: {error_msg}")

                    return cast(Dict[str, Any], data)

            except RateLimitError:
                raise
            except asyncio.TimeoutError:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # Exponential backoff
                    logger.warning(
                        f"Request timeout, retrying in {wait_time}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise ProviderError("NewsAPI request timed out after retries")
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2**attempt
                    logger.warning(
                        f"Request failed: {e}, retrying in {wait_time}s "
                        f"(attempt {attempt + 1}/{max_retries})"
                    )
                    await asyncio.sleep(wait_time)
                else:
                    raise ProviderError(f"NewsAPI request failed: {e}")

        raise ProviderError("NewsAPI request failed after all retries")

    def _parse_article(self, article_data: Dict[str, Any]) -> NewsArticle:
        """Parse NewsAPI article data to NewsArticle"""
        published_at_str = article_data.get("publishedAt")
        published_at = None
        if published_at_str:
            try:
                published_at = datetime.fromisoformat(published_at_str.replace("Z", "+00:00"))
            except Exception:
                published_at = datetime.now(timezone.utc)

        # Extract sentiment indicators (simple keyword-based)
        sentiment = self._extract_sentiment(
            article_data.get("title", ""), article_data.get("description", "")
        )

        return NewsArticle(
            title=article_data.get("title", ""),
            description=article_data.get("description"),
            url=article_data.get("url", ""),
            source=article_data.get("source", {}).get("name", "Unknown"),
            published_at=published_at or datetime.now(timezone.utc),
            content=article_data.get("content"),
            author=article_data.get("author"),
            sentiment=sentiment,
        )

    def _extract_sentiment(self, title: str, description: str) -> float:
        """
        Simple sentiment extraction based on keywords
        Returns: -1.0 (negative) to 1.0 (positive)
        """
        text = f"{title} {description or ''}".lower()

        positive_words = [
            "gain",
            "rise",
            "surge",
            "profit",
            "growth",
            "bull",
            "rally",
            "soar",
            "jump",
            "beat",
            "optimistic",
            "positive",
            "strong",
        ]
        negative_words = [
            "loss",
            "fall",
            "drop",
            "crash",
            "decline",
            "bear",
            "plunge",
            "miss",
            "weak",
            "pessimistic",
            "negative",
            "concern",
            "risk",
        ]

        positive_score = sum(1 for word in positive_words if word in text)
        negative_score = sum(1 for word in negative_words if word in text)

        total = positive_score + negative_score
        if total == 0:
            return 0.0

        sentiment = (positive_score - negative_score) / total
        return max(-1.0, min(1.0, sentiment))

    async def get_news(
        self, query: str, from_date: str, to_date: str, language: str = "en"
    ) -> List[NewsArticle]:
        """
        Get news articles for a query with date range

        Args:
            query: Search query (e.g., "Apple OR AAPL")
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            language: Article language code

        Returns:
            List of NewsArticle objects
        """
        self._record_request()

        try:
            params = {
                "q": query,
                "from": from_date,
                "to": to_date,
                "language": language,
                "sortBy": "publishedAt",
                "pageSize": 100,
            }

            data = await self._make_request("everything", params)
            articles = [self._parse_article(a) for a in data.get("articles", [])]

            logger.info(f"Fetched {len(articles)} articles for query: {query}")
            return articles

        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching news for query '{query}': {e}")
            raise ProviderError(f"NewsAPI get_news failed: {e}")

    async def get_top_headlines(
        self, category: str = "business", country: str = "us", page_size: int = 20
    ) -> List[NewsArticle]:
        """
        Get top headlines by category and country

        Args:
            category: Category (business, technology, etc.)
            country: Country code (us, gb, jp, etc.)
            page_size: Number of articles to fetch

        Returns:
            List of NewsArticle objects
        """
        self._record_request()

        try:
            params = {"category": category, "country": country, "pageSize": page_size}

            data = await self._make_request("top-headlines", params)
            articles = [self._parse_article(a) for a in data.get("articles", [])]

            logger.info(f"Fetched {len(articles)} top headlines for {category}/{country}")
            return articles

        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching top headlines: {e}")
            raise ProviderError(f"NewsAPI get_top_headlines failed: {e}")

    async def search_everything(
        self, q: str, language: str = "en", sort_by: str = "publishedAt"
    ) -> List[NewsArticle]:
        """
        Search all articles matching query

        Args:
            q: Search query
            language: Article language
            sort_by: Sort order (publishedAt, relevancy, popularity)

        Returns:
            List of NewsArticle objects
        """
        self._record_request()

        try:
            params = {"q": q, "language": language, "sortBy": sort_by, "pageSize": 100}

            data = await self._make_request("everything", params)
            articles = [self._parse_article(a) for a in data.get("articles", [])]

            logger.info(f"Fetched {len(articles)} articles for search: {q}")
            return articles

        except Exception as e:
            self._record_error()
            logger.error(f"Error searching articles for '{q}': {e}")
            raise ProviderError(f"NewsAPI search_everything failed: {e}")

    # BaseProvider interface implementation

    async def fetch_price(self, asset: Asset) -> ProviderResponse:
        """NewsAPI does not provide price data"""
        raise NotImplementedError("NewsAPI does not provide price data")

    async def fetch_ohlcv(
        self, asset: Asset, timeframe: str = "1d", limit: int = 100
    ) -> ProviderResponse:
        """NewsAPI does not provide OHLCV data"""
        raise NotImplementedError("NewsAPI does not provide OHLCV data")

    async def fetch_fundamentals(self, asset: Asset) -> ProviderResponse:
        """NewsAPI does not provide fundamental data"""
        raise NotImplementedError("NewsAPI does not provide fundamental data")

    async def fetch_news(self, asset: Asset, limit: int = 10) -> ProviderResponse:
        """Fetch news articles for an asset"""
        self._record_request()

        try:
            # Build search query from asset symbol and name
            query = asset.symbol
            if hasattr(asset, "name") and asset.name:
                query = f"{asset.symbol} OR {asset.name}"

            # Get recent news (last 7 days)
            from datetime import timedelta

            to_date = datetime.now(timezone.utc)
            from_date = to_date - timedelta(days=7)

            articles = await self.get_news(
                query=query,
                from_date=from_date.strftime("%Y-%m-%d"),
                to_date=to_date.strftime("%Y-%m-%d"),
            )

            # Limit results
            articles = articles[:limit]

            # Calculate aggregate sentiment
            sentiments = [a.sentiment for a in articles if a.sentiment is not None]
            avg_sentiment = sum(sentiments) / len(sentiments) if sentiments else 0.0

            data = {
                "articles": [a.to_dict() for a in articles],
                "count": len(articles),
                "sentiment": {
                    "average": avg_sentiment,
                    "positive_count": sum(1 for s in sentiments if s > 0.2),
                    "negative_count": sum(1 for s in sentiments if s < -0.2),
                    "neutral_count": sum(1 for s in sentiments if -0.2 <= s <= 0.2),
                },
            }

            return ProviderResponse(
                provider=self.name,
                asset=asset,
                data_type=DataType.NEWS,
                data=data,
                timestamp=datetime.now(timezone.utc),
                is_valid=True,
                is_fresh=True,
                confidence=0.90,
                metadata={
                    "source": "newsapi",
                    "query": query,
                    "sentiment_method": "keyword_based",
                },
            )

        except Exception as e:
            self._record_error()
            logger.error(f"Error fetching news from NewsAPI for {asset.symbol}: {e}")
            raise ProviderError(f"NewsAPI fetch failed: {e}")

    async def supports_asset(self, asset: Asset) -> bool:
        """Check if NewsAPI supports this asset type"""
        # NewsAPI can provide news for any asset type
        return True

    async def get_health(self) -> ProviderHealth:
        """Get NewsAPI provider health"""
        return ProviderHealth(
            provider_name=self.name,
            is_healthy=self._is_initialized,
            uptime_percent=await self.get_uptime_24h(),
            avg_latency_ms=200.0,  # NewsAPI is typically fast
            success_rate=await self.get_success_rate(),
            last_check=datetime.now(timezone.utc),
            error_count_24h=self._error_count,
        )
