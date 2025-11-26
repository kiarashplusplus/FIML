"""
Structured logging configuration with Sentry integration
"""

import logging
import sys
from typing import Any

import structlog
from structlog.types import EventDict, Processor

from fiml.core.config import settings
from fiml.core.sentry import init_sentry


def add_app_context(logger: Any, method_name: str, event_dict: EventDict) -> EventDict:
    """Add application context to log entries"""
    event_dict["app"] = "fiml"
    event_dict["environment"] = settings.fiml_env
    return event_dict


def configure_logging() -> None:
    """Configure structured logging with structlog and initialize Sentry"""

    # Determine log level
    log_level = getattr(logging, settings.fiml_log_level.upper())

    # Initialize Sentry for error tracking if DSN is configured
    # Sentry should be initialized early to capture any startup errors
    sentry_initialized = init_sentry(
        dsn=settings.sentry_dsn,
        environment=settings.fiml_env,
        release="fiml@0.2.2",
        # Higher sample rate in production for better visibility
        traces_sample_rate=0.1 if settings.is_production else 0.0,
        profiles_sample_rate=0.1 if settings.is_production else 0.0,
    )

    # Configure structlog processors
    processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        add_app_context,
    ]

    # Add JSON rendering for production, console for development
    if settings.is_production:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )

    # Log Sentry initialization status (only after logging is configured)
    if sentry_initialized:
        temp_logger = structlog.get_logger("fiml.sentry")
        temp_logger.info("Sentry error tracking initialized", environment=settings.fiml_env)


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a configured logger instance"""
    return structlog.get_logger(name)  # type: ignore[no-any-return]


# Configure logging on module import
configure_logging()

# Create default logger
logger = get_logger("fiml")
