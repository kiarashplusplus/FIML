"""
Azure OpenAI Client Implementation

Provides integration with Azure OpenAI services for natural language processing tasks.
Includes comprehensive error handling, retry logic, and rate limiting.
"""

import asyncio
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, cast

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
        messages: List[Dict[str, str]],
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
            "max_completion_tokens": max_tokens,  # Use max_completion_tokens for newer models
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

                        # Special handling for O1 models that only support temperature=1
                        if response.status_code == 400 and "temperature" in error_text and "1" in error_text:
                            logger.warning(
                                "Model requires temperature=1.0, retrying",
                                attempt=attempt + 1,
                            )
                            payload["temperature"] = 1.0
                            # Don't increment attempt counter for this adjustment, just retry immediately
                            # But we need to be careful not to infinite loop.
                            # Since we modify payload, next loop will use temp=1.0.
                            # We can just continue to next attempt, or recurse.
                            # Simplest is to modify payload and let the loop continue (consuming an attempt)
                            # or just continue.
                            # Actually, if I just modify payload and continue, it will retry with new payload.
                            continue

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
            return cast(str, narrative)

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

            content = cast(str, response["choices"][0]["message"]["content"])

            # Parse JSON response
            sentiment_scores = json.loads(content)

            # Validate response format
            required_keys = {"positive", "negative", "neutral"}
            if not all(key in sentiment_scores for key in required_keys):
                raise ProviderError("Invalid sentiment response format")

            logger.info("Sentiment analyzed successfully", scores=sentiment_scores)
            return cast(Dict[str, float], sentiment_scores)

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
            return cast(str, summary)

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

    # ==========================================================================
    # Market-Specific Narrative Generation Methods
    # ==========================================================================

    async def generate_market_summary(
        self,
        data: Dict[str, Any],
        style: str = "professional",
    ) -> str:
        """
        Generate market summary narrative for an asset

        Args:
            data: Market data containing price, volume, metrics
            style: Narrative style (professional, concise, detailed)

        Returns:
            Market summary narrative

        Raises:
            ProviderError: On API errors

        Example:
            >>> data = {
            ...     "symbol": "AAPL",
            ...     "price": 175.50,
            ...     "change": 4.25,
            ...     "change_percent": 2.48,
            ...     "volume": 75000000,
            ... }
            >>> summary = await client.generate_market_summary(data)
        """
        logger.info("Generating market summary", symbol=data.get("symbol"))

        system_message = {
            "role": "system",
            "content": (
                "You are a financial analyst providing factual market insights. "
                "Use clear, professional language. Avoid predictive statements - use 'currently', "
                "'historically', 'as of today'. Include data sources when available. "
                "IMPORTANT: End with: 'This is not financial advice. FIML provides data analysis only.'"
            ),
        }

        user_message = {
            "role": "user",
            "content": (
                f"Generate a {style} market summary for {data.get('symbol', 'this asset')}:\n"
                f"{json.dumps(data, indent=2)}\n\n"
                "Include: current price, price movement, volume analysis, 52-week position."
            ),
        }

        try:
            max_tokens = {"concise": 300, "professional": 500, "detailed": 800}.get(
                style, 500
            )

            response = await self._make_request(
                messages=[system_message, user_message],
                temperature=0.5,
                max_tokens=max_tokens,
            )

            summary = response["choices"][0]["message"]["content"]
            logger.info("Market summary generated", length=len(summary))
            return cast(str, summary)

        except Exception as e:
            logger.error("Failed to generate market summary", error=str(e))
            # Fallback to template-based narrative
            return self._fallback_market_summary(data)

    async def explain_price_movement(
        self,
        symbol: str,
        change_pct: float,
        volume: int,
        news: Optional[list] = None,
    ) -> str:
        """
        Explain price movement with context

        Args:
            symbol: Asset symbol
            change_pct: Price change percentage
            volume: Trading volume
            news: Optional news headlines

        Returns:
            Price movement explanation

        Example:
            >>> explanation = await client.explain_price_movement(
            ...     "AAPL", 2.48, 75000000, ["Q4 earnings beat estimates"]
            ... )
        """
        logger.info("Explaining price movement", symbol=symbol, change_pct=change_pct)

        system_message = {
            "role": "system",
            "content": (
                "You are a financial analyst explaining price movements. "
                "Provide factual analysis based on provided data. "
                "Avoid speculation about future prices. Use terms like 'currently', 'today'. "
                "Cite data sources. End with compliance disclaimer."
            ),
        }

        news_context = ""
        if news:
            news_context = f"\nRecent news: {', '.join(news[:3])}"

        user_message = {
            "role": "user",
            "content": (
                f"Explain the price movement for {symbol}:\n"
                f"- Change: {change_pct:+.2f}%\n"
                f"- Volume: {volume:,}{news_context}\n\n"
                "Provide clear explanation of what drove this movement."
            ),
        }

        try:
            response = await self._make_request(
                messages=[system_message, user_message],
                temperature=0.6,
                max_tokens=400,
            )

            explanation = response["choices"][0]["message"]["content"]
            logger.info("Price movement explained", length=len(explanation))
            return cast(str, explanation)

        except Exception as e:
            logger.error("Failed to explain price movement", error=str(e))
            return self._fallback_price_movement(symbol, change_pct, volume)

    async def interpret_technical_indicators(
        self,
        rsi: Optional[float] = None,
        macd: Optional[Dict[str, float]] = None,
        bollinger: Optional[Dict[str, float]] = None,
    ) -> str:
        """
        Interpret technical indicators

        Args:
            rsi: RSI value (0-100)
            macd: MACD values {macd, signal, histogram}
            bollinger: Bollinger bands {upper, middle, lower, current}

        Returns:
            Technical indicator interpretation

        Example:
            >>> interpretation = await client.interpret_technical_indicators(
            ...     rsi=65.3,
            ...     macd={"macd": 2.45, "signal": 1.92, "histogram": 0.53}
            ... )
        """
        logger.info("Interpreting technical indicators")

        indicators_data: Dict[str, Any] = {}
        if rsi is not None:
            indicators_data["RSI"] = rsi
        if macd:
            indicators_data["MACD"] = macd
        if bollinger:
            indicators_data["Bollinger Bands"] = bollinger

        system_message = {
            "role": "system",
            "content": (
                "You are a technical analyst interpreting indicators. "
                "Explain what indicators currently show. Avoid predictions. "
                "Use 'indicates', 'suggests', 'historically'. "
                "Include disclaimer: 'This is technical analysis, not investment advice.'"
            ),
        }

        user_message = {
            "role": "user",
            "content": (
                f"Interpret these technical indicators:\n{json.dumps(indicators_data, indent=2)}\n\n"
                "Explain what each indicator shows and overall technical picture."
            ),
        }

        try:
            response = await self._make_request(
                messages=[system_message, user_message],
                temperature=0.4,
                max_tokens=500,
            )

            interpretation = response["choices"][0]["message"]["content"]
            logger.info("Technical indicators interpreted", length=len(interpretation))
            return cast(str, interpretation)

        except Exception as e:
            logger.error("Failed to interpret technical indicators", error=str(e))
            return self._fallback_technical_interpretation(rsi, macd, bollinger)

    async def assess_risk_profile(
        self,
        volatility: float,
        beta: Optional[float] = None,
        var: Optional[float] = None,
    ) -> str:
        """
        Assess risk profile of an asset

        Args:
            volatility: Historical volatility
            beta: Beta coefficient vs market
            var: Value at Risk (95%)

        Returns:
            Risk profile assessment

        Example:
            >>> risk = await client.assess_risk_profile(
            ...     volatility=0.25, beta=1.15, var=0.05
            ... )
        """
        logger.info("Assessing risk profile", volatility=volatility)

        risk_data = {"volatility": volatility}
        if beta is not None:
            risk_data["beta"] = beta
        if var is not None:
            risk_data["value_at_risk_95"] = var

        system_message = {
            "role": "system",
            "content": (
                "You are a risk analyst assessing asset risk profiles. "
                "Provide factual risk assessment based on metrics. "
                "Use clear risk categories (low, moderate, high). "
                "End with: 'Past volatility does not guarantee future risk levels.'"
            ),
        }

        user_message = {
            "role": "user",
            "content": (
                f"Assess the risk profile based on:\n{json.dumps(risk_data, indent=2)}\n\n"
                "Explain risk level and what investors should understand."
            ),
        }

        try:
            response = await self._make_request(
                messages=[system_message, user_message],
                temperature=0.3,
                max_tokens=400,
            )

            assessment = response["choices"][0]["message"]["content"]
            logger.info("Risk profile assessed", length=len(assessment))
            return cast(str, assessment)

        except Exception as e:
            logger.error("Failed to assess risk profile", error=str(e))
            return self._fallback_risk_assessment(volatility, beta, var)

    async def compare_assets(
        self,
        asset1_data: Dict[str, Any],
        asset2_data: Dict[str, Any],
    ) -> str:
        """
        Compare two assets

        Args:
            asset1_data: First asset's data
            asset2_data: Second asset's data

        Returns:
            Comparative analysis

        Example:
            >>> comparison = await client.compare_assets(
            ...     {"symbol": "AAPL", "pe_ratio": 28.5, "growth": 15.8},
            ...     {"symbol": "MSFT", "pe_ratio": 32.1, "growth": 12.3}
            ... )
        """
        logger.info(
            "Comparing assets",
            asset1=asset1_data.get("symbol"),
            asset2=asset2_data.get("symbol"),
        )

        system_message = {
            "role": "system",
            "content": (
                "You are a financial analyst comparing assets. "
                "Provide objective comparison based on metrics. "
                "Avoid recommendations (don't say 'better' or 'should buy'). "
                "Use comparative language: 'higher', 'lower', 'more volatile'. "
                "End with: 'This comparison is for informational purposes only.'"
            ),
        }

        user_message = {
            "role": "user",
            "content": (
                f"Compare these two assets:\n\n"
                f"Asset 1: {json.dumps(asset1_data, indent=2)}\n\n"
                f"Asset 2: {json.dumps(asset2_data, indent=2)}\n\n"
                "Provide factual comparison of metrics."
            ),
        }

        try:
            response = await self._make_request(
                messages=[system_message, user_message],
                temperature=0.4,
                max_tokens=600,
            )

            comparison = response["choices"][0]["message"]["content"]
            logger.info("Assets compared", length=len(comparison))
            return cast(str, comparison)

        except Exception as e:
            logger.error("Failed to compare assets", error=str(e))
            return self._fallback_comparison(asset1_data, asset2_data)

    # ==========================================================================
    # Fallback Template-Based Narratives
    # ==========================================================================

    def _fallback_market_summary(self, data: Dict[str, Any]) -> str:
        """Generate fallback market summary when API fails"""
        symbol = data.get("symbol", "Asset")
        price = data.get("price", 0)
        change = data.get("change", 0)
        change_pct = data.get("change_percent", 0)
        volume = data.get("volume", 0)

        direction = "up" if change > 0 else "down"
        return (
            f"{symbol} is currently trading at ${price:.2f}, {direction} "
            f"${abs(change):.2f} ({change_pct:+.2f}%) in the last 24 hours. "
            f"Trading volume is {volume:,} shares. "
            f"This is not financial advice. FIML provides data analysis only."
        )

    def _fallback_price_movement(
        self, symbol: str, change_pct: float, volume: int
    ) -> str:
        """Generate fallback price movement explanation"""
        direction = "gained" if change_pct > 0 else "declined"
        magnitude = "significantly" if abs(change_pct) > 3 else "moderately"

        return (
            f"{symbol} has {direction} {magnitude} by {abs(change_pct):.2f}% "
            f"on volume of {volume:,} shares. This movement reflects current "
            f"market conditions. This is not financial advice."
        )

    def _fallback_technical_interpretation(
        self,
        rsi: Optional[float],
        macd: Optional[Dict[str, float]],
        bollinger: Optional[Dict[str, float]],
    ) -> str:
        """Generate fallback technical interpretation"""
        parts = []

        if rsi is not None:
            if rsi > 70:
                parts.append(f"RSI at {rsi:.1f} indicates overbought conditions")
            elif rsi < 30:
                parts.append(f"RSI at {rsi:.1f} indicates oversold conditions")
            else:
                parts.append(f"RSI at {rsi:.1f} indicates neutral momentum")

        if macd and "histogram" in macd:
            if macd["histogram"] > 0:
                parts.append("MACD shows bullish momentum")
            else:
                parts.append("MACD shows bearish momentum")

        if not parts:
            parts.append("Technical indicators are available for analysis")

        return (
            ". ".join(parts)
            + ". This is technical analysis, not investment advice."
        )

    def _fallback_risk_assessment(
        self,
        volatility: float,
        beta: Optional[float],
        var: Optional[float],
    ) -> str:
        """Generate fallback risk assessment"""
        if volatility < 0.15:
            risk_level = "low to moderate"
        elif volatility < 0.30:
            risk_level = "moderate"
        else:
            risk_level = "high"

        beta_text = ""
        if beta is not None:
            if beta > 1.2:
                beta_text = f" The beta of {beta:.2f} indicates higher volatility than the market."
            elif beta < 0.8:
                beta_text = f" The beta of {beta:.2f} indicates lower volatility than the market."

        return (
            f"Based on historical volatility of {volatility:.2%}, this asset shows "
            f"{risk_level} risk.{beta_text} Past volatility does not guarantee future risk levels."
        )

    def _fallback_comparison(
        self,
        asset1_data: Dict[str, Any],
        asset2_data: Dict[str, Any],
    ) -> str:
        """Generate fallback asset comparison"""
        symbol1 = asset1_data.get("symbol", "Asset 1")
        symbol2 = asset2_data.get("symbol", "Asset 2")

        parts = [f"Comparing {symbol1} and {symbol2}:"]

        # Compare P/E ratios if available
        pe1 = asset1_data.get("pe_ratio")
        pe2 = asset2_data.get("pe_ratio")
        if pe1 and pe2:
            higher = symbol1 if pe1 > pe2 else symbol2
            parts.append(f"{higher} has a higher P/E ratio")

        # Compare growth rates
        growth1 = asset1_data.get("growth")
        growth2 = asset2_data.get("growth")
        if growth1 and growth2:
            faster = symbol1 if growth1 > growth2 else symbol2
            parts.append(f"{faster} shows faster growth")

        return (
            ". ".join(parts) + ". This comparison is for informational purposes only."
        )
