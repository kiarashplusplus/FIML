"""
Component 10: FIML Educational Data Adapter
Formats market data with educational context and explanations
"""

from typing import Dict, Optional

import structlog

from fiml.arbitration.engine import DataArbitrationEngine
from fiml.core.models import Asset, DataType

logger = structlog.get_logger(__name__)


class FIMLEducationalDataAdapter:
    """
    Adapts FIML market data for educational purposes

    Features:
    - Beginner-friendly explanations
    - Context and interpretation for all metrics
    - Educational narratives
    - Platform-specific formatting
    - Integration with FIML arbitration engine
    """

    def __init__(self, arbitration_engine: Optional[DataArbitrationEngine] = None):
        """
        Initialize adapter with FIML arbitration engine

        Args:
            arbitration_engine: FIML data arbitration engine (creates new if None)
        """
        self.arbitration_engine = arbitration_engine or DataArbitrationEngine()
        logger.info("FIMLEducationalDataAdapter initialized with FIML integration")

    async def get_educational_snapshot(
        self,
        symbol: str,
        user_id: str,
        context: str = "lesson"
    ) -> Dict:
        """
        Get market data formatted for education using FIML arbitration

        Args:
            symbol: Stock/crypto symbol
            user_id: User identifier
            context: Context (lesson, quiz, mentor)

        Returns:
            Educational data dict with live FIML data and educational interpretations
        """
        try:
            # Create asset and get data via FIML arbitration
            asset = Asset(symbol=symbol, asset_class="stock")

            # Get arbitration plan (will use user's keys via FIMLProviderConfigurator)
            plan = await self.arbitration_engine.arbitrate_request(
                asset=asset,
                data_type=DataType.QUOTE,
                user_region="US"
            )

            # Execute the plan to get actual data
            from fiml.providers.registry import provider_registry
            provider = provider_registry.get_provider(plan.primary_provider)
            response = await provider.get_quote(asset)

            # Extract data from response
            quote = response.data
            current_price = quote.get("price", 0)
            open_price = quote.get("open", current_price)
            change = current_price - open_price
            change_percent = (change / open_price * 100) if open_price > 0 else 0
            volume = quote.get("volume", 0)
            avg_volume = quote.get("avg_volume", volume)

            # Build educational snapshot with live data
            educational_data = {
                "symbol": symbol,
                "name": quote.get("name", f"{symbol} Inc."),
                "price": {
                    "current": current_price,
                    "change": change,
                    "change_percent": change_percent,
                    "explanation": self.explain_price_movement(change_percent)
                },
                "volume": {
                    "current": volume,
                    "average": avg_volume,
                    "interpretation": self.explain_volume(volume, avg_volume)
                },
                "fundamentals": {
                    "pe_ratio": quote.get("pe_ratio"),
                    "market_cap": quote.get("market_cap"),
                    "explanation": self.explain_pe_ratio(quote.get("pe_ratio")) if quote.get("pe_ratio") else "P/E ratio not available"
                },
                "disclaimer": "📚 Live market data for educational purposes only",
                "data_source": f"Via FIML from {plan.primary_provider}",
                "timestamp": quote.get("timestamp")
            }

            # Safely calculate freshness if timestamps available
            if quote.get("timestamp") and quote.get("fetched_at"):
                try:
                    from datetime import datetime
                    ts = quote.get("timestamp")
                    fetched = quote.get("fetched_at")
                    if isinstance(ts, datetime) and isinstance(fetched, datetime):
                        educational_data["freshness_seconds"] = (fetched - ts).total_seconds()
                except Exception:
                    pass  # Skip freshness if calculation fails

            logger.info(
                "Educational snapshot created with live FIML data",
                symbol=symbol,
                user_id=user_id,
                provider=plan.primary_provider,
                context=context
            )

        except Exception as e:
            # Fallback to template data if FIML integration fails
            logger.warning(
                "Failed to get live data, using template",
                symbol=symbol,
                error=str(e)
            )
            educational_data = self._get_template_snapshot(symbol)

        return educational_data

    def _get_template_snapshot(self, symbol: str) -> Dict:
        """Fallback template data when FIML is unavailable"""
        return {
            "symbol": symbol,
            "name": f"{symbol} Inc.",
            "price": {
                "current": 150.25,
                "change": -2.30,
                "change_percent": -1.51,
                "explanation": self.explain_price_movement(-1.51)
            },
            "volume": {
                "current": 75000000,
                "average": 50000000,
                "interpretation": self.explain_volume(75000000, 50000000)
            },
            "fundamentals": {
                "pe_ratio": 28.5,
                "market_cap": "2.5T",
                "explanation": "P/E ratio of 28.5 suggests investors expect growth"
            },
            "disclaimer": "📚 Sample data for educational purposes",
            "data_source": "Template (FIML integration pending)"
        }

    def explain_price_movement(self, change_percent: float) -> str:
        """Educational interpretation of price change"""

        abs_change = abs(change_percent)
        direction = "up" if change_percent > 0 else "down"

        if abs_change < 0.5:
            return f"Minimal movement {direction} - typical daily fluctuation"
        elif abs_change < 2:
            return f"Moderate movement {direction} - notable but not unusual"
        elif abs_change < 5:
            return f"Significant movement {direction} - indicates strong market interest"
        else:
            return f"Exceptional movement {direction} - major event or news likely"

    def explain_volume(self, current: int, average: int) -> str:
        """Educational interpretation of volume"""

        ratio = current / average if average > 0 else 1

        if ratio < 0.5:
            return f"Volume is {ratio:.1f}x average - low interest today"
        elif ratio < 0.8:
            return f"Volume is {ratio:.1f}x average - below normal interest"
        elif ratio < 1.2:
            return "Volume is normal - typical trading activity"
        elif ratio < 2:
            return f"Volume is {ratio:.1f}x average - elevated interest"
        else:
            return f"Volume is {ratio:.1f}x average - very high interest, watch for news"

    def explain_pe_ratio(self, pe: float) -> str:
        """Explain P/E ratio in simple terms"""

        if pe < 0:
            return "Negative P/E (company has losses) - risky investment"
        elif pe < 15:
            return "Low P/E (< 15) - may be undervalued or facing challenges"
        elif pe < 25:
            return "Moderate P/E (15-25) - fairly valued"
        elif pe < 40:
            return "High P/E (25-40) - growth expected, but pricey"
        else:
            return "Very high P/E (> 40) - strong growth expected, high valuation"

    def explain_market_cap(self, market_cap: float) -> str:
        """Explain market cap categories"""

        # Assuming market_cap in billions
        if market_cap < 0.3:
            return "Micro-cap (< $300M) - very small, high risk"
        elif market_cap < 2:
            return "Small-cap ($300M - $2B) - small company, higher risk"
        elif market_cap < 10:
            return "Mid-cap ($2B - $10B) - medium-sized, balanced risk"
        elif market_cap < 200:
            return "Large-cap ($10B - $200B) - large established company"
        else:
            return "Mega-cap (> $200B) - massive company, lower volatility"

    async def format_for_lesson(self, data: Dict) -> str:
        """Format data for lesson display"""

        output = []
        output.append(f"📊 **{data['symbol']} - {data['name']}**\n")

        # Price info
        price = data.get('price', {})
        output.append(f"**Current Price:** ${price.get('current', 0):.2f}")
        output.append(f"**Change:** {price.get('change_percent', 0):+.2f}%")
        output.append(f"_({price.get('explanation', '')})_\n")

        # Volume info
        volume = data.get('volume', {})
        output.append(f"**Volume:** {volume.get('current', 0):,} shares")
        output.append(f"_({volume.get('interpretation', '')})_\n")

        # Fundamentals
        fund = data.get('fundamentals', {})
        if fund:
            output.append(f"**P/E Ratio:** {fund.get('pe_ratio', 'N/A')}")
            output.append(f"**Market Cap:** {fund.get('market_cap', 'N/A')}")
            output.append(f"_({fund.get('explanation', '')})_\n")

        # Disclaimer
        output.append(f"\n_{data.get('disclaimer', '')}_")

        return "\n".join(output)

    async def format_for_quiz(self, data: Dict) -> str:
        """Format data for quiz questions"""

        price = data.get('price', {})
        volume = data.get('volume', {})

        return (
            f"**{data['symbol']}**\n"
            f"Price: ${price.get('current', 0):.2f} ({price.get('change_percent', 0):+.2f}%)\n"
            f"Volume: {volume.get('current', 0):,}\n"
        )

    async def format_for_mentor(self, data: Dict, question: str) -> str:
        """Format data for AI mentor context"""

        # Provide concise data for mentor to reference
        price = data.get('price', {})

        return (
            f"Current {data['symbol']} data:\n"
            f"Price: ${price.get('current', 0):.2f} ({price.get('change_percent', 0):+.2f}%)\n"
            f"Interpretation: {price.get('explanation', '')}"
        )

    def create_chart_description(self, data: Dict) -> str:
        """Create text description of what a chart would show"""

        price = data.get('price', {})
        change = price.get('change_percent', 0)

        if change > 0:
            trend = "upward trend"
            color = "green"
        elif change < 0:
            trend = "downward trend"
            color = "red"
        else:
            trend = "flat movement"
            color = "gray"

        return (
            f"📈 Chart would show {trend} ({color} candles) "
            f"with current price at ${price.get('current', 0):.2f}"
        )
