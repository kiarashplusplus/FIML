"""
Market API Router
Provides market data endpoints for mobile app and web dashboard.

This router exposes FIML's market data capabilities via REST API,
using the same underlying MCP tools that power the bot.
"""

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from fiml.bot.education.fiml_adapter import get_fiml_data_adapter
from fiml.core.logging import get_logger

logger = get_logger(__name__)

market_router = APIRouter()


class PriceData(BaseModel):
    """Price data for a single asset"""
    symbol: str
    name: str
    price: float
    change: float
    change_percent: float
    source: str
    timestamp: Optional[str] = None
    asset_type: str = "stock"
    error: Optional[str] = None


class MultiPriceResponse(BaseModel):
    """Response containing prices for multiple assets"""
    prices: Dict[str, PriceData]
    count: int


class AssetDetailsResponse(BaseModel):
    """Detailed asset information with educational context"""
    symbol: str
    name: str
    asset_type: str
    price: Dict[str, Any]
    volume: Dict[str, Any]
    fundamentals: Dict[str, Any]
    narrative: Optional[str] = None
    key_insights: List[str] = []
    risk_factors: List[str] = []
    disclaimer: str
    data_source: str
    timestamp: Optional[str] = None
    is_fallback: bool = False


@market_router.get("/prices")
async def get_market_prices(
    symbols: str = Query(..., description="Comma-separated list of symbols")
) -> MultiPriceResponse:
    """
    Get current prices for multiple symbols.

    This endpoint is designed for mobile app market dashboards and
    any client that needs quick price data for multiple assets.

    Args:
        symbols: Comma-separated list of symbols (e.g., "AAPL,TSLA,BTC")

    Returns:
        Price data for each requested symbol
    """
    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]

    if not symbol_list:
        raise HTTPException(status_code=400, detail="No symbols provided")

    if len(symbol_list) > 50:
        raise HTTPException(status_code=400, detail="Maximum 50 symbols allowed per request")

    try:
        adapter = get_fiml_data_adapter()
        prices = await adapter.get_multiple_prices(symbol_list)

        # Convert to response model
        price_data = {
            symbol: PriceData(**data) for symbol, data in prices.items()
        }

        return MultiPriceResponse(prices=price_data, count=len(price_data))

    except Exception as e:
        logger.error("Failed to fetch market prices", symbols=symbols, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch prices: {str(e)}")


@market_router.get("/assets/{symbol}")
async def get_asset_details(symbol: str) -> AssetDetailsResponse:
    """
    Get detailed information about a specific asset with educational context.

    This endpoint provides comprehensive asset data including:
    - Current price and changes
    - Volume analysis
    - Fundamental metrics
    - AI-generated narrative (if available)
    - Educational explanations

    Args:
        symbol: Asset symbol (e.g., "AAPL", "BTC")

    Returns:
        Detailed asset information with educational context
    """
    try:
        adapter = get_fiml_data_adapter()
        data = await adapter.get_educational_snapshot(
            symbol=symbol.upper(),
            user_id="api_user",  # Generic user for API access
            context="mobile_app"
        )

        return AssetDetailsResponse(
            symbol=data.get("symbol", symbol.upper()),
            name=data.get("name", symbol.upper()),
            asset_type=data.get("asset_type", "stock"),
            price=data.get("price", {}),
            volume=data.get("volume", {}),
            fundamentals=data.get("fundamentals", {}),
            narrative=data.get("narrative"),
            key_insights=data.get("key_insights", []),
            risk_factors=data.get("risk_factors", []),
            disclaimer=data.get("disclaimer", "Educational purposes only"),
            data_source=data.get("data_source", "FIML"),
            timestamp=data.get("timestamp"),
            is_fallback=data.get("is_fallback", False),
        )

    except Exception as e:
        logger.error("Failed to fetch asset details", symbol=symbol, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch asset details: {str(e)}")


@market_router.get("/search")
async def search_assets(
    q: str = Query(..., description="Search query"),
    asset_type: Optional[str] = Query(None, description="Filter by asset type (stock, crypto)")
) -> List[Dict[str, Any]]:
    """
    Search for assets by symbol or name.

    This is a simple search endpoint for the mobile app autocomplete.

    Note: Currently uses a static list of common assets for fast search.
    Future enhancement: Integrate with a provider that supports symbol search
    (e.g., Alpha Vantage SYMBOL_SEARCH or FMP search endpoint).

    Args:
        q: Search query
        asset_type: Optional filter (stock or crypto)

    Returns:
        List of matching assets
    """
    # Static list of common assets for fast autocomplete
    # TODO: Consider externalizing to config or integrating with symbol search API
    # For now, this provides instant results without API latency
    all_assets = [
        {"symbol": "AAPL", "name": "Apple Inc.", "type": "stock"},
        {"symbol": "GOOGL", "name": "Alphabet Inc.", "type": "stock"},
        {"symbol": "MSFT", "name": "Microsoft Corporation", "type": "stock"},
        {"symbol": "AMZN", "name": "Amazon.com Inc.", "type": "stock"},
        {"symbol": "TSLA", "name": "Tesla Inc.", "type": "stock"},
        {"symbol": "META", "name": "Meta Platforms Inc.", "type": "stock"},
        {"symbol": "NVDA", "name": "NVIDIA Corporation", "type": "stock"},
        {"symbol": "BTC", "name": "Bitcoin", "type": "crypto"},
        {"symbol": "ETH", "name": "Ethereum", "type": "crypto"},
        {"symbol": "SOL", "name": "Solana", "type": "crypto"},
        {"symbol": "XRP", "name": "Ripple", "type": "crypto"},
        {"symbol": "DOGE", "name": "Dogecoin", "type": "crypto"},
        {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "type": "stock"},
        {"symbol": "V", "name": "Visa Inc.", "type": "stock"},
        {"symbol": "WMT", "name": "Walmart Inc.", "type": "stock"},
        {"symbol": "DIS", "name": "The Walt Disney Company", "type": "stock"},
        {"symbol": "NFLX", "name": "Netflix Inc.", "type": "stock"},
        {"symbol": "AMD", "name": "Advanced Micro Devices Inc.", "type": "stock"},
    ]

    query_upper = q.upper()

    # Filter by query
    results = [
        asset for asset in all_assets
        if query_upper in asset["symbol"] or query_upper in asset["name"].upper()
    ]

    # Filter by asset type if specified
    if asset_type:
        results = [asset for asset in results if asset["type"] == asset_type.lower()]

    return results[:10]  # Limit to 10 results
