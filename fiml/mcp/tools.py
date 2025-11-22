"""
MCP Tool Implementations
"""

import uuid
from datetime import datetime, timedelta

from fiml.agents.orchestrator import agent_orchestrator
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
    TaskInfo,
    TaskStatus,
)
from fiml.dsl.executor import fk_dsl_executor
from fiml.dsl.parser import fk_dsl_parser
from fiml.dsl.planner import execution_planner
from fiml.providers import provider_registry

logger = get_logger(__name__)


async def search_by_symbol(
    symbol: str, market: Market, depth: AnalysisDepth, language: str
) -> SearchBySymbolResponse:
    """
    Search for a stock by symbol with instant cached data and async deep analysis

    Args:
        symbol: Stock ticker symbol
        market: Market/exchange
        depth: Analysis depth level
        language: Response language

    Returns:
        SearchBySymbolResponse with cached data and task info
    """
    logger.info(
        "search_by_symbol called", symbol=symbol, market=market, depth=depth, language=language
    )
    
    from fiml.arbitration.engine import arbitration_engine
    from fiml.compliance.router import compliance_router, Region
    from fiml.compliance.disclaimers import disclaimer_generator, AssetClass
    
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
                as_of=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                source="compliance_blocked",
                ttl=0,
                confidence=0.0,
            ),
            task=TaskInfo(
                id="",
                type="equity_analysis",
                status=TaskStatus.FAILED,
                resource_url="",
                estimated_completion=datetime.utcnow(),
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
        # Fetch price data via arbitration engine
        plan = await arbitration_engine.arbitrate_request(
            asset=asset,
            data_type=DataType.PRICE,
            user_region="US",
        )
        
        # Execute the plan
        response = await arbitration_engine.execute_with_fallback(plan, asset, DataType.PRICE)
        
        # Extract data from response
        data = response.data if response else {}
        
        task_id = f"analysis-{symbol.lower()}-{uuid.uuid4().hex[:8]}"
        
        cached_data = CachedData(
            price=data.get("price", 0.0),
            change=data.get("change", 0.0),
            change_percent=data.get("change_percent", 0.0),
            as_of=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            source=response.provider if response else "unknown",
            ttl=300,  # 5 minutes
            confidence=response.confidence if response else 0.0,
        )
        
        task_info = TaskInfo(
            id=task_id,
            type="equity_analysis",
            status=TaskStatus.PENDING,
            resource_url=f"mcp://task/{task_id}",
            estimated_completion=datetime.utcnow() + timedelta(seconds=5),
            progress=0.0,
        )
        
        data_lineage = DataLineage(
            providers=[response.provider] if response else [],
            arbitration_score=plan.estimated_latency_ms / 10.0 if plan else 0.0,
            conflict_resolved=False,
            source_count=1,
        )
        
        # Generate disclaimer
        disclaimer = disclaimer_generator.generate(
            asset_class=AssetClass.EQUITY,
            region=Region.US,
            include_general=True,
        )
        
        return SearchBySymbolResponse(
            symbol=symbol.upper(),
            name=data.get("name", f"{symbol.upper()} Inc."),
            exchange=data.get("exchange", "NASDAQ"),
            market=market.value,
            currency="USD",
            cached=cached_data,
            task=task_info,
            disclaimer=disclaimer,
            data_lineage=data_lineage,
        )
        
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
                as_of=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                source="error",
                ttl=0,
                confidence=0.0,
            ),
            task=TaskInfo(
                id=task_id,
                type="equity_analysis",
                status=TaskStatus.FAILED,
                resource_url=f"mcp://task/{task_id}",
                estimated_completion=datetime.utcnow(),
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
    symbol: str, exchange: str, pair: str, depth: AnalysisDepth, language: str
) -> SearchByCoinResponse:
    """
    Search for cryptocurrency with instant cached data and async deep analysis

    Args:
        symbol: Crypto symbol
        exchange: Preferred exchange
        pair: Trading pair
        depth: Analysis depth level
        language: Response language

    Returns:
        SearchByCoinResponse with cached data and task info
    """
    logger.info(
        "search_by_coin called",
        symbol=symbol,
        exchange=exchange,
        pair=pair,
        depth=depth,
        language=language,
    )
    
    from fiml.arbitration.engine import arbitration_engine
    from fiml.compliance.router import compliance_router, Region
    from fiml.compliance.disclaimers import disclaimer_generator, AssetClass
    
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
                as_of=datetime.utcnow(),
                last_updated=datetime.utcnow(),
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
                estimated_completion=datetime.utcnow(),
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
        # Fetch price data via arbitration engine
        plan = await arbitration_engine.arbitrate_request(
            asset=asset,
            data_type=DataType.PRICE,
            user_region="US",
        )
        
        # Execute the plan
        response = await arbitration_engine.execute_with_fallback(plan, asset, DataType.PRICE)
        
        # Extract data from response
        data = response.data if response else {}
        
        task_id = f"crypto-{symbol.lower()}-{uuid.uuid4().hex[:8]}"
        
        cached_data = CachedData(
            price=data.get("price", 0.0),
            change=data.get("change", 0.0),
            change_percent=data.get("change_percent", 0.0),
            as_of=datetime.utcnow(),
            last_updated=datetime.utcnow(),
            source=response.provider if response else "unknown",
            ttl=30,  # 30 seconds for crypto (more volatile)
            confidence=response.confidence if response else 0.0,
        )
        
        task_info = TaskInfo(
            id=task_id,
            type="crypto_analysis",
            status=TaskStatus.PENDING,
            resource_url=f"mcp://task/{task_id}",
            estimated_completion=datetime.utcnow() + timedelta(seconds=3),
            progress=0.0,
        )
        
        data_lineage = DataLineage(
            providers=[response.provider] if response else [],
            arbitration_score=plan.estimated_latency_ms / 10.0 if plan else 0.0,
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
        
        return SearchByCoinResponse(
            symbol=symbol.upper(),
            name=data.get("name", symbol.upper()),
            pair=crypto_symbol,
            exchange=data.get("exchange", exchange),
            cached=cached_data,
            crypto_metrics=crypto_metrics,
            task=task_info,
            disclaimer=disclaimer,
            data_lineage=data_lineage,
        )
        
    except Exception as e:
        logger.error(f"Error fetching crypto data for {symbol}: {e}")
        
        # Return error response with disclaimer
        task_id = f"crypto-{symbol.lower()}-{uuid.uuid4().hex[:8]}"
        
        return SearchByCoinResponse(
            symbol=symbol.upper(),
            name=symbol.upper(),
            pair=crypto_symbol,
            exchange=exchange,
            cached=CachedData(
                price=0.0,
                change=0.0,
                change_percent=0.0,
                as_of=datetime.utcnow(),
                last_updated=datetime.utcnow(),
                source="error",
                ttl=0,
                confidence=0.0,
            ),
            crypto_metrics={},
            task=TaskInfo(
                id=task_id,
                type="crypto_analysis",
                status=TaskStatus.FAILED,
                resource_url=f"mcp://task/{task_id}",
                estimated_completion=datetime.utcnow(),
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

    # Get status from executor
    task_info = fk_dsl_executor.get_task_status(task_id)
    
    if task_info:
        return {
            "id": task_info.task_id,
            "status": task_info.status.value,
            "query": task_info.query,
            "progress": task_info.completed_steps / task_info.total_steps if task_info.total_steps > 0 else 0.0,
            "completed_steps": task_info.completed_steps,
            "total_steps": task_info.total_steps,
            "created_at": task_info.created_at.isoformat() if task_info.created_at else None,
            "started_at": task_info.started_at.isoformat() if task_info.started_at else None,
            "completed_at": task_info.completed_at.isoformat() if task_info.completed_at else None,
            "result": task_info.result,
            "error": task_info.error,
        }
    
    return {
        "id": task_id,
        "status": "not_found",
        "message": "Task not found",
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
