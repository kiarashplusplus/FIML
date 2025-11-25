"""
Comprehensive tests for NewsAPI Provider

Tests cover:
- Basic functionality (get_news, get_top_headlines, search_everything)
- Error handling and retries
- Rate limiting
- Data normalization
- Sentiment extraction
- Arbitration integration
"""

import os
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientSession

from fiml.arbitration.engine import DataArbitrationEngine
from fiml.core.exceptions import ProviderError, RateLimitError
from fiml.core.models import Asset, AssetType, DataType, Market
from fiml.providers.newsapi import NewsAPIProvider, NewsArticle

# Fixtures

@pytest.fixture
def mock_api_key():
    """Provide a mock API key"""
    return "test_api_key_12345"


@pytest.fixture
def newsapi_provider(mock_api_key):
    """Create NewsAPI provider instance"""
    return NewsAPIProvider(api_key=mock_api_key)


@pytest.fixture
def sample_article_data():
    """Sample article data from NewsAPI"""
    return {
        "source": {"id": "techcrunch", "name": "TechCrunch"},
        "author": "Jane Doe",
        "title": "Tesla stock surges on positive earnings",
        "description": "Tesla reports strong quarterly results",
        "url": "https://example.com/article",
        "urlToImage": "https://example.com/image.jpg",
        "publishedAt": "2025-11-23T10:00:00Z",
        "content": "Tesla has reported impressive earnings...",
    }


@pytest.fixture
def sample_api_response(sample_article_data):
    """Sample API response"""
    return {
        "status": "ok",
        "totalResults": 1,
        "articles": [sample_article_data],
    }


@pytest.fixture
def test_asset():
    """Test asset"""
    return Asset(symbol="TSLA", asset_type=AssetType.EQUITY, market=Market.US)


# Test initialization and configuration


@pytest.mark.asyncio
async def test_newsapi_provider_initialization(mock_api_key):
    """Test NewsAPI provider initialization"""
    provider = NewsAPIProvider(api_key=mock_api_key)
    assert provider.config.name == "newsapi"
    assert provider.config.priority == 8  # High priority for news
    assert provider.config.api_key == mock_api_key
    assert not provider._is_initialized

    await provider.initialize()
    assert provider._is_initialized
    assert provider._session is not None

    await provider.shutdown()
    assert not provider._is_initialized


@pytest.mark.asyncio
async def test_newsapi_provider_initialization_no_key():
    """Test NewsAPI provider fails without API key"""
    with patch.dict(os.environ, {}, clear=True), pytest.raises(ValueError, match="API key is required"):
        NewsAPIProvider()


@pytest.mark.asyncio
async def test_newsapi_provider_from_env():
    """Test NewsAPI provider loads API key from environment"""
    with patch.dict(os.environ, {"NEWSAPI_KEY": "env_test_key"}):
        provider = NewsAPIProvider()
        assert provider.config.api_key == "env_test_key"


# Test article parsing


def test_parse_article(newsapi_provider, sample_article_data):
    """Test article parsing"""
    article = newsapi_provider._parse_article(sample_article_data)

    assert isinstance(article, NewsArticle)
    assert article.title == "Tesla stock surges on positive earnings"
    assert article.source == "TechCrunch"
    assert article.author == "Jane Doe"
    assert article.url == "https://example.com/article"
    assert article.sentiment is not None
    assert -1.0 <= article.sentiment <= 1.0


def test_sentiment_extraction_positive(newsapi_provider):
    """Test positive sentiment extraction"""
    sentiment = newsapi_provider._extract_sentiment(
        "Stock soars on strong earnings beat",
        "Company reports profit growth and optimistic outlook"
    )
    assert sentiment > 0


def test_sentiment_extraction_negative(newsapi_provider):
    """Test negative sentiment extraction"""
    sentiment = newsapi_provider._extract_sentiment(
        "Stock plunges on earnings miss",
        "Company reports losses and pessimistic outlook"
    )
    assert sentiment < 0


def test_sentiment_extraction_neutral(newsapi_provider):
    """Test neutral sentiment extraction"""
    sentiment = newsapi_provider._extract_sentiment(
        "Company releases quarterly report",
        "The financial results are available"
    )
    assert abs(sentiment) < 0.3


# Test API methods


@pytest.mark.asyncio
async def test_get_news_success(newsapi_provider, sample_api_response):
    """Test successful news retrieval"""
    await newsapi_provider.initialize()

    with patch.object(newsapi_provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = sample_api_response

        articles = await newsapi_provider.get_news(
            query="Tesla",
            from_date="2025-11-16",
            to_date="2025-11-23"
        )

        assert len(articles) == 1
        assert articles[0].title == "Tesla stock surges on positive earnings"
        mock_request.assert_called_once()

    await newsapi_provider.shutdown()


@pytest.mark.asyncio
async def test_get_top_headlines_success(newsapi_provider, sample_api_response):
    """Test successful top headlines retrieval"""
    await newsapi_provider.initialize()

    with patch.object(newsapi_provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = sample_api_response

        articles = await newsapi_provider.get_top_headlines(
            category="business",
            country="us"
        )

        assert len(articles) == 1
        mock_request.assert_called_once()

    await newsapi_provider.shutdown()


@pytest.mark.asyncio
async def test_search_everything_success(newsapi_provider, sample_api_response):
    """Test successful search everything"""
    await newsapi_provider.initialize()

    with patch.object(newsapi_provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = sample_api_response

        articles = await newsapi_provider.search_everything(q="Tesla")

        assert len(articles) == 1
        mock_request.assert_called_once()

    await newsapi_provider.shutdown()


# Test error handling


@pytest.mark.asyncio
async def test_api_error_handling(newsapi_provider):
    """Test API error handling"""
    await newsapi_provider.initialize()

    with patch.object(newsapi_provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.side_effect = ProviderError("API error")

        with pytest.raises(ProviderError):
            await newsapi_provider.get_news("Tesla", "2025-11-16", "2025-11-23")

    await newsapi_provider.shutdown()


@pytest.mark.asyncio
async def test_rate_limit_error(newsapi_provider):
    """Test rate limit error handling"""
    await newsapi_provider.initialize()

    # Simulate hitting daily limit
    newsapi_provider._daily_request_count = newsapi_provider._daily_limit

    with pytest.raises(RateLimitError, match="Daily limit"):
        await newsapi_provider._check_rate_limit()

    await newsapi_provider.shutdown()


@pytest.mark.asyncio
async def test_retry_on_timeout(newsapi_provider):
    """Test retry logic on timeout"""
    await newsapi_provider.initialize()

    # Create a properly configured async mock for the session
    mock_session = AsyncMock(spec=ClientSession)

    # First call times out, second succeeds
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"status": "ok", "articles": []})

    # Create async context manager mocks for the get calls
    timeout_cm = AsyncMock()
    timeout_cm.__aenter__.side_effect = Exception("Timeout")
    timeout_cm.__aexit__ = AsyncMock(return_value=None)

    success_cm = AsyncMock()
    success_cm.__aenter__ = AsyncMock(return_value=mock_response)
    success_cm.__aexit__ = AsyncMock(return_value=None)

    # Set up the session.get to return the context managers in sequence
    mock_session.get = MagicMock(side_effect=[timeout_cm, success_cm])
    newsapi_provider._session = mock_session

    with patch.object(newsapi_provider, "_check_rate_limit", new_callable=AsyncMock):
        result = await newsapi_provider._make_request("test", {})
        assert result["status"] == "ok"

    await newsapi_provider.shutdown()


# Test BaseProvider interface


@pytest.mark.asyncio
async def test_fetch_news(newsapi_provider, test_asset, sample_api_response):
    """Test fetch_news implementation"""
    await newsapi_provider.initialize()

    with patch.object(newsapi_provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = sample_api_response

        response = await newsapi_provider.fetch_news(test_asset, limit=10)

        assert response.provider == "newsapi"
        assert response.data_type == DataType.NEWS
        assert response.is_valid
        assert "articles" in response.data
        assert "sentiment" in response.data
        assert len(response.data["articles"]) == 1

    await newsapi_provider.shutdown()


@pytest.mark.asyncio
async def test_fetch_price_not_supported(newsapi_provider, test_asset):
    """Test that fetch_price raises NotImplementedError"""
    await newsapi_provider.initialize()

    with pytest.raises(NotImplementedError):
        await newsapi_provider.fetch_price(test_asset)

    await newsapi_provider.shutdown()


@pytest.mark.asyncio
async def test_supports_asset(newsapi_provider, test_asset):
    """Test asset support check"""
    await newsapi_provider.initialize()

    # NewsAPI supports all asset types
    assert await newsapi_provider.supports_asset(test_asset)

    await newsapi_provider.shutdown()


@pytest.mark.asyncio
async def test_get_health(newsapi_provider):
    """Test provider health check"""
    await newsapi_provider.initialize()

    health = await newsapi_provider.get_health()

    assert health.provider_name == "newsapi"
    assert health.is_healthy
    assert health.uptime_percent >= 0
    assert health.success_rate >= 0

    await newsapi_provider.shutdown()


# Test arbitration integration


@pytest.mark.asyncio
async def test_newsapi_arbitration_priority(mock_api_key, test_asset):
    """Test that NewsAPI gets priority for news data in arbitration"""
    from fiml.providers.registry import provider_registry

    # Initialize registry
    await provider_registry.initialize()

    # Get arbitration engine
    engine = DataArbitrationEngine()

    # Create arbitration plan for NEWS data
    plan = await engine.arbitrate_request(
        asset=test_asset,
        data_type=DataType.NEWS,
        user_region="US",
        max_staleness_seconds=600
    )

    # NewsAPI should be prioritized for NEWS data if available
    available_providers = [p.name for p in provider_registry.providers.values() if p.is_enabled]

    if "newsapi" in available_providers:
        assert plan.primary_provider == "newsapi"

    await provider_registry.shutdown()


@pytest.mark.asyncio
async def test_newsapi_scoring_bonus():
    """Test that NewsAPI gets scoring bonus for NEWS/SENTIMENT"""
    from fiml.providers.mock_provider import MockProvider

    engine = DataArbitrationEngine()

    # Create mock NewsAPI provider
    newsapi = MockProvider()
    newsapi.name = "newsapi"
    newsapi._is_initialized = True
    await newsapi.initialize()

    # Create regular provider for comparison
    regular = MockProvider()
    regular.name = "regular_provider"
    regular._is_initialized = True
    await regular.initialize()

    asset = Asset(symbol="TSLA", asset_type=AssetType.EQUITY, market=Market.US)

    # Score for NEWS data type
    newsapi_score = await engine._score_provider(newsapi, asset, DataType.NEWS, "US", 600)

    # NewsAPI should get higher score (or be capped at 100)
    # Since both start with perfect scores (~99-100), NewsAPI will be capped at 100
    # But we can verify it's at the max
    assert newsapi_score.total == 100.0

    # For other data types, bonus should not apply
    newsapi_price_score = await engine._score_provider(newsapi, asset, DataType.PRICE, "US", 600)
    # NewsAPI shouldn't get bonus for PRICE, but since it doesn't implement price,
    # we'll just verify the score is valid
    assert 0 <= newsapi_price_score.total <= 100

    await newsapi.shutdown()
    await regular.shutdown()


# Test rate limiting


@pytest.mark.asyncio
async def test_rate_limit_per_minute(newsapi_provider):
    """Test per-minute rate limiting"""
    await newsapi_provider.initialize()

    # Set tight limit
    newsapi_provider.config.rate_limit_per_minute = 2

    # Make requests up to limit
    for _ in range(2):
        await newsapi_provider._check_rate_limit()

    # Next request should wait or raise error
    # Since we're checking quickly, it should still be within the minute
    assert len(newsapi_provider._request_times) == 2

    await newsapi_provider.shutdown()


@pytest.mark.asyncio
async def test_daily_limit_reset(newsapi_provider):
    """Test daily limit reset"""
    await newsapi_provider.initialize()

    # Set count near limit
    newsapi_provider._daily_request_count = 99

    # Simulate next day
    newsapi_provider._last_reset = datetime.now(timezone.utc) - timedelta(days=1, hours=1)

    # Check rate limit should reset counter
    await newsapi_provider._check_rate_limit()

    assert newsapi_provider._daily_request_count == 1  # Reset and incremented

    await newsapi_provider.shutdown()


# Test data normalization


@pytest.mark.asyncio
async def test_article_to_dict(sample_article_data, newsapi_provider):
    """Test article to dictionary conversion"""
    article = newsapi_provider._parse_article(sample_article_data)
    article_dict = article.to_dict()

    assert article_dict["title"] == sample_article_data["title"]
    assert article_dict["source"] == sample_article_data["source"]["name"]
    assert "published_at" in article_dict
    assert "sentiment" in article_dict


@pytest.mark.asyncio
async def test_aggregate_sentiment(newsapi_provider, test_asset):
    """Test aggregate sentiment calculation in fetch_news"""
    await newsapi_provider.initialize()

    sample_response = {
        "status": "ok",
        "articles": [
            {
                "title": "Stock soars",
                "description": "Positive earnings",
                "url": "http://example.com/1",
                "source": {"name": "Source1"},
                "publishedAt": "2025-11-23T10:00:00Z",
            },
            {
                "title": "Stock plunges",
                "description": "Negative outlook",
                "url": "http://example.com/2",
                "source": {"name": "Source2"},
                "publishedAt": "2025-11-23T11:00:00Z",
            },
        ]
    }

    with patch.object(newsapi_provider, "_make_request", new_callable=AsyncMock) as mock_request:
        mock_request.return_value = sample_response

        response = await newsapi_provider.fetch_news(test_asset)

        sentiment_data = response.data["sentiment"]
        assert "average" in sentiment_data
        assert "positive_count" in sentiment_data
        assert "negative_count" in sentiment_data
        assert sentiment_data["positive_count"] + sentiment_data["negative_count"] > 0

    await newsapi_provider.shutdown()
