"""
Tests for Azure OpenAI Client

Comprehensive test suite covering:
- Client initialization
- All API methods
- Error handling
- Retry logic
- Rate limiting
- Timeout handling
- Health checks
"""

import json
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from fiml.core.exceptions import (
    ConfigurationError,
    ProviderError,
    ProviderTimeoutError,
    RateLimitError,
)
from fiml.llm.azure_client import AzureOpenAIClient


@pytest.fixture
def mock_settings():
    """Mock settings for Azure OpenAI"""
    with patch("fiml.llm.azure_client.settings") as mock:
        mock.azure_openai_endpoint = "https://test.openai.azure.com"
        mock.azure_openai_api_key = "test-api-key"
        mock.azure_openai_deployment_name = "test-deployment"
        mock.azure_openai_api_version = "2024-02-15-preview"
        yield mock


@pytest.fixture
def client(mock_settings):
    """Create Azure OpenAI client for testing"""
    return AzureOpenAIClient()


@pytest.fixture
def mock_response():
    """Create a mock successful Azure OpenAI response"""
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": "This is a test response",
                },
                "finish_reason": "stop",
                "index": 0,
            }
        ],
        "usage": {
            "prompt_tokens": 10,
            "completion_tokens": 20,
            "total_tokens": 30,
        },
    }


class TestClientInitialization:
    """Test client initialization and configuration"""

    def test_init_with_settings(self, mock_settings):
        """Test initialization with settings from config"""
        client = AzureOpenAIClient()

        assert client.endpoint == "https://test.openai.azure.com"
        assert client.api_key == "test-api-key"
        assert client.deployment_name == "test-deployment"
        assert client.api_version == "2024-02-15-preview"
        assert client.timeout == 30
        assert client.max_retries == 3

    def test_init_with_custom_params(self, mock_settings):
        """Test initialization with custom parameters"""
        client = AzureOpenAIClient(
            endpoint="https://custom.openai.azure.com",
            api_key="custom-key",
            deployment_name="custom-deployment",
            api_version="2023-12-01",
            timeout=60,
            max_retries=5,
        )

        assert client.endpoint == "https://custom.openai.azure.com"
        assert client.api_key == "custom-key"
        assert client.deployment_name == "custom-deployment"
        assert client.api_version == "2023-12-01"
        assert client.timeout == 60
        assert client.max_retries == 5

    def test_init_missing_endpoint(self, mock_settings):
        """Test initialization fails without endpoint"""
        mock_settings.azure_openai_endpoint = None

        with pytest.raises(ConfigurationError, match="endpoint is not configured"):
            AzureOpenAIClient()

    def test_init_missing_api_key(self, mock_settings):
        """Test initialization fails without API key"""
        mock_settings.azure_openai_api_key = None

        with pytest.raises(ConfigurationError, match="API key is not configured"):
            AzureOpenAIClient()

    def test_init_missing_deployment_name(self, mock_settings):
        """Test initialization fails without deployment name"""
        mock_settings.azure_openai_deployment_name = None

        with pytest.raises(
            ConfigurationError, match="deployment name is not configured"
        ):
            AzureOpenAIClient()

    def test_endpoint_trailing_slash_removed(self, mock_settings):
        """Test trailing slash is removed from endpoint"""
        client = AzureOpenAIClient(
            endpoint="https://test.openai.azure.com/",
        )

        assert client.endpoint == "https://test.openai.azure.com"


class TestGenerateNarrative:
    """Test narrative generation"""

    @pytest.mark.asyncio
    async def test_generate_narrative_success(self, client, mock_response):
        """Test successful narrative generation"""
        mock_response["choices"][0]["message"]["content"] = (
            "AAPL stock is trading at $175.50, up $2.30 today."
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            context = {
                "asset": "AAPL",
                "price": 175.50,
                "change": 2.3,
            }

            narrative = await client.generate_narrative(context, language="en")

            assert narrative == "AAPL stock is trading at $175.50, up $2.30 today."
            assert client._request_count == 1
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_narrative_different_language(self, client, mock_response):
        """Test narrative generation in different language"""
        mock_response["choices"][0]["message"]["content"] = (
            "AAPL株は$175.50で取引されています。"
        )

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            context = {"asset": "AAPL", "price": 175.50}
            narrative = await client.generate_narrative(context, language="ja")

            assert "AAPL" in narrative
            # Check that language was passed in the request
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert any("ja" in msg["content"] for msg in payload["messages"])


class TestAnalyzeSentiment:
    """Test sentiment analysis"""

    @pytest.mark.asyncio
    async def test_analyze_sentiment_success(self, client, mock_response):
        """Test successful sentiment analysis"""
        sentiment_data = {"positive": 0.75, "negative": 0.05, "neutral": 0.20}
        mock_response["choices"][0]["message"]["content"] = json.dumps(sentiment_data)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            text = "The market is very bullish today"
            sentiment = await client.analyze_sentiment(text)

            assert sentiment == sentiment_data
            assert sentiment["positive"] == 0.75
            assert sentiment["negative"] == 0.05
            assert sentiment["neutral"] == 0.20

    @pytest.mark.asyncio
    async def test_analyze_sentiment_invalid_json(self, client, mock_response):
        """Test sentiment analysis with invalid JSON response"""
        mock_response["choices"][0]["message"]["content"] = "This is not JSON"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            with pytest.raises(ProviderError, match="Invalid JSON"):
                await client.analyze_sentiment("test text")

    @pytest.mark.asyncio
    async def test_analyze_sentiment_missing_keys(self, client, mock_response):
        """Test sentiment analysis with missing required keys"""
        sentiment_data = {"positive": 0.75, "negative": 0.25}  # Missing 'neutral'
        mock_response["choices"][0]["message"]["content"] = json.dumps(sentiment_data)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            with pytest.raises(ProviderError, match="Invalid sentiment response format"):
                await client.analyze_sentiment("test text")


class TestSummarizeAnalysis:
    """Test analysis summarization"""

    @pytest.mark.asyncio
    async def test_summarize_analysis_success(self, client, mock_response):
        """Test successful analysis summarization"""
        summary_text = "Technical indicators show bullish trend with RSI at 65."
        mock_response["choices"][0]["message"]["content"] = summary_text

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            data = {
                "technical_indicators": {"rsi": 65, "macd": "bullish"},
                "fundamentals": {"pe_ratio": 25.5},
            }

            summary = await client.summarize_analysis(data, max_length=500)

            assert summary == summary_text
            mock_post.assert_called_once()

    @pytest.mark.asyncio
    async def test_summarize_analysis_custom_length(self, client, mock_response):
        """Test summarization with custom max length"""
        mock_response["choices"][0]["message"]["content"] = "Short summary."

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            data = {"test": "data"}
            summary = await client.summarize_analysis(data, max_length=100)

            assert summary == "Short summary."
            # Check that max_tokens was calculated based on max_length
            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]
            assert payload["max_tokens"] == 25  # 100 // 4


class TestHealthCheck:
    """Test health check functionality"""

    @pytest.mark.asyncio
    async def test_health_check_success(self, client, mock_response):
        """Test successful health check"""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            health = await client.health_check()

            assert health["available"] is True
            assert health["authenticated"] is True
            assert health["operational"] is True

    @pytest.mark.asyncio
    async def test_health_check_configuration_error(self, mock_settings):
        """Test health check with configuration error"""
        mock_settings.azure_openai_endpoint = None

        with pytest.raises(ConfigurationError):
            AzureOpenAIClient()

    @pytest.mark.asyncio
    async def test_health_check_rate_limited(self, client):
        """Test health check when rate limited"""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=429,
                headers={"Retry-After": "60"},
                text="Rate limit exceeded",
            )

            health = await client.health_check()

            assert health["available"] is True
            assert health["authenticated"] is True
            assert health["operational"] is False

    @pytest.mark.asyncio
    async def test_health_check_timeout(self, client):
        """Test health check with timeout"""
        with patch(
            "httpx.AsyncClient.post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Timeout")

            health = await client.health_check()

            assert health["available"] is False
            assert health["authenticated"] is False
            assert health["operational"] is False

    @pytest.mark.asyncio
    async def test_health_check_invalid_response(self, client):
        """Test health check with invalid response"""
        invalid_response = {"error": "invalid"}

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: invalid_response,
            )

            health = await client.health_check()

            assert health["available"] is True
            assert health["authenticated"] is True
            assert health["operational"] is False


class TestErrorHandling:
    """Test error handling and retry logic"""

    @pytest.mark.asyncio
    async def test_rate_limit_with_retry(self, client, mock_response):
        """Test rate limit handling with successful retry"""
        responses = [
            MagicMock(
                status_code=429,
                headers={"Retry-After": "1"},
                text="Rate limit",
            ),
            MagicMock(
                status_code=200,
                json=lambda: mock_response,
            ),
        ]

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = responses

            with patch("asyncio.sleep", new_callable=AsyncMock):
                narrative = await client.generate_narrative({"test": "data"})

                assert narrative == "This is a test response"
                assert mock_post.call_count == 2
                assert client._rate_limit_count == 1

    @pytest.mark.asyncio
    async def test_rate_limit_exhausted(self, client):
        """Test rate limit with all retries exhausted"""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=429,
                headers={"Retry-After": "60"},
                text="Rate limit",
            )

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(RateLimitError, match="rate limit exceeded"):
                    await client.generate_narrative({"test": "data"})

                assert mock_post.call_count == 3  # max_retries
                assert client._rate_limit_count == 3

    @pytest.mark.asyncio
    async def test_http_error_with_retry(self, client, mock_response):
        """Test HTTP error handling with successful retry"""
        responses = [
            MagicMock(
                status_code=500,
                text="Internal Server Error",
            ),
            MagicMock(
                status_code=200,
                json=lambda: mock_response,
            ),
        ]

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = responses

            with patch("asyncio.sleep", new_callable=AsyncMock):
                narrative = await client.generate_narrative({"test": "data"})

                assert narrative == "This is a test response"
                assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_http_error_exhausted(self, client):
        """Test HTTP error with all retries exhausted"""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=500,
                text="Internal Server Error",
            )

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(ProviderError, match="API error: 500"):
                    await client.generate_narrative({"test": "data"})

                assert mock_post.call_count == 3

    @pytest.mark.asyncio
    async def test_timeout_with_retry(self, client, mock_response):
        """Test timeout handling with successful retry"""
        side_effects = [
            httpx.TimeoutException("Timeout"),
            MagicMock(
                status_code=200,
                json=lambda: mock_response,
            ),
        ]

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = side_effects

            with patch("asyncio.sleep", new_callable=AsyncMock):
                narrative = await client.generate_narrative({"test": "data"})

                assert narrative == "This is a test response"
                assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_timeout_exhausted(self, client):
        """Test timeout with all retries exhausted"""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Timeout")

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(ProviderTimeoutError, match="timeout after 3 attempts"):
                    await client.generate_narrative({"test": "data"})

                assert mock_post.call_count == 3

    @pytest.mark.asyncio
    async def test_request_error_with_retry(self, client, mock_response):
        """Test request error handling with successful retry"""
        side_effects = [
            httpx.RequestError("Connection failed"),
            MagicMock(
                status_code=200,
                json=lambda: mock_response,
            ),
        ]

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = side_effects

            with patch("asyncio.sleep", new_callable=AsyncMock):
                narrative = await client.generate_narrative({"test": "data"})

                assert narrative == "This is a test response"
                assert mock_post.call_count == 2

    @pytest.mark.asyncio
    async def test_exponential_backoff(self, client):
        """Test exponential backoff timing"""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=500,
                text="Error",
            )

            sleep_times = []

            async def mock_sleep(duration):
                sleep_times.append(duration)

            with patch("asyncio.sleep", side_effect=mock_sleep):
                with pytest.raises(ProviderError):
                    await client.generate_narrative({"test": "data"})

                # Check exponential backoff: 2^0=1, 2^1=2
                assert sleep_times == [1, 2]


class TestMetrics:
    """Test client metrics tracking"""

    def test_get_metrics_initial(self, client):
        """Test initial metrics"""
        metrics = client.get_metrics()

        assert metrics["request_count"] == 0
        assert metrics["error_count"] == 0
        assert metrics["rate_limit_count"] == 0
        assert metrics["last_request_time"] is None

    @pytest.mark.asyncio
    async def test_get_metrics_after_request(self, client, mock_response):
        """Test metrics after successful request"""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            await client.generate_narrative({"test": "data"})

            metrics = client.get_metrics()
            assert metrics["request_count"] == 1
            assert metrics["error_count"] == 0
            assert metrics["last_request_time"] is not None

    @pytest.mark.asyncio
    async def test_get_metrics_after_error(self, client):
        """Test metrics after error"""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=500,
                text="Error",
            )

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(ProviderError):
                    await client.generate_narrative({"test": "data"})

                metrics = client.get_metrics()
                assert metrics["request_count"] == 3  # 3 retries
                assert metrics["error_count"] == 3
                assert metrics["last_request_time"] is not None


class TestRequestConstruction:
    """Test request URL and header construction"""

    @pytest.mark.asyncio
    async def test_request_url_construction(self, client, mock_response):
        """Test that request URL is correctly constructed"""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            await client.generate_narrative({"test": "data"})

            expected_url = (
                "https://test.openai.azure.com/openai/deployments/test-deployment"
                "/chat/completions?api-version=2024-02-15-preview"
            )

            call_args = mock_post.call_args
            assert call_args.args[0] == expected_url

    @pytest.mark.asyncio
    async def test_request_headers(self, client, mock_response):
        """Test that request headers are correctly set"""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            await client.generate_narrative({"test": "data"})

            call_args = mock_post.call_args
            headers = call_args.kwargs["headers"]

            assert headers["Content-Type"] == "application/json"
            assert headers["api-key"] == "test-api-key"

    @pytest.mark.asyncio
    async def test_request_payload_structure(self, client, mock_response):
        """Test that request payload has correct structure"""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = MagicMock(
                status_code=200,
                json=lambda: mock_response,
            )

            await client.generate_narrative({"test": "data"})

            call_args = mock_post.call_args
            payload = call_args.kwargs["json"]

            assert "messages" in payload
            assert isinstance(payload["messages"], list)
            assert "temperature" in payload
            assert "max_tokens" in payload
            assert payload["temperature"] == 0.7
            assert payload["max_tokens"] == 500


class TestEdgeCases:
    """Test edge cases and additional coverage"""

    @pytest.mark.asyncio
    async def test_request_error_exhausted(self, client):
        """Test request error with all retries exhausted"""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.RequestError("Connection failed")

            with patch("asyncio.sleep", new_callable=AsyncMock):
                with pytest.raises(ProviderError, match="failed after 3 attempts"):
                    await client.generate_narrative({"test": "data"})

                assert mock_post.call_count == 3

    @pytest.mark.asyncio
    async def test_summarize_analysis_exception(self, client):
        """Test summarize_analysis with unexpected exception"""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Unexpected error")

            with pytest.raises(Exception, match="Unexpected error"):
                await client.summarize_analysis({"test": "data"})

    @pytest.mark.asyncio
    async def test_health_check_generic_exception(self, client):
        """Test health_check with generic exception"""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = Exception("Unexpected error")

            health = await client.health_check()

            assert health["available"] is False
            assert health["authenticated"] is False
            assert health["operational"] is False

    @pytest.mark.asyncio
    async def test_health_check_configuration_error_during_check(self, client):
        """Test health_check when ConfigurationError occurs during check"""
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = ConfigurationError("Configuration issue")

            health = await client.health_check()

            assert health["available"] is False
            assert health["authenticated"] is False
            assert health["operational"] is False

