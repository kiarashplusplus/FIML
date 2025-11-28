"""
Main FastAPI MCP Server
"""

from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Dict

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from fiml.alerts.router import alert_router
from fiml.bot.key_router import router as key_router
from fiml.bot.router import router as bot_router
from fiml.core.config import settings
from fiml.core.exceptions import FIMLException
from fiml.core.logging import get_logger
from fiml.core.sentry import capture_exception, set_context
from fiml.mcp.router import mcp_router
from fiml.monitoring.performance import PerformanceMiddleware
from fiml.providers import provider_registry
from fiml.web.dashboard import dashboard_router
from fiml.web.market_api import market_router
from fiml.websocket.router import websocket_router

logger = get_logger(__name__)


@asynccontextmanager  # type: ignore
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifecycle management for the application"""
    # Startup
    logger.info("Starting FIML server", version="0.3.0", environment=settings.fiml_env)

    # Initialize cache layers
    logger.info("Initializing cache layers...")
    try:
        from fiml.cache.manager import cache_manager

        await cache_manager.initialize()
    except Exception as e:
        logger.warning(f"Cache initialization failed (non-critical): {e}")

    # Initialize provider registry
    await provider_registry.initialize()
    logger.info("Provider registry initialized", provider_count=len(provider_registry.providers))

    # Initialize Ray cluster for multi-agent orchestration
    if settings.ray_address:
        logger.info("Initializing agent orchestrator...")
        try:
            from fiml.agents.orchestrator import agent_orchestrator

            await agent_orchestrator.initialize()
        except Exception as e:
            logger.warning(f"Agent orchestrator initialization failed (non-critical): {e}")

    # Initialize Cache Warmer
    if settings.enable_cache_warming:
        logger.info("Initializing cache warmer...")
        try:
            from fiml.cache.warming import cache_warmer

            await cache_warmer.initialize()
            # Start background warming if enabled
            await cache_warmer.start_background_warming(
                interval_minutes=settings.cache_warming_interval_seconds // 60
            )
        except Exception as e:
            logger.warning(f"Cache warmer initialization failed (non-critical): {e}")

    yield

    # Shutdown
    logger.info("Shutting down FIML server")

    try:
        from fiml.agents.orchestrator import agent_orchestrator

        if agent_orchestrator.initialized:
            await agent_orchestrator.shutdown()
    except (ImportError, Exception) as e:
        logger.debug(f"Agent orchestrator shutdown skipped: {e}")

    await provider_registry.shutdown()

    try:
        from fiml.cache.warming import cache_warmer

        if settings.enable_cache_warming:
            await cache_warmer.stop_background_warming()
    except (ImportError, Exception) as e:
        logger.debug(f"Cache warmer shutdown skipped: {e}")

    try:
        from fiml.cache.manager import cache_manager

        await cache_manager.shutdown()
    except (ImportError, Exception) as e:
        logger.debug(f"Cache manager shutdown skipped: {e}")


# Create FastAPI application
app = FastAPI(
    title="FIML - Financial Intelligence Meta-Layer",
    description="AI-Native Multi-Market Financial Intelligence Framework",
    version="0.3.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.is_development else None,
    redoc_url="/redoc" if settings.is_development else None,
)

# Add CORS middleware
if settings.enable_cors:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Add performance monitoring middleware
app.add_middleware(PerformanceMiddleware)

# Mount Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Include MCP router
app.include_router(mcp_router, prefix="/mcp", tags=["mcp"])

# Include WebSocket router
app.include_router(websocket_router, prefix="/ws", tags=["websocket"])

# Include Dashboard router
app.include_router(dashboard_router, prefix="/dashboard", tags=["dashboard"])

# Include Alert router
app.include_router(alert_router, prefix="/api", tags=["alerts"])

# Include Bot router (for Mobile/Web apps)
app.include_router(bot_router, prefix="/api/bot", tags=["bot"])

# Key Management API (for mobile app)
app.include_router(key_router, tags=["keys"])


# Include Market API router (for Mobile/Web apps)
app.include_router(market_router, prefix="/api/market", tags=["market"])


@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "0.3.0",
        "environment": settings.fiml_env,
    }


@app.get("/api/metrics/cache")
async def get_cache_metrics() -> Dict[str, Any]:
    """Get cache analytics metrics"""
    try:
        from fiml.cache.analytics import cache_analytics

        return cache_analytics.get_comprehensive_report()
    except Exception as e:
        logger.error(f"Failed to get cache metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cache metrics: {str(e)}")


@app.get("/api/metrics/watchdog")
async def get_watchdog_metrics() -> Dict[str, Any]:
    """Get watchdog health metrics"""
    try:
        from fiml.watchdog.health import watchdog_health_monitor

        return watchdog_health_monitor.get_health_summary()
    except Exception as e:
        logger.error(f"Failed to get watchdog metrics: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve watchdog metrics: {str(e)}"
        )


@app.get("/api/metrics/performance")
async def get_performance_metrics() -> Dict[str, Any]:
    """Get performance monitoring metrics"""
    try:
        from fiml.monitoring.performance import get_performance_metrics

        return get_performance_metrics()
    except Exception as e:
        logger.error(f"Failed to get performance metrics: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve performance metrics: {str(e)}"
        )


@app.get("/api/metrics/tasks")
async def get_task_metrics() -> Dict[str, Any]:
    """Get task registry metrics"""
    try:
        from fiml.monitoring.task_registry import task_registry

        return task_registry.get_stats()
    except Exception as e:
        logger.error(f"Failed to get task metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve task metrics: {str(e)}")


# Module-level database engine for health checks (created lazily)
_health_check_engine = None


async def _get_health_check_engine() -> Any:
    """Get or create a shared database engine for health checks"""
    global _health_check_engine
    if _health_check_engine is None:
        from sqlalchemy.ext.asyncio import create_async_engine

        _health_check_engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_size=1,
            max_overflow=0,
            pool_pre_ping=True,
        )
    return _health_check_engine


@app.get("/health/db")
async def health_check_db() -> Dict[str, Any]:
    """Database (PostgreSQL) health check endpoint"""
    try:
        from sqlalchemy import text

        engine = await _get_health_check_engine()
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))

        return {
            "status": "healthy",
            "service": "postgresql",
            "host": settings.postgres_host,
            "port": settings.postgres_port,
            "database": settings.postgres_db,
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Database health check failed: {str(e)}")


# Module-level Redis client for health checks (created lazily)
_health_check_redis = None


async def _get_health_check_redis() -> Any:
    """Get or create a shared Redis client for health checks"""
    global _health_check_redis
    if _health_check_redis is None:
        import redis.asyncio as aioredis

        _health_check_redis = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            socket_timeout=5,
        )
    return _health_check_redis


@app.get("/health/cache")
async def health_check_cache() -> Dict[str, Any]:
    """Cache (Redis) health check endpoint"""
    try:
        from fiml.cache.l1_cache import l1_cache

        # Try to use the existing l1_cache connection first
        if l1_cache._redis:
            await l1_cache._redis.ping()
            return {
                "status": "healthy",
                "service": "redis",
                "host": settings.redis_host,
                "port": settings.redis_port,
            }
        else:
            # Use the shared health check Redis client
            redis_client = await _get_health_check_redis()
            await redis_client.ping()

            return {
                "status": "healthy",
                "service": "redis",
                "host": settings.redis_host,
                "port": settings.redis_port,
            }
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Cache health check failed: {str(e)}")


@app.get("/health/providers")
async def health_check_providers() -> Dict[str, Any]:
    """Provider health check endpoint - returns health status of all data providers"""
    try:
        health_status = await provider_registry.get_all_health()

        providers_health = {}
        all_healthy = True

        for provider_name, health in health_status.items():
            providers_health[provider_name] = {
                "is_healthy": health.is_healthy,
                "uptime_percent": health.uptime_percent,
                "avg_latency_ms": health.avg_latency_ms,
                "success_rate": health.success_rate,
                "last_check": health.last_check.isoformat(),
                "error_count_24h": health.error_count_24h,
            }
            if not health.is_healthy:
                all_healthy = False

        return {
            "status": "healthy" if all_healthy else "degraded",
            "service": "data_providers",
            "total_providers": len(providers_health),
            "healthy_providers": sum(1 for h in health_status.values() if h.is_healthy),
            "providers": providers_health,
        }
    except Exception as e:
        logger.error(f"Provider health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Provider health check failed: {str(e)}")


@app.get("/health/providers/{provider_name}")
async def health_check_provider(provider_name: str) -> Dict[str, Any]:
    """Individual provider health check endpoint"""
    try:
        health = await provider_registry.get_provider_health(provider_name)

        if not health:
            raise HTTPException(status_code=404, detail=f"Provider '{provider_name}' not found")

        return {
            "status": "healthy" if health.is_healthy else "unhealthy",
            "provider": provider_name,
            "is_healthy": health.is_healthy,
            "uptime_percent": health.uptime_percent,
            "avg_latency_ms": health.avg_latency_ms,
            "success_rate": health.success_rate,
            "last_check": health.last_check.isoformat(),
            "error_count_24h": health.error_count_24h,
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Provider '{provider_name}' health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Provider health check failed: {str(e)}")


@app.get("/")
async def root() -> dict:
    """Root endpoint"""
    return {
        "service": "FIML - Financial Intelligence Meta-Layer",
        "version": "0.3.0",
        "docs": "/docs" if settings.is_development else None,
        "health": "/health",
        "health_endpoints": {
            "main": "/health",
            "database": "/health/db",
            "cache": "/health/cache",
            "providers": "/health/providers",
            "provider_specific": "/health/providers/{provider_name}",
        },
        "metrics": "/metrics",
        "metrics_endpoints": {
            "prometheus": "/metrics",
            "cache": "/api/metrics/cache",
            "watchdog": "/api/metrics/watchdog",
            "performance": "/api/metrics/performance",
            "tasks": "/api/metrics/tasks",
        },
    }


@app.exception_handler(FIMLException)
async def fiml_exception_handler(request: Request, exc: FIMLException) -> JSONResponse:
    """Handle FIML-specific exceptions"""
    logger.error(
        "FIML exception occurred",
        exception=str(exc),
        exception_type=type(exc).__name__,
        path=request.url.path,
    )
    # Capture FIML exceptions to Sentry with context
    capture_exception(
        exc,
        request_path=request.url.path,
        request_method=request.method,
    )
    return JSONResponse(
        status_code=400,
        content={
            "error": type(exc).__name__,
            "message": str(exc),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle general exceptions"""
    logger.exception(
        "Unexpected exception occurred",
        exception=str(exc),
        exception_type=type(exc).__name__,
        path=request.url.path,
    )
    # Capture unexpected exceptions to Sentry with request context
    set_context(
        "request",
        {
            "path": request.url.path,
            "method": request.method,
            "query_string": str(request.query_params),
        },
    )
    capture_exception(exc)
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "An unexpected error occurred",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "fiml.server:app",
        host=settings.fiml_host,
        port=settings.fiml_port,
        reload=settings.is_development,
        log_level=settings.fiml_log_level.lower(),
    )
