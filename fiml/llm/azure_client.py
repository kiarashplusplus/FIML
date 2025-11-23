"""
Azure OpenAI Client Implementation

Provides integration with Azure OpenAI services for natural language processing tasks.
Includes comprehensive error handling, retry logic, and rate limiting.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import httpx

from fiml.core.config import settings
from fiml.core.exceptions import (
    ConfigurationError,
    ProviderError,
    ProviderTimeoutError,
    RateLimitError,
)
from fiml.core.logging import get_logger

logger = get_logger(__name__)


class AzureOpenAIClient:
    """
    Azure OpenAI client with retry logic and error handling

    Provides methods for:
    - Narrative generation
    - Sentiment analysis
    - Data summarization
    - Health checks

    Configuration is loaded from settings (fiml.core.config):
    - azure_openai_endpoint
    - azure_openai_api_key
    - azure_openai_deployment_name
    - azure_openai_api_version
    """

    def __init__(
        self,
        endpoint: Optional[str] = None,
        api_key: Optional[str] = None,
        deployment_name: Optional[str] = None,
        api_version: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3,
    ):
        """
        Initialize Azure OpenAI client

        Args:
            endpoint: Azure OpenAI endpoint URL (defaults to settings)
            api_key: Azure OpenAI API key (defaults to settings)
            deployment_name: Deployment name (defaults to settings)
            api_version: API version (defaults to settings)
            timeout: Request timeout in seconds (default: 30)
            max_retries: Maximum number of retry attempts (default: 3)

        Raises:
            ConfigurationError: If required configuration is missing
        """
        self.endpoint = endpoint or settings.azure_openai_endpoint
        self.api_key = api_key or settings.azure_openai_api_key
        self.deployment_name = deployment_name or settings.azure_openai_deployment_name
        self.api_version = api_version or settings.azure_openai_api_version
        self.timeout = timeout
        self.max_retries = max_retries

        # Validate configuration
        if not self.endpoint:
            raise ConfigurationError("Azure OpenAI endpoint is not configured")
        if not self.api_key:
            raise ConfigurationError("Azure OpenAI API key is not configured")
        if not self.deployment_name:
            raise ConfigurationError("Azure OpenAI deployment name is not configured")

        # Remove trailing slash from endpoint
        self.endpoint = self.endpoint.rstrip("/")

        # Track request metrics
        self._request_count = 0
        self._error_count = 0
        self._rate_limit_count = 0
        self._last_request_time: Optional[datetime] = None

        logger.info(
            "Azure OpenAI client initialized",
            endpoint=self.endpoint,
            deployment=self.deployment_name,
            api_version=self.api_version,
        )

    async def _make_request(
        self,
        messages: list[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
    ) -> Dict[str, Any]:
        """
        Make a request to Azure OpenAI with retry logic

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens in response

        Returns:
            Response dictionary from Azure OpenAI

        Raises:
            ProviderError: On API errors
            ProviderTimeoutError: On timeout
            RateLimitError: On rate limit exceeded
        """
        url = (
            f"{self.endpoint}/openai/deployments/{self.deployment_name}"
            f"/chat/completions?api-version={self.api_version}"
        )

        headers: Dict[str, str] = {
            "Content-Type": "application/json",
            "api-key": self.api_key,  # type: ignore[dict-item]
        }

        payload = {
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_exception: Optional[Exception] = None

        for attempt in range(self.max_retries):
            try:
                self._request_count += 1
                self._last_request_time = datetime.now(timezone.utc)

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        url,
                        headers=headers,
                        json=payload,
                        timeout=self.timeout,
                    )

                    # Handle rate limiting
                    if response.status_code == 429:
                        self._rate_limit_count += 1
                        retry_after = int(response.headers.get("Retry-After", 60))

                        if attempt < self.max_retries - 1:
                            wait_time = min(retry_after, 2 ** attempt)
                            logger.warning(
                                "Rate limit hit, retrying",
                                attempt=attempt + 1,
                                wait_time=wait_time,
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise RateLimitError(
                                "Azure OpenAI rate limit exceeded",
                                retry_after=retry_after,
                            )

                    # Handle other HTTP errors
                    if response.status_code != 200:
                        error_text = response.text
                        self._error_count += 1
                        logger.error(
                            "Azure OpenAI API error",
                            status_code=response.status_code,
                            error=error_text,
                        )

                        if attempt < self.max_retries - 1:
                            # Exponential backoff
                            wait_time = 2 ** attempt
                            logger.warning(
                                "Retrying request",
                                attempt=attempt + 1,
                                wait_time=wait_time,
                            )
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            raise ProviderError(
                                f"Azure OpenAI API error: {response.status_code} - {error_text}"
                            )

                    # Success
                    return response.json()  # type: ignore[no-any-return]

            except httpx.TimeoutException as e:
                last_exception = e
                self._error_count += 1
                logger.warning(
                    "Request timeout",
                    attempt=attempt + 1,
                    timeout=self.timeout,
                )

                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue

            except httpx.RequestError as e:
                last_exception = e
                self._error_count += 1
                logger.error(
                    "Request error",
                    attempt=attempt + 1,
                    error=str(e),
                )

                if attempt < self.max_retries - 1:
                    wait_time = 2 ** attempt
                    await asyncio.sleep(wait_time)
                    continue

        # All retries exhausted
        if isinstance(last_exception, httpx.TimeoutException):
            raise ProviderTimeoutError(
                f"Azure OpenAI request timeout after {self.max_retries} attempts"
            )
        else:
            raise ProviderError(
                f"Azure OpenAI request failed after {self.max_retries} attempts: {last_exception}"
            )

    async def generate_narrative(
        self, context: Dict[str, Any], language: str = "en"
    ) -> str:
        """
        Generate a natural language narrative from context data

        Args:
            context: Dictionary containing context information
            language: Target language code (default: "en")

        Returns:
            Generated narrative text

        Raises:
            ProviderError: On API errors
            ConfigurationError: If client not properly configured

        Example:
            >>> client = AzureOpenAIClient()
            >>> context = {
            ...     "asset": "AAPL",
            ...     "price": 175.50,
            ...     "change": 2.3,
            ...     "volume": 75000000
            ... }
            >>> narrative = await client.generate_narrative(context)
        """
        logger.info("Generating narrative", language=language)

        # Build system and user messages
        system_message = {
            "role": "system",
            "content": (
                f"You are a financial analyst creating concise narratives in {language}. "
                "Analyze the provided context and generate a clear, professional summary."
            ),
        }

        user_message = {
            "role": "user",
            "content": f"Generate a narrative based on this context:\n{json.dumps(context, indent=2)}",
        }

        try:
            response = await self._make_request(
                messages=[system_message, user_message],
                temperature=0.7,
                max_tokens=500,
            )

            narrative = response["choices"][0]["message"]["content"]
            logger.info("Narrative generated successfully", length=len(narrative))
            return narrative  # type: ignore[return-value]

        except Exception as e:
            logger.error("Failed to generate narrative", error=str(e))
            raise

    async def analyze_sentiment(self, text: str) -> Dict[str, float]:
        """
        Analyze sentiment of text

        Args:
            text: Text to analyze

        Returns:
            Dictionary with sentiment scores:
            - positive: Score for positive sentiment (0.0 to 1.0)
            - negative: Score for negative sentiment (0.0 to 1.0)
            - neutral: Score for neutral sentiment (0.0 to 1.0)

        Raises:
            ProviderError: On API errors

        Example:
            >>> client = AzureOpenAIClient()
            >>> sentiment = await client.analyze_sentiment("The market is bullish today")
            >>> print(sentiment)
            {"positive": 0.75, "negative": 0.05, "neutral": 0.20}
        """
        logger.info("Analyzing sentiment", text_length=len(text))

        system_message = {
            "role": "system",
            "content": (
                "You are a sentiment analysis expert. Analyze the sentiment of the provided text "
                "and return ONLY a JSON object with three fields: positive, negative, and neutral. "
                "Each field should be a number between 0 and 1, and they should sum to 1.0. "
                'Example: {"positive": 0.7, "negative": 0.1, "neutral": 0.2}'
            ),
        }

        user_message = {
            "role": "user",
            "content": f"Analyze the sentiment of this text:\n{text}",
        }

        try:
            response = await self._make_request(
                messages=[system_message, user_message],
                temperature=0.3,
                max_tokens=100,
            )

            content = response["choices"][0]["message"]["content"]

            # Parse JSON response
            sentiment_scores = json.loads(content)

            # Validate response format
            required_keys = {"positive", "negative", "neutral"}
            if not all(key in sentiment_scores for key in required_keys):
                raise ProviderError("Invalid sentiment response format")

            logger.info("Sentiment analyzed successfully", scores=sentiment_scores)
            return sentiment_scores  # type: ignore[return-value]

        except json.JSONDecodeError as e:
            logger.error("Failed to parse sentiment response", error=str(e))
            raise ProviderError(f"Invalid JSON in sentiment response: {e}")
        except Exception as e:
            logger.error("Failed to analyze sentiment", error=str(e))
            raise

    async def summarize_analysis(
        self, data: Dict[str, Any], max_length: int = 500
    ) -> str:
        """
        Summarize analysis data into concise text

        Args:
            data: Dictionary containing analysis data to summarize
            max_length: Maximum length of summary in characters (default: 500)

        Returns:
            Summary text

        Raises:
            ProviderError: On API errors

        Example:
            >>> client = AzureOpenAIClient()
            >>> data = {
            ...     "technical_indicators": {...},
            ...     "fundamentals": {...},
            ...     "news_sentiment": {...}
            ... }
            >>> summary = await client.summarize_analysis(data, max_length=300)
        """
        logger.info("Summarizing analysis", max_length=max_length)

        # Calculate approximate max_tokens (roughly 4 characters per token)
        max_tokens = min(max_length // 4, 1000)

        system_message = {
            "role": "system",
            "content": (
                "You are a financial analyst. Create concise summaries of analysis data. "
                f"Keep summaries under {max_length} characters. Focus on key insights and actionable information."
            ),
        }

        user_message = {
            "role": "user",
            "content": f"Summarize this analysis data:\n{json.dumps(data, indent=2)}",
        }

        try:
            response = await self._make_request(
                messages=[system_message, user_message],
                temperature=0.5,
                max_tokens=max_tokens,
            )

            summary = response["choices"][0]["message"]["content"]
            logger.info("Analysis summarized successfully", length=len(summary))
            return summary  # type: ignore[return-value]

        except Exception as e:
            logger.error("Failed to summarize analysis", error=str(e))
            raise

    async def health_check(self) -> Dict[str, bool]:
        """
        Check health of Azure OpenAI service

        Returns:
            Dictionary with health status:
            - available: Whether service is available
            - authenticated: Whether authentication is valid
            - operational: Whether service is fully operational

        Example:
            >>> client = AzureOpenAIClient()
            >>> health = await client.health_check()
            >>> print(health)
            {"available": True, "authenticated": True, "operational": True}
        """
        logger.info("Performing health check")

        health_status = {
            "available": False,
            "authenticated": False,
            "operational": False,
        }

        try:
            # Simple test request
            messages = [
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'OK' if you can read this."},
            ]

            response = await self._make_request(
                messages=messages,
                temperature=0.0,
                max_tokens=10,
            )

            # If we got here, service is available and authenticated
            health_status["available"] = True
            health_status["authenticated"] = True

            # Check if response is valid
            if response.get("choices") and len(response["choices"]) > 0:
                health_status["operational"] = True

            logger.info("Health check completed", status=health_status)
            return health_status

        except ConfigurationError as e:
            logger.error("Health check failed: configuration error", error=str(e))
            return health_status

        except RateLimitError as e:
            logger.warning("Health check rate limited", error=str(e))
            # Service is available but rate limited
            health_status["available"] = True
            health_status["authenticated"] = True
            return health_status

        except ProviderTimeoutError as e:
            logger.error("Health check timeout", error=str(e))
            return health_status

        except Exception as e:
            logger.error("Health check failed", error=str(e))
            return health_status

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get client metrics

        Returns:
            Dictionary with metrics:
            - request_count: Total number of requests made
            - error_count: Total number of errors
            - rate_limit_count: Number of rate limit hits
            - last_request_time: Timestamp of last request
        """
        return {
            "request_count": self._request_count,
            "error_count": self._error_count,
            "rate_limit_count": self._rate_limit_count,
            "last_request_time": (
                self._last_request_time.isoformat() if self._last_request_time else None
            ),
        }
