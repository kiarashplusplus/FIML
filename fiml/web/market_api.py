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


# Common assets for fast local search (used as fallback)
COMMON_ASSETS = [
    {"symbol": "AAPL", "name": "Apple Inc.", "type": "stock"},
    {"symbol": "GOOGL", "name": "Alphabet Inc.", "type": "stock"},
    {"symbol": "MSFT", "name": "Microsoft Corporation", "type": "stock"},
    {"symbol": "AMZN", "name": "Amazon.com Inc.", "type": "stock"},
    {"symbol": "TSLA", "name": "Tesla Inc.", "type": "stock"},
    {"symbol": "META", "name": "Meta Platforms Inc.", "type": "stock"},
    {"symbol": "NVDA", "name": "NVIDIA Corporation", "type": "stock"},
    {"symbol": "JPM", "name": "JPMorgan Chase & Co.", "type": "stock"},
    {"symbol": "V", "name": "Visa Inc.", "type": "stock"},
    {"symbol": "WMT", "name": "Walmart Inc.", "type": "stock"},
    {"symbol": "DIS", "name": "The Walt Disney Company", "type": "stock"},
    {"symbol": "NFLX", "name": "Netflix Inc.", "type": "stock"},
    {"symbol": "AMD", "name": "Advanced Micro Devices Inc.", "type": "stock"},
    {"symbol": "INTC", "name": "Intel Corporation", "type": "stock"},
    {"symbol": "CRM", "name": "Salesforce Inc.", "type": "stock"},
    {"symbol": "ORCL", "name": "Oracle Corporation", "type": "stock"},
    {"symbol": "ADBE", "name": "Adobe Inc.", "type": "stock"},
    {"symbol": "PYPL", "name": "PayPal Holdings Inc.", "type": "stock"},
    {"symbol": "BTC", "name": "Bitcoin", "type": "crypto"},
    {"symbol": "ETH", "name": "Ethereum", "type": "crypto"},
    {"symbol": "SOL", "name": "Solana", "type": "crypto"},
    {"symbol": "XRP", "name": "Ripple", "type": "crypto"},
    {"symbol": "DOGE", "name": "Dogecoin", "type": "crypto"},
    {"symbol": "ADA", "name": "Cardano", "type": "crypto"},
    {"symbol": "DOT", "name": "Polkadot", "type": "crypto"},
    {"symbol": "AVAX", "name": "Avalanche", "type": "crypto"},
    {"symbol": "MATIC", "name": "Polygon", "type": "crypto"},
    {"symbol": "LINK", "name": "Chainlink", "type": "crypto"},
]


async def search_symbol_with_yfinance(query: str) -> List[Dict[str, Any]]:
    """
    Search for symbols using yfinance.

    This provides real-time symbol lookup for stocks.

    Args:
        query: Search query (symbol or company name)

    Returns:
        List of matching assets with symbol, name, and type
    """
    try:
        import yfinance as yf

        # Try to get info for exact symbol match first
        symbol = query.upper()
        ticker = yf.Ticker(symbol)
        info = ticker.info

        if info and info.get("symbol"):
            # Valid symbol found
            asset_type = "crypto" if info.get("quoteType") == "CRYPTOCURRENCY" else "stock"
            return [{
                "symbol": info.get("symbol", symbol),
                "name": info.get("longName") or info.get("shortName") or symbol,
                "type": asset_type,
                "exchange": info.get("exchange", ""),
                "sector": info.get("sector", ""),
            }]
    except Exception as e:
        logger.debug("yfinance lookup failed", query=query, error=str(e))

    return []


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

    This endpoint combines:
    1. Fast local search of common assets (instant results)
    2. Real-time yfinance lookup for exact symbol matches

    Args:
        q: Search query (symbol or company name)
        asset_type: Optional filter (stock or crypto)

    Returns:
        List of matching assets with symbol, name, and type
    """
    if not q or len(q.strip()) < 1:
        return []

    query_upper = q.upper().strip()
    results = []
    seen_symbols = set()

    # 1. Try real-time yfinance lookup for exact symbol match
    if len(query_upper) >= 1 and len(query_upper) <= 10:
        try:
            yf_results = await search_symbol_with_yfinance(query_upper)
            for asset in yf_results:
                if asset["symbol"] not in seen_symbols:
                    # Filter by asset type if specified
                    if asset_type and asset.get("type") != asset_type.lower():
                        continue
                    results.append(asset)
                    seen_symbols.add(asset["symbol"])
        except Exception as e:
            logger.debug("yfinance search failed", error=str(e))

    # 2. Search local common assets list (fast, no API call)
    for asset in COMMON_ASSETS:
        if asset["symbol"] in seen_symbols:
            continue
        if query_upper in asset["symbol"] or query_upper in asset["name"].upper():
            # Filter by asset type if specified
            if asset_type and asset.get("type") != asset_type.lower():
                continue
            results.append(asset)
            seen_symbols.add(asset["symbol"])

    # Limit to 10 results
    return results[:10]


# ============================================================================
# FK-DSL API Endpoints
# ============================================================================


class DSLQueryRequest(BaseModel):
    """Request model for FK-DSL query execution"""
    query: str
    async_execution: bool = False


class DSLQueryResponse(BaseModel):
    """Response model for FK-DSL query execution"""
    query: str
    status: str
    result: Optional[Dict[str, Any]] = None
    task_id: Optional[str] = None
    error: Optional[str] = None


class DSLTemplatesResponse(BaseModel):
    """Response model for DSL query templates"""
    templates: List[Dict[str, Any]]


@market_router.post("/dsl/execute", response_model=DSLQueryResponse)
async def execute_dsl_query(request: DSLQueryRequest) -> DSLQueryResponse:
    """
    Execute a Financial Knowledge DSL (FK-DSL) query.

    This endpoint provides mobile app access to FIML's powerful DSL
    for complex financial analysis queries.

    Example queries:
    - EVALUATE TSLA: PRICE, VOLATILITY(30d)
    - COMPARE AAPL, MSFT: PE_RATIO, MARKET_CAP
    - CORRELATE BTC, ETH: PRICE(90d)

    Args:
        request: DSL query request containing the query string

    Returns:
        Query execution result or task ID for async execution
    """
    from fiml.mcp.tools import execute_fk_dsl

    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        logger.info("Executing FK-DSL query via API", query=request.query)

        result = await execute_fk_dsl(
            query=request.query,
            async_execution=request.async_execution
        )

        return DSLQueryResponse(
            query=request.query,
            status=result.get("status", "unknown"),
            result=result.get("result"),
            task_id=result.get("task_id"),
            error=result.get("error"),
        )

    except Exception as e:
        logger.error("FK-DSL execution failed", query=request.query, error=str(e))
        return DSLQueryResponse(
            query=request.query,
            status="failed",
            error=str(e),
        )


@market_router.get("/dsl/templates", response_model=DSLTemplatesResponse)
async def get_dsl_templates() -> DSLTemplatesResponse:
    """
    Get available FK-DSL query templates.

    Returns a list of example queries that users can use as starting points.
    Useful for mobile app UI to show template buttons.
    """
    templates = [
        {
            "id": "evaluate_single",
            "name": "Evaluate Single Stock",
            "description": "Get price and key metrics for a stock",
            "query": "EVALUATE {SYMBOL}: PRICE, VOLUME, PE_RATIO",
            "example": "EVALUATE AAPL: PRICE, VOLUME, PE_RATIO",
            "category": "basic",
        },
        {
            "id": "compare_stocks",
            "name": "Compare Stocks",
            "description": "Compare metrics across multiple stocks",
            "query": "COMPARE {SYMBOL1}, {SYMBOL2}: PE_RATIO, MARKET_CAP",
            "example": "COMPARE AAPL, MSFT: PE_RATIO, MARKET_CAP",
            "category": "comparison",
        },
        {
            "id": "correlate_crypto",
            "name": "Crypto Correlation",
            "description": "Analyze price correlation between cryptocurrencies",
            "query": "CORRELATE {COIN1}, {COIN2}: PRICE({PERIOD})",
            "example": "CORRELATE BTC, ETH: PRICE(30d)",
            "category": "crypto",
        },
        {
            "id": "volatility_analysis",
            "name": "Volatility Analysis",
            "description": "Analyze volatility over different timeframes",
            "query": "EVALUATE {SYMBOL}: VOLATILITY({PERIOD}), PRICE",
            "example": "EVALUATE TSLA: VOLATILITY(30d), PRICE",
            "category": "technical",
        },
        {
            "id": "sector_screen",
            "name": "Sector Screening",
            "description": "Screen stocks in a sector by criteria",
            "query": "SCREEN SECTOR={SECTOR}: PE_RATIO < {VALUE}",
            "example": "SCREEN SECTOR=TECH: PE_RATIO < 30",
            "category": "screening",
        },
        {
            "id": "trend_analysis",
            "name": "Trend Analysis",
            "description": "Analyze price trends over time",
            "query": "TREND {SYMBOL}: PRICE({PERIOD})",
            "example": "TREND NVDA: PRICE(90d)",
            "category": "technical",
        },
    ]

    return DSLTemplatesResponse(templates=templates)
