"""
Sentry integration for FIML error tracking and monitoring.

This module initializes Sentry SDK with proper configuration for the FIML application,
including:
- Automatic exception capture
- Performance monitoring (traces)
- Integration with structlog for breadcrumbs
- Environment and release tagging
"""

import logging
from typing import Any, Literal

import sentry_sdk
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration
from sentry_sdk.types import Event, Hint

# Type alias for log levels accepted by Sentry
LogLevel = Literal["fatal", "critical", "error", "warning", "info", "debug"]


def init_sentry(
    dsn: str | None = None,
    environment: str = "development",
    release: str | None = None,
    traces_sample_rate: float = 0.1,
    profiles_sample_rate: float = 0.1,
) -> bool:
    """
    Initialize Sentry SDK for error tracking.

    Args:
        dsn: Sentry Data Source Name. If None or empty, Sentry is not initialized.
        environment: Environment name (development, staging, production, test)
        release: Release version string
        traces_sample_rate: Sample rate for performance monitoring (0.0 to 1.0)
        profiles_sample_rate: Sample rate for profiling (0.0 to 1.0)

    Returns:
        True if Sentry was initialized successfully, False otherwise.
    """
    if not dsn:
        return False

    # Configure logging integration to capture breadcrumbs
    # Only capture WARNING and above as breadcrumbs, ERROR and above as events
    logging_integration = LoggingIntegration(
        level=logging.INFO,  # Capture INFO+ as breadcrumbs
        event_level=logging.ERROR,  # Send ERROR+ as events
    )

    try:
        sentry_sdk.init(
            dsn=dsn,
            environment=environment,
            release=release,
            # Performance monitoring
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            # Integrations
            integrations=[
                logging_integration,
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
                AsyncioIntegration(),
            ],
            # Send default PII
            send_default_pii=False,
            # Attach stack traces to log messages
            attach_stacktrace=True,
            # Filter out specific exceptions that are not actionable
            before_send=_before_send,
        )
        return True
    except Exception:
        # If Sentry initialization fails, don't crash the application
        return False


def _before_send(event: Event, hint: Hint) -> Event | None:
    """
    Filter events before sending to Sentry.

    This can be used to:
    - Filter out non-actionable exceptions
    - Sanitize sensitive data
    - Add additional context
    """
    # Get exception info if available
    if "exc_info" in hint:
        exc_type, exc_value, _tb = hint["exc_info"]

        # Filter out expected exceptions that don't need tracking
        # For example, client disconnections or validation errors
        if exc_type.__name__ in ("CancelledError", "ConnectionResetError"):
            return None

    return event


def capture_exception(exception: Exception, **kwargs: Any) -> str | None:
    """
    Capture an exception and send it to Sentry.

    Args:
        exception: The exception to capture
        **kwargs: Additional context to attach to the event

    Returns:
        The Sentry event ID if captured, None otherwise.
    """
    with sentry_sdk.push_scope() as scope:
        for key, value in kwargs.items():
            scope.set_extra(key, value)
        return sentry_sdk.capture_exception(exception)


def capture_message(message: str, level: LogLevel = "info", **kwargs: Any) -> str | None:
    """
    Capture a message and send it to Sentry.

    Args:
        message: The message to capture
        level: Log level (debug, info, warning, error, fatal)
        **kwargs: Additional context to attach to the event

    Returns:
        The Sentry event ID if captured, None otherwise.
    """
    with sentry_sdk.push_scope() as scope:
        for key, value in kwargs.items():
            scope.set_extra(key, value)
        return sentry_sdk.capture_message(message, level=level)


def set_user(user_id: str | None = None, **kwargs: Any) -> None:
    """
    Set user context for Sentry events.

    Args:
        user_id: Unique identifier for the user
        **kwargs: Additional user attributes (email, username, ip_address, etc.)
    """
    user_data = kwargs
    if user_id:
        user_data["id"] = user_id
    sentry_sdk.set_user(user_data if user_data else None)


def set_tag(key: str, value: str) -> None:
    """
    Set a tag for Sentry events.

    Tags are indexed and searchable in Sentry.

    Args:
        key: Tag name
        value: Tag value
    """
    sentry_sdk.set_tag(key, value)


def set_context(name: str, context: dict[str, Any]) -> None:
    """
    Set additional context for Sentry events.

    Contexts are key-value data that provide additional information.

    Args:
        name: Context name
        context: Context data dictionary
    """
    sentry_sdk.set_context(name, context)


def add_breadcrumb(
    message: str,
    category: str = "default",
    level: str = "info",
    data: dict[str, Any] | None = None,
) -> None:
    """
    Add a breadcrumb for debugging context.

    Breadcrumbs are a trail of events that happened prior to an error.

    Args:
        message: Breadcrumb message
        category: Category for grouping (e.g., "http", "query", "user")
        level: Breadcrumb level (debug, info, warning, error, critical)
        data: Additional data for the breadcrumb
    """
    sentry_sdk.add_breadcrumb(
        message=message,
        category=category,
        level=level,
        data=data or {},
    )
