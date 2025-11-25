"""
Main FastAPI MCP Server
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from fiml.alerts.router import alert_router
from fiml.core.config import settings
from fiml.core.exceptions import FIMLException
from fiml.core.logging import get_logger
from fiml.mcp.router import mcp_router
from fiml.providers import provider_registry
from fiml.web.dashboard import dashboard_router
from fiml.websocket.router import websocket_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifecycle management for the application"""
    # Startup
    logger.info("Starting FIML server", version="0.2.2", environment=settings.fiml_env)

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
        from fiml.cache.manager import cache_manager
        await cache_manager.shutdown()
    except (ImportError, Exception) as e:
        logger.debug(f"Cache manager shutdown skipped: {e}")


# Create FastAPI application
app = FastAPI(
    title="FIML - Financial Intelligence Meta-Layer",
    description="AI-Native Multi-Market Financial Intelligence Framework",
    version="0.2.2",
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


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "0.2.2",
        "environment": settings.fiml_env,
    }


@app.get("/health/db")
async def health_check_db() -> dict:
    """Database (PostgreSQL) health check endpoint"""
    try:
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import create_async_engine

        engine = create_async_engine(settings.database_url, echo=False)
        async with engine.begin() as conn:
            await conn.execute(text("SELECT 1"))
        await engine.dispose()

        return {
            "status": "healthy",
            "service": "postgresql",
            "host": settings.postgres_host,
            "port": settings.postgres_port,
            "database": settings.postgres_db,
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "postgresql",
                "error": str(e),
            },
        )


@app.get("/health/cache")
async def health_check_cache() -> dict:
    """Cache (Redis) health check endpoint"""
    try:
        from fiml.cache.l1_cache import l1_cache

        # Try to ping Redis
        if l1_cache._redis:
            await l1_cache._redis.ping()
            return {
                "status": "healthy",
                "service": "redis",
                "host": settings.redis_host,
                "port": settings.redis_port,
            }
        else:
            # Try to initialize and check
            import redis.asyncio as aioredis

            redis_client = aioredis.from_url(
                settings.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
            )
            await redis_client.ping()
            await redis_client.aclose()

            return {
                "status": "healthy",
                "service": "redis",
                "host": settings.redis_host,
                "port": settings.redis_port,
            }
    except Exception as e:
        logger.error(f"Cache health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "redis",
                "error": str(e),
            },
        )


@app.get("/health/providers")
async def health_check_providers() -> dict:
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
                "last_check": health.last_check.isoformat() if health.last_check else None,
                "error_count_24h": health.error_count_24h,
            }
            if not health.is_healthy:
                all_healthy = False

        return {
            "status": "healthy" if all_healthy else "degraded",
            "total_providers": len(providers_health),
            "healthy_providers": sum(1 for h in health_status.values() if h.is_healthy),
            "providers": providers_health,
        }
    except Exception as e:
        logger.error(f"Provider health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
            },
        )


@app.get("/health/providers/{provider_name}")
async def health_check_provider(provider_name: str) -> dict:
    """Individual provider health check endpoint"""
    try:
        health = await provider_registry.get_provider_health(provider_name)

        if health is None:
            return JSONResponse(
                status_code=404,
                content={
                    "error": "ProviderNotFound",
                    "message": f"Provider '{provider_name}' not found",
                },
            )

        return {
            "provider": provider_name,
            "is_healthy": health.is_healthy,
            "uptime_percent": health.uptime_percent,
            "avg_latency_ms": health.avg_latency_ms,
            "success_rate": health.success_rate,
            "last_check": health.last_check.isoformat() if health.last_check else None,
            "error_count_24h": health.error_count_24h,
        }
    except Exception as e:
        logger.error(f"Provider health check failed for {provider_name}: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "provider": provider_name,
                "error": str(e),
            },
        )


@app.get("/")
async def root() -> dict:
    """Root endpoint"""
    return {
        "service": "FIML - Financial Intelligence Meta-Layer",
        "version": "0.2.2",
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
