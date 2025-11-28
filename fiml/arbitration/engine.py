"""
Data Arbitration Engine - Crown Jewel of FIML

Intelligently routes data requests to optimal providers with:
- Provider scoring and health monitoring
- Auto-fallback strategies
- Conflict resolution
- Weighted data merging
"""

from datetime import datetime, timezone
from typing import List, Optional

import numpy as np

from fiml.core.exceptions import NoProviderAvailableError
from fiml.core.logging import get_logger
from fiml.core.models import ArbitrationPlan, Asset, DataType, ProviderScore
from fiml.providers.base import BaseProvider, ProviderResponse
from fiml.providers.registry import provider_registry

logger = get_logger(__name__)


class DataArbitrationEngine:
    """
    Intelligently routes data requests to optimal providers

    Core responsibilities:
    1. Score providers based on freshness, latency, uptime, completeness, reliability
    2. Create execution plans with primary + fallback providers
    3. Execute with automatic fallback
    4. Merge data from multiple sources
    5. Resolve conflicts when providers disagree
    """

    def __init__(self, providers: Optional[List[BaseProvider]] = None) -> None:
        self.provider_registry = provider_registry
        self.custom_providers = providers

    async def arbitrate_request(
        self,
        asset: Asset,
        data_type: DataType,
        user_region: str = "US",
        max_staleness_seconds: int = 300,
    ) -> ArbitrationPlan:
        """
        Create an execution plan for a data request

        Args:
            asset: Asset to query
            data_type: Type of data needed
            user_region: User's geographic region for latency optimization
            max_staleness_seconds: Maximum acceptable data age

        Returns:
            ArbitrationPlan specifying primary provider, fallbacks, and merge strategy
        """
        logger.info(
            "Arbitrating request",
            asset=asset.symbol,
            data_type=data_type,
            region=user_region,
        )

        # Step 1: Get all compatible providers
        compatible_providers = await self.provider_registry.get_providers_for_asset(
            asset, data_type
        )

        if not compatible_providers:
            raise NoProviderAvailableError(
                f"No providers available for {asset.symbol} ({data_type})"
            )

        # Step 2: Score each provider
        provider_scores = []
        for provider in compatible_providers:
            score = await self._score_provider(
                provider, asset, data_type, user_region, max_staleness_seconds
            )
            provider_scores.append((provider, score))

        # Step 3: Sort by total score (descending)
        provider_scores.sort(key=lambda x: x[1].total, reverse=True)

        # Step 4: Filter out unhealthy providers (score < 50)
        healthy_providers = [(p, s) for p, s in provider_scores if s.total >= 50.0]

        if not healthy_providers:
            logger.warning("No healthy providers available, using best available")
            healthy_providers = provider_scores[:1]

        # Step 5: Create execution plan
        primary_provider = healthy_providers[0][0]
        fallback_providers = [p for p, _ in healthy_providers[1:3]]  # Top 2 fallbacks

        # Determine merge strategy
        merge_strategy = self._get_merge_strategy(data_type) if len(healthy_providers) > 1 else None

        # Estimate latency based on primary provider
        estimated_latency_ms = int(await primary_provider.get_latency_p95(user_region))

        plan = ArbitrationPlan(
            primary_provider=primary_provider.name,
            fallback_providers=[p.name for p in fallback_providers],
            merge_strategy=merge_strategy,
            estimated_latency_ms=estimated_latency_ms,
            timeout_ms=primary_provider.config.timeout_seconds * 1000,
        )

        logger.info(
            "Arbitration plan created",
            primary=plan.primary_provider,
            fallbacks=plan.fallback_providers,
            estimated_latency=estimated_latency_ms,
        )

        return plan

    async def execute_with_fallback(
        self, plan: ArbitrationPlan, asset: Asset, data_type: DataType
    ) -> ProviderResponse:
        """
        Execute data request with automatic fallback

        Args:
            plan: Arbitration plan
            asset: Asset to query
            data_type: Data type to fetch

        Returns:
            ProviderResponse from successful provider
        """
        # Build provider list: primary + fallbacks
        provider_names = [plan.primary_provider] + plan.fallback_providers
        providers = [self.provider_registry.providers.get(name) for name in provider_names]
        providers = [p for p in providers if p is not None]

        for i, provider in enumerate(providers):
            if provider is None:
                continue

            try:
                logger.info(
                    f"Attempting provider {i + 1}/{len(providers)}",
                    provider=provider.name,
                    asset=asset.symbol,
                )

                # Fetch data based on type
                response = await self._fetch_from_provider(provider, asset, data_type)

                # Validate response
                if response.is_valid and response.is_fresh:
                    provider_name = provider.name if provider else "unknown"
                    logger.info(
                        "Provider succeeded",
                        provider=provider_name,
                        asset=asset.symbol,
                        confidence=response.confidence,
                    )
                    return response
                else:
                    provider_name = provider.name if provider else "unknown"
                    logger.warning(
                        "Provider returned invalid/stale data",
                        provider=provider_name,
                        valid=response.is_valid,
                        fresh=response.is_fresh,
                    )

            except Exception as e:
                error_msg = str(e).lower()

                # Check for rate limits
                if "rate limit" in error_msg:
                    # Default cooldown: 60 seconds
                    cooldown_seconds = 60

                    # Try to parse wait time from error message
                    # Example: "Wait 18.5s"
                    import re
                    match = re.search(r"wait (\d+(\.\d+)?)s", error_msg)
                    if match:
                        cooldown_seconds = int(float(match.group(1))) + 1

                    provider.set_cooldown(cooldown_seconds)
                    logger.warning(
                        "Provider rate limited, setting cooldown",
                        provider=provider.name,
                        cooldown_seconds=cooldown_seconds
                    )

                provider_name = provider.name if provider else "unknown"
                logger.warning(
                    "Provider failed, falling back",
                    provider=provider_name,
                    error=str(e),
                    fallback_available=i < len(providers) - 1,
                )
                continue

        # All providers failed
        raise NoProviderAvailableError(f"All providers failed for {asset.symbol} ({data_type})")

    async def merge_multi_provider(
        self, responses: List[ProviderResponse], data_type: DataType
    ) -> ProviderResponse:
        """
        Merge data from multiple providers

        Args:
            responses: List of provider responses
            data_type: Type of data being merged

        Returns:
            Merged provider response
        """
        if not responses:
            raise ValueError("No responses to merge")

        if len(responses) == 1:
            return responses[0]

        logger.info(f"Merging {len(responses)} provider responses", data_type=data_type)

        # Use appropriate merge strategy based on data type
        if data_type == DataType.OHLCV:
            return await self._merge_ohlcv(responses)
        elif data_type == DataType.PRICE:
            return await self._merge_price(responses)
        elif data_type == DataType.FUNDAMENTALS:
            return await self._merge_fundamentals(responses)
        else:
            # Default: take most recent
            return max(responses, key=lambda r: r.timestamp)

    async def _score_provider(
        self,
        provider: BaseProvider,
        asset: Asset,
        data_type: DataType,
        region: str,
        max_staleness_seconds: int,
    ) -> ProviderScore:
        """
        Calculate comprehensive provider score

        Scoring factors:
        - Freshness (30%): How recent is the data
        - Latency (25%): Response time
        - Uptime (20%): Availability over last 24h
        - Completeness (15%): Data field coverage
        - Reliability (10%): Success rate over last N requests

        Special rules:
        - NewsAPI gets bonus score for NEWS and SENTIMENT data types
        """
        # Check if provider is in cooldown
        if provider.is_in_cooldown():
            return ProviderScore(
                total=0.0,
                freshness=0.0,
                latency=0.0,
                uptime=0.0,
                completeness=0.0,
                reliability=0.0,
            )

        # Freshness score
        last_update = await provider.get_last_update(asset, data_type)
        age_seconds = (datetime.now(timezone.utc) - last_update).total_seconds()
        freshness_score = max(0, 100 * (1 - age_seconds / max_staleness_seconds))

        # Latency score
        latency_p95 = await provider.get_latency_p95(region)
        max_acceptable_latency = 5000  # 5 seconds
        latency_score = max(0, 100 * (1 - latency_p95 / max_acceptable_latency))

        # Uptime score
        uptime_score = await provider.get_uptime_24h() * 100

        # Completeness score
        completeness_score = await provider.get_completeness(data_type) * 100

        # Reliability score
        reliability_score = await provider.get_success_rate() * 100

        # Weighted total
        total_score = (
            freshness_score * 0.30
            + latency_score * 0.25
            + uptime_score * 0.20
            + completeness_score * 0.15
            + reliability_score * 0.10
        )

        # Apply provider-specific bonuses
        if provider.name == "newsapi" and data_type in [DataType.NEWS, DataType.SENTIMENT]:
            # NewsAPI gets 20% bonus for news/sentiment data
            total_score *= 1.20
            logger.debug(f"Applied NewsAPI bonus for {data_type}, new score: {total_score:.2f}")

        # Cap at 100
        total_score = min(100.0, total_score)

        return ProviderScore(
            total=total_score,
            freshness=freshness_score,
            latency=latency_score,
            uptime=uptime_score,
            completeness=completeness_score,
            reliability=reliability_score,
        )

    async def _fetch_from_provider(
        self, provider: BaseProvider, asset: Asset, data_type: DataType
    ) -> ProviderResponse:
        """Fetch data from specific provider based on data type"""
        if data_type == DataType.PRICE:
            return await provider.fetch_price(asset)
        elif data_type == DataType.OHLCV:
            return await provider.fetch_ohlcv(asset)
        elif data_type == DataType.FUNDAMENTALS:
            return await provider.fetch_fundamentals(asset)
        elif data_type == DataType.NEWS:
            return await provider.fetch_news(asset)
        elif data_type == DataType.TECHNICAL:
            return await provider.fetch_technical(asset)
        else:
            raise ValueError(f"Unsupported data type: {data_type}")

    def _get_merge_strategy(self, data_type: DataType) -> str:
        """Determine merge strategy based on data type"""
        strategy_map = {
            DataType.PRICE: "weighted_average",
            DataType.OHLCV: "aggregate_candles",
            DataType.FUNDAMENTALS: "take_most_recent",
            DataType.NEWS: "deduplicate_and_merge",
            DataType.SENTIMENT: "weighted_average",
        }
        return strategy_map.get(data_type, "take_most_recent")

    async def _merge_price(self, responses: List[ProviderResponse]) -> ProviderResponse:
        """
        Merge price data using weighted average

        Weights are based on provider confidence scores
        """
        prices = [r.data.get("price", 0.0) for r in responses]
        weights = [r.confidence for r in responses]

        # Calculate weighted average
        weighted_price = np.average(prices, weights=weights)

        # Calculate confidence based on agreement
        std_dev = np.std(prices)
        agreement_confidence = 1.0 / (1.0 + std_dev / weighted_price)

        merged_data = {
            "price": weighted_price,
            "sources": [r.provider for r in responses],
            "source_count": len(responses),
            "price_range": {"min": min(prices), "max": max(prices)},
        }

        return ProviderResponse(
            provider="arbitration_engine",
            asset=responses[0].asset,
            data_type=DataType.PRICE,
            data=merged_data,
            timestamp=datetime.now(timezone.utc),
            is_valid=True,
            is_fresh=True,
            confidence=agreement_confidence,
            metadata={"merge_strategy": "weighted_average"},
        )

    async def _merge_ohlcv(self, responses: List[ProviderResponse]) -> ProviderResponse:
        """
        Merge OHLCV data

        - Open: Take from earliest timestamp
        - High: Max of all highs
        - Low: Min of all lows
        - Close: Take from latest timestamp
        - Volume: Sum (deduplicate exchanges)
        """
        all_candles = []
        for response in responses:
            candles = response.data.get("candles", [])
            all_candles.extend(candles)

        if not all_candles:
            return responses[0]

        merged_data = {
            "candles": all_candles,  # TODO: Implement proper OHLCV merge logic
            "sources": [r.provider for r in responses],
            "source_count": len(responses),
        }

        return ProviderResponse(
            provider="arbitration_engine",
            asset=responses[0].asset,
            data_type=DataType.OHLCV,
            data=merged_data,
            timestamp=datetime.now(timezone.utc),
            is_valid=True,
            is_fresh=True,
            confidence=0.95,
            metadata={"merge_strategy": "aggregate_candles"},
        )

    async def _merge_fundamentals(self, responses: List[ProviderResponse]) -> ProviderResponse:
        """
        Merge fundamental data

        Strategy: Take most recent data, fill in missing fields from other sources
        """
        # Sort by timestamp (most recent first)
        sorted_responses = sorted(responses, key=lambda r: r.timestamp, reverse=True)

        merged_data = {}
        for response in sorted_responses:
            for key, value in response.data.items():
                if key not in merged_data and value is not None:
                    merged_data[key] = value

        return ProviderResponse(
            provider="arbitration_engine",
            asset=responses[0].asset,
            data_type=DataType.FUNDAMENTALS,
            data=merged_data,
            timestamp=datetime.now(timezone.utc),
            is_valid=True,
            is_fresh=True,
            confidence=0.90,
            metadata={
                "merge_strategy": "take_most_recent",
                "sources": [r.provider for r in responses],
            },
        )


# Global arbitration engine instance
arbitration_engine = DataArbitrationEngine()
