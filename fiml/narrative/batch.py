"""
Batch Narrative Generation

Pre-generates narratives for popular symbols to reduce API calls
and improve response times during peak hours.
"""

from datetime import datetime, time, timezone
from typing import Any, Dict, List, Optional

from fiml.core.logging import get_logger
from fiml.core.models import AssetType
from fiml.narrative.cache import narrative_cache
from fiml.narrative.generator import NarrativeGenerator
from fiml.narrative.models import ExpertiseLevel, Language, NarrativeContext, NarrativePreferences

logger = get_logger(__name__)


class BatchNarrativeGenerator:
    """
    Pre-generate narratives for popular symbols

    Runs scheduled tasks to generate and cache narratives before
    market open to ensure instant retrieval during peak hours.
    """

    # Top 100 most popular symbols (extend as needed)
    POPULAR_SYMBOLS = [
        # Tech giants
        "AAPL",
        "MSFT",
        "GOOGL",
        "AMZN",
        "META",
        "NVDA",
        "TSLA",
        "NFLX",
        # Major indexes
        "SPY",
        "QQQ",
        "DIA",
        "IWM",
        "VTI",
        # Crypto
        "BTC/USD",
        "ETH/USD",
        "BNB/USD",
        "SOL/USD",
        "ADA/USD",
        "XRP/USD",
        # Financial
        "JPM",
        "BAC",
        "WFC",
        "GS",
        "MS",
        "C",
        "V",
        "MA",
        # Healthcare
        "JNJ",
        "UNH",
        "PFE",
        "ABBV",
        "TMO",
        "MRK",
        "LLY",
        # Consumer
        "WMT",
        "HD",
        "NKE",
        "COST",
        "MCD",
        "SBUX",
        "DIS",
        # Energy
        "XOM",
        "CVX",
        "COP",
        "SLB",
        "EOG",
        # Industrial
        "BA",
        "CAT",
        "GE",
        "UPS",
        "HON",
        # Semiconductor
        "AMD",
        "INTC",
        "QCOM",
        "AVGO",
        "MU",
        "TXN",
        # Communications
        "T",
        "VZ",
        "CMCSA",
        "TMUS",
        # Retail
        "AMZN",
        "TGT",
        "LOW",
        "TJX",
        "BABA",
    ]

    # Languages to pre-generate (focus on most common)
    DEFAULT_LANGUAGES = [Language.ENGLISH, Language.SPANISH, Language.CHINESE]

    # Expertise levels to pre-generate
    DEFAULT_EXPERTISE_LEVELS = [
        ExpertiseLevel.BEGINNER,
        ExpertiseLevel.INTERMEDIATE,
    ]

    def __init__(
        self,
        narrative_generator: Optional[NarrativeGenerator] = None,
    ):
        """
        Initialize batch narrative generator

        Args:
            narrative_generator: Optional narrative generator instance
        """
        self.narrative_generator = narrative_generator or NarrativeGenerator()
        self.narrative_cache = narrative_cache
        self._generation_count = 0
        self._error_count = 0
        logger.info("Batch narrative generator initialized")

    async def generate_daily_narratives(
        self,
        symbols: Optional[List[str]] = None,
        languages: Optional[List[Language]] = None,
        expertise_levels: Optional[List[ExpertiseLevel]] = None,
    ) -> Dict[str, Any]:
        """
        Generate narratives for popular symbols

        This is the main Celery task that runs daily at market open.

        Args:
            symbols: List of symbols to process (defaults to POPULAR_SYMBOLS)
            languages: Languages to generate (defaults to DEFAULT_LANGUAGES)
            expertise_levels: Expertise levels (defaults to DEFAULT_EXPERTISE_LEVELS)

        Returns:
            Summary of generation results

        Example:
            >>> generator = BatchNarrativeGenerator()
            >>> result = await generator.generate_daily_narratives()
            >>> print(f"Generated {result['success_count']} narratives")
        """
        start_time = datetime.now(timezone.utc)
        logger.info("Starting daily narrative generation")

        symbols = symbols or self.POPULAR_SYMBOLS[:100]
        languages = languages or self.DEFAULT_LANGUAGES
        expertise_levels = expertise_levels or self.DEFAULT_EXPERTISE_LEVELS

        total_combinations = len(symbols) * len(languages) * len(expertise_levels)
        success_count = 0
        error_count = 0
        skipped_count = 0

        # Check if it's appropriate market time
        if not self._is_market_open_soon():
            logger.warning("Batch generation running outside of pre-market hours")

        for symbol in symbols:
            # Determine asset type
            asset_type = self._determine_asset_type(symbol)

            for language in languages:
                for expertise_level in expertise_levels:
                    try:
                        # Check if already cached
                        cached = await self.narrative_cache.get(
                            symbol=symbol,
                            language=language.value,
                            expertise_level=expertise_level.value,
                        )

                        if cached:
                            skipped_count += 1
                            logger.debug(
                                "Skipping cached narrative",
                                symbol=symbol,
                                language=language.value,
                            )
                            continue

                        # Generate narrative
                        success = await self._generate_and_cache_narrative(
                            symbol=symbol,
                            asset_type=asset_type,
                            language=language,
                            expertise_level=expertise_level,
                        )

                        if success:
                            success_count += 1
                        else:
                            error_count += 1

                    except Exception as e:
                        error_count += 1
                        logger.error(
                            f"Failed to generate narrative: {e}",
                            symbol=symbol,
                            language=language.value,
                        )

        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()

        result = {
            "status": "completed",
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "duration_seconds": duration,
            "total_combinations": total_combinations,
            "success_count": success_count,
            "error_count": error_count,
            "skipped_count": skipped_count,
            "symbols_processed": len(symbols),
            "languages": [lang.value for lang in languages],
            "expertise_levels": [level.value for level in expertise_levels],
        }

        logger.info(
            "Daily narrative generation completed",
            duration=duration,
            success=success_count,
            errors=error_count,
        )

        return result

    async def _generate_and_cache_narrative(
        self,
        symbol: str,
        asset_type: str,
        language: Language,
        expertise_level: ExpertiseLevel,
    ) -> bool:
        """
        Generate and cache a single narrative

        Args:
            symbol: Asset symbol
            asset_type: Type of asset
            language: Target language
            expertise_level: User expertise level

        Returns:
            True if successful
        """
        try:
            # Build minimal context (will be enriched with real data)
            preferences = NarrativePreferences(
                language=language,
                expertise_level=expertise_level,
                include_technical=True,
                include_fundamental=expertise_level != ExpertiseLevel.BEGINNER,
                include_sentiment=expertise_level
                in [
                    ExpertiseLevel.ADVANCED,
                    ExpertiseLevel.QUANT,
                ],
                include_risk=True,
                max_length_chars=1500,
            )

            context = NarrativeContext(
                asset_symbol=symbol,
                asset_type=asset_type,
                region="US",
                preferences=preferences,
                # Note: In production, fetch real market data here
                price_data={
                    "price": 0,
                    "change": 0,
                    "change_percent": 0,
                },
            )

            # Generate narrative
            narrative = await self.narrative_generator.generate_narrative(context)

            # Cache the narrative
            narrative_data = {
                "summary": narrative.summary,
                "key_insights": narrative.key_insights,
                "risk_factors": narrative.risk_factors,
                "language": language.value,
                "generated_at": narrative.generated_at.isoformat(),
            }

            # Determine asset type enum
            asset_type_enum = AssetType.CRYPTO if "/" in symbol else AssetType.EQUITY

            await self.narrative_cache.set(
                symbol=symbol,
                narrative_data=narrative_data,
                language=language.value,
                expertise_level=expertise_level.value,
                asset_type=asset_type_enum,
            )

            self._generation_count += 1
            logger.debug(
                "Narrative generated and cached",
                symbol=symbol,
                language=language.value,
            )

            return True

        except Exception as e:
            self._error_count += 1
            logger.error(
                f"Failed to generate narrative: {e}",
                symbol=symbol,
                language=language.value,
            )
            return False

    def _determine_asset_type(self, symbol: str) -> str:
        """
        Determine asset type from symbol

        Args:
            symbol: Asset symbol

        Returns:
            Asset type string
        """
        if "/" in symbol or symbol.endswith("USD"):
            return "crypto"
        elif symbol in ["SPY", "QQQ", "DIA", "IWM", "VTI"]:
            return "index"
        else:
            return "equity"

    def _is_market_open_soon(self) -> bool:
        """
        Check if we're within 2 hours before market open

        Returns:
            True if within pre-market hours (7:30-9:30 AM ET = 12:30-14:30 UTC)
        """
        now = datetime.now(timezone.utc)
        current_time = now.time()

        # Pre-market hours: 7:30-9:30 AM ET (12:30-14:30 UTC)
        pre_market_start = time(12, 30)
        market_open = time(14, 30)

        is_weekday = (
            now.weekday() < 5
        )  # Monday=0, Tuesday=1, Wednesday=2, Thursday=3, Friday=4 (Saturday=5, Sunday=6 are excluded)

        return is_weekday and pre_market_start <= current_time <= market_open

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get batch generation metrics

        Returns:
            Dictionary with metrics
        """
        return {
            "total_generated": self._generation_count,
            "total_errors": self._error_count,
            "success_rate": (
                (self._generation_count / (self._generation_count + self._error_count)) * 100
                if (self._generation_count + self._error_count) > 0
                else 0.0
            ),
        }


# Celery task wrapper (to be integrated with Celery)
async def generate_daily_narratives_task() -> Dict[str, Any]:
    """
    Celery task for daily narrative generation

    This task should be scheduled to run at:
    - 9:00 AM ET (14:00 UTC) on weekdays for US market
    - Other times for international markets

    Example in Celery config:
        beat_schedule = {
            'generate-daily-narratives': {
                'task': 'fiml.narrative.batch.generate_daily_narratives_task',
                'schedule': crontab(hour=14, minute=0, day_of_week='1-5'),
            },
        }
    """
    generator = BatchNarrativeGenerator()
    result = await generator.generate_daily_narratives()

    logger.info(
        "Daily narrative generation task completed",
        success=result["success_count"],
        errors=result["error_count"],
    )

    return result
