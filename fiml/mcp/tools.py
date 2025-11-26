"""
MCP Tool Implementations
"""

import uuid
from datetime import datetime, timedelta, timezone
from datetime import time as time_obj
from typing import Any, Dict, Optional, cast

from fiml.arbitration.engine import arbitration_engine
from fiml.cache.manager import cache_manager
from fiml.core.logging import get_logger
from fiml.core.models import (
    AnalysisDepth,
    Asset,
    AssetType,
    CachedData,
    DataLineage,
    DataType,
    Market,
    SearchByCoinResponse,
    SearchBySymbolResponse,
    StructuralData,
    TaskInfo,
    TaskStatus,
)
from fiml.dsl.executor import fk_dsl_executor
from fiml.dsl.parser import fk_dsl_parser
from fiml.dsl.planner import execution_planner
from fiml.monitoring.task_registry import task_registry
from fiml.narrative.cache import cache_narrative, get_cached_narrative
from fiml.narrative.generator import NarrativeGenerator
from fiml.narrative.models import (
    ExpertiseLevel,
    Language,
    Narrative,
    NarrativeContext,
    NarrativePreferences,
)

logger = get_logger(__name__)

# Initialize narrative generator
_narrative_generator: Optional[NarrativeGenerator] = None


def get_narrative_generator() -> NarrativeGenerator:
    """Get or create narrative generator instance"""
    global _narrative_generator
    if _narrative_generator is None:
        _narrative_generator = NarrativeGenerator()
    return _narrative_generator


async def track_query_in_session(
    session_id: str,
    query_type: str,
    parameters: Dict[str, Any],
    result_summary: Optional[str] = None,
    execution_time_ms: Optional[float] = None,
    cache_hit: bool = False,
) -> None:
    """
    Track a query in the session context

    Args:
        session_id: Session UUID
        query_type: Type of query (e.g., "price", "fundamentals")
        parameters: Query parameters
        result_summary: Optional summary of result
        execution_time_ms: Execution time in milliseconds
        cache_hit: Whether result was from cache
    """
    try:
        from uuid import UUID

        from fiml.sessions.models import QueryRecord
        from fiml.sessions.store import get_session_store

        session_store = await get_session_store()
        session = await session_store.get_session(UUID(session_id))

        if session:
            # Add query to history
            query = QueryRecord(
                query_type=query_type,
                parameters=parameters,
                result_summary=result_summary,
                execution_time_ms=execution_time_ms,
                cache_hit=cache_hit,
            )

            session.add_query(query)
            await session_store.update_session(UUID(session_id), session)

            logger.debug(f"Tracked query in session {session_id}", query_type=query_type)

    except Exception as e:
        # Don't fail the main operation if session tracking fails
        logger.warning(f"Failed to track query in session: {e}")


def calculate_narrative_ttl(
    asset: Asset,
    volatility: Optional[float] = None,
) -> int:
    """
    Calculate dynamic TTL for narrative caching based on market conditions

    Args:
        asset: Asset being analyzed
        volatility: Price volatility (change_percent absolute value)

    Returns:
        TTL in seconds
    """
    # Get current time
    now = datetime.now(timezone.utc)
    current_time = now.time()

    # Market hours (NYSE: 9:30 AM - 4:00 PM ET, convert to UTC: 14:30-21:00)
    market_open = time_obj(14, 30)
    market_close = time_obj(21, 0)
    is_market_hours = market_open <= current_time <= market_close

    # Crypto is 24/7
    if asset.asset_type == AssetType.CRYPTO:
        base_ttl = 600  # 10 minutes baseline

        # Adjust for volatility
        if volatility:
            if volatility > 10:  # High volatility (>10%)
                return 180  # 3 minutes
            elif volatility > 5:  # Medium volatility (5-10%)
                return 300  # 5 minutes

        return base_ttl

    # Equity/traditional assets
    if not is_market_hours:
        # Pre-market/After-hours: less volatility
        return 1800  # 30 minutes

    # During market hours
    if volatility:
        if volatility > 3:  # Significant price movement (>3%)
            return 300  # 5 minutes
        elif volatility > 1:  # Moderate movement (1-3%)
            return 600  # 10 minutes

    return 900  # 15 minutes default during market hours


def format_narrative_text(narrative: Narrative) -> str:
    """
    Format narrative as plain text

    Args:
        narrative: Generated narrative

    Returns:
        Formatted text string
    """
    parts = ["EXECUTIVE SUMMARY", "=" * 50, narrative.summary, ""]

    for section in narrative.sections:
        parts.extend([
            "",
            section.title.upper(),
            "=" * 50,
            section.content,
        ])

    if narrative.key_insights:
        parts.extend([
            "",
            "KEY INSIGHTS",
            "=" * 50,
        ])
        for i, insight in enumerate(narrative.key_insights, 1):
            parts.append(f"{i}. {insight}")

    if narrative.risk_factors:
        parts.extend([
            "",
            "RISK FACTORS",
            "=" * 50,
        ])
        for i, risk in enumerate(narrative.risk_factors, 1):
            parts.append(f"{i}. {risk}")

    parts.extend([
        "",
        "DISCLAIMER",
        "=" * 50,
        narrative.disclaimer,
    ])

    return "\n".join(parts)


def format_narrative_markdown(narrative: Narrative) -> str:
    """
    Format narrative as markdown

    Args:
        narrative: Generated narrative

    Returns:
        Formatted markdown string
    """
    parts = ["# Executive Summary", "", narrative.summary, ""]

    for section in narrative.sections:
        parts.extend([
            f"## {section.title}",
            "",
            section.content,
            "",
        ])

    if narrative.key_insights:
        parts.extend(["## Key Insights", ""])
        for insight in narrative.key_insights:
            parts.append(f"- {insight}")
        parts.append("")

    if narrative.risk_factors:
        parts.extend(["## Risk Factors", ""])
        for risk in narrative.risk_factors:
            parts.append(f"- {risk}")
        parts.append("")

    parts.extend([
        "---",
        "",
        "*" + narrative.disclaimer + "*",
    ])

    return "\n".join(parts)


def truncate_narrative(text: str, max_length: int = 1000) -> str:
    """
    Truncate narrative for display limits

    Args:
        text: Text to truncate
        max_length: Maximum length

    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text

    return text[:max_length - 3] + "..."





async def search_by_symbol(
    symbol: str,
    market: Market,
    depth: AnalysisDepth,
    language: str,
    expertise_level: str = "intermediate",
    include_narrative: bool = True,
    session_id: Optional[str] = None,
) -> SearchBySymbolResponse:
    """
    Search for a stock by symbol with instant cached data and async deep analysis

    Args:
        symbol: Stock ticker symbol
        market: Market/exchange
        depth: Analysis depth level
        language: Response language (en, es, fr, ja, zh, de, it, pt, fa)
        expertise_level: User expertise level (beginner, intermediate, advanced, quant)
        include_narrative: Whether to generate narrative (default True, except for quick depth)
        session_id: Optional session ID to track context across queries

    Returns:
        SearchBySymbolResponse with cached data, task info, and optional narrative
    """
    logger.info(
        "search_by_symbol called",
        symbol=symbol,
        market=market,
        depth=depth,
        language=language,
        expertise_level=expertise_level,
        include_narrative=include_narrative,
        session_id=session_id,
    )

    from fiml.compliance.disclaimers import AssetClass, disclaimer_generator
    from fiml.compliance.router import Region, compliance_router

    # Create asset object
    asset = Asset(symbol=symbol.upper(), asset_type=AssetType.EQUITY)

    # Compliance check
    compliance_check = await compliance_router.check_compliance(
        request_type="price_query",
        asset_type="equity",
        region=Region.US,  # Default to US, should be from user context
        user_query=None,
    )

    if not compliance_check.passed:
        # Return compliance error
        return SearchBySymbolResponse(
            symbol=symbol.upper(),
            name=f"{symbol.upper()}",
            exchange="",
            market=market.value,
            currency="USD",
            cached=CachedData(
                price=0.0,
                change=0.0,
                change_percent=0.0,
                as_of=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
                source="compliance_blocked",
                ttl=0,
                confidence=0.0,
            ),
            task=TaskInfo(
                id="",
                type="equity_analysis",
                status=TaskStatus.FAILED,
                resource_url="",
                estimated_completion=datetime.now(timezone.utc),
                progress=0.0,
            ),
            disclaimer="\n".join(compliance_check.restrictions),
            data_lineage=DataLineage(
                providers=[],
                arbitration_score=0.0,
                conflict_resolved=False,
                source_count=0,
            ),
        )

    try:
        # Define fetch function for read-through cache
        async def fetch_price_data() -> Dict[str, Any]:
            # Fetch price data via arbitration engine
            plan = await arbitration_engine.arbitrate_request(
                asset=asset,
                data_type=DataType.PRICE,
                user_region="US",
            )

            # Execute the plan
            response = await arbitration_engine.execute_with_fallback(plan, asset, DataType.PRICE)

            # Return data with provider info for caching
            data = response.data if response else {}
            if response:
                data["_source_provider"] = response.provider
                data["_confidence"] = response.confidence
            return data

        # Use cache manager with read-through
        # Cache key will be built by manager: "price:{symbol}:any"
        cache_key = cache_manager.l1.build_key("price", asset.symbol, "any")

        data = await cache_manager.get_with_read_through(
            key=cache_key,
            data_type=DataType.PRICE,
            fetch_fn=fetch_price_data,
            asset=asset
        )

        if not data:
            data = {}

        # Extract provider info (might be from cache or fresh fetch)
        provider_name = data.pop("_source_provider", "unknown")
        confidence = data.pop("_confidence", 0.0)

        # Fetch additional data based on depth
        fundamental_data = {}
        technical_data = {}

        if depth in [AnalysisDepth.STANDARD, AnalysisDepth.DEEP]:
            try:
                # Fetch fundamentals
                fund_plan = await arbitration_engine.arbitrate_request(
                    asset=asset,
                    data_type=DataType.FUNDAMENTALS,
                    user_region="US",
                )
                fund_response = await arbitration_engine.execute_with_fallback(
                    fund_plan, asset, DataType.FUNDAMENTALS
                )
                if fund_response:
                    fundamental_data = fund_response.data
            except Exception as e:
                logger.warning(f"Failed to fetch fundamentals: {e}", symbol=symbol)

            try:
                # Fetch technicals
                tech_plan = await arbitration_engine.arbitrate_request(
                    asset=asset,
                    data_type=DataType.TECHNICAL,
                    user_region="US",
                )
                tech_response = await arbitration_engine.execute_with_fallback(
                    tech_plan, asset, DataType.TECHNICAL
                )
                if tech_response:
                    technical_data = tech_response.data
            except Exception as e:
                logger.warning(f"Failed to fetch technicals: {e}", symbol=symbol)

        task_id = f"analysis-{symbol.lower()}-{uuid.uuid4().hex[:8]}"

        cached_data = CachedData(
            price=data.get("price", 0.0),
            change=data.get("change", 0.0),
            change_percent=data.get("change_percent", 0.0),
            as_of=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc),
            source=provider_name,
            ttl=300,  # 5 minutes
            confidence=confidence,
        )

        # Create structural data object
        structural_data = None
        if fundamental_data:
            structural_data = StructuralData(
                market_cap=fundamental_data.get("market_cap"),
                pe_ratio=fundamental_data.get("pe_ratio"),
                beta=fundamental_data.get("beta"),
                avg_volume=fundamental_data.get("avg_volume"),
                week_52_high=fundamental_data.get("week_52_high"),
                week_52_low=fundamental_data.get("week_52_low"),
                sector=fundamental_data.get("sector"),
                industry=fundamental_data.get("industry"),
            )

        task_info = TaskInfo(
            id=task_id,
            type="equity_analysis",
            status=TaskStatus.PENDING,
            resource_url=f"mcp://task/{task_id}",
            estimated_completion=datetime.now(timezone.utc) + timedelta(seconds=5),
            progress=0.0,
            created_at=datetime.now(timezone.utc),
        )

        # Register task for status tracking (5 minute TTL)
        task_registry.register(task_info, ttl=300)

        data_lineage = DataLineage(
            providers=[provider_name],
            arbitration_score=0.0,  # TODO: Get from cache metadata if possible
            conflict_resolved=False,
            source_count=1,
        )

        # Generate disclaimer
        disclaimer = disclaimer_generator.generate(
            asset_class=AssetClass.EQUITY,
            region=Region.US,
            include_general=True,
        )

        # Generate narrative if requested and depth allows
        narrative_summary = None
        if include_narrative and depth != AnalysisDepth.QUICK:
            try:
                # Check cache first
                cached_narrative = await get_cached_narrative(
                    symbol.upper(), language, expertise_level
                )

                if cached_narrative:
                    from fiml.core.models import NarrativeSummary
                    narrative_summary = NarrativeSummary(**cached_narrative)
                    logger.debug("Using cached narrative", symbol=symbol)
                else:
                    # Generate new narrative
                    generator = get_narrative_generator()

                    # Map string to enum
                    try:
                        lang_enum = Language(language.lower())
                    except ValueError:
                        lang_enum = Language.ENGLISH

                    try:
                        expertise_enum = ExpertiseLevel(expertise_level.lower())
                    except ValueError:
                        expertise_enum = ExpertiseLevel.INTERMEDIATE

                    # Build narrative preferences based on depth
                    preferences = NarrativePreferences(
                        language=lang_enum,
                        expertise_level=expertise_enum,
                        include_technical=depth in [AnalysisDepth.STANDARD, AnalysisDepth.DEEP],
                        include_fundamental=depth in [AnalysisDepth.STANDARD, AnalysisDepth.DEEP],
                        include_sentiment=depth == AnalysisDepth.DEEP,
                        include_risk=depth == AnalysisDepth.DEEP,
                        max_length_chars=2000 if depth == AnalysisDepth.DEEP else 1000,
                    )

                    # Build narrative context
                    context = NarrativeContext(
                        asset_symbol=symbol.upper(),
                        asset_name=data.get("name", f"{symbol.upper()} Inc."),
                        asset_type="equity",
                        region="US",
                        price_data={
                            "price": cached_data.price,
                            "change": cached_data.change,
                            "change_percent": cached_data.change_percent,
                            "volume": data.get("volume", 0),
                            "market_cap": fundamental_data.get("market_cap", 0),
                            "pe_ratio": fundamental_data.get("pe_ratio", 0),
                        },
                        preferences=preferences,
                        data_sources=[provider_name],
                    )

                    # Add fundamental data
                    if fundamental_data:
                        context.fundamental_data = fundamental_data

                    # Add technical data for standard/deep
                    if depth in [AnalysisDepth.STANDARD, AnalysisDepth.DEEP]:
                        if technical_data:
                            context.technical_data = technical_data
                        else:
                            # Fallback to basic calculated technicals if fetch failed
                            context.technical_data = {
                                "trend": "bullish" if cached_data.change_percent > 0 else "bearish",
                                "strength": "strong" if abs(cached_data.change_percent) > 2 else "moderate",
                            }

                    # Add sentiment for deep
                    if depth == AnalysisDepth.DEEP:
                        context.sentiment_data = {
                            "overall": "positive" if cached_data.change_percent > 0 else "negative",
                            "confidence": 0.7,
                        }

                    # Generate narrative
                    narrative = await generator.generate_narrative(context)

                    # Convert to summary format with section metadata
                    from fiml.core.models import NarrativeSectionMeta, NarrativeSummary
                    narrative_summary = NarrativeSummary(
                        summary=narrative.summary,
                        key_insights=narrative.key_insights,
                        risk_factors=narrative.risk_factors,
                        language=language,
                        sections=[
                            NarrativeSectionMeta(
                                title=section.title,
                                type=section.section_type.value,
                                confidence=section.confidence,
                            )
                            for section in narrative.sections
                        ],
                    )

                    # Cache the narrative
                    ttl = calculate_narrative_ttl(
                        asset, abs(cached_data.change_percent)
                    )
                    await cache_narrative(
                        symbol.upper(),
                        language,
                        expertise_level,
                        narrative_summary.model_dump(),
                        ttl,
                    )

                    logger.info(
                        "Narrative generated",
                        symbol=symbol,
                        depth=depth,
                        language=language,
                        ttl=ttl,
                    )

            except Exception as e:
                logger.warning(
                    f"Narrative generation failed, continuing without: {e}",
                    symbol=symbol,
                )
                # DEBUG: Append error to disclaimer
                error_msg = str(e)
                if hasattr(e, 'response') and hasattr(e.response, 'text'):
                    error_msg += f" | Response: {e.response.text}"
                disclaimer += f" [DEBUG ERROR: {error_msg}]"

        # Track query in session if session_id provided
        if session_id:
            await track_query_in_session(
                session_id=session_id,
                query_type="equity_price",
                parameters={
                    "symbol": symbol.upper(),
                    "market": market.value,
                    "depth": depth.value,
                },
                result_summary=f"Price: {cached_data.price}, Change: {cached_data.change_percent}%",
                cache_hit=False,
            )

        response = SearchBySymbolResponse(
            symbol=symbol.upper(),
            name=data.get("name", f"{symbol.upper()} Inc."),
            exchange=data.get("exchange", "NASDAQ"),
            market=market.value,
            currency="USD",
            cached=cached_data,
            structural_data=structural_data,
            task=task_info,
            disclaimer=disclaimer,
            data_lineage=data_lineage,
            narrative=narrative_summary,
        )

        # Add session_id to response metadata if provided
        if session_id:
            # Store session_id in task metadata for reference
            task_info.resource_url += f"?session_id={session_id}"

        return response

    except Exception as e:
        logger.error(f"Error fetching data for {symbol}: {e}")

        # Return error response with disclaimer
        task_id = f"analysis-{symbol.lower()}-{uuid.uuid4().hex[:8]}"

        return SearchBySymbolResponse(
            symbol=symbol.upper(),
            name=f"{symbol.upper()}",
            exchange="",
            market=market.value,
            currency="USD",
            cached=CachedData(
                price=0.0,
                change=0.0,
                change_percent=0.0,
                as_of=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
                source="error",
                ttl=0,
                confidence=0.0,
            ),
            task=TaskInfo(
                id=task_id,
                type="equity_analysis",
                status=TaskStatus.FAILED,
                resource_url=f"mcp://task/{task_id}",
                estimated_completion=datetime.now(timezone.utc),
                progress=0.0,
            ),
            disclaimer=f"Error fetching data: {str(e)}",
            data_lineage=DataLineage(
                providers=[],
                arbitration_score=0.0,
                conflict_resolved=False,
                source_count=0,
            ),
        )


async def search_by_coin(
    symbol: str,
    exchange: str,
    pair: str,
    depth: AnalysisDepth,
    language: str,
    expertise_level: str = "intermediate",
    include_narrative: bool = True,
    session_id: Optional[str] = None,
) -> SearchByCoinResponse:
    """
    Search for cryptocurrency with instant cached data and async deep analysis

    Args:
        symbol: Crypto symbol
        exchange: Preferred exchange
        pair: Trading pair
        depth: Analysis depth level
        language: Response language (en, es, fr, ja, zh, de, it, pt, fa)
        expertise_level: User expertise level (beginner, intermediate, advanced, quant)
        include_narrative: Whether to generate narrative (default True, except for quick depth)
        session_id: Optional session ID to track context across queries

    Returns:
        SearchByCoinResponse with cached data, task info, and optional crypto narrative
    """
    logger.info(
        "search_by_coin called",
        symbol=symbol,
        exchange=exchange,
        pair=pair,
        depth=depth,
        language=language,
        expertise_level=expertise_level,
        include_narrative=include_narrative,
        session_id=session_id,
    )

    from fiml.compliance.disclaimers import AssetClass, disclaimer_generator
    from fiml.compliance.router import Region, compliance_router

    # Create asset object with pair format
    crypto_symbol = f"{symbol.upper()}/{pair.upper()}"
    asset = Asset(symbol=crypto_symbol, asset_type=AssetType.CRYPTO)

    # Compliance check
    compliance_check = await compliance_router.check_compliance(
        request_type="price_query",
        asset_type="crypto",
        region=Region.US,
        user_query=None,
    )

    if not compliance_check.passed:
        # Return compliance error
        return SearchByCoinResponse(
            symbol=symbol.upper(),
            name=f"{symbol.upper()}",
            pair=crypto_symbol,
            exchange=exchange,
            cached=CachedData(
                price=0.0,
                change=0.0,
                change_percent=0.0,
                as_of=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
                source="compliance_blocked",
                ttl=0,
                confidence=0.0,
            ),
            crypto_metrics={},
            task=TaskInfo(
                id="",
                type="crypto_analysis",
                status=TaskStatus.FAILED,
                resource_url="",
                estimated_completion=datetime.now(timezone.utc),
                progress=0.0,
            ),
            disclaimer="\n".join(compliance_check.restrictions),
            data_lineage=DataLineage(
                providers=[],
                arbitration_score=0.0,
                conflict_resolved=False,
                source_count=0,
            ),
        )

    try:
        # Define fetch function for read-through cache
        async def fetch_crypto_price() -> Dict[str, Any]:
            # Fetch price data via arbitration engine
            plan = await arbitration_engine.arbitrate_request(
                asset=asset,
                data_type=DataType.PRICE,
                user_region="US",
            )

            # Execute the plan
            response = await arbitration_engine.execute_with_fallback(plan, asset, DataType.PRICE)

            # Return data with provider info
            data = response.data if response else {}
            if response:
                data["_source_provider"] = response.provider
                data["_confidence"] = response.confidence
            return data

        # Use cache manager with read-through
        cache_key = cache_manager.l1.build_key("price", asset.symbol, "any")

        data = await cache_manager.get_with_read_through(
            key=cache_key,
            data_type=DataType.PRICE,
            fetch_fn=fetch_crypto_price,
            asset=asset
        )

        if not data:
            data = {}

        # Extract provider info
        provider_name = data.pop("_source_provider", "unknown")
        confidence = data.pop("_confidence", 0.0)

        task_id = f"crypto-{symbol.lower()}-{uuid.uuid4().hex[:8]}"

        cached_data = CachedData(
            price=data.get("price", 0.0),
            change=data.get("change", 0.0),
            change_percent=data.get("change_percent", 0.0),
            as_of=datetime.now(timezone.utc),
            last_updated=datetime.now(timezone.utc),
            source=provider_name,
            ttl=30,  # 30 seconds for crypto (more volatile)
            confidence=confidence,
        )

        task_info = TaskInfo(
            id=task_id,
            type="crypto_analysis",
            status=TaskStatus.PENDING,
            resource_url=f"mcp://task/{task_id}",
            estimated_completion=datetime.now(timezone.utc) + timedelta(seconds=3),
            progress=0.0,
            created_at=datetime.now(timezone.utc),
        )

        # Register task for status tracking (5 minute TTL)
        task_registry.register(task_info, ttl=300)

        data_lineage = DataLineage(
            providers=[provider_name],
            arbitration_score=0.0,  # TODO: Get from cache metadata
            conflict_resolved=False,
            source_count=1,
        )

        # Generate disclaimer for crypto
        disclaimer = disclaimer_generator.generate(
            asset_class=AssetClass.CRYPTO,
            region=Region.US,
            include_general=True,
        )

        # Extract crypto-specific metrics
        crypto_metrics = {
            "dominance": data.get("dominance", 0.0),
            "ath": data.get("ath", 0.0),
            "athDate": data.get("ath_date", ""),
            "volume24h": data.get("volume_24h", data.get("volume", 0.0)),
            "high_24h": data.get("high_24h", data.get("high", 0.0)),
            "low_24h": data.get("low_24h", data.get("low", 0.0)),
        }

        # Generate crypto narrative if requested and depth allows
        narrative_summary = None
        if include_narrative and depth != AnalysisDepth.QUICK:
            try:
                # Check cache first
                cached_narrative = await get_cached_narrative(
                    crypto_symbol, language, expertise_level
                )

                if cached_narrative:
                    from fiml.core.models import NarrativeSummary
                    narrative_summary = NarrativeSummary(**cached_narrative)
                    logger.debug("Using cached crypto narrative", symbol=crypto_symbol)
                else:
                    # Generate new crypto narrative
                    generator = get_narrative_generator()

                    # Map string to enum
                    try:
                        lang_enum = Language(language.lower())
                    except ValueError:
                        lang_enum = Language.ENGLISH

                    try:
                        expertise_enum = ExpertiseLevel(expertise_level.lower())
                    except ValueError:
                        expertise_enum = ExpertiseLevel.INTERMEDIATE

                    # Build narrative preferences for crypto
                    preferences = NarrativePreferences(
                        language=lang_enum,
                        expertise_level=expertise_enum,
                        include_technical=depth in [AnalysisDepth.STANDARD, AnalysisDepth.DEEP],
                        include_fundamental=depth in [AnalysisDepth.STANDARD, AnalysisDepth.DEEP],
                        include_sentiment=depth == AnalysisDepth.DEEP,
                        include_risk=True,  # Always include risk for crypto
                        max_length_chars=2000 if depth == AnalysisDepth.DEEP else 1000,
                    )

                    # Build crypto narrative context
                    context = NarrativeContext(
                        asset_symbol=crypto_symbol,
                        asset_name=data.get("name", symbol.upper()),
                        asset_type="crypto",
                        region="GLOBAL",
                        price_data={
                            "price": cached_data.price,
                            "change": cached_data.change,
                            "change_percent": cached_data.change_percent,
                            "volume": crypto_metrics.get("volume24h", 0),
                            "high_24h": crypto_metrics.get("high_24h", 0),
                            "low_24h": crypto_metrics.get("low_24h", 0),
                        },
                        preferences=preferences,
                        data_sources=[provider_name],
                    )

                    # Add crypto-specific fundamental data
                    if depth in [AnalysisDepth.STANDARD, AnalysisDepth.DEEP]:
                        context.fundamental_data = {
                            "dominance": crypto_metrics.get("dominance", 0),
                            "ath": crypto_metrics.get("ath", 0),
                            "ath_date": crypto_metrics.get("athDate", ""),
                            "blockchain_metrics": {
                                "exchanges": [exchange],
                                "trading_pairs": [pair],
                            },
                        }

                    # Add technical data
                    if depth in [AnalysisDepth.STANDARD, AnalysisDepth.DEEP]:
                        volatility = abs(cached_data.change_percent)
                        context.technical_data = {
                            "trend": "bullish" if cached_data.change_percent > 0 else "bearish",
                            "volatility": "high" if volatility > 5 else "moderate" if volatility > 2 else "low",
                            "24h_range": {
                                "high": crypto_metrics.get("high_24h", 0),
                                "low": crypto_metrics.get("low_24h", 0),
                            },
                        }

                    # Add sentiment for deep (crypto-specific)
                    if depth == AnalysisDepth.DEEP:
                        context.sentiment_data = {
                            "overall": "bullish" if cached_data.change_percent > 0 else "bearish",
                            "confidence": 0.6,  # Lower confidence for crypto
                            "market_fear_greed": "neutral",
                        }

                    # Add crypto risk warnings
                    context.risk_data = {
                        "volatility_risk": "high" if abs(cached_data.change_percent) > 5 else "moderate",
                        "liquidity_risk": "moderate",
                        "regulatory_risk": "high",
                        "market_type": "24/7 trading",
                        "funding_rates": data.get("funding_rate"),
                        "open_interest": data.get("open_interest"),
                    }

                    # Generate narrative
                    narrative = await generator.generate_narrative(context)

                    # Convert to summary format with crypto context and section metadata
                    from fiml.core.models import NarrativeSectionMeta, NarrativeSummary
                    narrative_summary = NarrativeSummary(
                        summary=narrative.summary,
                        key_insights=narrative.key_insights + [
                            f"Trading on {exchange} exchange with {pair} pair",
                            "Cryptocurrency markets operate 24/7 with high volatility",
                        ],
                        risk_factors=narrative.risk_factors + [
                            "Extreme price volatility and 24/7 market exposure",
                            "Regulatory uncertainty and potential restrictions",
                            "Exchange-specific risks including security and liquidity",
                        ],
                        language=language,
                        sections=[
                            NarrativeSectionMeta(
                                title=section.title,
                                type=section.section_type.value,
                                confidence=section.confidence,
                            )
                            for section in narrative.sections
                        ],
                    )

                    # Cache the crypto narrative with shorter TTL
                    ttl = calculate_narrative_ttl(
                        asset, abs(cached_data.change_percent)
                    )
                    await cache_narrative(
                        crypto_symbol,
                        language,
                        expertise_level,
                        narrative_summary.model_dump(),
                        ttl,
                    )

                    logger.info(
                        "Crypto narrative generated",
                        symbol=crypto_symbol,
                        depth=depth,
                        language=language,
                        ttl=ttl,
                    )

            except Exception as e:
                logger.warning(
                    f"Crypto narrative generation failed, continuing without: {e}",
                    symbol=crypto_symbol,
                )
                # Continue without narrative - graceful fallback

        # Track query in session if session_id provided
        if session_id:
            await track_query_in_session(
                session_id=session_id,
                query_type="crypto_price",
                parameters={
                    "symbol": symbol.upper(),
                    "exchange": exchange,
                    "pair": pair,
                    "depth": depth.value,
                },
                result_summary=f"Price: {cached_data.price}, Change: {cached_data.change_percent}%",
                cache_hit=False,
            )

        response = SearchByCoinResponse(
            symbol=symbol.upper(),
            name=data.get("name", symbol.upper()),
            pair=crypto_symbol,
            exchange=data.get("exchange", exchange),
            cached=cached_data,
            crypto_metrics=crypto_metrics,
            task=task_info,
            disclaimer=disclaimer,
            data_lineage=data_lineage,
            narrative=narrative_summary,
        )

        # Add session_id to response metadata if provided
        if session_id:
            task_info.resource_url += f"?session_id={session_id}"

        return response

    except Exception as e:
        logger.error(f"Error fetching crypto data for {symbol}: {e}")

        # Return error response with disclaimer
        task_id = f"crypto-{symbol.lower()}-{uuid.uuid4().hex[:8]}"

        error_task_info = TaskInfo(
            id=task_id,
            type="crypto_analysis",
            status=TaskStatus.FAILED,
            resource_url=f"mcp://task/{task_id}",
            estimated_completion=datetime.now(timezone.utc),
            progress=0.0,
            created_at=datetime.now(timezone.utc),
        )

        # Register failed task for tracking
        task_registry.register(error_task_info, ttl=300)

        return SearchByCoinResponse(
            symbol=symbol.upper(),
            name=symbol.upper(),
            pair=crypto_symbol,
            exchange=exchange,
            cached=CachedData(
                price=0.0,
                change=0.0,
                change_percent=0.0,
                as_of=datetime.now(timezone.utc),
                last_updated=datetime.now(timezone.utc),
                source="error",
                ttl=0,
                confidence=0.0,
            ),
            crypto_metrics={},
            task=error_task_info,
            disclaimer=f"Error fetching data: {str(e)}",
            data_lineage=DataLineage(
                providers=[],
                arbitration_score=0.0,
                conflict_resolved=False,
                source_count=0,
            ),
        )


async def get_task_status(task_id: str, stream: bool = False) -> dict:
    """
    Get status of an async analysis task

    Args:
        task_id: Task ID to query
        stream: Whether to stream updates

    Returns:
        Task status information
    """
    logger.info("get_task_status called", task_id=task_id, stream=stream)

    # First check the task registry (for analysis tasks)
    task_info = task_registry.get(task_id)

    # If not in registry, check FK-DSL executor
    if not task_info:
        task_info = fk_dsl_executor.get_task_status(task_id)

    if task_info:
        # Calculate progress safely
        completed = task_info.completed_steps or 0
        total = task_info.total_steps or 1
        progress = completed / total if total > 0 else 0.0

        return {
            "task_id": task_info.id,
            "status": task_info.status.value if task_info.status else "unknown",
            "type": task_info.type,
            "query": getattr(task_info, 'query', None),
            "progress": progress,
            "completed_steps": task_info.completed_steps,
            "total_steps": task_info.total_steps,
            "created_at": task_info.created_at.isoformat() if task_info.created_at else None,
            "started_at": task_info.started_at.isoformat() if task_info.started_at else None,
            "completed_at": task_info.completed_at.isoformat() if task_info.completed_at else None,
            "result": getattr(task_info, 'result', None),
            "error": getattr(task_info, 'error', None),
        }

    return {
        "task_id": task_id,
        "status": "not_found",
        "progress": None,
        "type": None,
    }


async def execute_fk_dsl(query: str, async_execution: bool = True) -> dict:
    """
    Execute a Financial Knowledge DSL query

    Args:
        query: FK-DSL query string
        async_execution: Whether to execute asynchronously

    Returns:
        Execution result or task ID
    """
    logger.info("execute_fk_dsl called", query=query, async_execution=async_execution)

    try:
        # Parse query
        parsed = fk_dsl_parser.parse(query)

        # Create execution plan
        plan = execution_planner.plan(parsed, query)

        if async_execution:
            # Start async execution
            task_id = await fk_dsl_executor.execute_async(plan)

            return {
                "task_id": task_id,
                "query": query,
                "status": "running",
                "total_steps": len(plan.tasks),
                "message": "DSL query execution started",
            }
        else:
            # Execute synchronously
            result = await fk_dsl_executor.execute_sync(plan)

            return {
                "query": query,
                "status": "completed",
                "result": result,
            }

    except Exception as e:
        logger.error(f"DSL execution failed: {e}", query=query)
        return {
            "query": query,
            "status": "failed",
            "error": str(e),
        }


async def get_narrative(
    symbol: str,
    asset_type: str = "equity",
    language: str = "en",
    expertise_level: str = "intermediate",
    analysis_data: Optional[Dict[str, Any]] = None,
    focus_areas: Optional[list] = None,
) -> Dict[str, Any]:
    """
    Generate standalone narrative for existing analysis data

    Args:
        symbol: Asset symbol (e.g., AAPL, BTC/USD)
        asset_type: Asset type (equity, crypto, forex, etc.)
        language: Language code (en, es, fr, ja, zh, de, it, pt, fa)
        expertise_level: User expertise (beginner, intermediate, advanced, quant)
        analysis_data: Existing analysis data to generate narrative from
        focus_areas: Specific areas to focus on (market, technical, fundamental, sentiment, risk)

    Returns:
        Generated narrative with full text and summary
    """
    logger.info(
        "get_narrative called",
        symbol=symbol,
        asset_type=asset_type,
        language=language,
        expertise_level=expertise_level,
        focus_areas=focus_areas,
    )

    try:
        # Check cache first
        cached_narrative = await get_cached_narrative(
            symbol.upper(), language, expertise_level
        )

        if cached_narrative:
            logger.debug("Returning cached narrative", symbol=symbol)
            return {
                "symbol": symbol.upper(),
                "asset_type": asset_type,
                "language": language,
                "expertise_level": expertise_level,
                "narrative": cached_narrative,
                "cached": True,
            }

        # Generate new narrative
        generator = get_narrative_generator()

        # Map string to enum
        try:
            lang_enum = Language(language.lower())
        except ValueError:
            lang_enum = Language.ENGLISH

        try:
            expertise_enum = ExpertiseLevel(expertise_level.lower())
        except ValueError:
            expertise_enum = ExpertiseLevel.INTERMEDIATE

        # Determine what to include based on focus areas
        if focus_areas is None:
            focus_areas = ["market", "technical", "fundamental", "sentiment", "risk"]

        # Build narrative preferences
        preferences = NarrativePreferences(
            language=lang_enum,
            expertise_level=expertise_enum,
            include_technical="technical" in focus_areas,
            include_fundamental="fundamental" in focus_areas,
            include_sentiment="sentiment" in focus_areas,
            include_risk="risk" in focus_areas or asset_type == "crypto",
            max_length_chars=2000,
        )

        # Build narrative context from analysis data
        context = NarrativeContext(
            asset_symbol=symbol.upper(),
            asset_name=analysis_data.get("name", symbol.upper()) if analysis_data else symbol.upper(),
            asset_type=asset_type,
            region=analysis_data.get("region", "US") if analysis_data else "US",
            preferences=preferences,
            data_sources=analysis_data.get("sources", []) if analysis_data else [],
        )

        # Add analysis data if provided
        if analysis_data:
            if "price_data" in analysis_data:
                context.price_data = analysis_data["price_data"]
            if "technical_data" in analysis_data:
                context.technical_data = analysis_data["technical_data"]
            if "fundamental_data" in analysis_data:
                context.fundamental_data = analysis_data["fundamental_data"]
            if "sentiment_data" in analysis_data:
                context.sentiment_data = analysis_data["sentiment_data"]
            if "risk_data" in analysis_data:
                context.risk_data = analysis_data["risk_data"]
        else:
            # Create minimal context
            context.price_data = {
                "price": 0.0,
                "change": 0.0,
                "change_percent": 0.0,
            }

        # Generate narrative
        narrative = await generator.generate_narrative(context)

        # Format narrative
        narrative_text = format_narrative_text(narrative)
        narrative_markdown = format_narrative_markdown(narrative)

        # Create response
        response_data = {
            "symbol": symbol.upper(),
            "asset_type": asset_type,
            "language": language,
            "expertise_level": expertise_level,
            "narrative": {
                "summary": narrative.summary,
                "key_insights": narrative.key_insights,
                "risk_factors": narrative.risk_factors,
                "sections": [
                    {
                        "title": section.title,
                        "content": section.content,
                        "type": section.section_type.value,
                        "confidence": section.confidence,
                    }
                    for section in narrative.sections
                ],
                "full_text": narrative_text,
                "markdown": narrative_markdown,
                "word_count": narrative.total_word_count,
                "generation_time_ms": narrative.generation_time_ms,
                "confidence": narrative.confidence,
            },
            "cached": False,
        }

        # Cache the narrative
        asset = Asset(symbol=symbol.upper(), asset_type=AssetType(asset_type))
        volatility = None
        if analysis_data and "price_data" in analysis_data:
            volatility = abs(analysis_data["price_data"].get("change_percent", 0))

        ttl = int(calculate_narrative_ttl(asset, volatility))
        await cache_narrative(
            symbol.upper(),
            language,
            expertise_level,
            cast(Dict[str, Any], response_data["narrative"]),
            ttl,
        )

        logger.info(
            "Narrative generated successfully",
            symbol=symbol,
            language=language,
            word_count=narrative.total_word_count,
            ttl=ttl,
        )

        return response_data

    except Exception as e:
        logger.error(f"Narrative generation failed: {e}", symbol=symbol)
        return {
            "symbol": symbol.upper(),
            "asset_type": asset_type,
            "language": language,
            "expertise_level": expertise_level,
            "error": str(e),
            "status": "failed",
        }


# =============================================================================
# Session Management Tools
# =============================================================================


async def create_analysis_session(
    assets: list[str],
    session_type: str,
    user_id: Optional[str] = None,
    ttl_hours: int = 24,
    tags: Optional[list[str]] = None,
) -> dict:
    """
    Create a new analysis session for tracking multi-query workflows

    Args:
        assets: List of asset symbols to analyze in this session
        session_type: Type of analysis (equity, crypto, portfolio, comparative, macro)
        user_id: Optional user identifier
        ttl_hours: Session time-to-live in hours (default 24, max per config)
        tags: Optional tags for categorizing the session

    Returns:
        Session information including session_id
    """
    from fiml.core.config import settings
    from fiml.sessions.models import SessionType
    from fiml.sessions.store import get_session_store

    logger.info(
        "create_analysis_session called",
        assets=assets,
        session_type=session_type,
        ttl_hours=ttl_hours,
    )

    try:
        # Validate TTL
        if ttl_hours > settings.session_max_ttl_hours:
            ttl_hours = settings.session_max_ttl_hours
            logger.warning(
                f"TTL capped at maximum: {settings.session_max_ttl_hours} hours"
            )

        # Get session store
        session_store = await get_session_store()

        # Create session
        session = await session_store.create_session(
            assets=assets,
            session_type=SessionType(session_type),
            user_id=user_id,
            ttl_hours=ttl_hours,
            tags=tags,
        )

        return {
            "status": "success",
            "session_id": str(session.id),
            "user_id": session.user_id,
            "type": session.type.value,
            "assets": session.assets,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "ttl_hours": ttl_hours,
            "tags": session.tags,
        }

    except Exception as e:
        logger.error(f"Failed to create session: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


async def get_session_info(session_id: str) -> dict:
    """
    Get information about an existing session

    Args:
        session_id: Session UUID

    Returns:
        Session information and state
    """
    from uuid import UUID

    from fiml.sessions.store import get_session_store

    logger.info("get_session_info called", session_id=session_id)

    try:
        session_store = await get_session_store()
        session = await session_store.get_session(UUID(session_id))

        if not session:
            return {
                "status": "not_found",
                "session_id": session_id,
            }

        return {
            "status": "success",
            "session_id": str(session.id),
            "user_id": session.user_id,
            "type": session.type.value,
            "assets": session.assets,
            "created_at": session.created_at.isoformat(),
            "expires_at": session.expires_at.isoformat(),
            "last_accessed_at": session.last_accessed_at.isoformat(),
            "is_expired": session.is_expired,
            "time_remaining_hours": round(session.time_remaining.total_seconds() / 3600, 2),
            "duration_hours": round(session.duration.total_seconds() / 3600, 2),
            "total_queries": session.state.history.total_queries,
            "cache_hit_rate": session.state.history.cache_hit_rate,
            "tags": session.tags,
            "recent_queries": [
                {
                    "type": q.query_type,
                    "timestamp": q.timestamp.isoformat(),
                    "cache_hit": q.cache_hit,
                }
                for q in session.state.history.get_recent_queries(5)
            ],
        }

    except Exception as e:
        logger.error(f"Failed to get session info: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


async def list_sessions(
    user_id: str,
    include_archived: bool = False,
    limit: int = 50,
) -> dict:
    """
    List sessions for a user

    Args:
        user_id: User identifier
        include_archived: Include archived sessions
        limit: Maximum number of sessions to return

    Returns:
        List of session summaries
    """
    from fiml.sessions.store import get_session_store

    logger.info("list_sessions called", user_id=user_id)

    try:
        session_store = await get_session_store()
        summaries = await session_store.list_user_sessions(
            user_id=user_id,
            include_archived=include_archived,
            limit=limit,
        )

        return {
            "status": "success",
            "user_id": user_id,
            "total_sessions": len(summaries),
            "sessions": [
                {
                    "session_id": str(s.id),
                    "type": s.type.value,
                    "assets": s.assets,
                    "created_at": s.created_at.isoformat(),
                    "expires_at": s.expires_at.isoformat(),
                    "total_queries": s.total_queries,
                    "is_expired": s.is_expired,
                    "is_archived": s.is_archived,
                    "tags": s.tags,
                }
                for s in summaries
            ],
        }

    except Exception as e:
        logger.error(f"Failed to list sessions: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


async def extend_session(session_id: str, hours: int = 24) -> dict:
    """
    Extend session expiration time

    Args:
        session_id: Session UUID
        hours: Hours to extend by

    Returns:
        Updated session info
    """
    from uuid import UUID

    from fiml.core.config import settings
    from fiml.sessions.store import get_session_store

    logger.info("extend_session called", session_id=session_id, hours=hours)

    try:
        # Validate extension
        if hours > settings.session_max_ttl_hours:
            hours = settings.session_max_ttl_hours

        session_store = await get_session_store()
        await session_store.extend_session(UUID(session_id), hours)

        # Get updated session
        session = await session_store.get_session(UUID(session_id))

        if not session:
            return {
                "status": "not_found",
                "session_id": session_id,
            }

        return {
            "status": "success",
            "session_id": str(session.id),
            "expires_at": session.expires_at.isoformat(),
            "time_remaining_hours": round(session.time_remaining.total_seconds() / 3600, 2),
        }

    except Exception as e:
        logger.error(f"Failed to extend session: {e}")
        return {
            "status": "error",
            "error": str(e),
        }


async def get_session_analytics(
    user_id: Optional[str] = None,
    session_type: Optional[str] = None,
    days: int = 30,
) -> dict:
    """
    Get session analytics and statistics

    Args:
        user_id: Filter by user (optional)
        session_type: Filter by type (optional)
        days: Number of days to analyze

    Returns:
        Analytics data including:
        - total_sessions: Total number of sessions
        - active_sessions: Number of currently active sessions
        - archived_sessions: Number of archived sessions
        - total_queries: Total queries across all sessions
        - avg_duration_seconds: Average session duration
        - avg_queries_per_session: Average queries per session
        - abandonment_rate: Rate of abandoned sessions
        - top_assets: Most analyzed assets
        - query_type_distribution: Distribution of query types
        - session_type_breakdown: Breakdown by session type
        - popular_tags: Most used tags
    """
    from fiml.sessions.analytics import SessionAnalytics
    from fiml.sessions.store import get_session_store

    logger.info("get_session_analytics called", user_id=user_id, days=days)

    try:
        session_store = await get_session_store()

        if not session_store._session_maker:
            # Return empty analytics if database not available
            return {
                "status": "success",
                "total_sessions": 0,
                "active_sessions": 0,
                "archived_sessions": 0,
                "total_queries": 0,
                "avg_duration_seconds": 0.0,
                "avg_queries_per_session": 0.0,
                "abandonment_rate": 0.0,
                "period_days": days,
                "user_id": user_id,
                "session_type": session_type,
                "top_assets": [],
                "query_type_distribution": {},
                "session_type_breakdown": {},
                "popular_tags": [],
                "message": "Session analytics database not initialized. Analytics will be available once the database is set up.",
            }

        analytics = SessionAnalytics(session_store._session_maker, session_store)
        stats = await analytics.get_session_stats(
            user_id=user_id,
            session_type=session_type,
            days=days,
        )

        return {
            "status": "success",
            **stats,
        }

    except Exception as e:
        logger.error(f"Failed to get session analytics: {e}")
        # Return a valid response structure even on error
        return {
            "status": "success",
            "total_sessions": 0,
            "active_sessions": 0,
            "archived_sessions": 0,
            "total_queries": 0,
            "avg_duration_seconds": 0.0,
            "avg_queries_per_session": 0.0,
            "abandonment_rate": 0.0,
            "period_days": days,
            "user_id": user_id,
            "session_type": session_type,
            "top_assets": [],
            "query_type_distribution": {},
            "session_type_breakdown": {},
            "popular_tags": [],
            "message": f"Session analytics temporarily unavailable: {str(e)}",
        }
