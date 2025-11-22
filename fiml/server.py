"""
Main FastAPI MCP Server
"""

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import make_asgi_app

from fiml.core.config import settings
from fiml.core.exceptions import FIMLException
from fiml.core.logging import get_logger
from fiml.mcp.router import mcp_router
from fiml.providers import provider_registry
from fiml.websocket.router import websocket_router

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Lifecycle management for the application"""
    # Startup
    logger.info("Starting FIML server", version="0.1.0", environment=settings.fiml_env)

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
    except:
        pass
    
    await provider_registry.shutdown()
    
    try:
        from fiml.cache.manager import cache_manager
        await cache_manager.shutdown()
    except:
        pass


# Create FastAPI application
app = FastAPI(
    title="FIML - Financial Intelligence Meta-Layer",
    description="AI-Native Multi-Market Financial Intelligence Framework",
    version="0.1.0",
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


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint"""
    return {
        "status": "healthy",
        "version": "0.1.0",
        "environment": settings.fiml_env,
    }


@app.get("/")
async def root() -> dict:
    """Root endpoint"""
    return {
        "service": "FIML - Financial Intelligence Meta-Layer",
        "version": "0.1.0",
        "docs": "/docs" if settings.is_development else None,
        "health": "/health",
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
