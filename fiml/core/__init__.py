"""
Core module initialization
"""

from fiml.core.config import settings
from fiml.core.sentry import (
                              add_breadcrumb,
                              capture_exception,
                              capture_message,
                              init_sentry,
                              set_context,
                              set_tag,
                              set_user,
)

__all__ = [
    "settings",
    "init_sentry",
    "capture_exception",
    "capture_message",
    "set_user",
    "set_tag",
    "set_context",
    "add_breadcrumb",
]
