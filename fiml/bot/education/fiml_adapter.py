"""
Component 10: FIML Educational Data Adapter
Formats market data with educational context and explanations

This adapter provides a unified interface for fetching real market data
through FIML's MCP tools and arbitration engine, with educational context.
It is designed to be reusable across both Telegram bot and mobile app.
"""

from typing import Any, Dict, Optional

import structlog

from fiml.core.models import AnalysisDepth, AssetType, Market

logger = structlog.get_logger(__name__)


class FIMLEducationalDataAdapter:
    """
    Adapts FIML market data for educational purposes

    Features:
    - Beginner-friendly explanations
    - Context and interpretation for all metrics
    - Educational narratives
    - Platform-specific formatting
    - Full integration with FIML MCP tools (search_by_symbol, search_by_coin)
    - Reusable across Telegram bot and mobile app
    """

    def __init__(self) -> None:
        """
        Initialize adapter with FIML MCP tools integration
        """
        logger.info("FIMLEducationalDataAdapter initialized with FIML MCP integration")

    def _detect_asset_type(self, symbol: str) -> AssetType:
        """
        Detect if symbol is stock or crypto
        
        Args:
            symbol: Asset symbol
            
        Returns:
            AssetType enum value
        """
        # Common crypto symbols
        crypto_symbols = {
            "BTC", "ETH", "SOL", "XRP", "ADA", "DOT", "AVAX", "MATIC", 
            "LINK", "UNI", "ATOM", "LTC", "DOGE", "SHIB", "BNB",
        }
        
        symbol_upper = symbol.upper().split("/")[0]  # Handle pairs like BTC/USDT
        
        if symbol_upper in crypto_symbols:
            return AssetType.CRYPTO
        return AssetType.EQUITY

    async def get_educational_snapshot(
        self, symbol: str, user_id: str, context: str = "lesson"
    ) -> Dict[str, Any]:
        """
        Get market data formatted for education using FIML MCP tools

        This method uses the full FIML integration via MCP tools (search_by_symbol
        or search_by_coin) which include:
        - Arbitration engine for provider selection
        - Caching (L1/L2) 
        - Narrative generation
        - Compliance checking

        Args:
            symbol: Stock/crypto symbol
            user_id: User identifier
            context: Context (lesson, quiz, mentor)

        Returns:
            Educational data dict with live FIML data and educational interpretations
        """
        try:
            from fiml.mcp.tools import search_by_coin, search_by_symbol

            asset_type = self._detect_asset_type(symbol)
            
            if asset_type == AssetType.CRYPTO:
                # Use search_by_coin for crypto
                response = await search_by_coin(
                    symbol=symbol.upper().split("/")[0],  # Extract base symbol
                    exchange="binance",
                    pair="USDT",
                    depth=AnalysisDepth.STANDARD,
                    language="en",
                    expertise_level="beginner",
                    include_narrative=True,
                )
                
                # Build educational data from crypto response
                cached = response.cached
                educational_data = {
                    "symbol": response.symbol,
                    "name": response.name,
                    "asset_type": "crypto",
                    "price": {
                        "current": cached.price,
                        "change": cached.change,
                        "change_percent": cached.change_percent,
                        "explanation": self.explain_price_movement(cached.change_percent),
                    },
                    "volume": {
                        "current": response.crypto_metrics.get("volume24h", 0),
                        "average": response.crypto_metrics.get("volume24h", 0),
                        "interpretation": "24-hour trading volume across exchanges",
                    },
                    "crypto_metrics": {
                        "high_24h": response.crypto_metrics.get("high_24h", 0),
                        "low_24h": response.crypto_metrics.get("low_24h", 0),
                        "ath": response.crypto_metrics.get("ath", 0),
                    },
                    "fundamentals": {
                        "market_dominance": response.crypto_metrics.get("dominance", "N/A"),
                        "explanation": "Market dominance shows this coin's share of total crypto market cap",
                    },
                    "narrative": response.narrative.summary if response.narrative else None,
                    "disclaimer": response.disclaimer or "📚 Live market data for educational purposes only",
                    "data_source": f"Via FIML from {cached.source}",
                    "timestamp": cached.as_of.isoformat() if cached.as_of else None,
                    "confidence": cached.confidence,
                }
            else:
                # Use search_by_symbol for stocks
                response = await search_by_symbol(
                    symbol=symbol.upper(),
                    market=Market.US,
                    depth=AnalysisDepth.STANDARD,
                    language="en",
                    expertise_level="beginner",
                    include_narrative=True,
                )
                
                # Build educational data from stock response
                cached = response.cached
                structural = response.structural_data
                
                educational_data = {
                    "symbol": response.symbol,
                    "name": response.name,
                    "asset_type": "stock",
                    "exchange": response.exchange,
                    "price": {
                        "current": cached.price,
                        "change": cached.change,
                        "change_percent": cached.change_percent,
                        "explanation": self.explain_price_movement(cached.change_percent),
                    },
                    "volume": {
                        "current": structural.avg_volume if structural else 0,
                        "average": structural.avg_volume if structural else 0,
                        "interpretation": self.explain_volume(
                            structural.avg_volume if structural else 0,
                            structural.avg_volume if structural else 1
                        ),
                    },
                    "fundamentals": {
                        "pe_ratio": structural.pe_ratio if structural else None,
                        "market_cap": structural.market_cap if structural else None,
                        "beta": structural.beta if structural else None,
                        "sector": structural.sector if structural else None,
                        "industry": structural.industry if structural else None,
                        "week_52_high": structural.week_52_high if structural else None,
                        "week_52_low": structural.week_52_low if structural else None,
                        "explanation": (
                            self.explain_pe_ratio(float(structural.pe_ratio))
                            if structural and structural.pe_ratio
                            else "P/E ratio not available"
                        ),
                    },
                    "narrative": response.narrative.summary if response.narrative else None,
                    "key_insights": response.narrative.key_insights if response.narrative else [],
                    "risk_factors": response.narrative.risk_factors if response.narrative else [],
                    "disclaimer": response.disclaimer or "📚 Live market data for educational purposes only",
                    "data_source": f"Via FIML from {cached.source}",
                    "timestamp": cached.as_of.isoformat() if cached.as_of else None,
                    "confidence": cached.confidence,
                }

            logger.info(
                "Educational snapshot created with live FIML data",
                symbol=symbol,
                user_id=user_id,
                asset_type=asset_type.value,
                source=cached.source,
                context=context,
            )

            return educational_data

        except Exception as e:
            # Fallback to template data if FIML integration fails
            logger.warning(
                "Failed to get live data via MCP tools, using template", 
                symbol=symbol, 
                error=str(e)
            )
            return self._get_template_snapshot(symbol)

    def _get_template_snapshot(self, symbol: str) -> Dict[str, Any]:
        """
        Fallback template data when FIML is unavailable
        
        This is used when:
        - Provider registry is not initialized
        - All providers fail
        - Cache is unavailable
        """
        asset_type = self._detect_asset_type(symbol)
        
        if asset_type == AssetType.CRYPTO:
            return {
                "symbol": symbol.upper(),
                "name": symbol.upper(),
                "asset_type": "crypto",
                "price": {
                    "current": 0.0,
                    "change": 0.0,
                    "change_percent": 0.0,
                    "explanation": "Unable to fetch live data - please check your API keys or try again later",
                },
                "volume": {
                    "current": 0,
                    "average": 0,
                    "interpretation": "Volume data unavailable",
                },
                "crypto_metrics": {},
                "fundamentals": {
                    "explanation": "Fundamental data unavailable",
                },
                "narrative": None,
                "disclaimer": "📚 Unable to fetch live data - please configure API keys with /addkey",
                "data_source": "Unavailable (API not configured or service error)",
                "is_fallback": True,
            }
        else:
            return {
                "symbol": symbol.upper(),
                "name": f"{symbol.upper()} Inc.",
                "asset_type": "stock",
                "price": {
                    "current": 0.0,
                    "change": 0.0,
                    "change_percent": 0.0,
                    "explanation": "Unable to fetch live data - please check your API keys or try again later",
                },
                "volume": {
                    "current": 0,
                    "average": 0,
                    "interpretation": "Volume data unavailable",
                },
                "fundamentals": {
                    "pe_ratio": None,
                    "market_cap": None,
                    "explanation": "Fundamental data unavailable",
                },
                "narrative": None,
                "disclaimer": "📚 Unable to fetch live data - please configure API keys with /addkey",
                "data_source": "Unavailable (API not configured or service error)",
                "is_fallback": True,
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

        # Convert to billions for easier comparison
        market_cap_billions = market_cap / 1_000_000_000

        if market_cap_billions < 0.3:
            return "Micro-cap (< $300M) - very small, high risk"
        elif market_cap_billions < 2:
            return "Small-cap ($300M - $2B) - small company, higher risk"
        elif market_cap_billions < 10:
            return "Mid-cap ($2B - $10B) - medium-sized, balanced risk"
        elif market_cap_billions < 200:
            return "Large-cap ($10B - $200B) - large established company"
        else:
            return "Mega-cap (> $200B) - massive company, lower volatility"

    async def format_for_lesson(self, data: Dict) -> str:
        """Format data for lesson display"""

        output = []
        output.append(f"📊 **{data['symbol']} - {data['name']}**\n")

        # Price info
        price = data.get("price", {})
        output.append(f"**Current Price:** ${price.get('current', 0):.2f}")
        output.append(f"**Change:** {price.get('change_percent', 0):+.2f}%")
        output.append(f"_({price.get('explanation', '')})_\n")

        # Volume info
        volume = data.get("volume", {})
        output.append(f"**Volume:** {volume.get('current', 0):,} shares")
        output.append(f"_({volume.get('interpretation', '')})_\n")

        # Fundamentals
        fund = data.get("fundamentals", {})
        if fund:
            output.append(f"**P/E Ratio:** {fund.get('pe_ratio', 'N/A')}")
            output.append(f"**Market Cap:** {fund.get('market_cap', 'N/A')}")
            output.append(f"_({fund.get('explanation', '')})_\n")

        # Disclaimer
        output.append(f"\n_{data.get('disclaimer', '')}_")

        return "\n".join(output)

    async def format_for_quiz(self, data: Dict) -> str:
        """Format data for quiz questions"""

        price = data.get("price", {})
        volume = data.get("volume", {})

        return (
            f"**{data['symbol']}**\n"
            f"Price: ${price.get('current', 0):.2f} ({price.get('change_percent', 0):+.2f}%)\n"
            f"Volume: {volume.get('current', 0):,}\n"
        )

    async def format_for_mentor(self, data: Dict, question: str) -> str:
        """Format data for AI mentor context"""

        # Provide concise data for mentor to reference
        price = data.get("price", {})

        return (
            f"Current {data['symbol']} data:\n"
            f"Price: ${price.get('current', 0):.2f} ({price.get('change_percent', 0):+.2f}%)\n"
            f"Interpretation: {price.get('explanation', '')}"
        )

    def create_chart_description(self, data: Dict) -> str:
        """Create text description of what a chart would show"""

        price = data.get("price", {})
        change = price.get("change_percent", 0)

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

    async def get_quick_price(self, symbol: str) -> Dict[str, Any]:
        """
        Get quick price data for a symbol (minimal processing, fast response)
        
        This is optimized for mobile app price displays and quick lookups.
        Uses the 'quick' depth level for faster responses.
        
        Args:
            symbol: Stock/crypto symbol
            
        Returns:
            Quick price data dict
        """
        try:
            from fiml.mcp.tools import search_by_coin, search_by_symbol
            
            asset_type = self._detect_asset_type(symbol)
            
            if asset_type == AssetType.CRYPTO:
                response = await search_by_coin(
                    symbol=symbol.upper().split("/")[0],
                    exchange="binance",
                    pair="USDT",
                    depth=AnalysisDepth.QUICK,
                    language="en",
                    include_narrative=False,  # Skip narrative for speed
                )
                cached = response.cached
                return {
                    "symbol": response.symbol,
                    "name": response.name,
                    "price": cached.price,
                    "change": cached.change,
                    "change_percent": cached.change_percent,
                    "source": cached.source,
                    "timestamp": cached.as_of.isoformat() if cached.as_of else None,
                    "asset_type": "crypto",
                }
            else:
                response = await search_by_symbol(
                    symbol=symbol.upper(),
                    market=Market.US,
                    depth=AnalysisDepth.QUICK,
                    language="en",
                    include_narrative=False,  # Skip narrative for speed
                )
                cached = response.cached
                return {
                    "symbol": response.symbol,
                    "name": response.name,
                    "price": cached.price,
                    "change": cached.change,
                    "change_percent": cached.change_percent,
                    "source": cached.source,
                    "timestamp": cached.as_of.isoformat() if cached.as_of else None,
                    "asset_type": "stock",
                }
        except Exception as e:
            logger.warning("Failed to get quick price", symbol=symbol, error=str(e))
            return {
                "symbol": symbol.upper(),
                "name": symbol.upper(),
                "price": 0.0,
                "change": 0.0,
                "change_percent": 0.0,
                "source": "error",
                "error": str(e),
            }

    async def get_multiple_prices(self, symbols: list[str]) -> Dict[str, Dict[str, Any]]:
        """
        Get price data for multiple symbols concurrently
        
        This is useful for mobile app market dashboards that need
        to display multiple assets at once.
        
        Args:
            symbols: List of stock/crypto symbols
            
        Returns:
            Dict mapping symbol to price data
        """
        import asyncio
        
        results = {}
        
        # Fetch all prices concurrently
        tasks = [self.get_quick_price(symbol) for symbol in symbols]
        prices = await asyncio.gather(*tasks, return_exceptions=True)
        
        for symbol, price_data in zip(symbols, prices):
            if isinstance(price_data, Exception):
                results[symbol.upper()] = {
                    "symbol": symbol.upper(),
                    "error": str(price_data),
                    "price": 0.0,
                }
            else:
                results[symbol.upper()] = price_data
                
        return results


# Singleton instance for easy access across the application
_fiml_data_adapter: Optional[FIMLEducationalDataAdapter] = None


def get_fiml_data_adapter() -> FIMLEducationalDataAdapter:
    """Get or create the singleton FIML data adapter instance"""
    global _fiml_data_adapter
    if _fiml_data_adapter is None:
        _fiml_data_adapter = FIMLEducationalDataAdapter()
    return _fiml_data_adapter
